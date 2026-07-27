"""Team Chat foundation wave event-name constants. Import at every emit site.

Namespaced `workspace.*` (matching the existing workspace.deletion.started/
completed events in services/intake/workspace_cascade.py), not `chat.*` —
there is no standalone chat domain module, chat lives inside the workspaces
service, one event per real content action.
"""
from __future__ import annotations

CHAT_MESSAGE_SENT = "workspace.chat.message_sent"
