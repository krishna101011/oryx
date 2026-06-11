"""API pull provider tests — SSRF, auth methods, cursor paging, mapping."""
from __future__ import annotations

import socket
import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from anant.services.intake.providers.api_pull.client import (
    FetchedResponse,
    ResolvedCredentials,
)
from anant.services.intake.providers.api_pull.config_schema import (
    ApiPullSourceConfig,
    EndpointSpec,
)
from anant.services.intake.providers.api_pull.mapper import (
    extract_cursor,
    extract_items,
    response_to_raw_items,
)
from anant.services.intake.providers.api_pull.safety import assert_url_safe
from anant.services.intake.providers.api_pull.sync import (
    ApiPullProvider,
    cursor_from_report,
)
from anant.services.intake.providers.base import (
    IntakeSourceKind,
    ValidationStatus,
)
from anant.services.intake.providers.errors import (
    ProviderError,
    ProviderErrorKind,
)
from anant.services.intake.providers.webhook.config_schema import (
    WebhookFieldMapping,
)

# ---------------------------- SSRF guard ----------------------------

def _patch_dns(addr: str):
    """Replace socket.getaddrinfo so the SSRF check tests with a known IP."""
    def fake_getaddrinfo(host, port, *a, **kw):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (addr, port))]
    return patch("socket.getaddrinfo", fake_getaddrinfo)


def test_safety_rejects_unsupported_scheme() -> None:
    with pytest.raises(ProviderError) as exc:
        assert_url_safe("file:///etc/passwd")
    assert "scheme" in exc.value.message.lower()


@pytest.mark.parametrize(
    "addr",
    ["10.0.0.5", "192.168.1.1", "172.16.0.1", "127.0.0.1", "169.254.169.254", "169.254.10.5"],
)
def test_safety_rejects_private_loopback_metadata_linklocal(addr: str) -> None:
    with _patch_dns(addr):
        with pytest.raises(ProviderError) as exc:
            assert_url_safe("https://vendor.test/x")
        assert exc.value.kind == ProviderErrorKind.PERMANENT


def test_safety_accepts_normal_public_ip() -> None:
    with _patch_dns("8.8.8.8"):
        assert_url_safe("https://vendor.test/x")  # no raise


def test_safety_allowlist_short_circuits_other_hosts() -> None:
    # Even with a public IP, a host not in the allowlist is rejected.
    with _patch_dns("8.8.8.8"):
        with pytest.raises(ProviderError) as exc:
            assert_url_safe(
                "https://evil.test/x", hostname_allowlist=["vendor.test"]
            )
        assert "allowlist" in exc.value.message.lower()


def test_safety_allowlist_accepts_subdomains() -> None:
    with _patch_dns("8.8.8.8"):
        assert_url_safe(
            "https://api.vendor.test/x", hostname_allowlist=["vendor.test"]
        )


# ---------------------------- config ----------------------------

@pytest.mark.asyncio
async def test_validate_config_requires_at_least_one_endpoint() -> None:
    p = ApiPullProvider(credentials_provider=AsyncMock())
    result = await p.validate_config({
        "base_url": "https://api.vendor.test/",
        "auth_method": "bearer",
        "endpoints_polled": [],
    })
    assert result.status == ValidationStatus.INVALID


@pytest.mark.asyncio
async def test_validate_config_accepts_minimal_bearer_setup() -> None:
    p = ApiPullProvider(credentials_provider=AsyncMock())
    result = await p.validate_config({
        "base_url": "https://api.vendor.test/",
        "auth_method": "bearer",
        "endpoints_polled": [{"path": "/v1/items"}],
    })
    assert result.status == ValidationStatus.OK


# ---------------------------- mapper ----------------------------

def test_extract_items_with_no_field_uses_items_key_default() -> None:
    body = {"items": [{"id": "1"}, {"id": "2"}]}
    out = extract_items(body, None)
    assert len(out) == 2


def test_extract_items_with_dotted_path() -> None:
    body = {"data": {"results": [{"id": "x"}]}}
    out = extract_items(body, "data.results")
    assert out == [{"id": "x"}]


