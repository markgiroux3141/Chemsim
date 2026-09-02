## S1 — A gas-CONSUMING surface reaction  ✅ **DONE 2026-08-25 — and it is NOT the third `PHASE_INDEX` entry the brief asked for**

The other half of M6's dichotomy, and the wrong answer it fixes is one a player
could see: **a flask with no iron in it made ammonia.** Not a numbered milestone —
it is what M6 measured its way to, and it was picked over M7 because it corrects
a visible answer rather than adding coverage.

**Done:** a flask with no iron makes **exactly 0.0** mol of ammonia; one with iron
makes 31.7% of theoretical in 600 s at 700 K; `sphalerite-roasting` runs to 78.3%
in 1800 s of blown air and conserves zinc to **1e-12**.

### ⚠⚠ THE BRIEF ASKED FOR ONE MECHANISM AND MEASUREMENT SAYS IT IS TWO

The brief said: add `PHASE_INDEX["solid"] = 2`, and note that a solid catalyst and
a roasting sulfide are "both `nu` on the solid block, so this may be one
mechanism". Both halves of that are refuted, and by arithmetic done before the
code:

| | a solid CATALYST | ROASTING |
|---|---|---|
| example | `N2 + 3 H2 <=> 2 NH3` over iron | `2 ZnS + 3 O2 -> 2 ZnO + 2 SO2` |
| stoichiometry | **zero on both sides** — `delta` never leaves the gas block | spans the gas AND solid blocks |
| thermodynamics | the ideal-gas basis; the catalyst's activity is 1 | the SOLID basis — its reactant is a lattice |
| so it is | a factor in `order`, and nothing else | a TERM, `SurfaceArrays` |

⚠ **AND THE PHASE LABEL IS NOT FREE, WHICH IS THE MEASUREMENT.**
`reaction_deltas` applies the pure-liquid standard-state shift to any phase that
is not `"gas"`. So calling a solid-catalysed gas reaction `"solid"` moves it onto
the wrong standard state:

| | dH / kJ/mol | dG / kJ/mol | K(500 K) |
|---|---:|---:|---:|
| `phase="gas"` | -91.880 | -32.820 | 2.683e+03 |
| `phase="solid"` | -114.769 | -132.542 | 7.019e+13 |
| shift | **-22.889** | **-99.722** | **x 2.616e+10** |

That is verbatim the failure the `PHASE_INDEX` comment was written to prevent —
"`phase='any'` validated, documented, and silently meant liquid" — arriving at the
line that comment is written on. **A solid-catalysed gas reaction IS a gas-phase
reaction**: every participant that has an activity is a gas.

And roasting cannot take the label either, for an independent reason:
`thermochemistry` REFUSES a lattice SMILES by name (`mineral_data`'s 407x
verdict), so a roasting row cannot be priced on the ideal-gas basis the kernel's
reverse derivation lives on. It needs `mineral_data` against a curated gas — the
subtraction `solid_state` argues is legal exactly here — so it is a curated table.

**`PHASE_INDEX` therefore still has two entries, for the second milestone
running, and for a different reason each time.** M6's was *the kernel cannot
express this rate law*. This one is *the label would change the thermodynamics*.

### THE TWO PIECES

**1. `ReactionTemplate.solid_catalyst`** — one extra `(r, n)` exponent matrix,
`KineticArrays.order_solid`, on a species' AMOUNT in mol rather than its
concentration. Five templates declare one by default: iron for `ammonia_synthesis`,
copper for both methanol rows, nickel for both hydrogenations. `catalyst=None`
reproduces the folded behaviour exactly.

* the catalyst is added to the network **whether or not anyone charges it**, so
  "put iron in the flask" is a runtime action and a player can add it mid-run;
* `A` is divided by `SOLID_CATALYST_REFERENCE` = **0.1 mol** (5.6 g of iron), the
  twin of `library.CATALYST_REFERENCE` in a different unit. `A_cat * 0.1 == A_folded`
  **exactly**, so `examples/named_routes.py` still reads **76.3%** ammonia at 700 K;
* the residual at that charge is **the volume the crystal displaces** and nothing
  else — measured, because the first guess was wrong. A VENTED comparison shows
  +0.086% and is not a comparison at all; sealed, with the flask enlarged by
  0.1 x 0.007096 L, the two agree to **-4.6e-11 mol**;
