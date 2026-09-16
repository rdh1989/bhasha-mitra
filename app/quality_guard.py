"""Generic translation quality guard with pluggable domain validation."""
from __future__ import annotations

from app.entity_protection import validate_entities
from app.translation_validation import validate_context_results


class TranslationQualityGuard:
    """Combine generic mechanical checks with an optional domain pack validator."""

    def __init__(self, domain_validator=None):
        self._domain_validator = domain_validator

    def validate(self, contexts, results):
        diagnostics = validate_context_results(contexts, results)
        for result in results:
            diagnostics["warnings"].extend(
                f"{warning}:{result.get('context_id')}"
                for warning in validate_entities(result.get("source_text", ""), result.get("translated_text", ""))
            )
            if self._domain_validator is not None:
                diagnostics["warnings"].extend(self._domain_validator(result))
        warnings = diagnostics["warnings"]
        retry_warnings = ("numeric_integrity", "formula_operator_integrity", "entity_integrity", "malformed_unicode")
        status = "PASS"
        if warnings:
            status = "RETRY" if any(any(warning.startswith(prefix) for prefix in retry_warnings) for warning in warnings) else "FLAG"
        return {**diagnostics, "status": status}
