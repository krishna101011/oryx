"""SSRF defense — shared by every outbound fetch of a user-controlled URL.

Three call sites feed this: api_pull source config (base_url), RSS feed_url,
and publishing webhook target config.url. All three are workspace-controlled
strings that this process will connect to — without a guard, a hostile
workspace admin could point any of them at internal infrastructure (Postgres,
Redis, the cloud metadata endpoint) and exfiltrate data through the response
body, or use us as a port scanner against internal hosts.

Two layers:
  1. Hostname allowlist if the caller provides one
  2. Deny list of private + link-local + loopback + cloud-metadata IPs

The deny list operates on resolved IPs, not on the URL alone — a hostile DNS
record that resolves to 169.254.169.254 must still be rejected. The resolver
lives here (sync; we only call it once per request).

Redirects are NOT handled here. A caller that follows redirects (RSS) MUST
call assert_url_safe again on every redirect target before connecting to it —
the initial URL looking safe proves nothing about where a 302 sends you next.

This module raises UnsafeUrlError, not a taxonomy from any particular caller
(ProviderError, ChannelError, ...) — it has no business knowing which of its
callers is asking. Each call site catches UnsafeUrlError and translates it
into its own error type.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# Known cloud metadata endpoints. The /16 link-local catch below covers these
# but we name them explicitly so deny-reasons are interpretable.
_METADATA_HOSTS: frozenset[str] = frozenset({
    "169.254.169.254",  # AWS, OpenStack, GCP
    "100.100.100.200",  # Alibaba
    "169.254.169.123",  # NTP-side metadata variant
})


class UnsafeUrlError(ValueError):
    """Raised when a URL would be unsafe to fetch (SSRF guard tripped)."""


def assert_url_safe(
    url: str, *, hostname_allowlist: list[str] | None = None
) -> None:
    """Raise UnsafeUrlError if the URL would be unsafe to fetch.

    Performs DNS resolution to catch hostnames that resolve to private space.
    Allowlist short-circuits when populated AND host matches.
    """
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise UnsafeUrlError(f"Unsupported URL scheme: {scheme}")

    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("URL missing hostname")

    if hostname_allowlist:
        if not any(host == allowed or host.endswith("." + allowed) for allowed in hostname_allowlist):
            raise UnsafeUrlError(f"Host {host!r} not in workspace allowlist")

    # Resolve and validate every returned address. A single bad address kills
    # the request — that's safer than trying to pin our HTTP client to the
    # surviving addresses.
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if scheme == "https" else 80))
    except socket.gaierror as e:
        raise UnsafeUrlError(f"DNS resolution failed for {host!r}: {e}") from e

    seen: set[str] = set()
    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        if ip_str in seen:
            continue
        seen.add(ip_str)
        _assert_ip_safe(ip_str, host=host)


def _assert_ip_safe(ip_str: str, *, host: str) -> None:
    if ip_str in _METADATA_HOSTS:
        raise UnsafeUrlError(f"Host {host!r} resolves to cloud metadata endpoint")
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError as e:
        raise UnsafeUrlError(f"Cannot parse IP {ip_str!r}") from e

    if ip.is_private:
        raise UnsafeUrlError(f"Host {host!r} resolves to private IP {ip_str}")
    if ip.is_loopback:
        raise UnsafeUrlError(f"Host {host!r} resolves to loopback IP {ip_str}")
    if ip.is_link_local:
        raise UnsafeUrlError(f"Host {host!r} resolves to link-local IP {ip_str}")
    if ip.is_multicast:
        raise UnsafeUrlError(f"Host {host!r} resolves to multicast IP {ip_str}")
    if ip.is_reserved:
        raise UnsafeUrlError(f"Host {host!r} resolves to reserved IP {ip_str}")
    if ip.is_unspecified:
        raise UnsafeUrlError(f"Host {host!r} resolves to unspecified address")
