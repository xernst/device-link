"""
Integration tests: Sydney Sweeney x American Eagle Jeans Incident (2025)

Scenario: A brand is hiring a Social Media Crisis Manager after the
Sydney Sweeney / American Eagle "Great Jeans" campaign controversy.
The ad played on "genes vs jeans" wordplay, went viral, got politicized
(Trump/Vance weighed in), was amplified by AI-driven TikTok bots, and
triggered a full-blown culture war. American Eagle saw billions of
impressions but faced boycott threats and stock volatility.

These tests simulate the full recruiting pipeline:
  1. Create the crisis manager job posting with screening questions
  2. Run candidates through the pipeline (strong, weak, edge cases)
  3. Complete voice screenings with AI scoring
  4. Verify status transitions and data integrity
"""

import json
import pytest
from moto import mock_aws
from tests.conftest import api_event

# ── Screening questions based on the Sweeney incident ──
SWEENEY_SCREENING_QUESTIONS = [
    "The Sydney Sweeney American Eagle ad generated billions of impressions but also backlash driven by AI bot amplification on TikTok. How would you distinguish organic outrage from manufactured controversy in the first 24 hours?",
    "When Trump and Vance publicly endorsed the ad, it became a political lightning rod. Walk us through your response playbook — do you lean in, stay silent, or pivot? What factors drive that decision?",
    "American Eagle's stock soared then dipped, foot traffic reports conflicted, and Sweeney later said negative coverage was fabricated. How do you establish a single source of truth for leadership during a crisis like this?",
    "Competitors Gap, Lucky Brand, and Levi's (with Beyonce) all launched rival denim campaigns within days. How would you protect brand share of voice when competitors are drafting off your viral moment?",
    "Sweeney stayed silent for months and later said she regretted it. If you were advising the talent, what would your 48-hour communication plan look like?",
]


