"""Lambda handlers for candidate filtering and matching."""

from src.models.candidate import Candidate
from src.models.job import Job
from src.services import dynamodb
from src.services.filtering import filter_candidates, match_jobs_to_candidate, score_candidate, generate_prescreen_questions
from src.utils.response import success, error, parse_body


def rank_candidates(event, context):
    """GET /jobs/{id}/candidates/rank — Rank candidates for a job by fit score.

    Query params:
        min_score: Minimum score to include (default: 0)
    """
    try:
        job_id = event["pathParameters"]["id"]

        # Fetch the job
        job_item = dynamodb.get_item(f"JOB#{job_id}", "METADATA")
        if not job_item:
            return error("Job not found", status_code=404)
        job = Job.from_dynamo(job_item).to_api()

        # Fetch all candidates for this job
        candidate_items = dynamodb.query_gsi1(f"JOB#{job_id}", "STATUS#")
        candidates = [Candidate.from_dynamo(item).to_api() for item in candidate_items]

        if not candidates:
            return success({"rankings": [], "count": 0, "job_id": job_id})

        # Get min_score from query params
        params = event.get("queryStringParameters") or {}
        min_score = int(params.get("min_score", "0"))

        rankings = filter_candidates(candidates, job, min_score=min_score)

        return success({
            "rankings": rankings,
            "count": len(rankings),
            "job_id": job_id,
            "job_title": job.get("title", ""),
        })
    except Exception as e:
        return error(str(e), status_code=500)


def match_candidate(event, context):
    """GET /candidates/{id}/match — Find best matching open jobs for a candidate.

    Query params:
        min_score: Minimum score to include (default: 0)
    """
    try:
        candidate_id = event["pathParameters"]["id"]

        # Fetch the candidate
        candidate_item = dynamodb.get_item(f"CANDIDATE#{candidate_id}", "PROFILE")
        if not candidate_item:
            return error("Candidate not found", status_code=404)
        candidate = Candidate.from_dynamo(candidate_item).to_api()

        # Fetch all open jobs
        job_items = dynamodb.query_gsi1("JOBS", "STATUS#open")
        jobs = [Job.from_dynamo(item).to_api() for item in job_items]

        if not jobs:
            return success({"matches": [], "count": 0, "candidate_id": candidate_id})

        params = event.get("queryStringParameters") or {}
        min_score = int(params.get("min_score", "0"))

        matches = match_jobs_to_candidate(candidate, jobs, min_score=min_score)

        return success({
            "matches": matches,
            "count": len(matches),
            "candidate_id": candidate_id,
            "candidate_name": f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip(),
        })
    except Exception as e:
        return error(str(e), status_code=500)


def score(event, context):
    """POST /candidates/score — Score a candidate against a specific job.

    Request body:
        candidate_id (required): Candidate ID
        job_id (required): Job ID
    """
    try:
        data = parse_body(event)
        candidate_id = data.get("candidate_id")
        job_id = data.get("job_id")

        if not candidate_id or not job_id:
            return error("candidate_id and job_id are required")

        candidate_item = dynamodb.get_item(f"CANDIDATE#{candidate_id}", "PROFILE")
        if not candidate_item:
            return error("Candidate not found", status_code=404)

        job_item = dynamodb.get_item(f"JOB#{job_id}", "METADATA")
        if not job_item:
            return error("Job not found", status_code=404)

        candidate = Candidate.from_dynamo(candidate_item).to_api()
        job = Job.from_dynamo(job_item).to_api()

        result = score_candidate(candidate, job)
        result["candidate_id"] = candidate_id
        result["job_id"] = job_id

        return success(result)
    except Exception as e:
        return error(str(e), status_code=500)


def prescreen_questions(event, context):
    """GET /jobs/{id}/prescreen-questions — Auto-generate pre-screen questions for a job."""
    try:
        job_id = event["pathParameters"]["id"]
        job_item = dynamodb.get_item(f"JOB#{job_id}", "METADATA")
        if not job_item:
            return error("Job not found", status_code=404)
        job = Job.from_dynamo(job_item).to_api()
        questions = generate_prescreen_questions(job)
        return success({
            "job_id": job_id,
            "job_title": job.get("title", ""),
            "questions": questions,
            "count": len(questions),
        })
    except Exception as e:
        return error(str(e), status_code=500)
