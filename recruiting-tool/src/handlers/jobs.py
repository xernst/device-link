"""Lambda handlers for job posting CRUD operations."""

from src.models.job import Job, JobStatus
from src.services import dynamodb
from src.utils.response import success, error, parse_body


def create(event, context):
    """POST /jobs — Create a new job posting."""
    try:
        data = parse_body(event)
        if not data.get("title"):
            return error("title is required")

        job = Job.from_api(data)
        dynamodb.put_item(job.to_dynamo())
        return success(job.to_api(), status_code=201)
    except Exception as e:
        return error(str(e), status_code=500)


def get(event, context):
    """GET /jobs/{id} — Get a job posting by ID."""
    try:
        job_id = event["pathParameters"]["id"]
        item = dynamodb.get_item(f"JOB#{job_id}", "METADATA")
        if not item:
            return error("Job not found", status_code=404)
        job = Job.from_dynamo(item)
        return success(job.to_api())
    except Exception as e:
        return error(str(e), status_code=500)


def list_all(event, context):
    """GET /jobs — List all job postings."""
    try:
        status_filter = (event.get("queryStringParameters") or {}).get("status")
        sk_prefix = f"STATUS#{status_filter}" if status_filter else "STATUS#"
        items = dynamodb.query_gsi1("JOBS", sk_prefix)
        jobs = [Job.from_dynamo(item).to_api() for item in items]
        return success({"jobs": jobs, "count": len(jobs)})
    except Exception as e:
        return error(str(e), status_code=500)


def update(event, context):
    """PUT /jobs/{id} — Update a job posting."""
    try:
        job_id = event["pathParameters"]["id"]
        data = parse_body(event)

        # Fetch existing
        item = dynamodb.get_item(f"JOB#{job_id}", "METADATA")
        if not item:
            return error("Job not found", status_code=404)

        existing = Job.from_dynamo(item)
        # Update fields
        for field in ["title", "location", "department", "description", "requirements",
                       "salary_min", "salary_max", "screening_questions"]:
            if field in data:
                setattr(existing, field, data[field])
        if "status" in data:
            existing.status = JobStatus(data["status"])

        from datetime import datetime, timezone
        existing.updated_at = datetime.now(timezone.utc).isoformat()
        dynamodb.put_item(existing.to_dynamo())
        return success(existing.to_api())
    except Exception as e:
        return error(str(e), status_code=500)


def delete(event, context):
    """DELETE /jobs/{id} — Delete a job posting."""
    try:
        job_id = event["pathParameters"]["id"]
        dynamodb.delete_item(f"JOB#{job_id}", "METADATA")
        return success({"deleted": job_id})
    except Exception as e:
        return error(str(e), status_code=500)
