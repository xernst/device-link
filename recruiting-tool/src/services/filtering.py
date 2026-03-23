"""Candidate filtering and matching service.

Scores candidates against job requirements using certifications, availability,
location, and experience. Role-specific weights and hard certification gating.
"""

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Role profiles
# ---------------------------------------------------------------------------

ROLE_PROFILES = {
    "spa": {
        "weights": {
            "certifications": 0.40,
            "availability": 0.25,
            "experience": 0.20,
            "location": 0.15,
        },
        "cert_required": True,
    },
    "management": {
        "weights": {
            "certifications": 0.15,
            "availability": 0.25,
            "experience": 0.40,
            "location": 0.20,
        },
        "cert_required": False,
    },
    "biosecurity": {
        "weights": {
            "certifications": 0.25,
            "availability": 0.35,
            "experience": 0.20,
            "location": 0.20,
        },
        "cert_required": True,
    },
    "guest_services": {
        "weights": {
            "certifications": 0.15,
            "availability": 0.35,
            "experience": 0.25,
            "location": 0.25,
        },
        "cert_required": False,
    },
}

# Default profile when role_category is not set
_DEFAULT_PROFILE = {
    "weights": {
        "certifications": 0.30,
        "availability": 0.20,
        "experience": 0.30,
        "location": 0.20,
    },
    "cert_required": False,
}

# ---------------------------------------------------------------------------
# Positions → role category mapping
# ---------------------------------------------------------------------------

POSITION_CATEGORY_MAP = {
    "massage therapist": "spa",
    "nail technician": "spa",
    "nail tech": "spa",
    "esthetician": "spa",
    "spa manager": "management",
    "station manager": "management",
    "assistant station manager": "management",
    "experience coordinator": "management",
    "senior experience coordinator": "management",
    "bio-security specialist": "biosecurity",
    "biosecurity specialist": "biosecurity",
    "guest service associate": "guest_services",
    "guest services associate": "guest_services",
}


def _get_profile(job: dict) -> dict:
    """Return the role profile for a job."""
    role_category = job.get("role_category")
    if role_category and role_category in ROLE_PROFILES:
        return ROLE_PROFILES[role_category]
    # Try to infer from title
    title = (job.get("title") or "").lower().strip()
    for position, category in POSITION_CATEGORY_MAP.items():
        if position in title:
            return ROLE_PROFILES[category]
    return _DEFAULT_PROFILE


# ---------------------------------------------------------------------------
# Main scoring entry point
# ---------------------------------------------------------------------------

def score_candidate(candidate: dict, job: dict) -> dict:
    """Score a candidate against a job posting.

    Returns a dict with:
      - total_score (0-100)
      - qualified (bool) — False if missing a hard-required cert
      - disqualification_reasons (list)
      - recommendation ("suggest_interview" | "flag_review" | "needs_info" | "disqualified")
      - recommendation_reason (str)
      - breakdown: {certifications, availability, experience, location}
      - matched_certifications, missing_certifications
      - availability_overlap, availability_gaps
    """
    profile = _get_profile(job)
    weights = profile["weights"]
    cert_required = profile["cert_required"]

    cert_result = _score_certifications(candidate, job)
    avail_result = _score_availability(candidate, job)
    experience_score = _score_experience(candidate, job)
    location_score = _score_location(candidate, job)

    # Hard disqualification check
    disqualification_reasons = []
    if cert_required and cert_result["missing_required"]:
        for c in cert_result["missing_required"]:
            disqualification_reasons.append(f"Missing required certification: {c}")

    qualified = len(disqualification_reasons) == 0

    if not qualified:
        total = 0
        recommendation = "disqualified"
        recommendation_reason = "; ".join(disqualification_reasons)
    else:
        total = int(
            cert_result["score"] * weights["certifications"]
            + avail_result["score"] * weights["availability"]
            + experience_score * weights["experience"]
            + location_score * weights["location"]
        )
        total = min(total, 100)
        recommendation, recommendation_reason = _make_recommendation(
            total, cert_result, avail_result
        )

    return {
        "total_score": total,
        "qualified": qualified,
        "disqualification_reasons": disqualification_reasons,
        "recommendation": recommendation,
        "recommendation_reason": recommendation_reason,
        "breakdown": {
            "certifications": cert_result["score"],
            "availability": avail_result["score"],
            "experience": experience_score,
            "location": location_score,
        },
        "matched_certifications": cert_result["matched"],
        "missing_certifications": cert_result["missing_required"] + cert_result["missing_preferred"],
        "availability_overlap": avail_result["overlap"],
        "availability_gaps": avail_result["gaps"],
        # Legacy fields for backwards compatibility
        "matched_skills": cert_result["matched"],
        "missing_skills": cert_result["missing_required"],
    }


