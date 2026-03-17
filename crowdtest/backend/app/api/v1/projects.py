from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter()


@router.post("/")
async def create_project(db: AsyncSession = Depends(get_db)):
    """Create a new project."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/")
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all projects."""
    raise HTTPException(status_code=501, detail="Not implemented")
