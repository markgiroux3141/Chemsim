## S4 — `mercury-from-cinnabar`'s second step  ✅ **DONE 2026-08-25 — the route emerged, and the re-label did NOT get reversed**

S1 credited `roasting`, discovered it had thereby claimed a route whose product
its term does not make, split the row out as `roasting-to-metal` and left it
uncovered — naming what was missing as **"a second reaction nobody built"**. S4
built it, and it is three lines of declaration:

    properties/surface.py       2 HgS + 3 O2 -> 2 HgO + 2 SO2      SurfaceArrays
    properties/solid_state.py   2 HgO        -> 2 Hg  +   O2       SolidStateArrays
    ------------------------------------------------------------
    what a retort does            HgS +   O2 ->   Hg  +   SO2      NOBODY WROTE THIS

**Measured on a sealed 10 L retort of pure oxygen holding 0.02 mol of cinnabar
at 900 K: 0.020000000000 mol of mercury and 0.020000000000 mol of SO2, on
0.020000 mol of oxygen consumed.** That is `mercury-from-cinnabar` step 1
coefficient for coefficient, out of a 2:3:2:2 and a 2:2:1 that do not mention
each other. Coverage **35/218 → 36/218 classes, 97 → 98 steps, 27 → 28
template-ready routes** — and unlike S1's `pyrite-roasting`, this one RUNS.

`examples/mercury_retort.py`, six panels, **4 s**. 14 tests in
`tests/test_mercury_retort.py`, **4 s**. ⚠ **The whole suite is 815 passed in
11:50** — the first measured green number since S1's last fix, which left it at
796 passed / 1 failed and was never re-run. **The tolerance audit was re-run
after the engine change and S2's finding is unmoved** — no example prints a
quotable digit that moves, and all three self-check examples come out OUTPUT
IDENTICAL.

### ⚠⚠ THE BRIEF SAID THE RE-LABEL WOULD GET REVERSED. IT WAS MEASURED BOTH WAYS AND KEPT

Folding the row back into `roasting` was the expected outcome, on the reading
that `roasting-to-metal` is an OUTCOME label and M1's standard forbids those.
Both arithmetics were run rather than argued:

| | classes | steps | template-ready routes |
|---|---|---|---|
| keep `roasting-to-metal` | **36/218** | 98 | 28/173 |
| fold back into `roasting` | 35/217 | 98 | 28/173 |

**The routes are identical, so the choice is only about what the class column
says** — and `roasting-to-metal` records a MECHANISM difference rather than an
outcome: this ore's oxide does not survive the furnace that makes it, which is
why one row needs two mechanisms where the other four need one. `solid-carbonation`
is the precedent — an emergent pair under a name of its own. Folding back would
delete the distinction S1 paid to find, in exchange for a smaller denominator.

### FOUR MECHANICS NOBODY WROTE

| | measured |
|---|---|
| the intermediate is INVISIBLE | montroydite's standing inventory is the roast's rate times its own clock — **8e-7 mol at the start, 3.4e-8 by 20 ks**, never 4e-5 of the charge. Its clock at 900 K is **0.24 s** against the roast's **5,918 s** |
| **the two clocks CROSS** | the decomposition's barrier is DERIVED at 304.4 kJ/mol and the roast's is DECLARED at 150, so cooling slows the first far faster. Equal at **611.7 K** under a bar of O2. The oxide's share of the mercury released: **2.0e-6 at 900 K, 4.3e-4 at 773, 1.9e-2 at 700, 0.341 at 650, 0.913 at 600.** Nothing gates on temperature anywhere |
| a retort CONDENSES | mercury boils at 629.8 K, so cooling the same flask to 400 K puts **97.9%** of the metal in the liquid block. That is what a retort is for, and it needed a curated vapour pressure — see below |
| and the oxide CANNOT COME BACK | cooled to 400 K, **289 K below the oxide's own threshold**, in a flask full of mercury vapour and oxygen — and no oxide forms, because there is none left to grow on |

### ⚠⚠ THE FIRST ROW WHOSE PRODUCTS ARE ALL GAS, AND IT BROKE A BOUND

`units_rev` is a minimum over the solids FORMED. Over an empty set that is
`+inf`, and the RHS multiplies it by a negative affinity.

⚠ **Measured, not predicted: a sealed 1 L retort holding 0.5 mol of montroydite
at 900 K raised `array must not contain infs or NaNs`** the instant `Q` crossed
`K` — which it does at that charge because `ln K` is only **+9.2** there. At
0.05 mol in the same flask `Q` never reaches `K` and the run is clean, **so the
failure had a CHARGE threshold as well as a temperature one, and the small
charge is the one an example would have been written with.**

