"""Lambda handlers for Slack interactivity — button actions and slash commands.

Endpoints:
  POST /slack/actions   — button clicks, interactive components
  POST /slack/commands  — slash commands (/rank, /outreach, /post-job, /candidates)
"""

import json
import logging
from urllib.parse import parse_qs

from src.models.candidate import Candidate, CandidateStatus
from src.models.job import Job
from src.services import dynamodb
from src.services.filtering import filter_candidates, generate_prescreen_questions
from src.services.slack import (
    verify_slack_signature,
    respond_to_action,
    post_rankings,
    send_notification,
    _candidate_blocks,
    _api_call,
    SLACK_CHANNEL,
)
from src.utils.response import success, error

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Actions handler — button clicks
# ---------------------------------------------------------------------------

def handle_actions(event, context):
    """POST /slack/actions — Handle Slack interactive component payloads."""
    try:
        body_raw = event.get("body", "") or ""
        headers = event.get("headers") or {}

        # Verify signature
        if not verify_slack_signature(
            body_raw,
            headers.get("X-Slack-Request-Timestamp", ""),
            headers.get("X-Slack-Signature", ""),
        ):
            return error("Invalid Slack signature", status_code=401)

        # Slack sends URL-encoded payload
        parsed = parse_qs(body_raw)
        payload = json.loads(parsed.get("payload", ["{}"])[0])

        action_type = payload.get("type")

        if action_type == "block_actions":
            for action in payload.get("actions", []):
                _dispatch_action(action, payload)

        # Always return 200 immediately — Slack requires < 3s response
        return {"statusCode": 200, "body": ""}
    except Exception as e:
        logger.error(f"Slack actions handler error: {e}")
        return {"statusCode": 200, "body": ""}  # Still 200 — never let Slack retry


def _dispatch_action(action: dict, payload: dict):
    """Route a button action to the right handler."""
    action_id = action.get("action_id", "")
    value = json.loads(action.get("value", "{}"))
    response_url = payload.get("response_url", "")
    user = payload.get("user", {})

    candidate_id = value.get("candidate_id", "")
    job_id = value.get("job_id", "")

    if action_id == "view_profile":
        _action_view_profile(candidate_id, job_id, response_url)

    elif action_id == "schedule_interview":
        _action_schedule_interview(candidate_id, job_id, response_url, user)

    elif action_id == "send_outreach":
        _action_send_outreach(candidate_id, job_id, response_url)

    elif action_id == "reject_candidate":
        _action_reject(candidate_id, response_url)


def _action_view_profile(candidate_id: str, job_id: str, response_url: str):
    candidate_item = dynamodb.get_item(f"CANDIDATE#{candidate_id}", "PROFILE")
    if not candidate_item:
        respond_to_action(response_url, "❌ Candidate not found.", replace=False)
        return

    job_item = dynamodb.get_item(f"JOB#{job_id}", "METADATA") if job_id else None
    candidate = Candidate.from_dynamo(candidate_item).to_api()
    job = Job.from_dynamo(job_item).to_api() if job_item else {"title": "Unknown", "job_id": job_id}

    from src.services.filtering import score_candidate
    score = score_candidate(candidate, job)
    blocks = _candidate_blocks(candidate, job, score)
    respond_to_action(response_url, f"Profile: {candidate['first_name']} {candidate['last_name']}", blocks=blocks, replace=False)


def _action_schedule_interview(candidate_id: str, job_id: str, response_url: str, user: dict):
    """Prompt recruiter to provide interview time in thread."""
    respond_to_action(
        response_url,
        f"📅 To schedule an interview, use:\n`/schedule-interview {candidate_id} YYYY-MM-DDTHH:MM:00-05:00 [duration_mins]`\nExample: `/schedule-interview {candidate_id} 2026-03-25T10:00:00-05:00 30`",
        replace=False,
    )


def _action_send_outreach(candidate_id: str, job_id: str, response_url: str):
    """Fire interview invite outreach to candidate."""
    try:
        from src.services.outreach import send_outreach
        candidate_item = dynamodb.get_item(f"CANDIDATE#{candidate_id}", "PROFILE")
        job_item = dynamodb.get_item(f"JOB#{job_id}", "METADATA") if job_id else None
        if not candidate_item:
            respond_to_action(response_url, "❌ Candidate not found.", replace=False)
            return

        candidate = Candidate.from_dynamo(candidate_item).to_api()
        job = Job.from_dynamo(job_item).to_api() if job_item else {}
        result = send_outreach(candidate, job, channel="email", template="interview_invite")
        respond_to_action(
            response_url,
            f"✉️ Outreach sent to {candidate['first_name']} {candidate['last_name']} ({candidate.get('email', '—')})",
            replace=False,
        )
    except Exception as e:
        respond_to_action(response_url, f"❌ Outreach failed: {e}", replace=False)


