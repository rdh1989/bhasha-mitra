"""
Translation History API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, status

router = APIRouter(tags=["Translation History"])


@router.get(
    "/translations",
    status_code=status.HTTP_200_OK,
    summary="Get translation history",
)
async def get_translations() -> dict:
    """
    Return all translation jobs.

    TODO:
        Replace with TranslationService once implemented.
    """

    return {
        "success": True,
        "count": 3,
        "translations": [
            {
                "job_id": "JOB-1001",
                "file_name": "training_video.mp4",
                "source_language": "English",
                "target_language": "Marathi",
                "status": "Completed",
                "progress": 100,
                "created_at": "2026-07-26 09:30",
            },
            {
                "job_id": "JOB-1002",
                "file_name": "meeting.mp4",
                "source_language": "Hindi",
                "target_language": "Marathi",
                "status": "Processing",
                "progress": 68,
                "created_at": "2026-07-26 10:15",
            },
            {
                "job_id": "JOB-1003",
                "file_name": "demo.mov",
                "source_language": "English",
                "target_language": "Gujarati",
                "status": "Failed",
                "progress": 15,
                "created_at": "2026-07-26 11:05",
            },
        ],
    }