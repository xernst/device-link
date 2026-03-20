"""Tests for data models."""

from src.models.candidate import Candidate, CandidateStatus, ResponseStatus
from src.models.job import Job, JobStatus, RoleCategory
from src.models.screening import Screening, ScreeningStatus, ScreeningResult


def test_candidate_roundtrip():
    candidate = Candidate(
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone="+1234567890",
        location="Naples, FL",
        source="indeed",
        job_id="job-123",
        certifications=["cosmetology", "color_specialist"],
        availability={"monday": ["morning", "afternoon"], "tuesday": ["evening"]},
        years_experience=5,
        response_status=ResponseStatus.AWAITING_RESPONSE,
    )
    dynamo_item = candidate.to_dynamo()
    restored = Candidate.from_dynamo(dynamo_item)
    assert restored.first_name == "Jane"
    assert restored.last_name == "Doe"
    assert restored.email == "jane@example.com"
    assert restored.status == CandidateStatus.NEW
    assert restored.job_id == "job-123"
    assert restored.certifications == ["cosmetology", "color_specialist"]
    assert restored.availability == {"monday": ["morning", "afternoon"], "tuesday": ["evening"]}
    assert restored.years_experience == 5
    assert restored.response_status == ResponseStatus.AWAITING_RESPONSE


def test_candidate_api_roundtrip():
    data = {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane@example.com",
        "phone": "+1234567890",
        "status": "new",
        "certifications": ["massage_therapy"],
        "availability": {"friday": ["morning"]},
        "years_experience": 3,
        "response_status": "responsive",
    }
    candidate = Candidate.from_api(data)
    api_output = candidate.to_api()
    assert api_output["first_name"] == "Jane"
    assert api_output["status"] == "new"
    assert api_output["certifications"] == ["massage_therapy"]
    assert api_output["years_experience"] == 3
    assert api_output["response_status"] == "responsive"


def test_candidate_defaults():
    candidate = Candidate(first_name="Test", last_name="User")
    assert candidate.certifications == []
    assert candidate.availability == {}
    assert candidate.years_experience is None
    assert candidate.last_contacted is None
    assert candidate.response_status == ResponseStatus.NOT_CONTACTED


def test_job_roundtrip():
    job = Job(
        title="Massage Therapist",
        location="Naples, FL",
        department="Spa",
        status=JobStatus.OPEN,
        salary_min=40000,
        salary_max=60000,
        screening_questions=["Tell me about your experience", "Why this role?"],
        required_certifications=["massage_therapy"],
        preferred_certifications=["cosmetology"],
        shift_schedule=["morning", "afternoon"],
        role_category=RoleCategory.SPA,
    )
    dynamo_item = job.to_dynamo()
    restored = Job.from_dynamo(dynamo_item)
    assert restored.title == "Massage Therapist"
    assert restored.salary_min == 40000
    assert restored.screening_questions == ["Tell me about your experience", "Why this role?"]
    assert restored.required_certifications == ["massage_therapy"]
    assert restored.preferred_certifications == ["cosmetology"]
    assert restored.shift_schedule == ["morning", "afternoon"]
    assert restored.role_category == RoleCategory.SPA


def test_job_api_roundtrip():
    data = {
        "title": "Esthetician",
        "location": "Naples, FL",
        "department": "Spa",
        "required_certifications": ["esthetician"],
        "shift_schedule": ["evening", "weekend"],
        "role_category": "spa",
    }
    job = Job.from_api(data)
    api_output = job.to_api()
    assert api_output["required_certifications"] == ["esthetician"]
    assert api_output["shift_schedule"] == ["evening", "weekend"]
    assert api_output["role_category"] == "spa"


def test_job_defaults():
    job = Job(title="Test Role")
    assert job.required_certifications == []
    assert job.preferred_certifications == []
    assert job.shift_schedule == []
    assert job.role_category is None


def test_screening_roundtrip():
    screening = Screening(
        candidate_id="cand-123",
        job_id="job-456",
        status=ScreeningStatus.COMPLETED,
        result=ScreeningResult.PASS,
        ai_score=85,
        duration_seconds=420,
        questions_asked=["Tell me about yourself"],
        responses=["I have 5 years experience..."],
    )
    dynamo_item = screening.to_dynamo()
    restored = Screening.from_dynamo(dynamo_item)
    assert restored.candidate_id == "cand-123"
    assert restored.result == ScreeningResult.PASS
    assert restored.ai_score == 85
    assert restored.duration_seconds == 420
