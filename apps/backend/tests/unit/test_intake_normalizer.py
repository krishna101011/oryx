"""Normalizer end-to-end on a representative raw payload."""
from __future__ import annotations

from anant.services.normalization.normalizer import normalize_raw_item
from anant.services.normalization.version import NORMALIZER_VERSION


def test_normalizer_extracts_sender_domain_from_email() -> None:
    out = normalize_raw_item({"sender": "Newsletter <hi@FT.com>", "subject": "X"})
    assert out.sender_domain == "ft.com"
    assert out.sender_label == "Newsletter <hi@FT.com>"


def test_normalizer_captures_subject_and_body_text() -> None:
    out = normalize_raw_item({
        "sender": "x@y.test",
        "subject": "  Daily Brief  ",
        "body_html": "<p>Hello&nbsp;<b>world</b></p>",
    })
    assert out.subject == "Daily Brief"
    assert "world" in out.body_text
    assert "<" not in out.body_text


def test_normalizer_extracts_links_from_html_when_not_provided() -> None:
    out = normalize_raw_item({
        "sender": "x@y.test",
        "subject": "x",
        "body_html": '<a href="https://example.com/a?utm_source=n">go</a>',
    })
    assert out.links[0]["url"] == "https://example.com/a"  # tracking stripped
    assert "go" in out.links[0]["anchor"]


def test_normalizer_uses_provided_links_when_present() -> None:
    out = normalize_raw_item({
        "sender": "x@y.test", "subject": "x",
        "links": [{"url": "https://EX.example.com/", "anchor": "L"}],
    })
    assert out.links[0]["url"].startswith("https://ex.example.com")


def test_normalizer_preserves_gmail_label_ids_in_metadata() -> None:
    out = normalize_raw_item({
        "sender": "x@y.test", "subject": "x",
        "label_ids": ["INBOX", "Label_1"],
        "thread_id": "t-1",
    })
    assert out.metadata["label_ids"] == ["INBOX", "Label_1"]
    assert out.metadata["thread_id"] == "t-1"


def test_normalizer_version_tagged_on_output() -> None:
    out = normalize_raw_item({"sender": "a@b.test", "subject": "x"})
    assert out.normalizer_version == NORMALIZER_VERSION
