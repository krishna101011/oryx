"""URL canonicalizer rules."""
from __future__ import annotations

import pytest

from anant.services.normalization.url_canonicalizer import (
    canonicalize_url,
    extract_domain,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("HTTPS://www.Example.COM/Path", "https://www.example.com/Path"),
        ("https://example.com:443/", "https://example.com"),
        ("http://example.com:80/", "http://example.com"),
        ("https://example.com/?utm_source=x&q=hello", "https://example.com/?q=hello"),
        ("https://example.com/?utm_campaign=a&utm_medium=b", "https://example.com/"),
        ("https://example.com/path#fragment", "https://example.com/path"),
        ("https://example.com/path#!route", "https://example.com/path#!route"),
        ("not-a-url", "not-a-url"),
        ("", ""),
    ],
)
def test_canonicalize_url_rules(raw: str, expected: str) -> None:
    assert canonicalize_url(raw) == expected


def test_canonicalize_url_strips_multiple_tracking_params() -> None:
    out = canonicalize_url(
        "https://x.test/p?utm_source=a&utm_medium=b&gclid=z&fbclid=q&keep=1"
    )
    assert "utm_" not in out and "gclid" not in out and "fbclid" not in out
    assert "keep=1" in out


def test_extract_domain_from_url() -> None:
    assert extract_domain("https://Foo.example.com/x") == "foo.example.com"


def test_extract_domain_from_email_address() -> None:
    assert extract_domain("Newsletter <hello@FOO.example.com>") == "foo.example.com"


def test_extract_domain_from_bare_string() -> None:
    assert extract_domain("Example") == "example"
