"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Package     : ai
Purpose     : Root package for the AI Framework.

Description
-----------
Provides the public entry point for the AI framework.

Notes
-----
This package intentionally performs NO initialization.

It MUST NOT:
    • Load AI models
    • Read configuration
    • Create providers
    • Initialize ModelManager

Initialization is handled explicitly by the application.
===============================================================================
"""

__version__ = "1.0.0"

__author__ = "Bhasha Mitra AI Team"

__all__ = [
    "__version__",
]