"""VerificationEngine — deterministic per-claim outcome. No AI, pure logic.

Implements §14.3 exactly. The engine reads the LINK relationship (ADR-037);
a "primary" link is a supporting link backed by primary_source evidence —
the single place the engine consults evidence_type.

Outcome rules, by epistemic type:
  unclassified                 -> unverifiable          (never typed -> cannot verify)
  opinion | rumor | speculation-> contested if any contradiction else unverified
                                  (these types CANNOT reach 'verified', ever — the
                                   epistemic ceiling lives in the scorer; the engine
                                   refuses the 'verified' label here)
  fact   -> needs a primary supporting link; else unverified;
            contested if any contradiction, else verified
  claim  -> needs any supporting link; else unverified;
            contested if any contradiction, else verified
"""
from __future__ import annotations

from oryx.services.verification.models import EvidenceLinkInput

ENGINE_VERSION = 1

_NEVER_VERIFIED = ("opinion", "rumor", "speculation")


class VerificationEngine:
    version = ENGINE_VERSION

    def determine_outcome(
        self, epistemic_type: str, links: list[EvidenceLinkInput]
    ) -> str:
        has_primary = any(
            l.relationship == "supports" and l.evidence_type == "primary_source"
            for l in links
        )
        has_support = any(l.relationship == "supports" for l in links)
        has_contradiction = any(l.relationship == "contradicts" for l in links)

        if epistemic_type == "unclassified":
            return "unverifiable"

        if epistemic_type in _NEVER_VERIFIED:
            return "contested" if has_contradiction else "unverified"

        if epistemic_type == "fact":
            if not has_primary:
                return "unverified"
            return "contested" if has_contradiction else "verified"

        if epistemic_type == "claim":
            if not has_support:
                return "unverified"
            return "contested" if has_contradiction else "verified"

        # Defensive: an unknown type is treated as unverifiable, never verified.
        return "unverifiable"
