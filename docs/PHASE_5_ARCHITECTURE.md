# ORYX — Phase 5 Architecture Blueprint
**Document:** `docs/PHASE_5_ARCHITECTURE.md`
**Version:** Rev 1 — Authoritative and Complete
**Status:** ARCHITECTURE FROZEN — IMPLEMENTATION APPROVED (freeze approved 2026-06-16)
**Phase:** 5 — Create · Publish
**Prepared by:** Principal Architect
**Date:** 2026-06-16
**Phase 4 Freeze Anchor:** `73bd2d4` (tag: phase4-freeze)
**Brand Commit:** `c8537de` (ORYX brand migration)

---

## TABLE OF CONTENTS
1. Executive Summary
2. Complete Phase 5 Vision
3. System Architecture Diagram
4. Domain Model
5. Module Map
6. Service Boundaries
7. Database Architecture
8. Event Architecture
9. AI Architecture
10. Channel Architecture
11. Mobile Architecture
12. Backend Architecture
13. Security Architecture
14. Shared Contract Architecture
15. Content Studio Architecture
16. Publishing Engine Architecture
17. Data Flow Diagrams
18. Entity Relationship Diagrams
19. Failure Recovery Design
20. Scalability Design
21. Multi-Tenant Isolation Design
22. Operational Architecture
23. Acceptance Criteria
24. Risks
25. Tradeoffs
26. Architecture Freeze Recommendation
27. Implementation Roadmap
28. Wave Breakdown (A–F)

---

## 1. EXECUTIVE SUMMARY
Phase 5 is the creation and publishing layer of ORYX. It sits between the intelligence layer (Phase 4) and the automation layer (Phase 6). Its singular responsibility is transforming verified, analyst-approved research packets into polished, multi-format content and distributing that content across configured publishing channels.

**Phase 5 is the first phase where ORYX writes prose.** This is intentional and architecturally significant. Phases 1–4 built the infrastructure to trust information. Phase 5 consumes that trust and converts it into output. The separation is not a coincidence — it prevents the system from ever publishing content that has not passed through epistemic verification.

**What Phase 5 produces:**
- AI-generated drafts in multiple formats from research packets
- Version-controlled content with full edit history
- Structured review and approval workflows
- Scheduled publications with a content calendar
- Multi-channel distribution (Twitter/X, LinkedIn, Email Newsletter, Notion, Webhook)
- A `content.published` event that Phase 6 subscribes to for notifications

**What Phase 5 does not produce:**
- Intake items (Phase 3)
- Verified claims or intelligence objects (Phase 4)
- Notifications or automation rules (Phase 6)
- Analytics or performance tracking (Phase 7)
- Market charts (Phase 9)

**The defining constraint of Phase 5 is verified-only content.** A draft can only be created from a research packet. A research packet can only reach `ready` status if it passed Phase 4's readiness gate. Content that has not been verified cannot reach the publishing pipeline.

**Current state at Phase 5 start:**
- Phase 4 frozen at `73bd2d4`
- `research.packet.ready` event live in outbox
- `consumed_at` on research_packets waiting to be set by Phase 5
- Feature flags `ff_content_drafts` and `ff_publishing_notion` already seeded (default OFF)

---

## 2. COMPLETE PHASE 5 VISION
### 2.1 The Content Pipeline

```
RESEARCH PACKET (Phase 4)
  research.packet.ready event
        │
        ▼
DRAFT GENERATION
  AI (Claude Sonnet) reads packet
  Generates draft in requested format
  No hallucination possible — content comes from verified intelligence objects
        │
        ▼
CONTENT STUDIO
  Analyst reads, edits, annotates the draft
  Version history tracked on every edit
  Format switching (tweet → newsletter → article)
        │
        ▼
REVIEW AND APPROVAL
  Draft submitted for review
  Reviewer approves or requests changes
  Approved drafts unlock publishing
        │
        ▼
CONTENT CALENDAR
  Approved draft scheduled for publication
  Optimal slot selection
  Calendar view in mobile
        │
        ▼
PUBLISHING ENGINE
  Channel adapters distribute to targets
  Delivery confirmed per channel
  Partial publish recovery
        │
        │  content.published event
        ▼
PHASE 6 — AUTOMATION · NOTIFICATIONS
```

### 2.2 The AI Contract in Phase 5
Phase 5 is where ORYX AI writes. But the contract is strict:
1. **AI generates from packet content only.** The generation prompt contains the intelligence object headlines, key_facts, and confidence scores from the packet. The AI cannot hallucinate facts that are not in the packet.
2. **Format determines structure, not content.** The AI shapes verified intelligence into the required format — tweet, newsletter, article. It does not invent claims.
3. **Source citations are preserved.** Every generated draft includes which intelligence objects it drew from, traceable back to the original intake items.
4. **Draft is always editable.** AI output is always a starting point. The analyst has full edit authority. Nothing publishes without a human in the loop (configurable per workspace policy).
5. **Re-generation is always available.** If the analyst dislikes the AI output, they can regenerate from the same packet with different instructions (temperature, length, tone, format).

### 2.3 Content Formats

```
TWEET_THREAD        Series of connected tweets (max 280 chars each)
LINKEDIN_POST       Long-form LinkedIn native format (max 3000 chars)
NEWSLETTER_SECTION  Section for an email newsletter (HTML + plain text)
ARTICLE             Long-form article (1000–5000 words)
REPORT_SUMMARY      Executive summary (200–500 words, structured)
CUSTOM              Free format with analyst-defined length constraints
```

### 2.4 Publishing Channels

```
TWITTER_X           Via Twitter API v2
LINKEDIN            Via LinkedIn API
EMAIL_NEWSLETTER    Via configured email provider (SMTP/SendGrid/Mailchimp)
NOTION              Via Notion API (creates or updates a page)
WEBHOOK             Generic outbound webhook (JSON payload)
EXPORT              PDF or Markdown download (no external API)
```

### 2.5 Where Phase 5 Fits

```
Phase 3  FROZEN  intake engine
Phase 4  FROZEN  verify · analyze · research
Phase 5  ← YOU ARE HERE  create · publish
Phase 6  NEXT    automation · notifications (reads content.published)
Phase 7           analytics (reads publication performance)
```

---

## 3. SYSTEM ARCHITECTURE DIAGRAM

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                         ORYX PLATFORM — PHASE 5                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  PHASE 4 BOUNDARY                              PHASE 6 BOUNDARY             ║
║  ────────────────                              ────────────────              ║
║  research.packet.ready                         content.published             ║
║       │                                               │                      ║
║       ▼                                               ▼                      ║
║  ┌────────────────────────────────────────────────────────────────────────┐  ║
║  │                    PHASE 5 CONTENT LAYER                               │  ║
║  │                                                                        │  ║
║  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐   │  ║
║  │  │    DRAFT     │   │   CONTENT    │   │       REVIEW             │   │  ║
║  │  │   SERVICE    │──▶│    STUDIO    │──▶│       SERVICE            │   │  ║
║  │  │              │   │   SERVICE    │   │                          │   │  ║
║  │  │ •PacketReader│   │ •Edit/Version│   │ •Approval workflow       │   │  ║
║  │  │ •AI Generator│   │ •Format Swap │   │ •Review queue            │   │  ║
║  │  │ •Regenerate  │   │ •CitationLink│   │ •Change requests         │   │  ║
║  │  └──────────────┘   └──────────────┘   └───────────┬──────────────┘   │  ║
║  │         │                                           │                   │  ║
║  │         ▼                                           ▼                   │  ║
║  │  ┌──────────────┐                       ┌──────────────────────────┐   │  ║
║  │  │  TEMPLATES   │                       │    CONTENT CALENDAR      │   │  ║
║  │  │   SERVICE    │                       │       SERVICE            │   │  ║
║  │  │              │                       │                          │   │  ║
║  │  │ •Format defs │                       │ •Schedule approved draft │   │  ║
║  │  │ •Tone config │                       │ •Optimal slot suggestion │   │  ║
║  │  │ •Length rules│                       │ •Calendar view           │   │  ║
║  │  └──────────────┘                       └───────────┬──────────────┘   │  ║
║  │                                                     │                   │  ║
║  │                                                     ▼                   │  ║
║  │                    ┌────────────────────────────────────────────────┐   │  ║
║  │                    │          PUBLISHING ENGINE                     │   │  ║
║  │                    │                                                │   │  ║
║  │                    │  ┌──────────┐ ┌──────────┐ ┌──────────────┐   │   │  ║
║  │                    │  │ Twitter  │ │ LinkedIn │ │  Newsletter  │   │   │  ║
║  │                    │  │ Adapter  │ │ Adapter  │ │  Adapter     │   │   │  ║
║  │                    │  └──────────┘ └──────────┘ └──────────────┘   │   │  ║
║  │                    │  ┌──────────┐ ┌──────────┐ ┌──────────────┐   │   │  ║
║  │                    │  │  Notion  │ │ Webhook  │ │  Export      │   │   │  ║
║  │                    │  │ Adapter  │ │ Adapter  │ │  Adapter     │   │   │  ║
║  │                    │  └──────────┘ └──────────┘ └──────────────┘   │   │  ║
║  │                    └────────────────────────────────────────────────┘   │  ║
║  │                                                                          │  ║
║  │  ─────────────────── SHARED INFRASTRUCTURE ─────────────────────────── │  ║
║  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────────┐   │  ║
║  │  │   OUTBOX     │  │   DRAINER    │  │    PUBLISH TARGETS          │   │  ║
║  │  │   EVENTS     │  │   (Phase 3)  │  │    (workspace-configured)   │   │  ║
║  │  └──────────────┘  └──────────────┘  └─────────────────────────────┘   │  ║
║  │  ┌────────────────────────────────────────────────────────────────────┐ │  ║
║  │  │                    POSTGRESQL DATABASE                             │ │  ║
║  │  │ content_drafts · draft_versions · content_templates               │ │  ║
║  │  │ draft_reviews · publish_targets · publications                    │ │  ║
║  │  │ calendar_entries · draft_citations                                │ │  ║
║  │  └────────────────────────────────────────────────────────────────────┘ │  ║
║  └────────────────────────────────────────────────────────────────────────┘  ║
║                                                                               ║
║  MOBILE — Content tab (ff_content_drafts)                                    ║
║  ContentStudioScreen · DraftEditorScreen · ReviewQueueScreen                 ║
║  CalendarScreen · PublishHistoryScreen                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## 4. DOMAIN MODEL
### 4.1 Core Entities
**ResearchPacket** (Phase 4 — read only after consumed_at set)
The frozen, gate-validated bundle of intelligence objects. Phase 5 sets `consumed_at` when it picks up the packet. After that, the packet is immutable.

