"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : translation.py
Purpose     : Translation API

Description:
    REST endpoint for file-based translation.

    Backend provides:
        transcript.json

    AI layer:
        • Reads transcript.json
        • Groups timestamped segments into translation units
        • Uses existing TranslationService
        • Preserves source text and timing information
        • Saves translation.json

Pipeline
--------
transcript.json
    ↓
Context-aware segment grouping
    ↓
Existing TranslationService
    ↓
translation.json

Author:
    Bhasha Mitra AI Team

Version:
    1.2
===============================================================================
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ai.translation.models import TranslationRequest
from ai.translation.timing import align_translation_words
from ai.core.service_registry import ServiceRegistry


router = APIRouter()

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Service
# --------------------------------------------------------------------------

service = ServiceRegistry.translation_service()


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

MAX_TRANSLATION_CHUNK_SIZE = 500

# Sentence boundary takes priority over MAX_TRANSLATION_CHUNK_SIZE (see grouping
# preference below). This hard ceiling only forces a split when a sentence
# never terminates (e.g. missing punctuation from ASR output), preventing
# clauses from being cut apart mid-sentence before translation.
HARD_MAX_TRANSLATION_CHUNK_SIZE = MAX_TRANSLATION_CHUNK_SIZE * 2


# --------------------------------------------------------------------------
# Segment Grouping
# --------------------------------------------------------------------------

def _build_translation_units(
    segments: list[dict],
) -> list[list[dict]]:
    """
    Group consecutive transcript segments into logical translation units.

    Grouping preference:
        1. Sentence boundary
        2. Maximum configured source-text size
        3. Word boundary

    Original segment timing is retained by the unit.
    """

    units: list[list[dict]] = []

    current_unit: list[dict] = []
    current_length = 0

    for segment in segments:

        text = str(
            segment.get("text", "")
        ).strip()

        if not text:
            continue

        segment_length = len(text)

        additional_length = (
            segment_length
            if not current_unit
            else segment_length + 1
        )

        # --------------------------------------------------------------
        # Add segment if it fits
        # --------------------------------------------------------------

        if (
            current_unit
            and
            current_length
            + additional_length
            <= HARD_MAX_TRANSLATION_CHUNK_SIZE
        ):

            current_unit.append(segment)

            current_length += (
                additional_length
            )

            # ----------------------------------------------------------
            # Sentence boundary
            # ----------------------------------------------------------

            if re.search(
                r"[.!?।！？]\s*$",
                text,
            ):

                units.append(
                    current_unit
                )

                current_unit = []
                current_length = 0

            continue

        # --------------------------------------------------------------
        # Current unit cannot accept another segment
        # --------------------------------------------------------------

        if current_unit:

            units.append(
                current_unit
            )

            current_unit = []
            current_length = 0

        # --------------------------------------------------------------
        # Segment itself fits
        # --------------------------------------------------------------

        if segment_length <= MAX_TRANSLATION_CHUNK_SIZE:

            current_unit = [segment]
            current_length = segment_length

            if re.search(
                r"[.!?।！？]\s*$",
                text,
            ):

                units.append(
                    current_unit
                )

                current_unit = []
                current_length = 0

            continue

        # --------------------------------------------------------------
        # Single segment is larger than the limit.
        #
        # Split only at word boundaries.
        # --------------------------------------------------------------

        words = text.split()

        word_parts: list[str] = []
        word_length = 0

        for word in words:

            additional_length = (
                len(word)
                if not word_parts
                else len(word) + 1
            )

            if (
                word_parts
                and
                word_length
                + additional_length
                > MAX_TRANSLATION_CHUNK_SIZE
            ):

                units.append(
                    [
                        {
                            "id": segment["id"],
                            "start": segment["start"],
                            "end": segment["end"],
                            "text": " ".join(
                                word_parts
                            ),
                        }
                    ]
                )

                word_parts = []
                word_length = 0

            word_parts.append(word)

            word_length += (
                additional_length
            )

        if word_parts:

            units.append(
                [
                    {
                        "id": segment["id"],
                        "start": segment["start"],
                        "end": segment["end"],
                        "text": " ".join(
                            word_parts
                        ),
                    }
                ]
            )

    if current_unit:

        units.append(
            current_unit
        )

    return units


