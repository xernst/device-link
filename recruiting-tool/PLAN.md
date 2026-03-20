# Recruiting Tool — Survey-Driven Refinement Plan

Based on team survey (2 respondents: Morgan, who lives in the role, + 1 historical perspective).

---

## Survey Findings → Code Gaps

| Survey Finding | Current State | Gap |
|---|---|---|
| Certifications are #1 filter (100%) | No cert field on Candidate or Job | Need `certifications` on Candidate, `required_certifications` on Job |
| Shift availability is #1 bot task (100%) | No availability field anywhere | Need `availability` on Candidate, `shift_schedule` on Job |
| Biggest blocker: unqualified candidates (50%) | Filtering scores skills but doesn't gate on hard requirements | Need hard disqualifiers (missing required cert = auto-flag) |
| Biggest blocker: candidate responsiveness (50%) | No responsiveness tracking | Need `last_contacted`, `response_status` on Candidate |
| Want bot to confirm certs + ask availability (100%) | Screening questions are free-text | Need auto-generated pre-screen questions from job requirements |
| Role-specific criteria vary by position | Generic skill matching | Need role category profiles with different scoring weights |
| 50% want "suggest interview" / 50% "just give info" | No recommendation in score output | Need `recommendation` field with actionable next step |
| 100% source from Indeed | Already built jobspy integration | Good — tune default search terms for their actual roles |

---

## Implementation Steps

### Step 1: Extend Candidate Model

Add to `src/models/candidate.py`:

```python
certifications: list      # ["cosmetology", "massage_therapy", "esthetician"]
availability: dict        # {"monday": ["morning","afternoon"], "tuesday": ["evening"], ...}
years_experience: int     # Explicit, not text-parsed
last_contacted: str       # ISO timestamp of last outreach
response_status: str      # "not_contacted", "awaiting_response", "responsive", "unresponsive"
```

Update `to_dynamo()`, `from_dynamo()`, `to_api()`, `from_api()` for all new fields.

### Step 2: Extend Job Model

Add to `src/models/job.py`:

```python
required_certifications: list   # ["cosmetology"] — hard requirement
preferred_certifications: list  # ["color_specialist"] — nice to have
shift_schedule: list            # ["morning", "afternoon", "evening", "weekend"]
role_category: str              # "spa", "management", "biosecurity", "guest_services"
```

Update all serialization methods. Update `jobs.update()` handler to include new fields.

### Step 3: Role-Specific Scoring Profiles

Add role category profiles in `src/services/filtering.py`:

```python
ROLE_PROFILES = {
    "spa": {
        "weights": {"certifications": 0.40, "experience": 0.20, "availability": 0.25, "location": 0.15},
        "cert_required": True,  # Missing required cert = hard fail
    },
    "management": {
        "weights": {"experience": 0.40, "certifications": 0.15, "availability": 0.25, "location": 0.20},
        "cert_required": False,
    },
    "biosecurity": {
        "weights": {"availability": 0.35, "certifications": 0.25, "experience": 0.20, "location": 0.20},
        "cert_required": True,
    },
    "guest_services": {
        "weights": {"availability": 0.35, "experience": 0.25, "certifications": 0.15, "location": 0.25},
        "cert_required": False,
    },
}
```

Positions → categories (from survey):
- **spa**: Massage Therapist, Nail Technician, Esthetician
- **management**: Spa Manager, Station Manager, Assistant Station Manager, Experience Coordinator, Senior Experience Coordinator
- **biosecurity**: Bio-Security Specialist
- **guest_services**: Guest Service Associate

### Step 4: Rewrite Scoring Engine

Replace the current 60/20/20 (skills/location/experience) with:

1. **Certification score** (new): Check candidate certs against job required/preferred certs. If `cert_required` and candidate is missing a required cert → hard flag (`"disqualified": true`, reason given).
2. **Availability score** (new): Overlap between candidate availability and job shift schedule. Full overlap = 100, partial = proportional, no data = 50 (neutral).
3. **Experience score** (existing, refined): Use explicit `years_experience` field first, fall back to text parsing.
4. **Location score** (existing): Keep as-is.
5. Drop generic "skills" scoring — the team cares about certs, not keyword overlap.

