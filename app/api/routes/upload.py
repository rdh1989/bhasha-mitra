"""
===============================================================================
BHASHA MITRA

Module:
    upload.py

Layer:
    Presentation / API

Description:
    Handles selection of an existing local video file.

Responsibilities:
    - Receive the local video path and filename
    - Validate that the source file exists
    - Validate the supported video extension
    - Create and persist a TranslationJob
    - Queue background preprocessing
    - Return the generated job ID
    - Provide clear translation lifecycle logging

Important:
    The video itself is NOT uploaded or copied.

    Only the local:
        file_path
        file_name

    are passed to the backend.
===============================================================================
"""

from __future__ import annotations

import logging
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from pydantic import BaseModel

from app.application.dto.create_job_request import (
    CreateJobRequest,
)

from infrastructure.bootstrap.application_container import (
    ApplicationContainer,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    tags=["Upload"],
)


_ALLOWED_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
}


# =============================================================================
# Request
# =============================================================================

class UploadRequest(BaseModel):
    """
    Request containing an existing local video.
    """

    file_path: str

    file_name: str

    source_language: str = "auto_detect"

    target_language: str


# =============================================================================
# Application Container
# =============================================================================

def get_application_container(
    request: Request,
) -> ApplicationContainer:
    """
    Return the single ApplicationContainer owned by the application.
    """

    container = getattr(
        request.app.state,
        "application_container",
        None,
    )

    if container is None:

        logger.error(
            "APPLICATION CONTAINER NOT AVAILABLE"
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Bhasha Mitra application infrastructure "
                "is still initializing."
            ),
        )

    return container


# =============================================================================
# Translation Job
# =============================================================================

@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Select a local video",
)
def upload_video(
    request: UploadRequest,
    container: ApplicationContainer = Depends(
        get_application_container,
    ),
) -> dict:
    """
    Create a translation job for an existing local video.

    The video itself is NOT copied or uploaded.
    """

    logger.warning(
        "TRANSLATION REQUEST RECEIVED | "
        "file=%s | source=%s | target=%s",
        request.file_name,
        request.source_language,
        request.target_language,
    )

    # =========================================================================
    # Resolve source
    # =========================================================================

    video_path = (
        Path(request.file_path)
        .expanduser()
        .resolve()
    )

    logger.info(
        "TRANSLATION SOURCE RESOLVED | "
        "path=%s",
        video_path,
    )

    # =========================================================================
    # Validate source file
    # =========================================================================

    if not video_path.is_file():

        logger.error(
            "TRANSLATION SOURCE NOT FOUND | "
            "path=%s",
            video_path,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video file was not found.",
        )

    logger.info(
        "TRANSLATION SOURCE VALIDATED | "
        "path=%s | size=%d bytes",
        video_path,
        video_path.stat().st_size,
    )

    # =========================================================================
    # Validate filename
    # =========================================================================

    file_name = Path(
        request.file_name
    ).name

    if not file_name:

        logger.error(
            "TRANSLATION REQUEST REJECTED | "
            "reason=EMPTY_FILENAME"
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A video filename is required.",
        )

    # =========================================================================
    # Validate extension
    # =========================================================================

    extension = Path(
        file_name
    ).suffix.lower()

    if extension not in _ALLOWED_EXTENSIONS:

        logger.error(
            "TRANSLATION REQUEST REJECTED | "
            "file=%s | extension=%s",
            file_name,
            extension,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Supported video formats are "
                "MP4, MOV, AVI, MKV, and WEBM."
            ),
        )

    logger.info(
        "VIDEO VALIDATION PASSED | "
        "file=%s | extension=%s",
        file_name,
        extension,
    )

    # =========================================================================
    # Create Translation Job
    # =========================================================================

    logger.warning(
        "TRANSLATION JOB CREATION STARTED | "
        "file=%s",
        file_name,
    )

    try:

        job = container.job_service.create(
            CreateJobRequest(
                input_file=video_path,
                source_language=request.source_language,
                target_language=request.target_language,
            )
        )

    except Exception as exc:

        logger.exception(
            "TRANSLATION JOB CREATION FAILED | "
            "file=%s | error_type=%s | error=%s",
            video_path,
            type(exc).__name__,
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create translation job.",
        ) from exc

    logger.warning(
        "TRANSLATION JOB CREATED | "
        "job_id=%s | file=%s | status=%s",
        job.id,
        video_path,
        job.status.value,
    )

    # =========================================================================
    # Queue Background Preprocessing
    # =========================================================================

    logger.warning(
        "PREPROCESSING QUEUE REQUESTED | "
        "job_id=%s",
        job.id,
    )

    try:

        container.preprocessing_queue.put(
            job.id
        )

    except Exception as exc:

        logger.exception(
            "PREPROCESSING QUEUE FAILED | "
            "job_id=%s | error_type=%s | error=%s",
            job.id,
            type(exc).__name__,
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Translation job was created, "
                "but preprocessing could not be queued."
            ),
        ) from exc

    logger.warning(
        "JOB QUEUED FOR PREPROCESSING | "
        "job_id=%s | status=%s",
        job.id,
        job.status.value,
    )

    # =========================================================================
    # Translation Request Accepted
    # =========================================================================

    logger.warning(
        "TRANSLATION REQUEST ACCEPTED | "
        "job_id=%s | file=%s | "
        "next_stage=PREPROCESSING",
        job.id,
        file_name,
    )

    # =========================================================================
    # Response
    # =========================================================================

    return {
        "success": True,
        "job_id": job.id,
    }


