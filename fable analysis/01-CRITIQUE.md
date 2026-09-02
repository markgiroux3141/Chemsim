# Critique: what works, what does not, and what to do differently

Everything below was measured against the tree on 2026-09-01. Numbers come from
running commands, not from the repo's own prose, which has drifted in several
places noted here.

---

## Part 1 — What genuinely works

Be clear about this before the tearing-apart: the physics engine is good, and a
weaker model should not "fix" the parts below.

**1. Detailed balance as architecture.** Templates declare forward kinetics only.
The reverse Arrhenius pair is derived from ΔH and ΔS at build time and enters the
kernel as an ordinary reaction (`reactions/thermo.py`, `network/builder.py:819`).
Le Chatelier, self-heating lowering yield, the azeotrope, and pH from mass action
are consequences, not code. Nobody should add a "reverse rate" field.

**2. One stiff system for the flask.** `y = [n_liquid | n_liquid2 | n_gas | n_solid | T]`
in moles, not concentrations, so a flask can boil dry. Boiling and melting points
are not looked up; they emerge from Σp reaching ambient and from the fusion law
reaching a = 1. A condenser is a cold vessel with two edges. This is the most
elegant modelling in the repo and it is correct.

**3. The numerics boundary is real.** Every import under `src/chemsim/numerics/`
is numpy, scipy, `constants`, or `KineticArrays`. No molecule ever reaches the
hot loop. The README's second boundary claim is true, verified by grep.

**4. Data discipline.** ΔGf is derived from ΔHf and S°, never transcribed.
Formation entries survive two independent cross-checks. Physical data is
generated from the catalog with provenance columns. The trap record (Joback
returning ΔHf for Cl₂, `chemicals` handing back your own Joback estimate as
"measured") is the most valuable artefact in the repo.

**5. Tests are honest.** 1,264 tests, zero `skip`, zero `xfail`, zero `TODO`,
no tolerance wider than `rel=0.5` and those two are justified. Conservation
tests are pure invariants. Pins in `test_vitriol.py` and `test_lead_chamber.py`
are derived, not "whatever the engine printed". Dead code is ~0.6%.

**6. The game loop exists.** A player can open a shelf, pour two things,
step, read the result, bottle it under a name, and a stock is a full
composition vector, never `(name, purity)`. That decision is right and it is
implemented (`engine/stock.py`, `ui/session.py`, `ui/app.py`).

---

## Part 2 — What does not work

### 2.1 The content pipeline is hand-crafted, one reaction at a time

This is the user's complaint and it is correct. The measurements:

| quantity | value |
|---|---:|
| reaction classes in the catalog | 240 |
| classes with a template | 59 |
| classes used by exactly ONE step in the whole corpus | 169 |
| ...of which have no template | 138 |
| routes one class away from template-ready | 44, wanting 35 different classes |
| best single template's unlock | 3 routes; after 7 templates the curve is flat at +1 |
| lines per template in `synthesis.py` | mean 59, median 40, max 226 |
| test + validation lines per template family | roughly 500 to 1,000 |
| historical velocity | +3 to +5 classes and +3 to +4 template-ready routes per session |

At that rate the remaining 181 classes are about 40 sessions, and the curve is
flat, so there is no lever inside this approach. Three structural causes:

**(a) The target list has no family structure.** The catalog is 173 *named
industrial processes*. A named process is a one-off by construction. 240 classes
over 377 steps is 1.57 steps per class. Any taxonomy that granular guarantees a
template never amortises. The repo noticed this in `ASSESSMENT.md` on
2026-08-17 ("the marginal value of another dozen templates exceeds another
physics module") and again in memory on 2026-08-31 ("the slog is a property of
the target list, not the architecture"), and then continued splitting classes
further for honesty. Honesty was right; velocity paid for it.

**(b) Many templates are single reactions in SMARTS clothing.**
`methanol_from_carbon_monoxide` matches CO + 2 H₂ and nothing else.
`ammonia_synthesis`, `water_gas_shift`, `steam_reforming`, `deacon_oxidation`,
`sulfur_combustion` are the same. Roughly a third of the library buys exactly one
catalog row each. The README's thesis ("a few hundred templates generate an
unbounded space") is true for esterification (166 acids × 190 alcohols ≈ 31,500
reactions) and false for the metallurgy and gas chemistry that the natural-
materials tech tree actually needs.

