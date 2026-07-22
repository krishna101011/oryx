"""OpenAICompatProvider + AI_PROVIDER Literal — provider-generalization wave.

No DB, no network: httpx.AsyncClient.post is patched (the same house pattern
as test_phase5_coverage.py) so the REAL provider code paths run against
controlled responses. Covers, in one place:

  - the new provider's full status→ProviderErrorKind mapping (the exact
    scheme AnthropicProvider uses — 401→AUTH, 429→RATE_LIMITED with the
    Retry-After hint, 5xx→TRANSIENT, other 4xx→PERMANENT, network→TRANSIENT),
  - the optional-bearer-auth and required-base-url/model pre-flight decisions,
  - the AIProviderName Literal rejecting an unknown AI_PROVIDER at startup,
  - factory-routing + error-mapping regression for AnthropicProvider and
    OllamaProvider. NOTE: before this wave NO test constructed
    AnthropicProvider directly, so the "regression" tests here are also the
    first direct coverage of its mapping — pinned now so future edits can't
    drift it silently.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from pydantic import ValidationError

from oryx.core.ai_provider import (
    NO_THINK_TOKEN,
    AnthropicProvider,
    OllamaProvider,
    OpenAICompatProvider,
    get_ai_provider,
)
from oryx.services.intake.providers.errors import ProviderError, ProviderErrorKind

BASE = "http://fake-vendor.local/v1"

OK_BODY = {
    "choices": [{"message": {"role": "assistant", "content": "hello from NIM"}}],
    "usage": {"prompt_tokens": 11, "completion_tokens": 7},
}


def _provider(**kw) -> OpenAICompatProvider:
    defaults = {"base_url": BASE, "model": "some/vendor-model", "api_key": "k"}
    defaults.update(kw)
    return OpenAICompatProvider(**defaults)


def _post_returning(status: int, *, json_body=None, headers=None, text: str = ""):
    async def fake_post(self, url, **kw):
        return httpx.Response(
            status,
            json=json_body,
            headers=headers,
            text=text if json_body is None else None,
            request=httpx.Request("POST", url),
        )

    return fake_post


async def _complete(provider: OpenAICompatProvider):
    return await provider.complete(
        system="sys", user="usr", max_tokens=64, temperature=0.0
    )


# --------------------------------------------------------------------------- #
# Success path
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_openai_compat_success_parses_text_and_token_total() -> None:
    with patch("httpx.AsyncClient.post", _post_returning(200, json_body=OK_BODY)):
        text, total = await _complete(_provider())
    assert text == "hello from NIM"
    assert total == 18  # prompt_tokens 11 + completion_tokens 7


@pytest.mark.asyncio
async def test_openai_compat_bearer_header_only_when_key_configured() -> None:
    seen: list[dict] = []

    async def capture_post(self, url, **kw):
        seen.append(kw.get("headers") or {})
        return httpx.Response(200, json=OK_BODY, request=httpx.Request("POST", url))

    with patch("httpx.AsyncClient.post", capture_post):
        await _complete(_provider(api_key="nvapi-secret"))
        await _complete(_provider(api_key=None))
    assert seen[0].get("authorization") == "Bearer nvapi-secret"
    assert "authorization" not in seen[1]  # local vLLM/LM Studio: no auth sent


# --------------------------------------------------------------------------- #
# disable_reasoning — the /no_think prepend happens on the wire only
# (reasoning-mode models return 200 with EMPTY content inside the pipeline's
# token budgets; diagnosed live against Nemotron 2026-07-22)
# --------------------------------------------------------------------------- #
def _capture_post(seen: list[dict]):
    async def capture(self, url, **kw):
        seen.append(kw.get("json") or {})
        return httpx.Response(200, json=OK_BODY, request=httpx.Request("POST", url))

    return capture


@pytest.mark.asyncio
async def test_openai_compat_disable_reasoning_prepends_no_think_on_wire_only() -> None:
    seen: list[dict] = []
    with patch("httpx.AsyncClient.post", _capture_post(seen)):
        await _complete(_provider(disable_reasoning=True))
        await _complete(_provider())  # default off
    on_system = seen[0]["messages"][0]["content"]
    assert on_system.startswith(f"{NO_THINK_TOKEN}\n\n")
    assert on_system.endswith("sys")  # caller's system string intact after the token
    assert seen[0]["messages"][1]["content"] == "usr"  # user message untouched
    # Flag off (the default): system goes out byte-identical, no token anywhere.
    assert seen[1]["messages"][0]["content"] == "sys"
    assert NO_THINK_TOKEN not in str(seen[1])


@pytest.mark.asyncio
async def test_factory_wires_disable_reasoning_from_settings() -> None:
    seen: list[dict] = []
    s = SimpleNamespace(
        ai_provider="openai_compatible",
        openai_compat_base_url=BASE,
        openai_compat_model="m",
        openai_compat_api_key="k",
        openai_compat_disable_reasoning=True,
    )
    with patch("httpx.AsyncClient.post", _capture_post(seen)):
        await _complete(get_ai_provider(s))
        del s.openai_compat_disable_reasoning  # attribute absent → False
        await _complete(get_ai_provider(s))
    assert seen[0]["messages"][0]["content"].startswith(NO_THINK_TOKEN)
    assert seen[1]["messages"][0]["content"] == "sys"


@pytest.mark.asyncio
async def test_disable_reasoning_is_noop_for_anthropic_and_ollama() -> None:
    seen: list[dict] = []
    s = SimpleNamespace(
        ai_provider="anthropic",
        anthropic_api_key="k",
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen2.5:7b-instruct",
        openai_compat_disable_reasoning=True,  # set, but must not leak
    )
    with patch("httpx.AsyncClient.post", _capture_post(seen)):
        await get_ai_provider(s, model="claude-x").complete(
            system="sys", user="usr", max_tokens=8, temperature=0.0
        )
        s.ai_provider = "ollama"
        await get_ai_provider(s).complete(
            system="sys", user="usr", max_tokens=8, temperature=0.0
        )
    assert seen[0]["system"] == "sys"  # Anthropic wire payload unchanged
    assert seen[1]["system"] == "sys"  # Ollama wire payload unchanged
    assert NO_THINK_TOKEN not in str(seen[0]) and NO_THINK_TOKEN not in str(seen[1])


# --------------------------------------------------------------------------- #
# Error mapping — the exact AnthropicProvider scheme, no new taxonomy
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_openai_compat_401_maps_to_auth() -> None:
    with patch("httpx.AsyncClient.post", _post_returning(401)):
        with pytest.raises(ProviderError) as exc:
            await _complete(_provider())
    assert exc.value.kind is ProviderErrorKind.AUTH


@pytest.mark.asyncio
async def test_openai_compat_429_maps_to_rate_limited_with_retry_after_hint() -> None:
    with patch(
        "httpx.AsyncClient.post",
        _post_returning(429, headers={"retry-after": "42"}),
    ):
        with pytest.raises(ProviderError) as exc:
            await _complete(_provider())
    assert exc.value.kind is ProviderErrorKind.RATE_LIMITED
    assert exc.value.retry_after_seconds == 42


@pytest.mark.asyncio
async def test_openai_compat_429_without_retry_after_leaves_hint_none() -> None:
    with patch("httpx.AsyncClient.post", _post_returning(429)):
        with pytest.raises(ProviderError) as exc:
            await _complete(_provider())
    assert exc.value.kind is ProviderErrorKind.RATE_LIMITED
    assert exc.value.retry_after_seconds is None


@pytest.mark.asyncio
async def test_openai_compat_5xx_maps_to_transient() -> None:
    with patch("httpx.AsyncClient.post", _post_returning(503)):
        with pytest.raises(ProviderError) as exc:
            await _complete(_provider())
    assert exc.value.kind is ProviderErrorKind.TRANSIENT


@pytest.mark.asyncio
async def test_openai_compat_other_4xx_maps_to_permanent() -> None:
    with patch(
        "httpx.AsyncClient.post", _post_returning(404, text="model not found")
    ):
        with pytest.raises(ProviderError) as exc:
            await _complete(_provider())
    assert exc.value.kind is ProviderErrorKind.PERMANENT
    assert "404" in exc.value.message


@pytest.mark.asyncio
async def test_openai_compat_network_error_maps_to_transient() -> None:
    async def boom(self, url, **kw):
        raise httpx.ConnectError("down")

    with patch("httpx.AsyncClient.post", boom):
        with pytest.raises(ProviderError) as exc:
            await _complete(_provider())
    assert exc.value.kind is ProviderErrorKind.TRANSIENT


@pytest.mark.asyncio
async def test_openai_compat_missing_base_url_or_model_is_permanent_preflight_no_http() -> None:
    async def must_not_be_called(self, url, **kw):  # pragma: no cover - guard
        raise AssertionError("pre-flight config error must not reach HTTP")

    with patch("httpx.AsyncClient.post", must_not_be_called):
        with pytest.raises(ProviderError) as exc1:
            await _complete(_provider(base_url=None))
        with pytest.raises(ProviderError) as exc2:
            await _complete(_provider(model=None))
    assert exc1.value.kind is ProviderErrorKind.PERMANENT
    assert "OPENAI_COMPAT_BASE_URL" in exc1.value.message
    assert exc2.value.kind is ProviderErrorKind.PERMANENT
    assert "OPENAI_COMPAT_MODEL" in exc2.value.message


# --------------------------------------------------------------------------- #
# AI_PROVIDER Literal — unknown values fail at startup, not silently
# --------------------------------------------------------------------------- #
def test_ai_provider_literal_rejects_unknown_value_at_startup() -> None:
    from oryx.config import Settings

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None, ai_provider="grok9000")
    assert "ai_provider" in str(exc.value)

    for valid in ("anthropic", "ollama", "openai_compatible"):
        assert Settings(_env_file=None, ai_provider=valid).ai_provider == valid


# --------------------------------------------------------------------------- #
# Factory routing + Anthropic/Ollama regression (behavior unchanged)
# --------------------------------------------------------------------------- #
def test_factory_routes_every_provider_name_and_default_is_unchanged() -> None:
    s = SimpleNamespace(
        ai_provider="anthropic",
        anthropic_api_key="k",
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen2.5:7b-instruct",
        openai_compat_base_url=BASE,
        openai_compat_model="m",
        openai_compat_api_key="k2",
    )
    assert isinstance(get_ai_provider(s, model="claude-x"), AnthropicProvider)
    s.ai_provider = "ollama"
    assert isinstance(get_ai_provider(s), OllamaProvider)
    s.ai_provider = "openai_compatible"
    assert isinstance(get_ai_provider(s), OpenAICompatProvider)
    # Settings object without the attribute at all → Anthropic (the factory's
    # getattr fallback, unchanged by this wave).
    assert isinstance(get_ai_provider(SimpleNamespace()), AnthropicProvider)


@pytest.mark.asyncio
async def test_anthropic_error_mapping_regression_401_and_429() -> None:
    provider = AnthropicProvider(model="claude-haiku-4-5-20251001", api_key="bad")

    with patch("httpx.AsyncClient.post", _post_returning(401)):
        with pytest.raises(ProviderError) as exc:
            await provider.complete(system="s", user="u", max_tokens=8, temperature=0.0)
    assert exc.value.kind is ProviderErrorKind.AUTH
    assert exc.value.message == "Anthropic API key rejected"

    with patch(
        "httpx.AsyncClient.post",
        _post_returning(429, headers={"retry-after": "42"}),
    ):
        with pytest.raises(ProviderError) as exc:
            await provider.complete(system="s", user="u", max_tokens=8, temperature=0.0)
    assert exc.value.kind is ProviderErrorKind.RATE_LIMITED
    assert exc.value.retry_after_seconds == 42


@pytest.mark.asyncio
async def test_ollama_regression_all_errors_transient() -> None:
    provider = OllamaProvider(base_url="http://localhost:11434", model="qwen2.5:7b-instruct")

    with patch("httpx.AsyncClient.post", _post_returning(500, text="boom")):
        with pytest.raises(ProviderError) as exc:
            await provider.complete(system="s", user="u", max_tokens=8, temperature=0.0)
    assert exc.value.kind is ProviderErrorKind.TRANSIENT

    async def down(self, url, **kw):
        raise httpx.ConnectError("down")

    with patch("httpx.AsyncClient.post", down):
        with pytest.raises(ProviderError) as exc:
            await provider.complete(system="s", user="u", max_tokens=8, temperature=0.0)
    assert exc.value.kind is ProviderErrorKind.TRANSIENT
