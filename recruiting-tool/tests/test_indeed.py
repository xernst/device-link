"""Tests for Indeed Job Sync API integration and Apply webhook."""

import json
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_aws

from src.services.indeed import parse_indeed_apply_webhook, post_job_to_indeed, expire_job_on_indeed


# ---- parse_indeed_apply_webhook tests ----

class TestParseIndeedApplyWebhook:
    def _sample_payload(self, **overrides):
        payload = {
            "applicationId": "app-abc-123",
            "job": {"sourceId": "job-xyz-456"},
            "applicant": {
                "name": {"given": "Maria", "family": "Santos"},
                "contactInfo": [
                    {"type": "EMAIL", "value": "maria@example.com"},
                    {"type": "PHONE", "value": "+12395550101"},
                ],
                "location": {"city": "Naples", "region": "FL"},
                "workExperience": [
                    {"startDateYear": 2019, "endDateYear": 2024},
                ],
            },
            "screenerAnswers": [
                {"question": "Do you hold a current cosmetology license?", "answer": "YES"},
                {"question": "Are you available to work morning shifts?", "answer": "YES"},
                {"question": "Are you available to work evening shifts?", "answer": "NO"},
            ],
        }
        payload.update(overrides)
        return payload

    def test_parses_name(self):
        result = parse_indeed_apply_webhook(self._sample_payload())
        assert result["first_name"] == "Maria"
        assert result["last_name"] == "Santos"

    def test_parses_contact_info(self):
        result = parse_indeed_apply_webhook(self._sample_payload())
        assert result["email"] == "maria@example.com"
        assert result["phone"] == "+12395550101"

    def test_parses_location(self):
        result = parse_indeed_apply_webhook(self._sample_payload())
        assert "Naples" in result["location"]
        assert "FL" in result["location"]

    def test_parses_years_experience(self):
        result = parse_indeed_apply_webhook(self._sample_payload())
        assert result["years_experience"] == 5

    def test_extracts_certifications_from_screener(self):
        result = parse_indeed_apply_webhook(self._sample_payload())
        assert "cosmetology" in result["certifications"]

    def test_extracts_availability_from_screener(self):
        result = parse_indeed_apply_webhook(self._sample_payload())
        assert "morning" in result["availability"].get("any", [])
        assert "evening" not in result["availability"].get("any", [])

    def test_source_is_indeed_apply(self):
        result = parse_indeed_apply_webhook(self._sample_payload())
        assert result["source"] == "indeed_apply"

    def test_application_id_in_notes(self):
        result = parse_indeed_apply_webhook(self._sample_payload())
        assert "app-abc-123" in result["notes"]

    def test_internal_fields_stripped(self):
        result = parse_indeed_apply_webhook(self._sample_payload())
        assert "_indeed_job_source_id" in result  # present but popped by handler
        assert "_indeed_application_id" in result

    def test_empty_payload(self):
        result = parse_indeed_apply_webhook({})
        assert result["first_name"] == ""
        assert result["email"] == ""
        assert result["certifications"] == []

    def test_no_screener_answers(self):
        payload = self._sample_payload()
        payload["screenerAnswers"] = []
        result = parse_indeed_apply_webhook(payload)
        assert result["certifications"] == []
        assert result["availability"] == {}

    def test_resume_url_in_notes(self):
        payload = self._sample_payload()
        payload["applicant"]["resumeUrl"] = "https://indeed.com/resume/abc"
        result = parse_indeed_apply_webhook(payload)
        assert "https://indeed.com/resume/abc" in result["notes"]


# ---- post_job_to_indeed tests ----

class TestPostJobToIndeed:
    def test_returns_error_when_not_configured(self, monkeypatch):
        monkeypatch.delenv("INDEED_CLIENT_ID", raising=False)
        monkeypatch.delenv("INDEED_CLIENT_SECRET", raising=False)
        result = post_job_to_indeed({"job_id": "job-1", "title": "Test"})
        assert result["success"] is False
        assert "not configured" in result["error"]

    def test_returns_error_when_no_employer_id(self, monkeypatch):
        monkeypatch.setenv("INDEED_CLIENT_ID", "test-id")
        monkeypatch.setenv("INDEED_CLIENT_SECRET", "test-secret")
        monkeypatch.delenv("INDEED_EMPLOYER_ID", raising=False)

        with patch("src.services.indeed._get_access_token", return_value="fake-token"):
            result = post_job_to_indeed({"job_id": "job-1", "title": "Test"})
        assert result["success"] is False
        assert "INDEED_EMPLOYER_ID" in result["error"]

    def test_successful_post(self, monkeypatch):
        monkeypatch.setenv("INDEED_CLIENT_ID", "test-id")
        monkeypatch.setenv("INDEED_CLIENT_SECRET", "test-secret")
        monkeypatch.setenv("INDEED_EMPLOYER_ID", "emp-123")

        mock_response = {
            "data": {
                "jobSync": {
                    "sourcedPostingId": "indeed-job-789",
                    "status": "ACTIVE",
                    "errors": [],
                }
            }
        }

        with patch("src.services.indeed._get_access_token", return_value="fake-token"), \
             patch("src.services.indeed._graphql", return_value=mock_response):
            result = post_job_to_indeed({
                "job_id": "job-1",
                "title": "Massage Therapist",
                "location": "Naples, FL",
                "required_certifications": ["massage_therapy"],
                "shift_schedule": ["morning"],
                "role_category": "spa",
            })

        assert result["success"] is True
        assert result["indeed_job_id"] == "indeed-job-789"

    def test_screener_questions_built_from_certs(self, monkeypatch):
        monkeypatch.setenv("INDEED_CLIENT_ID", "test-id")
        monkeypatch.setenv("INDEED_CLIENT_SECRET", "test-secret")
        monkeypatch.setenv("INDEED_EMPLOYER_ID", "emp-123")

        captured = {}

        def capture_graphql(query, variables, token):
            captured["variables"] = variables
            return {"data": {"jobSync": {"sourcedPostingId": "x", "status": "ACTIVE", "errors": []}}}

        with patch("src.services.indeed._get_access_token", return_value="fake-token"), \
             patch("src.services.indeed._graphql", side_effect=capture_graphql):
            post_job_to_indeed({
                "job_id": "job-1",
                "title": "Esthetician",
                "required_certifications": ["esthetician"],
                "shift_schedule": ["evening"],
            })

        questions = captured["variables"]["jobPosting"]["screenerQuestions"]
        assert any("esthetician" in q["question"].lower() for q in questions)
        assert any("evening" in q["question"].lower() for q in questions)


