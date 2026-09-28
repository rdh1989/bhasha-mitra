"""Text language detection for the optional source-language workflow."""
from __future__ import annotations

from langdetect import DetectorFactory, LangDetectException, detect_langs

DetectorFactory.seed = 0

_MIN_CONFIDENCE = 0.80
_MIN_MARGIN = 0.15


def detect_text_language(text: str, supported_codes: set[str]) -> tuple[str, float]:
    """Return a supported language code and confidence, or raise ValueError."""
    text = text.strip()
    if len(text) < 3:
        raise ValueError("Text is too short to detect a source language confidently.")
    try:
        candidates = detect_langs(text)
    except LangDetectException as exc:
        raise ValueError("The source language could not be detected.") from exc

    supported = []
    for candidate in candidates:
        code = candidate.lang.split("-", 1)[0].lower()
        if code in supported_codes:
            supported.append((code, float(candidate.prob)))
    if not supported:
        raise ValueError("The detected source language is not supported.")

    language, confidence = supported[0]
    if confidence < _MIN_CONFIDENCE:
        raise ValueError("The source language could not be detected confidently.")
    if len(supported) > 1 and confidence - supported[1][1] < _MIN_MARGIN:
        raise ValueError("The source language is ambiguous; select it manually.")
    return language, confidence
