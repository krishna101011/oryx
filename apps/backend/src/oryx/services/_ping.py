"""Helper for building a stub `ping` router used by every domain service in Phase 1.

Each domain (users, intake, verification, ...) imports this and registers a
single GET /<domain>/ping endpoint so the service folder is non-empty and
mountable from main.py. Real routes land in later phases.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from oryx.core.dependencies import envelope, get_request_id


def make_ping_router(service: str) -> APIRouter:
    router = APIRouter(prefix=f"/{service}", tags=[service])

    @router.get("/ping")
    async def ping(request: Request) -> dict:
        return envelope({"service": service, "pong": True}, request_id=get_request_id(request))

    return router
