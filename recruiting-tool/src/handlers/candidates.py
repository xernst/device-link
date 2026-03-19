"""Lambda handlers for candidate CRUD operations."""

from src.models.candidate import Candidate, CandidateStatus
from src.services import dynamodb
from src.services.slack import notify_new_candidate
from src.utils.response import success, error, parse_body


def create(event, context):
    """POST /candidates — Create a new candidate."""
    try:
        data = parse_body(event)
        if not data.get("first_name") or not data.get("last_name"):
            return error("first_name and last_name are required")

        candidate = Candidate.from_api(data)
        dynamodb.put_item(candidate.to_dynamo())

        # Notify recruiters via Slack
        job_title = data.get("job_title", "Unknown Position")
        notify_new_candidate(
            f"{candidate.first_name} {candidate.last_name}",
            job_title,
            candidate.source,
        )

        return success(candidate.to_api(), status_code=201)
    except Exception as e:
        return error(str(e), status_code=500)


def get(event, context):
    """GET /candidates/{id} — Get a candidate by ID."""
    try:
        candidate_id = event["pathParameters"]["id"]
        item = dynamodb.get_item(f"CANDIDATE#{candidate_id}", "PROFILE")
        if not item:
            return error("Candidate not found", status_code=404)
        candidate = Candidate.from_dynamo(item)
        return success(candidate.to_api())
    except Exception as e:
        return error(str(e), status_code=500)


def list_by_job(event, context):
    """GET /jobs/{id}/candidates — List candidates for a job."""
    try:
        job_id = event["pathParameters"]["id"]
        status_filter = (event.get("queryStringParameters") or {}).get("status")

        sk_prefix = f"STATUS#{status_filter}" if status_filter else "STATUS#"
        items = dynamodb.query_gsi1(f"JOB#{job_id}", sk_prefix)
        candidates = [Candidate.from_dynamo(item).to_api() for item in items]
        return success({"candidates": candidates, "count": len(candidates)})
    except Exception as e:
        return error(str(e), status_code=500)


def update_status(event, context):
    """PATCH /candidates/{id}/status — Update candidate status."""
    try:
        candidate_id = event["pathParameters"]["id"]
        data = parse_body(event)
        new_status = data.get("status")

        if not new_status:
            return error("status is required")

        # Validate status
        try:
            CandidateStatus(new_status)
        except ValueError:
            valid = [s.value for s in CandidateStatus]
            return error(f"Invalid status. Must be one of: {valid}")

        result = dynamodb.update_status(
            f"CANDIDATE#{candidate_id}", "PROFILE", new_status
        )
        return success({"candidate_id": candidate_id, "status": new_status})
    except Exception as e:
        return error(str(e), status_code=500)


def delete(event, context):
    """DELETE /candidates/{id} — Delete a candidate."""
    try:
        candidate_id = event["pathParameters"]["id"]
        dynamodb.delete_item(f"CANDIDATE#{candidate_id}", "PROFILE")
        return success({"deleted": candidate_id})
    except Exception as e:
        return error(str(e), status_code=500)
