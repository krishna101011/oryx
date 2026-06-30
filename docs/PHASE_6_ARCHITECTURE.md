# ORYX — Phase 6 Architecture: Automation & Notifications
**Document:** `docs/PHASE_6_ARCHITECTURE.md`
**Version:** Rev 1 — Authoritative and Complete
**Status:** ARCHITECTURE — DRAFTED, PENDING FREEZE REVIEW
**Phase:** 6 — Automation · Notifications
**Prepared by:** Principal Architect
**Date:** 2026-06-30
**Phase 5 Anchor:** see `docs/PHASE_5_ARCHITECTURE.md`

---

## ✅ REAL-CODE VERIFICATION (completed 2026-06-30, pre-freeze)

The two flagged items have now been verified against the live codebase
(not deferred to Wave A). Results — and one finding the draft did not
anticipate:

**1. Event catalog (Section 2) — the draft was WRONG in several places.**
Verified by reading every event-constants module
(`*/events/constants.py` **plus** `intake/events_constants.py`, which
does not follow the directory convention). Corrections, all reflected
in the rewritten Section 2:
- `intake.sync_failed` is **NOT an outbox event** — it is a
  `logger.warning(...)` call (`intake/sync_runner.py:314`). Phase 6
  cannot subscribe to it. The real Phase 3 outbox event is
  `intake.item.received`.
- Conflict events are `verification.conflict.detected` /
  `verification.conflict.resolved`, **not** `object.conflict.*`.
- Phase 4 emits **more** than the draft listed: the full
  `verification.claim.*` and `verification.evidence.collected` and
  `intelligence.object.*` families also exist.
- Phase 5 also emits `content.draft.created` (draft omitted it).

**2. `notification_frequency` (Section 4.2) — the draft's values were WRONG.**
The real column (`core/models.py:191`, enum `notification_frequency`)
is `off | instant | daily | weekly`, default `daily` — **not**
`off | daily_digest | weekly_digest`. Those `*_digest` strings are
values of a *different* enum, `activity_type`, used by the tables below.

**3. ⚠️ UNANTICIPATED FINDING — pre-existing notification infrastructure
already exists and overlaps this entire phase. ARCHITECT MUST RECONCILE
BEFORE FREEZE.**
Phase 2/4 already shipped, wired, and exposed via `/v1/activity/*`
(`services/activity/router.py`):
- `activity_inbox` — an in-app feed with `type/title/body/data/read_at`
  + `GET /v1/activity/inbox`, `POST /v1/activity/inbox/{id}/read`,
  and an `unreadCount`. This is **the same thing** the draft proposes
  to build new as `notifications` + `GET /v1/notifications`.
- `alert_preferences` — per `(account, type, channel)` rows with
  `frequency` + `quiet_hours`. Overlaps the proposed
  `notification_rules`.
- `alert_devices` — push-token registration (router comment literally
  says "delivery is Phase 6").
- `shared-types/src/activity.ts` already tags `daily_digest` /
  `weekly_digest` with `// Phase 6` comments.

  This is exactly the describe-vs-built drift the project tracks. The
  draft's premise ("Phase 6 owns three things, all new") is **false** —
  the feed and preference tables substantially already exist. The
  decision of whether Phase 6 *extends* `activity_inbox` /
  `alert_preferences` or *replaces* them with `notifications` /
  `notification_rules` is an architecture call for freeze review (Claude
  Chat role), not something to silently resolve in implementation. The
  rest of this document below is **left as originally drafted** so the
  architect can see the original intent against this finding; do not
  treat Sections 3 & 5 as final until this is reconciled.

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

**VERIFIED against the live codebase 2026-06-30** (see the verification
block at the top). This is the real, ground-truth list of outbox event
names and the constant that defines each. Events are registered for
consumption via the event bus (`bus.subscribe(...)` in
`services/queue/drainer.py` / `build_bus()`); that — not a new
mechanism — is how the NotificationDispatcher subscribes.

