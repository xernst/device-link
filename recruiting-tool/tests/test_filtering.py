"""Tests for candidate filtering and matching service."""

import json
import pytest
from moto import mock_aws

from src.services.filtering import (
    score_candidate,
    filter_candidates,
    match_jobs_to_candidate,
    generate_prescreen_questions,
    ROLE_PROFILES,
    SEARCH_PRESETS,
)
from src.services.scraper import extract_skills


# ---- extract_skills tests ----

class TestExtractSkills:
    def test_extracts_technical_skills(self):
        text = "Proficient in Python, JavaScript, and AWS. Experience with Docker and Kubernetes."
        skills = extract_skills(text)
        assert "python" in skills
        assert "javascript" in skills
        assert "aws" in skills
        assert "docker" in skills
        assert "kubernetes" in skills

    def test_extracts_pr_skills(self):
        text = "10 years in crisis management and public relations. Expert in brand management and media relations."
        skills = extract_skills(text)
        assert "crisis management" in skills
        assert "public relations" in skills
        assert "brand management" in skills
        assert "media relations" in skills

    def test_extracts_salon_skills(self):
        text = "Licensed cosmetology professional with hair styling and color specialist certifications. Strong customer service."
        skills = extract_skills(text)
        assert "cosmetology" in skills
        assert "hair styling" in skills
        assert "color specialist" in skills
        assert "customer service" in skills

    def test_empty_text_returns_empty(self):
        assert extract_skills("") == []
        assert extract_skills(None) == []

    def test_no_duplicates(self):
        text = "Python python PYTHON developer with Python experience"
        skills = extract_skills(text)
        assert skills.count("python") == 1


# ---- score_candidate tests ----

