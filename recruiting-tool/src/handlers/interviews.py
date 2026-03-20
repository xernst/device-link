"""Lambda handler for scheduling interviews."""

import os
from datetime import datetime, timezone

from src.models.candidate import Candidate, CandidateStatus
from src.models.job import Job
from src.services import dynamodb
from src.services.calendar import create_interview_event
from src.services.outreach import send_email
from src.utils.response import success, error, parse_body


def schedule(event, context):
    """POST /interviews — Schedule an interview."""
    try:
        data = parse_body(event)

        candidate_id = data.get("candidate_id")
        job_id = data.get("job_id")
        interviewer_email = data.get("interviewer_email")
        start_time = data.get("start_time")

        if not candidate_id or not job_id or not interviewer_email or not start_time:
            return error("candidate_id, job_id, interviewer_email, and start_time are required")

        duration_minutes = data.get("duration_minutes", 30)
        location = data.get("location", "")
        notes = data.get("notes", "")

        # Fetch candidate
        item = dynamodb.get_item(f"CANDIDATE#{candidate_id}", "PROFILE")
        if not item:
            return error("Candidate not found", status_code=404)
        candidate = Candidate.from_dynamo(item)

        # Fetch job
        job_item = dynamodb.get_item(f"JOB#{job_id}", "METADATA")
        if not job_item:
            return error("Job not found", status_code=404)
        job = Job.from_dynamo(job_item)

        # Create calendar event
        event_result = create_interview_event(
            candidate=candidate.to_api(),
            job=job.to_api(),
            interviewer_email=interviewer_email,
            start_iso=start_time,
            duration_minutes=duration_minutes,
            location=location,
            notes=notes,
        )

        # Update candidate status to screening_scheduled
        candidate.status = CandidateStatus.SCREENING_SCHEDULED
        candidate.updated_at = datetime.now(timezone.utc).isoformat()
        dynamodb.put_item(candidate.to_dynamo())

        # Send confirmation email if outreach is configured
        from_email = os.environ.get("OUTREACH_EMAIL_FROM")
        if from_email and candidate.email:
            candidate_name = f"{candidate.first_name} {candidate.last_name}"
            job_title = job.title
            send_email(
                to_address=candidate.email,
                subject=f"Interview Scheduled — {job_title}",
                body_html=(
                    f"<h2>Interview Confirmed</h2>"
                    f"<p>Dear {candidate_name},</p>"
                    f"<p>Your interview for <strong>{job_title}</strong> has been scheduled for {start_time}.</p>"
                    f"<p>Duration: {duration_minutes} minutes</p>"
                    f"{'<p>Location: ' + location + '</p>' if location else ''}"
                    f"<p>Best regards,<br>Recruiting Team</p>"
                ),
                body_text=(
                    f"Interview Confirmed\n\n"
                    f"Dear {candidate_name},\n\n"
                    f"Your interview for {job_title} has been scheduled for {start_time}.\n"
                    f"Duration: {duration_minutes} minutes\n"
                    f"{'Location: ' + location + chr(10) if location else ''}\n"
                    f"Best regards,\nRecruiting Team"
                ),
            )

        return success({
            "interview": {
                "candidate_id": candidate_id,
                "job_id": job_id,
                "interviewer_email": interviewer_email,
                "start_time": start_time,
                "duration_minutes": duration_minutes,
                "location": location,
                "notes": notes,
            },
            "event_id": event_result.get("event_id"),
            "ics_content": event_result.get("ics_content"),
            "calendar_link": event_result.get("calendar_link"),
            "candidate_status": CandidateStatus.SCREENING_SCHEDULED.value,
        }, status_code=201)
    except Exception as e:
        return error(str(e), status_code=500)
