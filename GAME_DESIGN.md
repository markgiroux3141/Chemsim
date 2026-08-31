# The game on top of the engine: inventory, gates, and chains

⚠ **THIS IS DESIGN, NOT BUILT.** Written 2026-08-20 after the interface landed.
Everything here is either a decision to be implemented or a MEASUREMENT taken to
test whether a decision was safe. Every number in it was measured in this repo; the
commands are at the bottom. Nothing is quoted from memory.

Companion documents: `HANDOFF.md` (what exists), `NEXT_SESSION.md` (the work
order), `EQUIPMENT_PLAN.md` (glassware), `recipes.py` (the one worked prep).

---

# 1. The one decision: a stock is a COMPOSITION, not a noun

An inventory item must **not** be `(name, purity%)`. It is the full per-phase mole
vector plus a temperature — which is exactly `VesselState`, which `SAVE_VERSION 4`
already serialises. Call an item a **stock**.

Consequences, none of which need engine work:

- **Purity is DERIVED, never stored.** "92% pure" is a label computed for display.
  The moment purity becomes game state, every gate in section 2 becomes decoration.
- **Two bottles labelled "ethanol, 95%" behave differently** if one's 5% is water
  and the other's is acetaldehyde. That difference is the game.
- **Impurities are tracked individually and forever**, so a contaminant introduced
  in step 1 can ruin step 6 and the player can trace it back. A purity scalar
  destroys exactly this loop.
- **A stock carries its own recipe.** `World.script` is the provenance, so "how did
  I make this" is answerable and re-runnable — and because the script stores
  CONDITIONS rather than instants, re-running at 10x scale waits the right length
  of time. That fork was taken in the wait-until session for this.

⚠ **AND A STOCK CAN REACT IN THE BOTTLE, which nobody designed and is free.** A
stock has a temperature and a phase layout, so advancing a stored stock's clock is
an ordinary integration. Wet aspirin hydrolyses back to salicylic acid on the shelf
(the ester template, reversed, by detailed balance). Lye left open absorbs CO2.
Ether under air makes peroxides — `peroxide_over_oxidation` is already in the
library. **Shelf life is emergent from an inventory of compositions**, and a bag of
nouns cannot do it at any price.

**A stock is a STATE, not an ingredient.** Pouring a hot stock into a cold flask
matters, so "let it cool" is an operation — and one the engine charges nothing for,
because an idle vessel short-circuits to the exact constant solution.

---

# 2. A gate must be a MECHANISM, never a threshold

There is no `if purity < x: fail` anywhere in the engine and it must never acquire
one. It does not need one. Six gates already exist:

| gate | the mechanism | measured |
|---|---|---|
| **dilution** | water is a PRODUCT of a reversible template, so a dilute feed caps its own conversion by Le Chatelier | 21.6% / 49.9% / **74.7%** conversion at 50 / 12 / 3 mol water |
| **wrong substrate** | any impurity matching a template's SMARTS diverts yield; selectivity IS SMARTS specificity | one oxidation template: methanol → formaldehyde, isopropanol → acetone, *t*-BuOH refused, glycerol gives both |
| **headspace budget** | O2 is finite, so stoppering is a real lever | 4x cook time gives nowhere near 4x side product; sealed gives zero |
| **medium polarity** | Born + the ionic rate correction: an aqueous pKa does not apply in an oil | acetic acid in neat acid/alcohol is ~1e6x less dissociated — **this is why you add H2SO4** |
| **co-crystallisation** | the solubility law | washing removes small polar impurities and CANNOT remove an aromatic of similar solubility |
| **scale** | crust loss goes as V^(2/3)/V | yield 88.8 / 83.6 / 72.7 / **49.4%** across four decades |

The scale gate is the sleeper: it makes "how much do I commit?" a real decision —
testing small costs yield, going big costs raw material — and nothing told it to.

**Four impurity classes, four different cures, and the player must diagnose which:**
small and polar → wash. Co-crystallising → recrystallise. Volatile → distil.
Ionic → extract.

---

# 3. The error taxonomy, and why the snowball fear is aimed at the wrong thing

The worry: small per-step approximations accumulate until step 12 is
unrecognisable. Four error classes, and they propagate completely differently.

**(a) RATE errors — forgiven, not accumulated.** Almost every synthesis step runs
to an ATTRACTOR: equilibrium, saturation, a bubble point, a tie line. Those are
fixed points. Get a rate constant wrong by 10x and the answer is identical; only
the clock moves. It is why this project's invariants are the stable things —
half-neutralised acetic acid sits at pH 4.76 = pKa *exactly*, the azeotrope lands
at x = 0.888, ethanol pins at 351.46 K. **A contracting map does not accumulate
error, it destroys it.** Ten steps of attractors is not ten steps of error.

**(b) COMPOSITION errors — propagate exactly, but LINEARLY.** An impurity left at
2% where it should be 0.2% is physically in the bottle and goes forward at full
size. But the next separation acts on it by the same solubility law it acts on
everything else, so ten steps of a 10x-too-large impurity give a 10x-too-large
impurity, not 1e10.

