## M6 — Solid-phase reactions  ✅ **DONE 2026-08-25 — as a TERM, not a third phase, and the choice was measured**

`CaCO3(s) -> CaO(s) + CO2(g)` runs, conserves matter, carries its own energy, and
has an example (`examples/lime_cycle.py`). 31 tests in `tests/test_solid_state.py`.
**Two declarations cover three catalog steps**, because the second and third are
the first two run backwards.

### ⚠⚠ THE HEADLINE: `PHASE_INDEX` DID NOT GAIN AN ENTRY, AND THAT IS THE ANSWER

M6's brief asked whether a solid-phase reaction is a third `PHASE_INDEX` entry or
a second term. **It is a term, and mass action was built first and measured
wrong.** A pure solid has UNIT ACTIVITY, so a pair of crystals fixes the gas
pressure above them at `K(T)` however much of each is present. Written as mass
action on the solid amounts, a sealed kiln settles at

    p / K  =  n(calcite) / n(quicklime)

**exactly — 3.0863 against 3.0863 at 1100 K, 1.2139 against 1.2139 at 1200 K,
five figures on both.** That is not a loose answer, it is a different shape of
answer: real calcite either decomposes completely (`p < K`) or does not start
(`p > K`), and the mass-action form always stops partway.

⚠ **And forward-only is not a way out**, measured on a sealed 1 L flask holding
0.1 mol: equilibrium conversion is 0.12% at 900 K, 1.23% at 1000 K, 7.95% at
1100 K and 37.3% at 1200 K, where forward-only reads 100% at all four. **The lime
kiln's whole mechanic — sweep the CO2 away or it stalls — is the part
forward-only deletes.**

The form is therefore `flux = (k_f - k_r Q) * units`, with ONE `units` chosen by
the sign of the affinity rather than one per direction. `units` is a common
factor, so it divides out of `flux = 0` (amount-independent equilibrium) while an
EXHAUSTED side still stops the reaction.

### ⚠ THE REPRESENTATION WAS FORCED, AND THAT IS THE OTHER MEASUREMENT

**The lattice had to become a species.** Every other solid here sits in the solid
block ion by ion, which is what makes precipitation conserve matter by
construction. Quicklime ion by ion is `[Ca+2].[O-2]`, and **the oxide ion is in
no aqueous table anywhere** — CaO does not dissolve to Ca2+ + O2-, it hydrates.
`thermochemistry` refuses `[O-2]` on net charge and `solubility_product` already
refused quicklime for exactly this reason. So there was no ionic route to the
product of calcining limestone.

`mineral_data` therefore gained `lattice` (the canonical one-species SMILES) plus
`Cp_solid` and `Vm_solid`, both measured CRC, both from the same row as `Hf_solid`
where available: 23 of the 25 minerals have all three. **Nothing about the fusion
law verdict is softened** — a crystal may now REACT while staying a crystal, and
it still may not dissolve.

### ⚠ Ea IS DERIVED, NOT DECLARED

An endothermic decomposition whose reverse is a gas landing on an oxide surface
has no reverse barrier, which fixes `Ea = dH` — the floor `detailed_balance`
already enforces everywhere else here. Consequences, both good:

* calcite comes out at **179.2 kJ/mol** against experimental calcination
  activation energies quoted at 170–200. Nothing was fitted.
* the reverse rate constant becomes `A exp(-dS/R)`, **independent of
  temperature** (4.26e-4 1/(bar s) for the decarbonation), because the two
  exponentials cancel in closed form at setup. A cold flask full of CO2 cannot
  acquire an exploding recombination rate.

`DECOMPOSITION_A = 1e5 1/s` is the only free number and it is a CLOCK: it
multiplies the whole flux, so it divides out of the equilibrium. Measured over
two decades — the same sealed pressure to seven figures. It is pinned to a kiln
timescale (630 s at 1200 K, the temperature the catalog's own `lime-cycle` row
runs at).

### FOUR MECHANICS NOBODY WROTE

* **A kiln temperature.** Under 1 bar of air, calcite stalls at 14% at 1100 K and
  runs to 99.8% at 1150 K. The threshold is where `K(T)` crosses ambient, and it
  comes out of the CRC formation pair. `solid_state_report` solves for it.
