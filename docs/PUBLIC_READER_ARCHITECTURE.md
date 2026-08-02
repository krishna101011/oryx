# ORYX — Public Reader Architecture

**Scope:** Public Reader Surface — NOT one of the 10 numbered phases (would
be the first unauthenticated, reader-facing route this project ever ships)
**Status:** DRAFT — Rev 1, RECON ONLY. Not designed, not reviewed, not
frozen. Committed as a documentation-only artifact for review before any
recon-into-build cycle starts — the same process Team/Workspace's
architecture went through before it was frozen.
**Depends on:** Phase 5 (`PublishTarget`, `DraftVersion`, `Publication`,
`PublicationCitation`/provenance — all already built), Phase 7 (analytics
rollups — confirmed to carry zero engagement signal today)
**Blocked on (greenfield, confirmed absent):** general-purpose rate
limiting, any caching layer (Redis/CDN/HTTP cache headers), a public
slug/short-ID scheme, reader-engagement instrumentation

---

## Revision Note

Rev 1. No prior revision exists — this document IS the recon output, not a
correction of one. Nothing below is a decision. It is what the real code
currently does and does not support, gathered so the next design pass
starts from fact rather than assumption.

## 1. Real Publish-Target Content Shape

`PublishTarget` (`core/models.py:1384-1416`, table `publish_targets`) is
pure channel identity/config — `workspace_id`, `channel` enum
(`twitter_x`, `linkedin`, `email_newsletter`, `notion`, `webhook`,
`export`), AES-256-GCM `credentials`/`credentials_iv` (never serialized to
any API response), JSONB `config`, health-check fields. It carries no
content of its own.

Every channel (`services/publishing/channels/*.py`) implements the shared
`PublishChannel` Protocol and receives one plain string
(`DraftVersion.content`), then independently reformats it: LinkedIn (raw
text, ≤3000 chars, one JSON field), X/Twitter (sentence-split into
≤280-char thread segments), Notion (newline-split into literal paragraph
blocks, no markdown parsing), newsletter (verbatim `text/plain` — no HTML
email exists today), webhook (JSON `{title, content, published_at}` plus a
separate structured `citations` array, HMAC-signed, explicitly documented
as machine consumption not human reading), export (the one channel that
emits real Markdown, `# {title}\n\n{content}`, to a local file).

There is no shared "final rendered artifact" anywhere. `DraftVersion`
has a `content_html` column, but it is optional, populated only on manual
analyst edits, never by AI generation, and never read by the publishing
engine (`engine.py` reads only `.content`). `Publication.external_url`
stores only the destination's own URL/path — a pointer to content living
on the third-party channel or local disk, never a stored rendered body.
Citation footers are appended per-channel, ad hoc, at publish time
(`engine.py:246-251`), not via any unified representation.

**Conclusion: no durable "this is the published version" body exists
today.** A public reader page would need to render `DraftVersion.content`
(a plain-text/markdown-ish blob) itself — nothing is pre-rendered to point
at.

## 2. Real Provenance Data & Boundaries

The real "show your work" table is `publication_citations` /
`PublicationCitation` (`core/models.py:1463-1494`) — a frozen, append-only
snapshot written atomically at publish time, deliberately decoupled from
later re-scoring. Columns: `publication_id`, `intelligence_object_id`,
`headline`, `epistemic_type`, `confidence_score`, `scoring_version`,
`snapshotted_at`. No JSONB columns.

The existing authenticated endpoint (`GET
/publications/{id}/provenance`, `services/publishing/router.py:84-123`,
workspace-scoped, `content.read` capability) returns exactly those fields
plus a derived `confidenceTier`, and by its own docstring deliberately does
no live join to `intelligence_objects` and exposes no claim/evidence-level
data.

