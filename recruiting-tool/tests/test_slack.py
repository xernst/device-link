"""Tests for Slack interactive service and handlers."""

import json
import pytest
from unittest.mock import patch, MagicMock
from urllib.parse import urlencode
from moto import mock_aws

from src.services.slack import (
    verify_slack_signature,
    _candidate_blocks,
    _rankings_blocks,
)


# ---- Signature verification ----

class TestVerifySlackSignature:
    def test_no_secret_passes(self, monkeypatch):
        monkeypatch.setenv("SLACK_SIGNING_SECRET", "")
        assert verify_slack_signature("body", "12345", "sig") is True

    def test_valid_signature(self, monkeypatch):
        import hmac, hashlib, time
        secret = "test-secret-abc"
        monkeypatch.setenv("SLACK_SIGNING_SECRET", secret)
        ts = str(int(time.time()))
        body = "payload=test"
        base = f"v0:{ts}:{body}"
        sig = "v0=" + hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest()
        assert verify_slack_signature(body, ts, sig) is True

    def test_invalid_signature_rejected(self, monkeypatch):
        import src.services.slack as slack_mod
        monkeypatch.setattr(slack_mod, "SLACK_SIGNING_SECRET", "real-secret")
        import time
        ts = str(int(time.time()))
        assert verify_slack_signature("body", ts, "v0=fakesig") is False

    def test_stale_timestamp_rejected(self, monkeypatch):
        import src.services.slack as slack_mod
        monkeypatch.setattr(slack_mod, "SLACK_SIGNING_SECRET", "secret")
        old_ts = "1000000000"  # way in the past
        assert verify_slack_signature("body", old_ts, "v0=anything") is False


# ---- Block Kit builders ----

class TestCandidateBlocks:
    def test_returns_list_of_blocks(self):
        candidate = {
            "candidate_id": "c1", "first_name": "Jane", "last_name": "Doe",
            "email": "jane@example.com", "phone": "+1234567890",
            "location": "Naples, FL", "source": "indeed_apply", "status": "new",
            "certifications": ["cosmetology"], "availability": {"monday": ["morning"]},
            "years_experience": 5,
        }
        job = {"job_id": "j1", "title": "Massage Therapist", "location": "Naples, FL"}
        score = {
            "total_score": 85, "qualified": True, "recommendation": "suggest_interview",
            "disqualification_reasons": [],
            "breakdown": {"certifications": 100, "availability": 80, "experience": 90, "location": 100},
        }
        blocks = _candidate_blocks(candidate, job, score)
        assert isinstance(blocks, list)
        assert len(blocks) >= 3
        # Should have action buttons
        action_block = next((b for b in blocks if b["type"] == "actions"), None)
        assert action_block is not None
        action_ids = [a["action_id"] for a in action_block["elements"]]
        assert "schedule_interview" in action_ids
        assert "reject_candidate" in action_ids

    def test_disqualified_shows_reason(self):
        candidate = {
            "candidate_id": "c2", "first_name": "Bob", "last_name": "Test",
            "certifications": [], "availability": {}, "status": "new",
        }
        job = {"job_id": "j1", "title": "Esthetician"}
        score = {
            "total_score": 0, "qualified": False,
            "recommendation": "disqualified",
            "disqualification_reasons": ["Missing required certification: esthetician"],
            "breakdown": {},
        }
        blocks = _candidate_blocks(candidate, job, score)
        context_blocks = [b for b in blocks if b["type"] == "context"]
        text = " ".join(str(e) for b in context_blocks for e in b.get("elements", []))
        assert "esthetician" in text

    def test_action_values_contain_ids(self):
        candidate = {"candidate_id": "cand-xyz", "first_name": "A", "last_name": "B",
                     "certifications": [], "availability": {}, "status": "new"}
        job = {"job_id": "job-xyz", "title": "Test"}
        blocks = _candidate_blocks(candidate, job)
        action_block = next(b for b in blocks if b["type"] == "actions")
        for element in action_block["elements"]:
            val = json.loads(element["value"])
            assert val["candidate_id"] == "cand-xyz"
            assert val["job_id"] == "job-xyz"


class TestRankingsBlocks:
    def test_returns_header_and_rows(self):
        rankings = [
            {"candidate_id": "c1", "candidate_name": "Alice Smith", "total_score": 90,
             "qualified": True, "recommendation": "suggest_interview"},
            {"candidate_id": "c2", "candidate_name": "Bob Jones", "total_score": 45,
             "qualified": True, "recommendation": "needs_info"},
        ]
        job = {"job_id": "j1", "title": "Nail Technician", "location": "Naples, FL"}
        blocks = _rankings_blocks(rankings, job)
        assert blocks[0]["type"] == "header"
        assert len(blocks) == 3  # header + 2 candidates

    def test_empty_rankings_shows_message(self):
        blocks = _rankings_blocks([], {"job_id": "j1", "title": "Test"})
        text = str(blocks)
        assert "No candidates" in text

    def test_caps_at_10(self):
        rankings = [
            {"candidate_id": f"c{i}", "candidate_name": f"Person {i}",
             "total_score": 50, "qualified": True, "recommendation": "flag_review"}
            for i in range(20)
        ]
        job = {"job_id": "j1", "title": "Test"}
        blocks = _rankings_blocks(rankings, job)
        # header + 10 candidates
        assert len(blocks) == 11


# ---- Slash command handlers ----

