"""Slack service — notifications, Block Kit messages, and interactive API calls.

Two modes:
1. Webhook (legacy) — one-way notifications via SLACK_WEBHOOK_URL
2. Bot API (full) — interactive messages, button responses, slash commands via SLACK_BOT_TOKEN

For interactive features, set SLACK_BOT_TOKEN + SLACK_SIGNING_SECRET.
"""

import json
import os
import logging
from typing import Optional
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#recruiting")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")

SLACK_API_BASE = "https://slack.com/api"

# Recommendation → emoji + color
RECOMMENDATION_STYLE = {
    "suggest_interview": {"emoji": "✅", "color": "#2eb886"},
    "flag_review":       {"emoji": "🟡", "color": "#e6a817"},
    "needs_info":        {"emoji": "⚪", "color": "#aaaaaa"},
    "disqualified":      {"emoji": "❌", "color": "#cc0000"},
}


# ---------------------------------------------------------------------------
# Core API caller
# ---------------------------------------------------------------------------

def _api_call(method: str, payload: dict) -> dict:
    """Call a Slack API method with bot token auth."""
    if not SLACK_BOT_TOKEN:
        logger.warning("SLACK_BOT_TOKEN not set — Slack API calls disabled")
        return {"ok": False, "error": "bot_token_not_configured"}

    data = json.dumps(payload).encode("utf-8")
    req = Request(
        f"{SLACK_API_BASE}/{method}",
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        },
    )
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        logger.error(f"Slack API call {method} failed: {e}")
        return {"ok": False, "error": str(e)}


def _webhook_send(payload: dict) -> bool:
    """Send via incoming webhook (fallback, no interactivity)."""
    if not SLACK_WEBHOOK_URL:
        return False
    req = Request(
        SLACK_WEBHOOK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        logger.error(f"Slack webhook send failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------

def verify_slack_signature(body: str, timestamp: str, signature: str) -> bool:
    """Verify Slack request signature using SLACK_SIGNING_SECRET."""
    import hmac
    import hashlib
    import time

    if not SLACK_SIGNING_SECRET:
        logger.warning("SLACK_SIGNING_SECRET not set — skipping signature verification")
        return True  # permissive if not configured

    # Reject stale requests (> 5 minutes old)
    try:
        if abs(time.time() - float(timestamp)) > 300:
            return False
    except (ValueError, TypeError):
        return False

    base = f"v0:{timestamp}:{body}"
    expected = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        base.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Block Kit builders
# ---------------------------------------------------------------------------

def _score_badge(total_score) -> str:
    """Return a colored score badge string for Block Kit display."""
    if not isinstance(total_score, (int, float)):
        return "⚪ —/100"
    score = int(total_score)
    if score >= 75:
        return f"🟢 *{score}/100*"
    elif score >= 50:
        return f"🟡 *{score}/100*"
    else:
        return f"🔴 *{score}/100*"


def _candidate_blocks(candidate: dict, job: dict, score: Optional[dict] = None) -> list:
    """Build Slack Block Kit blocks for a candidate card."""
    rec = (score or {}).get("recommendation", "")
    style = RECOMMENDATION_STYLE.get(rec, {"emoji": "❓", "color": "#aaaaaa"})
    rec_text = f"{style['emoji']} {rec.replace('_', ' ').title()}" if rec else ""
    total = (score or {}).get("total_score", "—")
    badge = _score_badge(total)

    certs = candidate.get("certifications") or []
    cert_text = ", ".join(certs) if certs else "_none listed_"

    avail = candidate.get("availability") or {}
    all_shifts = sorted({s for shifts in avail.values() for s in (shifts if isinstance(shifts, list) else [])})
    avail_text = ", ".join(all_shifts) if all_shifts else "_not specified_"

    yrs = candidate.get("years_experience")
    yrs_text = f"{yrs} yr{'s' if yrs != 1 else ''}" if yrs else "_unknown_"

    name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
    job_title = job.get("title", "Unknown Position")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"👤 {name} — {job_title}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Score*\n{badge}  {rec_text}"},
                {"type": "mrkdwn", "text": f"*Experience*\n{yrs_text}"},
                {"type": "mrkdwn", "text": f"*Location*\n{candidate.get('location', '—')}"},
                {"type": "mrkdwn", "text": f"*Certifications*\n{cert_text}"},
            ],
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Availability*\n{avail_text}"},
                {"type": "mrkdwn", "text": (
                    f"*Contact*\n📧 {candidate.get('email', '—')}  📞 {candidate.get('phone', '—')}"
                )},
            ],
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": (
                f"Source: `{candidate.get('source', 'unknown')}`  |  Status: `{candidate.get('status', 'new')}`"
            )}],
        },
    ]

    # Score breakdown if available
    if score and score.get("breakdown"):
        bd = score["breakdown"]
        breakdown_text = "  ".join([
            f"Certs: {bd.get('certifications', '—')}",
            f"Avail: {bd.get('availability', '—')}",
            f"Exp: {bd.get('experience', '—')}",
            f"Loc: {bd.get('location', '—')}",
        ])
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"📊 Score breakdown: {breakdown_text}"}],
        })

    # Disqualification reason
    if score and score.get("disqualification_reasons"):
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"⛔ {' | '.join(score['disqualification_reasons'])}",
            }],
        })

    # Action buttons
    cid = candidate.get("candidate_id", "")
    jid = job.get("job_id", "")
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Schedule Interview"},
                "style": "primary",
                "action_id": "schedule_interview",
                "value": json.dumps({"candidate_id": cid, "job_id": jid}),
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "👀 Flag for Review"},
                "action_id": "flag_review",
                "value": json.dumps({"candidate_id": cid, "job_id": jid}),
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "❌ Reject"},
                "style": "danger",
                "action_id": "reject_candidate",
                "value": json.dumps({"candidate_id": cid, "job_id": jid}),
                "confirm": {
                    "title": {"type": "plain_text", "text": "Reject candidate?"},
                    "text": {"type": "mrkdwn", "text": f"Mark *{name}* as rejected?"},
                    "confirm": {"type": "plain_text", "text": "Yes, reject"},
                    "deny": {"type": "plain_text", "text": "Cancel"},
                },
            },
        ],
    })

    return blocks


