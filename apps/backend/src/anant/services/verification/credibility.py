"""Source credibility feedback (ADR-031).

The bootstrap prior (editorial_confidence/100.0, neutral 0.5 on miss) is set
in migration 0006. This module evolves `accuracy_rate` after each run.

Evolution rule — DESIGN NOTE: the Rev 3 blueprint specifies the *bootstrap*
(§14.6) and the *principle* (ADR-031: "updated after each run, no manual
curation") but does not pin an update formula. Wave C uses a bounded EMA
that preserves the bootstrap prior and nudges toward observed outcomes:

    verified   -> accuracy += ALPHA * (1.0 - accuracy)
    contested  -> accuracy += ALPHA * (0.0 - accuracy)
    unverified / unverifiable -> no change
        (absence of verification is not evidence of *in*accuracy — only a
         decisive verified/contested outcome moves the needle)

This is transparent, bounded to [0, 1], and convergent. A richer model
(per-topic, recency-weighted) is reserved via the unused `topic_reliability`
column and is a candidate for a future ADR-031 revision.
"""
from __future__ import annotations

ALPHA = 0.1


def next_accuracy(current: float, outcome: str) -> float:
    """Pure EMA step. `current` is the credibility as it stood when the
    claim was scored; the result is the post-run value."""
    if outcome == "verified":
        return current + ALPHA * (1.0 - current)
    if outcome == "contested":
        return current + ALPHA * (0.0 - current)
    # unverified / unverifiable: no accuracy signal.
    return current