Add to score output:
```python
{
    "total_score": 82,
    "qualified": True,                          # False if missing required cert
    "disqualification_reasons": [],             # ["Missing required certification: cosmetology"]
    "recommendation": "suggest_interview",      # or "flag_review" or "needs_info" or "disqualified"
    "recommendation_reason": "Strong cert match, full availability overlap, 5+ years experience",
    "breakdown": {
        "certifications": 100,
        "availability": 80,
        "experience": 75,
        "location": 100,
    },
    "matched_certifications": ["cosmetology", "color_specialist"],
    "missing_certifications": [],
    "availability_overlap": ["morning", "afternoon"],
    "availability_gaps": ["evening"],
}
```

### Step 5: Auto-Generate Pre-Screen Questions

New function in `src/services/filtering.py`:

```python
def generate_prescreen_questions(job: dict) -> list:
```

Takes a job and generates screening questions based on:
- Required certifications → "Do you hold a current [X] license/certification?"
- Shift schedule → "Are you available to work [morning/evening/weekend] shifts?"
- Role-specific → management gets experience questions, spa gets certification questions

These auto-generated questions get merged with any manual `screening_questions` on the job.

### Step 6: Recommendation Logic

Thresholds (configurable later):

| Score Range | Qualified? | Recommendation |
|---|---|---|
| 75-100 | Yes | `suggest_interview` |
| 50-74 | Yes | `flag_review` |
| 0-100 | No (missing required cert) | `disqualified` |
| 0-49 | Yes | `needs_info` |

### Step 7: Candidate Responsiveness Tracking

Add `PATCH /candidates/{id}/contact` endpoint:
```json
{
    "response_status": "awaiting_response",
    "last_contacted": "2026-03-20T10:00:00Z"
}
```

Allow filtering candidates by `response_status` in `GET /jobs/{id}/candidates`:
```
GET /jobs/{id}/candidates?response_status=responsive
```

### Step 8: Indeed Search Presets

Add a presets function in `src/services/scraper.py` for the team's common searches:

```python
SEARCH_PRESETS = {
    "spa_therapists": {
        "search_terms": ["massage therapist", "esthetician", "nail technician"],
        "department": "Spa",
    },
    "management": {
        "search_terms": ["spa manager", "station manager", "experience coordinator"],
        "department": "Management",
    },
    "biosecurity": {
        "search_terms": ["biosecurity specialist", "bio-security"],
        "department": "Biosecurity",
    },
    "guest_services": {
        "search_terms": ["guest service associate", "front desk spa"],
        "department": "Guest Services",
    },
}
```

New endpoint: `POST /scrape/preset` — takes a preset name + location, runs all search terms, deduplicates, and bulk-imports.

### Step 9: Update Tests

- Update existing model serialization tests for new fields
- Add certification gate tests (missing required cert → disqualified)
- Add availability overlap scoring tests
- Add role-specific weight tests (spa vs management vs biosecurity)
- Add recommendation threshold tests
- Add pre-screen question generation tests
- Add responsiveness tracking tests
- Add preset scraping tests
- Update the existing scenario tests (Bud Light, Sweeney) to still pass with new fields

### Step 10: Update SAM Template

Add new Lambda functions:
- `ContactCandidateFunction` → `PATCH /candidates/{id}/contact`
- `ScrapePresetFunction` → `POST /scrape/preset`
- `PreScreenQuestionsFunction` → `GET /jobs/{id}/prescreen-questions`

---

## Files Changed

| File | Change |
|---|---|
| `src/models/candidate.py` | Add certifications, availability, years_experience, last_contacted, response_status |
| `src/models/job.py` | Add required_certifications, preferred_certifications, shift_schedule, role_category |
| `src/services/filtering.py` | Role profiles, cert gating, availability scoring, recommendations, prescreen questions |
| `src/services/scraper.py` | Search presets for team's roles |
| `src/handlers/filtering.py` | Update score output, add prescreen-questions handler |
| `src/handlers/candidates.py` | Add contact tracking handler |
| `src/handlers/scraping.py` | Add preset handler |
| `template.yaml` | 3 new Lambda functions |
| `tests/test_filtering.py` | Update + add tests for all new logic |
| `tests/test_models.py` | Update roundtrip tests for new fields |

---

## Not in Scope (Future)

- Resume parsing (OCR/PDF extraction)
- SMS/email outreach automation
- Calendar integration for interview scheduling
- Indeed application tracking (would need Indeed partner API)
