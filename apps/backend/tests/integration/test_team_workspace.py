"""Team/Workspace Rev 2 — real, live multi-member tests. WorkspaceMember/
role infrastructure has existed since Phase 2 but has never been exercised
beyond a single owner-only shape (recon: 278/278 real rows were role='owner',
zero invited_by, zero removed_at, zero accounts with >1 membership). Every
test here proves a real multi-member scenario actually works end-to-end
over real HTTP against the real DB — not a code-review claim.
"""
from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db


@pytest.fixture
def app():
    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app

    return create_app()


async def _signed_up_client(app, email: str | None = None) -> tuple[AsyncClient, dict]:
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://t")
    body = {
        "email": email or f"team+{uuid.uuid4().hex[:8]}@oryx.test",
        "password": "StrongPass123",
        "displayName": "Team Test",
        "deviceId": str(uuid.uuid4()),
        "deviceLabel": "Pytest Device",
        "devicePlatform": "ios",
    }
    res = await client.post("/v1/auth/signup", json=body)
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    client.headers["Authorization"] = f"Bearer {data['tokens']['accessToken']}"
    me = await client.get("/v1/auth/me")
    assert me.status_code == 200, me.text
    me_data = me.json()["data"]
    return client, {
        "email": body["email"],
        "device_id": body["deviceId"],
        "account_id": me_data["account"]["id"],
        "workspace_id": me_data["workspace"]["id"],
        "refresh_token": data["tokens"]["refreshToken"],
    }


async def _seed_invite(workspace_id: str, invited_email: str, role: str, invited_by: str):
    """Bypasses the HTTP creation endpoint only to get a deterministic raw
    token back — LogOnlyEmailProvider (the real dev default) doesn't log the
    token anywhere retrievable, exactly as a real email provider wouldn't
    hand it back either. The HTTP creation path itself is tested separately
    in test_create_invite_via_http_returns_real_fields_and_validates."""
    from oryx.core.db import get_sessionmaker
    from oryx.services.workspaces.repository import WorkspaceRepository

    sm = get_sessionmaker()
    async with sm() as session:
        repo = WorkspaceRepository(session)
        invite, raw_token = await repo.create_invite(
            workspace_id=uuid.UUID(workspace_id),
            invited_email=invited_email,
            role=role,
            invited_by=uuid.UUID(invited_by),
        )
        await session.commit()
        return str(invite.id), raw_token


async def test_create_invite_via_http_returns_real_fields_and_validates(app) -> None:
    owner, ctx = await _signed_up_client(app)
    invited_email = f"invitee+{uuid.uuid4().hex[:8]}@oryx.test"

    res = await owner.post(
        "/v1/workspaces/invites", json={"email": invited_email, "role": "editor"}
    )
    assert res.status_code == 200, res.text
    invite = res.json()["data"]
    assert invite["invitedEmail"] == invited_email
    assert invite["role"] == "editor"
    assert invite["acceptedAt"] is None
    assert invite["revokedAt"] is None
    assert "tokenHash" not in invite and "token_hash" not in invite

    # Duplicate pending invite for the same email is rejected.
    dup = await owner.post(
        "/v1/workspaces/invites", json={"email": invited_email, "role": "reader"}
    )
    assert dup.status_code == 422, dup.text

    # Inviting the owner's own email (already an active member) is rejected.
    self_invite = await owner.post(
        "/v1/workspaces/invites", json={"email": ctx["email"], "role": "reader"}
    )
    assert self_invite.status_code == 422, self_invite.text


async def test_invite_rejects_owner_role_at_the_type_level(app) -> None:
    owner, _ctx = await _signed_up_client(app)
    res = await owner.post(
        "/v1/workspaces/invites",
        json={"email": f"x+{uuid.uuid4().hex[:8]}@oryx.test", "role": "owner"},
    )
    assert res.status_code == 422, res.text


