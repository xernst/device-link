"""Calendar integration service — Google Calendar via OAuth2 + iCal fallback."""

import base64
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def create_interview_event(
    candidate: dict,
    job: dict,
    interviewer_email: str,
    start_iso: str,
    duration_minutes: int = 30,
    location: str = "",
    notes: str = "",
) -> dict:
    """Create Google Calendar event via API, invite candidate + interviewer.

    Fallback: Generate iCal (.ics) file content if Google API unavailable.
    Returns: {"event_id": str, "ics_content": str, "calendar_link": str|None}
    """
    ics_content = generate_ics(candidate, job, interviewer_email, start_iso, duration_minutes, location, notes)
    event_id = str(uuid.uuid4())

    # Try Google Calendar API first
    calendar_link = None
    google_event_id = None

    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID")
    service_account_json_b64 = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

    if calendar_id and service_account_json_b64:
        try:
            google_result = _create_google_event(
                calendar_id=calendar_id,
                service_account_json_b64=service_account_json_b64,
                candidate=candidate,
                job=job,
                interviewer_email=interviewer_email,
                start_iso=start_iso,
                duration_minutes=duration_minutes,
                location=location,
                notes=notes,
            )
            if google_result.get("event_id"):
                google_event_id = google_result["event_id"]
                calendar_link = google_result.get("calendar_link")
                event_id = google_event_id
        except Exception as e:
            logger.warning("Google Calendar API unavailable, falling back to iCal: %s", str(e))
    else:
        logger.warning("Google Calendar env vars not set — using iCal fallback only")

    return {
        "event_id": event_id,
        "ics_content": ics_content,
        "calendar_link": calendar_link,
    }


def generate_ics(candidate, job, interviewer_email, start_iso, duration_minutes, location, notes) -> str:
    """Pure iCal generation — no external dependency. Always available as fallback."""
    candidate_name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
    candidate_email = candidate.get("email", "")
    job_title = job.get("title", "Interview")

    # Parse start time
    start_dt = datetime.fromisoformat(start_iso)
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    # Format for iCal (UTC)
    if start_dt.tzinfo is not None:
        start_utc = start_dt.astimezone(timezone.utc)
        end_utc = end_dt.astimezone(timezone.utc)
    else:
        start_utc = start_dt
        end_utc = end_dt

    dt_format = "%Y%m%dT%H%M%SZ"
    uid = str(uuid.uuid4())
    now_stamp = datetime.now(timezone.utc).strftime(dt_format)

    summary = f"Interview: {candidate_name} — {job_title}"
    description = notes or f"Interview for {job_title} position"

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//RecruitingTool//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:REQUEST",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now_stamp}",
        f"DTSTART:{start_utc.strftime(dt_format)}",
        f"DTEND:{end_utc.strftime(dt_format)}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
    ]
    if location:
        lines.append(f"LOCATION:{location}")
    if interviewer_email:
        lines.append(f"ORGANIZER;CN=Interviewer:mailto:{interviewer_email}")
    if candidate_email:
        lines.append(f"ATTENDEE;CN={candidate_name};RSVP=TRUE:mailto:{candidate_email}")
    if interviewer_email:
        lines.append(f"ATTENDEE;CN=Interviewer;RSVP=TRUE:mailto:{interviewer_email}")

    lines.extend([
        "STATUS:CONFIRMED",
        "END:VEVENT",
        "END:VCALENDAR",
    ])

    return "\r\n".join(lines)


def _create_google_event(
    calendar_id, service_account_json_b64, candidate, job,
    interviewer_email, start_iso, duration_minutes, location, notes,
) -> dict:
    """Create event via Google Calendar API using service account credentials."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        logger.warning("Google API client libraries not installed")
        return {"error": "Google API client not installed"}

    # Decode service account JSON from base64
    sa_json = json.loads(base64.b64decode(service_account_json_b64))
    credentials = service_account.Credentials.from_service_account_info(
        sa_json, scopes=["https://www.googleapis.com/auth/calendar"]
    )

    service = build("calendar", "v3", credentials=credentials)

    candidate_name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
    candidate_email = candidate.get("email", "")
    job_title = job.get("title", "Interview")

    start_dt = datetime.fromisoformat(start_iso)
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    event_body = {
        "summary": f"Interview: {candidate_name} — {job_title}",
        "description": notes or f"Interview for {job_title} position",
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
        "attendees": [],
    }
    if location:
        event_body["location"] = location
    if candidate_email:
        event_body["attendees"].append({"email": candidate_email})
    if interviewer_email:
        event_body["attendees"].append({"email": interviewer_email})

    result = service.events().insert(
        calendarId=calendar_id, body=event_body, sendUpdates="all"
    ).execute()

    return {
        "event_id": result.get("id", ""),
        "calendar_link": result.get("htmlLink"),
    }
