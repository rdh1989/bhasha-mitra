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
from logging.handlers import RotatingFileHandler
from pathlib import Path

from ai.model_manager.manager import ModelManager

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


def _ensure_bootstrap_logging() -> None:
    """
    Ensure startup logs are always visible even before configuration loads.
    """

    project_root = Path(__file__).resolve().parents[1]
    log_directory = project_root / "storage" / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)

    format_string = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(format_string, date_format)

    root_logger = logging.getLogger()
    if root_logger.level > logging.INFO:
        root_logger.setLevel(logging.INFO)

    has_bootstrap_console = any(
        getattr(handler, "_bhasha_bootstrap_console", False)
        for handler in root_logger.handlers
    )

    if not has_bootstrap_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        setattr(console_handler, "_bhasha_bootstrap_console", True)
        root_logger.addHandler(console_handler)

    bootstrap_log_path = log_directory / "application.log"

    has_bootstrap_file = any(
        isinstance(handler, RotatingFileHandler)
        and Path(getattr(handler, "baseFilename", "")).resolve()
        == bootstrap_log_path.resolve()
        for handler in root_logger.handlers
    )

    if not has_bootstrap_file:
        file_handler = RotatingFileHandler(
            filename=bootstrap_log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def _configure_background_file_logging() -> None:
    """
    Attach a rotating logfile handler to the root logger.

    This ensures background worker logs and other module logs are
    persisted to disk in addition to console output.
    """

    try:

        logging_config = configuration.logging

        application_config = logging_config.get(
            "application",
            {},
        )

        if not application_config.get("enabled", True):
            return

        log_directory = Path(
            logging_config.get("directory", "storage/logs")
        ).expanduser()
        if not log_directory.is_absolute():
            project_root = Path(__file__).resolve().parents[1]
            log_directory = (project_root / log_directory).resolve()
        log_directory.mkdir(parents=True, exist_ok=True)

        application_filename = application_config.get(
            "filename",
            "application.log",
        )
        application_log_path = log_directory / application_filename

        max_size_mb = int(
            logging_config.get("rotation", {}).get("max_size_mb", 10)
        )
        backup_count = int(
            logging_config.get("rotation", {}).get("backup_count", 5)
        )

        format_string = logging_config.get(
            "format",
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
        date_format = logging_config.get(
            "date_format",
            "%Y-%m-%d %H:%M:%S",
        )

        level_name = str(
            logging_config.get("level", "INFO")
        ).upper()
        level = getattr(logging, level_name, logging.INFO)

        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        for handler in root_logger.handlers:

            if (
                isinstance(handler, RotatingFileHandler)
                and Path(getattr(handler, "baseFilename", "")).resolve()
                == application_log_path.resolve()
            ):
                return

        handler = RotatingFileHandler(
            filename=application_log_path,
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding="utf-8",
        )
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(format_string, date_format))

        root_logger.addHandler(handler)

        logger.info(
            "BACKGROUND FILE LOGGING CONFIGURED | file=%s",
            application_log_path,
        )

    except Exception:

        logger.exception(
            "Failed to configure background file logging."
        )


def _configure_ai_file_logging() -> None:
    """
    Attach a dedicated rotating logfile handler to ai.* loggers.
    """

    try:

        logging_config = configuration.logging

        ai_config = logging_config.get("ai", {})

        if not ai_config.get("enabled", False):
            return

        log_directory = Path(
            logging_config.get("directory", "storage/logs")
        ).expanduser()
        if not log_directory.is_absolute():
            project_root = Path(__file__).resolve().parents[1]
            log_directory = (project_root / log_directory).resolve()
        log_directory.mkdir(parents=True, exist_ok=True)

        ai_log_filename = ai_config.get("filename", "ai.log")
        ai_log_path = log_directory / ai_log_filename

        max_size_mb = int(
            logging_config.get("rotation", {}).get("max_size_mb", 10)
        )
        backup_count = int(
            logging_config.get("rotation", {}).get("backup_count", 5)
        )

        format_string = logging_config.get(
            "format",
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
        date_format = logging_config.get(
            "date_format",
            "%Y-%m-%d %H:%M:%S",
        )

        level_name = str(
            logging_config.get("level", "INFO")
        ).upper()
        level = getattr(logging, level_name, logging.INFO)

        ai_logger = logging.getLogger("ai")
        ai_logger.setLevel(level)

        for handler in ai_logger.handlers:

            if (
                isinstance(handler, RotatingFileHandler)
                and Path(getattr(handler, "baseFilename", "")).resolve()
                == ai_log_path.resolve()
            ):
                return

        handler = RotatingFileHandler(
            filename=ai_log_path,
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding="utf-8",
        )
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(format_string, date_format))

        ai_logger.addHandler(handler)

        logger.info(
            "AI FILE LOGGING CONFIGURED | file=%s",
            ai_log_path,
        )

    except Exception:

        logger.exception(
            "Failed to configure AI file logging."
        )


def _ensure_job_console_logging() -> None:
    """
    Ensure job and request loggers always print to console.
    """

    format_string = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(format_string, date_format)

    target_logger_names = (
        "app.api.routes.job",
        "bhasha_mitra",
    )

    for logger_name in target_logger_names:
        target_logger = logging.getLogger(logger_name)
        target_logger.setLevel(logging.INFO)

        has_console = any(
            isinstance(handler, logging.StreamHandler)
            and getattr(handler, "_bhasha_job_console", False)
            for handler in target_logger.handlers
        )

        if has_console:
            continue

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        setattr(console_handler, "_bhasha_job_console", True)

        target_logger.addHandler(console_handler)
        target_logger.propagate = True


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

    _ensure_bootstrap_logging()

    try:

        manager = ModelManager()
        manager.install_signal_handlers()

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

        _configure_background_file_logging()

        _configure_ai_file_logging()

        _ensure_job_console_logging()

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

        manager = ModelManager()
        manager.shutdown()

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

frontend_static_directory = (
    Path(__file__).resolve().parents[1] / "frontend" / "static"
).resolve()

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