async def test_reader_cannot_create_invites_but_owner_can(app) -> None:
    """Real non-owner role enforcement: a reader invited into the workspace
    and switched into it cannot hit a workspace.manage-gated route."""
    owner, owner_ctx = await _signed_up_client(app)
    reader, reader_ctx = await _signed_up_client(app)

    invite_id, raw_token = await _seed_invite(
        owner_ctx["workspace_id"], reader_ctx["email"], "reader", owner_ctx["account_id"]
    )
    accept = await reader.post(f"/v1/workspaces/invites/{raw_token}/accept")
    assert accept.status_code == 200, accept.text

    switch = await reader.post(
        "/v1/auth/switch-workspace",
        json={
            "refreshToken": reader_ctx["refresh_token"],
            "deviceId": reader_ctx["device_id"],
            "workspaceId": owner_ctx["workspace_id"],
        },
    )
    assert switch.status_code == 200, switch.text
    reader.headers["Authorization"] = f"Bearer {switch.json()['data']['accessToken']}"

    # Read-only access works for a reader.
    current = await reader.get("/v1/workspaces/current")
    assert current.status_code == 200, current.text
    assert current.json()["data"]["role"] == "reader"

    # workspace.manage-gated actions are real-rejected for a reader.
    denied = await reader.post(
        "/v1/workspaces/invites",
        json={"email": f"y+{uuid.uuid4().hex[:8]}@oryx.test", "role": "editor"},
    )
    assert denied.status_code == 403, denied.text

    # The owner (same workspace) can do it.
    allowed = await owner.post(
        "/v1/workspaces/invites",
        json={"email": f"z+{uuid.uuid4().hex[:8]}@oryx.test", "role": "editor"},
    )
    assert allowed.status_code == 200, allowed.text


async def test_view_invite_is_lightly_authenticated_not_membership_gated(app) -> None:
    owner, owner_ctx = await _signed_up_client(app)
    invitee, invitee_ctx = await _signed_up_client(app)

    _invite_id, raw_token = await _seed_invite(
        owner_ctx["workspace_id"], invitee_ctx["email"], "editor", owner_ctx["account_id"]
    )
    # invitee is authenticated but is NOT yet (and may never become) a member
    # of owner's workspace — viewing must still work.
    view = await invitee.get(f"/v1/workspaces/invites/{raw_token}")
    assert view.status_code == 200, view.text
    assert view.json()["data"]["role"] == "editor"

    unknown = await invitee.get("/v1/workspaces/invites/not-a-real-token")
    assert unknown.status_code == 404, unknown.text


async def test_accept_creates_real_membership_and_lists_correctly(app) -> None:
    owner, owner_ctx = await _signed_up_client(app)
    invitee, invitee_ctx = await _signed_up_client(app)

    _invite_id, raw_token = await _seed_invite(
        owner_ctx["workspace_id"], invitee_ctx["email"], "admin", owner_ctx["account_id"]
    )
    accept = await invitee.post(f"/v1/workspaces/invites/{raw_token}/accept")
    assert accept.status_code == 200, accept.text
    result = accept.json()["data"]
    assert result["workspaceId"] == owner_ctx["workspace_id"]
    assert result["role"] == "admin"

    # The invitee's OWN /workspaces list now includes the workspace they
    # just joined, alongside their own personal one.
    listed = await invitee.get("/v1/workspaces")
    assert listed.status_code == 200, listed.text
    workspace_ids = {w["id"] for w in listed.json()["data"]["workspaces"]}
    assert owner_ctx["workspace_id"] in workspace_ids
    assert invitee_ctx["workspace_id"] in workspace_ids

    # The owner's member list now shows 2 real active members.
    members = await owner.get("/v1/workspaces/members")
    assert members.status_code == 200, members.text
    member_ids = {m["accountId"] for m in members.json()["data"]}
    assert member_ids == {owner_ctx["account_id"], invitee_ctx["account_id"]}


async def test_accept_email_mismatch_is_rejected(app) -> None:
    owner, owner_ctx = await _signed_up_client(app)
    wrong_person, _wrong_ctx = await _signed_up_client(app)
    intended_email = f"intended+{uuid.uuid4().hex[:8]}@oryx.test"

    _invite_id, raw_token = await _seed_invite(
        owner_ctx["workspace_id"], intended_email, "reader", owner_ctx["account_id"]
    )
    res = await wrong_person.post(f"/v1/workspaces/invites/{raw_token}/accept")
    assert res.status_code == 403, res.text
    assert res.json()["error"]["code"] == "INVITE_EMAIL_MISMATCH"


