from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter()


@router.get("/archetypes")
async def list_archetypes():
    """List available persona archetypes."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/generate")
async def generate_persona_pack(db: AsyncSession = Depends(get_db)):
    """Generate a persona pack from audience description."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/packs")
async def list_persona_packs(db: AsyncSession = Depends(get_db)):
    """List saved persona packs."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/packs/{pack_id}")
async def get_persona_pack(pack_id: str, db: AsyncSession = Depends(get_db)):
    """Get pack details with individual personas."""
    raise HTTPException(status_code=501, detail="Not implemented")
