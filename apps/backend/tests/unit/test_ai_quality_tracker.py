"""AIQualityTracker — parse-failure streak signal + breaker non-interference.

Closes the parse-failure-on-200 visibility gap (2026-07-22 ADR): a
reasoning-mode model returning HTTP 200 with empty content parse-fails on
every call while the circuit breaker counts every one of those calls as a
SUCCESS. The tracker surfaces "N consecutive parse failures per call_type"
as the structured `ai_quality.parse_failure_streak` signal — and must NEVER
open a circuit, trigger a retry, or touch breaker state (regression-tested
here, not just asserted by inspection).
"""
from __future__ import annotations

import logging

import pytest

from oryx.core.ai_circuit_breaker import (
    FAILURE_THRESHOLD,
    PARSE_FAILURE_STREAK_THRESHOLD,
    AICircuitBreaker,
    AIQualityTracker,
    ai_circuit_breaker,
    ai_quality_tracker,
)
from oryx.services.intake.providers.errors import ProviderError, ProviderErrorKind

STREAK_SIGNAL = "ai_quality.parse_failure_streak"
BREAKER_LOGGER = "oryx.core.ai_circuit_breaker"


def _signals(caplog) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.getMessage() == STREAK_SIGNAL]


@pytest.fixture
def clean_singletons():
    """The module singletons are shared process state — cold-start them for
    the tests that go through the real call path, and restore after (the same
    snapshot-and-restore discipline test_logging_redaction.py needed)."""
    ai_quality_tracker.reset()
    ai_circuit_breaker._states.clear()
    yield
    ai_quality_tracker.reset()
    ai_circuit_breaker._states.clear()


# ---------------------------------------------------------------------------
# Streak threshold semantics
# ---------------------------------------------------------------------------


def test_streak_signal_fires_at_exactly_the_threshold(caplog) -> None:
    tracker = AIQualityTracker()
    with caplog.at_level(logging.WARNING, logger=BREAKER_LOGGER):
        for i in range(1, PARSE_FAILURE_STREAK_THRESHOLD):
            tracker.record_parse_outcome("extractor", ok=False)
            assert _signals(caplog) == [], f"signal fired early at failure {i}"

        tracker.record_parse_outcome("extractor", ok=False)  # the 5th
        assert len(_signals(caplog)) == 1
        record = _signals(caplog)[0]
        assert record.call_type == "extractor"
        assert record.consecutive_failures == PARSE_FAILURE_STREAK_THRESHOLD

        # Failures 6 and 7: the streak continues but the signal does not
        # re-fire mid-streak (once per streak, by design).
        tracker.record_parse_outcome("extractor", ok=False)
        tracker.record_parse_outcome("extractor", ok=False)
        assert len(_signals(caplog)) == 1
        assert tracker.streak("extractor") == PARSE_FAILURE_STREAK_THRESHOLD + 2


def test_success_resets_the_streak(caplog) -> None:
    tracker = AIQualityTracker()
    with caplog.at_level(logging.WARNING, logger=BREAKER_LOGGER):
        for _ in range(PARSE_FAILURE_STREAK_THRESHOLD - 1):
            tracker.record_parse_outcome("classifier", ok=False)
        tracker.record_parse_outcome("classifier", ok=True)
        assert tracker.streak("classifier") == 0

        # A fresh streak needs the FULL threshold again.
        for _ in range(PARSE_FAILURE_STREAK_THRESHOLD - 1):
            tracker.record_parse_outcome("classifier", ok=False)
        assert _signals(caplog) == []
        tracker.record_parse_outcome("classifier", ok=False)
        assert len(_signals(caplog)) == 1


def test_streak_can_fire_again_after_a_success_starts_a_new_streak(caplog) -> None:
    tracker = AIQualityTracker()
    with caplog.at_level(logging.WARNING, logger=BREAKER_LOGGER):
        for _ in range(PARSE_FAILURE_STREAK_THRESHOLD):
            tracker.record_parse_outcome("evidence_linker", ok=False)
        tracker.record_parse_outcome("evidence_linker", ok=True)
        for _ in range(PARSE_FAILURE_STREAK_THRESHOLD):
            tracker.record_parse_outcome("evidence_linker", ok=False)
    assert len(_signals(caplog)) == 2