async def test_expired_invite_cannot_be_accepted(app) -> None:
    from datetime import UTC, datetime, timedelta

    from oryx.core.db import get_sessionmaker
    from oryx.services.workspaces.repository import WorkspaceRepository

    owner, owner_ctx = await _signed_up_client(app)
    invitee, invitee_ctx = await _signed_up_client(app)

    sm = get_sessionmaker()
    async with sm() as session:
        repo = WorkspaceRepository(session)
        invite, raw_token = await repo.create_invite(
            workspace_id=uuid.UUID(owner_ctx["workspace_id"]),
            invited_email=invitee_ctx["email"],
            role="reader",
            invited_by=uuid.UUID(owner_ctx["account_id"]),
        )
        invite.expires_at = datetime.now(UTC) - timedelta(days=1)
        await session.commit()

    res = await invitee.post(f"/v1/workspaces/invites/{raw_token}/accept")
    assert res.status_code == 410, res.text
    assert res.json()["error"]["code"] == "INVITE_INVALID"


async def test_concurrent_accept_invite_race_exactly_one_wins(app) -> None:
    """The real race: two concurrent accept attempts on the SAME token.
    Proves the atomic UPDATE ... WHERE accepted_at IS NULL compare-and-swap,
    not just that it reads correctly in isolation."""
    from oryx.core.db import get_sessionmaker
    from oryx.core.models import WorkspaceMember

    owner, owner_ctx = await _signed_up_client(app)
    invitee, invitee_ctx = await _signed_up_client(app)

    _invite_id, raw_token = await _seed_invite(
        owner_ctx["workspace_id"], invitee_ctx["email"], "editor", owner_ctx["account_id"]
    )

    client_a = AsyncClient(transport=ASGITransport(app=app), base_url="http://t")
    client_b = AsyncClient(transport=ASGITransport(app=app), base_url="http://t")
    client_a.headers["Authorization"] = invitee.headers["Authorization"]
    client_b.headers["Authorization"] = invitee.headers["Authorization"]

    results = await asyncio.gather(
        client_a.post(f"/v1/workspaces/invites/{raw_token}/accept"),
        client_b.post(f"/v1/workspaces/invites/{raw_token}/accept"),
    )
    statuses = sorted(r.status_code for r in results)
    assert statuses == [200, 410], (
        f"expected exactly one winner (200) and one loser (410 INVITE_INVALID), "
        f"got {statuses}"
    )
    loser = results[0] if results[0].status_code == 410 else results[1]
    assert loser.json()["error"]["code"] == "INVITE_INVALID"

    # Real DB proof: exactly one active WorkspaceMember row, not zero, not two.
    sm = get_sessionmaker()
    from sqlalchemy import select

    async with sm() as session:
        result = await session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == uuid.UUID(owner_ctx["workspace_id"]),
                WorkspaceMember.account_id == uuid.UUID(invitee_ctx["account_id"]),
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].removed_at is None
        assert rows[0].role == "editor"


async def test_removed_member_next_request_fails_immediately(app) -> None:
    """The live proof of Rev 2's own claim: get_active_workspace re-checks
    membership on every request, so removal is instant at the workspace-
    access level — even on a still-unexpired access token."""
    owner, owner_ctx = await _signed_up_client(app)
    member, member_ctx = await _signed_up_client(app)

    _invite_id, raw_token = await _seed_invite(
        owner_ctx["workspace_id"], member_ctx["email"], "editor", owner_ctx["account_id"]
    )
    accept = await member.post(f"/v1/workspaces/invites/{raw_token}/accept")
    assert accept.status_code == 200, accept.text

    switch = await member.post(
        "/v1/auth/switch-workspace",
        json={
            "refreshToken": member_ctx["refresh_token"],
            "deviceId": member_ctx["device_id"],
            "workspaceId": owner_ctx["workspace_id"],
        },
    )
    assert switch.status_code == 200, switch.text
    still_valid_token = switch.json()["data"]["accessToken"]
    member.headers["Authorization"] = f"Bearer {still_valid_token}"

    # Confirm access works before removal.
    before = await member.get("/v1/workspaces/current")
    assert before.status_code == 200, before.text

    remove = await owner.delete(f"/v1/workspaces/members/{member_ctx['account_id']}")
    assert remove.status_code == 200, remove.text

    # THE SAME still-unexpired access token, immediately after removal.
    after = await member.get("/v1/workspaces/current")
    assert after.status_code == 404, after.text
    assert after.json()["error"]["code"] == "WORKSPACE_NOT_FOUND"

    # /auth/me also re-checks membership — same real instant cutoff.
    me_after = await member.get("/v1/auth/me")
    assert me_after.status_code == 404, me_after.text


