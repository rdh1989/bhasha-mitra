"""
Application-level validator for translation job requests.
"""

from pathlib import Path

from app.application.dto.create_job_request import CreateJobRequest
from app.application.exceptions import (
    DuplicateJobError,
    FileTooLargeError,
    InputFileNotFoundError,
    InvalidFileExtensionError,
    InvalidLanguagePairError,
    UnsupportedLanguageError,
)
from app.application.interfaces.job_repository import JobRepository
from infrastructure.configuration.configuration_manager import ConfigurationManager


class JobValidator:
    """
    Validates CreateJobRequest before creating a TranslationJob.

    This validator performs only application-level validation.
    Business rules belong in the Domain layer.
    """

    def __init__(
        self,
        job_repository: JobRepository,
        configuration_manager: ConfigurationManager,
    ) -> None:
        self._job_repository = job_repository
        self._configuration = configuration_manager

    def validate_create_request(
        self,
        request: CreateJobRequest,
    ) -> None:
        """
        Validate an incoming translation request.

        Raises:
            InputFileNotFoundError
            InvalidFileExtensionError
            FileTooLargeError
            UnsupportedLanguageError
            InvalidLanguagePairError
            DuplicateJobError
        """

        self._validate_file(request.input_file)
        self._validate_extension(request.input_file)
        self._validate_file_size(request.input_file)
        self._validate_languages(
            request.source_language,
            request.target_language,
        )
        self._validate_duplicate_job(request.input_file)

    # ---------------------------------------------------------
    # File Validation
    # ---------------------------------------------------------

    def _validate_file(
        self,
        file_path: Path,
    ) -> None:

        if not file_path.exists():
            raise InputFileNotFoundError(
                f"Input file '{file_path}' does not exist."
            )

        if not file_path.is_file():
            raise InputFileNotFoundError(
                f"'{file_path}' is not a valid file."
            )

    # ---------------------------------------------------------
    # Extension Validation
    # ---------------------------------------------------------

    def _validate_extension(
        self,
        file_path: Path,
    ) -> None:

        upload_config = self._configuration.get("app").get(
            "upload",
            {}
        )

        allowed_extensions = {
            extension.lower()
            for extension in upload_config.get(
                "allowed_extensions",
                [],
            )
        }

        extension = file_path.suffix.lower().removeprefix(".")

        if extension not in allowed_extensions:
            raise InvalidFileExtensionError(
                f"Unsupported file extension '{extension}'. "
                f"Allowed extensions: "
                f"{', '.join(sorted(allowed_extensions))}"
            )

    # ---------------------------------------------------------
    # File Size Validation
    # ---------------------------------------------------------

    def _validate_file_size(
        self,
        file_path: Path,
    ) -> None:

        upload_config = self._configuration.get("app").get(
            "upload",
            {}
        )

        max_size_mb = upload_config.get(
            "max_file_size_mb",
            2048,
        )

        max_size_bytes = max_size_mb * 1024 * 1024

        actual_size = file_path.stat().st_size

        if actual_size > max_size_bytes:
            raise FileTooLargeError(
                f"File size exceeds "
                f"{max_size_mb} MB."
            )

    # ---------------------------------------------------------
    # Language Validation
    # ---------------------------------------------------------

    def _validate_languages(
        self,
        source_language: str,
        target_language: str,
    ) -> None:

        source_language = source_language.strip().lower()
        target_language = target_language.strip().lower()

        if not source_language:
            raise UnsupportedLanguageError(
                "Source language is required."
            )

        if not target_language:
            raise UnsupportedLanguageError(
                "Target language is required."
            )

        if source_language == target_language:
            raise InvalidLanguagePairError(
                "Source and target languages cannot be the same."
            )

        languages_config = self._configuration.get("languages")

        supported_languages = {
            language.lower()
            for language in languages_config.get(
                "translation",
                {},
            ).get(
                "supported",
                [],
            )
        }

        if source_language not in supported_languages:
            raise UnsupportedLanguageError(
                f"Unsupported source language "
                f"'{source_language}'."
            )

        if target_language not in supported_languages:
            raise UnsupportedLanguageError(
                f"Unsupported target language "
                f"'{target_language}'."
            )

    # ---------------------------------------------------------
    # Duplicate Job Validation
    # ---------------------------------------------------------

    def _validate_duplicate_job(
        self,
        file_path: Path,
    ) -> None:

        existing_job = (
            self._job_repository.find_active_job(
                file_path
            )
        )

        if existing_job is not None:
            raise DuplicateJobError(
                f"An active translation job already exists "
                f"for '{file_path.name}'."
            )