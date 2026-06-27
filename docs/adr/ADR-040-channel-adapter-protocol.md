# ADR-040 — Channel Adapter Protocol

**Status:** Accepted — implemented in Phase 5 Wave D
**Date:** 2026-06-27
**Phase introduced:** 5
**Related:** ADR-044 (publishing idempotency), ADR-041 (credential encryption), ADR-025 (intake process topology)

---

## 1. Context

Phase 5 publishes one approved draft to many destinations — Twitter/X, LinkedIn,
an email newsletter, Notion, an arbitrary webhook, and a local Markdown export.
Each has a different API, auth model, content shape, and failure vocabulary. The
publishing engine must not know any of that. It needs one uniform way to ask
"deliver this content to that destination" and one uniform way to learn whether a
failure is worth retrying.

## 2. Decision

**A structural `PublishChannel` Protocol (`services/publishing/channels/base.py`),
one implementation per channel, dispatched through a registry.**

The protocol is four methods:

- `validate_credentials(credentials)` — called before a target is saved; a False
  result is a 400 and the target is not persisted.
- `health_check(credentials)` — liveness probe for `POST /targets/{id}/health-check`.
- `publish(content, draft_title, credentials, config)` — deliver; returns a frozen
  `PublishResult(external_id, external_url, status)` on success, **raises** on
  failure.
- `format_content(content, max_length)` — split/shape into one or more segments
  (e.g. a tweet thread); `[]` means nothing to publish.

It is a `@runtime_checkable` `Protocol`, mirroring the Phase 3 `IntakeProvider`
shape, so a tiny fake satisfies it in tests without inheritance and each channel
folder depends only on `base.py`.

**Six implementations behind a registry** (`channels/registry.py`):
`twitter_x`, `linkedin`, `email_newsletter`, `notion`, `webhook`, `export`. The
engine dispatches via `get_channel(channel)`; tests override an entry via
`register_channel(...)`. Adapters are stateless, so one shared instance per
channel is fine.

**Retry-eligibility is a type, not a message** (§16.3). The taxonomy:

- `PermanentChannelError` — bad credentials, suspended account, malformed config,
  4xx that retrying won't fix → the engine marks the publication `failed`
  immediately, **never** retries.
- `TransientChannelError` — rate limit (429), timeout, 5xx, network → the engine
  leaves the publication `pending` for the retry mechanism, up to the ceiling.

Both subclass `ChannelError` so a catch-all still works. The shared
`channels/http.py::raise_for_status` maps status codes to this taxonomy
identically across every HTTP channel, so classification is in one place rather
than re-implemented per adapter.

## 3. Consequences

### Positive
- The engine is channel-agnostic; adding a seventh channel is one file plus one
  registry line, no engine change.
- Branching on error *type* gives a single, testable retry contract that every
  channel obeys by construction.
- The structural Protocol keeps tests fast and inheritance-free.

### Negative
- The lowest-common-denominator interface can't express channel-specific richness
  (threaded replies, rich Notion blocks) beyond what `format_content` + `publish`
  encode. Accepted for this phase; richer per-channel options can ride in `config`.
- A channel author must correctly classify every failure mode as permanent vs
  transient. Mitigated by the shared `raise_for_status` helper handling the common
  HTTP cases centrally.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| `if channel == "twitter": ...` in the engine | Couples the engine to every API; untestable in isolation; grows without bound. |
| ABC base class with inheritance | Heavier than needed; the structural Protocol gives the same contract and a trivial fake. |
| Return a status enum instead of raising | Loses the permanent/transient distinction at the type level; forces the engine to re-derive retry-eligibility from strings. |
| One generic "HTTP channel" config-driven adapter | Cannot model Twitter threading, SMTP, Notion blocks, or file export under one config shape without becoming a mini-DSL. |

---

## Addendum (dated 2026-06-27) — Citation Provenance Patch

Published content now carries provenance back to the `intelligence_objects` it
cited (Wave A `draft_citations`), sized to each channel: the engine loads
citations once per publish and appends a `format_citation_footer(...)` string to
the content of every prose channel (a short capped list for twitter_x / linkedin
/ email_newsletter, the full list for notion / export), while **webhook** keeps
content untouched and receives the citations as a separate structured
`payload["citations"]` array via one new optional `publish()` parameter
(`citations=None`). This is purely additive and backward-compatible — the
`PublishChannel` protocol's four methods are unchanged, the new parameter defaults
to `None` so every existing call site and the six adapters keep working, and
confidence tiers reuse the canonical `confidenceBand` thresholds rather than
introducing a new scheme. It is not a protocol redesign.
