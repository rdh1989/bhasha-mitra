"""
===============================================================================
BHASHA MITRA

Module:
    dubbing_client.py

Layer:
    Infrastructure / AI

Description:
    Backend client for the AI Framework /api/ai/dubbing endpoint.

Responsibilities:
    - Call the AI Framework /api/ai/dubbing endpoint
    - Provide translated text path
    - Provide target language
    - Provide selected voice
    - Provide backend-owned output path
    - Return the dubbing response

The AI Framework owns:
    - Dubbing
    - TTS
    - Dubbed audio generation

The Backend owns:
    - API integration
    - Workflow orchestration
    - Job state
    - Output management
===============================================================================
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.security import internal_api_headers

logger = logging.getLogger(__name__)


class DubbingClient:
    """
    Client for the AI Framework /api/ai/dubbing API.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 18000.0,
    ) -> None:

        self._url = (
            f"{base_url.rstrip('/')}/api/ai/dubbing"
        )

        self._timeout = timeout

    @staticmethod
    def _extract_error_detail(
        error_body: Any,
    ) -> str:
        """
        Normalize AI Framework error payloads into one readable message.
        """

        if isinstance(error_body, dict):

            detail = error_body.get("detail")

            if isinstance(detail, str) and detail.strip():
                return detail.strip()

            if isinstance(detail, list):
                parts = []

                for item in detail:

                    if isinstance(item, dict):
                        msg = item.get("msg") or item.get("message")
                        if isinstance(msg, str) and msg.strip():
                            parts.append(msg.strip())
                    elif isinstance(item, str) and item.strip():
                        parts.append(item.strip())

                if parts:
                    return "; ".join(parts)

            message = error_body.get("message")

            if isinstance(message, str) and message.strip():
                return message.strip()

        if isinstance(error_body, str) and error_body.strip():
            return error_body.strip()

        return "Unknown dubbing API error."

    def generate(
        self,
        translated_text_path: str,
        language: str,
        voice: str,
        output_path: str,
    ) -> dict:
        """
        Generate dubbed audio using the AI Framework.

        The AI Framework /api/ai/dubbing endpoint expects the
        following request body:

            {
                "translated_text_path": "...",
                "language": "...",
                "voice": "...",
                "output_path": "..."
            }
        """

        if not translated_text_path:
            raise ValueError(
                "Translated text path cannot be empty."
            )

        if not language:
            raise ValueError(
                "Dubbing language cannot be empty."
            )

        if not voice:
            raise ValueError(
                "Dubbing voice cannot be empty."
            )

        if not output_path:
            raise ValueError(
                "Dubbing output path cannot be empty."
            )

        payload = {
            "translated_text_path": translated_text_path,
            "language": language,
            "voice": voice,
            "output_path": output_path,
        }

        logger.info(
            "DUBBING API REQUEST STARTED | "
            "url=%s | "
            "translated_text=%s | "
            "language=%s | "
            "voice=%s | "
            "output=%s | "
            "read_timeout=%.1fs",
            self._url,
            translated_text_path,
            language,
            voice,
            output_path,
            self._timeout,
        )

        try:

            response = httpx.post(
                self._url,
                headers=internal_api_headers(),
                json=payload,
                timeout=httpx.Timeout(
                    connect=30.0,
                    read=self._timeout,
                    write=30.0,
                    pool=30.0,
                ),
            )

        except httpx.TimeoutException as exc:

            logger.exception(
                "DUBBING API TIMEOUT | "
                "url=%s | "
                "translated_text=%s | "
                "output=%s",
                self._url,
                translated_text_path,
                output_path,
            )

            raise RuntimeError(
                "Dubbing API request timed out."
            ) from exc

        except httpx.HTTPError as exc:

            logger.exception(
                "DUBBING API HTTP REQUEST FAILED | "
                "url=%s | "
                "translated_text=%s | "
                "output=%s",
                self._url,
                translated_text_path,
                output_path,
            )

            raise RuntimeError(
                "Dubbing API request failed."
            ) from exc

        # =====================================================================
        # Handle HTTP errors.
        # =====================================================================

        if response.is_error:

            try:
                error_body: Any = response.json()
            except ValueError:
                error_body = response.text

            logger.error(
                "DUBBING API ERROR | "
                "status=%s | "
                "response=%s",
                response.status_code,
                error_body,
            )

            detail = self._extract_error_detail(
                error_body
            )

            raise RuntimeError(
                "Dubbing API returned HTTP "
                f"{response.status_code}: {detail}"
            )

        # =====================================================================
        # Parse response
        # =====================================================================

        try:

            result = response.json()

        except ValueError as exc:

            logger.error(
                "DUBBING API RETURNED INVALID JSON | "
                "status=%s | "
                "response=%s",
                response.status_code,
                response.text[:2000],
            )

            raise RuntimeError(
                "Dubbing API returned an invalid JSON response."
            ) from exc

        if not isinstance(result, dict):

            raise RuntimeError(
                "Dubbing API returned an invalid response type."
            )

        logger.info(
            "DUBBING API REQUEST COMPLETED | "
            "translated_text=%s | "
            "language=%s | "
            "voice=%s | "
            "output=%s",
            translated_text_path,
            language,
            voice,
            output_path,
        )

        return result