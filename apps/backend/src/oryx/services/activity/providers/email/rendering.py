"""Template rendering for alert and digest email.

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


def _digest(variables: dict[str, str]) -> tuple[str, str]:
    """A bundled summary of multiple items — genuinely different shape from
    _alert() above (one event, one line each), matching the real bundle
    DigestWorker._digest_content produces (title/count/highlights over a
    window, not a single event_type/severity pair)."""
    title = variables.get("title", "Your ORYX digest")
    category = variables.get("category", "-")
    frequency = variables.get("frequency", "daily")
    count = variables.get("count", "0")
    highlights = variables.get("highlights", "")
    label = "Daily" if frequency == "daily" else "Weekly"
    plural = "" if count == "1" else "s"
    lines = [
        title,
        "",
        f"{count} {category} update{plural} bundled into this {label.lower()} digest:",
        "",
        highlights or "(no details available)",
        "",
        "Open ORYX to see the full activity feed.",
        "",
        "You are receiving this because email digests are enabled for this",
        "category. Adjust this any time in Settings -> Notifications.",
    ]
    return f"ORYX {label.lower()} digest: {title}", "\n".join(lines)


def _password_reset(variables: dict[str, str]) -> tuple[str, str]:
    token = variables.get("reset_token", "")
    lines = [
        "Reset your ORYX password",
        "",
        "Use this code in the app to set a new password:",
        "",
        token,
        "",
        f"This code expires in {variables.get('expires_minutes', '30')} minutes.",
        "If you didn't request a reset, ignore this email — your password is",
        "unchanged and the code dies on its own.",
    ]
    return "ORYX password reset", "\n".join(lines)


def _invite(variables: dict[str, str]) -> tuple[str, str]:
    workspace_name = variables.get("workspace_name", "an ORYX workspace")
    inviter = variables.get("inviter_display_name", "Someone")
    role = variables.get("role", "member")
    token = variables.get("invite_token", "")
    lines = [
        f"{inviter} invited you to join {workspace_name} on ORYX as a{'n' if role[:1] in 'aeiou' else ''} {role}.",
        "",
        "Use this code in the app to accept:",
        "",
        token,
        "",
        f"This invite expires in {variables.get('expires_days', '7')} days.",
        "If you weren't expecting this, you can safely ignore this email —",
        "nothing happens until the invite is accepted.",
    ]
    return f"You're invited to {workspace_name} on ORYX", "\n".join(lines)


def render(message: EmailMessage) -> tuple[str, str]:
    """(subject, plain-text body) for a message. Never raises."""
    if message.template == "alert":
        return _alert(message.variables)
    if message.template == "digest":
        return _digest(message.variables)
    if message.template == "password_reset":
        return _password_reset(message.variables)
    if message.template == "invite":
        return _invite(message.variables)
    # Unknown template — deliver something honest rather than fail.
    body = "\n".join(f"{k}: {v}" for k, v in sorted(message.variables.items()))
    return f"ORYX: {message.template}", body or message.template
