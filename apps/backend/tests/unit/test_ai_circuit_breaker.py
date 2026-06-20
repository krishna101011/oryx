"""AI circuit breaker — threshold, open window, half-open probe, isolation."""
from __future__ import annotations

import pytest

from oryx.core.ai_circuit_breaker import (
    FAILURE_THRESHOLD,
    OPEN_WINDOW_SECONDS,
    AICircuitBreaker,
    CircuitOpenError,
)
from oryx.services.intake.providers.errors import ProviderError, ProviderErrorKind


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _failing():
    async def fn():
        raise ProviderError(kind=ProviderErrorKind.TRANSIENT, message="boom")

    return fn


def _succeeding(calls: list[int]):
    async def fn():
        calls.append(1)
        return "ok"

    return fn


@pytest.mark.asyncio
async def test_circuit_opens_after_threshold_failures() -> None:
    clock = FakeClock()
    breaker = AICircuitBreaker(clock=clock)

    for _ in range(FAILURE_THRESHOLD):
        with pytest.raises(ProviderError):
            await breaker.call("extractor", _failing())

    assert breaker.is_open("extractor")
    # Open window: fail fast, provider never invoked.
    calls: list[int] = []
    with pytest.raises(CircuitOpenError):
        await breaker.call("extractor", _succeeding(calls))
    assert calls == []


@pytest.mark.asyncio
async def test_below_threshold_stays_closed() -> None:
    breaker = AICircuitBreaker(clock=FakeClock())
    for _ in range(FAILURE_THRESHOLD - 1):
        with pytest.raises(ProviderError):
            await breaker.call("extractor", _failing())
    assert not breaker.is_open("extractor")


@pytest.mark.asyncio
async def test_success_resets_failure_streak() -> None:
    breaker = AICircuitBreaker(clock=FakeClock())
    calls: list[int] = []
    for _ in range(FAILURE_THRESHOLD - 1):
        with pytest.raises(ProviderError):
            await breaker.call("extractor", _failing())
    await breaker.call("extractor", _succeeding(calls))
    # Streak reset: another THRESHOLD-1 failures must not open it.
    for _ in range(FAILURE_THRESHOLD - 1):
        with pytest.raises(ProviderError):
            await breaker.call("extractor", _failing())
    assert not breaker.is_open("extractor")


@pytest.mark.asyncio
async def test_probe_success_closes_circuit() -> None:
    clock = FakeClock()
    breaker = AICircuitBreaker(clock=clock)
    for _ in range(FAILURE_THRESHOLD):
        with pytest.raises(ProviderError):
            await breaker.call("extractor", _failing())
    assert breaker.is_open("extractor")

    clock.advance(OPEN_WINDOW_SECONDS + 1)
    calls: list[int] = []
    # Half-open: this call IS the probe, and it goes through.
    assert await breaker.call("extractor", _succeeding(calls)) == "ok"
    assert calls == [1]
    assert not breaker.is_open("extractor")


@pytest.mark.asyncio
async def test_probe_failure_extends_window() -> None:
    clock = FakeClock()
    breaker = AICircuitBreaker(clock=clock)
    for _ in range(FAILURE_THRESHOLD):
        with pytest.raises(ProviderError):
            await breaker.call("extractor", _failing())

    clock.advance(OPEN_WINDOW_SECONDS + 1)
    with pytest.raises(ProviderError):  # probe runs, fails
        await breaker.call("extractor", _failing())

    # Window extended: still open just before the next deadline...
    clock.advance(OPEN_WINDOW_SECONDS - 1)
    with pytest.raises(CircuitOpenError):
        await breaker.call("extractor", _failing())
    # ...and half-open again after it.
    clock.advance(2)
    calls: list[int] = []
    await breaker.call("extractor", _succeeding(calls))
    assert calls == [1]


@pytest.mark.asyncio
async def test_call_types_are_isolated() -> None:
    breaker = AICircuitBreaker(clock=FakeClock())
    for _ in range(FAILURE_THRESHOLD):
        with pytest.raises(ProviderError):
            await breaker.call("extractor", _failing())
    assert breaker.is_open("extractor")
    assert not breaker.is_open("classifier")
    calls: list[int] = []
    await breaker.call("classifier", _succeeding(calls))  # unaffected
    assert calls == [1]


def test_circuit_open_error_is_a_transient_provider_error() -> None:
    err = CircuitOpenError(
        kind=ProviderErrorKind.TRANSIENT, message="open", call_type="extractor"
    )
    assert isinstance(err, ProviderError)
    assert err.kind == ProviderErrorKind.TRANSIENT
    assert err.call_type == "extractor"
