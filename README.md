# chemsim

An **emergent chemistry simulation engine**. The design goal: outcomes — yields,
side products, sensitivity to temperature and contamination — *emerge* from
integrating a reaction network, rather than being scripted. Molecules are graphs,
reactions are graph-rewrite **templates**, and the system's time-evolution is
**computed**, not looked up in a recipe table.

## The core idea

The real design axis is not "recipes vs. quantum mechanics." It's **where you draw
the line between what you parameterize and what you compute**:

- Parameterize the *reactions and molecular properties* (templates + kinetics +
  thermochemistry).
- Compute the *system's evolution* (concentrations, temperature, phases).

That line gives emergence at a tractable cost. A few hundred well-constrained
reaction templates generate an effectively unbounded space of concrete reactions,
so we never enumerate a combinatorial product dictionary. **Selectivity is
controlled by template specificity, which is where the curation effort goes.**

## Architecture

Strict downward dependencies. Two inversion boundaries keep the parts that matter
swappable.

```
Layer 7  ui/           A window over the engine: worker thread, chunked ops, snapshots            [done]
Layer 6  engine/       Headless deterministic stepper: world state, step(dt), save/load, events   [done]
Layer 5  vessel/       3 phases, VLE + Henry + solubility, energy balance, pressure, pH            [done]
Layer 4  numerics/     RHS builders, ODE integrators, activity coefficients ◄── the Rust/PyO3 seam  [done]
Layer 4.5 discovery/   Rate-based network refinement (needs a simulator, so it sits above one)     [done]
Layer 3  network/      Discover concrete reactions; derive reverse kinetics -> numeric arrays       [done]
Layer 2  reactions/    ReactionTemplate (SMARTS graph rewrite) + kinetics + reaction thermo        [done]
Layer 1  properties/   Thermochemistry, volatility, condensed-phase — estimated + curated          [done]
Layer 0  matter/       Molecular graphs, canonical identity   ◄── RDKit hidden here                [done]
```

**Boundary 1 — `matter` hides RDKit.** Nothing above Layer 0 imports rdkit. The
cheminformatics backend (parsing, canonicalization, substructure matching,
template application) is swappable.

**Boundary 2 — `numerics` sees only arrays.** The hot integration loop consumes
`KineticArrays` and `PhaseArrays` (numpy + species names) and knows nothing about
molecules. This is the clean swap point for a Rust/PyO3 kernel if/when profiling
demands it — and critically, cheminformatics happens at *setup* time, never inside
the loop. The same discipline applies to property *models*: Antoine, Lee-Kesler,
Rackett and Rowlinson-Bondi are all evaluated and fitted to plain polynomial
coefficients during assembly, so the kernel evaluates one polynomial form and has
never heard of any of them.

**The one exception, and why it is not a leak.** Activity coefficients depend on
*composition*, and composition is the state vector — so unlike every other
property they cannot be fitted in advance. The setup/hot-loop split moves rather
than breaks: what is precomputed is the UNIFAC *parameter* block (group counts,
size/surface parameters, the interaction matrix, all expanded to a dense subgroup
basis at assembly time), and what runs per step is the evaluation. Layer 4 still
receives nothing but numpy. The arrays are simply richer and the loop finally
does real work.

## Language & performance