def _rankings_blocks(rankings: list, job: dict) -> list:
    """Build Block Kit blocks for a ranked candidate list."""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📊 Rankings — {job.get('title', 'Job')} ({job.get('location', '')})"},
        },
    ]

    for i, r in enumerate(rankings[:10], 1):  # cap at 10
        rec = r.get("recommendation", "")
        style = RECOMMENDATION_STYLE.get(rec, {"emoji": "❓"})
        qual = "✅" if r.get("qualified") else "⛔"
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{i}. {r.get('candidate_name', 'Unknown')}*  {qual}  "
                    f"Score: *{r.get('total_score', 0)}*  {style['emoji']} {rec.replace('_', ' ')}"
                ),
            },
            "accessory": {
                "type": "button",
                "text": {"type": "plain_text", "text": "View"},
                "action_id": "view_profile",
                "value": json.dumps({"candidate_id": r.get("candidate_id", ""), "job_id": job.get("job_id", "")}),
            },
        })

    if not rankings:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "_No candidates found._"}})

    return blocks


def _job_posting_blocks(job: dict, pipeline_count: int = 0) -> list:
    """Build Block Kit blocks for a new job posting notification."""
    title = job.get("title", "Untitled Position")
    location = job.get("location", "—")
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")

    if salary_min and salary_max:
        salary_text = f"${salary_min:,} – ${salary_max:,}"
    elif salary_min:
        salary_text = f"From ${salary_min:,}"
    elif salary_max:
        salary_text = f"Up to ${salary_max:,}"
    else:
        salary_text = "_Not specified_"

    req_certs = job.get("required_certifications") or []
    cert_text = "  ".join(f"`{c}`" for c in req_certs) if req_certs else "_None_"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📋 New Job Synced — {title}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Location*\n{location}"},
                {"type": "mrkdwn", "text": f"*Salary Range*\n{salary_text}"},
                {"type": "mrkdwn", "text": f"*Required Certs*\n{cert_text}"},
                {"type": "mrkdwn", "text": f"*Pipeline*\n{pipeline_count} candidate{'s' if pipeline_count != 1 else ''} for similar roles"},
            ],
        },
    ]

    if job.get("description"):
        desc = job["description"][:300]
        if len(job["description"]) > 300:
            desc += "…"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Description*\n{desc}"},
        })

    shift = job.get("shift_schedule") or []
    if shift:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"🕐 Shifts: {', '.join(shift)}"}],
        })

    return blocks


