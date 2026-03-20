"""Lambda handlers for job scraping operations."""

from src.models.job import Job, JobStatus, RoleCategory
from src.services import dynamodb
from src.services.scraper import scrape_jobs
from src.services.filtering import SEARCH_PRESETS
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


def preset_import(event, context):
    """POST /scrape/preset — Scrape and import jobs using a named preset.

    Request body:
        preset (required): One of "spa_therapists", "management", "biosecurity", "guest_services"
        location (required): City/state to search
        results_wanted: Per search term (default: 10)
        hours_old: Max age in hours (default: 72)
        country: Country code (default: "USA")

    Runs all search terms in the preset, deduplicates by title+company, and bulk-imports.
    """
    try:
        data = parse_body(event)
        preset_name = data.get("preset")
        location = data.get("location", "")

        if not preset_name:
            return error("preset is required")
        if preset_name not in SEARCH_PRESETS:
            return error(f"Unknown preset. Available: {list(SEARCH_PRESETS.keys())}")

        preset = SEARCH_PRESETS[preset_name]
        results_wanted = data.get("results_wanted", 10)
        hours_old = data.get("hours_old", 72)
        country = data.get("country", "USA")

        # Scrape all search terms in the preset
        all_scraped = []
        seen = set()
        for term in preset["search_terms"]:
            scraped = scrape_jobs(
                search_term=term,
                location=location,
                results_wanted=results_wanted,
                hours_old=hours_old,
                country=country,
            )
            for job in scraped:
                dedup_key = f"{job.get('title', '').lower()}|{job.get('company', '').lower()}"
                if dedup_key not in seen:
                    seen.add(dedup_key)
                    all_scraped.append(job)

        # Import as DRAFT jobs with preset metadata
        department = preset["department"]
        role_category_str = preset.get("role_category")
        role_category = None
        if role_category_str:
            try:
                role_category = RoleCategory(role_category_str)
            except ValueError:
                role_category = None

        imported = []
        for scraped_job in all_scraped:
            job = Job(
                title=scraped_job.get("title", "Untitled"),
                location=scraped_job.get("location", location),
                department=department,
                description=scraped_job.get("description", ""),
                requirements="",
                status=JobStatus.DRAFT,
                salary_min=scraped_job.get("salary_min"),
                salary_max=scraped_job.get("salary_max"),
                role_category=role_category,
            )
            dynamodb.put_item(job.to_dynamo())
            api_job = job.to_api()
            api_job["source_url"] = scraped_job.get("job_url", "")
            api_job["source_site"] = scraped_job.get("site", "")
            api_job["company"] = scraped_job.get("company", "")
            imported.append(api_job)

        return success({
            "preset": preset_name,
            "imported": imported,
            "count": len(imported),
        }, status_code=201)
    except RuntimeError as e:
        return error(str(e), status_code=503)
    except Exception as e:
        return error(str(e), status_code=500)