**ContentDraft**
The primary content artifact. Created from a research packet by AI. Versioned on every edit. Has a format (TWEET_THREAD, ARTICLE, etc.) and a lifecycle state (draft → in_review → approved → scheduled → published | rejected).

**DraftVersion**
Every edit to a ContentDraft creates a new DraftVersion row. The current version is the latest by version_number. No version is ever deleted. Full edit history preserved.

**DraftCitation**
Links a ContentDraft to the specific intelligence objects it drew from. Provides the provenance chain from published content back to verified intelligence.

**ContentTemplate**
A reusable format definition. Specifies: format type, max length, tone guidance (formal/conversational/analytical), structure requirements, and which channel it targets.

**DraftReview**
A review action by an analyst. Approve, reject, or request changes. Non-destructive — never mutates the draft itself.

**PublishTarget**
A configured outbound channel for a workspace. Holds channel type (TWITTER_X, LINKEDIN, etc.) and encrypted channel credentials. One workspace may have multiple targets of the same type.

**Publication**
The act of publishing a specific draft version to a specific publish target. Records the external_id returned by the channel (tweet ID, post ID, email campaign ID, etc.) and delivery status.

**CalendarEntry**
Schedules a publication for a future time. Links draft to target to scheduled_at timestamp.

### 4.2 Entity Relationships (Conceptual)

```
ResearchPacket (Phase 4)
    │ 1:N
    ▼
ContentDraft ──── N:M ────▶ IntelligenceObject (via DraftCitation)
    │
    │ 1:N (versions)
    ▼
DraftVersion (every edit)
    │
    │ 1:N (reviews)
    ▼
DraftReview (approve/reject/change_request)
    │
    │ approved version only
    ▼
CalendarEntry ──▶ PublishTarget
    │
    ▼
Publication ──▶ PublishTarget
    (status: pending → delivered | failed)
```

---

## 5. MODULE MAP

```
┌─────────────────┬──────────────────────────────────┬────────────────────────────────┐
│ Module          │ Owns                             │ Never                          │
├─────────────────┼──────────────────────────────────┼────────────────────────────────┤
│ DRAFTS          │ content_drafts                   │ channel credentials            │
│                 │ draft_versions                   │ external API calls             │
│                 │ draft_citations                  │ scheduling logic               │
│                 │ AI generation (Sonnet)           │                                │
├─────────────────┼──────────────────────────────────┼────────────────────────────────┤
│ TEMPLATES       │ content_templates                │ draft content                  │
│                 │ format definitions               │ AI calls                       │
│                 │ tone/length config               │                                │
├─────────────────┼──────────────────────────────────┼────────────────────────────────┤
│ REVIEW          │ draft_reviews                    │ draft content writes           │
│                 │ review queue                     │ publishing                     │
│                 │ approval workflow                │ scheduling                     │
├─────────────────┼──────────────────────────────────┼────────────────────────────────┤
│ CALENDAR        │ calendar_entries                 │ draft content                  │
│                 │ scheduling logic                 │ channel adapters               │
│                 │ slot management                  │                                │
├─────────────────┼──────────────────────────────────┼────────────────────────────────┤
│ PUBLISHING      │ publications                     │ draft editing                  │
│                 │ channel adapters                 │ review decisions               │
│                 │ delivery tracking                │ scheduling decisions           │
│                 │ retry logic                      │                                │
├─────────────────┼──────────────────────────────────┼────────────────────────────────┤
│ TARGETS         │ publish_targets                  │ publishing logic               │
│                 │ credential management            │ draft logic                    │
│                 │ channel health checks            │                                │
├─────────────────┼──────────────────────────────────┼────────────────────────────────┤
│ EVENTS          │ Phase 5 event catalog            │ business logic                 │
│                 │ outbox integration               │ storage writes                 │
└─────────────────┴──────────────────────────────────┴────────────────────────────────┘
READ-ONLY ACCESS (Phase 5 reads, never writes):
  research_packets         (Phase 4 — marks consumed_at only)
  intelligence_objects     (Phase 4 — read for draft generation)
  claims                   (Phase 4 — read for citations)
  workspace_sources        (Phase 2 — source context)
  preferences              (Phase 2 — content_style preference)
```

---

## 6. SERVICE BOUNDARIES
### 6.1 Folder Structure

```
apps/backend/src/anant/services/
├── drafts/
│   ├── __init__.py
│   ├── router.py           CRUD + generate + regenerate endpoints
│   ├── service.py          Orchestration + PacketConsumerHandler
│   ├── generator.py        DraftGeneratorAI (Sonnet, versioned)
│   ├── repository.py       DB operations
│   ├── schemas.py          Pydantic request/response
│   ├── models.py           ContentDraft, DraftVersion frozen dataclasses
│   └── events/
│       ├── __init__.py
│       └── constants.py    DRAFT_CREATED, DRAFT_UPDATED, DRAFT_APPROVED
│                           DRAFT_REJECTED, DRAFT_PUBLISHED
│
├── templates/
│   ├── __init__.py
│   ├── router.py           CRUD for templates
│   ├── service.py          Template management
│   ├── repository.py
│   ├── schemas.py
│   └── models.py
│
├── review/
│   ├── __init__.py
│   ├── router.py           Review action endpoints
│   ├── service.py          Approval/rejection/change-request logic
│   ├── repository.py
│   └── schemas.py
│
├── calendar/
│   ├── __init__.py
│   ├── router.py           Calendar view + scheduling endpoints
│   ├── service.py          Slot management + scheduler trigger
│   ├── repository.py
│   └── schemas.py
│
├── publishing/
│   ├── __init__.py
│   ├── router.py           Manual publish + history endpoints
│   ├── service.py          Publication orchestration
│   ├── engine.py           PublishingEngine (fan-out to adapters)
│   ├── repository.py
│   ├── schemas.py
│   └── channels/
│       ├── base.py         PublishChannel protocol (abstract)
│       ├── twitter.py      TwitterXChannel
│       ├── linkedin.py     LinkedInChannel
│       ├── newsletter.py   NewsletterChannel
│       ├── notion.py       NotionChannel
│       ├── webhook.py      WebhookChannel
│       └── export.py       ExportChannel (PDF/Markdown, no external API)
│
└── targets/
    ├── __init__.py
    ├── router.py           Target CRUD + health check endpoints
    ├── service.py          Target management + credential encryption
    ├── repository.py
    └── schemas.py
```

---

## 7. DATABASE ARCHITECTURE
### 7.1 Migration Sequence

```
0009_phase5_wave_a.py    content_drafts · draft_versions · draft_citations
0010_phase5_wave_b.py    content_templates
0011_phase5_wave_c.py    draft_reviews
0012_phase5_wave_d.py    publish_targets · publications
0013_phase5_wave_e.py    calendar_entries
```

### 7.2 Complete Table Schemas

---

#### content_drafts

```sql
CREATE TABLE content_drafts (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id         UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    account_id           UUID NOT NULL REFERENCES accounts(id),
    packet_id            UUID NOT NULL REFERENCES research_packets(id),
    template_id          UUID REFERENCES content_templates(id),
    format               content_format_enum NOT NULL,
    title                TEXT NOT NULL,
    status               draft_status_enum NOT NULL DEFAULT 'draft',
    current_version      INTEGER NOT NULL DEFAULT 1,
    generation_model     TEXT NOT NULL,   -- e.g. 'claude-sonnet-4-6'
    generation_version   INTEGER NOT NULL,
    word_count           INTEGER,
    published_at         TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- CREATE TYPE content_format_enum AS ENUM
--   ('tweet_thread','linkedin_post','newsletter_section',
--    'article','report_summary','custom');
-- CREATE TYPE draft_status_enum AS ENUM
--   ('draft','in_review','changes_requested','approved',
--    'scheduled','published','rejected','archived');
```

---

#### draft_versions

```sql
CREATE TABLE draft_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id        UUID NOT NULL REFERENCES content_drafts(id) ON DELETE CASCADE,
    version_number  INTEGER NOT NULL,
    content         TEXT NOT NULL,       -- the actual prose
    content_html    TEXT,                -- rendered HTML (optional)
    edited_by       UUID NOT NULL REFERENCES accounts(id),
    edit_note       TEXT,                -- optional change note
    word_count      INTEGER,
    token_count     INTEGER,             -- AI tokens used for generation
    is_ai_generated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (draft_id, version_number)
);
```