**(c) THERMODYNAMIC DATA errors — the actual snowball, and it has NOTHING to do
with step count.** Gf out by 8 kJ/mol puts K out by 24x, on step 4 of 4 or step 4
of 40 alike. It does not accumulate because it does not need to. **It is already
this project's dominant error**: inconsistency between tabulated formation values
has overtaken Joback, and acetic acid with five alcohols spans 4.5 kJ/mol of
gas-phase dG_rxn where the chemistry says flat to ~1.

⚠ So the thing that makes step 12 unrecognisable is not a thousand small
approximations. **It is one bad number sitting where the chain uses it** — see
section 6, where S8 is out by ~226 kJ/mol right now. The defence is not "fewer
approximations", it is the discipline already in place: curated data, provenance
per value, two independent cross-checks, and a refusal when it cannot be priced.

**(d) TRACE AMPLIFICATION — the one class that genuinely can blow up, and it is a
design constraint rather than a numerical one.** Anything below the solver's atol
(1e-9 mol) is gone and unrecoverable. If a downstream step amplifies traces — a
nucleation seed, a catalyst poison, an autocatalytic induction — the trace had to
be RESOLVABLE when it was made. The engine has hit this twice already:
`SOLID_VISIBLE = 1e-6` and `LN_GAMMA_BORN_MAX = 12` are both resolution limits
chosen so the quantity that matters stays above atol.
**Rule: no game mechanic may depend on a quantity the solver cannot carry.**

⚠⚠ **AND THE CONVERSE, FOUND BY BUILDING CHAIN 2 AND NOW A PROPERTY RATHER
THAN A WARNING: NO CATALYTIC CYCLE MAY START FROM ZERO CATALYST.** A lead
chamber charged with SO2, water and air and **no carrier at all** used to reach
**89% yield**. It now reaches **0.00%** -- 1.6e-20 mol of NOx, eleven orders
below anything the game can see -- and the fix is `SOLID_GATE_TIME`, described
below. The rule survives its own fix, because it is what the DESIGN depends on:
the nitre is a reagent you must supply, and the cycle's 80 turnovers only mean
something because zero turnovers is reachable.

The mechanism is kept because it is the clearest example in this project of two
individually-correct halves making a wrong answer:

- **the SEED was a knee in the crystallisation term.** Dissolution was gated with
  `avail = nS/(nS + SOLID_EPS)`, SOLID_EPS = 1e-9: zero at nS = 0, but with a
  SLOPE of 1e9 there, so an EMPTY solid block carried a Jacobian diagonal of
  `k_diss * excess / eps`. Measured on the chamber, for blocks holding NOTHING:
  **-3.61e7 for NO, -3.95e7 for NO2 and H2SO4, -1.83e6 for water.** BDF overshot
  them negative and `project_non_negative` zeroed them, CREATING matter for any
  species with no positive holding to settle against.
- **the AMPLIFICATION was the chemistry, and it had no bound.** A catalytic cycle
  has no fixed gain on its catalyst -- 0.5 mmol of NOx turns over **80 times** in
  this chamber -- so a round-off-sized charge made a macroscopic amount of
  product. Measured **296x**: 1.2e-4 mol of created carrier against 3.6e-2 mol
  of acid.

⚠ **The drift was UNIVERSAL and the damage was not, and that difference is the
transferable part.** Every undersaturated species' solid block was drifting, and
the entry grew with the undersaturation -- so the most DILUTE species got the
worst of it (NO -1.21e-4 against water's -2.36e-16). But an esterification with
no alcohol charged absorbed the identical drift silently, because acetic acid's
solid block settles against its own 0.83 mol liquid holding. **The precondition
is a species near zero that is a CATALYST** -- one appearing on both sides of a
cycle -- which is why three sessions of esterification chemistry never saw it and
one afternoon of chain 2 did.

### ⚠ THE FIX, AND WHY THE OBVIOUS ONE WOULD HAVE BEEN WRONG

The liquid twin of this knee (`_layer_gates`, HANDOFF item 25) was fixed with a
SMOOTHSTEP -- zero *and flat* at zero. **That would have been the wrong move
here.** Flat at zero is `num_jac`'s other pathology: an undifferentiable column
whose perturbation factor inflates without bound, which is why the layer gate
needed `LAYER_REABSORB` as a companion with strictly disjoint gates. A companion
for the SOLID gate would have had to sit opposite the PRECIPITATION branch --
ungated by design, because anything can nucleate -- i.e. exactly the overlapping
arrangement that made the benzoic-acid acidification unsolvable.

So the rule item 25 produced is the binding one: **a state block that can sit at
exactly zero needs a derivative there that is neither enormous nor exactly zero,
and only ONE term may govern it near zero.** The gate itself had to carry that
derivative. `SOLID_GATE_TIME` makes its scale the DRIVING FORCE instead of a
constant:

    eps = SOLID_GATE_TIME * k_diss * excess        SOLID_GATE_TIME = 10 ms

which is a resistance-in-series form -- `1/rate = 1/(k_diss*excess) + tau/nS` --
so dissolution is limited BOTH by distance from saturation AND by how much solid
is present. **The empty-block slope collapses to exactly `1/tau` for every
species**, and that independence is the point: the old knee got worse the more
dilute a species was.

⚠ **The value is a measurement, not a preference.** Swept on the chamber, the
solid columns' largest entry reads 1.41e6 / 1.36e5 / 1.29e4 / 1.49e4 at
tau = 1e-4 / 1e-3 / 1e-2 / 1e-1 -- it stops shrinking at 1e-2 and 1e-1 is
slightly WORSE, so 1e-2 is the least distortion at which this gate has stopped
dominating. It moved no solubility, because `excess -> 0` drives the scale to
zero and the gate to 1.

⚠ **No local guard could have caught it, and that is structural.**
`check_raw_solution` bounds an excursion as a RATIO against the amount present,
with a 1e-3 mol floor for species legitimately at zero -- so 1.4e-7 was four
orders under the threshold and was correctly *reported* rather than refused.
Nothing looking at one integration step can see that a round-off residual is
about to be multiplied 300x downstream. It had to be fixed where it was made.

### ⚠⚠ AND THE CLASS IS NOT CLOSED: A DRYOUT BAND IS STILL LIVE

Asking what else shared `avail`'s shape found `MELT_BLEND` innocent (a clip,
slope 10) and `DRYOUT_MOLES` guilty. The sulfur burner walked into it: sulfur
boils at 717.8 K, so a burn run near that holds only a TRACE of condensate, and
if the trace lands inside `DRYOUT_MOLES` (1e-6 mol) **three** terms overlap --
layer 1's evaporation gated by `wet`, the dry-flask branch by `1 - wet`, and the
mole fractions floored on the same scale, so inside the band they **sum to less
than one** and every activity is understated. At 690 K the solve reports **111%
yield**; at 650 K and 730 K, either side, it closes to 1e-9.

