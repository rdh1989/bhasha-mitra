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

from ai.model_manager.manager import ModelManager


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

        print("Initializing AI Framework...")

        self._manager.initialize()

        self._manager.load_all()

        print("AI Framework Ready.")

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """
        Shutdown AI Framework.
        """

        print("Shutting down AI Framework...")

        self._manager.shutdown()

        print("AI Framework Shutdown Complete.")


ai_framework = AIFramework()