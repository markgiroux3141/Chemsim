# chemsim — outside assessment

An external read of the codebase as it stands, written 2026-08-17 against a
verified state: **451 tests passing** (5m41s), **ruff clean**, ~14.3k lines in
`src/`, ~9.7k in `tests/` + `validation/` + `tools/`.

> **Snapshot caveat.** That state was the tree at ~15:05. While this was being
> written, another session began the liquid–liquid equilibrium work: a new
> `numerics/lle.py`, and the vessel state vector growing a second liquid block
> (`pack` now takes `n_liquid, n_liquid2, n_gas, n_solid, T`). Mid-refactor the
> suite does not pass — that is an edit in flight, not a defect. Everything below
> describes the pre-LLE tree, and §4 item 6 is now *in progress* rather than
> proposed.

This document has three parts: what the project is and what it does well, how
complete it is, and what prior art exists. It ends with a prioritised list of
what would make it more complete and better in general.

---

## 1. What it is, and what is genuinely good about it

An emergent chemistry engine: parameterise *reactions and molecular properties*,
compute *system evolution*, so that yields, side products and sensitivity to
temperature and contamination fall out of integrating a network rather than out
of a recipe table.

The strict layering (`matter → properties → reactions → network → numerics →
discovery → vessel → engine`) is real rather than aspirational.
`numerics/vessel_integrator.py` genuinely never mentions a molecule;
`network/builder.py` hands down nothing but numpy arrays and a species list.
Both inversion boundaries hold.

Four things stand out as unusually good.

**1. Detailed balance as an architectural device, not a feature.** Templates
declare forward kinetics only. The reverse Arrhenius pair is derived at
build time and becomes an ordinary row in the reaction table, so the integration
kernel has never heard of reversibility. That single decision is why Le
Chatelier's principle, the reflux azeotrope, and "an insulated exotherm yields
*less* ester because K falls" are emergent rather than coded. Most simulators of
this kind expose a reverse rate as a free parameter and lose thermodynamic
consistency the moment someone tunes it.

**2. The flask solves composition, phase and temperature as one stiff system.**
`y = [n_liquid | n_gas | n_solid | T]`, in *moles* rather than concentrations, so
a flask can boil dry without the state vector becoming meaningless. Neither the
boiling point nor the melting point is looked up anywhere: a liquid boils when
its summed partial pressures reach ambient, and a solid melts because the
ideal-solubility limit reaches unity — which happens exactly at `Tm` because that
is what the fusion equation says. One equation therefore covers dissolution
*and* melting. This is the most elegant piece of modelling in the project.

**3. A condenser is not a class.** It is a cold vessel with a vapour edge in and
a drain edge back. Reflux and distillation required no new physics — condensation
is the existing phase model discovering `p > p_eq` in a cold vessel. The still
locating the azeotrope by itself at x = 0.894, with the pot temperature at its
minimum exactly there and no azeotrope table anywhere in the codebase, is the
single best demonstration in the repository.

**4. The data discipline.** Provenance on every curated value; ΔGf *derived* from
ΔHf and S° rather than transcribed, so both halves of an entry are consistent by
construction; every formation entry surviving two independent cross-checks;
exclusions listed with residuals rather than quietly dropped. The `validation/`
harnesses re-measure claims rather than restating them. And the traps are written
down where they bit — Joback silently returning ΔHf = −74.8 kJ/mol for Cl₂ when
the true value is 0 by definition; PSRK's published H₂ SMARTS `[HH]` matching any
atom bearing one hydrogen. This trap record is, in my view, the most valuable
single artifact in the repository, and it is the thing most comparable projects —
hobby *and* academic — do not have.

Supporting evidence of care throughout: zero `TODO`/`FIXME`/`HACK` markers in
14k lines; a non-negative projection that conserves totals exactly instead of the
`np.maximum` clamp that was creating matter; `PHASE_INDEX` raising on an unknown
phase rather than defaulting to liquid.

---

## 2. How complete is it?

The honest answer is three different numbers, and the spread between them is the
most important fact about the project's current state.

### As a physics engine: ~75–80%

