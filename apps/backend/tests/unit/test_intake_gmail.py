"""Gmail provider tests — config, scope, mapper, sync + CR-5 expiry recovery.

The transport is mocked at the gmail_client module surface. The mapper is
pure and tested against a fixture. The CR-5 path is explicitly asserted:
on a 404 from history.list, the provider falls back to messages.list and
the `fallback_recovered` flag flips.
"""
from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from unittest.mock import patch

import pytest

from anant.services.intake.providers.base import (
    IntakeSourceKind,
    ValidationStatus,
)
from anant.services.intake.providers.gmail import auth as gmail_auth
from anant.services.intake.providers.gmail import client as gmail_client
from anant.services.intake.providers.gmail.config_schema import (
    GMAIL_READONLY_SCOPE,
    REQUESTED_SCOPES,
)
from anant.services.intake.providers.gmail.mapper import gmail_message_to_raw
from anant.services.intake.providers.gmail.sync import (
    GmailProvider,
    cursor_from_report,
)

# ---------------------------- fixtures ----------------------------

def _b64url(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def _fixture_message(mid: str = "m-1") -> dict[str, Any]:
    return {
        "id": mid,
        "threadId": f"t-{mid}",
        "labelIds": ["INBOX", "Label_42"],
        "internalDate": "1717678800000",  # 2024-06-06 13:00:00 UTC
        "historyId": "1234",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": "Newsletter <hi@ft.com>"},
                {"name": "To", "value": "user@anant.test"},
                {"name": "Subject", "value": "Daily Macro Brief"},
                {"name": "Received", "value": "from junk; should not hash"},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": _b64url("Hello plain world")},
                },
                {
                    "mimeType": "text/html",
                    "body": {"data": _b64url("<p>Hello <b>HTML</b> world</p>")},
                },
            ],
        },
    }


@dataclass
class _FakeToken:
    access_token: str = "test-access-token"


async def _fake_token_provider() -> _FakeToken:
    return _FakeToken()


# ------------------------- scope / config ------------------------

def test_only_readonly_scope_is_requested() -> None:
    """ADR-023: this provider must request exactly one scope, readonly."""
    assert REQUESTED_SCOPES == (GMAIL_READONLY_SCOPE,)
    assert GMAIL_READONLY_SCOPE == "https://www.googleapis.com/auth/gmail.readonly"


def test_build_auth_url_includes_readonly_scope_and_state() -> None:
    url = gmail_auth.build_auth_url(
        client_id="cid", redirect_uri="https://anant.test/cb", state="STATE"
    )
    assert "gmail.readonly" in url
    assert "state=STATE" in url
    assert "access_type=offline" in url
    assert "prompt=consent" in url


@pytest.mark.asyncio
async def test_validate_config_defaults_accept_empty_input() -> None:
    p = GmailProvider(token_provider=_fake_token_provider)
    result = await p.validate_config({})
    assert result.status == ValidationStatus.OK


@pytest.mark.asyncio
async def test_validate_config_rejects_out_of_range_lookback() -> None:
    p = GmailProvider(token_provider=_fake_token_provider)
    result = await p.validate_config({"max_lookback_days_initial": 365})
    assert result.status == ValidationStatus.INVALID


# ------------------------- mapper ------------------------

def test_mapper_extracts_sender_subject_and_received_at() -> None:
    raw = gmail_message_to_raw(_fixture_message())
    assert raw.external_id == "m-1"
    assert raw.sender == "Newsletter <hi@ft.com>"
    assert raw.subject == "Daily Macro Brief"
    assert isinstance(raw.received_at, datetime)
    assert raw.received_at.tzinfo is not None


def test_mapper_extracts_both_plain_and_html_bodies() -> None:
    raw = gmail_message_to_raw(_fixture_message())
    assert "plain world" in (raw.body_text or "")
    assert "HTML" in (raw.body_html or "")


def test_mapper_preserves_label_ids_and_thread_id() -> None:
    raw = gmail_message_to_raw(_fixture_message())
    assert raw.payload["label_ids"] == ["INBOX", "Label_42"]
    assert raw.payload["thread_id"] == "t-m-1"


def test_mapper_skips_server_added_headers_in_hash() -> None:
    raw_a = gmail_message_to_raw(_fixture_message())
    # Same message fetched again — Received header is different but hash should be stable.
    m_b = _fixture_message()
    m_b["payload"]["headers"][-1]["value"] = "different-server-trace"
    raw_b = gmail_message_to_raw(m_b)
    assert raw_a.payload["raw_headers_hash"] == raw_b.payload["raw_headers_hash"]


# ------------------------- sync paths ------------------------

@pytest.mark.asyncio
async def test_bootstrap_pulls_messages_when_no_cursor() -> None:
    """First sync with no cursor → list_messages bounded by lookback."""

    async def fake_list_messages(*, access_token, label_ids, query, page_token, max_results):
        assert "newer_than:14d" == query  # default lookback
        return gmail_client.MessageIdsPage(
            message_ids=["m-1", "m-2"], next_page_token=None, result_size_estimate=2
        )

    async def fake_get_message(*, access_token, message_id, format):
        return _fixture_message(mid=message_id)

    async def fake_get_profile(*, access_token):
        return {"historyId": "9999"}

    with patch.multiple(
        gmail_client,
        list_messages=fake_list_messages,
        get_message=fake_get_message,
        get_profile=fake_get_profile,
    ):
        p = GmailProvider(token_provider=_fake_token_provider)
        items = []
        async for raw in p.sync(
            workspace_id=uuid.uuid4(),
            intake_source_id=uuid.uuid4(),
            cursor=None,
            config={},
        ):
            items.append(raw)
    assert len(items) == 2
    assert p.last_report is not None
    assert p.last_report.bootstrap_complete is True
    assert p.last_report.fallback_recovered is False
    assert p.last_report.new_history_id == "9999"


