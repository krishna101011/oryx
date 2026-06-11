# Anant Capital — Phase 3 Architecture (FROZEN)

**Phase:** 3 — Intake Layer
**Status:** FROZEN — Revision 2
**Depends on:** Phase 1 (foundation), Phase 2 (identity, control plane, provider layer, ADR-014 event bus)
**Unblocks:** Phase 4 (Verify + Analyze + Research)

> Phase 3 is the *INPUT* stage of the product pipeline.
> It ingests, normalizes, dedupes, and queues — **nothing else**.
> No verification rules. No AI. No content surfacing.

---

## Change Log — Revision 2

Ten change requests applied after staff-engineer review. The footguns are removed; structural fixes land before implementation, not after.

| #    | Change                                                                                                                  | Sections affected      |
| ---- | ----------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| CR-1 | **Unified `intake_sources` operational table** replaces polymorphic `source_id` FK across Phase 2 selection tables       | §8, §11, §13, §14, §16 |
| CR-2 | **Two-tier dedupe fingerprint**: link-anchored when URL present; `(domain, title, date_bucket)` fallback for body-only items | §9                     |
| CR-3 | **Outbox retention + dead-letter table.** Cleanup job + `outbox_dead_letter` for poison events                          | §12                    |
| CR-4 | **Persistent webhook idempotency table** with TTL eviction; replaces hand-wavy "24h window"                              | §6, §17                |
| CR-5 | **Gmail `historyId` expiry recovery path** — on 404, fall back to label-bounded full pull and re-establish cursor       | §4                     |
| CR-6 | **Workspace deletion cascade** for `intake_credentials` — best-effort upstream revoke before DB delete                  | §17                    |
| CR-7 | **Scheduler and drainer are separate processes by default.** API process never blocks on intake                          | §14                    |
| CR-8 | **Manual ingestion = platform admin only.** Workspace admins do not see the surface                                     | §14, §15               |
| CR-9 | **Cursor pagination on all operational endpoints** (`/intake/items`, `/intake/sources/:id/audit`) reusing Phase 1 envelope | §14                    |
| CR-10| **RSS redirect handling.** 301 → persist new URL + audit; 302 → follow, do not persist                                  | §5                     |

**Why these changes improve maintainability:**

- **CR-1** removes the single largest structural footgun: a polymorphic FK has no DB-level constraint, makes joins ambiguous, and breaks down on cascade deletes. The unified `intake_sources` table gives the orchestrator one table to talk to.
- **CR-2** prevents body-only Gmail items from cross-day false-positive dedupes — a real product bug if shipped as drawn.
- **CR-3 / CR-4** turn two implicit "eventually grows forever" footguns into bounded, audited stores.
- **CR-5 / CR-10** add the recovery paths real vendors require; without them, sources go silently broken after a week.
- **CR-6** closes the orphaned-credential leak path on workspace delete.
- **CR-7** pins the deployment topology so an API restart doesn't pause every workspace's sync.
- **CR-8** narrows the blast radius of manual ingest to the only role that should have it.
- **CR-9** prevents an unbounded response on operational endpoints — a small fix that matters once a workspace has weeks of audit data.

---

## 1. Why the Intake Layer Exists

### 1.1 The problem it solves

Every later phase consumes facts that originated outside our system. Without a dedicated intake layer:

| Without intake               | Phase that pays the cost                                |
| ---------------------------- | ------------------------------------------------------- |
| Each phase re-implements fetching, retries, dedupe | 4 (verification) and 5 (content)        |
| No system of record for "what arrived"             | 7 (analytics) — cannot answer source-level questions |
| Vendor SDKs scatter across the codebase            | Every phase ships with a wider blast radius   |
| Phase 4's verifier sits next to raw vendor calls   | Trust policy becomes inseparable from transport |

Phase 3 means **every fact entering the platform comes through one door, gets one shape, gets stored once, and emits one event** for the rest of the system.

### 1.2 What it deliberately is NOT

- **Not the verification engine.** Confidence scoring is Phase 4.
- **Not the research workflow.** Saving and threading are Phase 4.
- **Not the AI layer.** No summarization, no classification.
- **Not user-facing content.** Mobile sees health + operational state.
- **Not write-back.** We never reply to email, never modify upstream state.

### 1.3 Why these boundaries matter

The architecture freezes the line between *what arrived* and *what we believe about it*. That line is what makes Phase 4's verification policy meaningful — it operates on a clean, immutable raw record, not on an inference.

---

## 2. Intake Architecture Diagram

```
              ┌─────────┐    ┌────────┐    ┌───────────┐    ┌─────────────┐
              │  Gmail  │    │  RSS   │    │ Webhooks  │    │  API Pulls  │
              └────┬────┘    └───┬────┘    └─────┬─────┘    └──────┬──────┘
                   │              │                │                  │
                   ▼              ▼                ▼                  ▼
              ┌────────────────────────────────────────────────────────────┐
              │              IntakeProvider (Protocol)                     │
              │   sync() / handle_webhook() / validate_config()            │
              └────────────────────────┬───────────────────────────────────┘
                                       │   RawItem
                                       ▼
                          ┌────────────────────────┐
                          │    Normalizer (v=N)    │   → NormalizedItem
                          └────────────┬───────────┘
                                       │
                                       ▼
                          ┌────────────────────────┐
                          │   Dedupe (two-tier)    │   provider-key + fingerprint
                          └────────────┬───────────┘
                                       │
                       ┌───────────────┼────────────────┐
                       ▼               ▼                ▼
              ┌──────────────┐  ┌────────────┐  ┌─────────────────┐
              │ intake_items │  │ normalized │  │ dedupe_index    │
              │  (immutable) │  │  (derived) │  │ + duplicates    │
              └──────┬───────┘  └─────┬──────┘  └─────────────────┘
                     └────────┬───────┘
                              │  (atomic with payload write)
                              ▼
              ┌──────────────────────────────┐
              │ outbox_events                │   intake.item.received
              │ (Stage B of ADR-014)         │
              └────────┬──────────────────┬──┘
                       │                  │ poison
                       ▼                  ▼
              ┌─────────────┐    ┌──────────────────┐
              │ OutboxDrainer│   │ outbox_dead_letter│
              │ (separate pid)│   └──────────────────┘
              └──────┬──────┘
                     │
                     ▼
            [ Phase 4 — Verification (subscribes) ]
```

```
       ┌─────────────────────────────────┐
       │  intake_sources (Phase 3)       │ ◄── one operational row per source
       │  unified; no polymorphic FK     │
       └────┬───────────────┬────────────┘
            │ origin_kind=catalog          │ origin_kind=custom
            ▼                              ▼
  workspace_sources (Phase 2)    workspace_custom_sources (Phase 2)
  (user-facing selection)        (user-facing custom URLs)
```

Three boundaries the diagram makes explicit:

1. **Vendor isolation** — every external system speaks only through one `IntakeProvider`.
2. **Persistence atomicity** — normalized + dedupe + outbox row are written in **one transaction**. Crashes can't desync them.
3. **Forward decoupling** — downstream phases subscribe; intake doesn't know they exist.

---

## 3. Provider Abstraction Design