⚠ **The diagnostic that makes this a wall rather than a wobble is worth more
than the measurement, and it generalises.** The same burner shows a 1.7e-4
residual at 600 K, nowhere near the band, and in one run the two are
indistinguishable. **They are told apart by REFINING:**

    600 K, round-off   atol 1e-9 1.70e-04 -> 1e-11 6.9e-12 -> 1e-14 -5.5e-14
    690 K, the BAND    atol 1e-9 1.10e-01 -> 1e-11 5.0e-09 -> 1e-14  7.4e-04

**A round-off residual CONVERGES under refinement; a structural defect does
not.** Chunking says the same: 60 chunks takes 600 K to 4.8e-10 and leaves 690 K
at 5.3e-2. It is REPORTED rather than patched -- lowering the mole-fraction floor
MOVES the band to 730-900 K instead of removing it -- and it is on `fragilities`
and not only `diagnose`, because **the solve succeeds**.

**The approximation to reach for is therefore on TIME, never on MATTER.**

---

# 4. Where the time actually goes, and the one approximation with no drift

Cost is not proportional to simulated duration — it is concentrated in stiff
transients (`validation/wall_clock.py`). Measured spread on the same machine:

| operation | wall |
|---|---|
| idle flask, 1 h | 0.00 s (no solver call at all) |
| **aqueous esterification, 2 h** | **0.2 s** |
| crystal growth, 4 h | ~5 s |
| **acid quench, 10 s** | **40 s — 4.1x slower than real time** |
| near-anhydrous acidic organic medium | REFUSED, or > 10 min |

And the reason, measured on an aqueous acid network — **stiffness ratio 7e21**:

| reaction | k at 298 K |
|---|---|
| water recombination, H3O+ + OH- → 2 H2O | **9.4e+18** |
| carboxylic acid recombination | 9.8e+07 |
| **fischer esterification — the chemistry** | **1.2e-02** |

The engine resolves a 1e-19 s timescale to compute a proton concentration.

**THE PROPOSAL: stop integrating acid/base dissociation; solve it as an equilibrium
at each step boundary.** Why it survives section 3: **the value you would get by
integrating IS the equilibrium value.** It is not an approximation of the answer,
it is skipping a transient no chemist claims to observe. The five pH invariants are
equilibrium values, so they are the regression test and must come back IDENTICAL,
not merely close.

Precedent for the move is everywhere here: the LLE phase split, the METER rate and
the frozen layer permittivity are all boundary decisions for the same reason.

⚠ **The caveat to measure before shipping it.** Where dissociation feeds a SLOW
reaction — carboxylic-acid autocatalysis, or the ionic rate correction making every
rate a function of the medium — freezing it at boundaries makes an autocatalytic
acceleration lag by one chunk. Bounded by the chunk, measurable by comparison
against the integrated version. It is also the largest single piece of engine work
on the list, so prove it on ONE step first.

⚠ **And a design consequence that is free: keep the main line AQUEOUS AND DILUTE.**
That is where the engine is fast, and it is also where the real chemistry is. A
chain designed through glacial anhydrous conditions is a chain of 40-second steps
and occasional refusals — measured, not guessed.

---

# 5. Chain catalogue

Each chain names what works TODAY, what is a data job, and what is engine work.
The programme is: build a chain, hit a wall, patch the wall, continue.

## Chain 1 — aspirin from oil of wintergreen

Chosen because its first half is the flagship prep with different species.