async def test_owner_cannot_be_removed(app) -> None:
    owner, owner_ctx = await _signed_up_client(app)
    admin, admin_ctx = await _signed_up_client(app)

    _invite_id, raw_token = await _seed_invite(
        owner_ctx["workspace_id"], admin_ctx["email"], "admin", owner_ctx["account_id"]
    )
    accept = await admin.post(f"/v1/workspaces/invites/{raw_token}/accept")
    assert accept.status_code == 200, accept.text

    switch = await admin.post(
        "/v1/auth/switch-workspace",
        json={
            "refreshToken": admin_ctx["refresh_token"],
            "deviceId": admin_ctx["device_id"],
            "workspaceId": owner_ctx["workspace_id"],
        },
    )
    assert switch.status_code == 200, switch.text
    admin.headers["Authorization"] = f"Bearer {switch.json()['data']['accessToken']}"

    # Even an admin (workspace.manage-capable) cannot remove the owner.
    res = await admin.delete(f"/v1/workspaces/members/{owner_ctx['account_id']}")
    assert res.status_code == 422, res.text


async def test_workspace_switch_persists_across_token_refresh(app) -> None:
    """The real §5.1 fix: refresh() must inherit the session's own
    workspace_id, not silently revert to _primary_workspace_id's pick."""
    owner, owner_ctx = await _signed_up_client(app)
    member, member_ctx = await _signed_up_client(app)

    _invite_id, raw_token = await _seed_invite(
        owner_ctx["workspace_id"], member_ctx["email"], "editor", owner_ctx["account_id"]
    )
    assert (await member.post(f"/v1/workspaces/invites/{raw_token}/accept")).status_code == 200

    switch = await member.post(
        "/v1/auth/switch-workspace",
        json={
            "refreshToken": member_ctx["refresh_token"],
            "deviceId": member_ctx["device_id"],
            "workspaceId": owner_ctx["workspace_id"],
        },
    )
    assert switch.status_code == 200, switch.text
    switched_refresh = switch.json()["data"]["refreshToken"]

    # A plain refresh (not a switch) using the NEW refresh token must keep
    # the workspace scoped to owner_ctx's workspace, not member's original
    # (earlier-joined) personal workspace.
    refreshed = await member.post(
        "/v1/auth/refresh",
        json={"refreshToken": switched_refresh, "deviceId": member_ctx["device_id"]},
    )
    assert refreshed.status_code == 200, refreshed.text
    member.headers["Authorization"] = f"Bearer {refreshed.json()['data']['accessToken']}"

    current = await member.get("/v1/workspaces/current")
    assert current.status_code == 200, current.text
    assert current.json()["data"]["id"] == owner_ctx["workspace_id"]
    assert current.json()["data"]["role"] == "editor"


async def test_switch_workspace_rejects_a_workspace_the_account_does_not_belong_to(app) -> None:
    _owner, owner_ctx = await _signed_up_client(app)
    stranger, stranger_ctx = await _signed_up_client(app)

    res = await stranger.post(
        "/v1/auth/switch-workspace",
        json={
            "refreshToken": stranger_ctx["refresh_token"],
            "deviceId": stranger_ctx["device_id"],
            "workspaceId": owner_ctx["workspace_id"],
        },
    )
    assert res.status_code == 404, res.text

    # The stranger's original refresh token must still work (switch validated
    # membership BEFORE revoking anything).
    still_good = await stranger.post(
        "/v1/auth/refresh",
        json={
            "refreshToken": stranger_ctx["refresh_token"],
            "deviceId": stranger_ctx["device_id"],
        },
    )
    assert still_good.status_code == 200, still_good.text


