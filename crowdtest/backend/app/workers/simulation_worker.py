"""Celery worker for async simulation execution."""

# TODO: configure Celery with Redis broker
# from celery import Celery
# celery_app = Celery("crowdtest", broker=settings.redis_url)


async def run_simulation_task(simulation_id: str):
    """Main simulation task. Orchestrates the full pipeline:

    1. Load simulation config + materials from DB
    2. Generate personas (Sonnet call)
    3. Build social graph
    4. Run 7-turn simulation (batched Haiku calls)
    5. Run analysis (Sonnet call)
    6. Save results to DB
    7. Update status to 'complete'
    """
    # TODO: implement full pipeline
    pass
