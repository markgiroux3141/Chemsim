# Changelog, 2026-09-02 to 2026-09-12

Rolled out of `CHANGELOG.md` on 2026-09-16 when it passed 400 lines. Frozen:
grep it, never append to it. The live file at the root carries 2026-09-13
onward.

## 2026-09-12 — T8: three pKa rows, and the cannot-fire column is empty

`properties/electrolyte._PAIRS` 30 -> 33: oleic acid 5.02 (PubChem CID 445639,
Riddick 1985), eugenol 10.19 (IUPAC via CID 3314, Brauer 1964), hypochlorous
acid 7.53 (Morris, J. Phys. Chem. 70 (1966) 3798). The oleate is the molecular
constant, not the 8-10 the fatty-acid literature reports for a micelle surface
this engine has no phase for. `classify_silent.py` cannot-fire 2 -> 0, silent
28 -> 24, work order 22 -> 20; `build_reachable.py` (638 s) 29 -> 33 templates
fired; `build_playable.py` 21 -> 22; `catalog_coverage.py` refused 416 -> 412,
species-ready 85 -> 88, intersection 38 -> 40 on `hypochlorite-bleach` and
`bleaching-powder`. The priced oleate let the fatty-acid cascade reach a
stearate and crash the sweep out of the Evans-Polanyi barrier; the builder
drops that reaction with a notice now, as T1d did the reverse end (T13, T14).
`./check.ps1` green, 1,304 collected, 34 test files run; full suite NOT run.

## 2026-09-12 — T9: the shelf makes an aromatic aldehyde, and the work order was wrong

`tools/classify_silent.py` asked what the shelf can make from shelf species plus
the small-molecule closure, and coniferyl alcohol is 13 heavy atoms so it never
entered: `oxidative_cleavage` turns it and air into VANILLIN in one generation,
the substrate the file had at the head of its own work order as unmakeable.
Three defects, all in the classifier. The pool gains a bounded second tier --
each row too big for the closure, plus the closure, one generation, `<row>@1`,
reporting `step_frontier = 304` and `pool_unpriceable = 42`. The witness search
minimises COST not set size, so a real pair beats a one-tier cover that hid a
`cannot-fire`. A template is charged to EVERY missing slot, not the first: the
aldehyde blocked three templates and would have unblocked one. no-substrate
25 -> 20, needs-more-than-a-pair 1 -> 6; `[S;H2]` is the new head (T12).
`./check.ps1` green, 1,303 collected, `playable` green at 48 s, still DUE (T11).

## 2026-09-12 — T7: an equilibrium can be approached from either side

`network.builder._expand_reverse` searches every reversible template from its
PRODUCT side, so a species is found when only the far side of its equilibrium is
in the flask: discovery matched reactant patterns only, so CO2 and H2 in a hot
vessel made nothing while detailed balance held the reverse water-gas-shift rate
the whole time. The reverse rewrite PROPOSES and the forward rewrite DECIDES --
a candidate is re-run forward, kept only if it reproduces the products it came
from, then built in the template's own orientation, so no rate is declared, read
or invented (rule 9). Bounded by "a reverse step may not assemble a heavier
molecule"; unbounded it is retrosynthesis, and aspirin walked a polyester ladder
to the cap. `templates_fired` 25 -> 29 of 57, silent 32 -> 28, closure 41 -> 43
species (frontier still 0), `[C-]#[O+]` off the work order. Suite 1,301 passed
in 28m51s; tolerance audit red on pre-existing findings (T10). Next: T9.

## 2026-09-12 — T6: every silent template carries a label, and a ledger for the slow checks

`tools/classify_silent.py` classifies all 32 templates T4 found silent, in 2 s,
without re-running the 35-minute sweep: the 23 small-molecule shelf rows expand
to a TRUE fixpoint (41 species, frontier 0, `closure_frontier` in the artefact),
so "the shelf cannot make this" rests on a closure and not on a cap. 29
`no-substrate`, 1 `needs-more-than-a-pair`, 2 `cannot-fire` — and the 29 group
into 23 missing substrates, of which `[C-]#[O+]` alone holds four templates
(T7). The two `cannot-fire` rows are not bugs: both APPLY and lose the rewrite
to an unpriceable ion (T8). `data/checks/cadence.psv` + `tools/cadence.py` say
which expensive checks are owed, clocked in commits and derived from the
artefact where there is one. Tests 1,284 -> 1,297; smoke 39 -> 56.
`./check.ps1 -Full` green; the suite and the tolerance audit are DUE, not run.

## 2026-09-12 — T4: the third headline is computed, and it says 25 of 57

`tools/build_reachable.py` expands every pair of the 36 chargeable natural shelf rows to
a fixpoint with all 57 templates: **24,828 distinct reactions, and only 25 of 57 fire at
all**. The reaction total is the number NOT to quote — **98% of it is four templates**
(`ether_condensation`, `fischer_esterification`, `friedel_crafts_hydroxyalkylation`,
`transesterification`) over a sugar frontier — so the report leads with the template
count and names the 32 silent ones, a work queue nobody wrote by hand (T6). Bounds
reported: 320 of 630 pairs inert, 264 capped and undercounted, a three-reagent reaction
invisible. `COVERAGE_REPORT.md` READS the artefact; the sweep is ~35 min and segfaults
out of RDKit non-deterministically (pair 397 one run, 547 the next, 547 fine alone), so
it checkpoints, names the pair it attempts, resumes, and records one that dies twice.
Also closed the T1d hole it found: an ion already in the flask skips the product screen,
so that reversible reaction is now dropped with a notice. Tests 1279 -> 1284, green.

## 2026-09-12 — T1d: a missing pKa reports itself instead of killing the build

`examples/named_routes.py` runs to the end again — **17 routes in 32.4 s**, quoted from
its own output, and `CLAUDE.md`'s run list says so. The cause was not route 2:
`OutsideEstimatorDomain` on a charged species means *wrong provider, here is the right
one*, and `network.builder` passes it through on that promise — but with the ion overlay
ALREADY ON it means the opposite. New `UnpricedIon` draws the line, raised only when the
provider carries ions (counted, not declared) and this is not one. A template needing the
price (reversible, or Evans-Polanyi) DROPS the rewrite and reports it in `unpriced`; one
that does not still carries it, keeping `saponification` at 5 reactions on tristearin
instead of 0. Four tests pinned the traceback and now pin the report — Kolbe cascade,
eugenolate, nitroanilinium, hypochlorite: one bug recorded four times as "the refusal is
KEPT". Filed T5 to measure the pKa table's edge. Tests 1278 -> 1279; `check.ps1 -Full`
green plus 690 across 30 files; COVERAGE_REPORT regenerated, exception name only.

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
