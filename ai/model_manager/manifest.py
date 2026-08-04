"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : manifest.py
Purpose     : AI Model Manifest Reader

Description:
    Reads and validates model manifest files.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai.core.exceptions import (
    ConfigurationError,
    ModelNotFoundError,
)


class ManifestReader:
    """
    Reads AI model manifest files.

    Responsibilities
    ----------------
    • Read manifest.json
    • Parse JSON
    • Return manifest data

    Notes
    -----
    Validation is performed by ModelValidator.
    """

    def read(
        self,
        manifest_path: Path,
    ) -> dict[str, Any]:
        """
        Read manifest file.

        Parameters
        ----------
        manifest_path : Path
            Path to manifest.json

        Returns
        -------
        dict[str, Any]

        Raises
        ------
        ModelNotFoundError
            Manifest file does not exist.

        ConfigurationError
            Invalid JSON.
        """

        if not manifest_path.exists():
            raise ModelNotFoundError(
                f"Manifest not found: {manifest_path}"
            )

        try:
            with manifest_path.open(
                mode="r",
                encoding="utf-8",
            ) as file:
                return json.load(file)

        except json.JSONDecodeError as exc:
            raise ConfigurationError(
                f"Invalid manifest file: {manifest_path}"
            ) from exc