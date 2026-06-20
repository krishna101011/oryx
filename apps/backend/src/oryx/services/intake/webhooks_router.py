"""Public inbound webhook endpoint.

NO bearer auth. Security is entirely from:
  1. HMAC signature over (timestamp.body) using a per-source secret
  2. ±5 min replay window on the timestamp
  3. Persistent idempotency table dedupes retries (CR-4)
  4. 256 KiB body cap enforced at the edge

On success:
  - Records the idempotency key
  - Calls IntakeService.ingest_raw_item (Batch 1) which normalizes + dedupes +
    persists + emits intake.item.received

This file is the ONLY public-internet entrypoint into the intake pipeline.
Treat it accordingly — any change here needs a security review.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Path, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from oryx.core.dependencies import (
    db_session,
    envelope,
    get_request_id,
)
from oryx.core.errors import (
    NotFoundError,
    ValidationError,
)
from oryx.core.models import IntakeAuditLog, IntakeSource
from oryx.services.intake.credentials import IntakeCredentialsRepository
from oryx.services.intake.providers.errors import ProviderError
from oryx.services.intake.providers.webhook.config_schema import (
    HEADER_IDEMPOTENCY_KEY,
    HEADER_SIGNATURE,
    HEADER_TIMESTAMP,
    MAX_BODY_BYTES,
)
from oryx.services.intake.providers.webhook.idempotency import (
    IdempotencyOutcome,
    WebhookIdempotencyRepository,
)
from oryx.services.intake.providers.webhook.provider import WebhookProvider
from oryx.services.intake.service import IntakeService

router = APIRouter(prefix="/intake/webhooks", tags=["intake-webhook"])


# response_model=None: the `dict | JSONResponse` union is not a valid pydantic
# field, and FastAPI ≥0.112 refuses to infer a response model from it.
@router.post("/{workspace_id}/{intake_source_id}", response_model=None)
async def receive_webhook(
    workspace_id: uuid.UUID = Path(...),
    intake_source_id: uuid.UUID = Path(...),
    request: Request = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(db_session),
) -> dict | JSONResponse:
    # 1. Read body with size cap (defensive — also enforced by reverse proxy
    #    in production but never trust upstream alone).
    raw_body = await request.body()
    if len(raw_body) > MAX_BODY_BYTES:
        raise ValidationError(
            details={"reason": "body_too_large", "max_bytes": MAX_BODY_BYTES}
        )

    # 2. Source must exist, belong to the workspace in the path, and be active.
    source = await _load_source(db, workspace_id, intake_source_id)

    # 3. Load the live secret(s) — current + previous during rotation grace.
    creds_repo = IntakeCredentialsRepository(db)
    pair = await creds_repo.load(
        intake_source_id=source.id, workspace_id=workspace_id
    )
    if pair is None:
        raise NotFoundError("Webhook credentials missing")
    secrets_list: list[str] = [pair.token.decode("utf-8")]
    if pair.refresh_token:  # we re-use the refresh slot for "previous secret"
        secrets_list.append(pair.refresh_token.decode("utf-8"))

    # 4. Verify HMAC + timestamp window. Failures → 401 (PROVIDER_ERROR maps
    #    to 502 by default; we want 401 here). Build the response manually.
    from oryx.services.intake.providers.webhook.secrets import verify_request
    try:
        verify_request(
            secrets=secrets_list,
            signature_header=request.headers.get(HEADER_SIGNATURE),
            timestamp_header=request.headers.get(HEADER_TIMESTAMP),
            body=raw_body,
        )
    except ProviderError as e:
        # Audit but do not include the body — operator forensics is in audit
        # via timestamp + signature presence.
        db.add(
            IntakeAuditLog(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                intake_source_id=source.id,
                event="webhook_rejected",
                data={"reason": e.message[:120]},
            )
        )
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "code": "AUTH_REQUIRED",
                    "message": "Webhook authentication failed",
                    "requestId": get_request_id(request),
                }
            },
        )

    # 5. Idempotency — body-hash fallback if the sender didn't provide one.
    idempotency_key = request.headers.get(HEADER_IDEMPOTENCY_KEY)
    if not idempotency_key:
        import hashlib
        idempotency_key = "sha256:" + hashlib.sha256(raw_body).hexdigest()

    idem_repo = WebhookIdempotencyRepository(db)
    outcome = await idem_repo.record(
        workspace_id=workspace_id,
        intake_source_id=source.id,
        idempotency_key=idempotency_key,
    )
    if outcome == IdempotencyOutcome.DUPLICATE:
        # Idempotent success — 200 with no further work.
        db.add(
            IntakeAuditLog(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                intake_source_id=source.id,
                event="webhook_duplicate",
                data={"idempotency_key": idempotency_key[:64]},
            )
        )
        return envelope(
            {"duplicate": True}, request_id=get_request_id(request)
        )

    # 6. Hand off to the provider + orchestrator. Each item gets its own
    #    transaction inside IntakeService (Batch 1).
    provider = WebhookProvider()
    intake_svc = IntakeService(db)
    inserted = 0
    skipped = 0
    async for raw in provider.handle_webhook(
        workspace_id=workspace_id,
        intake_source_id=source.id,
        headers=dict(request.headers),
        body=raw_body,
        config=source.config or {},
    ):
        result = await intake_svc.ingest_raw_item(
            workspace_id=workspace_id,
            intake_source_id=source.id,
            provider_name="webhook",
            raw=raw,
        )
        if result.outcome.value == "inserted":
            inserted += 1
        else:
            skipped += 1

    db.add(
        IntakeAuditLog(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            intake_source_id=source.id,
            event="webhook_received",
            data={"inserted": inserted, "skipped": skipped},
        )
    )

    return envelope(
        {"inserted": inserted, "skipped": skipped},
        request_id=get_request_id(request),
    )


# ---------------- helpers ----------------

async def _load_source(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    source_id: uuid.UUID,
) -> IntakeSource:
    result = await db.execute(
        select(IntakeSource).where(
            IntakeSource.id == source_id,
            IntakeSource.workspace_id == workspace_id,
            IntakeSource.deleted_at.is_(None),
            IntakeSource.kind == "webhook",
            IntakeSource.enabled.is_(True),
        )
    )
    source = result.scalar_one_or_none()
    if source is None:
        # Don't leak whether the workspace exists vs the source exists.
        raise NotFoundError("Webhook endpoint not found")
    return source
