"""
===============================================================================
BHASHA MITRA

Module:
    transcript_client.py

Layer:
    Infrastructure / AI

Description:
    Backend client for the AI Framework Transcript API.

Responsibilities:
    - Call AI Framework transcript endpoint
    - Provide sufficient timeout for local ASR processing
    - Log request lifecycle
    - Log HTTP and timeout failures
===============================================================================
"""

from __future__ import annotations

import logging
import time

import httpx


logger = logging.getLogger(__name__)


class TranscriptClient:
    """
    Calls the AI Framework /transcript endpoint.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 1800.0,
    ) -> None:

        self._url = (
            f"{base_url.rstrip('/')}/api/ai/transcript"
        )

        self._timeout = timeout

        logger.info(
            "TranscriptClient initialized | "
            "url=%s | timeout=%ss",
            self._url,
            self._timeout,
        )

    # =========================================================================
    # Generate Transcript
    # =========================================================================

    def generate(
        self,
        audio_path: str,
    ) -> dict:
        """
        Generate a transcript for the supplied audio file.
        """

        started_at = time.monotonic()

        logger.info(
            "TRANSCRIPT REQUEST STARTED | "
            "audio=%s | timeout=%ss",
            audio_path,
            self._timeout,
        )

        try:

            response = httpx.post(
                self._url,
                json={
                    "audio_path": audio_path,
                },
                timeout=self._timeout,
            )

            elapsed = (
                time.monotonic()
                - started_at
            )

            logger.info(
                "TRANSCRIPT RESPONSE RECEIVED | "
                "status=%s | elapsed=%.2fs | audio=%s",
                response.status_code,
                elapsed,
                audio_path,
            )

            if response.status_code >= 400:

                logger.error(
                    "TRANSCRIPT API ERROR | "
                    "status=%s | elapsed=%.2fs | "
                    "response=%s",
                    response.status_code,
                    elapsed,
                    response.text[:2000],
                )

            response.raise_for_status()

            result = response.json()

            logger.info(
                "TRANSCRIPT REQUEST COMPLETED | "
                "elapsed=%.2fs | audio=%s",
                elapsed,
                audio_path,
            )

            return result

        except httpx.ReadTimeout as exc:

            elapsed = (
                time.monotonic()
                - started_at
            )

            logger.error(
                "TRANSCRIPT REQUEST TIMEOUT | "
                "elapsed=%.2fs | timeout=%ss | "
                "audio=%s",
                elapsed,
                self._timeout,
                audio_path,
            )

            raise RuntimeError(
                "AI Transcript request timed out "
                f"after {elapsed:.2f} seconds."
            ) from exc

        except httpx.HTTPStatusError as exc:

            elapsed = (
                time.monotonic()
                - started_at
            )

            logger.error(
                "TRANSCRIPT HTTP ERROR | "
                "status=%s | elapsed=%.2fs | "
                "audio=%s | response=%s",
                exc.response.status_code,
                elapsed,
                audio_path,
                exc.response.text[:2000],
            )

            raise

        except httpx.HTTPError as exc:

            elapsed = (
                time.monotonic()
                - started_at
            )

            logger.exception(
                "TRANSCRIPT HTTP CLIENT ERROR | "
                "elapsed=%.2fs | audio=%s",
                elapsed,
                audio_path,
            )

            raise

        except Exception:

            elapsed = (
                time.monotonic()
                - started_at
            )

            logger.exception(
                "TRANSCRIPT REQUEST FAILED | "
                "elapsed=%.2fs | audio=%s",
                elapsed,
                audio_path,
            )

            raise