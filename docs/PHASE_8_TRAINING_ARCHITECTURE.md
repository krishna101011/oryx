# ORYX — Phase 8 Training Architecture (Academy)

**Scope:** Phase 8 — `training` in Phase 1's module table; the shipped nav
displays it as **Academy** (`webNav.ts`'s `LEARN` group, currently
`pending: true`) — confirmed by recon to be the same feature under two
names, not two separate concepts.
**Status:** DRAFT — Rev 1. Real decisions below; not yet built, not yet
recon-verified against current code.
**Depends on:** Phase 2 (the `require_capability` pattern — reused for
authoring, not a new permissions scheme), the `ff_training` feature flag
(already seeded, default OFF)
**Blocked on (greenfield, confirmed absent):** the entire Course/Module/
Lesson/Enrollment/Certificate schema, any video hosting integration, any
authoring flow, any quiz/assessment model

---

## Revision Note

Rev 1. No prior revision exists. A separate recon pass found no real Phase
8 architecture anywhere in this codebase — only a one-word label repeated
across five other phases' frozen docs, a Phase-1-era ping-stub
router/placeholder screen, and one detailed but never-cited design mockup
(`docs/design-reference/screens/academy.jsx`). This document is the first
real scoping pass, not a correction of one.

## 1. What This Is

The "Training" module (Phase 1's module table), display name "Academy" in
the shipped nav — same feature, two names, confirmed by recon. The only
substantive prior material is `docs/design-reference/screens/academy.jsx`
— never cited in any architecture doc, but real and detailed: course cards
(code, title, level, duration, module count, progress %, certification
badge), a lesson viewer (numbered lesson list, video player,
transcript/reading-list, next-lesson nav), and account-level KPIs (courses
enrolled, lessons completed, certifications earned).

## 2. Content Model

`Course` (id, workspace-independent — content is platform-wide, not
per-workspace), `Module`, `Lesson` (belongs to a Module; fields: title,
video_asset_id, transcript_text, order), `Enrollment` (account_id,
course_id, enrolled_at), `LessonProgress` (account_id, lesson_id,
completed_at), `Certificate` (account_id, course_id, issued_at — issued
when every lesson in a course has a completion row).

## 3. Video Hosting: Cloudflare Stream

Real decision, not a placeholder: **Cloudflare Stream**, chosen over
raw self-built infrastructure (real research confirms this is expensive,
complex, and lower-quality at this scale) and over Mux (real pricing
research confirms 5-8x higher cost, justified by live-streaming/analytics
features not needed here). Bundled encoding + adaptive HLS delivery, no
separate transcoding pipeline to build or maintain. Lesson videos store a
Cloudflare Stream asset ID, not a raw file path.

## 4. Authoring

Per the confirmed decision that real content will be authored directly
(not pre-seeded), course/module/lesson creation needs a real,
workspace-capability-gated authoring flow — reusing the existing
`require_capability` pattern, not a new permissions scheme. Exact
capability scoping (a new `content.author`-style capability vs. reusing an
existing one) is a recon question for the next pass, not decided here.

## 5. Explicitly Out of Scope for Rev 1

Quizzes/assessments (not shown in the reference mockup — flagged as a real
future decision, not assumed). Multi-instructor/multi-author attribution.
Course pricing/paywalling beyond the existing subscription tiers (per the
pricing doc, Vision unlocks full Academy access — Rev 1 assumes
tier-gating only, no per-course purchase). Live cohorts or scheduled
sessions.
