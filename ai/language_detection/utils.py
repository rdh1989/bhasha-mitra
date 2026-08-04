"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : utils.py
Purpose     : Language Detection Utility Functions

Description:
    Common helper functions used by the Language Detection module.

These utilities are completely provider-independent.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations


def normalize_text(text: str) -> str:
    """
    Normalize input text.

    Parameters
    ----------
    text : str

    Returns
    -------
    str
    """

    return " ".join(text.split())


def normalize_language(language: str | None) -> str | None:
    """
    Normalize language code.

    Examples
    --------
    EN -> en
    mr-IN -> mr-in
    """

    if language is None:
        return None

    return language.strip().lower()


def is_empty(text: str | None) -> bool:
    """
    Check whether text is empty.

    Parameters
    ----------
    text : str | None

    Returns
    -------
    bool
    """

    return text is None or not text.strip()


def clamp_confidence(confidence: float) -> float:
    """
    Clamp confidence between 0.0 and 1.0.

    Parameters
    ----------
    confidence : float

    Returns
    -------
    float
    """

    return max(0.0, min(confidence, 1.0))


def sort_candidates(candidates):
    """
    Sort detected languages by confidence.

    Parameters
    ----------
    candidates : Iterable

    Returns
    -------
    list
    """

    return sorted(
        candidates,
        key=lambda item: item.confidence,
        reverse=True,
    )