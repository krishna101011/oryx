"""Phase 5 Wave A draft event-name constants. Import at every emit site.

Wave A emits only the first two; the rest of the content.* catalog
(approved / rejected / scheduled / published / publish.failed) lands in later
waves. content.published is the Phase 5 → Phase 6 boundary event.
"""
from __future__ import annotations

DRAFT_CREATED = "content.draft.created"
DRAFT_UPDATED = "content.draft.updated"

# Wave C — review workflow. submit-review and changes_requested deliberately
# reuse DRAFT_UPDATED (they are draft-lifecycle updates, not distinct events).
DRAFT_APPROVED = "content.draft.approved"
DRAFT_REJECTED = "content.draft.rejected"