def _screening_result_blocks(candidate_name: str, job_title: str, result: str,
                              score: Optional[int] = None,
                              answers: Optional[list] = None,
                              summary: Optional[str] = None) -> list:
    """Build Block Kit blocks for a screening result card."""
    badge_map = {
        "pass": ("✅", "Passed", "#2eb886"),
        "fail": ("❌", "Failed", "#cc0000"),
        "review": ("👀", "Needs Review", "#e6a817"),
    }
    emoji, label, color = badge_map.get(result, ("❓", "Unknown", "#aaaaaa"))
    score_badge = _score_badge(score) if score is not None else ""

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🎙️ Screening Complete — {candidate_name}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Result*\n{emoji} {label}"},
                {"type": "mrkdwn", "text": f"*Position*\n{job_title}"},
                {"type": "mrkdwn", "text": f"*AI Score*\n{score_badge}" if score is not None else "*AI Score*\n—"},
                {"type": "mrkdwn", "text": f"*Next Step*\n{_next_step_text(result)}"},
            ],
        },
    ]

    if summary:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Summary*\n{summary}"},
        })

    if answers:
        answer_lines = "\n".join(f"• {a}" for a in answers[:5])
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Key Answers*\n{answer_lines}"},
        })

    return blocks


def _next_step_text(result: str) -> str:
    """Return recommended next step based on screening result."""
    return {
        "pass": "Schedule in-person interview",
        "fail": "Send rejection notice",
        "review": "Manager review required",
    }.get(result, "Pending decision")


def _daily_digest_blocks(new_candidates: int = 0, pending_reviews: int = 0,
                          upcoming_screenings: int = 0,
                          top_candidates: Optional[list] = None) -> list:
    """Build Block Kit blocks for a daily digest summary."""
    today = datetime.now(timezone.utc).strftime("%A, %B %d")
    top_candidates = top_candidates or []

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📰 Daily Recruiting Digest — {today}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*New Candidates*\n{new_candidates}"},
                {"type": "mrkdwn", "text": f"*Pending Reviews*\n{pending_reviews}"},
                {"type": "mrkdwn", "text": f"*Upcoming Screenings*\n{upcoming_screenings}"},
                {"type": "mrkdwn", "text": f"*Top Scored This Week*\n{len(top_candidates)}"},
            ],
        },
    ]

    if top_candidates:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*🏆 Top Candidates This Week*"},
        })
        for c in top_candidates[:5]:
            name = c.get("name", "Unknown")
            c_score = c.get("score", 0)
            role = c.get("role", "—")
            badge = _score_badge(c_score)
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"{badge}  *{name}* — {role}"},
            })

    if not new_candidates and not pending_reviews and not upcoming_screenings and not top_candidates:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_No activity to report. Enjoy your morning! ☕_"},
        })

    return blocks


# ---------------------------------------------------------------------------
# Public notification functions
# ---------------------------------------------------------------------------

def notify_new_candidate(candidate_name: str, job_title: str, source: str,
                          candidate: Optional[dict] = None, job: Optional[dict] = None,
                          score: Optional[dict] = None):
    """Notify recruiters of a new candidate. Uses Block Kit if bot token available."""
    if SLACK_BOT_TOKEN and candidate and job:
        blocks = _candidate_blocks(candidate, job, score)
        result = _api_call("chat.postMessage", {
            "channel": SLACK_CHANNEL,
            "text": f"New applicant: {candidate_name} for {job_title}",
            "blocks": blocks,
        })
        return result.get("ok", False)
    else:
        # Fallback to webhook
        return _webhook_send({
            "text": f":new: *New Candidate*\nName: {candidate_name}\nPosition: {job_title}\nSource: {source}",
        })


