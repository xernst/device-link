"""Tests for outreach service and handlers."""

import json
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_aws

from tests.conftest import api_event


class TestOutreachService:
    """Unit tests for src/services/outreach.py."""

    def test_send_email_success(self, monkeypatch):
        monkeypatch.setenv("OUTREACH_EMAIL_FROM", "recruit@example.com")
        with patch("src.services.outreach.boto3") as mock_boto:
            mock_client = MagicMock()
            mock_client.send_email.return_value = {"MessageId": "abc123"}
            mock_boto.client.return_value = mock_client

            from src.services.outreach import send_email
            result = send_email("candidate@example.com", "Subject", "<p>Hi</p>", "Hi")

        assert result["sent"] is True
        assert result["message_id"] == "abc123"

    def test_send_email_no_from_address(self, monkeypatch):
        monkeypatch.delenv("OUTREACH_EMAIL_FROM", raising=False)
        from src.services.outreach import send_email
        result = send_email("candidate@example.com", "Subject", "<p>Hi</p>", "Hi")
        assert result["sent"] is False
        assert "not configured" in result["error"]

    def test_send_email_ses_error(self, monkeypatch):
        monkeypatch.setenv("OUTREACH_EMAIL_FROM", "recruit@example.com")
        with patch("src.services.outreach.boto3") as mock_boto:
            mock_client = MagicMock()
            mock_client.send_email.side_effect = Exception("SES down")
            mock_boto.client.return_value = mock_client

            from src.services.outreach import send_email
            result = send_email("candidate@example.com", "Subject", "<p>Hi</p>", "Hi")

        assert result["sent"] is False
        assert "SES error" in result["error"]

    def test_send_sms_success(self, monkeypatch):
        monkeypatch.setenv("OUTREACH_SMS_ENABLED", "true")
        with patch("src.services.outreach.boto3") as mock_boto:
            mock_client = MagicMock()
            mock_client.publish.return_value = {"MessageId": "sms123"}
            mock_boto.client.return_value = mock_client

            from src.services.outreach import send_sms
            result = send_sms("+15551234567", "Hello")

        assert result["sent"] is True
        assert result["message_id"] == "sms123"

    def test_send_sms_disabled(self, monkeypatch):
        monkeypatch.setenv("OUTREACH_SMS_ENABLED", "false")
        from src.services.outreach import send_sms
        result = send_sms("+15551234567", "Hello")
        assert result["sent"] is False
        assert "not enabled" in result["error"]

    def test_send_sms_sns_error(self, monkeypatch):
        monkeypatch.setenv("OUTREACH_SMS_ENABLED", "true")
        with patch("src.services.outreach.boto3") as mock_boto:
            mock_client = MagicMock()
            mock_client.publish.side_effect = Exception("SNS down")
            mock_boto.client.return_value = mock_client

            from src.services.outreach import send_sms
            result = send_sms("+15551234567", "Hello")

        assert result["sent"] is False
        assert "SNS error" in result["error"]

    def test_send_outreach_email(self, monkeypatch):
        monkeypatch.setenv("OUTREACH_EMAIL_FROM", "recruit@example.com")
        candidate = {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com", "phone": ""}
        job = {"title": "Spa Manager"}

        with patch("src.services.outreach.boto3") as mock_boto:
            mock_client = MagicMock()
            mock_client.send_email.return_value = {"MessageId": "msg1"}
            mock_boto.client.return_value = mock_client

            from src.services.outreach import send_outreach
            result = send_outreach(candidate, job, channel="email", template="interview_invite")

        assert result["sent"] is True
        assert result["channel"] == "email"
        assert result["template"] == "interview_invite"

    def test_send_outreach_sms(self, monkeypatch):
        monkeypatch.setenv("OUTREACH_SMS_ENABLED", "true")
        candidate = {"first_name": "Jane", "last_name": "Doe", "email": "", "phone": "+15551234567"}
        job = {"title": "Spa Manager"}

        with patch("src.services.outreach.boto3") as mock_boto:
            mock_client = MagicMock()
            mock_client.publish.return_value = {"MessageId": "sms1"}
            mock_boto.client.return_value = mock_client

            from src.services.outreach import send_outreach
            result = send_outreach(candidate, job, channel="sms", template="screening_reminder")

        assert result["sent"] is True
        assert result["channel"] == "sms"
        assert result["template"] == "screening_reminder"

    def test_send_outreach_unknown_template(self):
        from src.services.outreach import send_outreach
        result = send_outreach({}, {}, template="nonexistent")
        assert result["sent"] is False
        assert "Unknown template" in result["error"]

    def test_send_outreach_unknown_channel(self):
        from src.services.outreach import send_outreach
        result = send_outreach(
            {"first_name": "A", "last_name": "B", "email": "a@b.com"},
            {"title": "Job"},
            channel="pigeon",
        )
        assert result["sent"] is False
        assert "Unknown channel" in result["error"]

    def test_send_outreach_no_email(self, monkeypatch):
        monkeypatch.setenv("OUTREACH_EMAIL_FROM", "recruit@example.com")
        from src.services.outreach import send_outreach
        result = send_outreach(
            {"first_name": "A", "last_name": "B", "email": "", "phone": ""},
            {"title": "Job"},
            channel="email",
        )
        assert result["sent"] is False
        assert "no email" in result["error"].lower()

    def test_send_outreach_no_phone(self, monkeypatch):
        monkeypatch.setenv("OUTREACH_SMS_ENABLED", "true")
        from src.services.outreach import send_outreach
        result = send_outreach(
            {"first_name": "A", "last_name": "B", "email": "a@b.com", "phone": ""},
            {"title": "Job"},
            channel="sms",
        )
        assert result["sent"] is False
        assert "no phone" in result["error"].lower()

    def test_all_templates_exist(self):
        from src.services.outreach import TEMPLATES
        assert "interview_invite" in TEMPLATES
        assert "screening_reminder" in TEMPLATES
        assert "status_update" in TEMPLATES
        for name, tmpl in TEMPLATES.items():
            assert "subject" in tmpl
            assert "body_html" in tmpl
            assert "body_text" in tmpl
            assert "sms" in tmpl


class TestOutreachHandler:
    """Integration tests for outreach handlers."""

    @mock_aws
    def test_send_outreach_handler(self, dynamodb_table, monkeypatch):
        """POST /candidates/{id}/outreach — send email to candidate."""
        monkeypatch.setenv("OUTREACH_EMAIL_FROM", "recruit@example.com")

        from src.models.candidate import Candidate
        from src.models.job import Job
        from src.services import dynamodb as db

        candidate = Candidate(first_name="Jane", last_name="Doe", email="jane@example.com", job_id="job-1")
        job = Job(job_id="job-1", title="Spa Manager")
        db.put_item(candidate.to_dynamo())
        db.put_item(job.to_dynamo())

        with patch("src.services.outreach.boto3") as mock_boto:
            mock_client = MagicMock()
            mock_client.send_email.return_value = {"MessageId": "msg1"}
            mock_boto.client.return_value = mock_client

            from src.handlers.outreach import send
            event = api_event("POST", f"/candidates/{candidate.candidate_id}/outreach",
                              body={"job_id": "job-1", "channel": "email", "template": "interview_invite"},
                              path_params={"id": candidate.candidate_id})
            resp = send(event, None)

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["sent"] is True
        assert body["channel"] == "email"

        # Verify candidate was updated to awaiting_response
        updated = db.get_item(f"CANDIDATE#{candidate.candidate_id}", "PROFILE")
        assert updated["response_status"]["S"] == "awaiting_response"

    @mock_aws
    def test_send_outreach_candidate_not_found(self, dynamodb_table):
        from src.handlers.outreach import send
        event = api_event("POST", "/candidates/fake/outreach",
                          body={"job_id": "job-1"},
                          path_params={"id": "fake"})
        resp = send(event, None)
        assert resp["statusCode"] == 404

    @mock_aws
    def test_send_outreach_job_not_found(self, dynamodb_table):
        from src.models.candidate import Candidate
        from src.services import dynamodb as db
        candidate = Candidate(first_name="Jane", last_name="Doe")
        db.put_item(candidate.to_dynamo())

        from src.handlers.outreach import send
        event = api_event("POST", f"/candidates/{candidate.candidate_id}/outreach",
                          body={"job_id": "nonexistent"},
                          path_params={"id": candidate.candidate_id})
        resp = send(event, None)
        assert resp["statusCode"] == 404

    @mock_aws
    def test_send_outreach_missing_job_id(self, dynamodb_table):
        from src.handlers.outreach import send
        event = api_event("POST", "/candidates/any/outreach",
                          body={},
                          path_params={"id": "any"})
        resp = send(event, None)
        assert resp["statusCode"] == 400

    @mock_aws
    def test_bulk_outreach_handler(self, dynamodb_table, monkeypatch):
        """POST /jobs/{id}/outreach-bulk — send to all candidates for a job."""
        monkeypatch.setenv("OUTREACH_EMAIL_FROM", "recruit@example.com")

        from src.models.candidate import Candidate, ResponseStatus
        from src.models.job import Job
        from src.services import dynamodb as db

        job = Job(job_id="job-bulk", title="Esthetician")
        db.put_item(job.to_dynamo())

        # Create 3 candidates: 2 not_contacted, 1 awaiting_response
        c1 = Candidate(first_name="A", last_name="One", email="a@example.com", job_id="job-bulk",
                        response_status=ResponseStatus.NOT_CONTACTED)
        c2 = Candidate(first_name="B", last_name="Two", email="b@example.com", job_id="job-bulk",
                        response_status=ResponseStatus.NOT_CONTACTED)
        c3 = Candidate(first_name="C", last_name="Three", email="c@example.com", job_id="job-bulk",
                        response_status=ResponseStatus.AWAITING_RESPONSE)
        db.put_item(c1.to_dynamo())
        db.put_item(c2.to_dynamo())
        db.put_item(c3.to_dynamo())

        with patch("src.services.outreach.boto3") as mock_boto:
            mock_client = MagicMock()
            mock_client.send_email.return_value = {"MessageId": "bulk1"}
            mock_boto.client.return_value = mock_client

            from src.handlers.outreach import send_bulk
            event = api_event("POST", "/jobs/job-bulk/outreach-bulk",
                              body={"channel": "email", "template": "screening_reminder",
                                    "response_status_filter": "not_contacted"},
                              path_params={"id": "job-bulk"})
            resp = send_bulk(event, None)

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        # Should only send to the 2 not_contacted candidates
        assert body["total_candidates"] == 2
        assert body["sent"] == 2

    @mock_aws
    def test_bulk_outreach_job_not_found(self, dynamodb_table):
        from src.handlers.outreach import send_bulk
        event = api_event("POST", "/jobs/fake/outreach-bulk",
                          body={},
                          path_params={"id": "fake"})
        resp = send_bulk(event, None)
        assert resp["statusCode"] == 404
