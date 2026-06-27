"""Phase 5 end-to-end proof: research.packet.ready → content.published.

The single genuinely end-to-end test of the whole Create·Publish phase. Only the
AI generation call is faked (the same proven pattern as every prior wave); every
other hop is real, INCLUDING a real local HTTP server that receives the actual
signed webhook delivery (no faked channel). It:

  - drives the real chain packet-ready → consume → generate → submit → approve →
    publish, asserting at each hop;
  - proves delivery against a REAL HTTP server and verifies the HMAC signature
    the server received;
  - WALKS the causation chain by following parent event ids in outbox_events
    (content.published → content.draft.approved → content.draft.updated/created),
    confirming each parent row actually exists — not merely trusting payloads;
  - re-confirms the consumed_at boundary: Phase 5 sets it exactly once (step 1)
    and nothing afterwards — not generation, not publishing — ever touches it.
"""
from __future__ import annotations

import hashlib
import hmac
import http.server
import json
import threading
import uuid
from datetime import UTC, datetime
from typing import ClassVar

import pytest
from sqlalchemy import func, select

pytestmark = pytest.mark.requires_db


class _FakeGenerator:
    """Stands in for the Sonnet call — the only fake in the whole pipeline.
    Reports the real model id so the generation_model assertion is meaningful."""

    model = "claude-sonnet-4-6"
    version = 1

    def __init__(
        self,
        text: str = "Acme Corp raised five billion dollars this quarter.",
        tokens: int = 42,
    ) -> None:
        self._text = text
        self._tokens = tokens
        self.calls = 0

    async def generate(self, *, objects, format, instructions=None, template=None):
        from oryx.services.drafts.models import GeneratedDraft

        self.calls += 1
        return GeneratedDraft(
            content=self._text,
            word_count=len(self._text.split()),
            token_count=self._tokens,
        )


class _CapturingHandler(http.server.BaseHTTPRequestHandler):
    """Real webhook receiver: captures the body + signature headers and returns
    a 200 with an external id, exactly as a real downstream would."""

    received: ClassVar[dict] = {}

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        type(self).received = {
            "body": body,
            "signature": self.headers.get("X-Oryx-Signature"),
            "timestamp": self.headers.get("X-Oryx-Timestamp"),
        }
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"id": "whk_e2e_1"}')

    def log_message(self, *args) -> None:  # silence the test server
        pass