async def test_rename_workspace_requires_capability(app) -> None:
    """The doc §5.3 fix: PATCH /current previously had no capability gate at
    all ("currently safe only by accident")."""
    owner, owner_ctx = await _signed_up_client(app)
    reader, reader_ctx = await _signed_up_client(app)

    _invite_id, raw_token = await _seed_invite(
        owner_ctx["workspace_id"], reader_ctx["email"], "reader", owner_ctx["account_id"]
    )
    assert (await reader.post(f"/v1/workspaces/invites/{raw_token}/accept")).status_code == 200
    switch = await reader.post(
        "/v1/auth/switch-workspace",
        json={
            "refreshToken": reader_ctx["refresh_token"],
            "deviceId": reader_ctx["device_id"],
            "workspaceId": owner_ctx["workspace_id"],
        },
    )
    reader.headers["Authorization"] = f"Bearer {switch.json()['data']['accessToken']}"

    denied = await reader.patch("/v1/workspaces/current", json={"name": "Hijacked"})
    assert denied.status_code == 403, denied.text

    allowed = await owner.patch("/v1/workspaces/current", json={"name": "Renamed Real Team"})
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["data"]["name"] == "Renamed Real Team"


async def test_list_invites_shows_pending_and_excludes_revoked_and_accepted(app) -> None:
    owner, owner_ctx = await _signed_up_client(app)
    invitee, invitee_ctx = await _signed_up_client(app)

    pending_email = f"pending+{uuid.uuid4().hex[:8]}@oryx.test"
    _pending_id, _pending_token = await _seed_invite(
        owner_ctx["workspace_id"], pending_email, "reader", owner_ctx["account_id"]
    )

    revoked_id, _revoked_token = await _seed_invite(
        owner_ctx["workspace_id"],
        f"revoked+{uuid.uuid4().hex[:8]}@oryx.test",
        "editor",
        owner_ctx["account_id"],
    )
    revoke = await owner.post(f"/v1/workspaces/invites/{revoked_id}/revoke")
    assert revoke.status_code == 200, revoke.text

    _accepted_id, accepted_token = await _seed_invite(
        owner_ctx["workspace_id"], invitee_ctx["email"], "admin", owner_ctx["account_id"]
    )
    accept = await invitee.post(f"/v1/workspaces/invites/{accepted_token}/accept")
    assert accept.status_code == 200, accept.text

    listed = await owner.get("/v1/workspaces/invites")
    assert listed.status_code == 200, listed.text
    invites = listed.json()["data"]["invites"]
    emails = {i["invitedEmail"] for i in invites}
    assert emails == {pending_email}


async def test_reader_cannot_list_invites(app) -> None:
    owner, owner_ctx = await _signed_up_client(app)
    reader, reader_ctx = await _signed_up_client(app)

    _invite_id, raw_token = await _seed_invite(
        owner_ctx["workspace_id"], reader_ctx["email"], "reader", owner_ctx["account_id"]
    )
    assert (await reader.post(f"/v1/workspaces/invites/{raw_token}/accept")).status_code == 200
    switch = await reader.post(
        "/v1/auth/switch-workspace",
        json={
            "refreshToken": reader_ctx["refresh_token"],
            "deviceId": reader_ctx["device_id"],
            "workspaceId": owner_ctx["workspace_id"],
        },
    )
    reader.headers["Authorization"] = f"Bearer {switch.json()['data']['accessToken']}"

    denied = await reader.get("/v1/workspaces/invites")
    assert denied.status_code == 403, denied.text


async def test_revoke_invite_prevents_later_acceptance(app) -> None:
    owner, owner_ctx = await _signed_up_client(app)
    invitee, invitee_ctx = await _signed_up_client(app)

    invite_id, raw_token = await _seed_invite(
        owner_ctx["workspace_id"], invitee_ctx["email"], "reader", owner_ctx["account_id"]
    )
    revoke = await owner.post(f"/v1/workspaces/invites/{invite_id}/revoke")
    assert revoke.status_code == 200, revoke.text

    accept = await invitee.post(f"/v1/workspaces/invites/{raw_token}/accept")
    assert accept.status_code == 410, accept.text
    assert accept.json()["error"]["code"] == "INVITE_INVALID"


