<!-- ORYX — PR template. Defended phase boundaries are non-negotiable. -->

## What

<!-- One-sentence description. -->

## Phase

<!-- Pick one. Reviewers will reject PRs that cross phase lines. -->
- [ ] Phase 1 — Foundation
- [ ] Phase 2 — Identity & Control Plane
- [ ] Phase 3 — Intake
- [ ] Phase 4 — Verify + Analyze + Research
- [ ] Phase 5 — Create + Publish
- [ ] Phase 6 — Automation + Alerts
- [ ] Phase 7 — Analytics
- [ ] Phase 8 — Training
- [ ] Cross-cutting (docs, infra, CI)

## Checklist

- [ ] Stays within the declared phase scope
- [ ] No inline hex colors or magic spacing values
- [ ] If contracts changed: shared-types updated, pydantic mirror regenerated, drift check passes
- [ ] If a new event/handler: idempotency considered
- [ ] If a write endpoint: capability declared via `require()`
