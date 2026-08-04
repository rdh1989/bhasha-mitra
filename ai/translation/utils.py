"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : utils.py
Purpose     : Translation Utility Functions

Description:
    Common utility functions used by the Translation module.

These utilities are provider-independent.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from typing import Iterable


def normalize_language(language: str | None) -> str | None:
    """
    Normalize a language code.

    Examples
    --------
    EN -> en
    en-US -> en-us

    Parameters
    ----------
    language : str | None

    Returns
    -------
    str | None
    """

    if language is None:
        return None

    return language.strip().lower()


def normalize_text(text: str) -> str:
    """
    Normalize whitespace in text.

    Parameters
    ----------
    text : str

    Returns
    -------
    str
    """

    return " ".join(text.split())


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


def split_sentences(text: str) -> list[str]:
    """
    Split text into sentences.

    Note
    ----
    Simple implementation for v1.0.
    Advanced sentence segmentation can be introduced later.

    Parameters
    ----------
    text : str

    Returns
    -------
    list[str]
    """

    return [
        sentence.strip()
        for sentence in text.split(".")
        if sentence.strip()
    ]


def join_sentences(sentences: Iterable[str]) -> str:
    """
    Join translated sentences.

    Parameters
    ----------
    sentences : Iterable[str]

    Returns
    -------
    str
    """

    return ". ".join(sentence.strip() for sentence in sentences)