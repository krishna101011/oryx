# ADR-035 — AI Cost Control

**Status:** Accepted — budget + circuit breaker implemented in Waves A–B
**Date:** 2026-06-13
**Phase introduced:** 4
**Related:** ADR-014 (event architecture), ADR-018 (outbox / drainer retry)

---

## 1. Context

Phase 4 calls the Anthropic API at three pipeline sites — extraction,
epistemic typing, evidence linking — with conflict detection adding a fourth
in Wave D. Each is driven by the event drainer, which retries failed
deliveries up to 20 times. Two cost-and-stability hazards follow directly:

- **Unbounded spend.** A pathological intake burst, a retry storm, or a
  prompt that triggers long outputs can run AI cost away with no ceiling —
  and one workspace's runaway must not bankrupt the platform or starve
  others.
- **Cascade failure during a provider outage.** If Anthropic is down, every
  claim's call fails, retries 20× with backoff, and the queue fills with
  doomed work — burning latency and budget on calls that cannot succeed.

The model is also a frozen choice: `claude-haiku-4-5-20251001`, temperature 0,
for determinism and cost.

## 2. Decision

Two independent, composable mechanisms.

**(1) Per-workspace daily token budget** — `workspace_ai_budget`, PK
`(workspace_id, budget_date)`, default `budget_limit = 100_000`, overridable
per workspace via `feature_flag_overrides`. Checked **before** every AI call;
spend (`input + output` tokens) recorded **after** every call via an
`ON CONFLICT DO UPDATE` upsert — including when the response is unusable
(parse failure), because the tokens were really spent. On exhaustion:

- Extraction **defers** (transient raise → drainer backoff; the daily row
  resets at UTC midnight and deferred work drains automatically).
- Classification and evidence linking **flag the claim**
  (`requires_analyst_review = true`) and proceed degraded (claim stays
  unclassified / object proceeds with zero evidence) — there is no row to
  defer at those stages.

**(2) Shared in-process circuit breaker** (`core/ai_circuit_breaker.py`),
one state machine per `call_type` (`extractor`, `classifier`,
`evidence_linker`, …): **5 consecutive failures → 60s open window** (calls
fail fast with `CircuitOpenError`, no API hit) → **half-open**: the next real
call is the probe; success closes and resets, failure re-opens for another
60s. `CircuitOpenError` is a `ProviderError` subtype and flags affected
claims for analyst review. State is **in-process only** — a restart cold-
starts every circuit closed, which is the correct optimistic default. Call
types are isolated: an extractor outage does not trip the classifier.

**Secret handling.** `ANTHROPIC_API_KEY` lives in Settings (env var), is
never logged, and never appears in error messages. No claim text or body
text is ever logged — IDs and token counts only.

## 3. Consequences

### Positive
- AI cost blast radius is confined to one workspace per day; budget
  exhaustion in Workspace A cannot affect Workspace B.
- A provider outage degrades gracefully: the breaker stops doomed calls in
  ~5 failures and self-heals via probe, instead of 20× retry storms per item.
- Cost and breaker state are observable per workspace and per call_type.

### Negative
- Budget exhaustion delays processing until UTC midnight. Accepted — the
  alternative is unbounded cost; deferred work is not lost.
- Circuit state is lost on restart. Accepted deliberately: persisting it adds
  complexity for no benefit; a clean cold start is the right behavior.
- A wedged downstream during the half-open probe spends one real call to
  learn the circuit is still open. Accepted: a synthetic canary would spend
  unbudgeted tokens to learn nothing a real call doesn't.

## 4. Alternatives Considered

| Alternative | Why rejected |
|---|---|
| No budget control | Unbounded cost; a single workspace's burst is a platform-wide bill. |
| Global (not per-workspace) budget | One noisy workspace starves every other; no tenant isolation. |
| Persisted circuit-breaker state | Complexity and a new failure mode for no gain; restart-clean is correct. |
| Synthetic canary probe on half-open | Spends unbudgeted tokens to learn what the next real call reveals for free. |
| Rely on drainer retries alone for outages | 20× backoff per item floods the queue with doomed work and burns budget on impossible calls. |
