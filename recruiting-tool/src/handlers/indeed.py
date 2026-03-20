"""Lambda handlers for Indeed Job Sync API and Indeed Apply webhook."""

from src.models.candidate import Candidate
from src.models.job import Job
from src.services import dynamodb
from src.services.indeed import post_job_to_indeed, expire_job_on_indeed, parse_indeed_apply_webhook
from src.services.filtering import score_candidate, generate_prescreen_questions
from src.services.slack import notify_new_candidate
from src.utils.response import success, error, parse_body


def publish_job(event, context):
    """POST /jobs/{id}/publish — Post a job to Indeed via Job Sync API.

    Updates the job record with indeed_job_id on success.
    """
    try:
        job_id = event["pathParameters"]["id"]
        item = dynamodb.get_item(f"JOB#{job_id}", "METADATA")
        if not item:
            return error("Job not found", status_code=404)

        job = Job.from_dynamo(item)
        job_dict = job.to_api()

        result = post_job_to_indeed(job_dict)

        if result["success"]:
            # Store indeed_job_id on the job record
            dynamodb.update_attribute(
                f"JOB#{job_id}", "METADATA",
                "indeed_job_id", result.get("indeed_job_id", "")
            )

        return success({
            "job_id": job_id,
            "indeed_result": result,
        })
    except Exception as e:
        return error(str(e), status_code=500)


def unpublish_job(event, context):
    """POST /jobs/{id}/unpublish — Expire a job on Indeed."""
    try:
        job_id = event["pathParameters"]["id"]
        item = dynamodb.get_item(f"JOB#{job_id}", "METADATA")
        if not item:
            return error("Job not found", status_code=404)

        indeed_job_id = item.get("indeed_job_id", {}).get("S", "")
        if not indeed_job_id:
            return error("Job has no indeed_job_id — was it published to Indeed?", status_code=400)

        result = expire_job_on_indeed(indeed_job_id)
        return success({"job_id": job_id, "indeed_result": result})
    except Exception as e:
        return error(str(e), status_code=500)


def apply_webhook(event, context):
    """POST /indeed/apply — Inbound Indeed Apply webhook.

    Indeed POSTs application data here when a candidate applies via Indeed Apply.
    Creates a candidate record, runs scoring, notifies Slack.

    Security: validate X-Indeed-Signature header against INDEED_WEBHOOK_SECRET.
    """
    try:
        import hmac
        import hashlib
        import os

        # Signature validation
        webhook_secret = os.environ.get("INDEED_WEBHOOK_SECRET", "")
        if webhook_secret:
            sig_header = (event.get("headers") or {}).get("X-Indeed-Signature", "")
            raw_body = event.get("body", "") or ""
            expected = hmac.new(
                webhook_secret.encode(),
                raw_body.encode(),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(f"sha256={expected}", sig_header):
                return error("Invalid webhook signature", status_code=401)

        payload = parse_body(event)
        candidate_data = parse_indeed_apply_webhook(payload)

        # Resolve job_id from indeed source_id
        indeed_source_id = candidate_data.pop("_indeed_job_source_id", "")
        indeed_application_id = candidate_data.pop("_indeed_application_id", "")
        job_id = _resolve_job_id(indeed_source_id)
        if job_id:
            candidate_data["job_id"] = job_id

        # Create candidate
        candidate = Candidate.from_api(candidate_data)
        dynamodb.put_item(candidate.to_dynamo())

        # Auto-score if we have a job
        score_result = None
        if job_id:
            job_item = dynamodb.get_item(f"JOB#{job_id}", "METADATA")
            if job_item:
                job = Job.from_dynamo(job_item).to_api()
                score_result = score_candidate(candidate.to_api(), job)

        # Notify Slack
        job_title = "Unknown Position"
        if job_id:
            job_item = dynamodb.get_item(f"JOB#{job_id}", "METADATA")
            if job_item:
                job_title = job_item.get("title", {}).get("S", "Unknown Position")

        notify_new_candidate(
            f"{candidate.first_name} {candidate.last_name}",
            job_title,
            "indeed_apply",
        )

        return success({
            "candidate_id": candidate.candidate_id,
            "application_id": indeed_application_id,
            "score": score_result,
        }, status_code=201)
    except Exception as e:
        return error(str(e), status_code=500)


def _resolve_job_id(indeed_source_id: str) -> str:
    """Look up our internal job_id from the Indeed source_id (which is our job_id)."""
    if not indeed_source_id:
        return ""
    # We set sourceId = job_id when posting, so they match directly
    item = dynamodb.get_item(f"JOB#{indeed_source_id}", "METADATA")
    return indeed_source_id if item else ""