**(c) Each template is a Python function with an essay attached.** A template
is two lines of SMARTS and two numbers. In this repo it arrives as a 40 to 226
line function whose docstring argues its own irreversibility, plus a bespoke
test file (250 to 550 lines), plus a validation script (220 to 590 lines), plus
an entry in `TEMPLATE_CLASSES` in `validation/catalog_coverage.py:433`, plus a
paragraph in three markdown files. The per-template cost is dominated by prose
and ceremony, not by chemistry.

**(d) No leverage tooling exists.** Nothing generates an atom-mapped SMARTS from
a route step's reactant and product SMILES. Nothing proposes a template. The
catalog already contains 377 steps with SMILES on both sides. RDChiral-style
template extraction, USPTO template sets, and RMG's reaction families are
mentioned nowhere (grep: zero hits for `rdchiral`, `USPTO`, `reaction famil`).
RMG is cloned for its Benson thermochemistry and its reaction families are walked
past. NIST's Chemical Kinetics Database is never referenced; every
pre-exponential is, in the code's own words, "an order-of-magnitude choice for
the molecularity, as everywhere in this project."

**(e) Sessions were spent on the instrument, not the content.** The G-series
and P-series built and re-corrected the scoreboard four times (rules for what
counts as reachable, grids of scoring rules, joint versus marginal grants). Every
correction was valid. None added a reaction. The scoreboard is now more
accurate than the thing it scores is large.

### 2.2 Documentation has become a diary, and the diary is the primary interface

| file | size | headings | ⚠ markers | ALL-CAPS words |
|---|---:|---:|---:|---:|
| `HANDOFF.md` | 574 KB, 8,637 lines | **0** | 769 | 5,699 |
| `MILESTONES.md` | 462 KB, 7,810 lines | 320 | 729 | 4,402 |
| `NEXT_SESSION.md` | 214 KB | 29 | 456 | 1,551 |
| `NEXT_PROMPT.md` | 129 KB | 18 | 359 | 1,741 |

1.6 MB of root prose, 84% of it append-only session narrative. Over 1,600
warning glyphs and roughly 14,000 shouted words. A marker used 1,600 times
carries no signal. Section titles are paragraphs. `NEXT_SESSION.md` and
`NEXT_PROMPT.md` are the same artefact from two dates and both read as current.
The `README.md` Status section says "Layers 0–6 complete; 275 tests" while its own
architecture table lists Layer 7 done and the suite has 1,264 tests.
`GAME_DESIGN.md` quotes `SAVE_VERSION` as 4 in one place and 7 in another; it is 9.
`HANDOFF.md:82` tells a new contributor the suite takes "~25 s"; it takes about
30 minutes. `HANDOFF.md:3` and `EQUIPMENT_PLAN.md` tell the reader to start with
memory files that are not in the repo. There is no `CLAUDE.md`.

The consequence for a weaker model is severe: it will open `HANDOFF.md` because
the docs tell it to, spend its whole context on a headingless diary, and still
not know how to add a template, because no document anywhere says how. Grep for
"how to add" across every markdown file returns zero hits.

### 2.3 The diary leaked into the source

