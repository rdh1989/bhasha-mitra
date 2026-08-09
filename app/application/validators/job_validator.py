"""
===============================================================================
BHASHA MITRA

Module:
    job_validator.py

Layer:
    Application / Validation

Description:
    Validates Translation Job creation requests.

Language handling:
    source_language = "auto"
        Means the source language must be detected from the video.

    target_language
        Must be an explicitly supported language.

Responsibilities:
    - Validate input video
    - Validate source language
    - Validate target language
    - Validate job creation request

No new external dependencies are introduced.
===============================================================================
"""

from __future__ import annotations

from pathlib import Path

from app.application.dto.create_job_request import (
    CreateJobRequest,
)

from app.application.exceptions.unsupported_language_error import (
    UnsupportedLanguageError,
)


class JobValidator:
    """
    Validates Translation Job requests.
    """

    # =========================================================================
    # Constants
    # =========================================================================

    AUTO_LANGUAGE = "auto"

    SUPPORTED_LANGUAGES = {
        "en",
        "hi",
        "mr",
        "ta",
        "te",
        "kn",
        "gu",
        "bn",
    }

    # =========================================================================
    # Initialization
    # =========================================================================

    def __init__(
        self,
        job_repository=None,
        configuration_manager=None,
    ) -> None:
        """
        Initialize the validator.

        The dependencies are accepted for compatibility with the existing
        ApplicationContainer wiring.

        Validation itself does not require either dependency.
        """

        self._job_repository = job_repository
        self._configuration_manager = (
            configuration_manager
        )

    # =========================================================================
    # Create Job
    # =========================================================================

    def validate_create_request(
        self,
        request: CreateJobRequest,
    ) -> None:
        """
        Validate a Create Translation Job request.
        """

        self._validate_input_file(
            request.input_file
        )

        self._validate_languages(
            request.source_language,
            request.target_language,
        )

    # =========================================================================
    # Input File
    # =========================================================================

    def _validate_input_file(
        self,
        input_file: Path,
    ) -> None:
        """
        Validate the source video file.
        """

        if input_file is None:

            raise ValueError(
                "Input video file is required."
            )

        if not isinstance(
            input_file,
            Path,
        ):

            input_file = Path(
                input_file
            )

        if not input_file.is_file():

            raise FileNotFoundError(
                f"Input video file not found: "
                f"{input_file}"
            )

    # =========================================================================
    # Languages
    # =========================================================================

    def _validate_languages(
        self,
        source_language: str,
        target_language: str,
    ) -> None:
        """
        Validate source and target languages.

        "auto" is a valid source-language value and means:

            Detect the source language from the video.

        The target language must always be explicit.
        """

        # ---------------------------------------------------------------------
        # Source language
        # ---------------------------------------------------------------------

        if not source_language:

            raise UnsupportedLanguageError(
                "Source language is required."
            )

        if source_language != self.AUTO_LANGUAGE:

            if (
                source_language
                not in self.SUPPORTED_LANGUAGES
            ):

                raise UnsupportedLanguageError(
                    "Unsupported source language "
                    f"'{source_language}'."
                )

        # ---------------------------------------------------------------------
        # Target language
        # ---------------------------------------------------------------------

        if not target_language:

            raise UnsupportedLanguageError(
                "Target language is required."
            )

        if (
            target_language
            not in self.SUPPORTED_LANGUAGES
        ):

            raise UnsupportedLanguageError(
                "Unsupported target language "
                f"'{target_language}'."
            )

        # ---------------------------------------------------------------------
        # Same language
        #
        # "auto" is excluded because the actual source language has not yet
        # been detected.
        # ---------------------------------------------------------------------

        if (
            source_language != self.AUTO_LANGUAGE
            and source_language == target_language
        ):

            raise UnsupportedLanguageError(
                "Source and target languages "
                "cannot be the same."
            )