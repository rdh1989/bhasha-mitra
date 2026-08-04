"""
API route registration.
"""

from fastapi import APIRouter

from .download import router as download_router
from .health import router as health_router
from .job import router as job_router
from .models import router as models_router
from .providers import router as providers_router
from .translate import router as translate_router
from .upload import router as upload_router
from app.api.routes.translations import router as translations_router

router = APIRouter(prefix="/api/v1")

router.include_router(health_router)
router.include_router(upload_router)
router.include_router(translate_router)
router.include_router(job_router)
router.include_router(download_router)
router.include_router(providers_router)
router.include_router(models_router)
router.include_router(translations_router)