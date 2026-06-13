"""FastAPI application factory and entrypoint.

Run locally:
    uv run uvicorn anant.main:app --reload --port 8000

Process topology (CR-7 / ADR-025): production runs three processes —
this API plus `python -m anant.services.intake.scheduler` and
`python -m anant.services.queue.drainer`. Local dev may colocate all
three by setting ANANT_DEV_MONOPROCESS=1 (dev environment only).
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from anant.config import get_settings
from anant.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from anant.core.logging import configure_logging
from anant.core.middleware import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    TimingMiddleware,
)

# ---- Phase 2 real services ----
from anant.services.accounts.router import router as accounts_router

# ---- Phase 1 service stubs (still mounted) ----
from anant.services.activity.router import router as activity_router
from anant.services.analytics.router import router as analytics_router
from anant.services.auth.me import router as auth_me_router
from anant.services.auth.router import router as auth_router
from anant.services.automation.router import router as automation_router
from anant.services.claims.router import router as claims_router
from anant.services.conflicts.router import router as conflicts_router
from anant.services.content.router import router as content_router
from anant.services.evidence.router import router as evidence_router
from anant.services.feature_flags.router import router as feature_flags_router
from anant.services.health.router import router as health_router
from anant.services.intake.admin_router import router as intake_admin_router
from anant.services.intake.oauth_router import router as intake_oauth_router
from anant.services.intake.router import router as intake_router
from anant.services.intake.webhooks_router import router as intake_webhooks_router
from anant.services.onboarding.router import router as onboarding_router
from anant.services.preferences.router import router as preferences_router
from anant.services.profiles.router import router as profiles_router
from anant.services.publishing.router import router as publishing_router
from anant.services.research.router import router as research_router
from anant.services.review.router import router as review_router
from anant.services.sessions.router import router as sessions_router
from anant.services.sources.router import router as sources_router
from anant.services.training.router import router as training_router
from anant.services.verification.router import router as verification_router
from anant.services.workspaces.router import router as workspaces_router


def should_colocate(settings) -> bool:
    """§14.3 — monoprocess is a dev convenience only; the env check is the
    hard stop that keeps a stray flag from colocating in production."""
    return settings.anant_dev_monoprocess and settings.environment == "dev"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    tasks: list[asyncio.Task] = []
    settings = get_settings()
    if should_colocate(settings):
        # Imports stay local so the API process never pays for (or
        # accidentally depends on) worker wiring in the normal topology.
        from anant.core.db import get_sessionmaker
        from anant.services.intake.scheduler import IntakeScheduler
        from anant.services.queue.drainer import OutboxDrainer, build_bus

        sm = get_sessionmaker()
        scheduler = IntakeScheduler(
            sm,
            per_kind_concurrency=settings.scheduler_per_kind_concurrency,
            tick_seconds=settings.scheduler_tick_seconds,
        )
        drainer = OutboxDrainer(sm, build_bus(), batch_size=settings.drainer_batch_size)
        tasks = [
            asyncio.create_task(scheduler.run_forever(), name="intake.scheduler"),
            asyncio.create_task(drainer.run_forever(), name="queue.drainer"),
        ]
    yield
    for task in tasks:
        task.cancel()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    app = FastAPI(
        title="Anant Capital API",
        version=settings.build_version,
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        lifespan=_lifespan,
    )

    # --- Middleware (added last = runs first; the stack is reversed) ---
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id", "X-Response-Time"],
    )
    app.add_middleware(RateLimitMiddleware, prefix=settings.api_prefix)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # --- Exception handlers ---
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # --- Routers ---
    p = settings.api_prefix

    # Phase 1 (still stubs in their respective phases)
    app.include_router(health_router, prefix=p)
    app.include_router(intake_router, prefix=p)
    app.include_router(intake_admin_router, prefix=p)
    app.include_router(intake_oauth_router, prefix=p)
    app.include_router(intake_webhooks_router, prefix=p)
    app.include_router(verification_router, prefix=p)
    app.include_router(research_router, prefix=p)
    app.include_router(content_router, prefix=p)
    app.include_router(publishing_router, prefix=p)
    app.include_router(automation_router, prefix=p)
    app.include_router(analytics_router, prefix=p)
    app.include_router(training_router, prefix=p)

    # Phase 4 (Waves A-B): read-only claims + evidence surfaces.
    app.include_router(claims_router, prefix=p)
    app.include_router(evidence_router, prefix=p)
    # Phase 4 (Wave D): conflicts (read + resolve) + analyst review.
    app.include_router(conflicts_router, prefix=p)
    app.include_router(review_router, prefix=p)

    # Phase 2 real services. /auth/me is its own router for clarity.
    app.include_router(auth_router, prefix=p)
    app.include_router(auth_me_router, prefix=p)
    app.include_router(accounts_router, prefix=p)
    app.include_router(profiles_router, prefix=p)
    app.include_router(workspaces_router, prefix=p)
    app.include_router(preferences_router, prefix=p)
    app.include_router(sources_router, prefix=p)
    app.include_router(activity_router, prefix=p)
    app.include_router(feature_flags_router, prefix=p)
    app.include_router(onboarding_router, prefix=p)
    app.include_router(sessions_router, prefix=p)

    return app


app = create_app()