# ============================================================================
# Team nav promotion wave — GET /workspaces/activity, the real event data
# behind the new top-level Team section's Activity view.
# ============================================================================


async def test_activity_records_invited_joined_and_removed_in_order(app) -> None:
    owner, owner_ctx = await _signed_up_client(app)
    never_accepts, never_accepts_ctx = await _signed_up_client(app)
    joiner, joiner_ctx = await _signed_up_client(app)

    # 1. A real HTTP invite that is never accepted — proves member_invited is
    # recorded on the real create-invite path, not just the repository seed
    # helper other tests in this file use.
    invite = await owner.post(
        "/v1/workspaces/invites", json={"email": never_accepts_ctx["email"], "role": "editor"}
    )
    assert invite.status_code == 200, invite.text

    # 2. A second invite, accepted — proves member_joined.
    _invite_id, raw_token = await _seed_invite(
        owner_ctx["workspace_id"], joiner_ctx["email"], "editor", owner_ctx["account_id"]
    )
    accept = await joiner.post(f"/v1/workspaces/invites/{raw_token}/accept")
    assert accept.status_code == 200, accept.text

    # 3. Removing the just-joined member — proves member_removed.
    remove = await owner.delete(f"/v1/workspaces/members/{joiner_ctx['account_id']}")
    assert remove.status_code == 200, remove.text

    activity = await owner.get("/v1/workspaces/activity")
    assert activity.status_code == 200, activity.text
    events = activity.json()["data"]["events"]

    # Most-recent-first: removed, joined, invited.
    kinds = [e["event"] for e in events]
    assert kinds[:3] == ["member_removed", "member_joined", "member_invited"]

    removed_event = events[0]
    assert removed_event["actorAccountId"] == owner_ctx["account_id"]
    assert removed_event["subjectAccountId"] == joiner_ctx["account_id"]
    assert removed_event["role"] == "editor"

    joined_event = events[1]
    assert joined_event["actorAccountId"] == joiner_ctx["account_id"]
    assert joined_event["subjectAccountId"] == joiner_ctx["account_id"]
    assert joined_event["role"] == "editor"

    invited_event = events[2]
    assert invited_event["actorAccountId"] == owner_ctx["account_id"]
    assert invited_event["subjectAccountId"] is None
    assert invited_event["subjectEmail"] == never_accepts_ctx["email"]
    assert invited_event["role"] == "editor"


async def test_reader_can_read_activity_but_not_manage_gated(app) -> None:
    """Same access level as the Members list: activity is member-visible,
    not workspace.manage-gated."""
    owner, owner_ctx = await _signed_up_client(app)
    reader, reader_ctx = await _signed_up_client(app)

    invite_id, raw_token = await _seed_invite(
        owner_ctx["workspace_id"], reader_ctx["email"], "reader", owner_ctx["account_id"]
    )
    assert (await reader.post(f"/v1/workspaces/invites/{raw_token}/accept")).status_code == 200
    switch = await reader.post(
        "/v1/auth/switch-workspace",
        json={
            "refreshToken": reader_ctx["refresh_token"],
            "deviceId": reader_ctx["device_id"],
            "workspaceId": owner_ctx["workspace_id"],
        },
    )
    assert switch.status_code == 200, switch.text
    reader.headers["Authorization"] = f"Bearer {switch.json()['data']['accessToken']}"

    activity = await reader.get("/v1/workspaces/activity")
    assert activity.status_code == 200, activity.text
    # _seed_invite bypasses the HTTP create-invite endpoint (see its own
    # docstring), so it never records member_invited itself — only proving
    # that member_joined (recorded by the real accept endpoint above) is
    # visible to a plain reader, same access level as GET /workspaces/members.
    kinds = {e["event"] for e in activity.json()["data"]["events"]}
    assert "member_joined" in kinds
    assert invite_id
