# Backlog

Open work only. A finished item is **deleted** from this file — its record is the
`CHANGELOG.md` entry and the commit. No ticks, no post-mortems.

Sizing: S = under two hours, M = a session, L = two sessions.
Order is priority order. Do not start a Tier 2 item while a Tier 0 item is open.

---

## Tier 0 — make the repo cheap to enter

### T0.3 — README length (S, decided 2026-09-01: deferred into C1)
The status half is done, 662 -> 561 lines. What is left is the physics prose,
which is the best argument the README makes for why this is not a recipe table,
so it stays until C1 moves it into `docs/manual/chapters/` and the README keeps
a paragraph and a link per topic. Target 400, not 300. Not a Tier 0 blocker.

### T0.4 — a fast test subset (S)
There are no pytest markers at all, so the only way to run less than the
30-minute suite is to name files. Run `python -m pytest --durations=0 -q` once
(ask first), mark everything over 2 s `@pytest.mark.slow`, register the marker in
`pyproject.toml`, and put `pytest -m "not slow"` into `check.ps1`.
**Done when:** `pytest -m "not slow"` is green in under three minutes.

---

## Tier 1 — change the slope of coverage

The measurement behind this tier: 240 reaction classes over 377 catalog steps,
169 classes used by exactly one step, best single template unlocks 3 routes and
after 7 templates the curve is flat at +1. Historical velocity is +3 to +5
classes per session, so the remaining 181 classes are ~40 sessions and the curve
is flat. The bottleneck is that a template is a hand-written Python function.
Full argument: `fable analysis/05-COVERAGE-STRATEGY.md`.

T1.0 measured the gate on 2026-09-02 (`python validation/extraction_yield.py`,
argued in `docs/design/extraction-yield.md`): 174 of 377 rows resolve, balance
and sit in an uncovered class, spread over 132 classes of which 102 hold one row.
Upper bound if all became templates: intersection 38 -> 66, template-ready 46 ->
110; 36 of the 64 gained routes are then held by an unpriceable species. T1 and
T2 survive. The LP passes rows atom-mapping will refuse, so 174 is a ceiling.

### T1b — the row-level product check (M, was T1's fourth bullet)
The switch-over landed without it. `tools/build_templates.py` now checks the
column SET against `ReactionTemplate`'s fields and the SET of construction sites
under `src/chemsim`; what neither can ask is whether a row's SMARTS still makes
the products the catalog step says it makes. That is what the per-template test
files do, one file per template, and it is why they cannot be retired yet.
Build the instrument the M1 row check already implies: for each row, for each
`route_steps.psv` step of its `class`, resolve the step's reactants, fire the
template, and compare the product set. A row whose class has no runnable step is
reported, not skipped silently.
Then, and only then, retire the per-template test files — which needs a
full-suite run, so it is the same session or the one after.
**Done when:** one command reports pass/refused/no-runnable-step per row, its
count is in `NEXT.md`'s state table, and the file count under `tests/` has
dropped by the number of per-template files it replaced.

### T2 — extract literal templates from the catalog (L, unblocked: T1.0 and T1 are in)
`tools/extract_templates.py`: resolve each step's reactants and products to
SMILES, infer stoichiometry, atom-map, extract a reaction SMARTS with one bond of
context, verify it regenerates the products, assign kinetics from a class policy
table, write the row with `tier=literal`.
Note two things the analysis missed: the corpus carries **no stoichiometric
coefficients at all**, so balancing is an inference and not a check — and the LP
that does it now returns its vector: `corpus_balance.coefficients()`. The vector
is not unique when the element matrix has a two-dimensional nullspace
(`phthalic-anhydride-route` step 2 comes back fractional), so the extractor needs
a smallest-integer-vector step after the LP before it can write coefficients.
Rows that fail go to `needs_stoichiometry.psv` or `needs_review.psv`, never
silently.
**Done when:** the extracted rows pass T1b's row-level product check and the
report distinguishes template-ready-via-family from via-literal.

