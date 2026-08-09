"""
===============================================================================
BHASHA MITRA

Module:
    main.py

Layer:
    Application

Description:
    Main entry point for the Bhasha Mitra backend application.

Responsibilities:
    - Initialize FastAPI
    - Register middleware
    - Register backend API routes
    - Register AI Framework routes
    - Register frontend routes
    - Start infrastructure initialization in background
    - Start background workers
    - Start AI Framework/model loading in background
    - Expose the ApplicationContainer through FastAPI application state
    - Stop all workers during shutdown
    - Shutdown AI Framework during shutdown

Startup behavior:
    FastAPI/UI becomes available immediately.
    Infrastructure and AI model loading happen in the background.

Shutdown behavior:
    - Signal workers to stop
    - Wait for workers with a bounded timeout
    - Stop AI Framework
    - Release application references
===============================================================================
"""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ai.api.router import router as ai_router

from app.api.openapi.tags import tags_metadata
from app.api.routes import router as api_router
from app.middleware import register_middlewares

from frontend.pages.routes import router as frontend_router

from infrastructure.ai.initialize_framework import (
    ai_framework,
)

from infrastructure.bootstrap.application_container import (
    ApplicationContainer,
)

from infrastructure.bootstrap.worker_registration import (
    register_workers,
)

from infrastructure.configuration import configuration

from workers.worker_manager import WorkerManager


logger = logging.getLogger(__name__)


# =============================================================================
# Application state
# =============================================================================

_initialization_thread: threading.Thread | None = None

_shutdown_requested = threading.Event()

_initialization_completed = threading.Event()


# =============================================================================
# Application initialization
# =============================================================================

def _initialize_application(
    app: FastAPI,
) -> None:
    """
    Initialize infrastructure, workers and AI Framework in background.
    """

    try:

        logger.info(
            "Starting Bhasha Mitra background initialization."
        )

        # =====================================================================
        # Configuration
        # =====================================================================

        configuration.initialize()

        logger.info(
            "Application configuration initialized."
        )

        if _shutdown_requested.is_set():
            logger.info(
                "Shutdown requested before infrastructure initialization."
            )
            return

        # =====================================================================
        # Application Container
        # =====================================================================

        logger.info(
            "Creating ApplicationContainer."
        )

        application_container = ApplicationContainer()

        application_container.path_manager.validate()

        # ---------------------------------------------------------------------
        # Store the SINGLE container instance in FastAPI application state.
        # ---------------------------------------------------------------------

        app.state.application_container = (
            application_container
        )

        logger.info(
            "ApplicationContainer initialized."
        )

        if _shutdown_requested.is_set():
            logger.info(
                "Shutdown requested after infrastructure initialization."
            )
            return

        # =====================================================================
        # Worker Manager
        # =====================================================================

        manager = WorkerManager()

        register_workers(
            manager=manager,
            container=application_container,
        )

        app.state.worker_manager = manager

        if _shutdown_requested.is_set():
            logger.info(
                "Shutdown requested before workers were started."
            )
            return

        manager.start_all()

        logger.info(
            "Bhasha Mitra background workers started."
        )

        # =====================================================================
        # AI Framework
        # =====================================================================

        if _shutdown_requested.is_set():
            logger.info(
                "Shutdown requested before AI Framework initialization."
            )
            return

        logger.info(
            "Starting AI Framework initialization."
        )

        ai_framework.initialize()

        logger.info(
            "AI Framework Ready."
        )

        app.state.ai_framework_ready = True

    except Exception:

        logger.exception(
            "Bhasha Mitra background initialization failed."
        )

        app.state.infrastructure_ready = False

    else:

        app.state.infrastructure_ready = True

    finally:

        _initialization_completed.set()

        logger.info(
            "Bhasha Mitra background initialization thread completed."
        )


def _start_background_initialization(
    app: FastAPI,
) -> None:
    """
    Start infrastructure and AI initialization in a background thread.
    """

    global _initialization_thread

    if (
        _initialization_thread is not None
        and _initialization_thread.is_alive()
    ):
        logger.warning(
            "Background initialization is already running."
        )
        return

    _initialization_thread = threading.Thread(
        target=_initialize_application,
        args=(app,),
        name="BhashaMitraInitializer",
        daemon=True,
    )

    _initialization_thread.start()

    logger.info(
        "Bhasha Mitra background initialization started."
    )


