"""URL canonicalization for dedupe fingerprinting and link extraction.

Rules locked in Batch 1:
  - Lowercase the host (URLs are case-insensitive in the host portion)
  - Strip tracking query params (utm_*, gclid, fbclid, ref, ref_src, etc.)
  - Drop fragment unless it looks like an SPA route (heuristic: starts with '!')
  - Drop default ports
  - Drop trailing slash on root path only
  - Preserve case of path/query — case-sensitive on most servers

Anything not URL-shaped returns the original string lowercased + stripped.
"""
from __future__ import annotations

from urllib.parse import (
    parse_qsl,
    quote,
    unquote,
    urlencode,
    urlparse,
    urlunparse,
)

_TRACKING_PREFIXES: frozenset[str] = frozenset({
    "utm_", "vero_", "matomo_", "mtm_", "pk_", "stm_",
    "yclid", "gclid", "fbclid", "msclkid", "mc_eid", "mc_cid",
    "_hsenc", "_hsmi", "hsa_", "hsCtaTracking",
    "ref", "ref_src", "ref_url", "trk", "trkCampaign",
})

_DEFAULT_PORTS: dict[str, int] = {"http": 80, "https": 443}


def _strip_tracking(query: str) -> str:
    if not query:
        return ""
    pairs = parse_qsl(query, keep_blank_values=True)
    kept = [
        (k, v)
        for k, v in pairs
        if not any(k == p or k.startswith(p) for p in _TRACKING_PREFIXES)
    ]
    return urlencode(kept, quote_via=quote)


def canonicalize_url(raw: str) -> str:
    if not raw:
        return ""
    s = raw.strip()
    # If we can't parse it as a URL with a scheme, fall back to lowercase form.
    parsed = urlparse(s)
    if not parsed.scheme or not parsed.netloc:
        return s.lower()

    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower() if parsed.hostname else ""
    port = parsed.port

    netloc = host
    if port is not None and _DEFAULT_PORTS.get(scheme) != port:
        netloc = f"{host}:{port}"

    path = parsed.path or "/"
    original_had_query = bool(parsed.query)
    query = _strip_tracking(parsed.query)
    # Drop trailing slash on root path ONLY when the user didn't write a query.
    # This preserves `example.com/?…` vs `example.com/` distinction.
    if path == "/" and not original_had_query:
        path = ""

    fragment = parsed.fragment if parsed.fragment.startswith("!") else ""

    return urlunparse((scheme, netloc, unquote(path), "", query, fragment))


# Trailing chars often left over from email-style "Name <addr@host>" or
# parenthesized URL captures. Stripped before lowercasing.
_TRAILING_NOISE = ">),;:.\"'"


def extract_domain(raw: str) -> str:
    parsed = urlparse(raw.strip())
    if parsed.hostname:
        return parsed.hostname.lower()
    # Email-style "name@domain" (often inside <…>)
    if "@" in raw:
        tail = raw.rsplit("@", 1)[-1].strip()
        # Strip closing bracket / punctuation noise from the right edge
        tail = tail.rstrip(_TRAILING_NOISE)
        return tail.lower()
    return raw.strip().lower()