Phase 2 shipped the provider pattern. Phase 3 extends it: **every inbound source is an `IntakeProvider`**.

### 3.1 The interface

```python
class IntakeProvider(Protocol):
    name: str                            # 'gmail', 'rss', 'webhook', 'api_pull'
    kind: IntakeSourceKind

    async def validate_config(
        self, config: dict[str, Any]
    ) -> ValidationResult: ...

    async def sync(
        self,
        *,
        workspace_id: UUID,
        intake_source_id: UUID,           # operational row (see CR-1 / §8)
        cursor: SyncCursor | None,
    ) -> AsyncIterator[RawItem]: ...

    async def handle_webhook(
        self,
        *,
        workspace_id: UUID,
        intake_source_id: UUID,
        headers: dict[str, str],
        body: bytes,
    ) -> AsyncIterator[RawItem]:
        raise NotImplementedFeatureError(...)
```

### 3.2 Contract guarantees

| Guarantee                                                              | Why                                               |
| ---------------------------------------------------------------------- | ------------------------------------------------- |
| `sync()` is async-iterable and pageable                                | Stream; never load thousands of items in memory   |
| Idempotent by `(intake_source_id, external_id)`                        | Restarts and double-runs cannot create duplicates |
| Cursor returned is monotonic per source                                | Resuming never skips                              |
| Vendor errors translate to `ProviderError(kind=…)`                     | Service code never sees a vendor exception        |
| Concurrency limit honored per provider instance                        | Vendors rate-limit; we respect their quota        |
| **No** business rules inside the provider                              | Verification / scoring / classification = later   |

### 3.3 Folder shape (per provider)

```
services/intake/providers/<vendor>/
├── base.py              # IntakeProvider subclass scaffolding
├── client.py            # vendor SDK / HTTP transport
├── auth.py              # OAuth flow, refresh, rotation
├── mapper.py            # vendor item → RawItem
├── sync.py              # pull loop, cursor, pagination
├── webhook.py           # signature verification + handler (where applicable)
└── config_schema.py     # pydantic model for per-source config
```

Adding a new vendor is a folder copy + replacements — never a refactor.

---

## 4. Gmail Intake Design

### 4.1 Why Gmail is primary

The user's intelligence is already curated in their inbox via labels. We honor that by reading; we never write.

### 4.2 Authentication

- OAuth 2.0 with **`gmail.readonly` scope only**
- Access tokens encrypted at rest (`intake_credentials.encrypted_token`)
- Refresh tokens encrypted with workspace-scoped key derived from `INTAKE_KMS_KEY`
- Token rotation per call; expired token → single refresh + retry
- **Refresh failure → source status `auth_required`** (per §10 classification); stop attempting until user reconnects

### 4.3 Sync model

| Stage      | When                  | How                                       |
| ---------- | --------------------- | ----------------------------------------- |
| **A. Polling** | Phase 3 ships this    | Every connected source polled every 5–15 min |
| **B. Push**    | Phase 3.x patch       | Gmail Pub/Sub via `users.watch()`         |

Provider contract is identical across stages. Pull works on any deployment; push is a latency optimization layered on later.

### 4.4 Cursor: Gmail `historyId`

- We store the latest `historyId` we've processed
- Each sync calls `users.history.list(startHistoryId=cursor)`
- Cursor advances atomically with the items consumed

### 4.5 `historyId` expiry recovery — CR-5

Gmail expires history records after ~7 days. If our cursor is too old, the API returns 404.

```
sync() encounters 404 from history.list
        │
        ▼
log event 'gmail.history_id_expired'  → audit_log + metric
        │
        ▼
Fall back: users.messages.list(label_ids=…, q="newer_than:<initial_lookback>d")
        │
        ▼
Process items via normal mapper path
        │
        ▼
Re-establish cursor from users.history.list(startHistoryId=<latest_seen>)
```

This is a recovery path, **not** a normal retry. It increments a separate `gmail.fallback_recoveries` counter so we can spot a source that's perpetually falling behind.

### 4.6 What we read

- Messages within user-configured labels (default: INBOX + onboarding-pinned labels)
- History API for incremental sync; the §4.5 fallback for expiry
- Attachments **by metadata only** (filename, mimeType, size); never fetch bytes

### 4.7 What we extract per message

```
external_id        = Gmail message-id
received_at        = internalDate
sender             = From header
recipients         = To, Cc (counts only; addresses redacted in logs)
subject            = Subject header
body_text          = text/plain or sanitized HTML
links              = extracted URLs with anchor text
label_ids          = Gmail label set
thread_id          = Gmail thread id
raw_headers_hash   = sha256 of canonical header block
```

### 4.8 Per-source config

```json
{
  "labels_watched": ["INBOX", "Label_4839292"],
  "sender_allowlist": [],
  "sender_blocklist": [],
  "include_attachments_metadata": true,
  "max_lookback_days_initial": 14
}
```

### 4.9 Boundaries — ADR-023

- **Never** `users.messages.send` or `users.messages.modify`
- **Never** mark anything read on Gmail's side
- **Never** delete from Gmail
- OAuth scope disallows the above; ADR-023 + integration test enforces it from our side

---

## 5. RSS Intake Design

### 5.1 Sync model

- Per-source `fetch_interval_minutes` (default 30, min 5)
- HTTP conditional requests via **ETag** and **If-Modified-Since**
- Cursor = `(last_fetched_at, etag)`

### 5.2 Parsing

- Atom + RSS 2.0
- Item identity = `<guid>` if present, else `sha256(link, title, pubDate)`
- HTML in `<content:encoded>` sanitized server-side (allowlist)

### 5.3 RawItem mapping

```
external_id = <guid> or canonical hash
received_at = pubDate (fallback: now)
sender      = feed title
subject     = item title
body_text   = sanitized text
links       = [item link, content links]
```

### 5.4 Failure semantics

| Response       | Reaction                                                    |
| -------------- | ----------------------------------------------------------- |
| 200            | Process items; advance cursor                               |
| 304            | No-op; advance `last_fetched_at`                            |
| **301 (CR-10)**| **Persist new URL on the originating Phase 2 row + audit_log entry; retry once with new URL** |
| **302 (CR-10)**| **Follow this request only; do not persist; continue using original URL** |
| 401 / 403      | Mark `auth_required`; stop until user intervenes            |
| 4xx (other)    | Mark `degraded`; retry only at next scheduled tick          |
| 5xx / network  | Exponential backoff + jitter; circuit-break after N failures |

### 5.5 Why follow but not persist 302

302 is "temporary." Persisting it would lose the true source URL if the vendor reverts. 301 is permanent and audit-logged.

---

## 6. Webhook Intake Design

### 6.1 Inbound surface

```
POST /v1/intake/webhooks/:workspace_id/:intake_source_id
Headers:
  X-Anant-Signature: hmac-sha256=<hex>
  X-Anant-Timestamp: <unix-seconds>
  X-Anant-Idempotency-Key: <vendor-key-or-sha256-body>
  Content-Type: application/json
Body: vendor-specific JSON
```

### 6.2 Three independent controls