---

#### draft_citations

```sql
CREATE TABLE draft_citations (
    draft_id               UUID NOT NULL REFERENCES content_drafts(id) ON DELETE CASCADE,
    intelligence_object_id UUID NOT NULL REFERENCES intelligence_objects(id),
    added_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (draft_id, intelligence_object_id)
    -- Provenance: every draft knows which intelligence objects it drew from
    -- Traceable back to intake items and verified claims
);
```

---

#### content_templates

```sql
CREATE TABLE content_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    format          content_format_enum NOT NULL,
    tone            content_tone_enum NOT NULL DEFAULT 'analytical',
    max_words       INTEGER,
    min_words       INTEGER,
    structure_hint  TEXT,   -- plain text instructions for the AI
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- CREATE TYPE content_tone_enum AS ENUM
--   ('formal','analytical','conversational','authoritative','concise');
```

---

#### draft_reviews

```sql
CREATE TABLE draft_reviews (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id       UUID NOT NULL REFERENCES content_drafts(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    account_id     UUID NOT NULL REFERENCES accounts(id),
    outcome        review_outcome_enum NOT NULL,
    note           TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- CREATE TYPE review_outcome_enum AS ENUM
--   ('approved','rejected','changes_requested');
```

---

#### publish_targets

```sql
CREATE TABLE publish_targets (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id     UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name             TEXT NOT NULL,
    channel          publish_channel_enum NOT NULL,
    credentials      BYTEA NOT NULL,     -- AES-256-GCM encrypted JSON
    credentials_iv   BYTEA NOT NULL,     -- encryption IV
    config           JSONB NOT NULL DEFAULT '{}',
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    last_health_at   TIMESTAMPTZ,
    last_health_ok   BOOLEAN,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- CREATE TYPE publish_channel_enum AS ENUM
--   ('twitter_x','linkedin','email_newsletter','notion','webhook','export');
```

---

#### publications

```sql
CREATE TABLE publications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id        UUID NOT NULL REFERENCES content_drafts(id),
    version_number  INTEGER NOT NULL,
    target_id       UUID NOT NULL REFERENCES publish_targets(id),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    status          publication_status_enum NOT NULL DEFAULT 'pending',
    external_id     TEXT,       -- tweet ID, post ID, campaign ID, etc.
    external_url    TEXT,       -- published URL if available
    error_message   TEXT,
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    scheduled_at    TIMESTAMPTZ,
    published_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- CREATE TYPE publication_status_enum AS ENUM
--   ('pending','delivering','delivered','failed','cancelled');
```

---

#### calendar_entries

```sql
CREATE TABLE calendar_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    draft_id        UUID NOT NULL REFERENCES content_drafts(id),
    target_id       UUID NOT NULL REFERENCES publish_targets(id),
    scheduled_at    TIMESTAMPTZ NOT NULL,
    status          calendar_status_enum NOT NULL DEFAULT 'scheduled',
    publication_id  UUID REFERENCES publications(id),
    created_by      UUID NOT NULL REFERENCES accounts(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (draft_id, target_id)
    -- One draft can only be scheduled once per target
);
-- CREATE TYPE calendar_status_enum AS ENUM
--   ('scheduled','published','cancelled','failed');
```

### 7.3 Complete Index Registry

```sql
-- DRAFTS
CREATE INDEX idx_drafts_workspace_status
    ON content_drafts(workspace_id, status);
CREATE INDEX idx_drafts_workspace_packet
    ON content_drafts(workspace_id, packet_id);
CREATE INDEX idx_drafts_workspace_time
    ON content_drafts(workspace_id, created_at DESC);
-- VERSIONS
CREATE INDEX idx_draft_versions_draft
    ON draft_versions(draft_id, version_number DESC);
-- CITATIONS
CREATE INDEX idx_draft_citations_object
    ON draft_citations(intelligence_object_id);
-- TEMPLATES
CREATE INDEX idx_templates_workspace_format
    ON content_templates(workspace_id, format);
-- REVIEWS
CREATE INDEX idx_draft_reviews_draft
    ON draft_reviews(draft_id, created_at DESC);
CREATE INDEX idx_draft_reviews_pending
    ON draft_reviews(draft_id) WHERE outcome = 'changes_requested';
-- TARGETS
CREATE INDEX idx_publish_targets_workspace_channel
    ON publish_targets(workspace_id, channel);
CREATE INDEX idx_publish_targets_active
    ON publish_targets(workspace_id) WHERE is_active = TRUE;
-- PUBLICATIONS
CREATE INDEX idx_publications_draft
    ON publications(draft_id);
CREATE INDEX idx_publications_workspace_status
    ON publications(workspace_id, status);
CREATE INDEX idx_publications_pending
    ON publications(scheduled_at)
    WHERE status = 'pending' AND scheduled_at IS NOT NULL;
-- CALENDAR
CREATE INDEX idx_calendar_workspace_time
    ON calendar_entries(workspace_id, scheduled_at);
CREATE INDEX idx_calendar_scheduled
    ON calendar_entries(scheduled_at)
    WHERE status = 'scheduled';
```

### 7.4 Packet Consumption
Phase 5 sets `consumed_at` on Phase 4's `research_packets` table:

```sql
-- Phase 5 only operation on Phase 4 tables
UPDATE research_packets
SET consumed_at = NOW()
WHERE id = $packet_id
  AND consumed_at IS NULL;  -- idempotent guard
```

This is the only write Phase 5 ever makes to a Phase 4 table.

---

## 8. EVENT ARCHITECTURE
### 8.1 Event Catalog
All Phase 5 events use the ADR-014 DomainEvent envelope.

```
Event Name                     Emitter          Payload
──────────────────────────────────────────────────────────────────────────
content.draft.created        drafts svc    draftId · packetId · format
                                           workspaceId · generationModel
                                           versionNumber
content.draft.updated        drafts svc    draftId · workspaceId
                                           versionNumber · editedBy
content.draft.approved       review svc    draftId · workspaceId
                                           reviewedBy · versionNumber
content.draft.rejected       review svc    draftId · workspaceId
                                           reviewedBy · reason
content.draft.scheduled      calendar svc  draftId · targetId
                                           scheduledAt · workspaceId
                                           calendarEntryId
content.published            publishing    draftId · publicationId
                                           targetId · channel
                                           externalId · workspaceId
                             ← Phase 6 subscribes to this event
content.publish.failed       publishing    draftId · publicationId
                                           targetId · channel
                                           error · workspaceId
                                           attemptCount
```

### 8.2 Causation Chain

```
research.packet.ready         (Phase 4 — origin)
  causationId: null
      │
      ▼
content.draft.created         (on packet consumption + AI generation)
  causationId: research.packet.ready.id
      │
      ▼
content.draft.updated         (on each edit)
  causationId: content.draft.created.id
      │
      ▼
content.draft.approved        (on approval)
  causationId: content.draft.updated.id
      │
      ├────────────────────────────────▶ content.draft.scheduled (if scheduled)
      │                                    causationId: content.draft.approved.id
      │
      ▼
content.published             (on delivery)
  causationId: content.draft.approved.id
      │
      ▼
[ Phase 6 boundary ]
```

### 8.3 Phase 4 Subscription
Phase 5 subscribes to `research.packet.ready` at service startup.
Handler: `PacketConsumerHandler`
First action: Set `research_packets.consumed_at = NOW()` (marks handoff complete).
Then: Trigger draft generation.
Idempotent: if `consumed_at` already set, skip (re-delivery safe).

---

## 9. AI ARCHITECTURE
### 9.1 Model Selection
Phase 5 uses **Claude Sonnet** for draft generation — not Haiku.

```
Phase 4 AI calls:  Claude Haiku (extraction, classification, linking)
                   Speed > quality. Short outputs. Structured data.
Phase 5 AI calls:  Claude Sonnet (draft generation)
                   Quality > speed. Long outputs. Flowing prose.
```

Rationale: Draft generation produces 200–5000 words of polished content. The output quality directly affects publication quality. Haiku's output quality at this task is not acceptable for a premium intelligence platform.

### 9.2 Generation Prompt Architecture
The generation prompt has four layers:
**Layer 1 — System context:**

```
You are the ORYX content generation system. You write verified
financial intelligence as [format]. You write only from the
provided intelligence objects. You do not introduce facts,
claims, or figures that are not present in the source material.
You cite your sources by referencing the intelligence object
headlines.
```

**Layer 2 — Format specification:**

```
Format: [from content_template]
Tone: [from content_template]
Max words: [from content_template]
Structure: [from content_template.structure_hint]
```

**Layer 3 — Source material (from research packet):**

```
INTELLIGENCE OBJECTS:
[For each intelligence_object in packet:]
  Headline: [headline]
  Confidence: [confidence_score]
  Key Facts:
    [key: value for each key_fact]
  Epistemic Type: [epistemic_type]
```

**Layer 4 — Analyst instructions (optional):**

```
[From the generate request body — analyst can provide
 specific angle, emphasis, or length instructions]
```

### 9.3 Generation Versioning

```
GENERATION_MODEL_VERSION = 1  (integer constant in generator.py)
Tracks: model name + prompt version + system context version
Stored: content_drafts.generation_version
Purpose: when the prompt or model changes, existing drafts are
         not re-generated automatically. Analyst can request
         re-generation from the same packet.
```

### 9.4 AI Cost Control
Phase 5 inherits the circuit breaker from Phase 4:

