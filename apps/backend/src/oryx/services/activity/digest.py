"""DigestWorker — separate-process entry point (Phase 6 Wave B).

Run:
    python -m oryx.services.activity.digest

Same shape as the intake scheduler, the outbox drainer, and the calendar
scheduler (CR-7 / ADR-025): a tick loop in a standalone process, colocatable
into the API via oryx_dev_monoprocess in dev. The first tick runs immediately
at startup (before the first sleep) so a downtime backlog is caught up.

Each tick, for every (account, category) with an in_app alert_preferences row
at frequency 'daily' or 'weekly' (docs/PHASE_6_ARCHITECTURE.md §4.2 — the
cadence decision is the EXISTING per-account, per-category preference, nothing
new is invented here):

  1. resolve the account's LOCAL time from profiles.timezone (IANA name,
     default 'UTC') — no UTC hardcoding in the send-time check;
  2. compute the most recent send point: daily = local 08:00, weekly = local
     Monday 08:00;
  3. skip if a digest_runs row already covers that window — the
     UNIQUE(account_id, activity_type, frequency, window_start) constraint is
     the backstop, same idempotency principle as automation_log in Wave A;
  4. gather every activity_inbox row of that category created in
     [last window_end (or account creation), send point). Zero rows → write
     NOTHING (silence, not an empty digest — the next digest's window simply
     stretches back further, so no source row is ever lost or double-bundled);
  5. one or more rows → insert ONE activity_inbox bundle row
     (type='daily_digest'/'weekly_digest', data referencing the bundled ids)
     plus ONE digest_runs row, committed in ONE transaction.

Delivery boundary: the output is an in-app activity_inbox row ONLY — push is
Wave C, email digests are explicitly out of scope (§4.2). The
NotificationDispatcher is not touched; this worker only reads what it wrote.
"""
from __future__ import annotations

import asyncio
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import Row, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oryx.core.logging import get_logger
from oryx.core.models import Account, ActivityInbox, AlertPreference, DigestRun, Profile

logger = get_logger(__name__)

DEFAULT_TICK_SECONDS = 60.0

# Send points are LOCAL wall-clock times (§4.2 + the Wave B defaults):
# daily at 08:00 local, weekly at Monday 08:00 local.
SEND_HOUR_LOCAL = 8
WEEKLY_SEND_WEEKDAY = 0  # Monday (date.weekday() convention)

# frequency -> the activity_type bundle-row marker the digest row carries.
DIGEST_ROW_TYPE = {"daily": "daily_digest", "weekly": "weekly_digest"}

# How many bundled titles the body quotes before "+N more".
BODY_HIGHLIGHTS = 3

_SEVERITY_RANK = {"info": 0, "warning": 1, "error": 2}


def latest_send_point(*, now: datetime, tz: ZoneInfo, frequency: str) -> datetime:
    """The most recent send instant at or before `now`, as an aware UTC datetime.

    Computed in LOCAL wall-clock terms (build the local 08:00 datetime, let
    zoneinfo resolve its UTC offset) so DST transitions shift the UTC instant,
    not the local send time. Stepping back happens on the DATE (then
    re-localizing), never by subtracting a timedelta from an aware local
    datetime — that would silently cross DST boundaries at the wrong offset.
    """
    local_now = now.astimezone(tz)
    candidate_date = local_now.date()
    if frequency == "weekly":
        candidate_date -= timedelta(days=candidate_date.weekday() - WEEKLY_SEND_WEEKDAY)
    candidate = _local_send_dt(candidate_date, tz)
    if candidate > local_now:
        step = 7 if frequency == "weekly" else 1
        candidate = _local_send_dt(candidate_date - timedelta(days=step), tz)
    return candidate.astimezone(UTC)


def _local_send_dt(day: date, tz: ZoneInfo) -> datetime:
    return datetime(day.year, day.month, day.day, SEND_HOUR_LOCAL, tzinfo=tz)


@dataclass(frozen=True)
class _DigestTarget:
    """One (account, category, cadence) combination due for evaluation."""

    account_id: uuid.UUID
    category: str
    frequency: str
    timezone: str
    account_created_at: datetime