def _action_reject(candidate_id: str, response_url: str):
    """Mark candidate as rejected."""
    try:
        dynamodb.update_status(f"CANDIDATE#{candidate_id}", "PROFILE", CandidateStatus.REJECTED.value)
        candidate_item = dynamodb.get_item(f"CANDIDATE#{candidate_id}", "PROFILE")
        name = ""
        if candidate_item:
            c = Candidate.from_dynamo(candidate_item)
            name = f"{c.first_name} {c.last_name}"
        respond_to_action(response_url, f"❌ {name} marked as rejected.", replace=False)
    except Exception as e:
        respond_to_action(response_url, f"❌ Failed to reject: {e}", replace=False)


# ---------------------------------------------------------------------------
# Slash commands handler
# ---------------------------------------------------------------------------

def handle_commands(event, context):
    """POST /slack/commands — Handle Slack slash commands.

    Supported commands:
      /rank [job_title_or_id] [location]   — rank candidates for a job
      /candidates [job_title_or_id]         — list candidates with status
      /outreach [candidate_id] [channel]   — send outreach to a candidate
      /post-job [job_id]                   — publish job to Indeed
      /prescreen [job_id]                  — show pre-screen questions
    """
    try:
        body_raw = event.get("body", "") or ""
        headers = event.get("headers") or {}

        if not verify_slack_signature(
            body_raw,
            headers.get("X-Slack-Request-Timestamp", ""),
            headers.get("X-Slack-Signature", ""),
        ):
            return _slash_response("❌ Invalid request signature.")

        params = parse_qs(body_raw)
        command = params.get("command", [""])[0]
        text = params.get("text", [""])[0].strip()
        channel_id = params.get("channel_id", [""])[0]
        user_id = params.get("user_id", [""])[0]

        if command == "/rank":
            return _cmd_rank(text, channel_id)
        elif command == "/candidates":
            return _cmd_candidates(text, channel_id)
        elif command == "/outreach":
            return _cmd_outreach(text, channel_id)
        elif command == "/post-job":
            return _cmd_post_job(text, channel_id)
        elif command == "/prescreen":
            return _cmd_prescreen(text, channel_id)
        else:
            return _slash_response(f"Unknown command: `{command}`")
    except Exception as e:
        logger.error(f"Slack commands handler error: {e}")
        return _slash_response(f"❌ Error: {e}")


def _slash_response(text: str, blocks: list = None, in_channel: bool = False) -> dict:
    """Return a properly formatted Slack slash command response."""
    payload = {
        "response_type": "in_channel" if in_channel else "ephemeral",
        "text": text,
    }
    if blocks:
        payload["blocks"] = blocks
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def _find_job_by_title_or_id(query: str) -> dict:
    """Look up a job by ID or by title substring match."""
    # Try direct ID lookup
    item = dynamodb.get_item(f"JOB#{query}", "METADATA")
    if item:
        return Job.from_dynamo(item).to_api()

    # Scan open jobs for title match
    items = dynamodb.query_gsi1("JOBS", "STATUS#open")
    query_lower = query.lower()
    for item in items:
        job = Job.from_dynamo(item).to_api()
        if query_lower in job.get("title", "").lower():
            return job
    return {}


def _cmd_rank(text: str, channel_id: str) -> dict:
    """
    /rank [job_title_or_id]
    Post ranked candidates for a job to the channel.
    """
    if not text:
        return _slash_response("Usage: `/rank [job title or ID]`\nExample: `/rank Massage Therapist`")

    job = _find_job_by_title_or_id(text)
    if not job:
        return _slash_response(f"❌ No open job found matching `{text}`")

    candidate_items = dynamodb.query_gsi1(f"JOB#{job['job_id']}", "STATUS#")
    candidates = [Candidate.from_dynamo(i).to_api() for i in candidate_items]

    if not candidates:
        return _slash_response(f"No candidates found for *{job['title']}*.")

    rankings = filter_candidates(candidates, job)
    post_rankings(rankings, job, channel=channel_id)
    return _slash_response(f"📊 Posted rankings for *{job['title']}* ({len(rankings)} candidates)", in_channel=False)


