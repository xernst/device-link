"""Tests for candidate filtering and matching service."""

import json
import pytest
from moto import mock_aws

from src.services.filtering import (
    score_candidate,
    filter_candidates,
    match_jobs_to_candidate,
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
    def test_perfect_match(self):
        candidate = {
            "notes": "Expert in crisis management, public relations, brand management, and media relations.",
            "location": "New York, NY",
        }
        job = {
            "requirements": "Must have experience in crisis management, public relations, brand management, and media relations.",
            "location": "New York, NY",
        }
        result = score_candidate(candidate, job)
        assert result["total_score"] >= 80
        assert len(result["missing_skills"]) == 0
        assert len(result["matched_skills"]) >= 4

    def test_no_match(self):
        candidate = {
            "notes": "Expert Python developer with AWS and Docker experience.",
            "location": "San Francisco, CA",
        }
        job = {
            "requirements": "Must have cosmetology license and hair styling experience.",
            "location": "Miami, FL",
        }
        result = score_candidate(candidate, job)
        assert result["total_score"] < 40
        assert len(result["missing_skills"]) > 0
        assert len(result["matched_skills"]) == 0

    def test_partial_skill_match(self):
        candidate = {
            "notes": "Experience in social media and content strategy.",
            "location": "Remote",
        }
        job = {
            "requirements": "Need social media, content strategy, crisis management, and brand management skills.",
            "location": "New York, NY",
        }
        result = score_candidate(candidate, job)
        assert 0 < result["total_score"] < 100
        assert "social media" in result["matched_skills"]
        assert "content strategy" in result["matched_skills"]
        assert "crisis management" in result["missing_skills"]

    def test_location_match_same_city(self):
        candidate = {"notes": "", "location": "Austin, TX"}
        job = {"requirements": "", "location": "Austin, TX"}
        result = score_candidate(candidate, job)
        assert result["breakdown"]["location"] == 100

    def test_location_partial_match(self):
        candidate = {"notes": "", "location": "Dallas, TX"}
        job = {"requirements": "", "location": "Houston, TX"}
        result = score_candidate(candidate, job)
        # Same state
        assert result["breakdown"]["location"] == 75

    def test_remote_location_scores_well(self):
        candidate = {"notes": "", "location": "Remote"}
        job = {"requirements": "", "location": "San Francisco, CA"}
        result = score_candidate(candidate, job)
        assert result["breakdown"]["location"] >= 70

    def test_experience_years_match(self):
        candidate = {"notes": "7 years of experience in marketing."}
        job = {"requirements": "Requires 5+ years experience."}
        result = score_candidate(candidate, job)
        assert result["breakdown"]["experience"] == 100

    def test_experience_years_insufficient(self):
        candidate = {"notes": "2 years of experience in marketing."}
        job = {"requirements": "Requires 10+ years experience."}
        result = score_candidate(candidate, job)
        assert result["breakdown"]["experience"] < 50

    def test_seniority_match(self):
        candidate = {"notes": "Senior marketing manager with leadership experience."}
        job = {"requirements": "Looking for a senior brand strategist.", "description": ""}
        result = score_candidate(candidate, job)
        assert result["breakdown"]["experience"] == 100

    def test_empty_candidate_and_job(self):
        result = score_candidate({}, {})
        assert result["total_score"] == 50  # All neutral scores


# ---- filter_candidates tests ----

class TestFilterCandidates:
    def test_ranks_by_score_descending(self):
        candidates = [
            {"candidate_id": "1", "first_name": "Low", "last_name": "Match", "notes": "Customer service."},
            {"candidate_id": "2", "first_name": "High", "last_name": "Match", "notes": "Crisis management, public relations, brand management, media relations."},
            {"candidate_id": "3", "first_name": "Mid", "last_name": "Match", "notes": "Public relations and media relations."},
        ]
        job = {
            "requirements": "Need crisis management, public relations, brand management, and media relations.",
        }
        results = filter_candidates(candidates, job)
        assert len(results) == 3
        assert results[0]["candidate_id"] == "2"  # Best match first
        # Scores should be descending
        assert results[0]["total_score"] >= results[1]["total_score"]
        assert results[1]["total_score"] >= results[2]["total_score"]

    def test_min_score_filter(self):
        candidates = [
            {"candidate_id": "1", "first_name": "A", "last_name": "B", "notes": "Python developer."},
            {"candidate_id": "2", "first_name": "C", "last_name": "D", "notes": "Crisis management expert with public relations and brand management."},
        ]
        job = {
            "requirements": "Need crisis management, public relations, and brand management.",
        }
        results = filter_candidates(candidates, job, min_score=40)
        # Only the matching candidate should be included
        assert all(r["total_score"] >= 40 for r in results)

    def test_empty_candidates(self):
        results = filter_candidates([], {"requirements": "Python"})
        assert results == []


# ---- match_jobs_to_candidate tests ----

class TestMatchJobsToCandidate:
    def test_matches_best_jobs(self):
        candidate = {
            "notes": "Expert in crisis management and public relations.",
            "location": "New York, NY",
        }
        jobs = [
            {"job_id": "1", "title": "PR Manager", "requirements": "Crisis management and public relations.", "location": "New York, NY"},
            {"job_id": "2", "title": "Python Dev", "requirements": "Python, AWS, Docker.", "location": "SF, CA"},
            {"job_id": "3", "title": "Comms Lead", "requirements": "Public relations and media relations.", "location": "New York, NY"},
        ]
        results = match_jobs_to_candidate(candidate, jobs)
        assert len(results) == 3
        # PR Manager should rank highest
        assert results[0]["job_id"] == "1"
        assert results[0]["job_title"] == "PR Manager"


# ---- Handler integration tests ----

class TestFilteringHandlers:
    @mock_aws
    def test_rank_candidates_handler(self, dynamodb_table):
        from src.handlers.filtering import rank_candidates
        from src.models.job import Job, JobStatus
        from src.models.candidate import Candidate

        # Create a job
        job = Job(
            title="Crisis Communications Manager",
            requirements="Crisis management, public relations, brand management, media relations.",
            location="New York, NY",
            status=JobStatus.OPEN,
        )
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=job.to_dynamo())

        # Create candidates with varying fit
        strong = Candidate(
            first_name="Alice",
            last_name="Strong",
            job_id=job.job_id,
            notes="10 years in crisis management, public relations, brand management, and media relations.",
            location="New York, NY",
        )
        weak = Candidate(
            first_name="Bob",
            last_name="Weak",
            job_id=job.job_id,
            notes="Entry-level customer service experience.",
            location="Miami, FL",
        )
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=strong.to_dynamo())
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=weak.to_dynamo())

        event = {
            "pathParameters": {"id": job.job_id},
            "queryStringParameters": None,
        }
        response = rank_candidates(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert body["count"] == 2
        assert body["rankings"][0]["candidate_name"] == "Alice Strong"
        assert body["rankings"][0]["total_score"] > body["rankings"][1]["total_score"]

    @mock_aws
    def test_rank_candidates_job_not_found(self, dynamodb_table):
        from src.handlers.filtering import rank_candidates

        event = {
            "pathParameters": {"id": "nonexistent"},
            "queryStringParameters": None,
        }
        response = rank_candidates(event, None)
        assert response["statusCode"] == 404

    @mock_aws
    def test_match_candidate_handler(self, dynamodb_table):
        from src.handlers.filtering import match_candidate
        from src.models.job import Job, JobStatus
        from src.models.candidate import Candidate

        # Create open jobs
        pr_job = Job(
            title="PR Manager",
            requirements="Crisis management, public relations.",
            location="New York, NY",
            status=JobStatus.OPEN,
        )
        dev_job = Job(
            title="Python Developer",
            requirements="Python, AWS, Docker.",
            location="San Francisco, CA",
            status=JobStatus.OPEN,
        )
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=pr_job.to_dynamo())
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=dev_job.to_dynamo())

        # Create a PR-focused candidate
        candidate = Candidate(
            first_name="Carol",
            last_name="PRPro",
            notes="Expert in crisis management, public relations, and media relations.",
            location="New York, NY",
        )
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=candidate.to_dynamo())

        event = {
            "pathParameters": {"id": candidate.candidate_id},
            "queryStringParameters": None,
        }
        response = match_candidate(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert body["count"] == 2
        # PR job should rank higher
        assert body["matches"][0]["job_title"] == "PR Manager"

    @mock_aws
    def test_score_handler(self, dynamodb_table):
        from src.handlers.filtering import score
        from src.models.job import Job, JobStatus
        from src.models.candidate import Candidate

        job = Job(
            title="Social Media Manager",
            requirements="Social media, content strategy, digital marketing.",
            status=JobStatus.OPEN,
        )
        candidate = Candidate(
            first_name="Dave",
            last_name="Social",
            job_id=job.job_id,
            notes="5 years in social media and content strategy.",
        )
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=job.to_dynamo())
        dynamodb_table.put_item(TableName="recruiting-candidates", Item=candidate.to_dynamo())

        event = {
            "body": json.dumps({
                "candidate_id": candidate.candidate_id,
                "job_id": job.job_id,
            }),
        }
        response = score(event, None)
        body = json.loads(response["body"])

        assert response["statusCode"] == 200
        assert "total_score" in body
        assert "matched_skills" in body
        assert "social media" in body["matched_skills"]

    @mock_aws
    def test_score_missing_params(self, dynamodb_table):
        from src.handlers.filtering import score

        event = {"body": json.dumps({})}
        response = score(event, None)
        assert response["statusCode"] == 400