| Control                    | Guards against                                |
| -------------------------- | --------------------------------------------- |
| HMAC signature             | Forgery — only holders of the per-source secret can call |
| ±5-min timestamp window    | Replay of a previously valid request           |
| Idempotency key (24h TTL)  | Duplicate delivery from a well-behaved retrier |

### 6.3 Per-source secrets

- Per-source HMAC secret generated server-side at connect time
- Displayed to user **once**, stored hashed
- Rotation surfaces a new secret, retains old for 24h grace

### 6.4 Idempotency persistence — CR-4

```
webhook_idempotency_keys
─────────────────────────────────────────────────────────────────
workspace_id        uuid
intake_source_id    uuid     fk → intake_sources.id
idempotency_key     text     not null
seen_at             timestamp default now()
pk (workspace_id, intake_source_id, idempotency_key)
```

- Index: `(seen_at)` partial — accelerates the cleanup job
- Cleanup job (hourly): `DELETE WHERE seen_at < now() - interval '24 hours'`
- Memory store **is not used** — restarts must not reset the dedupe window

### 6.5 Body and rate caps

- Body size capped at 256 KiB at the edge
- Per-source rate limit: 60 req/min (configurable per plan)
- 429 returned with `Retry-After` when exceeded

### 6.6 Phase 3 webhook providers

- `generic_json` — maps fields by config template
- Vendor-specific providers added as needed (Zapier passthrough, Substack push)

---

## 7. API Pull Design

### 7.1 Per-source config

```json
{
  "base_url": "https://api.vendor.com/v2/",
  "auth_method": "bearer | api_key_header | oauth2_client_credentials",
  "endpoints_polled": [{ "path": "...", "params": {...} }],
  "cursor_field": "next_cursor",
  "fetch_interval_minutes": 15,
  "expected_response_shape": "list | paginated_object"
}
```

### 7.2 Mapping

Per-vendor `mapper.py` translates JSON paths to `RawItem`. No business logic; pure transformation.

### 7.3 Auth lifecycle

- Expired bearer / API key → `ProviderError(kind=AUTH)` → source becomes `auth_required` (same path as Gmail)
- OAuth client-credentials flow refreshes inline; failure escalates to `auth_required`

### 7.4 Why API pulls are isolated from RSS

| Concern        | RSS                          | API pull                                  |
| -------------- | ---------------------------- | ----------------------------------------- |
| Auth           | Rarely needed                | Required                                  |
| Pagination     | `pubDate` ordering           | Vendor cursor field                       |
| Payload        | Constrained by feed format   | Richer JSON                               |
| Sanitization   | HTML allowlist               | Structural validation                     |

Conflating them would force one or the other into a poorly-fitting interface.

---

## 8. Sync State and Cursor Strategy — REVISED (CR-1)

### 8.1 The structural fix

Revision 1 had `intake_source_state.source_id` referencing **either** `workspace_sources` **or** `workspace_custom_sources`. That polymorphism is forbidden in Rev 2.

Rev 2 introduces a single unified operational table:

```
intake_sources                            -- one row per operational source
─────────────────────────────────────────────────────────────────
id                    uuid     pk
workspace_id          uuid     fk → workspaces.id
kind                  enum     ('gmail','rss','webhook','api_pull','manual')
name                  text                    -- human label
enabled               bool     default true
config                jsonb    not null default '{}'   -- per-provider config

-- Origin link back to user-facing selection (informational; not FK-enforced
-- to keep selection vs operational lifecycles independent).
origin_kind           enum     ('catalog','custom')
origin_catalog_key    text     nullable        -- if origin_kind='catalog'
origin_custom_id      uuid     nullable        -- if origin_kind='custom'

-- Runtime cursor + health (was the polymorphic state table)
cursor                jsonb    nullable        -- provider-shaped opaque
last_synced_at        timestamp nullable
last_attempt_at       timestamp nullable
consecutive_failures  int       default 0
status                enum     ('healthy','degraded','auth_required','disabled')
last_error            text     nullable

created_at            timestamp
updated_at            timestamp
deleted_at            timestamp nullable
```

```
                     workspace_sources              workspace_custom_sources
                     (Phase 2 user-facing)          (Phase 2 user-facing)
                            │                                │
                            │ origin_kind='catalog'           │ origin_kind='custom'
                            └────────────────┬───────────────┘
                                             ▼
                                    ┌────────────────────┐
                                    │  intake_sources    │
                                    │  (Phase 3 ops)     │
                                    └────────────────────┘
```

### 8.2 Why `origin_*` is not an FK

The user-facing Phase 2 row may be deleted, soft-disabled, or restored independently of the operational record. Keeping `origin_*` as a soft pointer + audit log entry preserves both lifecycles. Cascade behavior is explicit in §17.

### 8.3 Why `cursor` is `jsonb`

Each provider's cursor shape differs (Gmail `historyId`, RSS `(etag, last_modified)`, API pull next-cursor strings). The orchestrator stays agnostic.

### 8.4 Indexes

- `intake_sources(workspace_id)` btree
- `intake_sources(status, last_synced_at)` btree — scheduler picks "healthy, oldest-syncing first"
- Partial index on `deleted_at IS NULL`

---

## 9. Deduplication Strategy — REVISED (CR-2)

### 9.1 What duplication looks like

- Same article forwarded to Gmail and surfaced via RSS
- Same alert webhook fired twice on vendor retry
- Same Gmail item caught in two watched labels
- RSS re-broadcasting with a new `pubDate`

### 9.2 Two-key strategy (unchanged)

1. **Provider key** — `(workspace_id, intake_source_id, external_id)`. Catches re-ingestion within one source.
2. **Cross-source key** — content fingerprint (REVISED below).

### 9.3 Fingerprint — two-tier with date fallback

| Item shape                  | Fingerprint                                                           |
| --------------------------- | --------------------------------------------------------------------- |
| **Has external link**       | `sha256(sender_domain, canonical_url(primary_link), normalize_title(subject))` |
| **No external link (body-only Gmail, etc.)** | `sha256(sender_domain, normalize_title(subject), date_bucket(received_at))` |

Where:

- `sender_domain` — lowercased host, no display name
- `canonical_url(...)` — strip utm/track params, normalize case, drop trailing slash
- `normalize_title(...)` — strip emoji, collapse whitespace, lowercase
- `date_bucket(...)` — `YYYY-MM-DD` in the workspace's timezone

### 9.4 Why the date bucket

Same-title same-sender body-only items from *different days* are not duplicates — they're a recurring brief. Revision 1's fingerprint would have collapsed them. Adding `date_bucket` keeps cross-source dedupe for linked items intact while preventing the body-only false positive.

### 9.5 The dedupe index

```
intake_dedupe_index
─────────────────────────────────────────────────────────────────
workspace_id         uuid    fk → workspaces.id
fingerprint          text    not null   -- 64-char hex
first_intake_item_id uuid    fk → intake_items.id
first_seen_at        timestamp
duplicate_count      int     default 0
pk (workspace_id, fingerprint)
```

### 9.6 The dedupe decision

For every incoming `RawItem`:

```
1. Compute provider key. Found? → skip silently.
2. Compute fingerprint (two-tier per §9.3).
   Found?
   ├── YES → increment duplicate_count
   │        record in intake_items_duplicates
   │        do NOT insert new intake_items row
   │
   └── NO  → insert intake_items row
            insert intake_items_normalized row
            insert intake_dedupe_index row
            insert outbox_events row
            (all in one transaction)
```

