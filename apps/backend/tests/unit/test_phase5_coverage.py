"""Phase 5 Wave F — targeted coverage for the generator's generate() path and the
channel adapters' credential-validation / health-check / transport-error branches.

No DB. The AI provider and httpx transport are faked so the real code paths run
without network. These complement (not replace) the behavioural tests in
test_draft_generator.py and test_publishing_channels.py.
"""
from __future__ import annotations

import itertools
import uuid
from unittest.mock import patch

import httpx
import pytest

from oryx.services.drafts.models import ObjectSnapshot


# --------------------------------------------------------------------------- #
# DraftGeneratorAI — generate() through a faked provider + template Layer 2
# --------------------------------------------------------------------------- #
def _template():
    from oryx.services.templates.models import ContentTemplate

    return ContentTemplate(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="Article",
        format="article",
        tone="measured",
        max_words=600,
        min_words=200,
        structure_hint="lede, body, kicker",
        is_default=True,
    )


def test_prompt_uses_template_fields_and_string_fact() -> None:
    from oryx.services.drafts.generator import build_generation_prompt

    obj = ObjectSnapshot(
        id=uuid.uuid4(),
        headline="Acme raised $5B",
        epistemic_type="fact",
        confidence_score=None,  # → "n/a" branch in _render_object
        key_facts={"summary": "a plain string fact"},  # → _fact_str str() branch
    )
    system, user = build_generation_prompt(
        objects=[obj],
        format="article",
        instructions=None,
        template=_template(),
    )
    assert "TONE: measured" in user
    assert "MAX WORDS: 600" in user
    assert "MIN WORDS: 200" in user
    assert "STRUCTURE: lede, body, kicker" in user
    assert "a plain string fact" in user
    assert "n/a" in user  # confidence rendered as n/a


@pytest.mark.asyncio
async def test_generate_runs_through_provider() -> None:
    from oryx.services.drafts import generator as gen_mod
    from oryx.services.drafts.generator import DraftGeneratorAI

    class _FakeProvider:
        async def complete(self, *, system, user, max_tokens, temperature):
            assert "ORYX" in system  # Layer 1 system context reached the provider
            assert max_tokens == gen_mod.GENERATION_MAX_TOKENS
            assert temperature == gen_mod.GENERATION_TEMPERATURE
            return ("Generated body of three.", 123)

    def _fake_factory(settings, *, model, timeout):
        assert model == gen_mod.ANTHROPIC_MODEL_SONNET
        return _FakeProvider()

    obj = ObjectSnapshot(
        id=uuid.uuid4(),
        headline="Acme raised $5B",
        epistemic_type="fact",
        confidence_score=0.9,
        key_facts={"Acme": {"predicate": "raised", "object": "$5B"}},
    )
    with patch.object(gen_mod, "get_ai_provider", _fake_factory):
        result = await DraftGeneratorAI().generate(
            objects=[obj],
            format="article",
            instructions="keep it tight",
            template=_template(),
        )
    assert result.content == "Generated body of three."
    assert result.token_count == 123
    assert result.word_count == 4  # "Generated body of three."


# --------------------------------------------------------------------------- #
# Twitter/X — validate, health, thread-reply chaining, transport error
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_twitter_validate_and_health() -> None:
    from oryx.services.publishing.channels.twitter import TwitterXChannel

    ch = TwitterXChannel()
    assert await ch.validate_credentials({"access_token": "t"}) is True
    assert await ch.validate_credentials({}) is False
    assert await ch.health_check({}) is False  # no token short-circuits

    async def ok_get(self, url, **kw):
        return httpx.Response(200, json={"data": {"id": "u1"}}, request=httpx.Request("GET", url))

    with patch("httpx.AsyncClient.get", ok_get):
        assert await ch.health_check({"access_token": "t"}) is True

    async def boom_get(self, url, **kw):
        raise httpx.ConnectError("down")

    with patch("httpx.AsyncClient.get", boom_get):
        assert await ch.health_check({"access_token": "t"}) is False


@pytest.mark.asyncio
async def test_twitter_thread_reply_chaining() -> None:
    from oryx.services.publishing.channels.twitter import TwitterXChannel

    counter = itertools.count(1)
    seen_replies = []

    async def fake_post(self, url, **kw):
        body = kw.get("json") or {}
        seen_replies.append("reply" in body)
        return httpx.Response(
            201,
            json={"data": {"id": f"tw_{next(counter)}"}},
            request=httpx.Request("POST", url),
        )

    long_content = " ".join(f"Sentence number {i} of a long thread." for i in range(40))
    ch = TwitterXChannel()
    with patch("httpx.AsyncClient.post", fake_post):
        result = await ch.publish(long_content, "t", {"access_token": "tok"}, {})
    assert result.status == "delivered"
    assert result.external_id == "tw_1"  # first tweet id
    assert seen_replies[0] is False  # first tweet is not a reply
    assert any(seen_replies[1:])  # later tweets chain via in_reply_to_tweet_id