# =============================================================================
# Local File Browser
# =============================================================================

@router.get(
    "/upload/browse",
    summary="Browse for a local video",
)
def browse_local_video() -> dict:
    """
    Open the native Windows file browser.

    The selected video is NOT uploaded.

    The endpoint returns only:
        file_path
        file_name
    """

    logger.info(
        "LOCAL VIDEO BROWSER OPENING"
    )

    root = tk.Tk()

    try:

        root.withdraw()

        root.attributes(
            "-topmost",
            True,
        )

        file_path = filedialog.askopenfilename(
            title="Select video - Bhasha Mitra",
            filetypes=[
                (
                    "Video files",
                    "*.mp4 *.mov *.avi *.mkv *.webm",
                ),
                (
                    "MP4 files",
                    "*.mp4",
                ),
                (
                    "MOV files",
                    "*.mov",
                ),
                (
                    "AVI files",
                    "*.avi",
                ),
                (
                    "MKV files",
                    "*.mkv",
                ),
                (
                    "WEBM files",
                    "*.webm",
                ),
            ],
        )

    finally:

        root.destroy()

    # =========================================================================
    # User Cancelled
    # =========================================================================

    if not file_path:

        logger.info(
            "LOCAL VIDEO SELECTION CANCELLED"
        )

        return {
            "success": True,
            "cancelled": True,
        }

    # =========================================================================
    # Validate Selected File
    # =========================================================================

    selected_file = (
        Path(file_path)
        .expanduser()
        .resolve()
    )

    logger.info(
        "LOCAL VIDEO SELECTED | "
        "path=%s",
        selected_file,
    )

    if not selected_file.is_file():

        logger.error(
            "SELECTED VIDEO DOES NOT EXIST | "
            "path=%s",
            selected_file,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected video file does not exist.",
        )

    # =========================================================================
    # Validate Extension
    # =========================================================================

    if (
        selected_file.suffix.lower()
        not in _ALLOWED_EXTENSIONS
    ):

        logger.error(
            "SELECTED VIDEO HAS UNSUPPORTED EXTENSION | "
            "path=%s | extension=%s",
            selected_file,
            selected_file.suffix,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Supported video formats are "
                "MP4, MOV, AVI, MKV and WEBM."
            ),
        )

    logger.info(
        "LOCAL VIDEO SELECTION VALIDATED | "
        "file=%s | size=%d bytes",
        selected_file.name,
        selected_file.stat().st_size,
    )

    # =========================================================================
    # Return Path Only
    # =========================================================================

    logger.info(
        "LOCAL VIDEO PATH RETURNED | "
        "file=%s",
        selected_file.name,
    )

    return {
        "success": True,
        "cancelled": False,
        "file_path": str(selected_file),
        "file_name": selected_file.name,
    }