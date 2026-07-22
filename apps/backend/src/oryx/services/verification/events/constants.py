"""Wave C event-name constants. Import at every emit site — no literals."""
from __future__ import annotations

CLAIM_VERIFIED = "verification.claim.verified"
CLAIM_FAILED = "verification.claim.failed"
# Post-freeze §3.3 extension (2026-07-22 ADR): observational quality signal,
# one event per AI parse failure on an HTTP-200 response. Payload carries
# callType ("extractor" | "classifier" | "conflict_detector" |
# "evidence_linker"). Analytics-only — deliberately absent from the
# dispatcher's notification catalog.
AI_PARSE_FAILED = "verification.ai.parse_failed"