Done, and done properly: template-driven network generation to a fixpoint with
element and charge balance enforced; three-tier property resolution (curated →
Benson → Joback) with formation and physical halves resolved independently;
vapour–liquid equilibrium with real UNIFAC activity coefficients plus a PSRK gas
extension; solid–liquid equilibrium; ions and pH as ordinary mass action with no
pH solver; a full energy balance; coupled multi-vessel rigs as one block state
vector; filtration; two mechanistic process losses.

What is missing is *named and scoped*, which is a materially different situation
from vague incompleteness:

| Gap | Consequence | Difficulty |
|---|---|---|
| Liquid–liquid equilibrium | No sep funnel, extraction or washing an organic layer | Large — grows the state vector |
| Electrolyte activity (γ = 1 for ions) | The prep's 0.6 M mother liquor is held ideal | Medium — Debye–Hückel or eUNIFAC |
| Activity-basis equilibrium | Non-ideal mixtures equilibrate to the wrong quotient | One line, then a full recalibration |
| Non-mass-action rate laws | No LHHW, no Michaelis–Menten | Medium |
| Electrochemistry | No chlor-alkali, no conducting polymers | Large |
| Polymers / extended solids | Needs chain-length distributions, not graphs | Large — different representation |
| Solid↔gas flux | No sublimation, no freeze-drying | Small |
| Viscosity model | `kinematic_viscosity` is one caller-set number | Small |

### As chemistry breadth: ~15%

`reactions/library.py` contains **five** templates. The coverage audit sits at
66/70 species. There is no aromatic substitution, no organometallics, no
Grignard, no reduction, no amide coupling, no protecting groups, no explicit
catalysis.

**This asymmetry is the central issue.** The engine can express far more
chemistry than has been written down for it. Every recent session has deepened
the engine; the set of reactions it can actually perform has grown by five. The
marginal value of another physics module is now lower than the marginal value of
another dozen templates, and that ordering has probably been true for a while.

### As a game: ~0%

There is no frontend, no goal, no progression, no player, no scoring. The engine
is headless by design and that was the correct call, but "a game inspired by Nile
Red" is currently a thesis statement rather than a product. Nothing about the
engine blocks it; the loop and the goal simply have not been built.

### Known defects and risks, separate from gaps

- **No version control.** ~24k lines including several thousand hand-curated
  physical constants, with no `.git` anywhere. This is the highest-severity item
  in the repository and it is not a chemistry problem.
- **No LICENSE or NOTICE.** `benson_data.py` is built from RMG-database and
  `critical_data.py` from `thermo`; both upstreams are MIT and both require
  attribution in derived work.
- **`filter_into`'s `retention` is a fraction of the wrong thing** (documented in
  `NEXT_SESSION.md`) — it makes cake wetness depend on how much mother liquor
  happened to be present rather than on crop size. Every crude-purity number in
  the project currently inherits this.
- **Pre-exponential factors are the last hand-authored parameter.** The library
  says so plainly, which is right: barriers set the temperature response and the
  competition (and are sourced), while A-factors set only absolute timescale. The
  risk is erosion — that a simulated reaction *time* eventually gets quoted as a
  prediction.
- **The engine layer has fallen behind the vessel layer.** `losses` is not
  plumbed through `VesselSpec`, so a `World`-based prep cannot have either loss.

---

## 3. Does anything like it exist?

Every *ingredient* exists in mature software. The *combination* does not, as far
as I can establish.

