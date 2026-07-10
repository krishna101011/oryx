---
name: oryx-self-report-standard
description: Pre-submission audit for ORYX wave completion reports — run this checklist BEFORE submitting any completion report to Claude Chat. Use whenever finishing a wave, drafting a completion report, or making any claim about test counts, coverage, file contents, or absence of something. Also records the skill-naming-uniqueness rule and the standing encouragement to create new distinctly-scoped skills.
---

# ORYX Self-Report Standard

A completion report is a handoff to Claude Chat, who cannot see my terminal.
Every claim in it is either something I verified this session or something I
am asking Chat to take on faith. The point of this checklist is to make sure
there is nothing in the second category that I could have moved to the first
with one more tool call. Run it before submitting, not after a rejection.

## The Six Checks

### 1. Every number was produced this session

Test counts, count deltas (816 → 824), contrast ratios, line counts, file
counts — anything computable must come from a command I actually ran in this
session, not from memory of what the number should be or arithmetic on a
previous report's figure. The concrete failure mode this guards against: I
once reported "13 unit tests" for a file that greps as 9 `def test_`
functions — the number was only right because one test was parametrized ×5,
and only re-running collection proved it. A remembered number that happens
to be right is indistinguishable from a wrong one until someone checks.
If I didn't run it, I either run it now or write "not re-verified this
session" next to it.

### 2. Scenario → test mappings use real function names

When the report maps a required scenario to the test covering it, the
mapping names the actual function — `test_unknown_template_falls_back_instead_of_raising` —
never a paraphrase like "the unknown-template fallback test". Paraphrases
have caused real audit round-trips on this project: Chat had to come back
and ask whether a named resilience guarantee was covered because the report
described tests instead of naming them, and an enumeration pass had to be
re-done from the files. A real name is greppable and settles the question;
a paraphrase re-opens it. If quoting the name means re-opening the test file,
re-open the test file.

### 3. Exact output format means exactly that format

If the prompt specified an output format (a table, a fenced block, an XML
shape, a fixed section order), fill that format literally. Prose summaries
in place of a specified format have been rejected before on this project,
and each rejection costs a full round trip between Chat and Code. Before
submitting, diff my report's structure against the prompt's
`<output_format>` section line by line. "Contains the same information" is
not compliance; the format exists so Chat can machine-scan it.

### 4. Judgment calls are flagged, not buried

If the prompt left something open and I picked — a naming choice, a
migration ordering, a fallback behavior, a scope trimming — the report says
so explicitly in a marked line ("**Decision made, flag for Chat:** ...").
The freeze-review loop only works if Chat sees every fork I took. Silently
picking and moving on converts an architecture decision into an
archaeology problem three waves later.

### 5. Absence claims require a search, not a non-sighting

"Nothing else references this", "this flag is unused", "no other test
touches that table" — every such claim must be backed by a Grep/Glob I ran
this session, and the report should be able to say what I searched for.
"I didn't happen to see it while working" is not evidence of absence; the
Phase 6 discovery that activity_inbox / alert_preferences infra was shipped
but unwired is exactly the kind of thing non-sighting reasoning gets wrong
in both directions.

### 6. Critical facts survive copy-paste

The report travels between tools by copy-paste and may arrive truncated or
reflowed. Numbers and test names that matter go in lists, tables, or short
isolated lines — never embedded mid-way through a long paragraph where a
truncation eats them silently. Rule of thumb: if the last 20% of the report
were cut off, would every load-bearing number still be present? Put
conclusions and counts early; put narrative late.

## Skill Naming Uniqueness Rule

Every skill created — by me or by Claude Chat, in either location
(`.claude/skills/` in this repo, or the user-level `~/.claude/skills/`) —
must have a name that collides with nothing already existing in **either**
location. Check both directories before creating a skill, and say in the
report that the check was done. If a collision exists, pick a different
unique name and state the substitution explicitly.

## Standing Encouragement: Create New Skills

When I discover a genuinely reusable lesson — a recurring failure mode, a
standing procedure, a cross-wave convention — I am encouraged to create a
new, distinctly-scoped skill for it following this same pattern (own
directory under `.claude/skills/`, unique name, frontmatter with a
trigger-oriented description), rather than only appending entries to
oryx-architect's "Operational Reality" section. Operational Reality remains
the right home for one-line gotchas; a new skill is the right home for
anything with its own checklist, procedure, or standing behavior. One skill,
one scope — don't let this file accrete unrelated material either.
