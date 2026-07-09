"""Template rendering for alert email.

The EmailMessage Protocol carries (template, variables) — the provider renders
its own subject/body, exactly like newsletter.py builds its own text/plain
content (Phase 0 confirmed: no SendGrid dynamic-template IDs anywhere in this
codebase). Plain text only, matching the newsletter precedent.

An unknown template renders a generic fallback instead of raising — a copy
mistake must degrade to an ugly email, never to a lost alert.
"""
from __future__ import annotations

from oryx.services.activity.providers.email.base import EmailMessage


def _alert(variables: dict[str, str]) -> tuple[str, str]:
    title = variables.get("title", "New activity")
    lines = [
        title,
        "",
        f"Category: {variables.get('category', '-')}",
        f"Severity: {variables.get('severity', '-')}",
        f"Event: {variables.get('event_type', '-')}",
        "",
        "Open ORYX to see the full details in your activity feed.",
        "",
        "You are receiving this because instant email alerts are enabled for",
        "this category. Adjust this any time in Settings -> Notifications.",
    ]
    return f"ORYX alert: {title}", "\n".join(lines)


def render(message: EmailMessage) -> tuple[str, str]:
    """(subject, plain-text body) for a message. Never raises."""
    if message.template == "alert":
        return _alert(message.variables)
    # Unknown template — deliver something honest rather than fail.
    body = "\n".join(f"{k}: {v}" for k, v in sorted(message.variables.items()))
    return f"ORYX: {message.template}", body or message.template
