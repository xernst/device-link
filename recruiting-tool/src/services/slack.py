"""Slack notification service for recruiter updates."""

import json
import os
from typing import Optional
from urllib.request import Request, urlopen


SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#recruiting")


def send_notification(message: str, channel: Optional[str] = None) -> bool:
    """Send a notification to Slack via webhook."""
    if not SLACK_WEBHOOK_URL:
        print("SLACK_WEBHOOK_URL not configured, skipping notification")
        return False

    payload = {
        "channel": channel or SLACK_CHANNEL,
        "text": message,
    }

    req = Request(
        SLACK_WEBHOOK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req) as response:
            return response.status == 200
    except Exception as e:
        print(f"Failed to send Slack notification: {e}")
        return False


def notify_screening_complete(candidate_name: str, job_title: str, result: str, score: Optional[int] = None):
    """Notify recruiters that a screening is complete."""
    emoji = {"pass": "white_check_mark", "fail": "x", "review": "eyes"}.get(result, "question")
    score_text = f" (Score: {score}/100)" if score is not None else ""
    message = (
        f":{emoji}: *Screening Complete*\n"
        f"Candidate: {candidate_name}\n"
        f"Position: {job_title}\n"
        f"Result: {result.upper()}{score_text}"
    )
    return send_notification(message)


def notify_new_candidate(candidate_name: str, job_title: str, source: str):
    """Notify recruiters of a new candidate."""
    message = (
        f":new: *New Candidate*\n"
        f"Name: {candidate_name}\n"
        f"Position: {job_title}\n"
        f"Source: {source}"
    )
    return send_notification(message)
