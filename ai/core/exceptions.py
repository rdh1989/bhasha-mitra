"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : exceptions.py
Purpose     : AI Framework Exceptions

Description:
    Defines all framework-level exceptions used across the AI layer.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations


class AIFrameworkError(Exception):
    """
    Base exception for the entire AI framework.

    All framework-specific exceptions inherit from this class.
    """
    pass


# ============================================================================
# Provider Exceptions
# ============================================================================

class ProviderError(AIFrameworkError):
    """
    Base exception for provider-related errors.
    """
    pass


class ProviderRegistrationError(ProviderError):
    """
    Raised when provider registration fails.

    Examples
    --------
    • Duplicate registration
    • Invalid provider class
    • Unsupported provider category
    """
    pass


class ProviderNotFoundError(ProviderError):
    """
    Raised when the requested provider is not registered.
    """
    pass


class ProviderCreationError(ProviderError):
    """
    Raised when ProviderFactory cannot create
    a provider instance.
    """
    pass


class ProviderInitializationError(ProviderError):
    """
    Raised when a provider fails during initialization.
    """
    pass


class ProviderHealthError(ProviderError):
    """
    Raised when a provider health check fails.
    """
    pass


# ============================================================================
# Model Manager Exceptions
# ============================================================================

class ModelError(AIFrameworkError):
    """
    Base exception for model management errors.
    """
    pass


class ModelNotFoundError(ModelError):
    """
    Raised when a requested model is unavailable.
    """
    pass


class ModelLoadError(ModelError):
    """
    Raised when model loading fails.
    """
    pass


class ModelValidationError(ModelError):
    """
    Raised when model validation fails.
    """
    pass


class ModelCacheError(ModelError):
    """
    Raised when model cache operations fail.
    """
    pass


# ============================================================================
# Configuration Exceptions
# ============================================================================

class ConfigurationError(AIFrameworkError):
    """
    Raised when framework configuration is invalid.
    """
    pass


# ============================================================================
# Runtime Exceptions
# ============================================================================

class ServiceError(AIFrameworkError):
    """
    Raised when an AI service encounters a runtime error.
    """
    pass