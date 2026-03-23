"""Tests for rich Slack Block Kit notifications — candidate cards, job postings,
daily digest, and screening result cards."""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.services.slack import (
    _candidate_blocks,
    _job_posting_blocks,
    _screening_result_blocks,
    _daily_digest_blocks,
    _score_badge,
    notify_new_candidate,
    notify_new_job,
    notify_screening_complete,
    send_daily_digest,
)


# ---------------------------------------------------------------------------
# Score badge
# ---------------------------------------------------------------------------

class TestScoreBadge:
    def test_green_for_75_plus(self):
        assert "🟢" in _score_badge(75)
        assert "🟢" in _score_badge(100)

    def test_yellow_for_50_to_74(self):
        assert "🟡" in _score_badge(50)
        assert "🟡" in _score_badge(74)

    def test_red_for_below_50(self):
        assert "🔴" in _score_badge(0)
        assert "🔴" in _score_badge(49)

    def test_non_numeric_returns_dash(self):
        assert "—" in _score_badge("—")
        assert "—" in _score_badge(None)


# ---------------------------------------------------------------------------
# Candidate card blocks
# ---------------------------------------------------------------------------

class TestCandidateCardBlocks:
    @pytest.fixture
    def candidate(self):
        return {
            "candidate_id": "c1", "first_name": "Jane", "last_name": "Doe",
            "email": "jane@example.com", "phone": "+1234567890",
            "location": "Naples, FL", "source": "indeed_apply", "status": "new",
            "certifications": ["cosmetology", "nail_technician"],
            "availability": {"monday": ["morning", "evening"], "wednesday": ["morning"]},
            "years_experience": 5,
        }

    @pytest.fixture
    def job(self):
        return {"job_id": "j1", "title": "Massage Therapist", "location": "Naples, FL"}

    @pytest.fixture
    def high_score(self):
        return {
            "total_score": 85, "qualified": True,
            "recommendation": "suggest_interview",
            "disqualification_reasons": [],
            "breakdown": {"certifications": 100, "availability": 80, "experience": 90, "location": 100},
        }

    def test_has_header_block(self, candidate, job, high_score):
        blocks = _candidate_blocks(candidate, job, high_score)
        header = blocks[0]
        assert header["type"] == "header"
        assert "Jane Doe" in header["text"]["text"]
        assert "Massage Therapist" in header["text"]["text"]

    def test_green_score_badge_for_high_score(self, candidate, job, high_score):
        blocks = _candidate_blocks(candidate, job, high_score)
        fields_text = str(blocks)
        assert "🟢" in fields_text

    def test_red_score_badge_for_low_score(self, candidate, job):
        score = {"total_score": 25, "recommendation": "needs_info", "breakdown": {}}
        blocks = _candidate_blocks(candidate, job, score)
        assert "🔴" in str(blocks)

    def test_has_action_buttons(self, candidate, job, high_score):
        blocks = _candidate_blocks(candidate, job, high_score)
        action_block = next((b for b in blocks if b["type"] == "actions"), None)
        assert action_block is not None
        action_ids = [a["action_id"] for a in action_block["elements"]]
        assert "schedule_interview" in action_ids
        assert "flag_review" in action_ids
        assert "reject_candidate" in action_ids

    def test_action_values_contain_ids(self, candidate, job):
        blocks = _candidate_blocks(candidate, job)
        action_block = next(b for b in blocks if b["type"] == "actions")
        for element in action_block["elements"]:
            val = json.loads(element["value"])
            assert val["candidate_id"] == "c1"
            assert val["job_id"] == "j1"

    def test_disqualification_shown(self, candidate, job):
        score = {
            "total_score": 0, "recommendation": "disqualified",
            "disqualification_reasons": ["Missing required cert: massage_therapy"],
            "breakdown": {},
        }
        blocks = _candidate_blocks(candidate, job, score)
        text = str(blocks)
        assert "massage_therapy" in text
        assert "⛔" in text

    def test_has_divider_before_actions(self, candidate, job):
        blocks = _candidate_blocks(candidate, job)
        action_idx = next(i for i, b in enumerate(blocks) if b["type"] == "actions")
        assert blocks[action_idx - 1]["type"] == "divider"

    def test_certifications_displayed(self, candidate, job):
        blocks = _candidate_blocks(candidate, job)
        text = str(blocks)
        assert "cosmetology" in text
        assert "nail_technician" in text

    def test_availability_displayed(self, candidate, job):
        blocks = _candidate_blocks(candidate, job)
        text = str(blocks)
        assert "evening" in text
        assert "morning" in text

    def test_no_score_shows_dash(self, candidate, job):
        blocks = _candidate_blocks(candidate, job, None)
        text = str(blocks)
        assert "—" in text


