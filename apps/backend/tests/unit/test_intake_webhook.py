"""Webhook provider tests — HMAC, replay window, idempotency, mapper.

Covers Phase 3 §6 + CR-4. Router endpoint is exercised by integration
tests (requires_db); these unit tests pin the pure-function contracts.
"""
from __future__ import annotations

import time
import uuid

import pytest

from oryx.services.intake.providers.base import (
    IntakeSourceKind,
    ValidationStatus,
)
from oryx.services.intake.providers.errors import (
    ProviderError,
    ProviderErrorKind,
)
from oryx.services.intake.providers.webhook.config_schema import (
    REPLAY_WINDOW_SECONDS,
    WebhookFieldMapping,
)
from oryx.services.intake.providers.webhook.mapper import (
    json_to_raw_item,
    lookup_path,
)
from oryx.services.intake.providers.webhook.provider import WebhookProvider
from oryx.services.intake.providers.webhook.secrets import (
    generate_secret,
    hash_secret_for_audit,
    sign_request,
    verify_request,
)

# ----------------------------- secrets -----------------------------

def test_generate_secret_has_high_entropy() -> None:
    samples = {generate_secret() for _ in range(50)}
    assert len(samples) == 50


def test_hash_secret_is_deterministic_and_long() -> None:
    s = generate_secret()
    h = hash_secret_for_audit(s)
    assert h == hash_secret_for_audit(s)
    assert len(h) == 64


# ----------------------------- HMAC -----------------------------

def test_sign_and_verify_round_trips() -> None:
    secret = generate_secret()
    ts = int(time.time())
    body = b'{"id":"x"}'
    sig = sign_request(secret=secret, timestamp=ts, body=body)
    result = verify_request(
        secrets=[secret],
        signature_header=sig,
        timestamp_header=str(ts),
        body=body,
    )
    assert result.timestamp == ts


def test_verify_accepts_bare_hex_or_prefixed_form() -> None:
    secret = generate_secret()
    ts = int(time.time())
    body = b"x"
    sig_prefixed = sign_request(secret=secret, timestamp=ts, body=body)
    sig_bare = sig_prefixed.split("=", 1)[1]
    # Both must verify successfully
    verify_request(
        secrets=[secret],
        signature_header=sig_prefixed,
        timestamp_header=str(ts),
        body=body,
    )
    verify_request(
        secrets=[secret],
        signature_header=sig_bare,
        timestamp_header=str(ts),
        body=body,
    )


def test_verify_rejects_wrong_secret() -> None:
    sig = sign_request(secret="a", timestamp=int(time.time()), body=b"x")
    with pytest.raises(ProviderError) as exc:
        verify_request(
            secrets=["b"],
            signature_header=sig,
            timestamp_header=str(int(time.time())),
            body=b"x",
        )
    assert exc.value.kind == ProviderErrorKind.PERMANENT


def test_verify_rejects_tampered_body() -> None:
    secret = generate_secret()
    ts = int(time.time())
    sig = sign_request(secret=secret, timestamp=ts, body=b"original")
    with pytest.raises(ProviderError):
        verify_request(
            secrets=[secret],
            signature_header=sig,
            timestamp_header=str(ts),
            body=b"tampered",
        )


def test_verify_rejects_missing_headers() -> None:
    with pytest.raises(ProviderError) as exc:
        verify_request(
            secrets=["x"],
            signature_header=None,
            timestamp_header="123",
            body=b"",
        )
    assert "header" in exc.value.message.lower()


def test_verify_rejects_non_integer_timestamp() -> None:
    with pytest.raises(ProviderError):
        verify_request(
            secrets=["x"],
            signature_header="hmac-sha256=ff",
            timestamp_header="not-a-number",
            body=b"",
        )


# ----------------------------- replay window -----------------------------

def test_verify_accepts_timestamp_inside_replay_window() -> None:
    secret = generate_secret()
    now = 1_700_000_000
    drift = REPLAY_WINDOW_SECONDS - 1
    ts = now - drift
    sig = sign_request(secret=secret, timestamp=ts, body=b"")
    verify_request(
        secrets=[secret],
        signature_header=sig,
        timestamp_header=str(ts),
        body=b"",
        now=now,
    )


def test_verify_rejects_timestamp_outside_replay_window() -> None:
    secret = generate_secret()
    now = 1_700_000_000
    ts = now - (REPLAY_WINDOW_SECONDS + 1)
    sig = sign_request(secret=secret, timestamp=ts, body=b"")
    with pytest.raises(ProviderError) as exc:
        verify_request(
            secrets=[secret],
            signature_header=sig,
            timestamp_header=str(ts),
            body=b"",
            now=now,
        )
    assert "replay" in exc.value.message.lower() or "window" in exc.value.message.lower()


