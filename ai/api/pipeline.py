"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : pipeline.py
Purpose     : AI Pipeline Management API

Description
-----------
Manage AI pipeline execution.

Author
------
Bhasha Mitra AI Team

Version
-------
1.0
===============================================================================
"""

from fastapi import APIRouter, HTTPException

from ai.pipeline.manager import PipelineManager
from ai.pipeline.contracts import (
    PipelineStatusResult,
    PipelineCancelResult,
)

router = APIRouter()

manager = PipelineManager()


# -----------------------------------------------------------------------------
# AI-016
# -----------------------------------------------------------------------------

@router.get(
    "/pipeline/status/{job_id}",
    response_model=PipelineStatusResult,
    summary="Pipeline Status",
)
def pipeline_status(
    job_id: str,
):
    """
    Get pipeline execution status.
    """

    try:

        return manager.status(job_id)

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# -----------------------------------------------------------------------------
# AI-017
# -----------------------------------------------------------------------------

@router.post(
    "/pipeline/cancel/{job_id}",
    response_model=PipelineCancelResult,
    summary="Cancel Pipeline",
)
def cancel_pipeline(
    job_id: str,
):
    """
    Cancel running pipeline.
    """

    try:

        return manager.cancel(job_id)

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )