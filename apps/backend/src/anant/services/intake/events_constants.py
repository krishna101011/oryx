"""Phase 3 intake event names, as constants for Phase 4+ subscribers.

Added in Phase 4 Wave A so subscriber registrations never use string
literals. The Phase 3 emit site predates this module and is frozen;
the name itself is immutable per ADR-014 §2.3.
"""
from __future__ import annotations

INTAKE_ITEM_RECEIVED = "intake.item.received"
