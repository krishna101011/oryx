# ADR-034: Phase 4 Retention and Partitioning Policy

**Status:** Accepted
**Date:** 2026-06-15
**Phase:** 4

## Context

Phase 4 produces append-mostly data — claims, evidence, verification runs,
analyst reviews, audit log, packets — that grows without bound. The platform
operates in a financial-intelligence context with compliance obligations, and
the audit chain must remain intact and reconstructable. We must define how long
each class of data lives and how the largest tables stay queryable at scale,
without actually building partitioning in Phase 4.

## Decision

Retention by data class:

| Data | Retention |
|---|---|
| `claims`, `evidence`, `claim_evidence_links` | **Indefinite** (audit chain) |
| `verification_runs` | **Indefinite** (versioned, append-only; ADR-032) |
| `analyst_reviews` | **Indefinite** (analyst accountability; ADR-033) |
| `verification_audit_log` | **7 years** (financial compliance) |
| `research_packets` (consumed) | **2 years minimum**, then archive |
| `source_credibility_records` | lifetime of the source (evolving state) |

**Partitioning (documented here, NOT implemented in Phase 4):** the large
append-only tables — `claims`, `verification_runs`, `verification_audit_log` —
are to be **range-partitioned monthly once they exceed ~10M rows**. Old
partitions are **detached, not dropped**: a detached partition can be moved to
cold storage and re-attached for an audit, so the chain is never broken.
Retention windows are enforced by detaching partitions past the window, never
by row-level `DELETE`.

Phase 4 ships none of this machinery. It commits to the policy so that the
schema (monotonic `created_at`, no in-place destructive updates on these
tables) stays partition-ready, and so the operator runbook has a written target.

## Consequences

- **Positive:** the audit chain is intact by construction — nothing destructive
  happens to claims/runs/reviews/audit rows, so any historical decision is
  reconstructable. Partition-by-detach keeps even "expired" data recoverable.
- **Positive:** the schema decisions made in Waves A–E (append-only runs,
  separate audit log, `created_at` on every large table) are already compatible
  with monthly range partitioning; no migration debt is incurred.
- **Negative:** indefinite retention on claims/evidence/runs grows storage
  unbounded until partitioning lands; this is an accepted Phase-4 cost. The
  policy is a commitment, not an enforced control, until the partitioning work
  (Wave F+/Phase 6) is built.

## Alternatives Considered

- **Hard-delete old rows past the retention window.** Rejected: breaks the audit
  chain and violates the financial-compliance requirement to reconstruct past
  decisions; detach-not-delete preserves recoverability.
- **Partition everything now in Phase 4.** Rejected: premature — tables are far
  below 10M rows, partitioning adds query-planner and migration complexity, and
  the constraint explicitly defers implementation. Documenting the target keeps
  the schema ready without the cost.
- **Single flat tables forever.** Rejected: `claims`, `runs`, and `audit_log`
  will outgrow single-table performance; committing to a partition plan now
  avoids a painful retrofit later.
