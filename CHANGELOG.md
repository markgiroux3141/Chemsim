# Changelog

Newest first. One entry per session, twelve lines at most, enforced by
`tools/check_docs.py`. When this file passes 400 lines the older half rolls into
`docs/history/changelog-YYYY-MM.md`.

## 2026-09-13 — T1b: every template row against the catalog step it claims

`tools/check_template_products.py` (2.2 s) fires each of the 59 rows over the
`route_steps.psv` steps its class names and compares the product set. 191 steps
tried: 31 pass, 14 partial, 9 wrong-product, 3 no-substrate, 0 no-fire, 2
no-class. Committed as `data/catalog/derived/template_products.psv`, counts
derived as `#!` keys; `--check` is a new `check.ps1` step and eight tests went
into `tests/test_template_table.py`, not a new file (1,345 -> 1,353). Offered
only what a step names it refused `skraup_cyclisation` and a fermentation, so a
slot may draw on a declared three-species medium and the row says when it did.
Retiring the per-template tests is refused: 132 of their 208 build a network or
run a vessel (`docs/design/per-template-tests-not-retired.md`). Chemistry
unmoved. Next: T2, whose two walls are now counted — 8 rows miss only a salt.
## 2026-09-13 — T27: four pKa rows in route-demand order, and three routes come clear

`electrolyte._PAIRS` 37 -> 41 rows, ions 38 -> 42: vanillin 7.40, `dH_diss`
+14.4 off its own 10/25/40/55 C series (Kenttamaa 1970, the determination the
coniferyl alcohol row already used); adipic acid 5.41 with its first proton
re-sourced 4.43 -> 4.42 so both are Howell and Fisher 1958; cinnamic acid 4.42
(Nordstrom and Lindberg 1965); dimethylammonium 10.77, `dH_diss` +50.0 off five
stated temperatures (Everett and Wynne-Jones 1941). `pka_domains.py` panel 3:
corpus ions wanting a pKa 448 -> 444, the routes behind them 51 -> 48, and
`adipic-acid-route`, `perkin-route` and `vanillin-lignin` now have no pKa-shaped
hole. Coverage does not move, for the T23 reason (`COVERAGE_REPORT.md`,
`PLAYABLE.md`, `ROUTE_INDEX.md`, `silent_templates.psv` byte-identical);
`named_routes` diffs only to the refusal notice's ion count and the clock, so no
tolerance run is owed. 1,345 tests, check green. Next: T23's ranking, then T26.
## 2026-09-13 — T23: four pKa rows a player can reach, and both slow checks run

`electrolyte._PAIRS` gains malonic acid's two protons (2.85 / 5.70, Ives and
Prasad 1970, one determination for both), 4-nitrophenol (7.16) and coniferyl
alcohol (9.54), from PubChem's `iupacpka`, each with a `dH_diss` derived from
its own source's temperature series. `python validation/pka_domains.py` panel 2:
shelf ions unpriceable 39 -> 35 over FOUR compounds -> ONE, and it now derives
tannic acid's 35 as a bound rather than rows to write. Coverage does NOT move
and that is the finding: the catalog names its ions one row at a time and none
of these four is one, so `COVERAGE_REPORT.md` (408 refused, 46/90/40) and
`PLAYABLE.md` (23 playable) regenerate byte-identical. Panel 4 now counts the
pairs the scale orders BACKWARDS, 3 of 10 -- a second refutation of a phenol
rule (`docs/design/phenol-pka-rule-refused.md`). 1,342 -> 1,345 tests, check
green, suite twice (28m39s / 30m09s, exit 0), tolerance to the same T10 three.

## 2026-09-13 — T5: the pKa gap is counted, and the phenol rule is refused

`validation/pka_domains.py` (new, ~5 s) sweeps the six ion-producing template
rows over the corpus and the shelf to a fixpoint, so the classes are the rows
rather than a re-typed list of groups. Corpus: 1,078 ions reached, 1,030
unpriceable over 395 compounds, and only 451 of those WANT a pKa -- the other
579 have no priceable parent, so a row for them would be skipped the day it was
written. By class, 208 amine / 139 carboxylic / 104 phenoxide want one, behind
27 / 20 / 21 routes; mineral oxyacid wants ZERO of its 89, which makes it a
thermochemistry gap (T25). Shelf: 39 unpriceable ions over FOUR compounds, 35 of
them tannic acid's powerset. A phenol plateau is refused on two measured
grounds: 39 of 79 gap phenols sit outside the curated substituent range, and two
curated rows share a sigma_sum 3.45 pKa units apart. `./check.ps1` green, 1,338
-> 1,342 tests; T5 and T0.3 out of `BACKLOG.md`, T23 and T25 in.

## 2026-09-13 — T13: an unpriceable species never reaches the integrator

Which half moves was decided by `vessel.build_phase_arrays`: it prices EVERY
species for heat capacity and molar volume before a reaction is looked at, so a
flask holding an unpriceable one cannot integrate whatever its reactions are.
So `_unpriceable` drops unconditionally -- T1d's `tmpl.uses_thermochemistry`
condition read the templates, the wrong half of the engine -- and a new
`_refuse_unpriceable_feed` refuses a CHARGED one at `build_network`'s door,
naming the species, since dropping it would delete matter the caller put in.
Measured: a branched-acid triglyceride + hydroxide went 10 species / 7
reactions / `to_arrays` raising -> 4 / 0 / runnable; `silent_templates.psv`
reads `pool_unpriceable` 41 -> 0, `step_frontier` 306 -> 265. PLAYABLE.md,
COVERAGE_REPORT.md and the 17 named routes regenerate byte-identical (23
playable, 46/90/40). `./check.ps1` green plus 371 tests in 13 modules.

