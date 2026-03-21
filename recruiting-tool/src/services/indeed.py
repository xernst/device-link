"""Indeed Job Sync API + Indeed Apply webhook integration.

Two distinct capabilities:
1. Job Sync API — post/update/expire Xwell job postings on Indeed
2. Indeed Apply webhook — receive and parse inbound candidate applications

Indeed API docs: https://docs.indeed.com/job-sync-api/
Auth: OAuth2 client_credentials via INDEED_CLIENT_ID + INDEED_CLIENT_SECRET
"""

import json
import os
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

INDEED_TOKEN_URL = "https://apis.indeed.com/oauth/v2/tokens"
INDEED_JOBS_API_URL = "https://apis.indeed.com/graphql"

# Role category → Indeed job type mapping
ROLE_CATEGORY_INDEED_MAP = {
    "spa": "FULL_TIME",
    "management": "FULL_TIME",
    "biosecurity": "FULL_TIME",
    "guest_services": "PART_TIME",
}


def _get_access_token() -> Optional[str]:
    """Fetch OAuth2 client_credentials token from Indeed."""
    client_id = os.environ.get("INDEED_CLIENT_ID")
    client_secret = os.environ.get("INDEED_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.warning("INDEED_CLIENT_ID or INDEED_CLIENT_SECRET not set — Indeed API disabled")
        return None

    try:
        import urllib.request
        import urllib.parse

        data = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "employer_access",
        }).encode()

        req = urllib.request.Request(
            INDEED_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            return body.get("access_token")
    except Exception as e:
        logger.error(f"Indeed OAuth token fetch failed: {e}")
        return None


def _graphql(query: str, variables: dict, token: str) -> dict:
    """Execute a GraphQL request against Indeed's API."""
    import urllib.request

    payload = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        INDEED_JOBS_API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Indeed-Locale": "en_US",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def post_job_to_indeed(job: dict) -> dict:
    """Post a job to Indeed via Job Sync API.

    Args:
        job: Job dict (from Job.to_api())

    Returns:
        {"success": True, "indeed_job_id": str} or {"success": False, "error": str}
    """
    token = _get_access_token()
    if not token:
        return {"success": False, "error": "Indeed API not configured"}

    employer_id = os.environ.get("INDEED_EMPLOYER_ID")
    if not employer_id:
        return {"success": False, "error": "INDEED_EMPLOYER_ID not set"}

    role_category = job.get("role_category") or "guest_services"
    job_type = ROLE_CATEGORY_INDEED_MAP.get(role_category, "FULL_TIME")

    # Build screener questions from required certs and shifts
    screener_questions = []
    for cert in job.get("required_certifications", []):
        screener_questions.append({
            "question": f"Do you hold a current {cert} license or certification?",
            "questionType": "BOOLEAN",
            "required": True,
            "preferredAnswer": "YES",
        })
    for shift in job.get("shift_schedule", []):
        screener_questions.append({
            "question": f"Are you available to work {shift} shifts?",
            "questionType": "BOOLEAN",
            "required": False,
            "preferredAnswer": "YES",
        })

    mutation = """
    mutation postJob($employerId: ID!, $jobPosting: JobPostingInput!) {
        jobSync(employerId: $employerId, jobPosting: $jobPosting) {
            sourcedPostingId
            status
            errors {
                field
                message
            }
        }
    }
    """

    variables = {
        "employerId": employer_id,
        "jobPosting": {
            "sourceId": job.get("job_id", ""),
            "title": job.get("title", ""),
            "description": job.get("description", "") or job.get("requirements", ""),
            "location": {
                "address": job.get("location", ""),
                "country": "US",
            },
            "jobType": job_type,
            "applyUrl": os.environ.get("INDEED_APPLY_WEBHOOK_URL", ""),
            "screenerQuestions": screener_questions,
        },
    }

    try:
        result = _graphql(mutation, variables, token)
        data = result.get("data", {}).get("jobSync", {})
        errors = data.get("errors", [])
        if errors:
            return {"success": False, "error": str(errors)}
        return {
            "success": True,
            "indeed_job_id": data.get("sourcedPostingId", ""),
            "status": data.get("status", ""),
        }
    except Exception as e:
        logger.error(f"Indeed post_job failed: {e}")
        return {"success": False, "error": str(e)}


def expire_job_on_indeed(indeed_job_id: str) -> dict:
    """Expire (close) a job on Indeed.

    Args:
        indeed_job_id: The sourcedPostingId returned when the job was posted

    Returns:
        {"success": True} or {"success": False, "error": str}
    """
    token = _get_access_token()
    if not token:
        return {"success": False, "error": "Indeed API not configured"}

    employer_id = os.environ.get("INDEED_EMPLOYER_ID")
    if not employer_id:
        return {"success": False, "error": "INDEED_EMPLOYER_ID not set"}

    mutation = """
    mutation expireJob($employerId: ID!, $sourcedPostingId: ID!) {
        expireJobPosting(employerId: $employerId, sourcedPostingId: $sourcedPostingId) {
            status
            errors { field message }
        }
    }
    """

    try:
        result = _graphql(
            mutation,
            {"employerId": employer_id, "sourcedPostingId": indeed_job_id},
            token,
        )
        data = result.get("data", {}).get("expireJobPosting", {})
        errors = data.get("errors", [])
        if errors:
            return {"success": False, "error": str(errors)}
        return {"success": True, "status": data.get("status", "")}
    except Exception as e:
        logger.error(f"Indeed expire_job failed: {e}")
        return {"success": False, "error": str(e)}


def parse_indeed_apply_webhook(payload: dict) -> dict:
    """Parse an inbound Indeed Apply webhook payload into a normalized candidate dict.

    Indeed sends application data when a candidate clicks "Apply with Indeed."
    See: https://docs.indeed.com/job-sync-api/integrate-with-job-sync-api

    Returns a dict compatible with Candidate.from_api()
    """
    applicant = payload.get("applicant", {})
    job_ref = payload.get("job", {})

    # Extract name
    name = applicant.get("name", {})
    first_name = name.get("given", "") or applicant.get("firstName", "")
    last_name = name.get("family", "") or applicant.get("lastName", "")

    # Contact info
    email = ""
    phone = ""
    for contact in applicant.get("contactInfo", []):
        if contact.get("type") == "EMAIL":
            email = contact.get("value", "")
        elif contact.get("type") == "PHONE":
            phone = contact.get("value", "")

    # Location
    location_data = applicant.get("location", {})
    location = ", ".join(filter(None, [
        location_data.get("city", ""),
        location_data.get("region", ""),
    ]))

    # Experience
    years_experience = None
    work_history = applicant.get("workExperience", [])
    if work_history:
        # Rough estimate: count total years across jobs
        total_months = 0
        for job in work_history:
            start = job.get("startDateYear")
            end = job.get("endDateYear") or datetime.now(timezone.utc).year
            if start:
                total_months += (int(end) - int(start)) * 12
        years_experience = max(1, total_months // 12) if total_months else None

    # Extract certifications from screener question answers
    certifications = []
    availability = {}
    screener_answers = payload.get("screenerAnswers", [])
    for answer in screener_answers:
        question = answer.get("question", "").lower()
        value = answer.get("answer", "")
        # Cert questions: "do you hold a current X license"
        if "license" in question or "certification" in question:
            # Extract cert name from question
            for cert_keyword in [
                "cosmetology", "esthetician", "massage_therapy", "massage therapy",
                "nail_technician", "nail technician", "color_specialist", "color specialist",
                "biosecurity", "bio-security",
            ]:
                if cert_keyword in question and str(value).upper() in ("YES", "TRUE", "1"):
                    certifications.append(cert_keyword.replace(" ", "_"))

        # Availability questions: "are you available to work X shifts"
        for shift in ["morning", "afternoon", "evening", "weekend", "overnight"]:
            if shift in question and str(value).upper() in ("YES", "TRUE", "1"):
                availability.setdefault("any", []).append(shift)

    # Resume S3 key placeholder — actual resume URL from Indeed if available
    resume_url = applicant.get("resumeUrl", "")

    notes = f"Applied via Indeed. Application ID: {payload.get('applicationId', 'unknown')}"
    if resume_url:
        notes += f"\nResume URL: {resume_url}"

    return {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "location": location,
        "source": "indeed_apply",
        "certifications": certifications,
        "availability": availability,
        "years_experience": years_experience,
        "notes": notes,
        # job_id must be resolved by handler from job.indeed_job_id → job_id lookup
        "_indeed_job_source_id": job_ref.get("sourceId", ""),
        "_indeed_application_id": payload.get("applicationId", ""),
    }
