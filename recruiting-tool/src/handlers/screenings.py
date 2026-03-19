"""Lambda handlers for voice screening operations."""

from src.models.screening import Screening, ScreeningStatus, ScreeningResult
from src.models.candidate import CandidateStatus
from src.services import dynamodb
from src.services.slack import notify_screening_complete
from src.utils.response import success, error, parse_body


def schedule(event, context):
    """POST /screenings — Schedule a new voice screening."""
    try:
        data = parse_body(event)
        if not data.get("candidate_id") or not data.get("job_id"):
            return error("candidate_id and job_id are required")

        screening = Screening(
            candidate_id=data["candidate_id"],
            job_id=data["job_id"],
            scheduled_at=data.get("scheduled_at"),
        )
        dynamodb.put_item(screening.to_dynamo())

        # Update candidate status
        dynamodb.update_status(
            f"CANDIDATE#{data['candidate_id']}",
            "PROFILE",
            CandidateStatus.SCREENING_SCHEDULED.value,
        )

        return success(screening.to_api(), status_code=201)
    except Exception as e:
        return error(str(e), status_code=500)


def get(event, context):
    """GET /screenings/{candidate_id}/{screening_id} — Get a screening."""
    try:
        candidate_id = event["pathParameters"]["candidate_id"]
        screening_id = event["pathParameters"]["screening_id"]
        item = dynamodb.get_item(
            f"CANDIDATE#{candidate_id}", f"SCREENING#{screening_id}"
        )
        if not item:
            return error("Screening not found", status_code=404)
        screening = Screening.from_dynamo(item)
        return success(screening.to_api())
    except Exception as e:
        return error(str(e), status_code=500)


def list_by_candidate(event, context):
    """GET /candidates/{id}/screenings — List screenings for a candidate."""
    try:
        candidate_id = event["pathParameters"]["id"]
        items = dynamodb.query_by_pk(f"CANDIDATE#{candidate_id}", "SCREENING#")
        screenings = [Screening.from_dynamo(item).to_api() for item in items]
        return success({"screenings": screenings, "count": len(screenings)})
    except Exception as e:
        return error(str(e), status_code=500)


def complete(event, context):
    """POST /screenings/{candidate_id}/{screening_id}/complete — Record screening results."""
    try:
        candidate_id = event["pathParameters"]["candidate_id"]
        screening_id = event["pathParameters"]["screening_id"]
        data = parse_body(event)

        item = dynamodb.get_item(
            f"CANDIDATE#{candidate_id}", f"SCREENING#{screening_id}"
        )
        if not item:
            return error("Screening not found", status_code=404)

        screening = Screening.from_dynamo(item)
        screening.status = ScreeningStatus.COMPLETED
        screening.ended_at = data.get("ended_at")
        screening.duration_seconds = data.get("duration_seconds")
        screening.transcript = data.get("transcript")
        screening.ai_summary = data.get("ai_summary")
        screening.ai_score = data.get("ai_score")
        screening.questions_asked = data.get("questions_asked", [])
        screening.responses = data.get("responses", [])

        if data.get("result"):
            screening.result = ScreeningResult(data["result"])

        from datetime import datetime, timezone
        screening.updated_at = datetime.now(timezone.utc).isoformat()
        dynamodb.put_item(screening.to_dynamo())

        # Update candidate status
        new_candidate_status = CandidateStatus.SCREENING_COMPLETE.value
        if screening.result == ScreeningResult.PASS:
            new_candidate_status = CandidateStatus.PASSED.value
        elif screening.result == ScreeningResult.FAIL:
            new_candidate_status = CandidateStatus.REJECTED.value

        dynamodb.update_status(
            f"CANDIDATE#{candidate_id}", "PROFILE", new_candidate_status
        )

        # Notify recruiters
        candidate_item = dynamodb.get_item(f"CANDIDATE#{candidate_id}", "PROFILE")
        if candidate_item:
            name = f"{candidate_item['first_name']['S']} {candidate_item['last_name']['S']}"
            job_item = dynamodb.get_item(f"JOB#{screening.job_id}", "METADATA")
            job_title = job_item["title"]["S"] if job_item else "Unknown"
            notify_screening_complete(
                name, job_title,
                screening.result.value if screening.result else "review",
                screening.ai_score,
            )

        return success(screening.to_api())
    except Exception as e:
        return error(str(e), status_code=500)