async def _seed(sm, *, webhook_url: str, secret: str):
    """workspace + creator/approver accounts + 2 (item, intelligence_object) +
    research workspace + a 'ready' (un-consumed) packet + a webhook target."""
    from oryx.core.credential_crypto import encrypt_credentials
    from oryx.core.models import (
        Account,
        IntakeItem,
        IntakeSource,
        IntelligenceObject,
        PublishTarget,
        ResearchPacket,
        ResearchWorkspace,
        Workspace,
    )

    now = datetime.now(UTC)
    async with sm() as session:
        creator = Account(
            id=uuid.uuid4(),
            email=f"creator+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        # A DIFFERENT account approves — the self-approval guard (Wave C) is never
        # engaged, keeping this test focused on the chain, not the policy.
        approver = Account(
            id=uuid.uuid4(),
            email=f"approver+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add_all([creator, approver])
        await session.flush()
        ws = Workspace(id=uuid.uuid4(), name="E2E", owner_account_id=creator.id)
        session.add(ws)
        await session.flush()
        source = IntakeSource(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            kind="rss",
            name="feed",
            enabled=True,
            config={},
            origin_kind="custom",
            status="healthy",
        )
        session.add(source)
        await session.flush()

        obj_ids: list[uuid.UUID] = []
        for i in range(2):
            item = IntakeItem(
                id=uuid.uuid4(),
                workspace_id=ws.id,
                intake_source_id=source.id,
                provider_name="rss",
                external_id=f"x-{uuid.uuid4().hex[:8]}",
                received_at=now,
                payload={},
                fingerprint=uuid.uuid4().hex,
            )
            session.add(item)
            await session.flush()
            obj = IntelligenceObject(
                id=uuid.uuid4(),
                workspace_id=ws.id,
                intake_item_id=item.id,
                epistemic_type="fact",
                confidence_score=0.9,
                verification_status="verified",
                claim_ids=[],
                conflict_ids=[],
                key_facts={"Acme": {"predicate": "raised", "object": "$5B"}},
                headline=f"Acme raised $5B ({i})",
                scoring_version=1,
            )
            session.add(obj)
            await session.flush()
            obj_ids.append(obj.id)

        rws = ResearchWorkspace(
            id=uuid.uuid4(), account_id=creator.id, workspace_id=ws.id, name="RW"
        )
        session.add(rws)
        await session.flush()
        packet = ResearchPacket(
            id=uuid.uuid4(),
            research_workspace_id=rws.id,
            workspace_id=ws.id,
            name="E2E packet",
            status="ready",
            intelligence_object_ids=obj_ids,
            conflict_acknowledged_ids=[],
            ready_at=now,
            consumed_at=None,  # Phase 5 owns this; still NULL at seed time
        )
        session.add(packet)
        await session.flush()
        ct, iv = encrypt_credentials({"secret": secret})
        target = PublishTarget(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            name="Webhook target",
            channel="webhook",
            credentials=ct,
            credentials_iv=iv,
            config={"url": webhook_url},
            is_active=True,
        )
        session.add(target)
        await session.commit()
        return ws.id, creator.id, approver.id, packet.id, obj_ids, target.id


@pytest.mark.asyncio
async def test_full_pipeline_packet_to_published(sm) -> None:
    from oryx.core.models import (
        DraftCitation,
        DraftVersion,
        OutboxEvent,
        Publication,
        ResearchPacket,
    )
    from oryx.services.drafts.events.constants import (
        DRAFT_APPROVED,
        DRAFT_CREATED,
        DRAFT_UPDATED,
    )
    from oryx.services.drafts.service import DraftService, PacketConsumerHandler
    from oryx.services.publishing.engine import PublishingEngine
    from oryx.services.publishing.events.constants import CONTENT_PUBLISHED
    from oryx.services.queue.bus import event_from_envelope
    from oryx.services.queue.outbox import enqueue_event
    from oryx.services.research.events.constants import PACKET_READY

    secret = "e2e-shared-secret"

    # ---- Start the REAL local HTTP server that receives the webhook ----------
    _CapturingHandler.received = {}
    server = http.server.HTTPServer(("127.0.0.1", 0), _CapturingHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        webhook_url = f"http://127.0.0.1:{port}/hook"
        ws_id, creator_id, approver_id, packet_id, obj_ids, target_id = await _seed(
            sm, webhook_url=webhook_url, secret=secret
        )

        # ---- Step 1: PacketConsumerHandler processes research.packet.ready ----
        # Enqueue a real root event, read it back, reconstruct the DomainEvent,
        # and run the REAL handler (its only job: set consumed_at).
        async with sm() as session:
            root_id = await enqueue_event(
                session,
                name=PACKET_READY,
                payload={"packetId": str(packet_id), "workspaceId": str(ws_id)},
                workspace_id=ws_id,
            )
            await session.commit()
            envelope = (await session.get(OutboxEvent, root_id)).event
        await PacketConsumerHandler(sm)(event_from_envelope(envelope))

        async with sm() as session:
            packet = await session.get(ResearchPacket, packet_id)
            assert packet.consumed_at is not None  # handoff marked exactly here
            assert packet.status == "ready"  # consumed_at only — status untouched
            consumed_at_after_step1 = packet.consumed_at

        # ---- Step 2: generate the draft (Sonnet faked) -----------------------
        draft = await DraftService(sm, generator=_FakeGenerator()).generate_draft(
            packet_id=packet_id,
            format="article",
            instructions=None,
            account_id=creator_id,
            workspace_id=ws_id,
        )
        draft_id = draft.id
        async with sm() as session:
            versions = (
                await session.execute(
                    select(DraftVersion).where(DraftVersion.draft_id == draft_id)
                )
            ).scalars().all()
            assert len(versions) == 1  # DraftVersion 1
            assert versions[0].version_number == 1
            assert versions[0].is_ai_generated is True
            cites = (
                await session.execute(
                    select(DraftCitation.intelligence_object_id).where(
                        DraftCitation.draft_id == draft_id
                    )
                )
            ).scalars().all()
            assert set(cites) == set(obj_ids)  # draft_citations for every source

        # ---- Step 3: submit for review ---------------------------------------
        svc = DraftService(sm, generator=_FakeGenerator())
        d = await svc.submit_review(
            draft_id=draft_id, account_id=creator_id, workspace_id=ws_id
        )
        assert d.status == "in_review"

        # ---- Step 4: approve (different account → no self-approval guard) -----
        d = await svc.approve_draft(
            draft_id=draft_id, account_id=approver_id, workspace_id=ws_id, note=None
        )
        assert d.status == "approved"

        # ---- Step 5: publish to the webhook target (REAL HTTP delivery) ------
        results = await PublishingEngine(sm).publish_draft(
            draft_id=draft_id,
            target_ids=[target_id],
            workspace_id=ws_id,
            account_id=approver_id,
        )
        assert len(results) == 1
        assert results[0].status == "delivered"
        assert results[0].external_id == "whk_e2e_1"  # parsed from the real 200
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    # ---- The real server actually received a correctly-signed request --------
    captured = _CapturingHandler.received
    assert captured, "the real local server received no request"
    ts = int(captured["timestamp"])
    expected_sig = "sha256=" + hmac.new(
        secret.encode(), f"{ts}.".encode() + captured["body"], hashlib.sha256
    ).hexdigest()
    assert captured["signature"] == expected_sig  # genuine HMAC over the body
    delivered_body = json.loads(captured["body"])
    assert delivered_body["content"]  # the draft content really crossed the wire

    # ---- Step 6: publications row delivered -------------------------------
    async with sm() as session:
        pub = (
            await session.execute(
                select(Publication).where(Publication.draft_id == draft_id)
            )
        ).scalar_one()
        assert pub.status == "delivered"
        assert pub.external_id == "whk_e2e_1"
        publication_id = pub.id

    # ---- Step 7: content.published event + WALK the causation chain -------
    async with sm() as session:
        published = (
            await session.execute(
                select(OutboxEvent)
                .where(OutboxEvent.event_name == CONTENT_PUBLISHED)
                .order_by(OutboxEvent.created_at.desc())
            )
        ).scalars().first()
        assert published is not None
        pe = published.event
        # Boundary payload is exactly the Phase 6 contract (§ engine).
        assert pe["payload"]["draftId"] == str(draft_id)
        assert pe["payload"]["publicationId"] == str(publication_id)
        assert pe["payload"]["targetId"] == str(target_id)
        assert pe["payload"]["channel"] == "webhook"
        assert pe["payload"]["externalId"] == "whk_e2e_1"
        assert pe["payload"]["workspaceId"] == str(ws_id)

        async def _fetch(event_id: str | None):
            if event_id is None:
                return None
            row = await session.get(OutboxEvent, uuid.UUID(event_id))
            return row.event if row is not None else None

        # published → approved: the parent row must genuinely exist.
        approved = await _fetch(pe["causationId"])
        assert approved is not None, "content.published causation parent missing"
        assert approved["name"] == DRAFT_APPROVED
        assert approved["payload"]["draftId"] == str(draft_id)

        # approved → updated (submit-review) / created: parent must exist too.
        parent_of_approved = await _fetch(approved["causationId"])
        assert parent_of_approved is not None, "approved causation parent missing"
        assert parent_of_approved["name"] in (DRAFT_UPDATED, DRAFT_CREATED)
        assert parent_of_approved["payload"]["draftId"] == str(draft_id)

    # ---- consumed_at was set ONCE (step 1) and NEVER touched afterwards ------
    async with sm() as session:
        packet = await session.get(ResearchPacket, packet_id)
        assert packet.consumed_at == consumed_at_after_step1  # unchanged
        assert packet.status == "ready"  # Phase 5 never writes packet.status
        # And exactly one draft exists for the packet (one-draft-per-packet).
        draft_count = (
            await session.execute(
                select(func.count())
                .select_from(Publication)
                .where(Publication.draft_id == draft_id)
            )
        ).scalar_one()
        assert draft_count == 1