```
RAW (impure by nature)                    DETOURS
  wintergreen oil  ~90% methyl salicylate
  wood ash         NaOH + carbonate + grit   A  leach ash -> filter -> evaporate
  vinegar          5% acetic acid            |    gate: carbonate is a WEAK base, so
  battery acid     ~30% H2SO4  (see chain 2) |    crude lye under-hydrolyses step 1
  water, ice, air                            |
                                            B  distil vinegar -- acetic acid is the
MAIN LINE                                    |   HIGH boiler, so the POT enriches
  1  saponify the oil        <-- needs A     |
  2  acidify                                C  dehydrate acid -> acetic ANHYDRIDE
  3  filter + recrystallise                  |   gate: REVERSIBLE with water as the
       -> SALICYLIC ACID [stock]             |   product, so C REQUIRES B first
  4  acetylate  <-- needs C, + catalyst -----+
  5  quench, crystallise, filter, wash
  6  recrystallise -> ASPIRIN [stock]
```

**Steps 1-3 need no new mechanics**: same reversible ester template running
backwards under hydroxide, same acidification, crystallisation, filtration, wash.

**The forced dependency is the point.** Anhydride formation is reversible with
water as the product, so you cannot make acetic anhydride in dilute vinegar — C is
gated on B and nothing enforces it but Le Chatelier. And you NEED the anhydride
because a phenol will not esterify with acetic acid in water. That is the real
reason aspirin is made this way, and the engine arrives at it independently.

**Two end-game purity puzzles with different cures**: unreacted salicylic acid
co-crystallises (recrystallise), acetic acid and salts wash out (wash).

Coverage, measured — the chain prices:

| species | Gf kJ/mol | Tm K | source |
|---|---|---|---|
| methyl salicylate | −339.0 | 360.4 | experimental |
| salicylic acid | −378.1 | 432.1 | Joback + curated fusion (real 431.7) |
| aspirin | −526.6 | 433.1 | Joback ⚠ real Tm ~408 |
| acetic anhydride | −479.4 | 200.2 | Benson (real 200.2) |
| salicylaldehyde | −144.0 | 266.1 | Benson |
| salicylate ion | REFUSED | — | needs pKa 2.97 |

⚠ **Aspirin's formation half is Joback, so its acetylation K is the weakest number
in the chain.** If this becomes the flagship it wants a curated entry — the same
overlay job `_CURATED_FUSION` already does for four solids.

DATA JOBS: anhydride formation template; anhydride acylation template; pKa entries
for salicylate (2.97) and carbonate (6.35 / 10.33). ENGINE WORK: none.

## Chain 2 — oil of vitriol, from volcanic sulfur and a nitre bed

The answer to "where does battery acid come from". Historical, and every gas in it
is **already priced experimentally**: SO2 −300.1, SO3 −371.0, NO +86.6, NO2 +51.3,
H2SO4 −653.4, HNO3 −73.9 kJ/mol.

```
NATURE                                THE LEAD CHAMBER
  native sulfur   --burn in air-->      SO2
  saltpetre       --+ a little H2SO4--> HNO3 ---> NOx
    (nitre bed: manure + ash + time)              |
                                                  v
       SO2 + NO2 + H2O  --->  H2SO4 + NO     the core step
       NO + 1/2 O2      --->  NO2            regenerates the carrier
       -------------------------------------------------------
       net:  SO2 + 1/2 O2 + H2O -> H2SO4,  catalysed by NOx
```

Three reasons this is a better game object than the folded catalyst we have:

- **A real catalytic CYCLE, not a rate multiplier.** NO2 is consumed and NO is
  regenerated, net zero. The player can watch it turn and can LOSE it, because NO
  escapes if you vent. "Keep the chamber shut" becomes a skill, and the
  headspace-budget mechanic already exists.
- **It BOOTSTRAPS.** You need a little H2SO4 to liberate HNO3 from saltpetre, and
  the process makes H2SO4 — so the first batch needs a seed from elsewhere (green
  vitriol, dry-distilled: literally where the name comes from). A chain that has to
  prime itself is a good beat.
- **It is GAS PHASE**, so it exercises `phase="gas"` and the pressure model, and it
  is the first chain that is not a flask of liquid.

**BUILT 2026-08-20 — `examples/oil_of_vitriol.py`, `tests/test_lead_chamber.py`,
`reactions.lead_chamber()`.** Every promise above holds and the chain cost ONE
data entry (S8) and TWO templates. Measured: the cycle turns to **100.0% yield
sealed**, the carrier does **80 turnovers** on a 0.5 mmol charge, venting drops it
to **22–42%**, and the network is **7 species / 4 reactions** (two forward, two
derived reverses).

**Three things emerged that nobody wrote down:**

- **A TEMPERATURE CEILING at ~600 K.** The regeneration is written reversible, so
  above ~600 K `2 NO2 -> 2 NO + O2` takes over and the carrier sits as NO, which
  cannot oxidise SO2. At 650 K the NO/NO2 ratio has flipped by 100x and the yield
  falls to 94%. Detailed balance derived that from the formation data; there is no
  maximum operating temperature anywhere in this project. It is why a real lead
  chamber is a big cool room.
