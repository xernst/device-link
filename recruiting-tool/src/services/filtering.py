"""Candidate filtering and matching service.

Scores candidates against job requirements using keyword overlap, location,
and salary fit. No ML — just practical, deterministic matching.
"""

import re
from typing import Optional

from src.services.scraper import extract_skills


def score_candidate(candidate: dict, job: dict) -> dict:
    """Score a candidate against a job posting.

    Returns a dict with:
      - total_score (0-100)
      - breakdown: {skills, location, experience}
      - matched_skills: list of matched skill keywords
      - missing_skills: list of required skills the candidate lacks
    """
    skills_result = _score_skills(candidate, job)
    location_score = _score_location(candidate, job)
    experience_score = _score_experience(candidate, job)

    # Weighted: skills 60%, location 20%, experience 20%
    total = int(
        skills_result["score"] * 0.6
        + location_score * 0.2
        + experience_score * 0.2
    )

    return {
        "total_score": min(total, 100),
        "breakdown": {
            "skills": skills_result["score"],
            "location": location_score,
            "experience": experience_score,
        },
        "matched_skills": skills_result["matched"],
        "missing_skills": skills_result["missing"],
    }


def filter_candidates(candidates: list, job: dict, min_score: int = 0) -> list:
    """Score and rank candidates for a job. Returns sorted by score descending.

    Args:
        candidates: list of candidate dicts (from API format)
        job: job dict (from API format)
        min_score: minimum total_score to include (0 = return all)
    """
    results = []
    for candidate in candidates:
        result = score_candidate(candidate, job)
        result["candidate_id"] = candidate.get("candidate_id", "")
        result["candidate_name"] = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
        if result["total_score"] >= min_score:
            results.append(result)

    results.sort(key=lambda r: r["total_score"], reverse=True)
    return results


def match_jobs_to_candidate(candidate: dict, jobs: list, min_score: int = 0) -> list:
    """Find the best matching jobs for a candidate. Returns sorted by score descending."""
    results = []
    for job in jobs:
        result = score_candidate(candidate, job)
        result["job_id"] = job.get("job_id", "")
        result["job_title"] = job.get("title", "")
        if result["total_score"] >= min_score:
            results.append(result)

    results.sort(key=lambda r: r["total_score"], reverse=True)
    return results


def _score_skills(candidate: dict, job: dict) -> dict:
    """Score skill overlap between candidate and job. Returns 0-100."""
    # Extract skills from job requirements + description
    job_text = f"{job.get('requirements', '')} {job.get('description', '')}"
    job_skills = set(extract_skills(job_text))

    if not job_skills:
        return {"score": 50, "matched": [], "missing": []}

    # Extract skills from candidate notes + source info
    candidate_text = f"{candidate.get('notes', '')} {candidate.get('resume_text', '')}"
    candidate_skills = set(extract_skills(candidate_text))

    matched = sorted(job_skills & candidate_skills)
    missing = sorted(job_skills - candidate_skills)

    score = int((len(matched) / len(job_skills)) * 100) if job_skills else 50
    return {"score": score, "matched": matched, "missing": missing}


def _score_location(candidate: dict, job: dict) -> int:
    """Score location match. Returns 0-100."""
    candidate_loc = (candidate.get("location") or "").lower().strip()
    job_loc = (job.get("location") or "").lower().strip()

    if not candidate_loc or not job_loc:
        return 50  # Unknown — neutral score

    if candidate_loc == job_loc:
        return 100

    # Check city or state overlap
    candidate_parts = set(_split_location(candidate_loc))
    job_parts = set(_split_location(job_loc))

    if candidate_parts & job_parts:
        return 75

    # Check for "remote" in either
    if "remote" in candidate_loc or "remote" in job_loc:
        return 70

    return 20


def _score_experience(candidate: dict, job: dict) -> int:
    """Score experience level match based on text signals. Returns 0-100."""
    candidate_text = f"{candidate.get('notes', '')} {candidate.get('resume_text', '')}".lower()
    job_text = f"{job.get('requirements', '')} {job.get('description', '')}".lower()

    if not candidate_text.strip() or not job_text.strip():
        return 50  # Unknown — neutral

    # Extract years of experience mentioned
    candidate_years = _extract_years(candidate_text)
    job_years = _extract_years(job_text)

    if candidate_years is not None and job_years is not None:
        if candidate_years >= job_years:
            return 100
        elif candidate_years >= job_years * 0.7:
            return 70
        else:
            return 30

    # Seniority keyword matching
    seniority_levels = ["intern", "junior", "mid", "senior", "lead", "principal", "director", "vp"]
    candidate_level = _detect_seniority(candidate_text, seniority_levels)
    job_level = _detect_seniority(job_text, seniority_levels)

    if candidate_level is not None and job_level is not None:
        diff = candidate_level - job_level
        if diff >= 0:
            return 100
        elif diff == -1:
            return 60
        else:
            return 25

    return 50


def _split_location(loc: str) -> list:
    """Split a location string into parts for comparison."""
    return [p.strip() for p in re.split(r'[,/]', loc) if p.strip()]


def _extract_years(text: str) -> Optional[int]:
    """Extract years of experience from text like '5+ years' or '3-5 years'."""
    patterns = [
        r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)',
        r'(\d+)\s*-\s*\d+\s*(?:years?|yrs?)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def _detect_seniority(text: str, levels: list) -> Optional[int]:
    """Detect seniority level from text. Returns index in levels list."""
    for i, level in reversed(list(enumerate(levels))):
        if re.search(r'\b' + level + r'\b', text):
            return i
    return None
