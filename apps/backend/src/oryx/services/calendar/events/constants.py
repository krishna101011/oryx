"""Phase 5 Wave E calendar event-name constants. Import at every emit site.

CALENDAR_ENTRY_SCHEDULED reuses the frozen-catalog name content.draft.scheduled
(the draft-lifecycle scheduled event). CALENDAR_ENTRY_CANCELLED is a Wave E
extension beyond the frozen catalog — emitted on cancellation so Phase 6
automation can eventually react to un-scheduling (consistent with the
event-driven pattern used everywhere else).
"""
from __future__ import annotations

CALENDAR_ENTRY_SCHEDULED = "content.draft.scheduled"
CALENDAR_ENTRY_CANCELLED = "content.calendar.cancelled"