**Infinity was the wrong bound, not a bound needing softening**, and the four
existing rows say what the right one is: calcination's reverse is bounded by
`n(CaO)` — the SEED — and not by the CO2 pressure, which lives in `Q`. This
engine cannot nucleate a solid from nothing (S3 named that gap), so a row with
no solid product deposits onto its own REACTANT crystal. Two consequences, both
wanted: `units` stays a COMMON FACTOR so the equilibrium is still `Q = K` (the
sealed 0.5 mol run now stalls at **71.8%** with Q and K agreeing to 0.05%), and
an exhausted charge stops the reaction in BOTH directions — which is the
nucleation gap stated rather than worked around. **The four pre-S4 rows are
bit-for-bit unmoved**, pinned by a test.

A declaration with NO crystal on either side — the one case neither fallback can
bound — is now refused at `price`, naming the kinetics kernel as its home.

### ⚠⚠ MERCURY: A METAL IN `element_data`, AND BOTH REFUSALS WERE ABOUT REPRESENTATION

`[Hg]` was refused twice over: as "a metallic lattice" in `LATTICE_ELEMENTS`, and
as a bare monatomic symbol whose "ideal-gas record is the ATOM, not the
substance". Both are true of the bonding and false of the representation:

* **mercury's reference state is a LIQUID with a boiling point**, which this
  engine's liquid block holds. It joins Br2 in `REFERENCE_SMILES`;
* **mercury's vapour IS the atom** — it boils monatomic at 629.8 K — so `[Hg]`'s
  ideal-gas record is exactly what is in the retort. That is what fails for
  `[C]`, `[S]` and `[Fe]`, and mercury has one condensed form so the symbol names
  it unambiguously.

The entry is **Hf +61.40, Gf +31.853 kJ/mol** — a condensed reference state, on
the same footing as bromine's +30.90/+3.08. Pinning it to zero would be the I2
bug again.

**⚠ TWO FREE EXACT CHECKS CAME WITH IT, AND ONE IS NEW TO THAT TABLE.**

1. **Cp = 5R/2 = 20.786 J/(mol K) EXACTLY, at every temperature.** A monatomic
   ideal gas has no modes to excite. Every other Cp there is a cubic fitted to a
   sampled curve with a residual to report; this one has an answer, and JANAF
   returns it to four figures.
2. **The condensed-reference-state identity closes to +0.012 kJ/mol** — CRC's
   `(Hf, S0)` pair on one side and the WebBook's Antoine curve on the other,
   which never met. **The tightest of the four**: Br2 −0.053, I2 +0.139,
   S8 +3.052 (a stated bound).

### ⚠⚠ AND LEE-KESLER HAD TO GO, WHICH THE SECOND CHECK IS WHAT CAUGHT

Every other element's vapour pressure here is Lee-Kesler from Tb/Tc/Pc. Over a
liquid METAL it reads **38.3 kPa at 523 K against CRC's 10.0 — 3.8x — while
agreeing at the boiling point to five figures, because it is ANCHORED there.**
That is the "boils at 1 atm is not an independent check" trap arriving with a
real cost: panel 3 is a condenser and would have been wrong by that factor. With
the estimated curve the cross-check residual is **+2.808 kJ/mol**; with a curated
NIST Antoine (within 2% of CRC over five decades of pressure) it is **+0.012**.

⚠ **And the curated curve would have BROKEN a stated invariant if it had just
been dropped in.** `build_element_data` differentiates `Hvap` out of the
Lee-Kesler curve precisely so the latent heat cannot disagree with the vapour
pressure — but `volatility` prefers a curated Antoine when it has one, so for
such a species that is no longer the curve the engine evaluates. The generator
now takes Clausius-Clapeyron on the CURATED curve instead: **59.444 kJ/mol
against Lee-Kesler's 57.344 and CRC's measured 59.11.** The invariant is kept
rather than traded.

### ⚠⚠ THE CURATED-SOURCE GUARD FALSELY REFUSED CRC's OWN MEASUREMENT

`solid_state.CURATED_FORMATION` and its twin in `surface` are a **PREFIX MATCH
ON A PROVENANCE STRING**, so what they actually test is how a sentence begins. A
GASEOUS element reference state says "element reference state (gaseous)" and
passes; a CONDENSED one says "Hf and S0 both from CRC via chemicals 1.5.2; Gf
DERIVED …" and was being called an ESTIMATE. `[Hg]` tripped it, **and it would
have refused a row evolving Br2, I2 or S8 identically.** Widened by one prefix;
the weakness is the mechanism rather than the list, and moving the tier into
`ThermoData` reaches every provider in Layer 1, so it is stated rather than done.

### ⚠ AND THE RATE-CEILING AUDIT COULD NOT SEE THE TABLE IT NEEDED TO