* it gates BOTH arrows, so it cannot move an equilibrium — detailed balance's
  identity survives an identical factor on each side.

**2. `SurfaceArrays` + `properties/surface.py`** — the roasting term.

    rate = k(T) * prod(nS ** order_solid) * prod(C_gas ** order_gas)     mol/s

⚠ **THE BASIS IS MIXED AND THE RATE IS NOT SCALED BY A VOLUME**, which is the one
thing this had to get right. A solid's *concentration* has no referent (the block
is an inventory in mol and `V_S` is nominal); a gas's *amount* is not what a
surface sees (arrival goes with the collision rate, so compressing the flask must
speed it up). So the rate is EXTENSIVE in the solid and INTENSIVE in the gas — and
one boolean, `PhaseArrays.lattice`, chooses both each species' basis and which
block its stoichiometry lands in, because a lattice is the only species here whose
block is unambiguous.

### FIVE MECHANICS NOBODY WROTE

| | measured |
|---|---|
| a sealed roast STALLS | **1.53%** in 20 ks. A litre of air holds 2.296 mmol of O2 and 0.1 mol of ore needs 150 — so "blow air through it" is an open end, not a rule, and it is the same shape as M6's kiln needing its CO2 swept |
| a blown roast GOES | **78.26%** in 1800 s at 1100 K, zinc closure 0.100000000000 |
| **autothermal roasting** | insulate the same flask and it reaches **100%** while heating itself from 1100 K to **1908.6 K**. A real zinc roaster burns no fuel; -882.7 kJ/mol is why. The VENT is what stops the runaway — gas leaving at T carries the heat out, which is what an off-gas duct does |
| two ores share one blast | 0.05 ZnS + 0.05 PbS -> **0.039131 mol each** of zincite and litharge, both closures exact to 1e-12 |
| the clock ignores the charge | first order in the solid, so `tau = 1/(k C_gas)`. A bigger bed is more throughput, not a longer roast |

### ⚠ FORWARD ONLY, AND THAT IS TWO MEASUREMENTS

A surface row may not be reversible and `price` refuses one that would need to be:

* **mass action on a solid AMOUNT reaches the wrong equilibrium** — M6's own
  measurement, `p/K = n_A/n_B` at 3.0863 against 3.0863, inherited exactly by any
  reversible row with non-zero solid stoichiometry. Not re-derived;
* **and the rows that exist have no observable reverse.** `ln K` at each row's own
  run temperature is **+67.6 to +78.8**; `LN_K_IRREVERSIBLE` is +20 and the
  tightest row (covellite) clears it by **20.7 decades**.

⚠ So `dG` is used ONCE, at pricing time, to justify dropping the reverse — and
then never again. And `Ea` is DECLARED here where M6 DERIVES it, which is the
whole asymmetry between the two: `max(dH, 0)` is ZERO for a reaction this
exothermic, i.e. a roast as fast as oxygen can arrive, which is not a roaster.

### ⚠ THE SHARED CLOCK IS A CLAIM, AND IT IS PARTLY REFUTED — STATED, NOT HIDDEN

M6's lesson is that a constant shared between rows claims they are the same event.
`ROASTING_A` = 3.21e6 L/(mol s) (**3.2e-5** of the collision limit, so it is a
rate and not a knob) and `ROASTING_EA` = 150 kJ/mol are shared, the claim being
that an O2 molecule arriving at a sulfide surface is one event. It holds
structurally and fails on temperature: the catalog's own equipment column puts
cinnabar in a **900 K** retort and sphalerite in an **1100 K** roaster, and one
clock makes cinnabar **31x slower** at its own temperature (56,358 s against
1,800 s).

⚠⚠ **AND THE ONE AVAILABLE FIX IS MEASURED GETTING THE ORDERING BACKWARDS.**
Evans-Polanyi is this project's only mechanism for intra-family rate differences,
and per two formula units of sulfide the enthalpies run **sphalerite -882.7,
galena -830.9, covellite -802.1, cinnabar -658.9** — so it would make sphalerite
the fastest and cinnabar the slowest, which is the reverse of the furnaces. The
overall enthalpy is not the barrier of the rate-determining step; what orders
these rows is the metal-sulfur bond and this project has no table for it. `alpha`
is zero and the ordering is NOT claimed.

### COVERAGE, AND A FALSE CREDIT THAT FORCED A RE-LABEL

