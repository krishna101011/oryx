# ORYX — Phase 7 Architecture (Analytics)

**Phase:** 7 — Analytics
**Status:** DRAFT — Rev 2, verified against real code (supersedes Rev 1 in full)
**Verification anchor:** commit 1cf197d's own recon findings (Phase 7 Wave A prep)
**Depends on:** Phase 2 (ADR-014 event architecture), Phase 3–6 (all event sources + automation
tables)
**Unblocks:** Phase 8 (may reference engagement patterns), Phase 9 (may reference usage
analytics later)

Phase 7 is the *measurement* layer. It reads. It does not gather, verify, create, or send
anything, and its failure must never affect any other phase's correctness.

---

## Revision Note (why Rev 2 exists)

Rev 1 assumed Phase 7 could be built as a single, pure event-bus subscriber, following ADR-014's
"Phase 7 reads every event for analytics." That's true for 17 of the real 20 bus events — but
three of Rev 1's eight proposed metrics (notification dispatch/suppression outcomes, digest
sends) are produced by components that don't publish to the bus at all: `NotificationDispatcher`
consumes without publishing, and `DigestWorker` is a standalone scheduler (ADR-025 shape), not a
subscriber. Rev 2 corrects this to a two-source design: a real bus subscriber for genuine bus
events, and direct aggregation over `automation_log`/`digest_runs` (already idempotent tables)
for automation outcomes — no new storage needed for those. Rev 2 also drops per-account
attribution (bus events are workspace-scoped, not account-scoped) and expands the metric set to
include the real research/verification funnel that Rev 1 missed entirely.

---

## 1. Why Phase 7 Exists

### 1.1 The problem it solves
By Phase 6, ORYX has continuous activity across five phases and no way to answer "is this
working" without a manual query.