class DigestWorker:
    """Tick loop that bundles digest-cadence accounts' feed rows (§4.2)."""

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        tick_seconds: float = DEFAULT_TICK_SECONDS,
    ) -> None:
        self._sm = sessionmaker
        self._tick_seconds = tick_seconds

    async def tick(self, now: datetime | None = None) -> int:
        """Evaluate every digest-cadence target once; return digests sent."""
        now = now if now is not None else datetime.now(UTC)
        async with self._sm() as session:
            targets = await _digest_targets(session)
        sent = 0
        for target in targets:
            try:
                if await self._process_target(target, now):
                    sent += 1
            except Exception:
                # One bad target (e.g. a corrupt timezone string) must never
                # kill the loop; the rest of the accounts still get digests.
                logger.exception(
                    "digest.target_crashed",
                    extra={
                        "account_id": str(target.account_id),
                        "category": target.category,
                        "frequency": target.frequency,
                    },
                )
        return sent

    async def _process_target(self, target: _DigestTarget, now: datetime) -> bool:
        tz = _safe_zone(target.timezone, account_id=target.account_id)
        send_point = latest_send_point(now=now, tz=tz, frequency=target.frequency)

        async with self._sm() as session:
            last_window_end = await session.scalar(
                select(DigestRun.window_end)
                .where(
                    DigestRun.account_id == target.account_id,
                    DigestRun.activity_type == target.category,
                    DigestRun.frequency == target.frequency,
                )
                .order_by(DigestRun.window_end.desc())
                .limit(1)
            )
            window_start = (
                last_window_end if last_window_end is not None
                else target.account_created_at
            )
            if window_start >= send_point:
                # Current window already sent, or the account is newer than
                # the send point (its first window hasn't closed yet).
                return False

            # Explicit idempotency check on the unique key; the constraint
            # itself is the backstop for a concurrent double-tick.
            already = await session.scalar(
                select(DigestRun.id).where(
                    DigestRun.account_id == target.account_id,
                    DigestRun.activity_type == target.category,
                    DigestRun.frequency == target.frequency,
                    DigestRun.window_start == window_start,
                )
            )
            if already is not None:
                return False

            rows = (
                await session.execute(
                    select(
                        ActivityInbox.id, ActivityInbox.title, ActivityInbox.severity
                    )
                    .where(
                        ActivityInbox.account_id == target.account_id,
                        ActivityInbox.type == target.category,
                        ActivityInbox.created_at >= window_start,
                        ActivityInbox.created_at < send_point,
                    )
                    .order_by(ActivityInbox.created_at)
                )
            ).all()
            if not rows:
                # Zero new activity → NO digest and NO digest_runs row. The
                # next digest's window_start stays put, so these empty windows
                # fold into the next non-empty digest without loss.
                return False

            digest = _build_digest_row(target, rows)
            session.add(digest)
            session.add(
                DigestRun(
                    id=uuid.uuid4(),
                    account_id=target.account_id,
                    activity_type=target.category,
                    frequency=target.frequency,
                    window_start=window_start,
                    window_end=send_point,
                )
            )
            try:
                # ONE transaction: the bundle row and its idempotency record
                # land together or not at all.
                await session.commit()
            except IntegrityError:
                # Lost a race with a concurrent tick: that tick's digest is
                # the real one, ours is a no-op.
                await session.rollback()
                return False

        logger.info(
            "digest.sent",
            extra={
                "account_id": str(target.account_id),
                "category": target.category,
                "frequency": target.frequency,
                "bundled": len(rows),
                "window_end": send_point.isoformat(),
            },
        )
        return True

    async def run_forever(self) -> None:
        # The first tick happens immediately (startup catch-up), BEFORE any
        # sleep, so a downtime backlog is processed without waiting a full
        # interval — same contract as the other three workers.
        while True:
            sent = await self.tick()
            if sent:
                logger.info("digest.tick", extra={"digests_sent": sent})
            await asyncio.sleep(self._tick_seconds)


async def _digest_targets(session: AsyncSession) -> list[_DigestTarget]:
    """Every (account, category) with an in_app preference at digest cadence.

    channel='in_app' because this wave's output IS the in-app feed row (§4.2
    reads preferences "for a given category/channel", and in_app is the only
    channel Phase 6 delivers on until Wave C). Profile is outer-joined:
    signup always creates one (timezone 'UTC'), but a missing row must not
    silently drop an account from digests.
    """
    result = await session.execute(
        select(
            AlertPreference.account_id,
            AlertPreference.type,
            AlertPreference.frequency,
            Profile.timezone,
            Account.created_at,
        )
        .join(Account, Account.id == AlertPreference.account_id)
        .outerjoin(Profile, Profile.account_id == AlertPreference.account_id)
        .where(
            AlertPreference.channel == "in_app",
            AlertPreference.frequency.in_(tuple(DIGEST_ROW_TYPE)),
        )
    )
    return [
        _DigestTarget(
            account_id=row.account_id,
            category=row.type,
            frequency=row.frequency,
            timezone=row.timezone or "UTC",
            account_created_at=row.created_at,
        )
        for row in result.all()
    ]


def _safe_zone(name: str, *, account_id: uuid.UUID) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (KeyError, ValueError):
        logger.warning(
            "digest.bad_timezone",
            extra={"account_id": str(account_id), "timezone": name},
        )
        return ZoneInfo("UTC")


def _build_digest_row(
    target: _DigestTarget, rows: Sequence[Row[tuple[uuid.UUID, str, str]]]
) -> ActivityInbox:
    count = len(rows)
    highlights = "; ".join(row.title for row in rows[:BODY_HIGHLIGHTS])
    if count > BODY_HIGHLIGHTS:
        highlights += f"; +{count - BODY_HIGHLIGHTS} more"
    label = "Daily" if target.frequency == "daily" else "Weekly"
    plural = "" if count == 1 else "s"
    return ActivityInbox(
        id=uuid.uuid4(),
        account_id=target.account_id,
        # A bundle can span workspaces, so the digest row is account-scoped.
        workspace_id=None,
        type=DIGEST_ROW_TYPE[target.frequency],
        # The bundle inherits the most severe thing it contains.
        severity=max((row.severity for row in rows), key=_SEVERITY_RANK.__getitem__),
        title=f"{label} digest — {count} {target.category} update{plural}",
        body=f"{count} {target.category} notification{plural}: {highlights}",
        data={
            "bundled_ids": [str(row.id) for row in rows],
            "category": target.category,
            "count": count,
        },
        source_event_type=None,
        source_event_id=None,
    )


async def amain() -> None:
    from oryx.core.db import get_sessionmaker
    from oryx.core.logging import configure_logging

    configure_logging()
    worker = DigestWorker(get_sessionmaker())
    logger.info("digest_worker.started", extra={"tick_seconds": DEFAULT_TICK_SECONDS})
    await worker.run_forever()


if __name__ == "__main__":
    asyncio.run(amain())
