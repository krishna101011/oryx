"""IntakeProvider Protocol — the abstraction every vendor implements.

Phase 3 Batch 1 ships the Protocol + shared dataclasses (RawItem, SyncCursor,
ValidationResult). The concrete vendor providers (Gmail, RSS, Webhook,
API pull) implement this in Batch 2.

Why a Protocol and not an ABC:
  - Structural typing — vendor folders depend only on this file, never on
    each other.
  - Tests can supply a tiny fake without any inheritance gymnastics.
  - Plays cleanly with FastAPI Depends() for runtime injection.

Why dataclasses and not pydantic:
  - This is an INTERNAL contract. We don't validate at boundaries inside
    the backend; pydantic shows up only at the HTTP edge (router → service).
  - Frozen dataclasses are faster and immutable — good for things that
    travel through async pipelines.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol


class IntakeSourceKind(str, Enum):
    GMAIL = "gmail"
    RSS = "rss"
    WEBHOOK = "webhook"
    API_PULL = "api_pull"
    MANUAL = "manual"


@dataclass(frozen=True)
class RawItem:
    """Provider-agnostic item shape going INTO the normalizer.

    Every provider's `mapper.py` translates the vendor item into this shape.
    Fields are intentionally minimal — anything richer is carried in `payload`
    and surfaces on the normalized side via the normalizer rules.
    """

    external_id: str
    received_at: datetime
    sender: str | None
    subject: str | None
    body_text: str | None
    body_html: str | None
    links: list[dict[str, str]]
    payload: dict[str, Any]  # full provider raw, stored verbatim in intake_items.payload

    @property
    def primary_link(self) -> str | None:
        for link in self.links:
            url = (link.get("url") or "").strip()
            if url:
                return url
        return None


@dataclass(frozen=True)
class SyncCursor:
    """Opaque, provider-shaped cursor. Stored in `intake_sources.cursor` (jsonb).

    The orchestrator never inspects the contents. Each provider serializes
    its own state into `value`.
    """

    value: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SyncResult:
    """Summary returned by a single sync() invocation."""

    items_yielded: int
    new_cursor: SyncCursor | None
    completed: bool  # True if the source is now caught up


class ValidationStatus(str, Enum):
    OK = "ok"
    INVALID = "invalid"
    AUTH_REQUIRED = "auth_required"


@dataclass(frozen=True)
class ValidationResult:
    status: ValidationStatus
    message: str | None = None


class IntakeProvider(Protocol):
    """Every inbound data source implements this.

    sync() is the pull path. handle_webhook() is the push path (optional —
    default impl in webhook providers).

    Implementations MUST honor:
      - Idempotency by (intake_source_id, external_id)
      - Monotonic cursor (resuming never skips)
      - Vendor errors translated to ProviderError (see errors.py)
      - No business rules (no verification, no scoring, no classification)
    """

    name: str
    kind: IntakeSourceKind

    async def validate_config(
        self, config: dict[str, Any]
    ) -> ValidationResult: ...

    def sync(
        self,
        *,
        workspace_id: uuid.UUID,
        intake_source_id: uuid.UUID,
        cursor: SyncCursor | None,
        config: dict[str, Any],
    ) -> AsyncIterator[RawItem]: ...

    # NOTE: `handle_webhook` is intentionally NOT declared on the Protocol.
    # Webhook-capable providers (Phase 3 Batch 2's webhook provider, future
    # Slack push, etc.) define their own `handle_webhook(...)` with the
    # signature documented below. The orchestrator does a `hasattr(provider,
    # "handle_webhook")` check before invoking it, so pull-only providers
    # (RSS, Gmail, API pull) just don't define the method.
    #
    # Expected signature when implemented:
    #     async def handle_webhook(
    #         self, *, workspace_id, intake_source_id,
    #         headers, body, config,
    #     ) -> AsyncIterator[RawItem]: ...