def test_extract_items_missing_path_returns_empty() -> None:
    assert extract_items({"a": 1}, "nope.here") == []


def test_extract_cursor_returns_path_value() -> None:
    body = {"page": {"next": "cur-2"}}
    assert extract_cursor(body, "page.next") == "cur-2"


def test_extract_cursor_missing_returns_none() -> None:
    assert extract_cursor({}, "page.next") is None
    assert extract_cursor({"x": 1}, None) is None


def test_response_to_raw_items_maps_each_record() -> None:
    body = {
        "items": [
            {"id": "a", "subject": "Alpha"},
            {"id": "b", "subject": "Beta"},
        ]
    }
    items = response_to_raw_items(
        body=body, items_field=None, mapping=WebhookFieldMapping()
    )
    assert [r.external_id for r in items] == ["a", "b"]
    assert items[0].subject == "Alpha"


# ---------------------------- sync paging ----------------------------

def _config(**kw) -> ApiPullSourceConfig:
    defaults = dict(
        base_url="https://api.vendor.test/",
        auth_method="bearer",
        endpoints_polled=[
            EndpointSpec(
                path="/v1/items",
                cursor_field="next_cursor",
                cursor_param="cursor",
            )
        ],
    )
    defaults.update(kw)
    return ApiPullSourceConfig.model_validate(defaults)


@pytest.mark.asyncio
async def test_sync_yields_items_and_persists_final_cursor() -> None:
    pages = [
        FetchedResponse(
            body={
                "items": [{"id": "a"}, {"id": "b"}],
                "next_cursor": "page-2",
            },
            final_url="https://api.vendor.test/v1/items",
        ),
        FetchedResponse(
            body={"items": [{"id": "c"}]},  # no next_cursor → end
            final_url="https://api.vendor.test/v1/items",
        ),
    ]
    call_count = {"n": 0}

    async def fake_fetch(**kw):
        i = call_count["n"]
        call_count["n"] += 1
        return pages[i]

    async def fake_creds() -> ResolvedCredentials:
        return ResolvedCredentials(token="t")

    p = ApiPullProvider(credentials_provider=fake_creds)
    with patch(
        "anant.services.intake.providers.api_pull.sync.fetch_endpoint", fake_fetch
    ):
        items = []
        async for raw in p.sync(
            workspace_id=uuid.uuid4(),
            intake_source_id=uuid.uuid4(),
            cursor=None,
            config=_config().model_dump(mode="json"),
        ):
            items.append(raw)

    assert [r.external_id for r in items] == ["a", "b", "c"]
    assert p.last_report is not None
    # End-of-pages → cursor cleared so next interval restarts
    assert p.last_report.endpoint_cursors == {}
    assert p.last_report.items_yielded == 3


@pytest.mark.asyncio
async def test_sync_respects_starting_cursor_from_prior_run() -> None:
    captured: dict[str, Any] = {}

    async def fake_fetch(**kw):
        captured.update(kw)
        return FetchedResponse(
            body={"items": [{"id": "x"}]}, final_url="x"
        )

    async def fake_creds() -> ResolvedCredentials:
        return ResolvedCredentials(token="t")

    from anant.services.intake.providers.base import SyncCursor
    starting = SyncCursor(value={"endpoints": {"/v1/items": "previous-cursor"}})

    p = ApiPullProvider(credentials_provider=fake_creds)
    with patch(
        "anant.services.intake.providers.api_pull.sync.fetch_endpoint", fake_fetch
    ):
        async for _ in p.sync(
            workspace_id=uuid.uuid4(),
            intake_source_id=uuid.uuid4(),
            cursor=starting,
            config=_config().model_dump(mode="json"),
        ):
            pass

    assert captured["params"]["cursor"] == "previous-cursor"


