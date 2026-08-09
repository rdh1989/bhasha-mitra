"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : router.py
Purpose     : AI API Router

Description
-----------
Registers every AI endpoint exposed by the AI Framework.

Author
------
Bhasha Mitra AI Team

Version
-------
1.0
===============================================================================
"""

from fastapi import APIRouter

from ai.api.health import router as health_router
from ai.api.models import router as models_router

from ai.api.translation import router as translation_router
from ai.api.asr import router as asr_router
from ai.api.language_detection import router as language_router
from ai.api.tts import router as tts_router
from ai.api.subtitle import router as subtitle_router

from ai.api.video_translation import router as video_router
from ai.api.transcript import router as transcript_router
from ai.api.dubbing import router as dubbing_router

router = APIRouter(
    prefix="/api/ai",
    tags=["AI Framework"],
)

# -------------------------------------------------------------------------
# Framework
# -------------------------------------------------------------------------

router.include_router(health_router)
router.include_router(models_router)

# -------------------------------------------------------------------------
# AI Services
# -------------------------------------------------------------------------

router.include_router(translation_router)
router.include_router(asr_router)
router.include_router(language_router)
router.include_router(tts_router)
router.include_router(subtitle_router)

# -------------------------------------------------------------------------
# AI Pipelines
# -------------------------------------------------------------------------

router.include_router(video_router)
router.include_router(transcript_router)
router.include_router(dubbing_router)