class TestScoreCandidate:
    def test_perfect_cert_match(self):
        candidate = {
            "certifications": ["cosmetology", "color_specialist"],
            "location": "Naples, FL",
            "years_experience": 5,
        }
        job = {
            "required_certifications": ["cosmetology"],
            "preferred_certifications": ["color_specialist"],
            "location": "Naples, FL",
            "role_category": "spa",
        }
        result = score_candidate(candidate, job)
        assert result["total_score"] >= 75
        assert result["qualified"] is True
        assert result["matched_certifications"] == ["cosmetology", "color_specialist"]
        assert result["missing_certifications"] == []

    def test_cert_gating_hard_disqualification(self):
        """Missing required cert = disqualified regardless of other scores."""
        candidate = {
            "certifications": [],
            "location": "Naples, FL",
            "years_experience": 10,
            "availability": {"monday": ["morning", "afternoon", "evening"]},
        }
        job = {
            "required_certifications": ["cosmetology"],
            "location": "Naples, FL",
            "role_category": "spa",
            "shift_schedule": ["morning"],
        }
        result = score_candidate(candidate, job)
        assert result["qualified"] is False
        assert result["recommendation"] == "disqualified"
        assert len(result["disqualification_reasons"]) == 1
        assert "cosmetology" in result["disqualification_reasons"][0]
        assert result["total_score"] == 0

    def test_missing_required_cert_with_good_other_scores(self):
        """Cert gating overrides even a perfect availability + experience score."""
        candidate = {
            "certifications": ["massage_therapy"],  # has this, not the required one
            "location": "Naples, FL",
            "years_experience": 8,
            "availability": {"monday": ["morning"], "tuesday": ["afternoon"]},
        }
        job = {
            "required_certifications": ["cosmetology"],
            "location": "Naples, FL",
            "role_category": "spa",
            "shift_schedule": ["morning"],
        }
        result = score_candidate(candidate, job)
        assert result["qualified"] is False
        assert result["recommendation"] == "disqualified"

    def test_no_cert_required_passes(self):
        """Management role — no cert required — should not be disqualified."""
        candidate = {
            "certifications": [],
            "location": "Naples, FL",
            "years_experience": 7,
        }
        job = {
            "required_certifications": [],
            "location": "Naples, FL",
            "role_category": "management",
        }
        result = score_candidate(candidate, job)
        assert result["qualified"] is True
        assert result["recommendation"] != "disqualified"

    def test_availability_full_overlap(self):
        candidate = {
            "availability": {"monday": ["morning", "afternoon"], "tuesday": ["evening"]},
        }
        job = {
            "shift_schedule": ["morning", "afternoon"],
        }
        result = score_candidate(candidate, job)
        assert result["breakdown"]["availability"] == 100
        assert set(result["availability_overlap"]) == {"morning", "afternoon"}
        assert result["availability_gaps"] == []

    def test_availability_partial_overlap(self):
        candidate = {
            "availability": {"monday": ["morning"]},
        }
        job = {
            "shift_schedule": ["morning", "evening", "weekend"],
        }
        result = score_candidate(candidate, job)
        assert 0 < result["breakdown"]["availability"] < 100
        assert "morning" in result["availability_overlap"]
        assert "evening" in result["availability_gaps"]

    def test_availability_no_candidate_data(self):
        """No availability data → neutral score, not a hard fail."""
        candidate = {}
        job = {"shift_schedule": ["morning", "evening"]}
        result = score_candidate(candidate, job)
        assert result["breakdown"]["availability"] == 50

    def test_role_specific_weights_spa(self):
        """Spa role: certs weigh 40%, availability 25%, experience 20%, location 15%."""
        profile = ROLE_PROFILES["spa"]
        assert profile["weights"]["certifications"] == 0.40
        assert profile["weights"]["availability"] == 0.25
        assert profile["cert_required"] is True

    def test_role_specific_weights_management(self):
        profile = ROLE_PROFILES["management"]
        assert profile["weights"]["experience"] == 0.40
        assert profile["cert_required"] is False

    def test_role_specific_weights_biosecurity(self):
        profile = ROLE_PROFILES["biosecurity"]
        assert profile["weights"]["availability"] == 0.35
        assert profile["cert_required"] is True

    def test_role_specific_weights_guest_services(self):
        profile = ROLE_PROFILES["guest_services"]
        assert profile["weights"]["availability"] == 0.35
        assert profile["cert_required"] is False

    def test_recommendation_suggest_interview(self):
        candidate = {
            "certifications": ["cosmetology"],
            "location": "Naples, FL",
            "years_experience": 6,
            "availability": {"monday": ["morning", "afternoon"], "tuesday": ["morning"]},
        }
        job = {
            "required_certifications": ["cosmetology"],
            "location": "Naples, FL",
            "shift_schedule": ["morning"],
            "role_category": "spa",
        }
        result = score_candidate(candidate, job)
        assert result["recommendation"] == "suggest_interview"
        assert result["total_score"] >= 75

    def test_recommendation_flag_review(self):
        """Meets cert requirement but has availability gaps → flag_review."""
        candidate = {
            "certifications": ["cosmetology"],
            "location": "Naples, FL",
            "years_experience": 1,
            "availability": {"monday": ["morning"]},
        }
        job = {
            "required_certifications": ["cosmetology"],
            "preferred_certifications": ["color_specialist", "nail_technician"],
            "location": "Miami, FL",  # different city, same state
            "shift_schedule": ["morning", "afternoon", "evening"],
            "role_category": "spa",
        }
        result = score_candidate(candidate, job)
        assert result["qualified"] is True
        assert result["recommendation"] in ("flag_review", "needs_info")

    def test_location_match_same_city(self):
        candidate = {"location": "Austin, TX"}
        job = {"location": "Austin, TX"}
        result = score_candidate(candidate, job)
        assert result["breakdown"]["location"] == 100

    def test_location_partial_match(self):
        candidate = {"location": "Dallas, TX"}
        job = {"location": "Houston, TX"}
        result = score_candidate(candidate, job)
        assert result["breakdown"]["location"] == 75

    def test_remote_location_scores_well(self):
        candidate = {"location": "Remote"}
        job = {"location": "San Francisco, CA"}
        result = score_candidate(candidate, job)
        assert result["breakdown"]["location"] >= 70

    def test_experience_years_match(self):
        candidate = {"years_experience": 7}
        job = {"requirements": "Requires 5+ years experience.", "description": ""}
        result = score_candidate(candidate, job)
        assert result["breakdown"]["experience"] == 100

    def test_experience_years_explicit_field(self):
        """Explicit years_experience field takes priority over text parsing."""
        candidate = {"years_experience": 2, "notes": "8 years experience in everything"}
        job = {"requirements": "10+ years experience.", "description": ""}
        result = score_candidate(candidate, job)
        assert result["breakdown"]["experience"] < 50

    def test_experience_years_insufficient(self):
        candidate = {"notes": "2 years of experience in marketing."}
        job = {"requirements": "Requires 10+ years experience.", "description": ""}
        result = score_candidate(candidate, job)
        assert result["breakdown"]["experience"] < 50

    def test_seniority_match(self):
        candidate = {"notes": "Senior marketing manager with leadership experience."}
        job = {"requirements": "Looking for a senior brand strategist.", "description": ""}
        result = score_candidate(candidate, job)
        assert result["breakdown"]["experience"] == 100

    def test_backwards_compat_matched_skills(self):
        """Legacy matched_skills field still present in output."""
        result = score_candidate({}, {})
        assert "matched_skills" in result
        assert "missing_skills" in result

    def test_empty_candidate_and_job(self):
        result = score_candidate({}, {})
        assert result["total_score"] == 50
        assert result["qualified"] is True


