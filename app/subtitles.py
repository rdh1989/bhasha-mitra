"""Builds SRT subtitle files from timed (start, end, text) segments.

Each translated segment becomes its own subtitle cue so captions stay in
sync with the dubbed audio and only appear during their own speaking
window (never lingering across the whole video). Long lines are wrapped
to a couple of short lines instead of one big block, so a cue never
covers a large portion of the screen.
"""
from __future__ import annotations

import textwrap

MAX_CHARS_PER_LINE = 42
MAX_LINES_PER_CUE = 2


def _format_timestamp(seconds: float) -> str:
    seconds = max(0.0, seconds)
    total_ms = round(seconds * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def _wrap_text(text: str) -> str:
    """Wrap onto at most MAX_LINES_PER_CUE short lines instead of one long
    line that would stretch across the screen."""
    text = " ".join(text.split())
    lines = textwrap.wrap(
        text, width=MAX_CHARS_PER_LINE, max_lines=MAX_LINES_PER_CUE, placeholder="..."
    )
    return "\n".join(lines) if lines else text


def build_srt(segments: list[tuple[float, float, str]]) -> str:
    """segments: list of (start_seconds, end_seconds, text) tuples, the same
    timing used to place each dubbed audio segment - keeps captions synced
    with what's actually heard."""
    cues = []
    index = 1
    for start, end, text in segments:
        text = text.strip()
        if not text or end <= start:
            continue
        cues.append(f"{index}\n{_format_timestamp(start)} --> {_format_timestamp(end)}\n{_wrap_text(text)}\n")
        index += 1
    return "\n".join(cues)
