"""Alert-email provider seam.

The Protocol IS services/auth/providers/email/base.py's EmailProvider,
re-exported unchanged — the same pattern providers/push/base.py uses for
ProviderResult/ProviderErrorKind. Dispatcher code imports the activity-local
names; the auth module stays the single owner of the interface shape.
"""
from __future__ import annotations

from oryx.services.auth.providers.email.base import (
    EmailMessage,
    EmailProvider,
    ProviderErrorKind,
    ProviderResult,
)

__all__ = ["EmailMessage", "EmailProvider", "ProviderErrorKind", "ProviderResult"]
