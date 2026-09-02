# Backlog

Open work only. A finished item is **deleted** from this file — its record is the
`CHANGELOG.md` entry and the commit. No ticks, no post-mortems.

Sizing: S = under two hours, M = a session, L = two sessions.
Order is priority order. Do not start a Tier 2 item while a Tier 0 item is open.

---

## Tier 0 — make the repo cheap to enter

### T0.3 — README length (S, decided: deferred into C1)
The status half is done: the stale paragraph, the false `[done]` on Layer 4.5,
the untrue RDKit claim and all 32 warning glyphs are gone, and the coverage
narrative points at the generated reports. 662 -> 561 lines.
Decision 2026-09-01: the 300-line target was arbitrary and the remaining overage
is the physics prose, which is the best argument the README makes for why this is
not a recipe table. It stays until C1 moves the same material into
`docs/manual/chapters/`, at which point the README keeps a paragraph and a link
per topic. The budget target is 400, not 300, and this item is not a Tier 0
blocker any more.

### T0.4 — a fast test subset (S)
There are no pytest markers at all, so the only way to run less than the
30-minute suite is to name files. Run `python -m pytest --durations=0 -q` once
(ask first), mark everything over 2 s `@pytest.mark.slow`, register the marker in
`pyproject.toml`, and put `pytest -m "not slow"` into `check.ps1`.
**Done when:** `pytest -m "not slow"` is green in under three minutes.

### T0.5 — the two generators disagree (S)
`data/catalog/COVERAGE_REPORT.md:630` says 47 templates; there are 57 (38
`synthesis.py` + 9 `library.py` + 6 `electrolyte.py` + 4 `electrochemistry.py`).
Line 820 cross-quotes `PLAYABLE.md` as "36 runnable, 12 playable"; `PLAYABLE.md`
says 21 playable. Make `validation/catalog_coverage.py` read those numbers from
`build_playable`'s output or drop the cross-quote, and count templates rather
than hard-coding them. Give both generators a `--check` flag that exits non-zero
when the committed file differs from a fresh run.
**Done when:** the two files agree and `check.ps1` runs both with `--check`.

---

## Tier 1 — change the slope of coverage

The measurement behind this tier: 240 reaction classes over 377 catalog steps,
169 classes used by exactly one step, best single template unlocks 3 routes and
after 7 templates the curve is flat at +1. Historical velocity is +3 to +5
classes per session, so the remaining 181 classes are ~40 sessions and the curve
is flat. The bottleneck is that a template is a hand-written Python function.
Full argument: `fable analysis/05-COVERAGE-STRATEGY.md`.

### T1.0 — measure the extractable yield before building anything (S)
Before T2 is worth two sessions, count what it could produce: of the 377 steps,
how many have every species resolving to a SMILES (no `*-marker`), balance under
`validation/corpus_balance.py`'s LP, and carry a class that has no template
today. That upper bound decides whether T2 happens.
**Done when:** the three-way count is in `CHANGELOG.md` with the command.

### T1 — templates become data (L)
`data/templates/templates.psv` with
`name | tier | smarts | A | Ea_J | reversible | phase | class | source | notes`
plus optional `alpha`, `orders`, `solid_catalyst`, `electrons`, `hammett_rho`,
`hammett_slot`. `tools/build_templates.py` emits
`src/chemsim/reactions/template_data.py` and a
`load_templates(tier=..., classes=...)`, exactly as the eight other `*_data.py`
modules are generated. Write rows for all 57 existing templates and assert field
equality against the constructors they replace. One table-driven test replaces
the per-template test files: every row fires on every catalog step of its class
and reproduces the step's products. `TEMPLATE_CLASSES` in
`validation/catalog_coverage.py:433` goes away — the `class` column is the map.
**Done when:** `examples/named_routes.py`, the bench and the coverage report run
from the PSV with identical output, and adding a template is one row.

