# ADR-038 — AI Model Selection for Draft Generation

**Status:** Accepted — implemented in Phase 5 Wave A (AIProvider added Wave B)
**Date:** 2026-06-27
**Phase introduced:** 5
**Related:** ADR-035 (AI cost control), ADR-036 (epistemic type system), ADR-032 (verification engine versioning)

---

## 1. Context

Phase 4 chose Claude Haiku for claim extraction and epistemic typing: those are
high-volume, structured, low-creativity tasks where Haiku's speed and price win
and the output is a constrained schema, not prose.

Phase 5 is different. Its product *is* the prose — a draft that an analyst reads,
edits, and publishes under the workspace's name. A cheaper model that produces
flatter, less coherent copy directly degrades the thing the user is paying for.
The question is which model the generation step uses, and how tightly the choice
is coupled to one vendor.

## 2. Decision

**Generation runs on Claude Sonnet — `claude-sonnet-4-6`** — not Haiku. The model
id is the single constant `ANTHROPIC_MODEL_SONNET` in
`services/drafts/generator.py`; `DraftGeneratorAI.model` exposes it and the
persisted `content_drafts.generation_model` records it per draft.

Verified generation parameters (read from the real code, not assumed):

- **Temperature `0.4`** (`GENERATION_TEMPERATURE`). Deliberately low-ish: enough
  warmth for readable prose, but anchored so the model does not drift from the
  source intelligence. This is *not* the 0.7 a generic "creative writing" default
  would use — the source-only constraint (below) matters more than flourish.
- **Max tokens `4096`** (`GENERATION_MAX_TOKENS`).
- The generation prompt is a four-layer shape; Layer 1 (system context) carries
  the non-negotiable constraint that the model writes **only** from the provided
  intelligence objects (`SOURCE_ONLY_MARKER`, asserted by a unit test). This is
  what separates ORYX content from generic AI writing.

**Self-contained client.** Phase 5 keeps its own generation call rather than
importing Phase 4's Haiku helper, so the content layer has no import dependency
on the claims pipeline. Vendor errors map onto the shared `ProviderError`
taxonomy and the call runs behind the shared AI circuit breaker (call type
`draft_generator`), so cost control (ADR-035) and retry policy apply unchanged.

**Provider abstraction (added Wave B).** Generation routes through the
`AIProvider` protocol (`core/ai_provider.py`): `AnthropicProvider` is the default;
`OllamaProvider` is a free local-dev alternative selected by `AI_PROVIDER=ollama`.
No prompt content, temperature, or max_tokens differ between providers. The Ollama
path is **explicitly documented as lower reliability for nuanced tasks** and is a
dev smoke-test path only — never a production substitute.

## 3. Consequences

### Positive
- The published artifact gets the model tier that matches its value; quality is
  a product decision, recorded per-draft for auditability.
- The circuit breaker + ProviderError reuse means generation inherits Phase 4's
  cost and resilience machinery without new infrastructure.
- The provider seam lets a developer run the whole pipeline with zero API spend
  locally, without the production path ever depending on it.

### Negative
- Sonnet costs materially more per draft than Haiku. Accepted: generation is
  analyst-triggered and one-draft-per-packet, so volume is bounded, and ADR-035's
  budget gate caps spend.
- A second provider implementation is a maintenance surface. Mitigated by the
  narrow `complete()` protocol — providers share everything above the call.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Reuse Phase 4's Haiku helper | Couples content to the claims pipeline and ships flatter prose for the one task where prose quality is the product. |
| Temperature 0.7+ "creative" default | Loosens the source anchor; raises the risk of invented facts, which is the cardinal sin for verified-intelligence content. |
| Anthropic-only, no provider seam | Forces API spend for every local run and every CI smoke test; the thin protocol makes the alternative cheap to keep. |
| Make Ollama a supported production backend | Small local models misclassify and under-write nuanced financial prose; supporting it in prod would silently degrade the product. |
