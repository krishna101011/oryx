# ORYX — Phase 6 Architecture: Automation & Notifications
**Document:** `docs/PHASE_6_ARCHITECTURE.md`
**Version:** Rev 1 — Authoritative and Complete
**Status:** ARCHITECTURE — DRAFTED, PENDING FREEZE REVIEW
**Phase:** 6 — Automation · Notifications
**Prepared by:** Principal Architect
**Date:** 2026-06-30
**Phase 5 Anchor:** see `docs/PHASE_5_ARCHITECTURE.md`

---

## ⚠️ MUST-VERIFY-AGAINST-REAL-CODE — RESOLVE BEFORE ANY WAVE A WORK

Two items in this document are reconstructed from prior-phase
discussion, NOT independently re-verified against the current real
code. They are the **first** thing Wave A must resolve, before building
anything:

1. **The real event catalog (Section 2).** Grep every service's
   `events/constants.py` for the actual existing event constants and
   treat THAT list as ground truth — correct Section 2 if it is stale,
   incomplete, or wrong about an exact event name.
2. **The real `notification_frequency` field (Section 4.2).** Confirm
   the exact existing field name and its allowed values (assumed here
   to be `off` | `daily_digest` | `weekly_digest`) against the
   onboarding/preferences code — do not assume.

---

## 1. Vision & Scope

Every phase before this one (2 through 5) emits domain events to the
outbox. Nothing has consumed most of them yet. Phase 6's entire job is
to listen, and turn those events into something a person actually
sees: an in-app notification feed, configurable rules about what gets
surfaced, and a transparent log of what fired and why.

**Phase 6 owns exactly three things, all new:** an in-app notification
feed, per-account notification rules/preferences, and an automation
audit log. It does not own, and must never directly read, any other
phase's private tables (content_drafts, calendar_entries, claims,
intelligence_objects, etc.) — it only reads the events those phases
already emit, and where it needs more than an ID, it calls that
phase's existing public read API, the same boundary already
established at the Phase 5→6 handoff.

**Explicitly out of scope for Phase 6:**
- Team/Workspace member management (separate, future deepening of
  Phase 2 — do not fold it in here just because they sit near each
  other in navigation)
- Real email or push delivery (architected for, not built — see
  Section 4)
- Any new AI involvement of any kind
- Analytics/usage dashboards (Phase 7's job — Phase 6 may eventually
  emit its own events that Phase 7 consumes later, following the same
  pattern this phase itself is built on)

## 2. The Event Catalog Phase 6 Consumes

**MANDATORY FIRST STEP FOR WHOEVER IMPLEMENTS THIS:** the list below is
reconstructed from architecture discussion across prior phases, NOT
independently re-verified against the current real code. Before
building anything, grep the actual codebase for every existing event
constant across every service's `events/constants.py`, and treat
THAT list as ground truth — correcting this document's list if it's
stale, incomplete, or wrong about an exact event name.

Known/expected events as of this writing:
```
Phase 3 (Intake):     intake.sync_failed, (others — verify)
Phase 4 (Verify):      object.conflict.detected, object.conflict.resolved,
                       research.packet.ready, (others — verify)
Phase 5 (Create/Publish): content.draft.updated, content.draft.approved,
                       content.draft.rejected, content.draft.scheduled,
                       content.calendar.cancelled, content.published,
                       content.publish.failed
```

Each event type maps to a default in-app notification when no rule
exists yet for that account (see Section 3.2) — sensible defaults,
not silence, so the feature is useful from day one without requiring
setup.

## 3. Database Schema

### 3.1 — `notifications` (the feed)
```
id                 uuid pk
account_id         uuid not null fk→accounts
workspace_id       uuid not null fk→workspaces
category           notification_category_enum
                     ('security'|'verification'|'publishing'|'system')
severity           notification_severity_enum ('info'|'warning')
title              text not null
body               text not null
source_event_type  text not null   -- the outbox event name that caused this
source_event_id    uuid not null   -- traceable back to outbox_events
read_at            timestamptz nullable
created_at         timestamptz not null default now()
```
Index: `(account_id, read_at, created_at desc)` — the feed query and
unread-count query both need this shape.

### 3.2 — `notification_rules` (per-account configuration)
```
id            uuid pk
account_id    uuid not null fk→accounts
rule_type     notification_rule_type_enum (fixed, curated list — see
              below, NOT a generic trigger/action composer)
is_enabled    boolean not null default true
config        jsonb not null default '{}'   -- e.g. {"channel":"in_app"}
created_at, updated_at
UNIQUE(account_id, rule_type)
```