### T2 — extract literal templates from the catalog (L, blocked on T1.0 and T1)
`tools/extract_templates.py`: resolve each step's reactants and products to
SMILES, infer stoichiometry, atom-map, extract a reaction SMARTS with one bond of
context, verify it regenerates the products, assign kinetics from a class policy
table, write the row with `tier=literal`.
Note two things the analysis missed: the corpus carries **no stoichiometric
coefficients at all**, so balancing is an inference and not a check — and the LP
that does it already exists at `validation/corpus_balance.py:104`, which throws
away the coefficient vector `linprog` has already computed. Returning `x` instead
of a bool is step two of the extractor.
Rows that fail go to `needs_stoichiometry.psv` or `needs_review.psv`, never
silently.
**Done when:** the extracted rows pass the table-driven test and the report
distinguishes template-ready-via-family from via-literal.

### T2a — do not let literal rows poison selectivity (S, part of T2)
S11 established that selectivity is a rate ratio between templates racing in the
same flask. A hundred literal rows carrying policy-table `A` and `Ea` would make
every multi-template flask's selectivity noise. Literal rows must be loadable
per-route or per-tier, not swept into the default library, and `full_library()`
must say which tier it loaded.
**Done when:** `load_templates(tier="family")` is what the bench uses by default
and a test asserts a literal row cannot enter it implicitly.

### T3 — generalise the literal rows that cluster (M, repeating)
Cluster literal rows by reacting centre; where three or more share one, write a
family row, confirm it covers every member, retire the members.
**Done when:** each session retires at least ten literal rows or clears twenty
review rows, counted in `CHANGELOG.md`.

### T4 — one new headline metric: reactions reachable from the shelf (M)
Run `build_network` to a fixpoint (`generations=None`, 400-species cap, 60 s
budget, cached by species pair) from every pair of natural shelf rows and count
distinct concrete reactions. This measures what a player can actually do, it is
computed rather than declared, and it cannot be gamed by adding rows to a list.
Decision 2026-09-01: the ~70-row organic-family checklist that was proposed
beside it is **not** adopted as a headline. A list the project writes and then
scores itself against is the same trap G4 found in the granularity scorer — an
instrument you can charge the target with. Keep such a list if it helps as a work
queue, in `BACKLOG.md` or a tools file, never in the report as a score.
The 173-route intersection stays as the second headline: it is the only number
anchored to chemistry the project did not invent.
**Done when:** the reachable-reaction count prints in `COVERAGE_REPORT.md` with
the command that produced it, beside the intersection.

---

## Tier 2 — engine work that moves playability

### R6 / E1 — a lattice becomes its ions (M)
A term consuming a `mineral_data` lattice and producing its ions in the solid
block, priced from the same Ksp `PrecipitationArrays` already uses, so a rock
dissolves. The design is argued in `docs/history/milestones/` — grep `R6`. This
is the one engine item that unblocks the "rock into water" half of the shelf, and
it converges the two representations of a rock that today have disjoint
mechanics.
**Done when:** 0.5 mol NaCl lattice into 30 mol water reaches the same end state
as 0.5 mol of its ions, and the six shelf rows that had to pick a representation
regain the other mechanic.

### R4 / E3 — delete `discovery/refine.py` (S, decided)
Decision 2026-09-01: **delete it**, and with it the `[done]` on Layer 4.5 in the
README's layer table and the `discovery` layer in `chemsim/__init__.py`.
The reasoning, so it is not relitigated: rate-aware pruning exists to make a
network tractable, and the R-series measured that a fixpoint is free for the
chemistry that matters (sulfur/air/water/NO2 closes at 14 species in 1.5 s).
Where a network *is* too big, the species cap already bounds it and reports
itself through `notices`; pruning would drop species silently, which rule 10
forbids without a report. The module as it stands is a sketch — zero callers,
zero tests, a duplicated `build_network`, and a `_rates_of` that judges species
on `to_arrays(thermo=None)`, i.e. on forward kinetics with no derived reverse,
no `T^n`, no declared orders against solids, no Hammett and no electrode work,
which is not the rate anything actually runs at. R3 already deleted
`prune_threshold` for a related reason. If T1/T2 make networks explode, rebuild
pruning against that measured need, where the charge is known, and make it
report what it dropped.
**Done when:** the module, its `discovery/__init__.py`, the layer row and the
README claim are gone, and `./check.ps1` is green.

