"""Shared AI circuit breaker (Phase 4 Rev 2 §21.2).

Tracks consecutive AI provider failures per `call_type` ("extractor",
"classifier", "evidence_linker", ...). After FAILURE_THRESHOLD consecutive
failures the circuit opens for OPEN_WINDOW_SECONDS: every call during the
window fails fast with CircuitOpenError, sparing both latency and budget.

Probe semantics: once the window expires the circuit is half-open — the
NEXT real call through the breaker serves as the probe. Success closes
the circuit and resets the counter; failure re-opens it for another
window. (A synthetic canary call would spend unbudgeted tokens for no
information a real call doesn't provide.)

State is in-process only, by design: a restart cold-starts every circuit
closed, which is the correct optimistic default.
"""
from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from anant.core.logging import get_logger
from anant.services.intake.providers.errors import ProviderError, ProviderErrorKind

logger = get_logger(__name__)

T = TypeVar("T")

FAILURE_THRESHOLD = 5
OPEN_WINDOW_SECONDS = 60.0


@dataclass(frozen=True)
class CircuitOpenError(ProviderError):
    """Raised instead of calling the provider while the circuit is open.

    A ProviderError subclass so existing taxonomy-based handling applies;
    TRANSIENT because the condition heals itself when the window expires.
    """

    call_type: str = ""


@dataclass
class _CircuitState:
    consecutive_failures: int = 0
    open_until: float | None = None  # monotonic-clock deadline


class AICircuitBreaker:
    """One instance per process (see module-level singleton below).

    The clock is injectable for tests; production uses time.monotonic so
    wall-clock jumps can't wedge a circuit open.
    """

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._states: dict[str, _CircuitState] = defaultdict(_CircuitState)

    def is_open(self, call_type: str) -> bool:
        state = self._states[call_type]
        return state.open_until is not None and self._clock() < state.open_until

    async def call(
        self, call_type: str, fn: Callable[[], Awaitable[T]]
    ) -> T:
        """Run `fn` under the breaker for `call_type`."""
        state = self._states[call_type]
        now = self._clock()

        was_open = state.open_until is not None
        if was_open and state.open_until is not None and now < state.open_until:
            raise CircuitOpenError(
                kind=ProviderErrorKind.TRANSIENT,
                message=f"AI circuit open for '{call_type}'",
                call_type=call_type,
            )
        # Window expired (half-open): this call is the probe.

        try:
            result = await fn()
        except ProviderError:
            state.consecutive_failures += 1
            if was_open or state.consecutive_failures >= FAILURE_THRESHOLD:
                # Failed probe extends the window; threshold breach opens it.
                state.open_until = self._clock() + OPEN_WINDOW_SECONDS
                logger.info(
                    "ai_circuit_breaker.opened",
                    extra={
                        "call_type": call_type,
                        "failure_count": state.consecutive_failures,
                    },
                )
            raise

        if was_open:
            logger.info(
                "ai_circuit_breaker.closed",
                extra={
                    "call_type": call_type,
                    "failure_count": state.consecutive_failures,
                },
            )
        state.consecutive_failures = 0
        state.open_until = None
        return result


# Module-level singleton — one breaker per process.
ai_circuit_breaker = AICircuitBreaker()
