"""Metric-key maps — Phase 7 Wave A (frozen doc §3.3, ADR-047).

Source A: EVENT_METRICS maps each of the 20 catalog bus events to its rollup
metric key. Source B: ACTION_METRICS maps automation_log's REAL action_taken
values (services/activity/dispatcher.py ACTION_* constants — confirmed, not
invented) to theirs; digests_sent counts digest_runs rows.

push_suppressed_quiet_hours is mapped although no dispatcher code writes that
action_taken value yet (quiet-hours suppression is currently silent by frozen
Phase 6 §3.3 — the logging addendum is a flagged follow-up). Until it lands,
the aggregate simply matches zero rows and the metric never appears in the
sparse rollup table; nothing crashes.
"""
from __future__ import annotations

# Bus event name -> metric key (Source A).
EVENT_METRICS: dict[str, str] = {
    "intake.item.received": "intake_items_received",
    "verification.claim.extracted": "claims_extracted",
    "verification.claim.typed": "claims_typed",
    "verification.claim.verified": "claims_verified",
    "verification.claim.failed": "claims_failed",
    "verification.evidence.collected": "evidence_collected",
    "verification.conflict.detected": "conflicts_detected",
    "verification.conflict.resolved": "conflicts_resolved",
    "intelligence.object.created": "intelligence_objects_created",
    "intelligence.object.updated": "intelligence_objects_updated",
    "intelligence.object.reviewed": "intelligence_objects_reviewed",
    "research.packet.ready": "research_packets_ready",
    "content.draft.created": "drafts_created",
    "content.draft.updated": "drafts_updated",
    "content.draft.approved": "drafts_approved",
    "content.draft.rejected": "drafts_rejected",
    "content.published": "drafts_published",
    "content.publish.failed": "publish_failures",
    "content.draft.scheduled": "drafts_scheduled",
    "content.calendar.cancelled": "calendar_cancellations",
}

# automation_log.action_taken -> metric key (Source B).
ACTION_METRICS: dict[str, str] = {
    "notification_created": "notifications_created",
    "suppressed_by_preference": "notifications_suppressed_by_preference",
    "push_sent": "push_sent",
    "push_failed": "push_failed",
    "push_suppressed_quiet_hours": "push_suppressed_quiet_hours",
}

# digest_runs rows -> this metric (Source B; account->workspace via members).
METRIC_DIGESTS_SENT = "digests_sent"
