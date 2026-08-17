"""
===============================================================================
BHASHA MITRA

Module:
    subtitle_client.py

Layer:
    Infrastructure / AI

Description:
    Backend client for the AI Framework Subtitle API.

Responsibilities:
    - Call the AI Framework /subtitle endpoint
    - Provide translation JSON path
    - Provide subtitle format and language
    - Return the subtitle generation response

The AI Framework owns:
    - Subtitle generation
    - Subtitle file creation

The Backend owns:
    - AI Framework integration
    - Workflow orchestration
    - Job state
===============================================================================
"""

from __future__ import annotations

import logging
import time

import httpx

from app.security import internal_api_headers

logger = logging.getLogger(__name__)


class SubtitleClient:
    """
    Client for the AI Framework /subtitle API.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 300.0,
    ) -> None:

        self._url = (
            f"{base_url.rstrip('/')}/api/ai/subtitle"
        )

        self._timeout = timeout

        logger.info(
            "SUBTITLE CLIENT INITIALIZED | "
            "url=%s | timeout=%ss",
            self._url,
            self._timeout,
        )

    def generate(
        self,
        translation_path: str,
        subtitle_format: str,
        language: str,
    ) -> dict:
        """
        Generate subtitles from the translated JSON.
        """

        logger.info(
            "SUBTITLE API REQUEST STARTED | "
            "translation=%s | format=%s | language=%s",
            translation_path,
            subtitle_format,
            language,
        )

        start_time = time.monotonic()

        try:

            response = httpx.post(
                self._url,
                headers=internal_api_headers(),
                json={
                    "translation_path": translation_path,
                    "subtitle_format": subtitle_format,
                    "language": language,
                },
                timeout=self._timeout,
            )

        except Exception as exc:

            elapsed = (
                time.monotonic() - start_time
            )

            logger.exception(
                "SUBTITLE API REQUEST FAILED | "
                "elapsed=%.2fs | "
                "translation=%s | "
                "error_type=%s | "
                "error=%s",
                elapsed,
                translation_path,
                type(exc).__name__,
                exc,
            )

            raise

        elapsed = (
            time.monotonic() - start_time
        )

        logger.info(
            "SUBTITLE API RESPONSE RECEIVED | "
            "status=%s | "
            "elapsed=%.2fs",
            response.status_code,
            elapsed,
        )

        if response.status_code >= 400:

            logger.error(
                "SUBTITLE API ERROR | "
                "status=%s | "
                "elapsed=%.2fs | "
                "response=%s",
                response.status_code,
                elapsed,
                response.text,
            )

        response.raise_for_status()

        try:

            result = response.json()

        except Exception as exc:

            logger.exception(
                "SUBTITLE API INVALID JSON RESPONSE | "
                "status=%s | "
                "elapsed=%.2fs | "
                "error_type=%s | "
                "error=%s",
                response.status_code,
                elapsed,
                type(exc).__name__,
                exc,
            )

            raise RuntimeError(
                "Subtitle API returned an invalid JSON response."
            ) from exc

        logger.info(
            "SUBTITLE API RESPONSE VALIDATED | "
            "result_type=%s",
            type(result).__name__,
        )

        if not isinstance(
            result,
            dict,
        ):

            raise RuntimeError(
                "Subtitle API returned an invalid response type."
            )

        logger.info(
            "SUBTITLE GENERATION RESPONSE RECEIVED | "
            "status=%s | "
            "subtitle_path=%s | "
            "elapsed=%.2fs",
            result.get("status"),
            result.get("subtitle_path"),
            elapsed,
        )

        return result