### 9.7 Workspace scope (unchanged)

Dedupe is per-tenant. One workspace's "duplicate" is another's "first sighting." Global dedupe would leak workspace activity timing.

---

## 10. Retry and Failure Handling

### 10.1 Classify, then react

| Kind            | Provider returns                | Reaction                                                |
| --------------- | ------------------------------- | ------------------------------------------------------- |
| `TRANSIENT`     | network blip, 5xx, timeout      | Backoff + retry, capped at 5                            |
| `RATE_LIMITED`  | 429 + Retry-After               | Sleep ≥ Retry-After, then retry once                    |
| `AUTH`          | 401 / 403, OAuth refresh failure| Mark `auth_required`; **stop attempting**               |
| `PERMANENT`     | 4xx (non-auth), invalid feed    | Mark `degraded`; retry only at next scheduled tick       |
| `UNKNOWN`       | anything else                   | Treat as TRANSIENT; log + alert                          |

### 10.2 Backoff schedule

```
delay(N) = min(30s × 2^N, 1h) ± 10% jitter
reset(N) = on first successful sync, N → 0
```

### 10.3 Circuit breaker

- Per `(workspace_id, intake_source_id)`
- After **10** consecutive failures → status `degraded`
- Scheduler skips degraded except for an **hourly probe**
- Successful probe → status `healthy`, counter reset

### 10.4 Audit log

```
intake_audit_log
─────────────────────────────────────────────────────────────────
id                  uuid     pk
workspace_id        uuid
intake_source_id    uuid
event               text     ('sync_start','sync_complete','sync_failed',
                              'webhook_received','dedupe_skip','circuit_broken',
                              'circuit_recovered','auth_lapsed','config_changed',
                              'rss_permanent_redirect','gmail_history_expired')
data                jsonb    default '{}'
created_at          timestamp
```

Append-only. Phase 7 analytics will consume it directly.

---

## 11. Storage Strategy — REVISED (CR-1)

### 11.1 Phase 3 table set

```
intake_sources                      -- §8 unified operational table
intake_items                        -- immutable raw record
intake_items_normalized             -- derived projection (rebuildable)
intake_items_duplicates             -- dedupe audit trail
intake_dedupe_index                 -- fingerprint index
intake_credentials                  -- encrypted vendor tokens
intake_audit_log                    -- append-only event trail
webhook_idempotency_keys            -- §6.4 dedup with TTL
outbox_events                       -- §12 emission ledger
outbox_dead_letter                  -- §12 poison-event holding pen
```

### 11.2 Why two tables for items

Normalization rules will change as Phase 4 learns what it needs. If raw and normalized share a row, every rule change requires a destructive migration or a vendor re-fetch (which may be rate-limited).

Two tables means:

- Raw is the source of truth, **immutable** (only `deleted_at` ever changes)
- Normalized can be **rebuilt** from raw via a worker (`INSERT ... SELECT`)
- Rules evolution = code change + offline backfill, never a customer-facing outage

### 11.3 Schemas

```
intake_items
─────────────────────────────────────────────────────────────────
id                  uuid       pk
workspace_id        uuid       fk → workspaces.id
intake_source_id    uuid       fk → intake_sources.id           ★ CR-1
provider_name       text
external_id         text       not null
received_at         timestamp  not null
fetched_at          timestamp  not null default now()
payload             jsonb      not null   -- full provider raw
fingerprint         text       not null
deleted_at          timestamp  nullable
unique (workspace_id, intake_source_id, external_id)

intake_items_normalized
─────────────────────────────────────────────────────────────────
intake_item_id      uuid       pk, fk → intake_items.id
sender_domain       text
sender_label        text
subject             text
body_text           text
links               jsonb      -- [{url, anchor}]
metadata            jsonb
normalized_at       timestamp  default now()
normalizer_version  int        not null
```

### 11.4 Indexes

- `intake_items(workspace_id, received_at desc)` — ordered listing
- `intake_items(workspace_id, fingerprint)` — fast dedupe
- `intake_items_normalized(sender_domain)` — Phase 4 leans on this
- Partial `intake_items WHERE deleted_at IS NULL`

### 11.5 Retention

| Table                  | Default          | Configurable |
| ---------------------- | ---------------- | ------------ |
| `intake_items`         | 24 months        | per workspace plan |
| `intake_items_normalized` | matches raw   | derived; rebuilds on `normalizer_version` bump |
| `intake_audit_log`     | 12 months        | per plan     |
| `webhook_idempotency_keys` | 24 hours      | fixed        |
| `outbox_events` (delivered) | 7 days        | fixed (§12)  |
| `outbox_dead_letter`   | 90 days          | fixed; ops surface |

### 11.6 Encryption at rest

- DB-level encryption is the operator's job
- Application-level encryption covers `intake_credentials.encrypted_token` + `encrypted_refresh_token`
- Webhook signatures stored hashed

### 11.7 Payload size acknowledgement

A single Gmail item with body + headers can be 50–150 KB. At 100 sources × 100 items/day per workspace, `intake_items` grows ~2 GB/year per workspace. Accepted for Phase 3; revisit body-extraction if >1 M items per workspace.

---

## 12. Queue Design — REVISED (CR-3)

### 12.1 Outbox from day 1

ADR-014 froze the event architecture. Phase 3 skips Stage A (in-process only) and adopts **Stage B (persistent outbox)** because Phase 4 cannot afford lost events on restart.

### 12.2 Tables

```
outbox_events
─────────────────────────────────────────────────────────────────
id              uuid     pk
event_name      text     not null   -- 'intake.item.received'
event           jsonb    not null   -- full DomainEvent envelope
workspace_id    uuid     nullable
created_at      timestamp default now()
delivered_at    timestamp nullable
attempts        int      default 0
last_error      text     nullable
last_attempt_at timestamp nullable

outbox_dead_letter
─────────────────────────────────────────────────────────────────
id              uuid     pk
original_id     uuid     not null
event_name      text     not null
event           jsonb    not null
workspace_id    uuid     nullable
moved_at        timestamp default now()
final_error     text     not null
total_attempts  int      not null
```

### 12.3 Cleanup + dead-letter policy — CR-3

```
Outbox lifecycle:

  insert ── attempts++ ── delivered ── retained 7 days ── DELETED
                │
                └── attempts > 20 OR permanent error ──► outbox_dead_letter
                                                         │
                                                         └── retained 90 days ──► DELETED
```

Concretely:

- **Cleanup job (hourly):** `DELETE FROM outbox_events WHERE delivered_at IS NOT NULL AND delivered_at < now() - interval '7 days'`
- **Dead-letter promotion (in drainer):** when `attempts > 20` or a handler raises a permanent classifier, copy to `outbox_dead_letter`, then delete the original row
- **Ops surface:** an admin endpoint lists dead-letter entries with `final_error` for replay or discard

### 12.4 Emission

Every intake transaction:

