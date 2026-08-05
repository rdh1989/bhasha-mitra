"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : models.py
Purpose     : AI Model Management API

Description
-----------
Provides endpoints for inspecting and managing loaded AI models.

Endpoints
---------
GET    /models
GET    /models/info
GET    /cache
POST   /cache/reload
GET    /version

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


# -----------------------------------------------------------------------------
# AI-002
# -----------------------------------------------------------------------------


@router.get(
    "/models",
    summary="Loaded AI Models",
)
def loaded_models():
    """
    Return currently loaded AI models.
    """

    manager = ModelManager()

    return {
        "count": len(manager.list_loaded_models()),
        "models": manager.list_loaded_models(),
    }


# -----------------------------------------------------------------------------
# AI-003
# -----------------------------------------------------------------------------


@router.get(
    "/models/info",
    summary="AI Model Information",
)
def model_information():
    """
    Return information about loaded models.
    """

    manager = ModelManager()

    models = []

    for key in manager.list_loaded_models():

        category, model = key.split(":", 1)

        metadata = manager._registry.get(
            category,
            model,
        )

        models.append(
            {
                "category": metadata["category"],
                "model": metadata["model"],
                "provider": metadata["provider"],
                "version": metadata["version"],
                "path": str(metadata["path"]),
            }
        )

    return {
        "count": len(models),
        "models": models,
    }


# -----------------------------------------------------------------------------
# AI-018
# -----------------------------------------------------------------------------


@router.get(
    "/cache",
    summary="Model Cache",
)
def cache():
    """
    Return model cache information.
    """

    manager = ModelManager()

    return {
        "cache_size": len(manager.list_loaded_models()),
        "loaded_models": manager.list_loaded_models(),
    }


# -----------------------------------------------------------------------------
# AI-019
# -----------------------------------------------------------------------------


@router.post(
    "/cache/reload",
    summary="Reload AI Models",
)
def reload_cache():
    """
    Reload every startup model.
    """

    manager = ModelManager()

    manager.shutdown()

    manager.initialize()

    manager.load_all()

    return {
        "status": "Success",
        "message": "AI model cache reloaded successfully.",
    }


# -----------------------------------------------------------------------------
# AI-020
# -----------------------------------------------------------------------------


@router.get(
    "/version",
    summary="AI Framework Version",
)
def version():
    """
    Return AI Framework version.
    """

    manager = ModelManager()

    return {
        "framework": "Bhasha Mitra AI Framework",
        "version": "1.0.0",
        "loaded_models": len(manager.list_loaded_models()),
    }


# -----------------------------------------------------------------------------
# AI-004
# -----------------------------------------------------------------------------


@router.get(
    "/statistics",
    summary="AI Runtime Statistics",
)
def statistics():
    """
    Return AI Framework runtime statistics.
    """

    manager = ModelManager()

    loaded_models = manager.list_loaded_models()

    return {
        "framework": "Bhasha Mitra AI Framework",
        "version": "1.0.0",
        "status": "Running",
        "loaded_models": len(loaded_models),
        "models": loaded_models,
        "cache_size": len(loaded_models),
        "startup_mode": "Preloaded",
        "inference_mode": "Cached",
        "memory_usage": "Available in v2",
        "gpu": "Available in v2",
        "uptime": "Available in v2",
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
    }