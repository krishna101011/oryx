"""Phase 5 Wave D publishing event-name constants. Import at every emit site.

content.published is the Phase 5 → Phase 6 boundary event (one per successful
per-target delivery). content.publish.failed is emitted when a target's delivery
is abandoned (permanent error, or transient exhausted at 5 attempts).
"""
from __future__ import annotations

CONTENT_PUBLISHED = "content.published"
CONTENT_PUBLISH_FAILED = "content.publish.failed"