```sql
BEGIN
  INSERT INTO intake_items (...);
  INSERT INTO intake_items_normalized (...);
  INSERT INTO intake_dedupe_index (...)  ON CONFLICT DO UPDATE ...;
  INSERT INTO outbox_events (event_name, event, workspace_id) VALUES (...);
COMMIT;
```

### 12.5 Drainer

```
OutboxDrainer (separate process — see §14):
  loop:
    rows = SELECT FROM outbox_events
           WHERE delivered_at IS NULL
             AND (last_attempt_at IS NULL OR last_attempt_at < now() - backoff(attempts))
           ORDER BY created_at
           LIMIT 100
    for row in rows:
      try:
        bus.publish(row.event)
        UPDATE outbox_events SET delivered_at = now() WHERE id = row.id
      except PermanentError as e:
        move_to_dead_letter(row, e); DELETE FROM outbox_events ...
      except Exception as e:
        UPDATE outbox_events SET attempts = attempts + 1,
                                  last_error = e,
                                  last_attempt_at = now()
        if attempts >= 20: move_to_dead_letter(...)
    sleep(1s if rows else 5s)
```

### 12.6 Event payload — `intake.item.received`

```ts
interface IntakeItemReceived {
  intakeItemId: Id;
  workspaceId: Id;
  intakeSourceId: Id;
  providerName: 'gmail' | 'rss' | 'webhook' | 'api_pull';
  receivedAt: Timestamp;
  fingerprint: string;
  externalId: string;
}
```

Payloads carry IDs, not content. Subscribers read full normalized rows by id.

---

## 13. Source Catalog and Trust Metadata — REVISED (CR-1)

### 13.1 Builds on Phase 2

Phase 2 shipped `source_catalog`, `workspace_sources`, `workspace_custom_sources` (user-facing selection state).

### 13.2 Phase 3 ALTERs

```sql
ALTER TABLE source_catalog
  ADD COLUMN provider_kind text,
  ADD COLUMN provider_config_schema jsonb;

ALTER TABLE workspace_custom_sources
  ADD COLUMN provider_kind text NOT NULL DEFAULT 'rss',
  ADD COLUMN verified_at timestamp,
  ADD COLUMN rejected_reason text;
```

`workspace_sources.config` is **not** added. Per-provider config moves to `intake_sources.config`. The Phase 2 selection tables remain unchanged in shape; the operational concerns move to `intake_sources`.

### 13.3 Two lifecycles, clearly split

| Layer                     | Concern                                       | Lifecycle           |
| ------------------------- | --------------------------------------------- | ------------------- |
| `source_catalog`          | Curated list shipped with the app             | Editor-managed      |
| `workspace_sources`       | Which catalog entries the workspace selected  | User-controlled     |
| `workspace_custom_sources`| User-added URLs                               | User-controlled     |
| **`intake_sources`**      | Operational shadow + config + cursor + health | Orchestrator-managed |

When a user adds a custom source or selects a catalog entry, a corresponding `intake_sources` row is created (`origin_kind` + `origin_catalog_key | origin_custom_id`). If they disable the selection, the operational row is soft-disabled — not deleted — so historical items remain attributable.

### 13.4 Trust metadata is not Phase 3's job

Confidence weights already exist in Phase 2 (`editorial_confidence`, `confidence_override`). Phase 3 only passes them on the event payload; using them is Phase 4. We deliberately do not build trust logic here.

---

## 14. Backend Structure Changes — REVISED (CR-7, CR-8, CR-9)

### 14.1 New service folders

```
apps/backend/src/anant/services/
├── intake/                              # orchestrator
│   ├── router.py                        # CRUD + status (CR-9 pagination)
│   ├── service.py                       # orchestration
│   ├── scheduler.py                     # entry point of intake.scheduler process
│   ├── repository.py                    # intake_sources + intake_items
│   ├── credentials.py                   # envelope encryption wrapper
│   ├── providers/                       # one folder per vendor (§3.3)
│   │   ├── gmail/
│   │   ├── rss/
│   │   ├── webhook/
│   │   └── api_pull/
│   └── webhooks_router.py               # /v1/intake/webhooks/:ws/:src
│
├── normalization/
│   ├── service.py
│   ├── normalizer.py
│   ├── url_canonicalizer.py
│   ├── text_sanitizer.py
│   └── version.py                       # NORMALIZER_VERSION
│
├── dedupe/
│   ├── fingerprint.py                   # two-tier fingerprint (CR-2)
│   ├── service.py
│   └── repository.py
│
├── queue/                               # outbox + drainer
│   ├── outbox.py                        # write side
│   ├── drainer.py                       # entry point of queue.drainer process
│   ├── bus.py                           # InProcessBus impl
│   └── dead_letter.py                   # promotion + ops queries
│
└── source_catalog/                      # expanded read/write
```

### 14.2 New endpoints (under `/v1`)

| Method | Path                                       | Purpose                                  | Notes                              |
| ------ | ------------------------------------------ | ---------------------------------------- | ---------------------------------- |
| POST   | `/intake/sources`                          | Add workspace source                     | Validates config against provider schema |
| GET    | `/intake/sources`                          | List with health                         | **Cursor-paginated (CR-9)**        |
| GET    | `/intake/sources/:id`                      | Detail                                   |                                    |
| PATCH  | `/intake/sources/:id`                      | Update config / enable / disable         |                                    |
| DELETE | `/intake/sources/:id`                      | Disconnect + revoke creds                | Soft-delete + audit + upstream revoke |
| POST   | `/intake/sources/:id/sync`                 | Manually trigger sync                    | Rate-limited per source: 1/min     |
| GET    | `/intake/sources/:id/audit`                | Per-source audit log                     | **Cursor-paginated (CR-9)**        |
| POST   | `/intake/webhooks/:ws/:src`                | Inbound webhook                          | HMAC + timestamp + idempotency     |
| GET    | `/intake/items`                            | Operational listing (counts + IDs only)  | **Cursor-paginated (CR-9)**        |
| GET    | `/intake/status`                           | Per-workspace health summary             |                                    |
| **POST** | **`/admin/intake/manual_ingest`**        | **Manual URL ingest** — **platform admin only (CR-8)** | Bypasses `ff_intake_manual` flag |
| POST   | `/admin/intake/dead-letter/:id/replay`     | Replay dead-letter event                 | Platform admin only                |
| POST   | `/admin/intake/dead-letter/:id/discard`    | Discard dead-letter event                | Platform admin only                |

Pagination contract reuses Phase 1: `?cursor=<opaque>&limit=<int>` → response includes `meta.pagination.nextCursor`. Default page size 50, max 200.

### 14.3 Process topology — CR-7

```
┌──────────────────────────────────────────────────────────────┐
│ Deploy unit                                                  │
├──────────────────────────────────────────────────────────────┤
│  process: api                  (uvicorn anant.main:app)      │
│  process: intake.scheduler     (separate; never blocks api)  │
│  process: queue.drainer        (separate; never blocks api)  │
└──────────────────────────────────────────────────────────────┘
```

- **API process** serves HTTP. Never blocks on intake.
- **`intake.scheduler` process** picks healthy sources, dispatches `sync()` calls. Each provider has its own concurrency limit.
- **`queue.drainer` process** drains `outbox_events`, publishes to the bus.
- Local dev can colocate behind `ANANT_DEV_MONOPROCESS=1` for convenience; production deploys never do.

