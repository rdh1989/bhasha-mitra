"""Generic domain-knowledge pack loading, protection, and validation."""
from __future__ import annotations

import json
import re
from pathlib import Path

from app.config import ACTIVE_DOMAIN_PACK_PATH

_PLACEHOLDER = "TERMGUARD{index}X"


def load_domain_pack(resource_path=None):
    path = Path(resource_path or ACTIVE_DOMAIN_PACK_PATH)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"domain": None, "entries": [], "category_compatibility": {}, "target_category_terms": {}}
    return payload


def domain_pack_applies(source_flores_code, target_flores_code, resource_path=None):
    pair = load_domain_pack(resource_path).get("language_pair", {})
    return not pair or (pair.get("source") == source_flores_code and pair.get("target") == target_flores_code)


def _entries(resource_path=None):
    pack = load_domain_pack(resource_path)
    entries = [entry for entry in pack.get("entries", []) if entry.get("confidence") == "high"]
    return sorted(entries, key=lambda entry: len(entry.get("source_term", "")), reverse=True), pack


def protect_terms(source_text: str, *, enabled: bool = False, resource_path=None):
    if not enabled:
        return source_text, [], {}
    entries, _ = _entries(resource_path)
    protected = source_text
    replacements = {}
    matches = []
    for entry in entries:
        if not entry.get("protection_allowed"):
            continue
        variants = [entry.get("source_term", ""), *entry.get("source_variants", [])]
        for source in sorted((value for value in variants if value), key=len, reverse=True):
            if not re.search(re.escape(source), protected):
                continue
            placeholder = _PLACEHOLDER.format(index=len(replacements))
            protected = re.sub(re.escape(source), placeholder, protected)
            replacements[placeholder] = entry["target_term"]
            matches.append({"source": source, "target": entry["target_term"], "category": entry.get("category")})
            break
    return protected, matches, replacements


def restore_terms(translated_text: str, replacements: dict[str, str]) -> str:
    for placeholder, target in replacements.items():
        translated_text = translated_text.replace(placeholder, target)
    return translated_text


def validate_terminology(source_text: str, translated_text: str, *, enabled: bool = False, resource_path=None):
    if not enabled:
        return translated_text, [], []
    entries, pack = _entries(resource_path)
    matches = []
    warnings = []
    target_categories = pack.get("target_category_terms", {})
    for entry in entries:
        source_variants = [entry.get("source_term", ""), *entry.get("source_variants", [])]
        if not entry.get("validation_allowed") or not any(source and source in source_text for source in source_variants):
            continue
        target_variants = [entry.get("target_term", ""), *entry.get("target_variants", [])]
        present = [target for target in target_variants if target and target in translated_text]
        contradictions = [
            {"category": category, "term": term}
            for category, terms in target_categories.items()
            if category not in pack.get("category_compatibility", {}).get(entry.get("category"), [entry.get("category")])
            for term in terms if term in translated_text
        ]
        matches.append({"source": entry.get("source_term"), "category": entry.get("category"), "approved_targets": target_variants, "target_present": present, "contradictions": contradictions})
        if contradictions:
            warnings.append(f"domain_category_contradiction:{entry.get('source_term')}")
        elif not present:
            warnings.append(f"missing_approved_term:{entry.get('source_term')}")
    return translated_text, matches, warnings


def terminology_consistency(results, *, enabled: bool = False, resource_path=None):
    if not enabled:
        return []
    entries, _ = _entries(resource_path)
    diagnostics = []
    for entry in entries:
        source = entry.get("source_term", "")
        variants = {}
        for result in results:
            if source in str(result.get("source_text", "")):
                target = str(result.get("translated_text", ""))
                variants[target] = variants.get(target, 0) + 1
        if variants:
            approved = [entry.get("target_term"), *entry.get("target_variants", [])]
            diagnostics.append({"source_concept": entry.get("category"), "source_term": source, "target_variants": variants, "frequency": sum(variants.values()), "approved_targets": approved, "status": "PASS" if all(target in approved for target in variants) else "INCONSISTENT"})
    return diagnostics