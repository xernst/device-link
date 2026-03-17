from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter()


@router.post("/")
async def create_material(db: AsyncSession = Depends(get_db)):
    """Upload marketing material."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{material_id}")
async def get_material(material_id: str, db: AsyncSession = Depends(get_db)):
    """Get material details."""
    raise HTTPException(status_code=501, detail="Not implemented")