def notify_screening_complete(candidate_name: str, job_title: str, result: str,
                               score: Optional[int] = None,
                               answers: Optional[list] = None,
                               summary: Optional[str] = None):
    """Notify recruiters that a screening is complete. Uses Block Kit if bot token available."""
    if SLACK_BOT_TOKEN:
        blocks = _screening_result_blocks(candidate_name, job_title, result,
                                           score, answers, summary)
        api_result = _api_call("chat.postMessage", {
            "channel": SLACK_CHANNEL,
            "text": f"Screening complete: {candidate_name} — {result.upper()}",
            "blocks": blocks,
        })
        return api_result.get("ok", False)
    else:
        # Fallback to plain text webhook
        emoji = {"pass": "white_check_mark", "fail": "x", "review": "eyes"}.get(result, "question")
        score_text = f" (Score: {score}/100)" if score is not None else ""
        return _webhook_send({
            "text": (
                f":{emoji}: *Screening Complete*\n"
                f"Candidate: {candidate_name}\nPosition: {job_title}\n"
                f"Result: {result.upper()}{score_text}"
            ),
        })


def notify_new_job(job: dict, pipeline_count: int = 0, channel: Optional[str] = None):
    """Notify recruiters of a new job synced from Indeed. Uses Block Kit if bot token available."""
    title = job.get("title", "Untitled Position")
    if SLACK_BOT_TOKEN:
        blocks = _job_posting_blocks(job, pipeline_count)
        result = _api_call("chat.postMessage", {
            "channel": channel or SLACK_CHANNEL,
            "text": f"New job synced: {title}",
            "blocks": blocks,
        })
        return result.get("ok", False)
    else:
        location = job.get("location", "")
        return _webhook_send({
            "text": f":briefcase: *New Job Synced*\nTitle: {title}\nLocation: {location}",
        })


def send_daily_digest(new_candidates: int = 0, pending_reviews: int = 0,
                       upcoming_screenings: int = 0,
                       top_candidates: Optional[list] = None,
                       channel: Optional[str] = None):
    """Send daily recruiting digest. Uses Block Kit if bot token available."""
    if SLACK_BOT_TOKEN:
        blocks = _daily_digest_blocks(new_candidates, pending_reviews,
                                       upcoming_screenings, top_candidates)
        result = _api_call("chat.postMessage", {
            "channel": channel or SLACK_CHANNEL,
            "text": "Daily Recruiting Digest",
            "blocks": blocks,
        })
        return result.get("ok", False)
    else:
        return _webhook_send({
            "text": (
                f":newspaper: *Daily Recruiting Digest*\n"
                f"New candidates: {new_candidates}\n"
                f"Pending reviews: {pending_reviews}\n"
                f"Upcoming screenings: {upcoming_screenings}"
            ),
        })


def send_notification(message: str, channel: Optional[str] = None) -> bool:
    """Send a plain text notification."""
    if SLACK_BOT_TOKEN:
        result = _api_call("chat.postMessage", {
            "channel": channel or SLACK_CHANNEL,
            "text": message,
        })
        return result.get("ok", False)
    return _webhook_send({"channel": channel or SLACK_CHANNEL, "text": message})


def post_rankings(rankings: list, job: dict, channel: Optional[str] = None) -> bool:
    """Post a ranked candidate list to Slack."""
    blocks = _rankings_blocks(rankings, job)
    result = _api_call("chat.postMessage", {
        "channel": channel or SLACK_CHANNEL,
        "text": f"Rankings for {job.get('title', 'job')}",
        "blocks": blocks,
    })
    return result.get("ok", False)


def post_ephemeral(channel: str, user: str, text: str, blocks: Optional[list] = None) -> bool:
    """Post an ephemeral message visible only to one user."""
    payload = {"channel": channel, "user": user, "text": text}
    if blocks:
        payload["blocks"] = blocks
    result = _api_call("chat.postEphemeral", payload)
    return result.get("ok", False)


def respond_to_action(response_url: str, text: str, blocks: Optional[list] = None, replace: bool = True):
    """Respond to a button click via response_url."""
    payload = {
        "text": text,
        "response_type": "in_channel",
        "replace_original": replace,
    }
    if blocks:
        payload["blocks"] = blocks
    req = Request(
        response_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        logger.error(f"Slack response_url call failed: {e}")
        return False