# --------------------------------------------------------------------------
# Translation Unit
# --------------------------------------------------------------------------

def _translate_unit(
    unit: list[dict],
    source_language: str,
    target_language: str,
) -> dict:
    """
    Translate one logical unit.

    Multiple transcript segments become one translated segment.

    Both source and translated text are retained so downstream
    dubbing and synchronization have access to the original text.
    """

    source_text = " ".join(
        str(segment["text"]).strip()
        for segment in unit
    ).strip()

    request = TranslationRequest(
        text=source_text,
        source_language=source_language,
        target_language=target_language,
    )

    result = service.translate(
        request
    )

    unit_start = unit[0]["start"]
    unit_end = unit[-1]["end"]

    # Word-level ASR timing carried over from transcript.json, used to
    # pace the translated words instead of copying source timestamps
    # (translation may reorder/merge/split words, so a 1:1 mapping would
    # be wrong).
    source_words = [
        word
        for segment in unit
        for word in segment.get("words", []) or []
    ]

    translated_words = align_translation_words(
        translated_text=result.translated_text.strip(),
        unit_start=unit_start,
        unit_end=unit_end,
        source_words=source_words,
    )

    return {
        "id": unit[0]["id"],
        "start": unit_start,
        "end": unit_end,
        "source_text": source_text,
        "translated_text": result.translated_text.strip(),
        "words": [
            {
                "word": word.word,
                "start": word.start,
                "end": word.end,
            }
            for word in translated_words
        ],
    }


# --------------------------------------------------------------------------
# AI-006
# --------------------------------------------------------------------------

@router.post(
    "/translate",
    summary="Translate Transcript",
)
def translate(
    transcript_path: str,
    source_language: str,
    target_language: str,
):
    """
    Translate transcript.json and generate translation.json.
    """

    try:

        # --------------------------------------------------------------
        # Input file
        # --------------------------------------------------------------

        input_path = Path(
            transcript_path
        )

        if not input_path.exists():

            raise HTTPException(
                status_code=404,
                detail=(
                    f"Transcript file not found: "
                    f"{input_path}"
                ),
            )

        if not input_path.is_file():

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Transcript path is not a file: "
                    f"{input_path}"
                ),
            )

        # --------------------------------------------------------------
        # Read transcript.json
        # --------------------------------------------------------------

        try:

            transcript_data = json.loads(
                input_path.read_text(
                    encoding="utf-8"
                )
            )

        except json.JSONDecodeError as exc:

            raise HTTPException(
                status_code=400,
                detail="Invalid transcript JSON.",
            ) from exc

        segments = transcript_data.get(
            "segments"
        )

        if not isinstance(
            segments,
            list,
        ) or not segments:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Transcript contains no segments."
                ),
            )

        # --------------------------------------------------------------
        # Build translation units
        # --------------------------------------------------------------

        translation_units = (
            _build_translation_units(
                segments
            )
        )

        # --------------------------------------------------------------
        # Translate
        # --------------------------------------------------------------

        translated_segments: list[dict] = []

        for unit in translation_units:

            translated_segment = _translate_unit(
                unit=unit,
                source_language=source_language,
                target_language=target_language,
            )

            translated_segments.append(
                translated_segment
            )

        # --------------------------------------------------------------
        # Save translation.json
        # --------------------------------------------------------------

        translation_path = (
            input_path.parent
            / "translation.json"
        )

        translation_path.write_text(
            json.dumps(
                {
                    "segments": translated_segments
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        # --------------------------------------------------------------
        # Backend contract
        # --------------------------------------------------------------

        return {
            "status": "PASS",
            "translation_path": str(
                translation_path
            ),
        }

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "TRANSLATION API FAILED | "
            "transcript=%s | "
            "source=%s | "
            "target=%s | "
            "error=%s",
            transcript_path,
            source_language,
            target_language,
            exc,
        )

        return {
            "status": "FAIL",
            "translation_path": None,
            "error_message": str(exc),
        }