**[RMG-Py](https://github.com/ReactionMechanismGenerator/RMG-Py) (MIT /
Northeastern)** is the closest scientific relative, and this project already
draws on it — `benson_data` is built from RMG-database. RMG does template-based
reaction families, Benson group additivity, and rate-based network enlargement
with pruning (the same idea as `discovery/refine.py`), then integrates via
[ReactionMechanismSimulator.jl](https://github.com/ReactionMechanismGenerator/ReactionMechanismSimulator.jl).
But RMG's world is *a reactor at a condition* — combustion, pyrolysis,
atmospheric chemistry. **There is no flask.** No boiling, no crystallisation, no
filtration, no cake, no transfer losses, no pH as emergent equilibria.

**Cantera, Chemkin, [KinSim](https://pubs.acs.org/doi/10.1021/acs.jchemed.9b00033)**
solve mechanisms you supply. No generation, no molecular graphs, no phase
behaviour of the kind here.

**[DWSIM](https://dwsim.org/), Aspen Plus, ChemCAD** are the other half, and are
far more mature at it: UNIFAC, flash, distillation, crystallisers, filters with
cake porosity and retained mother liquor. But species come from a databank and
reactions are declared as stoichiometry plus a rate expression. **There is no
molecule.** A side product nobody anticipated cannot appear.

**BioNetGen, COPASI** are rule-based network generation done well, but in
biochemistry — no thermochemistry, no phases, no temperature.

**ASKCOS, IBM RXN, Synthia** predict routes and products. They integrate nothing,
so they cannot report a yield, a selectivity, or what happens if the flask is
left open.

**Educational**: ChemCollective Virtual Lab, Labster, ChemReaX,
[Chemistry3D](https://arxiv.org/pdf/2406.08160). Fixed reaction sets with a
solver behind them; none generates chemistry it was not told about.

So the niche is specific and appears genuinely unoccupied: **RMG-style network
generation pointed at a bench flask instead of a combustor**, with enough
property estimation to price arbitrary graphs and enough vessel physics that
isolation and losses are part of the answer. The two communities that could build
it each already have what they need, so neither does. On the game side there is
nothing remotely comparable — the "chemistry games" that exist are puzzle games
with chemistry skins.

---

## 4. What would make it more complete, and better

Ordered by value per hour, not by intellectual interest.

### Tier 0 — infrastructure, measured in hours

1. **`git init`, commit, and push somewhere.** Every session's work currently
   depends on the filesystem not failing. There is also no way to answer "when
   did this number change and why", which for a project whose whole method is
   *measure, then re-measure* is a real methodological loss, not just a
   convenience one.
2. **LICENSE + a NOTICE crediting RMG-database and `thermo`.** Both MIT. Doing
   this now costs ten minutes; doing it after publication costs an audit.
3. **Split the fast suite from the slow one.** 5m41s is right at the boundary
   where a suite stops being run on every change. Mark the integration-heavy
   tests `@pytest.mark.slow`, default to `-m "not slow"`, and run everything in
   CI. (Once git exists, CI is free.)
4. **Restructure the written record.** `HANDOFF.md` is 60 KB and `NEXT_SESSION.md`
   16 KB, both organised chronologically. The durable content — the traps — is
   the most valuable thing in the project and it is currently indexed by *when it
   was discovered* rather than *where it applies*. Suggested split: `docs/traps.md`
   indexed by subsystem, `CHANGELOG.md` for the chronology, and a short
   `docs/design.md` holding the cross-cutting rationale (the setup/hot-loop split,
   the array contract, the one documented exception) that currently exists only in
   the README and in session memory. The test: could a second contributor be
   productive without reading 76 KB of narrative?

### Tier 1 — the completeness gap that actually matters

5. **Grow the template library — this is the highest-value work available.** The
   engine's expressive capacity is far ahead of its content. Concretely, in
   order:
   - **Explicit acid catalysis.** The audit already established this needs no new
     machinery: a catalyst is an explicit species with rate-law exponent 1 and net
     stoichiometry 0. It removes the "apparent barrier" caveat from three existing
     templates and makes "I forgot the acid" a thing the player can do.
   - **The benzoyl side product** named in `NEXT_SESSION.md`. It is the prep's
     stated purity gap, and it is a template rather than a knob — which is exactly
     the right kind of fix.
   - **A structurally different second route** — an aromatic substitution, an
     amide coupling, or a reduction. The current library is five templates all
     living on the alcohol/carbonyl axis, so the generality claim is untested
     outside one family.

   A good acceptance test for the library as a whole: *a route the library was not
   designed for produces a chemically plausible impurity nobody anticipated.*
   That is the founding claim, and it has been demonstrated once.

6. **Liquid–liquid equilibrium** *(underway as of 2026-08-17 15:05 — see the
   snapshot caveat at the top)*. The largest workflow hole: no sep funnel, no
   extraction, no washing an organic layer — which is most of practical
   preparative chemistry. UNIFAC already supplies the γ it needs. It grows the
   state vector, which is the one remaining large architectural change, and doing
   it *before* more features accumulate on the current vector is materially
   cheaper than doing it after.

### Tier 2 — keeping the claims true

7. **Make `validation/` a single runnable scorecard.** Five harnesses currently
   run by hand, when someone decides to. `python -m validation` should emit one
   report — every claim, its reference, its residual, and a pass/fail band — and
   that report should be committed, so drift is visible in a diff. This converts
   "measured" into "continuously measured", which is the difference between a
   discipline and a habit.
8. **Extend the equilibrium reference set from 2 reactions to 10–20.** The
   activity-basis question is currently *undecidable*, not merely unanswered: two
   reactions disagree by 4.9 kJ/mol, which is exactly the homologue spread, so
   there is no way to tell whether γ helps. More reference points is the only
   thing that unblocks it. (The homologue panel is the best diagnostic in the
   project precisely because it needs no reference at all — more instruments of
   that kind would be worth more than more data.)
9. **A machine-readable known-deviation registry.** Species and conditions where
   the model is known to be off, with the magnitude, asserted in tests. It stops
   a future improvement from being claimed where none happened, and makes a
   regression in a known-bad case visible instead of invisible.
10. **Give templates the provenance treatment the data tables already have.** A
    `ReactionTemplate` could carry the confidence of each of its parameters —
    barrier sourced, A-factor order-of-magnitude — so a generated report can state
    "this timescale is not predictive" without a human remembering to.

### Tier 3 — engineering

11. **Fix `filter_into`'s retention before building anything on top of it.** The
    diagnosis in `NEXT_SESSION.md` is correct and the fix is small; the cost of
    deferring is that every purity number produced in the meantime has to be
    re-measured anyway.
12. **Consider an analytic Jacobian for the reaction block before considering
    Rust.** `num_jac` costs 3n+1 extra RHS evaluations per Jacobian, and the
    reaction contribution is `delta.T @ diag(...) @ ...` — cheap to write in
    closed form. The benchmark already showed the γ kernel is flat from 4 to 25
    species, i.e. dominated by numpy dispatch overhead rather than arithmetic, so
    a language port addresses the wrong term. Sparsity reuse for single vessels
    and caching the UNIFAC group assembly are in the same category: larger
    multipliers than a rewrite, at no cost in language boundary.
13. **Plumb `losses` through `VesselSpec`** and decide whether `Vessel.reset()`
    should clear cumulative holdup records. Small, but the engine layer silently
    lagging the vessel layer is how divergence starts.
14. **A single documented entry point for "run an experiment".** Seven examples
    each assemble a network, a provider stack and a vessel by hand. A thin recipe
    API over `World` would consolidate them and give the eventual frontend
    something to call.

### Tier 4 — the decision that is actually blocking

15. **Write down whether this is a game or an engine.** They imply different next
    years, and the project is currently accumulating engine depth that a game
    would not need while deferring the content and the loop that a game requires.
    - *If a game*: the smallest honest slice is one scripted prep, a text UI over
      `World`, a score (yield × purity), and one failure the player can cause —
      leave the flask open, get the aldehyde. Every physical piece of that exists
      today. What is missing is a goal.
    - *If an engine or a paper*: package it, write the methods document, and
      publish. It is competitive with academic tooling in its niche, and the niche
      is unoccupied.

    Either answer is fine. Not answering is what costs.

---

## Summary judgement

This is unusually good work — more carefully reasoned than most research code,
with a documentation culture around *mistakes already paid for* that I rarely see
at any scale. The architecture has survived several changes that would have
broken a weaker one, and the one model that genuinely violated the founding
design principle (UNIFAC) was accommodated by moving the boundary rather than
abandoning it, which is the right response and the rare one.

The threat is not technical difficulty. It is that the engine keeps getting
deeper while the chemistry it can actually perform stays at five templates and
one preparation. The next marginal hour is worth more in `reactions/library.py`
than anywhere in the RHS — followed closely by ten minutes spent on `git init`.
