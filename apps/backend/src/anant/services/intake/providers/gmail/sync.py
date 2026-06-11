"""GmailProvider sync loop — historyId cursor with CR-5 expiry recovery.

Three sync paths share one orchestrator:

  1. Bootstrap (no cursor)        →  list_messages bounded by lookback_days_initial
  2. Steady state (cursor present)→  history.list(startHistoryId=cursor)
  3. CR-5 expiry recovery         →  history.list returns 404 → fall back to
                                     list_messages newer_than:<lookback>d → re-establish cursor

The provider does NOT call into IntakeService here. It just yields RawItems
and exposes the report via `last_report` so the orchestrator can persist
the new cursor and audit-log the recovery (when it happened).
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any

from anant.services.intake.providers.base import (
    IntakeSourceKind,
    RawItem,
    SyncCursor,
    ValidationResult,
    ValidationStatus,
)
from anant.services.intake.providers.gmail import client as gmail_client
from anant.services.intake.providers.gmail.config_schema import GmailSourceConfig
from anant.services.intake.providers.gmail.mapper import gmail_message_to_raw

# A small cap so the bootstrap pull cannot DoS the mailbox on a brand-new
# connect. Phase 4+ can lift this when paginated bootstrap matters.
BOOTSTRAP_MESSAGE_CAP = 200


# ---------------------------------------------------------------------------
# Report — what the caller persists after sync completes.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GmailSyncReport:
    new_history_id: str | None
    bootstrap_complete: bool
    items_yielded: int
    fallback_recovered: bool  # CR-5 flag — caller writes 'gmail_history_expired' audit


def cursor_from_report(report: GmailSyncReport) -> dict[str, Any]:
    out: dict[str, Any] = {"bootstrap_complete": report.bootstrap_complete}
    if report.new_history_id:
        out["history_id"] = report.new_history_id
    return out


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

# The TokenProvider is a callable the orchestrator hands the provider so the
# provider can ask for a (possibly refreshed) access token at sync time
# without ever touching credential storage directly. Keeps credential I/O
# in one place (services/intake/credentials.py).
TokenProvider = Callable[[], "AccessTokenAwaitable"]


class AccessTokenAwaitable:  # tiny duck-type for the awaited result
    access_token: str


class GmailProvider:
    """Stateless per request. `last_report` set on each sync() invocation."""

    name = "gmail"
    kind = IntakeSourceKind.GMAIL

    def __init__(self, *, token_provider: Any) -> None:
        # `token_provider` is an async callable returning an object with an
        # `access_token` attribute. The orchestrator wires this from
        # IntakeCredentialsRepository so we never store tokens inside the
        # provider.
        self._token_provider = token_provider
        self._last_report: GmailSyncReport | None = None

    @property
    def last_report(self) -> GmailSyncReport | None:
        return self._last_report

    async def validate_config(self, config: dict[str, Any]) -> ValidationResult:
        try:
            GmailSourceConfig.model_validate(config)
            return ValidationResult(status=ValidationStatus.OK)
        except Exception as e:
            return ValidationResult(
                status=ValidationStatus.INVALID, message=str(e)
            )

    async def sync(
        self,
        *,
        workspace_id: uuid.UUID,
        intake_source_id: uuid.UUID,
        cursor: SyncCursor | None,
        config: dict[str, Any],
    ) -> AsyncIterator[RawItem]:
        parsed = GmailSourceConfig.model_validate(config)
        c = cursor.value if cursor else {}
        history_id: str | None = c.get("history_id")
        bootstrap_complete: bool = bool(c.get("bootstrap_complete"))

        token_obj = await self._token_provider()
        access_token = token_obj.access_token

        # Path 1: bootstrap
        if not bootstrap_complete or not history_id:
            new_history_id, count, items = await _bootstrap(
                access_token=access_token,
                labels=parsed.labels_watched,
                lookback_days=parsed.max_lookback_days_initial,
            )
            for raw in items:
                yield raw
            self._last_report = GmailSyncReport(
                new_history_id=new_history_id,
                bootstrap_complete=True,
                items_yielded=count,
                fallback_recovered=False,
            )
            return

        # Path 2/3: delta or CR-5 fallback
        try:
            new_history_id, count, items = await _delta(
                access_token=access_token,
                start_history_id=history_id,
                labels=parsed.labels_watched,
            )
            for raw in items:
                yield raw
            self._last_report = GmailSyncReport(
                new_history_id=new_history_id,
                bootstrap_complete=True,
                items_yielded=count,
                fallback_recovered=False,
            )
        except gmail_client.HistoryIdExpiredError:
            # CR-5 recovery: behave like bootstrap, then surface the flag so
            # the orchestrator can write an 'gmail_history_expired' audit entry.
            new_history_id, count, items = await _bootstrap(
                access_token=access_token,
                labels=parsed.labels_watched,
                lookback_days=parsed.max_lookback_days_initial,
            )
            for raw in items:
                yield raw
            self._last_report = GmailSyncReport(
                new_history_id=new_history_id,
                bootstrap_complete=True,
                items_yielded=count,
                fallback_recovered=True,
            )


# ---------------------------------------------------------------------------
# Internals — bootstrap and delta pull. Pure functions for testability.
# ---------------------------------------------------------------------------

async def _bootstrap(
    *,
    access_token: str,
    labels: list[str],
    lookback_days: int,
) -> tuple[str | None, int, list[RawItem]]:
    """Bounded historical pull (CR-5 fallback path uses this too)."""
    query = f"newer_than:{lookback_days}d"
    collected_ids: list[str] = []
    page_token: str | None = None
    while True:
        page = await gmail_client.list_messages(
            access_token=access_token,
            label_ids=labels,
            query=query,
            page_token=page_token,
            max_results=100,
        )
        collected_ids.extend(page.message_ids)
        if not page.next_page_token or len(collected_ids) >= BOOTSTRAP_MESSAGE_CAP:
            break
        page_token = page.next_page_token

    collected_ids = collected_ids[:BOOTSTRAP_MESSAGE_CAP]

    items = await _fetch_full_messages(access_token, collected_ids)

    # Cursor is the latest historyId — get it from the mailbox profile.
    profile = await gmail_client.get_profile(access_token=access_token)
    new_history_id = str(profile.get("historyId")) if profile.get("historyId") else None
    return new_history_id, len(items), items


async def _delta(
    *,
    access_token: str,
    start_history_id: str,
    labels: list[str],
) -> tuple[str | None, int, list[RawItem]]:
    """Steady-state pull via history.list. May raise HistoryIdExpiredError → caller falls back."""
    label_id = labels[0] if labels else None
    collected_ids: list[str] = []
    new_history_id: str | None = None
    page_token: str | None = None
    while True:
        page = await gmail_client.list_history(
            access_token=access_token,
            start_history_id=start_history_id,
            label_id=label_id,
            page_token=page_token,
        )
        new_history_id = page.history_id or new_history_id
        collected_ids.extend(page.message_ids)
        if not page.next_page_token:
            break
        page_token = page.next_page_token

    items = await _fetch_full_messages(access_token, collected_ids)
    return new_history_id, len(items), items


async def _fetch_full_messages(
    access_token: str, ids: list[str]
) -> list[RawItem]:
    out: list[RawItem] = []
    for mid in ids:
        msg = await gmail_client.get_message(
            access_token=access_token, message_id=mid, format="full"
        )
        out.append(gmail_message_to_raw(msg))
    return out
