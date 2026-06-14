"""Wave E research event-name constants.

PACKET_READY is the Phase 4 → Phase 5 boundary event. Phase 5 subscribes to it
and is the ONLY code that sets research_packets.consumed_at.
"""
from __future__ import annotations

PACKET_READY = "research.packet.ready"