class TestScrapingHandlers:
    @mock_aws
    def test_import_creates_jobs(self, dynamodb_table):
        """Test import handler with mocked scraper results."""
        from unittest.mock import patch
        from src.handlers.scraping import import_jobs

        mock_results = [
            {
                "title": "Hair Stylist",
                "company": "Salon XYZ",
                "location": "Austin, TX",
                "description": "Looking for experienced hair stylist with color specialist skills.",
                "job_url": "https://indeed.com/job/123",
                "site": "indeed",
                "date_posted": "2026-03-18",
            },
        ]

        with patch("src.handlers.scraping.scrape_jobs", return_value=mock_results):
            event = {
                "body": json.dumps({
                    "search_term": "hair stylist",
                    "location": "Austin, TX",
                    "department": "Styling",
                    "screening_questions": ["Tell me about your experience."],
                }),
            }
            response = import_jobs(event, None)
            body = json.loads(response["body"])

        assert response["statusCode"] == 201
        assert body["count"] == 1
        assert body["imported"][0]["title"] == "Hair Stylist"
        assert body["imported"][0]["department"] == "Styling"
        assert body["imported"][0]["source_site"] == "indeed"
        assert body["imported"][0]["status"] == "draft"

    @mock_aws
    def test_search_missing_term(self, dynamodb_table):
        from src.handlers.scraping import search

        event = {"body": json.dumps({})}
        response = search(event, None)
        assert response["statusCode"] == 400
        assert "search_term" in json.loads(response["body"])["error"]

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
        assert body["jobs"][0]["title"] == "Test Job"
