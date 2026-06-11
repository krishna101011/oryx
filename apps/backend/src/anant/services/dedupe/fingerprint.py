"""Two-tier content fingerprint (CR-2 of the frozen Phase 3 spec).

Tier 1 — link-anchored:
    sha256(sender_domain || '\x1e' || canonicalize_url(primary_link)
           || '\x1e' || normalize_title(subject))

Tier 2 — body-only fallback (no useful link):
    sha256(sender_domain || '\x1e' || normalize_title(subject)
           || '\x1e' || date_bucket(received_at, tz))

The date bucket prevents same-title, same-sender body-only items from
*different days* from colliding. The `\x1e` separator (Record Separator)
keeps the hash collision-resistant against field-boundary games — even if
a title legitimately contains a URL, the separators keep the tiers
unambiguous.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from anant.services.normalization.text_sanitizer import normalize_title
from anant.services.normalization.url_canonicalizer import canonicalize_url

_SEP = "\x1e"

# Tier marker stored in the audit log; not part of the hash.
TIER_LINKED = "linked"
TIER_BODY_DATE = "body_date"


def _date_bucket(received_at: datetime, *, tz: str) -> str:
    """YYYY-MM-DD in the workspace's timezone. Tz-naive input is treated as UTC."""
    if received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=UTC)
    try:
        local = received_at.astimezone(ZoneInfo(tz))
    except Exception:
        local = received_at.astimezone(UTC)
    return local.strftime("%Y-%m-%d")


def _hash(parts: list[str]) -> str:
    return hashlib.sha256(_SEP.join(parts).encode("utf-8")).hexdigest()


def compute_fingerprint(
    *,
    sender_domain: str | None,
    subject: str | None,
    primary_link: str | None,
    received_at: datetime,
    workspace_tz: str = "UTC",
) -> tuple[str, str]:
    """Return (fingerprint, tier_label)."""
    sd = (sender_domain or "").strip().lower()
    title = normalize_title(subject)

    if primary_link and primary_link.strip():
        url_canon = canonicalize_url(primary_link)
        if url_canon:
            return _hash([sd, url_canon, title]), TIER_LINKED

    bucket = _date_bucket(received_at, tz=workspace_tz)
    return _hash([sd, title, bucket]), TIER_BODY_DATE


def pick_primary_link(links: list[dict[str, str]] | None) -> str | None:
    """Choose the most-likely-canonical link from a normalized list.

    Phase 3 rule: first link wins. Phase 4 may pick more cleverly
    (e.g. preferring https, preferring non-tracking domains).
    """
    if not links:
        return None
    for link in links:
        url = (link.get("url") or "").strip()
        if url:
            return url
    return None