`validation/rate_ceiling.py` claims "nothing approaches the unimolecular
ceiling", which is a claim about every rate constant in the project — and its
two panels walk `net.reactions`, which `SOLID_STATE_REACTIONS` never becomes.
**A fourth panel now reads it.** The claim survives at 298 K by 26 decades on the
worst row. The hot half does not: a solid decomposition's forward constant is
`A0 exp(dS/R)` and three moles of gas is an enormous entropy, so S4's row sits at
**1.93e18 1/s and crosses 1e14 at 3710 K — inside the RHS's own 5000 K clamp**,
the first row in the project to do so. `sulfate-thermal-decomposition` crosses at
7543 K and had never been measured either. **Reported, not guarded**, on the
policy already stated: the constant multiplies both directions of an affinity
flux, so it divides out of `flux = 0` and moves a CLOCK, not an equilibrium. The
retort runs 2810 K below its own crossing.

### ⚠ WHAT IS NOT MODELLED, STATED

* **liquid mercury is 99.85% HELD IDEAL.** A metal is not a set of organic
  fragments, so it has no UNIFAC groups and its γ is DECLARED 1 — which is what
  M4 built that flag for. The visible cost is that O2 and SO2 dissolve in the
  pool on Henry constants **measured in water**, transferred through a ratio of
  activity coefficients that is 1 here: **0.14% of the SO2**, named and bounded.
* **the oxide's threshold runs ~85 K cool** — 688.7 K against CRC's ~773 — the
  same direction and the same cause (dCp = 0) as every other row in that table.
* **nucleation, still.** Now with a second face: a solid can only be deposited
  where one already is, which S4 turns from a refusal into a modelled bound.

### THE CATALOG ARTEFACTS, AND EVERY LINE OF THE DIFF IS EXPLAINED

All three regenerated. **S3's byte-stability fix held: every changed line is a
real consequence and there is no noise.** `ROUTE_INDEX.md` came out unchanged,
because no row was re-labelled. What moved:

| | |
|---|---|
| one species | **refused 466 → 465, measured 141 → 142** — mercury |
| the credit | classes **35 → 36**, steps **97 → 98**, template-ready **27 → 28** |
| the shape of the remainder | routes one class away **60 → 59**, from **46 → 45** distinct classes |
| ⚠ a route that is not this one | **`castner-kellner` became species-ready AND fully sourced** — 48 → 49 and 4 → 5. Curating one element paid somewhere nobody was looking |

### ⚠⚠ AND THE FIFTH INSTRUMENT FINDING: `species-ready` IS BLIND TO `mineral_data`

Reconciling that diff line by line turned up a column that has been understating
itself since M3. `species-ready` asks whether every species resolves under the
plain `ThermochemistryProvider` — which **REFUSES A LATTICE BY NAME**, correctly,
because the fusion law is 407x wrong for one. But a lattice has had a home since
M3: `mineral_data`, on the solid basis, which is what precipitation,
`SolidStateArrays` and `SurfaceArrays` all price from.

**Measured: 14 routes read species-UNREADY while every one of their refused
species is a mineral this project prices** — 49 of 173, where the honest number
is at most 63.

    2-ethylhexanol-route  aniline-route      copper-smelting    deacon-process
    fischer-tropsch       haber-bosch        hydrogenation-margarine
    mercury-from-cinnabar methanol-synthesis nylon66-route      phenacetin-route
    steam-reforming       vermilion-route    water-gas-shift

⚠ Two of those are `haber-bosch` and `methanol-synthesis`, where the only
"refused" species is **the solid CATALYST S1 curated so that it could be put in
the flask**. One is `lime-cycle`, which M6 declared complete end to end from
limestone and which `examples/lime_cycle.py` demonstrably runs.

⚠⚠ **It is the exact OPPOSITE shape to `pyrite-roasting`**, and having both is
what makes the pair informative: pyrite reads template-ready and does NOT run;
`mercury-from-cinnabar` reads species-unready and DOES, at 0.020000000000 mol on
a 0.02 mol charge. **Two columns, two directions of error, neither a bug in the
engine.**

⚠ **NOT FIXED HERE, DELIBERATELY.** It changes the definition of a published
column, so it owes the standing check S1's third mistake installed — predict which
routes it moves, then measure — and a full verification pass behind it. Recorded at
the line that computes it, and it is the next session's instrument job.

### ⚠⚠ S6 CLOSED IT, AND THE ANSWER IS 16 — THE 14 ABOVE IS WRONG

**Read §S6 for the correction.** The diagnosis above is right in every respect
except its size. The 14 was measured with a RAW string comparison of the
catalog's SMILES against the `by_lattice` key, and the catalog spells its salts
in a different fragment order than the canonical table. Matching canonically —
which is what `network/builder.py` does to every input SMILES before the species
list exists — gives **16**, and species-ready **49 → 65**, not 63.

⚠⚠ The two missed are `vulcanisation` and **`lime-cycle`** — and `lime-cycle` is
named in the paragraph immediately above as the headline case while being absent
from the list of fourteen ids beside it. **The number, the list and the prose
disagreed with one another.** Left standing rather than silently corrected,
because the disagreement is the finding.

---