`⚠` appears 851 times in non-generated source. Milestone tags (`S9`, `M6`, `C4`,
`R3`...) appear roughly 300 times in comments. The hot loop closure `rhs` in
`numerics/vessel_integrator.py:1948` is 506 lines, 56% of them comments, many of
them changelog entries ("MEASURED: the head stalled at 9.998e-07 mol... same
relocate-the-fight signature as the ramp"). `ReactionTemplate`'s class docstring
is 200 lines. `_dryout_gates` is 158 lines with 3 lines of code. The content of
these comments is often excellent physics. It is in the wrong file: it triples
the size of every module and a reader in 2027 cannot resolve "S9" without
archaeology.

### 2.4 Architectural claims that are not true

- **"`matter` hides RDKit; nothing above Layer 0 imports rdkit"** (`README.md:40`,
  `chemsim/__init__.py:14`). False. `reactions/template.py:25`,
  `reactions/hammett.py:182` and `properties/fragmentation.py` import rdkit
  directly. `fragmentation.py:58` even has a comment saying "No rdkit here".
  Either enforce it (a test that greps) or stop claiming it.
- **Strict downward layering.** Holds at module level with one lazy upward import:
  `properties/electrolyte.py:406` imports `chemsim.reactions.ReactionTemplate`
  inside a function. A lazy import is how a cycle gets silenced without being
  removed. Dissociation templates belong in `reactions/`.
- **"Layer 4.5 discovery"** is listed as `[done]`. `discovery/refine.py` has zero
  callers and zero tests, has been dormant since Layer 6, builds the same network
  twice (`edge_net` and `core_net` are constructed with identical arguments), and
  its `_rates_of` calls `to_arrays(thermo=None)`, which ignores derived reverse
  kinetics, the `T^n` exponent, declared orders' interaction with solids, Hammett
  and electrode work. It is not done. It is a sketch.

### 2.5 Engineering debt in the hot path

- `VesselIntegrator.make_rhs` is 673 lines wrapping a 506-line closure with about
  40 captured locals. Nothing inside is independently testable or profilable.
  It contains visually separate phase blocks (volumes, Born transfer, per-layer
  reaction, surface, solid-state, transport) that are begging to be functions.
- `VesselIntegrator` and `RigIntegrator` share 11 identically named methods with
  no shared Protocol or base class. `numerics/integrator.py` defines an
  `Integrator` neither inherits from.
- `synthesis.py` is 2,626 lines of flat constructors and 17 bundle functions;
  `library.py` holds the sulfur chemistry except for the two sulfur templates
  that are in `synthesis.py`. The split has no rule.

### 2.6 Kinetics are qualitative and the docs do not say so loudly enough

Every `A` is a guess at the collision limit for the molecularity. Every `Ea` is
"the middle of a literature band" with no citation. The repo's own defence is
correct as far as it goes: most steps run to an attractor, so a rate wrong by 10×
moves the clock and not the answer. But the game's selectivity mechanics
(competing templates, Evans–Polanyi, Hammett) are rate *ratios*, and a ratio of
two guesses is a guess. The `validation/rate_ceiling.py` check only catches a
pre-exponential above the collision limit. Nothing checks a barrier against a
measured rate. This is acceptable for a game. It must be labelled as such in one
place a player or developer will read.

### 2.7 Process: 30-minute suite, no fast subset, no CI, validation that prints

- No pytest markers at all. The only way to run less than 30 minutes is to name
  files. `HANDOFF` claims 25 s.
- No `.github/`, `tox.ini`, `Makefile` or `noxfile`. Nothing has ever run
  automatically.
- `validation/` is 41 scripts with 3,285 `print` calls and 9 `assert`s, no
  runner, no exit codes. It is a lab notebook labelled as a validation harness.
  Its findings are correct and unrepeatable by machine.
- Two generated reports disagree: `COVERAGE_REPORT.md` quotes PLAYABLE as
  "36 runnable, 12 playable"; `PLAYABLE.md` says 21 playable. The generators
  are not run together.

### 2.8 The game has the engine's honesty problem inverted

The engine refuses to be silent about approximations, which is right. The UI
then exposes every one of them: "one generation" as the unit of a step, a
species cap, a generations box, a "REACT FURTHER" button that raises bounds. The
repo's own R-series measurement shows a fixpoint is free for the whole inorganic
half of the shelf (sulfur/air/water/NO₂ closes at 14 species in 1.5 s). "React
until done" is available today by setting `generations=None` and has not been
made the default. A player should never see the word "generation".

---

## Part 3 — What to do differently

### 3.1 Change what "coverage" means

Stop scoring against 173 one-off industrial routes as the headline. Two better
headlines, both computable today:

1. **Functional-group family coverage.** A list of about 60 to 80 named organic
   reaction families (esterification, amide formation, SN2 on alkyl halides,
   E1/E2, hydration, hydrogenation, oxidation ladders, aldol, Grignard,
   Friedel–Crafts, EAS variants, reductions, Diels–Alder...). One template each,
   each amortising over hundreds of substrates. This is where the architecture's
   thesis is actually true.
2. **Concrete reactions reachable from the shelf**, counted by running the
   fixpoint from every shelf pair. This measures what a player can do, not
   what a historian named.

Keep the catalog for inorganic tech-tree routes, where a step really is a
one-off, and accept that those are literal reactions.

### 3.2 Make templates data, and make a "literal reaction" a legal template

A template is `(name, smarts, A, Ea, reversible, phase, class, source, notes)`.
Put them in a PSV or YAML next to the catalog. Load them with one function.
Two tiers:

- **family** templates: generic SMARTS, curated by hand, the current standard.
- **literal** templates: one specific balanced reaction as an atom-mapped SMARTS,
  auto-generated from a catalog step's SMILES and reviewed, with kinetics from a
  per-class default policy.

The repo already does this in spirit (`sulfur_combustion` is literal). Admitting
it lets the 377 catalog steps become 377 candidate rows produced by a script,
not 377 Python functions produced by sessions. Testing becomes table-driven: one
parametrised test asserts every row fires on its own step's reactants, produces
its declared products, and balances. See `05-COVERAGE-STRATEGY.md`.

### 3.3 Build the extraction tool before writing another template

`tools/extract_templates.py`: for each `route_steps.psv` row with graph species
on both sides, atom-map with RDKit (MCS-based for small inorganic steps;
`rxnmapper` optional for organics), extract a reaction SMARTS with one bond
radius of context, verify it regenerates the products, write the row. Expect
150 to 250 of 377 to succeed automatically. That is more template-ready steps in
one afternoon than the last three weeks produced.

### 3.4 Adopt a kinetics policy instead of a kinetics essay

A table by class: molecularity → `A`; class → `Ea` band midpoint; reversible
unless the class is in the irreversible list (gas loss, anion product,
elimination into excess). Apply it to every literal template. Write the essay
once, in `docs/`, not once per template. Where NIST Kinetics has a value, use it
and cite the record id in the `source` column.

### 3.5 Cut the documentation to a working set

- One `CLAUDE.md` (under 150 lines): what this is, how to run, where things are,
  the ten rules. Point it at this folder.
- `README.md`: keep architecture, quickstart, and one status table that is
  generated. Delete the milestone narrative.
- Freeze `HANDOFF.md`, `MILESTONES.md`, `NEXT_SESSION.md` into `docs/history/`.
  Never append to them again. A session's record is a `CHANGELOG.md` entry of
  five to ten lines plus the commit message.
- Move physics essays out of function bodies into `docs/manual/chapters/`, which
  already exists and is the best-structured artefact in the repo. Leave a
  one-line comment with the chapter reference.
- Ban `⚠` and ALL-CAPS emphasis in new text. Use `NOTE:` and `WARNING:` at most
  once per file.

### 3.6 Make the suite runnable

Add `@pytest.mark.slow` to anything over 2 s (`--durations` tells you which),
register the marker, and make `pytest -m "not slow"` finish in under 3 minutes.
Add a `check.ps1` / `Makefile` that runs ruff, the fast suite, and
`tools/build_playable.py --check`. Convert `validation/` scripts to either
tests with asserts or scripts that exit non-zero on a regression.

### 3.7 Engine work that is actually worth doing

In priority order, and none of it before 3.2 and 3.3:

1. Decompose `make_rhs` into the phase-block functions it visually contains, with
   a `Protocol` shared by both integrators. Measured performance must not change.
2. Wire or delete `discovery/refine.py`. If wired: fix the duplicate build, make
   `_rates_of` use the real `to_arrays(thermo)`, put the knob where the charge
   lives (the bench pick), and default the UI to "react until done" for
   non-building chemistry.
3. Enforce the RDKit boundary with a test, or delete the claim from the README
   and `__init__.py`.
4. R6, the lattice-to-ions term, because it unblocks the whole "rock into water"
   half of the shelf. It is the one engine item that moves playability.

### 3.8 What not to build

- No electrolyte activity model, no LHHW rate laws, no polymer distributions, no
  Rust kernel, until the template count is in the hundreds. The physics is ahead
  of the content by an order of magnitude already.
- No more scoreboard corrections. The instrument is accurate enough.
- No new markdown file over 300 lines.

---

## Part 4 — A fair word on the slow crawl

Part of the slowness is inherent and part is self-inflicted. Inherent: correct
chemistry with honest kinetics and priced species is slow, and the repo's
refusal to fake a class as a mechanism it is not was the right call for a
simulator whose selling point is emergence. Self-inflicted: choosing a target
list with no family structure, wrapping every template in a bespoke Python
function with a bespoke test file, and writing the project's history into its
source and its README. The first is a tax that stays. The other three are
choices, and `05-COVERAGE-STRATEGY.md` and `06-WORK-ORDER.md` are how to reverse
them.
