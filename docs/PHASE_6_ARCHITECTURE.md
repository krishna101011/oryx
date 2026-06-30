# ORYX — Phase 6 Architecture: Automation & Notifications (Rev 2)
**Document:** `docs/PHASE_6_ARCHITECTURE.md`
**Version:** Rev 2 — supersedes Rev 1 in full
**Status:** ARCHITECTURE — FROZEN (frozen 2026-06-30). Rev 1's
"three new tables" premise was proven false by direct code investigation
in two passes; both items flagged at end of pass 1 were resolved with
evidence in pass 2 — see Revision Note at the bottom.
**Phase:** 6 — Automation · Notifications
**Prepared by:** Principal Architect
**Date:** 2026-06-30
**Verification Anchor:** commit `6ffde15`
**Phase 5 Anchor:** see `docs/PHASE_5_ARCHITECTURE.md`

---

## 1. Revised Vision & Scope

Phase 2 already built real, working infrastructure for this phase and never
finished wiring it up: `activity_inbox` (the feed, reads/mark-read fully
functional), `alert_preferences` (a per-category, per-channel preference
matrix with quiet hours), and `alert_devices` (push token registration) all
exist today. **Nothing writes into `activity_inbox`. Nothing calls the push
provider. Phase 6's real job is to build the missing writer and the missing
delivery, not to build a parallel system.**

