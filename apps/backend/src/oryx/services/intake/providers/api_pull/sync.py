"""ApiPullProvider sync loop.

Cursor model is per-endpoint. The stored cursor is a dict keyed by endpoint
path:
    {"endpoints": {"/v1/items": "next-page-token-1", "/v1/alerts": "abc"}}

When an endpoint doesn't return a cursor in its response, that endpoint
is considered caught up for this sync; we'll re-fetch from the start on
the next interval. Vendors who paginate forever should be configured with
a sane fetch_interval_minutes.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from oryx.services.intake.providers.api_pull.client import (
    ResolvedCredentials,
    fetch_endpoint,
)
from oryx.services.intake.providers.api_pull.config_schema import (
    ApiPullSourceConfig,
    EndpointSpec,
)
from oryx.services.intake.providers.api_pull.mapper import (
    extract_cursor,
    response_to_raw_items,
)
from oryx.services.intake.providers.base import (
    IntakeSourceKind,
    RawItem,
    SyncCursor,
    ValidationResult,
    ValidationStatus,
)

MAX_PAGES_PER_ENDPOINT = 20  # bounds the cost of a single sync invocation


@dataclass(frozen=True)
class ApiPullSyncReport:
    endpoint_cursors: dict[str, str]
    items_yielded: int


def cursor_from_report(report: ApiPullSyncReport) -> dict[str, Any]:
    return {"endpoints": dict(report.endpoint_cursors)}


# Credentials provider: the orchestrator hands the provider an async callable
# that resolves credentials. Keeps the credential I/O at one boundary.
CredentialsProvider = Any  # callable[..., Awaitable[ResolvedCredentials]]


class ApiPullProvider:
    name = "api_pull"
    kind = IntakeSourceKind.API_PULL

    def __init__(self, *, credentials_provider: CredentialsProvider) -> None:
        self._credentials_provider = credentials_provider
        self._last_report: ApiPullSyncReport | None = None

    @property
    def last_report(self) -> ApiPullSyncReport | None:
        return self._last_report

    async def validate_config(self, config: dict[str, Any]) -> ValidationResult:
        try:
            ApiPullSourceConfig.model_validate(config)
            return ValidationResult(status=ValidationStatus.OK)
        except Exception as e:
            return ValidationResult(
                status=ValidationStatus.INVALID, message=str(e)
            )

    async def sync(
        self,
        *,
        workspace_id: uuid.UUID,
        intake_source_id: uuid.UUID,
        cursor: SyncCursor | None,
        config: dict[str, Any],
    ) -> AsyncIterator[RawItem]:
        parsed = ApiPullSourceConfig.model_validate(config)
        endpoint_cursors_in: dict[str, str] = (
            cursor.value.get("endpoints", {}) if cursor else {}
        )
        creds = await self._credentials_provider()

        new_endpoint_cursors: dict[str, str] = {}
        total = 0

        for endpoint in parsed.endpoints_polled:
            async for raw in _sync_one_endpoint(
                config=parsed,
                endpoint=endpoint,
                creds=creds,
                start_cursor=endpoint_cursors_in.get(endpoint.path),
                result_cursors=new_endpoint_cursors,
            ):
                yield raw
                total += 1

        self._last_report = ApiPullSyncReport(
            endpoint_cursors=new_endpoint_cursors,
            items_yielded=total,
        )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

async def _sync_one_endpoint(
    *,
    config: ApiPullSourceConfig,
    endpoint: EndpointSpec,
    creds: ResolvedCredentials,
    start_cursor: str | None,
    result_cursors: dict[str, str],
) -> AsyncIterator[RawItem]:
    """Yield items page by page. Mutates `result_cursors`:
       - on cursor present at end → sets [endpoint.path] = cursor
       - on no cursor at end → ensures [endpoint.path] is absent
    """
    page_cursor = start_cursor
    pages_fetched = 0
    # Default: clear any prior cursor for this endpoint unless we explicitly
    # set one below.
    result_cursors.pop(endpoint.path, None)

    while True:
        params = dict(endpoint.params)
        if page_cursor and endpoint.cursor_param:
            params[endpoint.cursor_param] = page_cursor

        result = await fetch_endpoint(
            config=config,
            creds=creds,
            path=endpoint.path,
            params=params,
        )
        items = response_to_raw_items(
            body=result.body,
            items_field=endpoint.items_field,
            mapping=config.mapping,
        )
        for raw in items:
            yield raw

        new_cursor = extract_cursor(result.body, endpoint.cursor_field)
        pages_fetched += 1
        if new_cursor is None:
            # End of pages — clear any cursor we may have set on earlier pages
            # of this same sync. Next interval starts fresh, which is the
            # right behavior for vendors that don't paginate backwards.
            result_cursors.pop(endpoint.path, None)
            break
        # More pages: persist the cursor so the next sync resumes here, and
        # keep paging within this run until we exhaust or hit the cap.
        result_cursors[endpoint.path] = new_cursor
        page_cursor = new_cursor

        if pages_fetched >= MAX_PAGES_PER_ENDPOINT:
            break
