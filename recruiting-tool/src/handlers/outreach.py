"""Lambda handlers for candidate outreach (email/SMS)."""

from datetime import datetime, timezone

from src.models.candidate import Candidate, ResponseStatus
from src.models.job import Job
from src.services import dynamodb
from src.services.outreach import send_outreach
from src.utils.response import success, error, parse_body


def send(event, context):
    """POST /candidates/{id}/outreach — Send outreach to a candidate."""
    try:
        candidate_id = event["pathParameters"]["id"]
        data = parse_body(event)

        job_id = data.get("job_id")
        channel = data.get("channel", "email")
        template = data.get("template", "interview_invite")

        if not job_id:
            return error("job_id is required")

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

        # Send outreach
        result = send_outreach(candidate.to_api(), job.to_api(), channel=channel, template=template)

        if result.get("sent"):
            # Update candidate tracking
            candidate.response_status = ResponseStatus.AWAITING_RESPONSE
            candidate.last_contacted = datetime.now(timezone.utc).isoformat()
            candidate.updated_at = datetime.now(timezone.utc).isoformat()
            dynamodb.put_item(candidate.to_dynamo())

        return success(result)
    except Exception as e:
        return error(str(e), status_code=500)


def send_bulk(event, context):
    """POST /jobs/{id}/outreach-bulk — Send outreach to all matching candidates for a job."""
    try:
        job_id = event["pathParameters"]["id"]
        data = parse_body(event)

        channel = data.get("channel", "email")
        template = data.get("template", "interview_invite")
        response_status_filter = data.get("response_status_filter")

        # Fetch job
        job_item = dynamodb.get_item(f"JOB#{job_id}", "METADATA")
        if not job_item:
            return error("Job not found", status_code=404)
        job = Job.from_dynamo(job_item)

        # Fetch all candidates for this job
        items = dynamodb.query_gsi1(f"JOB#{job_id}", "STATUS#")
        candidates = [Candidate.from_dynamo(item) for item in items]

        # Apply response_status filter if provided
        if response_status_filter:
            candidates = [c for c in candidates if c.response_status.value == response_status_filter]

        sent_count = 0
        failed_count = 0
        results = []

        for candidate in candidates:
            result = send_outreach(candidate.to_api(), job.to_api(), channel=channel, template=template)
            if result.get("sent"):
                sent_count += 1
                # Update candidate tracking
                candidate.response_status = ResponseStatus.AWAITING_RESPONSE
                candidate.last_contacted = datetime.now(timezone.utc).isoformat()
                candidate.updated_at = datetime.now(timezone.utc).isoformat()
                dynamodb.put_item(candidate.to_dynamo())
                results.append({"candidate_id": candidate.candidate_id, "sent": True})
            else:
                failed_count += 1
                results.append({"candidate_id": candidate.candidate_id, "sent": False, "error": result.get("error", "")})

        return success({
            "job_id": job_id,
            "total_candidates": len(candidates),
            "sent": sent_count,
            "failed": failed_count,
            "results": results,
        })
    except Exception as e:
        return error(str(e), status_code=500)
