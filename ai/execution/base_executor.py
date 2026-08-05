"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : base_executor.py
Purpose     : Base Execution Layer

Description
-----------
Base class for all AI execution engines.

Responsibilities
----------------
• Access already loaded models
• Execute inference
• Return framework models

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from ai.model_manager.manager import ModelManager


class BaseExecutor:
    """
    Base class for AI execution.
    """

    def __init__(self) -> None:
        self._model_manager = ModelManager()

    def get_model(
        self,
        category: str,
        model: str,
    ):
        """
        Return an already-loaded model.

        Raises
        ------
        RuntimeError
            If the requested model has not been loaded.
        """

        if not self._model_manager.is_loaded(category, model):
            raise RuntimeError(
                f"Model '{category}:{model}' is not loaded."
            )

        return self._model_manager.get_model(
            category=category,
            model=model,
        )