```python
# call_type = "draft_generator"
circuit_breaker.check("draft_generator")
```

Per-workspace daily token budget applies to Phase 5 generation calls.
Draft generation is expensive (Sonnet, long outputs).
Default budget remains 100,000 tokens/workspace/day.
Phase 5 generation call type can have its own sub-budget configured
via feature_flag_overrides if needed.

### 9.5 Regeneration
Analyst can regenerate a draft from the same packet at any time:

```
POST /v1/drafts/{id}/regenerate
Body: { instructions: string? }  -- optional analyst angle
```

Regeneration:
- Creates a new DraftVersion with is_ai_generated = True
- Increments current_version
- Does NOT create a new ContentDraft row
- Does NOT re-consume the packet
- Emits DRAFT_UPDATED event

The packet remains consumed (`consumed_at` already set). Regeneration reads from the same packet snapshot.

---

## 10. CHANNEL ARCHITECTURE
### 10.1 Channel Adapter Protocol
All channel adapters implement the same protocol:

```python
class PublishChannel(Protocol):
    channel_type: str  # e.g. "twitter_x"
    async def validate_credentials(
        self, credentials: dict
    ) -> ValidationResult:
        """Check credentials are valid before saving."""
        ...
    async def health_check(
        self, credentials: dict
    ) -> HealthResult:
        """Periodic liveness check."""
        ...
    async def publish(
        self,
        draft_version: DraftVersion,
        draft: ContentDraft,
        credentials: dict,
        config: dict,
    ) -> PublishResult:
        """
        Publish the content.
        Returns: PublishResult(external_id, external_url, status)
        Must be idempotent: same draft_version_id → same external post.
        """
        ...
    def format_content(
        self,
        content: str,
        format: ContentFormat,
    ) -> list[str]:
        """
        Format content for this channel.
        Returns list of segments (e.g. individual tweets for a thread).
        """
        ...
```

### 10.2 Channel Implementations
**TwitterXChannel**
- API: Twitter API v2
- Auth: OAuth 2.0 App-only or User-context
- Idempotency: check for existing tweet with same content_hash before posting
- Tweet thread: post sequentially, each reply-to the previous
- External ID: tweet ID (first tweet in thread for threads)
- Credential fields: bearer_token, client_id, client_secret, access_token, access_token_secret

**LinkedInChannel**
- API: LinkedIn API v2
- Auth: OAuth 2.0 with openid+profile+email+w_member_social scopes
- Format: ugcPosts endpoint
- External ID: LinkedIn post URN
- Credential fields: access_token, person_urn

**NewsletterChannel**
- Configurable: SendGrid, Mailchimp, SMTP
- Sub-type stored in config.provider field
- External ID: campaign ID or message ID
- For SMTP: sends immediately; no campaign tracking
- Credential fields: api_key, list_id, from_email, from_name

**NotionChannel**
- API: Notion API v1
- Creates a new page in a configured database or parent page
- Maps draft content to Notion block format (paragraphs, headings)
- External ID: Notion page ID
- External URL: Notion page URL
- Credential fields: integration_token, parent_page_id

**WebhookChannel**
- Outbound POST to configured URL
- Payload: { draft_id, version_number, content, format, published_at, citations }
- Signed with HMAC-SHA256 using a shared secret
- Retries: 3 attempts with exponential backoff
- Credential fields: url, secret

**ExportChannel**
- No external API
- Generates PDF (via weasyprint or reportlab) or Markdown file
- Returns a signed download URL (stored in local file storage)
- External URL: download URL
- Credential fields: none (format: 'pdf' | 'markdown' stored in config)

### 10.3 Credential Encryption
All channel credentials encrypted at rest:

```python
# AES-256-GCM encryption
# Key: ORYX_PUBLISH_KEY from environment (32 bytes)
# IV: random 12 bytes per record
# Stored as BYTEA: credentials column (ciphertext) + credentials_iv column
def encrypt_credentials(plaintext: dict) -> tuple[bytes, bytes]:
    key = settings.oryx_publish_key  # 32-byte secret
    iv = os.urandom(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    ciphertext, _ = cipher.encrypt_and_digest(json.dumps(plaintext).encode())
    return ciphertext, iv
def decrypt_credentials(ciphertext: bytes, iv: bytes) -> dict:
    key = settings.oryx_publish_key
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    plaintext = cipher.decrypt(ciphertext)
    return json.loads(plaintext)
```

Credentials never appear in logs, never in event payloads, never in API responses (write-only).

---

## 11. MOBILE ARCHITECTURE
### 11.1 Feature Flag Gates

```
ff_content_drafts     →  drafts/ module (content studio, drafts, review)
ff_publishing_notion  →  targets/ module (publish targets config)
                          (flag name is legacy; gates ALL channel targets)
```

Both flags already seeded in the database (default OFF).

### 11.2 Module Structure

```
apps/mobile/src/modules/content/
├── screens/
│   ├── ContentHomeScreen.tsx          Draft list + status overview
│   ├── DraftEditorScreen.tsx          Rich text editor + version history
│   ├── DraftDetailScreen.tsx          Read-only view + actions
│   ├── GenerateDraftScreen.tsx        Select packet + format + template
│   ├── ReviewQueueScreen.tsx          Drafts pending review
│   ├── CalendarScreen.tsx             Content calendar grid view
│   ├── PublishHistoryScreen.tsx       All publications + delivery status
│   └── PublishTargetScreen.tsx        Configure channels
├── components/
│   ├── DraftCard.tsx                  headline · format · status pill · word count
│   ├── FormatBadge.tsx                TWEET · ARTICLE · NEWSLETTER etc.
│   ├── DraftStatusPill.tsx            draft · in_review · approved · published
│   ├── VersionHistoryList.tsx         Scrollable list of DraftVersion entries
│   ├── CitationTag.tsx                Intelligence object reference chip
│   ├── ChannelBadge.tsx               Twitter · LinkedIn · Newsletter etc.
│   ├── PublicationStatusIcon.tsx      pending · delivered · failed
│   └── CalendarDayCell.tsx            Day cell with scheduled publications
└── hooks/
    ├── useDraftList.ts
    ├── useDraftEditor.ts
    ├── useGenerateDraft.ts
    ├── useReviewQueue.ts
    ├── useCalendar.ts
    └── usePublications.ts
```

### 11.3 Navigation Contract

```
RootTabNavigator
├── Home
├── Research              (ff_research — Phase 4)
├── Content               (ff_content_drafts → ContentHomeScreen)
│   ├── Draft Detail      → DraftEditorScreen
│   ├── Generate          → GenerateDraftScreen
│   ├── Review Queue      → ReviewQueueScreen
│   ├── Calendar          → CalendarScreen
│   └── Publish History   → PublishHistoryScreen
├── Activity              (ff_activity)
└── Settings
    └── Publish Targets   (ff_publishing_notion → PublishTargetScreen)
```

### 11.4 Content Studio — Layout Contract (Bloomberg × Apple)
The content studio is the densest screen in Phase 5. It must feel like a Bloomberg terminal editing surface — functional, data-rich — inside Apple-level clean chrome.

```
DraftEditorScreen:
┌──────────────────────────────────────────────────────────────────┐
│  [← Back]   [Title — editable inline]        [DraftStatusPill]  │
│  [FormatBadge]  [word_count]  [version v3 ▾]  [•••]             │
├──────────────────────────────────────────────────────────────────┤
│  CITATIONS                                              [+ Add]  │
│  [CitationTag: Headline 1]  [CitationTag: Headline 2]            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Rich text editing area — full width]                           │
│   Content flows here. Analyst can type freely.                   │
│   AI-generated content appears here initially.                   │
│                                                                  │
│   [For tweet thread: individual tweet cards numbered 1/4 2/4]   │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  [Regenerate with AI]    [Submit for Review]    [Schedule ▾]    │
└──────────────────────────────────────────────────────────────────┘
Design principles:
- Editor area takes ≥65% of screen height
- No decorative chrome in the editor area
- Citations appear above content (provenance visible at all times)
- Status pill always visible in header
- Word count always visible (Bloomberg density)
- Actions always reachable at bottom without scrolling
```

### 11.5 Calendar Screen — Layout Contract

```
CalendarScreen:
┌──────────────────────────────────────────────────────────────────┐
│  [◀ June 2026]  [▶]              [+ Schedule]                    │
├──────────────────────────────────────────────────────────────────┤
│  Mon  Tue  Wed  Thu  Fri  Sat  Sun                               │
│  ─────────────────────────────────────────────                   │
│  [CalendarDayCell × 30 days]                                     │
│  Each cell: date number + channel icon dots for scheduled items  │
│  Teal dot = scheduled · Green = published · Red = failed         │
├──────────────────────────────────────────────────────────────────┤
│  SCHEDULED THIS WEEK                                             │
│  [DraftCard with scheduled_at time + ChannelBadge]              │
│  [DraftCard ...]                                                 │
└──────────────────────────────────────────────────────────────────┘
```

### 11.6 Design Token Extensions

