"""Retry classifier — pure function of error kind + attempts."""
from __future__ import annotations

from oryx.services.intake.providers.errors import (
    MAX_TRANSIENT_RETRIES,
    ProviderError,
    ProviderErrorKind,
    classify_retry,
)


def test_auth_error_never_retries_and_marks_auth_required() -> None:
    err = ProviderError(kind=ProviderErrorKind.AUTH, message="401")
    decision = classify_retry(err, attempts=0)
    assert decision.should_retry is False
    assert decision.final_status == "auth_required"


def test_permanent_error_does_not_retry_within_attempt_marks_degraded() -> None:
    err = ProviderError(kind=ProviderErrorKind.PERMANENT, message="invalid feed")
    decision = classify_retry(err, attempts=0)
    assert decision.should_retry is False
    assert decision.final_status == "degraded"


def test_rate_limited_honors_retry_after() -> None:
    err = ProviderError(
        kind=ProviderErrorKind.RATE_LIMITED, message="429", retry_after_seconds=42
    )
    decision = classify_retry(err, attempts=0)
    assert decision.should_retry is True
    assert decision.delay_seconds == 42


def test_rate_limited_without_hint_uses_backoff() -> None:
    err = ProviderError(kind=ProviderErrorKind.RATE_LIMITED, message="429")
    decision = classify_retry(err, attempts=2)
    assert decision.should_retry is True
    assert decision.delay_seconds > 0


def test_transient_retries_with_growing_delay() -> None:
    err = ProviderError(kind=ProviderErrorKind.TRANSIENT, message="5xx")
    d1 = classify_retry(err, attempts=0)
    d2 = classify_retry(err, attempts=3)
    assert d1.should_retry and d2.should_retry
    assert d2.delay_seconds > d1.delay_seconds


def test_transient_gives_up_at_cap_and_marks_degraded() -> None:
    err = ProviderError(kind=ProviderErrorKind.TRANSIENT, message="5xx")
    decision = classify_retry(err, attempts=MAX_TRANSIENT_RETRIES)
    assert decision.should_retry is False
    assert decision.final_status == "degraded"


def test_unknown_gives_up_quickly_and_marks_degraded() -> None:
    err = ProviderError(kind=ProviderErrorKind.UNKNOWN, message="huh")
    decision_early = classify_retry(err, attempts=0)
    decision_late = classify_retry(err, attempts=2)
    assert decision_early.should_retry is True
    assert decision_late.should_retry is False
    assert decision_late.final_status == "degraded"
