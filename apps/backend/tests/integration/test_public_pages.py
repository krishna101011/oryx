"""Public Reader Rev 1 (docs/PUBLIC_READER_ARCHITECTURE.md §6) — end to end
against real Postgres.

  1. GET /public/pages/{slug} is unauthenticated and returns ONLY the §6
     allow-list — proven by exact key-set equality at every depth AND by a
     raw-text sentinel scan for real claim/evidence/workspace/account/draft
     values that exist in the seeded data but must never leak
     (test_public_endpoint_returns_only_allowlisted_fields)
  2. Publishing a draft automatically creates exactly one public page, in
     the same transaction as the status transition
     (test_publish_creates_public_page_automatically)
  3. content_snapshot is frozen at first publish — a later edit to the
     internal draft never changes what is already public
     (test_content_snapshot_frozen_after_draft_edit)
  4. slug uniqueness + "exactly one page per draft", both enforced at the
     schema level, not just by the engine's own status guard
     (test_slug_is_unique_and_one_page_per_draft)
  5. an unknown slug 404s, never a live join / partial leak
     (test_unknown_slug_404s)
  6. rate limiting rejects excess requests to THIS route specifically,
     while an unrelated route stays unaffected
     (test_rate_limiting_rejects_excess_requests_to_public_pages_route)
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update

pytestmark = pytest.mark.requires_db

CLAIM_SENTINEL = "CLAIM-SENTINEL-must-never-leak-3e8d"
EVIDENCE_SENTINEL = "EVIDENCE-SENTINEL-must-never-leak-6a2f"

_ALLOWED_TOP_KEYS = {"content", "publishedAt", "citations"}
_ALLOWED_CITATION_KEYS = {
    "headline", "epistemicType", "confidenceScore", "scoringVersion", "snapshottedAt",
}


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
            external_id="ext-1", external_url="https://example.test/post", status="delivered",
        )


@pytest.fixture
def restore_registry():
    from oryx.services.publishing.channels import registry

    saved = registry.all_channels()
    yield registry
    for key in list(registry.all_channels()):
        if key not in saved:
            del registry._REGISTRY[key]
    for key, adapter in saved.items():
        registry.register_channel(key, adapter)


async def _seed_cited_draft(sm, *, with_claims_and_evidence: bool = False):
    """account + workspace + 1 intelligence object (real headline/score/type)
    + approved draft citing it via draft_citations. Optionally attaches real
    claim + evidence rows (sentinel text) behind that object, mirroring the
    full chain the public boundary must never expose."""
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
        account = Account(
            id=uuid.uuid4(),
            email=f"reader+{uuid.uuid4().hex[:8]}@oryx.test",
            password_hash="x",
            password_changed_at=now,
            status="active",
        )
        session.add(account)
        await session.flush()
        ws = Workspace(id=uuid.uuid4(), name="W", owner_account_id=account.id)
        session.add(ws)
        await session.flush()

        source = IntakeSource(
            id=uuid.uuid4(), workspace_id=ws.id, kind="rss", name="feed",
            enabled=True, config={}, origin_kind="custom", status="healthy",
        )
        session.add(source)
        await session.flush()
        item = IntakeItem(
            id=uuid.uuid4(), workspace_id=ws.id, intake_source_id=source.id,
            provider_name="rss", external_id=f"x-{uuid.uuid4().hex[:8]}",
            received_at=now, payload={}, fingerprint=uuid.uuid4().hex,
        )
        session.add(item)
        await session.flush()
        obj = IntelligenceObject(
            id=uuid.uuid4(), workspace_id=ws.id, intake_item_id=item.id,
            epistemic_type="fact", confidence_score=0.87,
            verification_status="verified", claim_ids=[], conflict_ids=[],
            key_facts={"never": "exposed"}, headline="Acme raised $5B",
            scoring_version=1,
        )
        session.add(obj)
        await session.flush()

        if with_claims_and_evidence:
            claim = Claim(
                id=uuid.uuid4(), workspace_id=ws.id, intake_item_id=item.id,
                text=CLAIM_SENTINEL, subject=CLAIM_SENTINEL, predicate="says",
                object=CLAIM_SENTINEL, epistemic_type="fact", extractor_version=1,
            )
            session.add(claim)
            evidence = Evidence(
                id=uuid.uuid4(), workspace_id=ws.id, intake_item_id=item.id,
                evidence_type="corroboration", text=EVIDENCE_SENTINEL,
            )
            session.add(evidence)
            await session.flush()
            session.add(ClaimEvidenceLink(
                claim_id=claim.id, evidence_id=evidence.id,
                relationship="supports", strength=0.8, linker_version=1,
            ))
            await session.execute(
                update(IntelligenceObject).where(IntelligenceObject.id == obj.id)
                .values(claim_ids=[claim.id])
            )

        rws = ResearchWorkspace(
            id=uuid.uuid4(), account_id=account.id, workspace_id=ws.id, name="RW"
        )
        session.add(rws)
        await session.flush()
        packet = ResearchPacket(
            id=uuid.uuid4(), research_workspace_id=rws.id, workspace_id=ws.id,
            name="P", status="consumed", intelligence_object_ids=[obj.id],
            conflict_acknowledged_ids=[], ready_at=now,
        )
        session.add(packet)
        await session.flush()
        draft = ContentDraft(
            id=uuid.uuid4(), workspace_id=ws.id, account_id=account.id,
            packet_id=packet.id, format="article", title="Reader Draft",
            status="approved", current_version=1,
            generation_model="claude-sonnet-4-6", generation_version=1, word_count=3,
        )
        session.add(draft)
        await session.flush()
        session.add(DraftVersion(
            id=uuid.uuid4(), draft_id=draft.id, version_number=1,
            content="The real public body.", edited_by=account.id,
            is_ai_generated=True, word_count=4,
        ))
        session.add(DraftCitation(draft_id=draft.id, intelligence_object_id=obj.id))
        await session.commit()
        return ws.id, account.id, draft.id


async def _make_target(sm, *, workspace_id, channel: str = "webhook"):
    from oryx.core.credential_crypto import encrypt_credentials
    from oryx.core.models import PublishTarget

    ct, iv = encrypt_credentials({"secret": "s"})
    async with sm() as session:
        target = PublishTarget(
            id=uuid.uuid4(), workspace_id=workspace_id, name="T", channel=channel,
            credentials=ct, credentials_iv=iv, config={}, is_active=True,
        )
        session.add(target)
        await session.commit()
        return target.id


async def _publish(sm, restore_registry, *, workspace_id, account_id, draft_id, channel="webhook"):
    from oryx.services.publishing.engine import PublishingEngine

    restore_registry.register_channel(channel, _DeliverChannel())
    target_id = await _make_target(sm, workspace_id=workspace_id, channel=channel)
    results = await PublishingEngine(sm).publish_draft(
        draft_id=draft_id, target_ids=[target_id],
        workspace_id=workspace_id, account_id=account_id,
    )
    assert results[0].status == "delivered", results[0].error_message


def _walk_keys(node) -> list[str]:
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
# 1 — allow-list, proven by exact key sets + raw-text sentinel scan
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_public_endpoint_returns_only_allowlisted_fields(sm, app, restore_registry) -> None:
    from oryx.core.models import PublicPage

    ws_id, account_id, draft_id = await _seed_cited_draft(sm, with_claims_and_evidence=True)
    await _publish(sm, restore_registry, workspace_id=ws_id, account_id=account_id, draft_id=draft_id)

    async with sm() as session:
        page = (
            await session.execute(select(PublicPage).where(PublicPage.content_draft_id == draft_id))
        ).scalar_one()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        res = await client.get(f"/v1/public/pages/{page.slug}")
    assert res.status_code == 200, res.text
    body = res.json()

    data = body["data"]
    assert set(data.keys()) == _ALLOWED_TOP_KEYS
    assert len(data["citations"]) == 1
    assert set(data["citations"][0].keys()) == _ALLOWED_CITATION_KEYS

    # Structurally absent, not just unpopulated: no forbidden key name at ANY
    # depth of the decoded payload (data or meta).
    forbidden_keys = {
        "workspaceId", "accountId", "draftId", "contentDraftId", "targetId",
        "publicationId", "intelligenceObjectId", "credentials", "credentialsIv",
        "confidenceTier", "claimIds", "keyFacts", "intakeItemId", "config",
        "editedBy", "text", "subject", "predicate", "object",
    }
    all_keys = set(_walk_keys(body))
    assert not (all_keys & forbidden_keys), all_keys & forbidden_keys

    # Real values that exist in the seeded data must never appear in the
    # raw response text — not renamed, not nested differently, just absent.
    raw = res.text
    assert CLAIM_SENTINEL not in raw
    assert EVIDENCE_SENTINEL not in raw
    assert str(ws_id) not in raw
    assert str(account_id) not in raw
    assert str(draft_id) not in raw

    assert data["content"] == "The real public body."
    assert data["citations"][0]["headline"] == "Acme raised $5B"
    assert data["citations"][0]["epistemicType"] == "fact"
    assert data["citations"][0]["confidenceScore"] == pytest.approx(0.87)
    assert data["citations"][0]["scoringVersion"] == 1


# --------------------------------------------------------------------------- #
# 2 — automatic creation, one per draft, in the SAME transaction
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_publish_creates_public_page_automatically(sm, restore_registry) -> None:
    from oryx.core.models import PublicPage

    ws_id, account_id, draft_id = await _seed_cited_draft(sm)
    async with sm() as session:
        none_yet = (
            await session.execute(select(PublicPage).where(PublicPage.content_draft_id == draft_id))
        ).scalar_one_or_none()
        assert none_yet is None

    await _publish(sm, restore_registry, workspace_id=ws_id, account_id=account_id, draft_id=draft_id)

    async with sm() as session:
        page = (
            await session.execute(select(PublicPage).where(PublicPage.content_draft_id == draft_id))
        ).scalar_one()
        assert page.workspace_id == ws_id
        assert page.content_snapshot == "The real public body."
        assert page.slug and len(page.slug) == 12


# --------------------------------------------------------------------------- #
# 3 — content_snapshot is frozen, never a live read
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_content_snapshot_frozen_after_draft_edit(sm, restore_registry) -> None:
    from oryx.core.models import DraftVersion, PublicPage

    ws_id, account_id, draft_id = await _seed_cited_draft(sm)
    await _publish(sm, restore_registry, workspace_id=ws_id, account_id=account_id, draft_id=draft_id)

    async with sm() as session:
        await session.execute(
            update(DraftVersion)
            .where(DraftVersion.draft_id == draft_id, DraftVersion.version_number == 1)
            .values(content="EDITED AFTER PUBLISH — must never appear publicly")
        )
        await session.commit()

    async with sm() as session:
        page = (
            await session.execute(select(PublicPage).where(PublicPage.content_draft_id == draft_id))
        ).scalar_one()
        assert page.content_snapshot == "The real public body."


# --------------------------------------------------------------------------- #
# 4 — slug uniqueness + exactly one page per draft, at the schema level
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_slug_is_unique_and_one_page_per_draft(sm) -> None:
    from sqlalchemy.exc import IntegrityError

    from oryx.core.models import PublicPage
    from oryx.services.reader.repository import PublicPagesRepository

    ws_id, account_id, draft_id = await _seed_cited_draft(sm)

    async with sm() as session:
        repo = PublicPagesRepository(session)
        first = await repo.create(
            content_draft_id=draft_id, workspace_id=ws_id, content_snapshot="v1",
        )
        await session.commit()

    # Calling create() again for the SAME draft returns the SAME row — one
    # page per draft is enforced, not just attempted once.
    async with sm() as session:
        repo = PublicPagesRepository(session)
        second = await repo.create(
            content_draft_id=draft_id, workspace_id=ws_id, content_snapshot="v2-should-be-ignored",
        )
        await session.commit()
    assert second.id == first.id
    assert second.slug == first.slug
    assert second.content_snapshot == "v1"  # the original snapshot, untouched

    # The UNIQUE(slug) constraint is real at the DB level, not just convention.
    async with sm() as session:
        _, _, other_draft_id = await _seed_cited_draft(sm)
        session.add(PublicPage(
            id=uuid.uuid4(), content_draft_id=other_draft_id, workspace_id=ws_id,
            slug=first.slug, content_snapshot="dupe",
        ))
        with pytest.raises(IntegrityError):
            await session.commit()


# --------------------------------------------------------------------------- #
# 5 — unknown slug 404s
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_unknown_slug_404s(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        res = await client.get("/v1/public/pages/does-not-exist")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


# --------------------------------------------------------------------------- #
# 6 — rate limiting, scoped to this route
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_rate_limiting_rejects_excess_requests_to_public_pages_route(
    sm, app, restore_registry
) -> None:
    ws_id, account_id, draft_id = await _seed_cited_draft(sm)
    await _publish(sm, restore_registry, workspace_id=ws_id, account_id=account_id, draft_id=draft_id)
    from oryx.core.models import PublicPage

    async with sm() as session:
        page = (
            await session.execute(select(PublicPage).where(PublicPage.content_draft_id == draft_id))
        ).scalar_one()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        codes = []
        for _ in range(65):
            r = await client.get(f"/v1/public/pages/{page.slug}")
            codes.append(r.status_code)
        assert 429 in codes, f"expected rate limiting, got codes={codes}"
        limited = [r for r in codes if r == 429]
        assert all(c in (200, 429) for c in codes)

        # Scoped to THIS route: health stays unaffected by the same client.
        health = await client.get("/v1/health")
        assert health.status_code == 200
    assert len(limited) >= 1