- **A NEGATIVE activation energy that is real.** `2 NO + O2 -> 2 NO2` is
  genuinely termolecular and one of the few reactions with a measured negative
  barrier (ONOONO dimer): k = 1.2e-31 exp(+530/T) cm⁶ molecule⁻² s⁻¹, which
  converts to A = 4.35e10 L²mol⁻²s⁻¹ and Ea = −4.4 kJ/mol. **Both parameters are
  SOURCED** — the only template in the library whose A is not hand-authored. So
  "run it cool" is right for two independent reasons.
- **The venting loss is NOT MONOTONE in `k_vent`** (22.4 / 23.4 / 41.7% at 1 / 10
  / 1e3), because a large conductance holds the chamber at ambient pressure so
  little net volume crosses the boundary, while a small one needs a real pressure
  difference to pass the same flux.

⚠ **THE NITRATE-LIBERATION TEMPLATE DOES NOT EXIST AND DOES NOT NEED TO.** The
asked-for template turned out to be a proton transfer the engine already does:
`NO3− + H2SO4 <=> HNO3 + HSO4−`, with both pKa values already in
`electrolyte._PAIRS` (−3.0 and −1.4), the existing `mineral_oxyacid_dissociation`
template, and detailed balance. Finding that out was worth more than writing one.
⚠ And a trap it exposed: **do not subtract provider Gf values by hand** — the
ions are anchored on the acid in its LIQUID standard state while the neutrals are
ideal-gas, so a naive difference reads −46.2 kJ where the pKa gap says −9.1.
`standard_state.reaction_shift` gets it right; a script doing its own arithmetic
does not.

⚠⚠ **THE BURNER IS THE WALL, AND IT IS MEASURED RATHER THAN OMITTED.**
`S8 + 8 O2 -> 8 SO2` has excellent thermochemistry (dG −2449.7 kJ, ln K = 988 —
a hard attractor) and a bounded network (4 species, 1 reaction, 0.45 s). What
fails is the RATE LAW, because the kernel takes mass-action exponents from
stoichiometry, so a global stoichiometry written as one elementary step is
**NINTH ORDER, eighth in O2**:

1. it cannot run with a physical pre-exponential — [O2]⁸ = 2.9e-20 at 700 K and
   atmospheric oxygen, so it needs **A = 7e24 (L/mol)⁸/s**;
2. with O2 in EXCESS the attractor holds and the wrong form is **forgiven** —
   100.0% at 550 / 700 / 900 K and at A = 1e20 and 1e24 alike, exactly as
   section 3(a) predicts;
3. **with O2 LIMITING it is not** — 86.5 / 92.8% at A = 1e20 against 96.4 / 98.0%
   at 1e24. The answer depends on a hand-authored A, because [O2]⁸ stalls
   asymptotically and the last oxygen never burns. **That corrupts the
   headspace-budget gate**, one of the six that already work;
4. forced to A = 1e26 the projection CREATES MATTER — 334.8% yield, with
   `conservation_report` naming 0.136 mol O2 and 0.047 mol S8 created.

**The fix is engine work and it is named: rate laws whose exponents are DECLARED
independently of stoichiometry.** Much cheaper than the LHHW/Michaelis-Menten
item it belongs to — no site balance, no saturation term — and this is its first
concrete case. ⚠ **The obvious workaround is blocked by the element table, and
correctly**: crack the ring first (`S8 <=> 4 S2`, real) then burn `S2 + 2 O2`
(third order, well posed), but S2 has a measured formation half and NO measured
Tb/Tc/Pc anywhere, because a diatomic that never condenses as itself has no
boiling point. Inventing two critical constants to get past that is the exact
failure `element_data` exists to prevent.

⚠ **THE SEED IS AN INPUT, and the bootstrap is honest but incomplete.** Green
vitriol is in the mineral table (Gf(s) −820.38 kJ/mol, CRC) but its dry
distillation `FeSO4 -> Fe2O3 + SO3` is a SOLID-PHASE DECOMPOSITION and this
engine has no solid-phase reactions — its solids dissolve and react in a liquid,
which a dry retort has none of. Named engine gap, not a data gap. The player still
feels the dependency.

DATA JOBS: **done** — one element (S8). ENGINE WORK: **two named gaps**, declared
rate orders (the burner) and solid-phase reactions (the seed).

## Chains to design next

Candidates that bottom out in nature and exercise something new: potash + fat →
soap (saponification of a triglyceride, and a real LLE/salting-out separation);
limestone → quicklime → slaked lime (calcination, a solid-phase decomposition the
engine cannot currently do); fermentation → wash → the AZEOTROPE WALL (distillation
stops at 95.6% and no amount of skill passes it — the best kind of puzzle);
green vitriol → dry distillation → the H2SO4 seed for chain 2.

---

# 6. THE FLOOR, AND THE CLASS OF BUG IT CLOSED

**BUILT 2026-08-20.** `properties/element_data.py` (generated by
`tools/build_element_data.py`) and `properties/mineral_data.py` (by
`tools/build_mineral_data.py`), plus a guard in `thermochemistry.get`.
Re-measured by `validation/game_gates.py` panels 4 and 4b.

