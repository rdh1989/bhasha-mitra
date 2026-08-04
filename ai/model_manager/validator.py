"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : validator.py
Purpose     : AI Model Validator

Description:
    Validates AI model metadata and filesystem resources before loading.

Design Pattern:
    Validator

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from pathlib import Path

from ai.core.exceptions import (
    ModelNotFoundError,
    ModelValidationError,
)


class ModelValidator:
    """
    Validates AI model resources.

    Responsibilities
    ----------------
    • Validate model directory exists
    • Validate required files exist
    • Validate manifest structure
    • Validate model metadata

    Notes
    -----
    This class never loads AI models.
    """

    def validate_directory(
        self,
        model_path: Path,
    ) -> bool:
        """
        Validate model directory exists.
        """

        if not model_path.exists():
            raise ModelNotFoundError(
                f"Model directory not found: {model_path}"
            )

        if not model_path.is_dir():
            raise ModelValidationError(
                f"Expected directory: {model_path}"
            )

        return True

    def validate_file(
        self,
        file_path: Path,
    ) -> bool:
        """
        Validate required model file.
        """

        if not file_path.exists():
            raise ModelNotFoundError(
                f"Required file not found: {file_path}"
            )

        if not file_path.is_file():
            raise ModelValidationError(
                f"Expected file: {file_path}"
            )

        return True

    def validate_manifest(
        self,
        manifest: dict,
    ) -> bool:
        """
        Validate complete manifest structure.

        Expected format
        ---------------
        {
            "asr": {
                "provider": "...",
                "model": "...",
                "path": "...",
                "version": "..."
            },
            ...
        }
        """

        if not manifest:
            raise ModelValidationError(
                "Manifest is empty."
            )

        required_sections = {
            "asr",
            "translation",
            "language_detection",
            "tts",
        }

        missing_sections = required_sections - manifest.keys()

        if missing_sections:
            raise ModelValidationError(
                f"Missing manifest sections: {sorted(missing_sections)}"
            )

        for section_name, config in manifest.items():

            if not isinstance(config, dict):
                raise ModelValidationError(
                    f"Invalid configuration for '{section_name}'."
                )

            if section_name == "ffmpeg":
                if "path" not in config:
                    raise ModelValidationError(
                        "FFmpeg configuration requires 'path'."
                    )
                continue

            required_fields = {
                "provider",
                "path",
            }

            missing_fields = required_fields - config.keys()

            if missing_fields:
                raise ModelValidationError(
                    f"Section '{section_name}' missing fields: "
                    f"{sorted(missing_fields)}"
                )

        return True