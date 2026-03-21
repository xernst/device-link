"""SMS/Email outreach service using AWS SES and SNS."""

import logging
import os
from datetime import datetime, timezone

import boto3

logger = logging.getLogger(__name__)

TEMPLATES = {
    "interview_invite": {
        "subject": "Interview Invitation — {job_title}",
        "body_html": (
            "<h2>Interview Invitation</h2>"
            "<p>Dear {candidate_name},</p>"
            "<p>We are pleased to invite you to interview for the <strong>{job_title}</strong> position.</p>"
            "<p>Please reply to this email or contact us to schedule your interview.</p>"
            "<p>Best regards,<br>Recruiting Team</p>"
        ),
        "body_text": (
            "Interview Invitation\n\n"
            "Dear {candidate_name},\n\n"
            "We are pleased to invite you to interview for the {job_title} position.\n\n"
            "Please reply to this email or contact us to schedule your interview.\n\n"
            "Best regards,\nRecruiting Team"
        ),
        "sms": "Hi {candidate_name}, you're invited to interview for {job_title}. Please reply or check your email for details.",
    },
    "screening_reminder": {
        "subject": "Screening Reminder — {job_title}",
        "body_html": (
            "<h2>Screening Reminder</h2>"
            "<p>Dear {candidate_name},</p>"
            "<p>This is a friendly reminder about your screening for the <strong>{job_title}</strong> position.</p>"
            "<p>Please respond at your earliest convenience.</p>"
            "<p>Best regards,<br>Recruiting Team</p>"
        ),
        "body_text": (
            "Screening Reminder\n\n"
            "Dear {candidate_name},\n\n"
            "This is a friendly reminder about your screening for the {job_title} position.\n\n"
            "Please respond at your earliest convenience.\n\n"
            "Best regards,\nRecruiting Team"
        ),
        "sms": "Hi {candidate_name}, reminder about your screening for {job_title}. Please respond at your earliest convenience.",
    },
    "status_update": {
        "subject": "Application Update — {job_title}",
        "body_html": (
            "<h2>Application Update</h2>"
            "<p>Dear {candidate_name},</p>"
            "<p>We have an update regarding your application for the <strong>{job_title}</strong> position.</p>"
            "<p>Please check in with our recruiting team for more details.</p>"
            "<p>Best regards,<br>Recruiting Team</p>"
        ),
        "body_text": (
            "Application Update\n\n"
            "Dear {candidate_name},\n\n"
            "We have an update regarding your application for the {job_title} position.\n\n"
            "Please check in with our recruiting team for more details.\n\n"
            "Best regards,\nRecruiting Team"
        ),
        "sms": "Hi {candidate_name}, there's an update on your {job_title} application. Check your email for details.",
    },
}


def send_email(to_address: str, subject: str, body_html: str, body_text: str) -> dict:
    """Send email via SES. Uses env var OUTREACH_EMAIL_FROM as sender."""
    from_address = os.environ.get("OUTREACH_EMAIL_FROM")
    if not from_address:
        logger.warning("OUTREACH_EMAIL_FROM not set — skipping email send")
        return {"error": "OUTREACH_EMAIL_FROM not configured", "sent": False}

    try:
        region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        client = boto3.client("ses", region_name=region)
        response = client.send_email(
            Source=from_address,
            Destination={"ToAddresses": [to_address]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": body_html, "Charset": "UTF-8"},
                    "Text": {"Data": body_text, "Charset": "UTF-8"},
                },
            },
        )
        return {"sent": True, "message_id": response.get("MessageId", "")}
    except Exception as e:
        logger.error("SES send error: %s", str(e))
        return {"error": f"SES error: {str(e)}", "sent": False}


def send_sms(phone_number: str, message: str) -> dict:
    """Send SMS via SNS. Phone number must be E.164 format."""
    sms_enabled = os.environ.get("OUTREACH_SMS_ENABLED", "false").lower() == "true"
    if not sms_enabled:
        logger.warning("OUTREACH_SMS_ENABLED not true — skipping SMS send")
        return {"error": "SMS sending not enabled", "sent": False}

    try:
        region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        client = boto3.client("sns", region_name=region)
        response = client.publish(
            PhoneNumber=phone_number,
            Message=message,
        )
        return {"sent": True, "message_id": response.get("MessageId", "")}
    except Exception as e:
        logger.error("SNS send error: %s", str(e))
        return {"error": f"SNS error: {str(e)}", "sent": False}


def send_outreach(candidate: dict, job: dict, channel: str = "email", template: str = "interview_invite") -> dict:
    """High-level outreach function.

    Templates: interview_invite, screening_reminder, status_update.
    After sending, returns dict with sent status, channel, template info.
    """
    if template not in TEMPLATES:
        return {"error": f"Unknown template: {template}", "sent": False}

    tmpl = TEMPLATES[template]
    candidate_name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
    job_title = job.get("title", "Open Position")

    fmt = {"candidate_name": candidate_name, "job_title": job_title}

    if channel == "email":
        to_address = candidate.get("email")
        if not to_address:
            return {"error": "Candidate has no email address", "sent": False}

        result = send_email(
            to_address=to_address,
            subject=tmpl["subject"].format(**fmt),
            body_html=tmpl["body_html"].format(**fmt),
            body_text=tmpl["body_text"].format(**fmt),
        )
    elif channel == "sms":
        phone = candidate.get("phone")
        if not phone:
            return {"error": "Candidate has no phone number", "sent": False}

        result = send_sms(
            phone_number=phone,
            message=tmpl["sms"].format(**fmt),
        )
    else:
        return {"error": f"Unknown channel: {channel}", "sent": False}

    if result.get("sent"):
        return {
            "sent": True,
            "channel": channel,
            "template": template,
            "message_id": result.get("message_id", ""),
        }

    return result