Fields/joins that must never reach an unauthenticated viewer, confirmed by
inspection: any account/workspace identifier (`Publication.workspaceId
/draftId/targetId`, `ContentDraft.account_id`, `DraftVersion.edited_by`,
`AnalystReview.account_id`); `PublishTarget.credentials`/`credentials_iv`;
`IntelligenceObject.claim_ids`/`key_facts` (unconstrained JSONB)/
`intake_item_id` (one hop from raw ingested source content); raw
`Claim.text/subject/predicate/object` and `requires_analyst_review`;
`SourceCredibilityRecord` (accuracy rate, bias indicators, topic
reliability) and `VerificationRun` (source trust score, factors, AI token
cost) — both workspace-scoped internal scoring, one join away from
"verification status" if a public page ever computed it live instead of
reading the frozen snapshot; `IntakeSource.config` and
`IntakeCredentials.encrypted_token`.

**The isolation preventing all of this from leaking today is the existing
code's deliberate choice not to join back to `intelligence_objects`/
`claims` live — that boundary is doing all the protective work, not a
schema-level guarantee.**

## 3. Real Security Surface & Existing Infrastructure

This would be the first unauthenticated content-serving route. Every
currently-unauthenticated route (`/health`, `/version`, Stripe/Razorpay
webhooks, intake webhooks, Gmail OAuth callback) has its own compensating
control (vendor signature, HMAC, signed JWT state) and none of them serve
content to a browsing human — categorically different from what's being
considered here.

**Rate limiting:** `slowapi` is a dead dependency (listed in
`pyproject.toml`, never imported anywhere). The one real limiter,
`RateLimitMiddleware` (`core/middleware.py:47-109`), is in-process,
per-worker, `deque`-based, and hard-scoped to `POST
/auth/signin|signup` only — its own docstring calls it a Phase-2
placeholder ("replace with Redis-backed when we scale horizontally").
Client key is `X-Forwarded-For`/`request.client.host` — spoofable without
a trusted proxy layer, which isn't configured anywhere in this repo.
Nothing generalized exists for any other route.

**Caching:** fully absent. No Redis, no `REDIS_URL`, no CDN config, no
`Cache-Control`/`ETag` on any response anywhere. `docker-compose.local.yml`
defines only `db` + `backend`.

**Draft-vs-published guard:** genuinely spread across three tables, not
one boolean. `ContentDraft.status == "published"` is set by the publishing
engine only after fan-out delivery succeeds to at least one third-party
channel; `Publication.status` (per target) and `CalendarEntry.status` are
separate, independently-tracked states. **There is no "web"/site-rendering
channel today, and "published" currently means "delivered somewhere
external," not "safe to render on our own site."** A draft can be
`published` (tweeted) with zero design intent around public web rendering
— this is a real gap, not an assumption to build on.

**URL/slug design:** everything today is raw internal UUIDs in paths. The
one precedent for an opaque public identifier is the workspace-invite
token (`secrets.token_urlsafe` + stored hash, raw value never reused) — a
bearer-credential pattern, not a content-addressable or human-readable
slug. No short-ID library (nanoid/hashids) exists in the dependency tree.

**Net: rate limiting, caching, slug design, and "what counts as publicly
safe" are all greenfield.** The in-process rate-limiter pattern and the
invite-token opaque-ID pattern are the only two things worth imitating;
neither is production-grade for a scraping-exposed public surface as-is.

## 4. Real Analytics Dependency

`AnalyticsAggregator` (`services/analytics/`) is purely internal-team
activity analytics (intake/claims/drafts/publications lifecycle,
notification/digest delivery counts) rolled into
`analytics_rollups_daily`. There is no engagement/view concept anywhere,
and this is explicitly enforced, not just missing: `shared/types.py:606-
607` and the mirrored TS types state "no engagement field exists because
no real engagement signal exists anywhere in the platform," and
`test_publishing_response_contains_no_engagement_fields` asserts no
`view`/`engagement`/`impression`/`click` key exists at any depth in the
analytics API response.

