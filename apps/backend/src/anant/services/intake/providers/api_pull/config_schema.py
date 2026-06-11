"""Per-source config for the generic API pull provider.

Vendor-specific providers (Phase 3.x) can ship their own config schema;
this is the default that covers most JSON-over-HTTP feeds.

Three auth methods locked in Batch 2 — anything more exotic ships its
own provider folder.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from anant.services.intake.providers.webhook.config_schema import (
    WebhookFieldMapping,
)


class EndpointSpec(BaseModel):
    """One endpoint within a source. A source may poll multiple endpoints."""

    model_config = ConfigDict(extra="ignore")

    path: str = Field(min_length=1)
    method: Literal["GET"] = "GET"  # POST endpoints not supported in Batch 2
    params: dict[str, str] = Field(default_factory=dict)

    # Cursor handling — vendor-shaped. `cursor_field` is a dotted path in the
    # RESPONSE that produces the next-page cursor; `cursor_param` is the QUERY
    # parameter name we should set when sending the cursor on subsequent calls.
    cursor_field: str | None = None
    cursor_param: str | None = None

    # Where to find the item list inside the response. Empty = response body
    # itself is the array; otherwise dotted path (e.g. "data.items").
    items_field: str | None = None


class ApiPullSourceConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    base_url: HttpUrl
    auth_method: Literal["bearer", "api_key_header", "oauth2_client_credentials"]

    # api_key_header method: which header to set. Token comes from credentials.
    api_key_header_name: str | None = None

    # oauth2_client_credentials method
    oauth2_token_url: HttpUrl | None = None
    oauth2_scope: str | None = None

    endpoints_polled: list[EndpointSpec] = Field(min_length=1, max_length=10)
    fetch_interval_minutes: int = Field(default=15, ge=5, le=1440)

    # Reuse the webhook mapping schema — same dotted-path transform.
    mapping: WebhookFieldMapping = Field(default_factory=WebhookFieldMapping)

    # Optional explicit hostname allowlist. If empty, the SSRF guard
    # relies solely on the private-IP deny list.
    hostname_allowlist: list[str] = Field(default_factory=list)

    # Hard size cap; anything bigger is treated as PERMANENT.
    max_response_bytes: int = Field(default=5 * 1024 * 1024, ge=1024, le=64 * 1024 * 1024)