# ---- filter_candidates tests ----

class TestFilterCandidates:
    def test_ranks_by_score_descending(self):
        candidates = [
            {
                "candidate_id": "1", "first_name": "Low", "last_name": "Match",
                "certifications": [], "availability": {},
            },
            {
                "candidate_id": "2", "first_name": "High", "last_name": "Match",
                "certifications": ["cosmetology"],
                "availability": {"monday": ["morning", "afternoon"]},
                "years_experience": 5,
                "location": "Naples, FL",
            },
        ]
        job = {
            "required_certifications": ["cosmetology"],
            "shift_schedule": ["morning"],
            "location": "Naples, FL",
            "role_category": "spa",
        }
        results = filter_candidates(candidates, job)
        assert results[0]["candidate_id"] == "2"
        assert results[0]["total_score"] >= results[1]["total_score"]

    def test_disqualified_sorted_to_bottom(self):
        """Disqualified candidates (missing required cert) appear after qualified ones."""
        candidates = [
            {
                "candidate_id": "qualified", "first_name": "Q", "last_name": "One",
                "certifications": ["cosmetology"],
                "availability": {},
                "location": "Naples, FL",
            },
            {
                "candidate_id": "disqualified", "first_name": "D", "last_name": "Two",
                "certifications": [],
                "years_experience": 20,
                "availability": {"monday": ["morning"]},
                "location": "Naples, FL",
            },
        ]
        job = {
            "required_certifications": ["cosmetology"],
            "role_category": "spa",
        }
        results = filter_candidates(candidates, job)
        qualified_ids = [r["candidate_id"] for r in results if r["qualified"]]
        disqualified_ids = [r["candidate_id"] for r in results if not r["qualified"]]
        # All qualified before all disqualified
        assert qualified_ids == ["qualified"]
        assert disqualified_ids == ["disqualified"]
        qual_index = next(i for i, r in enumerate(results) if r["candidate_id"] == "qualified")
        disq_index = next(i for i, r in enumerate(results) if r["candidate_id"] == "disqualified")
        assert qual_index < disq_index

    def test_min_score_filter(self):
        candidates = [
            {"candidate_id": "1", "first_name": "A", "last_name": "B", "certifications": []},
            {
                "candidate_id": "2", "first_name": "C", "last_name": "D",
                "certifications": ["cosmetology"],
                "location": "Naples, FL",
                "years_experience": 5,
            },
        ]
        job = {
            "required_certifications": ["cosmetology"],
            "location": "Naples, FL",
            "role_category": "spa",
        }
        results = filter_candidates(candidates, job, min_score=60)
        qualified_results = [r for r in results if r["qualified"]]
        assert all(r["total_score"] >= 60 for r in qualified_results)

    def test_empty_candidates(self):
        results = filter_candidates([], {"required_certifications": ["cosmetology"]})
        assert results == []


