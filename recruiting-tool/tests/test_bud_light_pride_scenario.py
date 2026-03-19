"""
Integration tests: Bud Light x Dylan Mulvaney Pride Incident (2023)

Scenario: Anheuser-Busch is hiring a VP of Brand Risk & Crisis Strategy
after the Bud Light / Dylan Mulvaney partnership triggered the largest
consumer boycott in recent history. Key facts:
  - April 2023: Mulvaney posted a sponsored Instagram ad with a custom
    Bud Light can featuring her face, celebrating her "365 days of girlhood"
  - Kid Rock shot cases of Bud Light with an MP5, video got 11M+ views
  - 800K+ social mentions in one week (more than all of Q1 2023)
  - Sales dropped 28.4% by mid-May, eventually costing $1.4B in revenue
  - Bud Light lost its #1 US beer position to Modelo Especial
  - VP Marketing Alissa Heinerscheid and exec Daniel Blake took leave
  - AB InBev's "middle ground" response alienated both sides
  - Mulvaney said Bud Light never reached out to support her
  - 500 independent distributors affected
  - Brand still hasn't fully recovered as of 2025

These tests simulate recruiting for the executive who would prevent
the next crisis — or at least manage it without losing $1.4 billion.
"""

import json
import pytest
from moto import mock_aws
from tests.conftest import api_event


BUD_LIGHT_SCREENING_QUESTIONS = [
    "Bud Light's partnership with Dylan Mulvaney cost $1.4 billion in lost sales and the #1 beer position in America. With hindsight, walk us through the risk assessment framework you would have applied before greenlighting this campaign.",
    "AB InBev took a 'middle ground' approach — they didn't defend the partnership or distance from it. This alienated both conservatives and LGBTQ+ advocates. What decisive action would you have recommended in the first 72 hours?",
    "Kid Rock's video of shooting Bud Light cases got 11 million views and catalyzed the boycott. How do you handle a high-profile detractor whose content is going mega-viral and inspiring consumer action?",
    "Dylan Mulvaney said Bud Light never reached out to support her during the backlash. She was receiving threats and was afraid to leave her house. How do you balance brand damage control with duty of care to the talent you partnered with?",
    "The boycott enabled Bud Light drinkers to discover Modelo, and most never came back. Marketing professor Ernan Haruvy called this a permanent switching event. How would you design a win-back campaign for lapsed loyalists?",
]


