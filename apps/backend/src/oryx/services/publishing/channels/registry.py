"""Channel registry — maps publish_channel_enum values to adapter instances.

The publishing engine dispatches through `get_channel(channel)`. Adapters are
stateless, so a single shared instance per channel is fine; tests can override
the map via `register_channel` to inject a fake.
"""
from __future__ import annotations

from oryx.services.publishing.channels.base import PublishChannel
from oryx.services.publishing.channels.export import ExportChannel
from oryx.services.publishing.channels.linkedin import LinkedInChannel
from oryx.services.publishing.channels.newsletter import NewsletterChannel
from oryx.services.publishing.channels.notion import NotionChannel
from oryx.services.publishing.channels.twitter import TwitterXChannel
from oryx.services.publishing.channels.webhook import WebhookChannel

_REGISTRY: dict[str, PublishChannel] = {
    "twitter_x": TwitterXChannel(),
    "linkedin": LinkedInChannel(),
    "email_newsletter": NewsletterChannel(),
    "notion": NotionChannel(),
    "webhook": WebhookChannel(),
    "export": ExportChannel(),
}


def get_channel(channel: str) -> PublishChannel:
    adapter = _REGISTRY.get(channel)
    if adapter is None:
        raise KeyError(f"No publish channel adapter registered for '{channel}'")
    return adapter


def register_channel(channel: str, adapter: PublishChannel) -> None:
    """Override an adapter (used by tests to inject fakes)."""
    _REGISTRY[channel] = adapter


def all_channels() -> dict[str, PublishChannel]:
    return dict(_REGISTRY)