def filter_candidates(candidates: list, job: dict, min_score: int = 0) -> list:
    """Score and rank candidates for a job. Returns sorted by score descending.

    Disqualified candidates are sorted to the bottom regardless of score.
    """
    results = []
    for candidate in candidates:
        result = score_candidate(candidate, job)
        result["candidate_id"] = candidate.get("candidate_id", "")
        result["candidate_name"] = (
            f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
        )
        if result["total_score"] >= min_score or not result["qualified"]:
            results.append(result)

    # Qualified candidates first (sorted by score), then disqualified
    qualified = sorted(
        [r for r in results if r["qualified"]],
        key=lambda r: r["total_score"],
        reverse=True,
    )
    disqualified = [r for r in results if not r["qualified"]]
    return qualified + disqualified


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


# ---------------------------------------------------------------------------
# Pre-screen question generation
# ---------------------------------------------------------------------------

def generate_prescreen_questions(job: dict) -> list:
    """Auto-generate pre-screen questions from job requirements.

    Covers:
    - Required certifications → ask if candidate holds them
    - Shift schedule → ask about availability
    - Role-specific follow-ups
    """
    questions = []

    # Cert questions
    for cert in job.get("required_certifications", []):
        questions.append(f"Do you hold a current {cert} license or certification?")

    for cert in job.get("preferred_certifications", []):
        questions.append(f"Do you have a {cert} certification? (preferred but not required)")

    # Availability questions
    shifts = job.get("shift_schedule", [])
    if shifts:
        shift_str = ", ".join(shifts)
        questions.append(
            f"This role requires availability for {shift_str} shifts. "
            f"Are you able to work these hours?"
        )

    # Role-specific questions
    role_category = job.get("role_category")
    if not role_category:
        title = (job.get("title") or "").lower()
        for position, category in POSITION_CATEGORY_MAP.items():
            if position in title:
                role_category = category
                break

    if role_category == "management":
        questions.append("How many years of team management experience do you have?")
        questions.append("Can you describe a time you managed a team in a high-pressure environment?")
    elif role_category == "biosecurity":
        questions.append("Are you available to work on short notice or irregular schedules if needed?")
        questions.append("Do you have experience with health screening or medical protocols?")
    elif role_category == "guest_services":
        questions.append("Do you have experience in customer-facing or hospitality roles?")
    elif role_category == "spa":
        questions.append("How many years of hands-on experience do you have in a spa or salon setting?")

    # Append any manually set screening questions from the job
    for q in job.get("screening_questions", []):
        if q not in questions:
            questions.append(q)

    return questions


# ---------------------------------------------------------------------------
# Indeed search presets — built from config + legacy names
# ---------------------------------------------------------------------------

from src.config.indeed_presets import get_search_presets_for_scraper

# Detailed per-role presets from config
_CONFIG_PRESETS = get_search_presets_for_scraper()

# Legacy grouped preset for backwards compatibility
_LEGACY_PRESETS = {
    "spa_therapists": {
        "search_terms": ["massage therapist", "esthetician", "nail technician"],
        "department": "Spa",
        "role_category": "spa",
    },
    "management": {
        "search_terms": ["spa manager", "station manager", "experience coordinator"],
        "department": "Management",
        "role_category": "management",
    },
    "biosecurity": {
        "search_terms": ["biosecurity specialist", "bio-security specialist"],
        "department": "Biosecurity",
        "role_category": "biosecurity",
    },
    "guest_services": {
        "search_terms": ["guest service associate", "front desk spa", "spa receptionist"],
        "department": "Guest Services",
        "role_category": "guest_services",
    },
}

# Merged: config presets take precedence, legacy names still work
SEARCH_PRESETS = {**_LEGACY_PRESETS, **_CONFIG_PRESETS}


# ---------------------------------------------------------------------------
# Internal scoring helpers
# ---------------------------------------------------------------------------

def _score_certifications(candidate: dict, job: dict) -> dict:
    """Score certification match. Returns 0-100, matched/missing lists."""
    required = [c.lower() for c in job.get("required_certifications", [])]
    preferred = [c.lower() for c in job.get("preferred_certifications", [])]
    candidate_certs = [c.lower() for c in candidate.get("certifications", [])]

    if not required and not preferred:
        return {
            "score": 50,
            "matched": [],
            "missing_required": [],
            "missing_preferred": [],
        }

    matched = []
    missing_required = []
    missing_preferred = []

    for cert in required:
        if cert in candidate_certs:
            matched.append(cert)
        else:
            missing_required.append(cert)

    for cert in preferred:
        if cert in candidate_certs:
            matched.append(cert)
        else:
            missing_preferred.append(cert)

    total_certs = len(required) + len(preferred)
    required_weight = 0.8
    preferred_weight = 0.2

    required_score = (
        (len(required) - len(missing_required)) / len(required) * 100
        if required
        else 100
    )
    preferred_score = (
        (len(preferred) - len(missing_preferred)) / len(preferred) * 100
        if preferred
        else 100
    )

    if required and preferred:
        score = int(required_score * required_weight + preferred_score * preferred_weight)
    elif required:
        score = int(required_score)
    else:
        score = int(preferred_score)

    return {
        "score": score,
        "matched": matched,
        "missing_required": missing_required,
        "missing_preferred": missing_preferred,
    }


