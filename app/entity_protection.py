"""Domain-independent protection and validation of numeric entities."""
from __future__ import annotations

import re

_ENTITY = re.compile(
    r"(?<!\w)(?:\d+(?:[.,]\d+)?|[०-९]+(?:[.,][०-९]+)?)(?:\s*(?:%|°|kg|mg|km|cm|mm|ha|ml|[kKmMgGlL]))?"
    r"|(?<!\w)[A-Za-z]+\s*[×x*/÷]\s*(?:[A-Za-z]+|\d+)(?!\w)"
)


def protect_entities(text: str):
    replacements = {}
    matches = []

    def replace(match):
        placeholder = f"ENTITYGUARD{len(replacements)}X"
        value = match.group(0)
        replacements[placeholder] = value
        matches.append(value)
        return placeholder

    return _ENTITY.sub(replace, text), matches, replacements


def restore_entities(text: str, replacements: dict[str, str]) -> str:
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    return text


def validate_entities(source_text: str, target_text: str) -> list[str]:
    source_entities = [match.group(0) for match in _ENTITY.finditer(source_text)]
    target_entities = [match.group(0) for match in _ENTITY.finditer(target_text)]
    if source_entities != target_entities:
        return ["entity_integrity"]
    return []
