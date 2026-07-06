"""PII redaction in structured logs.

Asserts that REDACT_FIELDS values never reach a sink in plaintext.
"""
from __future__ import annotations

import json
import logging
from io import StringIO

from oryx.core.logging import REDACT_FIELDS, RedactingFormatter, configure_logging

# Skip `name` — it's a built-in LogRecord field that pytest's log capture
# also tracks; overriding it via setattr breaks pytest internals. The
# redaction logic still applies to it when it surfaces in real logs.
_SETTABLE = [f for f in REDACT_FIELDS if f != "name"]


def test_redacted_fields_replaced_with_sentinel() -> None:
    """Every surfaced REDACT_FIELDS key in the JSON output is sanitized."""
    fmt = RedactingFormatter("%(message)s")
    rec = logging.LogRecord(
        name="t", level=logging.INFO, pathname="", lineno=0,
        msg="event", args=(), exc_info=None,
    )
    for field in _SETTABLE:
        setattr(rec, field, "SHOULD_BE_REDACTED")
    out = fmt.format(rec)
    parsed = json.loads(out)
    surfaced = [f for f in _SETTABLE if f in parsed]
    assert surfaced, "expected PII keys to surface in the JSON output"
    for field in surfaced:
        assert parsed[field] == "[redacted]", f"{field} leaked"
    assert "SHOULD_BE_REDACTED" not in out


def test_non_sensitive_fields_pass_through() -> None:
    fmt = RedactingFormatter("%(message)s")
    rec = logging.LogRecord(
        name="t", level=logging.INFO, pathname="", lineno=0,
        msg="event", args=(), exc_info=None,
    )
    rec.account_id = "acct-123"  # type: ignore[attr-defined]
    rec.event_type = "signin_success"  # type: ignore[attr-defined]
    out = fmt.format(rec)
    parsed = json.loads(out)
    assert parsed["account_id"] == "acct-123"
    assert parsed["event_type"] == "signin_success"


def test_configure_logging_attaches_redacting_formatter() -> None:
    # configure_logging() re-levels the root logger and replaces its handlers;
    # restore both so this test's global side effects don't leak into the rest
    # of the suite (an INFO root level here previously masked/unmasked logging
    # bugs in unrelated integration tests depending on run order).
    root = logging.getLogger()
    prior_level = root.level
    prior_handlers = list(root.handlers)
    try:
        buf = StringIO()
        configure_logging()
        handler = root.handlers[0]
        handler.stream = buf
        log = logging.getLogger("oryx.test")
        log.warning("auth.event", extra={"email": "a@b.com", "account_id": "x"})
        output = buf.getvalue()
        assert "a@b.com" not in output
        assert "[redacted]" in output
        assert "x" in output
    finally:
        for h in list(root.handlers):
            root.removeHandler(h)
        for h in prior_handlers:
            root.addHandler(h)
        root.setLevel(prior_level)
