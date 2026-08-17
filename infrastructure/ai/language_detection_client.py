"""
===============================================================================
BHASHA MITRA

Module:
    infrastructure/ai/language_detection_client.py

Layer:
    Infrastructure / AI

Description:
    Backend client for the AI Framework Language Detection API.

Responsibilities:
    - Call the AI Framework language detection endpoint.
    - Pass the local transcript/text to the AI Framework.
    - Validate HTTP responses.
    - Provide detailed logging.
===============================================================================
"""

from __future__ import annotations

import logging
import time

import httpx

from app.security import internal_api_headers

logger = logging.getLogger(__name__)


class LanguageDetectionClient:
    """
    Calls the AI Framework /api/ai/language-detection endpoint.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 120.0,
    ) -> None:

        self._url = (
            f"{base_url.rstrip('/')}/api/ai/language-detection"
        )

        self._timeout = timeout

        logger.info(
            "LANGUAGE DETECTION CLIENT INITIALIZED | "
            "url=%s | timeout=%ss",
            self._url,
            self._timeout,
        )

    def detect(
        self,
        text: str,
    ) -> dict:
        """
        Detect the language of supplied text.

        The AI Framework owns the actual language detection
        implementation/provider.
        """

        if not text or not text.strip():

            raise ValueError(
                "Text for language detection cannot be empty."
            )

        logger.info(
            "LANGUAGE DETECTION REQUEST STARTED | "
            "text_length=%d",
            len(text),
        )

        start_time = time.monotonic()

        try:

            response = httpx.post(
                self._url,
                headers=internal_api_headers(),
                json={
                    "text": text,
                },
                timeout=self._timeout,
            )

            elapsed = time.monotonic() - start_time

            logger.info(
                "LANGUAGE DETECTION API RESPONSE RECEIVED | "
                "status=%s | elapsed=%.2fs",
                response.status_code,
                elapsed,
            )

            if response.status_code >= 400:

                logger.error(
                    "LANGUAGE DETECTION API ERROR | "
                    "status=%s | elapsed=%.2fs | "
                    "response=%s",
                    response.status_code,
                    elapsed,
                    response.text[:2000],
                )

                response.raise_for_status()

            try:

                result = response.json()

            except Exception as exc:

                logger.exception(
                    "LANGUAGE DETECTION API INVALID JSON | "
                    "status=%s | elapsed=%.2fs | "
                    "error_type=%s | error=%s",
                    response.status_code,
                    elapsed,
                    type(exc).__name__,
                    exc,
                )

                raise RuntimeError(
                    "Language detection API returned "
                    "an invalid JSON response."
                ) from exc

            if not isinstance(result, dict):

                logger.error(
                    "LANGUAGE DETECTION API RETURNED INVALID TYPE | "
                    "result_type=%s",
                    type(result).__name__,
                )

                raise RuntimeError(
                    "Language detection API returned "
                    "an invalid response type."
                )

            logger.info(
                "LANGUAGE DETECTION COMPLETED | "
                "elapsed=%.2fs | result=%s",
                elapsed,
                result,
            )

            return result

        except httpx.HTTPError:

            elapsed = time.monotonic() - start_time

            logger.exception(
                "LANGUAGE DETECTION HTTP REQUEST FAILED | "
                "elapsed=%.2fs | url=%s",
                elapsed,
                self._url,
            )

            raise

        except Exception:

            elapsed = time.monotonic() - start_time

            logger.exception(
                "LANGUAGE DETECTION REQUEST FAILED | "
                "elapsed=%.2fs",
                elapsed,
            )

            raise