```
-- Draft status colors
--color-status-draft:             #4E5D6C   grey (inactive)
--color-status-in-review:         #F59E0B   amber
--color-status-approved:          #22C55E   aurora green
--color-status-scheduled:         #6366F1   indigo
--color-status-published:         #00D4C8   accent teal
--color-status-rejected:          #EF4444   red
-- Format badge colors
--color-format-tweet:             #60A5FA   soft blue
--color-format-linkedin:          #6366F1   indigo
--color-format-newsletter:        #9B5DE5   violet
--color-format-article:           #00D4C8   teal
--color-format-report:            #4E5D6C   grey
--color-format-custom:            #8B95A5   secondary
-- Calendar dots
--color-cal-scheduled:            #6366F1   indigo dot
--color-cal-published:            #22C55E   green dot
--color-cal-failed:               #EF4444   red dot
-- Channel badge colors
--color-channel-twitter:          #60A5FA   soft blue
--color-channel-linkedin:         #6366F1   indigo
--color-channel-newsletter:       #9B5DE5   violet
--color-channel-notion:           #00D4C8   teal
--color-channel-webhook:          #F59E0B   amber
--color-channel-export:           #8B95A5   secondary grey
```

---

## 12. BACKEND ARCHITECTURE
### 12.1 Draft Generation Flow

```python
async def generate_draft(
    packet_id: uuid,
    format: ContentFormat,
    template_id: uuid | None,
    instructions: str | None,
    account_id: uuid,
    workspace_id: uuid,
    session: AsyncSession,
) -> ContentDraft:
    # 1. Load and validate packet
    packet = await research_packet_repo.get(packet_id, session)
    assert packet.status == 'ready'
    assert packet.workspace_id == workspace_id
    # 2. Set consumed_at (Phase 5 handoff — idempotent)
    if packet.consumed_at is None:
        await research_packet_repo.mark_consumed(packet_id, session)
    # 3. Load intelligence objects from packet
    objects = await intelligence_repo.get_many(
        packet.intelligence_object_ids, session
    )
    # 4. Load template (use workspace default if not specified)
    template = await template_repo.get(template_id or default, session)
    # 5. Build generation prompt
    prompt = build_generation_prompt(objects, template, instructions)
    # 6. Call Claude Sonnet
    content, tokens = await generator.generate(prompt, format)
    # 7. Create draft + first version (atomic)
    draft = ContentDraft(
        packet_id=packet_id,
        format=format,
        template_id=template.id,
        status='draft',
        generation_model='claude-sonnet-4-6',
        generation_version=GENERATION_MODEL_VERSION,
    )
    version = DraftVersion(
        version_number=1,
        content=content,
        edited_by=account_id,
        is_ai_generated=True,
        token_count=tokens,
    )
    citations = [DraftCitation(intelligence_object_id=o.id)
                 for o in objects]
    await draft_repo.create_with_version(draft, version, citations, session)
    # 8. Emit DRAFT_CREATED
    await outbox.enqueue(DRAFT_CREATED, {...}, session)
    # 9. Commit (draft + version + citations + outbox — atomic)
    return draft
```

### 12.2 Publishing Engine Flow

```python
async def publish(
    draft_id: uuid,
    target_id: uuid,
    workspace_id: uuid,
    session: AsyncSession,
) -> Publication:
    # 1. Load draft — must be approved
    draft = await draft_repo.get(draft_id, session)
    assert draft.status == 'approved'
    assert draft.workspace_id == workspace_id
    # 2. Load current version content
    version = await draft_repo.get_version(
        draft_id, draft.current_version, session
    )
    # 3. Load publish target + decrypt credentials
    target = await target_repo.get(target_id, session)
    credentials = decrypt_credentials(target.credentials, target.credentials_iv)
    # 4. Get channel adapter
    adapter = channel_registry.get(target.channel)
    # 5. Create publication record (pending)
    publication = await pub_repo.create(
        draft_id=draft_id,
        version_number=draft.current_version,
        target_id=target_id,
        status='pending',
        session=session,
    )
    # 6. Call channel adapter
    try:
        result = await adapter.publish(version, draft, credentials, target.config)
        await pub_repo.mark_delivered(
            publication.id, result.external_id, result.external_url, session
        )
        await draft_repo.mark_published(draft_id, session)
        await outbox.enqueue(CONTENT_PUBLISHED, {...}, session)
    except ChannelError as e:
        await pub_repo.mark_failed(publication.id, str(e), session)
        await outbox.enqueue(CONTENT_PUBLISH_FAILED, {...}, session)
        raise
    return publication
```

### 12.3 Scheduler
The calendar scheduler runs as a background task (same pattern as Phase 3 scheduler):

```
Every 60 seconds:
  Query calendar_entries WHERE:
    status = 'scheduled'
    AND scheduled_at <= NOW() + 5 minutes
    AND scheduled_at > NOW() - 5 minutes
  For each entry:
    Trigger publishing engine for (draft_id, target_id)
    Update calendar_entry.status = 'published' | 'failed'
    Update calendar_entry.publication_id
```

---

## 13. SECURITY ARCHITECTURE
### 13.1 Authentication
Phase 5 inherits Phase 2's auth stack unchanged. No new auth primitives.

### 13.2 Channel Credential Security

```
Credentials never stored in plaintext
Credentials never logged
Credentials never returned by GET endpoints
Credentials validated before save (adapter.validate_credentials())
Credentials re-encrypted if ORYX_PUBLISH_KEY is rotated
ORYX_PUBLISH_KEY: 32-byte secret in environment
                   Never committed to code
                   Rotatable via key rotation procedure
```

### 13.3 Content Security

```
Draft content never injected into SQL (parameterized only)
AI generation output sanitized before storage
HTML content (newsletter) sanitized with allowlist
No draft content in event payloads (IDs only)
No draft content in log lines
```

### 13.4 Webhook Outbound Security
For WebhookChannel:
- HMAC-SHA256 signature on every outbound payload
- Header: `X-ORYX-Signature: sha256=<hex>`
- Header: `X-ORYX-Timestamp: <unix-seconds>`
- ±5 minute replay window
- Receiver should validate signature before processing

### 13.5 Publish Target Isolation

```
publish_targets are workspace-scoped
No workspace can publish to another workspace's targets
target_id validated against workspace_id on every publish call
channel credentials are workspace-isolated
```

---

## 14. SHARED CONTRACT ARCHITECTURE
### 14.1 New Type Files

```
packages/shared-types/src/
├── drafts.ts        ContentFormat · DraftStatus · ContentDraft ·
│                    DraftVersion · DraftCitation · GenerateRequest
├── templates.ts     ContentTone · ContentTemplate
├── review.ts        ReviewOutcome · DraftReview
├── publishing.ts    PublishChannel · PublicationStatus ·
│                    PublishTarget · Publication
├── calendar.ts      CalendarStatus · CalendarEntry
└── events/
    └── phase5.ts    DomainEvent payload types for all Phase 5 events
```

### 14.2 Key Types

```typescript
// drafts.ts
export type ContentFormat =
  | 'tweet_thread' | 'linkedin_post' | 'newsletter_section'
  | 'article' | 'report_summary' | 'custom';
export type DraftStatus =
  | 'draft' | 'in_review' | 'changes_requested' | 'approved'
  | 'scheduled' | 'published' | 'rejected' | 'archived';
export interface ContentDraft {
  id: string;
  workspaceId: string;
  accountId: string;
  packetId: string;
  templateId: string | null;
  format: ContentFormat;
  title: string;
  status: DraftStatus;
  currentVersion: number;
  generationModel: string;
  wordCount: number | null;
  publishedAt: string | null;
  createdAt: string;
  updatedAt: string;
}
export interface DraftVersion {
  id: string;
  draftId: string;
  versionNumber: number;
  content: string;
  contentHtml: string | null;
  editedBy: string;
  editNote: string | null;
  wordCount: number | null;
  tokenCount: number | null;
  isAiGenerated: boolean;
  createdAt: string;
}
export interface GenerateRequest {
  packetId: string;
  format: ContentFormat;
  templateId?: string;
  instructions?: string;
}
// publishing.ts
export type PublishChannel =
  | 'twitter_x' | 'linkedin' | 'email_newsletter'
  | 'notion' | 'webhook' | 'export';
export type PublicationStatus =
  | 'pending' | 'delivering' | 'delivered' | 'failed' | 'cancelled';
export interface Publication {
  id: string;
  draftId: string;
  versionNumber: number;
  targetId: string;
  workspaceId: string;
  status: PublicationStatus;
  externalId: string | null;
  externalUrl: string | null;
  errorMessage: string | null;
  scheduledAt: string | null;
  publishedAt: string | null;
  createdAt: string;
}
```

### 14.3 MeResponse Extension

```typescript
interface MeResponse {
  // ...all existing Phase 2 + Phase 4 fields...
  content: {
    draftCount: number;        // total drafts in workspace
    pendingReviewCount: number; // drafts in 'in_review' status
    scheduledCount: number;     // drafts in 'scheduled' status
    publishedThisWeek: number;  // publications delivered in last 7 days
  };
}
```

---

## 15. CONTENT STUDIO ARCHITECTURE
### 15.1 Version Control Model
Every save creates a new version. The model is append-only.

```
Version 1: AI-generated (is_ai_generated=True)
Version 2: Analyst edit (is_ai_generated=False)
Version 3: AI regeneration (is_ai_generated=True)
Version 4: Analyst edit (is_ai_generated=False)
  ↑
content_drafts.current_version = 4
```

Rules:
- current_version always points to the latest version
- No version is ever deleted
- Analyst can revert to a previous version (creates a new version with that content)
- Re-generation creates a new version, does not overwrite

### 15.2 Draft Lifecycle

