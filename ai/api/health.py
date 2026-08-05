"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : health.py
Purpose     : AI Health API

Description
-----------
Health endpoint for AI Framework.

Responsibilities
----------------
• Verify AI Framework is initialized
• Verify loaded models
• Return AI health status

Author
------
Bhasha Mitra AI Team

Version
-------
1.0
===============================================================================
"""

from fastapi import APIRouter

from ai.model_manager.manager import ModelManager

router = APIRouter()


@router.get(
    "/health",
    summary="AI Framework Health",
)
def health():
    """
    AI Framework Health Check.
    """

    manager = ModelManager()

    loaded_models = manager.list_loaded_models()

    return {
        "status": "Healthy",
        "framework": "Bhasha Mitra AI Framework",
        "version": "1.0.0",
        "models_loaded": len(loaded_models),
        "loaded_models": loaded_models,
    }