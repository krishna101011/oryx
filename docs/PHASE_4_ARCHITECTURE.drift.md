# Phase 4 Architecture — Drift Companion

`docs/PHASE_4_ARCHITECTURE.md` is a binary PDF (Rev 3, dated 2026-06-12,
authored before the `anant` → `oryx` rename). Because it is a PDF rather than
Markdown, drift notes cannot be appended to its body without rewriting or
corrupting it. This sidecar file records that drift instead. The PDF body is
left unchanged.

## Known Drift (noted 2026-06-23)

Cross-checked the PDF against the actual Phase 4 code in
`apps/backend/src/oryx/services/{claims,evidence,verification,conflicts,review,intelligence,research}/`
and the Alembic migrations. The following describe-vs-built discrepancies were found:

1. **Stale `anant/` module path (pre-rename).** §6.1 (Folder Structure) heads the
   tree with `apps/backend/src/anant/services/`, and §12.1 (Source of Truth) cites
   the Pydantic mirror at `apps/backend/src/anant/shared/types.py`. The shipped
   paths are `apps/backend/src/oryx/services/` and
   `apps/backend/src/oryx/shared/types.py`. No `anant` references remain anywhere
   in the code — only in this document.

2. **Migration sequence is wrong (§7.1, and the §26 roadmap count).** The doc lists
   Phase 4 as six migrations `0004`–`0009`, with the research tables in a separate
   `0009_phase4_wave_f.py`. In reality Phase 4 is **five** migrations, `0004`–`0008`;
   there is no `0009_phase4_wave_f.py`. `intelligence_objects` **and** all three
   research tables (`research_workspaces`, `research_workspace_items`,
   `research_packets`) are created together in `0008_phase4_wave_e.py`. `0009` is
   the first Phase 5 migration (`0009_phase5_wave_a.py`).
   - Sub-point: the doc's Phase 3 baseline filenames `0002_phase3_intake.py` /
     `0003_phase3_additions.py` are actually `0002_phase3_baseline.py` /
     `0003_phase3_wave_f.py`.

3. **Event-bus wiring drift (§8.3 `build_bus()`).** The shipped
   `services/queue/drainer.py:build_bus()` differs from the doc's sketch:
   - The bus is constructed as `InProcessBus()` and handlers attach via
     `bus.subscribe(...)`, not `EventBus()` / `bus.register(...)`.
   - Conflict-lifecycle handling is a single `ObjectConflictProjector` subscribed
     to **both** `CONFLICT_DETECTED` and `CONFLICT_RESOLVED` — not the doc's
     `ObjectUpdateHandler` registered on `CONFLICT_RESOLVED` only.
   - There is no `OBJECT_REVIEWED → PacketUpdateHandler` registration in
     `build_bus()`.

### Confirmed accurate (no drift)

All 13 Phase 4 table names, all 11 event-name constants
(`verification.*`, `intelligence.*`, `research.packet.ready`), the seven-service
folder layout and their internal files, and the `build_bus()` location itself all
match the shipped code.
