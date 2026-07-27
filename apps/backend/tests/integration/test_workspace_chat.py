"""Team Chat foundation wave — a single workspace-wide channel.

Real, live HTTP tests over the real DB (same shape as test_team_workspace.py):
send/fetch, genuine cursor pagination (a second poll returns only new
messages, not the whole history again — the thing recon flagged
WorkspaceAuditLog's unpaginated "latest 50" as unfit for), sender-restricted
edit/delete with soft-delete redaction, and the last-read marker. The
notification-dispatch side (CHAT_MESSAGE_SENT routing through the real
NotificationDispatcher) is covered separately in
test_notification_dispatcher.py, following that file's existing
construct-a-DomainEvent-and-call-the-handler-directly convention.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

pytestmark = pytest.mark.requires_db


@pytest.fixture
def app():
    import os

    os.environ.setdefault("DATABASE_URL", os.environ["ORYX_TEST_DB"])
    from oryx.main import create_app

    return create_app()


async def _signed_up_client(app, email: str | None = None) -> tuple[AsyncClient, dict]:
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://t")
    body = {
        "email": email or f"chat+{uuid.uuid4().hex[:8]}@oryx.test",
        "password": "StrongPass123",
        "displayName": "Chat Test",
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


async def _add_member(app, owner_ctx: dict, *, role: str) -> tuple[AsyncClient, dict]:
    """A second real member of owner_ctx's workspace, via the real invite +
    accept HTTP flow (same pattern test_team_workspace.py uses) — and then
    SWITCHED into that workspace, since accepting an invite alone does not
    change the account's active workspace (its access token still carries
    its own personal workspace until a real switch-workspace call)."""
    invited_email = f"chatmember+{uuid.uuid4().hex[:8]}@oryx.test"
    _invite_id, raw_token = await _seed_invite(
        owner_ctx["workspace_id"], invited_email, role, owner_ctx["account_id"]
    )
    member, member_ctx = await _signed_up_client(app, email=invited_email)
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
    member.headers["Authorization"] = f"Bearer {switch.json()['data']['accessToken']}"
    return member, member_ctx


async def test_send_and_fetch_messages_via_http(app) -> None:
    owner, ctx = await _signed_up_client(app)

    sent = await owner.post("/v1/workspaces/messages", json={"body": "hello team"})
    assert sent.status_code == 200, sent.text
    msg = sent.json()["data"]
    assert msg["body"] == "hello team"
    assert msg["senderAccountId"] == ctx["account_id"]
    assert msg["workspaceId"] == ctx["workspace_id"]
    assert msg["editedAt"] is None
    assert msg["deletedAt"] is None

    fetched = await owner.get("/v1/workspaces/messages")
    assert fetched.status_code == 200, fetched.text
    body = fetched.json()
    assert [m["body"] for m in body["data"]] == ["hello team"]
    assert body["meta"]["pagination"]["nextCursor"] is not None

    # send() enqueues the real outbox event the dispatcher subscribes to.
    from oryx.core.db import get_sessionmaker
    from oryx.core.models import OutboxEvent

    sm = get_sessionmaker()
    async with sm() as session:
        rows = (
            await session.execute(
                select(OutboxEvent).where(
                    OutboxEvent.workspace_id == uuid.UUID(ctx["workspace_id"])
                )
            )
        ).scalars().all()
    matching = [r for r in rows if r.event_name == "workspace.chat.message_sent"]
    assert len(matching) == 1
    assert matching[0].event["payload"]["messageId"] == msg["id"]


async def test_send_message_rejects_empty_body(app) -> None:
    owner, _ctx = await _signed_up_client(app)
    res = await owner.post("/v1/workspaces/messages", json={"body": "   "})
    assert res.status_code == 422, res.text


async def test_cursor_pagination_returns_only_new_messages_on_second_poll(app) -> None:
    """The real behavior this wave exists for: a second poll with the cursor
    from the first response returns ONLY the message sent afterward, not the
    whole history again."""
    owner, _ctx = await _signed_up_client(app)

    first = await owner.post("/v1/workspaces/messages", json={"body": "message A"})
    assert first.status_code == 200, first.text

    page1 = await owner.get("/v1/workspaces/messages")
    assert page1.status_code == 200
    page1_data = page1.json()
    assert [m["body"] for m in page1_data["data"]] == ["message A"]
    cursor = page1_data["meta"]["pagination"]["nextCursor"]
    assert cursor is not None

    second = await owner.post("/v1/workspaces/messages", json={"body": "message B"})
    assert second.status_code == 200, second.text

    page2 = await owner.get("/v1/workspaces/messages", params={"since": cursor})
    assert page2.status_code == 200
    page2_data = page2.json()
    # Only the NEW message — not message A again.
    assert [m["body"] for m in page2_data["data"]] == ["message B"]

    # Polling again with the SAME (now-latest) cursor and nothing new sent
    # returns an empty page, and hands back a usable cursor (not null).
    cursor2 = page2_data["meta"]["pagination"]["nextCursor"]
    page3 = await owner.get("/v1/workspaces/messages", params={"since": cursor2})
    assert page3.status_code == 200
    assert page3.json()["data"] == []
    assert page3.json()["meta"]["pagination"]["nextCursor"] == cursor2


async def test_edit_message_restricted_to_sender(app) -> None:
    owner, owner_ctx = await _signed_up_client(app)
    other, _other_ctx = await _add_member(app, owner_ctx, role="editor")

    sent = await owner.post("/v1/workspaces/messages", json={"body": "original"})
    message_id = sent.json()["data"]["id"]

    forbidden = await other.patch(
        f"/v1/workspaces/messages/{message_id}", json={"body": "hijacked"}
    )
    assert forbidden.status_code == 403, forbidden.text

    edited = await owner.patch(
        f"/v1/workspaces/messages/{message_id}", json={"body": "corrected"}
    )
    assert edited.status_code == 200, edited.text
    edited_data = edited.json()["data"]
    assert edited_data["body"] == "corrected"
    assert edited_data["editedAt"] is not None


async def test_delete_message_restricted_to_sender_and_redacts_body(app) -> None:
    owner, owner_ctx = await _signed_up_client(app)
    other, _other_ctx = await _add_member(app, owner_ctx, role="editor")

    sent = await owner.post("/v1/workspaces/messages", json={"body": "delete me"})
    message_id = sent.json()["data"]["id"]

    forbidden = await other.delete(f"/v1/workspaces/messages/{message_id}")
    assert forbidden.status_code == 403, forbidden.text

    deleted = await owner.delete(f"/v1/workspaces/messages/{message_id}")
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["data"]["deleted"] is True

    fetched = await owner.get("/v1/workspaces/messages")
    rows = fetched.json()["data"]
    assert len(rows) == 1
    assert rows[0]["id"] == message_id
    assert rows[0]["body"] is None
    assert rows[0]["deletedAt"] is not None

    # A second delete of an already-deleted message is a clean 404, not a
    # silent no-op — matches the repository's "caller decides" contract.
    again = await owner.delete(f"/v1/workspaces/messages/{message_id}")
    assert again.status_code == 404, again.text


async def test_mark_read_persists_last_read_marker(app) -> None:
    owner, ctx = await _signed_up_client(app)

    sent = await owner.post("/v1/workspaces/messages", json={"body": "read me"})
    message_id = sent.json()["data"]["id"]

    before = await owner.get("/v1/workspaces/messages/read")
    assert before.status_code == 200
    assert before.json()["data"]["lastReadMessageId"] is None

    marked = await owner.post("/v1/workspaces/messages/read", json={"messageId": message_id})
    assert marked.status_code == 200, marked.text
    marker = marked.json()["data"]
    assert marker["lastReadMessageId"] == message_id
    assert marker["workspaceId"] == ctx["workspace_id"]
    assert marker["accountId"] == ctx["account_id"]
    assert marker["lastReadAt"] is not None

    after = await owner.get("/v1/workspaces/messages/read")
    assert after.status_code == 200
    assert after.json()["data"]["lastReadMessageId"] == message_id
