"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : adapter.py
Purpose     : Translation Adapter
===============================================================================
"""

from ai.translation.models import TranslationResult


class TranslationAdapter:
    """
    Converts provider-specific translation output into framework models.
    """

    def to_framework_result(
        self,
        provider_result,
    ) -> TranslationResult:

        # Temporary implementation.
        # Assumes provider already returns TranslationResult.
        return provider_result