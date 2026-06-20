"""Phase 4 event-name constants.

Every emit site imports from here — no string literals for event names
anywhere in Wave A code. Names follow the ADR-014 convention
(<domain>.<entity>.<verb_past_tense>) and are immutable once shipped.
"""
from __future__ import annotations

CLAIM_EXTRACTED = "verification.claim.extracted"
CLAIM_TYPED = "verification.claim.typed"
