"""Transparency — publication provenance snapshot ("show your work").

Proves the four mandated guarantees end to end against real Postgres:
  1. publishing snapshots every cited intelligence object's confidence_score /
     epistemic_type / scoring_version at that moment
     (test_publish_snapshots_cited_objects_at_publish_moment)
  2. re-scoring AFTER publication does not change the provenance view — the
     endpoint reads the snapshot, never a live join
     (test_rescore_after_publish_does_not_change_provenance_view)
  3. the serialized response carries no claim or evidence data at ANY depth,
     proven by sentinel strings on real claim/evidence rows plus a recursive
     key walk (test_provenance_response_contains_no_claim_or_evidence_data)
  4. cross-workspace isolation: a foreign workspace's publication provenance
     reads as 404 (test_provenance_cross_workspace_isolation)

Plus the same-transaction guarantee: the snapshot rides the transaction that
creates the pending publication row, so it exists even when delivery FAILS
(test_snapshot_written_even_when_delivery_fails).
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update

pytestmark = pytest.mark.requires_db

CLAIM_SENTINEL = "CLAIM-SENTINEL-must-never-leak-7f3a"
EVIDENCE_SENTINEL = "EVIDENCE-SENTINEL-must-never-leak-9c1b"


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app

    return create_app()


class _DeliverChannel:
    channel_type = "fake"

    def __init__(self) -> None:
        self.publish_calls = 0

    async def validate_credentials(self, credentials):
        return True

    async def health_check(self, credentials):
        return True

    def format_content(self, content, max_length):
        return [content]

    async def publish(self, content, draft_title, credentials, config, citations=None):
        from oryx.services.publishing.channels.base import PublishResult

        self.publish_calls += 1
        return PublishResult(
            external_id="ext-1",
            external_url="https://example.test/post",
            status="delivered",
        )


class _PermanentFailChannel(_DeliverChannel):
    async def publish(self, content, draft_title, credentials, config):
        from oryx.services.publishing.channels.base import PermanentChannelError

        self.publish_calls += 1
        raise PermanentChannelError("bad credentials")


@pytest.fixture
def restore_registry():
    """Snapshot + restore the channel registry around a test."""
    from oryx.services.publishing.channels import registry

    saved = registry.all_channels()
    yield registry
    for key in list(registry.all_channels()):
        if key not in saved:
            del registry._REGISTRY[key]
    for key, adapter in saved.items():
        registry.register_channel(key, adapter)


async def _seed_cited_draft(
    sm,
    *,
    workspace_id: uuid.UUID | None = None,
    account_id: uuid.UUID | None = None,
    with_claims_and_evidence: bool = False,
):
    """account + workspace (or the given ones) + 2 intelligence objects with
    DISTINCT scores/types + approved draft citing both via draft_citations.
    Optionally attaches real claim + evidence rows (sentinel text) behind the
    first object, mirroring the full Phase 4 chain."""
    from oryx.core.models import (
        Account,
        Claim,
        ClaimEvidenceLink,
        ContentDraft,
        DraftCitation,
        DraftVersion,
        Evidence,
        IntakeItem,
        IntakeSource,
        IntelligenceObject,
        ResearchPacket,
        ResearchWorkspace,
        Workspace,
    )

    now = datetime.now(UTC)
    async with sm() as session:
        if account_id is None:
            account = Account(
                id=uuid.uuid4(),
                email=f"prov+{uuid.uuid4().hex[:8]}@oryx.test",
                password_hash="x",
                password_changed_at=now,
                status="active",
            )
            session.add(account)
            await session.flush()
            account_id = account.id
        if workspace_id is None:
            ws = Workspace(id=uuid.uuid4(), name="W", owner_account_id=account_id)
            session.add(ws)
            await session.flush()
            workspace_id = ws.id

        source = IntakeSource(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            kind="rss",
            name="feed",
            enabled=True,
            config={},
            origin_kind="custom",
            status="healthy",
        )
        session.add(source)
        await session.flush()

        # Two objects with deliberately different values so the snapshot
        # assertions cannot pass by accident.
        specs = [
            {"epistemic_type": "fact", "confidence_score": 0.9, "headline": "Acme raised $5B"},
            {"epistemic_type": "claim", "confidence_score": 0.55, "headline": "Rival eyes merger"},
        ]
        obj_ids: list[uuid.UUID] = []
        first_item_id: uuid.UUID | None = None
        for spec in specs:
            item = IntakeItem(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                intake_source_id=source.id,
                provider_name="rss",
                external_id=f"x-{uuid.uuid4().hex[:8]}",
                received_at=now,
                payload={},
                fingerprint=uuid.uuid4().hex,
            )
            session.add(item)
            await session.flush()
            if first_item_id is None:
                first_item_id = item.id
            obj = IntelligenceObject(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                intake_item_id=item.id,
                epistemic_type=spec["epistemic_type"],
                confidence_score=spec["confidence_score"],
                verification_status="verified",
                claim_ids=[],
                conflict_ids=[],
                key_facts={},
                headline=spec["headline"],
                scoring_version=1,
            )
            session.add(obj)
            await session.flush()
            obj_ids.append(obj.id)

        if with_claims_and_evidence:
            claim = Claim(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                intake_item_id=first_item_id,
                text=CLAIM_SENTINEL,
                subject=CLAIM_SENTINEL,
                predicate="says",
                object=CLAIM_SENTINEL,
                epistemic_type="fact",
                extractor_version=1,
            )
            session.add(claim)
            evidence = Evidence(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                intake_item_id=first_item_id,
                evidence_type="corroboration",
                text=EVIDENCE_SENTINEL,
            )
            session.add(evidence)
            await session.flush()
            session.add(
                ClaimEvidenceLink(
                    claim_id=claim.id,
                    evidence_id=evidence.id,
                    relationship="supports",
                    strength=0.8,
                    linker_version=1,
                )
            )
            # Wire the claim into the first object, completing the real chain
            # the boundary must not expose.
            await session.execute(
                update(IntelligenceObject)
                .where(IntelligenceObject.id == obj_ids[0])
                .values(claim_ids=[claim.id])
            )

        rws = ResearchWorkspace(
            id=uuid.uuid4(), account_id=account_id, workspace_id=workspace_id, name="RW"
        )
        session.add(rws)
        await session.flush()
        packet = ResearchPacket(
            id=uuid.uuid4(),
            research_workspace_id=rws.id,
            workspace_id=workspace_id,
            name="P",
            status="consumed",
            intelligence_object_ids=obj_ids,
            conflict_acknowledged_ids=[],
            ready_at=now,
        )
        session.add(packet)
        await session.flush()
        draft = ContentDraft(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            account_id=account_id,
            packet_id=packet.id,
            format="article",
            title="Cited Draft",
            status="approved",
            current_version=1,
            generation_model="claude-sonnet-4-6",
            generation_version=1,
            word_count=3,
        )
        session.add(draft)
        await session.flush()
        session.add(
            DraftVersion(
                id=uuid.uuid4(),
                draft_id=draft.id,
                version_number=1,
                content="The body content.",
                edited_by=account_id,
                is_ai_generated=True,
                word_count=3,
            )
        )
        for obj_id in obj_ids:
            session.add(DraftCitation(draft_id=draft.id, intelligence_object_id=obj_id))
        await session.commit()
        return workspace_id, account_id, draft.id, obj_ids


async def _make_target(sm, *, workspace_id, channel: str, name: str = "T"):
    from oryx.core.credential_crypto import encrypt_credentials
    from oryx.core.models import PublishTarget

    ct, iv = encrypt_credentials({"secret": "s"})
    async with sm() as session:
        target = PublishTarget(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            name=name,
            channel=channel,
            credentials=ct,
            credentials_iv=iv,
            config={},
            is_active=True,
        )
        session.add(target)
        await session.commit()
        return target.id


async def _signup(client: AsyncClient, sm) -> tuple[str, uuid.UUID, uuid.UUID]:
    """Fresh user over HTTP (workspace owner → content.read/write). Returns
    (token, workspace_id, account_id)."""
    from oryx.core.models import Account, WorkspaceMember

    email = f"prov+{uuid.uuid4().hex[:8]}@oryx.test"
    res = await client.post(
        "/v1/auth/signup",
        json={
            "email": email,
            "password": "StrongPass123",
            "displayName": "Prov User",
            "deviceId": str(uuid.uuid4()),
            "deviceLabel": "Pytest",
            "devicePlatform": "ios",
        },
    )
    assert res.status_code == 200, res.text
    token = res.json()["data"]["tokens"]["accessToken"]
    async with sm() as session:
        account = (
            await session.execute(select(Account).where(Account.email == email))
        ).scalar_one()
        member = (
            await session.execute(
                select(WorkspaceMember).where(WorkspaceMember.account_id == account.id)
            )
        ).scalar_one()
        return token, member.workspace_id, account.id


def _walk_keys(node) -> list[str]:
    """Every key at every depth of a decoded JSON payload."""
    keys: list[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            keys.append(k)
            keys.extend(_walk_keys(v))
    elif isinstance(node, list):
        for v in node:
            keys.extend(_walk_keys(v))
    return keys


# --------------------------------------------------------------------------- #
# 1 — snapshot written at publish, values exact
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_publish_snapshots_cited_objects_at_publish_moment(
    sm, restore_registry
) -> None:
    from oryx.core.models import PublicationCitation
    from oryx.services.publishing.engine import PublishingEngine

    restore_registry.register_channel("webhook", _DeliverChannel())
    ws_id, account_id, draft_id, obj_ids = await _seed_cited_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id, channel="webhook")

    res = await PublishingEngine(sm).publish_draft(
        draft_id=draft_id, target_ids=[target_id],
        workspace_id=ws_id, account_id=account_id,
    )
    assert res[0].status == "delivered"
    publication_id = res[0].publication_id

    async with sm() as session:
        rows = (
            await session.execute(
                select(PublicationCitation).where(
                    PublicationCitation.publication_id == publication_id
                )
            )
        ).scalars().all()
    by_obj = {r.intelligence_object_id: r for r in rows}
    assert set(by_obj) == set(obj_ids)  # every cited object, nothing else
    fact = by_obj[obj_ids[0]]
    assert fact.epistemic_type == "fact"
    assert fact.confidence_score == pytest.approx(0.9)
    assert fact.scoring_version == 1
    assert fact.headline == "Acme raised $5B"
    claim = by_obj[obj_ids[1]]
    assert claim.epistemic_type == "claim"
    assert claim.confidence_score == pytest.approx(0.55)
    assert claim.scoring_version == 1


# --------------------------------------------------------------------------- #
# same-transaction guarantee: snapshot exists even when delivery FAILS
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_snapshot_written_even_when_delivery_fails(
    sm, restore_registry
) -> None:
    """The snapshot rides the pending-row transaction, not the delivered step:
    a permanent channel failure still leaves the publication row WITH its full
    snapshot — no publication can exist without one."""
    from sqlalchemy import func

    from oryx.core.models import Publication, PublicationCitation
    from oryx.services.publishing.engine import PublishingEngine

    restore_registry.register_channel("twitter_x", _PermanentFailChannel())
    ws_id, account_id, draft_id, obj_ids = await _seed_cited_draft(sm)
    target_id = await _make_target(sm, workspace_id=ws_id, channel="twitter_x")

    res = await PublishingEngine(sm).publish_draft(
        draft_id=draft_id, target_ids=[target_id],
        workspace_id=ws_id, account_id=account_id,
    )
    assert res[0].status == "failed"

    async with sm() as session:
        pub = (
            await session.execute(
                select(Publication).where(Publication.draft_id == draft_id)
            )
        ).scalar_one()
        assert pub.status == "failed"
        n = (
            await session.execute(
                select(func.count())
                .select_from(PublicationCitation)
                .where(PublicationCitation.publication_id == pub.id)
            )
        ).scalar_one()
        assert n == len(obj_ids)


# --------------------------------------------------------------------------- #
# 2 — re-score after publish: the provenance view must not move
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_rescore_after_publish_does_not_change_provenance_view(
    sm, app, restore_registry
) -> None:
    from oryx.core.models import IntelligenceObject
    from oryx.services.publishing.engine import PublishingEngine

    restore_registry.register_channel("webhook", _DeliverChannel())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, ws_id, account_id = await _signup(client, sm)
        headers = {"Authorization": f"Bearer {token}"}
        _, _, draft_id, obj_ids = await _seed_cited_draft(
            sm, workspace_id=ws_id, account_id=account_id
        )
        target_id = await _make_target(sm, workspace_id=ws_id, channel="webhook")
        res = await PublishingEngine(sm).publish_draft(
            draft_id=draft_id, target_ids=[target_id],
            workspace_id=ws_id, account_id=account_id,
        )
        publication_id = res[0].publication_id

        first = await client.get(
            f"/v1/publications/{publication_id}/provenance", headers=headers
        )
        assert first.status_code == 200, first.text
        before = first.json()["data"]
        assert before["publicationId"] == str(publication_id)
        assert len(before["entries"]) == 2
        # Strongest first: the 0.9 fact leads.
        assert before["entries"][0]["confidenceScore"] == pytest.approx(0.9)
        assert before["entries"][0]["confidenceTier"] == "high"
        assert before["entries"][0]["epistemicType"] == "fact"
        assert before["entries"][0]["scoringVersion"] == 1

        # Re-score EVERY cited object to radically different values — the
        # documented failure mode a live join would exhibit.
        async with sm() as session:
            await session.execute(
                update(IntelligenceObject)
                .where(IntelligenceObject.id.in_(obj_ids))
                .values(
                    confidence_score=0.05,
                    epistemic_type="rumor",
                    scoring_version=2,
                    headline="REWRITTEN AFTER PUBLISH",
                )
            )
            await session.commit()

        second = await client.get(
            f"/v1/publications/{publication_id}/provenance", headers=headers
        )
        assert second.status_code == 200
        after = second.json()["data"]
        # The snapshot is genuinely immutable: byte-for-byte identical payload.
        assert after == before
        assert all(e["headline"] != "REWRITTEN AFTER PUBLISH" for e in after["entries"])
        assert all(e["scoringVersion"] == 1 for e in after["entries"])


# --------------------------------------------------------------------------- #
# 3 — no claim/evidence data at any response depth
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_provenance_response_contains_no_claim_or_evidence_data(
    sm, app, restore_registry
) -> None:
    from oryx.services.publishing.engine import PublishingEngine

    restore_registry.register_channel("webhook", _DeliverChannel())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token, ws_id, account_id = await _signup(client, sm)
        headers = {"Authorization": f"Bearer {token}"}
        # Real claim + evidence rows exist behind the cited object, with
        # sentinel text — the strongest possible leak bait.
        _, _, draft_id, _ = await _seed_cited_draft(
            sm, workspace_id=ws_id, account_id=account_id,
            with_claims_and_evidence=True,
        )
        target_id = await _make_target(sm, workspace_id=ws_id, channel="webhook")
        res = await PublishingEngine(sm).publish_draft(
            draft_id=draft_id, target_ids=[target_id],
            workspace_id=ws_id, account_id=account_id,
        )
        publication_id = res[0].publication_id

        resp = await client.get(
            f"/v1/publications/{publication_id}/provenance", headers=headers
        )
        assert resp.status_code == 200, resp.text
        # Prove the ABSENCE on the raw serialized bytes, not just the schema.
        assert CLAIM_SENTINEL not in resp.text
        assert EVIDENCE_SENTINEL not in resp.text
        # And structurally: no key at ANY depth is claim- or evidence-shaped.
        body = resp.json()
        assert body["data"]["entries"], "expected a non-empty provenance payload"
        for key in _walk_keys(body):
            lowered = key.lower()
            assert "claim" not in lowered, f"claim-shaped key leaked: {key}"
            assert "evidence" not in lowered, f"evidence-shaped key leaked: {key}"


# --------------------------------------------------------------------------- #
# 4 — cross-workspace isolation
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_provenance_cross_workspace_isolation(
    sm, app, restore_registry
) -> None:
    from oryx.services.publishing.engine import PublishingEngine

    restore_registry.register_channel("webhook", _DeliverChannel())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        token_a, ws_a, account_a = await _signup(client, sm)
        token_b, _ws_b, _account_b = await _signup(client, sm)
        _, _, draft_id, _ = await _seed_cited_draft(
            sm, workspace_id=ws_a, account_id=account_a
        )
        target_id = await _make_target(sm, workspace_id=ws_a, channel="webhook")
        res = await PublishingEngine(sm).publish_draft(
            draft_id=draft_id, target_ids=[target_id],
            workspace_id=ws_a, account_id=account_a,
        )
        publication_id = res[0].publication_id

        own = await client.get(
            f"/v1/publications/{publication_id}/provenance",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert own.status_code == 200

        foreign = await client.get(
            f"/v1/publications/{publication_id}/provenance",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert foreign.status_code == 404