@pytest.mark.asyncio
async def test_sync_stops_at_max_pages_safety_bound() -> None:
    """If the vendor keeps returning a cursor, we still bail at the cap."""
    async def fake_fetch(**kw):
        return FetchedResponse(
            body={"items": [{"id": "x"}], "next_cursor": "infinity"},
            final_url="x",
        )

    async def fake_creds() -> ResolvedCredentials:
        return ResolvedCredentials(token="t")

    p = ApiPullProvider(credentials_provider=fake_creds)
    with patch(
        "anant.services.intake.providers.api_pull.sync.fetch_endpoint", fake_fetch
    ):
        items = []
        async for raw in p.sync(
            workspace_id=uuid.uuid4(),
            intake_source_id=uuid.uuid4(),
            cursor=None,
            config=_config().model_dump(mode="json"),
        ):
            items.append(raw)

    # MAX_PAGES_PER_ENDPOINT = 20 in sync.py
    assert len(items) == 20
    # And cursor preserved for next run.
    assert p.last_report is not None
    assert p.last_report.endpoint_cursors == {"/v1/items": "infinity"}


def test_cursor_from_report_round_trip() -> None:
    from anant.services.intake.providers.api_pull.sync import ApiPullSyncReport
    report = ApiPullSyncReport(
        endpoint_cursors={"/v1/a": "c1", "/v1/b": "c2"}, items_yielded=10
    )
    assert cursor_from_report(report) == {
        "endpoints": {"/v1/a": "c1", "/v1/b": "c2"}
    }


def test_provider_metadata_locked() -> None:
    p = ApiPullProvider(credentials_provider=AsyncMock())
    assert p.name == "api_pull"
    assert p.kind == IntakeSourceKind.API_PULL


# ---------------------------- auth method wiring ----------------------------

@pytest.mark.asyncio
async def test_client_applies_bearer_auth_header() -> None:
    from anant.services.intake.providers.api_pull import client as cli
    captured_headers: dict[str, str] = {}

    async def fake_request(self, url, **kw):
        captured_headers.update(kw.get("headers") or {})
        return type("R", (), {
            "status_code": 200,
            "content": b'{"items":[]}',
            "headers": {},
            "url": url,
            "text": "",
        })()

    with _patch_dns("8.8.8.8"), patch(
        "httpx.AsyncClient.get", fake_request
    ):
        await cli.fetch_endpoint(
            config=_config(),
            creds=ResolvedCredentials(token="my-bearer"),
            path="/v1/items",
            params={},
        )
    assert captured_headers.get("Authorization") == "Bearer my-bearer"


@pytest.mark.asyncio
async def test_client_applies_api_key_header_with_custom_name() -> None:
    from anant.services.intake.providers.api_pull import client as cli
    captured: dict[str, str] = {}

    async def fake_request(self, url, **kw):
        captured.update(kw.get("headers") or {})
        return type("R", (), {
            "status_code": 200,
            "content": b'{"items":[]}',
            "headers": {},
            "url": url,
            "text": "",
        })()

    cfg = _config(
        auth_method="api_key_header",
        api_key_header_name="X-Vendor-Key",
    )
    with _patch_dns("8.8.8.8"), patch("httpx.AsyncClient.get", fake_request):
        await cli.fetch_endpoint(
            config=cfg,
            creds=ResolvedCredentials(token="key-xyz"),
            path="/v1/items",
            params={},
        )
    assert captured.get("X-Vendor-Key") == "key-xyz"
    assert "Authorization" not in captured


@pytest.mark.asyncio
async def test_client_oauth2_cc_requires_token_url_and_client_secret() -> None:
    from anant.services.intake.providers.api_pull import client as cli
    cfg = _config(
        auth_method="oauth2_client_credentials",
        oauth2_token_url="https://api.vendor.test/oauth/token",
    )
    with _patch_dns("8.8.8.8"):
        with pytest.raises(ProviderError) as exc:
            await cli.fetch_endpoint(
                config=cfg,
                creds=ResolvedCredentials(),  # missing client_id/secret
                path="/v1/items",
                params={},
            )
        assert exc.value.kind == ProviderErrorKind.PERMANENT