This is now smaller than originally drafted in one place (no new
feed/preference tables) and larger in another (real FCM/APNs delivery,
confirmed in scope per the project owner's decision below).

**Phase 6 owns, all new:**
- The `NotificationDispatcher` worker (the missing writer)
- The `DigestWorker` (bundles daily/weekly digest rows)
- Real push provider implementations (FCM, APNs) replacing the Phase 2
  `LogOnlyPushProvider` stub
- The `automation_log` table and its read view (the one genuinely new
  piece of storage)
- Four new columns on the existing `activity_inbox` table

**Explicitly still out of scope:** Team/Workspace, analytics dashboards, any
new AI involvement — unchanged from Rev 1.

## 2. Event Catalog — Verified Against Real Code

Authoritative as of the verification pass (commit 6ffde15). Re-confirm
against `events/constants.py` again at the start of Wave A in case anything
shipped between now and then — do not treat this as permanently frozen
truth, only as accurate at time of writing.

| Real event | Source | `activity_type` category | Severity |
|---|---|---|---|
| `intake.item.received` | Phase 3 | system | info |
| `verification.conflict.detected` | Phase 4 | verification | warning |
| `verification.conflict.resolved` | Phase 4 | verification | info |
| `verification.claim.failed` | Phase 4 | verification | error |
| `verification.evidence.collected` | Phase 4 | verification | info |
| `intelligence.object.*` (family) | Phase 4 | verification | info |
| `content.draft.created` | Phase 5 | publishing | info |
| `content.draft.updated` | Phase 5 | publishing | info |
| `content.draft.approved` | Phase 5 | publishing | info |
| `content.draft.rejected` | Phase 5 | publishing | warning |
| `content.draft.scheduled` | Phase 5 | publishing | info |
| `content.calendar.cancelled` | Phase 5 | publishing | info |
| `content.published` | Phase 5 | publishing | info |
| `content.publish.failed` | Phase 5 | publishing | error |

`security` (existing category, already used for auth events) is untouched —
Phase 6 does not add to it; it already exists from Phase 2's auth work.

## 3. Database Schema

### 3.1 — `activity_inbox` (ALTER, not CREATE)

```sql
ALTER TABLE activity_inbox
  ADD COLUMN severity activity_severity_enum NOT NULL DEFAULT 'info';
  -- new enum: 'info' | 'warning' | 'error'
ALTER TABLE activity_inbox
  ADD COLUMN source_event_type text NULL;
ALTER TABLE activity_inbox
  ADD COLUMN source_event_id uuid NULL;
```

Widen the existing `activity_type` enum additively:
```sql
ALTER TYPE activity_type ADD VALUE 'verification';
ALTER TYPE activity_type ADD VALUE 'publishing';
```

**Confirmed via direct investigation (corrected from Rev 2's guess):**
`instant_alert`/`daily_digest`/`weekly_digest` are NOT currently used
anywhere — never queried, never written, reserved enum slots explicitly
tagged `// Phase 6` in the TypeScript mirror. Rev 2 incorrectly assumed
these already represented bundled digest rows; they don't, they're
simply unbuilt. Phase 6 gives them real meaning for the first time:
`daily_digest`/`weekly_digest` become bundle-row markers written only by
`DigestWorker` on `activity_inbox` (Section 4.2). `instant_alert` is not
used by Phase 6 at all — see the usage-convention decision below.

**Resolved usage convention (new decision, closes Rev 2's open question):**
`alert_preferences.type` already has a separate `frequency` column
(`off/instant/daily/weekly`) covering cadence — so Phase 6 only ever
reads/writes `alert_preferences` rows using the four real content
categories (`security`/`system`/`verification`/`publishing`).
`instant_alert`/`daily_digest`/`weekly_digest` stay untouched on that
table; `frequency` already does that job. On `activity_inbox`, those same
three values get used for the row's actual *kind*: a category value for a
single categorized item, or `daily_digest`/`weekly_digest` for a bundle
row with no single category (it spans several). Six shared enum values,
two tables, two distinct and non-conflicting jobs.

New index, replacing the existing `(account_id, created_at)` index if it
doesn't already serve unread-filtering well:
```sql
CREATE INDEX ix_activity_account_unread
  ON activity_inbox (account_id, read_at, created_at DESC);
```
Confirm with `EXPLAIN` during Wave A whether the existing index is
sufficient before assuming a new one is needed — don't add an index
speculatively if the existing one already serves the real query well.

### 3.2 — `alert_preferences` (NO SCHEMA CHANGE — reused as-is)

The existing `(account_id, type, channel)` matrix with `frequency` and
`quiet_hours` is sufficient for per-category, per-channel control. No new
table, no new columns. Phase 6's only job here is to make sure
`type` values of `verification`/`publishing` resolve sensibly when no row
exists yet for a given account (same "missing row = default" pattern as
Rev 1 proposed, just applied to the real table instead of a new one) —
confirm the existing read path already does this gracefully, fix if not.

### 3.3 — `alert_devices` (NO SCHEMA CHANGE — reused as-is)

Already correct and sufficient: platform, push_token, disabled_at. No
changes needed.

### 3.4 — `automation_log` (NEW — the one genuinely new table)

```
id                       uuid pk
account_id               uuid not null
workspace_id             uuid not null
activity_inbox_id        uuid nullable fk to activity_inbox
                          (null when suppressed by preference - see below)
triggered_by_event_type  text not null
triggered_by_event_id    uuid not null
action_taken             text not null
  -- 'notification_created' | 'suppressed_by_preference' |
  -- 'push_sent' | 'push_failed'
created_at               timestamptz not null default now()
```

Every dispatcher decision gets a row here — including suppressions. This
is what makes the Automation Hub's "why didn't I get this" answer
possible, not just "why did I."

### 3.5 — Retention (carried forward from the verification pass, unchanged)

Deferred to Wave D. No cleanup logic in Waves A through C. Stated as a
decision, not a silent gap.

## 4. Workers — Confirmed Scope: Real Push Included

All workers follow the existing standalone-process pattern (intake
scheduler, queue drainer, calendar scheduler) — same `run_forever()`/
`amain()` shape, same `ORYX_DEV_MONOPROCESS=1` colocation in local dev.

### 4.1 — NotificationDispatcher

Subscribes to the event catalog in Section 2. For each event:
1. Resolve affected account(s) for the workspace (architect as "all
   accounts in the workspace," same forward-compatibility note as Rev 1,
   unchanged reasoning).
2. Look up `alert_preferences` for the account/category/channel='in_app'
   combination. If `frequency != 'off'`: insert into `activity_inbox`
   (with the new columns populated), insert an `automation_log` row with
   `action_taken='notification_created'`. If `frequency == 'off'`: insert
   ONLY an `automation_log` row with `action_taken='suppressed_by_preference'`,
   `activity_inbox_id=null`.
3. Separately check the same account/category/channel='push' combination.
   If enabled and not in quiet hours: call the real push provider
   (Section 4.3), log `push_sent`/`push_failed` accordingly.

### 4.2 — DigestWorker

Reads accounts where `alert_preferences.frequency` is `daily` or `weekly`
for a given category/channel. On schedule, bundles unread items since the
last digest into one NEW `activity_inbox` row with `type='daily_digest'`
or `'weekly_digest'`. This is genuinely new behavior — confirmed via
investigation that nothing currently writes these values; Phase 6 is the
first thing to ever populate them, consistent with their `// Phase 6` tag
in the TypeScript types. Real digest *delivery* (an actual email) is
still out of scope — the digest is an in-app bundle and/or a push
notification pointing at it, not an emailed summary. Flag this distinction
explicitly in Wave A so it's not assumed to mean "now we send emails too."

### 4.3 — Push Providers (NEW — replacing the Phase 2 stub)

Implement `FCMProvider` (Android + Web push) and `APNsProvider` (iOS)
against the existing `PushProvider` Protocol from `providers/push/base.py`
— do not change that Protocol's shape, implement against it.

**Follow the exact pattern already proven in Phase 5 Wave D** for
Twitter/LinkedIn/Notion: write the real, complete provider implementation
code, test it against a real or faked HTTP layer (no live Firebase/Apple
account needed to prove the code is correct), and flag clearly that real
credentials (a Firebase service account, an Apple Push key) must be
provisioned before this leaves local development — the same honest,
established pattern as `ORYX_PUBLISH_KEY` and the Anthropic API key
earlier in this project. `LogOnlyPushProvider` remains the dev-environment
default; real providers activate via the same kind of environment-gated
switch already used for `AI_PROVIDER`.

## 5. API Surface

```
GET   /v1/activity                          (existing - confirm it already
                                              supports category/severity
                                              filters once Section 3.1's
                                              columns land; extend if not)
PATCH /v1/activity/{id}                      (existing - mark read)
POST  /v1/activity/mark-all-read             (existing - confirm exact name)

GET   /v1/activity/alerts/preferences        (CONFIRMED real path, existing
                                              - list_alert_prefs. Returns
                                              only rows that exist today, no
                                              resolved-defaults layer. Phase
                                              6 extends this same endpoint to
                                              backfill sensible defaults for
                                              any missing category/channel
                                              combination server-side -
                                              same centralize-resolution-once
                                              pattern as Phase 5's
                                              resolve_template, rather than
                                              duplicating default logic into
                                              the mobile client.)
PUT   /v1/activity/alerts/preferences/{type}/{channel}
                                              (CONFIRMED real path and verb,
                                              existing - upsert_alert_pref,
                                              ON CONFLICT DO UPDATE. Phase 6
                                              only ever calls this with
                                              type in {security, system,
                                              verification, publishing} -
                                              never with the cadence-label
                                              values, per the Section 3.1
                                              usage convention.)

POST  /v1/activity/devices                   (existing - push token reg)
DELETE /v1/activity/devices/{id}             (existing)

GET   /v1/automation-log                     (NEW - the transparency view)
```

## 6. Mobile Screens

- **Notification Center** — reads `/v1/activity`, grouped by category,
  unread via a small accent dot. **Verify whether Phase 2 already built
  any UI against this API** before assuming this screen is net-new —
  the backend existing for months without a consuming screen is possible
  but worth a quick check, not an assumption either way.
- **Notification Preferences** (Settings) — per-category by per-channel
  toggle grid (verification/publishing/system by in-app/push/email) plus
  quiet-hours range picker, against the real `alert_preferences` shape.
  Same verify-before-build caveat as above.
- **Automation Hub** — Rules tab (same data as Preferences, reframed) +
  Log tab (the new `automation_log` feed, including suppressed entries
  so a user can genuinely see why something didn't fire).

## 7. Wave Breakdown

- **Wave A** — Confirm the `activity_type` row-shape interpretation
  (Section 3.1) and confirm whether `/v1/alert-preferences` already
  exists (Section 5) BEFORE writing migration code. Then: migration
  (ALTER activity_inbox, widen enum, create automation_log),
  NotificationDispatcher, in-app delivery path only (no push yet).
  End-to-end: a real event fires, a real row appears via the real
  existing `/v1/activity` API.
- **Wave B** — DigestWorker, confirm/build Notification Preferences UI,
  Automation Hub (both tabs).
- **Wave C** — Real FCM + APNs providers, wired into the dispatcher,
  tested via fakes, credential-provisioning requirement clearly
  documented (not blocking Wave C's completion, same pattern as Wave D's
  external-credential channels).
- **Wave D** — Hardening: full pipeline test (a real event from every
  category correctly produces, suppresses, or pushes per real preference
  state), ADRs, freeze.

## 8. Phase 6 to Phase 7 Boundary

Unchanged from Rev 1: Phase 6 emits its own small event catalog
(`notification.created`, `automation_rule.changed`) for Phase 7 to
consume later, continuing the same boundary discipline.

---

## Revision Note

Rev 1 assumed Phase 6 was building entirely new storage. A first
investigation pass (commit 6ffde15) found Phase 2 had already built the
feed, the preference matrix, and the device-registration table — fully
wired on the read side, completely unwired on the write side, with push
delivery explicitly named as Phase 6's job in the original Phase 2 code
comments. That pass left two open questions for Rev 2; a second
investigation pass resolved both with direct evidence: the real
`alert_preferences` API paths and verb (`PUT`, not the assumed `PATCH`),
and confirmation that the digest-cadence enum values were never
previously used at all — Rev 2's initial guess that they already
represented bundled rows was wrong and has been corrected. Both
corrections are folded into this document directly. Two confirmed product
decisions carried through unchanged: reuse the existing per-category
preference granularity rather than building finer per-event rules, and
include real push delivery (FCM/APNs) rather than deferring it. Treat Rev
1 as fully superseded.
