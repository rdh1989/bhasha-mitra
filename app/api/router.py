from fastapi import APIRouter

from app.api.dashboard import router as dashboard_router
from app.api.upload import router as upload_router
from app.api.jobs import router as jobs_router
from app.api.settings import router as settings_router

router = APIRouter()

router.include_router(dashboard_router)
router.include_router(upload_router)
router.include_router(jobs_router)
router.include_router(settings_router)