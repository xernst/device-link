from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter()


@router.post("/")
async def create_simulation(db: AsyncSession = Depends(get_db)):
    """Create and run a new simulation."""
    # TODO: accept SimulationCreate schema, queue Celery task
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{simulation_id}")
async def get_simulation(simulation_id: str, db: AsyncSession = Depends(get_db)):
    """Get simulation status and results."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{simulation_id}/feed")
async def get_simulation_feed(simulation_id: str, db: AsyncSession = Depends(get_db)):
    """Get the simulated social feed."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{simulation_id}/report")
async def get_simulation_report(simulation_id: str, db: AsyncSession = Depends(get_db)):
    """Get the full analysis report."""
    raise HTTPException(status_code=501, detail="Not implemented")
