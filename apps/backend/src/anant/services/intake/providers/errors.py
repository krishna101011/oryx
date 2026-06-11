"""Provider error taxonomy + retry classifier.

A vendor SDK can raise hundreds of distinct exception types. We collapse
them into five intent-bearing kinds before they cross the provider boundary.
The orchestrator branches on the kind, not the underlying exception.

This is the file the scheduler consults to decide:
  - retry vs not retry
  - degrade source vs lock it as auth_required
  - whether to honor a Retry-After hint

Map your vendor exceptions to ProviderErrorKind inside the vendor folder's
`sync.py`. Do NOT raise raw vendor exceptions out of a provider.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProviderErrorKind(str, Enum):
    TRANSIENT = "transient"          # 5xx, network blip, timeout
    RATE_LIMITED = "rate_limited"    # 429
    AUTH = "auth"                    # 401/403 or refresh-token failure
    PERMANENT = "permanent"          # 4xx (non-auth), invalid response shape
    UNKNOWN = "unknown"              # anything else; treat as TRANSIENT


@dataclass(frozen=True)
class ProviderError(Exception):
    kind: ProviderErrorKind
    message: str
    retry_after_seconds: int | None = None
    cause_class: str | None = None

    def __str__(self) -> str:  # pragma: no cover — trivial
        return f"{self.kind.value}: {self.message}"


# ---------------------------------------------------------------------------
# Retry classifier — pure function of the error kind, attempt number,
# and (optional) Retry-After hint. The scheduler calls this; providers
# don't need to know about it.
# ---------------------------------------------------------------------------

MAX_TRANSIENT_RETRIES = 5
BASE_BACKOFF_SECONDS = 30
BACKOFF_CAP_SECONDS = 60 * 60
JITTER_RATIO = 0.10


@dataclass(frozen=True)
class RetryDecision:
    should_retry: bool
    delay_seconds: int
    final_status: str | None = None  # 'auth_required' | 'degraded' | None


def _backoff(attempts: int) -> int:
    delay = min(BASE_BACKOFF_SECONDS * (2 ** attempts), BACKOFF_CAP_SECONDS)
    return int(delay)


def classify_retry(
    error: ProviderError,
    *,
    attempts: int,
) -> RetryDecision:
    """Phase 3 retry policy per the frozen architecture §10.

    `attempts` is the count BEFORE this attempt (0 on first try).
    """
    kind = error.kind

    if kind == ProviderErrorKind.AUTH:
        # AUTH never auto-retries — only user intervention can fix it.
        return RetryDecision(
            should_retry=False,
            delay_seconds=0,
            final_status="auth_required",
        )

    if kind == ProviderErrorKind.PERMANENT:
        # Don't burn quota on something the vendor said is permanently wrong;
        # try again on the next scheduled tick.
        return RetryDecision(
            should_retry=False,
            delay_seconds=0,
            final_status="degraded",
        )

    if kind == ProviderErrorKind.RATE_LIMITED:
        delay = error.retry_after_seconds or _backoff(attempts)
        return RetryDecision(should_retry=True, delay_seconds=delay)

    # TRANSIENT and UNKNOWN follow the same backoff curve, but UNKNOWN
    # exits to degraded after fewer attempts so it's visible to ops.
    if kind == ProviderErrorKind.TRANSIENT:
        if attempts >= MAX_TRANSIENT_RETRIES:
            return RetryDecision(
                should_retry=False, delay_seconds=0, final_status="degraded"
            )
        return RetryDecision(should_retry=True, delay_seconds=_backoff(attempts))

    # UNKNOWN
    if attempts >= 2:
        return RetryDecision(
            should_retry=False, delay_seconds=0, final_status="degraded"
        )
    return RetryDecision(should_retry=True, delay_seconds=_backoff(attempts))