* **A sealed tube that stalls**, per the table above.
* **Slaking** (`lime-cycle` step 2) — the dehydration row run backwards.
* **Carbonation** (`lime-cycle` step 3) — not any single row's reverse: it is the
  dehydration row forwards and the decarbonation row backwards, sharing the
  quicklime in the solid block. Measured: 0.02 mol of slaked lime under CO2 at
  700 K yields limestone through a quicklime intermediate neither declaration
  names in that role, with calcium exact to 1e-9.

### ⚠⚠ SECOND PUSH, SAME SESSION: THE CONSTANT WAS DECLARED AT THE WRONG END, AND
### A SECOND ROW IS WHAT PROVED IT

M6 shipped with `DECOMPOSITION_A = 1e5 1/s` as a declared FORWARD pre-exponential,
calibrated on the lime kiln. Adding chain 2's seed broke it immediately and
completely:

| row | dH / kJ | forward, A declared | measured |
|---|---:|---|---|
| calcite -> quicklime + CO2 | 179.2 | 630 s at 1200 K | a real kiln |
| **2 FeSO4 -> Fe2O3 + SO2 + SO3** | **340.0** | **1.7e-13 1/s at 1000 K** | **0.00% in 20,000 s at every temperature its thermodynamics allow** |

**Thirteen decades of clock error on a row whose thermodynamics were exactly
right.** With `Ea = dH`, a barrier nearly double calcite's is unreachable.

⚠ **THE MISSING PHYSICS IS THE ENTROPY OF MAKING GAS, AND FOLDING IT INTO A
CONSTANT IS THE MISTAKE.** With the transition state taken to resemble the
products — the same late-TS assumption that makes the reverse barrierless and
fixes `Ea = dH` — the forward pre-exponential is `A0 exp(dS/R)`, and what is left
over is

    k_rev = A_fwd exp(-(Ea - dH)/RT) exp(-dS/R) = A0      exactly, at every T

**so `A0` is the REVERSE constant** — the pre-exponential of ONE elementary event,
a gas molecule arriving at a crystal surface with no barrier to climb. That event
is the same event for calcite, green vitriol and baking soda, which is why one
number can cover rows that make different amounts of gas. The forward direction
is not one event: it is that one run backwards against a different amount of
gas-making entropy each time.

`RECOMBINATION_A = 4.259e-4 1/(bar s)`, unchanged in value from the first
version's calibration, so **calcination's forward constant comes back as
100000.34 against the 1e5 it was declared at — 3 ppm, and every lime number is
provably unmoved.** The four rows then land at:

| row | dH | dS | tau | at |
|---|---:|---:|---:|---:|
| calcination-decarbonation | 179.2 | 160.3 | 631 s | 1200 K |
| calcination-dehydration | 108.5 | 143.6 | 146 s | 900 K |
| sulfate-thermal-decomposition | 340.0 | 377.6 | 25 s | 1000 K |
| bicarbonate-thermal-decomposition | 135.6 | 334.4 | 44 s | 450 K |

**Three of those four are timescales nothing was calibrated against** — a red-hot
retort of green vitriol in half a minute, and baking soda in the catalog's own
`calciner, 450 K` in under a minute. They came out right because the entropy
stopped hiding in the constant. ⚠ The one number that DID move is the
dehydration row's clock, 7.4x slower; its equilibrium is untouched.

### ⚠ TWELVE MINERALS, AND CHAIN 2's SEED WAS NEVER AN ENGINE PROBLEM

`mineral_data` is now **37 entries**. Every candidate tried priced on the existing
rule except one, and the two new rows are:

* **`2 FeSO4(s) -> Fe2O3(s) + SO2(g) + SO3(g)`** — chain 2's seed, recorded as
  blocked on the engine since M6 was written. **It was blocked on ONE MINERAL.**
  Goes to completion at 1000 K in ~300 s, ending at `p(SO2) = p(SO3) = 0.5066 bar`
  — the two gases sharing the ambient total exactly.
* **`2 NaHCO3(s) -> Na2CO3(s) + CO2(g) + H2O(g)`** — `solvay-process` step 3, and
  why a cake rises.

