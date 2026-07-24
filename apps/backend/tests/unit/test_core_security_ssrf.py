"""oryx.core.security.ssrf — the shared SSRF guard.

This is the canonical home of the guard (moved out of
intake/providers/api_pull/safety.py — see that module's docstring). It now
backs three call sites: api_pull (translates to ProviderError, tested in
test_intake_api_pull.py), RSS and publishing webhooks (both tested against
the real guard in test_ssrf_redirect_and_loopback.py). This file tests the
guard itself, in isolation from any caller's error taxonomy.
"""
from __future__ import annotations

import socket
from unittest.mock import patch

import pytest

from oryx.core.security.ssrf import UnsafeUrlError, assert_url_safe


def _patch_dns(addr: str):
    def fake_getaddrinfo(host, port, *a, **kw):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (addr, port))]
    return patch("socket.getaddrinfo", fake_getaddrinfo)


def test_rejects_unsupported_scheme() -> None:
    with pytest.raises(UnsafeUrlError, match="scheme"):
        assert_url_safe("file:///etc/passwd")


def test_rejects_ftp_scheme() -> None:
    with pytest.raises(UnsafeUrlError, match="scheme"):
        assert_url_safe("ftp://vendor.test/x")


@pytest.mark.parametrize(
    "addr",
    [
        "10.0.0.5",           # private
        "192.168.1.1",        # private
        "172.16.0.1",         # private
        "127.0.0.1",          # loopback
        "169.254.169.254",    # AWS/GCP/OpenStack metadata
        "169.254.10.5",       # link-local
        "100.100.100.200",    # Alibaba metadata
        "224.0.0.1",          # multicast
    ],
)
def test_rejects_non_public_resolved_ip(addr: str) -> None:
    with _patch_dns(addr):
        with pytest.raises(UnsafeUrlError):
            assert_url_safe("https://vendor.test/x")


def test_accepts_normal_public_ip() -> None:
    with _patch_dns("8.8.8.8"):
        assert_url_safe("https://vendor.test/x")  # no raise


def test_allowlist_short_circuits_other_hosts() -> None:
    with _patch_dns("8.8.8.8"):
        with pytest.raises(UnsafeUrlError, match="allowlist"):
            assert_url_safe("https://evil.test/x", hostname_allowlist=["vendor.test"])


def test_allowlist_accepts_subdomains() -> None:
    with _patch_dns("8.8.8.8"):
        assert_url_safe("https://api.vendor.test/x", hostname_allowlist=["vendor.test"])