@pytest.mark.asyncio
async def test_delta_uses_history_id_when_cursor_present() -> None:
    """Steady state: history.list path is taken."""

    async def fake_list_history(*, access_token, start_history_id, label_id, page_token):
        assert start_history_id == "100"
        return gmail_client.HistoryPage(
            history_id="200", message_ids=["m-1"], next_page_token=None
        )

    async def fake_get_message(*, access_token, message_id, format):
        return _fixture_message(mid=message_id)

    from anant.services.intake.providers.base import SyncCursor
    cursor = SyncCursor(value={"history_id": "100", "bootstrap_complete": True})
    with patch.multiple(
        gmail_client,
        list_history=fake_list_history,
        get_message=fake_get_message,
    ):
        p = GmailProvider(token_provider=_fake_token_provider)
        items = []
        async for raw in p.sync(
            workspace_id=uuid.uuid4(),
            intake_source_id=uuid.uuid4(),
            cursor=cursor,
            config={},
        ):
            items.append(raw)
    assert len(items) == 1
    assert p.last_report is not None
    assert p.last_report.new_history_id == "200"
    assert p.last_report.fallback_recovered is False


@pytest.mark.asyncio
async def test_cr5_history_id_expired_falls_back_to_bootstrap() -> None:
    """CR-5: when history.list raises HistoryIdExpiredError, fall back to
    list_messages and surface fallback_recovered=True so the orchestrator
    can write the gmail_history_expired audit entry."""

    async def fake_list_history(**_kw):
        raise gmail_client.HistoryIdExpiredError()

    async def fake_list_messages(*, access_token, label_ids, query, page_token, max_results):
        return gmail_client.MessageIdsPage(
            message_ids=["m-1"], next_page_token=None, result_size_estimate=1
        )

    async def fake_get_message(*, access_token, message_id, format):
        return _fixture_message(mid=message_id)

    async def fake_get_profile(*, access_token):
        return {"historyId": "77777"}

    from anant.services.intake.providers.base import SyncCursor
    cursor = SyncCursor(value={"history_id": "999", "bootstrap_complete": True})

    with patch.multiple(
        gmail_client,
        list_history=fake_list_history,
        list_messages=fake_list_messages,
        get_message=fake_get_message,
        get_profile=fake_get_profile,
    ):
        p = GmailProvider(token_provider=_fake_token_provider)
        items = []
        async for raw in p.sync(
            workspace_id=uuid.uuid4(),
            intake_source_id=uuid.uuid4(),
            cursor=cursor,
            config={},
        ):
            items.append(raw)
    assert len(items) == 1
    assert p.last_report is not None
    assert p.last_report.fallback_recovered is True
    assert p.last_report.new_history_id == "77777"


def test_cursor_from_report_round_trip() -> None:
    from anant.services.intake.providers.gmail.sync import GmailSyncReport
    report = GmailSyncReport(
        new_history_id="abc",
        bootstrap_complete=True,
        items_yielded=5,
        fallback_recovered=False,
    )
    assert cursor_from_report(report) == {
        "history_id": "abc",
        "bootstrap_complete": True,
    }


def test_provider_metadata_locked() -> None:
    p = GmailProvider(token_provider=_fake_token_provider)
    assert p.name == "gmail"
    assert p.kind == IntakeSourceKind.GMAIL


# ------------------------- read-only enforcement ------------------------

def test_client_module_does_not_reference_write_methods() -> None:
    """ADR-023 enforcement test. If anyone adds messages.send or similar
    inside gmail/client.py the module's import-time assertion fails;
    this test confirms the assertion is wired."""
    import importlib
    # Re-importing must not raise. If it does, the deny-list tripped.
    importlib.reload(gmail_client)
    # And the deny-list itself must still exist.
    assert "messages.send" in gmail_client._DENY_LIST
    assert "messages.modify" in gmail_client._DENY_LIST


# ------------------------- OAuth state ------------------------

def test_oauth_state_round_trips_through_signed_jwt() -> None:
    w = uuid.uuid4()
    a = uuid.uuid4()
    s = uuid.uuid4()
    state = gmail_auth.encode_state(
        workspace_id=w, account_id=a, intake_source_id=s
    )
    claims = gmail_auth.decode_state(state)
    assert claims.workspace_id == w
    assert claims.account_id == a
    assert claims.intake_source_id == s


def test_oauth_state_rejects_tampered_token() -> None:
    state = gmail_auth.encode_state(
        workspace_id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        intake_source_id=uuid.uuid4(),
    )
    tampered = state[:-2] + ("xx" if not state.endswith("xx") else "yy")
    from anant.services.intake.providers.errors import (
        ProviderError,
        ProviderErrorKind,
    )
    with pytest.raises(ProviderError) as exc:
        gmail_auth.decode_state(tampered)
    assert exc.value.kind == ProviderErrorKind.PERMANENT
