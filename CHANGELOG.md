# Changelog

Newest first. One entry per session, twelve lines at most, enforced by
`tools/check_docs.py`. When this file passes 400 lines the older half rolls into
`docs/history/changelog-YYYY-MM.md`.

## 2026-09-12 — T1c: the bench loads all 57 templates, and a library can ask for ions

`ui.examples.full_library()` is `load_templates(tier="family")` — 57, was a module
sweep gathering **50, and not a subset**: a package re-export shadowed
`electrochemistry` (4 electrode templates), `properties/electrolyte` was never swept
(6 dissociations), and 3 acid-gated duplicates ran esterification twice. The blocker:
`inventory.needs_electrolyte` read the CHARGE only and the bench's default items carry
no ion, so the whole table refused at build time on `water_autoionization`. It reads
the library too now, through `ReactionTemplate.touches_ions` — net charge per SLOT,
since a per-ATOM sum calls 15 neutral templates ionic (`[N+](=O)[O-]`, `[C-]#[O+]`).
Measured: the default bench goes 26 species/19 reactions to 35/24, and sulfur + air +
water + NO2 exhausts at 5 generations where it exhausted at 3 (H2SO4 -> bisulfate ->
sulfate, NH3 -> ammonium). Tests 1276 -> 1278, `check.ps1 -Full` green, `src/chemsim`
glyphs 1043 -> 1042. Next: T4, reachable reactions, on the whole table.

## 2026-09-08 — T1 switch-over: the engine builds its templates from the table

The 57 constructors in `reactions/` and `properties/electrolyte.py` are wrappers
over `load_templates()`: they keep their keyword arguments and hold no data, and
`library._catalysed_row`/`_surface_row` undo whichever catalyst a row carries and
apply the caller's, in one place. Every template-producing callable was snapshotted
over a keyword grid before and after: **577 variants across 69 callables,
byte-identical**. `TEMPLATE_CLASSES` is 14 integrator-TERM entries, the other 46
derived from the `class` column, correcting 12 report cells that named constructors
rather than templates. The row-vs-constructor check became a tautology and is now
`CONSTRUCTION_SITES`: the `ReactionTemplate(` sites under `src/chemsim` are exactly
the 5 loaders. One row is enough — +1 row gave 58 templates and 47 classes with no
Python edited. Tests 1276, `check.ps1 -Full` green plus 356 more (one unreproduced
`test_ui` flake). Filed not fixed: T1d, `named_routes.py` dies on route 2 at `cf636da` too; T1c, `full_library()` gathers 50 of 57.

## 2026-09-08 — T1 first half: 57 templates are 57 rows, checked against the code