### T3 — generalise the literal rows that cluster (M, bounded)
Cluster literal rows by reacting centre; where three or more share one, write a
family row, confirm it covers every member, retire the members. T1.0 found only
6 uncovered classes with three or more extractable rows (24 rows in all), so this
is one or two sessions, not a repeating one.
**Done when:** the 6 families are written or refused with a reason, and the
retired row count is in `CHANGELOG.md`.

### T5 — measure what the 30-row pKa table bounds (S, measurement first)
T1d turned "no pKa for this ion" from a traceback into a reported coverage
limit, and the reports promptly named five in one session: salicyl alcohol's
phenoxide, the Kolbe dianion, eugenolate, a nitroanilinium, hypochlorite. A
family template matches any aromatic hydroxyl or any amine; `_PAIRS` is 30
hand-typed rows. Nobody knows how wide the gap is. Sweep the 1167 priced corpus
species, fire each dissociation template on each, and count the ions with no
pair — grouped by the acid class that would fix them, since one sourced pKa
series can cover many rows. Do this BEFORE writing any pKa: the answer decides
whether the fix is a dozen rows or an estimator, and an estimator for pKa is the
kind of thing `element_data` exists to refuse.
T8 answered three of them by hand (oleate, eugenolate, hypochlorite) and the
table went 30 -> 33 rows, so the sweep is now over a table just shown to be
three short of what a flask of NATURAL shelf rows reaches in one generation.
T14 asks the same question for one acid class.
**Done when:** the count and its top acid classes are in `NEXT.md`'s state table
with the command, and a follow-up item names whichever of the two fixes the
number argues for.

### T11 — an artefact-backed check that changes nothing can never clear (S)
Found 2026-09-12 while closing T7. `playable` went DUE at 8 commits, was re-run
(45 s, `--check` green), and produced BYTE-IDENTICAL output -- so there is no
commit touching `data/catalog/PLAYABLE.md` to derive a last-run from, and
`--record` refuses an artefact-backed row by design. The row therefore reads DUE
for ever until the artefact's CONTENT happens to move, which is the one thing a
passing check does not do. Deriving the date from git is still right -- it is
what stops a row being stamped green by hand -- so the fix is a third state: a
run that confirms no change is recorded as such, distinct from both a stamp and
a commit. Note the same trap waits for `reachable`.
**Done when:** re-running an artefact-backed check whose output is unchanged
clears its DUE, and `python tools/cadence.py` explains which of the two happened.

### T10 — two examples print a digit that depends on the solver (S)
`validation/tolerance_audit.py`'s first recorded run came back red on
`activity` (worst 0.128%) and `multistep_prep` (0.107%): a quotable digit moves
between the default tolerance and rtol 1e-8. Measured PRE-EXISTING -- both print
byte-identical output on pre-T7 and post-T7 source -- so this is debt the audit
found rather than damage. `named_routes` additionally raises at rtol 1e-8, and
the audit diagnoses that in-run as older than S13. The fix the audit itself
prescribes: give each example its own tight tolerance, as `lime_cycle.py` and
`roasting_and_the_catalyst_gate.py` already do.
**Done when:** `python validation/tolerance_audit.py` exits 0, or the ledger
note says which of the three is a standing refusal and why.

### T13 — an unpriced ion in the flask still stops `to_arrays` (S, found in T8)
`_unpriceable` deliberately KEEPS an ion the template that made it does not
need a price for -- `saponification` is irreversible with alpha = 0, so its
stearate is registered unpriced on purpose, and dropping it would delete
chemistry the engine can do. T8 then guarded the two places that ask for the
price later (the Evans-Polanyi barrier, and detailed balance since T1d), so
`build_network` no longer raises. `ReactionNetwork.to_arrays` still does:
measured today on a flask charged with saligenolate plus saligenol plus water,
which builds 7 reactions and then refuses. So a network can be built, reported
and un-runnable, and the player finds out one call later than the notice.
Decide which it is: either the species is dropped at registration after all
(and the notice says the flask lost matter), or `to_arrays` reports the same
way the builder does and the vessel runs without it. Do not pick by taste --
the second changes what is in the flask silently unless it notices too.
**Done when:** a network holding an unpriced ion either integrates or refuses
with a notice naming the species, and one test pins whichever was chosen.

