"""
===============================================================================
BHASHA MITRA
===============================================================================

Module:
    exceptions.py

Layer:
    Infrastructure / Configuration

Description:
    Defines exceptions raised by the configuration infrastructure.

Responsibilities:
    - Provide the configuration-specific exception type.

===============================================================================
"""


class ConfigurationError(Exception):
    """
    Raised when configuration loading or persistence fails.
    """