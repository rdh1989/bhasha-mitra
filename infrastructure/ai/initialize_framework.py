"""
===============================================================================
Bhasha Mitra
-------------------------------------------------------------------------------
Module      : ai_framework.py
Purpose     : AI Framework Initializer

Description:
    Initializes and shuts down the AI Framework.

Responsibilities
----------------
• Initialize AI Framework
• Load configured AI models
• Shutdown AI Framework

Notes
-----
This module orchestrates the AI Framework lifecycle.

It does NOT:
• Load individual providers
• Know model names
• Know model paths
• Perform inference
===============================================================================
"""

import logging

from ai.model_manager.manager import ModelManager


logger = logging.getLogger(__name__)


class AIFramework:
    """
    AI Framework Initializer.
    """

    def __init__(self) -> None:

        self._manager = ModelManager()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """
        Initialize AI Framework.
        """

        logger.info("Initializing AI Framework")

        self._manager.initialize()

        self._manager.load_all()

        logger.info("AI Framework Ready")

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """
        Shutdown AI Framework.
        """

        logger.info("Shutting down AI Framework")

        self._manager.shutdown()

        logger.info("AI Framework Shutdown Complete")


ai_framework = AIFramework()