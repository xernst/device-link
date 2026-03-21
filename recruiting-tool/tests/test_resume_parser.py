"""Tests for resume parsing service and handler."""

import json
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_aws

from tests.conftest import api_event


class TestResumeParserService:
    """Unit tests for src/services/resume_parser.py."""

    def test_parse_resume_extracts_text_and_skills(self):
        """Textract returns LINE blocks — we extract text, skills, certs, and years."""
        mock_response = {
            "Blocks": [
                {"BlockType": "PAGE", "Text": ""},
                {"BlockType": "LINE", "Text": "Jane Doe"},
                {"BlockType": "LINE", "Text": "Licensed Massage Therapist with 5 years of experience"},
                {"BlockType": "LINE", "Text": "Skills: customer service, scheduling, massage therapy"},
                {"BlockType": "LINE", "Text": "CPR Certified, First Aid"},
            ]
        }
        with patch("src.services.resume_parser.boto3") as mock_boto:
            mock_client = MagicMock()
            mock_client.detect_document_text.return_value = mock_response
            mock_boto.client.return_value = mock_client

            from src.services.resume_parser import parse_resume
            result = parse_resume("test-bucket", "resumes/test.pdf")

        assert "error" not in result
        assert "Jane Doe" in result["raw_text"]
        assert result["years_experience"] == 5
        assert "cpr certified" in result["certifications"] or "cpr" in result["certifications"]
        assert "first aid" in result["certifications"]
        assert "customer service" in result["skills"]
        assert "massage therapy" in result["skills"]

    def test_parse_resume_no_experience_found(self):
        """When no years pattern matches, years_experience is None."""
        mock_response = {
            "Blocks": [
                {"BlockType": "LINE", "Text": "John Smith"},
                {"BlockType": "LINE", "Text": "Recent graduate looking for work"},
            ]
        }
        with patch("src.services.resume_parser.boto3") as mock_boto:
            mock_client = MagicMock()
            mock_client.detect_document_text.return_value = mock_response
            mock_boto.client.return_value = mock_client

            from src.services.resume_parser import parse_resume
            result = parse_resume("test-bucket", "resumes/test.pdf")

        assert result["years_experience"] is None
        assert result["certifications"] == []

    def test_parse_resume_range_years(self):
        """Pattern '3-5 years of experience' extracts the higher end."""
        mock_response = {
            "Blocks": [
                {"BlockType": "LINE", "Text": "3-5 years of experience in spa management"},
            ]
        }
        with patch("src.services.resume_parser.boto3") as mock_boto:
            mock_client = MagicMock()
            mock_client.detect_document_text.return_value = mock_response
            mock_boto.client.return_value = mock_client

            from src.services.resume_parser import parse_resume
            result = parse_resume("test-bucket", "resumes/test.pdf")

        assert result["years_experience"] == 5

    def test_parse_resume_textract_error(self):
        """Textract API failure returns error dict instead of raising."""
        with patch("src.services.resume_parser.boto3") as mock_boto:
            mock_client = MagicMock()
            mock_client.detect_document_text.side_effect = Exception("Textract unavailable")
            mock_boto.client.return_value = mock_client
            mock_boto.exceptions.Boto3Error = Exception

            from src.services.resume_parser import parse_resume
            result = parse_resume("test-bucket", "resumes/test.pdf")

        assert "error" in result
        assert result["raw_text"] == ""

    def test_extract_certifications_dedup(self):
        """Certs are deduplicated and sorted."""
        from src.services.resume_parser import _extract_certifications
        result = _extract_certifications("CPR certified. Also CPR and First Aid trained. LMT licensed.")
        assert result == sorted(set(result))
        assert "cpr" in result or "cpr certified" in result

    def test_extract_certifications_empty(self):
        from src.services.resume_parser import _extract_certifications
        assert _extract_certifications("") == []
        assert _extract_certifications(None) == []

    def test_extract_years_experience_plus_format(self):
        from src.services.resume_parser import _extract_years_experience
        assert _extract_years_experience("10+ years experience in cosmetology") == 10

    def test_extract_years_experience_no_match(self):
        from src.services.resume_parser import _extract_years_experience
        assert _extract_years_experience("I have lots of experience") is None
        assert _extract_years_experience("") is None
        assert _extract_years_experience(None) is None


class TestParseResumeHandler:
    """Integration tests for the parse-resume handler."""

    @mock_aws
    def test_parse_resume_handler_success(self, dynamodb_table):
        """POST /candidates/{id}/parse-resume — full flow."""
        import os
        os.environ["ASSETS_BUCKET"] = "test-assets"

        from src.models.candidate import Candidate
        candidate = Candidate(
            first_name="Jane", last_name="Doe",
            email="jane@example.com", resume_s3_key="resumes/jane.pdf",
        )
        from src.services import dynamodb as db
        db.put_item(candidate.to_dynamo())

        mock_textract_response = {
            "Blocks": [
                {"BlockType": "LINE", "Text": "Jane Doe"},
                {"BlockType": "LINE", "Text": "Licensed Massage Therapist"},
                {"BlockType": "LINE", "Text": "8 years of experience"},
                {"BlockType": "LINE", "Text": "CPR Certified"},
                {"BlockType": "LINE", "Text": "Skills: customer service, scheduling"},
            ]
        }

        with patch("src.services.resume_parser.boto3") as mock_boto:
            mock_client = MagicMock()
            mock_client.detect_document_text.return_value = mock_textract_response
            mock_boto.client.return_value = mock_client

            from src.handlers.resume import parse
            event = api_event("POST", f"/candidates/{candidate.candidate_id}/parse-resume",
                              path_params={"id": candidate.candidate_id})
            resp = parse(event, None)

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["extracted"]["years_experience"] == 8
        assert "customer service" in body["extracted"]["skills"]
        assert body["candidate"]["years_experience"] == 8
        assert "[Resume Parse]" in body["candidate"]["notes"]

    @mock_aws
    def test_parse_resume_candidate_not_found(self, dynamodb_table):
        from src.handlers.resume import parse
        event = api_event("POST", "/candidates/fake-id/parse-resume",
                          path_params={"id": "fake-id"})
        resp = parse(event, None)
        assert resp["statusCode"] == 404

    @mock_aws
    def test_parse_resume_no_resume_key(self, dynamodb_table):
        """Candidate exists but has no resume_s3_key."""
        from src.models.candidate import Candidate
        from src.services import dynamodb as db
        candidate = Candidate(first_name="Bob", last_name="Smith")
        db.put_item(candidate.to_dynamo())

        from src.handlers.resume import parse
        event = api_event("POST", f"/candidates/{candidate.candidate_id}/parse-resume",
                          path_params={"id": candidate.candidate_id})
        resp = parse(event, None)
        assert resp["statusCode"] == 400
        assert "resume" in json.loads(resp["body"])["error"].lower()
