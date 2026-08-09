"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : subtitle.py
Purpose     : Subtitle Generation API

Description:
    REST endpoint for subtitle generation.

    Backend provides:
        translation.json

    AI layer:
        • Reads translation.json
        • Converts timestamped segments into SubtitleRequest
        • Uses configured SubtitleService
        • Generates the configured subtitle format
        • Returns generated subtitle path

    No AI model is required for subtitle generation.

Author:
    Bhasha Mitra AI Team

Version:
    1.1
===============================================================================
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from ai.subtitle.models import (
    SubtitleRequest,
    SubtitleSegment,
)

from ai.core.service_registry import ServiceRegistry


router = APIRouter()


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

service = ServiceRegistry.subtitle_service()


# ---------------------------------------------------------------------------
# AI-009
# ---------------------------------------------------------------------------

@router.post(
    "/subtitle",
    summary="Generate Subtitle",
)
def generate_subtitle(
    translation_path: str,
    subtitle_format: str | None = None,
    language: str | None = None,
):
    """
    Generate subtitle from translation.json.

    Input:
        translation_path:
            Path to translation.json.

        subtitle_format:
            Optional configured subtitle format.

        language:
            Optional subtitle language.

    Output:
        {
            "status": "PASS",
            "subtitle_path": "..."
        }
    """

    try:

        # ------------------------------------------------------------------
        # Input file
        # ------------------------------------------------------------------

        input_path = Path(
            translation_path
        )

        if not input_path.exists():

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Translation file not found: "
                    f"{input_path}"
                ),
            )

        if not input_path.is_file():

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Translation path is not a file: "
                    f"{input_path}"
                ),
            )

        # ------------------------------------------------------------------
        # Read translation.json
        # ------------------------------------------------------------------

        try:

            translation_data = json.loads(
                input_path.read_text(
                    encoding="utf-8"
                )
            )

        except json.JSONDecodeError as exc:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid translation JSON.",
            ) from exc

        # ------------------------------------------------------------------
        # Read segments
        # ------------------------------------------------------------------

        segments = translation_data.get(
            "segments"
        )

        if not isinstance(
            segments,
            list,
        ) or not segments:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Translation contains no segments."
                ),
            )

        # ------------------------------------------------------------------
        # Convert to framework subtitle segments
        # ------------------------------------------------------------------

        subtitle_segments: list[
            SubtitleSegment
        ] = []

        for segment in segments:

            if not isinstance(
                segment,
                dict,
            ):

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Invalid subtitle segment."
                    ),
                )

            try:

                subtitle_segments.append(
                    SubtitleSegment(
                        start=float(
                            segment["start"]
                        ),
                        end=float(
                            segment["end"]
                        ),
                        text=str(
                            segment["text"]
                        ).strip(),
                    )
                )

            except (
                KeyError,
                TypeError,
                ValueError,
            ) as exc:

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Invalid subtitle segment data."
                    ),
                ) from exc

        # ------------------------------------------------------------------
        # Output path
        # ------------------------------------------------------------------
        #
        # The SubtitleService/formatter determines the actual format.
        # We only provide a destination based on the requested format.
        #
        # The format itself remains configuration-driven inside
        # SubtitleService.
        # ------------------------------------------------------------------

        extension = (
            subtitle_format
            or "srt"
        ).strip().lower()

        output_path = (
            input_path.parent
            / f"subtitle.{extension}"
        )

        # ------------------------------------------------------------------
        # Subtitle request
        # ------------------------------------------------------------------

        subtitle_request = SubtitleRequest(
            segments=subtitle_segments,
            output_path=output_path,
            subtitle_format=subtitle_format,
            language=language,
        )

        # ------------------------------------------------------------------
        # Generate
        # ------------------------------------------------------------------

        result = service.generate(
            subtitle_request
        )

        # ------------------------------------------------------------------
        # Backend contract
        # ------------------------------------------------------------------

        return {
            "status": "PASS",
            "subtitle_path": str(
                result.subtitle_path
            ),
        }

    except HTTPException:
        raise

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except FileExistsError as exc:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Subtitle output already exists.",
        ) from exc

    except OSError as exc:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to write subtitle output.",
        ) from exc

    except Exception:

        return {
            "status": "FAIL",
            "subtitle_path": None,
        }