```
[Created from packet]
        │
        ▼
    DRAFT ──────────────────────────────┐
        │                               │ (analyst edits)
        │ (submit for review)           │
        ▼                               │
    IN_REVIEW                           │ CHANGES_REQUESTED
        │                               │      │
        │ (reviewer approves)           │      │ (analyst edits)
        ▼                               │      │
    APPROVED ◄──────────────────────────┘      │
        │                                      │
        ├──────────────────────────────────────┘
        │
        ├── (analyst schedules) → SCHEDULED
        │                              │ (scheduler fires)
        │                              ▼
        └── (analyst publishes now) → PUBLISHED
                                       │
                                       (emits content.published)
REJECTED ← reviewer rejects at any point
ARCHIVED ← analyst archives (soft delete)
```

### 15.3 Review Policy
Review is configurable per workspace via preferences:

```
verification_strictness = 'strict'    → review required before publishing
verification_strictness = 'balanced'  → review required (default)
verification_strictness = 'loose'     → review optional (analyst can self-approve)
```

The `loose` setting allows the same account to submit and approve their own draft.
The `balanced` and `strict` settings require a different account to approve.
Platform admins can always override this policy.

---

## 16. PUBLISHING ENGINE ARCHITECTURE
### 16.1 Fan-Out Pattern
One draft can be published to multiple targets simultaneously:

```
POST /v1/drafts/{id}/publish
Body: { target_ids: [uuid, uuid, uuid] }
```

The engine creates one Publication record per target and dispatches them in parallel. Each is independent — failure of one does not affect others. The draft status becomes `published` when at least one publication succeeds.

### 16.2 Idempotency
Publishing is idempotent by `(draft_id, version_number, target_id)`:

```python
# Before calling the channel adapter:
existing = await pub_repo.get_by_draft_target(
    draft_id, version_number, target_id
)
if existing and existing.status == 'delivered':
    return existing  # Already published — return existing publication
```

This prevents duplicate posts on re-delivery of `content.draft.approved` events.

### 16.3 Retry Strategy

```
Failed publications retry via outbox with exponential backoff:
  Attempt 1: immediate
  Attempt 2: 5 min delay
  Attempt 3: 30 min delay
  Attempt 4: 2 hour delay
  Attempt 5: dead letter
PermanentChannelError (invalid credentials, account suspended):
  → immediate dead letter, no retry
  → analyst notified via publication.status = 'failed'
  → error_message populated with human-readable explanation
TransientChannelError (rate limit, timeout, 5xx):
  → retry with backoff
  → after 5 attempts → dead letter
```

### 16.4 Partial Publication Recovery
If publishing to 3 targets and 2 succeed + 1 fails:
- 2 Publications marked `delivered`
- 1 Publication marked `failed`
- draft.status = `published` (at least one succeeded)
- `content.published` emitted for each successful publication
- `content.publish.failed` emitted for the failure
- Analyst can retry the failed publication independently

---

## 17. DATA FLOW DIAGRAMS
### 17.1 Full Content Pipeline

```
PHASE 4 OUTBOX
  outbox_events WHERE event_name = 'research.packet.ready'
        │
        │  Drainer picks up event
        ▼
STEP 1: PACKET CONSUMPTION
  Set research_packets.consumed_at = NOW() (idempotent)
  Load all intelligence_objects from packet.intelligence_object_ids
  Validate packet.status = 'ready'
  Validate all objects are non-contested OR conflict-acknowledged
STEP 2: AUTO-DRAFT or MANUAL
  Option A (auto): Generate draft immediately on packet receipt
    (workspace preference: auto_draft = true)
  Option B (manual): Analyst opens ContentHomeScreen
    Selects packet from list → GenerateDraftScreen
    Chooses format + template → triggers generation
STEP 3: AI GENERATION
  Build prompt from: intelligence objects + template + analyst instructions
  Call Claude Sonnet
  Store content as DraftVersion 1 (is_ai_generated=True)
  Create draft_citations for all source objects
  Draft status = 'draft'
  Emit DRAFT_CREATED
STEP 4: CONTENT STUDIO (ANALYST)
  Analyst reads AI draft on DraftEditorScreen
  Edits content → each save creates new DraftVersion
  Can regenerate (→ new version, AI-generated)
  Can switch format (resets to new AI generation)
  Can add/remove citations
  Draft status = 'draft' (editable)
STEP 5: REVIEW SUBMISSION
  Analyst taps "Submit for Review"
  Draft status → 'in_review'
  Emit DRAFT_UPDATED
  Reviewer sees draft in ReviewQueueScreen
STEP 6: REVIEW DECISION
  Reviewer approves:
    Draft status → 'approved'
    Emit DRAFT_APPROVED
    Analyst can now schedule or publish immediately
  Reviewer requests changes:
    Draft status → 'changes_requested'
    Analyst returns to editor (status → 'draft')
  Reviewer rejects:
    Draft status → 'rejected'
    Draft cannot be published
STEP 7: SCHEDULING OR IMMEDIATE PUBLISH
  Option A (schedule):
    Analyst selects target(s) + time on CalendarScreen
    Creates calendar_entries
    Draft status → 'scheduled'
    Emit DRAFT_SCHEDULED
  Option B (publish now):
    Analyst taps "Publish" with target(s) selected
    Triggers publishing engine immediately
STEP 8: PUBLISHING ENGINE
  For each target:
    Decrypt credentials
    Format content for channel
    Call channel adapter
    On success:
      Publication status → 'delivered'
      Emit CONTENT_PUBLISHED
    On failure:
      Publication status → 'failed'
      Retry or dead letter
      Emit CONTENT_PUBLISH_FAILED
  Draft status → 'published' (if any target succeeded)
STEP 9: PHASE 6 BOUNDARY
  Phase 6 subscribes to content.published
  Triggers: notifications to followers, automation rules, digests
```

### 17.2 Regeneration Flow

```
Analyst in DraftEditorScreen
  Taps "Regenerate with AI"
  Optionally enters new instructions
        │
        ▼
  POST /v1/drafts/{id}/regenerate
  Body: { instructions: "Focus on the macro implications" }
        │
        ▼
  Generator loads same packet (already consumed)
  Builds new prompt with original + new instructions
  Calls Claude Sonnet
  Creates new DraftVersion (version_number + 1, is_ai_generated=True)
  Updates content_drafts.current_version
  Emits DRAFT_UPDATED
        │
        ▼
  DraftEditorScreen refreshes with new content
  Version history shows previous versions in VersionHistoryList
```

---

## 18. ENTITY RELATIONSHIP DIAGRAMS

```
research_packets (Phase 4)
    │ consumed by
    │ 1:N
    ▼
content_drafts
    │ workspace_id · account_id · packet_id · format · status
    │
    ├── 1:N ──▶ draft_versions
    │              version_number · content · is_ai_generated
    │              edited_by · token_count
    │
    ├── N:M ──▶ intelligence_objects (via draft_citations)
    │              provenance chain
    │
    ├── 1:N ──▶ draft_reviews
    │              outcome · note · version_number
    │
    ├── 1:N ──▶ publications
    │              target_id · status · external_id · external_url
    │
    └── 1:N ──▶ calendar_entries
                   target_id · scheduled_at · publication_id
publish_targets (workspace-owned)
    │ workspace_id · channel · credentials (encrypted)
    │
    ├──▶ publications (used in)
    └──▶ calendar_entries (targeted by)
content_templates (workspace-owned)
    │ format · tone · max_words · structure_hint
    └──▶ content_drafts (used by)
workspaces (Phase 2)
    │
    ├──▶ content_drafts
    ├──▶ publish_targets
    ├──▶ content_templates
    ├──▶ publications
    └──▶ calendar_entries
```

---

## 19. FAILURE RECOVERY DESIGN
### 19.1 Draft Generation Failure

```
Claude Sonnet call fails:
  → Circuit breaker fires (call_type="draft_generator")
  → Draft creation is NOT attempted (no partial draft)
  → Analyst sees error in GenerateDraftScreen
  → Can retry generation (packet remains consumed)
  → Packet.consumed_at already set — packet is still "theirs"
AI budget exhausted:
  → Generation blocked
  → Analyst sees "Daily AI budget reached" message
  → Budget resets at UTC midnight
  → Draft can be created manually (analyst types content directly)
```

### 19.2 Publication Failure

```
Channel adapter fails:
  → Publication.status = 'failed'
  → error_message populated
  → PublishHistoryScreen shows failure with error
  → Analyst can retry: POST /v1/publications/{id}/retry
  → Retry creates new attempt on existing publication record
Permanent failure (bad credentials, suspended account):
  → PermanentChannelError
  → No retry
  → publish_targets.last_health_ok = false
  → Analyst notified to reconfigure target
Partial multi-target failure:
  → Failed targets show individually in PublishHistoryScreen
  → Successful targets unaffected
  → Analyst retries only failed targets
```

### 19.3 Scheduler Failure

```
Scheduler misses a scheduled publication:
  → calendar_entries with scheduled_at in the past and status='scheduled'
  → On next scheduler tick: detect overdue entries
  → Publish up to 15 minutes late (grace window)
  → Beyond 15 minutes: mark as failed, notify analyst
Scheduler process restarts:
  → Queries calendar_entries on startup for overdue entries
  → Processes missed publications immediately
  → Idempotent: existing delivery check prevents double-publish
```

### 19.4 Packet Already Consumed

```
Scenario: analyst tries to generate from a packet that another
          session already consumed.
Detection:
  consumed_at IS NOT NULL on the packet
Response:
  Return the existing draft(s) created from this packet
  via GET /v1/drafts?packet_id={id}
  Do NOT re-consume or re-generate
  Show analyst: "A draft was already created from this packet"
```

---