**Deliberately NOT a generic rule engine.** Per the design arc's own
guidance ("resist building a complex flow-chart editor"), `rule_type`
is a fixed enum mapping 1:1 to the event catalog above (e.g.
`draft_approved`, `conflict_detected`, `publish_failed`,
`scheduled_publish_succeeded`) — each one a simple on/off toggle, not
a composable condition. If a real need for genuinely conditional rules
emerges later, that's a deliberate future expansion, not a v1 default.

A missing row for a given `(account_id, rule_type)` means "default
enabled, in-app channel" — rules only need to exist as rows when
someone actually changes the default, keeping the table small.

### 3.3 — `automation_log` (transparency/audit)
```
id                  uuid pk
account_id          uuid not null
workspace_id        uuid not null
rule_id             uuid nullable fk→notification_rules
                     (null when a default fired, no explicit rule yet)
triggered_by_event_type  text not null
triggered_by_event_id    uuid not null
action_taken        text not null  -- e.g. "notification_created"
created_at          timestamptz not null default now()
```
Every single notification creation gets a matching log row — this is
the "why did I get this" answer surfaced later in the Automation Hub.

## 4. The Two Worker Processes

Both follow the EXACT existing standalone-worker-process pattern
(intake scheduler, queue drainer, calendar scheduler) — same
`run_forever()`/`amain()` shape, same colocation via
`ORYX_DEV_MONOPROCESS=1` in local dev, registered in `main.py`'s
lifespan the same way. Do not invent a different mechanism.

### 4.1 — NotificationDispatcher
Subscribes to the outbox events in Section 2 (via whatever the
existing handler-registration mechanism actually is — Phase 4's
`ObjectConflictProjector` is the precedent to follow, not reinvent).
For each event: resolve the affected account(s) for that
workspace (currently 1:1, architect this as "all accounts in the
workspace" even though that's always one row today — this is exactly
the kind of forward-compatibility that avoids rework when Team ships).
Check `notification_rules` for that account/rule_type (missing row =
default enabled). If enabled: insert a `notifications` row, insert a
matching `automation_log` row, in one transaction.

### 4.2 — DigestWorker
Reads the notification_frequency preference already collected at
onboarding (`off` | `daily_digest` | `weekly_digest` — confirm the
exact existing field name and values, don't assume). On its own
schedule (daily tick checks accounts due for a daily digest; same
worker also checks weekly-due accounts), bundles each account's unread
notifications since their last digest into a single digest-style
notification entry, rather than emailing anything — **email/push
delivery is explicitly NOT built in Phase 6**, only the in-app
bundling logic. The `channel` field already in `notification_rules.config`
anticipates real delivery channels being added later without a schema
change.

## 5. API Surface

```
GET  /v1/notifications              (paginated, filter by category/read state)
PATCH /v1/notifications/{id}        (mark read)
POST /v1/notifications/mark-all-read

GET  /v1/notification-rules         (effective rules — including unset
                                      defaults, resolved, so the UI never
                                      has to know about the "missing row
                                      = default" convention itself)
PATCH /v1/notification-rules/{rule_type}   (enable/disable, set config)

GET  /v1/automation-log             (paginated, the transparency view)
```

## 6. Mobile Screens

- **Notification Center** — a feed, not a settings page, grouped by
  category, unread shown via a small accent dot (not a loud badge
  count crowding the tab bar), tapping an entry navigates to its
  source object via the relevant phase's existing detail screen.
- **Notification Preferences** (Settings, deepened) — the existing
  frequency setting plus a per-category toggle list driven by
  `GET /v1/notification-rules`.
- **Automation Hub** — two tabs: Rules (the toggle list, same screen
  data as Preferences but framed for power users) and Log (the
  automation_log feed, read-only, "here's what fired and why").

## 7. Wave Breakdown

- **Wave A** — Migration, NotificationDispatcher, default-enabled
  behavior for the full real event catalog, GET/PATCH notification
  endpoints, Notification Center screen. End-to-end: a real event
  fires, a real notification appears in the feed.
- **Wave B** — notification_rules CRUD, per-category toggle UI,
  deepened Notification Preferences screen, rule resolution logic
  (missing row = default) properly tested.
- **Wave C** — DigestWorker, automation_log, Automation Hub screen
  (Rules + Log tabs). End-to-end: disabling a rule actually suppresses
  a notification, and the log explains why nothing fired.
- **Wave D** — Hardening: full pipeline test (a real event from
  EVERY phase's catalog correctly produces or correctly suppresses a
  notification per rule state), ADRs, freeze.

## 8. Phase 6 → Phase 7 Boundary

Phase 6 should itself emit a small event catalog of its own
(`notification.created`, `automation_rule.changed`) that Phase 7
(Analytics) can later subscribe to for usage metrics — continuing the
exact same event-driven boundary discipline this phase was built on,
not a special exception for whichever phase comes last.