# ---------------------------------------------------------------------------
# Job posting blocks
# ---------------------------------------------------------------------------

class TestJobPostingBlocks:
    @pytest.fixture
    def job(self):
        return {
            "job_id": "j1", "title": "Nail Technician",
            "location": "Naples, FL",
            "salary_min": 35000, "salary_max": 55000,
            "required_certifications": ["nail_technician", "cosmetology"],
            "description": "Full-time nail technician needed.",
            "shift_schedule": ["morning", "afternoon"],
        }

    def test_has_header(self, job):
        blocks = _job_posting_blocks(job)
        assert blocks[0]["type"] == "header"
        assert "Nail Technician" in blocks[0]["text"]["text"]

    def test_salary_range_displayed(self, job):
        blocks = _job_posting_blocks(job)
        text = str(blocks)
        assert "$35,000" in text
        assert "$55,000" in text

    def test_required_certs_highlighted(self, job):
        blocks = _job_posting_blocks(job)
        text = str(blocks)
        assert "`nail_technician`" in text
        assert "`cosmetology`" in text

    def test_pipeline_count(self, job):
        blocks = _job_posting_blocks(job, pipeline_count=12)
        text = str(blocks)
        assert "12 candidates" in text

    def test_pipeline_count_singular(self, job):
        blocks = _job_posting_blocks(job, pipeline_count=1)
        text = str(blocks)
        assert "1 candidate " in text

    def test_shift_schedule_shown(self, job):
        blocks = _job_posting_blocks(job)
        text = str(blocks)
        assert "morning" in text
        assert "afternoon" in text

    def test_description_truncated(self, job):
        job["description"] = "x" * 500
        blocks = _job_posting_blocks(job)
        desc_block = next(b for b in blocks if b.get("text", {}).get("text", "").startswith("*Description*"))
        assert desc_block["text"]["text"].endswith("…")
        # Should be max 300 chars of content + "…"
        assert len(desc_block["text"]["text"]) < 330

    def test_no_salary_shows_not_specified(self):
        job = {"title": "Test", "location": "FL"}
        blocks = _job_posting_blocks(job)
        text = str(blocks)
        assert "Not specified" in text

    def test_no_certs_shows_none(self):
        job = {"title": "Test", "location": "FL"}
        blocks = _job_posting_blocks(job)
        text = str(blocks)
        assert "None" in text


# ---------------------------------------------------------------------------
# Screening result blocks
# ---------------------------------------------------------------------------