`scheduler.py` and `drainer.py` are runnable entry points (`python -m anant.services.intake.scheduler` and `python -m anant.services.queue.drainer`).

### 14.4 OAuth surface (Gmail in Phase 3)

```
GET  /v1/intake/oauth/gmail/start         → vendor auth URL
GET  /v1/intake/oauth/gmail/callback      → exchange code, store credentials
POST /v1/intake/oauth/gmail/disconnect    → revoke upstream + delete creds
```

Callback URL pinned per environment in `Settings`.

### 14.5 Feature flag catalog additions

```
ff_intake_gmail        default OFF (cohort rollout first)
ff_intake_rss          default OFF
ff_intake_webhook      default OFF
ff_intake_api_pull     default OFF
ff_intake_manual       default OFF   # surface gated; platform-admin only regardless of flag
```

---

## 15. Mobile Structure Changes — REVISED (CR-8)

Phase 3 keeps mobile **operational**, not editorial.

### 15.1 Module additions

```
apps/mobile/src/modules/intake/
├── screens/
│   ├── IntakeHomeScreen.tsx             # sources dashboard
│   ├── ConnectGmailScreen.tsx           # OAuth start + return
│   ├── AddRssSourceScreen.tsx
│   ├── AddWebhookSourceScreen.tsx       # shows HMAC secret ONCE
│   ├── SourceDetailScreen.tsx           # health, audit, manual sync
│   └── ManualIngestScreen.tsx           # PLATFORM ADMIN ONLY (CR-8)
├── components/
│   ├── SourceHealthPill.tsx
│   ├── SourceCard.tsx
│   └── AuditTimeline.tsx
└── hooks/
    ├── useIntakeSources.ts
    ├── useIntakeStatus.ts
    └── useSourceAudit.ts
```

### 15.2 ManualIngestScreen visibility — CR-8

```
                       account.is_platform_admin == true
                                     │
                                     ▼
            ┌────────────────────────────────────────────┐
            │  Settings → Developer Tools → Manual Ingest│
            └────────────────────────────────────────────┘

  Workspace admins / owners / editors / readers: do not see the surface at all.
```

Implementation: the route is mounted only when `me.account.isPlatformAdmin === true`. There is no "request access" affordance — this is operator-only.

### 15.3 Surface rules

- **No "items" list.** Listing items would imply verified truth (Phase 4's claim, not Phase 3's).
- **Operational language only.** "Connected", "Healthy", "Auth lapsed", "Last sync 4m ago."
- **Connect flow is explicit.** OAuth scope + read-only guarantees surfaced inline. User confirms before consent.

### 15.4 Settings extensions

`Settings → Trusted Sources` (Phase 2) becomes the entry point for Phase 3 connect flows. Adding a source flips the matching feature flag's per-workspace override on and routes the user into Phase 3 screens.

### 15.5 Design rules

Preserve the premium dark finance system. Reuse `Screen`, `Card`, `Spacer`, `Text`, `Button`, `SettingsRow`. New: `SourceHealthPill` (small status chip; no new tokens, just composes existing ones).

---

## 16. Shared Contracts and Schemas — REVISED (CR-1)

### 16.1 New `packages/shared-types/src/` files

```
src/intake.ts          # IntakeItem (id-only operational view)
src/intake-sources.ts  # IntakeSource, IntakeSourceKind, SourceHealth, OriginKind
src/intake-events.ts   # IntakeItemReceived payload
src/intake-webhooks.ts # WebhookEnvelope, helpers
```

### 16.2 Key types

```ts
type IntakeSourceKind = 'gmail' | 'rss' | 'webhook' | 'api_pull' | 'manual';
type SourceHealth = 'healthy' | 'degraded' | 'auth_required' | 'disabled';
type OriginKind = 'catalog' | 'custom';

interface IntakeSource {
  id: Id;
  workspaceId: Id;
  kind: IntakeSourceKind;
  name: string;
  enabled: boolean;
  config: Record<string, unknown>;
  health: SourceHealth;
  lastSyncedAt: Timestamp | null;
  consecutiveFailures: number;
  originKind: OriginKind;
  originCatalogKey: string | null;
  originCustomId: Id | null;
}

interface IntakeItem {
  id: Id;
  workspaceId: Id;
  intakeSourceId: Id;          // ★ CR-1
  providerName: string;
  externalId: string;
  receivedAt: Timestamp;
  fingerprint: string;
}
```

### 16.3 What we do NOT expose

The full `IntakeItemRaw` payload — provider-specific, can include sender PII — is **not** in shared-types. It lives only in the backend's internal models. Mobile sees `IntakeItem` (IDs + counts), nothing more.

### 16.4 Pagination types

Inherited from Phase 1's `Pagination` envelope. All paginated endpoints return `{ data: [...], meta: { pagination: { nextCursor }, requestId, serverTime } }`.

---

## 17. Security Model — REVISED (CR-4, CR-6)

### 17.1 Risk matrix

| Risk                          | Impact                              | Mitigation                                                                    |
| ----------------------------- | ----------------------------------- | ----------------------------------------------------------------------------- |
| Gmail credentials leak        | Catastrophic — full inbox access    | Workspace-scoped envelope encryption; `gmail.readonly` only; audit all refreshes |
| Webhook spoofing              | Corrupted downstream data           | HMAC signature                                                                 |
| Webhook replay                | Duplicate events at rest            | ±5-min timestamp window                                                        |
| Webhook duplicate delivery    | Bloated dedupe index                | `webhook_idempotency_keys` table with 24h TTL (CR-4)                          |
| Malicious RSS payload         | XSS / stored injection              | Server-side allowlist sanitization                                             |
| SSRF via API-pull config      | Internal-service pivot              | Hostname allowlist; deny RFC1918, link-local, metadata IPs                     |
| Rate-limit bypass abuse       | Vendor account suspension           | Per-source concurrency cap; honor Retry-After                                  |
| Data exfiltration via custom URL | Hostile outbound proxy             | Custom sources untrusted; no header replay; capped response size               |
| Workspace deletion leaves orphan tokens | Indefinite vendor access  | **Workspace hard-delete cascade (CR-6)**                                       |
| `INTAKE_KMS_KEY` rotation event | Breaks all encrypted creds         | Re-encryption migration runbook (Appendix C)                                  |

### 17.2 Workspace deletion cascade — CR-6

```
DELETE workspace
   │
   ▼
emit event: workspace.deletion.started
   │
   ▼
foreach intake_source where workspace_id = X:
   │
   ▼
   provider.auth.revoke(credentials)    [best-effort; logs failure but proceeds]
   │
   ▼
   DELETE FROM intake_credentials WHERE intake_source_id = ...
   DELETE FROM intake_sources WHERE id = ...
   │
   ▼
DELETE FROM intake_items WHERE workspace_id = X  (cascade)
DELETE FROM webhook_idempotency_keys WHERE workspace_id = X
DELETE FROM outbox_events WHERE workspace_id = X
   │
   ▼
emit event: workspace.deletion.completed
```