@mock_aws
class TestBudLightPrideScenario:
    """End-to-end pipeline test using the Bud Light / Mulvaney crisis."""

    # ── 1. Job creation ──

    def test_create_vp_brand_risk_job(self, dynamodb_table):
        from src.handlers.jobs import create

        event = api_event("POST", "/jobs", body={
            "title": "VP Brand Risk & Crisis Strategy",
            "location": "New York, NY",
            "department": "Global Marketing Leadership",
            "description": (
                "Newly created role reporting to the CMO. Following the Bud Light / "
                "Dylan Mulvaney crisis that resulted in $1.4B lost revenue, loss of "
                "the #1 US beer position to Modelo, and executive departures, this "
                "role will build the enterprise crisis playbook from scratch. "
                "You will own pre-campaign risk scoring, real-time response protocols, "
                "talent duty-of-care frameworks, and distributor communication strategy."
            ),
            "requirements": (
                "10+ years brand management at a Fortune 500 CPG company. "
                "Direct experience managing a consumer boycott or activist campaign. "
                "Proven track record rebuilding brand equity post-crisis. "
                "Experience with distributor/franchise networks. "
                "Ability to brief the C-suite and board under pressure."
            ),
            "status": "open",
            "salary_min": 250000,
            "salary_max": 350000,
            "screening_questions": BUD_LIGHT_SCREENING_QUESTIONS,
        })
        response = create(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 201
        assert body["title"] == "VP Brand Risk & Crisis Strategy"
        assert body["salary_min"] == 250000
        assert body["salary_max"] == 350000
        assert len(body["screening_questions"]) == 5
        assert "$1.4 billion" in body["screening_questions"][0]

    # ── 2. Strong candidate — seasoned crisis executive ──

    def test_strong_candidate_crisis_executive(self, dynamodb_table):
        from src.handlers.candidates import create

        event = api_event("POST", "/candidates", body={
            "first_name": "Rachel",
            "last_name": "Whitfield",
            "email": "r.whitfield@example.com",
            "phone": "+12125559001",
            "location": "Chicago, IL",
            "source": "executive_search",
            "job_id": "bud-light-crisis-job",
            "notes": (
                "Former VP Crisis Communications at PepsiCo. Managed the Kendall Jenner "
                "protest ad crisis (2017). 12 years CPG brand management. "
                "Published HBR article on post-boycott brand recovery. "
                "Board advisory experience with 3 Fortune 500 companies."
            ),
        })
        response = create(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 201
        assert body["first_name"] == "Rachel"
        assert body["source"] == "executive_search"

    # ── 3. Moderate candidate — needs review ──

    def test_moderate_candidate_for_review(self, dynamodb_table):
        from src.handlers.candidates import create

        event = api_event("POST", "/candidates", body={
            "first_name": "Jason",
            "last_name": "Park",
            "email": "jason.park@example.com",
            "phone": "+14155559002",
            "location": "San Francisco, CA",
            "source": "referral",
            "job_id": "bud-light-crisis-job",
            "notes": (
                "7 years brand marketing at tech companies (Salesforce, Stripe). "
                "No CPG experience but strong on social media analytics. "
                "Led a successful brand repositioning after a data breach. "
                "No distributor network experience."
            ),
        })
        response = create(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 201
        assert body["first_name"] == "Jason"

    # ── 4. Screening — strong candidate passes with high score ──

    def test_screening_crisis_exec_passes(self, dynamodb_table):
        from src.handlers.candidates import create as create_candidate
        from src.handlers.screenings import schedule, complete

        # Create candidate
        cand_resp = create_candidate(api_event("POST", "/candidates", body={
            "first_name": "Rachel",
            "last_name": "Whitfield",
            "email": "r.whitfield@example.com",
            "phone": "+12125559001",
            "source": "executive_search",
            "job_id": "bud-light-crisis-job",
        }), None)
        cand_id = json.loads(cand_resp["body"])["candidate_id"]

        # Schedule
        sched_resp = schedule(api_event("POST", "/screenings", body={
            "candidate_id": cand_id,
            "job_id": "bud-light-crisis-job",
            "scheduled_at": "2025-10-01T10:00:00Z",
        }), None)
        assert sched_resp["statusCode"] == 201
        screening_id = json.loads(sched_resp["body"])["screening_id"]

        # Complete — excellent responses
        complete_resp = complete(api_event(
            "POST",
            f"/screenings/{cand_id}/{screening_id}/complete",
            path_params={"candidate_id": cand_id, "screening_id": screening_id},
            body={
                "result": "pass",
                "ai_score": 95,
                "duration_seconds": 612,
                "questions_asked": BUD_LIGHT_SCREENING_QUESTIONS,
                "responses": [
                    "The risk framework should have flagged three things: the talent's audience "
                    "overlap with Bud Light's core demo was near zero, the cultural moment around "
                    "trans rights was at peak polarization, and AB InBev had no rapid-response "
                    "playbook in place. I use a 4-quadrant risk matrix — audience alignment, "
                    "cultural temperature, brand permission, and response readiness. This campaign "
                    "would have scored red on three of four quadrants.",

                    "In the first 72 hours you have to pick a lane. I would have recommended a "
                    "full-throated defense of the partnership — 'We sent a personalized can to "
                    "celebrate a customer's milestone, as we do for thousands of customers.' "
                    "Frame it as customer appreciation, not political statement. The middle ground "
                    "is the worst place to be — you lose both sides.",

                    "You can't out-shout Kid Rock. The play is to flood the zone with positive "
                    "brand association — activate your sports sponsorships, your distributor "
                    "relationships, your bar partnerships. Make the counter-narrative visual and "
                    "emotional. And privately, reach out to Kid Rock's management — sometimes a "
                    "direct conversation de-escalates faster than a public fight.",

                    "Duty of care is non-negotiable. Within 24 hours of the backlash I would have "
                    "called Mulvaney directly, offered security resources, PR support, and a public "
                    "statement of support. The fact that she said they never reached out is the "
                    "single most damaging detail — it tells every future partner that you'll "
                    "abandon them under fire.",

                    "The switching problem is structural, not emotional. Drinkers discovered "
                    "Modelo and found they liked it. A win-back campaign can't just be 'remember "
                    "us' — it needs a product hook. Limited editions, local brewery collabs, "
                    "a loyalty program with real rewards. And you need the distributor network "
                    "activated — they're your ground game. 500 distributors pushing sampling "
                    "events is more powerful than any Super Bowl ad.",
                ],
                "ai_summary": (
                    "Outstanding candidate. Demonstrated a concrete risk framework (4-quadrant "
                    "model), advocated for decisive early action vs. middle-ground paralysis, "
                    "showed empathy for talent duty-of-care, and proposed a structural win-back "
                    "strategy. Direct experience with the Pepsi/Jenner crisis is highly relevant. "
                    "Strong recommendation to advance."
                ),
            },
        ), None)
        body = json.loads(complete_resp["body"])

        assert complete_resp["statusCode"] == 200
        assert body["result"] == "pass"
        assert body["ai_score"] == 95
        assert body["duration_seconds"] == 612
        assert len(body["responses"]) == 5
        assert "$1.4 billion" not in body["responses"][0]  # candidate should give analysis, not parrot the question
        assert "duty of care" in body["responses"][3].lower()

    # ── 5. Screening — moderate candidate gets review flag ──

    def test_screening_moderate_candidate_review(self, dynamodb_table):
        from src.handlers.candidates import create as create_candidate
        from src.handlers.screenings import schedule, complete

        cand_resp = create_candidate(api_event("POST", "/candidates", body={
            "first_name": "Jason",
            "last_name": "Park",
            "email": "jason.park@example.com",
            "phone": "+14155559002",
            "source": "referral",
            "job_id": "bud-light-crisis-job",
        }), None)
        cand_id = json.loads(cand_resp["body"])["candidate_id"]

        sched_resp = schedule(api_event("POST", "/screenings", body={
            "candidate_id": cand_id,
            "job_id": "bud-light-crisis-job",
        }), None)
        screening_id = json.loads(sched_resp["body"])["screening_id"]

        complete_resp = complete(api_event(
            "POST",
            f"/screenings/{cand_id}/{screening_id}/complete",
            path_params={"candidate_id": cand_id, "screening_id": screening_id},
            body={
                "result": "review",
                "ai_score": 62,
                "duration_seconds": 445,
                "questions_asked": BUD_LIGHT_SCREENING_QUESTIONS[:3],
                "responses": [
                    "I think the main issue was they didn't do enough market research before "
                    "the campaign. A/B testing with focus groups would have caught the risk. "
                    "I'd recommend always running campaigns through a diverse focus group first.",

                    "I would have issued a statement within 24 hours saying we respect all "
                    "viewpoints and that the partnership was about celebration, not politics. "
                    "Keep it neutral and factual.",

                    "For the Kid Rock situation, I'd monitor the social metrics and prepare "
                    "a response only if the sentiment stays negative for more than a week. "
                    "Sometimes these things blow over on their own.",
                ],
                "ai_summary": (
                    "Candidate shows decent instincts but lacks CPG-specific and boycott "
                    "management experience. Focus group suggestion is reasonable but wouldn't "
                    "have caught the velocity of the backlash. 'Wait and see' approach to "
                    "Kid Rock is too passive for a $1.4B crisis. No mention of distributor "
                    "impact or talent duty-of-care. Recommend: additional interview with "
                    "hiring manager to probe further."
                ),
            },
        ), None)
        body = json.loads(complete_resp["body"])

        assert complete_resp["statusCode"] == 200
        assert body["result"] == "review"
        assert body["ai_score"] == 62
        assert 400 <= body["duration_seconds"] <= 500

    # ── 6. Full pipeline — schedule then verify status transition ──

    def test_candidate_status_transitions(self, dynamodb_table):
        from src.handlers.candidates import create as create_candidate, get as get_candidate
        from src.handlers.screenings import schedule

        # Create
        cand_resp = create_candidate(api_event("POST", "/candidates", body={
            "first_name": "Test",
            "last_name": "Pipeline",
            "email": "test@example.com",
            "phone": "+10005551234",
            "source": "test",
            "job_id": "bud-light-crisis-job",
        }), None)
        cand_id = json.loads(cand_resp["body"])["candidate_id"]

        # Verify initial status
        get_resp = get_candidate(api_event(
            "GET", f"/candidates/{cand_id}",
            path_params={"id": cand_id},
        ), None)
        assert json.loads(get_resp["body"])["status"] == "new"

        # Schedule screening — should transition to screening_scheduled
        schedule(api_event("POST", "/screenings", body={
            "candidate_id": cand_id,
            "job_id": "bud-light-crisis-job",
        }), None)

        get_resp2 = get_candidate(api_event(
            "GET", f"/candidates/{cand_id}",
            path_params={"id": cand_id},
        ), None)
        assert json.loads(get_resp2["body"])["status"] == "screening_scheduled"

    # ── 7. Screening questions round-trip ──

    def test_bud_light_questions_persist(self, dynamodb_table):
        from src.handlers.jobs import create, get

        resp = create(api_event("POST", "/jobs", body={
            "title": "VP Brand Risk — Bud Light Recovery",
            "status": "open",
            "screening_questions": BUD_LIGHT_SCREENING_QUESTIONS,
        }), None)
        job_id = json.loads(resp["body"])["job_id"]

        get_resp = get(api_event("GET", f"/jobs/{job_id}", path_params={"id": job_id}), None)
        body = json.loads(get_resp["body"])

        assert len(body["screening_questions"]) == 5
        assert "Kid Rock" in body["screening_questions"][2]
        assert "Dylan Mulvaney" in body["screening_questions"][3]
        assert "Modelo" in body["screening_questions"][4]

    # ── 8. Job not found ──

    def test_get_nonexistent_job(self, dynamodb_table):
        from src.handlers.jobs import get

        resp = get(api_event("GET", "/jobs/fake", path_params={"id": "nonexistent-job"}), None)
        assert resp["statusCode"] == 404

    # ── 9. Screening not found ──

    def test_complete_nonexistent_screening(self, dynamodb_table):
        from src.handlers.screenings import complete

        resp = complete(api_event(
            "POST", "/screenings/fake/fake/complete",
            path_params={"candidate_id": "fake", "screening_id": "fake"},
            body={"result": "pass", "ai_score": 99},
        ), None)
        assert resp["statusCode"] == 404

    # ── 10. Validate screening with missing fields ──

    def test_schedule_screening_missing_fields(self, dynamodb_table):
        from src.handlers.screenings import schedule

        resp = schedule(api_event("POST", "/screenings", body={
            "candidate_id": "some-id",
            # missing job_id
        }), None)
        assert resp["statusCode"] == 400
        assert "required" in json.loads(resp["body"])["error"]
