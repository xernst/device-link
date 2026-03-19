"""Lambda handlers for job scraping operations."""

from src.models.job import Job, JobStatus
from src.services import dynamodb
from src.services.scraper import scrape_jobs
from src.utils.response import success, error, parse_body


def search(event, context):
    """POST /scrape/search — Scrape job boards for listings.

    Request body:
        search_term (required): Job title or keywords
        location: City/state
        sites: List of sites to scrape (default: ["indeed"])
        results_wanted: Number of results (default: 20)
        hours_old: Max age in hours (default: 72)
        country: Country code (default: "USA")

    Returns scraped job listings (not saved to DB).
    """
    try:
        data = parse_body(event)
        search_term = data.get("search_term")
        if not search_term:
            return error("search_term is required")

        jobs = scrape_jobs(
            search_term=search_term,
            location=data.get("location", ""),
            site_names=data.get("sites"),
            results_wanted=data.get("results_wanted", 20),
            hours_old=data.get("hours_old", 72),
            country=data.get("country", "USA"),
        )

        return success({"jobs": jobs, "count": len(jobs)})
    except RuntimeError as e:
        return error(str(e), status_code=503)
    except Exception as e:
        return error(str(e), status_code=500)


def import_jobs(event, context):
    """POST /scrape/import — Scrape and import jobs into the recruiting pipeline.

    Request body:
        search_term (required): Job title or keywords
        location: City/state
        department: Department to assign
        sites: List of sites (default: ["indeed"])
        results_wanted: Number of results (default: 10)
        hours_old: Max age in hours (default: 72)
        country: Country code (default: "USA")
        screening_questions: Default screening questions for imported jobs

    Returns created job records.
    """
    try:
        data = parse_body(event)
        search_term = data.get("search_term")
        if not search_term:
            return error("search_term is required")

        scraped = scrape_jobs(
            search_term=search_term,
            location=data.get("location", ""),
            site_names=data.get("sites"),
            results_wanted=data.get("results_wanted", 10),
            hours_old=data.get("hours_old", 72),
            country=data.get("country", "USA"),
        )

        department = data.get("department", "")
        screening_questions = data.get("screening_questions", [])
        imported = []

        for scraped_job in scraped:
            job = Job(
                title=scraped_job.get("title", "Untitled"),
                location=scraped_job.get("location", ""),
                department=department,
                description=scraped_job.get("description", ""),
                requirements="",
                status=JobStatus.DRAFT,
                salary_min=scraped_job.get("salary_min"),
                salary_max=scraped_job.get("salary_max"),
                screening_questions=screening_questions,
            )
            dynamodb.put_item(job.to_dynamo())
            api_job = job.to_api()
            # Attach source metadata
            api_job["source_url"] = scraped_job.get("job_url", "")
            api_job["source_site"] = scraped_job.get("site", "")
            api_job["company"] = scraped_job.get("company", "")
            imported.append(api_job)

        return success({"imported": imported, "count": len(imported)}, status_code=201)
    except RuntimeError as e:
        return error(str(e), status_code=503)
    except Exception as e:
        return error(str(e), status_code=500)