⚠ **AND THE CATALOG'S OWN ROW NAMES A PRODUCT THAT IS NOT THE REACTION.**
`vitriol-distillation` step 1 reads `iron-ii-sulfate -> iron-ii-OXIDE +
sulfur-trioxide`, which balances and is not what happens: FeO does not survive red
heat. The declaration is the chemistry (hematite, with half the sulfur reduced) and
the row is recorded as a simplification. ⚠ **FeO is refused by the curation rule
anyway, on the half nobody would guess** — its formation pair shares WEBBOOK, and
**CRC tabulates no crystal heat capacity for it at all**, so the refusal that stops
the wrong reaction being built is the BOOKKEEPING one. The five roasting oxides and
four more sulfides are curated too, which closes the DATA half of `roasting`'s
refusal and leaves it waiting on one clearly-named engine feature.

### ⚠ A TWO-GAS ROW CHANGES WHAT "HOT ENOUGH" MEANS

A row evolving `n` moles of gas has `K` in `bar^n`, so comparing it against a
pressure is a units error the moment `n > 1`.
`SolidStateArrays.threshold_temperature` solves `K(T) = (P_ambient / n)^n` instead
— the reference state where the evolved gases are the whole atmosphere and share
the ambient total. **For `n = 1` that is exactly `K = P_ambient`, so no lime number
moves**; for green vitriol it is 874 K against the 918 K where `K` reaches
1 bar^2, because two gases sharing one bar is 0.25 bar^2 and not 1.

### ⚠⚠ AND THE DEFAULT SOLVER TOLERANCE IS NOT CONVERGED FOR A VENTED KILN

Found while re-measuring the gate, and it corrects a row this session had already
written down. On the 1100 K swept kiln:

| rtol / atol | converted | p(CO2) / bar |
|---|---:|---:|
| 1e-6 / 1e-9 (**the default**) | 39.04% | 0.0000 |
| 1e-8 / 1e-11 | **13.97%** | **0.7275** = K(1100 K) exactly |
| 1e-10 / 1e-13 | 13.97% | 0.7275 |

It CONVERGES, which is what says the loose reading is an artefact and not a
different physical answer, and **the tight runs are also FASTER** (1.4–3.3 s
against 5–13 s) because the loose solver was thrashing. The cause is the vent:
`k_vent` is 1e3 mol/(bar s), so the gas balance is far stiffer than the chemistry
feeding it. ⚠ **It is not this milestone's term** — the same 36% appears with the
solid-state term as the network's only reaction, and converges to the same 13.97%.
Any slow source feeding this vent is exposed to it.

The corrected gate, converged:

| T / K | K(T) / bar | vs 1.013 | converted | p(CO2) |
|---:|---:|---|---:|---:|
| 1000 | 0.1026 | below | 1.30% | 0.1026 |
| 1073 | 0.4444 | below | 6.54% | 0.4443 |
| 1100 | 0.7275 | below | 13.97% | 0.7275 |
| **1119** | **1.0146** | **the threshold** | 43.53% | 0.9949 |
| 1150 | 1.7052 | ABOVE | 99.75% | 1.0132 |
| 1200 | 3.7231 | ABOVE | 100.00% | 1.0132 |

⚠ **AND IT SHARPENS WHAT THE GATE IS.** Below the threshold an open flask's CO2
sits at **exactly K(T)** — it is not swept anywhere, because a vent only pushes
gas out when the TOTAL exceeds ambient and the air makes up the rest. **"Sweep the
kiln" needs a carrier FLOW (`Vessel.ingress`), not an open door.** Above it, CO2
alone would exceed ambient, so it pushes the air out and the reaction runs to
completion. One comparison, `K(T)` against `P_ambient`, and both branches fall out
of it.

### ⚠ AND THE COVERAGE ACCOUNTING COST TWO MORE CLASS SPLITS — 26 ROUTES NOW

Regenerated at HEAD: **26 / 173 routes template-ready** (was 25) and **32 / 214
classes** (was 29 / 212). `lime-cycle` is now COMPLETE end to end from limestone,
and it is the first entry in the report's template-ready list.

Getting there needed M5's standard spent twice more, and both times the answer
was **split rather than refuse**, on the `catalytic-hydrogenation` precedent:

| was | rows | became | why |
|---|---:|---|---|
| `hydration` | 3 | `lime-slaking` (2) + `carbonyl-hydration` (1) | two are `CaO + H2O -> Ca(OH)2`; the third is CHLORAL HYDRATE, a gem-diol on a carbonyl |
| `carbonation` | 2 | `solid-carbonation` (1) + `basic-carbonate-precipitation` (1) | setting mortar is a solid-state reaction; the white-lead stack is a metathesis in solution |

