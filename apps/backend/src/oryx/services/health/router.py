"""Health + version endpoints.

These are the first end-to-end typed endpoints — the contract is defined
in packages/shared-types/src/common.ts and mirrored in shared/types.py.
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request

from oryx.config import Settings, get_settings
from oryx.core.dependencies import envelope, get_request_id
from oryx.shared.types import ApiResponse, BuildInfo, HealthStatus

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[HealthStatus])
async def health(
    request: Request, settings: Settings = Depends(get_settings)
) -> dict:
    payload = HealthStatus(
        status="ok",
        service=settings.service_name,
        environment=settings.environment,
        serverTime=datetime.now(UTC),
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))


@router.get("/version", response_model=ApiResponse[BuildInfo])
async def version(
    request: Request, settings: Settings = Depends(get_settings)
) -> dict:
    payload = BuildInfo(
        version=settings.build_version,
        commit=settings.build_commit,
        builtAt=datetime.now(UTC),
    )
    return envelope(payload.model_dump(by_alias=True), request_id=get_request_id(request))