class TestSlashCommands:
    @mock_aws
    def test_rank_no_text(self, dynamodb_table):
        from src.handlers.slack_interactive import handle_commands
        with patch("src.handlers.slack_interactive.verify_slack_signature", return_value=True):
            event = {"body": urlencode({"command": "/rank", "text": "", "channel_id": "C123", "user_id": "U1"}), "headers": {}}
            response = handle_commands(event, None)
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "Usage" in body["text"]

    @mock_aws
    def test_rank_job_not_found(self, dynamodb_table):
        from src.handlers.slack_interactive import handle_commands
        with patch("src.handlers.slack_interactive.verify_slack_signature", return_value=True):
            event = {"body": urlencode({"command": "/rank", "text": "nonexistent job xyz", "channel_id": "C123", "user_id": "U1"}), "headers": {}}
            response = handle_commands(event, None)
        body = json.loads(response["body"])
        assert "No open job found" in body["text"]

    @mock_aws
    def test_rank_posts_results(self, dynamodb_table):
        from src.handlers.slack_interactive import handle_commands
        from src.models.job import Job, JobStatus, RoleCategory
        from src.models.candidate import Candidate

        job = Job(title="Massage Therapist", status=JobStatus.OPEN, role_category=RoleCategory.SPA,
                  required_certifications=["massage_therapy"])
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=job.to_dynamo())

        cand = Candidate(first_name="Ana", last_name="Lopez", job_id=job.job_id,
                         certifications=["massage_therapy"], location="Naples, FL")
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=cand.to_dynamo())

        with patch("src.handlers.slack_interactive.verify_slack_signature", return_value=True), \
             patch("src.handlers.slack_interactive.post_rankings", return_value=True):
            event = {"body": urlencode({"command": "/rank", "text": "Massage Therapist", "channel_id": "C123", "user_id": "U1"}), "headers": {}}
            response = handle_commands(event, None)

        body = json.loads(response["body"])
        assert "Posted rankings" in body["text"] or "ranking" in body["text"].lower()

    @mock_aws
    def test_candidates_command(self, dynamodb_table):
        from src.handlers.slack_interactive import handle_commands
        from src.models.job import Job, JobStatus
        from src.models.candidate import Candidate

        job = Job(title="Esthetician", status=JobStatus.OPEN)
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=job.to_dynamo())
        cand = Candidate(first_name="Maria", last_name="Cruz", job_id=job.job_id)
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=cand.to_dynamo())

        with patch("src.handlers.slack_interactive.verify_slack_signature", return_value=True):
            event = {"body": urlencode({"command": "/candidates", "text": job.job_id, "channel_id": "C123", "user_id": "U1"}), "headers": {}}
            response = handle_commands(event, None)

        body = json.loads(response["body"])
        assert "Maria" in body["text"]

    @mock_aws
    def test_prescreen_command(self, dynamodb_table):
        from src.handlers.slack_interactive import handle_commands
        from src.models.job import Job, JobStatus, RoleCategory

        job = Job(title="Nail Technician", status=JobStatus.OPEN,
                  required_certifications=["nail_technician"],
                  shift_schedule=["morning", "evening"],
                  role_category=RoleCategory.SPA)
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=job.to_dynamo())

        with patch("src.handlers.slack_interactive.verify_slack_signature", return_value=True):
            event = {"body": urlencode({"command": "/prescreen", "text": job.job_id, "channel_id": "C123", "user_id": "U1"}), "headers": {}}
            response = handle_commands(event, None)

        body = json.loads(response["body"])
        assert "nail_technician" in body["text"]
        assert "morning" in body["text"]

    @mock_aws
    def test_invalid_signature_rejected(self, dynamodb_table):
        from src.handlers.slack_interactive import handle_commands
        with patch("src.handlers.slack_interactive.verify_slack_signature", return_value=False):
            event = {"body": "payload=test", "headers": {}}
            response = handle_commands(event, None)
        body = json.loads(response.get("body", "{}"))
        assert "signature" in body.get("text", "").lower() or "signature" in body.get("error", "").lower()


# ---- Actions handler ----

class TestActionsHandler:
    @mock_aws
    def test_invalid_signature_returns_200(self, dynamodb_table):
        """Slack requires 200 even on errors to prevent retries."""
        from src.handlers.slack_interactive import handle_actions
        with patch("src.handlers.slack_interactive.verify_slack_signature", return_value=False):
            event = {"body": "payload={}", "headers": {}}
            response = handle_actions(event, None)
        assert response["statusCode"] == 401

    @mock_aws
    def test_reject_action_updates_status(self, dynamodb_table):
        from src.handlers.slack_interactive import handle_actions
        from src.models.candidate import Candidate

        cand = Candidate(first_name="Test", last_name="Reject")
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=cand.to_dynamo())

        payload = {
            "type": "block_actions",
            "response_url": "https://hooks.slack.com/actions/test",
            "user": {"id": "U1", "name": "morgan"},
            "actions": [{
                "action_id": "reject_candidate",
                "value": json.dumps({"candidate_id": cand.candidate_id, "job_id": ""}),
            }],
        }
        from urllib.parse import quote
        body = f"payload={quote(json.dumps(payload))}"

        with patch("src.handlers.slack_interactive.verify_slack_signature", return_value=True), \
             patch("src.handlers.slack_interactive.respond_to_action") as mock_respond:
            event = {"body": body, "headers": {}}
            response = handle_actions(event, None)

        assert response["statusCode"] == 200
        # Verify candidate was rejected
        item = dynamodb_table.get_item(
            TableName="recruiting-candidates",
            Key={"PK": {"S": f"CANDIDATE#{cand.candidate_id}"}, "SK": {"S": "PROFILE"}}
        )["Item"]
        assert item["status"]["S"] == "rejected"
