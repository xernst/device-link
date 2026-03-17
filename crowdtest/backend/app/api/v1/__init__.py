from fastapi import APIRouter

from app.api.v1.simulations import router as simulations_router
from app.api.v1.materials import router as materials_router
from app.api.v1.personas import router as personas_router
from app.api.v1.projects import router as projects_router

router = APIRouter()
router.include_router(simulations_router, prefix="/simulations", tags=["simulations"])
router.include_router(materials_router, prefix="/materials", tags=["materials"])
router.include_router(personas_router, prefix="/personas", tags=["personas"])
router.include_router(projects_router, prefix="/projects", tags=["projects"])