# ---- match_jobs_to_candidate tests ----

class TestMatchJobsToCandidate:
    def test_matches_best_jobs(self):
        candidate = {
            "certifications": ["massage_therapy"],
            "location": "Naples, FL",
            "years_experience": 5,
        }
        jobs = [
            {
                "job_id": "1", "title": "Massage Therapist",
                "required_certifications": ["massage_therapy"],
                "location": "Naples, FL",
                "role_category": "spa",
            },
            {
                "job_id": "2", "title": "Spa Manager",
                "required_certifications": [],
                "location": "Miami, FL",
                "role_category": "management",
            },
        ]
        results = match_jobs_to_candidate(candidate, jobs)
        assert results[0]["job_id"] == "1"


# ---- generate_prescreen_questions tests ----

class TestGeneratePrescreenQuestions:
    def test_cert_questions_generated(self):
        job = {"required_certifications": ["cosmetology", "nail_technician"]}
        questions = generate_prescreen_questions(job)
        assert any("cosmetology" in q for q in questions)
        assert any("nail_technician" in q for q in questions)

    def test_preferred_cert_questions_generated(self):
        job = {"preferred_certifications": ["color_specialist"]}
        questions = generate_prescreen_questions(job)
        assert any("color_specialist" in q for q in questions)
        assert any("preferred" in q.lower() for q in questions)

    def test_shift_availability_question(self):
        job = {"shift_schedule": ["morning", "evening", "weekend"]}
        questions = generate_prescreen_questions(job)
        assert any("morning" in q and "evening" in q for q in questions)

    def test_spa_role_question(self):
        job = {"role_category": "spa"}
        questions = generate_prescreen_questions(job)
        assert any("spa" in q.lower() or "salon" in q.lower() for q in questions)

    def test_management_role_questions(self):
        job = {"role_category": "management"}
        questions = generate_prescreen_questions(job)
        assert any("management" in q.lower() for q in questions)

    def test_biosecurity_role_questions(self):
        job = {"role_category": "biosecurity"}
        questions = generate_prescreen_questions(job)
        assert any("biosecurity" in q.lower() or "health" in q.lower() or "short notice" in q.lower() for q in questions)

    def test_manual_questions_appended(self):
        job = {
            "screening_questions": ["Why do you want to work here?"],
            "required_certifications": ["cosmetology"],
        }
        questions = generate_prescreen_questions(job)
        assert "Why do you want to work here?" in questions

    def test_no_duplicate_manual_questions(self):
        q = "Why do you want to work here?"
        job = {"screening_questions": [q, q]}
        questions = generate_prescreen_questions(job)
        assert questions.count(q) == 1

    def test_role_inferred_from_title(self):
        job = {"title": "Massage Therapist"}
        questions = generate_prescreen_questions(job)
        assert any("spa" in q.lower() or "salon" in q.lower() for q in questions)

    def test_empty_job_returns_empty(self):
        questions = generate_prescreen_questions({})
        assert isinstance(questions, list)


# ---- Search presets tests ----

class TestSearchPresets:
    def test_all_presets_present(self):
        expected = {"spa_therapists", "management", "biosecurity", "guest_services"}
        assert set(SEARCH_PRESETS.keys()) == expected

    def test_preset_structure(self):
        for name, preset in SEARCH_PRESETS.items():
            assert "search_terms" in preset, f"{name} missing search_terms"
            assert "department" in preset, f"{name} missing department"
            assert isinstance(preset["search_terms"], list)
            assert len(preset["search_terms"]) > 0

    def test_spa_preset_has_expected_terms(self):
        terms = SEARCH_PRESETS["spa_therapists"]["search_terms"]
        assert any("massage" in t for t in terms)
        assert any("esthetician" in t for t in terms)


# ---- Handler integration tests ----

