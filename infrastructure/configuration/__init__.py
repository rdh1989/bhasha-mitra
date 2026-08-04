"""
Configuration package.
"""

from infrastructure.configuration.configuration_manager import ConfigurationManager

configuration = ConfigurationManager()

__all__ = [
    "ConfigurationManager",
    "configuration",
]