Shipping a public page would not produce analytics data for free:
request-timing/request-ID middleware only writes to response headers,
nothing is persisted per-request, and the rollup metric catalog is closed
and asserted at import time with no page-view key. Page views, anonymous
visitors, and especially time-on-page (which requires a client-side
beacon — impossible to derive from a single server-side GET) would all
need entirely new instrumentation: a new event/table, a new write path,
and client JS. `PHASE_7_ARCHITECTURE.md` explicitly frames real engagement
data as "a new decision (possibly requiring a platform-side integration),
not something to fake here" — deliberately demoted, not merely deferred.

## 5. Hidden Reference Check

No public reader page or "published article view" mockup exists anywhere
in `docs/design-reference/`. The only superficially relevant hits are
noise: a decorative "Public handle" profile-field label in
`settings.jsx` (fake mockup data, unrelated to content publishing), and a
"CITATION" chip inside `research.jsx`'s internal analyst research
workspace view (an internal-tool UI element, not a reader-facing page). No
prior design intent for an unauthenticated article/reader view was found.

## 6. Rev 1 Decisions

**Automatic public pages.** Every ContentDraft that reaches
`status == "published"` automatically gets a public page. One open
edge case, deliberately still unresolved: whether a draft published
ONLY to a private-facing channel (e.g. an internal newsletter) should
be exempted from this rule — flagged for confirmation, not decided.

**The public-page model.** A new table, `PublicPage`, one row per
`ContentDraft` (not per `Publication` — a draft may fan out to several
external channels, but gets exactly one public page). Fields: `id`,
`content_draft_id` (FK), `workspace_id`, `slug` (opaque, unique — see
below), `content_snapshot` (Text — the rendered body at the moment of
first successful publish), `published_at`. Created automatically the
instant `ContentDraft.status` transitions to `published`.

**Content is a frozen snapshot, never a live read.** `DraftVersion.content`
is mutable and internal. The public page stores its own copy at publish
time — matching the exact philosophy `PublicationCitation` already uses
for provenance data. A later edit to the internal draft never silently
changes what's already public; that would need an explicit, separate
republish action, out of scope for Rev 1.

**Exposure boundary — explicit allow-list, not a deny-list.** The public
response includes ONLY: the content snapshot, and the exact same fields
`publication_provenance` already returns today — `headline`,
`epistemic_type`, `confidence_score`, `scoring_version`,
`snapshotted_at`. Nothing else. This reuses a boundary already decided
as safe once; it isn't inventing a new transparency policy.

Never included, ever, enforced by the query itself never joining these
tables: any account or workspace identifier, `PublishTarget.credentials`,
`Claim.text`/`subject`/`predicate`/`object`,
`IntelligenceObject.key_facts`/`claim_ids`/`intake_item_id`,
`SourceCredibilityRecord`, `VerificationRun`, `IntakeSource.config`,
`IntakeCredentials`. The public repository method must be written to
SELECT only PublicPage's own columns — never given the ability to join
outward at all, not merely trusted not to.

**URLs are opaque, not sequential, not bearer secrets.** A short, random
public ID (e.g. nanoid — confirmed no such library exists yet, so this
is a new, small dependency) — not a raw UUID, and explicitly not the
invite-token pattern (that's a one-time bearer credential; this is a
permanent, shareable, non-secret address).

**Rendering happens in the existing frontend, not a new backend
template engine.** No Jinja2, no server-rendered HTML. The backend
exposes one new, narrow, unauthenticated `GET /public/pages/{slug}`
returning the shape above; the existing Expo web app renders it as a
real screen with no auth guard.

**Rate limiting — real for this route, honestly incomplete elsewhere.**
The existing limiter is an admitted placeholder scoped only to
signin/signup. Rev 1 extends it to cover the new public route as a
genuine, immediate improvement — but a Redis-backed or edge-level
solution is real follow-up work before this route should be considered
safe under real scraping load at real scale.

**Explicitly out of scope for Rev 1.** Reader-engagement analytics
(page views, time-on-page) — needs entirely new instrumentation
including client-side JS, already correctly demoted in the Phase 7 doc.
Editing a public page after publish, or ever un-publishing one — real
product questions for a later revision.