class TestScreeningResultBlocks:
    def test_pass_badge(self):
        blocks = _screening_result_blocks("Jane Doe", "Stylist", "pass", score=82)
        text = str(blocks)
        assert "✅" in text
        assert "Passed" in text
        assert "🟢" in text  # score >= 75

    def test_fail_badge(self):
        blocks = _screening_result_blocks("Bob Smith", "Stylist", "fail", score=30)
        text = str(blocks)
        assert "❌" in text
        assert "Failed" in text
        assert "🔴" in text  # score < 50

    def test_review_badge(self):
        blocks = _screening_result_blocks("Ana Lee", "Tech", "review", score=60)
        text = str(blocks)
        assert "👀" in text
        assert "Needs Review" in text

    def test_next_step_pass(self):
        blocks = _screening_result_blocks("Jane", "Job", "pass")
        text = str(blocks)
        assert "in-person interview" in text

    def test_next_step_fail(self):
        blocks = _screening_result_blocks("Jane", "Job", "fail")
        text = str(blocks)
        assert "rejection" in text

    def test_next_step_review(self):
        blocks = _screening_result_blocks("Jane", "Job", "review")
        text = str(blocks)
        assert "Manager review" in text

    def test_answers_shown(self):
        answers = ["Has 3 years experience", "Available weekends", "Holds cosmetology license"]
        blocks = _screening_result_blocks("Jane", "Job", "pass", answers=answers)
        text = str(blocks)
        assert "3 years experience" in text
        assert "weekends" in text

    def test_answers_capped_at_5(self):
        answers = [f"Answer {i}" for i in range(10)]
        blocks = _screening_result_blocks("Jane", "Job", "pass", answers=answers)
        text = str(blocks)
        assert "Answer 4" in text
        assert "Answer 5" not in text

    def test_summary_shown(self):
        blocks = _screening_result_blocks("Jane", "Job", "pass", summary="Strong candidate overall.")
        text = str(blocks)
        assert "Strong candidate overall" in text

    def test_header_contains_name(self):
        blocks = _screening_result_blocks("Jane Doe", "Stylist", "pass")
        assert blocks[0]["type"] == "header"
        assert "Jane Doe" in blocks[0]["text"]["text"]


# ---------------------------------------------------------------------------
# Daily digest blocks
# ---------------------------------------------------------------------------

class TestDailyDigestBlocks:
    def test_has_header(self):
        blocks = _daily_digest_blocks()
        assert blocks[0]["type"] == "header"
        assert "Daily Recruiting Digest" in blocks[0]["text"]["text"]

    def test_shows_counts(self):
        blocks = _daily_digest_blocks(new_candidates=5, pending_reviews=3, upcoming_screenings=2)
        text = str(blocks)
        assert "5" in text
        assert "3" in text
        assert "2" in text

    def test_top_candidates_shown(self):
        top = [
            {"name": "Alice Smith", "score": 92, "role": "Massage Therapist"},
            {"name": "Bob Jones", "score": 78, "role": "Esthetician"},
        ]
        blocks = _daily_digest_blocks(top_candidates=top)
        text = str(blocks)
        assert "Alice Smith" in text
        assert "Bob Jones" in text
        assert "🏆" in text

    def test_top_candidates_capped_at_5(self):
        top = [{"name": f"Person {i}", "score": 90 - i, "role": "Test"} for i in range(10)]
        blocks = _daily_digest_blocks(top_candidates=top)
        text = str(blocks)
        assert "Person 4" in text
        assert "Person 5" not in text

    def test_empty_digest_shows_message(self):
        blocks = _daily_digest_blocks()
        text = str(blocks)
        assert "No activity" in text

    def test_not_empty_when_has_candidates(self):
        blocks = _daily_digest_blocks(new_candidates=1)
        text = str(blocks)
        assert "No activity" not in text


# ---------------------------------------------------------------------------
# Public notification functions (integration)
# ---------------------------------------------------------------------------

class TestNotifyNewCandidate:
    def test_uses_block_kit_when_bot_token(self, monkeypatch):
        import src.services.slack as slack_mod
        monkeypatch.setattr(slack_mod, "SLACK_BOT_TOKEN", "xoxb-test")
        candidate = {
            "candidate_id": "c1", "first_name": "Jane", "last_name": "Doe",
            "certifications": [], "availability": {}, "status": "new",
        }
        job = {"job_id": "j1", "title": "Stylist"}
        with patch.object(slack_mod, "_api_call", return_value={"ok": True}) as mock_api:
            result = notify_new_candidate("Jane Doe", "Stylist", "indeed", candidate, job)
        assert result is True
        call_args = mock_api.call_args
        assert "blocks" in call_args[0][1]

    def test_falls_back_to_webhook(self, monkeypatch):
        import src.services.slack as slack_mod
        monkeypatch.setattr(slack_mod, "SLACK_BOT_TOKEN", "")
        with patch.object(slack_mod, "_webhook_send", return_value=True) as mock_wh:
            notify_new_candidate("Jane Doe", "Stylist", "indeed")
        mock_wh.assert_called_once()


