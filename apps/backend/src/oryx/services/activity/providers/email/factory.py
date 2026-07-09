"""Alert-email provider selection.

Mirrors the AI/push switches exactly (core/ai_provider.py get_ai_provider via
AI_PROVIDER; providers/push/factory.py get_push_provider via PUSH_PROVIDER):
EMAIL_PROVIDER=log_only (the default — Phase 2's stub keeps logging instead of
delivering), =sendgrid, or =smtp. Like AI_PROVIDER, the value names the
concrete provider (email has no per-device platform axis, so there is no
'real' indirection).

The default reuses auth's LogOnlyEmailProvider — it is the one stub behind
the shared EmailProvider Protocol; duplicating it here would just fork the
log vocabulary. An unconfigured real provider degrades to ok=False AUTH
results, never a crash (same promise as the push factory).
"""
from __future__ import annotations

from oryx.config import get_settings
from oryx.services.auth.providers.email.log_only import LogOnlyEmailProvider

from .base import EmailProvider
from .sendgrid import SendGridEmailProvider
from .smtp import SMTPEmailProvider


def get_email_provider(settings=None) -> EmailProvider:
    """Factory. EMAIL_PROVIDER=sendgrid|smtp → real delivery; else log-only."""
    settings = settings if settings is not None else get_settings()
    selected = getattr(settings, "email_provider", "log_only")
    if selected == "sendgrid":
        return SendGridEmailProvider(
            getattr(settings, "sendgrid_api_key", None),
            from_email=getattr(settings, "alert_email_from", "alerts@oryx.local"),
            from_name=getattr(settings, "alert_email_from_name", "ORYX Alerts"),
        )
    if selected == "smtp":
        return SMTPEmailProvider(
            getattr(settings, "smtp_host", None),
            port=getattr(settings, "smtp_port", 587),
            username=getattr(settings, "smtp_username", None),
            password=getattr(settings, "smtp_password", None),
            from_email=getattr(settings, "alert_email_from", "alerts@oryx.local"),
        )
    return LogOnlyEmailProvider()