Upstream revoke is **best effort**. If Gmail's revoke endpoint is unreachable, we log the credential id + sub claim into `workspace_deletion_orphan_credentials` for ops to handle manually. The local credentials are still deleted.

### 17.3 Secret handling

| Secret                     | Storage                                                 |
| -------------------------- | ------------------------------------------------------- |
| OAuth client secret        | Environment variable (operator-managed)                  |
| `INTAKE_KMS_KEY`           | Environment variable; rotation runbook in Appendix C    |
| `WEBHOOK_HMAC_PEPPER`      | Environment variable; rotation-friendly secret prefix    |
| Per-source webhook secret  | Generated server-side; shown to user once; stored hashed |
| Gmail OAuth tokens         | Encrypted at rest with `INTAKE_KMS_KEY`                  |

### 17.4 Permissions

| Capability       | Roles               | Endpoints                                  |
| ---------------- | ------------------- | ------------------------------------------ |
| `intake.read`    | reader+ in workspace | List sources, view health, view audit      |
| `intake.write`   | admin + owner       | Connect, disconnect, update config, manual sync |
| `intake.platform`| platform admin only | Manual ingest, dead-letter ops             |

Public webhook endpoint requires no auth; security comes entirely from HMAC + timestamp + idempotency.

### 17.5 Logging

| Event                       | Logged                                                 |
| --------------------------- | ------------------------------------------------------ |
| OAuth connect / disconnect  | account_id, workspace_id, source_id                    |
| OAuth refresh failed        | account_id, workspace_id, source_id, error_class       |
| Webhook secret rotation     | account_id, workspace_id, source_id                    |
| Sender email                | **Redacted to domain** in log lines                    |
| Body content                | **Never logged.** Only fingerprints, byte counts        |

---

## 18. Scaling Strategy

### 18.1 Phase 3 targets

```
100 workspaces × 10 sources × 1 sync per 15 min  ≈ 67 syncs/minute
Webhook burst                                    ≤ 10/s per workspace
```

### 18.2 What pays off as we grow

| Decision                                   | Benefit                                                 |
| ------------------------------------------ | ------------------------------------------------------- |
| Provider-scoped concurrency limits         | Sick provider can't starve healthy ones                 |
| Outbox + drainer (Stage B)                 | Survives crashes; replayable; broker-ready              |
| Per-workspace cursors                      | One workspace's stuck source isolates within its row    |
| Stateless normalizer + `NORMALIZER_VERSION`| Backfill in one query; no vendor re-fetch               |
| Workspace-scoped dedupe                    | No global hot index; shard-friendly                     |
| `outbox_dead_letter`                       | Poison-event isolation; ops queue                       |
| Separate scheduler / drainer processes     | API restart doesn't pause sync                          |

### 18.3 Where we'll hit limits

| Limit                          | When                          | Move                                          |
| ------------------------------ | ----------------------------- | --------------------------------------------- |
| Polling latency                | Users want push-fast Gmail    | Layer in Gmail Pub/Sub push                   |
| Single-process drainer throughput | Events > ~500/s            | Swap `InProcessBus` → broker (ADR-014 Stage C) |
| Postgres index pressure        | `intake_items` > 100M rows    | Partition by `workspace_id` hash; archive >24mo |
| Vendor rate limit              | Workspace count > vendor quota | Per-tenant OAuth apps                          |

### 18.4 Migrations that DON'T require app changes

- `EventBus` swap: one line in `main.py`. No service code moves.
- DB partitioning: declarative partitions in migration; service code unchanged.
- Vendor swap (RSS parser, HTTP client): provider folder replacement.

### 18.5 Explicitly NOT for Phase 3

No Redis cache. No queue broker. No worker autoscaling. No multi-region. All have known upgrade paths; none justified by Phase 3 load.

---

## 19. Implementation Roadmap

### 19.1 Strict build order

```
 1. shared-types: intake, intake-sources, intake-events, intake-webhooks
 2. Migrations: intake_sources, intake_items, intake_items_normalized,
    intake_items_duplicates, intake_dedupe_index, intake_credentials,
    intake_audit_log, webhook_idempotency_keys, outbox_events,
    outbox_dead_letter; ALTERs on source_catalog, workspace_custom_sources;
    new feature flag rows
 3. core/security/secrets.py — workspace-scoped envelope encryption
 4. services/queue/outbox.py + bus.py (InProcessBus, Stage B)
 5. services/queue/dead_letter.py + cleanup job scaffolding
 6. services/normalization/* (rules + NORMALIZER_VERSION)
 7. services/dedupe/* (two-tier fingerprint + repo + decision)
 8. services/intake/repository.py + credentials.py + scheduler.py skeleton
 9. IntakeProvider Protocol + ProviderError taxonomy
10. providers/rss/* (ships first — proves end-to-end pipe, no auth)
11. providers/gmail/* + OAuth router + historyId expiry recovery (CR-5)
12. providers/webhook/* + public webhooks_router + idempotency table queries
13. providers/api_pull/* (mapper-driven generic)
14. services/intake/router.py — sources CRUD + pagination (CR-9)
15. services/intake/service.py — orchestration glue
16. services/queue/drainer.py — separate-process entry point (CR-7)
17. main.py wiring + entry points for intake.scheduler + queue.drainer
18. Mobile: useIntakeSources, useIntakeStatus, useSourceAudit hooks
19. Mobile: IntakeHomeScreen (sources dashboard)
20. Mobile: ConnectGmailScreen + AddRssSourceScreen + AddWebhookSourceScreen
21. Mobile: SourceDetailScreen + SourceHealthPill component
22. Mobile: ManualIngestScreen (platform-admin gated, CR-8)
23. Settings → Trusted Sources updates: routes into Phase 3 flows
24. Workspace deletion cascade (CR-6) wiring
25. Tests:
    - Unit: fingerprint two-tier, normalizer rules, URL canonicalizer,
      HMAC verify, circuit breaker, retry classifier, dedupe decision,
      idempotency TTL cleanup, dead-letter promotion
    - Integration: RSS sync + 301 redirect persist (CR-10),
      Gmail OAuth callback round-trip with mock + historyId expiry recovery (CR-5),
      Webhook HMAC + replay + idempotency,
      Outbox drainer publishes exactly once on success, retries + dead-letters on poison,
      Dedupe insertion vs skip
    - Security: SSRF allowlist, HMAC timestamp window, replay window,
      OAuth scope assertion, secret rotation, workspace delete cascade (CR-6)
26. Operational docs: scheduler topology, drainer scaling, vendor quotas,
    "Gmail auth lapsed" mass-event runbook, KMS rotation drill
```

### 19.2 Build order diagram

```
shared-types ──► migrations ──► secrets ──► outbox+bus ──► dead-letter
                                                       │
                                                       ▼
                          normalizer ──► dedupe ──► IntakeProvider Protocol
                                                            │
                                                            ▼
                                    RSS ──► Gmail ──► Webhook ──► API pull
                                            │
                                            ▼
                          intake router ──► service ──► drainer (separate pid)
                                                              │
                                                              ▼
                                                main.py + process entry points
                                                              │
                                                              ▼
                                          mobile hooks ──► screens ──► gates
                                                              │
                                                              ▼
                                          tests ──► security pass ──► ops docs
```

