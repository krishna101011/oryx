"""Pluggable AI provider abstraction.

Swap AI backends by setting AI_PROVIDER=anthropic (default), AI_PROVIDER=ollama,
or AI_PROVIDER=openai_compatible (any /chat/completions vendor — NVIDIA NIM,
vLLM, LM Studio, ...). No prompt content, temperature, or max_tokens values
change between providers.

QUALITY NOTE: Local models (Ollama) are materially lower quality than
claude-haiku-4-5-20251001 for epistemic classification accuracy. Claims that a
Haiku run would correctly label "fact" or "rumor" may be misclassified by
qwen2.5:7b-instruct or equivalent small models. Treat Ollama mode as a dev
smoke-test path only — never as a production substitute for Anthropic.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import httpx

from oryx.services.intake.providers.errors import ProviderError, ProviderErrorKind

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_API_VERSION = "2023-06-01"

# Control token understood by reasoning-capable open models (NVIDIA Nemotron
# v1.5, Qwen3, ...): placed in the system message it disables the "thinking"
# phase, so content starts at output token 0 instead of after ~1000 reasoning
# tokens. Sent on the wire only when openai_compat_disable_reasoning is set —
# caller prompt constants never contain it.
NO_THINK_TOKEN = "/no_think"


@runtime_checkable
class AIProvider(Protocol):
    async def complete(
        self,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int]:
        """Returns (response_text, total_tokens_used)."""
        ...


class AnthropicProvider:
    """Direct Anthropic Messages API. Vendor errors map onto ProviderError so
    the circuit breaker / drainer retry policy applies unchanged."""

    def __init__(self, model: str, api_key: str, timeout: float = 60.0) -> None:
        self._model = model
        self._api_key = api_key
        self._timeout = timeout

    async def complete(
        self,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int]:
        if not self._api_key:
            raise ProviderError(
                kind=ProviderErrorKind.AUTH,
                message="ANTHROPIC_API_KEY is not configured",
            )
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    _ANTHROPIC_API_URL,
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": _ANTHROPIC_API_VERSION,
                        "content-type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "system": system,
                        "messages": [{"role": "user", "content": user}],
                    },
                )
        except httpx.HTTPError as exc:
            raise ProviderError(
                kind=ProviderErrorKind.TRANSIENT,
                message=f"Anthropic API unreachable: {exc}",
            ) from exc

        if resp.status_code == 401:
            raise ProviderError(
                kind=ProviderErrorKind.AUTH, message="Anthropic API key rejected"
            )
        if resp.status_code == 429:
            retry_after = resp.headers.get("retry-after")
            raise ProviderError(
                kind=ProviderErrorKind.RATE_LIMITED,
                message="Anthropic rate limit",
                retry_after_seconds=int(retry_after) if retry_after else None,
            )
        if resp.status_code >= 500:
            raise ProviderError(
                kind=ProviderErrorKind.TRANSIENT,
                message=f"Anthropic API {resp.status_code}",
            )
        if resp.status_code >= 400:
            raise ProviderError(
                kind=ProviderErrorKind.PERMANENT,
                message=f"Anthropic API {resp.status_code}: {resp.text[:200]}",
            )

        data: dict[str, Any] = resp.json()
        blocks = data.get("content") or []
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        usage = data.get("usage") or {}
        total = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
        return text, total


class OllamaProvider:
    """Local Ollama REST provider (http://localhost:11434 by default).

    Maps the same (system, user, max_tokens, temperature) interface onto
    Ollama's /api/generate endpoint. Token count uses eval_count +
    prompt_eval_count from the response.

    Model quality is materially lower than Anthropic for financial-intelligence
    epistemic classification — see module docstring.
    """

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def complete(
        self,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int]:
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self._base_url}/api/generate",
                    json={
                        "model": self._model,
                        "prompt": user,
                        "system": system,
                        "stream": False,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": temperature,
                        },
                    },
                )
        except httpx.HTTPError as exc:
            raise ProviderError(
                kind=ProviderErrorKind.TRANSIENT,
                message=f"Ollama unreachable at {self._base_url}: {exc}",
            ) from exc

        if resp.status_code >= 400:
            raise ProviderError(
                kind=ProviderErrorKind.TRANSIENT,
                message=f"Ollama {resp.status_code}: {resp.text[:200]}",
            )

        data: dict[str, Any] = resp.json()
        text = data.get("response", "")
        total = int(data.get("eval_count", 0)) + int(data.get("prompt_eval_count", 0))
        return text, total


class OpenAICompatProvider:
    """Generic OpenAI-compatible /chat/completions provider — NVIDIA NIM,
    vLLM, LM Studio, or any other vendor speaking the OpenAI wire shape.

    Vendor errors map onto ProviderError with the exact same status→kind
    scheme as AnthropicProvider (401→AUTH, 429→RATE_LIMITED with the
    Retry-After hint, 5xx→TRANSIENT, other 4xx→PERMANENT) so the circuit
    breaker / drainer retry policy applies unchanged.

    api_key is deliberately optional at runtime (unlike AnthropicProvider's
    pre-flight): local servers such as vLLM and LM Studio accept
    unauthenticated requests, and an auth-requiring vendor answers a missing
    or bad key with a 401 that maps to AUTH like any rejected credential.
    base_url and model have no universal default across vendors, so a
    missing one is a pre-flight ProviderError(PERMANENT) — "invalid by
    configuration", never a silent guess.
    """

    def __init__(
        self,
        base_url: str | None,
        model: str | None,
        api_key: str | None,
        timeout: float = 60.0,
        disable_reasoning: bool = False,
    ) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._model = model
        self._api_key = api_key
        self._timeout = timeout
        self._disable_reasoning = disable_reasoning

    async def complete(
        self,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, int]:
        if not self._base_url:
            raise ProviderError(
                kind=ProviderErrorKind.PERMANENT,
                message="OPENAI_COMPAT_BASE_URL is not configured",
            )
        if not self._model:
            raise ProviderError(
                kind=ProviderErrorKind.PERMANENT,
                message="OPENAI_COMPAT_MODEL is not configured",
            )
        headers = {"content-type": "application/json"}
        if self._api_key:
            headers["authorization"] = f"Bearer {self._api_key}"
        if self._disable_reasoning:
            system = f"{NO_THINK_TOKEN}\n\n{system}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": self._model,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                    },
                )
        except httpx.HTTPError as exc:
            raise ProviderError(
                kind=ProviderErrorKind.TRANSIENT,
                message=f"OpenAI-compatible API unreachable: {exc}",
            ) from exc

        if resp.status_code == 401:
            raise ProviderError(
                kind=ProviderErrorKind.AUTH,
                message="OpenAI-compatible API key rejected",
            )
        if resp.status_code == 429:
            retry_after = resp.headers.get("retry-after")
            raise ProviderError(
                kind=ProviderErrorKind.RATE_LIMITED,
                message="OpenAI-compatible API rate limit",
                retry_after_seconds=int(retry_after) if retry_after else None,
            )
        if resp.status_code >= 500:
            raise ProviderError(
                kind=ProviderErrorKind.TRANSIENT,
                message=f"OpenAI-compatible API {resp.status_code}",
            )
        if resp.status_code >= 400:
            raise ProviderError(
                kind=ProviderErrorKind.PERMANENT,
                message=f"OpenAI-compatible API {resp.status_code}: {resp.text[:200]}",
            )

        data: dict[str, Any] = resp.json()
        choices = data.get("choices") or []
        message = (choices[0].get("message") or {}) if choices else {}
        text = message.get("content") or ""
        usage = data.get("usage") or {}
        total = int(usage.get("prompt_tokens", 0)) + int(usage.get("completion_tokens", 0))
        return text, total


def get_ai_provider(
    settings,
    *,
    model: str = "claude-haiku-4-5-20251001",
    timeout: float = 60.0,
) -> AIProvider:
    """Factory. AI_PROVIDER=ollama → OllamaProvider; AI_PROVIDER=
    openai_compatible → OpenAICompatProvider; anything else → AnthropicProvider.

    Callers supply the model string they need (Haiku for pipeline calls,
    Sonnet for draft generation). OllamaProvider and OpenAICompatProvider
    ignore it and use their configured model for everything.
    """
    if getattr(settings, "ai_provider", "anthropic") == "ollama":
        return OllamaProvider(
            base_url=getattr(settings, "ollama_base_url", "http://localhost:11434"),
            model=getattr(settings, "ollama_model", "qwen2.5:7b-instruct"),
        )
    if getattr(settings, "ai_provider", "anthropic") == "openai_compatible":
        return OpenAICompatProvider(
            base_url=getattr(settings, "openai_compat_base_url", None),
            model=getattr(settings, "openai_compat_model", None),
            api_key=getattr(settings, "openai_compat_api_key", None),
            timeout=timeout,
            disable_reasoning=getattr(
                settings, "openai_compat_disable_reasoning", False
            ),
        )
    return AnthropicProvider(
        model=model,
        api_key=getattr(settings, "anthropic_api_key", None) or "",
        timeout=timeout,
    )