def _cmd_candidates(text: str, channel_id: str) -> dict:
    """
    /candidates [job_title_or_id]
    List candidates with status for a job.
    """
    if not text:
        return _slash_response("Usage: `/candidates [job title or ID]`")

    job = _find_job_by_title_or_id(text)
    if not job:
        return _slash_response(f"❌ No open job found matching `{text}`")

    items = dynamodb.query_gsi1(f"JOB#{job['job_id']}", "STATUS#")
    candidates = [Candidate.from_dynamo(i).to_api() for i in items]

    if not candidates:
        return _slash_response(f"No candidates for *{job['title']}*.")

    lines = [f"*Candidates — {job['title']}* ({len(candidates)} total)\n"]
    for c in candidates:
        resp = c.get("response_status", "not_contacted")
        resp_emoji = {"responsive": "🟢", "awaiting_response": "🟡", "unresponsive": "🔴", "not_contacted": "⚪"}.get(resp, "⚪")
        lines.append(
            f"• *{c['first_name']} {c['last_name']}* — `{c['status']}` {resp_emoji} `{resp}`"
        )

    return _slash_response("\n".join(lines), in_channel=True)


def _cmd_outreach(text: str, channel_id: str) -> dict:
    """
    /outreach [candidate_id] [email|sms]
    Send outreach to a candidate.
    """
    parts = text.split()
    if not parts:
        return _slash_response("Usage: `/outreach [candidate_id] [email|sms]`")

    candidate_id = parts[0]
    channel = parts[1] if len(parts) > 1 else "email"

    candidate_item = dynamodb.get_item(f"CANDIDATE#{candidate_id}", "PROFILE")
    if not candidate_item:
        return _slash_response(f"❌ Candidate `{candidate_id}` not found.")

    try:
        from src.services.outreach import send_outreach
        candidate = Candidate.from_dynamo(candidate_item).to_api()
        job_item = dynamodb.get_item(f"JOB#{candidate.get('job_id', '')}", "METADATA") if candidate.get("job_id") else None
        job = Job.from_dynamo(job_item).to_api() if job_item else {}
        send_outreach(candidate, job, channel=channel, template="interview_invite")
        return _slash_response(
            f"✉️ Outreach sent to *{candidate['first_name']} {candidate['last_name']}* via {channel}",
            in_channel=True,
        )
    except Exception as e:
        return _slash_response(f"❌ Outreach failed: {e}")


def _cmd_post_job(text: str, channel_id: str) -> dict:
    """
    /post-job [job_id]
    Publish a job to Indeed.
    """
    if not text:
        return _slash_response("Usage: `/post-job [job_id]`")

    item = dynamodb.get_item(f"JOB#{text.strip()}", "METADATA")
    if not item:
        return _slash_response(f"❌ Job `{text}` not found.")

    try:
        from src.services.indeed import post_job_to_indeed
        job = Job.from_dynamo(item).to_api()
        result = post_job_to_indeed(job)
        if result["success"]:
            dynamodb.update_attribute(f"JOB#{job['job_id']}", "METADATA", "indeed_job_id", result["indeed_job_id"])
            return _slash_response(f"✅ *{job['title']}* posted to Indeed (ID: `{result['indeed_job_id']}`)", in_channel=True)
        else:
            return _slash_response(f"❌ Failed to post to Indeed: {result['error']}")
    except Exception as e:
        return _slash_response(f"❌ Error: {e}")


def _cmd_prescreen(text: str, channel_id: str) -> dict:
    """
    /prescreen [job_id]
    Show auto-generated pre-screen questions for a job.
    """
    if not text:
        return _slash_response("Usage: `/prescreen [job_id]`")

    item = dynamodb.get_item(f"JOB#{text.strip()}", "METADATA")
    if not item:
        job = _find_job_by_title_or_id(text)
        if not job:
            return _slash_response(f"❌ Job `{text}` not found.")
        job_dict = job
    else:
        job_dict = Job.from_dynamo(item).to_api()

    questions = generate_prescreen_questions(job_dict)
    if not questions:
        return _slash_response("No pre-screen questions generated for this job.")

    lines = [f"*Pre-Screen Questions — {job_dict.get('title', 'Job')}*\n"]
    for i, q in enumerate(questions, 1):
        lines.append(f"{i}. {q}")

    return _slash_response("\n".join(lines))
