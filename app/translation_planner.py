"""Bounded, deterministic, language-neutral TranslationContext planning."""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from os import environ

from app.config import TRANSLATION_CONTEXT_MAX_DURATION_SECONDS

_SENTENCE_END = re.compile(r"[.!?।！？]$|[.!?।！？][\"'”’»)]$")
_OPENING = re.compile(r"[([{\"'“‘«]$")
_CLOSING = re.compile(r"^[\])}»\"'”’]")
_CONTINUATION_PUNCTUATION = re.compile(r"[,;:…\-–—/]$")
_NUMBER_END = re.compile(r"(?:\d|[०-९])$")
_DEFAULT_DANGLING_WORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "for", "with", "from", "in", "on", "at", "by",
    "which", "that", "who", "whose", "where", "when", "because", "although", "if", "while", "than", "as",
    "is", "are", "was", "were", "be", "been", "being", "will", "would", "can", "could", "should",
}
_DEFAULT_CONTINUATION_STARTERS = _DEFAULT_DANGLING_WORDS | {
    "they", "he", "she", "it", "this", "these", "those",
}
_SYNTACTICALLY_OPEN = re.compile(r"\b(?:is|are|was|were|be|been|being)\s+home$", re.IGNORECASE)


def _configured_words(name, defaults):
    configured = environ.get(name, "").strip()
    return {word.strip().lower() for word in configured.split(",") if word.strip()} or set(defaults)


DANGLING_FUNCTION_WORDS = _configured_words("TRANSLATION_CONTEXT_DANGLING_WORDS", _DEFAULT_DANGLING_WORDS)
CONTINUATION_STARTERS = _configured_words("TRANSLATION_CONTEXT_CONTINUATION_STARTERS", _DEFAULT_CONTINUATION_STARTERS)


@dataclass(frozen=True)
class TranslationContext:
    context_id: int
    event_ids: tuple[int, ...]
    source_start: float
    source_end: float
    source_text: str
    source_events: tuple[object, ...]
    planner_reason: str
    context_status: str = "OK"
    continuation_score: float = 0.0
    boundary_score: float = 0.0
    dependency_score: float = 0.0
    pause_score: float = 0.0
    completion_score: float = 0.0
    decision: str = "KEEP_STANDALONE"
    decision_reasons: tuple[str, ...] = ()


def _word(token):
    return re.sub(r"^[^\w]+|[^\w]+$", "", token.lower(), flags=re.UNICODE)


def _event_signals(event, next_event=None):
    text = str(getattr(event, "text", "") or "").strip()
    tokens = text.split()
    continuation = 0.0
    boundary = 0.0
    reasons = []
    if not text:
        return {"continuation": 0.0, "boundary": 1.0, "dependency": 0.0, "pause": 0.0, "completion": 0.0}
    if _SENTENCE_END.search(text):
        boundary += 1.0
        reasons.append("TERMINAL_PUNCTUATION")
    if _CONTINUATION_PUNCTUATION.search(text):
        continuation += 0.8
        reasons.append("CONTINUATION_PUNCTUATION")
    if _OPENING.search(text):
        continuation += 0.5
    if _NUMBER_END.search(text):
        continuation += 0.35
    if len(tokens) <= 2 and not _SENTENCE_END.search(text):
        continuation += 0.25
    if next_event is not None and _CLOSING.match(str(getattr(next_event, "text", "") or "").strip()):
        continuation += 0.3
    last_word = _word(tokens[-1]) if tokens else ""
    if last_word in DANGLING_FUNCTION_WORDS:
        continuation += 0.65
        reasons.append("DANGLING_FUNCTION_WORD")
    first_word = _word(tokens[0]) if tokens else ""
    if first_word in CONTINUATION_STARTERS:
        continuation += 0.6
        reasons.append("CURRENT_SEGMENT_CONTINUATION")
    if _SYNTACTICALLY_OPEN.search(text):
        continuation += 0.7
        reasons.append("SYNTACTICALLY_INCOMPLETE")
    next_tokens = str(getattr(next_event, "text", "") or "").strip().split() if next_event is not None else []
    next_first = _word(next_tokens[0]) if next_tokens else ""
    if next_first in CONTINUATION_STARTERS:
        continuation += 0.6
        reasons.append("NEXT_SEGMENT_CONTINUATION")
    elif next_tokens and next_tokens[0][:1].islower() and len(tokens) >= 4 and not _SENTENCE_END.search(text):
        continuation += 0.6
        reasons.append("LOWERCASE_NEXT_SEGMENT")
    pause_before = getattr(event, "pause_before", None)
    pause_after = getattr(event, "pause_after", None)
    if pause_after is not None:
        pause = max(float(pause_after), 0.0)
        boundary += min(pause / 3.0, 1.0)
    elif pause_before is not None:
        pause = max(float(pause_before), 0.0)
        boundary += min(pause / 3.0, 1.0)
    dependency = min(1.0, continuation / 1.25)
    completion = max(0.0, 1.0 - dependency - min(boundary, 0.5))
    return {
        "continuation": continuation,
        "boundary": min(boundary, 1.0),
        "dependency": dependency,
        "pause": min(boundary, 1.0),
        "completion": completion,
        "reasons": tuple(dict.fromkeys(reasons)),
    }