## 2026-09-13 — T18: the plateau is a rule, and a soap route starts running

`properties/carboxylic_pka.py` (new) holds T14's domain predicate, moved out of
`validation/` and rewritten against `Molecule` so Layer 1 gains no RDKit edge --
`matter.Molecule.reprotonated` is the one graph edit it needed. Its plateau
value is DERIVED from `_PAIRS` (4.95, the mean of the two in-domain rows from C3
up, span 4.87-5.02) and never typed. `ThermochemistryProvider` takes an
`ion_fallback` consulted after the curated table misses and before the refusal,
so a measurement is never overridden; `build_network` reports every ion the rule
priced through `notices`. Stearic acid + water: 12 species / 4 reactions -> 21 /
21. Corpus pairs priced 14 -> 32 (`validation/fatty_acid_pka.py --corpus-only`),
species-ready 89 -> 90, runnable 46 -> 47 (`soap-saponification`), shelf 70 -> 72
rows as its two feeds are newly STRANDED, playable unmoved at 23. `./check.ps1`
green, 18 test files + the 17 named routes byte-identical; suite/tolerance due.

## 2026-09-13 — T17: the scorer credits every step product, and a route falls out

`tools/build_playable.shelves` credited `route_roles.products`, so a species a
route makes and then consumes earned nothing -- while `needs` has read step
order since G4. `lime-cycle` row 2 slakes lime and row 3 carbonates it away, so
slaked lime was invisible and `bleaching-powder` stayed chain-blocked behind a
test red for three sessions. Every step product is credited now. Playable 22 ->
23 (`bleaching-powder`, tier 2), ceiling 46 -> 50, fed-but-unrunnable 21 -> 23,
target-only shortfall 6 -> 7; `copper-ii-oxide` is earned off the copper roaster
so its shelf row is deleted, 71 -> 70 rows and intermediates 24 -> 23. The
fouling-rule grid's difference is no longer zero, +1 in both rows, because the
rule it prices was strengthened. Nine pins re-measured over five test files;
`./check.ps1` green and 127 tests pass in the six files that import the scorer.
Suite and tolerance still due at 8; the deep chain's digits are unchanged.

## 2026-09-13 — T14: the plateau is a rule, and the pool is why

`validation/fatty_acid_pka.py` (new, 118 s) counts the carboxylic pKa wall
before anything is written. Corpus: 172 compounds carry a carboxyl, 182 distinct
conjugate pairs, 11 priced, 19 inside the plateau domain, 152 needing their own
measurement. Pool (oleic acid against each of the 36 other natural shelf rows,
11 capped at 400 species): 446 pairs, 253 in the domain — but 243 of those are
oligomers of ONE acid self-esterifying, a series with no last member. Corpus and
pool share 4 of 624. So rows close a list and this is not a list: T14 is
replaced by T18 (the rule), T19 (230 diacids, a different question) and T20 (the
oligoester series is a bound question). The plateau's width is derived from
`_PAIRS` rather than asserted: 4.87 to 5.02 from C3 up. Tests 1309 -> 1329.
No `src/` change, so no trajectory moved; suite and tolerance still due at 7.

## 2026-09-13 — T15: pyrrhotite saturates its own water, and pyrite is FeS2

Two repairs, both curation. `troilite` joins `build_mineral_data.CANDIDATES`
(CRC 1317-37-9, Hfs -100.0, S0s 60.3, Cps and Vm from one compilation), so
`iron-ii-sulfide` stops being the shelf row whose ions sit in the solid block for
ever: `build_shelf` moves it from SOLID IONS, INERT to a crop that dissolves,
lattices 49 -> 50, buildable-with-a-Ksp 28 -> 29, still 2 cation-blocked. pKsp
18.775 is derived, and the flask reaches exactly sqrt(Ksp) = 4.10e-10 M in each
ion and holds femtomoles of H2S over T12's two sulfide pKa rows. Acid keeps it
going and cannot speed it up -- the drive is `k_diss*V*(Qroot - Ksproot)`, so HCl
buys nanomoles an hour. `iron-disulfide` was `[Fe+2].[S-]S[S-]`, FeS3; now FeS2,
a formula fix for `corpus_balance` and not a price. Tests 1307 -> 1309; 46/89/40
and 22 playable unmoved; `./check.ps1` green, `routes` pass (149 tests, 223 s).
NOTE: `test_playable_levers` is RED and already was -- bisected to 188f22a, T8.

## 2026-09-13 — T12: the sulfide is priced by subtraction, and [S;H2] leaves the work order

C2 refused a pKa for HS- -> S2- because the compilations span 12.9 to 19; it was
never a pick. `ion_data` holds [SH-] and [S-2] on one CRC basis, so their
difference IS the dissociation Gibbs energy: 73.7 kJ/mol, pKa 12.91. Anything else
prices [S-2] twice, here and in five sulfide Ksp. `_PAIRS` 32 -> 33 rows (34 priced
ions); `sulfide_protonation` and `hydrosulfide_protonation` go protonation-first,
the reverse sweep refusing a proposal heavier than its flask. Templates 57 -> 59,
chargeable 1167 -> 1174, species-ready 88 -> 89, natural rows 36 -> 37, lattices
with a Ksp that cannot be flasked 5 -> 2 (both now cation-blocked). Work order
20 -> 19 and its head `[S;H2]` is gone: both Claus templates fire on the closure,
24 rows / 48 species, still a fixpoint -- which took 16 MINUTES until the Claus SO2
slot was tightened, `[O]=[S]=[O]` matching a sulfate too and eight such slots being
6561 rewrites of a 24-molecule template (T16 is the twin). `./check.ps1` green.

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