# =============================================================================
# FastAPI lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    """
    FastAPI application lifecycle.

    FastAPI becomes available immediately.
    Infrastructure and AI initialization happen in background.
    """

    logger.info(
        "Starting Bhasha Mitra application."
    )

    # -------------------------------------------------------------------------
    # Initial application state
    # -------------------------------------------------------------------------

    app.state.application_container = None
    app.state.worker_manager = None
    app.state.ai_framework_ready = False
    app.state.infrastructure_ready = False

    _shutdown_requested.clear()
    _initialization_completed.clear()

    # -------------------------------------------------------------------------
    # Start background initialization
    # -------------------------------------------------------------------------

    _start_background_initialization(
        app
    )

    logger.info(
        "Bhasha Mitra UI/API is available. "
        "Infrastructure and AI models are loading in background."
    )

    # -------------------------------------------------------------------------
    # Application is now serving requests
    # -------------------------------------------------------------------------

    yield

    # =========================================================================
    # Shutdown
    # =========================================================================

    logger.info(
        "Bhasha Mitra shutdown initiated."
    )

    _shutdown_requested.set()

    # =========================================================================
    # Stop workers
    # =========================================================================

    manager: WorkerManager | None = getattr(
        app.state,
        "worker_manager",
        None,
    )

    if manager is not None:

        logger.info(
            "Stopping Bhasha Mitra workers."
        )

        try:

            manager.stop_all()

        except Exception:

            logger.exception(
                "Failed to stop Bhasha Mitra workers."
            )

        try:

            manager.join_all(
                timeout=10.0
            )

        except Exception:

            logger.exception(
                "Failed while waiting for workers."
            )

        logger.info(
            "Worker shutdown completed."
        )

    # =========================================================================
    # Wait for initialization thread
    # =========================================================================

    initialization_thread = _initialization_thread

    if (
        initialization_thread is not None
        and initialization_thread.is_alive()
    ):

        logger.info(
            "Waiting for background initialization to finish."
        )

        initialization_thread.join(
            timeout=10.0
        )

        if initialization_thread.is_alive():

            logger.warning(
                "Background initialization did not finish "
                "within shutdown timeout."
            )

    # =========================================================================
    # AI Framework shutdown
    # =========================================================================

    try:

        logger.info(
            "Shutting down AI Framework."
        )

        ai_framework.shutdown()

        logger.info(
            "AI Framework shutdown completed."
        )

    except Exception:

        logger.exception(
            "AI Framework shutdown failed."
        )

    # =========================================================================
    # Clear application state
    # =========================================================================

    app.state.application_container = None
    app.state.worker_manager = None
    app.state.infrastructure_ready = False
    app.state.ai_framework_ready = False

    logger.info(
        "Bhasha Mitra shutdown completed."
    )


# =============================================================================
# FastAPI application
# =============================================================================

app = FastAPI(
    title="Bhasha Mitra API",
    description="""
Offline AI-powered multilingual video translation platform.

Features:

- Video Upload
- Speech Recognition (ASR)
- Language Translation
- Subtitle Generation
- Text-to-Speech
- Job Management
- Provider Discovery
- Model Management
""",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
    contact={
        "name": "Bhasha Mitra Team",
        "email": "support@bhashamitra.local",
    },
    license_info={
        "name": "Proprietary",
    },
)


# =============================================================================
# Middleware
# =============================================================================

register_middlewares(
    app
)


# =============================================================================
# Backend API routes
# =============================================================================

app.include_router(
    api_router
)


# =============================================================================
# AI Framework routes
# =============================================================================

app.include_router(
    ai_router
)


# =============================================================================
# Frontend static files
# =============================================================================

frontend_static_directory = Path(
    "frontend/static"
)

if frontend_static_directory.is_dir():

    app.mount(
        "/static",
        StaticFiles(
            directory=str(
                frontend_static_directory
            )
        ),
        name="static",
    )

else:

    logger.warning(
        "Frontend static directory not found: %s",
        frontend_static_directory,
    )


# =============================================================================
# Frontend routes
# =============================================================================

app.include_router(
    frontend_router
)


# =============================================================================
# Root endpoint
# =============================================================================

@app.get(
    "/",
    tags=["Root"],
)
async def root() -> dict:
    """
    Root endpoint.
    """

    return {
        "application": "Bhasha Mitra",
        "version": app.version,
        "status": "Running",
    }