## 20. SCALABILITY DESIGN
### 20.1 Draft Content Storage
`draft_versions.content` is TEXT (potentially large for articles).
Large content stored inline — PostgreSQL handles up to 1GB per row via TOAST.
At Phase 5 launch volumes this is appropriate.
Phase 7+ may introduce object storage for long-form content.

### 20.2 Content Calendar
The scheduler polls every 60 seconds.
`idx_calendar_scheduled` partial index on `scheduled_at WHERE status='scheduled'`
makes the polling query sub-millisecond even at millions of entries.

### 20.3 Channel Rate Limiting
Each channel adapter manages its own rate limiting:

```
TwitterXChannel:   300 tweets/15min per app (v2 limit)
LinkedInChannel:   150 API calls/day per app
NewsletterChannel: SendGrid 100 emails/second
NotionChannel:     3 requests/second
WebhookChannel:    No platform limit — adapter handles target backpressure
```

Per-workspace channel rate limits enforced via feature_flag_overrides.

### 20.4 Retention Windows

```
content_drafts            Account close or explicit archive
draft_versions            Indefinite (audit trail)
draft_citations           Indefinite (provenance)
draft_reviews             Indefinite (audit trail)
publish_targets           Account close
publications (delivered)  2 years minimum → archive
publications (failed)     90 days → archive
calendar_entries          1 year after scheduled_at → archive
content_templates         Account close
```

---

## 21. MULTI-TENANT ISOLATION DESIGN

```
Layer 1 — Database:
  workspace_id on every Phase 5 table
  All queries include WHERE workspace_id = $current_workspace
  Publish targets: workspace-scoped credentials
  Draft citations: isolated (intelligence_objects are workspace-scoped)
Layer 2 — Channel credentials:
  Credentials encrypted with workspace-specific IV
  No credential sharing across workspaces
  Workspace A's Twitter credentials cannot access Workspace B's drafts
Layer 3 — Content isolation:
  Draft content never exposed to other workspaces
  Publication external_ids isolated by workspace
  AI generation uses only the workspace's own research packets
Layer 4 — AI generation:
  Per-workspace daily token budget
  Workspace A's budget exhaustion does not affect Workspace B
```

---

## 22. OPERATIONAL ARCHITECTURE
### 22.1 Pipeline Metrics

```
Metric                               Type      Labels
────────────────────────────────────────────────────────────────────
draft_generation_latency_seconds     histogram workspace_id
draft_generation_tokens              histogram workspace_id
draft_count_by_format                counter   workspace_id, format
draft_count_by_status                gauge     workspace_id, status
publication_latency_seconds          histogram workspace_id, channel
publication_success_rate             ratio     workspace_id, channel
publication_failure_rate             ratio     workspace_id, channel
scheduler_overdue_entries            gauge     —
```

### 22.2 AI Metrics

```
ai_draft_generation_calls            counter   workspace_id
ai_draft_generation_tokens           counter   workspace_id
ai_draft_regeneration_calls          counter   workspace_id
ai_circuit_breaker_state             gauge     call_type=draft_generator
ai_budget_utilization_phase5         ratio     workspace_id
```

### 22.3 Alert Thresholds

```
Condition                              Alert channel
────────────────────────────────────────────────────────────────────
publication_failure_rate > 0.10        Slack (channel degraded)
scheduler_overdue_entries > 5          PagerDuty
ai_circuit_breaker_state = 1           Slack
ai_budget_utilization > 0.80           Slack (cost warning)
publish_target.last_health_ok = false  Analyst in-app notification
draft_generation_latency P95 > 30s     PagerDuty
```

---

## 23. ACCEPTANCE CRITERIA
Phase 5 is frozen when ALL of the following are satisfied:

### Content Generation
- [ ] `research.packet.ready` triggers draft generation handler
- [ ] `consumed_at` set on packet before generation (idempotent)
- [ ] Draft content sourced exclusively from packet intelligence objects
- [ ] No hallucinated facts (generation prompt constrains to packet content)
- [ ] DraftCitations created for all source intelligence objects
- [ ] Re-generation creates new DraftVersion, does not overwrite
- [ ] AI generation token count recorded in draft_versions.token_count

### Version Control
- [ ] Every edit creates a new DraftVersion row
- [ ] Previous versions never deleted
- [ ] current_version always points to latest
- [ ] Revert to previous version creates new version with old content
- [ ] Version history visible in mobile UI

### Review Workflow
- [ ] Draft cannot be published without `approved` status
  (unless workspace policy = 'loose')
- [ ] Same-account approve blocked on balanced/strict workspaces
- [ ] Change request returns draft to 'draft' status
- [ ] All review actions in draft_reviews table (non-destructive)

### Content Calendar
- [ ] Scheduler polls every 60 seconds
- [ ] Overdue publications processed within 15-minute grace window
- [ ] Overdue beyond 15 minutes → failed + analyst notification
- [ ] calendar_entries UNIQUE constraint (draft_id, target_id)

### Publishing Engine
- [ ] Channel credentials encrypted at rest (AES-256-GCM)
- [ ] Credentials never in logs, events, or GET responses
- [ ] Publishing idempotent by (draft_id, version_number, target_id)
- [ ] Partial multi-target failure does not block other targets
- [ ] PermanentChannelError → immediate dead letter, no retry
- [ ] TransientChannelError → retry with exponential backoff
- [ ] `content.published` emitted on each successful delivery
- [ ] Phase 6 can subscribe to `content.published` from outbox

### Phase Boundary Integrity
- [ ] Phase 5 never writes to intelligence_objects, claims, evidence
- [ ] Phase 5 only writes consumed_at on research_packets (nothing else)
- [ ] Draft content never sourced from intake_items directly
  (must come through intelligence_objects in the packet)
- [ ] No verification engine, epistemic typing, or scoring logic

### Mobile
- [ ] `ff_content_drafts` gates all content module screens
- [ ] `ff_publishing_notion` gates publish targets configuration
- [ ] ContentHomeScreen shows drafts with status pills
- [ ] DraftEditorScreen shows citations above content area
- [ ] DraftEditorScreen shows word count (always visible)
- [ ] CalendarScreen shows channel icon dots per day
- [ ] PublishHistoryScreen shows delivery status per publication

### Shared Contracts
- [ ] All Phase 5 types in `packages/shared-types/src/`
- [ ] Pydantic mirror regenerated; drift check passes
- [ ] MeResponse extended with `content{}` keys

### Quality Gates
- [ ] CI green: lint, type-check, drift-check, tests
- [ ] Unit coverage ≥80%: draft generator, publishing engine,
      channel adapters, version control logic
- [ ] Integration test: packet → draft → review → publish end-to-end
- [ ] Security: credentials never in logs; channel credentials encrypted

---

## 24. RISKS
| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| R1 | AI generates content that contradicts the verified intelligence (hallucination) | HIGH | Prompt architecture constrains generation to packet content only. No hallucination possible within the constraint. Analyst review provides human gate. |
| R2 | Channel credentials stolen from database | HIGH | AES-256-GCM encryption at rest. Credentials never in logs or API responses. Separate ORYX_PUBLISH_KEY not in database. Key rotation procedure documented. |
| R3 | Channel API rate limits exceeded during high-volume publishing | MEDIUM | Per-channel rate limit tracking. Per-workspace concurrency caps. Backoff on 429 responses. Analyst alerted when rate limited. |
| R4 | Draft published twice (duplicate post) | MEDIUM | Idempotency check on (draft_id, version_number, target_id) before calling adapter. Adapter-level idempotency for channels that support it (tweet content hash). |
| R5 | Scheduler drift on Windows/portable Postgres environment | MEDIUM | Same pattern as Phase 3 scheduler (proven). Grace window for overdue publications. Overdue detection on startup. |
| R6 | Research packet consumed but draft generation fails | MEDIUM | consumed_at already set — packet is permanently consumed. Analyst can still create draft manually or retry generation. Packet is not "locked" — it is "claimed." |
| R7 | Claude Sonnet latency causes poor UX for draft generation | MEDIUM | Streaming response support (show content as it generates). Loading state in GenerateDraftScreen. Analyst can cancel and retry. |
| R8 | External channel API changes break adapters | LOW | Channel adapters are isolated. One channel breaking does not affect others. Adapter health checks surface issues before they affect users. |
| R9 | Content calendar overload at peak volume | LOW | Partial index on pending entries makes polling sub-millisecond. Concurrent publication limited by per-workspace caps. |

---

## 25. TRADEOFFS
| Decision | Cheaper Path | Why We Pay the Cost |
|----------|-------------|---------------------|
| Claude Sonnet for generation | Claude Haiku | Phase 5 produces published content. Quality of prose directly affects platform reputation. Haiku is not acceptable for 3000-word articles. The cost difference is justified. |
| Append-only DraftVersion history | Overwrite on edit | Full edit history enables audit trail, revert functionality, and A/B comparison. Deletion would remove the evidence of AI generation vs human editing — valuable for product analytics and trust. |
| Separate content_templates table | Inline format config per draft | Templates are reusable. One workspace may have 10 drafts using the same newsletter template. Templates evolve independently of drafts. Coupling them forces duplicate config. |
| Encrypted credentials in database | Plaintext or external vault | Keeping credentials in the same database as the content simplifies the architecture. AES-256-GCM encryption provides adequate security for channel credentials at Phase 5 scale. External vault is Phase 10+ architecture. |
| Per-draft citation tracking | No provenance | Every published piece needs a provenance chain back to verified intelligence. Without citations, ORYX cannot answer "what was this article based on?" — a core trust proposition of the platform. |
| Draft status machine with 8 states | Simple published/unpublished | Rich status enables the review workflow, scheduling, rejection, and archiving. Collapsing to two states would force application logic into code rather than data, making the system harder to audit. |
| Manual review required (balanced policy) | Auto-approve | The core value proposition of ORYX is trust. Auto-approving content without human review defeats the purpose of the verification layer. The review step is the final human gate before the platform publishes. |
| Channel-adapter isolation | Monolithic publish function | Channels evolve at different rates (Twitter changes its API, Notion adds new block types). Isolation means adding Threads or Substack in Phase 6 does not touch existing channels. |
| Phase 6 owns notifications | Phase 5 sends notifications | Clean boundary. Content creation is Phase 5's domain. Notifying followers of new content is Phase 6's domain. Mixing them couples content creation to notification delivery. |

