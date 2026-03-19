"""Tests for data models."""

from src.models.candidate import Candidate, CandidateStatus
from src.models.job import Job, JobStatus
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
    )
    dynamo_item = candidate.to_dynamo()
    restored = Candidate.from_dynamo(dynamo_item)
    assert restored.first_name == "Jane"
    assert restored.last_name == "Doe"
    assert restored.email == "jane@example.com"
    assert restored.status == CandidateStatus.NEW
    assert restored.job_id == "job-123"


def test_candidate_api_roundtrip():
    data = {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane@example.com",
        "phone": "+1234567890",
        "status": "new",
    }
    candidate = Candidate.from_api(data)
    api_output = candidate.to_api()
    assert api_output["first_name"] == "Jane"
    assert api_output["status"] == "new"


def test_job_roundtrip():
    job = Job(
        title="Stylist",
        location="Naples, FL",
        department="Salon",
        status=JobStatus.OPEN,
        salary_min=40000,
        salary_max=60000,
        screening_questions=["Tell me about your experience", "Why this role?"],
    )
    dynamo_item = job.to_dynamo()
    restored = Job.from_dynamo(dynamo_item)
    assert restored.title == "Stylist"
    assert restored.salary_min == 40000
    assert restored.screening_questions == ["Tell me about your experience", "Why this role?"]


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
