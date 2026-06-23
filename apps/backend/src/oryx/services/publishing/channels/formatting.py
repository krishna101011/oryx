"""Content-formatting helpers shared by channel adapters.

Kept channel-agnostic and pure so they are trivially unit-testable without any
network or credentials.
"""
from __future__ import annotations

import re

# Split on sentence terminators followed by whitespace. Deliberately simple —
# this is presentation segmentation, not NLP.
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    return [s for s in (p.strip() for p in _SENTENCE_RE.split(text.strip())) if s]


def _hard_chunks(s: str, limit: int) -> list[str]:
    """Last-resort splitter for a single sentence longer than `limit`."""
    return [s[i : i + limit] for i in range(0, len(s), limit)]


def _pack(sentences: list[str], limit: int) -> list[str]:
    """Greedily pack sentences into ≤limit segments (no numbering). A sentence
    longer than limit is hard-split."""
    out: list[str] = []
    current = ""
    for sentence in sentences:
        pieces = (
            [sentence] if len(sentence) <= limit else _hard_chunks(sentence, limit)
        )
        for piece in pieces:
            if not current:
                current = piece
            elif len(current) + 1 + len(piece) <= limit:
                current = f"{current} {piece}"
            else:
                out.append(current)
                current = piece
    if current:
        out.append(current)
    return out


def thread_segments(content: str, max_length: int) -> list[str]:
    """Pack content into segments no longer than `max_length`, breaking on
    sentence boundaries where possible. A sentence longer than the limit is
    hard-split. If the result is more than one segment, each is numbered
    "(i/n)" — the numbering suffix is reserved within `max_length` so a numbered
    segment never overflows.

    Used by Twitter (max 280). Returns at least one segment ([] for empty input).
    """
    sentences = split_sentences(content)
    if not sentences:
        return []

    raw = _pack(sentences, max_length)
    if len(raw) <= 1:
        return raw

    # Reserve room for the " (i/n)" suffix. Shrinking the budget can grow the
    # segment count, which widens the suffix — iterate to a fixpoint.
    n = len(raw)
    packed = raw
    while True:
        suffix = len(f" ({n}/{n})")
        budget = max_length - suffix
        if budget <= 0:
            # Pathological tiny max_length — number without further packing.
            return [f"{seg} ({i}/{len(raw)})" for i, seg in enumerate(raw, 1)]
        candidate = _pack(sentences, budget)
        if len(candidate) == n:
            packed = candidate
            break
        n = len(candidate)

    total = len(packed)
    return [f"{seg} ({i}/{total})" for i, seg in enumerate(packed, 1)]


def single_segment(content: str, max_length: int | None) -> list[str]:
    """One segment, optionally truncated to max_length. Used by single-post
    channels (LinkedIn, Notion, Newsletter, Webhook, Export)."""
    text = content.strip()
    if max_length is not None and len(text) > max_length:
        text = text[:max_length]
    return [text] if text else []