def test_call_types_are_isolated(caplog) -> None:
    tracker = AIQualityTracker()
    with caplog.at_level(logging.WARNING, logger=BREAKER_LOGGER):
        for _ in range(PARSE_FAILURE_STREAK_THRESHOLD - 1):
            tracker.record_parse_outcome("extractor", ok=False)
            tracker.record_parse_outcome("conflict_detector", ok=False)
        assert _signals(caplog) == []
        tracker.record_parse_outcome("conflict_detector", ok=False)
    signals = _signals(caplog)
    assert len(signals) == 1
    assert signals[0].call_type == "conflict_detector"
    assert tracker.streak("extractor") == PARSE_FAILURE_STREAK_THRESHOLD - 1


# ---------------------------------------------------------------------------
# Regression: quality outcomes and circuit state are fully independent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_failures_never_affect_circuit_state() -> None:
    """MANDATORY constraint: a mountain of parse failures must leave the
    breaker exactly as it was — closed, zero consecutive failures, calls
    passing straight through."""
    breaker = AICircuitBreaker()
    tracker = AIQualityTracker()

    for _ in range(PARSE_FAILURE_STREAK_THRESHOLD * 3):
        tracker.record_parse_outcome("extractor", ok=False)

    assert not breaker.is_open("extractor")
    assert breaker._states["extractor"].consecutive_failures == 0
    calls: list[int] = []

    async def succeeding():
        calls.append(1)
        return "ok"

    assert await breaker.call("extractor", succeeding) == "ok"
    assert calls == [1]  # never failed fast — the circuit truly stayed closed


@pytest.mark.asyncio
async def test_circuit_failures_never_affect_the_quality_streak() -> None:
    """Independence holds in the other direction too: real ProviderErrors
    open the circuit without touching the parse streak."""
    breaker = AICircuitBreaker()
    tracker = AIQualityTracker()
    tracker.record_parse_outcome("extractor", ok=False)  # streak = 1

    async def failing():
        raise ProviderError(kind=ProviderErrorKind.TRANSIENT, message="boom")

    for _ in range(FAILURE_THRESHOLD):
        with pytest.raises(ProviderError):
            await breaker.call("extractor", failing)

    assert breaker.is_open("extractor")
    assert tracker.streak("extractor") == 1  # untouched


# ---------------------------------------------------------------------------
# The real scenario: reasoning-mode trap through the real extractor call path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reasoning_mode_trap_fires_streak_at_five_with_circuit_closed(
    monkeypatch, caplog, clean_singletons
) -> None:
    """The diagnosed 2026-07-22 failure mode, end to end: the provider
    returns HTTP 200 with tokens billed and EMPTY content, so every extract()
    parse-fails while the breaker records every call as a success. The streak
    signal must fire at exactly the 5th consecutive failure — not the 4th,
    not again on the 6th — with the extractor circuit closed throughout."""
    from oryx.services.claims import extractor as extractor_module
    from oryx.services.claims.extractor import AIProviderResult, ClaimExtractorAI

    async def reasoning_mode_response(**kwargs):
        # Tokens billed, content empty — the exact Nemotron signature.
        return AIProviderResult(text="", input_tokens=0, output_tokens=900)

    monkeypatch.setattr(
        extractor_module, "call_ai_provider", reasoning_mode_response
    )
    extractor = ClaimExtractorAI()

    with caplog.at_level(logging.WARNING, logger=BREAKER_LOGGER):
        for i in range(1, PARSE_FAILURE_STREAK_THRESHOLD + 2):  # calls 1..6
            result = await extractor.extract("Apple reported record revenue.")
            assert result.parse_failed is True
            assert result.tokens_used == 900  # spend is real, per the incident

            fired = len(_signals(caplog))
            if i < PARSE_FAILURE_STREAK_THRESHOLD:
                assert fired == 0, f"signal fired early, at call {i}"
            else:
                assert fired == 1, f"expected exactly one signal by call {i}"

            # The circuit never budges: these are successful deliveries.
            assert not ai_circuit_breaker.is_open("extractor")
            assert (
                ai_circuit_breaker._states["extractor"].consecutive_failures == 0
            )

    signal = _signals(caplog)[0]
    assert signal.call_type == "extractor"
    assert signal.consecutive_failures == PARSE_FAILURE_STREAK_THRESHOLD