def _score_availability(candidate: dict, job: dict) -> dict:
    """Score shift availability overlap. Returns 0-100, overlap/gaps lists."""
    job_shifts = job.get("shift_schedule", [])
    candidate_avail = candidate.get("availability", {})

    if not job_shifts:
        return {"score": 50, "overlap": [], "gaps": []}

    if not candidate_avail:
        return {"score": 50, "overlap": [], "gaps": job_shifts}

    # Flatten all candidate available shifts across all days
    all_candidate_shifts = set()
    for day_shifts in candidate_avail.values():
        if isinstance(day_shifts, list):
            all_candidate_shifts.update(s.lower() for s in day_shifts)

    job_shifts_lower = [s.lower() for s in job_shifts]
    overlap = [s for s in job_shifts_lower if s in all_candidate_shifts]
    gaps = [s for s in job_shifts_lower if s not in all_candidate_shifts]

    score = int((len(overlap) / len(job_shifts_lower)) * 100) if job_shifts_lower else 50
    return {"score": score, "overlap": overlap, "gaps": gaps}


def _score_location(candidate: dict, job: dict) -> int:
    """Score location match. Returns 0-100."""
    candidate_loc = (candidate.get("location") or "").lower().strip()
    job_loc = (job.get("location") or "").lower().strip()

    if not candidate_loc or not job_loc:
        return 50

    if candidate_loc == job_loc:
        return 100

    candidate_parts = set(_split_location(candidate_loc))
    job_parts = set(_split_location(job_loc))

    if candidate_parts & job_parts:
        return 75

    if "remote" in candidate_loc or "remote" in job_loc:
        return 70

    return 20


def _score_experience(candidate: dict, job: dict) -> int:
    """Score experience level. Returns 0-100."""
    # Prefer explicit years_experience field
    candidate_years = candidate.get("years_experience")
    if candidate_years is None:
        candidate_text = f"{candidate.get('notes', '')} {candidate.get('resume_text', '')}".lower()
        candidate_years = _extract_years(candidate_text)

    job_text = f"{job.get('requirements', '')} {job.get('description', '')}".lower()
    job_years = _extract_years(job_text)

    if candidate_years is not None and job_years is not None:
        if candidate_years >= job_years:
            return 100
        elif candidate_years >= job_years * 0.7:
            return 70
        else:
            return 30

    # Seniority keyword matching
    if candidate_years is None:
        candidate_text = f"{candidate.get('notes', '')} {candidate.get('resume_text', '')}".lower()
    else:
        candidate_text = ""

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


def _make_recommendation(total: int, cert_result: dict, avail_result: dict) -> tuple:
    """Return (recommendation, reason) based on score and sub-scores."""
    if total >= 75:
        reason_parts = []
        if cert_result["score"] >= 80:
            reason_parts.append("strong cert match")
        if avail_result["score"] >= 80:
            reason_parts.append("good availability")
        if not reason_parts:
            reason_parts.append("strong overall profile")
        return "suggest_interview", ", ".join(reason_parts).capitalize()
    elif total >= 50:
        gaps = []
        if cert_result["missing_preferred"]:
            gaps.append(f"missing preferred certs: {', '.join(cert_result['missing_preferred'])}")
        if avail_result["gaps"]:
            gaps.append(f"availability gaps: {', '.join(avail_result['gaps'])}")
        reason = "Meets minimum bar. " + ("; ".join(gaps) if gaps else "Review manually.")
        return "flag_review", reason
    else:
        reason_parts = []
        if cert_result["score"] < 50:
            reason_parts.append("cert score low")
        if avail_result["score"] < 50:
            reason_parts.append("availability gap")
        reason = "Below threshold. " + (", ".join(reason_parts) if reason_parts else "Consider skipping.")
        return "needs_info", reason


def _split_location(loc: str) -> list:
    """Split a location string into parts for comparison."""
    return [p.strip() for p in re.split(r"[,/]", loc) if p.strip()]


def _extract_years(text: str) -> Optional[int]:
    """Extract years of experience from text like '5+ years' or '3-5 years'."""
    patterns = [
        r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)",
        r"(\d+)\s*-\s*\d+\s*(?:years?|yrs?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def _detect_seniority(text: str, levels: list) -> Optional[int]:
    """Detect seniority level from text. Returns index in levels list."""
    for i, level in reversed(list(enumerate(levels))):
        if re.search(r"\b" + level + r"\b", text):
            return i
    return None


# ---------------------------------------------------------------------------
# Legacy shim — kept for backwards compat with any code importing extract_skills
# from this module (tests import it from scraper, but just in case)
# ---------------------------------------------------------------------------

def extract_skills(text: str) -> list:
    """Thin wrapper — delegates to scraper.extract_skills."""
    from src.services.scraper import extract_skills as _extract
    return _extract(text)