### T14 — the fatty-acid pKa wall (S, measurement first)
T8 priced the oleate and the cascade in `gypsum + oleic-acid` promptly reached
a stearate, a hydroxystearate and two partial-glyceride carboxylates that
`_PAIRS` does not carry. Each is the SAME number to three figures -- every
unbranched aliphatic carboxylic acid sits on the 4.9 plateau the table's own
formic/acetic/propanoic series is converging to -- so this is not 30 lookups,
it is one rule with a domain. Before writing any of them, count them: sweep
the corpus and the pool for carboxylates whose acid is an unbranched chain,
and report how many rows a single plateau value would cover against how many
genuinely need their own measurement. T5 is the same question one level up.
**Done when:** the count is in `NEXT.md` with its command, and a follow-up
item says whether the fix is rows or a rule.
### T15 — the sulfide half of the shelf is still half-represented (S, found in T12)
T12 priced `[S-2]`, so pyrrhotite is chargeable and the closure reaches H2S.
Two things did not come with it, and `tools/build_shelf.py` now prints the
first one by name rather than asserting nobody can hit it.
* `iron-ii-sulfide` declares `solid` with ion species and has NO Ksp, because
  troilite is not in `mineral_data`. Its ions therefore sit in the solid block
  for ever: DISCOVERY reacts them and the integrator cannot move them, which is
  panel 5's "the score and the chemistry came out of different tables" arriving
  from the shelf side. `chemicals` has FeS under CAS 1317-37-9 (Hfs -100.0,
  S0s 60.3), so the mineral row is a tuple in `tools/build_mineral_data.py`.
* `iron-disulfide` is written `[Fe+2].[S-]S[S-]`, which is FeS3, not pyrite.
  Fixing the SMILES to `[S-][S-]` gives the formula `corpus_balance` needs for
  `pyrite-roasting` and does NOT make the row chargeable: the disulfide is in
  `ion_data` but its acid (HS-SH) is in no pKa pair. Two separate repairs.
**Done when:** a flask of pyrrhotite and water makes H2S in the INTEGRATOR, or
the shelf row says `liquid` and says why; and pyrite's formula is FeS2.

### T16 — the other loose sulfur-dioxide slot (S, found in T12)
`sulfur_dioxide_oxidation_by_nitrogen_dioxide` still writes SO2 as
`[O:1]=[S:2]=[O:3]`, the pattern that made `claus_comproportionation` take
sixteen minutes once H2S existed. It matches a SULFATE too, and two shelf rows
are sulfates. It is not a bomb -- three slots, not eight -- but the rewrite it
then attempts makes a five-bonded sulfur that sanitisation throws away, so the
template does work it cannot use on every flask holding a vitriol. Tighten it to
`[OX1]=[SX2]=[OX1]` as T12 did for the Claus row. It is chain 2's carrier step,
so the tolerance audit is owed and the Ea/A must not move.
**Done when:** the slot matches one shelf species, and
`tests/test_lead_chamber.py` is green with the same numbers.

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
The warning glyph appears ~1,040 times in non-generated source and milestone tags ~300 times.
First target is now `validation/catalog_coverage.py`: T1 deleted the 46
template-backed entries of `TEMPLATE_CLASSES` and derives them from the table,
which left **656 lines of taxonomy prose around a 14-entry dict**. The prose is
the record of why `combustion`, `deprotonation`, `acid-base` and `redox` were
split, and it is worth keeping — in `docs/design/`, with a pointer.
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