class TestFilteringHandlers:
    @mock_aws
    def test_rank_candidates_handler(self, dynamodb_table):
        from src.handlers.filtering import rank_candidates
        from src.models.job import Job, JobStatus
        from src.models.candidate import Candidate

        job = Job(
            title="Massage Therapist",
            requirements="Licensed massage therapist required.",
            location="Naples, FL",
            status=JobStatus.OPEN,
            required_certifications=["massage_therapy"],
            role_category="spa",
        )
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=job.to_dynamo())

        strong = Candidate(
            first_name="Alice", last_name="Strong", job_id=job.job_id,
            certifications=["massage_therapy"],
            location="Naples, FL",
            years_experience=5,
        )
        weak = Candidate(
            first_name="Bob", last_name="Weak", job_id=job.job_id,
            certifications=[],
            location="Miami, FL",
        )
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=strong.to_dynamo())
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=weak.to_dynamo())

        event = {"pathParameters": {"id": job.job_id}, "queryStringParameters": None}
        response = rank_candidates(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert body["count"] == 2
        # Alice is qualified, Bob is disqualified — Alice should be first
        assert body["rankings"][0]["candidate_name"] == "Alice Strong"

    @mock_aws
    def test_rank_candidates_job_not_found(self, dynamodb_table):
        from src.handlers.filtering import rank_candidates

        event = {"pathParameters": {"id": "nonexistent"}, "queryStringParameters": None}
        response = rank_candidates(event, None)
        assert response["statusCode"] == 404

    @mock_aws
    def test_prescreen_questions_handler(self, dynamodb_table):
        from src.handlers.filtering import prescreen_questions
        from src.models.job import Job, JobStatus, RoleCategory

        job = Job(
            title="Esthetician",
            location="Naples, FL",
            status=JobStatus.OPEN,
            required_certifications=["esthetician"],
            shift_schedule=["morning", "afternoon"],
            role_category=RoleCategory.SPA,
        )
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=job.to_dynamo())

        event = {"pathParameters": {"id": job.job_id}}
        response = prescreen_questions(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert body["job_id"] == job.job_id
        assert body["count"] > 0
        assert any("esthetician" in q for q in body["questions"])
        assert any("morning" in q for q in body["questions"])

    @mock_aws
    def test_match_candidate_handler(self, dynamodb_table):
        from src.handlers.filtering import match_candidate
        from src.models.job import Job, JobStatus
        from src.models.candidate import Candidate

        spa_job = Job(
            title="Massage Therapist",
            required_certifications=["massage_therapy"],
            location="Naples, FL",
            status=JobStatus.OPEN,
            role_category="spa",
        )
        mgmt_job = Job(
            title="Spa Manager",
            location="Naples, FL",
            status=JobStatus.OPEN,
            role_category="management",
        )
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=spa_job.to_dynamo())
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=mgmt_job.to_dynamo())

        candidate = Candidate(
            first_name="Carol", last_name="Therapist",
            certifications=["massage_therapy"],
            location="Naples, FL",
            years_experience=4,
        )
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=candidate.to_dynamo())

        event = {"pathParameters": {"id": candidate.candidate_id}, "queryStringParameters": None}
        response = match_candidate(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert body["count"] == 2
        assert body["matches"][0]["job_title"] == "Massage Therapist"

    @mock_aws
    def test_score_handler(self, dynamodb_table):
        from src.handlers.filtering import score
        from src.models.job import Job, JobStatus
        from src.models.candidate import Candidate

        job = Job(
            title="Nail Technician",
            required_certifications=["nail_technician"],
            status=JobStatus.OPEN,
            role_category="spa",
        )
        candidate = Candidate(
            first_name="Dave", last_name="Nails",
            certifications=["nail_technician"],
            job_id=job.job_id,
        )
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=job.to_dynamo())
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=candidate.to_dynamo())

        event = {"body": json.dumps({"candidate_id": candidate.candidate_id, "job_id": job.job_id})}
        response = score(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert "total_score" in body
        assert body["qualified"] is True

    @mock_aws
    def test_score_missing_params(self, dynamodb_table):
        from src.handlers.filtering import score

        event = {"body": json.dumps({})}
        response = score(event, None)
        assert response["statusCode"] == 400


class TestScrapingHandlers:
    @mock_aws
    def test_import_creates_jobs(self, dynamodb_table):
        from unittest.mock import patch
        from src.handlers.scraping import import_jobs

        mock_results = [
            {
                "title": "Hair Stylist", "company": "Salon XYZ",
                "location": "Austin, TX",
                "description": "Looking for experienced hair stylist.",
                "job_url": "https://indeed.com/job/123",
                "site": "indeed", "date_posted": "2026-03-18",
            },
        ]

        with patch("src.handlers.scraping.scrape_jobs", return_value=mock_results):
            event = {"body": json.dumps({
                "search_term": "hair stylist", "location": "Austin, TX",
                "department": "Styling",
                "screening_questions": ["Tell me about your experience."],
            })}
            response = import_jobs(event, None)
            body = json.loads(response["body"])

        assert response["statusCode"] == 201
        assert body["count"] == 1
        assert body["imported"][0]["title"] == "Hair Stylist"
        assert body["imported"][0]["status"] == "draft"

    @mock_aws
    def test_preset_import_deduplicates(self, dynamodb_table):
        from unittest.mock import patch
        from src.handlers.scraping import preset_import

        # Both search terms return the same job
        mock_results = [
            {
                "title": "Massage Therapist", "company": "Spa Co",
                "location": "Naples, FL", "description": "...",
                "job_url": "https://indeed.com/1", "site": "indeed", "date_posted": "2026-03-18",
            },
        ]

        with patch("src.handlers.scraping.scrape_jobs", return_value=mock_results):
            event = {"body": json.dumps({"preset": "spa_therapists", "location": "Naples, FL"})}
            response = preset_import(event, None)
            body = json.loads(response["body"])

        assert response["statusCode"] == 201
        # Should be deduplicated — same title+company from multiple search terms → 1 result
        assert body["count"] == 1
        assert body["preset"] == "spa_therapists"

    @mock_aws
    def test_preset_import_invalid_preset(self, dynamodb_table):
        from src.handlers.scraping import preset_import

        event = {"body": json.dumps({"preset": "nonexistent", "location": "Naples, FL"})}
        response = preset_import(event, None)
        assert response["statusCode"] == 400

    @mock_aws
    def test_search_missing_term(self, dynamodb_table):
        from src.handlers.scraping import search

        event = {"body": json.dumps({})}
        response = search(event, None)
        assert response["statusCode"] == 400

    @mock_aws
    def test_search_returns_results(self, dynamodb_table):
        from unittest.mock import patch
        from src.handlers.scraping import search

        mock_results = [
            {"title": "Test Job", "company": "Test Co", "location": "Remote",
             "description": "A test job.", "job_url": "https://example.com",
             "site": "indeed", "date_posted": "2026-03-18"},
        ]

        with patch("src.handlers.scraping.scrape_jobs", return_value=mock_results):
            event = {"body": json.dumps({"search_term": "test"})}
            response = search(event, None)
            body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert body["count"] == 1


class TestContactTracking:
    @mock_aws
    def test_track_contact_handler(self, dynamodb_table):
        from src.handlers.candidates import track_contact
        from src.models.candidate import Candidate

        candidate = Candidate(first_name="Eve", last_name="Prospect")
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=candidate.to_dynamo())

        event = {
            "pathParameters": {"id": candidate.candidate_id},
            "body": json.dumps({"response_status": "awaiting_response"}),
        }
        response = track_contact(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert body["response_status"] == "awaiting_response"
        assert body["last_contacted"] is not None

    @mock_aws
    def test_track_contact_not_found(self, dynamodb_table):
        from src.handlers.candidates import track_contact

        event = {
            "pathParameters": {"id": "nonexistent"},
            "body": json.dumps({"response_status": "responsive"}),
        }
        response = track_contact(event, None)
        assert response["statusCode"] == 404

    @mock_aws
    def test_track_contact_invalid_status(self, dynamodb_table):
        from src.handlers.candidates import track_contact
        from src.models.candidate import Candidate

        candidate = Candidate(first_name="Frank", last_name="Test")
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=candidate.to_dynamo())

        event = {
            "pathParameters": {"id": candidate.candidate_id},
            "body": json.dumps({"response_status": "ghost_mode"}),
        }
        response = track_contact(event, None)
        assert response["statusCode"] == 400
