"""Per-source sync execution — provider construction, ingestion, persistence.

The scheduler (scheduler.py) decides WHICH sources are due; this module
executes ONE source's sync end to end:

    load source → audit sync_start → provider.sync() → ingest each RawItem
    (own transaction per item) → persist cursor + health → audit sync_complete

Failure paths route through the §10 retry classifier: the runner never
sleeps — backoff is realized by the scheduler's due-time computation on
`consecutive_failures`, so a slow vendor can't hold a worker slot hostage.

Provider construction is the ONLY place credentials are wired. Providers
receive async callables (token_provider / credentials_provider) and never
touch credential storage — same boundary Wave D established.
"""
from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.config import get_settings
from oryx.core.logging import get_logger
from oryx.core.models import IntakeSource, WorkspaceCustomSource
from oryx.services.intake.credentials import IntakeCredentialsRepository
from oryx.services.intake.providers.api_pull.client import ResolvedCredentials
from oryx.services.intake.providers.api_pull.sync import (
    ApiPullProvider,
)
from oryx.services.intake.providers.api_pull.sync import (
    cursor_from_report as api_pull_cursor,
)
from oryx.services.intake.providers.base import SyncCursor
from oryx.services.intake.providers.errors import (
    ProviderError,
    ProviderErrorKind,
    classify_retry,
)
from oryx.services.intake.providers.gmail import auth as gmail_auth
from oryx.services.intake.providers.gmail.sync import (
    GmailProvider,
)
from oryx.services.intake.providers.gmail.sync import (
    cursor_from_report as gmail_cursor,
)
from oryx.services.intake.providers.rss.sync import (
    RssProvider,
)
from oryx.services.intake.providers.rss.sync import (
    cursor_from_report as rss_cursor,
)
from oryx.services.intake.repository import IntakeRepository
from oryx.services.intake.service import IntakeService

logger = get_logger(__name__)

# §10.3 — consecutive failures before the circuit opens.
CIRCUIT_BREAK_THRESHOLD = 10
# Refresh the Gmail access token when it expires within this window.
TOKEN_EXPIRY_SKEW = timedelta(seconds=60)
MAX_STORED_ERROR_CHARS = 2000