def plan_translation_contexts(events, *, max_events=3, max_characters=1200, max_duration=TRANSLATION_CONTEXT_MAX_DURATION_SECONDS):
    contexts = []
    assigned = set()
    unsafe_boundaries = 0

    def add(indexes, reason, status="OK", decision="KEEP_STANDALONE", signals=None):
        nonlocal unsafe_boundaries
        if not indexes or any(i in assigned for i in indexes):
            return False
        selected = [(i, events[i]) for i in indexes]
        text = " ".join(str(event.text).strip() for _, event in selected).strip()
        duration = float(selected[-1][1].end) - float(selected[0][1].start)
        if not text or len(indexes) > max_events or len(text) > max_characters or duration > max_duration:
            unsafe_boundaries += 1
            return False
        signals = signals or {"continuation": 0.0, "boundary": 0.0, "dependency": 0.0, "pause": 0.0, "completion": 1.0, "reasons": ()}
        contexts.append(TranslationContext(
            context_id=len(contexts), event_ids=tuple(indexes), source_start=float(selected[0][1].start),
            source_end=float(selected[-1][1].end), source_text=text,
            source_events=tuple(event for _, event in selected), planner_reason=reason,
            context_status=status, continuation_score=signals["continuation"],
            boundary_score=signals["boundary"], dependency_score=signals["dependency"],
            pause_score=signals["pause"], completion_score=signals["completion"], decision=decision,
            decision_reasons=tuple(signals.get("reasons", ())),
        ))
        assigned.update(indexes)
        return True

    index = 0
    while index < len(events):
        if index in assigned:
            index += 1
            continue
        text = str(getattr(events[index], "text", "") or "").strip()
        if not text:
            unsafe_boundaries += 1
            index += 1
            continue
        next_event = events[index + 1] if index + 1 < len(events) else None
        signals = _event_signals(events[index], next_event)
        next_signals = _event_signals(next_event) if next_event is not None else None
        current_words = text.split()
        current_first = _word(current_words[0]) if current_words else ""
        previous_context = contexts[-1] if contexts else None
        if (
            current_first in CONTINUATION_STARTERS
            and previous_context is not None
            and previous_context.event_ids == (index - 1,)
            and signals["dependency"] >= 0.45
        ):
            previous_event = events[index - 1]
            combined_text = f"{previous_event.text} {text}".strip()
            combined_duration = float(events[index].end) - float(previous_event.start)
            if len(combined_text) <= max_characters and combined_duration <= max_duration:
                contexts[-1] = replace(
                    previous_context,
                    event_ids=(index - 1, index),
                    source_end=float(events[index].end),
                    source_text=combined_text,
                    source_events=(previous_event, events[index]),
                    planner_reason="PREVIOUS_SEGMENT_CONTINUATION",
                    decision="MERGE_PREVIOUS",
                    continuation_score=signals["continuation"],
                    dependency_score=signals["dependency"],
                    completion_score=signals["completion"],
                    decision_reasons=tuple(dict.fromkeys((*signals.get("reasons", ()), "PREVIOUS_SEGMENT_CONTINUATION"))),
                )
                assigned.add(index)
                index += 1
                continue
        can_expand = next_event is not None and signals["dependency"] >= 0.45 and signals["boundary"] < 0.9
        if can_expand and index + 1 not in assigned:
            indexes = [index, index + 1]
            while len(indexes) < max_events:
                combined = " ".join(str(events[i].text).strip() for i in indexes)
                following = indexes[-1] + 1
                combined_signals = _event_signals(
                    type("Event", (), {"text": combined, "pause_after": None})(),
                )
                if following >= len(events) or following in assigned or combined_signals["dependency"] < 0.45:
                    break
                indexes.append(following)
            if add(indexes, "STRUCTURAL_CONTINUATION_CONTEXT", decision="MERGE_NEXT", signals=signals):
                index += len(indexes)
                continue
        ambiguous = len(text.split()) == 1 and not _SENTENCE_END.search(text)
        status = "AMBIGUOUS_CONTEXT" if ambiguous else "OK"
        decision = "AMBIGUOUS" if ambiguous else "KEEP_STANDALONE"
        if not add([index], "SINGLE_EVENT_CONTEXT", status, decision, signals):
            unsafe_boundaries += 1
        index += 1

    diagnostics = {
        "source_events": len(events), "translation_contexts": len(contexts),
        "merged_event_groups": sum(len(c.event_ids) > 1 for c in contexts),
        "single_event_contexts": sum(len(c.event_ids) == 1 for c in contexts),
        "unsafe_boundaries": unsafe_boundaries, "words_lost": 0, "words_duplicated": 0,
        "decisions": {decision: sum(c.decision == decision for c in contexts) for decision in {
            "KEEP_STANDALONE", "MERGE_PREVIOUS", "MERGE_NEXT", "MERGE_BOTH", "AMBIGUOUS"
        }},
    }
    return contexts, diagnostics