⚠⚠ **AND THIS IS THE FIRST TIME A CLASS HAS BEEN CREDITED TO A MECHANISM THAT
EMERGED RATHER THAN BEING WRITTEN.** `lime-slaking` is the dehydration row run
backwards. `solid-carbonation` is not any single row's reverse — it is the
dehydration row forwards and the decarbonation row backwards, sharing the
quicklime in the solid block. **Two declarations, three credited mechanisms.**

### ⚠ M5's STANDARD, SPENT AGAIN — AND IT COST A CATALOG ROW

`calcination` **is two mechanisms** and both are built: decarbonation (calcite ->
quicklime + CO2) and dehydration. ⚠ **But the dehydration built is NOT the
catalog's own row.** Bayer's `Al(OH)3 -> Al2O3 + H2O` needs two minerals
`mineral_data` does not have; `Ca(OH)2 -> CaO + H2O` is the same mechanism on
species that already price. **The mechanism is covered honestly and the row is
not claimed** — `data/catalog` still scores it uncovered, which is the point of
having a standard.

`roasting` stays refused, and the refusal now has two independent halves:

* **data** — all five rows are `metal sulfide + O2 -> metal oxide + SO2`; of the
  five sulfides only ZnS prices and **none of the five oxides does**.
* **⚠ mechanism** — roasting CONSUMES a gas, and the affinity form is measurably
  not a rate law for that: `p_O2 -> 0` puts the pressure in the denominator of Q
  and drives the reverse flux to **2.6e15 formula units per second**. A gas
  reactant is REFUSED where the arrays are built, with that reason.

**So the third `PHASE_INDEX` entry is still wanted — by a different mechanism
than the one M6 built.** A gas-consuming surface reaction IS mass action: first
order in a gas pressure, gated on a solid being present. That is also what the
five heterogeneous templates need (`alkene_hydrogenation`, `nitro_hydrogenation`,
`ammonia_synthesis`, both methanol rows), so **"a flask with no iron in it makes
ammonia" is NOT fixed by M6** and now has a clear shape.

### ⚠ dCp = 0, AND THE CORRECTION WAS BUILT AND REJECTED

Same discipline as `PrecipitationArrays.ln_Ksp`. The cost is stated: the 1 bar
decomposition temperature comes out at 1118.2 K for calcite (literature ~1170)
and 755.2 K for slaked lime (~785), so kilns run 30–50 K cool. A `dCp(T)`
correction from the CRC `Cps` values moves calcite to 1107.7 K (**worse by 10 K**)
and slaked lime to 774.9 K (better by 20). One improves and one degrades, which
is the signature of a half-applied correction — a mineral's `Cp_solid` is a 298 K
constant while a gas `Cp` here is a real cubic. A half-correction that helps one
row and hurts another is worse than a stated omission.

### ⚠ ONE LATENT FRAGILITY FOUND, PRE-EXISTING, REPORTED NOT FIXED

A species that is in the network but **absent from a flask with no vent, no
liquid and no reaction** has an identically zero Jacobian column — verbatim the
`num_jac` trap `LAYER_REABSORB` documents. Measured, sealed at 1100 K, with and
without N2/O2 in the species list:

| charge / mol | lean network | N2/O2 present but absent |
|---:|---:|---|
| 0.05 | `p/K - 1` = -1.7e-07 | **RAISED**: CO2 reached -2.572 mol |
| 0.1 | +3.5e-09 | -2.6e-11 |
| 0.4 | -5.4e-13 | +1.6e-07 |
| 1.0 | +2.6e-08 | +1.9e-11 |

The hair trigger on the charge is the signature of a NaN Jacobian, not of a
physical instability. **It does not return a wrong number** —
`check_raw_solution` raises "a failed integration wearing a success flag" — so it
is a latent fragility, and M6 made a pre-existing one reachable rather than
introducing it. Note what it is NOT: the lean column is exact at
`units_f/units_r` up to 129.5, so **the term's own sign switch handles a 130x
derivative jump at its own operating point without trouble.**

**Still here, and unchanged:** the lead chamber's missing fourth step
(nitrosylsulfuric acid, chamber crystals), and the green-vitriol seed — `FeSO4 ->
Fe2O3 + SO3` still needs an Fe2O3 mineral entry, and SO3 on the product side
makes it a decomposition the term can run the day that entry exists.

---