class SyncOutcome(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class SourceSnapshot:
    """Immutable view of the source row taken at sync start.

    The sync may run for a while; we act on what was true when it started
    and re-read nothing mid-flight except via fresh sessions at persist time.
    """

    id: uuid.UUID
    workspace_id: uuid.UUID
    kind: str
    config: dict[str, Any]
    cursor: dict[str, Any] | None
    status: str
    consecutive_failures: int
    origin_custom_id: uuid.UUID | None


ProviderFactory = Callable[
    [SourceSnapshot, async_sessionmaker[AsyncSession]], Any
]


class SourceSyncRunner:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        provider_factory: ProviderFactory | None = None,
    ) -> None:
        self._sm = sessionmaker
        self._provider_factory = provider_factory or build_provider

    async def sync_source(self, source_id: uuid.UUID) -> SyncOutcome:
        snapshot = await self._claim(source_id)
        if snapshot is None:
            return SyncOutcome.SKIPPED

        provider = self._provider_factory(snapshot, self._sm)

        items = 0
        try:
            async with self._sm() as session:
                service = IntakeService(session)
                async for raw in provider.sync(
                    workspace_id=snapshot.workspace_id,
                    intake_source_id=snapshot.id,
                    cursor=SyncCursor(value=snapshot.cursor) if snapshot.cursor else None,
                    config=snapshot.config,
                ):
                    await service.ingest_raw_item(
                        workspace_id=snapshot.workspace_id,
                        intake_source_id=snapshot.id,
                        provider_name=provider.name,
                        raw=raw,
                    )
                    # Own transaction per item (service.py contract): one bad
                    # item never rolls back its siblings.
                    await session.commit()
                    items += 1
        except ProviderError as err:
            await self._record_failure(snapshot, err)
            return SyncOutcome.FAILED
        except Exception as e:
            # leaks despite the taxonomy is treated as UNKNOWN per §10.1
            unknown = ProviderError(
                kind=ProviderErrorKind.UNKNOWN,
                message=str(e)[:MAX_STORED_ERROR_CHARS],
                cause_class=type(e).__name__,
            )
            await self._record_failure(snapshot, unknown)
            return SyncOutcome.FAILED

        await self._record_success(snapshot, provider, items)
        return SyncOutcome.COMPLETED

    # ------------------------------------------------------------------
    # Persistence steps — each opens its own short session.
    # ------------------------------------------------------------------

    async def _claim(self, source_id: uuid.UUID) -> SourceSnapshot | None:
        """Re-read the source, stamp last_attempt_at, audit sync_start.

        Stamping last_attempt_at first means a crashed sync is retried on
        the failure-backoff curve instead of immediately — safe default.
        """
        async with self._sm() as session:
            src = await session.get(IntakeSource, source_id)
            if src is None or src.deleted_at is not None or not src.enabled:
                return None
            snapshot = SourceSnapshot(
                id=src.id,
                workspace_id=src.workspace_id,
                kind=src.kind,
                config=dict(src.config or {}),
                cursor=dict(src.cursor) if src.cursor else None,
                status=src.status,
                consecutive_failures=src.consecutive_failures,
                origin_custom_id=src.origin_custom_id,
            )
            src.last_attempt_at = datetime.now(UTC)
            repo = IntakeRepository(session)
            await repo.write_audit(
                workspace_id=src.workspace_id,
                intake_source_id=src.id,
                event="sync_start",
                data={"kind": src.kind},
            )
            await session.commit()
            return snapshot

    async def _record_success(
        self, snapshot: SourceSnapshot, provider: Any, items: int
    ) -> None:
        report = getattr(provider, "last_report", None)
        async with self._sm() as session:
            service = IntakeService(session)
            repo = IntakeRepository(session)

            redirect_to: str | None = getattr(report, "permanent_redirect_to", None)
            if redirect_to:
                await self._persist_redirect(session, repo, snapshot, redirect_to)

            if getattr(report, "fallback_recovered", False):
                # CR-5 — the provider already self-healed; we make it visible.
                await repo.write_audit(
                    workspace_id=snapshot.workspace_id,
                    intake_source_id=snapshot.id,
                    event="gmail_history_expired",
                    data={"recovered": True},
                )

            # No report → the provider learned nothing; keep the old cursor
            # rather than wiping the column.
            new_cursor = (
                _cursor_from_report(snapshot.kind, report)
                if report is not None
                else snapshot.cursor
            )
            await service.mark_sync_success(
                source_id=snapshot.id, new_cursor=new_cursor
            )

            if snapshot.status == "degraded":
                await repo.write_audit(
                    workspace_id=snapshot.workspace_id,
                    intake_source_id=snapshot.id,
                    event="circuit_recovered",
                    data={},
                )

            await repo.write_audit(
                workspace_id=snapshot.workspace_id,
                intake_source_id=snapshot.id,
                event="sync_complete",
                data={"items": items},
            )
            await session.commit()

    async def _persist_redirect(
        self,
        session: AsyncSession,
        repo: IntakeRepository,
        snapshot: SourceSnapshot,
        new_url: str,
    ) -> None:
        """CR-10: 301 → persist the new URL on the operational config AND the
        originating Phase 2 custom-source row, then audit. Clearing
        last_attempt_at makes the next tick the "retry once with new URL"."""
        old_url = snapshot.config.get("feed_url")
        await session.execute(
            update(IntakeSource)
            .where(IntakeSource.id == snapshot.id)
            .values(
                config={**snapshot.config, "feed_url": new_url},
                last_attempt_at=None,
                updated_at=datetime.now(UTC),
            )
        )
        if snapshot.origin_custom_id is not None:
            await session.execute(
                update(WorkspaceCustomSource)
                .where(WorkspaceCustomSource.id == snapshot.origin_custom_id)
                .values(url=new_url)
            )
        await repo.write_audit(
            workspace_id=snapshot.workspace_id,
            intake_source_id=snapshot.id,
            event="rss_permanent_redirect",
            data={"old_url": old_url, "new_url": new_url},
        )

    async def _record_failure(
        self, snapshot: SourceSnapshot, err: ProviderError
    ) -> None:
        decision = classify_retry(err, attempts=snapshot.consecutive_failures)
        failures_after = snapshot.consecutive_failures + 1
        next_status = decision.final_status
        circuit_broken = False
        if next_status is None and failures_after >= CIRCUIT_BREAK_THRESHOLD:
            next_status = "degraded"
            circuit_broken = True

        async with self._sm() as session:
            service = IntakeService(session)
            repo = IntakeRepository(session)
            await service.mark_sync_failure(
                source_id=snapshot.id,
                error_message=str(err)[:MAX_STORED_ERROR_CHARS],
                next_status=next_status,
            )
            await repo.write_audit(
                workspace_id=snapshot.workspace_id,
                intake_source_id=snapshot.id,
                event="sync_failed",
                data={
                    "kind": err.kind.value,
                    "message": err.message[:500],
                    "consecutive_failures": failures_after,
                },
            )
            if err.kind == ProviderErrorKind.AUTH:
                await repo.write_audit(
                    workspace_id=snapshot.workspace_id,
                    intake_source_id=snapshot.id,
                    event="auth_lapsed",
                    data={},
                )
            if circuit_broken:
                await repo.write_audit(
                    workspace_id=snapshot.workspace_id,
                    intake_source_id=snapshot.id,
                    event="circuit_broken",
                    data={"consecutive_failures": failures_after},
                )
            await session.commit()
        logger.warning(
            "intake.sync_failed",
            extra={
                "intake_source_id": str(snapshot.id),
                "error_kind": err.kind.value,
                "next_status": next_status,
            },
        )


