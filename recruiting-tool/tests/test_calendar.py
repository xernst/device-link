"""Tests for calendar service and interview handler."""

import json
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_aws

from tests.conftest import api_event


class TestCalendarService:
    """Unit tests for src/services/calendar.py."""

    def test_generate_ics_basic(self):
        from src.services.calendar import generate_ics
        ics = generate_ics(
            candidate={"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
            job={"title": "Spa Manager"},
            interviewer_email="hr@example.com",
            start_iso="2026-03-25T10:00:00+00:00",
            duration_minutes=30,
            location="Main Office",
            notes="First round interview",
        )
        assert "BEGIN:VCALENDAR" in ics
        assert "END:VCALENDAR" in ics
        assert "BEGIN:VEVENT" in ics
        assert "Jane Doe" in ics
        assert "Spa Manager" in ics
        assert "Main Office" in ics
        assert "hr@example.com" in ics
        assert "jane@example.com" in ics
        assert "METHOD:REQUEST" in ics

    def test_generate_ics_no_location(self):
        from src.services.calendar import generate_ics
        ics = generate_ics(
            candidate={"first_name": "Bob", "last_name": "Smith", "email": ""},
            job={"title": "Technician"},
            interviewer_email="hr@example.com",
            start_iso="2026-04-01T14:00:00+00:00",
            duration_minutes=60,
            location="",
            notes="",
        )
        assert "LOCATION" not in ics
        assert "Bob Smith" in ics

    def test_generate_ics_naive_datetime(self):
        """Handles naive datetimes (no timezone info)."""
        from src.services.calendar import generate_ics
        ics = generate_ics(
            candidate={"first_name": "A", "last_name": "B", "email": "a@b.com"},
            job={"title": "Test"},
            interviewer_email="x@y.com",
            start_iso="2026-03-25T10:00:00",
            duration_minutes=30,
            location="",
            notes="",
        )
        assert "DTSTART:" in ics
        assert "DTEND:" in ics

    def test_create_interview_event_ics_fallback(self, monkeypatch):
        """When Google env vars are not set, returns ICS content and no calendar_link."""
        monkeypatch.delenv("GOOGLE_CALENDAR_ID", raising=False)
        monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)

        from src.services.calendar import create_interview_event
        result = create_interview_event(
            candidate={"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
            job={"title": "Esthetician"},
            interviewer_email="hr@example.com",
            start_iso="2026-03-25T10:00:00+00:00",
            duration_minutes=45,
        )
        assert result["event_id"]
        assert "BEGIN:VCALENDAR" in result["ics_content"]
        assert result["calendar_link"] is None

    def test_create_interview_event_google_success(self, monkeypatch):
        """When Google API works, returns event_id and calendar_link."""
        import base64
        fake_sa = base64.b64encode(json.dumps({"type": "service_account"}).encode()).decode()
        monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")
        monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", fake_sa)

        with patch("src.services.calendar._create_google_event") as mock_gcal:
            mock_gcal.return_value = {
                "event_id": "google-evt-123",
                "calendar_link": "https://calendar.google.com/event?id=123",
            }

            from src.services.calendar import create_interview_event
            result = create_interview_event(
                candidate={"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
                job={"title": "Manager"},
                interviewer_email="hr@example.com",
                start_iso="2026-03-25T10:00:00+00:00",
            )

        assert result["event_id"] == "google-evt-123"
        assert result["calendar_link"] == "https://calendar.google.com/event?id=123"
        assert "BEGIN:VCALENDAR" in result["ics_content"]

    def test_create_interview_event_google_fails_gracefully(self, monkeypatch):
        """If Google API throws, falls back to ICS."""
        import base64
        fake_sa = base64.b64encode(json.dumps({"type": "service_account"}).encode()).decode()
        monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")
        monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", fake_sa)

        with patch("src.services.calendar._create_google_event") as mock_gcal:
            mock_gcal.side_effect = Exception("Google API down")

            from src.services.calendar import create_interview_event
            result = create_interview_event(
                candidate={"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
                job={"title": "Manager"},
                interviewer_email="hr@example.com",
                start_iso="2026-03-25T10:00:00+00:00",
            )

        assert result["event_id"]  # UUID fallback
        assert result["calendar_link"] is None
        assert "BEGIN:VCALENDAR" in result["ics_content"]


class TestInterviewHandler:
    """Integration tests for the interview scheduling handler."""

    @mock_aws
    def test_schedule_interview_success(self, dynamodb_table, monkeypatch):
        """POST /interviews — full flow."""
        monkeypatch.delenv("GOOGLE_CALENDAR_ID", raising=False)
        monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
        monkeypatch.delenv("OUTREACH_EMAIL_FROM", raising=False)

        from src.models.candidate import Candidate
        from src.models.job import Job
        from src.services import dynamodb as db

        candidate = Candidate(first_name="Jane", last_name="Doe", email="jane@example.com", job_id="job-1")
        job = Job(job_id="job-1", title="Spa Manager")
        db.put_item(candidate.to_dynamo())
        db.put_item(job.to_dynamo())

        from src.handlers.interviews import schedule
        event = api_event("POST", "/interviews", body={
            "candidate_id": candidate.candidate_id,
            "job_id": "job-1",
            "interviewer_email": "hr@example.com",
            "start_time": "2026-03-25T10:00:00-05:00",
            "duration_minutes": 30,
            "location": "Conference Room A",
            "notes": "First round",
        })
        resp = schedule(event, None)

        assert resp["statusCode"] == 201
        body = json.loads(resp["body"])
        assert body["event_id"]
        assert "BEGIN:VCALENDAR" in body["ics_content"]
        assert body["candidate_status"] == "screening_scheduled"
        assert body["interview"]["candidate_id"] == candidate.candidate_id

        # Verify candidate status was updated in DB
        updated = db.get_item(f"CANDIDATE#{candidate.candidate_id}", "PROFILE")
        assert updated["status"]["S"] == "screening_scheduled"

    @mock_aws
    def test_schedule_interview_sends_confirmation_email(self, dynamodb_table, monkeypatch):
        """When OUTREACH_EMAIL_FROM is set, sends confirmation email."""
        monkeypatch.setenv("OUTREACH_EMAIL_FROM", "recruit@example.com")
        monkeypatch.delenv("GOOGLE_CALENDAR_ID", raising=False)
        monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)

        from src.models.candidate import Candidate
        from src.models.job import Job
        from src.services import dynamodb as db

        candidate = Candidate(first_name="Jane", last_name="Doe", email="jane@example.com", job_id="job-1")
        job = Job(job_id="job-1", title="Spa Manager")
        db.put_item(candidate.to_dynamo())
        db.put_item(job.to_dynamo())

        with patch("src.handlers.interviews.send_email") as mock_send:
            mock_send.return_value = {"sent": True, "message_id": "conf1"}

            from src.handlers.interviews import schedule
            event = api_event("POST", "/interviews", body={
                "candidate_id": candidate.candidate_id,
                "job_id": "job-1",
                "interviewer_email": "hr@example.com",
                "start_time": "2026-03-25T10:00:00-05:00",
            })
            resp = schedule(event, None)

        assert resp["statusCode"] == 201
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[1]["to_address"] == "jane@example.com"
        assert "Spa Manager" in call_args[1]["subject"]

    @mock_aws
    def test_schedule_interview_missing_fields(self, dynamodb_table):
        from src.handlers.interviews import schedule
        event = api_event("POST", "/interviews", body={"candidate_id": "c1"})
        resp = schedule(event, None)
        assert resp["statusCode"] == 400
        assert "required" in json.loads(resp["body"])["error"]

    @mock_aws
    def test_schedule_interview_candidate_not_found(self, dynamodb_table):
        from src.handlers.interviews import schedule
        event = api_event("POST", "/interviews", body={
            "candidate_id": "fake",
            "job_id": "job-1",
            "interviewer_email": "hr@example.com",
            "start_time": "2026-03-25T10:00:00-05:00",
        })
        resp = schedule(event, None)
        assert resp["statusCode"] == 404

    @mock_aws
    def test_schedule_interview_job_not_found(self, dynamodb_table):
        from src.models.candidate import Candidate
        from src.services import dynamodb as db
        candidate = Candidate(first_name="Jane", last_name="Doe")
        db.put_item(candidate.to_dynamo())

        from src.handlers.interviews import schedule
        event = api_event("POST", "/interviews", body={
            "candidate_id": candidate.candidate_id,
            "job_id": "nonexistent",
            "interviewer_email": "hr@example.com",
            "start_time": "2026-03-25T10:00:00-05:00",
        })
        resp = schedule(event, None)
        assert resp["statusCode"] == 404