"Make it from natural things" always terminates at an element or a mineral, and
that floor did not exist. What was there instead was a class of silent wrong
answer: **an estimator applied outside its domain returns a well-formed number
that means nothing.** Joback and Benson are fitted to NEUTRAL, MULTI-ELEMENT
molecules. Four instances were live in this repo:

| species | estimator said | exact / correct | error |
|---|---|---|---|
| Cl2 | Hf −74.81 | **0 by definition** | ~1e13 in K — fixed 2026-08-16, species by species |
| **F2** | **Gf −440.5** | **0 by definition** | still live; the lesson had not generalised |
| **S8** | **Gf +275.96** | **+48.68** (gaseous S8, JANAF) | e^91 in K |
| **[Cl−]** | **Gf −10.43** | **−111.73** (from HCl's pKa) | **101 kJ/mol, and two answers for one species** |

⚠ **THE FIX IS THE DOMAIN, NOT THE SPECIES.** `thermochemistry.get` now refuses
an element or an ion outright — it comes from a curated table or it is refused BY
NAME, with the refusal saying which table to add it to or which representation to
use instead. That closes the class permanently, which is what fixing Cl2 alone
did not.

⚠ **AND THE STANDARD STATE IS NOT ALWAYS THE OBVIOUS ONE — the same bug one
level up, and it was already here.** A `ThermoData` is on the IDEAL-GAS basis, so
only a species whose reference state IS the gas is exactly zero. **Br2 (a
liquid) and I2 (a solid) were pinned at 0.0** where their ideal-gas records are
+3.08 and +19.29 kJ/mol in Gf, +30.90 and +62.40 in Hf. So the species-by-species
fix for Cl2 put a 62 kJ/mol error into iodine while taking a 75 kJ/mol error out
of chlorine.

**The independent cross-check is that shifting the ideal-gas value back down into
its own phase must return zero**, and nothing in it touches the formation table —
Psat comes from Tb/Tc/Pc through Lee-Kesler and Hfus/Tm are separate
measurements:

    Gf(g) + R T ln(Psat/P_std) − Hfus(1 − T/Tm)  ==  0

Measured: **Br2 −0.05, I2 +0.14 kJ/mol.** With the old pinned zeros those
residuals would have been **−3.14 and −19.15**, so the check can reject and does.
⚠ **Sulfur is the weak row and the harness says so: +3.05 kJ/mol**, because
Lee-Kesler is extrapolated from Tb = 717.8 K down to Tr = 0.23 and liquid
sulfur's vapour is not S8 but a shifting S8/S6/S2 equilibrium. That row is a
sanity bound, not a confirmation, and **S8's vapour-pressure curve is the weakest
number in chain 2.**

The floor now reads:

| species | plain provider | electrolyte provider |
|---|---|---|
| H2, N2, O2, **F2**, Cl2 | **0.0, exactly** | same |
| **S8 (rhombic)** | **Gf +48.68**, JANAF, derived | same |
| Br2 / I2 | **+3.08 / +19.29**, CRC, derived | same |
| ozone | +163.24, CRC, derived | same |
| atomic [S], [C], graphite, metals, S2, P4 | **REFUSED, by name, with the reason** | same |
| KNO3, NaCl, KHSO4 | **REFUSED** | −79.3 / −111.7 / −704.9, ion by ion |
| CaCO3, CaO, FeSO4, K2CO3 | REFUSED (which ion, named) | same |

**No element is priced wrong and no mineral prices differently under the two
providers** — the second was the "two answers for one species" worry, and the
answer was to make the plain provider REFUSE rather than answer.

## A LATTICE IS NOT A MOLECULE, and the fusion law says so out loud

The mineral question was "does a lattice need its own entry, or is ion-by-ion
plus a lattice energy the honest form?" **Measured, and the answer is neither on
its own.** The engine's only route from a solid into solution is the
ideal-solubility fusion law, and against tabulated solubility at 298 K:

| salt | fusion law | measured | ratio |
|---|---|---|---|
| NaCl | 0.015 mol/L | 6.15 | 0.0025 — **407x too INSOLUBLE** |
| K2CO3 | 0.014 | 8.03 | 0.0017 — 585x too insoluble |
| Na2CO3 | 0.008 | 2.06 | 0.0040 — 251x too insoluble |
| KNO3 | 8.96 | 3.51 | 2.55 — **2.6x too SOLUBLE** |
| CaCO3 | 0.0015 | 0.00014 | 11.0 — 11x too soluble |

**6,445x of spread, and the sign flips.** Not a bias a factor could absorb — the
wrong law. Tm and Hfus describe lattice → MELT; dissolution is lattice →
HYDRATED IONS, and the hydration energy appears in neither. So:

- the lattice **does** get its own entry, on the solid basis, because that is
  what a solubility product or a calcination would be computed from — 13 entries,
  Gf DERIVED and agreeing with CRC's own tabulated Gf(s) to 0.03–0.25 kJ/mol on
  five of six anchors;
- but it is **REFERENCE DATA, not a provider tier**, and the refusal names the
  ion-by-ion route: *"that is calcite, an ionic lattice… charge its ions
  instead"*;
- ion-by-ion is the representation for anything DISSOLVED, and a mineral in a
  flask is dissolved.

⚠ One source disagreement worth knowing: **CRC's own K2CO3 entry is not
internally consistent.** Deriving Gf from its Hf and S0 gives −1065.3 against its
tabulated −1063.5. Five other anchors land within 0.25. That is what deriving
rather than transcribing exposes.

⚠ **Pyrite is absent and that is a source limit, not an oversight**: FeS2 has a
tabulated enthalpy (WEBBOOK) and no entropy anywhere, so its Gf cannot be
derived, and mixing two tabulations inside one entry is forbidden.

# 7. What NOT to build

- **No purity scalar in game state.** Section 1.
- **No recipe unlock list.** The network discovers species, so the recipe book is
  what the player has actually made.
- **No success/failure flag on a reaction.** The outputs are yield and composition,
  and that is the score.
- **No `if` that reads a purity and decides an outcome.** The moment one exists,
  section 2 is decoration.
- **No approximation that touches MATTER.** Section 3. Time is fair game; the
  contents of the flask are not.

---

# 8. THE SHELF, THE STOCK AND THE STEP -- the playable loop

Sections 1-7 describe what a stock IS and what must never be built. This section
is the loop that uses them, and it exists because the engine has been able to run
this for a long time and nothing has ever asked it to. `grep -r inventory src/`
returns engine internals and nothing else.

**The goal of the P-series is one sentence:** a player opens a shelf, pours two
things into a flask, does something to it, reads what came out, and puts the
result back on the shelf under a name. Everything below is in service of that
sentence and nothing else.

## 8.1 The loop, and the two verbs that are missing

`chemsim.ui` already has the hard half: a worker thread that owns the `World`, an
immutable `Snapshot` the view polls, a command queue (`Do` / `Step` /
`WaitUntil` / `Reset` / `Load`), a live recipe panel and a reports panel. What it
does not have is any notion that the player owns anything. It loads one of four
hardcoded scenarios and resets to the start.

Two verbs close the loop:

    BOTTLE   vessel -> shelf     name the current VesselState and store it
    CHARGE   shelf  -> vessel    pour a stored stock into a flask

That is the whole mechanic. Both are serialisation against a structure
`SAVE_VERSION` already writes, because **a stock is a `VesselState`** (section
1) -- a per-phase mole vector plus a temperature, not `(name, purity)`.

## 8.2 A step is ONE GENERATION, and that is not a compromise

Measured (`validation/playable_levers.py` panel 5), full template library:

    gens  charged   species  reactions  seconds
       1        5        45         36     0.63
       1       12        77         67     0.43
       2        5       400        766    12.38
       2       12       400        743     4.03

**Five ordinary bench reagents explored two generations deep hit the 400-species
cap in twelve seconds.** Twelve reagents explored one deep cost under half a
second. An open inventory is only tractable one generation at a time.

The fortunate part is that this is also the mechanic that was wanted for its own
sake: *mix two things, see what you get, then use that in the next step.* **One
generation is exactly "what can the things in this flask do, once."** The
products of that step become reactants only when the player takes another step,
which is what a bench feels like anyway.

⚠⚠ **BUT IT IS AN APPROXIMATION THAT TOUCHES MATTER, WHICH SECTION 7 FORBIDS,
AND THE RESOLUTION IS THAT IT MUST NOT BE SILENT.** If A + B makes C and C would
immediately react on to D, one generation shows C and never D. That changes the
contents of the flask, which is the one thing section 3 says may never be
approximated. It is admissible only under this project's other standing rule --
*coverage limits are never silent* -- so:

* **the unexplored frontier must be reported.** `build_network` used to break out
  of its expansion loop with a non-empty frontier and say nothing, while
  `max_species`, oversize molecules and mixed standard states all reported.
  ⚠ **CLOSED IN P1**: the limit now issues a notice naming the count and the
  species, and `ReactionNetwork.unexpanded` carries the same set as data so a
  frontend can act on it rather than parse a sentence. ⚠ And the frontier is
  taken on EITHER exit from the loop, which was P1's own correction to itself:
  the bounds compete, and at `generations=2` the species cap bites first, so
  reading the frontier only on the generation branch reported an empty one for a
  400-species network truncated mid-round. Panel 5 caught it. Against a species
  cap the set is a LOWER bound and that notice says so;
* **the player controls the bound.** A "react further" control that raises the
  generation limit turns a computational cap into a game verb. A flask that has
  more to give should say so and let the player ask for it. ⚠ P1 built the
  SAYING -- the count sits in the reports panel's heading, where it is legible
  without scrolling past possibly hundreds of notices. **The ASKING is P4**, and
  it needs `generations` to become a `Scenario` field, which it is not yet:
  `World` builds its network to a fixpoint and nothing can currently request
  one-generation play through the UI at all.

*A limit the player can see and lift is not an approximation; it is a choice.*

## 8.3 What a shelf may hold, and why it is not everything

**416 of the 1583 corpus compounds are REFUSED a price**, so an "all chemicals"
inventory tops out near **1167**. That refusal is the element floor doing its
job: group-contribution estimators are fitted to neutral, multi-element molecules
and outside that domain they return a well-formed number that means nothing
(Joback prices Cl2 at -74.81 kJ/mol where the answer is 0 by definition).

**A refused species must be visible in the picker, greyed, with its reason.** It
may not be silently absent and it may not be chargeable-then-failing. A player
who cannot find sodium metal deserves to be told that the engine declines to
price it, not left to conclude the game is broken.

## 8.4 What goes on the shelf, measured rather than chosen

`validation/playable_levers.py` panel 3. Twenty-three routes are RUNNABLE today
and merely unreachable, and they split into two kinds that are not
interchangeable:

* **19 are a CHAIN problem** -- they want a species some other route makes, and
  that route is itself stranded. 24 distinct species; granting them takes
  playable **21 -> 40**. These can eventually be EARNED, which is why the
  reduction work is deferred rather than cancelled.
* **4 are a BOTTLE problem** -- `benzaldehyde`, `malonic-acid`, `4-nitrophenol`,
  `bromoethane` are made by nothing in 173 routes. Worth only +1 together,
  because each of their routes is short of something else as well. These can only
  be bought, or the corpus grows a route for them.

Granting all 28 gives **41 of 173 playable**. ⚠ For comparison: 22 template
sessions on their own give **31** (panel 2). *The shelf is the cheapest distance
on the board by a wide margin, and it is a design decision rather than chemistry.*

## 8.5 The shelf as data, not code

Same shape as the rest of the corpus -- a PSV under `data/catalog/`, so it can be
diffed, tested and regenerated:

    # shelf.psv -- id | tier | amount | phase | note
    water            | natural      | 5.0  | liquid | -
    sulfuric-acid    | natural      | 1.0  | liquid | oil of vitriol
    benzaldehyde     | bottle       | 0.5  | liquid | nothing in the corpus makes it
    nickel           | intermediate | 0.1  | solid  | chain: made by a stranded route

Three tiers, and the tier is the whole design argument:

    natural        on the shelf because it comes out of the ground or a plant
    intermediate   on the shelf because a stranded route would make it (EARNABLE)
    bottle         on the shelf because nothing in the corpus makes it at all

⚠ **The tier is what lets the shelf shrink later.** When a session makes a
stranded route reachable, its `intermediate` rows are deleted and the player
earns them instead. Nothing about that is possible if the shelf is a flat list of
names, and it is the whole reason the tier column exists on day one.

**And an "everything" toggle is a separate axis from the tiers** -- the
all-chemicals cheat is every priced species at once, for exploration and for
testing the picker against 1167 rows. It is not a fourth tier.

## 8.6 What this section does NOT license

Section 7 already forbids a purity scalar, a recipe unlock list, a success flag
and any `if` that reads a purity. Three more that this loop makes tempting:

* **No "recipe succeeded" moment.** The answer to an experiment is a composition
  and a yield -- *71% conversion, 4% of a side product, 0.3 g left in the crust*
  -- and reading the flask IS the game. A green tick over the top of it would
  destroy the only thing this engine has that nothing else does.
* **No shelf entry that is not a real `VesselState`.** The moment a bottle is a
  noun with a number, section 1 is gone and every gate becomes decoration.
* **No silent generation limit.** Section 8.2. If the frontier is non-empty the
  player is told.

---

# Every number above, and how to re-measure it

```bash
# section 8, the shelf and the step: every number is printed by
#   validation/playable_levers.py (~2 min). Panels 3, 5 and 6 are the
#   ones section 8 quotes.
# section 2, the dilution gate: 20.9 / 48.8 / 74.1% conversion
#   0.83 mol acetic acid + 2.05 mol ethanol at 353 K, sealed under N2, 2 h,
#   varying only the water charged (50 / 12 / 3 mol). ~0.2 s each.
# section 4, the stiffness: k for every reaction in an aqueous acid network at
#   298 K, sorted. Ratio 7.05e21, top entry water_autoionization_rev at 9.43e18.
# section 5, chain 1 coverage: ThermochemistryProvider().get() on each species.
# section 6, the floor: the same, plus electrolyte_provider(), ion by ion for salts.
python validation/game_gates.py        # ALL FOUR PROBES, sections 2/4/5/6
python examples/oil_of_vitriol.py      # chain 2, end to end, and its wall
python validation/wall_clock.py        # the cost table in section 4
python validation/process_losses.py    # the scale gate (⚠ stale since `porosity`)
python examples/competing_pathways.py  # the wrong-substrate gate
python examples/multistep_prep.py      # steps 1-3 of chain 1, in another guise
```

**DONE 2026-08-20: `validation/game_gates.py` is that harness**, and every
number in sections 2, 4, 5 and 6 above now comes out of it. Two consequences of
making it one:

- ⚠ **the dilution gate moved, and only slightly: 21.6 / 49.9 / 74.7% against the
  quoted 20.9 / 48.8 / 74.1.** The inline probe's flask geometry was never
  recorded, so the harness now DEFINES the measurement rather than reproducing
  it. That is the whole argument for harnesses in one line.
- the stiffness table came back identical (ratio 7.05e21, water recombination
  9.431e18, esterification 1.157e-2), which is what a stable measurement looks
  like.
