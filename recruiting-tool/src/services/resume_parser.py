"""Resume parsing service using AWS Textract."""

import logging
import os
import re
from typing import Optional

import boto3

from src.services.scraper import extract_skills

logger = logging.getLogger(__name__)

# Known certification keywords to scan for
CERT_KEYWORDS = [
    "licensed massage therapist", "lmt", "licensed esthetician",
    "cosmetology license", "licensed cosmetologist",
    "nail technician license", "certified nail technician",
    "cpr certified", "cpr", "first aid",
    "osha", "bloodborne pathogens",
    "pmp", "aws certified", "cissp", "cpa", "cfa",
    "servsafe", "food handler",
    "certified public accountant",
    "registered nurse", "rn", "lpn",
    "board certified", "national certification",
]


def parse_resume(s3_bucket: str, s3_key: str) -> dict:
    """Use AWS Textract to extract text from a resume PDF/image stored in S3.

    Returns dict with: raw_text, certifications (list), years_experience (int|None), skills (list).
    Uses detect_document_text for simple text extraction.
    Calls extract_skills() from scraper to detect skill keywords.
    Also attempts to extract certifications by scanning for known cert keywords.
    """
    try:
        region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        client = boto3.client("textract", region_name=region)

        response = client.detect_document_text(
            Document={
                "S3Object": {
                    "Bucket": s3_bucket,
                    "Name": s3_key,
                }
            }
        )

        # Extract all LINE blocks into raw text
        lines = []
        for block in response.get("Blocks", []):
            if block["BlockType"] == "LINE":
                lines.append(block.get("Text", ""))

        raw_text = "\n".join(lines)

        # Extract skills using the existing scraper utility
        skills = extract_skills(raw_text)

        # Extract certifications by scanning for known cert keywords
        certifications = _extract_certifications(raw_text)

        # Extract years of experience
        years_experience = _extract_years_experience(raw_text)

        return {
            "raw_text": raw_text,
            "certifications": certifications,
            "years_experience": years_experience,
            "skills": skills,
        }

    except boto3.exceptions.Boto3Error as e:
        logger.error("Textract API error: %s", str(e))
        return {"error": f"Textract API error: {str(e)}", "raw_text": "", "certifications": [], "years_experience": None, "skills": []}
    except Exception as e:
        logger.error("Resume parsing error: %s", str(e))
        return {"error": f"Resume parsing error: {str(e)}", "raw_text": "", "certifications": [], "years_experience": None, "skills": []}


def _extract_certifications(text: str) -> list:
    """Scan text for known certification keywords."""
    if not text:
        return []
    text_lower = text.lower()
    found = []
    for cert in CERT_KEYWORDS:
        if cert.lower() in text_lower:
            found.append(cert)
    return sorted(set(found))


def _extract_years_experience(text: str) -> Optional[int]:
    """Extract years of experience from resume text."""
    if not text:
        return None

    # Pattern: "X+ years" or "X years"
    match = re.search(r'(\d+)\+?\s*years?\s+(?:of\s+)?experience', text, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # Pattern: "X-Y years"
    match = re.search(r'(\d+)\s*[-–]\s*(\d+)\s*years?\s+(?:of\s+)?experience', text, re.IGNORECASE)
    if match:
        return int(match.group(2))  # Take the higher end

    return None