### E2 — "react until done" as the default (S)
The R-series measured a fixpoint as free for the whole inorganic half of the
shelf (sulfur/air/water/NO₂ closes at 14 species in 1.5 s). `generations=None`
does it today and is not the default. In `ui/examples.py:bench()`, default to
`None` unless a template in the loaded library is self-feeding (a product
matching one of its own reactant slots — compute once at load), and fall back to
`generations=1` with a visible notice when one is. A player should never see the
word "generation".
**Done when:** sulfur + air + water reaches sulfuric acid with no button press
and glucose + water still terminates.

### E4 — decompose `make_rhs` (L)
`numerics/vessel_integrator.py:1781` is 673 lines wrapping a 506-line closure
with ~40 captured locals; nothing inside is independently testable or
profilable, though it visually contains its phase blocks already (volumes, Born
transfer, per-layer reaction, surface, solid-state, transport). Extract them as
module-level functions over arrays. Define the `Protocol` in
`numerics/integrator.py` that `VesselIntegrator` and `RigIntegrator` both
satisfy — they share eleven identically named methods and no base class.
**Done when:** no function in `numerics/` exceeds 120 lines of code, and
`validation/tolerance_audit.py` before and after shows no trajectory change
beyond solver tolerance, with the difference reported.

### E5 — the RDKit boundary claim (S)
`README.md:40` and `chemsim/__init__.py:14` say nothing above Layer 0 imports
rdkit. `reactions/template.py:25-26`, `reactions/hammett.py:182` and
`properties/fragmentation.py` do — and `fragmentation.py:58` carries a comment
saying "No rdkit here". Either move `ReactionFromSmarts`/`RunReactants` behind a
`matter/rewrite.py`, route `hammett.survey` through `Molecule`, and add a test
that greps `src/chemsim` outside `matter/` for `rdkit`; or delete the claim.
**Done when:** the claim and the code agree.

---

## Tier 3 — cleanup, only once Tier 1 has landed

### C1 — move the essays out of the source (M, repeating)
The warning glyph appears ~1,050 times in non-generated source and milestone tags ~300 times.
`ReactionTemplate`'s class docstring is 200 lines; `_dryout_gates` is 158 lines
around 3 lines of code; the `rhs` closure is 56% comments, many of them
changelog entries. The physics in them is good and the file is wrong. Move it to
`docs/manual/chapters/`, leave a one-line pointer.
**Done when:** `python tools/check_docs.py` shows the `src/chemsim` glyph budget
under 50 and no comment carries a milestone tag.

### C2 — `validation/` becomes tests or checks (M)
41 scripts, 3,285 `print` calls, 9 `assert`s, no runner and no exit codes: a lab
notebook labelled a validation harness. Each script either gains asserts and
moves to `tests/` under `slow`, or exits non-zero on a regression and joins
`check.ps1 --full`.
**Done when:** every file in `validation/` fails loudly when its own claim breaks.

### C3 — extract the live design rationale from `GAME_DESIGN.md` (S)
It is 58 KB and quotes `SAVE_VERSION` as 4 in one place and 7 in another; it is
9. The load-bearing arguments — "a stock is a composition, not (name, purity)",
"a gate must be a mechanism", lattice versus ions — become one `docs/design/`
file each, stripped of narrative. What is left becomes an index or goes to
`docs/history/`.
**Done when:** no root markdown file quotes a `SAVE_VERSION` and each argument
lives in exactly one place.

---

## Not doing, and why

| not doing | because |
|---|---|
| a Debye–Hückel / electrolyte activity model | γ for ions blocks no route |
| LHHW or Michaelis–Menten rate laws | no playable route needs one |
| a Rust kernel | the RHS is 231 µs; the cost is numpy dispatch, not arithmetic |
| another coverage-scoreboard correction | four are in; the instrument is fine |
| appending to anything in `docs/history/` | frozen |
| a markdown file over 300 lines | nobody reads it |
