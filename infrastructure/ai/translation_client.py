"""
===============================================================================
BHASHA MITRA

Module:
    translation_client.py

Layer:
    Infrastructure / AI

Description:
    Backend client for the AI Framework Translation API.

Responsibilities:
    - Call the AI Framework /api/ai/translate endpoint
    - Provide transcript JSON path
    - Provide source language
    - Provide target language
    - Wait for long-running translation requests
    - Return the translation response

The AI Framework owns:
    - Translation
    - Long-text/context grouping
    - Translation artifact generation

The Backend owns:
    - HTTP integration
    - Workflow orchestration
    - Error handling
    - Job state

Timeout strategy:
    Connection timeout:
        Short

    Write timeout:
        Short

    Pool timeout:
        Short

    Read timeout:
        Long

Reason:
    Translation is a long-running synchronous AI operation.
    The backend must not terminate the request merely because
    translation takes several minutes.
===============================================================================
"""

from __future__ import annotations

import logging
import time

import httpx


logger = logging.getLogger(__name__)


class TranslationClient:
    """
    Client for the AI Framework /api/ai/translate API.

The endpoint parameters are sent as query parameters.
    """

    # =========================================================================
    # Timeout configuration
    # =========================================================================

    DEFAULT_CONNECT_TIMEOUT = 30.0
    DEFAULT_WRITE_TIMEOUT = 30.0
    DEFAULT_POOL_TIMEOUT = 30.0

    # -------------------------------------------------------------------------
    # Translation can take several minutes.
    #
    # 30 minutes is intentionally used instead of 300 seconds.
    # -------------------------------------------------------------------------

    DEFAULT_READ_TIMEOUT = 1800.0

    # =========================================================================
    # Constructor
    # =========================================================================

    def __init__(
        self,
        base_url: str,
        timeout: float = DEFAULT_READ_TIMEOUT,
    ) -> None:
        """
        Initialize the Translation API client.

        Args:
            base_url:
                AI Framework base URL.

            timeout:
                Maximum time allowed while waiting for the AI
                Framework response.

                Default:
                    1800 seconds = 30 minutes.
        """

        if not base_url:
            raise ValueError(
                "AI Framework base URL cannot be empty."
            )

        if timeout <= 0:
            raise ValueError(
                "Translation timeout must be greater than zero."
            )

        self._url = (
            f"{base_url.rstrip('/')}/api/ai/translate"
        )

        self._timeout = httpx.Timeout(
            connect=self.DEFAULT_CONNECT_TIMEOUT,
            read=timeout,
            write=self.DEFAULT_WRITE_TIMEOUT,
            pool=self.DEFAULT_POOL_TIMEOUT,
        )

        logger.info(
            "TRANSLATION CLIENT INITIALIZED | "
            "url=%s | "
            "connect_timeout=%ss | "
            "read_timeout=%ss | "
            "write_timeout=%ss | "
            "pool_timeout=%ss",
            self._url,
            self.DEFAULT_CONNECT_TIMEOUT,
            timeout,
            self.DEFAULT_WRITE_TIMEOUT,
            self.DEFAULT_POOL_TIMEOUT,
        )

    # =========================================================================
    # Translation
    # =========================================================================

    def translate(
        self,
        transcript_path: str,
        source_language: str,
        target_language: str,
    ) -> dict:
        """
        Translate the supplied transcript JSON.

        The AI Framework handles:
            - transcript loading
            - long-text grouping
            - context management
            - translation
            - translation artifact generation

        Returns:
            AI Framework response dictionary.
        """

        if not transcript_path:

            raise ValueError(
                "Transcript path cannot be empty."
            )

        if not source_language:

            raise ValueError(
                "Source language cannot be empty."
            )

        if not target_language:

            raise ValueError(
                "Target language cannot be empty."
            )

        logger.warning(
            "TRANSLATION API REQUEST STARTED | "
            "url=%s | "
            "transcript=%s | "
            "source=%s | "
            "target=%s | "
            "read_timeout=%ss",
            self._url,
            transcript_path,
            source_language,
            target_language,
            self._timeout.read,
        )

        start_time = time.monotonic()

        try:

            # AI Framework /api/ai/translate expects these values
            # as QUERY PARAMETERS, not a JSON request body.
            #
            # Sending them via json= causes FastAPI to return:
            #   422 Unprocessable Content
            #   query.transcript_path -> Field required
            #   query.source_language -> Field required
            #   query.target_language -> Field required
            response = httpx.post(
                self._url,
                params={
                    "transcript_path": transcript_path,
                    "source_language": source_language,
                    "target_language": target_language,
                },
                timeout=self._timeout,
            )

        except httpx.ReadTimeout:

            elapsed = (
                time.monotonic()
                - start_time
            )

            logger.exception(
                "TRANSLATION API READ TIMEOUT | "
                "url=%s | "
                "transcript=%s | "
                "elapsed=%.2fs | "
                "configured_read_timeout=%ss",
                self._url,
                transcript_path,
                elapsed,
                self._timeout.read,
            )

            raise

        except httpx.ConnectTimeout:

            elapsed = (
                time.monotonic()
                - start_time
            )

            logger.exception(
                "TRANSLATION API CONNECTION TIMEOUT | "
                "url=%s | "
                "elapsed=%.2fs",
                self._url,
                elapsed,
            )

            raise

        except httpx.HTTPError:

            elapsed = (
                time.monotonic()
                - start_time
            )

            logger.exception(
                "TRANSLATION HTTP REQUEST FAILED | "
                "url=%s | "
                "transcript=%s | "
                "elapsed=%.2fs",
                self._url,
                transcript_path,
                elapsed,
            )

            raise

        elapsed = (
            time.monotonic()
            - start_time
        )

        # =====================================================================
        # Log HTTP response
        # =====================================================================

        logger.info(
            "TRANSLATION API RESPONSE RECEIVED | "
            "status_code=%s | "
            "elapsed=%.2fs",
            response.status_code,
            elapsed,
        )

        # =====================================================================
        # Handle HTTP errors
        # =====================================================================

        if response.is_error:

            logger.error(
                "TRANSLATION API ERROR | "
                "status=%s | "
                "elapsed=%.2fs | "
                "response=%s",
                response.status_code,
                elapsed,
                response.text[:2000],
            )

            response.raise_for_status()

        # =====================================================================
        # Parse response
        # =====================================================================

        try:

            result = response.json()

        except ValueError:

            logger.exception(
                "TRANSLATION API RETURNED INVALID JSON | "
                "status=%s | "
                "elapsed=%.2fs | "
                "response=%s",
                response.status_code,
                elapsed,
                response.text[:2000],
            )

            raise RuntimeError(
                "Translation API returned invalid JSON."
            )

        # =====================================================================
        # Validate response
        # =====================================================================

        if not isinstance(
            result,
            dict,
        ):

            raise RuntimeError(
                "Translation API returned "
                "an invalid response."
            )

        logger.info(
            "TRANSLATION API RESPONSE VALIDATED | "
            "status=%s | "
            "elapsed=%.2fs | "
            "result_status=%s",
            response.status_code,
            elapsed,
            result.get("status"),
        )

        # =====================================================================
        # Successful response
        # =====================================================================

        if result.get("status") == "PASS":

            logger.warning(
                "TRANSLATION API REQUEST COMPLETED | "
                "transcript=%s | "
                "source=%s | "
                "target=%s | "
                "translation=%s | "
                "elapsed=%.2fs",
                transcript_path,
                source_language,
                target_language,
                result.get(
                    "translation_path"
                ),
                elapsed,
            )

        else:

            logger.error(
                "TRANSLATION API RETURNED NON-PASS | "
                "transcript=%s | "
                "source=%s | "
                "target=%s | "
                "result_status=%s | "
                "elapsed=%.2fs",
                transcript_path,
                source_language,
                target_language,
                result.get("status"),
                elapsed,
            )

        return result