`data/templates/templates.psv` holds every template in 17 columns — the thirteen
`ReactionTemplate` fields plus `tier`, `class`, `source`, `notes` — and
`tools/build_templates.py` emits `src/chemsim/reactions/template_data.py`
(`load_templates`, `template_classes`, `tier_counts`). Two checks, both run by
`check.ps1`: the column set is read off the dataclass, so a field with no column
fails the build (P4's lesson, which cost three milestones); and every row is
compared field for field against the constructor it copies, found by an `ast`
walk — dropping `hammett_rho` from one row fails it, measured. The `class` column
carries 46 of `TEMPLATE_CLASSES`' 59 keys, the other 13 being integrator TERMS
with no SMARTS. `template_counts()` gained `_NOT_A_TEMPLATE_SOURCE` so the loader
is not a 58th template; it goes when the constructors do, which is the
switch-over and the second half. Tests 1264 -> 1275, `./check.ps1 -Full` green.

## 2026-09-07 — an unattended loop runs /session on repeat in fresh contexts

`tools/loop/run-loop.ps1` starts a new `claude -p "/session"` process per
iteration, so each begins with an empty context and reads its state back out of
the repo; `/session` and `/handoff` were already that handshake, so the runner
adds no coordination of its own. It stops on `tools/loop/STOP` (written by a
session that met the goal, or by the operator as a brake), a session cap, a
wall-clock deadline, a non-zero exit, two iterations in a row that leave HEAD
unmoved, or a tree left dirty or HEAD not level with `origin/main`.
`tools/loop/PROTOCOL.md` is what those sessions read: context does not survive,
nobody is there to ask, the ask-first commands do not run, still one task.
`GOAL.md`'s `## Goal` section is passed in and outranks NEXT.md's ordering.
Transcripts and STOP are gitignored. `./check.ps1` green, 39 passed. No
chemistry moved; task 1 is still T1.

## 2026-09-02 — T0.5: the report counts its own templates (47 -> 57) and both generators ratchet

`validation/catalog_coverage.py` had five hand-maintained `N_*_TEMPLATES`
constants summing to 47 against 57 in the tree; `template_counts()` now walks
`reactions/*.py` and `properties/electrolyte.py` with `ast` and counts
`ReactionTemplate(` construction sites, so the report reads 57 (38 synthesis,
9 library, 6 electrolyte, 4 electrochemistry) and moves on its own. Its
`PLAYABLE.md` cross-quote said 36 runnable / 12 playable / 21 fed-but-unrunnable
against 44 / 21 / 22; it is now parsed from that file's footer, which gained the
fed-but-unrunnable count and is a declared contract. New `catalog.emit()` gives
both generators `--check`; `check.ps1 -Full` runs playable first, coverage
second, and both are green. `COVERAGE_REPORT.md` was stale on 207 unrelated
lines (`OutsideEstimatorDomain`) and is regenerated. No engine change, no other
number moved. Next: T1 (templates become data).

## 2026-09-02 — T1.0: 174 of 377 rows are extractable and uncovered; T1 and T2 survive

Added `validation/extraction_yield.py` (~40 s), which cross-tabulates every
catalog step by resolves-to-SMILES, balances under the LP, and class-uncovered:
174 / 118 / 69 / 6 / 10 / 0 over the six reachable cells; its 75 unbalanceable
and 10 unresolvable rows match `corpus_balance.py`. The 174 span 132 classes,
102 of them single-row; only 6 classes hold three or more rows, so T3 is bounded.
Upper bound if all became templates: template-ready 46 -> 110, intersection
38 -> 66, with 36 of the 64 gained routes held by an unpriceable species.
`corpus_balance.coefficients()` now returns `linprog`'s vector; it is fractional
where the nullspace is 2-D, so T2 needs an integer step. Argument in
`docs/design/extraction-yield.md`; `BACKLOG.md` T1.0 deleted, T2 and T3
rewritten. `./check.ps1` green, 1,264 tests collected, no other number moved.
Next: T0.5 (the two generators disagree), then T1 (templates as data).

## 2026-09-02 — /session runs one task end to end and pushes main

Added `.claude/skills/session/`: take task 1 from `NEXT.md` (or the user's
steering), do it to its done-when, close out through `handoff`, push, confirm.
One task per invocation; the full suite and the tolerance audit stay ask-first,
so a task that needs them is skipped for the next one and the skip reported.
`handoff` Step 8 is now commit and push (fast-forward, never force); its
description no longer says "never push". `CLAUDE.md` session shape points at
the skill. No code, no numbers moved; `./check.ps1` and `check_docs` green.
Next: `/session` in a fresh context, which should take T1.0.

## 2026-09-02 — the handoff is frozen, capped and made repeatable

Moved the seven root monoliths (1.5 MB, 84% narrative) into `docs/history/`,
rewrote the 53 references, and split the milestones file on its own headings into
79 sections (largest 23 KB) behind an index, verified line by line. Added
`CLAUDE.md`, `NEXT.md`, `BACKLOG.md`, this file, `check.ps1`, and
`tools/check_docs.py`, which caps the working set and ratchets existing debt in
both directions. `README.md` 662 -> 561: the Status paragraph ("Layers 0-6
complete; 275 tests" against 1,264) is a table of regenerable numbers, the false
`[done]` on Layer 4.5 and the untrue RDKit-boundary claim are corrected, 32
glyphs gone, qualitative kinetics stated in Known limitations. Decided in
`BACKLOG.md`: delete `discovery/refine.py`; adopt reachable-reactions and reject
a self-scored family checklist; defer the README trim into C1. Added the
`handoff` skill. Next: T1.0, the extractability measurement.
