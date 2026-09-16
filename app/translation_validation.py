"""Mechanical validation for TranslationContext results."""
from __future__ import annotations

import re
import unicodedata

_NUMBER = re.compile(r"(?<![\w])\d+(?:[.,]\d+)?|(?<![\w])[०-९]+(?:[.,][०-९]+)?")
_OPERATOR = re.compile(r"[+×*/=()\-]|गुणिले|भागिले|अधिक|वजा")
_UNIT = re.compile(r"(?:\d+|[०-९]+)\s*(?:सेमी|सेंटीमीटर|मीटर|किलो|किलोग्राम|लिटर|टक्के|%)", re.IGNORECASE)
_UNICODE_ARTIFACT = re.compile(r"(?:\\u|(?<![A-Za-z])[uU]|ü)093[cC]|[®�]")
_MIXED_DEVANAGARI = re.compile(r"[\u0900-\u097F][A-Za-z]|[A-Za-z][\u0900-\u097F]")
_DANGLING_SOURCE_END = re.compile(
    r"\b(?:the|a|an|and|or|but|to|of|for|with|from|in|on|at|by|which|that|who|whose|where|when|because|"
    r"although|if|while|than|as|is|are|was|were|be|been|being|will|would|can|could|should)$",
    re.IGNORECASE,
)
_OPEN_SOURCE_END = re.compile(r"\b(?:is|are|was|were|be|been|being)\s+home$", re.IGNORECASE)


def has_unicode_corruption(text: str) -> bool:
    return bool(_UNICODE_ARTIFACT.search(text) or _MIXED_DEVANAGARI.search(text) or any(unicodedata.category(char) == "Cc" for char in text))


def source_linguistic_completeness(text: str) -> str:
    """Classify only obvious source fragments; do not attempt full parsing."""
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return "INCOMPLETE"
    if re.search(r"[.!?।！？](?:[\"'”’»)]*)$", normalized):
        return "COMPLETE"
    if _DANGLING_SOURCE_END.search(normalized) or _OPEN_SOURCE_END.search(normalized):
        return "INCOMPLETE"
    return "AMBIGUOUS"


def validate_context_results(contexts, results):
    warnings = []
    context_ids = [result.get("context_id") for result in results]
    event_ids = [event_id for context in contexts for event_id in context.event_ids]
    result_event_ids = [event_id for result in results for event_id in result.get("event_ids", [])]
    if len(context_ids) != len(set(context_ids)):
        warnings.append("duplicate_context_id")
    if sorted(event_ids) != sorted(result_event_ids):
        warnings.append("event_traceability_mismatch")
    for context, result in zip(contexts, results):
        text = str(result.get("translated_text", ""))
        source_text = str(result.get("source_text", getattr(context, "source_text", "")))
        if source_text.strip():
            completeness = source_linguistic_completeness(source_text)
            result["linguistic_completeness"] = completeness
            if completeness == "INCOMPLETE":
                warnings.append(f"linguistic_completeness:{result.get('context_id')}")
        if not text.strip():
            warnings.append(f"empty_translation:{result.get('context_id')}")
        normalized = unicodedata.normalize("NFC", text)
        if normalized != text:
            warnings.append(f"unicode_normalized:{result.get('context_id')}")
        if has_unicode_corruption(text):
            warnings.append(f"malformed_unicode:{result.get('context_id')}")
        source_numbers = _NUMBER.findall(source_text)
        target_numbers = _NUMBER.findall(text)
        if source_numbers != target_numbers:
            warnings.append(f"numeric_integrity:{result.get('context_id')}")
        if len(_OPERATOR.findall(source_text)) != len(_OPERATOR.findall(text)):
            warnings.append(f"formula_operator_integrity:{result.get('context_id')}")
        if _UNIT.findall(source_text) and not _UNIT.findall(text):
            warnings.append(f"unit_integrity:{result.get('context_id')}")
        if source_text.strip() and source_text.strip() in text:
            warnings.append(f"untranslated_source_text:{result.get('context_id')}")
        target_words = text.split()
        if len(target_words) >= 6:
            for size in range(2, min(6, len(target_words) // 2 + 1)):
                phrases = [target_words[i:i + size] for i in range(len(target_words) - size + 1)]
                if len(phrases) != len({tuple(phrase) for phrase in phrases}):
                    warnings.append(f"repeated_target_span:{result.get('context_id')}")
                    break
    for previous, current in zip(results, results[1:]):
        if current["source_start"] < previous["source_start"] or current["source_end"] < previous["source_end"]:
            warnings.append("non_monotonic_context_timestamps")
    return {"valid": not warnings, "warnings": warnings}