**33/215 classes** (was 32/214) and **27/173 template-ready routes** (was 26). ⚠ **S3 then took this to 35/218 and left the routes at 27 -- see §S3.**

⚠⚠ **CREDITING `roasting` AS M6 LABELLED IT PRODUCED A FALSE CREDIT.**
`mercury-from-cinnabar` reads `mercury-sulfide + oxygen -> mercury +
sulfur-dioxide`, and this term makes the OXIDE — HgO decomposes at roasting heat,
which is exactly why the row is written that way. On the unsplit label that route
moved into the template-ready list on the strength of a mechanism that does not
make its product: the `deprotonation` mistake M1 named, from the other direction.
M6 had already recorded the reading ("one template will not cover that row
honestly") without acting on it. The row is now `roasting-to-metal`, uncovered.

⚠ **AND THE ONE ROUTE THIS ADDS TO THE TEMPLATE-READY LIST IS `pyrite-roasting`,
WHICH DOES NOT RUN** — pyrite has `Hfs` in WEBBOOK and `S0s` in nothing, so
`mineral_data` refuses it under the same-database rule. That is not a broken
number, it is what template-readiness MEANS (species-readiness is the other
column). The honest summary: **+1 class, +1 template-ready route, and ZERO new
routes that run end to end**, because all three smelting routes are still blocked
at `carbothermic-reduction` / `gas-solid-reduction`.

### THE DATA: three metals, and a free exact check on each

`mineral_data` gains **iron, nickel and copper** — 40 entries. A metal is a
lattice with no dissolved form, so `ions` is EMPTY and that emptiness is the
claim: `build_precipitation_arrays` now skips an ion-less record, because "every
ion is present" is VACUOUSLY TRUE of an empty tuple and iron filings would
otherwise be offered to `solubility_product` as a lattice whose only ion is itself.

⚠ **All three come out at `Hf = Gf = 0.0` EXACTLY**, and that is a check rather
than a datum — the same free, exact check `element_data` is built on, arriving on
the solid basis. `Gf` is derived through the same entropy subtraction every
mineral row uses, which for a metal subtracts the row's own entropy from itself. A
non-zero result would prove an allotrope mismatch, which is the failure CRC's
grey-tin row is refused for, and the generator REFUSES on it.

### ⚠ WHAT IS NOT MODELLED, AND ONE LATENT UNITS ISSUE

* **the site balance.** A real surface saturates; this one does not. **Ten times
  the catalyst is ten times the rate, for ever** — measured as an initial rate to
  1e-9. Right at low coverage, wrong at high, and stated rather than approximated.
  (A yield ratio after a finite run reads 9.75, and that 2.5% is depletion.)
* **⚠ `detailed_balance`'s rate cap compares a catalysed pre-exponential against a
  limit that is not in its units.** A declared catalyst puts an order-1 factor in
  MOL into the rate law, so `A` carries an extra `mol^-1` and 1e11 L/(mol s) is
  not a bound on it. `validation/rate_ceiling.apparent_A` multiplies by
  `SOLID_CATALYST_REFERENCE` to undo exactly that and the audit is restored to its
  baseline (`ammonia_synthesis_rev` crosses at **1335.1 K**, unmoved);
  `detailed_balance` does not, so it would fire **10x too eagerly**. Bounded in the
  class this project forgives — the cap scales BOTH pre-exponentials so K is
  invariant, and the cost is a clock at most 10x slow — and **it does not fire on
  any of the five catalysed templates**, which a test now pins. Fixing it properly
  wants the reference charge as an argument, not a Layer-2 import cycle.
* **`mercury-from-cinnabar`'s second step.** `cinnabar-roasting` gives
  montroydite; the metal needs mercury as a species and a decomposition row. That
  would be a genuinely EMERGENT two-step, like M6's carbonation.

**Still here, unchanged:** the zero-Jacobian-column fragility (a catalyst does not
trip it — its column is populated even at zero amount, and its ROW is what is
zero), and the default-tolerance issue. Every number above is at rtol 1e-8 /
atol 1e-11, and on a sealed roast the tight run is again the FASTER one — 3.67 s
against 19.94 s.

⚠⚠ **AND THAT SPEEDUP DOES NOT GENERALISE, WHICH THE AUDIT BELOW MEASURED.** It
is a property of a stiff vent fed by slow chemistry, not of tightening. Swept
across 11 examples the tight run is faster in **2** and slower in **9**, worst
**7.2x**.

---
