"""Thin service wrapper. Phase 3 normalization has no state; this exists for
parity with other services (router → service → providers → repository) and
so callers depend on a stable surface even as the normalizer evolves.
"""
from __future__ import annotations

from typing import Any

from oryx.services.normalization.normalizer import (
    NormalizedItem,
    normalize_raw_item,
)


class NormalizationService:
    """Stateless. Safe to construct ad-hoc."""

    def normalize(self, raw_payload: dict[str, Any]) -> NormalizedItem:
        return normalize_raw_item(raw_payload)