---

## 26. ARCHITECTURE FREEZE RECOMMENDATION
Phase 5 architecture is ready to freeze when:
- [ ] All 25 sections reviewed by Principal Architect
- [ ] Phase 4 → Phase 5 boundary confirmed (research.packet.ready contract)
- [ ] Phase 5 → Phase 6 boundary defined (content.published payload)
- [ ] Channel adapter protocol finalized (all 6 channels specified)
- [ ] Credential encryption key management documented
- [ ] Mobile content studio layout confirmed (Bloomberg × Apple contract)
- [ ] No open TBDs in any section
- [ ] ADRs planned: ADR-038 through ADR-046

### ADR Requirements

```
ADR-038  AI Model Selection for Generation  (Sonnet vs Haiku; why quality > speed)
ADR-039  Draft Version Control Model        (append-only; no overwrite)
ADR-040  Channel Adapter Protocol           (isolation contract)
ADR-041  Credential Encryption Strategy     (AES-256-GCM; key management)
ADR-042  Review Policy by Workspace         (strict/balanced/loose)
ADR-043  Packet Consumption Semantics       (consumed_at; what it means)
ADR-044  Publishing Idempotency             (by draft_id+version+target)
ADR-045  Content Calendar Scheduler         (60s poll; 15min grace)
ADR-046  Phase 5 → Phase 6 Boundary        (content.published event contract)
```

---

## 27. IMPLEMENTATION ROADMAP
### Current State at Phase 5 Start

```
ff_content_drafts     exists in DB, default OFF
ff_publishing_notion  exists in DB, default OFF
research.packet.ready event firing from Phase 4
consumed_at on research_packets: NULL, waiting for Phase 5
Content tab in RootTabNavigator: exists, gated OFF
```

### Total Scope

```
New migrations:      5 (0009 through 0013)
New service folders: 6 (drafts, templates, review, calendar, publishing, targets)
New DB tables:       8
New indexes:         12
New events:          7
New mobile screens:  8
New TS type files:   6 (drafts, templates, review, publishing, calendar, events/phase5)
ADRs to write:       9 (ADR-038 through ADR-046)
```

---

## 28. WAVE BREAKDOWN (A–F)

---

### WAVE A — Draft Foundation and AI Generation
**Status: PENDING**
**Goal:** Establish the core draft entity with AI generation from research packets. An analyst can create a draft from any ready packet and get polished AI-generated content.

**Scope:**
- Migration 0009: content_drafts + draft_versions + draft_citations
- PacketConsumerHandler subscribed to research.packet.ready
  (sets consumed_at, then triggers generation)
- DraftGeneratorAI (Claude Sonnet, versioned, budget-gated)
- DRAFT_CREATED and DRAFT_UPDATED events
- POST /v1/drafts/generate endpoint
- POST /v1/drafts/{id}/regenerate endpoint
- GET /v1/drafts and GET /v1/drafts/{id} (with current version content)
- GET /v1/drafts/{id}/versions (version history)
- PUT /v1/drafts/{id}/version (save new version on edit)
- ContentHomeScreen (draft list with status pills)
- GenerateDraftScreen (select packet + format)
- DraftEditorScreen (editor + version history + citations)
- drafts.ts shared types

**Dependencies:** Phase 4 frozen. research.packet.ready firing. intelligence_objects table exists.
**Acceptance Criteria:** Generation produces content. consumed_at set idempotently. Citations created. Version history preserved. 3 consecutive test runs stable.

---

### WAVE B — Content Templates and Format Management
**Status: PENDING**
**Goal:** Introduce reusable format templates. Different workspaces can define their own templates for different content styles and channels.

**Scope:**
- Migration 0010: content_templates
- Template CRUD service and router
- Default template seeding per workspace (one per format)
- Template selection in GenerateDraftScreen
- Content format switching (regenerates with new format's template)
- Templates visible in content_templates endpoint
- templates.ts shared types

**Dependencies:** Wave A complete. content_drafts exists.
**Acceptance Criteria:** Default templates seeded on workspace creation. Template selection changes generation prompt. Format switching works.

---

### WAVE C — Review Workflow and Approval
**Status: PENDING**
**Goal:** Implement the review workflow. Drafts move through approval before they can be published. Review policy enforced by workspace preference.

**Scope:**
- Migration 0011: draft_reviews
- Review service: submit, approve, reject, request_changes
- POST /v1/drafts/{id}/submit-review
- POST /v1/drafts/{id}/approve (with review policy enforcement)
- POST /v1/drafts/{id}/reject
- POST /v1/drafts/{id}/request-changes
- ReviewQueueScreen (pending reviews list)
- DraftStatusPill applied across all draft screens
- DRAFT_APPROVED and DRAFT_REJECTED events
- MeResponse content{} counts
- review.ts shared types

**Dependencies:** Wave B complete. Draft lifecycle states established.
**Acceptance Criteria:** Review policy enforced at API layer (not just UI). Same-account approve blocked on balanced/strict. change_request → draft → resubmit flow works.

---

### WAVE D — Publish Targets and Channel Configuration
**Status: PENDING**
**Goal:** Analysts configure their publishing channels. Credentials are encrypted at rest. Health checks validate channel connectivity.

**Scope:**
- Migration 0012: publish_targets + publications
- PublishTarget CRUD (credentials encrypted on save, never returned in GET)
- Channel adapter implementations (all 6: Twitter, LinkedIn, Newsletter, Notion, Webhook, Export)
- Credential encryption/decryption service
- POST /v1/targets (create with credential validation)
- GET /v1/targets (list, no credentials returned)
- DELETE /v1/targets/{id}
- POST /v1/targets/{id}/health-check
- POST /v1/drafts/{id}/publish (manual immediate publish)
- GET /v1/publications (history)
- PublishHistoryScreen
- PublishTargetScreen (Settings → Publish Targets)
- CONTENT_PUBLISHED and CONTENT_PUBLISH_FAILED events
- publishing.ts shared types
- ORYX_PUBLISH_KEY added to Settings

**Dependencies:** Wave C complete. Approved drafts exist.
**Acceptance Criteria:** Credentials encrypted at rest (test-asserted). Credentials never in logs or GET responses. Publishing idempotent (double-publish produces one post). Partial multi-target failure handled correctly.

---

### WAVE E — Content Calendar and Scheduling
**Status: PENDING**
**Goal:** Analysts schedule content for future publication. The calendar shows what is scheduled, what has published, and what has failed.

**Scope:**
- Migration 0013: calendar_entries
- Calendar scheduler (60-second poll, 15-minute grace window)
- POST /v1/calendar (schedule a draft for a target at a time)
- GET /v1/calendar (range query: start_date to end_date)
- DELETE /v1/calendar/{id} (cancel scheduled entry)
- CalendarScreen (month grid with channel icon dots)
- DRAFT_SCHEDULED event
- calendar.ts shared types
- Overdue detection on scheduler startup
- Integration test: schedule → scheduler fires → publication delivered

**Dependencies:** Wave D complete. publish_targets and publishing engine exist.
**Acceptance Criteria:** Scheduler publishes within 15 minutes of scheduled_at. Overdue entries recovered on restart. Calendar view accurate. Unique constraint (draft_id, target_id) enforced.

---

### WAVE F — Hardening, ADRs, Full Pipeline Test, Freeze
**Status: PENDING**
**Goal:** Complete the full pipeline integration test, write all ADRs, harden failure paths, achieve coverage targets, and freeze Phase 5.

**Scope:**
- Full pipeline integration test: research.packet.ready → content.published
- ADRs 038–046 written in docs/adr/
- Retry/dead-letter tests for publishing failures
- Credential encryption unit tests (encrypt → decrypt roundtrip)
- Channel adapter mock tests (all 6 channels)
- Coverage ≥80% on: draft generator, publishing engine, each channel adapter
- Security scan: no credentials in logs
- check.sh fully green
- MeResponse content{} counts verified end-to-end
- Phase 5 freeze commit + tag: phase5-freeze

**Dependencies:** Wave E complete. All tables, services, and screens exist.
**Acceptance Criteria:** Full pipeline test passes end-to-end. All 9 ADRs written. Coverage ≥80%. check.sh green. Freeze tag applied.

---

*ORYX Phase 5 Architecture — Rev 1*
*Principal Architect | 2026-06-16*
*Phase 4 frozen at: 73bd2d4 (phase4-freeze)*
*Brand migrated at: c8537de*
*Architecture freeze APPROVED: 2026-06-16. Implementation may begin — Wave A first.*
*The `phase5-freeze` tag is reserved for the end of Wave F (implementation complete).*
*Deviations require an explicit Rev 2.*