Python now, with discipline — not as a throwaway. The hot loop's cost scales with
the number of species/reactions in a vessel (small, stiff ODE system; milliseconds
in SciPy's C solvers), **not** with the number of molecules. Python only becomes a
bottleneck for spatial gradients, large auto-generated networks, or many
simultaneous vessels — and for those, the `numerics` boundary lets us drop a Rust
kernel in surgically, with nothing above it changing. Defer Rust until real numbers
justify it.

## Quickstart

```bash
python -m pip install -e ".[dev,viz]"   # runtime + test oracle (thermo) + plotting
python -m chemsim.ui                    # THE WINDOW. Add prep/boil/ester to open on one
python -m pytest -q                     # conservation, identity, Joback cross-checks
python examples/esterification.py       # graph -> template -> network -> equilibrium
python examples/thermochemistry.py      # properties + equilibrium from structure alone
python examples/vessel.py               # boiling, boiling dry, self-heating, distillation
python examples/workshop.py             # crystallisation, melting, pH/titration, the engine
python examples/activity.py             # azeotropes and real solubilities, from UNIFAC
python examples/named_routes.py         # 17 named historical routes, integrated end to end
python examples/mercury_retort.py       # a route that EMERGES from two declarations
```

## The interface

`python -m chemsim.ui` opens a Tkinter window over a `World`: glassware, the
selected vessel's temperature / pressure / pH / phase volumes / per-phase
composition, the engine's own reports, and the recipe as it accumulates. Four
worked starting points, including the benzoic-acid preparation.

**The hard part of a frontend here is not layout.** Cost is concentrated in stiff
transients rather than in elapsed simulated time — an idle flask does an hour in
0.00 s, a boiling plateau does 1200 s in 0.73 s, and ten seconds of an acid quench
costs 40 s — so the expensive moments are exactly the ones somebody is watching and
an operation must never be a blocking call. Hence: one worker thread owns the
`World` and nothing else touches it, every command goes through one queue in
submission order, and the only shared object is an immutable snapshot published by
a single assignment. There is no lock around the engine at all.

**Chunking is part of the recipe, not a rendering trick.** A long step runs as a
sequence of short ones so a thermometer climbs rather than teleports, and because
freezing the layer permittivity made the caller's `dt` weakly load-bearing, that
changes the answer slightly — so `World.script` records the chunks that were run
and a replay reproduces what was seen. A chopped `wait_until` is still a scipy
root, so chopping costs resolution nowhere.

`chemsim/ui/session.py` is the half that can be wrong and has no widgets in it;
`tests/test_ui.py` drives it and never opens a window.

## Unit conventions

Internal SI-ish: concentration mol/L, temperature K, energy J/mol, time s. Units
live only at domain boundaries; the numeric core uses bare floats.

## Status

Layers 0–6 complete; 275 tests. A Fischer-esterification *template* (not a
hand-written
reaction) is applied to SMILES starting materials; the network builder discovers
the concrete reaction and canonicalizes products; the integrator runs it to
equilibrium — with element and charge conservation enforced by tests. The same
template generalizes to any acid+alcohol with zero extra code.

Layer 1 adds Joback group-contribution thermochemistry: properties (ΔHf, ΔGf,
Cp(T), Tb, Tc, Pc, Vc) are estimated from molecular structure, with a curated
experimental table overriding species Joback can't handle (water, O2, …) and
provenance tracked on every value. The group table and fragmentation are
cross-checked against the `thermo` library across many molecules in the test
suite.

**Reverse rates are now derived, not declared.** A template specifies *forward*
kinetics only; at network-build time the reverse Arrhenius pair falls out of
detailed balance, k_f / k_r = K(T):

```
A_rev  = A_fwd · exp(−ΔS/R)
Ea_rev = Ea_fwd − ΔH
```

Because that result is itself Arrhenius, the reverse enters the network as an
ordinary reaction and Layer 4 stays a mass-action integrator that has no concept
of reversibility. The esterification equilibrium is therefore fully derived, and
a closed reactor integrates to exactly that quotient from either direction. A
declared barrier below the reaction's endothermicity is raised to the
thermodynamic floor (Ea_rev ≥ 0) with a printed notice.

**The standard state is the liquid, not the ideal gas.** Group-contribution
thermochemistry describes an isolated molecule at 1 bar; nearly every reaction
here runs in solution. Using the gas numbers unmodified is the claim that
solvation is free — the same class of error ideal Raoult made about vapour
pressure. Each species is moved across by the vapour pressure we already have:

```
ΔGf(liquid) = ΔGf(gas) + RT·ln(Psat/P°)
ΔHf(liquid) = ΔHf(gas) − ΔHvap
```

with ΔHvap taken from the *same* Antoine curve by Clausius–Clapeyron, so both
halves come from one correlation and the entropy derived from them is real
(water 44.1 vs 44.0 measured, ethanol 42.7 vs 42.3, acetone 31.6 vs 31.0). For
Fischer esterification that is a factor of 2.4: **K(298 K) goes from 19.4 to
8.1**, against a measured ~4. What remains is group-contribution error in the
formation data itself, which is a separate and known limitation.

A dissolved gas takes the same expression with its Henry constant in place of
Psat — one formula, two standard states. Species too involatile to trust (ions,
and anything whose extrapolated Psat falls below 10⁻¹² bar) keep the basis their
data was derived on, and say so.

The subtle part is pH. Ion formation data is back-derived from measured pKa
*against the acid*, so the anchor has to be taken in the same standard state. It
is — and pure water still reads 7.00, half-neutralised acetic acid still reads
4.76 exactly.

**Δn ≠ 0 is now exact at every temperature.** The activity→molarity conversion
carries a factor `T^Δn`, which is not Arrhenius. It used to be folded into `A_rev`
at one reference temperature, leaving K to drift as `(T/T_ref)^Δn`. It now lives
in the temperature exponent of a modified Arrhenius form:

```
k = A · T^n · exp(−Ea/RT),        n_rev = n_fwd + Δn
```

`n` is zero for every declared rate — detailed balance is the only thing that
sets it — so the common case stays pure Arrhenius and the kernel skips the
exponent entirely when no reaction needs one.

## Rates that respond to thermochemistry

Everything above derives *thermodynamics* from structure. Rates were the
exception: one template handed the same barrier to every substrate it matched, so
which of two competing products formed faster was an author's choice rather than
a prediction. A template can now declare an Evans–Polanyi transfer coefficient:

```
Ea_i = Ea + α·ΔH_i
```

so a more exothermic member of the same family is faster. One esterification
template over three alcohols, with α = 0.5:

| alcohol | ΔH (kJ/mol) | Ea (J/mol) |
|---|---|---|
| isopropanol | −10.94 | 44 532 |
| methanol | −9.96 | 45 018 |
| ethanol | −8.69 | 45 655 |

With α = 0 (the default) all three get 50 000, which is the old behaviour
exactly. The reverse direction needs nothing extra: detailed balance gives
`Ea_rev = Ea − (1−α)·ΔH`, which is the Evans–Polanyi relation for the reverse
with transfer coefficient `1−α`. It is still an empirical relation with a fitted
α — it is just no longer a free parameter per substrate.

## Layer 5 — the flask works out its own temperature

The vessel solves composition, phase and temperature as **one stiff system**:

```
y = [ n_liquid (n) | n_gas (n) | n_solid (n) | T ]
```

Moles rather than concentrations, deliberately — concentration needs a volume,
and the liquid volume is itself a state variable that shrinks as things boil off
or crystallise out. Moles stay meaningful when the flask boils dry.

Property models are resolved to arrays *at setup*, so the hot loop stays pure
numpy. Vapour pressure (Antoine, or Lee-Kesler fitted to Antoine form) and
Henry's-law gas solubility collapse to **one** functional form and one array, so
Raoult and Henry are the same line of code. Liquid molar volume (Rackett) and
liquid heat capacity (Rowlinson-Bondi) are sampled and fitted to cubics. Every
value carries provenance, and curated experimental data overrides an estimate
wherever the correlation is known to fail.

What this buys is behaviour nobody wrote down:

| Observed | Why it happens |
|---|---|
| Ethanol pins at **351.46 K** under a hotplate | Evaporation runs away when Σp reaches ambient; latent heat absorbs the input. There is no boiling point in the code. |
| Boil-off rate = (Q − losses) / ΔHvap | Falls out of the energy balance, and is asserted in the tests |
| A flask boiled dry **superheats** | The plateau lasts exactly as long as there is liquid, not one second longer |
| An insulated exotherm gets **less** product | Self-heating raises T, which lowers K via detailed balance — Le Chatelier from a heat-transfer coefficient |
| 50/50 ethanol/water → **71%** ethanol vapour | Raoult alone; distillation with no separation model |
| Air-saturated water holds **0.28 mM** O₂ | Henry's law through the same array as Raoult (real value ≈ 0.27 mM) |

A sealed vessel conserves every element across *all three* phases — the Layer 3
guardrail, extended to matter moving between phases.

```bash
python examples/vessel.py     # boiling, boiling dry, self-heating, distillation
```

## Layer 6 — the headless stepper

`World` owns vessels and a clock. `step(dt)` is one of the two driving calls: a
real-time frontend calls it per frame, a batch experiment calls it in a loop, a
test calls it once. Player actions are **timestamped events** — the only thing
that may mutate a vessel — and they fire strictly between integrations, so an
outcome can never depend on the solver's adaptive step size.

The other driving call is **`wait_until`**, and it is what makes a recipe a recipe.
A real procedure has no durations in it — "heat until it refluxes", "cool until
crystals appear", "distil until the pot reaches 110 °C" — and every one of those is
a **root of a function of the state**, located by `solve_ivp` to solver tolerance,
so the instant is *discovered* rather than declared:

```python
out = w.wait_until("pot", boils(), timeout=7200.0)
out = w.wait_until("beaker", crystals("OC(=O)c1ccccc1"), timeout=14400.0)
out = w.wait_until("head", temperature_steady(0.01), timeout=3600.0)
out.elapsed        # how long it ACTUALLY took -- the clock moves by this, not the timeout
```

Three of those conditions had to be written differently than they read, and
[`validation/wait_conditions.py`](validation/wait_conditions.py) is why: `dT/dt → 0`
is approached **asymptotically** and never crossed, so "the temperature stabilised"
is a *tolerance* and not an equality; and `nS` starts at exactly zero and *leaves*
it, so "crystals appear" is a micromole rather than a zero-crossing inside the
solver's own atol.

A save stores the **scenario** (templates as SMARTS text, feed species, vessel
config), the **script** (everything ever asked of the world, including the
conditions waited on — never the instants they resolved to), and moles and
temperature — never the discovered network, which is rebuilt deterministically on
load. So a run is a pure function of (scenario, script), and `World.replay` re-runs
one from its recipe alone. Saves are small, readable JSON, and no RDKit object is
ever serialised. The format is version-stamped and refuses an incompatible reader
rather than mis-mapping fields.

## Three phases, ions, and gas-phase reaction

The vessel state is now `[n_liquid | n_gas | n_solid | T]`.

**Solids.** One equation covers both dissolution and melting:

```
ln(x_sat) = −(ΔHfus/R)(1/T − 1/Tm)
```

At `T = Tm` the right-hand side is zero, so `x_sat = 1` — the solid becomes fully
miscible with its own melt. That is why there is no separate melting model, and
why melting shows a latent-heat plateau for the same reason boiling does. ΔHfus
and Tm come from Joback group contributions.

**Ions and pH.** There is no pH solver. Dissociation is entered as ordinary
reversible reactions — `HA + H₂O ⇌ A⁻ + H₃O⁺` — so detailed balance supplies
every Ka and the stiff integrator resolves the fast equilibrium. Writing it with
water on both sides makes Δn = 0, which cancels the standard-state conversion
exactly. Ion formation data is back-derived from measured pKa against *this
project's* water entry, so the two unit systems never have to be reconciled.
The charge-balance check that Layer 3 has enforced since the beginning finally
earns its keep.

| Result | Value | Reference |
|---|---|---|
| Pure water | pH 7.00 | 7.00 |
| 0.1 M acetic acid | pH 2.89 | 2.88 (Henderson–Hasselbalch) |
| Half-neutralised | pH 4.76 | = pKa, exactly |
| Equivalence point | pH 8.88 | basic, as acetate is a weak base |
| 0.05 M H₂SO₄ | pH 1.24 | ~1.1, with correct HSO₄⁻/SO₄²⁻ split |

**Gas-phase reaction.** A template declares `phase="gas"` and its rate is computed
from headspace concentrations, which is what makes Haber/Ostwald-style chemistry
expressible at all.

## Bounded discovery

Structural expansion enumerates every reachable species. For a polymerising feed
— a diacid and a diol — that is an unbounded oligomer series: correct chemistry,
fatal computation. Two changes fix it:

- **Incremental expansion.** Only combinations involving a newly-added species are
  tried; re-running old pairs every round was quadratic waste.
- **`max_molar_mass`.** An explicit bound, with everything dropped named in the
  log — and a diagnosis that a growing series usually means the system polymerises,
  which species enumeration cannot represent properly.

The polyester case went from 24 s and a silent truncation to 0.04 s with an
explicit report. `chemsim.discovery` additionally refines a network by *simulating*
it and keeping only species that carry real flux; it sits at Layer 4.5 because
that needs an integrator, and Layer 3 must not import Layer 4.

## Activity coefficients — the liquid stops being ideal

Raoult's law quietly asserts that a molecule cannot tell what it is surrounded
by. Two things followed from that, wrong in the same direction: distillation
always ran to a pure product, and a solid dissolved as readily in a solvent it
hates as in one it loves. One model (UNIFAC) fixes both, because both were the
same missing term.

```
Raoult:      p_eq,i = x_i · γ_i · Psat_i
Solubility:  ln(x_sat · γ) = −(ΔHfus/R)(1/T − 1/Tm)
```

Group assignment reuses the Joback machinery exactly — one greedy,
priority-ordered SMARTS matcher with formula verification, two group tables.
Every R, Q and interaction parameter is cross-checked against the `thermo`
oracle in the test suite, and group assignments are checked against published
decompositions.

| Observed | Reference |
|---|---|
| Ethanol/water **azeotrope at x = 0.888** (95.3 wt%), boiling at **351.17 K** | 0.894 / 95.6 wt%, 351.3 K |
| …and it boils **below both** pure components (351.45 / 372.45 K) | minimum-boiling, as observed |
| Benzoic acid in water, 298 K: **3.26 g/L** | 3.44 g/L — ideal law gives 1128 g/L |

There is no azeotrope table and no solubility table. The azeotrope is simply the
composition where y = x, and it exists because γ bends the equilibrium line
across the diagonal.

**Two things that are stated rather than assumed.** A species with no group
decomposition (ions — UNIFAC is a non-electrolyte model, and there is no
Debye–Hückel term here) is held at γ = 1 and *named* in
`vessel.activity_model.report()`. So is any main-group pair missing from the
published matrix — roughly half of them are, and zero is the strong claim that
two groups mix athermally, not a synonym for "unknown".

### Two reference states, one expression

A condensable species uses the **symmetric** convention: γ → 1 as the liquid
becomes pure in it. A dissolved gas cannot — it has no pure liquid at these
temperatures — so it uses the **unsymmetric** convention, referenced to infinite
dilution in the solvent its Henry constant was measured in:

```
γ*ᵢ = γᵢ(x) / γᵢ^∞(reference solvent)
```

That division is what transfers a measured constant to a different solvent,
because the solute's (hypothetical) pure-liquid fugacity cancels out of the
ratio: `H(S)/H(ref) = γ^∞(S)/γ^∞(ref)`. In water the correction is 1 by
construction and the calibrated number comes back untouched; anywhere else it is
computed. Standard UNIFAC has no group for a permanent gas, so the group table
carries PSRK's gas extension — added as main groups UNIFAC *doesn't have*, so no
existing parameter is overwritten and every validated result above is unchanged
to the last digit.

The divisor depends only on temperature, so it collapses to four numbers at
setup like everything else. It is fitted in 1/T rather than T — it is a ratio of
Boltzmann factors, so van 't Hoff is the right basis, and it fits an order of
magnitude better there (0.15% vs 2.5% for N₂).

| O₂ under air, 298 K | chemsim | measured |
|---|---|---|
| water (the reference solvent) | **0.27 mM** | 0.27 |
| methanol | 1.55 mM | 2.10 |
| ethanol | 1.57 mM | 2.10 |
| benzene | 1.44 mM | 1.80 |
| n-hexane | 2.41 mM | 3.10 |

Every one of those used to return water's 0.27 mM.

**Melting and dissolution finally separate.** They had shared one equation, which
was right for melting and badly wrong for dissolution. Written in *activity*
rather than mole fraction, the fusion law is composition-independent and still
gives a_sat = 1 exactly at Tm; dissolution then divides by γ, and melting does
not — a pure solid in equilibrium with its own melt must not care how badly some
solvent dissolves it.

**Cost.** The RHS goes from ~140 µs to ~231 µs per call (1.7×) for a 4-species
vessel. Notably the γ kernel is *flat* from 4 species to 25 (~78 → ~87 µs): at
these sizes both numbers are numpy dispatch overhead on small arrays, not
arithmetic. So this does not by itself justify the Rust seam — the case for that
rests on fixed per-call overhead, which was already there and which a Rust kernel
would collapse for the whole RHS, not just this part.

## Coverage, measured against a 1,583-compound catalog

`data/catalog/` holds a hand-authored corpus — 1,583 compounds and 173 named
synthetic routes (377 steps), from the lime cycle and Tyrian purple through the
lead chamber and Leblanc to the Hock process, SOHIO ammoxidation and PLA. It is
data only; nothing in `src/chemsim` imports it. It exists so that *how much
chemistry does this cover* can be run rather than guessed:

```
python tools/catalog.py                # structural validation
python tools/build_route_index.py      # feedstocks -> intermediates -> products
python validation/catalog_coverage.py  # the audit
```

| | |
|---|---|
| formation half measured or Benson | **740 / 1583 (47%)** |
| ... of which priced as a LATTICE, on the solid basis | 30 |
| formation half falls back to Joback | 399 (25%) |
| refused | 444 (28%), of which ~166 are charged organics the Born model correctly declines |
| UNIFAC-decomposable (can enter an LLE) | 828 (52%) |
| routes species-ready | **77 / 173** (was 49) |
| reaction classes with a template | **50 / 229** (was 12) |
| routes template-ready | 40 / 173 (was 7) |
| ⚠⚠ **routes template-ready AND species-ready — the one to quote** | **30 / 173** |

⚠⚠ **40 IS NOT WHAT COULD RUN; 30 IS.** The three readiness columns answer
INDEPENDENT questions and the smallest does not bound the others: a route needs a
template for every step **and** a price for every species. **10 of the 40
template-ready routes have a refused species** — `pyrite-roasting`, `tnt-route`,
`superphosphate` and seven more. Nothing computed the intersection until S6.
⚠ And 30 is an **upper bound on what runs**, not a measured count: a class is
credited when a template would fire on the right substrate at all, and
`pyrite-roasting` is the standing proof that this is not the same as running.

⚠⚠ **S9 MOVED THE INTERSECTION BY +4 — ALL THREE SMELTING ROUTES AND THERMITE —
FOR ~15 LINES OF ENGINE.** S8 had named "a REVERSIBLE solid-gas term" as the most
valuable unscoped item in the plan, blocking the work queue's only +2. It turned
out to be one algebraic rearrangement of a term that already existed: writing the
affinity's gas quotient as its two ONE-SIDED products, `k_f P_react - k_r P_prod`
instead of `k_f - k_r Q`, so nothing is ever divided by a pressure that can reach
zero. Same root, so the same equilibrium; the five pre-S9 rows are BIT-IDENTICAL.
⚠ And **half the reason recorded beside that refusal was about mass action, a
form this term never used.** The class count's denominator moved too, because
`carbothermic-reduction` was one label over four mechanisms.

⚠ **THE REFUSED COLUMN WENT UP IN S7 AND THAT WAS THE POINT.** Nine catalog
compounds are dot-separated NEUTRAL mixtures — a rubber marker, a nylon salt,
"water gas" — and the guard only refused a multi-fragment SMILES when a fragment
was CHARGED. Joback prices `CC(C)=CC.S1SSSSSSS1` **222.11 kJ/mol above the sum
of its own two parts**; in an ideal gas that sum is an identity, not an estimate.
It cost two species-ready routes and no route in the BOTH column.

⚠⚠ **AND `species-ready` MOVED 63 → 77 IN S8 FOR ZERO MOVEMENT ON THE
INTERSECTION, WHICH WAS PREDICTED BEFORE IT WAS DONE.** 15 routes were blocked
only by a bare element symbol — the refusal being right, since the ideal-gas
record for `[C]` is the carbon ATOM at Gf +671 kJ/mol while the charcoal in the
flask is 0. Nine element solids were curated into `mineral_data` on the SOLID
basis, exactly as S1 did for iron, nickel and copper, and **not one of the 15 is
template-ready**, so the number a route is judged on did not move at all. ⚠ What
it did move is the SHAPE of the queue: six classes went from 0 runnable routes to
1 and one went from 1 to 2, so the element work is a **multiplier on template
work** rather than a headline of its own. That is the whole finding, and
NEXT_PROMPT had called it "the cheapest item here" for two sessions.

⚠⚠ **AND S10 TOOK ONE OF THE NINE BACK OUT, FOR +0 ON ALL FOUR COLUMNS — ALSO
PREDICTED.** `zinc` is no longer a `mineral_data` lattice. It has a monatomic
vapour, ONE condensed form and a measured sublimation curve, so it passes every
test S4 admitted mercury on and belongs in `element_data` — where, unlike a
lattice, **it can boil**. S8's curation was right for what it was for; what
changed is that *a lattice may react and may never boil* turned out to be a
statement about the ENTRY and not about the metal. `zinc-smelting`'s retort
evolves zinc VAPOUR now and condenses it in a cool receiver at 1180.15 K, which
is a real Belgian retort's actual mechanic — and **no engine code changed at
all.** Eight of the nine remain. See MILESTONES.md §S10.

⚠ **`species-ready` moved 49 → 65 in S6 without one new datum being curated**:
the audit was asking only the three ideal-gas providers, which refuse an ionic
lattice by name — correctly, since the fusion law is the engine's only route
from a solid into solution and it is measured wrong for a lattice by up to 407x
in *both* directions. But refusing to **dissolve** a species is not refusing to
**price** it, and `mineral_data` has priced these on the solid basis since M3.
19 compounds moved refused → `mineral` and 16 routes with them, including
`lime-cycle`, which M6 declared complete end to end and whose example runs.
`template-ready` is untouched — but it moved the INTERSECTION from 12 to 17, which
is where curating a species pays and where the template count cannot reach.

⚠⚠ **M8 ADDED ELECTRICITY AS A REAGENT, AND ITS OWN HEADLINE CLASS DID NOT
SURVIVE THE ROW CHECK.** A template declares how many electrons cross the
external circuit; `build_network(cell_potential=...)` says what the supply is
set to; `n F E` joules come off the reaction's Gibbs energy, and a reaction whose
chemistry costs less than the cell supplies runs. The threshold is the
**decomposition potential** and nothing declares it — 1.441 V for water against
a book 1.229, 2.362 V for brine against 2.186, out of formation data alone.
⚠ But `electrolysis` is the greedy curve's top row at +3 routes, and its four
rows are THREE mechanisms: aqueous (built), molten-salt (a melt is not a phase
here) and amalgam (a marker with no graph). Split on M1's standard, the top row
is worth **+1**. The other +2 came from `electro-organic-coupling`, whose two
rows are both built. **+3 template-ready and +3 runnable, from a curve that
promised +3 from one class.**

⚠⚠ **S7 TOOK FOUR INORGANIC GAS PROCESSES — AND MEASURED THE QUEUE'S TOP TWO
ROWS AT ZERO FIRST.** `water-gas-shift`, `steam-reforming`, the Deacon process
and the Claus process: five templates, `+4` on the intersection, every one of
them charged into a real vessel by `validation/gas_processes.py`. What they buy
is behaviour nobody declared — the shift peaking at 620 K and falling away above
it, the reformer inert until 900 K, Deacon's ceiling and rate crossing near
650 K, and a Claus flask recovering 100.0% of its sulfur at exactly the
stoichiometric air rate because burning a third of the feed is what leaves the
2:1 ratio the second template wants.
⚠ They were chosen because the two classes at the top of the RUNNABLE queue
measured **zero honest routes**: `isomerisation`'s three rows are three
mechanisms and each fails its own way (a cis/trans pair the estimators price at
dH = dG = **0.000 exactly**; a glucose/fructose row priced at K = 4.8e-08 because
the corpus spells one as a pyranose and the other as a furanose; an ionic pair
that is not species-ready), and both `crosslinking` rows produce something with
no chemistry behind it. **So RUNNABLE has the fault ALONE had:** it asks whether
a species resolves, not whether the number is right, nor whether the row's
product is a graph. The second of those is now mechanised.
⚠ And S7 split `combustion` — six rows, **five mechanisms**, credited since M1 to
a template that fires on two of them. It is the first split here whose measured
effect on the headline is NEGATIVE (`match-chemistry` loses template-ready), and
that is a split doing its job.

⚠ The class denominator MOVES, because a class is a mechanism claim and reading
a class's rows sometimes splits it: 212 -> 224 over M6, S1, S3, M8 and S7. Six of
the classes gained since M5 are covered by TERMS rather than by templates —
a reaction inside a crystal, a gas arriving at one, an ionic lattice leaving
solution — and one of those, `roasting-to-metal`, is covered by **two terms
that emerge into a route neither of them declares**. The template count is 43.

**The species side is in reasonable shape and the reaction side is still the
binding one**, but M5 changed the shape of that gap rather than just its size.
Twenty new templates in `reactions/synthesis.py` took the route count from 7 to
25 — and the reason it took twenty rather than five is the finding: the gap is a
long tail with no bottleneck in it. **Before M5, 63 routes sat one class away
from 50 distinct classes; after, 56 sit one class away from 43.** Eighteen routes
cost twenty templates, and the next eighteen will cost about the same.

⚠ **Six candidate classes were REFUSED rather than credited**, on the standard
that a reaction class is a *mechanism* claim and not an outcome:
`catalytic-air-oxidation` is three mechanisms, `fermentation` is a metabolic
network, `pyrolysis` mostly acts on things with no molecular graph. A seventh,
`catalytic-hydrogenation`, was **split** into five mechanism labels instead —
because unlike the others, every one of its rows *is* a clean mechanism. See
`data/catalog/README.md`.

Note also that the roles in the route index are **derived from the steps, not
declared**: a species consumed but never produced is a primary feedstock, one
both produced and consumed is an intermediate. A declared split would drift
silently the first time a step was edited. See `data/catalog/README.md`.

## Known limitations

Deliberate, and each has a clear route:

- **Group-contribution formation data is the dominant error in K now.** With the
  standard state fixed, Fischer esterification sits at 8.1 against a measured ~4;
  Joback ΔGf carries several kJ/mol of uncertainty, which is a factor of 2–4 in K.
  A second estimator (Benson) or curated ΔGf is the route.
- **Equilibrium is on a concentration basis, not an activity basis.** γ corrects
  phase equilibria and solubility but not the reaction quotient, so a strongly
  non-ideal mixture equilibrates to the wrong quotient. Fixing it means rates on
  activities, which redefines every rate constant's units — a distinct project.
- **UNIFAC understates how fast an associating solute's solubility climbs with
  temperature.** Benzoic acid in water is 0.95× the measured value at 298 K but
  0.48× at 333 K. The absolute scale is fixed; the slope is not.
- **No electrolyte activity model.** Ions sit at γ = 1, so ionic strength does
  not affect anything. Debye–Hückel or an extension of UNIFAC would be the fix.
- **Gas solubility is transferred, not measured.** Only the aqueous constants are
  experimental; every other solvent is predicted through γ^∞, and runs ~25% low
  for the solvents above and 2.6× high for acetone.
- **Carbon monoxide's reference state fits poorly** (3.6% against 0.15% for O₂).
  PSRK's parameters for it are strongly quadratic in T. Reported by
  `activity_model.report()` rather than absorbed.
- **The gas extension mixes two regressions.** Organic pairs are UNIFAC-VLE, gas
  pairs are PSRK. Sound because PSRK's organic backbone *is* UNIFAC's (1124 of
  1174 pairs bit-identical), but it is a join, not one self-consistent fit.
- **Joback gaps**: no anhydride, sulfoxide/sulfonyl, formamide or aryl-aldehyde
  groups, and no metals, Si, B or P. Curated data covers the common reagents;
  a second estimator (Benson) is the general fix.
- **Polymers and extended solids** need a different representation entirely —
  chain-length distributions, not graphs.
- **Rate laws are power-law mass action**, so Langmuir–Hinshelwood and
  Michaelis–Menten have nowhere to live yet.
