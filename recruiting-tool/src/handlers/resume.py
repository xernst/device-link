"""Lambda handler for resume parsing."""

import os

from src.models.candidate import Candidate
from src.services import dynamodb
from src.services.resume_parser import parse_resume
from src.utils.response import success, error


def parse(event, context):
    """POST /candidates/{id}/parse-resume — Parse a candidate's resume via Textract."""
    try:
        candidate_id = event["pathParameters"]["id"]

        # Fetch candidate
        item = dynamodb.get_item(f"CANDIDATE#{candidate_id}", "PROFILE")
        if not item:
            return error("Candidate not found", status_code=404)

        candidate = Candidate.from_dynamo(item)

        if not candidate.resume_s3_key:
            return error("Candidate has no resume uploaded (resume_s3_key is empty)")

        s3_bucket = os.environ.get("ASSETS_BUCKET", "")
        if not s3_bucket:
            return error("ASSETS_BUCKET not configured", status_code=500)

        # Parse resume
        result = parse_resume(s3_bucket, candidate.resume_s3_key)

        if result.get("error"):
            return error(result["error"], status_code=500)

        # Update candidate with extracted data
        if result.get("certifications"):
            # Merge with existing certifications (no duplicates)
            existing = set(candidate.certifications)
            existing.update(result["certifications"])
            candidate.certifications = sorted(existing)

        if result.get("years_experience") is not None:
            candidate.years_experience = result["years_experience"]

        # Append extraction notes
        extracted_info = []
        if result.get("skills"):
            extracted_info.append(f"Skills detected: {', '.join(result['skills'])}")
        if result.get("certifications"):
            extracted_info.append(f"Certs detected: {', '.join(result['certifications'])}")
        if result.get("years_experience") is not None:
            extracted_info.append(f"Experience: {result['years_experience']} years")

        if extracted_info:
            note = "[Resume Parse] " + "; ".join(extracted_info)
            if candidate.notes:
                candidate.notes = candidate.notes + "\n" + note
            else:
                candidate.notes = note

        from datetime import datetime, timezone
        candidate.updated_at = datetime.now(timezone.utc).isoformat()
        dynamodb.put_item(candidate.to_dynamo())

        return success({
            "candidate": candidate.to_api(),
            "extracted": {
                "certifications": result.get("certifications", []),
                "years_experience": result.get("years_experience"),
                "skills": result.get("skills", []),
            },
        })
    except Exception as e:
        return error(str(e), status_code=500)
