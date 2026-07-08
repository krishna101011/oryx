# ORYX — Phase 7 Architecture (Analytics)

**Phase:** 7 — Analytics
**Status:** DRAFT — Rev 1, pending real-code verification pass (NOT FROZEN)
**Depends on:** Phase 2 (ADR-014 event architecture), Phase 3 (intake events), Phase 4
(verification/research events), Phase 5 (publishing events), Phase 6 (automation/digest events)
**Unblocks:** Phase 8 (may reference engagement patterns), Phase 9 (may reference usage
analytics later)

Phase 7 is the *measurement* layer. It answers "what happened, how often, and is it trending"
across everything Phases 2–6 already built. It reads. It does not gather, verify, create, or
send anything.

---

## 1. Why Phase 7 Exists

### 1.1 The problem it solves
By Phase 6, ORYX has five phases' worth of continuous activity — intake events, verification
outcomes, published content, automation decisions — and no way to answer "is this actually
working" without a manual database query.

### 1.2 What Phase 7 deliberately is NOT (per the original blueprint)
- NOT a new ingestion mechanism — Phase 3 owns how information enters the system.
- NOT a content creation engine — Phase 5 owns drafting/publishing.
- NOT the training/education product — that's Phase 8.
- NOT load-bearing for any other phase's correctness — analytics is observational; if Phase 7
  goes down, nothing else should break.

### 1.3 Why now
Phase 6 makes the platform proactive. The natural next question is whether that proactivity is
actually valuable. Waiting longer means losing historical data in the shape analytics needs —
aggregates can only be computed from the moment collection starts.

---

## 2. Core Architectural Decision: Event-Driven Rollups, Not Query-Time Aggregation

Worth its own ADR — confirm the real next ADR number before Code writes it (do not assume a
number).

**Option A — Query-time aggregation.** Compute every dashboard number live via aggregate SQL
over activity_inbox / automation_log / digest_runs / content/publishing tables directly.
Simple, no new subscriber — but slows as history grows, and couples analytics-read load to the
same tables the live product depends on.

**Option B — Event-driven incremental rollups (RECOMMENDED).** Phase 7 subscribes to the same
ADR-014 event bus every other phase already publishes to — exactly what ADR-014 anticipated
("Phase 7 reads every event for analytics") — and maintains its own denormalized rollup
tables, updated incrementally as events arrive. Same pattern NotificationDispatcher already
proved for automation_log, just building counters/time-series instead of decision rows.

**Decision: Option B.** It matches the codebase's existing architectural style exactly, and
it's the design ADR-014 already gestured at before Phase 3 was built.

---

## 3. Data Model

### 3.1 New tables — Wave A

`analytics_events_raw` — NOT a full re-store of every event (that would just be a second
ingestion layer, explicitly forbidden). A lightweight, append-only fact: an event of type X
happened for account Y at time Z. Columns: id, account_id, workspace_id, event_type (text,
must match real frozen event bus names — verify, don't invent), occurred_at.

`analytics_rollups_daily` — one row per (account_id, metric_key, date), numeric value. Every
chart in Phase 7 is a query over this single table, grouped by date range.

Metric keys, Wave A scope (confirm every one against real current event names first):
- intake_items_received
- verification_conflicts_detected / verification_conflicts_resolved
- drafts_created / drafts_published
- notifications_dispatched / notifications_suppressed
- digests_sent

### 3.2 Later tables — Wave B/C, tentative, NOT built in Wave A
- `analytics_publishing_performance` — per-piece engagement over time. Flag plainly if no real
  engagement signal (views, opens) exists yet beyond "published: yes/no" — do not invent a
  fake metric to fill the gap.
- `analytics_cohorts` — deferred. A single-workspace product has a cohort of one; this table's
  real value only exists once Team/Workspace multi-user genuinely ships. Do not build
  speculative cohort infrastructure for data that doesn't exist.

---

## 4. What Phase 7 Does / Does Not Do

**Does:** subscribe to the event bus and record lightweight facts; compute and store daily
rollups; serve a dashboard (KPI summary + engagement charts) reading only rollup tables; serve
research-usage and publishing-performance views to the extent real underlying data exists.

**Does NOT do:** new ingestion (Phase 3's domain); content creation/publishing logic (Phase
5's domain); training content (Phase 8's domain); cohort analytics requiring multiple real
workspaces (deferred to post-Team/Workspace); any external analytics vendor integration in
Wave A — first-party only. (Open question for the user, not decided here: is a future
external analytics vendor even wanted, or is homegrown sufficient indefinitely?)

---

## 5. Feature Flag
`ff_analytics` — already seeded OFF in Phase 2's migration. Activate only once Wave A has real
data to show — an empty dashboard is worse than no nav item at all.

---

## 6. Wave Breakdown (proposed, subject to the verification pass)

**Wave A — Rollup foundation.** AnalyticsAggregator subscriber, both new tables, the §3.1
metric set computed and stored. No UI.

**Wave B — Dashboard UI + research/publishing views.** KPI cards + engagement charts over
Wave A's rollups; research usage and publishing performance to the extent real data supports
— flag, don't fake, any metric that can't be honestly computed yet.

**Wave C — Trends + whatever cohort work is actually possible today.** Trend detection
(up/down vs. prior period) over existing rollups. Cohort scope explicitly limited to "one
workspace" reality unless Team/Workspace has shipped by then — if it has, revisit this wave's
scope before starting rather than building against a stale assumption.

---

## 7. Open Questions — Confirm During the Verification Pass, Do Not Guess
1. Does any engagement/view signal exist for published content, or is there currently nothing
   to measure beyond "published: yes/no"?
2. Does anything resembling `analytics_events_raw` already exist, or is it built from scratch?
3. Confirm the complete, current, real list of event names in production — the catalog has
   grown since Phase 6 (e.g. a possible new push_suppressed_quiet_hours value) — before
   finalizing §3.1's metric list against it.
