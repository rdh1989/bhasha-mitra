"""
===============================================================================
BHASHA MITRA
===============================================================================

Module:
    safe_filename.py

Layer:
    Infrastructure / Filesystem

Description:
    Provides utilities for sanitizing and validating filesystem filenames.

Responsibilities:
    - Sanitize user-supplied filenames
    - Generate unique safe filenames
    - Prefix filenames with job IDs
    - Validate file extensions
    - Ensure required file extensions
    - Remove file extensions

Does Not:
    - Create directories
    - Select application storage paths
    - Manage translation jobs
    - Persist files

===============================================================================
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from uuid import uuid4


class SafeFilename:
    """
    Utility for sanitizing and generating safe filenames.
    """

    _INVALID_CHARS = re.compile(
        r'[<>:"/\\|?*\x00-\x1F]'
    )

    _MULTIPLE_SPACES = re.compile(
        r"\s+"
    )

    _MULTIPLE_UNDERSCORES = re.compile(
        r"_+"
    )

    @classmethod
    def sanitize(
        cls,
        filename: str,
    ) -> str:
        """
        Convert a filename into a filesystem-safe filename.
        """

        if not isinstance(
            filename,
            str,
        ):

            raise TypeError(
                "Filename must be a string."
            )

        filename = Path(
            filename
        ).name

        filename = unicodedata.normalize(
            "NFKD",
            filename,
        )

        filename = (
            filename
            .encode(
                "ascii",
                "ignore",
            )
            .decode("ascii")
        )

        filename = cls._INVALID_CHARS.sub(
            "",
            filename,
        )

        filename = cls._MULTIPLE_SPACES.sub(
            "_",
            filename.strip(),
        )

        filename = cls._MULTIPLE_UNDERSCORES.sub(
            "_",
            filename,
        )

        if not filename:
            filename = "file"

        return filename

    @classmethod
    def unique(
        cls,
        filename: str,
    ) -> str:
        """
        Generate a unique safe filename while preserving extension.
        """

        filename = cls.sanitize(
            filename
        )

        path = Path(
            filename
        )

        unique_id = uuid4().hex

        return (
            f"{path.stem}_"
            f"{unique_id}"
            f"{path.suffix}"
        )

    @classmethod
    def with_job_id(
        cls,
        job_id: str,
        filename: str,
    ) -> str:
        """
        Prefix a sanitized filename with a job ID.
        """

        if not job_id.strip():

            raise ValueError(
                "Job ID cannot be empty."
            )

        filename = cls.sanitize(
            filename
        )

        return (
            f"{job_id}_"
            f"{filename}"
        )

    @classmethod
    def has_allowed_extension(
        cls,
        filename: str,
        allowed_extensions: set[str],
    ) -> bool:
        """
        Check whether a filename has an allowed extension.
        """

        extension = Path(
            filename
        ).suffix.lower()

        return extension in {
            ext.lower()
            for ext in allowed_extensions
        }

    @classmethod
    def ensure_extension(
        cls,
        filename: str,
        extension: str,
    ) -> str:
        """
        Ensure filename has the specified extension.
        """

        if not extension:

            raise ValueError(
                "Extension cannot be empty."
            )

        if not extension.startswith("."):

            extension = (
                f".{extension}"
            )

        path = Path(
            cls.sanitize(filename)
        )

        if (
            path.suffix.lower()
            == extension.lower()
        ):

            return path.name

        return (
            f"{path.stem}"
            f"{extension}"
        )

    @classmethod
    def remove_extension(
        cls,
        filename: str,
    ) -> str:
        """
        Remove the file extension.
        """

        return Path(
            filename
        ).stem