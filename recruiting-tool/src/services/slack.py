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

def _candidate_blocks(candidate: dict, job: dict, score: Optional[dict] = None) -> list:
    """Build Slack Block Kit blocks for a candidate card."""
    rec = (score or {}).get("recommendation", "")
    style = RECOMMENDATION_STYLE.get(rec, {"emoji": "❓", "color": "#aaaaaa"})
    score_text = f"{style['emoji']} *{rec.replace('_', ' ').title()}*" if rec else ""
    total = (score or {}).get("total_score", "—")

    certs = candidate.get("certifications") or []
    cert_text = ", ".join(certs) if certs else "_none listed_"

    avail = candidate.get("availability") or {}
    all_shifts = sorted({s for shifts in avail.values() for s in (shifts if isinstance(shifts, list) else [])})
    avail_text = ", ".join(all_shifts) if all_shifts else "_not specified_"

    yrs = candidate.get("years_experience")
    yrs_text = f"{yrs} yr{'s' if yrs != 1 else ''}" if yrs else "_unknown_"

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{candidate.get('first_name', '')} {candidate.get('last_name', '')}*"
                    f"  |  {job.get('title', 'Unknown Position')}  |  {candidate.get('location', '')}\n"
                    f"📧 {candidate.get('email', '—')}  |  📞 {candidate.get('phone', '—')}\n"
                    f"Source: `{candidate.get('source', 'unknown')}`  |  Status: `{candidate.get('status', 'new')}`"
                ),
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Score*\n{total}/100  {score_text}"},
                {"type": "mrkdwn", "text": f"*Experience*\n{yrs_text}"},
                {"type": "mrkdwn", "text": f"*Certifications*\n{cert_text}"},
                {"type": "mrkdwn", "text": f"*Availability*\n{avail_text}"},
            ],
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
            "elements": [{"type": "mrkdwn", "text": f"Score breakdown: {breakdown_text}"}],
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
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "📅 Schedule Interview"},
                "style": "primary",
                "action_id": "schedule_interview",
                "value": json.dumps({"candidate_id": cid, "job_id": jid}),
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "📋 View Profile"},
                "action_id": "view_profile",
                "value": json.dumps({"candidate_id": cid, "job_id": jid}),
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "✉️ Send Outreach"},
                "action_id": "send_outreach",
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
                    "text": {"type": "mrkdwn", "text": f"Mark *{candidate.get('first_name')} {candidate.get('last_name')}* as rejected?"},
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


def notify_screening_complete(candidate_name: str, job_title: str, result: str, score: Optional[int] = None):
    """Notify recruiters that a screening is complete."""
    emoji = {"pass": "white_check_mark", "fail": "x", "review": "eyes"}.get(result, "question")
    score_text = f" (Score: {score}/100)" if score is not None else ""
    return _webhook_send({
        "text": (
            f":{emoji}: *Screening Complete*\n"
            f"Candidate: {candidate_name}\nPosition: {job_title}\n"
            f"Result: {result.upper()}{score_text}"
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
