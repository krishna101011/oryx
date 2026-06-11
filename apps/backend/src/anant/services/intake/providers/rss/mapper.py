"""ParsedItem → RawItem.

Pure transformation. No IO. No business logic. This file is the
narrow waist of the RSS provider — the only thing that knows both
the feedparser shape and the orchestrator shape.
"""
from __future__ import annotations

from anant.services.intake.providers.base import RawItem
from anant.services.intake.providers.rss.parser import ParsedItem


def parsed_item_to_raw(item: ParsedItem, *, feed_title: str | None) -> RawItem:
    payload: dict = {
        "guid": item.external_id,
        "title": item.title,
        "summary": item.summary_text,
        "content_html": item.content_html,
        "primary_link": item.primary_link,
        "feed_title": feed_title,
    }
    links = []
    if item.primary_link:
        links.append({"url": item.primary_link, "anchor": item.title or ""})

    return RawItem(
        external_id=item.external_id,
        received_at=item.received_at,
        sender=feed_title,
        subject=item.title,
        body_text=item.summary_text,
        body_html=item.content_html,
        links=links,
        payload=payload,
    )