### 19.3 Dependency order justification

- shared-types first because every later step is typed by them
- Migrations before backend so ORM aligns
- Outbox + dead-letter before providers — emission must work before there's anything to emit
- Normalizer + dedupe before providers — providers need a destination
- RSS before Gmail — zero auth complexity; proves the pipe
- Mobile after backend has `/intake/sources` working — screens have data
- Tests track real-world risk order: hash + retry + HMAC + dedupe + cascade first

### 19.4 First five backend commits

1. Migration: `intake_sources` + `outbox_events` + `outbox_dead_letter`
2. `services/queue/outbox.py` + `bus.py` (`InProcessBus`) + drainer skeleton
3. `services/dedupe/fingerprint.py` (two-tier) + unit tests
4. `services/normalization/normalizer.py` + `NORMALIZER_VERSION = 1`
5. `services/intake/providers/rss/*` — `sync()` proven end-to-end against a fixture

### 19.5 First five mobile commits *(after backend OAuth surface live)*

1. `hooks/useIntakeSources.ts`
2. `IntakeHomeScreen` (sources list + `SourceHealthPill`)
3. `AddRssSourceScreen` (form + POST `/intake/sources`)
4. `SourceDetailScreen` + `AuditTimeline`
5. `ConnectGmailScreen` (OAuth start + callback handoff)

### 19.6 Phase 3 exit checklist

- [ ] RSS sources sync end-to-end; items appear in `intake_items` with correct dedupe
- [ ] RSS 301 redirect persisted on originating row + audit log entry (CR-10)
- [ ] Gmail OAuth round-trip works; tokens encrypted at rest; refresh succeeds
- [ ] Gmail `historyId` expiry falls back to label list and re-establishes cursor (CR-5)
- [ ] Webhook endpoint accepts signed POSTs, rejects bad signatures, dedupes replays via `webhook_idempotency_keys` (CR-4)
- [ ] Outbox drainer emits `intake.item.received` exactly once per item (idempotent dummy subscriber)
- [ ] Outbox cleanup job runs hourly; dead-letter promotion verified (CR-3)
- [ ] Circuit breaker trips after 10 failures and recovers on probe
- [ ] Workspace deletion revokes upstream tokens (best-effort) and removes local creds (CR-6)
- [ ] Mobile shows healthy / degraded / auth_required states accurately
- [ ] Manual ingestion (platform admin only) gated correctly (CR-8); workspace admins do not see surface
- [ ] All operational endpoints cursor-paginated (CR-9)
- [ ] Normalizer version bump → backfill path documented and run on staging
- [ ] All feature flags default OFF; per-cohort beta rollout plan committed
- [ ] No write-back to any vendor possible (verified by integration test)
- [ ] `intake.scheduler` and `queue.drainer` run as separate processes; API restart doesn't pause sync (CR-7)

### 19.7 Phase 3 out-of-scope (defended)

If any of these appears in a Phase 3 PR, it gets reverted:

- Any verification rule, confidence score, or trust mutation beyond Phase 2 weights
- Any AI/ML usage (summarization, classification, embeddings)
- Any user-facing surface implying an item is "true" or "verified"
- Any write-back to a vendor (send, reply, label-modify, delete)
- Any cross-workspace dedupe or cross-tenant data flow
- Any content-list view in mobile
- Any push notification delivery (Phase 6)
- Any publishing or content drafting
- Multi-tenant Gmail app config sharing across workspaces
- ManualIngestScreen exposed to workspace admins (must remain platform-admin only)

---

## Appendix A — ADRs to land this phase

1. `ADR-018-outbox-pattern.md` — adopt outbox as the queue from Phase 3 day 1
2. `ADR-019-two-tier-dedupe.md` — link-anchored + date-bucket fallback (CR-2 rationale)
3. `ADR-020-normalizer-versioning.md` — separate raw and normalized; rebuild path
4. `ADR-021-intake-credentials-encryption.md` — workspace-scoped key derivation
5. `ADR-022-webhook-hmac-signing.md` — signing scheme + timestamp window + idempotency
6. `ADR-023-no-writeback-policy.md` — defensive enforcement; integration test guards
7. `ADR-024-unified-intake-sources-table.md` — why no polymorphic FK (CR-1)
8. `ADR-025-intake-process-topology.md` — separate scheduler / drainer / api processes (CR-7)

---

## Appendix B — Tradeoffs (final summary)

| Decision                                         | Cheaper path                  | Why we pay more                                            |
| ------------------------------------------------ | ----------------------------- | ---------------------------------------------------------- |
| Unified `intake_sources` table                   | Polymorphic FK to Phase 2     | DB-level constraints; clean joins; cascade clarity (CR-1)  |
| Two storage tables (raw + normalized)            | One table                     | Rules evolution without vendor re-fetch                    |
| Outbox + drainer from day 1                      | In-process pub/sub            | Replayable; crash-safe; broker-ready                       |
| `outbox_dead_letter` + cleanup                   | Indefinite outbox growth      | Bounded storage; poison isolation (CR-3)                    |
| Provider folder per vendor                       | One adapter file each         | Vendor swap = folder replacement                            |
| Workspace-scoped dedupe                          | Global hashset                | Tenant isolation; shard-friendly                            |
| **Two-tier fingerprint with date bucket**        | One formula                   | Prevents false positives on body-only items (CR-2)         |
| **Persistent webhook idempotency**               | In-process cache              | Survives restarts; bounded by TTL (CR-4)                   |
| **historyId expiry recovery**                    | Mark source broken            | Source self-heals after Gmail vacation (CR-5)              |
| **Workspace delete cascades upstream revoke**    | Just delete locally           | No orphan vendor access (CR-6)                              |
| **Separate scheduler / drainer processes**       | Colocate with API             | API restart doesn't pause sync (CR-7)                       |
| **Platform-admin-only manual ingest**            | Workspace-admin gate          | Narrowest blast radius (CR-8)                               |
| **Cursor pagination from day 1**                 | Return all rows               | Unbounded responses caught early (CR-9)                     |
| **RSS 301 persists, 302 follows**                | Treat both alike              | Source maintenance without losing the real URL (CR-10)     |
| Operational mobile UI only                       | Show ingested items           | Phase 3 has no truth claim to make                          |

---

## Appendix C — `INTAKE_KMS_KEY` Rotation Runbook (operator)

```
0. Have new key value ready (high-entropy 32+ bytes).
1. Deploy app version with dual-key support: INTAKE_KMS_KEY + INTAKE_KMS_KEY_PREVIOUS
2. Run `python -m anant.services.intake.credentials reencrypt --batch=200`
   - Reads ciphertext under PREVIOUS key, writes under new key
   - Marks rows with `kms_key_version = N+1`
3. Verify `SELECT count(*) FROM intake_credentials WHERE kms_key_version = N` == 0
4. Deploy app version without INTAKE_KMS_KEY_PREVIOUS
5. Wipe old key from secret manager
```

If step 2 fails mid-batch, re-running is idempotent — already-rotated rows are skipped.

---

*Phase 3 architecture document, frozen at Revision 2 on 2026-06-07. Implementation may proceed.*
