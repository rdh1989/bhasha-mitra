"""
Maps ISO language codes to NLLB-200 FLORES-200 codes.

The source of truth is config/languages.yaml (`languages.<code>.nllb_code`)
so adding a supported language only requires editing that YAML file.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_LANGUAGES_YAML_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "languages.yaml"
)


def _load_language_codes() -> dict[str, str]:

    with _LANGUAGES_YAML_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:

        config = yaml.safe_load(handle) or {}

    languages = config.get("languages") or {}

    return {
        code: info["nllb_code"]
        for code, info in languages.items()
        if isinstance(info, dict) and "nllb_code" in info
    }


LANGUAGE_CODES: dict[str, str] = _load_language_codes()