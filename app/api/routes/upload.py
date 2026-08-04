"""
Upload API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile, status

router = APIRouter(tags=["Upload"])


@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a video",
)
async def upload_video(
    file: UploadFile = File(...),
) -> dict:
    """
    Upload a video file.
    """

    # TODO: Delegate to UploadController

    return {
        "success": True,
        "message": "Upload API not implemented.",
        "filename": file.filename,
    }