class TestNotifyScreeningComplete:
    def test_uses_block_kit_when_bot_token(self, monkeypatch):
        import src.services.slack as slack_mod
        monkeypatch.setattr(slack_mod, "SLACK_BOT_TOKEN", "xoxb-test")
        with patch.object(slack_mod, "_api_call", return_value={"ok": True}) as mock_api:
            result = notify_screening_complete("Jane", "Stylist", "pass", score=85)
        assert result is True
        payload = mock_api.call_args[0][1]
        assert "blocks" in payload

    def test_falls_back_to_webhook(self, monkeypatch):
        import src.services.slack as slack_mod
        monkeypatch.setattr(slack_mod, "SLACK_BOT_TOKEN", "")
        with patch.object(slack_mod, "_webhook_send", return_value=True) as mock_wh:
            notify_screening_complete("Jane", "Stylist", "pass", score=85)
        mock_wh.assert_called_once()
        text = mock_wh.call_args[0][0]["text"]
        assert "PASS" in text

    def test_passes_answers_and_summary(self, monkeypatch):
        import src.services.slack as slack_mod
        monkeypatch.setattr(slack_mod, "SLACK_BOT_TOKEN", "xoxb-test")
        with patch.object(slack_mod, "_api_call", return_value={"ok": True}) as mock_api:
            notify_screening_complete(
                "Jane", "Stylist", "pass", score=85,
                answers=["Has 5 years exp"], summary="Strong candidate",
            )
        blocks = mock_api.call_args[0][1]["blocks"]
        text = str(blocks)
        assert "5 years exp" in text
        assert "Strong candidate" in text


class TestNotifyNewJob:
    def test_uses_block_kit_when_bot_token(self, monkeypatch):
        import src.services.slack as slack_mod
        monkeypatch.setattr(slack_mod, "SLACK_BOT_TOKEN", "xoxb-test")
        job = {"title": "Stylist", "location": "FL", "salary_min": 40000, "salary_max": 60000}
        with patch.object(slack_mod, "_api_call", return_value={"ok": True}) as mock_api:
            result = notify_new_job(job, pipeline_count=5)
        assert result is True
        payload = mock_api.call_args[0][1]
        assert "blocks" in payload

    def test_falls_back_to_webhook(self, monkeypatch):
        import src.services.slack as slack_mod
        monkeypatch.setattr(slack_mod, "SLACK_BOT_TOKEN", "")
        with patch.object(slack_mod, "_webhook_send", return_value=True) as mock_wh:
            notify_new_job({"title": "Stylist", "location": "FL"})
        mock_wh.assert_called_once()
        text = mock_wh.call_args[0][0]["text"]
        assert "Stylist" in text


class TestSendDailyDigest:
    def test_uses_block_kit_when_bot_token(self, monkeypatch):
        import src.services.slack as slack_mod
        monkeypatch.setattr(slack_mod, "SLACK_BOT_TOKEN", "xoxb-test")
        with patch.object(slack_mod, "_api_call", return_value={"ok": True}) as mock_api:
            result = send_daily_digest(new_candidates=3, pending_reviews=1)
        assert result is True
        payload = mock_api.call_args[0][1]
        assert "blocks" in payload

    def test_falls_back_to_webhook(self, monkeypatch):
        import src.services.slack as slack_mod
        monkeypatch.setattr(slack_mod, "SLACK_BOT_TOKEN", "")
        with patch.object(slack_mod, "_webhook_send", return_value=True) as mock_wh:
            send_daily_digest(new_candidates=3, pending_reviews=1, upcoming_screenings=2)
        mock_wh.assert_called_once()
        text = mock_wh.call_args[0][0]["text"]
        assert "3" in text