### 1.2 What Phase 7 deliberately is NOT
- NOT a new ingestion mechanism (Phase 3's domain).
- NOT content creation/publishing logic (Phase 5's domain).
- NOT the training/education product (Phase 8's domain).
- NOT load-bearing for any other phase — purely observational.

### 1.3 Why now
Waiting longer loses historical data in the shape analytics needs — aggregates can only be
computed from the moment collection starts.

---

## 2. Core Architectural Decision: Two Sources, One Read Model

**Source A — Bus-derived facts (Wave A, new).** A real subscriber, `AnalyticsAggregator`,
registered exactly like `NotificationDispatcher` (`build_bus()` in `drainer.py`, per-event
`subscribe()` calls, same locally-scoped-handler-import pattern to avoid the
`PermanentDeliveryError` circular import). Its ONLY job: for each of the 17 real bus events,
write one row to `analytics_events_raw`, workspace-scoped, with a unique constraint making
redelivery a safe no-op — confirm at build time what stable identifier a delivered bus event
actually carries (the outbox row's own id is the likely candidate; verify, don't assume the
column name) and key the constraint on that.

**Source B — Existing-table aggregation (Wave A, no new subscriber, no new storage).** For
automation outcomes that never touch the bus — dispatch/suppression decisions and digest sends —
Phase 7 reads directly from `automation_log` and `digest_runs`, which are already idempotent by
their own unique constraints. No duplication, no new idempotency problem to solve.

**The read model — `analytics_rollups_daily`.** One row per (workspace_id, metric_key, date),
refreshed periodically by a small tick-based worker (same shape as the calendar/digest
schedulers — confirm the exact precedent file at build time) that recomputes each day's numbers
as a fresh aggregate query over Source A and Source B. Nothing increments; everything is
recomputed, so re-running a refresh is always safe.

*Worth its own ADR — ADR-047 (confirmed as the next available number).*

---

## 3. Data Model

### 3.1 `analytics_events_raw` (new, Wave A)
Columns: id, workspace_id (NOT account_id — bus events are workspace-scoped; per-account
attribution is deliberately deferred, see §4), event_name (must match the real 20-event
catalog verbatim), occurred_at, and a stable dedup key (confirm the real source field at build
time) under a unique constraint.

### 3.2 `analytics_rollups_daily` (new, Wave A)
One row per (workspace_id, metric_key, date), numeric value. Every Wave B chart queries this
table only — never the raw sources directly.

### 3.3 Metric keys, Wave A — grounded in the real 20-event catalog, not invented

**Intake:** intake_items_received (intake.item.received)

**Verification/research funnel** (this is what "research usage" actually measures — Rev 1 had
almost none of this):
claims_extracted, claims_typed, claims_verified, claims_failed, evidence_collected,
intelligence_objects_created/updated/reviewed, research_packets_ready
(research.packet.ready — the only direct research-usage signal that exists; do not build a
Wave B "research usage" view without this one)

**Content/publishing funnel:**
drafts_created, drafts_updated, drafts_approved, drafts_rejected, drafts_published
(content.published), publish_failures (content.publish.failed — the natural denominator for a
success rate), drafts_scheduled, calendar_cancellations

**Automation (Source B — from automation_log/digest_runs, NOT bus events):**
notifications_created, notifications_suppressed_by_preference, push_sent, push_failed,
push_suppressed_quiet_hours (once that logging addendum lands), digests_sent — map these to
automation_log's real `action_taken` values at build time; do not invent new label strings that
don't match what's actually stored.

### 3.4 `analytics_publishing_performance` — explicitly demoted, not deferred silently
No engagement/view signal exists anywhere in the codebase today — the Publication model carries
only delivery lifecycle (status, external_id, external_url, attempt_count, published_at).
Wave B's publishing-performance view is therefore limited to delivery success rate
(drafts_published vs. publish_failures) and time-to-publish — NOT engagement, because there is
nothing to honestly measure yet. If real engagement data is ever wanted, that's a new decision
(possibly requiring a platform-side integration), not something to fake here.

### 3.5 `analytics_cohorts` — still deferred
Unchanged from Rev 1: a single-workspace product has a cohort of one. Do not build this until
Team/Workspace multi-user genuinely exists.

---

## 4. What Phase 7 Does / Does Not Do

**Does:** subscribe to the 17 real bus events and record idempotent workspace-level facts;
directly aggregate automation_log/digest_runs for automation metrics; refresh daily rollups on
a periodic tick; serve a dashboard reading only from rollups.

**Does NOT do:** new ingestion; content creation/publishing logic; training content; per-account
attribution (deferred); cohort analytics (deferred, needs Team/Workspace); fake engagement
metrics where no real signal exists; external analytics vendor integration in Wave A.

---

## 5. Feature Flag
`ff_analytics` — seeded OFF since Phase 2. Activate only once Wave A has real data to show.

---

## 6. Wave Breakdown

**Wave A — Rollup foundation.** `AnalyticsAggregator` bus subscriber + `analytics_events_raw`
(Source A), direct aggregation queries over `automation_log`/`digest_runs` (Source B), the
periodic rollup-refresh worker, `analytics_rollups_daily` populated for every §3.3 metric. No UI.

**Wave B — Dashboard UI + research/publishing views.** KPI cards + engagement charts over
Wave A's rollups. Research usage view built on the real verification/research funnel (§3.3).
Publishing view limited to delivery success rate + time-to-publish, per §3.4 — no fabricated
engagement numbers.

**Wave C — Trends.** Up/down-vs-prior-period detection over existing rollups. Cohort work stays
out of scope unless Team/Workspace has shipped by then — revisit explicitly before starting if so.

---

## 7. Confirm at Build Time (not guessed here)
1. The exact stable identifier a delivered bus event carries, for `analytics_events_raw`'s
   unique constraint.
2. The exact `automation_log.action_taken` string values currently in use, to map Source B
   metrics correctly.
3. The exact precedent file/shape for the periodic rollup-refresh worker (confirm which
   existing scheduler — calendar or digest — is the closer template).