| Real event name | Constant | Phase / source | Default category | Default severity |
|---|---|---|---|---|
| `intake.item.received` | `INTAKE_ITEM_RECEIVED` | 3 — intake | system | info |
| `verification.claim.extracted` | `CLAIM_EXTRACTED` | 4 — claims | verification | info |
| `verification.claim.typed` | `CLAIM_TYPED` | 4 — claims | verification | info |
| `verification.evidence.collected` | `EVIDENCE_COLLECTED` | 4 — evidence | verification | info |
| `verification.claim.verified` | `CLAIM_VERIFIED` | 4 — verification | verification | info |
| `verification.claim.failed` | `CLAIM_FAILED` | 4 — verification | verification | **error** |
| `verification.conflict.detected` | `CONFLICT_DETECTED` | 4 — conflicts | verification | warning |
| `verification.conflict.resolved` | `CONFLICT_RESOLVED` | 4 — conflicts | verification | info |
| `research.packet.ready` | `PACKET_READY` | 4 — research | verification | info |
| `intelligence.object.created` | `OBJECT_CREATED` | 4 — intelligence | verification | info |
| `intelligence.object.updated` | `OBJECT_UPDATED` | 4 — intelligence | verification | info |
| `intelligence.object.reviewed` | `OBJECT_REVIEWED` | 4 — intelligence | verification | info |
| `content.draft.created` | `DRAFT_CREATED` | 5 — drafts | publishing | info |
| `content.draft.updated` | `DRAFT_UPDATED` | 5 — drafts | publishing | info |
| `content.draft.approved` | `DRAFT_APPROVED` | 5 — drafts | publishing | info |
| `content.draft.rejected` | `DRAFT_REJECTED` | 5 — drafts | publishing | warning |
| `content.draft.scheduled` | `CALENDAR_ENTRY_SCHEDULED` | 5 — calendar | publishing | info |
| `content.calendar.cancelled` | `CALENDAR_ENTRY_CANCELLED` | 5 — calendar | publishing | warning |
| `content.published` | `CONTENT_PUBLISHED` | 5 — publishing | publishing | info |
| `content.publish.failed` | `CONTENT_PUBLISH_FAILED` | 5 — publishing | publishing | **error** |

Note: `intake.sync_failed` from the original draft is intentionally
absent — it is a log line, not an outbox event (see verification block).
A failed sync that should reach the user must first be promoted to a
real outbox event in the intake service; that is a prerequisite, not
something Phase 6 can subscribe to today.

**Category mapping rationale.** The proposed `category` enum is
`security | verification | publishing | system`. The mapping above is
deliberate, not mechanical: everything in the `verification.*` and
`intelligence.*` families is the Verify/Analyze surface → `verification`;
everything in the `content.*` family (draft lifecycle, calendar,
publishing) is the Create/Publish surface → `publishing`;
`intake.item.received` is plumbing the user did not explicitly act on →
`system`. No current outbox event maps to `security` — that category is
reserved for the auth/session events the existing `activity_inbox`
already records as `type='security'` (another reconciliation point with
the finding above).

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
severity           notification_severity_enum ('info'|'warning'|'error')
title              text not null
body               text not null
source_event_type  text not null   -- the outbox event name that caused this
source_event_id    uuid not null   -- traceable back to outbox_events
read_at            timestamptz nullable
created_at         timestamptz not null default now()
```
Index: `(account_id, read_at, created_at desc)` — the feed query and
unread-count query both need this shape.

**Severity decision (resolved pre-freeze): three levels, not two.**
The draft proposed `info | warning`. Verification of the real event
catalog surfaced two genuine *failure* events — `content.publish.failed`
and `verification.claim.failed` — that are categorically different from
a "warning". A warning is "something needs your attention" (a conflict
was detected, a draft was rejected, a scheduled post was cancelled); a
failure is "the system tried to do a thing on your behalf and it did not
work." Collapsing those into the same level would make the only two
events a user must actually act on indistinguishable from advisory
notices. So the enum is `info | warning | error`, with `error` reserved
for the `*.failed` events (see the per-event mapping in Section 2). If
`intake.sync_failed` is later promoted to a real outbox event, it slots
into `error` too.

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

### 3.4 — Retention

Retention/cleanup for `notifications` and `automation_log` is
**deferred to Wave D hardening**. Waves A–C ship no cleanup logic, no
TTL, and no archival — rows accumulate unbounded by design during the
build-out, and the pruning policy (age cap, per-account row cap, or
both) is decided and implemented in Wave D once the real write volume
is observable. This is a stated decision, not an oversight.

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
Reads the `notification_frequency` preference already collected at
onboarding. **VERIFIED:** the real column is
`user_preferences.notification_frequency` (`core/models.py:191`), an
enum `notification_frequency` with values **`off | instant | daily |
weekly`**, default `daily` — not the `*_digest` strings the draft
assumed (those belong to the separate `activity_type` enum). The
DigestWorker bundles for `daily` and `weekly`; `instant` means
"dispatch immediately, no digest" (handled by the NotificationDispatcher
path, not here); `off` suppresses. On its own schedule (daily tick
checks accounts whose frequency is `daily`; same worker also checks
`weekly`-due accounts), it bundles each account's unread notifications
since their last digest into a single digest-style notification entry,
rather than emailing anything — **email/push delivery is explicitly NOT
built in Phase 6**, only the in-app bundling logic. The `channel` field already in `notification_rules.config`
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
