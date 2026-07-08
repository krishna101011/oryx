"""Push-provider selection — Phase 6 Wave C.

Mirrors the AI provider switch (core/ai_provider.py get_ai_provider, driven by
AI_PROVIDER): PUSH_PROVIDER=log_only (the default — Phase 2's stub keeps
logging instead of delivering) or PUSH_PROVIDER=real, which activates the real
implementations per device platform: FCMProvider for Android, APNsProvider for
iOS. 'web' devices always get the log-only stub — browser push is not part of
this wave.

Credentials for the real providers are read from settings (see fcm.py /
apns.py module docstrings for exactly what to generate and where to put it);
an unconfigured real provider degrades to ok=False AUTH results, never a
crash.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from oryx.config import get_settings

from .apns import APNsProvider
from .base import PushProvider
from .fcm import FCMProvider
from .log_only import LogOnlyPushProvider


@lru_cache(maxsize=4)
def _load_json_file(path: str) -> dict[str, Any] | None:
    try:
        with open(path, encoding="utf-8") as fh:
            loaded = json.load(fh)
        return loaded if isinstance(loaded, dict) else None
    except (OSError, ValueError):
        return None


@lru_cache(maxsize=4)
def _load_text_file(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def get_push_provider(platform: str, settings=None) -> PushProvider:
    """Factory. PUSH_PROVIDER=real → FCM (android) / APNs (ios); else log-only."""
    settings = settings if settings is not None else get_settings()
    if getattr(settings, "push_provider", "log_only") != "real":
        return LogOnlyPushProvider()
    if platform == "android":
        sa_file = getattr(settings, "fcm_service_account_file", None)
        return FCMProvider(_load_json_file(sa_file) if sa_file else None)
    if platform == "ios":
        key_file = getattr(settings, "apns_key_file", None)
        return APNsProvider(
            key_pem=_load_text_file(key_file) if key_file else None,
            key_id=getattr(settings, "apns_key_id", None),
            team_id=getattr(settings, "apns_team_id", None),
            topic=getattr(settings, "apns_topic", "com.oryx.app"),
            use_sandbox=getattr(settings, "apns_use_sandbox", True),
        )
    # 'web' (or anything unknown): no real browser-push provider this wave.
    return LogOnlyPushProvider()