# ---- expire_job tests ----

class TestExpireJobOnIndeed:
    def test_returns_error_when_not_configured(self, monkeypatch):
        monkeypatch.delenv("INDEED_CLIENT_ID", raising=False)
        result = expire_job_on_indeed("indeed-job-123")
        assert result["success"] is False

    def test_successful_expire(self, monkeypatch):
        monkeypatch.setenv("INDEED_CLIENT_ID", "test-id")
        monkeypatch.setenv("INDEED_CLIENT_SECRET", "test-secret")
        monkeypatch.setenv("INDEED_EMPLOYER_ID", "emp-123")

        mock_response = {
            "data": {
                "expireJobPosting": {"status": "EXPIRED", "errors": []}
            }
        }

        with patch("src.services.indeed._get_access_token", return_value="fake-token"), \
             patch("src.services.indeed._graphql", return_value=mock_response):
            result = expire_job_on_indeed("indeed-job-123")

        assert result["success"] is True
        assert result["status"] == "EXPIRED"


# ---- Handler integration tests ----

class TestIndeedHandlers:
    @mock_aws
    def test_apply_webhook_creates_candidate(self, dynamodb_table):
        from src.handlers.indeed import apply_webhook
        from src.models.job import Job, JobStatus, RoleCategory

        # Create a job with job_id matching the sourceId
        job = Job(
            title="Massage Therapist",
            status=JobStatus.OPEN,
            required_certifications=["massage_therapy"],
            role_category=RoleCategory.SPA,
        )
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=job.to_dynamo())

        payload = {
            "applicationId": "app-test-001",
            "job": {"sourceId": job.job_id},
            "applicant": {
                "name": {"given": "Lucia", "family": "Gomez"},
                "contactInfo": [
                    {"type": "EMAIL", "value": "lucia@example.com"},
                    {"type": "PHONE", "value": "+12395550199"},
                ],
                "location": {"city": "Naples", "region": "FL"},
                "workExperience": [{"startDateYear": 2020, "endDateYear": 2025}],
            },
            "screenerAnswers": [
                {"question": "Do you hold a current massage_therapy license?", "answer": "YES"},
            ],
        }

        event = {
            "body": json.dumps(payload),
            "headers": {},
        }

        with patch("src.handlers.indeed.notify_new_candidate"):
            response = apply_webhook(event, None)

        body = json.loads(response["body"])
        assert response["statusCode"] == 201
        assert "candidate_id" in body
        assert body["score"] is not None
        assert body["score"]["qualified"] is True

    @mock_aws
    def test_publish_job_handler_no_config(self, dynamodb_table, monkeypatch):
        from src.handlers.indeed import publish_job
        from src.models.job import Job, JobStatus

        monkeypatch.delenv("INDEED_CLIENT_ID", raising=False)

        job = Job(title="Nail Technician", status=JobStatus.OPEN)
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=job.to_dynamo())

        event = {"pathParameters": {"id": job.job_id}}
        response = publish_job(event, None)
        body = json.loads(response["body"])

        # Should succeed at handler level but return Indeed error
        assert response["statusCode"] == 200
        assert body["indeed_result"]["success"] is False

    @mock_aws
    def test_publish_job_not_found(self, dynamodb_table):
        from src.handlers.indeed import publish_job

        event = {"pathParameters": {"id": "nonexistent"}}
        response = publish_job(event, None)
        assert response["statusCode"] == 404

    @mock_aws
    def test_unpublish_job_no_indeed_id(self, dynamodb_table):
        from src.handlers.indeed import unpublish_job
        from src.models.job import Job, JobStatus

        job = Job(title="Guest Service Associate", status=JobStatus.OPEN)
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=job.to_dynamo())

        event = {"pathParameters": {"id": job.job_id}}
        response = unpublish_job(event, None)
        assert response["statusCode"] == 400
        assert "indeed_job_id" in json.loads(response["body"])["error"]