# ---------------------------------------------------------------------------
# Provider factory + credential wiring
# ---------------------------------------------------------------------------

def build_provider(
    snapshot: SourceSnapshot, sm: async_sessionmaker[AsyncSession]
) -> Any:
    if snapshot.kind == "rss":
        return RssProvider()
    if snapshot.kind == "gmail":
        return GmailProvider(token_provider=_gmail_token_provider(sm, snapshot))
    if snapshot.kind == "api_pull":
        return ApiPullProvider(
            credentials_provider=_api_pull_credentials_provider(sm, snapshot)
        )
    # webhook = push-only, manual = operator-only; neither is pollable.
    raise ValueError(f"source kind {snapshot.kind!r} is not pollable")


@dataclass(frozen=True)
class _AccessToken:
    access_token: str


def _gmail_token_provider(
    sm: async_sessionmaker[AsyncSession], snapshot: SourceSnapshot
) -> Callable[[], Awaitable[_AccessToken]]:
    async def provide() -> _AccessToken:
        async with sm() as session:
            creds_repo = IntakeCredentialsRepository(session)
            pair = await creds_repo.load(
                intake_source_id=snapshot.id, workspace_id=snapshot.workspace_id
            )
            if pair is None:
                raise ProviderError(
                    kind=ProviderErrorKind.AUTH,
                    message="no stored credentials for gmail source",
                )
            now = datetime.now(UTC)
            fresh = (
                pair.token_expires_at is not None
                and pair.token_expires_at - TOKEN_EXPIRY_SKEW > now
            )
            if fresh or pair.refresh_token is None:
                # No refresh token → use what we have; if it's actually
                # expired Gmail returns 401 → ProviderError(AUTH) →
                # auth_required, which is the correct terminal state.
                return _AccessToken(pair.token.decode("utf-8"))

            settings = get_settings()
            if not settings.gmail_client_id or not settings.gmail_client_secret:
                raise ProviderError(
                    kind=ProviderErrorKind.AUTH,
                    message="gmail oauth client not configured",
                )
            bundle = await gmail_auth.refresh_access_token(
                refresh_token=pair.refresh_token.decode("utf-8"),
                client_id=settings.gmail_client_id,
                client_secret=settings.gmail_client_secret,
            )
            await creds_repo.store(
                intake_source_id=snapshot.id,
                workspace_id=snapshot.workspace_id,
                token=bundle.access_token.encode("utf-8"),
                # Google usually omits the refresh token on refresh; keep ours.
                refresh_token=(
                    bundle.refresh_token.encode("utf-8")
                    if bundle.refresh_token
                    else pair.refresh_token
                ),
                token_expires_at=now + timedelta(seconds=bundle.expires_in_seconds),
                kms_key_version=pair.kms_key_version,
            )
            await session.commit()
            return _AccessToken(bundle.access_token)

    return provide


def _api_pull_credentials_provider(
    sm: async_sessionmaker[AsyncSession], snapshot: SourceSnapshot
) -> Callable[[], Awaitable[ResolvedCredentials]]:
    async def provide() -> ResolvedCredentials:
        async with sm() as session:
            pair = await IntakeCredentialsRepository(session).load(
                intake_source_id=snapshot.id, workspace_id=snapshot.workspace_id
            )
        if pair is None:
            raise ProviderError(
                kind=ProviderErrorKind.AUTH,
                message="no stored credentials for api_pull source",
            )
        if snapshot.config.get("auth_method") == "oauth2_client_credentials":
            # Storage convention for oauth2_cc sources:
            #   encrypted_token         = client_id
            #   encrypted_refresh_token = client_secret
            if pair.refresh_token is None:
                raise ProviderError(
                    kind=ProviderErrorKind.AUTH,
                    message="oauth2_client_credentials source is missing client_secret",
                )
            return ResolvedCredentials(
                client_id=pair.token.decode("utf-8"),
                client_secret=pair.refresh_token.decode("utf-8"),
            )
        return ResolvedCredentials(token=pair.token.decode("utf-8"))

    return provide


def _cursor_from_report(kind: str, report: Any) -> dict[str, Any]:
    if kind == "rss":
        return rss_cursor(report)
    if kind == "gmail":
        return gmail_cursor(report)
    if kind == "api_pull":
        return api_pull_cursor(report)
    raise ValueError(f"no cursor mapping for kind {kind!r}")
