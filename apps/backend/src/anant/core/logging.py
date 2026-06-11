"""Structured logging.

Every log line is single-line JSON keyed by event, with request_id and
service name attached. PII redaction is enforced at the formatter level.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger

from anant.config import get_settings

REDACT_FIELDS: set[str] = {
    "email",
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "phone",
    "name",
    "address",
    "ip_address",
}


class RedactingFormatter(jsonlogger.JsonFormatter):
    """Strip sensitive fields before they reach any sink."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        settings = get_settings()
        log_record.setdefault("service", settings.service_name)
        log_record.setdefault("environment", settings.environment)
        for k in list(log_record.keys()):
            if k in REDACT_FIELDS:
                log_record[k] = "[redacted]"


def configure_logging() -> None:
    """Initialize root logger. Idempotent — safe to call from tests."""
    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.log_level)
    # Clear pre-existing handlers (uvicorn / pytest may add their own).
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        RedactingFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