@mock_aws
class TestSweeneyJeansScenario:
    """End-to-end pipeline test using the Sydney Sweeney jeans crisis as context."""

    def _create_table(self, dynamodb_table):
        """Table is created by the fixture."""
        pass

    # ── 1. Job creation ──

    def test_create_crisis_manager_job(self, dynamodb_table):
        from src.handlers.jobs import create

        event = api_event("POST", "/jobs", body={
            "title": "Social Media Crisis Manager — Denim & Fashion",
            "location": "New York, NY (Remote OK)",
            "department": "Brand Marketing",
            "description": (
                "Lead crisis response for viral social media moments. "
                "This role was created after the Sydney Sweeney x American Eagle "
                "'Great Jeans' campaign generated billions of impressions, political "
                "commentary from the White House, AI-driven TikTok bot amplification, "
                "and competing denim launches from Gap, Levi's, and Lucky Brand. "
                "You will own the playbook for turning controversy into brand equity."
            ),
            "requirements": (
                "5+ years social media crisis management. "
                "Experience with bot/AI detection tools (Cyabra, Graphika). "
                "Track record navigating politically charged brand moments. "
                "Fashion/retail industry experience preferred."
            ),
            "status": "open",
            "salary_min": 130000,
            "salary_max": 185000,
            "screening_questions": SWEENEY_SCREENING_QUESTIONS,
        })
        response = create(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 201
        assert body["title"] == "Social Media Crisis Manager — Denim & Fashion"
        assert body["status"] == "open"
        assert body["salary_min"] == 130000
        assert len(body["screening_questions"]) == 5
        assert "AI bot amplification" in body["screening_questions"][0]
        return body["job_id"]

    # ── 2. Candidate creation — strong candidate ──

    def test_strong_candidate_experienced_crisis_lead(self, dynamodb_table):
        from src.handlers.candidates import create

        event = api_event("POST", "/candidates", body={
            "first_name": "Maya",
            "last_name": "Torres",
            "email": "maya.torres@example.com",
            "phone": "+12125551001",
            "location": "New York, NY",
            "source": "linkedin",
            "job_id": "sweeney-crisis-job",
            "notes": (
                "8 years crisis comms at major fashion brands. "
                "Led response during a viral TikTok boycott campaign (2023). "
                "Familiar with Cyabra bot detection. "
                "Published case study on navigating politically charged brand moments."
            ),
        })
        response = create(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 201
        assert body["first_name"] == "Maya"
        assert body["source"] == "linkedin"
        assert body["status"] == "new"

    # ── 3. Candidate creation — weak candidate ──

    def test_weak_candidate_no_crisis_experience(self, dynamodb_table):
        from src.handlers.candidates import create

        event = api_event("POST", "/candidates", body={
            "first_name": "Derek",
            "last_name": "Hanson",
            "email": "derek.h@example.com",
            "phone": "+13105551002",
            "location": "Los Angeles, CA",
            "source": "indeed",
            "job_id": "sweeney-crisis-job",
            "notes": (
                "2 years social media coordinator at a local boutique. "
                "No crisis management experience. "
                "Managed organic Instagram content only."
            ),
        })
        response = create(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 201
        assert body["first_name"] == "Derek"
        assert body["status"] == "new"

    # ── 4. Screening — strong candidate passes ──

    def test_screening_strong_candidate_passes(self, dynamodb_table):
        from src.handlers.candidates import create as create_candidate
        from src.handlers.screenings import schedule, complete

        # Create candidate first
        cand_event = api_event("POST", "/candidates", body={
            "first_name": "Maya",
            "last_name": "Torres",
            "email": "maya.torres@example.com",
            "phone": "+12125551001",
            "source": "linkedin",
            "job_id": "sweeney-crisis-job",
        })
        cand_resp = create_candidate(cand_event, None)
        cand_id = json.loads(cand_resp["body"])["candidate_id"]

        # Schedule screening
        sched_event = api_event("POST", "/screenings", body={
            "candidate_id": cand_id,
            "job_id": "sweeney-crisis-job",
            "scheduled_at": "2025-09-15T14:00:00Z",
        })
        sched_resp = schedule(sched_event, None)
        assert sched_resp["statusCode"] == 201
        screening_id = json.loads(sched_resp["body"])["screening_id"]

        # Complete screening — strong performance
        complete_event = api_event(
            "POST",
            f"/screenings/{cand_id}/{screening_id}/complete",
            path_params={"candidate_id": cand_id, "screening_id": screening_id},
            body={
                "result": "pass",
                "ai_score": 92,
                "duration_seconds": 487,
                "questions_asked": SWEENEY_SCREENING_QUESTIONS[:3],
                "responses": [
                    "In the first 24 hours I'd run the social listening data through Cyabra "
                    "to flag bot clusters. With the Sweeney campaign, Cyabra found fake TikTok "
                    "profiles driving the initial outrage. I'd brief leadership with a bot-vs-organic "
                    "breakdown within 6 hours, and hold any public response until we have signal clarity.",

                    "When Trump endorsed the ad, the calculus changed — you can't un-ring that bell. "
                    "I'd recommend strategic silence from the brand while the political cycle runs, "
                    "let Sweeney's team handle talent-side messaging, and prepare a pivot campaign "
                    "that re-centers the product. The worst move is engaging the political angle directly.",

                    "I'd set up a war room dashboard — Brandwatch for sentiment, Google Analytics for "
                    "real traffic vs. reported traffic, and a direct line to store ops for foot traffic "
                    "actuals. Sweeney later said the negative foot traffic reports were fabricated. "
                    "You need internal ground truth before the media narrative calcifies.",
                ],
                "ai_summary": (
                    "Exceptional candidate. Deep expertise in bot detection (Cyabra), "
                    "political crisis navigation, and real-time brand monitoring. "
                    "Demonstrated clear frameworks for the Sweeney-specific scenario. "
                    "Recommended: advance to final round."
                ),
            },
        )
        complete_resp = complete(complete_event, None)
        body = json.loads(complete_resp["body"])

        assert complete_resp["statusCode"] == 200
        assert body["result"] == "pass"
        assert body["ai_score"] == 92
        assert body["duration_seconds"] == 487
        assert len(body["responses"]) == 3
        assert "Cyabra" in body["responses"][0]

    # ── 5. Screening — weak candidate fails ──

    def test_screening_weak_candidate_fails(self, dynamodb_table):
        from src.handlers.candidates import create as create_candidate
        from src.handlers.screenings import schedule, complete

        # Create candidate
        cand_event = api_event("POST", "/candidates", body={
            "first_name": "Derek",
            "last_name": "Hanson",
            "email": "derek.h@example.com",
            "phone": "+13105551002",
            "source": "indeed",
            "job_id": "sweeney-crisis-job",
        })
        cand_resp = create_candidate(cand_event, None)
        cand_id = json.loads(cand_resp["body"])["candidate_id"]

        # Schedule + complete screening — weak performance
        sched_event = api_event("POST", "/screenings", body={
            "candidate_id": cand_id,
            "job_id": "sweeney-crisis-job",
        })
        sched_resp = schedule(sched_event, None)
        screening_id = json.loads(sched_resp["body"])["screening_id"]

        complete_event = api_event(
            "POST",
            f"/screenings/{cand_id}/{screening_id}/complete",
            path_params={"candidate_id": cand_id, "screening_id": screening_id},
            body={
                "result": "fail",
                "ai_score": 31,
                "duration_seconds": 298,
                "questions_asked": SWEENEY_SCREENING_QUESTIONS[:3],
                "responses": [
                    "I would just check if the comments are negative or positive "
                    "and report that to my manager.",

                    "I think the brand should have just deleted the ad and apologized. "
                    "Controversy is always bad for business.",

                    "I'd check our social media analytics dashboard, "
                    "I'm not sure what else you'd need.",
                ],
                "ai_summary": (
                    "Candidate lacks crisis management depth. No familiarity with "
                    "bot detection tools, no framework for political brand moments, "
                    "and suggested deleting content — which would amplify the Streisand "
                    "effect. Not recommended for this role."
                ),
            },
        )
        complete_resp = complete(complete_event, None)
        body = json.loads(complete_resp["body"])

        assert complete_resp["statusCode"] == 200
        assert body["result"] == "fail"
        assert body["ai_score"] == 31
        assert body["duration_seconds"] == 298

    # ── 6. Edge case: missing required fields ──

    def test_create_candidate_missing_name(self, dynamodb_table):
        from src.handlers.candidates import create

        event = api_event("POST", "/candidates", body={
            "email": "nobody@example.com",
        })
        response = create(event, None)
        assert response["statusCode"] == 400
        assert "required" in json.loads(response["body"])["error"]

    # ── 7. Edge case: invalid status transition ──

    def test_invalid_status_value(self, dynamodb_table):
        from src.handlers.candidates import update_status

        event = api_event(
            "PATCH", "/candidates/fake-id/status",
            path_params={"id": "fake-id"},
            body={"status": "viral_meltdown"},
        )
        response = update_status(event, None)
        assert response["statusCode"] == 400
        assert "Invalid status" in json.loads(response["body"])["error"]

    # ── 8. Screening questions round-trip through DynamoDB ──

    def test_screening_questions_persist_in_job(self, dynamodb_table):
        from src.handlers.jobs import create, get

        event = api_event("POST", "/jobs", body={
            "title": "Crisis Manager — Sweeney Response",
            "status": "open",
            "screening_questions": SWEENEY_SCREENING_QUESTIONS,
        })
        resp = create(event, None)
        job_id = json.loads(resp["body"])["job_id"]

        get_event = api_event("GET", f"/jobs/{job_id}", path_params={"id": job_id})
        get_resp = get(get_event, None)
        body = json.loads(get_resp["body"])

        assert get_resp["statusCode"] == 200
        assert len(body["screening_questions"]) == 5
        assert "Sydney Sweeney" in body["screening_questions"][0]
        assert "Trump and Vance" in body["screening_questions"][1]
        assert "Gap, Lucky Brand" in body["screening_questions"][3]
        assert "Sweeney stayed silent" in body["screening_questions"][4]