# ----------------------------- rotation grace -----------------------------

def test_verify_succeeds_when_signed_by_previous_secret_in_grace_window() -> None:
    """Rotation grace: the verifier accepts a list of secrets; if either
    matches we accept. The router passes [current, previous]."""
    old = generate_secret()
    new = generate_secret()
    ts = int(time.time())
    body = b"x"
    sig = sign_request(secret=old, timestamp=ts, body=body)
    # Sender still uses the old secret; verifier holds both.
    verify_request(
        secrets=[new, old],
        signature_header=sig,
        timestamp_header=str(ts),
        body=body,
    )


# ----------------------------- mapper -----------------------------

def test_lookup_path_dotted_access() -> None:
    payload = {"a": {"b": {"c": 42}}}
    assert lookup_path(payload, "a.b.c") == 42


def test_lookup_path_array_indexing() -> None:
    payload = {"items": [{"id": "first"}, {"id": "second"}]}
    assert lookup_path(payload, "items[0].id") == "first"
    assert lookup_path(payload, "items[1].id") == "second"


def test_lookup_path_returns_none_on_missing() -> None:
    assert lookup_path({}, "a.b") is None
    assert lookup_path({"a": []}, "a[0].b") is None


def test_mapper_extracts_default_fields() -> None:
    mapping = WebhookFieldMapping()
    payload = {
        "id": "evt-1",
        "created_at": "2026-06-07T09:00:00Z",
        "from": "alerts@vendor.test",
        "subject": "Alert",
        "body": "Something happened",
        "url": "https://vendor.test/event/1",
    }
    raw = json_to_raw_item(payload, mapping=mapping)
    assert raw.external_id == "evt-1"
    assert raw.sender == "alerts@vendor.test"
    assert raw.subject == "Alert"
    assert raw.body_text == "Something happened"
    assert raw.received_at.year == 2026


def test_mapper_falls_back_to_body_hash_when_external_id_missing() -> None:
    raw = json_to_raw_item(
        {"foo": "bar"}, mapping=WebhookFieldMapping(external_id="nonexistent")
    )
    assert raw.external_id.startswith("sha256:")


def test_mapper_handles_epoch_seconds_and_ms() -> None:
    mapping = WebhookFieldMapping(external_id="id", received_at="ts")
    raw_s = json_to_raw_item({"id": "x", "ts": 1700000000}, mapping=mapping)
    raw_ms = json_to_raw_item({"id": "x", "ts": 1700000000000}, mapping=mapping)
    assert raw_s.received_at == raw_ms.received_at


def test_mapper_custom_paths() -> None:
    mapping = WebhookFieldMapping(
        external_id="event.id",
        sender="event.actor.email",
        subject="event.title",
    )
    raw = json_to_raw_item(
        {"event": {"id": "e-1", "actor": {"email": "u@x"}, "title": "T"}},
        mapping=mapping,
    )
    assert raw.external_id == "e-1"
    assert raw.sender == "u@x"
    assert raw.subject == "T"


# ----------------------------- provider -----------------------------

def test_provider_metadata_locked() -> None:
    p = WebhookProvider()
    assert p.name == "webhook"
    assert p.kind == IntakeSourceKind.WEBHOOK


def test_provider_declares_handle_webhook() -> None:
    """The router uses hasattr(provider, 'handle_webhook') to route — verify."""
    assert hasattr(WebhookProvider(), "handle_webhook")


@pytest.mark.asyncio
async def test_provider_validate_config_accepts_defaults() -> None:
    p = WebhookProvider()
    result = await p.validate_config({})
    assert result.status == ValidationStatus.OK


@pytest.mark.asyncio
async def test_provider_handle_webhook_yields_raw_item_from_default_mapping() -> None:
    import json as _json
    p = WebhookProvider()
    body = _json.dumps({
        "id": "evt-7",
        "created_at": "2026-06-07T10:00:00Z",
        "from": "feed@vendor.test",
        "subject": "Title",
        "body": "Body text",
        "url": "https://vendor.test/7",
    }).encode("utf-8")
    items = []
    async for raw in p.handle_webhook(
        workspace_id=uuid.uuid4(),
        intake_source_id=uuid.uuid4(),
        headers={},
        body=body,
        config={},
    ):
        items.append(raw)
    assert len(items) == 1
    assert items[0].external_id == "evt-7"
    assert items[0].subject == "Title"
