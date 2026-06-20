"""Text sanitizer + title normalizer + link extraction."""
from __future__ import annotations

from oryx.services.normalization.text_sanitizer import (
    extract_links,
    normalize_title,
    sanitize_html_to_text,
)


def test_sanitize_html_strips_tags_and_entities() -> None:
    html = "<p>Hello&nbsp;<b>world</b></p>"
    assert "world" in sanitize_html_to_text(html)
    assert "<" not in sanitize_html_to_text(html)
    assert "&nbsp;" not in sanitize_html_to_text(html)


def test_sanitize_html_collapses_runs_of_whitespace() -> None:
    html = "<div>a       b\n\n\n\n\nc</div>"
    out = sanitize_html_to_text(html)
    assert "a b" in out
    assert "\n\n\n" not in out


def test_sanitize_html_empty_input() -> None:
    assert sanitize_html_to_text(None) == ""
    assert sanitize_html_to_text("") == ""


def test_normalize_title_strips_emoji_and_lowercases() -> None:
    assert normalize_title("📈 Daily Macro Brief") == "daily macro brief"


def test_normalize_title_collapses_whitespace() -> None:
    assert normalize_title("Hello    World") == "hello world"


def test_normalize_title_none() -> None:
    assert normalize_title(None) == ""


def test_extract_links_pairs_href_with_anchor() -> None:
    html = '<a href="https://example.com">click <b>here</b></a>'
    out = extract_links(html)
    assert out[0].url == "https://example.com"
    assert "click" in out[0].anchor


def test_extract_links_handles_multiple() -> None:
    html = '<a href="a">A</a> and <a href="b">B</a>'
    out = extract_links(html)
    assert [l.url for l in out] == ["a", "b"]
