"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : downloader.py
Purpose     : AI Model Downloader

Description:
    Handles downloading and updating AI models.

Notes:
    This module is intentionally lightweight in v1.0 because Bhasha Mitra
    ships with pre-downloaded offline models. Future releases may use this
    module to download or update models from supported repositories.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from pathlib import Path


class ModelDownloader:
    """
    Downloads and updates AI models.

    Responsibilities
    ----------------
    • Download AI models
    • Resume interrupted downloads
    • Verify downloaded artifacts
    • Update existing models

    Notes
    -----
    Current Version:
        Placeholder implementation.

    Future Scope:
        • Hugging Face
        • Bhashini
        • Internal Model Repository
    """

    def download(
        self,
        model_name: str,
        destination: Path,
    ) -> None:
        """
        Download a model.

        Parameters
        ----------
        model_name : str
            Model identifier.

        destination : Path
            Destination directory.

        Raises
        ------
        NotImplementedError
            Download support is not implemented in v1.0.
        """
        raise NotImplementedError(
            "Model download is not supported in the current release."
        )

    def update(
        self,
        model_name: str,
    ) -> None:
        """
        Update an installed model.

        Parameters
        ----------
        model_name : str
            Model identifier.

        Raises
        ------
        NotImplementedError
            Update support is not implemented in v1.0.
        """
        raise NotImplementedError(
            "Model update is not supported in the current release."
        )