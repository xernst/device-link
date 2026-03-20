"""Job scraping service using python-jobspy to pull listings from Indeed and other boards."""

import re
from typing import Optional


def scrape_jobs(
    search_term: str,
    location: str = "",
    site_names: Optional[list] = None,
    results_wanted: int = 20,
    hours_old: int = 72,
    country: str = "USA",
    proxies: Optional[list] = None,
) -> list:
    """Scrape job listings from job boards.

    Returns a list of dicts with normalized job data.
    """
    try:
        from jobspy import scrape_jobs as _scrape
    except ImportError:
        raise RuntimeError("python-jobspy is not installed. Run: pip install python-jobspy")

    sites = site_names or ["indeed"]

    kwargs = {
        "site_name": sites,
        "search_term": search_term,
        "results_wanted": results_wanted,
        "hours_old": hours_old,
        "country_indeed": country,
    }
    if location:
        kwargs["location"] = location
    if proxies:
        kwargs["proxies"] = proxies

    df = _scrape(**kwargs)

    if df.empty:
        return []

    jobs = []
    for _, row in df.iterrows():
        job = {
            "title": _safe_str(row, "title"),
            "company": _safe_str(row, "company"),
            "location": _safe_str(row, "location"),
            "description": _safe_str(row, "description"),
            "job_url": _safe_str(row, "job_url"),
            "site": _safe_str(row, "site"),
            "date_posted": _safe_str(row, "date_posted"),
        }
        # Optional fields that may not exist in all results
        for field in ["salary_min", "salary_max", "job_type", "company_url"]:
            if field in row.index:
                val = row[field]
                if val is not None and str(val) != "nan":
                    job[field] = int(val) if "salary" in field else str(val)
        jobs.append(job)

    return jobs


def _safe_str(row, col: str) -> str:
    """Safely extract a string value from a DataFrame row."""
    if col not in row.index:
        return ""
    val = row[col]
    if val is None or (isinstance(val, float) and str(val) == "nan"):
        return ""
    return str(val)


def extract_skills(text: str) -> list:
    """Extract common skills/keywords from job description or resume text."""
    if not text:
        return []

    # Normalize
    text_lower = text.lower()

    # Common skill patterns for recruiting (salon/spa + general)
    skill_patterns = [
        # Technical / general
        "python", "javascript", "typescript", "react", "node.js", "aws", "sql",
        "java", "c\\+\\+", "go", "rust", "docker", "kubernetes", "terraform",
        "git", "ci/cd", "agile", "scrum", "project management",
        # Marketing / PR / comms (relevant to the crisis comms test scenarios)
        "public relations", "crisis management", "crisis communications",
        "social media", "digital marketing", "content strategy", "brand management",
        "media relations", "corporate communications", "stakeholder management",
        "reputation management",
        # Salon / spa / beauty
        "cosmetology", "esthetician", "hair styling", "color specialist",
        "nail technician", "massage therapy", "skin care", "customer service",
        "scheduling", "inventory management", "retail sales",
        # General professional
        "leadership", "communication", "analytics", "data analysis",
        "budgeting", "strategic planning", "team management",
        "microsoft office", "excel", "powerpoint",
    ]

    found = []
    for pattern in skill_patterns:
        if re.search(r'\b' + pattern + r'\b', text_lower):
            # Store the clean version
            found.append(pattern.replace("\\+\\+", "++").replace("\\b", ""))

    return sorted(set(found))