@pytest.mark.asyncio
async def test_twitter_transport_error_is_transient() -> None:
    from oryx.services.publishing.channels.base import TransientChannelError
    from oryx.services.publishing.channels.twitter import TwitterXChannel

    async def boom(self, url, **kw):
        raise httpx.ConnectError("down")

    ch = TwitterXChannel()
    with patch("httpx.AsyncClient.post", boom):
        with pytest.raises(TransientChannelError):
            await ch.publish("Short tweet.", "t", {"access_token": "tok"}, {})


# --------------------------------------------------------------------------- #
# LinkedIn — validate, health, transport error
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_linkedin_validate_and_health() -> None:
    from oryx.services.publishing.channels.linkedin import LinkedInChannel

    ch = LinkedInChannel()
    assert await ch.validate_credentials({"access_token": "t", "person_urn": "u"}) is True
    assert await ch.validate_credentials({"access_token": "t"}) is False
    assert await ch.health_check({}) is False

    async def ok_get(self, url, **kw):
        return httpx.Response(200, request=httpx.Request("GET", url))

    with patch("httpx.AsyncClient.get", ok_get):
        assert await ch.health_check({"access_token": "t"}) is True

    async def boom_get(self, url, **kw):
        raise httpx.ConnectError("down")

    with patch("httpx.AsyncClient.get", boom_get):
        assert await ch.health_check({"access_token": "t"}) is False


@pytest.mark.asyncio
async def test_linkedin_transport_error_is_transient() -> None:
    from oryx.services.publishing.channels.base import TransientChannelError
    from oryx.services.publishing.channels.linkedin import LinkedInChannel

    async def boom(self, url, **kw):
        raise httpx.ConnectError("down")

    ch = LinkedInChannel()
    with patch("httpx.AsyncClient.post", boom):
        with pytest.raises(TransientChannelError):
            await ch.publish("Body", "t", {"access_token": "t", "person_urn": "u"}, {})


# --------------------------------------------------------------------------- #
# Notion — validate, health, paragraph chunking, transport error
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_notion_validate_and_health() -> None:
    from oryx.services.publishing.channels.notion import NotionChannel

    ch = NotionChannel()
    assert await ch.validate_credentials({"integration_token": "t"}) is True
    assert await ch.validate_credentials({}) is False
    assert await ch.health_check({}) is False

    async def ok_get(self, url, **kw):
        return httpx.Response(200, request=httpx.Request("GET", url))

    with patch("httpx.AsyncClient.get", ok_get):
        assert await ch.health_check({"integration_token": "t"}) is True

    async def boom_get(self, url, **kw):
        raise httpx.ConnectError("down")

    with patch("httpx.AsyncClient.get", boom_get):
        # The shared get() helper raises TransientChannelError; health swallows it.
        assert await ch.health_check({"integration_token": "t"}) is False


@pytest.mark.asyncio
async def test_notion_long_line_chunks_and_transport_error() -> None:
    from oryx.services.publishing.channels.base import TransientChannelError
    from oryx.services.publishing.channels.notion import NotionChannel, _paragraph_blocks

    # A single line longer than the 2000-char block limit splits into >1 block.
    blocks = _paragraph_blocks("x" * 4500)
    assert len(blocks) == 3  # 2000 + 2000 + 500

    async def boom(self, url, **kw):
        raise httpx.ConnectError("down")

    ch = NotionChannel()
    with patch("httpx.AsyncClient.post", boom):
        with pytest.raises(TransientChannelError):
            await ch.publish(
                "Body line", "Title", {"integration_token": "t"}, {"parent_page_id": "p"}
            )


# --------------------------------------------------------------------------- #
# Newsletter — recipient parsing, validate/health, provider guards
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_newsletter_validate_health_and_guards() -> None:
    from oryx.services.publishing.channels.base import PermanentChannelError
    from oryx.services.publishing.channels.newsletter import NewsletterChannel, _recipients

    ch = NewsletterChannel()
    assert await ch.validate_credentials({"api_key": "SG.x"}) is True
    assert await ch.validate_credentials({"host": "h", "username": "u"}) is True
    assert await ch.validate_credentials({}) is False
    assert await ch.health_check({"api_key": "SG.x"}) is True

    assert _recipients({"to": "a@b.c"}) == ["a@b.c"]  # str → list
    assert _recipients({"to": ["a@b.c", "d@e.f"]}) == ["a@b.c", "d@e.f"]
    assert _recipients({}) == []

    # No recipients → permanent.
    with pytest.raises(PermanentChannelError):
        await ch.publish("body", "subj", {"api_key": "SG.x"}, {"provider": "sendgrid"})
    # Unknown provider → permanent.
    with pytest.raises(PermanentChannelError):
        await ch.publish(
            "body", "subj", {"api_key": "SG.x"}, {"provider": "carrier-pigeon", "to": ["a@b.c"]}
        )
