# Milestones: from "a simulator with chains" to "a sandbox you can play"

Written 2026-08-22, after auditing `data/catalog` (1,583 compounds, 173 routes)
and probing four capability questions against the running code. Every number
below is measured, not estimated; the probes are reproducible from the snippets
named in each section.

⚠⚠⚠ **THE LIVE ARC IS THE R-SERIES ("react until done"), added 2026-08-31.
The P-SERIES IS COMPLETE (P0-P4) and the C-series is PAUSED. R1 is DONE
2026-09-01 -- an unpriceable species is the fourth REPORTED coverage limit now,
and closing the crash showed the picker's own two-row pick has FIVE unpriceable
species and zero reactions. R2 and R5 are DONE 2026-09-01 -- the BLAS cap
lives at the entry points (`chemsim.threads`, never `chemsim/__init__`) and
REACT FURTHER writes the raised bounds back into the bench boxes the next pour
reads. R3 is DONE 2026-09-01 -- `prune_threshold` is DELETED (SAVE_VERSION 9):
it could not be wired even in principle, because the pruning it promised needs
the CHARGE and a Scenario does not contain the charge. R4 and R6 are open.**
Jump to `# THE R-SERIES`
near the end of this file;
it opens with the measurement that changed the order. Everything above it is
the record of how the engine got here and remains the authority on what was
built and why.

**The one-line finding: the engine is open-ended and the content is not.** There
are no recipes anywhere in this project — templates are SMARTS rewrites applied
to whatever species are present, and `build_network` discovers reactions to a
fixpoint. A player can already mix anything. The reason most mixtures do nothing
was that the library is 10 templates against the catalog's 197 reaction
classes. ⚠ **As of M5 that reads 34 templates against 212 classes, 29 of them
covered** — the shape of the problem changed but not its direction.

---

# PART 1 — THE FOUR CAPABILITY QUESTIONS, ANSWERED BY MEASUREMENT

## 1. Can a player mix two arbitrary things and have something happen?

**Yes, mechanically — this is already the architecture.** Nothing is keyed by
recipe. Measured, with `alcohol_chemistry()` loaded and no reaction named:

| charged | reactions found | discovered |
|---|---:|---|
| ethanol + acetic acid | 4 | ethyl acetate, water, diethyl ether, ethene |
| ethanol + toluene | 2 | diethyl ether, water, ethene |
| ethanol + water | 2 | diethyl ether, ethene |
| acetone + hexane | 0 | nothing |
| toluene + water | 0 | nothing |

⚠ **And "nothing happens" is not the same as "the flask is inert."** Where no
SMARTS matches, the vessel is still a real physical mixture: VLE, LLE, mutual
solubility, dissolution, heat capacity. Toluene + water separates into two
layers and steam-distils at 358.31 K without a single reaction.

**So the honest statement is: the mechanism is fully general; the library covers
8-11 of 197 reaction classes.** That is a content problem, not a design one, and
it is what Part 2 is about.

⚠ One engineering consequence to design for: mixing two things means BUILDING A
NETWORK at charge time (0.45 s for a 4-species case, longer for a rich one). A
sandbox where the player mixes freely needs that cached and bounded, or the UI
stalls on every pour.

## 2. Does heating it change the answer? Does a catalyst?

**Heat: yes, and it is the flagship mechanic.** Same flask, same charge, nothing
declared — measured over one hour:

| T / K | ethyl acetate | diethyl ether | ethene |
|---:|---:|---:|---:|
| 320 | 1.476 | 0.000 | 0.000 |
| 400 | 1.408 | 0.023 | 0.00003 |
| 480 | 0.421 | 0.751 | 0.017 |

The barriers differ, so the branching does. Nobody wrote "if hot, make ether."

**Catalysts: yes, in two distinct forms, and both work.** A *folded* catalyst
(hydronium on both sides of one SMARTS — rate multiplier, no cycle) and a
*genuine cycle* (the lead chamber's NOx: 80.3 turnovers on a 0.5 mmol charge,
watchable and losable). The second is the interesting one and it is real.

## 3. Precipitates?

**Molecular solids: yes, and emergently.** Benzoic acid, 0.05 mol under 55 mol
water, nothing declared — cooling crystallises it out of the fusion law against
γ:

| T / K | dissolved | solid |
|---:|---:|---:|
| 330.0 | 0.050000 | 0.000000 |
| 298.1 | 0.026681 | 0.023319 |
| 275.0 | 0.012236 | 0.037764 |

Filtration, cake porosity and the crystal-crust loss are all built on top.

⚠ **Ionic precipitates: NO, and this is a missing MODEL rather than a missing
template.** `solidifies` is set only where Tm *and* Hfus *and* condensable
(`vessel.py:502`), and an ion has none of those — measured, `[Na+]` and `[Cl-]`
both read `solidifies = False`. **There is no solubility product anywhere in
`src/chemsim`.** So AgCl, BaSO₄, chrome yellow, and every "add A to B and it goes
cloudy" moment cannot happen. The catalog lists `precipitation-metathesis` at 5
steps / 5 routes, and the report files it under "no template" — it is worse than
that, and Milestone 4 is the fix.

⚠ Also absent: any **nucleation barrier or metastable zone**. Precipitation is
ungated by design ("anything can nucleate"), so a supersaturated solution crashes
out instantly. No seeding, no supersaturation, no oiling-out.

## 4. Condenser — boil a mixture and capture a cut?

**The physics: yes.** A pot, a vapour edge and a cold receiver *are* a still, and
the enrichment is real. Measured, 2 mol ethanol + 2 mol water, 300 W:

| t / s | pot T | head T | head EtOH | head H₂O | x(EtOH) |
|---:|---:|---:|---:|---:|---:|
| 200 | 302.43 | 300.62 | 0.665 | 0.351 | **0.655** |
| 600 | 303.63 | 299.57 | 1.841 | 1.139 | 0.618 |
| 1200 | 313.00 | 290.00 | 2.000 | 1.998 | **0.500** |

Reflux holds a plateau at 352.892 K indefinitely; a still finds the
ethanol/water azeotrope at x = 0.888, 351.17 K. All of that works today.

⚠ **The protocol: NO, and the last row above is why it matters.** The enrichment
*washes back out to 50%* because everything comes over eventually and there is no
way to stop and change the receiver. Fractional distillation IS taking a cut, and
the cut cannot be expressed:

* `World` — the replayable, saveable, scriptable layer — **has no rig at all.**
  Its event kinds are `CHARGE`, `SET_HEAT`, `SET_ENVIRONMENT`, `SET_VENT`,
  `SET_STIRRING`, `SET_SHAKING`, `FILL_HEADSPACE`, `TRANSFER`, `FILTER`. No
  vapour edge, no condenser, no receiver.
* There is no `SWAP_RECEIVER` verb, so **"collect the fraction boiling between
  351 and 355 K" is unsayable** — not merely unimplemented.
* `wait_until` exists and can watch a temperature, but it can only watch the
  vessel it is given, and the head is not a vessel `World` knows about.

**This is the single largest gap between "the physics is there" and "you can play
it", and it is plumbing rather than science.**

---

# PART 2 — WHAT THE CATALOG ADDS, AND THREE CORRECTIONS TO IT

`data/catalog` is a genuinely good instrument and its headline is right: the
species side is in decent shape and the reaction side is not. Three of its
numbers need correcting before planning on them.

**(a) It undercounts templates.** `TEMPLATE_CLASSES` in
`validation/catalog_coverage.py:195` only knows `reactions/library.py` and misses
the six proton-transfer templates in `properties/electrolyte.py:305`. Crediting
them: **3 → 6 template-ready routes, 21 → 46 steps covered (6% → 12%)**, with no
code written.

**(b) `acid-base` is two capabilities wearing one label.** Its 15 steps split
into proton transfer with a tabulated pKa (sodium phenoxide + HCl, salicylate
acidification, KNO₃ + H₂SO₄ — all working today) and **carbanion generation**
(malonate + ethoxide, ylides from *n*-BuLi, enolates), which needs C-H pKa values
the electrolyte table does not have. `redox` and `oxidation` have the same
problem: they are outcome labels, and a template is SMARTS on a *mechanism*.
**The taxonomy is too coarse to drive work at this granularity.**

**(c) The 50% UNIFAC headline is diluted.** Split by whether UNIFAC means
anything: **molecular organics 59%, salts/ions/elements/minerals 27%**. The real
gap is 41% of organics. Still the largest *silent* failure in the project — no
decomposition means γ = 1, which in a two-phase calculation asserts the phases do
not separate — but quote it at its true size.

## The finding the coverage report does not give: there is no lever

The report ranks missing classes by frequency, which is the wrong ranking for
deciding what to build. Ranked by **marginal unlock** instead:

* 61 routes are **one class** away — from **46 different classes**.
* The best single template unlocks **6 routes (3%)**.
* The best **twelve** templates reach **31/173 (18%)**.

And the two rankings barely overlap. The most-used classes (`acid-base`,
`catalytic-hydrogenation`, `hydrolysis`) unlock **zero** routes on their own,
because those routes each need three other things too.

| ranked by routes unlocked | ranked by steps covered |
|---|---|
| catalytic-air-oxidation (6) | acid-base (15) |
| acid-displacement (6) | catalytic-hydrogenation (10) |
| electrolysis (6) | hydrolysis (8) |
| redox (6) | deprotonation (6) |

**"Full template coverage" is a ~150-template grind with no bottleneck to
attack.** Plan for a *target* ("twenty playable routes"), never for completeness.

## What the catalog prices that was previously unranked

* **Solid-phase reactions** — `roasting` + `calcination` + `carbothermic-reduction`
  = 13 steps, ~5 routes.
* **Electrochemistry** — 4 routes outright (chlor-alkali, Downs, Hall-Héroult).
* **Polymers as distributions** — `radical-polymerisation` + `polycondensation`
  = 11 steps.

⚠ And it caught a gap in work just completed: the catalog's `lead-chamber` route
has a **fourth step we did not build** — nitrosylsulfuric acid, the "chamber
crystals" that form in a water-starved chamber. Our chain 2 is steps 1-3.

---

# PART 3 — THE MILESTONES

Ordered. Each is self-contained enough to hand to a fresh context. Each states
what "done" means as a **measurement**, because that is this project's habit and
it is what stops a milestone from being declared finished early.

---

## M0 — Close the dryout band  ✔ **DONE 2026-08-23**  *(engine)*

The one live wrong answer, and it is closed: **690 K went 1.1e-01 → 1.9e-11**
created oxygen. HANDOFF items 72 and 73 are the record.

**The fix was the CLAMP, not the gates.** `x1 = nL1 / max(N1, DRYOUT_MOLES)` put
the mole-fraction floor on the same scale as the gate multiplying it, so a flask
below that scale had x summing to 0.57 and every activity understated by that
factor. The floor is now `MOLE_FRACTION_DENOM = 1e-30` — 24 decades below the
gate — and the rule is *a clamp that exists to avoid 0/0 must not double as a
gate.*

⚠ **And the work order's own prescription — make the gates DISJOINT, as item 25
did — is WRONG here, measured.** It closes the band and breaks a condenser:
disjointness leaves a dead zone where both halves are zero, and a condenser comes
to rest exactly there. The head stalled at 9.998e-07 mol and **the reflux plateau
went 352.89 → 370.39 K.** The pair stayed complementary (`wet + dry == 1`
exactly for a single liquid). **Whether a gate pair should be disjoint or
complementary depends on whether its dead zone is survivable** — item 25's halves
oppose each other, these two are one flux written twice.

**What is left at 690 K with O2 limiting (~1e-5) is the depleted reactant, not
the band** — with O2 non-limiting the same flask reads 1.9e-11 — and **its value
at default tolerance is luck**: nudging the INERT nitrogen charge by 0.5% swings
it five orders of magnitude. So the burner's 730 K row moved from 2.0e-09 to
5.2e-06 and that is **reported as a finding**, not a regression: it was never an
invariant. The residual belongs to **M7**.

**What it hands the rest of the plan:**
* **M2 inherits a sound evaporation block** — the reflux plateau is now steady
  indefinitely rather than drifting, which is what a fractional-distillation
  protocol has to build on.
* **M3 and M6 inherit the gate-shape rule above.** A solubility product and a
  solid-phase reaction each need a "is this phase here" gate, and the question to
  ask first is now *what happens in my dead zone*, not *is it smooth*.

---

## M1 — Make the coverage instrument trustworthy  ✔ **DONE 2026-08-23**

All three parts landed. **The corrected baseline is 33/377 steps (8.8%) and
4/173 routes**, against the 46/377 and ~6 routes predicted here — and the reason
for the gap is the milestone's own finding.

**1. The instrument was miscounting in three separate ways.**
* It knew only `reactions/library.py`, missing the six dissociation templates in
  `properties/electrolyte.py`. **14 templates, not 10** — and `library.py` holds
  8, so even the 10 was wrong.
* ⚠ **Crediting the six was NOT the lookup-table edit predicted.** The 21 → 46
  arithmetic needed `deprotonation` (6 steps) to be proton transfer. **Five of
  its six rows are carbanion generation** — malonate and acetoacetate anions, a
  Wittig ylide, two enolates — exactly the capability §2(b) says has no template.
  Crediting the class would have made the audit *less* truthful, which is the
  failure this milestone exists to prevent.
* And the summary print had a variable-shadowing bug reporting **"20 compounds"
  and coverage of 5520%**. Fixed.

**2. The fix was the TAXONOMY, not a "partial" coverage level.** `acid-base`,
`redox`, `oxidation` and `deprotonation` were OUTCOME labels spanning several
mechanisms each, and a template is SMARTS on a MECHANISM. **32 rows re-labelled**
to the mechanism their own reactants and products show; the full decision table
is in `data/catalog/README.md`. Once classes are specific enough, "is there a
template" has a yes/no answer and the mapping needs no notion of partial.

⚠ It also **reconciled a contradiction in this document**: `acid-displacement`
was listed both as covered and as a top *missing* class. Both were right about
different rows — 1 of its 4 steps needs only proton transfer, and 3 need a
gypsum precipitation, i.e. **M3**.

⚠ Two rules fell out, both in the catalog README: *the class is the mechanism;
whether a reagent is priced is a SPECIES question the audit counts separately*
(so Kjeldahl's boric-acid titration is `proton-transfer` even though boron has no
oxyacid template), and *a step's NAME can lie; its reactants cannot* —
`williamson-ether`'s "alkoxide formation" reads `phenol + NaOH → phenoxide`, so
the phenol template does cover it.

**3. The marginal-unlock table is in `COVERAGE_REPORT.md`, and it revises the
numbers this document was planned against.** Splitting outcome classes into
mechanisms necessarily *lowers* per-class unlock, so:

| | this document estimated | measured after M1 |
|---|---|---|
| routes one class away | 61, from 46 classes | **64, from 50 classes** |
| best single template | 6 routes | **3 routes** (`electrolysis`, `catalytic-air-oxidation`) |
| best twelve templates | 31/173 | **30/173** |
| best twenty | — | **43/173** |

⚠ **The shape of the conclusion is unchanged and now measured: there is no
lever.** 64 routes are one class away and they want 50 different classes. Plan
for a target, never for completeness — M5's framing stands.

⚠ **A note on the greedy curve's tie-break, because it is easy to get wrong.**
Maximising "routes unlocked outright" hits zero after ~15 classes: every route
left needs two or more. A loop that stops there reports a curve that flattens
because *it* gave up. So when nothing unlocks a route alone, the next class is
the one appearing in the most remaining routes — those rows show `+0` honestly. A
template can be the right thing to build next and still unlock nothing yet.

---

## M2 — The still as a protocol  ✔ **DONE 2026-08-23**

**Both halves landed. The protocol was done first; the 0.85 heart is now met by a
plate column** — `examples/plate_column.py`, **heart 0.8544 mole fraction ethanol
from a 50/50 ethanol/water charge, 8 plates at reflux ratio 5**, and it replays
from its script to **0.000e+00**.

**The protocol** (HANDOFF 76): `Scenario.edges` (`EdgeSpec(kind, a, b, k)` over
`vapour`/`drain`/`thermal`/`meter`), `SWAP_RECEIVER`, `SET_EDGE`,
`Rig.wait_until` + `RigIntegrator.step_until`, `collect_fraction`. **`SAVE_VERSION`
4 → 5.** Three receivers each held a different mixture and the run replayed
exactly; the script carries only bands, never an instant.

**The column** (HANDOFF 77), and it needed one engine fix plus a defect found:

⚠⚠ **THE FIRST COLUMN ATTEMPT FAILED BECAUSE THE STILL HAD NO OPEN END, NOT
BECAUSE OF STARTUP — the diagnosis in this document was wrong.** Every vessel in a
still is declared `k_vent=0` and a receiver is reached only by a DRAIN, so pot +
plates + head + condenser were one **sealed** volume. Measured: **3.34 bar and the
pot at 385.9 K on two plates, 3.77 bar and 389.6 K on eight** — taller is hotter,
which is exactly why adding plates made it worse, why UNIFAC left the range its
correlations cover, and why a band chosen from atmospheric boiling points was
never entered. ⚠ And the *shipped* `fractional_distillation.py` had the same
defect: it was distilling at **3.09 bar with the pot superheating to 548 K**, so
its published cuts (0.060/0.287/0.580 mol, heart 0.523) were taken on a
pressurised trace. Both are fixed by one vent on the condenser, which is where a
real distillation is open to the room, and both examples' numbers moved.

⚠ **The engine fix: `temperature_steady` on a rig vessel was answered by the
vessel's OWN uncoupled derivative.** Every other condition reads the STATE, so
lifting it onto the rig vector by the owner's slice is exact; this one reads the
DERIVATIVE. Measured: a column pinned at 351.22 K and unmoving for 1200 s **timed
out**, and fires in 0.0 s on the coupled root. Same lesson as `step_until`'s, one
level deeper — *it is not only WHEN a condition is located that belongs to the
coupled trajectory, it is what the condition computes.*

⚠ **Two more, both measured.** **Boilup is a plate-efficiency knob, not a clock**
— the same 8 plates at R=5 plateau at **0.8538 at 250 W and 0.8486 at 500 W**, and
the two runs cost the same wall clock, so a distillation example cannot be made
cheaper by turning the mantle up. And **in a good column the head does not move**
(351.19 K ± 0.002 across the whole take-off), so the head is the wrong instrument
for closing that cut and the band goes on the POT's rising bubble point. That does
not weaken "the head is not the condenser" — it is the flip side of it.

⚠ **What it costs:** `examples/plate_column.py` is ~13 min of saturated CPU on 14
coupled vessels, half of it panel 4's replay, and the cold-start FLOOD dominates
rather than the distillation. Declaring the plates already warm changes it by 1 s
— the transient is the phase change. `tests/test_still.py` pins the mechanism at
0–2 plates for ~2 min instead.

## M3 — Ionic precipitation: a solubility product  ✔ **DONE 2026-08-23**

**All four "done when" clauses met. A metathesis precipitates: 0.01 mol of AgCl
out of AgNO₃ + NaCl in water, 1:1 to the last digit, conservation report empty,
supernatant at √Ksp — with no AgCl species, no template and no recipe anywhere.**
HANDOFF item 79 is the record.

⚠⚠ **AND THE BLOCKER THIS SECTION SPENT MOST OF ITS LENGTH ON WAS NOT REAL.**
The measurement below stands — a naive Ksp on the old tables really did return a
float for 9 of 13 minerals, 25–29 decades out with the sign flipping, because a
spectator cancels only when it appears on BOTH sides. What was wrong was the
conclusion drawn from `chemicals` returning `None`:

> "IT CANNOT COME OUT OF `chemicals` … so this is hand-curation."

**True of the FUNCTIONS, false of the PACKAGE.** `chemicals` 1.5.2 ships
`Electrolytes/CRC Thermodynamic Properties of Aqueous Ions.tsv` — 173 ions, one
compilation, `H+` at 0/0/0/0, i.e. the conventional scale stated by the table
itself — and no accessor function reads it. **A refusal from an API is not
evidence that the data is absent**, which is the mirror image of this project's
older rule that a *successful* call can be a wrong answer, and it cost this
milestone a re-plan around work that did not need doing.

**What landed:**
* **`properties/ion_data.py`** (58 ions, generated by `tools/build_ion_data.py`),
  on the conventional `Gf(H⁺,aq) = 0` basis, kept structurally separate from
  `electrolyte`'s pKa entries with a test enforcing no import either way.
  Every entry cross-checked by re-deriving `Gf` from its own `Hf` and `S(aq)`
  against the element reference states — worst residual **0.85 kJ/mol**. ⚠ The
  `(z/2)·S°(H₂)` term in that derivation is what makes it a check on the BASIS
  and not on arithmetic: drop it and a singly charged ion misses by exactly
  **T·S°(H₂)/2 = 19.48 kJ/mol**.
* **Ksp against the five solubilities `mineral_data` already carried** (entered
  long ago to condemn the fusion law): rock salt **0.99×**, potash 3.92, soda ash
  0.58, saltpetre 0.28, calcite 0.48. **Inside a factor of 4 across 4.4e4× of
  measured solubility**, nothing fitted. The stated factor is **4**, and the
  residual is γ — `solubility()` assumes infinite dilution, which is why caustic
  potash comes out at 2.2e5 mol/L and `SolubilityProduct.dilute` exists.
* **The term**: `PrecipitationArrays` + one RHS block, exactly the shape this
  section predicted. ⚠ **The solid block holds the IONS, not a lattice species**,
  which makes conservation exact by construction and creates the one limit —
  it is an ion inventory, so two lattices sharing an ion cannot be told apart.
  Bounded by `units = min nS_i/nu_i` (a lattice can only dissolve while every one
  of its ions is in the solid) and reported as latent.
* **`mineral_data` 13 → 25 lattices**; `element_data` gained 15 reference states
  and **REFUSED tin by name** — CRC's row for that CAS is grey tin (Hf = −2100
  J/mol, not zero), and an element in its reference state is zero by definition.
* **Coverage 4 → 7 template-ready routes, 33 → 41 steps**, crediting
  `precipitation-metathesis` and `acid-displacement-precipitating` to a TERM
  rather than a template.

⚠ **The prediction in `thermochemistry` that a Ksp would end the spectator zeros
DID NOT COME TRUE, and the reason is an accident of the failed first attempt.**
The term consumes Ksp as a number from two independent tables and never reads a
Gf from the provider, so the cation appears in no equilibrium the kernel
evaluates and the five pH invariants are unmoved. The licence is now *sharper*:
**a zero is safe while no consumer reads it ONCE.** Electrochemistry still breaks
it.

**Refused rather than bundled: the nucleation barrier.** Three lines of code, and
`S_crit` is a measured substance-specific width this project has no source for.
Left on the backlog, named.

**Still open here:** an ionic-strength model (Debye–Hückel) would close the factor
of 4; a lattice entry for sodium bicarbonate and Prussian blue, and an S0s for
PbCrO₄, would make three more `precipitation-metathesis` rows species-ready.

## M4 — The UNIFAC gap  ✔ **DONE 2026-08-23 — both halves, in the order the measurement put them: the flag first, the matcher second**

41% of molecular organics had no group decomposition, which silently set
γ = 1. A missing template *refuses*; this *lied*, and it lied about phase
separation — the mechanic every workup runs on. That framing stood. What the
measurement added, before anything was built, is that "the gap" was never one
problem, and the half the section led with had a hard ceiling.
`validation/unifac_gap.py` is the measurement and now also the verification; it
runs in about a minute.

**Coverage: 730 → 764 of 1155 organics, 63.2% → 66.1%.**

### ⚠⚠ The important half: silence was not a neutral default, it was an argument

`numerics/lle.py` has always said, as a virtue, that **an ideal liquid never
splits** — the tangent-plane test returns "stable" for free with no group
parameters. Put that next to "a neutral species with no decomposition is held at
γ = 1" and the omission is not noise around the right answer: **everything held
ideal argues for one phase, and the answer it argues for is exactly the one
`Vessel.lle_report()` used to return as the empty string.**

It now says so, in all three branches — including the stable-single-phase one
that used to be silent:

    this liquid is stable as one phase -- but 14.3% is NEUTRAL species with no
    UNIFAC decomposition, held at gamma = 1 rather than computed
    (O=S(=O)(O)O 0.143). An ideal liquid never splits, so that verdict is the
    one the missing model was always going to give

⚠ **And the two-layer case prints the signature of the lie beside the warning:**
water/toluene/sulfuric acid comes out with H₂SO₄ at **0.058 mole fraction in
BOTH layers**, because equality of activity with γ = 1 on both sides of an
interface is equality of MOLE FRACTION. The same failure the Born term was built
to fix for ions, still running for neutrals, now visible rather than inferable.

**The threshold was bounded arithmetically and the bound said something.**
Water/toluene 3:1 at 298.15 K and at the 358.31 K of the steam distillation,
fifteen third components each added at mole fraction `f` and the tangent-plane
test run twice — once modelled, once forced ideal:

| held ideal | displacement per unit `f` | |
|---|---:|---|
| acetone, ethers, esters, alcohols, DMSO | **0.03 – 0.25** | belongs in the MAJOR layer |
| DCM, chloroform, benzene, hexane, cyclohexane, heptane | **0.99 – 3.46** | belongs in the MINOR layer |

⚠ **The slopes do not scatter, they split in two, and the boundary is which
layer the species belongs in.** A species held ideal is not merely given the
wrong γ — `activity_coefficients` drops it out of the group composition every
OTHER species' γ is computed against, so a hydrocarbon that ought to DEFINE the
organic layer is kept out of the layer it defines.

⚠ **And there is no dead zone:** the displacement is LINEAR in `f` down to
0.0005, so there is no fraction below which the model becomes correct, only one
below which the error is too small to print. That is what makes the threshold a
REPORTING decision, stated as one: `lle_report` prints mole fractions to three
decimals, so `IDEAL_FRACTION_REPORT = 0.01 / IDEAL_TIE_LINE_SENSITIVITY =
0.01 / 3.46 = 0.003`. For scale at the other end, sweeping to `f = 0.6`, the
stable/unstable **verdict** never flipped below an ideal mole fraction of
**0.44**.

⚠ **Ions are not counted**, and `ActivityArrays.report()` now lists them
separately too. An ion at γ = 1 is a stated policy with the Born term doing the
part that decides partitioning; a neutral at γ = 1 is a gap. Running them
together made the gap look like the policy.

### The matcher half: two fixes, and the second one's safety is an ordering

* **(a) the ketone SMARTS, +14.** `CH3CO` was `[CX4;H3][CX3](=O)` with no `;H0`
  on the carbonyl carbon, so the KETONE group matched an ALDEHYDE, won the
  greedy pass by being the larger match, and stranded the aldehyde hydrogen —
  the tally check then refused the whole molecule, which is it doing its job. It
  cost the entire aliphatic aldehyde series, ethanal through dodecanal. Added to
  the `_SMARTS_CORRECTIONS` mechanism that already existed; ketones verified
  unmoved; `unifac_data`'s docstring claim that the patterns *are* thermo's is
  corrected, and `test_only_the_documented_patterns_differ_from_the_oracle`
  enumerates all ten divergences.
* **(b) a backtracking fallback, +20.** Priority says which group is PREFERRED,
  not which is POSSIBLE, so greedy can eat an atom the only workable cover
  needed elsewhere. `fragmentation._search` is a depth-first search over covers
  with the atom tally bounded by the formula at every node.

⚠⚠ **What makes (b) safe in a matcher Joback also uses is not what it finds, it
is WHEN IT RUNS: only after the greedy pass has been refused.** For any molecule
that fragments today the search is unreachable, so it can turn a refusal into an
answer and can never turn one answer into another. Measured over the catalog:
**Joback unmoved at 1057 species, zero gained and zero changed**; Benson does not
use this matcher. ⚠ And a search that exhausts its budget refuses with a
*different message* — "I did not find a cover" is not "there is no cover".
Measured, nothing comes close: deepest success 18 nodes, most expensive refusal
718, budget 20 000, 0.01 s of search over the whole catalog.

### ⚠ We stop three short of the planned ceiling, on purpose

The 66.4% ceiling was thermo's number on the identical patterns. We reach
**66.1%**, and the three species thermo still decomposes are three it gets by
counting hydrogens off the MOLECULE instead of off the GROUP — `CF2` onto a CHF₂
carbon, the whole-molecule `FURFURAL` group onto a substituted furan, and the
ether group `CH3O` onto a methoxy RADICAL (caught by one of our own documented
pattern corrections). **A refusal is the right answer three times.** The
transferable form: *a number measured off another implementation is a
measurement of that implementation, not a target.*

### What is still missing, named

391 organics still have no decomposition, and `unifac_gap.py` PANEL 2 names them
by unassigned atom environment: 171 carbonyl oxygens outside the
ketone/aldehyde/ester/acid/amide set (anhydrides, acid chlorides, ureas,
carbonates), 75 sulfonyl oxygens, 91 aromatic nitrogens outside a pyridine RING,
nitrate esters, phosphates. Ethene and ethyne have no UNIFAC-VLE decomposition at
all. **None of it is an oversight — it is the edge of a 1975 table, and going
past it means a different model (Dortmund, NIST-UNIFAC) with its own
combinatorial term. That is the basis error M3 exists as the warning about: a
separate, argued decision, not a table merge.**

---

## M5 — Templates to a target, chosen by unlock  ✅ **DONE 2026-08-24**

**Target was 20+ template-ready routes. Measured: 7 → 25 of 173, and 12 → 29 of
212 reaction classes**, from **20 new templates** in `reactions/synthesis.py`.
`examples/named_routes.py` runs 17 of them end to end in ~24 s.

⚠ **THE GREEDY ORDER M1 HANDED FORWARD WAS MOSTLY OUTCOME LABELS, AND THAT IS
THE MILESTONE'S REAL FINDING.** Six of the ten classes at the top of that queue
have no template here, and only one of the six is a difficulty problem:

| refused class | routes it would have unlocked | why |
|---|---:|---|
| `catalytic-air-oxidation` | 3 | three mechanisms — liquid-phase radical autoxidation, Mars–van Krevelen vapour oxidation, and an oxidative ring cleavage |
| `fermentation` | 2 | a metabolic **network**, not a transformation |
| `pyrolysis` | 2 | two of three rows read `coal-marker → coal-tar-marker` |
| `isomerisation` | 2 | three mechanisms under one label |
| `thermal-cracking` | 1 | a lumped product slate from a radical chain |
| `separation` | 1 | the engine *does* fractionate — but a distillation is not a reaction class, and that route's feedstock is a marker |

**M1 built the standard; M5 is the first milestone that had to SPEND it, and
spending it cost six routes off the top of the queue.** What replaced them is a
long tail, and M5 barely shortened it: **63 routes one class away from 50
distinct classes before, 56 from 43 after**. So the work was 20 templates for 18
routes rather than 5 templates for 18, and the next 18 will cost about the same.

⚠ **One class was SPLIT rather than refused, and the distinction matters.**
`catalytic-hydrogenation` is the most-used class with no template in the corpus
(10 steps) and its rows are five mechanisms — but unlike `fermentation`, every
one of them *is* a clean mechanism. So the rows were re-labelled on M1's
precedent and two of the five built. The other three are named gaps. See
`data/catalog/README.md`.

### What it also turned up, none of it planned

* **A reversible template is discovered in the FORWARD direction only.** An ester
  and water in a flask find nothing, however reversible the esterification is,
  because `build_network` matches reactant patterns. General to every reversible
  template in the project; **not fixed** — M5 wrote `ester_hydrolysis` from the
  ester side instead.
* **A neutral species with no vapour-pressure curve MIXES standard states**, and
  it was silent. Worth **+323 kJ/mol** on the first reaction that hit it.
  `standard_state.mixed_basis` now names it and `build_network` prints a notice.
* **An estimator outside its domain arrived as a scipy traceback.** Joback gives
  triolein Tb 1690 K / Tc 4020 K, hence a **negative acentric factor**, hence a
  saturation pressure that falls with temperature. Now a refusal that names the
  species.
* **The audit was calling 9 neutral species "ion".** A neutral that does not boil
  is a different claim from an ion that cannot; it has its own tier now.
* One engine change was needed: `ReactionTemplate.run` collapses explicit
  hydrogens, or the ammonia the Haber template makes is a *different species*
  from the ammonia in the bottle, with the mass balance closing perfectly.

---

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

## S2 — The tolerance audit  ✅ **DONE 2026-08-25 — and the instrument had to be audited before its findings could be**

Two milestones running had quoted a tolerance-limited number, so
`validation/tolerance_audit.py` re-runs every example at rtol 1e-8 / atol 1e-11
and diffs. It patches the two `run` DEFAULTS rather than editing examples, so an
example that already passes its own tolerance is untouched — which is the
built-in self-check: `lime_cycle` and `roasting_and_the_catalyst_gate` come out
**byte-identical at speedup 1.00**, and if they did not, the harness would be
what is wrong.

**Result: 11 examples swept, and after one fix ZERO print a quotable digit that
moves.** 5 move below 0.1%, 6 are identical.

### ⚠ THE ONE REAL MOVE, AND IT WAS IN THE PANEL THAT EXISTS TO SHOW IT

`workshop` Part 2 — melting a dry solid, whose entire point is the latent-heat
plateau:

| t = 800 s | T | solid |
|---|---:|---:|
| rtol 1e-6 (default) | 389.50 K | 2.0000 |
| rtol 1e-8 | **388.38 K** | **1.9656** |

The default says melting has not started. It has: 1.7% of the charge is gone and
the flask is **1.1 K cooler**, because the melt is absorbing latent heat. The
loose run overshoots the temperature by delaying the onset — of the plateau the
line under it points at.

⚠ **AND FIXING IT COST ONE SECOND.** Tightening Part 2 alone takes the example
from **8.1 s to 9.1 s**, not to 58.9 s. The 7.2x belonged to the other panels,
which move by 4e-4 and are deliberately left alone.

### ⚠⚠ ONE EXAMPLE CANNOT BE SWEPT AT ALL, AND ITS NUMBERS ARE STILL CORRECT

`oil_of_vitriol` **RAISES** at rtol 1e-8, in one call —
`burn(690 K, s8=0.002, o2=0.10)`, the panel that demonstrates the dryout-band
fix. `lu_factor` gets `array must not contain infs or NaNs` on `I - c J`: a **NaN
Jacobian**, after 50.7 s of thrashing.

| that call | SO2 / mol | wall |
|---|---:|---:|
| default tolerance | **0.016000** | 0.7 s |
| rtol 1e-8 | **RAISES** | 50.7 s |
| rtol 1e-8 + 1e-9 mol of SO2 charged | **0.016000** | 1.6 s |
| rtol 1e-8 + 1e-6 mol of SO2 charged | 0.016001 | 2.5 s |
| rtol 1e-7 | **0.016000** | 1.5 s |

A trace of the absent species removes the failure and the answer is unchanged to
six figures — **the same diagnostic that identified this trap in the first
place**. So `oil_of_vitriol`'s results are CONFIRMED and what is exposed is the
engine, not the example. **"It moved" and "it refused" are different findings and
the audit reports them in different rows.**

⚠⚠ **THE ZERO-JACOBIAN-COLUMN TRAP THEREFORE HAS A SECOND TRIGGER.** It was
documented as *a species in the network but absent from a sealed flask*. It is
also reachable by *tightening the tolerance on a flask holding a trace* — same
NaN, same fix. That widens the case for the `LAYER_REABSORB`-style honest
diagonal on the gas block, which is still a session of its own.

### ⚠⚠ AND IT REFUTED A CLAIM THIS PROJECT HAD STARTED TO GENERALISE

M6 measured its kiln running FASTER tight (1.4–3.3 s against 5–13 s) and S1
measured the same on a roast (3.67 against 19.94 s). Swept across every example:
**faster in 2 of 11, slower in 9, worst 7.2x.** The speedup is a property of a
stiff vent fed by slow chemistry, not of tightening. Each local measurement was
right; the pattern they suggested is not there, and believing it would tell the
next session that tightening is free.

### ⚠⚠ AND THE INSTRUMENT MANUFACTURED A FINDING BEFORE IT WAS FIXED

Its first version reported `wait_until` moving by **12.5%**. That number was
`0.07 s of wall` against `0.08 s of wall`; the example's real worst move is
**1.04e-4**. A wall clock is now excised as a **token**, not by dropping the
line — because this project prints physics and timing on one line
(`t = 1353.13 s ... (0.89 s of wall)`), so dropping the line would have hidden
the move in `t`. And keying on the word "wall" would have been worse than
coarse: `lime_cycle` prints `±14.374 W wall`, a heat flux, which is exactly the
kind of number the audit exists to check. **An instrument that cannot tell a
wall clock from a result will invent findings** — the same failure shape as a
coverage number counting a route the engine cannot run.

---

## S3 — Split `thermal-decomposition`  ✅ **DONE 2026-08-25 — +2 classes, ZERO routes, and the report was not byte-stable**

M6 read this class against M1's standard, recorded "four rows and they are **four
mechanisms**", and ran out of session rather than acting on it. The reading held.
Four rows re-labelled in `route_steps.psv`, no engine work, because **both
covering mechanisms were already declared under exactly these two names**:

| route | became | covered? |
|---|---|---|
| `vitriol-distillation` 1 | `sulfate-thermal-decomposition` | ✔ built by M6, **runs** (25.4 s at 1000 K) |
| `solvay-process` 3 | `bicarbonate-thermal-decomposition` | ✔ built by M6, **runs** (43.7 s at 450 K) |
| `melamine-route` 1 | `urea-deammoniation` | ✘ a template only |
| `marsh-test` 2 | `hydride-thermal-deposition` | ✘ nucleation, and species |

**Measured: 33/215 classes → 35/218, covered steps 95 → 97, template-ready routes
27 → 27.** Unlike S1, the two credited rows are rows that RUN.

### ⚠⚠ THE INSTRUMENT FIRST — THE COVERAGE REPORT WAS NOT BYTE-STABLE

Regenerating `COVERAGE_REPORT.md` at HEAD (this project's own rule: a committed
generated report is not a baseline) gave a **17-line diff with every number
identical**. `sorted(covered, key=lambda x: -step_classes[x])` sorts a **set**
with no tie-break, so equal step counts came out in `PYTHONHASHSEED` order — while
the `missing` table eight lines below already had `(-count, name)`.

⚠ **A report you cannot diff is a weak instrument**: 17 lines of noise per
regeneration is more than enough to hide a real one-line change in review, which
is what the file is regenerated for. Fixed in one line and verified S2's way —
**byte-identical across `PYTHONHASHSEED=0` and `=1`**. It was the only unstable
site: the greedy `max` already carried a `c` tie-break and the dict-item sorts are
insertion-ordered.

### ⚠⚠ AND THE OTHER GENERATED FILE WAS STALE BY THREE MILESTONES

`ROUTE_INDEX.md` had **not been regenerated since the initial commit**, while
`route_steps.psv` was re-labelled by M5, M6 and S1. Regenerating it moved **21
class labels: 11 from M5, 5 from M6, 1 from S1 and 4 from S3.**

⚠ **It is the one generated file no audit reads** — `catalog_coverage.py` parses
`route_steps.psv` directly — so a stale index changes no measured number, fails no
test and warns nobody. Anyone reading it for a step's class between M5 and S3 got a
pre-M5 answer. The standing rule was "a committed generated report is not a
baseline"; what this adds is that it has to cover the artefact **nothing checks**,
because that is the one that rots in silence.

### ⚠⚠ WHICH ROUTES IT MOVED: ZERO — PREDICTED FIRST, THEN MEASURED

S1's third mistake ("a coverage number moving is not evidence the engine moved")
is now a standing check, and this is the first time it ran *before* the credit
rather than after. All four affected routes are blocked on a **second** uncovered
class — `hydrolysis`, `carbonate-equilibrium`, `trimerisation`,
`dissolving-metal-reduction` — so no route could move, and none did.

⚠ **The greedy curve's "+1 route" for this class was never a standalone unlock.**
It sat at rank 14, i.e. *after* `hydrolysis` was added at rank 6. Read as a
promise it would have delivered a route it cannot deliver — the same misreading as
S1's, arriving from a different table. The standalone table answers that question
and never listed the class.

**What did move is the shape of the remaining work**, and that is the part worth
acting on: `solvay-process` and `vitriol-distillation` both went from two classes
away to **one**, so routes-one-class-away went 58 → 60 from 44 → 46 distinct
classes, and **`hydrolysis` jumped to greedy rank 4 (+2 routes)**.

### ⚠⚠ ONE OF THE TWO CREDITS IS A LATENT FALSE CREDIT, AND THE SPLIT MADE IT NEARER

`vitriol-distillation` step 1 reads `iron-ii-sulfate -> iron-ii-OXIDE +
sulfur-trioxide`; the declaration makes **hematite**, `2 FeSO4 -> Fe2O3 + SO2 +
SO3`. The credit is honest for the **opposite** reason to cinnabar's, and telling
the two apart is the entire value of the check:

* **cinnabar** — the ROW is right (a retort does give the metal) and the mechanism
  stops short of it, so the row needs a second reaction nobody built. Not covered.
* **green vitriol** — the MECHANISM is right and the ROW is wrong. FeO does not
  survive red heat, and `mineral_data` refuses it anyway on its crystal Cp.
  Nothing further is needed to reach the real products.

⚠ **The landmine:** the class is credited and the row still names a product this
engine never makes. Inert today, because step 2 is uncovered. **The day
`hydrolysis` is credited, `vitriol-distillation` goes template-ready on a step
whose stated product does not exist in the run** — and this split just made
`hydrolysis` the 4th-best template to build. Not corrected in the corpus, on the
`diels-alder-route` precedent.

⚠⚠ **Measured, and sharper than "someday": `hydrolysis` unlocks exactly ONE route
on its own, and it is `vitriol-distillation`.** The entire standalone payoff of the
4th-ranked template is the one route carrying a step whose product the engine does
not make.

### The two gaps cost different amounts, which is why they are two classes

* **`urea-deammoniation` is blocked on a TEMPLATE ONLY.** All three species
  resolve and the kernel can already express a unimolecular decomposition in a
  liquid — urea melts at 406 K and the row runs at 620 K, so it is a liquid-phase
  graph rewrite, not a lattice. ⚠ One caveat that is a physical fact rather than a
  gap: cyanic acid is one of the nine neutral species with no boiling point in any
  source, so it is `nonvolatile` and cannot enter the gas block.
* **`hydride-thermal-deposition` is blocked on BOTH, and its mechanism gap has a
  name: NUCLEATION.** `SurfaceArrays` is first order and **extensive** in the
  solid amount, so a solid at zero mol has zero rate for ever — and the term is
  irreversible by construction, so no roasting row can be run backwards to deposit
  one. Depositing a solid from no solid is not expressible here at all. `arsine`
  and `arsenic` are both refused outright, independently of that.

---

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

## S5 — The honest diagonal on the gas block  ✅ **DONE 2026-08-25 — and the fix was in the wrong LAYER, which one measurement said**

**The brief:** a `LAYER_REABSORB`-style honest diagonal on the gas block, to close
the oldest live engine fragility — *a species in the network but absent from a
sealed flask has an identically zero Jacobian column, `num_jac` inflates its
perturbation factor without bound, BDF gets a NaN Jacobian.* Five triggers were on
record across M6, S2 and three `fragilities`/`LAYER_REABSORB` comments.

**What shipped:** `src/chemsim/numerics/jacobian.py`, a bound on the differencing
STEP, imposed at all three `solve_ivp` sites. No chemistry moved. The gas block was
not touched.

### ⚠⚠ FOUR OF THE FIVE TRIGGERS DO NOT REPRODUCE, AND THE FIFTH IS NOT IN THE GAS BLOCK

Every recorded trigger was re-run before anything was written:

| trigger | on record | measured now |
|---|---|---|
| M6's sealed lime kiln, 0.05 mol, N2/O2 absent | RAISED, CO2 reached −2.572 mol | runs clean, `p/K − 1 = −1.56e−04` |
| ... the same at 0.1 / 0.4 / 1.0 mol | clean | clean |
| `fragilities`' `kla=0`, empty headspace | named, never reproduced | still never reproduced (the at-rest short-circuit or a live reaction catches it) |
| a vessel at rest | already short-circuited | already short-circuited |
| **S2's `oil_of_vitriol` at rtol 1e-8** | RAISES after 50.7 s | **RAISES after 52.7 s ✔** |

⚠ The kiln stopped failing because S4 changed `SolidStateArrays.units`, not because
anything was fixed. **A fragility that no longer fires is not a fragility that was
closed, and the difference is only visible if you re-run it.**

### ⚠⚠ THE ONE THAT FIRES OVERFLOWS IN LIQUID LAYER 2 — AND `LAYER_REABSORB` IS THE CAUSE, NOT THE PRECEDENT

Instrumenting the failing run: of 4322 `num_jac` calls, exactly ONE column reaches
`inf`. It is **liquid layer 2's SO2, holding 8.21e-29 mol** — not the gas block,
not absent, and not flat. Every other column tops out at 1.49e+3.

`LAYER_REABSORB` drains an empty layer 2 at `−1.0 · drain2 · nL2`, which is
**strictly negative for any positive holding**. `num_jac` takes `f_sign = −1` and
therefore steps **DOWNWARD** — straight into the RHS's own `np.maximum(y, 0.0)`.
Every downward step, at every size, lands on the same clamped state:

    h            -2.2e-24   -2.2e-19   -2.2e-14   -2.2e-09   -2.2e-04   -2.2e+06
    max |diff|    8.84e-29   8.84e-29   8.84e-29   8.84e-29   8.84e-29   8.84e-29

**Constant over thirty decades of step size**, against a `scale` of 8.37e-14 taken
from a different species' row — so `max_diff < NUM_JAC_DIFF_SMALL · scale` is true
no matter what. Twenty-eight consecutive calls at one unchanged state (t = 1.08799)
climb a decade each, and about two hundred later the factor reads **2.220e+307**.

⚠⚠ **The term the brief named as the PRECEDENT to copy is what points the probe at
the clamp.** And a diagonal on the gas block could not have reached this column at
all. *The brief named a mechanism; the measurement named a different one, in a
different layer.*

### ⚠⚠ THE FIRST BOUND WAS WRONG, AND THE EXAMPLES ARE WHAT SAID SO

`num_jac` uses `h = factor · max(atol, |y_j|)`. The obvious reading — `factor = 1`
moves the variable by all of itself, so cap it at 1.0 — was implemented, swept on
four runs, and every one came out bit-identical. **It was wrong.** Where `|y_j| ≤
atol` the fraction is of ATOL, not of the variable, so `factor = 149` on an absent
species is a 1.5e-7 mol probe of a 0.1 mol flask — a perfectly good probe.

Measured across all sixteen examples, before and after: **8 of 16 moved.**

| | ceiling 1.0 | the state's own extent |
|---|---|---|
| `roasting_and_the_catalyst_gate` | SO2 **0.000201 → 0.000197 mol** | identical |
| `multistep_prep` closure | 100.0127% → 100.0017% | identical |
| `fractional_distillation` tail cut | 0.0702 → **0.0711 mol** | 0.07016210 → 0.07016229 |
| `fractional_distillation` wall | 253 → 402 s (**+59%**) | 253 → 300 s |
| examples whose numbers moved | **6** | **1** |

⚠ **A four-run sweep is not the example set.** "No digit moved" measured on four
runs did not survive sixteen — and the audit that would have caught it is the one
this session then had to write.

### THE BOUND THAT SURVIVED: THE STATE'S OWN EXTENT

    |h_j| <= max_i |y_i|      i.e.   factor_j <= max_i |y_i| / max(atol, |y_j|)

*A difference quotient is a derivative of THIS system only while the probe stays
inside it — you cannot learn anything about a state by moving one of its components
further than the whole state extends.* It is per column and per call, computed from
the state, **with no constant in it.** On a single vessel it never binds: the
busiest example asks for 1.490e+09 (`extraction`) against a bound of order 1e11–1e12.
On the failing column it lands at 6.9e13 — finite, which is all the crash needed.
Swept on that run, **every finite ceiling from 1e2 to 1e14 turns the raise into
0.0160000000**, so what fixes it is finiteness and the value is free to mean
something.

### ⚠⚠ IT DOES BIND ON A RIG, AND THE HONEST TEST IS AGAINST A CONVERGED RUN

`fractional_distillation` — fourteen coupled vessels — wants **3.252e+12** and is
clamped in **232 of its 1833 Jacobians**:

| | converged, rtol 1e-8 | default UNBOUND | default BOUND |
|---|---|---|---|
| forerun | 0.43671495 | 0.43671550 | 0.43671561 |
| heart | 0.55620830 | 0.55620760 | 0.55620765 |
| tail | 0.07016219 | 0.07016210 | 0.07016229 |
| pot T / K | 408.20578700 | 408.20567700 | 408.20573700 |

⚠ **At rtol 1e-8 the heart and tail are BIT-IDENTICAL bounded and unbounded**, so
the two converge to the same answer. At the default, neither is systematically
nearer it — bounded is closer on the heart and the pot, unbounded on the forerun
and the tail — and every difference is **at or below 1e-6 relative, three decades
below the 1e-3 band `tolerance_audit.py` itself declares as a quotable digit.**
So what moved is solver noise, not the answer. ⚠ And what the rig WANTED is worth
looking at before mourning it: factor 3.25e+12 against `atol = 1e-9` is a probe of
**3250 units** on a species holding nothing, in a rig whose entire contents are a
few mol. The seventh-figure move is the difference between two fictions.

⚠ The rig runs ~122 Jacobians per solve against the ~316 an overflow needs. **It is
one longer run away from the same crash.**

### WHAT IT DOES NOT FIX, STATED

The burner still takes ~53 s at rtol 1e-8 against 0.8 s at the default. BDF is
genuinely struggling with a liquid layer holding 1e-29 mol; the bound stops that
struggle ending in a NaN and does not stop the struggle. **The 1.0 ceiling ran it in
2.6 s — which looked like a speedup and was a different Jacobian BDF happened to
like, on a run whose answers it was moving elsewhere. A faster wrong number is not a
better one.**

Nor does it make a flat column non-flat. A species genuinely absent from a sealed
flask still has an identically zero column, and **zero is the correct derivative for
it.** What changes is that `num_jac` stops treating "I measured zero" as "I failed
to measure".

### S2's ONE COVERAGE GAP IS CLOSED

`KNOWN_REFUSAL` is empty. `oil_of_vitriol` moved to `EXPENSIVE` — it completes and
gives the 0.0160000000 mol of SO2 that S2's diagnosis already said was correct.
⚠ That diagnosis was **right about the answer and wrong about the column**: it read
"a species absent from a sealed flask", and the column is layer 2's SO2, frozen
rather than flat.

### ⚠⚠ AND THEN THE SWEEP WAS ACTUALLY RUN, WHICH TURNED UP A SIXTH INSTRUMENT FAULT

`tolerance_audit.py --only oil_of_vitriol` — the run S2 could not do at all —
**completes in 1061 s tight against 57 s loose (18.5x)** and reports
`<-- QUOTABLE DIGITS MOVE, worst 99.85%`. ⚠ **That headline is wrong, and the
five lines behind it say why:**

| line | default | tight | what it is |
|---|---|---|---|
| 900 K | 4.038e-08 | **6.166e-11** | created matter |
| 675 K | 5.620e-07 | **1.587e-09** | created matter |
| 690 K | 2.935e-05 | **2.728e-07** | created matter |
| 730 K | 5.233e-06 | **7.357e-07** | created matter |
| 450 K | 1.5154e-03 | 1.5155e-03 | **liquid held — rel 6.6e-05** |

**Four of the five are the created-matter residual, and every one gets SMALLER**
— a residual converging toward zero, which is a residual behaving. They are
exactly the rows `NEXT_SESSION.md` already carries as **"NOT AN INVARIANT"**,
on S2's own measurement that a 0.5% nudge to the INERT nitrogen swings them
between 2.5e-09 and 4.5e-04. The one physical number in the list moves by
**6.6e-05 relative, three decades under the audit's own 1e-3 reportable band.**

⚠⚠ **A RELATIVE-DIFFERENCE TEST IS MEANINGLESS ON A COLUMN WHOSE CONVERGED VALUE
IS ZERO.** `0.000e+00 -> 2.728e-07` gives rel 0.991 and reads as "99% moved"; it
means "a residual got smaller". The audit HAS a both-below guard
(`REPORT_ABS = 1e-9`) and 2.9e-05 clears it comfortably while still being a
residual. **Reported and NOT fixed:** raising the guard would blunt it for
genuine quantities, and picking the number needs its own measurement and its own
prediction-then-measure pass. It is named here and in the audit so the next
reader does not take the flag at face value.

**So the honest verdict on the closed gap: the example sweeps now, its only
physical number is converged at the default, and the flag it raises is the
instrument dividing one near-zero by another.** Sixth session running, the
instrument was part of the story.

### WHAT WAS BUILT

* `src/chemsim/numerics/jacobian.py` — `factor_bound` and `BoundedJacobian`, wired
  into `VesselIntegrator.run`, `RigIntegrator.run` and Layer 3's `Integrator.run`.
  ⚠ `jac_sparsity` is **consumed** by it, not passed alongside: BDF ignores
  `jac_sparsity` the moment `jac` is callable, so a rig handing over both would
  silently lose the column groups `useful_sparsity` exists to compute.
* `tests/test_jacobian.py` — 11 tests, ~55 s, of which the ~53 s one is the
  regression itself.
* `validation/jacobian_bound.py` — standing audit, four panels, ~1 min. **Run it
  after touching the RHS, `atol`, or anything in `numerics`.** Panel 3 is the check
  that would have rejected the 1.0 ceiling.

---

## S6 — Teach `species-ready` about `mineral_data`  ✅ **DONE 2026-08-25 — the gap was real, and the RECORDED SIZE OF IT was itself wrong**

**The brief:** `species-ready` asks the plain `ThermochemistryProvider`, which
refuses an ionic lattice by name. A lattice has had a home since M3 —
`mineral_data`, on the solid basis — and it is the table precipitation,
`SolidStateArrays` and `SurfaceArrays` all price from. S4 recorded the gap at
**14 routes, 49 → at most 63 of 173**, and deferred it because it redefines a
published column.

**What shipped:** `_mineral_fallback` in `validation/catalog_coverage.py`, a new
`mineral` tier, and two generated report sections. **No `src/` file was touched
and no chemistry moved.** 19 compounds move refused → `mineral`; species-ready
goes **49 → 65**, fully-sourced **5 → 14**.

| column | before | after |
|---|---:|---:|
| routes species-ready | 49 (28.3%) | **65 (37.6%)** |
| routes fully sourced | 5 (2.9%) | **14 (8.1%)** |
| compounds resolving | 1118 (70.6%) | **1137 (71.8%)** |
| formation measured/Benson | 716 (45.2%) | **735 (46.4%)** |
| refused | 465 (29.4%) | **446 (28.2%)** |
| UNIFAC-decomposable | 836 | 836 — **unchanged, by design** |
| reaction classes | 36/218 | 36/218 — unchanged |
| routes template-ready | 28/173 | **28/173 — unchanged** |

### ⚠⚠ THE PREDICTION WAS 14 AND THE ANSWER IS 16 — THE RECORDED NUMBER WAS THE BUG, ONE LAYER DOWN

The standing check was run: predict, then measure. The prediction was S4's
recorded 14, and it came out **16**. The cause is not the corpus and not the
engine — it is how the recorded estimate was measured. It compared the catalog's
SMILES to the `by_lattice` key as a **raw string**, and the catalog spells its
salts in a different fragment order than the canonical table:

    catalog   [Ca+2].[O-]C([O-])=O          [Zn+2].[O-2]
    table     O=C([O-])[O-].[Ca+2]          [O-2].[Zn+2]

| matching rule | routes moved |
|---|---:|
| raw lattice string | 14 ← **the recorded estimate** |
| raw, or the sorted dissolved-ion tuple | 15 |
| **canonical lattice — what the engine itself does** | **16** |

The two it missed are `vulcanisation` and **`lime-cycle`** — and `lime-cycle` is
the route S4's own note names *in its prose* as the headline case ("which M6
declared complete from limestone and whose example demonstrably runs") while its
list of fourteen route ids does not contain it. **The recorded number, the
recorded list and the recorded prose disagreed with each other, and only
re-measuring showed it.** This is the same lesson as S5's four dead triggers in a
different costume: a recorded measurement is a claim about a past state, and it
can be wrong about its own subject.

Canonical is not a convenience — it is what the engine does. `network/builder.py`
line 320 rebuilds every input SMILES through `Molecule.from_smiles` before the
species list exists, so `vessel.py`'s raw `by_lattice()` lookup is reached with
the canonical key. That was **verified rather than inferred**: all 19 rescued
minerals were charged into a real `Vessel` solid block, 19 of 19 holding their
full 0.02 mol. The opposite failure — `pyrite-roasting`, which reads
template-ready and does not run — is exactly what that check exists to prevent.

### ⚠⚠ THE RULE IS A FALLBACK, NEVER AN OVERRIDE, AND THAT IS THE WHOLE DESIGN

The obvious implementation — *is this compound a mineral?* — is wrong, and
measurably so. 36 catalog compounds sit on a mineral lattice, but 17 of them
**already resolve as `ion`**: `sodium-chloride`'s ions are priced, it genuinely
dissolves, and with `precipitation=True` it can also leave solution. Labelling it
`mineral` would **downgrade** a species the engine handles in two phases to one
it handles in one, and would have silently cut the published UNIFAC count.

So `_mineral_fallback` is consulted **only where all three providers have already
refused**. That is not a new precedence, it is the engine's own: `thermochemistry`
prices the ions when it can, and `mineral_data` is what the solid block falls back
to when it cannot. Because every rescued species was previously refused, the
branch returns exactly where the refusal did — and **the UNIFAC count does not
move by one**, which is the honest answer: a lattice cannot enter a liquid
mixture, by the same verdict that sent it down this branch.

### ⚠ `mineral` IS A SEPARATE TIER, NOT PART OF `measured`

It is measured data — CRC `Hf` and `S0`, `Gf` derived against the same element
reference states, same-database rule enforced — so it counts on the measured side
of the formation headline. But it is reported under its own name, because a
solid-basis `Hf`/`Gf` **is not on the ideal-gas basis every `ThermoData` uses**.
Folding it into `measured` in the report would make exactly the conflation the
separate `MineralRecord` type upstream exists to prevent.

### ⚠⚠ THE COLUMN NOBODY WAS COMPUTING: THE INTERSECTION IS 17, NOT 28

Asked afterwards what the coverage actually is, S6 measured the one thing none of
the three readiness columns says. **They answer INDEPENDENT questions, and the
smallest does not bound the others.**

| | routes |
|---|---:|
| species-ready | 65 |
| template-ready | 28 |
| **BOTH — the only one a route can be judged on** | **17** |

**11 of the 28 template-ready routes have a refused species and cannot run** —
`pyrite-roasting`, `tnt-route`, `superphosphate`, `chrome-yellow-route`,
`biodiesel-route` and six more. Quoting 28 as *what could run* overstates it by a
factor of 1.6, and this project has quoted 28 since S4.

⚠ **AND IT CHANGES WHAT S6 IS WORTH.** Measured both ways: the intersection
without the `mineral` tier is **12**, with it **17**. So the milestone that
"moved no template-ready route" moved the runnable count by **+5** — more than the
last three content milestones combined. Curating a species and writing a template
are the SAME axis on this column, which neither of the published ones can show.

⚠⚠ **AND THE WORK QUEUE WAS RANKED ON THE OVERSTATED COLUMN.** The greedy curve
and the one-class-away table both counted template unlocks alone. Re-ranked by
routes that would clear BOTH bars, the top changes hands:

| class | unlocks ALONE | of those, RUNNABLE |
|---|---:|---:|
| `isomerisation` | 3 | **2** |
| `crosslinking` | 2 | **2** |
| `electro-organic-coupling` | 2 | **2** |
| `electrolysis` (= M8) | 3 | **1** |
| `catalytic-air-oxidation` | 3 | **0** |

⚠ `catalytic-air-oxidation` is the third row of the greedy curve and is worth
**ZERO** runnable routes. Both tables now carry a RUNNABLE column, generated.

⚠ One thing the re-rank does NOT settle: `electro-organic-coupling`
(`kolbe-electrolysis`, `adiponitrile-route`) is electrochemistry too, and M8's
brief names only `electrolysis`. If one milestone covers both it is +5 unlocked /
**+3 runnable**, which would put it back on top. **That is a scoping question to
answer before scheduling M8, not an assumption to make.**

> ⚠⚠ **M8 ANSWERED IT, AND THE RUNNABLE HALF WAS RIGHT WHILE THE UNLOCKED HALF
> WAS NOT.** One mechanism does cover both — an applied cell potential supplying
> `n F E` — so the milestone was scoped to both, and the measured outcome is
> **+3 runnable, exactly as predicted, on +3 unlocked rather than +5.**
>
> The two missing unlocks are the price of M1's row check landing on the greedy
> curve's own top row. `electrolysis`'s four rows are THREE mechanisms, split at
> the CATHODE: `aqueous-electrolysis` (chloralkali — reduces water, BUILT),
> `molten-salt-electrolysis` (downs-cell, hall-heroult — a melt is not a phase
> here) and `amalgam-electrolysis` (castner-kellner — reduces the sodium, and
> the product is a marker). **The row that has led the greedy curve since M1 is
> worth +1, not +3.**
>
> ⚠ Note which of the two columns survived. `RUNNABLE` was right because both
> melt rows are ALSO blocked on a bare element, so the split cost nothing there —
> the column that counts what can actually run was insensitive to the very error
> that halved the other one. **That is the second time in two milestones that
> the intersection was the trustworthy column.** See §M8.

⚠ **And the claim it makes is narrow.** A mineral resolves here *as a crystal*:
it can be charged, held and reacted, and it still cannot dissolve. A step needing
one in solution is still not expressible. **None of the 16 routes becomes
template-ready**, and template-readiness remains the binding constraint — which is
why the honest headline of this milestone is the unchanged 28, not the 65.

### ⚠ THE NEXT ONE ALONG IS THE SAME SHAPE, AND IT IS NOW MEASURED: 15 ROUTES

45 compounds are still refused as *a bare element symbol*, and the refusal is
right — the ideal-gas value for `[C]` is the atom at Gf +671 kJ/mol while the
charcoal in the flask is 0. `iron`, `copper` and `nickel` escaped it only because
**S1 needed them as solid catalysts** and curated them into `mineral_data`; the
other 45 did not. **15 routes are blocked by nothing else**, and the leverage is
now a table rather than a hunch: `cobalt` +3, then `carbon-graphite`, `platinum`
and `silver` at +2 each.

⚠ It is a curation job with a **layering question in front of it**.
`element_data.REFERENCE_STATES` already carries S0 and the reference state for
these — Zn(s), Ag(s), C(graphite) — but with `smiles=None`, because a SOLID
reference state had nowhere to live until the solid block existed. Mercury
resolves today precisely because its standard state is a LIQUID and so it got a
SMILES. What is missing is that binding plus the `Cp_solid`/`Vm_solid` pair
`priced_solid` demands. **Whether that belongs in `element_data` or in
`mineral_data` is a real decision — a metal is not a mineral — and it owes its own
predict-then-measure pass.**

### ⚠ BOTH NEW REPORT SECTIONS ARE GENERATED, AND THAT IS THE POINT

The estimate this milestone replaces was a hand-written comment that drifted from
its own corpus. Both replacements — *the 16 routes species-ready on a lattice* and
*the 15 blocked only by a bare element* — are computed on every run, so they
cannot rot the way it did. `COVERAGE_REPORT.md` remains byte-identical across
`PYTHONHASHSEED` values (checked at 12345, 999 and 4242), as do
`route_roles.psv` and `species_roles.psv`.

**Touched:**
* `validation/catalog_coverage.py` — `_mineral_fallback`, the `mineral` tier,
  `SOURCED_TIERS`, and the two generated sections. ⚠ The three hard-coded
  `measured + benson + ion` sums now go through `SOURCED_TIERS`; adding a tier
  without adding it there is how a headline silently under-counts.
* `data/catalog/COVERAGE_REPORT.md`, `data/catalog/derived/species_roles.psv` —
  regenerated. `ROUTE_INDEX.md` and `route_roles.psv` regenerated and unchanged.
* `README.md` — the coverage table, plus the new `routes species-ready` row.

**NOT touched:** anything under `src/`. The engine, the 826-test suite and every
example are untouched by construction, and no invariant in `NEXT_SESSION.md`
moves.

---

## S7 — The four inorganic gas processes  ✅ **DONE 2026-08-26 — and the queue's top two rows measured ZERO before a line was written**

**+5 classes (38 → 43 of 224), +3 template-ready (31 → 34), +4 RUNNABLE
(20 → 24).** Five templates, no engine work in Layers 3–4, one refusal widened
in Layer 1, and two new standing audits. **The intersection moved +4, which is
the largest single-session move it has had.**

| | before | after |
|---|---:|---:|
| classes with a template | 38 / 220 | **43 / 224** |
| templates | 38 | **43** |
| routes species-ready | 65 | **63** |
| routes template-ready | 31 | **34** |
| ⚠⚠ **routes BOTH — the one to quote** | **20** | **24** |

⚠ **PREDICTED FIRST, ALL FIVE EXACTLY**: 43/224 classes, 43 templates, 34
template-ready, 24 BOTH, and species-ready holding at 65 before the refusal was
widened. The refusal then took it to 63, which was predicted as "≤ 4, and 0 in
the BOTH column" and measured at 2 and 0.

### ⚠⚠ 1. THE QUEUE'S TOP TWO ROWS WERE MEASURED BEFORE BEING COSTED, AND BOTH ARE WORTH NOTHING

`catalog_coverage`'s work queue is ranked by RUNNABLE — routes a class unlocks
that are also species-ready — which is the column M8 proved to be the
trustworthy one. Its top two rows were `isomerisation` (+3 / **+2 runnable**)
and `crosslinking` (+2 / **+2 runnable**). **Neither is worth a single honest
route, and the three reasons are all different:**

| row | measured |
|---|---|
| `hydrogenation-margarine` 2 `oleic + H2 + Ni -> elaidic + Ni` | **the row cannot be balanced** (an H2 in, none out) AND the pair prices at **dH = dG = 0.000 exactly** |
| `starch-hydrolysis` 3 `glucose -> fructose` | **dG +41.784 kJ/mol, K = 4.8e-08** — the engine would call high-fructose corn syrup impossible |
| `wohler-urea` 2 `ammonium-cyanate -> urea` | not species-ready: a dot-separated ionic pair, cyanate in no ion table here |
| `tanning-route` 2 | product is `tanned-leather-marker` — no molecular graph |
| `vulcanisation` 1 | product is `CC(C)=CC.S1SSSSSSS1` — **its own two reactants side by side** |

⚠ **THE CIS/TRANS ZERO IS THE ONE WORTH READING.** Benson has no cis correction
in the RMG group set this project uses, so oleic and elaidic acid come back with
*identical* Hf and Gf. A template on that row reports a confident 50:50 for a
real ~5:1. **The data to fix it exists and is not usable as it stands:** WEBBOOK
carries both liquid enthalpies, −764.8 and −769.0 kJ/mol, and that 4.2 kJ/mol
gap agrees with Benson's own historical cis NNI term of 4.18 to 0.4% — two
independent sources. But neither has an S0, so no Gf can be derived; and
grafting Benson's original correction onto RMG-fitted group values mixes two
bases, which is the trap `chemsim-benson-status` names. **Recorded as a route
in, not taken.**

⚠ **AND THE GLUCOSE ROW'S FAULT IS IN THE CORPUS, NOT THE ESTIMATOR.** Glucose
is spelled as a PYRANOSE and fructose as a FURANOSE, and Benson charges the
ring-size difference. Two independent problems on one row, and S3's *which one
is WRONG* question has a clear answer here for once: the corpus is.

⚠⚠ **SO `RUNNABLE` HAS THE SAME SHAPE OF FAULT `ALONE` HAD, AND IT IS WORTH
STATING AS A RULE.** `ALONE` counts routes and cannot ask whether the species
are priced. `RUNNABLE` adds that bar and cannot ask two more:

1. **is the number that comes back RIGHT?** Not mechanisable. One row prices at
   exactly zero and another 40 kJ/mol out, and no column can see either.
2. **is the row's PRODUCT a graph at all?** This one IS mechanisable, and S7
   mechanised it: a route with a marker on the PRODUCT side of any step is now
   excluded from the RUNNABLE column. `crosslinking` goes to **+0** and
   `oxidative-complexation` leaves the top twenty. ⚠ It moves no route in the
   BOTH column — checked, not assumed.

### 2. THE FOUR PROCESSES, AND THREE OF THEM ARE INTERESTING ONLY BECAUSE THEY ARE REVERSIBLE

| class | template | route |
|---|---|---|
| `water-gas-shift` | `water_gas_shift` over hematite | `water-gas-shift` |
| `steam-reforming` | `steam_reforming` over nickel | `steam-reforming` |
| `catalytic-gas-oxidation` (⚠ S9 SPLIT IT — see §S9) | `deacon_oxidation` over tenorite | `deacon-process` |
| `comproportionation` | `claus_comproportionation` | `claus-process` |
| `hydrogen-sulfide-combustion` | `hydrogen_sulfide_combustion` | `claus-process` |

Every equilibrium came out at its textbook value off this project's own tables
before a template existed — dH −41.15 against a book −41.2 for the shift, +206.2
against +206 for the reformer, −114.4 against −114.5 for Deacon. **What the
templates buy is behaviour nobody declared**, measured in
`validation/gas_processes.py`:

* the **shift** peaks at **81.3% at 620 K** and falls to 55.6% at 900 K. Below
  620 K the barrier limits it and above it the equilibrium does. Two reactors,
  hot then cold, and nothing says so;
* the **reformer** is **0.01% converted at 700 K and 36.1% at 1300 K**, and
  thinning the same 1100 K flask from 54 bar to 0.63 bar takes it from 18.6% to
  **73.5%** — the one gas equilibrium in this project that pressure *hurts*,
  because two moles go in and four come out;
* **Deacon**'s ceiling and rate cross between 600 and 700 K: 90.6% in ten
  seconds at 600 K climbing to 91.2% over an hour, against 84.6% at 700 K
  reached in ten seconds and never bettered. **The whole industrial history of
  the process is those two columns**;
* **Claus** recovers **100.0% of its sulfur at exactly 0.10 mol of O2 for 0.20
  of H2S** and less on either side, because burning one third of the feed is
  what leaves the 2:1 H2S:SO2 the second template wants. **Neither template
  knows the other exists.**

⚠ **THE CLAUS TEMPLATE HAS TWENTY-FOUR REACTANT SLOTS, AND S8 IS THE REASON.**
The chemistry is `2 H2S + SO2 -> 3 S + 2 H2O`; this project's sulfur is the S8
crown and a graph rewrite cannot write 3/8 of a ring, so the smallest whole
multiple is `16 H2S + 8 SO2 -> 3 S8 + 16 H2O`. Declared first order in each
reagent — the burner's decision, with a bigger number in it — and therefore
**not reversible**, which costs nothing at ln K +232.

⚠ **AND THE CONVERSION CEILING A REAL CLAUS TRAIN HAS IS NOT THERMODYNAMIC
HERE, YET THE VESSEL STILL FINDS ONE.** This equilibrium says 100%; what the
flask does at 500 K is CONDENSE the sulfur, because S8 boils at 717.8 K. That is
the sulfur condenser between the stages, and it is the vapour-pressure curve
rather than the equilibrium.

### ⚠⚠ 3. `combustion` WAS AN OUTCOME LABEL — AND THIS IS THE FIRST SPLIT WHOSE HEADLINE EFFECT IS NEGATIVE

Six rows under one label, credited to `sulfur_combustion` since M1. That
template's SMARTS is `S8 + 8 O2 -> 8 SO2`, so it fires on **two** of the six.

| route | step | became | covered? |
|---|---|---|---|
| `lead-chamber` 1, `contact-process` 1 | `S8 + O2 -> SO2` | `sulfur-combustion` | ✔ unchanged |
| `claus-process` 1 | `H2S + O2 -> SO2 + H2O` | `hydrogen-sulfide-combustion` | ✔ **built here** |
| `blast-furnace` 1 | `C(gr) + O2 -> CO2` | `carbon-combustion` | ✘ named gap |
| `ethylene-oxide-route` 2 | `C2H4 + O2 -> CO2 + H2O` | `hydrocarbon-combustion` | ✘ named gap |
| `match-chemistry` 1 | `KClO3 + P4 -> P2O5 + KCl` | `chlorate-oxygen-transfer` | ✘ named gap |

⚠ **THE MATCH ROW IS NOT COMBUSTION AT ALL**, which is the clearest sign the
label was an outcome: a solid oxidiser hands its oxygen to a solid fuel on
friction, with no air and no flame until after it goes.

⚠⚠ **`match-chemistry` LOSES TEMPLATE-READY FOR IT.** Every previous split here
— `roasting`, `thermal-decomposition`, `electrolysis` — held the headline or
raised it. This one lowers it. It was never species-ready, so the intersection
does not move, and **a split whose measured effect is negative is a split doing
its job.** This is the first one in the project to prove that.

### ⚠⚠ 4. A NEUTRAL MULTI-FRAGMENT SMILES WAS PRICED, AND THE RECORDED REASON FOR ALLOWING IT WAS MEASURED FALSE

`thermochemistry._refuse_outside_estimator_domain` refused a dot-separated
SMILES only when a fragment carried CHARGE. Its docstring said why: *"a neutral
multi-fragment SMILES (a hydrate, a co-crystal) is deliberately left alone:
nothing in this project produces one, so refusing it would widen the blast
radius for no measured gain."* **Both halves are false.** The catalog carries
**eleven**, and:

| species | whole | its fragments | gap |
|---|---:|---:|---:|
| `vulcanised-rubber-marker` `CC(C)=CC.S1SSSSSSS1` | **+273.70** (Joback) | −48.83 + 100.42 = +51.59 | **+222.11** |
| `nbr-marker` `CC(C#N).CC=CC` | −17.33 (Joback) | +46.16 | **−63.49** |
| `sbr-marker` | +15.61 (Benson) | +16.43 | −0.82 |
| `butyl-rubber-marker`, `nylon-66-salt` | Benson | — | **+0.00 exactly** |

⚠⚠ **IN AN IDEAL GAS THE SUM IS AN IDENTITY, NOT AN ESTIMATE.** There are no
intermolecular interactions, so the record for a collection of fragments IS the
sum of theirs. **Benson honours it because it is additive over groups; Joback
does not**, because its correlation has a constant term and non-linear terms, so
two disconnected fragments double-count the constant. So the refusal is now on
the FRAGMENT COUNT and the charge only decides which message is printed.

⚠ **AND THE AUDIT WAS DISAGREEING WITH THE PROVIDER IT AUDITS.**
`catalog_coverage.audit_compound` treated *any* dot as ionic and priced
fragment-by-fragment, so all nine kept resolving after the engine stopped
pricing them. That is right for a salt — the electrolyte path really does hold
the two ions — and wrong for a neutral mixture, which `builder` canonicalises
into ONE species. Fixed to ask about the whole species unless a fragment is
charged. **Cost: 9 compounds to `refused`, 2 routes out of species-ready
(`vulcanisation` and `nylon66-route`, both lattice-carried), and 0 in the BOTH
column.**

### ⚠⚠ 5. NOTHING HAS EVER CHECKED THAT A CATALOG ROW BALANCES

`tools/catalog.py`'s `validate` checks that every SMILES parses, every species id
exists and every route's target is made by one of its own steps. **It has never
checked that a step conserves matter.** `validation/corpus_balance.py` is that
check, and the question is not "does it balance as written" — the corpus carries
no coefficients on purpose — but **does a strictly positive coefficient vector
exist**, an LP feasibility problem over the element-and-charge matrix.

**Measured: 75 of 367 testable rows cannot be balanced by any positive
coefficients.** Classified, because the three kinds cost different things:

| kind | n | what it is |
|---|---:|---|
| `spurious` | 17 | a reagent consumed on paper and nowhere else. `hydrogenation-margarine`'s hydrogen; `perkin-route`'s sodium acetate, which is the BASE |
| `charge` | 1 | elements balance, charge does not — an ionic half-row |
| `atoms` | 57 | an element with no source. Mostly deliberate (`anthracene + K2Cr2O7 -> anthraquinone + water` never says what became of the chromium); a few are plain mistakes (`indican + oxygen -> tyrian-purple + water` needs bromine and there is none on the left) |

⚠⚠ **AND IT TOUCHES THE HEADLINE EXACTLY ONCE.** One of the 24 BOTH routes
carries an unbalanceable step: `perkin-route` step 1. It is **inert**, because
`perkin_condensation`'s SMARTS is on the aldehyde and the anhydride and never
mentions the base. `vitriol-distillation`'s landmine in a milder form: the class
is credited, the ROW is wrong, and the two do not meet.

⚠ **NOT FIXED, ON THE `diels-alder-route` PRECEDENT.** Inventing chemistry
inside an audit corpus is not allowed. 61 of 173 routes carry at least one such
row; this is a third readiness bar, reported so it cannot rot, not a to-do list.

### ⚠ 6. THE NEW ROW IN THE RATE-CEILING AUDIT, FOUND ON ITS FIRST RUN

`deacon_oxidation_rev` crosses the bimolecular collision ceiling at **1141 K** —
the COLDEST of the high-order reverse rows, below `ammonia_synthesis_rev`'s
1335 K and `methanol_from_carbon_dioxide_rev`'s 1248 K. **Reported, not
guarded**, on exactly the policy those two already sit under: the cap scales both
pre-exponentials by one factor, so it moves a CLOCK and not an equilibrium, and
the process is run to 900 K.
⚠ And the crossing temperature is **not a physical statement** for these rows:
the reverse of Deacon is `2 Cl2 + 2 H2O -> 4 HCl + O2`, a FOURTH-order rate
constant in L³/(mol³ s), against a ceiling in L/(mol s). M8's unit error, and
the column is good for RANKING rather than for a verdict.

### ⚠ 7. THE SMALL THINGS

* `deacon_oxidation`'s brief said A = 1e13 puts equilibrium "on a scale of
  minutes at 700 K". **The run said ten seconds.** The number stayed and the
  claim was corrected — ten seconds is the defensible one and a converter's
  contact time is seconds.
* `synthesis_gas_chemistry`'s docstring still said "there is no catalyst species
  — the flask will make ammonia with no iron in it". **S1 made that false and
  nothing caught it until S7 read it.** Corrected in place, with the history.
* the WGS product template first came out as `O=C=[O+]` — the CO's `[O+]` was
  never neutralised. Caught by reading the product SMILES, which is the second
  time that has been the catch (see `sulfur_dioxide_oxidation`).

**Files:** `properties/thermochemistry.py` (the fragment refusal),
`reactions/synthesis.py` (5 templates, 3 bundles, 1 stale claim),
`reactions/__init__.py` (exports), `data/catalog/route_steps.psv` (6 rows
re-labelled), `data/catalog/README.md` (+110 lines),
`validation/catalog_coverage.py` (the class map, the fragment rule, the marker
bar), `validation/rate_ceiling.py` (the three new reversible templates),
`validation/gas_processes.py` (new, standing audit),
`validation/corpus_balance.py` (new, standing audit),
`tests/test_gas_processes.py` (new, 19 tests), `README.md`.

---

## S8 — The bare-element gap, and the +2 it was supposed to enable  ✅ **DONE 2026-08-26 — the curation landed, the template it was for is REFUSED, and both were predicted**

**+14 species-ready (63 → 77), +0 on the intersection (24), and the reason for
the second number is the whole milestone.** Nine element solids curated,
`element_data` given two reference entropies it was missing, zero new templates,
and `gas-solid-reduction` — the only +2 on the work queue — measured and refused.

| | before | after |
|---|---:|---:|
| routes species-ready | 63 / 173 | **77 / 173** |
| ... of them carried by a lattice | 14 | **28** |
| compounds refused | 455 | **444** |
| classes with a template | 43 / 224 | 43 / 224 |
| ⚠⚠ **routes BOTH — the one to quote** | **24** | **24** |

### ⚠⚠ 1. THE ELEMENT GAP IS WORTH +14 SPECIES-READY AND EXACTLY ZERO ON THE INTERSECTION

`NEXT_PROMPT` called this "the cheapest item here, and untouched since S6" for two
sessions. **S7 predicted it at +0 on the intersection by reading the two lists
against each other; S8 did it and measured +0.** None of the 15 routes blocked
only by a bare element is template-ready, so curating every one of them moves the
column a route is judged on by nothing.

⚠ **WHAT IT ACTUALLY BUYS IS A MULTIPLIER, AND THAT IS VISIBLE IN THE QUEUE.**
Before and after, on the RUNNABLE column:

| class | before | after | its routes |
|---|---:|---:|---|
| `gas-solid-reduction` | 1 | **2** | `copper-smelting`, `lead-smelting` |
| `catalytic-air-oxidation` | 0 | **1** | `p-xylene-oxidation` |
| `carbothermic-reduction` | 0 | **1** | `zinc-smelting` |
| `metal-ion-aldehyde-oxidation` | 0 | **1** | `tollens-test` |
| `molten-salt-electrolysis` | 0 | **1** | `downs-cell` |
| `pyrolysis` | 0 | **1** | `wood-distillation` |
| `disproportionation-hydrolysis` | — | **1** | `ostwald-process` (new entry) |
| `hydroformylation` | — | **1** | `oxo-process` (new entry) |
| `metallothermic-reduction` | — | **1** | `thermite` (new entry) |

**So the honest summary is +0 today and +9 opportunities that did not exist
before**, and the ordering lesson is that species work should follow the template
it enables rather than lead it.

### 2. THE CURATION, AND WHY `element_data` WAS THE WRONG HOME

Nine rows in `mineral_data`, on the SOLID basis, `ions=()`, `Hf = Gf = 0` by
definition: `cobalt`, `silver`, `platinum`, `palladium`, `lead`, `aluminium`,
`sodium`, `zinc`, `carbon-graphite`. **No new machinery** — S1 had already built
the shape for `iron`, `nickel` and `copper`, and
`tools/build_mineral_data.py` carried the whole argument in a block comment above
a three-item list.

⚠ **THE LAYERING QUESTION S6 RAISED HAS AN ANSWER AND IT IS IN THE TYPE, NOT THE
MODULE NAME.** `element_data`'s record is on the IDEAL-GAS basis, and the
ideal-gas record for `[Fe]` is the ATOM at +416 kJ/mol — a real number that is
not iron filings. A solid-basis zero belongs in the solid-basis module.
`element_data.REFERENCE_STATES` still carries each element's S0, which is what
the Gf derivation consumes, and **S8 had to add two: Pt and Pd were missing**, so
platinum and palladium could not have been derived without touching that file.
The regeneration is purely additive — 10 lines, nothing existing moved.

⚠ **THE LIST WAS CALLED `METALS` AND THE NAME WAS WRONG BY ONE ROW.**
`carbon-graphite` is a COVALENT lattice. Every property the entry needs is about
the REPRESENTATION rather than the bonding — no dissolved form, a crystalline
reference state, a definitional zero, and a solid block that holds it exactly as
it holds iron — so renaming the list to `ELEMENT_SOLIDS` was cheaper than an
exception, and an exception was the only alternative.

⚠ **AND THE DEFINITIONAL-ZERO CHECK FIRED, WHICH IS WHY TIN IS NOT IN THE LIST.**
CRC's row for 7440-31-5 is GREY tin at `Hfs = -2.1 kJ/mol` against a white-tin
reference state. The generator refuses it rather than taking the wrong allotrope
— the same check `reference_entropies` has made since the element floor was built.

⚠ **VERIFIED BY RUNNING.** All nine charged into a real `Vessel` at 800 K with
air, held to twelve figures over 600 s, `conservation_report` empty. S6's
precedent: reading `priced_solid` is a different claim from charging it.

⚠ **AND THE IDEAL-GAS REFUSAL IS NOT SOFTENED BY ONE DIGIT.** `thermo.get("[C]")`
still refuses, with the same message; `validation/game_gates.py` still reports
graphite, Na, K, Ca, Fe, Cu, Zn as REFUSED on that basis. Curating the solid
basis and refusing the gas basis are the same statement made twice.

### ⚠⚠ 3. `gas-solid-reduction` IS REFUSED, AND THE REFUSAL IS THE CHEMISTRY

The only +2 on the queue. Its four rows are `MO(s) + CO(g) -> M(s) + CO2(g)` —
the same shape as a roast, a gas arriving at a crystal — so it looked like four
rows of `SURFACE_REACTIONS` and no code. **Every one fails
`surface.LN_K_IRREVERSIBLE`, priced against this project's own tables at each
row's own furnace temperature:**

    tenorite + CO  -> copper  + CO2    dG -127.72 kJ/mol   ln K  10.90 @ 1500 K
    litharge + CO  -> lead    + CO2    dG  -68.31          ln K   7.24 @ 1400 K
    hematite + 3CO -> 2 iron  + 3CO2   dG  -29.48          ln K   4.20 @ 1300 K
    zincite  + CO  -> zinc    + CO2    dG  +63.31          ln K  -4.10 @ 1400 K

⚠⚠ **AND THE BOUND IS NOT THE PROBLEM — THE CHEMISTRY IS.** A blast furnace's top
gas still contains carbon monoxide, and it does because these reductions really
are reversible: the CO/CO2 ratio over an oxide is the equilibrium a furnace's
entire design is built around. The zinc row is not even downhill; a real zinc
retort works because the zinc **boils off at 1180 K**, which is product removal
rather than a favourable equilibrium — and `mineral_data` holds zinc as a lattice
with no vapour pressure, so that escape is not expressible here either.

⚠ Softening `LN_K_IRREVERSIBLE` would admit a real reverse flux into a term that
is integrated FORWARD ONLY, and the refusal message already says why that cannot
be traded: mass action written on a solid AMOUNT settles at `p/K = n_A/n_B`
rather than at unit activity (M6's measurement), so a reversible declaration
would reach a wrong equilibrium while looking like one that does not.

**So `gas-solid-reduction` is a NAMED ENGINE GAP: it needs a REVERSIBLE
solid-gas term.** It is the second gap of that shape after NUCLEATION, and unlike
nucleation it has **two species-ready routes waiting on it** — which makes it the
most valuable engine item in the plan that nobody has scoped.

### ⚠ 4. WHAT THE SESSION DID NOT DO, AND WHY THAT IS THE RIGHT ANSWER

No template was written. The queue's only +2 turned out to need engine work, and
the alternatives are all +1 — `wacker-oxidation`, `oxidative-cleavage`,
`skraup-cyclisation`, `metallothermic-reduction` and the six the curation just
created. Picking one at random would have been worth less than measuring which
ones are real, and S7's own lesson is that the ranking lies. **The queue is now
ranked against three bars instead of one; the next session picks off it.**

**Files:** `tools/build_element_data.py` (Pt/Pd reference states),
`tools/build_mineral_data.py` (`METALS` → `ELEMENT_SOLIDS`, +9 rows),
`src/chemsim/properties/element_data.py` (regenerated, +10 lines),
`src/chemsim/properties/mineral_data.py` (regenerated, +144 lines),
`src/chemsim/properties/surface.py` (the refusal, recorded),
`tests/test_element_solids.py` (new, 38 tests),
`tests/test_element_data.py` (the exemption list), `README.md`,
`data/catalog/COVERAGE_REPORT.md` and both `derived/*.psv` (regenerated).

---

## S9 — The reversible solid-gas term, and the smelter  ✅ **DONE 2026-08-26 — the queue's only +2 was one algebraic rearrangement, and the reason recorded beside the refusal was about a form the term never used**

**+5 classes (43 → 48, of 229 after two splits), +4 template-ready (34 → 38), +4 RUNNABLE
(24 → 28)** — tying S7 for the largest single-session move the intersection has
had. Six declarations, ~15 lines of engine, no new term, no new phase, and the
five pre-S9 solid-state rows are BIT-IDENTICAL.

⚠ **All four coverage numbers were PREDICTED before the audit was run and all
four came out exactly**: 48 classes, 38, 28, and species-ready holding at 77.
⚠ The class DENOMINATOR moved 224 → 229 because S9 made TWO splits, and only
one of them was planned — see §8 and §9 below.

| | before | after |
|---|---:|---:|
| classes with a template | 43 / 224 | **48 / 229** |
| routes template-ready | 34 / 173 | **38 / 173** |
| routes species-ready | 77 / 173 | 77 / 173 |
| ⚠⚠ **routes BOTH — the one to quote** | **24** | **28** |

The four: `copper-smelting`, `lead-smelting`, `zinc-smelting`, `thermite`. **All
three smelting routes at once**, which `catalog_coverage.py` has carried a
comment about since S1 — *"all three smelting routes are still blocked at
`carbothermic-reduction` / `gas-solid-reduction`"*.

### ⚠⚠ 1. THE ENGINE GAP WAS ONE ALGEBRAIC REARRANGEMENT, AND HALF THE REASON BESIDE IT WAS ABOUT A DIFFERENT FORM

S8 named "a REVERSIBLE solid-gas term" as **the most valuable engine item in the
plan that nobody had scoped**. `SolidStateArrays` already integrates the affinity
form and already reaches `Q = K`; what it refused was a gas REACTANT, on two
recorded grounds:

1. *its pressure sits in the DENOMINATOR of `Q = prod(p ** nu_gas)`, so an
   atmosphere depleted of it drives the reverse flux to 2.6e15 formula units per
   second* — **true, and cured by not writing a quotient.**

       net = k_f * prod(p ** consumed_gas)  -  k_r * prod(p ** formed_gas)

   is `P_react (k_f - k_r Q)` algebraically — **the same root, so the same
   equilibrium** — and at `p_react = 0` it is the finite `-k_r P_prod`. Measured
   on the copper row at 1400 K: the old branch reads 1.50e-8, 1.50e-2, 1.50e+4,
   1.50e+22, `inf` as p_CO falls 1 → 1e-3 → 1e-6 → 1e-30 → 0; the new one is
   bounded by `k_r` at 1.4973e-08 the whole way.

2. *mass action written on a solid AMOUNT settles at `p/K = n_A/n_B`* — M6's
   measurement, true, and **not about this term.** The affinity form takes ONE
   `units` for both directions, chosen by the sign of the affinity, so it is a
   common factor that divides out of `net = 0`. That was already the case when
   the refusal was written. Measured across a **50x charge range**: Q/K =
   1.0000, 1.0000, 1.0000.

⚠⚠ **SO M6 DREW THE LINE IN THE WRONG PLACE, AND THE RIGHT LINE IS ALREADY ONE
OF THIS PROJECT'S INVARIANTS.** The dichotomy was recorded as *inside a crystal /
at its surface*, and S4 had already broken that by turning a crystal entirely
into gas. The line that actually holds is **reversible or not**: an affinity form
cannot carry DECLARED rate orders, because detailed balance fixes its exponents
at the stoichiometric coefficients or the equilibrium is wrong. That is verbatim
*"a declared rate order may NEVER be reversible"*, which has been in the
invariants table since M8's rate work, arriving in a new place. So roasting stays
in `SurfaceArrays` — `3 O2` as mass action stalls asymptotically, which is what
`SurfaceReaction.orders` exists to declare away — and it stays there **for the
order and not for the denominator**.

### ⚠⚠ 2. THE SECOND CHANGE: `Ea = max(dH, 0)` IS A DERIVATION ABOUT A DECOMPOSITION, AND ON AN EXOTHERMIC ROW IT RETURNS ZERO

M6 derives the barrier rather than declaring it, correctly: an endothermic
decomposition whose reverse is a gas landing on a crystal has no reverse barrier,
so `Ea = dH`, and calcite comes out at 179.2 kJ/mol against a measured 170–200.
Write an EXOTHERMIC row and the same line gives **zero**.

| row | dH/kJ | derived A | what that IS |
|---|---:|---:|---|
| `metallothermic-reduction` | −851.50 | 4.15e-6 1/s | a 2.8-**day** thermite, at every temperature |
| `tenorite-carbon-monoxide-reduction` | −125.68 | 9.70e-4 1/(bar s) | 17 minutes at 298 K as well as at 1500 |

⚠ **The finding is not the size of the numbers, it is that the temperature has
left the rate law.** With `Ea = 0` there is no exponential. Thermite's entire
mechanic is that it sits in a jar until something lights it; a smelter's is that
it needs a furnace. So an exothermic row DECLARES its forward pair and still gets
its reverse by detailed balance — the direction every `ReactionTemplate` here
declares in — and `price` refuses the derivation for such a row by name.

⚠ **AND A DECLARED `Ea` BELOW `dH` IS REFUSED, WHICH IS NOT A CONVENIENCE.**
`Ea_rev = max(Ea - dH, 0)` clips, and the clip would leave `k_f/k_r` no longer
equal to `K` — the equilibrium would silently stop being the thermodynamics. The
`max` is provably inert for the derived pair (`max(dH,0) - dH >= 0` always), so
the guard only bites on a declaration. It is also `detailed_balance`'s own floor
everywhere else in this project.

### 3. THE SIX DECLARATIONS, AND THE THREE THAT NEEDED NOTHING NEW

| row | module | dH/kJ | kinetics | what it is |
|---|---|---:|---|---|
| `tenorite-carbon-monoxide-reduction` | `solid_state` | −125.68 | declared | `copper-smelting` 2 |
| `litharge-carbon-monoxide-reduction` | `solid_state` | −63.98 | declared | `lead-smelting` 2 |
| `metallothermic-reduction` | `solid_state` | −851.50 | declared | `thermite`, the whole route |
| `zincite-carbothermic-reduction` | `solid_state` | +239.97 | **derived** | `zinc-smelting` 2 |
| `boudouard-gasification` | `solid_state` | +172.45 | **derived** | `blast-furnace` 2 |
| `carbon-combustion` | `surface` | −393.51 | declared | `blast-furnace` 1, the tuyere |

⚠⚠ **`carbothermic-reduction` NEEDED NO ENGINE WORK AT ALL, AND THE QUEUE HAD
PRICED THE WRONG REACTION.** `NEXT_PROMPT` warned that `ZnO + CO -> Zn + CO2` is
**uphill at +63.3 kJ/mol** and might be `gas-solid-reduction`'s problem in a
second costume. The catalog's own row is not that reaction: it reads
`zinc-oxide + carbon-graphite -> zinc + carbon-monoxide`, and with graphite the
entropy of making a mole of CO carries it — **dG = 0 at 1264.3 K** against a real
Belgian retort's 1200–1300. Two solid reactants and one gas PRODUCT is an
ordinary row of M6's table that nobody had written. **S8 measured a row the
catalog does not contain and concluded the class was blocked.**

⚠ **AND THE SAME IS TRUE OF BOUDOUARD, WHICH IS THE ONLY DERIVED ROW WITH A GAS
REACTANT.** It is endothermic, so `Ea = max(dH,0)` is right for it and its
reverse — 2 CO laying down soot on carbon — really is the barrierless event
`RECOMBINATION_A` was calibrated as. **The gas-reactant fix and the declared-pair
fix are independent, and Boudouard needs only the first.**

### ⚠⚠ 4. THE ROUTE NOBODY DECLARES: ORE + COKE + AIR → METAL

Four declarations in two modules, none of which mentions another. They share a
solid block and a headspace:

    surface.py       CuS + O2  -> CuO + SO2     a gas at a crystal (S1)
    surface.py       C   + O2  -> CO2           the tuyere         (S9)
    solid_state.py   C   + CO2 -> 2 CO          Boudouard, reversible
    solid_state.py   CuO + CO  -> Cu + CO2      the reduction, reversible
    ------------------------------------------------------------------
    the catalog route  CuS + O2 -> CuO + SO2, then CuO + CO -> Cu + CO2

Measured on a sealed 10 L flask holding 0.04 mol of covellite and 0.20 mol of
graphite at 1500 K, with air and nothing else: **0.040000 mol of copper,
0.040000 mol of SO2, no ore and no coke left, `conservation_report` empty.** The
same for galena at 1400 K and for sphalerite at 1400 K.

⚠ **THE AIR IS THE CONTROL, WHICH IS WHAT A SMELTER ACTUALLY ADJUSTS.** On the
copper flask: 0.02 mol O2 → 29.01%, 0.06 → 80.41%, 0.10 → 99.89%, 0.20 →
100.00%. Nothing declares that curve; it is the roast running out of oxidant.

⚠⚠ **AND THE ZINC FLASK GOES *DOWN* AT 0.20 mol OF OXYGEN, WHICH NOBODY DECLARED
EITHER.** 0.032476 mol of metal at 0.06 and **0.025515 at 0.20**, with 0.014485
mol of zincite left and the coke completely gone. The reason is that
`zincite-carbothermic-reduction` and `carbon-combustion` **compete for the same
carbon**, and a blast rich enough to burn all of it leaves nothing to reduce the
oxide with. The copper and lead flasks do not do this, because their reductant is
the CO the carbon made and Boudouard keeps handing it back. **Overblowing a zinc
retort really does waste the charge, and no line in this project says so.**

⚠⚠ **S10 WITHDREW THIS PARAGRAPH'S CONCLUSION.** The competition is real, but which side won was decided by two DERIVED pre-exponentials — and making the zinc a VAPOUR moved one by 24x (`tau` 256.9 s → 10.9 s), so the reduction now takes the zincite before the blast can burn the coke. The yield is **monotone and saturating**: .0117 / .0229 / .0328 / .0400, flat to 0.50 mol O2. ⚠⚠ **THE SIGN OF THE EFFECT DEPENDED ON A CLOCK**, and it was written up here as physics. A real furnace does waste an overblown charge, for transport reasons this engine does not model. **Thermodynamic conclusions here survive a phase change in a product; kinetic ones need not.** See §S10.

### ⚠⚠ 5. THE CARRIER IS THE MECHANIC, AND IT IS THE LEAD CHAMBER'S FAILURE MODE THAT DIDN'T HAPPEN

A flask of ore and coke with **no gas in it at all** is **exactly inert** — 0.0
copper, 0.0 CO, 0.0 CO2, at the default rung, rtol 1e-6, rtol 1e-8 and rtol
1e-10. Both reactions that would run need a carbon oxide and there is none.

⚠⚠ **THAT IS THE QUESTION `chemsim-solid-gate-fix` EXISTS TO ASK.** A cycle with
gain on its own carrier is precisely the shape that let round-off seed the lead
chamber to an 89% yield on 1.2e-4 mol of phantom NOx. The reason it cannot happen
here is the FORM and not a guard: the arriving gas enters as `p ** 1` with no
denominator, so zero in is zero out with a bounded slope. A smoothstep with a
constant scale is what failed in the chamber, and there is none in this term.

⚠ **AND ONCE SEEDED THE CARRIER MULTIPLIES, WHICH IS REAL CHEMISTRY.** 1e-12 mol
of CO2 — **one part in 1e11 of the charge** — reduces the whole 0.10 mol of
oxide. Boudouard makes 2 CO out of 1 CO2 and the reduction hands one CO2 back, so
the cycle gains a carrier per turn; a blast furnace's gas volume really does grow
that way. **The carbon is the reagent and the carbon oxide is only the vehicle**,
which is why a furnace is charged with coke.

### 6. THERMITE — THE ONLY ROW IN EITHER SOLID TABLE WITH NO GAS AT ALL

Four crystals, no gas, so both one-sided pressure products are empty (exactly
1.0) and the affinity collapses to `k_f - k_r`, a constant. That is correct: with
no gas there is no quotient to move, so at ln K +29.5 the row is effectively
irreversible and runs to completion. One pin, on the reported 1200 K ignition
temperature, buys a column nothing was fitted to:

| T / K | conversion in 600 s |
|---:|---:|
| 298.15 | **0.0000%** — exactly zero |
| 600 | 0.0000% (3.1e-10 mol) |
| 800 | 0.2171% |
| **933** | **36.95%** — ⚠ **and this is where ALUMINIUM MELTS** |
| 1000 | 98.16% |
| 1200 | 100.00% |

⚠ 933 K is the trigger every account of thermite names, and nothing in this
engine knows it: the column is one Arrhenius pair.

⚠ **AND AN INSULATED FLASK IGNITES ITSELF.** The energy balance was already
there; 851.5 kJ/mol into a few J/K is a runaway nobody declared. Cold and
insulated it stays at 298.15 K to six figures and makes nothing; lit at 1000 K
it goes to 100% and the rise is the arithmetic — **+322.45 K** measured against
+323.86 predicted on a 50 J/K flask, +33.87 against +33.88 on a 500 J/K one.

⚠ **STATED LIMITATION: NOTHING CAPS THE TEMPERATURE.** A real thermite stops near
3135 K because the IRON BOILS, and a lattice in this engine may react and may
never boil. A 1 J/K flask reports 5469 K — above the RHS's own `T_MAX` clamp of
5000, which bounds RATE evaluation and not the state. **It is the same statement
the zinc retort makes** (below), and it is the honest cost of the one-boolean
lattice.

### ⚠ 7. THE ZINC RETORT KEEPS ITS THERMODYNAMICS AND LOSES ITS DISTILLATION

`mineral_data` holds zinc as a lattice, `thermo.get("[Zn]")` refuses the
monatomic vapour as a bare element, and a lattice here may react and may never
boil. So the row makes **solid** zinc, and the product removal that pulls a real
retort over is not expressible.
⚠⚠ **S10 CLOSED THIS, AND THE SENTENCE ABOVE IS WHY IT LOOKED HARD: it is about the `mineral_data` ENTRY, not about zinc.** `[Zn]` passes every test S4 admitted mercury on, so it moved to `element_data`, the row evolves a VAPOUR, and the threshold came DOWN to 1197.8 K — **with no engine change at all.** See §S10. ⚠ **The row does not need it**: ln K is already
+2.21 at the catalog's own 1400 K. Vented, the threshold is measured where the
thermodynamics put it — 3.61% at 1100 K, 29.44% at 1200, **87.05% at 1264**,
99.96% at 1300, 100% at 1400.

### ⚠⚠ 8. `carbothermic-reduction` WAS AN OUTCOME LABEL AND WAS SPLIT — AND THE ROW CHECK COST NOTHING THIS TIME

Five rows, **four mechanisms**, and only the oxide one is built. Crediting the
class on it would have claimed routes to calcium carbide and to white phosphorus
that this engine cannot make — `roasting-to-metal`'s false credit in a fourth
costume. See `data/catalog/README.md`. The split moves the denominator (224 →
227) and costs no route, because none of the other four was covered.

### ⚠ 9. AND THE INSTRUMENT AUDIT FOUND A FALSE CITATION FOUR MILESTONES OLD

`surface.ROASTING_A`'s pinning comment has ended *"validation/rate_ceiling.py
re-measures it"* since S1. **It did not.** `rate_ceiling` walks `net.reactions`,
and a `SurfaceReaction` never becomes a `Reaction`; S4 found the identical fault
about `SOLID_STATE_REACTIONS` and added a panel, and this table was left out —
with the sentence claiming otherwise sitting right beside the constant. S9
tripped over it while writing the same sentence for a new one.
`rate_ceiling.surface_panel` now reads it: every pre-exponential in the table is
**below the collision limit outright**, so no row can cross at any temperature.
⚠ And the units had to be the BIMOLECULAR ceiling, not the unimolecular one that
panel above it uses — a surface rate is order 1 in one gas, in L/(mol s). That is
M8's unit error, avoided by naming the order.

### 10. WHAT IS REFUSED, MEASURED RATHER THAN ASSUMED

* **`direct-combination`** (`vermilion-route`: `Hg + S8 -> HgS`) was on the queue
  as *"probably"* part of this work. It is not: mercury is a curated LIQUID
  element and S8 is a MOLECULAR solid, and `build_surface_arrays` refuses a
  non-lattice solid by name because `PhaseArrays.lattice` cannot answer "how much
  solid is there" for a species with a solid block AND a liquid block AND a
  headspace. Neither table's shape. **Still one class away and still not this.**
* **`blast-furnace`** gains three of its five classes and is still not
  template-ready: `slagging` has no template (and `silicon-dioxide` /
  `calcium-silicate` have no lattice), and both `gas-solid-reduction` rows in it
  need an `iron-ii-oxide` `mineral_data` refuses on the crystal Cp. **One class
  and one mineral away** — the closest any five-step route has been.
* **`carbon-combustion`'s ln K at 2200 K is +21.87 against a bar of +20**, the
  tightest row in `SURFACE_REACTIONS` by 46 nats. Not a marginal constant: above
  ~1000 K carbon dioxide over carbon is increasingly taken to CO, so this
  reaction's own product stops being the stable one. **The reversal is declared
  next door**, and nothing connects the two but a shared headspace.

**Files:** `src/chemsim/numerics/vessel_integrator.py` (the split, ~30 lines with
its argument), `src/chemsim/properties/solid_state.py` (+2 optional fields, two
guards, five rows, two constant blocks), `src/chemsim/properties/surface.py`
(+2 optional fields, one guard, one row, two constants, the false-citation note),
`src/chemsim/vessel/vessel.py` (the refusal lifted), `validation/smelting.py`
(new, 8 panels), `validation/rate_ceiling.py` (`surface_panel`),
`validation/catalog_coverage.py` (5 classes), `data/catalog/route_steps.psv`
(5 rows re-labelled), `tests/test_smelting.py` (new, 20 tests),
`tests/test_solid_state.py` (5 rewritten, 4 new), `tests/test_surface.py`
(2 rewritten), `data/catalog/README.md`, `README.md`, `COVERAGE_REPORT.md` and
both `derived/*.psv` (regenerated, byte-identical across `PYTHONHASHSEED`).

---

## S10 — A metal that vaporises  ✅ **DONE 2026-08-26 — the engine queue's top item was HALF a data job, and separating the halves is what located the engine gap**

**+0 classes, +0 template-ready, +0 species-ready, +0 RUNNABLE — all four
predicted before the audit ran, and all four came out.** This is an honesty and
mechanic milestone and it was taken as one. What it buys is a **zinc retort that
distils**, three corrected instruments, and an engine gap that is now one
sentence instead of two.

| | before | after |
|---|---:|---:|
| classes with a template | 48 / 229 | 48 / 229 |
| routes template-ready | 38 / 173 | 38 / 173 |
| routes species-ready | 77 / 173 | 77 / 173 |
| routes BOTH — the one to quote | **28** | **28** |

⚠ **NO ENGINE CODE CHANGED.** Not one line of `numerics/` or `vessel/`. The
existing evaporation and melt terms do all of the work below.

### ⚠⚠ 1. "A LATTICE MAY REACT AND MAY NEVER BOIL" WAS A STATEMENT ABOUT AN ENTRY

S9 handed this forward as the plan's top engine item, and as ONE gap covering two
symptoms: the zinc retort makes solid zinc, and nothing caps thermite's
temperature. Both cited the same sentence. **They are not one gap**, and the
pairing is what hid the real one.

Zinc's half needed no engine work at all. `mineral_data` held zinc as a lattice,
so `PhaseArrays` gave it `vol_A` = 1e-30 bar and `solidifies` = False — but that
was a property of the ENTRY. Measured against S4's own three tests for admitting
mercury, zinc passes all three:

* **the atom IS the vapour** — zinc boils monatomic at 1180.15 K (group 12,
  closed d10 s2, so there is no Zn2 to be wrong about), so `[Zn]`'s ideal-gas
  record is what is in the retort;
* **there is nothing to disambiguate** — zinc has ONE condensed form, which is
  what fails for `[S]`, `[C]` and `[Fe]`;
* **and its reference state is expressible** — a SOLID with a melting point.
  ⚠ Mercury passed this one on the liquid block; zinc passes it on the SOLID
  block, which this table already relied on twice for I2 and S8. **A solid
  reference state is not a new thing here.**

So `[Zn]` went into `element_data` and out of `mineral_data`, and the retort row
became `ZnO + C -> Zn(g) + CO`. One edit to a tuple.

### ⚠⚠ 2. THE VAPOUR PRESSURE IS ALGEBRA, NOT A FIT, AND IT HAS FOUR INDEPENDENT CHECKS

Lee-Kesler has no domain over a liquid metal — S4 measured it 3.8x high for
mercury at 523 K — so zinc needed a curated curve for mercury's reason. Alcock,
Itkin & Horrigan (1984), the standard compilation for exactly this problem,
publish the liquid range as **two constants**:

    log10(p / atm) = 5.378 - 6286 / T          692.677-1180 K

With C = D = 0 that IS Antoine form with C = 0, so the conversion is a change of
base and of pressure unit and **nothing is fitted** — and the round trip
reproduces Alcock's own published 5.378 / 6286 to four figures. The two forms
agree to 4e-15 over 700-3000 K.

⚠⚠ **AND ALCOCK'S FIT IS NOT ANCHORED AT Tb, WHICH MAKES THE BOILING POINT A
REAL CHECK HERE.** `chemsim-physical-data-sourcing` records that "boils at 1 atm"
is NOT independent for a Lee-Kesler curve, because ω is inverted at Tb precisely
to make it pass. Alcock's fit was made over 692.7-750 K and never saw Tb, so
where it lands the boiling point is genuine evidence. **The same trap, read from
the other side.** Four checks, and CRC never meets Alcock in any of them:

| check | result |
|---|---|
| `Gf(g) + RT ln(Psub/P0) = 0`, on the SUBLIMATION curve at 298 K | **-0.184 kJ/mol** (Br2 -0.053, Hg +0.012, I2 +0.139, S8 +3.052) |
| Alcock's sublimation SLOPE vs CRC's Hf(g) = 130.400 | **130.674, +0.21%** |
| the unanchored boiling point | **1168.84 K vs 1180.15, -0.96%** |
| the sublimation and liquid fits meeting at the triple point | **+0.103%** |

⚠ The derived `Gf(g)` is **94.801 kJ/mol** against CRC's tabulated 95.2, -0.42%.
⚠ Tc/Pc/Vc are YAWS only — the **compilation** tier — and are stamped as such;
they reach nothing but the Watson factor and Rackett/Rowlinson-Bondi.
⚠ And the price of taking Hvap from the curve the engine evaluates (which is this
project's rule) is that Alcock's two-constant fit measures the latent heat NEAR
THE MELTING POINT: 120.344 kJ/mol against CRC's 115.3 at Tb, **+4.4%**. Taking
CRC's instead would put two tabulations in one record. Stated, not corrected.

### ⚠⚠ 3. THE RETORT'S THRESHOLD MOVED 66 K, TOWARD THE LITERATURE

Carrying the zinc as a vapour adds its sublimation energy and its entropy to the
row, and the entropy wins:

    Zn(s) product, S9    dH +240.0 kJ/mol   dS +189.8   dG = 0 at 1264.2 K
    Zn(g) product, S10   dH +370.4 kJ/mol   dS +309.2   dG = 0 at 1197.8 K

against a real Belgian retort's 1200-1300 and a literature threshold of ~1200 K.

⚠ **AND THE BARRIER WENT UP BY THE SAME 130.4 kJ/mol**, because M6 derives it as
`max(dH, 0)`. 370.4 kJ/mol is inside the 300-400 range reported for apparent
activation energies of carbothermic zinc reduction, so the derived barrier is
defensible rather than merely arithmetic. ⚠⚠ **The row is nevertheless FASTER**,
because an Arrhenius pair is not separable: the derived `A` carries `exp(dS/R)`,
and at 1400 K `exp(119.4/R) = 1.7e6` beats `exp(-130400/RT) = 1.4e-5` by ~24x.
**tau went 256.9 s -> 10.9 s.** The equilibrium is untouched — both directions
scale by one factor — and `rate_ceiling` says the new A is still under the limit.

### ⚠⚠ 4. THE DISTILLATION, AND TWO MECHANICS NOBODY DECLARED

A sealed 1 L retort at 1400 K: **0.040000 mol of zinc, every atom in the
headspace**, no ore and no coke left, conservation clean. Cool the receiver and
it comes back:

     T/K       Zn(g)       Zn(l)       Zn(s)
    1400    0.040000    0.000000    0.000000    <- the burn
    1180    0.011596    0.028404    0.000000
     900    0.000335    0.039665    0.000000
     600    0.000000    0.000000    0.040000

**Tb = 1180.15 K and Tm = 692.68 K appear in no declaration and in no script.**

⚠⚠ **AND THE VENT DOES NOTHING UNTIL THE RETORT BEATS THE ROOM.**
`solid_state_report` computes 1156 K for this row's two evolved gases to reach one
bar between them. Measured, sealed against vented: **12.29% / 12.29% at 1150 K**
(sealed pressure 0.9325 bar) and **13.52% / 18.63% at 1156 K** (1.0312 bar),
rising to 25.67% / 99.84% at 1198 K. A derived van 't Hoff number and a flask
that was actually run, agreeing to the degree.

⚠⚠ **AND A VENTED RETORT BLOWS ITS OWN PRODUCT UP THE CHIMNEY.** Once the product
is a gas, the vent that pulls the reaction over carries the metal away, so the two
numbers a smelter cares about come apart and move in OPPOSITE directions:

     T/K   ore consumed   metal kept   up the flue
    1200         99.91%       51.04%        48.87%
    1400        100.00%       43.53%        56.47%

**That is why a real Belgian retort has a condenser hanging off it**, and it is
why the threshold panel is run SEALED. ⚠ `conservation_report` is silent
throughout, correctly: the vent is a declared boundary flux. *An invariant
measured across a boundary flux is not an invariant.*

### ⚠⚠ 5. AND S9's OVERBLOWING FINDING IS GONE — IT WAS A RATE ARTEFACT PRESENTED AS PHYSICS

S9 measured the zinc smelter's yield going DOWN at 0.20 mol O2 (0.032476 at 0.06
against 0.025515 at 0.20) and wrote: *"Overblowing a zinc retort really does waste
the charge."* The competition it identified is real — the carbothermic reduction
and the tuyere DO want the same carbon, and copper and lead do not, because their
reductant is the CO the carbon made and Boudouard hands it back.

**What decided the race was two derived pre-exponentials, and §3 moved one of them
by 24x.** The reduction now takes the zincite before the blast can burn the coke,
and the yield is monotone and saturating:

    O2/mol   0.02    0.04    0.06    0.10    0.14    0.20    0.50
    Zn/mol  .0117   .0229   .0328   .0400   .0400   .0400   .0400

⚠⚠ **THE SIGN OF THE EFFECT DEPENDED ON A CLOCK.** A real furnace does waste an
overblown charge, for transport reasons this engine does not model, so the old
panel read like a prediction and was a coincidence of two rate constants.
**Thermodynamic conclusions here survive a phase change in a product; kinetic ones
need not.** New rule, and it is the sharpest thing in this session.

### ⚠⚠ 6. THE ESTIMATOR WAS RETURNING A NEGATIVE HEAT CAPACITY, AND MERCURY HAD CARRIED IT SINCE S4

Found by walking into it: `CondensedProvider.get` fits Rowlinson-Bondi over a
**hardcoded 250-450 K** and every caller takes the default — an organic-solvent
window. For a metal that is a LIQUID correlation evaluated where there is no
liquid, then extrapolated into the range where there is one:

    mercury (liquid 234-630 K)   -25.26 at Tm, -12.62 at 298 K, +22.45 at Tb
                                 against a real 27.98
    zinc    (liquid 693-1180 K)  +34.84 at Tm, +462.51 at Tb (15x)
                                 against a real 31.38

⚠ **A negative Cp is not an accuracy problem — adding heat to that liquid LOWERS
its temperature — AND IT WAS REACHABLE.** The default glassware is 50 J/K, so a
flask holding more than **3.96 mol of liquid mercury (795 g, 59 mL)** had a
NEGATIVE TOTAL thermal mass. Measured at 5 mol: **-12.808 J/K.**

Both are replaced by measurement, and both measurements are unusually clean:
mercury from CRCSTD 28.000 / VDI 28.031 / thermo Fit-2023 27.976 — **three
sources inside 0.2%** — and zinc from the WebBook Shomate liquid curve, whose
validity window is 692.73-1180.17 K, i.e. **exactly zinc's liquid range**, flat at
31.380 across all of it.

⚠⚠ **THE GENERAL FAULT IS REPORTED AND NOT FIXED, AND IT IS LARGE.** Swept over
`data/catalog`: **103 compound rows still return a negative liquid Cp somewhere
inside their own liquid range** and 41 more swing over 5x across it — worst,
carminic acid at **-21482 J/(mol K)**. Most of those have a JOBACK-estimated
Tm/Tb that is itself meaningless (carminic acid "melts" at 1398 K and really
decomposes), which is what made the two metals the clean cases: their transition
temperatures are MEASURED and the Cp was still wrong. ⚠ And it bites at BOTH ends
— ethylene reads ~1574 J/(mol K) at its 113.9 K melting point. Nothing runs a
flask there today, so this is a LATENT fragility: reported, not refused.

⚠ Measured cost of the fix on the pinned example: `examples/mercury_retort.py`
moves by **one digit in the ninth decimal** (0.012636665 -> 0.012636666), 1 part
in 1e8.

### ⚠⚠ 7. TWO MORE INSTRUMENTS WERE WRONG, AND ONE INVENTED A 90 kJ/mol FINDING

* **`validation/game_gates.py` printed a residual whether or not the shift it
  differences had been applied.** `standard_state.shift` REFUSES a shift whose
  298 K vapour pressure is under `PSAT_FLOOR_BAR` = 1e-12 — correctly, since the
  correlation is then extrapolated far past its data — and returns `dGf = 0.0`
  with a reason. Differencing that zero printed **"zinc, residual +90.78 kJ/mol"**
  for a formation pair that is fine. ⚠ An INSTRUMENT-GENERATED FINDING, which is
  S2's fault in a new place, and every other row has an applied shift, so the
  hole was unreachable until a solid with a 2e-16 bar vapour pressure arrived.
  The panel reports REFUSED with the reason now, and gives zinc the check it CAN
  have — the sublimation route, one step, no Hfus term, **-0.184 kJ/mol.**
* **`volatility._CURATED_ANTOINE` stamped every entry `NIST WebBook`.** True of
  all nine rows and false the moment a tenth came from Alcock. ⚠ **That is the
  shape S9's false citation had: correct when written, silently wrong after the
  next addition.** Per-entry overrides now, in `volatility` and in `condensed` —
  where the shared strings claimed "at 298 K" for a zinc liquid volume taken at
  700 K, because zinc is a solid at 298 K.

### ⚠⚠ 8. IRON IS REFUSED, AND THAT REFUSAL IS WHERE THE ENGINE GAP ACTUALLY IS

Thermite's cap is the other half of S9's item, and it does NOT yield to the same
move. **The data is nearly there and the mechanism would work:** Alcock's liquid
equation converts to Antoine exactly (A = 6.352717, B = 19574, C = 0) and
unanchored puts Tb at 3083.98 K against 3134.15 measured, **-1.60%**; that curve's
slope gives Hvap = 374.7 kJ/mol, so boiling the 2 mol of iron a mole of thermite
makes would absorb **749.5 of the 851.5 kJ it releases, 88.0%**. Three counts
against, measured rather than assumed:

1. ⚠⚠ **IRON CANNOT LEAVE `mineral_data` THE WAY ZINC DID.** It is a declared
   `solid_catalyst` — `ammonia_synthesis(catalyst="iron")`, resolved through
   `MINERALS["iron"].lattice` — as well as thermite's own solid product. So iron
   has to be BOTH a `mineral_data` lattice and a `thermochemistry` gas, and
   `PhaseArrays.lattice` is one boolean picking both a species' basis and its
   destination block. **Zinc never needed that: nothing else referenced its
   lattice entry.** This is the engine gap, and it is smaller and sharper than
   the one S9 handed forward.
2. `[Fe]` fails S4's **disambiguation** test, which `[Zn]` passes: three solid
   allotropes with two transitions inside thermite's own temperature range, and
   `dCp = 0` with a single Tm/Hfus cannot represent them. `element_data`'s own
   refusal list already names `[Fe]` beside `[C]` and `[S]` for this.
3. **ONE cross-check, not four.** Alcock tabulates no sublimation curve for iron,
   so the 298 K reference-state identity zinc closed at -0.184 kJ/mol cannot be
   evaluated at all.

⚠⚠ **CORRECTION, MEASURED AFTER THIS SECTION WAS WRITTEN — COUNT 1 ABOVE
OVERSTATES THE COST, AND NEXT_PROMPT ENGINE QUEUE ITEM 1 CARRIES THE MEASUREMENT.**
Patching iron's volatility in place and running thermite insulated CAPS it
(5469.43 → 3490.99 K at 1 J/K, conservation clean, and the 50 J/K flask
identical because it never reaches Tm). Three things count 1 got wrong:
`PhaseArrays.lattice`'s two hot-loop uses are in the SURFACE term only and **iron
is in no surface row**, so `C_mix[Fe] ** 0 == 1.0` exactly and they are inert;
the Haber catalyst reads `order_solid`/`nS` and **never depended on the flag** —
what needs `MINERALS["iron"]` is NAME RESOLUTION, which is separable from
volatility; so the real blocker is **one branch in `build_phase_arrays`** pinning
`NONVOLATILE_A`/`solidifies = False`, i.e. a setup-layer change with **no RHS
edit**. Counts 2 and 3 stand and are the reason this is still not done: they are
DATA objections, and the engine fix does not touch them. **The general
one-boolean-two-jobs form is still worth fixing** — and note
`build_surface_arrays` already splits `order_solid`/`order_gas` from the
declaration and then throws the `nu` split away.

### 9. WHAT THE FUSION LAW DOES TO A METAL IN WATER, MEASURED BEFORE IT WAS ACCEPTED

`solidifies = True` exposes zinc to the ideal fusion-law solubility, and zinc has
no UNIFAC groups so its gamma is 1. Measured at 298 K, x_sat = 0.197 — 89 g/100 mL
against a real ~1e-8. ⚠ **That wrongness is PRE-EXISTING and shared**, which is
why zinc joining it is consistent rather than new: iodine is over by **1.5e4x**
and sulfur by **1.1e8x** on the same law, and zinc's mole fraction (0.197) is
SMALLER than iodine's (0.238), sulfur's (0.275) or naphthalene's (0.302). It is
reachable only by putting metal in water, which no route does. Reported.

### 10. THE SMALL THINGS

* `data/catalog/derived/species_roles.psv` moves zinc from the `mineral`
  provenance tier to **`measured`**, which is an upgrade in the audit's own terms.
* All three catalog artefacts regenerated and byte-identical across
  `PYTHONHASHSEED` 0 / 1 / 12345.
* ⚠ Three separate pieces of prose had rotted inside this session's own edits:
  the audit's overblowing paragraph, its "a lattice against three curated gases"
  (the row now has two of each), and its "the same statement the zinc retort
  makes". **A generated file's prose rots exactly like a hand-written one**, and
  so does an audit's.
* ⚠ `validation/smelting.py` is **CRLF**, contrary to the handoff's note that the
  newer `validation/*.py` are LF. Check, do not assume.
* ⚠ The cp1252 trap again, twenty-fifth session running — a warning glyph inside
  a `print()` in a scratch probe.

⚠ **THE SUITE: 932 passed / 0 failed in 13:20**, run after every `src/` edit — a
real baseline rather than arithmetic, which is the first time in four sessions.

**Files:** `tools/build_element_data.py` (`REFERENCE_SMILES` +Zn with the
argument, `LATTICE_ELEMENTS` -Zn, `CANDIDATES` +Zn),
`tools/build_mineral_data.py` (`ELEMENT_SOLIDS` -zinc),
`src/chemsim/properties/element_data.py` and `mineral_data.py` (regenerated),
`src/chemsim/properties/volatility.py` (Alcock entry + `_CURATED_SOURCE`),
`src/chemsim/properties/condensed.py` (two liquid Cp, two liquid volumes, two
source-override tables), `src/chemsim/properties/solid_state.py` (the retort row
evolves a vapour), `validation/smelting.py` (panel 6 rewritten, panel 6b new, the
iron refusal), `validation/game_gates.py` (the `applied` bug + zinc's sublimation
check), `validation/catalog_coverage.py` (the S8 paragraph), `tests/test_smelting.py`
(+3 tests, 3 rewritten), `tests/test_element_solids.py`, `tests/test_element_data.py`
(+3 tests), `tests/test_phase_properties.py` (+2 tests), `tests/test_solid_state.py`,
`data/catalog/COVERAGE_REPORT.md` and `derived/species_roles.psv` (regenerated).

---

## S11 — Two competing templates, an ion for a catalyst, and a hand-typed list  ✅ **DONE 2026-08-26 — the coverage queue's two best rows, plus the discovery that a species is estimated because nobody typed its name**

**+2 classes, +2 template-ready, +0 species-ready, +2 RUNNABLE — all four
predicted before the audit ran, and all four came out.** Two content classes off
the queue, one instrument fault CLOSED (engine queue item 6), and one new
honesty item that is larger than either of them.

| | before | after |
|---|---:|---:|
| classes with a template | 48 / 229 | **50 / 229** |
| routes template-ready | 38 / 173 | **40 / 173** |
| routes species-ready | 77 / 173 | 77 / 173 |
| ⚠⚠ **routes BOTH — the one to quote** | **28** | **30** |
| templates | 43 | **45** |

⚠ **NO ENGINE CODE CHANGED AGAIN.** Not one line of `numerics/` or `vessel/`,
for the second milestone running. Everything below is declarations, data, and
one instrument.

### ⚠⚠ 1. THE OXO PROCESS — TWO TEMPLATES THAT RACE, AND THE THERMODYNAMICS POINT THE WRONG WAY

`hydroformylation` is the first class here whose two catalog rows are ONE
reaction with TWO regiochemistries — `butyraldehyde` and `isobutyraldehyde` from
the same reactants, the second row's own condition column reading "same reactor,
n:iso selectivity". One template cannot cover it, and the pair is the mechanic.

⚠⚠ **AND THE INTERESTING PART IS THAT THE ENGINE'S OWN TABLES SAY THE BRANCHED
PRODUCT SHOULD WIN.**

    propene + CO + H2 -> butanal            dH -113.73   dG298 -38.72   K(420) 10.08
    propene + CO + H2 -> 2-methylpropanal   dH -123.08   dG298 -43.54   K(420) 23.52

The branched aldehyde is **9.35 kJ/mol more exothermic** and takes 2.33 of every
3.33 molecules at equilibrium. The real reactor makes the LINEAR one, four to
one. **The oxo process is under kinetic control and running against its own
thermodynamics**, which is why the aldehyde industry wants has to be taken out of
a reactor rather than waited for.

⚠⚠ **SO EVANS-POLANYI HAD TO BE SWITCHED OFF, AND THAT IS A DECLARATION.** `alpha`
scales the barrier with dH, so **any** transfer coefficient above zero hands the
more exothermic branched route the lower barrier and names the wrong major
product with confidence. `alpha=0.0` on both, and a test asserts it.

**ONE NUMBER IS FITTED**: a 4.8 kJ/mol barrier difference, chosen so
`exp(dEa/RT)` is 4.0 at the catalog row's own 420 K. Everything else is a
consequence, and the consequences were measured:

| what | measured |
|---|---|
| the reactor, 1 L at 200 bar / 420 K / 0.1 mol cobalt / 1 h | **94.3% converted**, n:iso **3.952** |
| n:iso against `exp(dEa/RT)` at 380 / 400 / 420 / 450 K | 4.569 / 4.234 / 3.952 / 3.543 against 4.569 / 4.235 / 3.953 / **3.607** |
| ⚠ and at 480 / 520 K | **1.867 / 0.760** against a pure kinetic 3.329 / 3.035 |
| the cobalt gate | 0 mol -> **exactly zero**, and 0.001 / 0.01 / 0.1 / 0.5 mol are a first-order knob |

⚠⚠ **NOBODY DECLARED A MAXIMUM OPERATING TEMPERATURE AND THE FLASK HAS ONE.** Up
to ~450 K the selectivity IS the exponential, to three figures. Above it the two
REVERSE reactions get inside the reactor's own hour and the stable branched
product starts winning; the conversion turns over in the same place. **A real
cobalt oxo reactor sits at 410-450 K.**

### ⚠⚠ 2. REVERSIBLE, AND THE ALTERNATIVE WAS MEASURED RATHER THAN ARGUED

Three moles of gas become one, so this equilibrium turns over on heating: ln K is
+2.31 at 420 K and **-7.46 at 600**. `alkene_hydrogenation` argues that
irreversibility is "a claim about temperature rather than about thermodynamics",
and that argument does not transfer here — retro-hydroformylation is real and
industrial. Measured, one hour, each temperature's own charge:

| | 1 bar, reversible | 1 bar, IRREVERSIBLE | 200 bar, reversible |
|---|---:|---:|---:|
| 420 K | 0.469% | 0.470% | 93.1% |
| 500 K | 1.475% | 20.202% | 91.0% |
| **600 K** | **0.013%** | **77.933%** | 53.3% |

**A factor of ~6000 at 600 K and 1 bar, on a flask a player can build.** And the
200 bar column is the process: pressure buys back what heat costs, because three
moles become one.

### ⚠⚠ 3. AND THE PAIR CROSSES FROM KINETIC TO THERMODYNAMIC CONTROL ON ITS OWN

Nothing declares a crossover. The two templates share a reactant, detailed
balance supplies both reverses at `Ea - dH` (209.7 and 223.9 kJ/mol, nobody typed
either), so the kinetic product is eaten by the stable one through propene:

    t          1 h     10 h    4 days   6 weeks   1 year   11 years   settled
    n:iso     3.952   3.944    3.863     3.204     1.188     0.513     0.513
    GAS       3.304   3.296    3.229     2.678     0.993     0.4286    0.4283

⚠⚠ **AND THE LAST TWO ROWS DISAGREE, WHICH IS ALSO CORRECT AND ALSO UNDECLARED.**
`K(n)/K(iso)` is **0.4283** and the HEADSPACE lands on it to four figures. The
flask's INVENTORY ratio settles at **0.513**, because at 200 bar and 420 K this
reactor holds ~1.7 mol of LIQUID product and butanal (Tb 347.95 K) is the less
volatile of the two, so it hides in the layer. **A real cobalt oxo reactor is a
liquid-phase process for exactly this reason, and nothing asked for a two-phase
reactor — it is what a 200-bar charge of those five species IS.**
⚠ **AN EQUILIBRIUM CONSTANT IS A STATEMENT ABOUT PARTIAL PRESSURES. Read it
against the headspace, never against the inventory.**

### ⚠⚠ 4. THE WACKER PROCESS — THE FIRST TEMPLATE WHOSE CATALYST IS AN ION

`wacker-process` writes `copper-ii-ion` on both sides of its only row, which is
`library._maybe_catalyse`'s own case — except that `[Cu+2]` is priced from
`ion_data` and `thermochemistry` refuses a charged species by name. **So the gate
this template carries is not "did you add the catalyst" but "is there a SOLVENT
for it to be an ion in."** A flask built without `electrolyte_provider()`
REFUSES; it does not run slowly.

⚠ **AND IT REFUSES AT THE VESSEL, NOT AT THE NETWORK.** `build_network` succeeds
and names `[Cu+2]` as a species, because a network is a GRAPH question; pricing
happens one layer down in `build_phase_arrays`. That is the layering working, and
the message names the ion and says what to do.

Measured: 1 L of water, 0.02 mol Cu(II) as the chloride, 0.20 mol each of
ethylene and oxygen above it, 400 K — **40.1% converted in one minute, 98.2% in
ten**, against a real one-stage Wacker's 30-40% per pass on minutes of residence.
Copper out = copper in, to 1e-12. Carbon closure exact.

⚠ **AND THE COPPER LOADING IS A FIRST-ORDER KNOB THAT IS ACTUALLY RIGHT.** The
site balance M10 is missing is a statement about a SURFACE; there are no sites to
saturate in a chloride liquor. This is the one place the project's catalysis is
on firmer ground than its heterogeneous templates.

### ⚠⚠ 5. ONE THING IN THE WACKER TEMPLATE IS DELIBERATELY WRONG, AND IT IS MEASURED

The real Wacker rate law is first order in the alkene, first order in palladium
and **ZERO order in oxygen** — the O2 only reoxidises the copper(I) and never
appears in the rate-determining hydroxypalladation. This template declares FIRST
order in oxygen. **The reason is mechanical rather than chemical**: the kinetics
kernel has no availability gate (`_avail` serves the solid block only), so a
reactant at order zero keeps reacting after it runs out and is driven negative.
`hydrogen_sulfide_combustion` keeps one O2 slot at order 1 for the same reason.

The cost, measured rather than described — acetaldehyde in 60 s against O2
charged: **0.05 -> 1.00x, 0.10 -> 1.92x, 0.20 -> 3.53x, 0.40 -> 5.85x.** A real
reactor would give 1.00 throughout. Right at LOW oxygen, wrong at high, same
shape as the missing site balance.

⚠ What IS declared correctly is the alkene order: the SMARTS consumes two
ethylenes to balance one O2, so mass action would make it SECOND order in the
alkene. `orders=(1.0, 0.0, 1.0, 1.0)` puts it back to first, which is the
measured law. A declared order may never be reversible, and here that costs
nothing: ln K is +129 at 400 K.

### ⚠⚠ 6. **A SPECIES IS ESTIMATED BECAUSE NOBODY TYPED ITS NAME — 310 OF THEM**

The biggest thing in this milestone, and it was found by a failing reactor rather
than by an audit. `physical_data.py` is GENERATED, and what it is generated FROM
is `CANDIDATES` in `tools/build_physical_data.py` — **a hand-typed list of 33
names.** Everything not on it falls to Joback, whether or not a measurement
exists.

Propene was not on it. So the oxo reactor's own feedstock read **Tb 264.92 K
against a measured 225.53 and Tc 427.64 against 364.21**, both ~17% high — and
`chemicals` holds five independent experimental sources for that boiling point
(HEOS, CRC_ORG, COMMON_CHEMISTRY, WEBBOOK, YAWS, agreeing inside 0.5 K).

⚠⚠ **AND THE Tc ERROR WAS NOT COSMETIC.** An oxo reactor sits at 420 K, which is
55 K ABOVE propene's real critical temperature and 8 K BELOW Joback's — so the
engine condensed **0.91 mol of "liquid propene" into a supercritical flask**, the
reactor read 167 bar where it was charged to 200, and the extra stiff phase left
**2.8e-24 mol of butanal in a species with no source at all**. One line in a
candidate list removed all three: 200.00 bar exactly, no liquid, and the
zero-cobalt gate reads exactly 0.0.

**THE GENERAL CASE, MEASURED OVER THE WHOLE CATALOG:**

| | |
|---|---:|
| catalog species with a graph | 1539 |
| in `physical_data.MEASURED_PHYSICAL` | **33** |
| no CAS resolvable | 1070 |
| CAS but genuinely no experimental Tb | 126 |
| ⚠⚠ **experimental Tb available and NOT in the table** | **310** |
| ...of those, PRICE a Tb in this engine today | **229** |
| mean / median / worst \|error\| against the measurement | **5.81% / 2.94% / 84.89%** |
| over 2% / 5% / 10% / 20% | 138 / 70 / 34 / 11 |

The worst: arachidonic acid 819.35 against 443.15, dinitrogen tetroxide 503.28
against 294.30, linolenic acid 769.43 against 504.15, **ethylene 234.56 against
169.38**.

⚠⚠ **AND THE INSTRUMENT THAT MEASURED IT WAS WRONG FIRST, AS USUAL.** The first
run said 360 and listed *borane* boiling at 2823 K and *methane* at 4273. Cause:
`chemicals.CAS_from_any("C")` reads a bare SMILES as a FORMULA, so `C` resolved
to carbon and `B` to boron. `CAS_from_any("smiles=C")` gives methane, and the
count fell to 310. **A single-letter SMILES is also an element symbol.**

### ⚠⚠ 7. FOUR RECORDS WERE OVERRIDDEN AND A GUARD HAD TO BE REWRITTEN TO ALLOW IT

`test_the_measured_table_never_overrides_a_working_joback_record` failed, and it
was RIGHT to: propene, ethylene, butanal and 2-methylpropanal all resolve fully
through Joback. But that rule was a SCOPING decision, not a physics claim — the
milestone that wrote it was closing a coverage gap and deliberately did not
relitigate accuracy on species that already worked. Its own stated reason ("the
moment it stops being true the azeotrope, the boiling points and the crop sizes
all move at once") **is a call for measurement, not a reason never to do it.**

So the guard now names WHICH records were overridden, and still refuses any it
does not name — `DELIBERATE_OVERRIDES`, with a second test asserting no stale
entries. **The cost was measured example by example before any entry was kept:**
propene, butanal and 2-methylpropanal appear in NO example and move nothing;
ethylene appears in two, and `competing_pathways`'s worst moved number is
0.20380 -> 0.20485 (**0.5%**) with `named_routes` reporting ethanol-hydration at
**2.7% instead of 2.9%**.

⚠⚠ **AND THE PREDICTION ETHYLENE'S ENTRY WAS MADE ON WAS WRONG.** The brief was:
a Wacker flask dissolves 83% of its ethylene charge, the whole process is that a
gas must dissolve before meeting the copper, so a measured boiling point should
move it. **Measured after: 0.16588 -> 0.16596. Four significant figures
unchanged** — because ethylene's vapour pressure comes from
`volatility._CURATED_ANTOINE` and **Tb does not feed that curve at all.** What
the entry corrects is Tc, Tm and Hvap.

⚠⚠ **AND THE 83% IS REAL AND IS A SEPARATE FAULT, REPORTED NOT FIXED.** Ethylene
is a CONDENSABLE species here, so its solubility is Raoult's law against
Psat = **219.9 bar** — a curated Antoine evaluated at 400 K, which is **118 K
above ethylene's critical temperature of 282.35 K.** Oxygen beside it is a
Henry's-law solute and behaves. **NOTHING IN `build_phase_arrays` COMPARES T TO
Tc.** It makes the Wacker liquor richer in alkene than a real one, by roughly
40x. New engine-queue item.

### ⚠⚠ 8. ENGINE QUEUE ITEM 6 IS CLOSED, AND **NOT** BY RAISING `REPORT_ABS`

`tolerance_audit.py` has reported `QUOTABLE DIGITS MOVE, worst 99.85%` on
`oil_of_vitriol` since S5, and that headline was wrong: four of its five moved
lines are the created-matter residual and **every one gets smaller** at the tight
tolerance. The obvious fix — raise `REPORT_ABS` above 2.9e-05 — is the wrong one.
`REPORT_ABS` is SYMMETRIC, so raising it would blind the audit to a small
quantity GROWING as well as shrinking, and **a residual growing under refinement
is the defect the whole file exists to catch.**

The fix is a SECOND floor, `CONVERGING_ABS`, applied only when the tight run's
value is SMALLER than the loose one's. **Direction is the information the old
test threw away.** And the number came out of a measurement this project already
had rather than out of the audit: `NEXT_SESSION.md` records that same column
swinging **2.5e-09 to 4.5e-04 under an INERT 0.5% N2 nudge** — a perturbation
that cannot change the answer. 5e-04 is the top of that swing.

⚠ **AND THE SUPPRESSION IS NEVER SILENT**: a line whose only moves are converging
tokens is still printed, under its own heading, with its values.

**PREDICTED BEFORE THE 19-MINUTE RUN, AND ALL FOUR CAME OUT:** 5 moved lines ->
**1**; worst 0.9985 -> **6.60e-05**; the headline flips from QUOTABLE DIGITS MOVE
to **(below 0.1%)**; and no other example changes — `CONVERGING_ABS` fires on
**zero tokens across all twelve cheap examples**, which is the safety measurement
that mattered.

### ⚠ 9. THE OXO REVERSE IS THE ONE ROW WHOSE CROSSING TEMPERATURE IS A REAL STATEMENT

`rate_ceiling.py` gained an oxo panel, on M12's standing instruction to check the
reverse a template IMPLIES. Every other reverse it flags is high-order, so its
pre-exponential is in `L^n/(mol^n s)` and comparing it to a collision limit is
M8's unit error — the column is only good for RANKING.
`hydroformylation_linear_rev` is `butanal -> propene + CO + H2`, **one molecule
falling apart**, so its `A` really is in 1/s and `UNIMOLECULAR_LIMIT` really is
its yardstick.

It is **2.0e26 and 1.2e27 1/s**, and that is the third appearance of a thing this
project has now named twice: an **entropy of gas-making in a pre-exponential**.
One mole becomes three, dS_rev = +251.6 J/(mol K), and `exp(dS/R)` is 1.4e13 by
itself. Detailed balance is not free to shrink it without breaking `k_f/k_r = K`.
⚠ It crosses at **969.4 K** (branched 966.8), 550 K above the reactor. ⚠ The
brief predicted ~824 K off a 1e13 ceiling and the audit's own constant put it
145 K higher; **the measured number stands.**

### 10. AND TWO REFUSALS WERE RE-MEASURED AND BOTH STAND

Engine queue items 3 and 7 were both priced as "one source away". Re-queried
against `chemicals` 1.5.2 this session:

* **`pyrite`** — `Hfs` in WEBBOOK, `S0s` in **nothing**. Blocked, and the
  same-database rule is worth keeping. **Unchanged.**
* **`iron-ii-oxide`** — `Hfs` in CRC and WEBBOOK, `S0s` in WEBBOOK, so the
  same-database rule COULD be met from WEBBOOK. But its CRC standard row has
  `Cps = NaN`, and a species in the solid block has to say how much heat it
  holds. **Still blocked, on the recorded reason.**
* ⚠⚠ **AND ITEM 3 WAS PRICED WRONG.** `slagging` was listed as needing
  "`silicon-dioxide` and `calcium-silicate` in `mineral_data`", i.e. two curated
  entries and one declaration. Silica is fully available (CRC: Hfs -910700,
  Gfs -856300, S0s 41.5, Cps 44.4). **Calcium silicate has NO data in
  `chemicals` under any of its three CAS numbers** — 10101-39-0, 1344-95-2,
  13983-17-0 — so it is not a curation job at all. `slagging` is blocked, and
  `blast-furnace` is blocked twice over.

### ⚠⚠ 12. AND A THIRD CLASS WAS ATTEMPTED AND REFUSED — BECAUSE THE BALANCE AUDIT'S TEST IS WEAK

`oxidative-cleavage` was the queue's next row after the two above, worth +1 and
listed as clean: every species resolves, and `corpus_balance` passes its only
step. **It cannot be built, and finding out why is a finding about the
instrument.**

The row is `coniferyl alcohol + oxygen -> vanillin + water`. Coniferyl alcohol is
**C10H12O3** and vanillin is **C8H8O3**: a C10 monolignol makes ONE C8 vanillin
and a C2 fragment the row does not name. `corpus_balance` passes it anyway,
because its test is *does ANY positive coefficient vector conserve every element*,
and there is one:

    8 C10H12O3 + 7 O2  ->  10 C8H8O3 + 8 H2O

**EIGHT AROMATIC RINGS IN AND TEN OUT.** Element conservation does not forbid
rearranging carbon skeletons, so a row can PASS this audit and still not be the
reaction it is written as. ⚠ **A pass there is not permission to write a SMARTS**,
and the audit says so in a new last panel now.

Naming the missing C2 product would be inventing chemistry inside the corpus,
which is the `diels-alder-route` precedent this project already follows. **So the
class is REFUSED, measured, and the measurement is printed rather than remembered.**

⚠⚠ **AND THE ROW NEXT TO IT ON THE SAME QUEUE IS THE CONVERSE, WHICH IS WHY BOTH
WERE CHECKED.** `skraup-route` step 2 reads with **aniline on BOTH sides**, which
looks exactly like the `spurious` pattern the audit exists to catch — and is not:
the nitrobenzene oxidant is REDUCED to aniline. It balances at

    3 aniline + 3 acrolein + 1 nitrobenzene -> 3 quinoline + 1 aniline + 5 water

with **four aromatic rings in and four out**. That is the real Skraup
stoichiometry, and it is now the coverage queue's best row — 7 reactant slots and
9 product slots, which the Claus template's 24 proves is reachable.
**Two rows, one passing audit each, and only one of them is real.**

### 13. THE SMALL THINGS

* **`species_roles.psv` upgrades four provenance tiers** — ethylene `joback -> measured`,
  and propylene, butanal and 2-methylpropanal `joback -> benson` (a measured Tb lets Benson's formation half assemble where
  Joback's was standing in). An upgrade in the audit's own terms, and it is what
  a coverage report CAN see about this work — the 310 it cannot see are engine
  queue item 1.
* `validation/hydroformylation.py` and `validation/wacker.py` are new standing
  audits. Every class S11 credits went into a real `Vessel`; the coverage table
  credited nothing on a lookup.
* ⚠ Panel 3 of the oxo audit prints the KINETIC ratio beside the actual one,
  because the first version printed only the actual one and read as if the
  Arrhenius ratio had collapsed. **A column that answers one question cannot
  answer the next one**, again.
* ⚠ The oxo audit's own prose rotted twice inside this session — once when
  reversibility changed the 480/520 K numbers, once when propene's boiling point
  changed the conversion. **Third session running.**


## S12 — The Skraup, whose oxidant becomes one of its own reagents  ✅ **DONE 2026-08-26 — +1 on every column as predicted, and the source comment's own hand-priced numbers were wrong by 163 kJ/mol before the audit caught them**

**+1 class, +1 template-ready, +0 species-ready, +1 RUNNABLE — all four predicted
before the audit ran and all four came out.** The coverage queue's top row, taken
for the mechanic S11 named it for: a row that reads like a bookkeeping error and
is not one.

| | before | after |
|---|---:|---:|
| classes with a template | 50 / 229 | **51 / 229** |
| routes template-ready | 40 / 173 | **41 / 173** |
| routes species-ready | 77 / 173 | 77 / 173 |
| ⚠⚠ **routes BOTH — the one to quote** | **30** | **31** |
| templates | 45 | **46** |

⚠ **NO ENGINE CODE CHANGED, THIRD MILESTONE RUNNING.** Not one line of
`numerics/` or `vessel/`, and no data table either — so `tolerance_audit.py`
carries no new exposure and was not re-run. Everything below is one template, one
class registration, one standing audit and one test file.

### ⚠⚠ 1. THE ROW HAS ANILINE ON BOTH SIDES AND IT IS NOT THE `spurious` PATTERN

    skraup-route 2 | aniline + acrolein + nitrobenzene + sulfuric-acid
                   -> quinoline + aniline + water + sulfuric-acid

`corpus_balance`'s `spurious` bucket is 17 rows of a reagent written as consumed
that is really a catalyst. This is not one of them: **the aniline coming out is
the NITROBENZENE, reduced.** Each ring closure sheds two hydrogens and one
nitroarene takes six, which forces the multiple:

        3 x  aniline + acrolein  ->  quinoline + H2O + 2 [H]
             PhNO2 + 6 [H]       ->  PhNH2 + 2 H2O
        ---------------------------------------------------------
        3 aniline + 3 acrolein + PhNO2 -> 3 quinoline + PhNH2 + 5 H2O

C33H38N4O5 on both sides, four aromatic rings in and four out. **Seven reactant
slots and nine product slots**, plus the acid on both sides as an eighth — the
`claus_comproportionation` shape, at a third of the size. The SMARTS was written
from the electron count and balanced first time.

### ⚠⚠⚠ 2. THE BIGGEST FINDING IS THAT MY OWN PRICED NUMBERS WERE WRONG, AND THE AUDIT CAUGHT THEM

The block comment in `synthesis.py` was written BEFORE the audit ran, off a hand
calculation summing `ThermoData.Hf` and `.Gf` over both sides. It said
**dH −561.63, dG298 −572.55, dS +36.65 J/(mol K)**, and it built an argument on
the sign of that dS: seven molecules become nine, so heating the flask makes the
forward direction more favourable, so irreversible is safe. Then panel 2 printed
what `reaction_deltas` actually returns:

|  basis | dH / kJ | dG298 / kJ | dS / J/(mol K) |
|---|---:|---:|---:|
| ideal gas | −561.63 | −572.55 | **+36.65** |
| pure liquid | −725.16 | −627.05 | **−329.08** |
| difference | **−163.53** | −54.49 | **−365.73** |

⚠⚠ **THE TWO BASES DO NOT AGREE ON THE SIGN OF dS, AND THE EASY ONE IS THE WRONG
ONE.** The template is `phase="liquid"`, so `reaction_deltas` puts every
condensable species on its own pure liquid — and **NINE product molecules
condense against SEVEN reactant ones.** That is worth 163.53 kJ/mol in dH and it
flips the entropy.

⚠ **THE CONCLUSION SURVIVED AND THE REASON FOR IT DID NOT.** Irreversible is
still safe: ln K on the basis the engine uses is **252.9 at 298 K, 154.2 at 450
and 105.8 at 600**, and dG crosses zero at **2204 K**. But the argument that made
it safe was about the wrong standard state, and *"seven molecules become nine"* is
exactly the kind of sentence that reads as a physical fact and is a basis-
dependent one. **A PHASE LABEL CARRIES A STANDARD STATE** — S1 recorded that
about a surface rate law, and it is the same trap in a comment.

`test_the_two_standard_states_disagree_on_the_sign_of_dS` pins BOTH rows, so the
comment cannot rot back to the hand calculation it started as.

### ⚠⚠ 3. THE PREPARATION'S OWN ODDITY FALLS OUT OF THE FLASK, NOT OUT OF A DECLARATION

A real Skraup makes its acrolein in situ from glycerol and never charges it. The
textbook reason is that neat acrolein polymerises. Here is the other half,
measured — acrolein boils at 314 K and this reaction runs at 450:

    k_vent      quinoline   acrolein left
    0 (sealed)   1.000000       0.000000
    1e-3         0.919592       0.000000
    1e+0         0.061473       0.000000
    1e+3         0.016883       0.000000

**An open flask loses 98% of the yield**, and nothing declares that: it is the
vapour-pressure curve against the vent conductance, the same mechanic that gives
the Claus train its sulfur condenser. ⚠ It is also why `run()` in the audit is
sealed — this project has no reflux head that returns a vapour to the pot, so
`k_vent=0` IS the condenser, and the pressure that buys (13.7 bar at 450 K) is
printed rather than hidden.

### ⚠⚠ 4. THE OXIDANT'S REDUCTION PRODUCT IS ITSELF A SUBSTRATE, AND THE NETWORK FOUND IT

Charge **p-toluidine** instead of aniline and nothing else, and the flask makes:

    Cc1ccc2ncccc2c1   6-methylquinoline    0.666667 mol
    c1ccc2ncccc2c1    quinoline            0.333333 mol
    Nc1ccccc1         aniline              0.000000 mol

**Exactly 2:1, totalling the 1.0 mol of acrolein charged.** The nitrobenzene is
reduced to aniline and the aniline then goes round again as a SUBSTRATE, because
the template's three amine slots do not have to be the same molecule — so one
event in three has to spend an aniline. That is a real nuisance of the real
preparation (a Skraup on a substituted aniline with nitrobenzene as the oxidant
contaminates its product with the parent quinoline) and **nobody declared it**.
It is the clearest emergence this project has produced from a single template.

### ⚠ 5. THE SMALL THINGS THAT WERE STILL DECISIONS

* **Every slot it consumes keeps order 1** — S11's rule, and here it costs
  nothing to obey. `orders=(1,1,0,0,0,0,1,1)`: first order in the amine, the
  enal, the oxidant and the acid, so nitrobenzene carries an exponent rather than
  being driven negative. Unlike the Wacker, where the same rule forces an oxygen
  order the real rate law says is zero, **a real Skraup DOES slow as its oxidant
  is spent**, so the honest declaration is also the right one. Measured:
  0.10 / 0.20 mol of nitrobenzene cap the yield at exactly 3x, and the acrolein
  sits there.
* **The acid is spelled as the hydronium it makes**, not as `sulfuric-acid`.
  That is `ACID_CATALYST` and the same choice `esterification`,
  `ether_condensation` and `alkene_dehydration` already make; it is also why the
  network needs `electrolyte_provider()`, which is the Wacker's gate again.
  A flask with no acid makes **exactly zero**.
* **Ea 80 kJ/mol, A 3.0e6 (3.0e7 declared, after `CATALYST_REFERENCE`).** An
  APPARENT barrier over a four-step sequence, fitted to the one thing the
  preparation reports — a Skraup at violent reflux is over in an hour or two.
  Measured at one minute: 1.85% at 350 K, 36.6% at 400, 69.7% at 420, 98.4% at
  450.
* ⚠ **`validation/rate_ceiling.py` GAINED A SKRAUP PANEL**, because a template
  that is not in that file is not audited and "it is obviously small" is not a
  measurement. 2.90e-18 of the bimolecular ceiling — and the crossing column is
  meaningless for it for the Deacon's reason, since a fourth-order `A` is in
  L^3/(mol^3 s).
* `validation/skraup.py` is a new standing audit, ~10 s, seven panels. Every
  claim above is one of its panels; the class is credited on an INTEGRATION and
  not on the coverage table, which is the S1 standard.
* `COVERAGE_REPORT.md` and both `derived/*.psv` re-checked byte-identical across
  `PYTHONHASHSEED`.
* **The whole suite: 961 passed / 0 failed in 13:20**, run after every `src/`
  edit. ⚠ 952 + 9 would have given the same number, which is exactly why it was
  RUN rather than computed.
* ⚠ **A `⚠` inside a `print()` did NOT ship this time.** Twenty-six sessions.

## S13 — The hand-typed list, closed  ✅ **DONE 2026-08-26 — and the instrument built to expose it undercounted the gap by 60%, using S11's own fix as the reason**

**37 hand-typed species became 1239 generated ones.** `physical_data.py` was a
file that READ as generated and was a transcription on the inside: it is emitted
by `tools/build_physical_data.py` from `CANDIDATES`, a hand-typed list, and
anything not on that list fell to Joback whether or not `chemicals` held five
experimental sources for it. NEXT_PROMPT called this "the largest honesty item on
this list" for two sessions running. It is closed.

| | before | after |
|---|---:|---:|
| species in `MEASURED_PHYSICAL` | 37 | **1239** |
| ...carrying a measured boiling point | 20 | **896** |
| corpus species whose PHYSICAL half is measured | 40 / 1583 (2.5%) | **652 / 1583 (41.2%)** |
| corpus species whose physical half is Joback | 964 (60.9%) | **333 (21.0%)** |
| routes species-ready | 77 / 173 | **80 / 173** |
| ⚠⚠ **routes BOTH — the one to quote** | **31** | **31** |
| classes with a template | 51 / 229 | 51 / 229 |
| templates | 46 | 46 |

⚠ **+0 ON THE HEADLINE, AND THAT WAS PREDICTED.** This is a DATA milestone, not
a coverage one: it does not add a template, so it cannot add a class or a
template-ready route, and `BOTH` is bounded by template-ready. What it moves is
whether the numbers the engine already reports are *right*. **+3 species-ready
and 14 fewer refusals** are the only coverage effects and they are side effects.

### ⚠⚠⚠ 1. THE LARGEST FINDING IS ABOUT THIS SESSION'S OWN INSTRUMENT, AND IT USED S11's FIX AS THE REASON

S11 recorded a trap: `chemicals.CAS_from_any("C")` returns **CARBON**, because a
bare SMILES is read as a FORMULA and a single-letter SMILES is also an element
symbol. Its sweep listed methane boiling at 4273 K and counted 360 where the
answer was 310. The recorded fix was **"always use `smiles=`"**.

S13 built `validation/boiling_points.py` on exactly that fix, measured the gap at
**322 species**, wrote the number into a commit message, and generated a table.
**The table had no aniline in it. No nitrobenzene, no quinoline.**

    CAS_from_any("smiles=Nc1ccccc1")  -> "A SMILES identifier was recognized,
                                          but it is not in the database."
    CAS_from_any("aniline")           -> 62-53-3, Tb 457.15 K

⚠⚠ **`chemicals`' SMILES index does not contain three of the most ordinary
organic compounds there are.** Measured over the corpus: of **1069** species with
no graph-resolved CAS, **874 resolve by NAME with a matching formula and 508 of
those carry a measured boiling point.** The gap is **830, not 322** — the
instrument undercounted it by 60%, and it did so by faithfully applying the fix
for the previous session's trap.

**THE FIX FOR ONE TRAP BECAME THE NEXT TRAP.** Both keys, graph first, with the
formula cross-check as the arbiter — and the cross-check earns its place: it
**refuses 72 name matches outright** whose database formula disagrees with the
graph the table is keyed by.

    resolved to a CAS by GRAPH ('smiles=')      432
    resolved to a CAS by NAME                   877
    name matched a DIFFERENT formula, refused    72
    no CAS from either key                      193
    CAS, but no non-estimated Tb anywhere       478
    entered the table                          1202

### ⚠⚠ 2. THE GAP WAS NOT EXOTIC. IT WAS THE SOLVENT IN THE FLASK

Panel 5 of the new audit is the one that changed what to do about this. Every one
of these was priced by **Joback**, in a project whose flagship rig is a
distillation column:

| species | engine | measured | error |
|---|---:|---:|---:|
| acetylene | 216.60 | 189.00 | **+14.60%** |
| methanol | 314.66 | 337.63 | **−6.80%** (23 K) |
| ethanol | 337.54 | 351.57 | **−3.99%** (14 K) |
| diethyl ether | 313.54 | 307.60 | +1.93% |
| n-hexane | 336.88 | 341.87 | −1.46% |
| acetaldehyde, acetic acid, iodomethane, propanoic acid | | | under 0.3% |

Over the whole table: **881 species had an estimated boiling point corrected,
mean |error| 6.10%, worst 110.94%. 437 were more than 2% off and 68 more than
20% off.** A mean of a few per cent is not the finding — the finding is that the
error was UNSIGNED and UNBOUNDED, and nothing in the engine knew which was the 3%
one and which the 85% one, **because all of them RESOLVED**.

### ⚠⚠ 3. THE COUNT OF ABSENT SPECIES IS NOT THE COUNT OF WRONG ONES

322 species were absent from `MEASURED_PHYSICAL`; only **213** would have changed
the resolved record. Water, oxygen and hydrogen chloride are all "absent" and all
irrelevant to it — they are curated in `_CURATED_RAW`, which short-circuits the
whole resolution. `boiling_points.py` resolves every candidate **twice, through
two providers**, rather than arguing about tiers, and prints both numbers.

### ⚠⚠ 4. AND THE COVERAGE AUDIT'S TIER CLASSIFIER WAS PARSING PROSE — `thermochemistry` HAD ALREADY WRITTEN DOWN WHY THAT WOULD FAIL

`ThermoData.physical_source` carries this comment, from the session that added
it: *"Kept as its own field because a record is assembled from
independently-resolved halves ... deducing it by matching on the prefix of a
composite string is the kind of guess that goes quietly wrong the first time the
wording changes."*

`catalog_coverage._thermo_tier` was handed the WHOLE `source` string — which
names BOTH halves — and returned `measured` if the word "experimental" appeared
anywhere in it. Before S13 only 37 species had a measured physical half, so the
physical clause almost never contained that word and the count read 144.
**After the sweep the same code reported 669 species with a MEASURED FORMATION
half — a 4.6x overstatement of the project's headline honesty number, produced
by a data change that touched no formation data at all.**

Its twin, `_volatility_tier`, matched neither "measured" nor "joback" in the new
wording and fell through to a bare `return "benson"` at the bottom — reporting
**659 physical halves as Benson, where there is no such thing.** Benson gives a
heat capacity, not a boiling point. The old report showed 20 of them and nobody
had asked what they were.

⚠ **A DEFAULT AT THE BOTTOM OF A MATCHER IS A GUESS.** Both now split the
composite string on its own structure, take `physical_source` as the field it is,
and **raise on an unrecognised provenance** rather than defaulting.

⚠ **AND THE FIX FOUND A REAL PRE-EXISTING ERROR IN THE OTHER DIRECTION:** the
measured-formation count was 144 and is 135. Nine species had an estimated
formation half and were being counted as measured.

⚠⚠ **AND IT NEEDED A NEW TIER, WHICH IS NOT A ROUNDING.** 47 boiling points come
from YAWS or WIKIDATA, which `chemicals` itself describes as published-but-
unsourced. `build_physical_data` has kept `experimental` and `compilation` apart
on every value since the table existed; before S13 exactly one corpus species
carried a compilation-tier value, so the audit could get away with having no name
for it. Folding 47 into `measured` would relabel an unauditable compilation as a
measurement — the one thing `physical_data`'s docstring exists to refuse. The
report has a `compilation` row now.

### ⚠⚠ 5. A FIT WINDOW THAT COULD EXCLUDE THE BOILING POINT IT WAS BRACKETING

`volatility.py` fitted its Antoine curve over
`T_lo = max(0.30*Tc, Tb - 120, 150.0)`. The word in its own comment is
**BRACKETING**, and the bare 150 K floor breaks that for anything cryogenic:

| species | Tb | window opened at | residual at Tb |
|---|---:|---:|---:|
| methane | 111.66 | 150.00 | **+16.50%** |
| nitric oxide | 121.38 | 150.00 | **+14.53%** |
| fluorine | 85.04 | 150.00 | −0.19% |

The curve reached the normal boiling point **only by extrapolation, 38 K outside
its own fitted domain**. ⚠ **PRE-EXISTING AND INVISIBLE**: the check that exists
for exactly this walked `MEASURED_PHYSICAL`, and all three are in `_CURATED_RAW`.
S13's sweep put species with measured boiling points into the table in bulk and
the same fault came in through the front door — 1,3-butadiene at −1.52% — which
is how it was found. One line: `min(150.0, t.Tb)`.

### ⚠ 6. THE 1.5% BAR WAS MEASURED OVER NINE SPECIES

`test_every_assembled_record_boils_at_one_atmosphere` now walks all three tables
that carry a Tb, not just one, and checks **889 condensable records against 20**.
**858 clear the original 1.5%.** The 31 that do not are named in `BOILS_LOOSELY`
with the residual each was measured at, and **eight of them are pre-existing and
this check could not see them** — water at +2.57%, SO2, SO3, HF, formaldehyde,
nitric acid, the nitrite pair, and zinc.

Nearly every one is polar, associating, or both, and boils between 250 and 375 K:
a three-parameter Antoine is being least-squares fitted to a three-parameter
corresponding-states correlation, and neither knows about hydrogen bonding.

⚠⚠ **ZINC IS NOT A THIRTY-SECOND FINDING, IT IS S10's FIRST ONE IN THE OTHER
VARIABLE.** S10 recorded zinc's curated Alcock curve as boiling at 1168.84 K
against a measured 1180.15 — **−0.96% in TEMPERATURE**. The same disagreement
read as a PRESSURE at the measured Tb is **+12.61%**, because dP/P is
(dHvap/RT)·dT/T and zinc's curve is steep. **A bar set in temperature and a bar
set in pressure are not the same bar**, and quoting one against the other would
have manufactured a regression in an entry behaving exactly as its own session
measured it.

### ⚠⚠ 7. WHAT IT COST, MEASURED BY RUNNING ALL FIFTEEN EXAMPLES BEFORE AND AFTER

Not argued. `run_examples.py` ran the whole example set against the old table and
the new one and `tolerance_audit.diff` compared them line by line.

| example | worst moved line | what it is |
|---|---:|---|
| `esterification`, `lime_cycle`, `roasting_and_the_catalyst_gate`, `mercury_retort`, `oil_of_vitriol` | **IDENTICAL** | |
| `activity` | 3.98% | n-hexane's activity coefficient, 2.41 → 2.51 |
| `extraction` | 3.96% | DCM/water partition, 65.5 → 68.2 |
| `competing_pathways` | 4.46% | 510 K row; ethanol conversion 6.21% → 6.42% |
| `wait_until` | 4.58% | **the boil at 1353 s → 1418 s** |
| `workshop` | 8.71% | solid held at 1400 s, 0.1299 → 0.1423 |
| `multistep_prep` | 27.3% | the crop: yield 84.0% → **82.7%**, purity 99.6% → **99.7%** |
| `vessel` | **structural** | the flask is still boiling at 175 s where it had gone dry |
| `named_routes` | **structural** | see below |
| `plate_column` | 0.05% | **HEART = 0.8548 against 0.8544. Target still MET.** |
| `fractional_distillation` | 11.8% | the 270 s row: head 418.02 K → 371.44 K |

⚠ **THE FLAGSHIP RESULT SURVIVED AT THE FOURTH DIGIT** and its replay determinism
is still exact — original vs replayed 0.000e+00 mol on all three receivers.

### ⚠⚠ 8. AND `named_routes` LOST FOUR WARNINGS AND GAINED ONE, WHICH IS THE WHOLE MILESTONE IN ONE EXAMPLE

Four `MIXES STANDARD STATES` notices **disappeared**. The engine had been saying
*"Do not read this reaction's equilibrium constant"* about DDT isomers,
dinitrotoluenes and the stearic/oleic pair — because those species had no liquid
standard-state shift while their partners did. They have one now.

And one notice **appeared**, which is the engine refusing loudly on better data:

    template 'ester_hydrolysis' declares Ea=70000 J/mol for aspirin hydrolysis,
    below its endothermicity dH=75599 J/mol. An elementary barrier cannot be
    lower than dH; raised to 75599.

`aspirin-impurity` reports **59.2% where it reported 99.8%**. Nobody changed a
barrier; the reaction's enthalpy moved onto a measured basis and the guard that
was already there fired.

### ⚠ 9. FIVE TESTS MOVED AND EACH ONE WAS A FINDING

* **`test_a_flask_with_no_acid_does_nothing`** asserted `== 0.0` and now reads
  4.1e-18. ⚠ **S12 wrote "exactly zero" and that was one word too strong.** Water
  autoprotolyses, so `electrolyte_provider` hands an acid-free flask ~4e-29 mol
  of hydronium, and a rate first order in it is SMALL, not ABSENT — measured at
  ~2.4e-25 mol after ten hours and flat thereafter. The 0.0 was the solver's
  trajectory clamping a column that never got off the floor.
* **`test_a_rate_tolerance_fires_on_the_FIRST_transient`** — the documented trap
  **did not go away, it went below the default tolerance.** Ethanol's Joback
  boiling point made the flask twice as volatile at 298 K as it should be, so the
  opening evaporative swing was **−24 K/s**; with the measured record it is
  **−1.42 K/s**, still crossing zero inside half a second, and BDF at the default
  tolerance no longer resolves a spike that brief. ⚠ `max_step` does NOT recover
  it (0.1 and 0.01 both still land at the plateau); **rtol 1e-9 does**, at 0.08 s
  and 297.78 K. A behaviour this project had written down was resting on a wrong
  boiling point making a transient big enough to see.
* **`test_waiting_for_a_boil_agrees_with_the_boiling_readout`** — `boils()` stops
  on a scipy ROOT of `volatile_pressure − P_ambient`, so that expression is zero
  to solver precision and **whether the last bit lands at −1e-15 or +1e-15 bar is
  not physics**. `is_boiling`'s bare `>=` therefore called a flask integrated to
  its own boiling point NOT boiling. Measured: −1.110e-15 bar at the root, and
  +9.7e-08 exactly 0.05 s later. The readout gained a 1e-12 relative floor —
  three decades above the noise it absorbs and six below the smallest excess any
  boiling flask carries. **The test had been passing on which side of the root
  the last bit fell.**
* **`test_provenance_distinguishes_measured_from_estimated`** — its own
  illustration turned inside out. It read *"ethyl acetate has a measured
  formation half sitting on a Joback physical one"*; after the sweep **no catalog
  species has that combination at all.** The halves still differ — it is the
  FORMATION half that falls back now, which is the direction the tiers were
  always meant to fail in: a boiling point is looked up, an enthalpy of formation
  is estimated.
* **`test_the_crust_volume_is_the_wetted_area_times_one_particle_layer`** —
  ⚠ **S13 MADE THIS NUMBER WORSE AND THE RECORD BETTER, AND IT IS WRITTEN DOWN
  RATHER THAN WIDENED AWAY.** Benzoic acid's measured CRC boiling point brings
  Wilson-Jasperson criticals and a **Fedors** Vc with it, because a record may
  not mix two group-contribution methods inside itself. Fedors puts Vc at 326.43
  cm³/mol against Joback's 343.50 and the literature's ~341 — so on THIS species
  the estimator that came with the measurement is the worse of the two, and the
  molar volume fell from 96 mL/mol to 87.4 against a real ~96.5. Taken anyway,
  because the rule is the rule and Fedors' 7.7% mean error is MEASURED while
  cherry-picking Joback's Vc onto a measured Tb would put two methods in one
  record.

### ⚠ 10. THE GATE HAD TO CHANGE SHAPE RATHER THAN GROW

`DELIBERATE_OVERRIDES` is a list of EXCEPTIONS, and that is the right shape while
the table is a SUPPLEMENT: 37 hand-typed names, so overriding a working Joback
record is unusual and someone should have to say what it cost. With the corpus as
the input, **243 of the entries override a record Joback prices completely**, and
a list of 243 hand-typed exceptions is not a guard — it is a transcription of the
table.

So the cost was measured ONCE, for the whole batch, and written down (§7 above).
The generator emits `CORPUS_SWEEP`, naming every entry that came in that way, and
two tests keep the teeth: the two sets must be **DISJOINT**, and `CORPUS_SWEEP`
must be a subset of the table it describes. A fifth species added by hand still
lands in front of the original test with nothing to excuse it.

### ⚠⚠ 12. THE TOLERANCE AUDIT SAID "CANNOT BE SWEPT" AND IT WAS NOT A REGRESSION

`named_routes` raises at rtol 1e-8 after 2.377e-05 s of a 3600 s run --
`aniline-route`, 5 mol of hydrogen charged as a LIQUID into 1 L at 470 K where
it is a Henry's-law solute and flashes into the headspace inside 24 microseconds.
The audit went from "2 lines moved" to "CANNOT BE SWEPT", which reads as
something S13 broke. Measured on both bases, by rebuilding the same vessel
through `ThermochemistryProvider(measured_physical=...)`:

| basis | default (1e-6) | rtol 1e-7 | rtol 1e-8 |
|---|---|---|---|
| pre-S13 Joback | 1.000000 mol | **RAISES** | 1.000000 mol |
| S13 measured | 1.000000 mol | **RAISES** | **RAISES** |

⚠⚠ **A ONE-POINT TOLERANCE SWEEP CANNOT TELL "NEWLY BROKEN" FROM "ALREADY BROKEN
AT A POINT IT DOES NOT SAMPLE."** The fragility was reachable before S13 and one
decade CLOSER to the default than the point this file tests. What the data change
moved is which tolerances happen to step over it. The answer is confirmed on both
bases -- complete conversion, 1.000000 mol -- and it is in `KNOWN_REFUSAL` with
the measurement, the way S5 recorded `oil_of_vitriol`.

### ⚠ 13. TWO EXAMPLES NOW PRINT A TOLERANCE-DEPENDENT DIGIT WHERE S11 FOUND NONE

* `activity` -- methanol's mole fraction, 0.0783 against 0.0782, **0.1277%**.
* `multistep_prep` -- **`pH = inf` at the default tolerance and 11.65 at rtol
  1e-8.** ⚠ The `inf` is PRE-EXISTING and unchanged by S13 -- it is in the
  base run too -- and it is the same mechanism as the Skraup's "exactly zero":
  a hydronium column the loose solver clamps to a literal 0.0. What is new is
  that the audit can now SEE it, because the tight run resolves it.

⚠ Both are on the audit's watch list rather than fixed. The `pH = inf` is worth a
session on its own: a readout that reports infinity is not an accuracy problem.

### ⚠ 14. AND A DOCUMENTED-INERT OVERFLOW BECAME REACHABLE

`activity.activity_coefficients` overflows `np.exp(-a / T)` for the PSRK
quadratic below **4.28 K** -- carried for several sessions as "PRE-EXISTING,
measured inert". `plate_column` now prints five `RuntimeWarning` lines where it
printed none: something in that fourteen-vessel rig evaluates an activity
coefficient below 4.28 K. ⚠ **MEASURED HARMLESS WHERE IT FIRES**: the heart cut
is 0.8548 against 0.8544, the target is still met, and the replay determinism is
still exact at 0.000e+00 mol on all three receivers. **The word to change is
"inert", not the number.**

### ⚠⚠ 15. AND IT CLOSED EIGHT TENTHS OF M11 AS A SIDE EFFECT

M11's own costed starting point, carried in `NEXT_SESSION.md` since M5, is
*"10 species that need ONE measured boiling point each"* -- species whose
formation half already resolves and which are refused only because nothing
prices their vapour pressure. `COVERAGE_REPORT.md` counts that bucket, and it
went **10 -> 2**.

The two left are `performic-acid` and `phenyl-radical`. Neither has a
non-estimated boiling point in `chemicals` under either key, and a phenyl radical
is not going to acquire one. ⚠ **That bucket is not a work queue any more**, and
M11 needs re-costing before it is scheduled: what remains of it is the formation
half (267 species with no group value in any published tabulation), which is a
different problem with a different answer.

### 11. THE SMALL THINGS

* `validation/boiling_points.py` is a new standing audit, **2 seconds**, and it
  was written to stay useful once the gap is closed: panel 2 measures what the
  CORRECTION was worth by resolving every species through
  `ThermochemistryProvider(measured_physical=False)`, which is not a
  reconstruction of the old behaviour — it IS the old behaviour.
* Panel 3 **demonstrates** both traps live rather than describing them, and
  asserts that the two keys still disagree, so neither fix can be undone
  silently.
* `physical_estimation.py` Panel 3 — the acentric factor, the one independent
  check in the chain — went from **n≈20 to n=254**, and the design held:
  **measured Tc/Pc mean |Δω| 0.029, Wilson-Jasperson 0.121.**
* **The whole suite: 965 passed / 0 failed in 21:36**, run after every `src/` edit. 961 + 4 new tests, and it was RUN rather than computed.
* **`tolerance_audit.py` WAS re-run** — a data table changed — and its three self-check examples stayed OUTPUT IDENTICAL.
* `physical_data.py` is 13736 lines. `critical_data.py` came out byte-identical.
* `COVERAGE_REPORT.md` and both `derived/*.psv` re-checked byte-identical across
  `PYTHONHASHSEED`.
* ⚠ **A `⚠` inside a `print()` DID ship this time**, in the first draft of
  `boiling_points.py`, and was caught before the first run. Twenty-seven
  sessions.

## M7 -- Dissociation as an equilibrium  *(M12 TOOK MOST OF ITS CASE AWAY)*

**RE-SCOPE THIS BEFORE SCHEDULING IT.** The headline was a stiffness ratio of
**7.05e21**, essentially all acid/base recombination -- and 9.431e18 of that was
water's reverse autoionization, **a rate constant 9.4e7 times the collision
limit**. M12 capped it at 1.0e11 (HANDOFF 82), so the ratio is now **8.6e12**:
still stiff, no longer the largest number in the project by eight orders, and
the flask it was worst on now integrates 6.6x FASTER than before rather than
needing a new representation to be affordable.

What genuinely survives, and it is the real argument:

* **The value integrating gives IS the equilibrium value.** That was always the
  principled reason and it is untouched by how fast the pair runs.
* **It still owns the stiff-reactant-at-zero residual** (1e-4 level, reported,
  converges) -- and M12 made that MORE visible at the default rung, not less:
  the prep creates 2.53e-05 mol of benzoyl there now, against 3.5e-12, because
  fewer and larger steps cover the same span. It converges to -4.4e-15 by rtol
  1e-8, and `conservation_report` says so unprompted.

**Done when:** the five pH invariants come back IDENTICAL and the stiffness ratio
falls by orders of magnitude. Measure the ratio again first -- the number in
every previous planning document is the pre-M12 one.

---

## M8 — Electrochemistry  ✅ **DONE 2026-08-25 — and the class it was named for did not survive its own row check**

**+2 classes (36 → 38 of 220), +3 template-ready (28 → 31), +3 RUNNABLE
(17 → 20).** Four templates, one field, one `if`. No new term in Layer 4, no new
phase, no new gate, and the pre-M8 example set is byte-identical.

### 1. THE MECHANIC, AND WHY IT NEEDED NO ENGINE

An electrolysis cell does electrical work `w = n F E` on the reaction.
`ReactionTemplate.electrons` says how many electrons cross the external circuit;
`build_network(cell_potential=...)` says what the supply is set to; their product
lands on `ConcreteReaction.electrical_work` and `reaction_deltas` subtracts it
from **both** dH and dG. A reaction whose chemistry costs less than the cell
supplies then runs, and the voltage where the two balance is the

    E_dec = dG_chem / (n F)

of every electrochemical series ever printed. **The gate is a comparison of two
energies this project already computed**, which is why nothing had to be
invented to hold it.

⚠ **THE SHIFT GOES ON dH AS WELL AS dG, AND THAT IS THE ONE PIECE OF ALGEBRA
WORTH CHECKING.** The supply holds E fixed, so `w` does not vary with
temperature, and a T-independent shift is an ENTHALPY shift. Put it in dG alone
and `reaction_entropy` — which reads `dS = (dH - dG)/T` — books the whole cell
voltage as reaction entropy, and K then drifts as `exp(w/RT)`. Shifting both
leaves dS exactly the chemistry's. **And the energy balance comes out right for
free**: `to_arrays` takes its dH from the same function, so the heat the flask
sees is `w - dH_chem`, zero at the thermoneutral voltage. A real cell does that.

⚠⚠ **EVANS-POLANYI ON AN ELECTRODE REACTION IS THE BUTLER-VOLMER EQUATION, AND
`alpha` IS THE TRANSFER COEFFICIENT.** An identity, not a resemblance: with the
work inside dH, `Ea_i = Ea + alpha (dH_chem - n F E)` is `Ea - alpha n F eta` up
to the entropy term — the Tafel slope, with alpha at its conventional 0.5. So
**`Ea` on an electrode template is the ACTIVATION OVERPOTENTIAL in energy units,
`n F eta_a`**, and the kinetics needed no new field either.

### 2. ⚠⚠ THE BRIEF NAMED THE TOP OF THE GREEDY CURVE, AND THE ROW CHECK TOOK TWO THIRDS OF IT

`electrolysis` has been the set-cover curve's **first row at +3 routes** since
M1. Its four rows are THREE mechanisms, distinguished at the CATHODE:

| became | rows | covered? |
|---|---|---|
| `aqueous-electrolysis` | `chloralkali` | ✔ the cathode reduces WATER |
| `molten-salt-electrolysis` | `downs-cell`, `hall-heroult` | ✘ a MELT is not a phase here |
| `amalgam-electrolysis` | `castner-kellner` | ✘ a mercury cathode reduces the SODIUM; the product is a marker |

**So the curve's top row is worth +1, not +3.** Chloralkali and Castner-Kellner
take the same feed and give the same chlorine; one makes caustic soda and the
other makes sodium metal, and the reason is which species the cathode reduces.
Crediting them together would have claimed a route to sodium metal this engine
cannot make — `roasting-to-metal`'s false credit in a new costume. ⚠ The two melt
rows cost nothing today: both are blocked on a bare element as well (`sodium`,
`aluminium`, `carbon-graphite`), so neither was ever one class away from running.

The other +2 came from `electro-organic-coupling`, which was NOT split — its two
rows are two mechanisms and **both are built**, which is the `ester-hydrolysis`
precedent and exactly when a multi-mechanism class may be credited.

### 3. ⚠⚠ THE BRIEF SAID THIS WOULD BREAK THE SPECTATOR ZEROS. IT DID NOT, AND THE REASON IS THE FINDING

The brief: *"a half-cell potential is not consumed as a number: it puts the ion
back into an equilibrium the kernel evaluates. Budget for re-deriving the five pH
values."* **Measured: they did not move, and no half-cell potential exists.**

Every template here is a WHOLE CELL — anode plus cathode, electrons cancelled,
charge balanced. That is not a convenience: a half reaction does not conserve
charge, and `builder._element_charge_balance` rejects a rewrite that does not. It
is also what the catalog rows already say — `sodium-chloride + water ->
sodium-hydroxide + chlorine + hydrogen` is the cell, not the anode. And it means
**no electrode potential was ever curated**: dG of a half reaction needs a
reference electrode, dG of a cell does not, so the driving force comes out of the
same dGf table that fixes every other equilibrium in the project. Nothing new
entered the ion equilibria, so nothing moved. `test_born.py`,
`test_solids_and_ions.py`, `test_precipitation.py`, `test_solubility_product.py`:
76 passed.

⚠ **AND THE "done when" WAS MET IN THE OTHER VARIABLE.** The brief asked that
"the current is the control". It is not — the VOLTAGE is, and see §6. Voltage is
what makes the gate thermodynamic and therefore derivable; a current budget is a
Layer 4 term and would have been a second milestone.

### 4. ⚠ THE NUMBER IS DERIVED, AND `validation/cell_potentials.py` AUDITS IT

| cell | E_dec derived | electrochemical series |
|---|---:|---:|
| `2 H2O -> 2 H2 + O2` | **1.441 V** | 1.229 |
| `2 Cl- + 2 H2O -> Cl2 + H2 + 2 OH-` | **2.362 V** | 2.186 |
| `2 Br- + 2 H2O -> Br2 + H2 + 2 OH-` | **2.061 V** | 1.894 |

Within a quarter of a volt, from formation data, with no electrode potential in
`src/`. ⚠ **The book column is an INDEPENDENT CHECK and must never become a
target** — nothing in it feeds anything in `src/`.

⚠⚠ **AND THE AUDIT FOUND A PRE-EXISTING ERROR ON ITS FIRST RUN: dG SURVIVES THE
ION TABLE'S MIXED BASIS AND dS DOES NOT.** The brine cell's dS is out by
**−591 J/(mol K)** and the bromide cell's by −738, which REVERSES the sign of
dE/dT: every cell here needs more voltage when heated, every real one needs less.
The cause is that this project's ions are derived from measured pKa against its
OWN water reference, and its own water is priced on the **ideal-gas** basis
(Hf −241.8, not the aqueous −285.8). For a reaction that conserves water the
offset cancels and nothing has noticed since the electrolyte model was built;
**every cell reaction consumes water and makes hydroxide**, so it does not.
**Quote E_dec at 298 K. Do not quote how it moves with temperature, and do not
read a cell's HEAT** — `to_arrays` takes its enthalpy from the same dH.

### 5. ⚠⚠ THE SOLVER SAID THE PRE-EXPONENTIAL WAS THE WRONG KIND OF NUMBER

Declared at `A = 1e10` — an order under the collision limit, which is how every
other pre-exponential in this project is bounded — a cell at 3.0 V consumed
0.2 mol of chloride inside a nanosecond and `Vessel.run` died with *required step
size is less than spacing between numbers* after **4.2e-09 s of a 3600 s
interval**. The rate cap had been firing at the low-voltage end too, scaling a
pair by 4.031e-14. Both are the same wrong ceiling seen from two ends.

**An electrode reaction is not two molecules meeting.** It happens on a SURFACE;
its rate is proportional to electrode AREA, not to volume; the molecules in the
bulk are not at the electrode at all. `A = 1e10` asserts that every chloride in
the flask is touching the anode. The right units are a current density over an
area:

    rate [mol/(L s)] = j0 [A/cm2] * a [cm2/L] / (n F)
    5e-8             = 1e-3       * 10        / (2 * 96485)

and the check that makes it defensible is that **it comes back out as an
ampere**: 5e-8 mol/(L s) at unit concentrations is 1e-2 A, and the cells below
run between a milliamp and a couple of amps. A bench power supply has those.

### 6. WHAT IS NOT MODELLED, MEASURED RATHER THAN ASSERTED: THERE IS NO CURRENT BUDGET

A real supply delivers a fixed number of electrons per second and the electrode
reactions divide them. Here they divide nothing, so **every reaction the cell
clears runs at its own full rate, simultaneously**. The measured consequence is
that activation selectivity washes out as the barriers reach `barrier`'s floor at
zero:

| E (V) | k(brine) / k(water) | one flask of brine, one hour |
|---:|---:|---|
| 2.5 | **4.76e+17** | 0.0177 mol Cl2, 8.9e-19 mol O2 |
| 3.0 | 5.94 | 0.0176 mol Cl2, 0.091 mol O2 |
| 4.0 | 1.00 | 0.0169 mol Cl2, 0.53 mol O2 |

**The usable window for a selective brine cell in this engine is roughly
2.2–2.7 V**, where a real one holds 99% selectivity at 3 V and above. Same shape
as the site balance: right at low loading, wrong at high. ⚠ Pinned by a test as
a LIMIT — if a later milestone makes the ratio hold at 4 V, that test should fail
and be rewritten, not deleted.

⚠ The chlorine PLATEAUS across 2.5–4.0 V and the oxygen does not, which is the
whole mechanic in one column: above 2.5 V the halide barrier is already floored
so more volts buy it nothing, while oxygen's is still coming down. The chloride
is a charge that runs out; the water is the solvent and does not.

### 7. ⚠ THE ADIPONITRILE ROW IS NOT AN ELECTRODE REACTION, AND THAT IS ARITHMETIC

The row reads `acrylonitrile + water -> adiponitrile + oxygen`, so the expected
shape was a fourth `electrons`-carrying template. Running the numbers first said
otherwise:

* the CELL `4 AN + 2 H2O -> 2 ADN + O2` costs **+212.7 kJ/mol** — genuinely
  uphill, genuinely needs 0.551 V;
* but `2 AN + H2 -> ADN` is **−171.7 kJ/mol**, downhill on its own. **The voltage
  does not pay for the carbon–carbon bond.** It pays for tearing hydrogen out of
  water, which is `water_electrolysis` and is in every aqueous cell already.

So the route is two steps whose overall stoichiometry — the oxygen included —
EMERGES. Measured end to end: 65.6% conversion at 3 V, nothing at 2 V.
⚠ **The cost is stated rather than hidden:** routing the electrons through free
H2 puts the route's threshold at water's 1.441 V instead of its own 0.551 V,
**0.89 V too high**. Baizer's cell runs near 4 V so nothing about whether it RUNS
turns on it, but the threshold this engine reports is the wrong one.
⚠ The alternative was measured and refused: written as the one 6-slot lump the
row implies, the rate law is FOURTH ORDER in acrylonitrile, the limiting
reagent — `sulfur_combustion`'s stall in the case its own note says is NOT
forgiven, where the yield stops being chemistry and becomes a reading of `A`.

### 8. WHAT IS EMERGENT

* Kolbe generalises with nothing enumerated: acetate + propanoate gives ethane,
  propane **and** butane, because the two reactant slots fill independently.
  ⚠ Read the 1.49 : 0.98 : 0.57 ratio as the three rate constants Evans-Polanyi
  set from three slightly different dH — the STATISTICAL factor of 2 on the cross
  is not in it, which is this engine's mass-action convention everywhere.
* One halide template covers Cl, Br and I, and bromide goes at a lower voltage
  because its chemistry costs less. Nothing was told that.
* Kolbe needs the CARBOXYLATE: a flask of glacial acetic acid does not
  electrolyse, and the template says so by matching `[O-]`.

**Files:** `reactions/electrochemistry.py` (new, 4 templates),
`reactions/template.py` (`electrons` + two refusals),
`reactions/reaction.py` (`electrical_work`), `reactions/thermo.py` (the
subtraction + `decomposition_potential`), `network/builder.py`
(`cell_potential`), `constants.py` (`FARADAY`),
`validation/cell_potentials.py` (new, standing audit),
`examples/electrolysis_cell.py` (new, 5 panels),
`tests/test_electrochemistry.py` (new, 21 tests).

---

## M8 — Electrochemistry  *(the original brief, kept for the record)*

Electrode potentials and Faraday's law. Unlocks `electrolysis` outright:
**chloralkali, Hall-Héroult aluminium, the Downs cell, Castner-Kellner** — and
gates conducting polymers behind M9.

⚠ **THIS ONE WILL BREAK THE SPECTATOR ZEROS**, and it is the only planned item
that does. HANDOFF 78-79's rule is that *a zero is safe while no consumer reads
it once* — the five pH invariants survived M3 because the Ksp is computed from
two independent tables and consumed as a NUMBER. A half-cell potential is not
consumed as a number: it puts the ion back into an equilibrium the kernel
evaluates. Budget for re-deriving the five pH values, do not budget for them
being unmoved.

**Done when:** brine electrolyses to chlorine and caustic soda, the current is
the control, and Faraday's law falls out of the integration rather than being
asserted.

---

## M9 — Polymers as chain-length distributions  *(12 routes; the design has seen this problem twice before)*

**Species enumeration is the wrong representation for a polymer**, and this is
the same failure as the network explosion, seen a third time: a self-feeding
template that regenerates its own matched group runs to the species cap. The
catalog wants **Bakelite, nylon 66, PET, polyethylene, PVC, PTFE, polyurethane,
neoprene, urea-formaldehyde, polylactide, MMA and styrene** — twelve routes, and
the most recognisable industrial chemistry of the 20th century.

The representation is a population balance, most likely method-of-moments: carry
the first few moments of the chain-length distribution as state rather than one
species per degree of polymerisation. ⚠ **That is a new KIND of state variable**
— not a species count — so `PHASE_INDEX`, the conservation report and the
non-negative projection all have to be told what it is. Scope this before
promising it.

⚠ **And check the cheap approximation FIRST, as M3 and M4 both should have
taught:** a route whose *target* is the polymer but whose interesting chemistry
is the MONOMER (vinyl chloride, styrene, MMA, caprolactam) may only need the
monomer step, with polymerisation as a terminal sink. Measure how many of the
twelve that covers before building a moment closure.

**Done when:** a polymerisation runs without enumerating species, and the number
average and dispersity come out of the integration.

---

## M10 — Saturation-form rate laws  *(8 routes, one of them the oldest chemistry there is)*

⚠ **THIS IS THE LARGEST UNOWNED WALL, and it was not in any milestone until an
audit went looking.** Every rate in this project is power-law mass action, so
**Langmuir-Hinshelwood and Michaelis-Menten have nowhere to live** — a surface
or an enzyme has a SITE BALANCE, which is a denominator term, and the kernel
admits no rate form beyond `A·exp(-Ea/RT)·∏cᵛ`. That is exactly why homogeneous
catalysis was free (HANDOFF 37, a folded concentration) and this is not.

What it blocks, measured against `data/catalog`:

| route | era |
|---|---|
| **ethanol by fermentation** | ancient |
| Tyrian purple from murex | ancient |
| acetone-butanol-ethanol fermentation | 1900s |
| citric acid by fermentation | 1900s |
| monosodium glutamate | 1900s |
| penicillin fermentation and semisynthesis | 1900s |
| lactic acid to polylactide | modern |
| *(plus `biological-oxidation` / `biological-reduction` steps)* | |

**Brewing is the oldest applied chemistry in the catalog and the engine cannot
express it.** For a game inspired by preparative chemistry that is a worse hole
than aluminium.

⚠ Note the field to hang it off ALREADY EXISTS: `orders` (declared rate orders,
HANDOFF's declared-rate-order work) was the cheap first case of this backlog item
and explicitly does NOT close it — there is still no denominator. Adding one is a
kernel change, so it needs the full suite behind it.

⚠ **A declared rate order may never be reversible**, and the same will hold of a
saturating form: detailed balance derives the reverse pair from the forward
kinetics, and a Michaelis-Menten forward rate has no Arrhenius reverse. Expect to
declare these irreversible and say so.

⚠⚠ **CHECK THE CHEAP APPROXIMATION FIRST — AND IT NEEDS NO KERNEL CHANGE AT
ALL.** `orders` is a per-slot exponent tuple summed into the exponent matrix the
kernel has always carried, and **zero is already a legal order** — the sulfur
burner declares `(1, 1, 0, 0, 0, 0, 0, 0, 0)`. A declared order of **0 in the
substrate** IS the saturated limit of Michaelis-Menten: the reaction runs at a
constant rate set by enzyme loading until the substrate is exhausted, which is
most of what a fermentation looks like from outside. That gets the plateau, the
loading dependence and the sharp end-point today, for the cost of one tuple.

What it does NOT get is the TRANSITION — the approach to saturation, and the
crossover to first order as substrate runs out. So measure whether any catalog
route actually depends on the transition before building a denominator term. If
none does, M10 collapses from a kernel change into a template exercise, and the
milestone should say so rather than being built out of tidiness.

**Done when:** a fermentation runs to a substrate-limited plateau rather than to
completion, and the plateau moves with enzyme loading.

---

## M11 — The unpriceable families  *(16 routes, and it is curation, not research)*

⚠ **ALSO UNOWNED UNTIL AN AUDIT WENT LOOKING.** 472 of 1583 catalog compounds are
refused outright, and `data/catalog/COVERAGE_REPORT.md` already classifies every
one by cause. What no milestone did was commit to closing a family. Sixteen
routes touch a compound class that nothing in this project can price:

| family | routes | what dies with it |
|---|---:|---|
| isocyanate | 4 | Curtius, Hofmann rearrangement, MDI, polyurethane |
| sulfonic-acid | 4 | DOP plasticiser, alkali fusion, picric acid |
| organometallic | 3 | **Grignard addition, Wittig olefination**, Ziegler-Natta |
| pigment | 2 | **Prussian blue**, chrome yellow |
| azo | 1 | **diazotisation and azo coupling** — the founding dye chemistry |
| organosilicon | 1 | silicones by the direct process |
| sulfonamide + sulfonyl-halide | 1 | **sulfanilamide**, the first antibiotic |

⚠ **START WITH THE BUCKET THAT IS ALREADY COSTED.** The coverage report separates
**10 species that need exactly ONE measured boiling point each** — their
formation half already resolves from Benson, and they are refused only because
nothing prices their vapour pressure. `4-hydroxybenzaldehyde`,
`4-methylbenzaldehyde`, `5-hydroxymethylfurfural`, `carbonic-acid`,
`diethyl-carbonate`, `dimethyl-carbonate`, `ethyl-formate`,
`norbornene-dicarboxylic-anhydride`, `performic-acid`, `phenyl-radical`. That is
a lookup, not a research problem, and it has been sitting costed and unclaimed.

⚠ **AND CHECK BEFORE PROMISING THE REST.** 276 of the refusals want a group value
*that may not exist in any published tabulation*, and 186 are charged organics
outside the Born domain **where the refusal is correct** — the Born radius
correlation is fitted to small hard ions and an organic cation is not one. This
milestone is the curatable remainder, not the whole 472.

⚠ Every entry goes through `thermochemical-data-curation`'s rules: source it,
never recall it; derive Gf rather than transcribing it; never mix sources within
one entry; cross-check everything.

**Done when:** azo coupling, a Grignard and sulfanilamide can all be priced, and
the 10-boiling-point bucket is empty.

---

## ✔ M12 — The adiabatic energy leak  **DONE 2026-08-24**  *(engine)*

**An insulated flask destroyed 495 J after a precipitation event, against a
0.0087 J chemical budget.** Now reads **+0.15759 K at 3600 s in one call**,
agreeing with itself at every tolerance rung from 1e-6 to 1e-9, with **+0.005 J**
unaccounted over the post-event window. HANDOFF 82 has the full account.

**The cause was in Layer 2, not in the solver, the energy equation or the
precipitation term.** `dissociation_templates` sets `Ea = 60 kJ/mol` for water
autoionization so the elementary-barrier clamp does not fire on water's 55.8
kJ/mol dissociation enthalpy — which leaves detailed balance handing the REVERSE
a 4.2 kJ/mol barrier and a rate constant of **9.4e18 L/(mol s), 9.4e7 times the
collision limit**, for a recombination measured at 1.4e11. Its two heat terms
then sat at ±5.2e9 W around a net of a fraction of a watt, and three consecutive
BDF steps of 167.63 s destroyed 467 of the 495 J while the composition did not
move by a picomole.

⚠ **The asymmetry that allowed it, in one sentence: this project has always
refused an impossible hand-authored pre-exponential and never checked the ones it
DERIVES.** `reactions.thermo.COLLISION_LIMIT` closes that — both pre-exponentials
scaled by one factor, so `K = k_f/k_r` is invariant exactly and Kw stays
1.0022e-14. Exactly one reaction in the project needed it.

**Four fixes were refuted by measurement first**, and each will be proposed
again: the precipitation term (controlled for), the energy equation's algebra
(`q_rxn / (-dH·dn) = 1.000000` pointwise), tolerance in BOTH directions
(tightening the temperature's own budget made it *worse* — 31,324 steps), and the
integrator (Radau and LSODA both get it right and neither survives the prep).

**The audit shipped too**, which was the other half: `Vessel.energy_report()`
prints the GROSS reaction heat beside the net — a net of 1e-3 W looks identical
whether a flask is at rest or whether two 5.2e9 W terms are cancelling to twelve
digits — plus `VesselIntegrator.energy_terms`, `validation/rate_ceiling.py` and
`tests/test_energy_balance.py`.

**It also made everything faster.** The stiffest mode in every aqueous flask got
6.7e7× slower: the benzoic-acid prep runs in **6.0 s where it took 39.4 s**, and
its converged benzoate is unchanged to nine figures (0.199993746).

⚠ **STILL OPEN, REPORTED RATHER THAN FIXED:** the guard is evaluated at 298.15 K,
and `carboxylic_acid_dissociation_rev` **crosses the ceiling at 416.6 K** — a
temperature a reflux reaches. `validation/rate_ceiling.py` prints every crossing.
⚠ And `born_A` is zero for `[Ag+]`, so silver is carried as a NEUTRAL by the ion
transfer term; harmless in one aqueous phase, wrong in an extraction, and
nothing says so.

---

# ⚠⚠ THE G-SERIES -- THE GAME ARC, ADDED 2026-08-27 ON A DIRECTION CHANGE

⚠⚠ **THE CATALOG IS A MEASURING INSTRUMENT AND WAS BEING READ AS A
SPECIFICATION.** 173 named industrial routes is an excellent yardstick for *does
the engine cover chemistry*. It is a poor target list for a game: nobody wants to
replay the Solvay process, all 173 is ~100 sessions, and the last 60 are
polymers, fermentation networks and spatial models -- the least interesting
chemistry in the corpus.

⚠ **AND THE SCOREBOARD MISMEASURES IN BOTH DIRECTIONS**, which is why seven good
sessions looked like stagnation:

* it **overstates**, because a runnable route need not be *reachable*. Measured
  2026-08-27: of the 31 routes in the BOTH column, **only 13 connect to natural
  materials.** 14 are blocked on an intermediate the engine cannot make and 4
  start from a reagent bottle nothing in the corpus fills.
* it **understates**, because it scores the CATALOG's granularity rather than the
  ENGINE's ability. `benzene-nitration` is written as a three-step arenium
  mechanism (`nitronium-generation`, `electrophilic-aromatic-substitution`,
  `arenium-deprotonation`) and therefore scores as not-template-ready -- while
  the engine nitrates benzene quantitatively TODAY:

      benzene 1.0 + nitric acid 1.2, 340 K, 2 h
        benzene left  0.0000     NITROBENZENE  1.0000 mol     conservation clean

⚠ **THE CONTENT SLOPE IS NOT AN ASYMPTOTE, AND THE EARLIER READING OF IT WAS
TAKEN OVER THE WRONG SESSIONS.** S7-S13 averaged +1.6 routes/session, but every
one of those seven was an ENGINE or DATA session; none was a content session.
The greedy set-cover curve is the real content slope: **20 templates take
template-ready 41 -> 72**, and the RUNNABLE column converts at roughly half, so
**20 templates is about 31 -> 46 runnable.** At the demonstrated content rate
(S11 built two templates, S12 built one) that is 10-20 sessions. ⚠ There is still
**no lever** -- 47 routes are one class away, from 37 DIFFERENT classes (G4's
`saponification` credit moved both by one) -- so it is a grind with a real slope,
not a breakthrough waiting to happen.
⚠⚠ **AND G4 MEASURED THAT THE GRIND IS THE REAL WORK.** Of the 142 routes outside
the BOTH column, exactly **5** turned out to be catalog bookkeeping rather than
missing capability; the other 137 are chemistry this engine cannot do or data
nothing prices. **There is no shortcut hiding in the scoreboard.**

## ⚠⚠ THE GOAL, STATED, SO THAT WORK CAN BE SCORED AGAINST IT

> **A connected tech tree: ~10 natural starting materials to ~40 targets, every
> one reachable from the ground, with the 1800s aromatic branch lit up.**

⚠ **COVERAGE IS NOT CANCELLED, IT IS DEFERRED.** The C-series (below, unwritten)
is where "add the boring reactions until the corpus is covered" lives, and the
G-series does nothing that makes it harder -- every template the G-series builds
counts for coverage too. The decision is about ORDER, not about scope.

## G1 -- The dropping funnel, and the first playground  ~~*(the fastest testable slice)*~~ ✔✔ **DONE 2026-08-27**

⚠⚠ **AND THE BRIEF BELOW NAMED THE WRONG GAP. READ HANDOFF §99 FIRST.** Every
one of the four items in the build list already existed as the rig's `meter`
edge, which `rig_integrator` documents as *"a dropping funnel or a syringe
pump"*: it delivers a set rate, it CARRIES THE DONOR'S SENSIBLE HEAT (270 K
funnel -> pot at 298.13 K, 370 K funnel -> 364.12 K, same moles), its reservoir
runs out exactly (0.001 to 10 mol/s, conserved to 1e-12), and `SET_EDGE`
already opens and shuts it inside a saveable scenario. A `feed` vector was
REFUSED as a second home for all of it, with a `feed_T` that is a declared
constant where a funnel VESSEL's temperature is a solved one.

⚠⚠ **WHAT WAS REAL IS THE ONE THING THE BRIEF SAID CAME FOR FREE.** *"It
composes with `wait_until` for free"* is FALSE, for exactly the reason
`collect_fraction` exists: an Event carries an absolute `t`, so a tap-close
scheduled after a discovered instant bakes THIS run's crossing into the recipe
and the same recipe REFUSES at twice the charge. `World.add_dropwise` stores
the condition. **SAVE_VERSION 5 -> 6** -- for a different reason than the brief
gave: an unknown SCRIPT VERB is discovered part-way through `run_script`, so a
v5 reader stops half-way through a recipe holding a world that looks finished.

⚠ **NO RHS EDIT, SO `tolerance_audit.py` WAS NOT OWED.** Playground:
`examples/dropping_funnel.py` (39 s). Audit: `validation/dropwise.py` (78 s).

*The original brief follows, kept because the measurement that overturned it
only means something against it.*


⚠⚠ **THE TARGET VIGNETTE, IN THE USER'S OWN WORDS**: toss a handful of materials
in a vessel, heat it, drip an acid in -- and *if you drip too much at once it
heats up and changes the reaction*, so you have to cool it and add slowly -- then
collect the vapour, run it through a condenser, and take the drops in a
temperature range.

⚠ **MEASURED AGAINST THE ENGINE, 2026-08-27. EXACTLY ONE MECHANIC IS MISSING:**

| the vignette | the engine |
|---|---|
| a handful of materials in a vessel | ✔ `Vessel.charge` |
| heat it up | ✔ `Q_input` / `SET_HEAT` |
| **drip an acid in slowly** | **MISSING** |
| too fast -> it heats up -> the reaction changes | ✔ emergent, once a feed exists |
| cool it down | ✔ `SET_ENVIRONMENT`, `UA` |
| collect the vapour, condense it | ✔ `Rig` vapour + drain edges |
| take the drops in a temperature range | ✔ `collect_fraction(enter, leave)` -- M2 |

⚠ **`ingress` IS NOT THE MECHANIC AND MUST NOT BE STRETCHED INTO IT.** It is
mol/s into the HEADSPACE, it is a constant, and it models an air leak. A dropping
funnel adds to LIQUID LAYER 1, carries SENSIBLE HEAT, and RUNS OUT.

**The build, and it is small:**

1. `VesselConditions.feed` -- an (n,) mol/s vector added to the **liquid layer 1**
   block of the RHS, beside where `ingress` is added to the vapour block.
2. `VesselConditions.feed_T` -- the temperature of what is being added, so the
   energy equation gets `sum(feed * Cp) * (feed_T - T)`. ⚠ **THIS TERM IS THE
   WHOLE POINT**: without it, dripping ice-cold acid warms the flask exactly as
   fast as dripping boiling acid, and the "cool it and add slowly" mechanic is
   cosmetic.
3. **THE RESERVOIR IS NOT STATE.** A funnel that runs out looks like a new state
   block and must not become one -- see the block-order trap. It is a DURATION:
   `total / rate`, derived, with the feed set back to zero afterwards. That is
   also what makes it a RECIPE rather than a script, and it composes with
   `wait_until` for free ("drip until the pot reaches 340 K, then stop").
4. A `SET_FEED` event so a drip saves and replays. **SAVE_VERSION 5 -> 6.**

⚠ **IT TOUCHES THE RHS**, so: `feed=None` must reproduce the current engine BIT
FOR BIT, and `tolerance_audit.py` is owed. S9's bit-identical test is the template.

⚠ **THE PLAYGROUND ITSELF SHOULD USE A FAMILY THAT ALREADY RACES**, and one
exists: `competing_pathways`' five templates on ethanol / acetic acid / air. Its
ester yield is measured at **85.6% at 420 K falling to 6.4% at 510 K**, so
temperature genuinely selects the product -- and both feedstocks are
**from-the-ground** (fermentation, then vinegar). ⚠⚠ **DO NOT BUILD IT ON
NITRATION -- MEASURED AND REFUSED, SEE G2.**

## G2 -- Ring deactivation, so nitration is a PROCESS and not an EVENT ✔✔ **DONE 2026-08-27**

✔ **BUILT AS THE BRIEF SCOPED IT, AND ITS FOUR DESIGN QUESTIONS ALL ANSWERED
THE WAY IT GUESSED.** It lives at SETUP (`build_network` bakes the shifted `Ea`
into the kinetics array -- no RHS edit, no tolerance-audit exposure); the
basis is Hammett; an unsubstituted ring keeps the declared barrier BIT FOR
BIT; and the corpus cost is four measured routes. See HANDOFF §100 and
`src/chemsim/reactions/hammett.py`.

⚠⚠ **THE ONE THING THE BRIEF DID NOT SAY, AND IT IS S12'S FINDING AGAIN: A rho
IS MEANINGLESS WITHOUT ITS SIGMA SCALE.** The table is **sigma-PLUS** (Brown &
Okamoto 1958), because electrophilic substitution builds positive charge on
the ring -- methoxy is -0.27 on sigma and -0.778 on sigma+, amino -0.66 and
-1.30. A sigma+-fitted rho applied to aqueous sigma is two bases multiplied
together.

**The result**: three barriers 25.0 kJ/mol apart, and 1.0 mol toluene + 3.5 mol
nitric acid is mono at 300 K/10 s, di at 300 K/100 s and 340 K/1 h, and TNT
only at 380 K -- the escalating sequence real manufacture uses. `tnt-route`
0.1528 -> 0.0662 mol (worse and righter); `benzene-nitration` 0.1762 ->
**0.8000** and `picric-acid-route` 0.0481 -> **0.1208** (both improvements,
because a mononitration can now STOP); `ddt-route` unchanged.

⚠ **THREE THINGS IT DOES NOT DO AND THEY ARE NAMED**: no regioselectivity (the
sum has no attacked carbon in it), no PROTONATION (aniline is priced as a free
base at 2.8e8 x benzene where the real anilinium is slower than benzene, and
4-aminophenol drives the barrier through a reported clamp), no sterics.
**Protonation coupled into a barrier is the next item on this branch.**

*The original brief follows.*


⚠⚠ **THE OBVIOUS DEMO REACTION WAS TESTED FIRST AND IT DOES NOT WORK.** Nitration
is the canonical add-slowly-or-it-runs-away reaction in all of chemistry, so it
was the natural choice for G1. Measured, 1.0 toluene + 3.5 nitric acid, staged by
nitro count:

      T/K      t/s  toluene     mono       di      tri
      300       10   0.0008   0.0098   0.0278   0.9616
      300      100   0.0000   0.0000   0.0000   1.0000
      340       10   0.0000   0.0000   0.0000   1.0000
      380     1000   0.0000   0.0000   0.0000   1.0000

**96% TRINITRO IN TEN SECONDS AT ROOM TEMPERATURE, AND THE ENDPOINT DOES NOT MOVE
WITH TEMPERATURE AT ALL.** There is no stage to catch and nothing for an addition
rate to control.

⚠ **THE CAUSE IS EXACT AND IT IS ONE LINE**: `aromatic_nitration(A=1.0e10,
Ea=60_000.0, alpha=0.0)` gives **one A and one Ea to every nitration on every
substrate**, so 2,4-dinitrotoluene nitrates exactly as fast as toluene. In
reality each nitro group deactivates the ring by 4-6 orders of magnitude, which is
precisely why TNT manufacture is a THREE-STAGE process with escalating acid and
temperature.

⚠⚠ **AND THE CHEAP FIX IS THE WRONG ONE. DO NOT JUST RAISE `alpha`.** S11
measured that Evans-Polanyi names the WRONG major product when kinetics fight
thermodynamics, and set `alpha = 0.0` on both hydroformylation templates for
exactly that reason. A substituent effect on an aromatic ring is an ELECTRONIC
property of the substrate, not a function of the reaction enthalpy, and dressing
one up as the other would be the `chemsim-competing-templates` trap again.

⚠ What this is really asking for is a **substituent-aware barrier** -- a term that
reads the ring's existing substituents and shifts Ea. That is new capability and
it is worth scoping properly. ⚠⚠ **AND IT IS THE HIGHEST-VALUE ITEM IN THE
G-SERIES**, because the same missing effect gates the whole 1800s aromatic tree:
dyes, explosives and painkillers all live on selective substitution, and the
engine currently cannot tell a deactivated ring from a fresh one.

## G5 -- Protonation coupled into a barrier ✔✔ **DONE 2026-08-27** *(and the answer is that it is a DATA job, and it does not close the gap)*

⚠ **NUMBERED G5 AND PLACED HERE ON PURPOSE.** It was not in the original
G-series list -- G2 created it as *"the best-scoped new item"* and NEXT_PROMPT
carried it above G3. Done items are kept in completion order at the top of this
section, so G5 sits between G2 and the unbuilt G3/G4 rather than after them.

⚠⚠⚠ **THE BRIEF'S FIRST DESIGN QUESTION WAS THE RIGHT ONE AND THE ANSWER
KILLED THE DESIGN.** G2 asked: *"Is it a barrier shift or a species split? ... 
Measure that before designing a coupling -- it would be a data job, not an
engine one."* It IS a species split, `dissociation_templates()` DOES already
make the ion, and the table row is three lines. **And the arithmetic bound,
taken before any of it was written, says the split does not fix aniline.**

Two channels run in parallel and the pot's acidity weights them:

    free base   -NH2   sigma+ -1.300   k/k0 = 2.8184e+08
    anilinium   -NH3+  sigma  +0.860   k/k0 = 2.5704e-06     ratio 1.10e14

    crossover at [H3O+] = Ka * k_free / k_ion = 2.630e+09 mol/L,  pH -9.42

⚠⚠ **AND -9.42 IS NOT A WRONG NUMBER.** Real aniline gives largely meta product
only in 90-98% sulfuric acid, whose Hammett acidity function H0 falls to
roughly -8 at 90 wt% and roughly -10 at 98 wt%. ⚠ The band is quoted to ONE
FIGURE because it is recalled rather than sourced here: the claim is that -9.42
lands INSIDE the band real aniline nitration is run in. The engine's own two
table rows land it there without being told about it. **The split is the right model; the flask
cannot get there.**

⚠⚠⚠ **AND THE WALL IS A SECOND MEASUREMENT NOBODY HAD TAKEN: THE POT GETS LESS
ACIDIC AS THE ACID GETS DRIER.** 5 + 5 mol of HNO3/H2SO4 in 30 mol of water
reads **pH -0.789**; the same acid in 10 mol reads -0.233 and in 2 mol reads
**+4.899**. Every dissociation here is written with water on both sides, so
`[H2O]` is a mass-action factor and running out of water suppresses the reaction
that makes the proton -- real chemistry the engine gets for free, and also the
ceiling. **The reachable floor is pH -0.79, ten decades above the crossover.**

⚠ **SO THE LIMIT IS RENAMED RATHER THAN REMOVED. It is not "no protonation in a
barrier" any more; it is "NO ACIDITY FUNCTION"** -- H0 is not the concentration
of anything, and this engine's only handle on acidity is a mass-action molarity.
That is a better-posed gap than the one G2 named, and it is the honest state of
the aromatic branch.

**What was built, and what it buys:**

* `ion_thermochemistry` anchors on the **NEUTRAL** member of a pair rather than
  on the acid. ⚠⚠ **FOUR CURATED ROWS HAD BEEN PRODUCING NOTHING** -- ammonium,
  methylammonium, pyridinium, anilinium are CATION/neutral pairs whose acid is
  the ion, and a bare `except Exception: continue` swallowed the (correct)
  refusal to price a charge. **Refused species 430 -> 419, ion-resolvable
  84 -> 95, species-ready routes 80 -> 82, `solvay-process` 0 -> species-ready.**
  Eleven corpus species -- every ammonium salt in the catalog -- and
  `COVERAGE_REPORT.md` had been printing the refusal for twelve of them, session
  after session. The 24 anions are BIT-IDENTICAL.
* an `ammonio` sigma row (0.86 / 0.60, labelled PROXY, meta-directing DECLARED),
  so an anilinium is no longer priced as an unsubstituted benzene. ⚠ It is the
  one row whose two constants are ordered the wrong way round, which is the
  second reason `meta_directing` is not derived.
* `amine_protonation` replaces `ammonium_dissociation`, whose `[NX4H+]` matched
  a protonated TERTIARY amine and nothing else -- **the template named for the
  ammonium ion was the one ion it could not touch.** Written
  protonation-forward, because discovery is forward-only.

**Measured in the engine: 2.8e8 -> 380 x benzene. Six of the fourteen decades.**
⚠⚠ **And the other eight are not in the protonation model** -- the anilinium is
100.000% of the aniline in the pot and carries **1e-7 %** of the rate. The
residual is a FREE-BASE LEAK, and the next item is named with its arithmetic
done: `rho * sigma+` = 8.45 decades off a line fitted on |rho*sigma| < 2.6, where
the real relation SATURATES because nitration of an activated arene is
encounter-controlled. See HANDOFF §101 and `validation/protonation.py` panel 5.
⚠⚠ **AND ITS DESIGN QUESTION IS WHICH OF TWO THINGS IT IS**: a capped RATIO of
decades (SETUP, free, but asserts a temperature-independent selectivity at the
ceiling) or an absolute ENCOUNTER RATE (physically right, but the two rate laws
have different temperature dependences, so it is an RHS edit with the tolerance
audit attached). **Measure the temperature spread over 300-380 K first** -- if
the capped rates stay well under the encounter limit there, the two forms are
indistinguishable and the cheap one wins. See NEXT_PROMPT.

⚠ **A NEW STRUCTURAL MISMATCH, AND THE REFUSAL IS KEPT:** a protonation
TEMPLATE is open-ended where the ion table is a CURATED LIST, so nitrating an
aniline refuses to build on a nitroanilinium nobody curated. Curating the nine
pKa values is measured to buy nothing, so the refusal stands -- the element
floor's rule applied to a pKa.

⚠⚠ **AND THE PLAYABLE RESULT IS THE ONE REAL CHEMISTRY USES, ALREADY
BUILDABLE:** nobody nitrates an aniline, you acetylate it first. An amide does
not answer `amine_protonation`'s pattern, so the acetanilide network BUILDS where
the aniline one refuses. **Nobody told the engine that an amide is a protecting
group.**
⚠ **G6 CHANGED WHY THIS WORKS AND NOT WHETHER IT DOES.** G5 wrote it as a
BARRIER difference -- acetanilide activated by 22.3 kJ/mol against aniline's 48.2
-- and under the encounter plateau both rings are activated by the same 15.3
kJ/mol, because both ask the line for more than 2.686 decades. The protection is
therefore entirely about PROTONATION, which is the real mechanism: an amide has
no lone pair to protonate and an aniline in mixed acid is an anilinium.

## ⚠⚠ WHAT IS LEFT — **THE G-SERIES IS COMPLETE** (2026-08-27, AFTER G3)

    1. G4 -- the granularity audit           ✔ DONE. The answer is FIVE, and
                                                the useful half of it is that
                                                the number is SMALL
    2. the HAMMETT LINE SATURATES            ✔ DONE as §G6. A sourced encounter
                                                plateau; the design question
                                                answered itself in a measurement
    3. G3 -- PLAYABLE.md                     ✔ DONE. 12 of 173, three tiers, and
                                                the C-series is a 21-row TABLE
                                                rather than a grind

⚠⚠⚠ **THE ARC IS THE C-SERIES NOW, AND G3 HANDED IT A WORK ORDER INSTEAD OF A
BACKLOG.** Every G-series item is built. The next thing to build is CONTENT, and
`data/catalog/PLAYABLE.md` §8 says which content: **21 routes are already fed
from natural materials and blocked only on a template or a price**, and granting
all 21 takes playability from 12 to **37** — the G-series GOAL's own ~40. The
other 116 unrunnable routes move a coverage number and no player can reach them
until something in the 21 lands. ⚠ **Read that table before picking a template.**

⚠⚠ **THE ORDER WAS TAKEN AS WRITTEN AND BOTH ITEMS PAID FOR THEMSELVES IN THE
WAY THE ARGUMENT ABOVE PREDICTED, WHICH IS WORTH RECORDING BECAUSE THE ARGUMENT
WAS ABOUT ORDER RATHER THAN VALUE.** G4 went first for M1's reason -- a session
spent against an unmeasured scoreboard may be aimed at a gap that is not a gap --
and it retired the unknown by measuring that 137 of 142 routes outside the BOTH
column are real work. G6 then spent itself on chemistry without hedging, and its
own corpus cost came out at ZERO, which G4's number had already predicted.
**Neither session's headline was the one its brief expected**: G4's was that FIVE
is small, G6's was that the physically-correct-sounding model could not fire.

⚠ **AND THE COUNTER-ARGUMENT THAT WAS KEPT IS NOW SPENT.** It said the G-series
exists because the catalog *"is a measuring instrument and was being read as a
specification"* and that more instrument work risks the trap §"the shape of the
plan" names. The answer is in hand and **there is no remaining instrument question
standing between this project and content work.** G3 is the exception and it is a
different artefact: it answers *what can a player make*, which no existing report
asks.

## G6 -- The Hammett line SATURATES ✔✔ **DONE 2026-08-27** *(and the answer to its design question was a measurement, not a preference)*

⚠ **NUMBERED G6 AND PLACED HERE FOR G5's REASON.** It was not in the original
G-series list either: G5 created it, measured its arithmetic and deliberately
did not build it because the CONSTANT needed sourcing. NEXT_PROMPT carried it as
item 1 of the work order. Done items are kept in completion order.

**WHAT IT IS.** `rho * sum(sigma+)` priced aniline **8.45 decades** above
benzene off a line fitted on arenes with |rho·sigma| < 2.6 -- a 3.25x
extrapolation of the abscissa -- and the real relation does not go there:
nitration of a strongly activated arene is **ENCOUNTER-CONTROLLED**, so past a
plateau further activation buys no rate at all.
`hammett.SATURATION_DECADES = 2.686`, one-sided, declared per template as
`ReactionTemplate.hammett_saturation`. **At SETUP, so no RHS edit and no
tolerance-audit exposure**, and everything under the plateau is bit-identical.

⚠⚠⚠ **THE BRIEF'S DESIGN QUESTION -- CAPPED RATIO OR ABSOLUTE ENCOUNTER CEILING
-- ANSWERED ITSELF IN A MEASUREMENT, AND NOT THE COST ARGUMENT THE BRIEF
EXPECTED.** `min(k_hammett, k_enc)` is the physically correct form for an
ELEMENTARY step, and it can only ever fire on the one case a floor already
catches: with the plateau lifted, every substrate with a positive barrier runs
at 0.9-1.2% of a diffusion ceiling or less, and only 4-aminophenol reaches it
*because* `clamp_barrier` has already floored its barrier at zero, leaving
`k = A = 1e10`. ⚠⚠ **AND THE REASON IS STRUCTURAL: THIS RATE LAW IS NOT
ELEMENTARY.** `aromatic_nitration` is written on the arene and HNO3, so the
nitronium pre-equilibrium is folded into `Ea`; an absolute ceiling in these units
would have to be `k_enc * [NO2+]/[HNO3]`, a property of the medium's ACIDITY --
the thing G5 measured this engine has nowhere to put. The observable plateau
sits **six decades below** any diffusion constant. **The capped ratio is not the
cheap approximation to the right model; it is the only one that can express what
was measured.**

⚠⚠ **THE CONSTANT IS HAND-AUTHORED AND THE BOUND IS THE DELIVERABLE**, which is
the licence § STATED NON-GOALS gives an A-factor. Belson & Strachan, *J. Chem.
Soc., Perkin Trans. 2*, **1989**, 15 (aq. HNO3, 293-333 K):
benzene : toluene : p-xylene : mesitylene = **1 : 22 : 256 : 485**, with
p-xylene and mesitylene *diffusion-controlled and the others not*; log10(485) =
2.686. Coombes, Moodie & Schofield, *J. Chem. Soc. B*, **1968**, 800: the limit
exists and IS the encounter rate, with benzene within a SIXTH of it in the
strongest acids.
⚠⚠⚠ **AND THE SECOND SOURCE IS THE LOWER BOUND RATHER THAN A RIVAL VALUE.**
Benzene-within-a-sixth reads as 0.778 decades and applying it caps **toluene at
6.0 against a measured 22** -- damaging a substrate the same literature says is
NOT diffusion-controlled. **A plateau cannot sit below the fastest substrate that
does not saturate**, so the band is 2.02-2.69 and the declared value is its top.

**THE RESULT.** mesitylene 1.16e6 -> **485** (the datum; a 2400x correction),
p-xylene 1.10e4 -> 485 against a measured 256 (1.9x high, the factor the
plateau's own two data differ by), toluene **untouched** at 105 against 22
(that 4.8x is `rho`'s). ⚠⚠ **And the aniline in the engine's most acidic
reachable flask goes from 1.10e3 x benzene to 1.89e-3 x -- 5.8 decades and
across the line that matters**, because the observable is that aniline in strong
acid nitrates SLOWER than benzene. **It took G5 and G6 together**: the split
supplies the deactivated species, the plateau stops the free base being priced
off the end of the line.

⚠⚠ **THE CORPUS COST IS MEASURED AT ZERO** -- `benzene-nitration` 1.0000,
`tnt-route` 0.0643, `picric-acid-route` 0.1250 mol, unchanged to four decimals,
with phenol's first nitration slowed **1968x** to get there because that step was
never rate-limiting. G4's number says why that was predictable. ⚠ **G2's
four-route cost table is a script now** rather than a HANDOFF paragraph.

⚠⚠ **AND IT COST G5 ITS HEADLINE, WHICH IS THE THING TO CARRY FORWARD.** G5
reported the free-base/anilinium crossover at pH **-9.42** landing inside the
real H0 band *"without being told about it"*, and read that as evidence the split
was right. **That agreement was a property of the extrapolation**: with the free
base at a sourced plateau the crossover is **-3.66**. The split is still the
right model and the pot still cannot reach either number, but the coincidence was
not evidence. **A number that agrees with reality is only evidence if the model
behind it is inside its own domain.**

⚠ The one-sided decision was measured too: a two-sided cap at the same value
puts 0.0345 mol of trinitro in the flask in ten seconds at 300 K and finishes at
340 K, which is G2's failure restored.

See HANDOFF §103, `validation/saturation.py` (six panels, 27 s),
`tests/test_saturation.py` (12 tests).

## G3 -- `PLAYABLE.md`, the scoreboard the goal needs ✔✔ **DONE 2026-08-27** *(and the answer is that the tech tree is a BUSH, not a tree)*

**WHAT IT IS.** `tools/build_playable.py` writes `data/catalog/PLAYABLE.md` (326
lines, ~50 s because it RUNS the deep chain) and `tests/test_playable.py` (18
tests) pins every headline in it. The question no other artefact asks:
*what can a player make, starting from what?*

    tier 1 -- from the ground                8 routes
    tier 2 -- one step up                    3
    tier 3 -- two steps up                   1     <- methanol, and that is all
    runnable but unfed                      24
    not runnable                           137
                                           173

**12 of 173 playable, against a GOAL of ~40, and the deepest chain is 3 tiers.**

### ⚠⚠⚠ 1. THE HEADLINE IS THE SHAPE, NOT THE COUNT: 8 OF THE 12 ARE TIER 1

The GOAL asks for a *connected tech tree*. This corpus is not a short tree; it is
a **fan of one-step routes off the ground with one thin chain hanging off it**.
Two thirds of what a player can make touches nothing another route made. That is
a different problem from "not enough routes" and it is the reason this artefact
had to exist rather than a bigger coverage number.

### ⚠⚠⚠ 2. THE DEEPEST CHAIN IN THE CORPUS RUNS THROUGH A BYPRODUCT, AND THE THIRD TIER IS ONE CATALYST

    zinc-smelting  1400 K  ->  zinc 0.032793 mol  AND  carbon monoxide 0.054290
      copper-smelting 1500 K on that CO  ->  copper 0.039995 mol
      water-gas-shift  700 K on that CO  ->  hydrogen 0.053445 mol
        methanol-synthesis 520 K, copper in the solid block -> 0.004154 mol

⚠⚠ **NOTHING ELSE A PLAYER CAN REACH MAKES CARBON MONOXIDE**, and the retort
makes MORE of it than of its own target. Three tier-2 routes and one tier-3 route
all want it. ⚠⚠ **AND METHANOL IS TIER 3 FOR EXACTLY ONE REASON: ITS CATALYST.**
Its CO is tier 1 and its hydrogen is tier 1 too (`chloralkali` throws hydrogen
off making caustic soda from rock salt) -- it is tier 3 only because **the copper
has to be smelted first, and smelting it needs the byproduct of smelting a
different metal.** Grant free copper and the corpus has no third tier at all.
⚠ *A catalyst is a tech-tree node, and treating one as free was measured at two
routes and one whole tier.*

### ⚠⚠⚠ 3. FOUR SCORING RULES, ALL FOUR MEASURED WRONG FIRST -- AND FIXING ONE MASKED ANOTHER

G4's rule (**the target may not be CHARGED**) was reused rather than re-derived;
it lives in `catalog.route_reachable` now and both audits call it. The three new
ones:

* **a need is decided by ORDER, not by `route_roles`** -- `lime-cycle` derives an
  EMPTY feedstock list because row 3 regenerates the limestone row 1 calcined, so
  a closed cycle scored playable while needing *nothing at all*;
* **a route shelves its target AND its byproducts**, target unioned in
  explicitly, because a route's target is not always among its products;
* **a catalyst is a feedstock**.

⚠⚠⚠ **AND THE INTERACTION IS THE FINDING.** Measured as a 2x3 grid: under the
CORRECT needs rule, shelving byproducts-only costs nothing (12 either way), so
the fouling-row bug is **invisible**; it is worth one route only under the wrong
needs rule (13 against 14). **Two rules were wrong at once and fixing the first
masked the second** -- had they been done in the other order, the shelf rule
would have looked like a distinction without a difference, gone in wrong, and
started costing routes silently the moment the lead chamber became reachable.
⚠ *Measure two suspected rules as a GRID, not as a list.*

### ⚠⚠ 4. THE SAME TWO CATALOG ROUTES BROKE THREE OF THE FOUR RULES, AND G4 HAD ALREADY FOUND ONE OF THEM

`lead-chamber` is in it twice. Row 4 (the nitrosylsulfuric acid that fouls a
chamber) is what made G4's ROW scorer call the route blocked -- and the same row
makes `route_roles` classify sulfuric acid as an INTERMEDIATE, so a shelf built
from products alone does not hold the thing the route exists to make. Row 2 then
wants nitrogen dioxide and row 3 makes it, so the **NOx carrier reads as an
intermediate when it is a starting charge** -- G4's own run had to hand it
0.004 mol by hand and measured it recovered.
⚠⚠ **AND THAT COSTS THE 18TH CENTURY ITS SULFURIC ACID.** `lead-chamber` is
blocked on a *pinch* of NO2 that nothing reachable makes; the corpus has
saltpetre as a natural material and **no step that turns it into NOx**, though
that is historically exactly where the charge came from. A **corpus** gap, and
one of the two most valuable single species in the file.

### ⚠⚠ 5. WHAT RUNNING IT BOUGHT, WHICH IS G1's QUESTION ANSWERED

⚠ **THE COPPER SMELTER IS ORE-LIMITED, NOT CO-LIMITED** -- doubling the retort's
CO moves the copper in the sixth decimal. That is the *opposite* of what the
contention above suggests and only running it settled which.
⚠ **THE CATALYST IS A GATE, NOT A MULTIPLIER** -- 0.01 mol of copper already
reaches 99.3% of the reference rate, so one ore charge is 4x more catalyst than
the route needs. A player must *reach* copper and need not stockpile it.
⚠⚠ **WHAT DOES BITE IS SCALE.** At the retort's own scale methanol converts at
**7.7%**; the same route, template and loading at the corpus's declared charge of
3 mol CO + 12 mol H2 gives **99.8%**. *"Reachable" and "worth doing" are
different questions and a static scoreboard can only answer the first.*
⚠ And the first version of the generator shadowed its own output buffer and wrote
a 200-byte file of route names. **`test_the_report_on_disk_matches_the_code`
caught it on its first run**, which is the whole argument for asserting a
generated artefact -- see §6.

### ⚠⚠ 6. THE ARTEFACT HAS TESTS, BECAUSE `ROUTE_INDEX.md` DID NOT

S3 found the route index stale by three milestones for one reason: no audit read
it. So `tests/test_playable.py` pins the headline, the tier shape, all four rules
*and their wrong answers*, the lever, and the fact that the file on disk is the
one the current code produces. ⚠ It does not diff the whole report --
`chemsim-generated-artefacts` records that a report which cannot be diffed is a
report nobody diffs -- it pins the numbers a reader would quote.

### ⚠⚠⚠ 7. THE DELIVERABLE IS A WORK ORDER, AND IT IS FINITE

**21 of the 137 unrunnable routes are ALREADY FED from natural materials.** Grant
all 21 and the fixed point reaches **37** playable -- the GOAL's own ~40, because
four more (`acetic-fermentation`, `haber-bosch`, `saltpetre-nitric`, `thermite`)
fall out free once the shelf grows. Ranked by what each is worth:

    +3  hall-heroult      1 class (molten-salt-electrolysis)  -- aluminium
                            unblocks thermite, whose iron unblocks haber-bosch
    +2  abe-fermentation, blast-furnace, iron-gall-ink, vitriol-distillation
    +1  the other sixteen

⚠⚠ **THE C-SERIES IS THIS TABLE AND NOT A GRIND AGAINST 173 ROUTES.** The other
116 move a coverage number no player can reach. ⚠ **AND THE TWO RANKINGS
DISAGREE**: `COVERAGE_REPORT.md`'s greedy curve maximises classes per template;
this maximises routes a player can walk to.
⚠ **TWO OF THE 21 NEED NO TEMPLATE AT ALL** -- `hypochlorite-bleach` and
`pyrite-roasting` are blocked purely on a refused price, and pyrite is the engine
queue's own source-blocked entry (enthalpy in WEBBOOK, entropy in nothing).
**A data refusal is now measurably a PLAYABILITY blocker and not just a coverage
one.**

### ⚠⚠ 8. NO LEVER, AND THE FREQUENT BLOCKER IS NOT THE VALUABLE ONE

The biggest single species grant is **+2** (`nitrogen-dioxide`, `aluminium`) --
the same shape as coverage's "no lever". ⚠⚠ And `sulfuric-acid` **blocks the most
routes (4) and is worth +1**, because every route it blocks is blocked by
something else too. *A histogram of blockers is not a work order; the fixed point
is, and they disagree.*

### ⚠ 9. THE HAND JUDGEMENT, PRINTED

45 species are declared NATURAL in three groups with a sourced reason each, and
the rule is stated: obtainable without running any chemistry. **The GOAL says
~10, so the list is generous by 4x and 12 is an UPPER bound.** What is
deliberately NOT natural is printed too, because that half is the arguable half:
the catalyst metals, the metals as opposed to their ores, methane, the
benzaldehyde bottle, and the fermentation products.

*The original brief follows.*

## G3 -- `PLAYABLE.md`, the scoreboard the goal needs

A generated standing audit answering the question no existing artefact does:
**what can a player make, starting from what?** `ROUTE_INDEX.md` knows feedstocks
but not what runs; `COVERAGE_REPORT.md` knows what runs but never asks whether a
feedstock is obtainable. Neither answers *"what can I make from a rock?"*

⚠ The classification is already written and measured (7 from-the-ground / 6
one-step-up / 14 blocked on an unmakeable intermediate / 4 from a reagent bottle).
⚠ **The one hand judgement in it -- which compounds count as NATURAL -- must be
printed, not hidden**, so it can be argued with.

⚠⚠⚠ **AND THE MEASUREMENT DISAGREED WITH THAT CLASSIFICATION, WHICH IS THE FIRST
THING G3 HAD TO SETTLE.** The 7/6/14/4 above sums to the 31 of the BOTH column
and it is a LOOSE ONE-STEP count: it credits a route whose feedstock is any other
route's *target*, whether or not that route can run. Re-measured on the same 31,
that rule gives **6 from-the-ground / 8 one-step (14 total)** -- so the recorded
"13 connect to natural materials" was close to right about the TOTAL and wrong
about the SPLIT. The strict fixed point, which only credits a hop onto a route
that is itself playable, gives **10 of the 31** and **12 of the 36 runnable**.
⚠⚠ **EIGHT OF THE THIRTEEN HOPS LANDED ON ROUTES THAT CANNOT RUN**, and a
one-step count cannot see that because it never asks the question twice. *A
reachability claim has to be iterated to a fixed point or it is not a reachability
claim.*

## G4 -- The granularity audit ✔✔ **DONE 2026-08-27 — the answer is FIVE, and the value of the session is that FIVE IS SMALL**

**The brief, kept because the answer only means something against it:** how many
routes are, like `benzene-nitration`, chemically runnable but scored as blocked
because the catalog spells a mechanism out in steps the engine does in one?
**Nobody had counted.** Until someone did, the BOTH column was an unknown amount
too low, and content work may have been aimed at gaps that are not gaps.

**The deliverable is `validation/granularity.py` (~18 s, five panels) and
`tests/test_granularity.py` (9 tests, 9.3 s).** Every route counted is charged
into a real `Vessel` and its moles are printed. Nothing is credited on an
argument.

### ⚠⚠⚠ 1. THE ANSWER: 31 + 5, AND EACH OF THE FIVE WAS RUN

    benzene-nitration        1.000000 mol nitrobenzene   (340 K, 2 h)
    aniline-route            0.998860 mol aniline        (470 K, 2 h, Ni charged)
    hydrogenation-margarine  1.000000 mol tristearin     (450 K, 2 h, Ni charged)
    tanning-route            1.999999 mol gallic acid    (360 K, 2 h)
    lead-chamber             0.104063 mol sulfuric acid  (650 K burn -> 350 K chamber)

**The reported 31 understates what the engine does by 16%.** But the number that
matters is the other one: **142 routes are outside the BOTH column and only 5 of
them are catalog artefacts — 4%.** ⚠⚠ **THE BOTH COLUMN WAS NOT HIDING A CONTENT
BACKLOG.** The remaining 137 can now be treated as real work rather than as
possible bookkeeping, and that retirement of an unknown is what the session
bought. M1 is the precedent both ways: it fixed this same instrument and its
corrected baseline went DOWN.

### ⚠⚠⚠ 2. THE BRIEF'S OWN WORKED EXAMPLE IS NOT IN THE BUCKET THE BRIEF POINTS AT

`benzene-nitration` is **species**-blocked, not template-blocked: `nitronium` and
`arenium-benzene` are refused a price, correctly — a mechanism has them and a
flask never holds them. The obvious search (walk the species-ready, not
template-ready routes) **would have missed the case that started the audit.**
Granularity has two forms:

* **STEP granularity** — one transformation spelled as several rows whose classes
  have no template;
* **SPECIES granularity** — one transformation spelled through intermediates the
  engine never materialises, and those intermediates have no price.

### ⚠⚠ 3. THE INSTRUMENT SCORES ROWS, AND A ROUTE IS A DAG

That is the finding underneath the count. Four of the five are blocked by a row
that **is not on the path to the target at all**:

    aniline-route            rows 1 and 2 are ALTERNATIVES, read as a sequence
    hydrogenation-margarine  row 2 is the corpus's own "trans isomer byproduct"
    tanning-route            row 2 crosslinks collagen into a MARKER, past the target
    lead-chamber             row 4 makes CHAMBER CRYSTALS -- the FOULING product

⚠ **THE CORPUS SAYS SO IN ITS OWN PROSE AND NOTHING READ IT.** Nine rows in eight
routes are named `... byproduct`, `side reaction` or `alternative`, and five more
rows in five routes have products that are a **subset** of their reactants — they
are workup (crystallisation, salting out, lixiviation, kieselguhr) and cannot ever
match a template. A coverage number that scores them as uncovered mechanisms is
counting gaps no template can close.

### ⚠⚠⚠ 4. THE SCORER MADE THREE FALSE CREDITS AND RUNNING CAUGHT ALL THREE

**This is the most transferable thing in the session.** A `TARGET-REACHABLE`
scorer — does the DAG get from feedstocks to the target — first said 38, not 36:

* `bayer-process` and `contact-process` scored reachable **by BUYING the target**,
  because in both the target is also a step-1 reactant. Bayer *purifies* bauxite;
  the contact process recycles its own acid. ⚠ **A scorer that does not forbid
  charging the target will credit every recycle loop in the corpus.** Rule added,
  38 → 36.
* `starch-hydrolysis` survived that rule and **the RUN refuted it.** `starch-unit`
  is spelled in the corpus as a single α-D-glucopyranose ring, and row 1 reads
  `starch-unit + water -> maltose` — a hydrolysis making a disaccharide out of a
  monosaccharide. The engine matched **nothing at all**: zero reactions, not a
  slow one. 36 → 35, and `benzene-nitration` (found by the other mechanism) puts
  it back to 36.

⚠⚠ **S1's *"crediting a class made a FALSE route credit"* is now a THREE-time
finding, and the only thing that caught it each time was charging a flask.**

### ⚠⚠ 5. ONE CLASS THE INSTRUMENT HAD SIMPLY NEVER KEYED

`TEMPLATE_CLASSES` mapped the M5 `saponification` template under
`ester-hydrolysis`'s name, and the catalog **also** has a class literally called
`saponification`. It read as an uncovered mechanism for eight milestones. Checked
the S1 way before crediting it — tristearin + hydroxide builds 10 species and 7
`saponification` reactions, all three esters off down to glycerol.

    reaction classes covered   51 -> 52        steps covered   114 -> 115
    routes ONE class away      46 -> 47        from classes    36 -> 37
    template-ready / BOTH      41 / 31         UNCHANGED

⚠ **+0 routes, and it was credited anyway**, because a class that reads as a gap
sends work at a template that is already built. `soap-saponification` still cannot
run: its other row is `salting-out` (a phase split) and its target
`sodium-stearate` is REFUSED — the stearate anion has no pKa in the ion table.

### ⚠ 6. WHAT WAS DELIBERATELY *NOT* DONE

**The BOTH column in `COVERAGE_REPORT.md` still says 31.** That table is a
mechanical measure of the CORPUS; the five rest on a hand judgement about five
specific rows (*this row is a byproduct, that one is fouling, that one makes a
marker*). Folding a judgement into a mechanical column is how the `deprotonation`
credit happened in M1. The report gained a **pointer** instead, so the judgement
can be argued with where it is written down.

# ⚠⚠ THE C-SERIES -- CONTENT, STARTED 2026-08-27, AND ITS WORK ORDER IS `PLAYABLE.md` §8

Where *"grind out the remaining classes, including the boring ones"* was going to
live. G3 replaced the grind with a **21-row table**: the routes that are already
FED from natural materials and blocked only on a template or a price. Everything
outside that table moves a coverage number no player can reach.

⚠⚠ **AND C1 MEASURED THE FIRST THING NOBODY EXPECTED ABOUT THAT TABLE: GRANTING
A ROW MAKES IT LONGER.** 21 rows became **24** and the ceiling moved **37 -> 41**,
because the shelf grew and four routes that were not fed became fed. *A work
order derived from a fixed point is not a burndown list.*

⚠⚠ **AND C2 AND C3 MEASURED IT SHRINKING AGAIN -- 24 -> 22 -> 20 -- WITH THE
CEILING PINNED AT 41 THROUGHOUT.** Neither phosphoric acid nor vanillin feeds a
route that was not fed already. *The list moves in both directions and the GOAL
has not moved since C1.*

⚠⚠⚠ **AND C3 FOUND THAT THE TABLE ANSWERS THE WRONG QUESTION FOR A SESSION
THAT BUILDS TEMPLATES.** §8's `worth` column grants a **ROUTE**; a template
grants a **CLASS**, and the two disagree at the top of the table -- granting
`molten-salt-electrolysis` leaves §8's +3 top row unrunnable, and granting
`slagging` moves nothing at all. **`PLAYABLE.md` §8b is the per-class table now,
and it is the one to shop in.** 9 of the 20 rows cannot be bought by a template
at any price.

⚠⚠⚠ **AND THE THREE C-SERIES ITEMS HAVE FOUND THE SAME SHAPE THREE TIMES: THE
BLOCKER RECORDED IN THE TABLE WAS NOT THE BLOCKER.** C1 -- a price for a species
**not in the route's chemistry**. C2 -- a price **in a different table**. C3 -- a
class **refused on the evidence of one of its two rows**. *Print the refusal and
read what it says before costing it, and read every row of a class before
refusing the class.*

## C1 -- Oil of vitriol from a rock ✔✔ **DONE 2026-08-27** *(and the route was blocked on a price for a species that is not in its chemistry)*

**12 -> 14 playable, 36 -> 37 runnable, 52/229 -> 53/236 classes, 82 -> 83
species-ready, 41 -> 42 template-ready, 31 -> 32 BOTH.** One template, one
corpus row corrected, one eight-row class split into eight.
`validation/vitriol.py` (7 panels, 18 s), `tests/test_vitriol.py` (18 tests).

### ⚠⚠⚠ 1. THE HALF THE BRIEF WOULD HAVE CALLED FREE WAS ALREADY BUILT, AND THE HALF IT CALLED A TEMPLATE WAS A DATA REFUSAL

`vitriol-distillation` is two rows: roast green vitriol, catch what comes off.
PLAYABLE §8 priced it at +2 and listed **two** blockers -- the `hydrolysis` class
and a refused `iron-ii-oxide`. Both readings were wrong in the same direction:

* **the roast has been in the engine since M6.** `properties/solid_state.py`
  declares `2 FeSO4 -> Fe2O3 + SO2 + SO3` and it runs: nothing below 800 K,
  complete by 1000 K, exactly 0.05 mol of each product from 0.10 of the mineral.
  The catalog's own condition column says *"retort, red heat"* and nobody had
  ever told the engine that.
* **`iron-ii-oxide` was never in the reaction.** The row named FeO; FeO does not
  survive red heat and `mineral_data` refuses it on its crystal Cps, which CRC
  does not tabulate. So a route was blocked on a datum for a species its own
  chemistry never makes. ⚠ *That is a shape worth looking for again: a refused
  species in a route's BLOCKER list may be a corpus error rather than a curation
  job.* Correcting the row alone moved species-ready 82 -> 83.

⚠⚠ **AND `data/catalog/README.md` HAD RECORDED THE LANDMINE THREE MILESTONES
EARLIER, WITH THE INSTRUCTION.** S3's split wrote *"the day `hydrolysis` is
credited, `vitriol-distillation` goes template-ready on a step whose stated
product does not exist in the run -- whoever builds it owes this row a second
look."* C1 is that session. **A recorded landmine with a named trigger is the
cheapest documentation this project writes**, and it worked exactly as intended.

### ⚠⚠⚠ 2. `hydrolysis` WAS AN OUTCOME LABEL SITTING NEXT TO SEVEN COUNTER-EXAMPLES

Eight rows, the catalog's second-biggest class after `proton-transfer`. The
argument for splitting is not that they are eight mechanisms -- they are -- it is
that the taxonomy **already carried** `amide-`, `ester-`, `epoxide-`,
`glycoside-`, `nitrile-`, `isocyanate-` and `disproportionation-hydrolysis`.
Everything it knew how to name had been named; `hydrolysis` was the bin for the
rest. That is M1's finding with seven of its own family standing beside it.

    contact-process 4      H2S2O7 + H2O -> 2 H2SO4          oleum-hydrolysis
    vitriol-distillation 2 SO3 + H2O -> H2SO4               sulfur-trioxide-hydration  <- built
    leblanc-process 4      CaS + H2O + CO2 -> CaCO3 + H2S   sulfide-carbonation
    frank-caro 3           CaCN2 + H2O -> NH3 + CaCO3       cyanamide-hydrolysis
    castner-kellner 2      Na(Hg) + H2O -> NaOH + H2 + Hg   amalgam-decomposition
    calcium-carbide 2      CaC2 + H2O -> C2H2 + Ca(OH)2     carbide-hydrolysis
    furfural-route 1       xylose + H2O -> xylose           pentosan-hydrolysis
    grignard-route 3       R-OMgBr + H2O -> R-OH            organometallic-protonolysis

Denominator +7, numerator +1. S7's shape: **a split that lowers the headline is a
split working.** ⚠ `oleum-hydrolysis` is the near-miss and is deliberately NOT
credited -- `[SX3]` against disulfuric acid's two `[SX4]` sulfurs, asserted.

⚠⚠ **AND ONE ROW'S CLASS WAS DECIDED RATHER THAN DERIVED, THEN MEASURED BOTH
WAYS.** `furfural-route` 1 is chemically a glycoside hydrolysis and the
convention would file it under the COVERED `glycoside-hydrolysis`; it is not
there, because the row is fragility 29b (`xylose + water -> xylose`) and no
template can ever match it. **Measured: it costs ZERO either way today**, because
the route needs three more classes. *A false credit is cheapest to refuse before
it can pay*, and the cell that is currently equal to its neighbour is exactly
G3's grid lesson pointing forward instead of back.

### ⚠⚠⚠ 3. THE CEILING IS EMERGENT AND NOBODY DECLARED IT: `ln K = 0` AT 664.3 K

`dH -97.53 kJ/mol`, `dS -146.8 J/(mol K)`, all three species EXPERIMENTAL
(NIST/CODATA). `dH/dS` is **664.3 K**, and in a dry gas the conversion falls
46.8% -> 1.6% between 600 K and 800 K -- checked against the closed-form root of
the same K, which it matches to three figures at every rung. **A receiver has to
be COOL, which is what a receiver is.** Same shape as the lead chamber's 600 K
NOx ceiling: an operating limit that came out of the formation data.

⚠ **AND THE CONDENSER BEATS THE CEILING, WHICH IS THE BETTER HALF OF IT.** With a
mole of liquid water present the conversion is **100.000% at every temperature up
to 600 K** -- not because K is large there (`ln K` is 1.89) but because sulfuric
acid boils at 610 K and leaves the gas as fast as it forms. *Le Chatelier, done
by a phase change the template knows nothing about.*

### ⚠⚠ 4. THE RATE LAW IS APPARENT, AND THE TRADE WAS MEASURED RATHER THAN ASSUMED

The real gas-phase reaction is **second order in water** (the water-dimer path);
what is declared here is bimolecular with `A = 1e10` pinned at the order of the
collision limit and `Ea = 23.6 kJ/mol` putting `k(298)` at the ORDER of the
reported effective constant. ⚠ **That figure is RECALLED and is used as an order
of magnitude, not a value** -- which is only defensible because the answer is
**100.000% at A = 1e6, 1e8, 1e10 and 1e11**.

⚠⚠ **`orders=(1.0, 2.0)` WAS REFUSED AND THE REFUSAL IS THE INTERESTING PART.**
It is the more correct rate law, and `ReactionTemplate.orders` may not be
combined with `reversible` -- a declared order has no detailed-balance partner.
So the choice was between the right ORDER and the right REVERSE. The order is
forgiven (five decades) and the reverse is the mechanic (the 664 K ceiling).
*Between two wrong-in-different-ways declarations, keep the one whose error is
MEASURED to be invisible.*

### ⚠⚠ 5. THE LIQUID CHANNEL WAS BUILT AND REFUSED ON CONSERVATION

`phase="any"` in a receiver full of water is not an obviously wrong idea. Built,
measured, refused:

    phase    conv 320-600 K   sulfur in - out at 320 K   700 K wall clock
    gas          100.000%        +8.4e-15 mol                434 s
    liquid       100.000%        +2.9e-06 mol (REPORTED)      13 s
    any          100.000%        +1.5e-06 mol (REPORTED)      72 s

It buys **nothing** and costs a projection residual six thousand times the
tolerance: the liquid pseudo-first-order constant is 1.4e6 1/s against a 600 s
run. ⚠ The residual is **not silent** -- `conservation_report` names it, which is
what made it priceable at all. ⚠ And there is no second SOURCED constant to put
on a liquid arrow; it would be the gas one copied.

### ⚠⚠⚠ 6. THE CHEAPEST REPRODUCTION OF ENGINE QUEUE ITEM 15 IN THE REPO

A ONE-POT flask -- green vitriol and water together -- measured at the default
tolerance:

     800 K, 2000 s     0.4 s      liquid layer 3.4e-17 mol
     900 K,  500 s    44.4 s      liquid layer 6.6e-17 mol
    1000 K,  200 s    > 9 MINUTES, did not finish

**Six species, one template.** That is the burner's `LAYER_REABSORB` thrashing
(item 15) on a network small enough to instrument, against the burner's 52 s on a
full chamber. ⚠ Not this template's bug: the same charge with no water is panel 1
and costs 0.3 s.

⚠ **AND THE PANEL WAS BUILT TO CONFIRM THE 664 K CEILING AND DID NOT.** In 66 bar
of steam the acid is still favoured 3.35:1 at 800 K -- `K * p_H2O = 3.33`, so
Le Chatelier is winning again -- and what actually kills the one pot is that the
SULFATE has moved 0.285% in 2000 s. **So the two-vessel apparatus is right for a
reason that is half chemistry and half numerics**, and it is written that way
rather than as the clean thermodynamic story.

### ⚠⚠⚠ 7. C1 DISSOLVED THE ONLY EVIDENCE FOR ONE OF G3's FOUR SCORING RULES

G3's rule 3 -- *a route shelves its target AND its byproducts* -- was justified by
a measured difference: 13 against 14 under the wrong needs rule. Re-measured:

                     shelf=target   +byproducts   +target unioned in
    needs=roles      G3 10 / C1 11  G3 13 / C1 15  G3 14 / C1 15
    needs=order      G3  8 / C1 10  G3 12 / C1 14  G3 12 / C1 14

**Every cell of the byproducts/both column is now equal.** The route the rule
bought was `saltpetre-nitric`, whose sulfuric acid came from the lead chamber's
fouling row; C1 gave the acid a route of its own, so losing the chamber's copy
costs nothing anywhere.

⚠⚠ **THE RULE IS KEPT, AND NOT OUT OF SENTIMENT.** It is a statement about
`route_roles` -- still true, still asserted -- and its measured cost is a property
of TODAY'S corpus. *A rule justified by a difference must not be reverted the day
the difference goes away; that is how a corrected instrument un-corrects itself.*
The grid is pinned at its new all-equal values in `tests/test_playable.py` with
the reason written above it.

### ⚠⚠ 8. THE WORK ORDER RE-PRICED ITSELF, AND THE CHEAPEST ROW IS NOW A MINERAL

    fed but unrunnable   21 -> 24      ceiling   37 -> 41
    iron-gall-ink        +2 -> +1      (C1 already delivered its second point)
    nitrogen-dioxide     +2 -> +1      (fragility 31 is worth half what G3 priced)
    need NO template      2 -> 4       hypochlorite-bleach, pyrite-roasting,
                                       **phosphoric-wet, superphosphate**

⚠⚠⚠ **`calcium-phosphate` IS WORTH +2 AND NEEDS NO CHEMISTRY AT ALL.** Phosphate
rock is already on the NATURAL list, both new routes are `acid-displacement-
precipitating` (covered), and both are blocked on that one refused price. **It is
the cheapest row in the whole work order and it is a data job.** ⚠ The lever
finding survived with all new numbers: `nickel` and `benzaldehyde` block three
routes each and are worth +1; `aluminium` blocks ONE and is worth +2. *A finding
that survives having its own example removed was about the shape, not the
example.*

### ⚠ 9. WHAT C1 DID NOT DO

* **The full suite was NOT run.** `src/` changed (one template plus the
  `reactions` export), so it is owed. The last clean figure is G6's
  **1045 passed / 0 failed in 23:03**, plus G3's 18 and C1's 18 -> expected
  **1081**. ⚠ This is the first session in the arc to ship an unrun suite, and it
  was a deliberate scheduling call, not an oversight.
* **`tolerance_audit.py` is asserted NOT owed.** No RHS edit and no data table
  moved -- the template is additive and every pre-existing network builds the
  same reactions from the same constants. Last measured state remains S13's.
* **`oleum-hydrolysis` is a gap on purpose** and `contact-process` is blocked
  twice over (`vanadium-pentoxide` and `disulfuric-acid` are both refused).
* **The 664 K ceiling is not a REFLUX head** (fragility 21). A receiver here is a
  cold flask, not an apparatus that returns condensate.

---

## C2 -- Phosphate rock ✔✔ **DONE 2026-08-27** *(the work order named the mineral, and the block was a pKa in a different table)*

**14 -> 16 playable, 37 -> 39 runnable, 83 -> 85 species-ready, 32 -> 34 BOTH,
419 -> 416 refused, 53/236 classes and 42 template-ready UNCHANGED.** Two
one-line data rows and one engine bound. `validation/phosphate_rock.py`
(8 panels, ~280 s -- the most expensive standing audit in the repo), `tests/test_phosphate.py` (16 tests).

### ⚠⚠⚠ 1. THE +2 WAS EXACTLY RIGHT AND THE REASON GIVEN FOR IT WAS ENTIRELY WRONG

`PLAYABLE.md` §8 called `calcium-phosphate` **"THE CHEAPEST ROW IN THE TABLE AND
IT IS A LOOKUP"** -- one mineral price, +2 playable routes, no chemistry at all.
The +2 landed, to the route. **The mineral price bought none of it.**

The catalog spells the rock as its ions, so `catalog_coverage` prices it
FRAGMENT BY FRAGMENT through `electrolyte_provider`, and the fragment it choked
on was `[O-]P([O-])([O-])=O`. `ion_data` has carried phosphate, hydrogen
phosphate and dihydrogen phosphate on the aqueous basis since M3;
`electrolyte._PAIRS` carried phosphoric acid's **1st and 2nd** dissociations and
stopped there. So the route was blocked on a missing **pKa**, in a table nobody
was looking at, while the work order named a **mineral**.

Measured as a 2x2, because guessing which row paid would have been guessing
(`tests/test_phosphate.py::test_the_pKa_row_is_what_moved_the_score`):

    compound              neither     pKa row   mineral row      both
    calcium-phosphate     refused      priced        priced    priced
    sodium-phosphate      refused      priced       refused    priced
    phosphate-ion         refused      priced       refused    priced

**All three move on the pKa row alone. The mineral row's contribution to every
published coverage number is ZERO.**

⚠⚠⚠ *A ROUTE'S BLOCKER CAN BE IN A DIFFERENT TABLE FROM THE ONE THE WORK ORDER
NAMES.* C1 found a route blocked on a price for a species **not in its
chemistry**; C2 found one blocked on a price **in the wrong table**. Both had
been recorded for three milestones as a mineral-curation job, and neither was
one.

### ⚠⚠⚠ 2. AND THE MINERAL ROW IS WHY IT RUNS, WHICH IS A DIFFERENT QUESTION

Drop the `MineralRecord` and keep the pKa: `phosphoric-wet` still reads
species-ready, still counts in the BOTH column, still scores as playable -- and
the rock is **INERT**. Its ions sit in the solid block for ever, because no Ksp
connects them to the solution. Measured, 600 s at rtol 1e-8, k_diss = 10:

    mineral_data          converted        H3PO4       H2PO4-
    with the lattice        8.0317%   0.00132188   0.00028447
    WITHOUT it              0.0000%   0.00000000   0.00000000

⚠⚠ **THE SCORE AND THE CHEMISTRY CAME OUT OF DIFFERENT TABLES AND NEITHER ONE
IMPLIES THE OTHER.** That is G4's rule (*only RUNNING it said so*) arriving from
a new side: G4's three false credits were routes that scored and did not run;
this is a route that scores on one table and needs a second one to move. **Two
data rows, disjoint payoffs, and the brief could see one of them.**

### ⚠⚠ 3. THE MEMBERSHIP GAP -- TWO CURATED TABLES OVER THE SAME IONS

`solubility_product`'s docstring warns at length that `ion_data` and
`electrolyte` price the same ions on **different zeros** -- chloride is -131.20
in one and -111.73 in the other, 3.4 decades of Ksp. **Nothing anywhere compares
which ions they HAVE.** After C2, of the 30 lattices that can be given a Ksp,
**25 can be put in a flask and 5 cannot** -- and all five are blocked on the
same ion:

    sphalerite   galena   covellite   chalcocite   cinnabar       all on [S-2]

Same shape as phosphate: `_PAIRS` carries `H2S -> [SH-]` at pKa 7.00 and stops.
⚠ **A POLYPROTIC ACID GETS ENTERED AS FAR AS SOMEBODY NEEDED, AND NOTHING CHECKS
THAT THE CHAIN IS FINISHED.** `validation/phosphate_rock.py` panel 3 measures
the gap so it cannot happen silently a third time.

⚠⚠ **AND THE SULFIDE STEP IS A REFUSAL, NOT THE NEXT ONE-LINE FIX.** HS- -> S2-
is quoted anywhere between about 12.9 and 19 depending on the compilation --
**six decades of disagreement about one number**, which is `element_data`'s rule
exactly: report it, do not invent it. Phosphoric acid's third pKa was takeable
*because* the two rows above it fix the series (2.15 / 7.20 / **12.35**, not
CRC's 2.16 / 7.21 / 12.32 -- the iodide row's decision, made a second time).

### ⚠⚠ 4. THE PRICE IS REAL, AND THREE OF THE FOUR ROWS BESIDE IT ARE NOT

CRC carries **both halves in one row**: Hfs -4120.8 kJ/mol, S0s 236.0 J/(mol K),
Cps 227.8, plus a crystal Vm. Probed in the same run, the other three members of
PLAYABLE §8's *"needs no template at all"* bucket:

    species                  Hfs from        S0s from
    calcium-phosphate        CRC             CRC          <- the only one
    calcium-silicate         nothing         nothing         (3 CAS numbers)
    pyrite                   WEBBOOK         nothing
    sodium-hypochlorite      nothing         nothing

⚠ **A DATA JOB IS ONLY CHEAP WHEN THE DATA IS THERE**, and the bucket the work
order called a data job is three-quarters refusals. Both engine-queue entries
that predicted this (item 11 on `calcium-silicate`, item 14 on `pyrite`) are
re-confirmed rather than re-derived.

### ⚠⚠⚠ 5. THE ENGINE BOUND: exp() BEING FINITE IS NOT k*V*exp() BEING FINITE

The first digestion threw two `RuntimeWarning`s out of `PrecipitationArrays`.
`LN_SATURATION_CAP` exists, in its own words, *"so that a transient absurd state
during a Jacobian perturbation cannot produce an inf"* -- **and it did not.** It
bounds a CONCENTRATION; the next line multiplies by the liquid volume, which a
Newton iterate does not bound. Instrumented, the failing state is

    T = 1.0 K     nL1 = 5.0e10 mol     V_L1 = 9.2e8 L     roots -> exp(700)

so `1e-2 * 9.2e8 * exp(700)` overflows to `inf`, and to `nan` one line later in
the `_avail` product. Fixed by giving the cap the multiply's headroom;
**bit-identical wherever `k_diss * V_L1 <= 1`, which is every vessel in this
repo**, and asserted as such.

⚠⚠⚠ **AND IT ANSWERS ENGINE QUEUE ITEM 6's OPEN QUESTION, FROM A DIFFERENT
TERM.** That row records a PSRK overflow below 4.28 K and says *"WHAT IS NOT
KNOWN IS **WHERE** -- nothing has found which call passes a T that low."*
**Nothing does: `T_MIN = 1.0` manufactures it.** A Newton iterate proposes a
temperature below 1 K, the RHS's `min(max(float(y[-1]), T_MIN), T_MAX)` hands
every term exactly 1.0, and every `1/T` in the right-hand side is evaluated
297 K outside its domain at once. Item 6's probe does not need writing; its
answer needed finding somewhere cheaper.

⚠ **The overflow was measured HARMLESS in both the answer and the clock** --
identical digits, 79.1 s against 81.2 s. The word that changes is "unbounded",
not any number.

### ⚠⚠⚠ 5b. AND THAT FIX BROKE THREE EXAMPLES, THE SUITE STAYED GREEN, AND ONLY `tolerance_audit.py` SAW IT

The headroom went in as `max(math.log(scale), 0.0)`. **That is the same function
as `math.log(max(scale, 1.0))` only where the log is DEFINED**, and `scale` is
`k_diss * V_L1` — which is exactly **zero** whenever a vessel declares
`k_diss = 0.0`. Three do: `workshop` part 3, `named_routes`, and `recipes`'
crystallise stage, so `multistep_prep` as well. All three began raising
`ValueError: math domain error` at rtol 1e-8.

    example            PRE-C2                      with the bad headroom
    multistep_prep     6 lines moved, worst inf    RAISES
    workshop           2 lines moved, 1.98e-04     RAISES
    named_routes       RAISES (diagnosed)          RAISES, DIFFERENT error

⚠⚠⚠ **THE FULL TEST SUITE WOULD HAVE STAYED GREEN.** Nothing in `tests/` charges
a `k_diss = 0` vessel through the precipitation branch; the audit caught it by
comparing against its own recorded baseline, and a `git stash` of C2 confirmed
the three were healthy before. **This is the clearest case the project has for
the rule that an RHS edit owes the tolerance audit ten minutes**, and it is worth
more than the finding the audit was run to check.
⚠ Fixed, and the assertion is now a test: `test_a_vessel_may_declare_k_diss_ZERO`.
*A vessel with `k_diss = 0` is a deliberate configuration — "no dissolution in
this flask" — not an edge case.*

### ⚠⚠⚠ 6. THE DEFAULT TOLERANCE CANNOT BE TRUSTED ON THIS FLASK

600 s, 0.03 mol H2SO4, the same eleven-species flask:

    k_diss     loose conv   loose s     tight conv   tight s    ratio
      1          46.059%      36.3         0.823%       2.4      56.0
     10           8.032%      58.5         8.032%      16.6       1.00

⚠⚠ **The default reports the wrong answer at one knob setting and the right one
at another, and nothing in the answer says which.** ⚠ The tight run is also the
**fast** one -- 15x -- which is the tell: the loose solver is thrashing, not
saving work. Every number in C2 is quoted at rtol 1e-8 for that reason.

⚠⚠ **AND THE FIRST SWEEP OF THIS SESSION WAS RUN AT THE DEFAULT AND WAS ENTIRELY
WRONG**, non-monotonic in both k_diss and time -- 46% at 600 s against 4.9% at
3600 s, and 8% at k_diss 10 against 46% at k_diss 1. *A non-monotonic sweep is
not a finding about chemistry; it is a solver saying it has not converged, and
reading it as chemistry is how a wrong number gets written down.*

### ⚠⚠⚠ 7. THE LIMIT THIS NAMES: AN ACID CANNOT ATTACK A CRYSTAL

`PrecipitationArrays` drives dissolution on
`k_diss * V * (Q^(1/N) - Ksp^(1/N))`, so with the solution swept clean the
fastest this rock can EVER dissolve is `k_diss * V * Ksp^(1/5)` = 2.9e-9 mol/s
at the vessel default -- **40 days for 0.01 mol.** Conversion is exactly linear
in the knob (0.0157 / 0.0825 / 0.823 / 8.03 / 70.7 % for k_diss 1e-2 up to 1e2)
and **the acid does not enter it at all**:

    H2SO4/mol     converted        pH
      0.03          8.03175%     1.487
      0.30          8.20475%     0.517
      1.00          8.36332%    -0.001

**Thirty-three times the acid, a decade and a half of pH, and 4 % of the
conversion.** A real wet-process digestion is a SURFACE reaction going with
[H+]; this engine has that shape for a **gas** arriving at a crystal
(`SurfaceArrays`, S1) and **not for a liquid**. ⚠ So the rock digests on a
vessel knob rather than on its chemistry, and `PLAYABLE.md` §5's rule -- *a
yield is not a corpus property* -- is what every conversion here has to be read
under.

### ⚠⚠ 8. THE WORK ORDER SHRANK THIS TIME, WHICH IS C1's LESSON IN REVERSE

C1 measured that granting a row makes the fixed-point work order LONGER (21 ->
24). C2 granted two and it went **24 -> 22**: nothing new became fed, because
phosphoric acid feeds no route that was not fed already. ⚠ **The ceiling did not
move: 41, exactly as before.** ⚠⚠ But the shelf still re-priced a lever --
`ethylene` was +1 in G3's table and is **+2** now, because `ethanol-hydration`
was blocked on ethylene *and phosphoric acid* and is now blocked on ethylene
alone. *Re-run `build_playable.py` after every content item; the worths move in
both directions, and not where you expect.*

### ⚠⚠⚠ 9. THE FULL SUITE CAME BACK 7 FAILED, AND ALL SEVEN WERE THE INSTRUMENT WORKING

C2 re-ran every generated artefact -- `build_playable.py`, `catalog_coverage.py`,
`corpus_balance.py`, `granularity.py`, `build_route_index.py` -- read every
headline they printed, and wrote those headlines into MILESTONES, HANDOFF and
NEXT_PROMPT by hand. **It did not run `tests/test_playable.py`, which PINS the
same headlines.** The suite found:

    test_playable   14 -> 16 playable, 37 -> 39 runnable
    test_playable   fed-but-unrunnable 24 -> 22
    test_playable   needs=roles closure 15 -> 17
    test_playable   the rule-3 grid, all four cells
    test_playable   target-only shelving 10 -> 12
    test_playable   the species-only bucket, 4 rows -> 2
    test_protonation  the ion table 28 -> 29

Every one is a number C2 had already measured. **The generated report and the
test that pins it are two different consumers of the same number, and running
one is not running the other.** ⚠ G3 built these assertions for exactly this
(*assert a generated artefact or it will rot*) and C1's handoff even lists
`test_playable` among what it ran; C2 read that list and skipped it anyway.

⚠⚠ **THE GRID WAS RE-MEASURED WHOLE RATHER THAN PATCHED**, because the
claim is about the DIFFERENCE between cells and not about any one of them:

                       shelf=target        +byproducts    +target unioned in
    needs=roles  G3 10 / C1 11 / C2 13   13 / 15 / 17    14 / 15 / 17
    needs=order  G3  8 / C1 10 / C2 12   12 / 14 / 16    12 / 14 / 16

Rule 3's measured cost is **still zero in both rows**, so C1's *"the rule is kept
and the zero is asserted"* survives a second corpus change.

⚠⚠ **AND ONE ASSERTION WAS A PREDICTION C2 CASHED.**
`test_four_of_the_work_order_need_no_template_at_all` ended by granting
`phosphoric-wet` and `superphosphate` and asserting **+2**. C2 delivered that, so
the line now measures **zero**. Rewritten to assert where the +2 landed instead
of leaving a claim that had quietly stopped meaning anything. *A test that
predicts a gain has to be rewritten by the session that delivers it.*

### ⚠⚠⚠ 10. C2 WROTE A TIMING FINDING DOWN AND THEN REFUTED IT WITH A SECOND RUN

The suite ran three times. The first (C1's owed one) had a `k_diss` sweep running
alongside it and came back **+25% over G6**, every big row 14-23% up. That was
recorded, in four documents, as *"a single-threaded pytest run on a 16-core box
is NOT insulated from one concurrent single-threaded job -- measured at +25% wall
clock. Run the suite alone."*

**The clean run refutes it.**

                        G6      C2 contaminated   C2 alone   the two C2 runs
    total            23:03          28:47          29:55        +3.9%
    the ONE RIG test 176.9 s        201.40         199.26       -1.1%
    catalysis         75.1 s         89.17          91.50       +2.6%
    burner @1e-8      52.8 s         64.90          64.81       -0.1%

The clean run is **SLOWER** than the contaminated one, and the two agree inside
the recorded ~8%/~1% noise floor on every row. **One concurrent single-threaded
job cost nothing measurable.**

⚠⚠ *A PLAUSIBLE CAUSE MEASURED ONCE IS A GUESS.* The concurrency story was
mechanistically sensible, arrived with a number attached, and was wrong. The
second run is what turned it into a finding, and it made it the opposite finding.
The rule that came out of it -- *run the suite alone* -- is still tidy practice;
it just is not supported by the measurement that was cited for it, and that
citation is removed rather than left standing.

⚠⚠⚠ **WHAT IS REAL IS A +30% NOTHING EXPLAINS, AND IT IS THE S12->S13
SHAPE A SECOND TIME.** G6's 1045 tests took 1383 s; 1097 take 1795 s. New test
files since G6 account for roughly **179 s** (`test_phosphate` ~104,
`test_playable` ~57, `test_vitriol` ~18), leaving about **230 s spread across
tests that did not change** -- far outside the floor. The project already records
S12->S13 as *"20x outside the floor and a real unexplained regression"*; **this is
a second one and neither has been bisected.** A `git stash`-and-rerun of
`--durations=25` across the suspect commits is still the cheap next step, and it
is worth more now that there are two data points rather than one.

### What C2 did NOT do

* **`superphosphate` is scored, not demonstrated.** Its catalog row is a "den,
  ambient" paste with NO water, and an engine whose only ionic chemistry is
  aqueous cannot express a solventless acidulation. It scores through the same
  two data rows, and its chemistry is the digestion above stopped earlier.
* **`white-phosphorus` did not move**, and it names calcium-phosphate too. It is
  blocked three more ways: no `carbothermic-phosphate-reduction` template, no
  formation pair for P4 in any source here, and `calcium-silicate` refused.
  **Pricing one species of four is worth nothing on a route.**
* **No new reaction class and no new template.** 53/236 and 42 template-ready
  are both unchanged; every step in both routes was already covered.
* **`tolerance_audit.py` IS OWED AND WAS RUN, AND IT PAID FOR ITSELF** -- see
  §5b: it caught a crash in three examples that the whole green test suite
  missed. ⚠ The pKa row is separately MEASURED bit-identical for all 28
  pre-existing ions, so the data half owed nothing; the RHS edit is what owed
  it.

---

## C3 -- Vanillin from clove oil ✔✔ **DONE 2026-08-27** *(and the class had been refused on the evidence of one of its two rows)*

**16 -> 18 playable, 39 -> 41 runnable, 53/236 -> 55/236 classes, 42 -> 44
template-ready, 34 -> 36 BOTH, species-ready UNCHANGED at 85.** Two templates,
two classes, no data rows and no engine code. `validation/vanillin.py`
(9 panels, ~2 min), `tests/test_vanillin.py` (31 tests).

### ⚠⚠⚠ 1. THE CLASS WAS REFUSED IN S11, AND THE REFUSAL WAS ABOUT A ROW

S11 went to build `oxidative-cleavage`, read `vanillin-lignin` step 1, found that
a C10 monolignol cannot make one C8 vanillin and a water, and **refused the
class** — on the ground that naming the missing C2 fragment would be inventing
chemistry inside the corpus. That refusal is recorded in §S11 §12 and printed by
`validation/corpus_balance.py`'s last panel, and it was **right about the row.**

The class has two rows. Measured, before anything was written:

    isoeugenol + O2 -> vanillin + acetaldehyde      C10H12O4 both sides, EXACT
    coniferyl  + O2 -> vanillin + glycolaldehyde    C10H12O5 both sides, EXACT
    coniferyl  + O2 -> vanillin + water             C10H12O5 -> C8H10O4    NO

**`vanillin-eugenol` step 2 balances 1:1 and names its C2 fragment.** So the
template is written off that row — and applied to coniferyl alcohol it produces
the fragment the lignin row omits, which is **`glycolaldehyde`, a compound
`data/catalog/compounds/07-carbonyls.psv` has carried all along.** *The mechanism
supplies the fragment and the corpus supplies its name; nothing is invented.*

⚠⚠⚠ **THREE SESSIONS RUNNING HAVE FOUND ONE OF THIS SHAPE.** C1: a route blocked
on a price for a species **not in its chemistry**. C2: a route blocked on a price
**in a different table**. C3: a **class refused on the evidence of one of its
rows.** *Read every row of a class before refusing the class* — and the cost of
not doing so was two playable routes for two SMARTS strings and no new data.

⚠ **AND THE CORPUS ROW WAS LEFT WRONG ON PURPOSE**, which is the half of S11's
reason that stands. On coniferyl alcohol the mechanism is unambiguous. The
catalog row is about alkaline **lignin liquor**, where the C2 fragment is a
mixture depending on which monolignol reacted, so writing one name into it would
over-commit the corpus in exactly the way S11 declined to.

### ⚠⚠ 2. AND THE ROW S11 REFUSED IS NOW INSIDE THE HEADLINE

`vanillin-lignin` was outside the BOTH column when S11 wrote its panel. C3
covered its only class, so it is inside it now: **`corpus_balance`'s own standing
example of a row that PASSES the balance test and is not the reaction it is
written as is counted in the number the project quotes.** The one row that audit
FLAGS inside BOTH is `perkin-route`; the row that is actually wrong is the one it
cannot see. Panel updated rather than remembered.

### ⚠⚠⚠ 3. THE SESSION'S SHARPEST FINDING IS NUMERICAL: AN EQUILIBRIUM IS EXACT ON THE LIQUID AND NOT ON THE INVENTORY

C3's first flask read an isoeugenol:eugenol ratio of **15362** where `kf/kb` is
**2677.83**, and that 5.7x was nearly written into a template comment as
chemistry. It is the **HEADSPACE**:

    liquor / L    t / s    TOTAL ratio   LIQUID ratio   eug in gas   iso in gas
         0.082   3.6e+05      10993.93        2677.83       60.14%       22.27%
         0.730   3.6e+05       2866.67        2677.83       10.25%        2.12%

**The liquid ratio is `kf/kb` to the last digit**; detailed balance is exact and
was never in question. The allyl isomer is ~5x the more volatile, so a share of
the eugenol sits where no rate law can reach it — and the smaller the liquor, the
bigger the lie. ⚠⚠ **`state().total()` is the right number for a YIELD and the
wrong one for an EQUILIBRIUM.** A rate law is written on one phase; read the
equilibrium on that phase or not at all. Same shape as *"energy_terms lies unless
given the run's own boundary state"*.

### ⚠⚠ 4. §8 RANKS ROUTES AND A SESSION BUILDS TEMPLATES — SO `PLAYABLE.md` GREW A §8b

The work order's `worth` column grants a **route**. A C-series session grants a
**class**. Measured, they disagree at the top of the table:

| §8 row | its worth | grant its CLASS instead |
|---|---:|---|
| `hall-heroult` | **+3** — the top row | **still not runnable**: cryolite is refused a price too. The class lands +1, on `downs-cell` |
| `blast-furnace` | **+2** | **+0 runnable, +0 playable**: three refused species |
| `abe-fermentation` | **+2** | +3 runnable, +2 playable — the only one of the three a template can buy |

**A row's worth assumes every OTHER blocker away, and a template only removes one
of them.** 9 of the 20 rows cannot be bought by templates at all, and only 7 of
the 23 missing classes are worth a single point. `tools/build_playable.py` now
generates both tables.

⚠⚠⚠ **AND THE PAIR C3 BUILT IS SUPER-ADDITIVE, WHICH THE SESSION'S OWN PROBE
HID.** `alkene-isomerisation` alone is worth **+0** and `oxidative-cleavage`
alone **+1**; together they are **+2**, because `vanillin-eugenol` needs both
while `vanillin-lignin` needs only the second. C3's scouting probe printed its
pair table `[:12]` and the row fell off the bottom, so the session went in
expecting +1 and delivered +2. *A probe that truncates its own output can hide
the row it was written to find.*

### ⚠⚠⚠ 5. AND §8b's DETECTOR FOUND A LIVE FALSE CREDIT — THEN HAD ONE OF ITS OWN

`route_reachable` blocks a route whose **reactant** has no molecular graph, and
does **not** look at one the route MAKES. So:

* **`oxidative-complexation` is scored +1 on `iron-gall-ink`**, whose product
  `iron-gallate-marker` the corpus deliberately does not spell. **Build it and
  the route goes template-ready and `build_network` has no graph to make its
  product from.** The trigger is written into `data/catalog/README.md` in C1's
  and C2's landmine form.
* the same shape sits at **+0** on `castner-kellner` / `sodium-amalgam-marker`.
* ⚠ **and the detector's first version blamed `pyrolysis`/`coal-gas` too**,
  where the marker is on the LEFT and the route was already dead. **A
  false-credit detector needs the same does-it-actually-run check as everything
  it audits.**

### ⚠⚠ 6. THE FLASK: WHAT RUNS, AND UNDER WHAT

An **autoclave**, and that is not decoration: 0.73 L of alkaline liquor in a 2 L
vessel at 470 K sits under ~30 bar of its own steam, which is what an alkaline
oxidation digester is.

    T / K   t / h   P / bar   vanillin   yield
      400     4.0     15.67   0.000432    0.43%
      440     4.0     21.73   0.026878   26.88%
      470     4.0     29.29   0.093150   93.15%
      490     4.0     38.19   0.099985   99.98%

⚠ **The acetaldehyde is 1:1 with the vanillin at every row** — §1's balance
showing up as an invariant of the run rather than as a claim about the corpus.
⚠ **The isomerisation is rate-determining** (94.65% in 4 h alone, against the
cleavage's 97% in 1 h), so the intermediate never accumulates, which is the real
preparation's shape. ⚠⚠ **There is no over-oxidation channel**, so every yield
above is an UPPER BOUND against a real 60-80%; what is calibrated is the
isomerisation.

⚠⚠ **AND THE BASE IS THE GATE, IN A PLACE NEITHER TEMPLATE NAMES.** Zero
hydroxide gives **exactly zero** vanillin. `oxidative_cleavage` declares no
catalyst and would cleave any isoeugenol in the flask; there is none, because the
step that MAKES isoeugenol is the base-catalysed one. *A two-template route is
gated by whichever step comes first, and neither template says so on its own.*

⚠ **Both routes land in tier 2 and NOT on sulfuric acid.** Eugenol (clove oil)
and coniferyl alcohol (wood lignin) are both on the natural list; what has to be
made is the **caustic soda**. So rule 3 — *a catalyst is a feedstock* — is what
puts vanillin one hop up, and C3 is the first session to move the tree away from
being mostly tier-1: **9 of 18 is exactly half**, where G3's assertion was a
strict majority. The bush is still 3 tiers deep and tier 3 is still one route.

### ⚠⚠ 7. TWO CLAIMS C3 WROTE AND THEN MEASURED FALSE

* **The bundle does NOT need `dissociation_templates()` — it must not be given
  them.** That line was copied from `wacker_chemistry` and is the opposite of the
  truth: eugenol IS a phenol, so `phenol_dissociation` fires on it and
  `build_network` refuses the whole network for want of an **eugenolate pKa**.
  G5's rule reaching a new substrate — *an open-ended rewrite over a curated
  table will find the edge of the table*, met on an amine there and a phenol
  here. **The refusal is KEPT**: this route needs no phenolate, and G5 measured
  what curating pKa values for an unused template buys.
* **Ea 110 kJ/mol was 8x too fast, and the arithmetic that chose it assumed a
  ONE-LITRE liquid.** The flask's liquor is 0.73 L, so its hydroxide is
  correspondingly more concentrated. Corrected to **115**, calibrated against the
  flask. *An apparent barrier calibrated against a rate has to be calibrated
  against the rate the FLASK computes, not the one the envelope does.*

### ⚠ 8. AND THE PRE-BUILD ARITHMETIC WAS DONE ON THE WRONG STANDARD STATE

|  | ideal gas | | pure liquid | |
|---|---:|---:|---:|---:|
| | dH | ln K 470 | dH | ln K 470 |
| eugenol -> isoeugenol | −21.80 | +8.04 | **−56.56** | **+7.89** |
| isoeugenol + O2 -> vanillin + MeCHO | −325.58 | +85.71 | **−320.92** | **+94.37** |

Both templates are `phase="liquid"`, so the second pair is what the flask uses.
⚠⚠ **The two ln K values for the isomerisation agree to 2% while their dH values
differ by 35 kJ/mol and the sign of dS flips** (+20.45 against −54.72 J/K).
**That agreement is a coincidence, not a licence** — two errors cancelling at one
temperature. S12's rule; the template comment was corrected against the audit
rather than the other way round.

### ⚠ 9. WHAT C3 DID NOT DO, SAID OUT LOUD

* **The lignin row runs and its ln K may not be read.** Coniferyl alcohol has no
  vapour-pressure curve, so `build_network` prints M5's MIXES STANDARD STATES
  notice on it. The reaction is irreversible so no rate depends on the number.
  ⚠ **Which is a second, independent reason the eugenol row was the right one to
  build from: all four of its species carry a curve. S11 picked the row that is
  worse in both ways.**
* **The product's double-bond geometry is not declared.** cis, trans and
  geometry-free isoeugenol price at Hf −216.705 and Gf −49.315, identical to
  three decimals — S7's `oleic -> elaidic` finding re-measured. So the template's
  product is a **different species string** from the corpus's trans isoeugenol
  and thermochemically the same molecule. ⚠ **It makes no spurious cycle, because
  discovery is FORWARD-ONLY** (M5): charge the corpus's trans isomer and the
  isomerisation is not in the network at all. *A rule that has cost this project
  a template twice does useful work here.*
* **No over-oxidation, no vanillic acid, no polymerisation.** The three things
  that cap a real vanillin yield. `peroxide_over_oxidation` exists and is
  deliberately NOT in this bundle, because a bundle carrying it would also
  oxidise the acetaldehyde.
* **`tolerance_audit.py` is NOT owed**: no RHS edit, no data-table edit, and
  nothing outside the new bundle can reach either template.

### ⚠⚠⚠ 10. THE SUITE IS GREEN, AND ITS CLOCK CLOSED ONE OF C2's OPEN ITEMS

**1128 passed / 0 failed in 24:54, run alone.** C3 ran **31 more tests than C2 in
300 fewer seconds**:

                        G6        C2        C3     C2->C3    G6->C3
    total / s         1383.0    1795.0    1494.6    -16.7%     +8.1%
    tests               1045      1097      1128     +2.8%     +7.9%
    the ONE RIG test   176.9     199.3     163.2    -18.1%     -7.7%
    catalysis           75.1      91.5      73.5    -19.7%     -2.2%
    burner @1e-8        52.8      64.8      51.0    -21.3%     -3.4%
    SECONDS PER TEST  1.3234    1.6363    1.3250   -19.0%    +0.12%

**Per test, C3 is within 0.12% of G6 and C2 sat 24% above both.** Nothing changed
that either number could depend on, so **C2's *"+30% that nothing explains"* was
the machine and not the code** — C2's own *a plausible cause measured once is a
guess*, applied to the timing note it wrote about itself.

⚠⚠ **AND THAT MAKES THE RECORDED NOISE FLOOR WRONG.** *"~8% on the biggest
single row and ~1% on the mid rows"* (G5 against G6) came from two runs that
happened to be quiet; the observed between-run spread on this box is **~20% on
every big row**. ⚠ **The S12->S13 eight minutes has to be re-priced against
that** — it was called *20x outside the floor and a real unexplained regression*
on the strength of the floor that is now wrong, and against ~20% an eight-minute
gap on a ~23-minute suite is not clearly outside it. Neither gap has been
bisected and neither should be believed without a controlled repeat.
**A wall clock compared across SESSIONS is not an instrument; the same box in the
same session is.** What survives is the `--durations` LIST as a per-row diff, not
the total as a regression alarm.

## C4 -- The ABE fermentation ✔✔ **DONE 2026-08-28** *(the class M5 refused was an outcome label, and its lump was a formatting artefact)*

**18 -> 20 playable, 41 -> 42 runnable, 55/236 -> 57/240 classes, 44 -> 45
template-ready, 36 -> 37 BOTH, species-ready UNCHANGED at 85.** Four templates,
one bundle, a five-way TAXONOMY SPLIT, no data rows and no engine code.
`validation/fermentation.py` (8 panels, ~30 s), `tests/test_fermentation.py`
(31 tests). **§8b's only +2 row, taken — and there is no +2 row left.**

### ⚠⚠⚠ 1. THE CLASS WAS REFUSED IN M5, AND THE REFUSAL WAS ABOUT THE LABEL

M5 refused `fermentation` as *"a metabolic **network**, not a transformation"*.
`PLAYABLE.md` §8b priced it as **the biggest single class left, +2 playable**, and
NEXT_PROMPT recorded C3's own measurement of the row it is sold on:

    abe-fermentation 1, as written  C6H12O6 -> C10H24O5              NO
    ... balances only at            5 C6H12O6 -> 2 acetone + 2 butanol
                                    + 2 ethanol + 12 CO2 + 8 H2

with the verdict *"five glucoses in and six carbon skeletons out is not a graph
rewrite"*. **Every word of that is true and none of it is about the mechanism.**

⚠⚠⚠ **THE LUMP WAS A FORMATTING ARTEFACT.** Clostridial solventogenesis is three
independent branches off one pyruvate node, and each balances **exactly on ONE
glucose**:

    glucose        -> 2 ethanol + 2 CO2            C6H12O6 both sides, EXACT
    glucose        -> 1-butanol + 2 CO2 + H2O      C6H12O6 both sides, EXACT
    glucose + H2O  -> acetone + 3 CO2 + 4 H2       C6H14O7 both sides, EXACT

**Nothing consumes five sugars. It was three reactions written on one line, and
the 5:2:2:2:12:8 vector was the arithmetic of that line rather than of any
chemistry.** ⚠ So `corpus_balance`'s weak test passed the row for the same reason
it passes `vanillin-lignin`, and the two rows need **opposite** answers: the
lignin row is short a PRODUCT and must be left wrong; this one was short a LINE
BREAK and could just be split. *A coefficient vector cannot tell those apart.*

⚠⚠⚠ **FOUR SESSIONS RUNNING HAVE FOUND ONE OF THIS SHAPE.** C1: a route blocked
on a price for a species **not in its chemistry**. C2: a route blocked on a price
**in a different table**. C3: a **class refused on the evidence of one of its
rows**. C4: a **class refused on the evidence of its row's FORMATTING**. *Read
the mechanism, not the line.*

### ⚠⚠⚠ 2. AND THE CLASS HAD TO BE SPLIT FIVE WAYS, BECAUSE THE +2 WAS OTHERWISE A FALSE CREDIT

Five catalog rows carried `fermentation` and they are five mechanisms:

| row | mechanism | C4 |
|---|---|---|
| `abe-fermentation` 1 | anaerobic clostridial **solventogenesis** | **BUILT** |
| `lactic-acid-pla` 1 | anaerobic **homolactic** glycolysis, no gas at all | **BUILT** |
| `citric-acid-fermentation` 1 | **aerobic overflow** of a blocked TCA cycle | gap |
| `msg-route` 1 | aerobic overflow plus **reductive amination** | gap |
| `penicillin-route` 1 | **secondary-metabolite** biosynthesis on a fed precursor | gap |

**A template written off `abe-fermentation` cannot make citric acid, glutamic
acid or penicillin G out of a sugar.** Crediting the old five-row class off it
would have template-readied four routes `build_network` cannot run — G4's *only
RUNNING it said so*, **arriving before the run for once, because the rows were
read first.** So `route_steps.psv` names five classes, on S7's `combustion`
precedent and M5's own `catalytic-hydrogenation` one.

⚠⚠ **THE HEADLINE COST IS +4 ON THE DENOMINATOR** — 236 classes to 240 — against
+2 covered. **S7's rule again: a split that lowers the headline is a split
working.** ⚠ And the split is what makes the three gaps *costable*: each now has
a yes/no answer instead of a fifth of one.

### ⚠⚠⚠ 3. M10's CHEAP VERSION IS REFUTED, AND IT FAILS WORSE THAN ITS OWN DOCSTRINGS SAY

§M10 scopes the Michaelis-Menten plateau as *"a declared order of ZERO in the
substrate IS the saturated limit ... needs no kernel change"*, and a fermentation
substrate is the one slot it would sit in. **It needs one.** There is no
availability gate outside the solid block (`_avail`), so the rate law cannot know
the substrate is gone — and two docstrings in this project say the reactant *"is
driven negative"*. Run to 1500 h at order zero (`validation/fermentation.py`
panel 5):

    orders               t/h      glucose        EtOH    EtOH/max
    mass action (ours)  1500     0.015087     0.96983       0.970
    (0.0,) -- M10's      200     0.382801     0.23440       0.234
    (0.0,) -- M10's     1100     0.000000     1.27577       1.276  IMPOSSIBLE
    (0.0,) -- M10's     1500     0.000000     1.79388       1.794  IMPOSSIBLE
    (0.0,) -- M10's     3000     REFUSED -- RuntimeError, species reached -1.74 mol

⚠⚠⚠ **THE SUBSTRATE IS CLAMPED AT ZERO IN THE REPORTED STATE WHILE THE PRODUCTS
GROW PAST THE STOICHIOMETRIC CEILING, AND THE RUN REPORTS SUCCESS FOR ~1900
SIMULATED HOURS.** 1.79 mol of ethanol out of 0.5 mol of glucose is 3.6x what
that sugar can give. **`state()` does not go negative — it hides the negative,
and the products are where the violation shows.**

⚠⚠ **THE GUARD IS LOAD-BEARING AND ITS LABEL IS NOT.** `conservation_report()`
sees every mole:

    non-negative projection created 1 species' worth of round-off it could not
    settle against a positive holding: <glucose> 3.97e-01 mol

**Four tenths of a mole, called "round-off".** The wording is calibrated for the
case the method was written for, and it is the only witness a caller has. *Same
shape as "energy_terms lies unless given the run's own boundary state" and as
"state().total() is the right number for a yield and the wrong one for an
equilibrium": the check exists, is correct, and its own prose mis-sizes what it
found.* ⚠ **M10 stays OPEN and its cheap door is measured shut**: a saturating
form needs the denominator, or the kernel needs the gate the solid block has.

### ⚠⚠ 4. WHAT IS FITTED, WHAT IS NOT, AND THE ONE NUMBER THAT CHECKS THE MODEL

Reference flask: 0.5 mol glucose in 10 mol water — ~0.19 L of a 2.6 M mash — in a
sealed 2 L vessel at **310 K**, which is blood heat.

     t/h   glucose     EtOH     BuOH  acetone      CO2       H2   conv%   A:B:E
    12.0   0.34598  0.02335  0.08755  0.05480   0.3628   0.2192  30.80  2.35:3.75:1
    48.0   0.11223  0.05830  0.21863  0.13999   0.9155   0.5600  77.55  2.40:3.75:1
    96.0   0.02459  0.07125  0.26719  0.17260   1.1234   0.6904  95.08  2.42:3.75:1

**FITTED:** the batch time (77.6% in 48 h is an ABE batch) and the **solvent
slate** — the classical 3:6:1 by MASS is 2.38:3.73:1 by mole, and three
pre-exponentials were set to it.

⚠⚠ **AND THAT FIT IS DECLARED RATHER THAN HIDDEN BEHIND AN ALPHA, WHICH IS THE
SESSION'S DESIGN DECISION.** Evans-Polanyi over three branches that differ by
**220 kJ/mol** in dH would predict a slate of nothing but butanol. A real slate
is set by the organism's regulation and its pH. **Selectivity between two
CHEMICAL templates is derivable in this project (S11); selectivity between two
METABOLIC branches is not**, and saying so is worth more than a plausible alpha.

⚠⚠⚠ **NOT FITTED, AND IT IS THE ONE NUMBER THAT CHECKS THE MODEL: THE
FERMENTATION GAS COMES OUT AT CO2 61.94% / H2 38.06% AGAINST A REPORTED ~60/40.**
H2 comes **only** from the acetonic branch, so the gas ratio is a consequence of
the solvent slate and the three stoichiometries and nothing was aimed at it.

⚠ **AND TWO INVARIANTS HOLD TO SOLVER PRECISION AT EVERY POINT** — §1's balance
showing up as a property of the trajectory: **H2/acetone is exactly 4.000000000000**,
and CO2 is `3A + 2B + E` to nine figures.

### ⚠⚠ 5. THE ORGANISM IS NOT A SPECIES, AND THAT IS THE SESSION'S HONEST HOLE

Every other gate in this project is a mechanism you can charge: an acid, a base,
a lattice, a voltage, a pinch of NO2. **A fermentation's gate is ALIVE.** The
corpus has no graph for a Clostridium and `_maybe_catalyse` needs one, so the
four templates take a `catalyst` parameter, default it to None, and **a flask of
sterile sugar water ferments.** ⚠ The hole is under all eight of M10's biological
routes, not this one, and it is why `Ea` is an APPARENT barrier over twenty
enzymatic steps. *An inventory item for a culture is a GAME_DESIGN answer, not an
engine one.*

⚠ **AND EVERY YIELD IS AN UPPER BOUND, FOR C3's REASON WITH A NEW MECHANISM.** A
real ABE batch stalls near 20 g/L of butanol because butanol dissolves the
organism that makes it, and **nothing here can express a product poisoning its
own catalyst when the catalyst is not in the flask.**

⚠ A sealed fermenter reaches **24.7 bar** at 96 h on its own CO2 and H2, and
nothing was told to do that. Vented (`k_vent` 1e-3) it sits at 1.01 bar and the
**conversion is unchanged to 1%** — no branch is reversible, so the pressure
cannot push back. *A hazard, not a ceiling*, unlike the vanillin digester where
30 bar of steam is what makes the route go.

### ⚠⚠ 6. WHAT THE SMARTS REFUSES, AND BOTH REFUSALS ARE THE POINT

The four templates share one hexopyranose pattern, narrow in one place: **the
anomeric carbon must carry an -OH**.

* **sucrose is inert to all four.** A glycoside does not match, so a brewer has to
  invert the sugar first — which is `ethanol-fermentation` step 1
  (`glycoside-hydrolysis`) being load-bearing rather than decorative.
* **fructose is inert too, and that one is a corpus limit.** Real clostridia eat
  it; the corpus spells it a **FURANOSE**, and a five-ring sugar is a different
  pattern. **S7's pyranose/furanose finding, costing a SUBSTRATE this time rather
  than an equilibrium constant.**
* **mannose IS eaten**, which is correct: same constitution, and the pattern
  queries no stereochemistry.

⚠ Every branch prints M5's **MIXES STANDARD STATES** notice, because glucose's
vapour pressure at 298 K is below the standard-state floor (its Tb is an
unanchored 825.6 K estimate on a sugar that decomposes) while its products all
shift. The two conventions differ by **64-219 kJ/mol** in dH and **flip the sign
of dS** (+466.41 -> -32.26 J/K on the ethanolic branch). ⚠⚠ **What that costs is
the EQUILIBRIUM CONSTANT and nothing else**: dG is between -121 and -353 kJ/mol
on *either* basis, so nothing is reversible under any reading. **Do not quote a K
for a fermentation in this project.** C3's notice, arriving on a SUBSTRATE.

### ⚠⚠⚠ 7. AND A STEREOCENTRE TURNED UP A KEYING BUG IN THE PROVIDER, WHICH IS THE FINDING NOTHING WAS LOOKING FOR

`homolactic_fermentation` makes a **new stereocentre** out of a sugar carbon.
RDKit inherits an unspecified chirality, so the plain pattern emits **one
L-lactic acid and one D-** from the same glucose — two species where the corpus
has one. The fix is RDKit's own rule (chirality specified in the reactant
template and absent from the product template is REMOVED), so the pattern spells
its four centres `[C;H1;@,@@:n]` and the product is geometry-free. **That is C3's
isoeugenol decision reached through a stereocentre instead of a double bond.**

⚠⚠⚠ **AND MEASURING IT FOUND SOMETHING GENERAL: THE TWO HALVES OF A ThermoData
ARE KEYED THE OPPOSITE WAY ROUND WITH RESPECT TO STEREOCHEMISTRY.**

    corpus rows whose SMILES carries a stereo marker     146
    ... which PRICE OFF A DIFFERENT SOURCE when flat       31
          the PHYSICAL half is what moved                  30
          the FORMATION half is what moved                  2
          the STEREO spelling prices better                29
          the FLAT spelling prices better                   2

* **the PHYSICAL tables carry the chiral spelling.** Sorbitol chiral reaches a
  measured Tb (YAWS, 704.0 K); flattened it falls to Joback at 888.2 K, **184 K
  away**. 29 rows are that shape — limonene, the pinenes, menthol, borneol,
  linalool, camphor, carvone, xylitol, lindane.
* **the FORMATION table carries the FLAT spelling.** Lactic acid flat reaches an
  **experimental** formation record; the corpus's chiral spelling misses it and
  falls to **Benson**, with the Tb 107 K apart.

⚠⚠⚠ **SO FOR 31 COMPOUNDS THE DATA TIER IS SELECTED BY AN ORTHOGRAPHIC
ACCIDENT** — and a spelling carries no thermochemical information at all, because
no estimator here tells one enantiomer from another (S7, re-measured).
⚠ **NOT FIXED, deliberately**: the fix is a stereo-insensitive **FALLBACK** in
the lookup (S6's rule — a fallback, never an override), and it touches the
provider every number in this project comes out of. **Recorded with a size, which
is what makes it costable.** `validation/fermentation.py` panel 8;
`tests/test_fermentation.py` pins the 146.

### ⚠⚠⚠ 8. THE WORK ORDER GREW, THE CEILING MOVED FOR THE FIRST TIME SINCE C1, AND THE CHEAP END IS OVER

| session | granted | FED_BUT_UNRUNNABLE | ceiling | playable |
|---|---|---:|---:|---:|
| G3 | — | 21 | 37 | 12 |
| C1 | 1 route | **24** | **41** | 14 |
| C2 | 2 rows | 22 | 41 | 16 |
| C3 | 2 classes | 20 | 41 | 18 |
| **C4** | **1 class** | **23** | **45** | **20** |

⚠⚠⚠ **THE CEILING IS NOT A CONSTANT, AND TWO SESSIONS OF IT SITTING STILL WERE A
PROPERTY OF WHAT THEY BUILT.** A fermentation puts acetone, ethanol, butanol and
— through `acetic-fermentation` — acetic acid on the shelf, which FEEDS four
routes that were not fed before: `acetic-anhydride-ketene`, `chloral-route`,
`mercury-fulminate-route`, `white-lead-route`. **The goal a session is measured
against moves with the session.**

⚠⚠ **AND §8b HAS NO +2 ROW LEFT.** C4 took the only one. What remains is six
classes tied at **+1** (`dehydration-cyclisation`, `biological-transformation`,
`direct-combination`, `molten-salt-electrolysis`, `oxidative-complexation`,
`pyrolysis`) and 23 at **+0**, ten of which no template can buy at any price.
**From here every row buys one route or none.**

⚠ **AND `ethylene` WAS RE-PRICED BY A SESSION THAT NEVER TOUCHED IT**: joint-
biggest single species grant at **+2** in §7 before C4, **+1** after. `aluminium`
is now the sole +2. *A content item re-prices a lever it never went near — re-run
`tools/build_playable.py` after every one.*

⚠⚠ **THE SECOND ROUTE IS BOUGHT BY A BRANCH THAT IS NOT THE TARGET, AND IT MOVED
A RULE'S EVIDENCE.** `abe-fermentation`'s catalog target is propanone; what
unblocks `acetic-fermentation` is the **ethanol**, the minority branch at a
seventh of the butanol. So it is a route bought by a BYPRODUCT, and the
target-only shortfall in `test_playable.py` **moved 4 -> 5 for the first time in
five sessions** — the same mechanism as the zinc retort's carbon monoxide.
⚠ *Which is the opposite of the fouling rule one test above it, whose only
evidence C1 dissolved and which is kept on a measured zero. A rule kept on a zero
difference and a rule kept on a growing one are different bets, and both are
printed.*

### ⚠ 9. WHAT C4 DID NOT DO, SAID OUT LOUD

* **The three aerobic rows are not built**, and two of them do not balance on one
  substrate either: `citric-acid-fermentation` reads sucrose and balances at
  `sucrose + 3 O2 -> 2 citric + 3 H2O`, and `msg-route` needs
  `2 glucose + 2 NH3 + 3 O2 -> 2 glutamate + 2 CO2 + 6 H2O` because one hexose
  wants one-and-a-half O2. **Both are honest lumps** -- the citric row at 1:1 in
  its own sugar, the glutamate row only at a twofold multiple -- which is a
  smaller sin than the one this session undid — but neither is fed, so neither
  buys a playable route.
* **`homolactic_fermentation` buys +0 playability.** `lactic-acid-pla` needs a
  polymerisation as well. It was built for the class and for §7's stereo finding,
  and it is measured at +0 rather than assumed at +1.
* **It is NOT in `fermentation_chemistry`.** A clostridial flask does not make
  lactate in quantity, and a bundle carrying it beside the ABE three would report
  a slate no organism produces.
* **The solvent slate drifts, and it is the water slot.** 2.31:3.75:1 at the
  first step and 2.42:3.75:1 at 96 h, because the acetonic branch consumes a
  water and has it in its rate law while the other two do not (S11's rule: every
  slot a template consumes keeps order 1). **Measured, stated, not corrected** —
  the alternative is order zero in water and §3 is what that does.
* **`tools/build_playable.py`'s §8b table was lifted to module level** as
  `CLASS_WORTH`, so a test can assert it. C3 generated it inside the writer, and
  *a generated table nothing asserts is a table that rots* — `ROUTE_INDEX.md`
  went three milestones that way.
* **The ethanol here is not `ethanol-fermentation`.** That route spells its four
  steps out as `glycolysis`, `decarboxylation` and `biological-reduction` and is
  a finer job with three uncovered classes. **The corpus asks for the LUMP by
  labelling five rows `fermentation` and those four by mechanism**, and reading
  that distinction is what told C4 a lump was the honest template here.

### ⚠ 10. THE SUITE, AND THE CLOCK

**1159 passed / 0 failed in 26:09**, run alone.

                        G6        C2        C3        C4     C3->C4
    total / s         1383.0    1795.0    1494.6    1569.5     +5.0%
    tests               1045      1097      1128      1159     +2.7%
    the ONE RIG test   176.9     199.3     163.2     156.2     -4.3%
    catalysis           75.1      91.5      73.5      81.0    +10.2%
    burner @1e-8        52.8      64.8      51.0      52.9     +3.7%
    SECONDS PER TEST  1.3234    1.6363    1.3250    1.3542     +2.2%

⚠⚠⚠ **C3's RE-PRICING HOLDS.** Per test, G6 / C3 / C4 are within **2.4%** of each other
and C2 sat **24% above all three** — so C2's *"+30% that nothing explains"* was the
machine, and the ~8%/~1% floor recorded before it came from two quiet runs.
⚠⚠ **AND INDIVIDUAL BIG ROWS STILL MOVE 4-10% WITH NO CAUSE** — catalysis +10.2% here
while the rig test went **down** 4.3% in the same run. *One row's change is not a signal;* 
the per-test total is, and the `--durations` list is a per-row diff rather than an alarm.
⚠ The S12->S13 eight minutes is still unbisected.

## C5 -- The sugar-to-furan dehydrations ✔✔ **DONE 2026-08-28** *(two rows, one mechanism, and a bug that took two generations to see)*

**20 -> 21 playable (tiers 10 / 10 / 1), 42 -> 44 runnable, 57/240 -> 59/240
classes, 45 -> 46 template-ready, 37 -> 38 BOTH, species-ready UNCHANGED at 85.**
Three templates, one bundle, **one ENGINE fix**, one data row, no taxonomy split.
`validation/furans.py` (9 panels, ~2 min), `tests/test_furans.py` (20 tests,
~2 min). **§8b's top row, and the first C-series session that had to change the
engine to spend it.**

### ⚠⚠⚠ 1. THE SAME RULE THAT SPLIT C4's CLASS SAYS *DO NOT SPLIT* HERE

`dehydration-cyclisation` was §8b's top row after C4: **+1 playable, +2
runnable**, the largest runnable gain on a table C4 had flattened. Its two rows:

    hmf-route      1   fructose + H2SO4 -> 5-HMF    + water + H2SO4
    furfural-route 2   xylose   + H2SO4 -> furfural + water + H2SO4

C3 bought a class by reading its SECOND row; C4 bought one by SPLITTING it five
ways. **Both were applying *read every row before crediting the class*, and here
that rule says the opposite.** These are one mechanism — an acid-catalysed triple
dehydration of a sugar into a furan, a pentose giving furfural and a ketohexose
giving 5-HMF — and each balances exactly 1:1 on its own sugar with three waters.

⚠⚠ **SO THE CLASS STANDS AND THE CREDIT NEEDS BOTH TEMPLATES.** Grant it off the
HMF row alone and `furfural-route` goes template-ready with nothing in the engine
able to make furfural. *The check that catches a false credit and the check that
catches a lazy lump are the same check; which way it points is a property of the
rows and not of the session reading them.*

### ⚠⚠⚠ 2. THE CORPUS SPELLING C4 BOOKED AS A LOST SUBSTRATE IS LOAD-BEARING HERE -- FOR ONE ROW OF TWO

C4 measured that its hexopyranose pattern does not fire on fructose *"because the
corpus spells fructose as a FURANOSE: a five-ring sugar is a different pattern"*,
and booked it as a corpus limit. It is not a defect, and the two rows use it
differently — measured out of RDKit's own reactant-to-product atom tags rather
than read off the SMARTS:

| row | product ring atoms from the SUGAR'S OWN ring |
|---|---:|
| fructose -> 5-HMF | **5 of 5** |
| xylose -> furfural | **3 of 5** |

* **fructose** — the β-D-fructofuranose ring C2-C3-C4-C5-O **IS** 5-HMF's furan
  ring. No ring bond is formed or broken; three hydroxyls leave, C6 goes to the
  aldehyde, and aromaticity perception does the rest.
* **xylose** — the xylofuranose ring is C1-C2-C3-C4-O and furfural's is
  C2-C3-C4-C5-O. **The WRONG RING.** C5 and its hydroxyl are pulled IN, the
  sugar's own ring oxygen leaves as one of the three waters, and C1 is pushed OUT
  to become the aldehyde.

⚠ **A COEFFICIENT VECTOR CANNOT SEE THAT**: both rows are 1:1:3. It is the same
blindness `corpus_balance` has, arriving on two rows that are both RIGHT.

⚠ Neither template moves an oxygen between carbons, so C4's atom-map standard
holds on both. The rehydration below is the one that cannot meet it and says so.

### ⚠⚠⚠ 3. THE ENGINE COULD NOT FERMENT SUGAR IT HAD INVERTED ITSELF

Found two generations deep in C5's own chain and then measured on C4's.
**`ReactionTemplate.run` handed back products carrying RDKit's `noImplicit` flag,
and no template can run on such a molecule.** A product-template atom written
with an H count (`[CH3:2]`, `[OH1:8]`) comes back with its hydrogens counted as
EXPLICIT; substructure matching cannot see the difference, because the total H
count is identical, so the species is discovered, priced, charged and reported
exactly as normal — and then `RunReactants` hands the flag to the NEXT template's
products, any product atom that template did not itself spell an H count for
inherits an H it must not have, and `run` catches the valence error and returns
an **empty list**.

    the glucose sucrose inversion makes    OC[C@H]1O[C@H](O)[C@H](O)[C@@H](O)[C@@H]1O
    the same SMILES, parsed                ... identical, and equal by Molecule.__eq__

    template                     BEFORE   AFTER
    ethanolic_fermentation            0        1
    butanolic_fermentation            0        1
    acetonic_fermentation             0        1
    homolactic_fermentation           1        1

    charge SUCROSE + water   4 species,  1 reaction,  ethanol FALSE   ->  9 / 4 / TRUE
    charge GLUCOSE + water   7 species,  3 reactions, ethanol TRUE    ->  7 / 3 / TRUE

⚠⚠⚠ **C4's DOCSTRING SAYS A BREWER *"has to invert the sugar first"*, AND A
BREWER WHO DID GOT NOTHING.** The claim was right about the chemistry and false
about the engine. **It is invisible to every single-template test**, because
catching it takes one template to MAKE what another consumes, and every
fermentation test C4 wrote charges glucose directly.

⚠ The general sweep — every unimolecular template against every species any
template can make from a corpus substrate — found **8 disagreements before and
0 after**, and **every one of them was C4's chemistry**: seven a fermentation
template on sugar `glycoside_hydrolysis` had inverted, and the eighth C4's own
lactic acid failing to reach `alkene_dehydration`.

⚠⚠ **THE FOURTH ROW IS THE INSTRUCTIVE ONE.** `homolactic_fermentation` was never
broken — not because it is more careful in general, but because it happens to
spell an H count for the ONE atom that carried the flag (the anomeric hydroxyl
`glycoside_hydrolysis` writes `[OX2H1:5]`), where the other three send that atom
into a CO2 they wrote `[O:6]=[C:9]=[O:10]`. **Spelling an H count on every
product atom IS a valid fix — and it is a rule an author has to remember on every
atom of every template, which is why the fix went into the TYPE instead.**

The fix is one line: re-parse every product from its own canonical SMILES.
`Molecule`'s docstring already states the identity contract — *two Molecules are
equal iff their canonical SMILES match* — and **two molecules were satisfying it
while behaving differently**. A round trip through the SMILES this engine already
uses as identity cannot lose anything that was part of the identity.

⚠⚠ **AND REMOVING THE BUG REMOVED AN ACCIDENTAL GENERATION CAP.**
`kolbe_schmitt` feeds itself: it carboxylates a phenoxide to salicylate,
dissociation takes salicylate's PHENOL proton, and the dianion is a phenoxide the
same template carboxylates again. The old behaviour stopped that walk at
generation 2. Generation 4 wants 2-hydroxyisophthalate, which the corpus does not
price, so `tests/test_named_routes.py` DECLARES `generations=3` now — which is
what `aromatic_chemistry` already tells a reader to do for a self-feeding
template. **An accidental cap is still a cap: removing the accident means writing
the cap down**, and it costs the other five cases in that test nothing.

⚠ **THE pKa ROW WAS EXPOSED, NOT MISSED.** Salicylic acid's second dissociation
(pKa 13.4, against phenol's own 9.95 — the same ortho hydrogen bond that makes
the FIRST proton come off at 2.97 instead of benzoic acid's 4.20) was never asked
for, because nothing could reach the mono-anion with a template. *C2's rule from
the other side: a table can be short a row for years if nothing can get far
enough to ask for it.*

### ⚠⚠ 4. THE +0 ROW IS WHAT MAKES THE +1 ROW MEAN ANYTHING

`hmf-route` row 2 is `hydration-ring-opening`, priced **+0** in `PLAYABLE.md`
because the route's target is already reached at row 1 — and the corpus names it
*"the side reaction that limits yield"*. It was built anyway, and re-measuring
confirms the +0 is real: removing it moves the playable count by nothing.

**Without it a flask of fructose in acid runs to 100% HMF and reports a number no
laboratory has ever seen.** With it the HMF rises, peaks and falls, and where the
peak sits is a property of two barriers rather than of a declared stopping time.
*A row worth nothing on the scoreboard can be the row that makes the scoreboard's
number mean something.*

### ⚠⚠⚠ 5. AND ITS BARRIER IS THE LOWER ONE, WHICH PREDICTED SOMETHING NOTHING WAS AIMED AT

Formation 140 kJ/mol, destruction 110 kJ/mol, both literature bands. The
destruction is therefore the **less** temperature-sensitive step:

     T/K    peak HMF yield     at t/h
     390          39.85%      155.71
     405          46.31%       42.01
     420          52.34%       11.33
     435          58.28%        3.06
     450          63.33%        0.83

**SELECTIVITY IMPROVES WITH TEMPERATURE, AND THE BATCH GETS SHORTER.** Hot-and-
short is exactly how this process is operated. Only the LEVEL of the yield is
fitted; the DIRECTION is the part that could have come out wrong. *S11's
competing-templates finding, arriving on a CONSECUTIVE pair instead of a parallel
one.*

⚠⚠ **AND A SECOND LEVER FELL OUT THAT NOBODY ASKED FOR: AN INERT SPECTATOR.**
Glucose does nothing in this network — no template touches it — and adding
0.5 mol of it takes the peak yield from **52.4% to 61.6%**. It occupies liquid
volume, the water concentration falls, and the rehydration is second order in
water while the dehydration is zeroth. **A chemically inert species moves the
yield, through the volume.** That is the corpus row's own condition column
explaining itself — `hmf-route` step 1 reads *"420 K, DMSO or biphasic"*, and
what those solvents are FOR is taking the water away from the HMF. **This engine
has no solvent model and reproduces the direction of the trick anyway, because
water is a REACTANT in the rate law rather than a background.**

### ⚠⚠ 6. ONE NUMBER IS FITTED, AND IT CHECKS AGAINST SOMETHING IT WAS NOT FITTED TO

C4 fitted three pre-exponentials and could check none of them. C5 fits **one** —
the rehydration's `A` — because a peak yield is a RATIO of two rates, and two
barriers fix only how that ratio moves with temperature, never its value at any
one temperature. 5.0e5 L²/mol²/s puts the peak at **52.5% at 420 K** against a
reported ~50-55% for fructose in dilute aqueous acid.

⚠ **THE CHECK:** folded against the flask's own water (~52.6 mol/L) that is an
effective first-order 1.4e9 /s — about 7000× below a bare transition-state
frequency factor, an entropy of activation near **−74 J/(mol K)**. That is what
ordering TWO water molecules into a transition state costs. *A fitted constant
that lands on a physically sensible ΔS‡ is a different kind of number from one
that only reproduces its own target.*

### ⚠⚠ 7. THE TEMPLATES ARE STEREO-BLIND AND EVERY EXTRA HIT IS RIGHT

Swept over all 1583 corpus compounds:

    ketofuranose_dehydration   fructose, sorbose            -> 5-HMF    (2 hits)
    aldofuranose_dehydration   ribose, xylose, arabinose    -> furfural (3 hits)
    hmf_rehydration            5-hydroxymethylfurfural      -> LA + FA  (1 hit)

**All five substrate hits are correct chemistry and none was aimed at.** Every
pentose gives furfural in hot acid — that is what a pentosan assay IS — and
L-sorbose is a ketohexose that dehydrates like fructose. C4's `[C;H1;@,@@:n]`
device is what makes it stereo-blind, and here the generalisation it buys is the
chemistry's own.

⚠ **SUCROSE IS INERT TO BOTH** — a glycoside has no free anomeric -OH, C4's
narrowing on a different ring size — so a syrup has to be inverted first. **That
inversion is the chain §3 fixed**, and it is why `hmf-route` is tier 2.

⚠ **AND FURFURAL IS INERT TO THE REHYDRATION**, which is correct: it has no
hydroxymethyl, and it is indeed the furan that survives what destroys HMF.

### ⚠⚠ 8. THE SCOREBOARD, AND THE TIER-1 MAJORITY IS GONE

| session | granted | fed-but-unrunnable | ceiling | playable | tiers |
|---|---|---:|---:|---:|---|
| G3 | — | 21 | 37 | 12 | 8 / 3 / 1 |
| C1 | 1 route | 24 | 41 | 14 | 9 / 4 / 1 |
| C2 | 2 rows | 22 | 41 | 16 | 9 / 6 / 1 |
| C3 | 2 classes | 20 | 41 | 18 | 9 / 8 / 1 |
| C4 | 1 class | 23 | **45** | 20 | 10 / 9 / 1 |
| **C5** | **1 class** | **22** | **45** | **21** | **10 / 10 / 1** |

⚠⚠⚠ **TIER 1 IS A MINORITY OF THE PLAYABLE SET FOR THE FIRST TIME.** G3's finding
was *most playable routes are tier 1* — a bush, not a tree. C3 took it to exactly
half and asserted the equality, saying that whoever broke it would be the session
where a real tier appeared. C5 broke it: **10 of 21.** The operator in
`test_the_tech_tree_is_a_shallow_bush` has now gone `>` then `==` then `<`, and
every step of that was a session buying a route that stands on another route's
output. ⚠ **Tier 3 is STILL one route, six sessions running**, and that is the
half of G3's finding that has not moved at all.

⚠⚠ **AND C5 IS THE FIRST SESSION SINCE C2 THAT DID NOT MOVE THE CEILING.** C4
moved it 41 → 45 because four solvents on the shelf FEED four more routes. 5-HMF
and levulinic acid feed nothing — no corpus route takes either as an input.
**A route can be worth a playable point and worth nothing to the goal it is
scored against**, and which of the two a session gets is a property of the corpus
rather than of the chemistry built.

⚠⚠ **`hmf-route` STANDS ON TWO TIER-1 ROUTES AT ONCE, WHICH IS A FIRST.**
`invert-sugar` for the fructose and C1's `vitriol-distillation` for the acid that
catalyses it. Every other tier-2 route in the file needs one upstream route or
one granted reagent.

⚠ **AND THE HEADLINE TEST HAD TO BE RENAMED, BY C4's OWN RULE.**
`test_the_answer_is_twenty_playable_three_tiers_deep` carried a LEVEL in its name,
and C4 had written down that *a test that pins a level will be re-numbered by the
next session that moves it, and the claim will quietly become someone else's
arithmetic*. It is `test_the_headline_and_the_tiers_are_what_the_report_says`
now. **Two sessions running, that rule has cost a test its name — and both times
`test_the_PAIR_is_worth_more_than_the_sum_of_its_parts` survived untouched,
because it asserts differences.**

### ⚠ 9. AND A LATENT SCORING ARTEFACT SURFACED THE MOMENT A ROUTE WENT RUNNABLE

`furfural-route` step 1 is written `xylose + water -> xylose`: the corpus has no
pentosan graph, so the row uses its own product as a stand-in feedstock. **A
species on both sides of a step is exactly what `route_roles` calls a CATALYST**,
so the `with_catalysts=False` counterfactual hands the route's actual SUGAR over
for free and calls it playable.

⚠⚠ **THE HEADLINE IS IMMUNE, AND THAT IS THE POINT.** `needs()` decides by ORDER
(PLAYABLE.md's rule 2, measured wrong first in G3), and by order xylose is used
at the step that first makes it, so it is external and the route is correctly not
playable. **The artefact appears only in the one counterfactual where
`route_roles` still gets to answer** — and it was latent until C5 made
`furfural-route` runnable. *A rule that was already known to be right is what
kept a corpus wart out of the headline.*

### ⚠ 10. WHAT C5 DID NOT DO, SAID OUT LOUD

* **`furfural-route` is runnable and NOT playable**, and the blocker is xylose:
  nothing in 173 routes makes a pentose. It is +1 on the runnable count and +0 on
  playability, measured rather than assumed.
* **Furfural runs to 100% and that is an upper bound.** Real yields stop near 50%
  because furfural RESINIFIES into humins, and this project has no representation
  for an amorphous polymer. `hmf-route` got a yield-limiting row because the
  CORPUS wrote one down; `furfural-route` did not. **The difference between the
  two flasks is a property of the catalog, not of the chemistry.**
* **`aldofuranose_dehydration` is NOT in `furan_chemistry`.** Same class,
  different feedstock — a bundle carrying both would report a flask nobody runs.
* **The sugars MIX STANDARD STATES for the third session running.** The
  dehydration's dH is −14.4 (gas) against −191.3 (liquid); the rehydration, which
  has no sugar in it, differs by 9. **It costs the K and nothing else** — all
  three templates are irreversible and dG is strongly negative on either basis.
  ⚠ Do not quote a K for these reactions. C3's notice, C4's notice, and now
  printed beside the numbers it applies to.
* **The stereo-keying job C4 handed forward is still open.** 31 corpus compounds
  select a data tier by an orthographic accident. Nothing here touched it.

### ⚠⚠⚠ 11. THE SUITE FOUND NINE, AND TWO OF THE NINE WERE NOT LEVELS

C5 green-lit ~150 tests across the files most likely to be affected and the full
suite still found nine. **Five were level-pins C5 legitimately moved** — three in
`test_fermentation.py` (the §8b table it owns), one in `test_protonation.py` (the
ion count, 29 → 30, an ANION again exactly as its own docstring predicts) and one
in `test_vitriol.py` (`furfural-route`'s uncovered classes, 4 → 3). **The other
four were real, and neither of them is what a green subset would have suggested.**

#### ⚠⚠⚠ THE FLAGSHIP PREP HAD BEEN MAKING AN ESTER IN CAUSTIC SODA

`test_prep_side_products.py` failed three ways, all reading `total(ACETIC) == 0`
where it used to be positive. The cause is the fix working:

    charge, 2 h, air, saponified          BEFORE        AFTER
    acetic acid                          positive      0.000000e+00
    acetate                                 0.0        6.848146e-03
    ethyl acetate                        positive      0.000000e+00
    free hydroxide in the pot                       9.312816e-02 mol

**The pot is a SAPONIFICATION and holds 0.093 mol of free hydroxide.** A
carboxylic acid in that liquor is a carboxylATE — and until C5,
`carboxylic_acid_dissociation` could not fire on the acetic acid, because
`peroxide_over_oxidation` had MADE it and the product carried the flag. So the
acid sat there neutral in caustic soda **and then Fischer-esterified with the
ethanol.** ⚠⚠ **There is no Fischer esterification at pH 13, and the engine had
been reporting one since the prep's side-product model was written.** The cascade
itself is unchanged and correct — 6.85 mmol of acetyl at two hours, exactly as
before — it is the SPECIATION that was wrong. The tests count acid plus conjugate
base now, which is what *"the prep makes its own contaminant"* always meant.

⚠ *A two-generation bug hid a one-generation wrong answer: the dissociation is
the SECOND template to touch that species, and nothing in the project charges
acetic acid into that pot by hand.*

#### ⚠⚠⚠ AND A GREEN TEST WAS RESTING ON THE ORDER OF TWO IDENTICAL ROWS

`test_dropping_funnel.py::test_the_funnel_itself_can_be_what_is_watched` died
with `RuntimeError: Factor is exactly singular` out of BDF's `I - c*J`. C5's fix
changes the order in which `run` returns product sets, so two nitration
reactions — **same name, same reactants, same products' KIND, same A, same Ea** —
swap places in the stoichiometry matrix. Nothing else about the network moves:
species set, species ORDER, every A, every Ea, every dH, every molecule-derived
property diff to zero.

⚠⚠ **MEASURED BOTH WAYS ROUND RATHER THAN ASSUMED, WHICH IS WHAT DECIDED IT:**

    pre-C5 engine + pre-C5 order      OK,   elapsed 29.985 s
    post-C5 engine + post-C5 order    RuntimeError: Factor is exactly singular
    post-C5 engine + PRE-C5 order     OK,   elapsed 29.985 s
    pre-C5 engine + POST-C5 order     RuntimeError: Factor is exactly singular

**The ordering is the whole cause and neither engine is.** ⚠ The first three
attempts at that experiment were no-ops, because `World` imports `build_network`
into its own module namespace and the monkeypatch was going onto
`chemsim.network.builder`. *An experiment that returns the answer you expected is
the one to check hardest — the "order is not the cause" reading survived two
rounds of that before the patch was pointed at the right module.*

⚠⚠ **THE SCENARIO IS WHAT IS FRAGILE, AND IT IS FRAGILE FOR A DOCUMENTED REASON.**
`aromatic_nitration` FEEDS ITSELF, and the funnel scenario let it run to
`max_species=60` — 15 species, all the way to HEXAnitrobenzene, twelve of which
cannot form at 280 K in the seconds the test runs and sit at structural zero.
Capped, it is robust: **elapsed is 29.985 s at every cap from 4 to 14 and the run
only fails at 15.** The answer not moving across ten caps is what says the cap is
not tuning. ⚠ `aromatic_chemistry`'s docstring has said *"CAP THE EXPANSION"* for
a self-feeding template since M5; this is the second place in one session where
removing the accidental cap meant writing a real one down, the other being the
Kolbe cascade in §3.

⚠ **AND THE SAME TEST HAD A SECOND, SMALLER VERSION OF THE SAME DISEASE.** With
the network capped it then failed on `assert funnel.total(NITRIC) < 1.0e-4`,
reading **1.0000000000000826e-04**. `consumed` is a ROOT, and a root is zero to
solver precision; a strict `<` asserts which SIDE of a root the solver stopped
on, which nothing guarantees. It is `pytest.approx(1.0e-4, rel=1e-9)` now.

⚠⚠⚠ **THE FRAGILITY ITSELF IS NOT FIXED AND IS HANDED FORWARD.** What C5 fixed is
a test that was passing for the wrong reason. **A 15-species rig network with
twelve structurally-zero columns can factor exactly singular, and whether it does
depends on a row permutation that changes nothing physical.** That is the rig
integrator's, it is now reproducible in four lines, and it belongs to a numerics
session rather than to a content one.

### ⚠ 12. THE SUITE, AND THE CLOCK

**The clock:** C5 RAN THE SUITE TWICE IN ONE SESSION, AND THAT IS THE BEST NOISE MEASUREMENT THIS PROJECT HAS

**1179 passed / 0 failed in 28:59**, run alone. C5 owed a second run after fixing
the nine the first one found, so for once there are TWO full runs of the same box
in the same session, 18 minutes apart:

                        run 1     run 2   change     touched between?
    total / s          1660.8    1739.0    +4.7%
    tests                1179      1179       --
    the ONE RIG test    160.8     158.5    -1.4%     no
    catalysis            72.2      72.4    +0.2%     no
    burner @1e-8         50.8      85.0   **+67.3%** NO
    rig azeotrope        22.2      34.3   **+54.5%** NO

⚠⚠⚠ **TWO ROWS MOVED MORE THAN HALF THEIR OWN VALUE WITH NOTHING TOUCHED, IN THE
SAME SESSION, WHILE THE TOTAL MOVED 4.7%.** Neither test nor anything either one
depends on was edited between the runs. **That settles what four sessions of
cross-session comparison could only bound: a single `--durations` row is not an
instrument, and the per-test total is.** C3 measured the between-run spread at
~20% on every big row; C5 measures it at **67% on one row and 0.2% on another in
the same pair of runs**, which is a stronger and less flattering answer.

Against the session series:

                        G6        C2        C3        C4        C5     C4->C5
    total / s         1383.0    1795.0    1494.6    1569.5    1739.0    +10.8%
    tests               1045      1097      1128      1159      1179     +1.7%
    the ONE RIG test   176.9     199.3     163.2     156.2     158.5     +1.5%
    catalysis           75.1      91.5      73.5      81.0      72.4    -10.6%
    burner @1e-8        52.8      64.8      51.0      52.9      85.0    +60.7%
    SECONDS PER TEST  1.3234    1.6363    1.3250    1.3542    1.4750     +8.9%

⚠⚠ **PER TEST, C5 IS 1.4750 s AGAINST C4's 1.3542 -- AND MOST OF THAT IS WORK
THAT WAS ADDED RATHER THAN SLOWED.** `tests/test_furans.py` is ~125 s of new
integration; take it out and C5 is **1.3927 s per test, +2.8% on C4**, back
inside the band G6/C3/C4 sit in. ⚠ The rest is the burner row, and the two-run
control above says what that is worth.

⚠ **THE S12->S13 EIGHT MINUTES IS STILL UNBISECTED**, and it is now measured
against a noise floor that is much wider on a single row than anyone had
allowed for.

## C6 -- The rig singularity ✔✔ **DONE 2026-08-28** *(handed forward as a numerics session, and it was a pump running dry)*

**No route, no class, no species, no data row -- ONE ENGINE LINE.** Playable
stays **21** (tiers 10 / 10 / 1), classes **59/240**, BOTH **38**, ceiling 45.
C5's `max_species=10` cap on `test_dropping_funnel` is **LIFTED** and the
scenario runs at 60. Two new tests in `tests/test_rig.py`, one new panel in
`validation/dropwise.py`. **The first C-series session that bought nothing on the
scoreboard, deliberately.**

### ⚠⚠⚠ 1. THE FRAGILITY WAS FILED IN THE WRONG LAYER, AND THE FILING WAS C5's OWN BEST MEASUREMENT

C5 handed this forward as *"a 15-species rig network with twelve
structurally-zero columns factors `I - c*J` exactly singular, and whether it does
turns on a permutation that changes nothing physical"* -- scoped explicitly as
**"a numerics session on the rig integrator"**, in the same family as the
zero-Jacobian-column pathology. C5's evidence was real and taken both ways round:
the pre-C5 engine fails on the post-C5 ordering and the post-C5 engine passes on
the pre-C5 one.

**It is one line in `rig_integrator`'s METER branch, and the ordering was never
the cause.** A permutation changes which step size `num_jac` lands on; the number
it was scaling was meaningless at every step size.

⚠ *That is the C-series shape arriving on an ENGINE item for the first time. C1:
a route blocked on a price for a species not in its chemistry. C2: a price in a
different table. C3: a class refused on one of its two rows. C4: a class refused
on its row's formatting. C5: a class that would have been half-credited. **C6: a
fragility whose stated cause was a true measurement pointing at the wrong
layer.***

### ⚠⚠⚠ 2. THE FIRST LINK ALREADY CHANGES THE QUESTION: IT IS THE SPARSE PATH THAT RAISES

`useful_sparsity` hands this rig a pattern -- **62 groups of 82 columns at cap
10, 92 of 122 at cap 15** -- so `num_jac` returns a SPARSE `J`, and scipy's BDF
branches to `splu`. **"Factor is exactly singular" is SuperLU's message**, raised
at the unguarded `LU = self.lu(self.I - c * J)` in `_step_impl`. Forced onto the
dense path, the identical network at the identical cap runs:

    cap  LU        result                             NITRIC left
     10  sparse    elapsed=29.985000000               1.000000000000e-04
     10  dense     elapsed=29.985000000               1.000000000000e-04
     14  sparse    elapsed=29.985000000               1.000000000000e-04
     15  sparse    RAISED Factor is exactly singular
     15  dense     elapsed=29.985000000               9.999999999999e-05

**A rank-deficient `I - c*J` is a hard crash on one path and a rejected step on
the other**, and nothing about the chemistry chooses between them.

### ⚠⚠⚠ 3. AND THE MATRIX IS NOT SINGULAR. IT IS SCALED.

Captured at the failing factorisation: **no zero rows, no zero columns, no
duplicate rows or columns**, and `lu_factor` accepts it with **min|U_ii| =
1.5064e-03, zero pivots, no warnings**. What it has is **cond = 4.038e+23**, a
top singular value of **6.9575e+19** against a smallest of 2e-04.

⚠ LAPACK's default-tolerance `matrix_rank` reports **26 of 122**, which reads
like a rank deficiency and is not one -- the tolerance is
`122 * eps * 6.96e19 ~ 1.9e+06`, so it calls everything below 1.9e6 zero. *A rank
computed at a default tolerance on a matrix spanning 23 decades is a statement
about the dynamic range, not about the rank.*

### ⚠⚠⚠ 4. THE 1e+19 ENTRIES ARE NOT DERIVATIVES, AND ONE SWEEP SETTLES IT

All ten of the largest entries live in ONE row -- `pot.T` -- differenced against
funnel LIQUID columns holding 1e-39 to 1e-44 mol:

    h            f(y + h e_j)[pot.T]     quotient
    1.0e-30           2.903164e-01      -1.9e+25
    1.0e-20          -1.322448e+00      -1.6e+20
    1.0e-12          -1.322448e+00      -1.6e+12
    1.0e-09          -1.322448e+00      -1.6e+09
    1.0e-06          -1.322448e+00      -1.6e+06
    1.0e+00          -1.322448e+00      -1.6e+00
    3.6e+02          -1.322448e+00      -4.5e-03

**`f` is CONSTANT across twenty decades of `h`.** It is a STEP: `Delta f` is
fixed at -1.6128 and the quotient is exactly `-1.6128 / h`, so **`num_jac`
reports its own probe size**. ⚠ This is the same shape as `jacobian.py`'s burner
column -- a difference that does not move with `h` -- arriving from the opposite
side: there the model had projected the derivative away, here it is a
discontinuity.

### ⚠⚠⚠ 5. THE STEP IS A COMPOSITION TAKEN OVER NOTHING

At the failing state the funnel is drained -- liquid-1 sums to -1.66e-05 raw,
**7.30e-26 mol after the RHS's own clamp**. Adding **1e-20 mol** of
hexanitrobenzene, twenty-one decades below `atol`:

    base     total=7.295132e-26   dominant species index 3 at x = 0.159137
    probed   total=1.000007e-20   dominant species index 14 at x = 0.999993

**A mole fraction is SCALE-INVARIANT, so an empty vessel's composition is
infinitely sensitive.** The meter carries the donor's composition and its
enthalpy into the pot, so `f[pot.T]` steps `+2.903355e-01 -> -1.322434e+00`.
⚠ **The control is exact: the same 1e-20 probe on the POT, holding 1.10 mol,
moves `f[pot.T]` by 0.000000e+00.**

### ⚠⚠⚠ 6. THE GUARD WAS A 0/0 CLAMP DOING A GATE'S JOB, AND THIS CODEBASE HAD ALREADY FORBIDDEN THAT IN WRITING

The METER branch read

    moves = ([(0, k * nL1_a / tot_a), (n, k * nL2_a / tot_a)]
             if tot_a > 0.0 else [(0, np.zeros(n))])

against `MOLE_FRACTION_DENOM`'s own comment: *"a clamp that exists to avoid 0/0
must not double as a second gate"* -- **the exact defect, one module over, stated
long before it was met here.** At `tot_a = 7.3e-26` the test passes, the division
is finite, and the pump delivers its full `k` mol/s.

⚠⚠ **A METER IS THE ONLY EDGE EXPOSED, AND THAT IS STRUCTURAL RATHER THAN
LUCKY.** A VAPOUR edge's flux is `k dP x_a` with `dP` proportional to the same
`nG_a` the composition is taken over; a DRAIN is `k nL_a` outright. Both are
first order in the holdup and stop themselves. **A meter's driver is a DECLARED
CONSTANT** -- which is exactly the property `validation/dropwise.py` panel 1 had
written down as a virtue: *"nothing in the flux law slows it down as the funnel
drains."*

⚠ **Measured rather than argued**, with a control proving the probe can see
something: a live vapour edge gives a worst quotient of **2.487e+03 that is FLAT
across probe sizes** -- the signature of a real derivative -- and at a drained
donor the vapour edge's worst quotient is **0.0**.

### ⚠⚠ 7. THE FIX, AND WHY ITS TWO HALVES MUST NOT SHARE A SCALE

`_smoothstep(tot_a / DRYOUT_MOLES)` is the GATE -- zero AND FLAT at zero, so a
drained funnel is an honestly flat column instead of a cliff -- and
`MOLE_FRACTION_DENOM`, 24 decades lower, is the 0/0 CLAMP. The delivered flux
becomes `k u^2 (3 - 2u)`: **QUADRATIC in the donor's holdup, self-limiting harder
than a drain's first order.**

    funnel holds   delivered mol/s   fraction of k    closed form
        1.00e-02      1.000000e-02    1.000000e+00   1.000000e+00
        1.00e-06      1.000000e-02    1.000000e+00   1.000000e+00
        1.00e-08      2.980000e-06    2.980000e-04   2.980000e-04
        1.00e-10      2.999800e-10    2.999800e-08   2.999800e-08
        1.00e-20      3.000000e-30    3.000000e-28   3.000000e-28

⚠ The gate scale is **two decades below the 1e-4 mol root this scenario stops
on**, so it is fully open where the answer is decided. ⚠⚠ **And it does not
strand the charge**: `validation/dropwise.py` panel 1 is UNCHANGED -- 0.0 left
and 0.5 delivered at every rate from 0.001 to 10 mol/s -- because the smoothstep
tail keeps draining. *Attenuating a flux cannot make matter, and it does not have
to lose any either.*

### ⚠⚠⚠ 8. THE CAP IS LIFTED AND THE ANSWER DID NOT MOVE

`elapsed` is **29.985000000 s at every cap from 4, 8, 10, 12, 14, 15, 20 to 60**
-- the same value the ten capped runs agreed on before the fix --
and `test_dropping_funnel` is back at `max_species=60`. **An answer that does not
move across the fix is what says it is a fix and not a retune**, which is the
same evidence C5 used to say its cap was not tuning.

### ⚠⚠⚠ 9. AND C6 NEARLY WROTE THE OPPOSITE OF ITS OWN FINDING INTO THE ENGINE

The donor total reaching **-6.29e-03 mol** was measured over RHS EVALUATIONS, and
it went into a code comment as *"the funnel is pumped 6.29 mmol past empty -- 2%
of its charge"*. **That is false.** Checked against `solve_ivp`'s own returned
solution: **150 accepted points, NONE negative, bottoming out at +1.500000e-04
mol**, exactly where the run stops. Those negatives are Newton trial iterates.

⚠⚠⚠ **The corrected statement is the more transferable one:**

> **an RHS is not only evaluated on its trajectory, and a term that is defensible
> only there is not defensible.**

The dry donor appears at Newton iterates and `num_jac` probe points -- states the
ANSWER never visits and the SOLVER always does -- and BDF differences the
function there. ⚠ *A measurement was right and the sentence drawn from it was
wrong: C5's permutation finding, happening to C6.*

### ⚠⚠ 10. A DOCSTRING HAD GONE STALE IN THE ONE WAY THAT MATTERED

`useful_sparsity` said the pattern is pure overhead *"for every rig in this
repo's test suite"*. G1's dropping funnel arrived after that was written, is
joined by a METER -- two LIQUID blocks and a temperature, not a reach through the
gas volume -- and it GROUPS, so it takes the sparse path. **The code was right;
`useful_sparsity` measures per rig and always did.** But the sparse path is the
one that RAISES where the dense one recovers, so a reader who trusted the
sentence would have concluded the crashing branch was unreachable here.
*"Measured per rig rather than assumed once" saved the behaviour; nothing was
re-measuring the sentence.*

### ⚠ 11. A LATENT UNIT MISMATCH, FOUND AND NOT FIRED

`BoundedJacobian`'s bound is `|h_j| <= max_i |y_i|`, argued as *"you cannot learn
anything about a state by moving one of its components further than the whole
state extends"*. On this rig `max|y|` is **356.0482 -- a TEMPERATURE in kelvin**
-- and it is spent as a ceiling on a MOLE COUNT: the bound permits a probe of
**356 mol** into a species holding 1e-39. **It did not fire here** (the solver
asked for factor 2.2204e-13, peak 1.49e-02, **0 clamps in 20 Jacobians**), so
nothing is changed. Recorded as **fragility 00b** because the argument for the
bound is stated in units the bound does not have.

### ⚠⚠⚠ 11b. THE SUITE, AND ITS CLOCK IDENTIFIES WHICH OF C5's TWO RUNS WAS WRONG

⚠⚠⚠ **THE SUITE: 1181 passed / 0 failed in 29:01, run alone -- AND ITS CLOCK
IDENTIFIES WHICH OF C5's TWO RUNS WAS THE ANOMALY.** C5 ran the suite twice
in one session with nothing touched between, saw the burner move +67.3% and
the rig azeotrope +54.5%, and concluded that **a single `--durations` row is
not an instrument and the per-test total is.** C6 is a THIRD run of the same
box, and it lands on C5's **RUN 1**:

                        C5 run 1   C5 run 2       C6   vs run 1   vs run 2
    total / s             1660.8     1739.0   1741.4     +4.9%      +0.1%
    tests                   1179       1179     1181
    SECONDS PER TEST      1.40865    1.47498  1.47454     +4.7%     -0.03%
    catalysis               72.2       72.4    72.65      +0.6%      +0.3%
    burner @1e-8            50.8       85.0    51.12      +0.6%     -39.9%
    rig azeotrope           22.2       34.3    22.30      +0.5%     -35.0%
    the ONE RIG test       160.8      158.5   206.60     +28.5%     +30.3%

⚠⚠ **C6 IS WITHIN 0.6% OF C5's RUN 1 ON ALL THREE OF THE ROWS C5 COULD ONLY
CALL "MOVED".** So C5's run 2 was the outlier on the burner and the azeotrope,
and their ordinary values are ~51 s and ~22 s. **Two runs can say a row is
unreliable; it takes a third to say which run was wrong.**

⚠⚠⚠ **AND THE NOISE MOVED TO A DIFFERENT ROW.** The one rig test is
**+28.5% / +30.3%** against BOTH of C5's runs -- a new high on the largest row
in the suite, in the session that matches C5's run 1 everywhere else. **It is
not C6's doing: `test_still` has no meter edge at all** (its two mentions of
the word are prose), so nothing C6 changed is reachable from it. *The spread
is not spread evenly across rows -- it lands on ONE big row at a time, and
which row is not stable between runs.* That is a stronger form of C5's
conclusion and it points the same way: **quote the per-test total, never a
row.**

⚠ **PER TEST, C6 IS 1.47454 s AGAINST C5's 1.47498 -- a difference of 0.03%
across an engine change to the rig RHS**, which is the number worth keeping.
The two new tests are ~5 s of the total.

                        G6        C2        C3        C4        C5        C6
    total / s         1383.0    1795.0    1494.6    1569.5    1739.0    1741.4
    tests               1045      1097      1128      1159      1179      1181
    SECONDS PER TEST  1.3234    1.6363    1.3250    1.3542    1.4750    1.4745

⚠ The S12->S13 eight minutes is still unbisected.

### ⚠⚠⚠ 11c. THE TOLERANCE AUDIT WAS OWED, AND IT CAUGHT C5's EXEMPTION

⚠⚠ **THE AUDIT IS CLEAN FOR C6, AND IT FOUND TWO THINGS ANYWAY.** Four of the
five rows C2 recorded as the baseline come back **exactly**: `named_routes`
raises (the diagnosed entry), `workshop` 2 lines / 1.98e-04, `activity`
1.28e-03, `mercury_retort` — the harness's own self-check — 0 lines and 1.01x.

**ONE ROW MOVED: `multistep_prep`, 6 lines / worst `inf` -> 8 lines / worst
1.07e-03.** ⚠⚠⚠ **It is not C6's.** That example has **no `Rig` and no meter
edge at all** (its single grep hit for "rig" is the word *outright*), and C6's
only executable change runs inside the rig's edge loop under `kind == METER`.

⚠⚠⚠ **IT IS C5's, AND C5 DECLARED THIS AUDIT NOT OWED.** C5's ground was *"no
RHS edit and no data-table edit"* — and C5 edited `ReactionTemplate.run`, which
changes **which species exist**, which is the state vector itself. The prep's
acetic acid dissociates in the caustic pot now (C5's speciation fix), and the
baseline moved with it. **So the rule as written is necessary and not
sufficient:**

> an RHS edit owes the audit — **and so does a change to network CONSTRUCTION**,
> because a species that exists is a state-vector entry.

⚠ C5 came within one sentence of this. Its own handoff says of `electrolyte._PAIRS`
that *"`_PAIRS` decides which ions exist, and an ion that exists is a state-vector
entry"* — it applied that reasoning to a data table and not to its own engine
change.

⚠⚠ **AND THE MOVE IS AN IMPROVEMENT: FRAGILITY 26 IS CLOSED.** The `inf` is gone
from the audit output entirely — `multistep_prep`'s worst is a finite 1.07e-03 on
`[OH-]` 0.0931 vs 0.0932. **`pH = inf` had been printed since S13**; a pot whose
acid could not dissociate had no hydroxide to take a logarithm of. *C5 closed a
fragility it did not know it was touching, and only running the audit found out.*

⚠ **TWO CORRECTIONS TO WHAT THIS AUDIT COSTS AND REPORTS.**
* ⚠⚠⚠ ~~**It is ~2 h 35 m, not "ten minutes."**~~ **REFUTED BY C7**, which
  timed the same script at **10 m 31 s** and checked it against the summary's own
  per-example wall clocks (622 s). The original "ten minutes" was right. What C6
  measured was an interval, not a run. Measured 16:26:05 -> 19:01:39 on this
  box. The "ten-minute run" figure in HANDOFF is stale and was quoted forward
  twice. **Budget two and a half hours.**
* **`multistep_prep`'s tight WALL CLOCK reads 95172.31 s, which is 26 hours and
  is impossible** — the whole audit was 9334 s. The field is a plain
  `time.time()` delta around `runpy.run_path`, so only a clock jump can produce
  it and none was confirmed. **It is a TIMING field and the audit's verdicts are
  string diffs, so no numerical conclusion rests on it.** Recorded rather than
  explained.

### ⚠ 12. WHAT C6 DID NOT DO, SAID OUT LOUD

* **Nothing on the scoreboard.** 21 playable, 59/240 classes, 38 BOTH, ceiling
  45 -- all unchanged, and that was the trade taken knowingly. `PLAYABLE.md` §8b
  is untouched and still has five classes tied at +1.
* **The stereo-keying job (fragility 0c) is untouched and has now been handed
  forward THREE times.** 31 corpus compounds still select a data tier by an
  orthographic accident.
* **`splu`'s raise is not caught.** C6 removed the cause rather than the
  consequence: a rank-deficient `I - c*J` on a rig that earns a sparsity pattern
  is still a hard `RuntimeError` where the dense path would reject the step.
  **That is a real remaining hole and it is now the whole of fragility 00** --
  narrower than C5 left it, and no longer resting on a scenario that has been
  fixed.
* **No other `n_i / sum(n)` in the engine was audited.** The vapour edge was
  measured clean and the drain is first order by construction; the vessel RHS's
  own mole fractions were not swept.

## C7 -- The stereo-keying job ✔✔ **DONE 2026-08-30** *(both recorded numbers were right, about different questions -- and the biggest thing in the session is not stereochemistry)*

**No route, no class, no species, no data row: one new module and six lookup
sites.** Playable stays **21** (tiers 10 / 10 / 1), classes **59/240**, BOTH
**38**, ceiling 45. `PLAYABLE.md` §8b is untouched for the second session
running. What moved is NUMBERS: **43 pairs of spellings that resolved
differently now resolve the same**, and four catalog steps the engine actually
runs stopped pricing their product off an estimator. New:
`properties/stereo_keys.py`, `matter.stereo_free_smiles`,
`validation/stereo_keying.py`.

⚠ The regenerated artefacts say what moved and what did not.
`COVERAGE_REPORT.md`'s **formation half measured goes 146 -> 148** -- lactic acid
and pla-unit -- and `lactic-acid`'s LIMITING tier becomes `compilation`, because
its formation half is measured now and its physical half is a YAWS boiling point.
`PLAYABLE.md` comes back **byte-identical**.

### ⚠⚠⚠ 1. THE FIRST DELIVERABLE WAS A RE-MEASUREMENT, AND BOTH RECORDED NUMBERS REPRODUCED

C4 filed this at **31 of 146**. C6 re-measured **145 of 205** and could not
reconcile them, and NEXT_PROMPT said *"a 4.7x gap on a headline is not a
methodological rounding"*. **It is exactly a methodological difference, and C7
reproduced both numbers to the unit.**

    what was asked                                      count
    canonical spelling carries stereochemistry            212
    ... of those, TETRAHEDRAL ('@')                       146   <- C4's population
    ... of those, E/Z only                                 66
    the two spellings reach different TABLES              149   <- C6's question
    the two spellings resolve to a different SOURCE        49   <- C4's question
    ... of those, tetrahedral                              31   <- C4's headline

C4 filtered candidates on `"@"` in the raw SMILES column, which is a filter on
TETRAHEDRAL stereochemistry -- a double bond carries a spelling too, and 66 more
corpus rows have one. C6 asked about table MEMBERSHIP over the wider population.

⚠⚠⚠ **AND THE 100 COMPOUNDS BETWEEN THE TWO ANSWERS ARE A SEPARATE BUG, WHICH IS
HOW C7 FOUND ITS LARGEST ITEM.** For 102 compounds the record exists under one
spelling and changes nothing: it holds a melting point and no boiling point, and
the Tm overlay is gated on `half.Tb is None`, so a species Joback can fragment
keeps Joback's boiling point *and Joback's melting point*. See §7.

*Membership counts records; only the resolved value counts numbers. Both
sessions measured correctly and only one of them measured the cost.*

### ⚠⚠⚠ 2. THE MECHANISM ON RECORD WAS TWO ROWS OF FORTY-NINE, AND THE REAL ONE IS STRUCTURAL

Fragility 0c said *the two halves of a record are keyed OPPOSITE ways* -- physical
chiral, formation flat. That is **lactic acid and pla-unit**, and nothing else.
The real shape is one table against all the others:

    table                        keys   keys carrying stereochemistry
    MEASURED_PHYSICAL            1239                            146   GENERATED
    PHYSICAL_PROPERTIES             9                              0   hand-typed
    IDEAL_GAS_FORMATION            82                              0   hand-typed
    LIQUID_FORMATION               58                              0   hand-typed
    _CURATED_RAW                   50                              0   hand-typed
    _CURATED_FUSION                 4                              0   hand-typed
    electrolyte._PAIRS             29                              0   hand-typed

**The only table with a spelling in its keys is the one a GENERATOR wrote.** S13
built `MEASURED_PHYSICAL` by resolving corpus SMILES to CAS numbers, so it
inherited the corpus's spelling; every other table was typed by hand and a human
types the simple form. ⚠ *That is a rule about how a table came to exist, not
about chemistry, and it predicts the direction of every one of the 147 one-sided
rows C6 measured.*

### ⚠⚠⚠ 3. IT WAS LIVE, AND WHAT MADE IT LIVE IS A TEMPLATE

A missed record costs nothing unless something looks a species up FLAT, and the
corpus never does. **No template in the library spells stereochemistry on its
product side: 0 of 50.** A rewrite cannot emit a spelling its SMARTS does not
name, so every centre a template makes or touches comes out unspecified -- and
the unspecified species is not the corpus's. Four catalog steps, run:

    step                     emitted                     Tb was      Tb now
    perkin-route 1           O=C(O)C=Cc1ccccc1        581.9 Job    573.1 CRC
    knoevenagel-route 1      O=C(O)C=Cc1ccccc1        581.9 Job    573.1 CRC
    menthol-route 2          CC1CCC(C(C)C)C(O)C1      530.3 Job    487.1 CRC
    lactic-acid-pla 1        CC(O)C(=O)O              505.5 Job    398.1 YAWS
    biodiesel-route 1        CCCCCCCC/C=C\CCC...        the CONTROL: unchanged

The control is the one that matters as much as the three: `transesterification`
does not touch the C=C, so RDKit carries the spelling through and the emitted
methyl oleate IS the corpus's. **A template loses a spelling only where it
rewrites one.**

⚠ `matter/molecule.py` had said this in prose since v1 -- *"templates do not
yet control stereochemistry, so a rewrite can lose it; the identity model is
ahead of the reaction model here"* -- and nothing had ever measured what it
costs. *A limitation written down is not a limitation priced.*

### ⚠⚠ 4. THE FIX: A FALLBACK WITH TWO LIMITS, AND THE SECOND ONE FIRES

`properties/stereo_keys.py`. S6's rule -- a fallback and never an override -- with
the two limits that are the whole of its safety:

1. **It may cross an AMBIGUITY and never a DIFFERENCE.** A query naming no
   stereochemistry may take a record that names some; a query naming some may
   take a flat record. Two differently specified spellings never share one --
   those are two species, which is what `matter/molecule.py` says and this must
   not contradict.
2. **The unspecified side must be answered by EXACTLY ONE record.**

⚠⚠ **The second guard is not defensive programming: `MEASURED_PHYSICAL` holds
seven skeletons carrying more than one stereoisomer, and the worst of them is
`O=C(O)C=CC(=O)O` -- maleic and fumaric acid, 230.1 K apart in Tb.** A flat
butenedioic acid without the guard takes one of them depending on dictionary
order. The aldohexose skeleton offers glucose, mannose and galactose; `CC=CC`
offers cis-2-butene, trans-2-butene *and* the flat spelling. **A fallback that
guesses is worse than the estimator it replaces, because it is wrong with a
measurement's authority.**

Every value that arrives this way says so: the provenance string gains
`(matched on the stereochemistry-free spelling: <key>)`. The provider takes a
`stereo_fallback=False` flag, for the same reason `benson=False` and
`measured_physical=False` exist -- the difference is measured, not described.

### ⚠⚠ 5. THE STRIP HAD A TRAP IN IT AND IT IS ONE CHARACTER OF API

`Chem.MolToSmiles(mol, isomericSmiles=False)` is the obvious way to flatten a
spelling and it is the wrong one: **it drops ISOTOPE labels too.** It turns
`[2H][2H]` into `[H][H]` and `[13CH4]` into `C`. Built on that flag, the fallback
would hand **deuterium hydrogen's record** -- two species merged by a flag
reached for to do something else. `matter.stereo_free_smiles` uses
`Chem.RemoveStereochemistry`, which touches only stereochemistry, and says why.

⚠ It also explains part of the 212-vs-205 gap between C7's population and C6's,
and it is why C7's own first probe counted deuterium as a stereoisomer.
*The instrument had the bug it was looking for.*

### ⚠ 6. WHAT THE RULE REFUSES, AND IT IS RIGHT ABOUT HALF OF IT

Two corpus rows have a sibling record the fallback will not take:

    elaidic-acid   dTb 128.0 K   the table holds oleic acid, the CIS isomer
    pla-unit       dTb 107.3 K   the table holds L-lactic acid; this is the D

**The rule is right about the first and costs the second.** Elaidic and oleic
acid are different compounds; taking one for the other would be a wrong number
with a measurement's authority. D- and L-lactic acid have the same scalar
thermochemistry, so that record IS pla-unit's, and 107 K of Joback is a real
loss. *A rule that took the sibling would be right once and wrong once.*
Separating them means inverting every centre and comparing -- cheap to state,
easy to get wrong on a diastereomer, and worth exactly one row. **Priced rather
than guessed at.**

### ⚠⚠⚠ 7. THE LARGEST THING C7 FOUND IS NOT ABOUT STEREOCHEMISTRY, AND IT IS NOT FIXED

Chasing why 102 compounds have a record that changes nothing:

    MEASURED_PHYSICAL entries                                    1239
    ... holding a melting point and NO boiling point               376
    ... whose measured Tm never reaches the resolved record        214

The physical half reads `if m.Tm is not None and half.Tb is None:`, so a
measured melting point is overlaid only where nothing else supplied a boiling
point. Joback supplies one for anything he can fragment -- **and then he supplies
the melting point too.** Worst case is **877 K**: methotrexate melts at 468.1 K
and the record says 1344.7.

⚠⚠ **AND THE COMMENT BESIDE THAT GATE ARGUED IT WAS HARMLESS ON A CLAIM THE
GENERATED FILE CONTRADICTS.** It read *"Nothing in the measured table is a
species Joback already prices completely (the builder checks and reports), so no
existing record's fusion pair moves."* `tools/build_physical_data.py` classifies
each candidate and does **not** exclude on it: **855 of the 1239 entries are
stamped `Joback: complete` in the generated file itself.** *A check that reports
is not a check that filters.*

Tm drives crystallisation and enters the solubility law exponentially, so this is
worth more than the thing the session was about. **Deliberately not fixed here**:
closing it moves 214 melting points at once, and inside a session about spellings
neither change would be attributable. It is fragility 0c-i and it is the top of
the queue.

### ⚠ 8. WHAT ELSE IS STILL KEYED FLAT, WITH ITS SIZE

`electrolyte._PAIRS` prices lactic acid as `CC(O)C(=O)O` and the corpus spells it
`C[C@H](O)C(=O)O`, so **a corpus-spelled lactic acid in water does not
dissociate.** Two rows (`lactic-acid`, `pla-unit`), measured, live. Left out of
this session's fallback on purpose: `_PAIRS` decides WHICH IONS EXIST, so
widening it changes the state vector rather than a number in it, and C6's rule
makes that a network-construction change owing its own audit. Fragility 0c-ii.

### ⚠ 9. AN INSTRUMENT ERROR THE AUDIT CAUGHT ON ITSELF

Panel 5 first reported **16** compounds still disagreeing after the fix. Ten of
them agree to 2e-16. **Benson sums its group contributions in the order the atoms
come out of the SMILES, and a stereochemistry-free spelling numbers the atoms
differently**, so the same molecule spelled two ways gives Cp coefficients that
differ in the last bits. Compared with `==` that reads as a failure to fix them.
The panel compares to 1e-12 now and reports the bit-noise separately. ⚠ *A
group-contribution sum is not bit-reproducible across spellings*, which is worth
knowing on its own and is nowhere else recorded.

### 10. THE SUITE AND THE TOLERANCE AUDIT

    1191 passed / 0 failed in 28:00        <- run ALONE, nothing else on the box

C6 was **1181 in 29:01**. C7 adds ten tests: one in `test_fermentation.py` for
the template-made species, and `tests/test_stereo_keys.py` (9).

⚠⚠⚠ **AND C7 RAN THE SUITE TWICE ON IDENTICAL SOURCE, WHICH SETTLES A
METHODOLOGICAL CLAIM C6 MADE.** The first run was **1182 in 29:58**, the second
**1191 in 28:00** with 1.14 s of new tests between them:

    run          tests    total / s    SECONDS PER TEST
    C6            1181       1741.4              1.4745
    C7 run 1      1182       1798.2              1.5214
    C7 run 2      1191       1681.0              1.4114

**The same source, the same session, the same box, and the per-test total moves
6.6%.** C6 offered that statistic as the stable one -- *"quote the per-test
total, never a row"* -- on the strength of landing within **0.03%** of C5 across
an engine change. ⚠ **That agreement was a coincidence.** The per-test total is
not reliable to better than ~7%, and C7 measured that CONTROLLED rather than
across sessions, which is the first time anything here has. *Two runs can say a
statistic is noisy; only two runs of the SAME code can say how noisy.*

```bash
python -m pytest -q --durations=25
```



⚠⚠⚠ **THE AUDIT IS ~10 MINUTES, NOT 2 h 35 m -- C6's CORRECTION WAS ITSELF
WRONG, AND C7 QUOTED IT FORWARD BEFORE MEASURING IT.** Timed **01:33:22 ->
01:43:53, 10 m 31 s**, and the run's own summary bounds it independently: the
twelve examples' loose and tight wall clocks sum to **622 s**, which is the
whole of the work it does. C6 recorded 16:26:05 -> 19:01:39 and attributed that
entire interval to the audit. **The repo's original "ten minutes" was right, was
replaced by a measurement of something else, and was then quoted forward twice
-- into C7's plan and into the question C7 put to the user about what the
session would cost.** ⚠ *A wall-clock interval is not a duration unless
something was watching the process.*

⚠⚠ **AND THE AUDIT IS CLEAN FOR C7: EVERY ROW C6 RECORDED COMES BACK EXACTLY.**
`named_routes` raises (the diagnosed entry), `workshop` 2 lines / 1.98e-04,
`activity` 1.28e-03, `mercury_retort` -- the harness's own self-check -- 0 lines
and 1.00x, and **`multistep_prep` 8 lines / worst 1.07e-03**, which is where
C5's speciation fix left it and where C6 found it. **Nothing moved**, which is
the right answer for a change that gives two spellings of one substance the same
numbers rather than changing what any single species integrates.

The two quotable-digit rows are unchanged and still quotable-digit rows:
`activity` at 0.1277% and `multistep_prep` at 0.1073%. Four more move below
0.1%. Tight is faster in 5 of 12 and slower in 7, worst 4.6x.

```bash
python validation/tolerance_audit.py            # ~10 min, and OWED by any change
                                                # to an RHS, a data table, or
                                                # network CONSTRUCTION
```


### ⚠ 11. WHAT C7 DID NOT DO, SAID OUT LOUD

* **Nothing on the scoreboard**, for the second session running. 21 playable,
  59/240 classes, 38 BOTH, ceiling 45. §8b is untouched and still has five
  classes tied at +1. ⚠ `COVERAGE_REPORT.md` did move: **formation half
  measured 146 -> 148**, lactic acid and pla-unit, and `PLAYABLE.md` regenerates
  byte-identical.
* ⚠ **The root README's coverage table was several regenerations behind and is
  now copied from the generated report.** It was quoting a formation coverage
  **155 compounds too high** (921 against 766), a class count against the wrong
  denominator (51/229 against 59/240) and a BOTH column of 31 against 38. C7 did
  not cause that drift and the memory note about it said "one regeneration
  behind"; it was more. **The front door of the repo is the one number nobody
  re-runs.**

* **The Tm gate is measured and open** (§7). It is the biggest live number in
  this file.
* **`electrolyte._PAIRS` is not wrapped** (§8). Two rows.
* **The enantiomer extension is priced and not built** (§6). One row.
* **Templates still do not control stereochemistry.** The identity half of the
  mismatch stands; only the lookup half is closed.
* **No other SMILES-keyed table was swept for the same shape beyond the eight in
  §2** -- `psrk_data`, `unifac_data` and `mineral_data` are keyed by group or by
  mineral name rather than by species, and `dielectric_data` was measured at 0
  stereo keys, but nothing checked the SOLID tables.

# THE P-SERIES -- MAKE IT PLAYABLE. ✔✔ **COMPLETE 2026-08-31 (P0-P4). THE LIVE ARC IS THE R-SERIES BELOW.**

⚠⚠⚠ **THIS WAS THE WORK ORDER, AND THE C-SERIES IS STILL PAUSED BEHIND IT.
THE REASON IS MEASURED RATHER THAN FELT.** ⚠ The loop is built and it was
played, and the playing produced an OBJECTION rather than a next feature --
*it wouldn't stop artificially at sulfur dioxide and need a deliberate
trigger* -- which is what the R-series is. Read it after this section.

The C-series work order is `PLAYABLE.md` §8b: 22 rows, each buying one route.
C6 and C7 both spent a session on engine honesty and bought nothing on the
scoreboard, and the question "is this always going to be a slow slog" got asked.
`validation/playable_levers.py` answers it, and the answer changed the plan:

    what                                                     playable (of 173)
    today                                                                   21
    grant all 27 missing CLASSES  (~22 template sessions)                   31
    grant every species a price   (data work)                               25
    grant BOTH                                                              45
    grant the 28 stranded-route SPECIES  (a shelf decision)                 41

⚠⚠⚠ **22 TEMPLATE SESSIONS BUY +10 ROUTES, NOT +24.** The ceiling of 45 that
§8b is written against is a JOINT grant of templates AND prices; §8b ranks each
class holding prices fixed, so every row in it is understated and the total is
overstated. **The two streams are super-additive: +10 and +4 apart, +24
together.**

⚠⚠⚠ **AND 23 ROUTES ARE ALREADY RUNNABLE AND MERELY UNREACHABLE.** The engine
executes them today; they are stranded because their feedstocks are made by other
stranded routes. **Granting those 28 species takes 21 -> 41 with no new chemistry
of any kind.** That is a decision about what a player starts with, and it is the
cheapest distance on the board by a factor of four.

⚠⚠ **THE ENGINE WAS NEVER THE PROBLEM, AND THE SAME AUDIT SAYS SO.** One
template -- `esterification` -- matches 166 acids against 190 alcohols, about
**31 500 reactions**, and the catalog credits its class with **9 route steps**.
**169 of the 240 catalog classes appear in exactly one route step**, because the
catalog is a list of named industrial processes and a named process is a one-off
by construction. *The slog is a property of the target list, not of the
architecture -- and the remaining §8b rows are overwhelmingly metallurgical,
which is precisely the chemistry with no family structure to exploit.*

**So the P-series stops optimising a number nobody can play and builds the loop
instead.** `GAME_DESIGN.md` §8 is the design; every figure above is a panel of
`validation/playable_levers.py`.

## P1 -- The notices have to have somewhere to go -- **DONE 2026-08-31**

`build_network` printed to stdout. A mix-anything game generates hundreds of
NOTICE lines per step -- 397 for five reagents at two generations -- and stdout
is not a place a player looks. Both halves are built.

**1. The notices are carried, not moved.** `ReactionNetwork.notices` holds every
string the builder emitted, in order; `Snapshot.notices` publishes them from the
worker thread; the reports panel renders them beneath the vessel's own reports
under a labelled rule. ⚠ The `print` stays -- a validation script and a test
harness both read it -- so the two channels say the same thing and a test asserts
exactly that. `_ExpansionState.report` became `reports` and RETURNS its strings,
because a method that prints can only serve one destination and that is the whole
bug.

⚠ **AND THE PANEL NEEDED A SCROLLBAR, WHICH IS NOT A COSMETIC NOTE.** It was
seven lines tall and now holds four hundred notices: showing the first seven of
four hundred is the same failure as printing them where nobody looks. `_set_text`
also had to stop resetting the scroll position -- it runs on every 120 ms poll,
so a bare delete-and-insert scrolled a reader back to the top before they could
finish a sentence.

**2. The silent coverage limit is closed.** The generation limit broke out of the
expansion loop with a non-empty frontier and said nothing, while `max_species`,
oversize molecules and mixed standard states all reported. It now issues a notice
naming the count and the species, and `ReactionNetwork.unexpanded` carries the
same set as data. The count is promoted into the reports panel's HEADING rather
than left as the last of hundreds of lines, because it is a fact about the flask
rather than a note about it: *this flask has more to give.*

⚠⚠⚠ **AND `validation/playable_levers.py` PANEL 5 CAUGHT P1'S OWN FIRST VERSION
BEING WRONG, WHICH IS THE FINDING WORTH CARRYING.** The first version read the
frontier only on the generation branch. Panel 5 -- extended in this session to
print `notices` and `frontier` columns, which also re-measured the 397 to the
unit -- reported **frontier 0 for every `gens=2` row**, on 400-species networks
that had plainly been truncated:

        gens  charged  species  reactions  seconds  notices  frontier
           1        3       12          4     0.01        1         3
           1        5       45         36     0.62       31        34
           1        8       63         51     0.56       44        49
           1       12       77         67     0.43       44        59
           2        3       12          8     0.02        0         0
           2        5      400        766    12.40      397       355
           2        8      400        755     6.07      406       337
           2       12      400        743     3.99      392       323

**THE BOUND THAT BIT IS NOT ALWAYS THE BOUND THAT WAS DECLARED.** At
`generations=2` the species cap bites first, so the generation branch never runs
-- and a "react further" control reading that empty frontier would have declined
to offer itself on precisely the flask with the most left to give. The frontier
is now taken on either exit and the NOTICE says which bound stopped it. ⚠ Against
a species cap it is a LOWER bound and the cap's notice now says so: the round the
cap interrupted was left unfinished, so combinations of the previous frontier
went untried as well and those species are not in the list. Against a generation
limit -- the case the game runs on every step -- it is exact.

⚠ **A BOUND THAT NEVER BIT MUST STAY SILENT, and that measurement is what makes
the notice mean anything.** `generations=6` on a system that closes in two exits
through the `while` with an empty frontier and says nothing, because it is not an
approximation. A notice keyed on the ARGUMENT rather than the OUTCOME would have
fired on every `refine` round in the project.

⚠⚠ **WHAT P1 FOUND AND DID NOT FIX, AND P4 NEEDS IT: `generations` IS NOT A
`Scenario` FIELD.** `World.__post_init__` builds its network to a fixpoint and
there is no way to ask for one-generation play through the UI at all. So
`Snapshot.unexpanded` is correct and currently always empty in a session. Adding
it is a `Scenario` field, a `to_dict`/`from_dict` pair and a `SAVE_VERSION` bump
-- which P2 is touching anyway for BOTTLE and CHARGE, and which is why it was
left rather than bolted on here.

Suite **1202 passed / 0 failed in 30:52**; `tolerance_audit.py` **10 m 36 s**
and byte-identical to C7's record, nothing moved. Scoreboard unchanged: 21 of
173 playable, 59/240 classes, 38 BOTH.

## P2 -- `Stock` and the shelf: the two verbs that close the loop -- **DONE 2026-08-31**

    BOTTLE         vessel -> shelf     name the current VesselState and store it
    CHARGE_STOCK   shelf  -> vessel    pour a stored stock into a flask

Both are built, both are events, and `SAVE_VERSION` is **7**. `engine/stock.py`
is the new module: a `Stock` is a name, a `VesselState`, and the script that
made it; a `Shelf` is those by name in arrival order.

**A stock is a `VesselState`** (§1) -- a per-phase mole vector and a
temperature, never `(name, purity)` -- and that claim is now a MEASUREMENT rather
than a design note. Two bottles both honestly labelled "90 mol% ethanol", one's
10% water and the other's 10% acetic acid, charged into identical flasks at 353 K
for two hours: **the sour one makes 9.83e-02 mol of ethyl acetate and the wet
one makes 3.83e-11**, which is below the integrator's own per-component atol and six
orders down. A purity scalar cannot tell those two bottles apart.

Purity is DERIVED, and P2 found that deriving it is not one number:

⚠⚠ **A BARE PERCENTAGE ON A SHELF ROW IS THE ONE FIGURE THAT MEANS NEITHER.**
0.05 mol of benzoic acid wet with 0.05 mol of water is **50 mol% and 13 wt%**
water -- and worse, the BIGGEST COMPONENT of that bottle is water by mole and
benzoic acid by mass. So `major()` takes the basis as well as `purity()` does:
a major fixed on moles printed beside a purity quoted by mass reads *"water at
87 wt%"*, which is two true numbers making one false statement.

⚠ **BOTTLING LOSES A FILM AND A CRUST**, through `Vessel.withdraw` and the same
two mechanics a pour suffers, because bottling wets the glass. Had it moved
matter perfectly, BOTTLE would have been a loss-free transfer sitting beside a
lossy one and **bottle-and-recharge would have been the cheapest route around
holdup in the game.** Cross-checked the other way too: bottling a hot flask and
charging the stock into a cold one gives the same moles and the same final
temperature, to 1e-12, as pouring one flask into the other.

⚠ Impurities are carried individually and forever, which is the whole loop --
measured over three steps at half scale each, the 0.02 mol of water charged in
step 1 is 0.005 mol in the third bottle and the bottle's own script says where it
came from. And **a stock can react in the bottle**, which nobody designed: it has
a temperature and a phase layout, so advancing one is an ordinary integration.

### Three findings, two of them pre-existing bugs

⚠⚠⚠ **A REPLAY DROPPED A TRAILING EVENT, AND "BOTTLE IT AND STOP" IS ONE.**
`now` schedules for the current instant and events fire BETWEEN integrations, so
an action taken after the last step -- which the original run applied with
`flush` -- was left sitting in the replayed world's queue. Measured on a
two-event script: `set_heat` 50 W gave the original `Q_input = 50.0` and the
replay **0.0**, with one event still pending. Pre-existing, and invisible for as
long as it was because only a TRAILING event can be bitten: anything with a
`step` after it is applied by that step. *P2 would have shipped a replay with an
empty shelf.* `run_script` now flushes at the end, which is trajectory-neutral
and adds nothing to the script.

⚠⚠ **A STOCK'S PROVENANCE CANNOT BE "THE SCRIPT AS IT STANDS", BECAUSE THE
SCRIPT RUNS AHEAD OF THE EVENT QUEUE.** Entries are appended when an action is
SCHEDULED. The same run, bottled and then replayed, produced two stocks with
identical compositions to every digit and DIFFERENT provenances -- the replayed
one carrying the `charge_stock` that happened afterwards. So the recipe is sliced
at the entry that scheduled the bottling: a recipe that includes what happened to
a bottle after it was filled is not that bottle's recipe, and reading the live
script would have made the field depend on when the queue was flushed.

⚠⚠ **THE UI'S FILTER BUTTON DISCARDED THE WHOLE FLASK, SILENTLY, AND HAS SINCE
IT EXISTED.** It sent `to=` and the FILTER event reads `filtrate` and `cake`, so
the vessel picked in the dropdown received nothing and both streams were binned.
Measured on a 1 mol charge: *"filter flask: cake 0.0000 mol solid + 0.0000 mol
liquor -> discarded; filtrate 1.0000 mol -> discarded"* -- which is the engine's
own `transfer_log` saying exactly what happened, on a channel nothing in the view
was reading. **The refluxing rig's 0.34 mol of air again, one panel over.** Fixed
with two destination pickers, since a filtration has two streams. ⚠ And the
Transfer tab's `"all"` phase, offered since the first commit, was never
implemented -- `pour_into` raised on it. Implemented, because BOTTLE needs the
same word: the contents of the flask and NOT its headspace, because a bottle
brings its own air.

### And what P1 handed over: `generations` is a `Scenario` field now

`World.__post_init__` called `build_network` with no `generations`, so a world
always built to a fixpoint and **nothing could request one-generation play
through the UI at all** -- `Snapshot.unexpanded` was correct and permanently
empty. It is a field, a `to_dict`/`from_dict` pair that keeps `None` as `None`
(`int(...)` would raise and a default of 0 would build an EMPTY network), and it
reaches the snapshot: a `generations=1` session leaves ethyl acetate on the
frontier and says so in a notice. **P4's "react further" control now has both a
state to offer and a bound to lift.**

Suite **1202 -> 1227 tests, 0 failed in 29:23**. `tolerance_audit.py` is NOT owed: P2
touched no RHS, no data table and no network construction -- `generations` is
plumbed THROUGH `build_network`'s existing argument and changes nothing when it
is `None`, which is every existing scenario.

## P3 -- The shelf as data, with three tiers ✔✔ **DONE 2026-08-31** *(and the obvious resolution rule strands five rows in a form no mechanic can touch)*

`data/catalog/shelf.psv` exists: **71 rows**, `id | tier | amount | phase | note`,
diffable and tested like the rest of the corpus. `tools/build_shelf.py` resolves
it against the whole compound catalog and writes
`src/chemsim/engine/shelf_data.py` (`SHELF`, 71 rows; `ROSTER`, all 1583 species
with a verdict each); `src/chemsim/engine/inventory.py` turns a row into a real
`Stock`, and `scenario_for` turns a SELECTION into a world.

    natural       43 rows   out of the ground, the air, or something living
    intermediate  24 rows   a STRANDED route makes it -- EARNABLE, so DELETE it
                            the day that route becomes reachable
    bottle         4 rows   nothing in 173 catalog routes makes it at all
    ---
    all_priced()  1167      the cheat axis. NOT a fourth tier.
    roster()      1583      the picker's content, 416 of them greyed

⚠ **45 natural species, 43 rows, and the two missing ones cannot be added.**
`coal-marker` and `collagen-marker` have no molecular graph -- a marker is a
rock, a mixture or a protein carried so the catalog's routes stay balanced -- so
neither can be a `VesselState`, which §8.6 forbids outright. The generator
refuses an unresolvable id and `tests/test_playable_levers.py` pins the marker
set as an equality, so a third one cannot appear silently.

⚠ **Seven natural rows are REFUSED a price and stay on the shelf anyway** --
gold, quartz, pyrite, pyrrhotite, pyrolusite, borax, cryolite. "You can dig this
up" is a true statement about the world whatever the estimators say; the picker
greys them WITH the engine's own reason, and the day one is curated the row
lights up with no edit to the file.

### ⚠⚠⚠ THE FINDING: A ROCK HAS TWO REPRESENTATIONS AND THEY ARE NOT INTERCHANGEABLE

The obvious rule -- *charge a mineral as its `mineral_data` lattice* -- reads
correctly, generates a clean report, and **puts five shelf rows into the flask as
matter no mechanic in this engine can touch.** Measured, 0.5 mol into 30 mol of
water at 298 K for 600 s:

    rock salt as [Na+] + [Cl-] in the solid block   0.5 mol dissolved, block empty
    rock salt as the lattice '[Cl-].[Na+]'          0.5 mol of solid, for ever

Because the engine holds a solid **two incompatible ways**, and each has
mechanics the other does not:

    the LATTICE as one species     calcination, roasting, gas-solid reduction
                                   (`solid_state`, `surface`: the lattice IS the
                                   species)
    its IONS in the solid block    dissolution and precipitation through a Ksp
                                   (`PrecipitationArrays`: "the lattice is not a
                                   species and never becomes one")

and **nothing converts one into the other** -- `examples/lime_cycle.py` says so
in a comment: *the two representations of CaCO3 are different species that do not
know about each other.* Rock salt, fluorite, saltpetre, phosphate rock and
anhydrite have NO solid-state or surface reaction, so dissolving is the only
thing they do. Two of the five are load-bearing: rock salt is the chlor-alkali
feedstock, and `validation/phosphate_rock.py` charges the rock as
`{[Ca+2]: 3, PO4(3-): 2}` in the solid block and had already recorded that
*without the lattice the rock is INERT.* **C2 measured the failure mode this rule
would have walked into, a session before it was written.**

So the rule is MECHANISM-DRIVEN, read off the engine's own declarations:

    1. a lattice a solid_state/surface reaction consumes  -> the LATTICE
    2. else a mineral with ions and a priceable Ksp       -> its IONS, solid
    3. else charged fragments                            -> its ions, dissolved
    4. else                                              -> the molecule

⚠ **Rules 1 and 2 COLLIDE on six rows and rule 1 wins, which costs them their
dissolution**: calcite, covellite, galena, sphalerite, cinnabar, green vitriol
can be calcined or roasted and **cannot be dissolved by anything**. Limestone in
acid does nothing. That is a **NAMED ENGINE GAP** rather than a preference, and
the way out is a mechanic that turns a lattice charge into its ions.

⚠ **And the coverage audit's own tier answers a different question.** Seven rows
audit as `ion` and are rocks: the audit asks *can this be priced at all*, the
shelf asks *what species is in the bottle*, and the two come apart on 7 of 71.

### The phase column is a DECLARATION, and olive oil is why

The engine can answer "solid, liquid or gas at 298 K" for a neutral molecule --
gas if p_sat is above 1 atm, solid if Tm is above 298.15, liquid otherwise -- and
it is wrong about **triolein by 550 K**: Joback gives it `Tm = 828.9 K`, so a
derived phase puts a bottle of olive oil in the SOLID block. One shelf row in 71
disagrees with the engine and it is that one. *An estimator outside its domain
again, one rung further out than the element floor.*

⚠ A Henry's-law species is a GAS here, and reading `coefficient()` as a pressure
put nitrogen, oxygen and carbon dioxide in the liquid on the first pass.

`tolerance_audit.py` is **not owed by the PSV** -- a shelf row feeds no property
estimator and no rate -- but see P4, which changed what a network is built from.

## P4 -- The step UI, and then play it ✔✔ **DONE 2026-08-31** *(and playing it found six template fields that never reached the engine)*

Both controls are built and both are in the window.

**THE BENCH TAB IS THE PICKER.** 71 tiered rows, or all 1167 priced species, or
all 1583 with the 416 refusals **greyed and carrying their reason**; tier
checkboxes, a search box, a `generations` field and a species cap. ⚠ Choosing
rows BUILDS THE WORLD rather than filling a list -- P2's handoff -- so
`inventory.scenario_for` owns the two guarantees a widget cannot be trusted with:
every charged species in `feed_species`, and `electrolyte` on whenever an ion is
charged. `examples.bench` is an `Example` like the other four, so Reset, Save and
Load need no special case.

**REACT FURTHER raises the bound.** ⚠⚠ **AND IT RAISES THE SPECIES CAP TOO, which
is not a convenience**: at `generations=2` four bench reagents hit 400 species, so
the bound that BITES is the cap and a button that only bumped `generations` would
rebuild an identical network and look broken. Measured: glucose, water and air
give 400 species and 653 reactions at *both* 2 and 3 generations. **P1 found the
same competition from the other side.** The Drive tab now says which bound is in
force at all times, because "built to a fixpoint" and "bounded with nothing left
over" are different states of the world.

⚠ And it replays the RECIPE against a deeper reaction set, which is *the
experiment re-done knowing more chemistry* and not *the flask carried on from
here*. Stated in the message rather than left to be inferred from a number that
moved.

**The save format had to be fixed first.** It held `{"example": key, "script":
[...]}`, which is enough only while every world is one of four hard-coded ones. A
bench world is a shelf selection and has no key; a reacted-further world differs
from its key's scenario by exactly the bound that was raised. Both would have
reloaded as something else, silently. It carries `Scenario.to_dict()` now, and a
pre-P4 file still opens.

### ⚠⚠⚠ THEN IT WAS PLAYED, AND THE PLAY FOUND SIX FIELDS THE ENGINE NEVER SAW

Sulfur, air, water and a trace of NO2 off the shelf -- the game's own chain 2 --
**would not make vitriol at one atmosphere.** Two causes, in the order they were
found, and *neither one was findable from a green suite*:

**1. The bench's library was false by more than half.** It collected only
`*_chemistry` bundles -- the rule `validation/playable_levers.py` panel 5 uses --
and silently skipped every template exported as a function of its own:
`sulfur_combustion`, `sulfur_trioxide_hydration`, `lead_chamber`,
`esterification`, `cannizzaro` and about forty more. The flask gave **four
species, no reactions and an EMPTY FRONTIER at every generation count**, which is
the engine correctly reporting a library with no sulfur chemistry in it, while a
blurb claiming *every template in the project* was on screen. The sweep is by
RESULT TYPE now, so a naming convention nobody promised to keep cannot fool it.

**2. ⚠⚠⚠ `TemplateSpec` WAS DROPPING SIX `ReactionTemplate` FIELDS, AND A
FRONTEND CAN ONLY REACH THE ENGINE THROUGH A `Scenario`.** `sulfur_combustion`
declares `orders=(1, 1, 0...)` -- first order in oxygen, which S11 spent a
session establishing -- and the network ran the SMARTS' own **ninth-body mass
action** instead. 0.02 mol of S8 in a sealed litre at 700 K for an hour:

    O2 charged     declared 1st order     mass action (9 bodies)
      0.05 mol         15.23%                    0.0000%
      0.20 mol         99.44%                    0.0736%
      0.50 mol        100.00%                   77.85%

**A threshold where the declared law is a straight line**, and the shelf's own
oxygen bottle sits at 0.05. The same drop silently **un-gated every heterogeneous
catalyst** (`solid_catalyst`, S1 -- eleven templates declare one, and without it
ammonia synthesis runs in a flask with no iron), **took the driving force out of
every electrode reaction** (`electrons`, M8), and **lost G2's ring
deactivation** (`hammett_rho`, and `aromatic_nitration()` ships with **-6.5**, so
this was the DEFAULT being lost -- every stage of a staged nitration ran at the
same rate). `SAVE_VERSION` is **8**: the same bytes mean something different now,
which is the strongest reason to bump there is.

⚠ **THREE OF THE SIX WERE FOUND BY A TEST AND THREE BY THE PLAY, AND THE TEST
ONLY FOUND THEM BECAUSE IT ASSERTED THE *SET* OF FIELDS.** The play reached
`orders`; writing `tmpl_fields <= spec_fields` turned up the three `hammett_*`
ones immediately. *The lesson is not "add the field" -- `alpha`'s own comment
already said a template field is not finished until it round-trips. It is that
the assertion has to be about the set rather than about whichever field somebody
remembered.*

### And then it worked

    gens  species  frontier  what appeared
       1        6         1  SO2
       2        8         2  SULFURIC ACID, and NO
       3        8         0  nothing -- the network is complete and says so

**Chain 2 out of the picker in two presses of a button**, from four natural rows
and one intermediate. ⚠ The NO2 is why the `intermediate` tier exists: there is
no template for SO2 + O2 -> SO3 without a carrier, so sulfur, air and water alone
stop at SO2 **with an empty frontier** -- the engine saying it knows no further
chemistry rather than declining to look.

⚠ **The bench flask VENTS**, so an open flask at 700 K passes its steam and its
oxygen out of the top (S12's lesson again) and makes 3e-5 mol of SO2 in an hour.
And the shelf's gas amounts are deliberately small -- 0.05 mol is about a litre
at room conditions -- so an oxidation in a 1 L flask is oxygen-starved by
construction, which is a true thing about a bench rather than a bug: 0.2 mol of
S8 wants 1.6 mol of O2.

⚠⚠ **AND THE SHELF'S OWN WATER BOTTLE STOPS THE SHELF'S OWN SULFUR
BURNING, WHICH IS THE PLAY'S LAST FINDING AND IS EMERGENT.** A gas-phase
combustion is first order in GASEOUS S8, and 5 mol of water (90 mL) holds the
sulfur in the liquid. Sealed, 700 K, one hour, 0.05 mol of oxygen throughout:

    S8 charged   water    S8 in the gas    burnt
      0.20 mol   5.0 mol      4.30e-04     0.0001%
      0.20 mol   0.5 mol      3.32e-03     1.7369%
      0.02 mol   5.0 mol      4.70e-05     0.0003%
      0.02 mol   0.5 mol      3.92e-04    15.2266%

**A tenth of the water is 7.7x the sulfur in the vapour and four orders of
magnitude of conversion.** Nothing declares that: it is the phase model
partitioning S8 into whichever liquid is there. *You do not burn sulfur in a wet
flask*, and the engine says so without being told. ⚠ An earlier draft of this
section said "seal it and the same charge burns", which is FALSE and was written
from the 0.02 mol row: sealing changes almost nothing at 5 mol of water. The
lever is how much water you pour, and the shelf's bottle is 5.0.


`validation/shelf.py` is the standing audit for all four panels above.

## What the P-series must NOT do

`GAME_DESIGN.md` §7 and §8.6. No purity scalar; no recipe unlock list; no
success flag over an experiment (the answer is a composition and a yield, and
reading the flask IS the game); no shelf entry that is not a real `VesselState`;
no silent generation limit.

⚠ **And it must not try to reduce the shelf to naturals in the same pass.**
That is the C-series, it is 22 one-off sessions, and the measurement says it can
wait. Get the loop playable first.

## The C-series -- coverage, deliberately deferred (the ORIGINAL note, kept)

Where "grind out the remaining classes, including the boring ones" lives. The
greedy curve in PART 2 is its work order, subject to the RUNNABLE-column warning
printed beneath it. ⚠ Nothing in the G-series blocks it and every G-series
template counts toward it.

# THE R-SERIES -- REACT UNTIL DONE. **THE LIVE ARC AS OF 2026-08-31, AND IT STARTS FROM AN OBJECTION RATHER THAN FROM A PLAN. R1 IS DONE (2026-09-01); R2-R6 ARE OPEN.**

⚠⚠⚠ **THE OBJECTION, IN THE USER'S OWN WORDS:** *"In the real world these
materials would continue to react until everything was done -- it wouldn't stop
artificially at sulfur dioxide and need a deliberate trigger."*

**That is correct, and this project already conceded it in writing.**
`GAME_DESIGN.md` §8.2 says one generation is an approximation that **TOUCHES
MATTER**, which §3 forbids, and that it is admissible **only** because it is
never silent. P1 built the saying and P4 built the asking, and neither of them
made the approximation go away. So the R-series is the arc that asks whether the
bound can simply be **dropped**, and every row below is a measurement rather
than an opinion.

`validation/shelf.py` panel 5 is the standing audit for all of it: sub-panels A
to F, ~2.8 minutes, thread-capped, every figure re-measured live except F, which
is recorded and re-runnable with `--mass-cap`.

## ⚠⚠⚠ THE HEADLINE: THE BOUND IS NOT THERE FOR THE REASON EVERYONE ASSUMED

**It is not a discovery-cost bound. It is an INTEGRATION-cost bound**, and
nothing in this repo said so before now.

    glucose + water + air        species   rxn    build      step   sim s   wall s / sim s
    generations=1                     33    20    1.29s     9.97s    3600           0.0028
    fixpoint (hit the 400 cap)       400   644   20.25s   120.25s     300           0.4008

**A fixpoint is ~145x more expensive to INTEGRATE, and the extra 20 seconds of
BUILD is a rounding error next to it.** The same simulated hour is **10 seconds
against 24 minutes**. The solver evaluates all 644 reactions on every
right-hand-side call, and nearly every one of them is kinetically dead at 298 K.

*Everybody had been looking at the wrong half of the cost.* **That is the case
for rate-aware pruning (R4), and it is the only thing on this list that is
really about performance.*

## 1. A FIXPOINT IS FREE FOR NON-POLYMERISING CHEMISTRY -- IT IS AVAILABLE TODAY

    picked off the shelf, generations=None    species   rxn   frontier   build
    sulfur, air, water, NO2                        14     5          0   1.51s
    limestone + water                               8     0          0   0.58s
    brine                                           9     0          0   0.84s

**Frontier ZERO in every row.** The pick in the objection -- P4's own chain 2 --
**closes on its own in a second and a half**, and the SO2 stop that prompted the
complaint is not a bound biting at all: it is the engine reporting that it knows
no SO2 + O2 chemistry without a carrier. Set `generations=None` and that flask
runs to completion with no trigger and no button. **For the whole inorganic half
of the shelf, "react until done" is not a feature to build; it is a default to
choose.**

## 2. SUGARS AND ORGANICS EXPLODE, AND IT IS A PROPERTY OF THE TEMPLATE SET

glucose + water + air at a fixpoint: **400 species, 644 reactions, frontier
367** -- it hit the species cap, so it is not a fixpoint at all.

**The cause is that two templates BUILD.** `esterification` and
`ether_condensation` take an acid or an alcohol and hand back a bigger molecule
that is a **valid reactant for the same rule**, and a sugar is a polyol, so the
product set feeds itself. There is no fixpoint for this chemistry -- only a size
bound or a count bound. **No parameter anybody can raise fixes it**, which is
why the answer has to be a different axis (R4) rather than a bigger number.

## 3. ⚠⚠⚠ A MOLAR-MASS CAP IS DEAD AS AN IDEA, AND THE REASON OUTLIVES THE MEASUREMENT

Measured on the same pick, and **refuted**. ⚠ The table below is the R1 one:
**two of its four rows could not be measured before R1**, because they crashed
on an unpriceable species -- that is what *"it turns two picks into crashes"*
used to mean.

    max_molar_mass   rxn   frontier    build    outcome
    none             644        367    10.6s    hit the 400-species cap
    500 g/mol        519        367   100.6s    hit it too -- and is SMALLER
    400 g/mol        458         83   126.1s    smaller still
    250 g/mol        842        199   380.7s    hit it -- and is BIGGER

**It never closes the fixpoint at any cap, and every cap is ~10x to ~36x
slower.** ⚠⚠ **AND THE TWO ROWS R1 UNLOCKED CHANGE THE FINDING'S SHAPE: THE
REACTION COUNT IS NOT MONOTONIC IN THE CAP.** 519 and 458 are both BELOW the
uncapped 644 and only 250 g/mol goes above it, so *a tighter bound makes a
bigger network* is **true at 250 g/mol and is not a law** -- and it was stated
as one only because the two rows that contradict it were the two that crashed.

What survives all of it, and does not depend on the arithmetic: **the cost is in
the SEARCH and not in the RESULT.** 500 g/mol takes 100 s to produce FEWER
reactions than 10.6 s of uncapped work, because a cap makes the expansion try
combinations it then refuses. And where the bound bites hardest it also
**REDIRECTS** the search into a denser region -- 842 against 644 -- because
refusing the heavy products leaves the light ones to recombine with each other.

⚠⚠⚠ **AND THIS FINDING'S OWN CORRECTION WAS ITSELF WRONG, WHICH IS THE PART
TO READ.** The first write-up recorded the uncapped build at **10.9 s**, making
388 s a **35x** slowdown. The R-series overturned that to **19x**, on the grounds
that sub-panel B builds the identical network at 19.8 / 20.1 / 20.2 s and so the
10.9 s did not reproduce. **It reproduces**: re-running sub-panel F itself gives
**10.5 and 10.6 s**. B and F were never measuring the same thing -- **B builds a
WORLD and F calls `build_network`** -- so the R-series divided F's numerator by
B's denominator, *which is the exact mistake it was accusing the first write-up
of.* Interleaved in one process, identical networks (400 species / 644
reactions) both ways:

    build_network    11.14s   10.67s   10.85s
    World(bench)     20.46s   20.35s

Not a warm cache, and it does not drift with order: the ~9.6 s gap is World and
Vessel construction on top of the network build. **Like for like it is 36x, and
the original 35x was right.** ⚠ A consequence worth carrying forward: **"build"
in sub-panels B and C is a WORLD build and roughly half of it is not discovery
at all** -- which leaves panel C's conclusion untouched, because 10.8 s of
discovery against 107 s of stepping is the same argument as 19.8 against 107.
*A number quoted across two measurement paths is wrong however carefully it is
divided.*

## 4. AND AT THE SAME CLOCK THE FLASK IS BARELY DIFFERENT -- THE OPEN QUESTION, SETTLED

This was handed forward as **unmeasured** and costed at ~20 minutes of stepping.
It is ~2 minutes: step both worlds **to the same clock** rather than to the same
wall time, which is what the earlier attempt failed to do. glucose + water +
air, 300 s from an identical charge:

    species present                27  (gens=1)   vs   42  (fixpoint)
    new species in the fixpoint    15
    largest move on ANYTHING       5.56e-07 mol, against a 0.5 mol charge
    temperature                    296.9214 K    vs   296.9213 K

**The two runs DO give different flasks** -- the extra species are real and the
bound touches matter exactly as §8.2 says. **But the 624 extra reactions move
nothing by as much as a micromole**, and the 15 species that appear top out at
2.0e-07 mol.

⚠ **SCOPE IT HONESTLY, BECAUSE THIS IS ONE SYSTEM AT ONE TEMPERATURE FOR ONE
CLOCK.** The species that appear are lactate **esters**, and esters BUILD, so a
hot flask or a long run is a different measurement and **it has not been made**.
This is evidence that the bound is cheap *here*; it is not a proof that the
bound is cheap. **It does mean the correctness argument for one-generation play
is now stronger than it was, and the performance argument is the one that is
actually load-bearing.**

## 5. ⚠⚠⚠ AN UNPRICEABLE SPECIES CRASHES THE BUILD, AND IT IS REACHABLE IN TWO CLICKS

    picker rows '5-HMF' + 'oxygen', generations=1  ->  ValueError
    no thermochemistry available for 'O=Cc1ccc(C=O)o1': its formation half
    resolved (Benson group additivity) but there is NO physical half

**Both rows are offered ungreyed by the picker, and this is ONE generation.**
The handoff recorded this as *"deeper exploration crashes rather than
degrades"*; that understates it. 5-HMF is priced and chargeable, and the species
it makes -- 2,5-diformylfuran -- has a formation half from Benson and no
physical half, because no measured Tb exists anywhere, so no vapour-pressure
curve can be built and thermochemistry refuses rather than pretending the thing
is non-volatile.

**That refusal is right in isolation and wrong here.** `max_species`,
`max_molar_mass` and `generations` all DROP, NOTICE and carry on. This one
propagated out of `build_network` as a bare `ValueError` and the player got a
traceback. **It is the reason R1 was a prerequisite and not a nice-to-have.**

✔ **CLOSED BY R1, AND THE COUNT IN THIS FINDING IS WRONG BY FOUR.** The
exception reported the first refusal and stopped. With all of them reported it
is **five species from three templates** -- the dialdehyde, its ether dimer and
three bis-furylmethanes -- and with all five refused **the pick has ZERO
reactions**. The engine cannot price any chemistry it can find between 5-HMF and
oxygen, which is a statement about the pick that no traceback could make. See
R1 below.

---

# THE R-SERIES WORK ORDER, RANKED

## R1 -- AN UNPRICEABLE SPECIES BECOMES A REPORTED COVERAGE LIMIT. ✔✔ **DONE 2026-09-01, AND IT CHANGED THE ANSWER RATHER THAN JUST THE FAILURE MODE.**

Drop it, do not expand it, notice it -- exactly as `max_species`,
`max_molar_mass` and `generations` already behave, on the same
`_ExpansionState.reports` channel, carried on `ReactionNetwork.notices` and
published through `Snapshot`. **Nothing deeper than one generation is safe until
this exists** (finding 5).

⚠⚠ **THERE IS A REAL DESIGN QUESTION INSIDE IT AND IT MUST BE ARGUED, NOT
WRAPPED IN A `try`/`except`.** A species that cannot be priced **is not in the
model**, so dropping it changes what is in the flask -- and `GAME_DESIGN.md` §3
forbids that being silent. The argument that makes it admissible is the same one
§8.2 makes for the generation bound: *the limit is a choice the moment the
player can see it.* Which means the notice has to name the species, name which
half of its record resolved, and say what would fix it (a measured boiling point
in `properties/physical_data.py`) -- the refusal already says all three, so the
work is routing it rather than writing it.

⚠ And it must drop **the reaction, not just the species**, the way the
`max_molar_mass` branch in `_expand_once` already does with `too_big` -- a
half-registered reaction whose product has no thermochemistry is worse than
either alternative.

### WHAT WAS BUILT

`network/builder.py` grew a **fourth reported coverage limit**, on exactly the
channel the other three use. `_unpriceable` screens every NEW product BEFORE
`_concrete_reactions` runs, because pricing is what that call does; a species no
provider can price is recorded against its own refusal in
`_ExpansionState.unpriced`, the whole rewrite is dropped the way the `too_big`
branch drops one, and `_ExpansionState.reports` emits a notice that is printed
AND carried on `ReactionNetwork.notices` -> `Snapshot.notices`. The structured
companion is **`ReactionNetwork.unpriced`**, a `{smiles: refusal}` map on the
same footing as `unexpanded`.

The notice quotes the refusal **verbatim** for the first three species, because
the refusal already names the species, says which half of its record resolved,
and says what would fix it -- so the work was ROUTING it, not writing it,
exactly as this milestone predicted. `_NOTICE_REASONS = 3` because a refusal runs
~400 characters and twelve of them is a notice that has hidden itself in its own
length.

### ⚠⚠⚠ THE CRASH WAS HIDING THE REAL ANSWER, AND THAT IS THE FINDING

A traceback reports the FIRST refusal and stops. Closing it showed the picker's
own pick is not one species:

    picker rows '5-HMF' + 'oxygen', generations=1
      aerobic_oxidation                 2,5-diformylfuran
      ether_condensation                its ether dimer
      friedel_crafts_hydroxyalkylation  three bis-furylmethanes
      ------------------------------------------------------------
      5 species dropped, 5 rewrites discarded, and the flask has
      8 species and **ZERO REACTIONS**

**The engine cannot price ANY chemistry it can find between 5-HMF and oxygen.**
That is a fact about the pick that the exception could not state, and it is a
different fact from "something went wrong". *A crash says a thing failed; a
notice says what is missing and what would fix it, and only the second is a
limit a player can act on.* ⚠ It also re-prices the earlier write-up: the
handoff called this *"deeper exploration crashes"*, panel 5E corrected that to
*one generation off the picker's own roster*, and R1 corrects it again to
**five species from three templates**.

### ⚠⚠ THE DESIGN QUESTION WAS NOT THE ONE THIS MILESTONE PREDICTED

It predicted the hard part would be arguing that dropping a species is
admissible at all -- it touches matter, which §3 forbids being silent -- and that
argument is §8.2's and went in as written. **The hard part was that ONE PROVIDER
RAISES TWO REFUSALS AND ONLY ONE OF THEM IS A COVERAGE LIMIT.**

    no thermochemistry available    NO SOURCE IN THIS PROJECT prices this
                                    species, with any provider.  A DATA gap.
    OutsideEstimatorDomain          THIS provider is the wrong one.  The
                                    species IS priceable and the message says
                                    by what.  A SETUP gap.

Treating them alike is what the first implementation did, and it **broke two
green tests**, which is how the distinction was found rather than argued:

* `test_granularity.py::test_saponification_fires_on_the_catalog_s_own_substrate`
  -- saponification under a NEUTRAL provider makes a stearate ion that
  `electrolyte_provider()` prices perfectly well. 5 reactions became 0.
* `test_furans.py::test_the_kolbe_cascade_needs_its_generation_cap_declared`
  -- the kolbe dianion, which that file pins as a RAISE.

So the element floor's refusal is passed through untouched, and the fix is a
**type**, not a string match: `properties/thermochemistry.OutsideEstimatorDomain`,
a `ValueError` subclass, so every existing `except ValueError` still catches it
and nothing else changed by adding it. Both tests went green again **with no
test edits**, which is the evidence that the distinction is the code's and not
the tests'.

⚠ **AND THE REASON THE SETUP GAP IS SAFE TO PASS THROUGH IS MEASURED, NOT
ASSUMED.** `VolatilityProvider` short-circuits a charged species to non-volatile
*before* consulting thermochemistry, which is why an ionic product under a
neutral provider has always built rather than raised. The one path that does
price it is a REVERSIBLE template, and `_concrete_in_phase` already catches that
and re-raises naming the reaction, the phase and the provider to use. **A loud
refusal that names its own fix is the right answer to a misconfigured network;
a missing MEASUREMENT is the one nobody can act on, and that is the only one
that drops.**

### WHAT IT COST AND WHAT IT DID NOT

Nothing. `ThermochemistryProvider.get` caches on success, so a species that
survives the screen is priced once and read from the cache by the reaction
construction two lines later; `state.unpriced` is consulted first and is the
failure cache the provider does not keep. `validation/shelf.py` panel 5E is
rewritten from *"if this line prints, R1 is done"* to asserting the notice, and
four tests are pinned in `tests/test_robustness.py` -- the file whose docstring
is *every state a player can reach must WORK, or REFUSE CLEANLY WITH A REASON.*

### ⚠⚠ AND THE AUDIT R1 OWED FOUND A NUMBER THAT HAD BEEN WRONG FOR THREE SESSIONS

`validation/tolerance_audit.py` was owed from P4 and from R1 -- both are network
CONSTRUCTION. Eleven of its twelve rows held byte-for-byte. `workshop` came back
**1.95e-04** against a standing record of **1.98e-04** stable across P1 and C7.

Three causes were refuted before the real one was found: **not R1** (all four of
`workshop`'s networks report `unpriced` empty, and a worktree at HEAD already
reads 1.95e-04), **not BLAS threading** (capped twice and uncapped once, all
1.95e-04 -- so R2's capping is numerically neutral here), **not noise** (it is
deterministic in every repeat). Bisected to **`05609c4`, P3+P4**.

⚠⚠⚠ **THE MOVED LINE IS A JSON SAVE-FILE SIZE IN BYTES.**

    save = 10113 bytes of JSON      P2 and before
    save = 10237 bytes of JSON      P4 and after

**The loose/tight gap is 2 bytes in both and never changed** -- the saved JSON
holds a float whose decimal form is two characters longer at rtol 1e-8. What
moved is the DENOMINATOR: P4's six new `TemplateSpec` fields grew every save file
by 124 bytes, so 2/10113 became 2/10237. **`workshop`'s default-tolerance stdout
is byte-identical across those commits**, which is the proof. *That row was never
evidence about convergence; every session that quoted 1.98e-04 was quoting the
size of a JSON blob.*

Fixed in the instrument, on the file's own precedent: it already excises a wall
clock as a TOKEN because the first version manufactured a `wait_until` finding
out of *"0.07 s of wall"*. A serialized size is the same class of number, so
`scrub` now takes both -- and the module **asserts its own behaviour on import**,
because both findings this audit has ever manufactured came out of `scrub` rather
than out of a solver. ⚠ `1.25 bar` survives the size pattern only through its
trailing ``, which is load-bearing and is now asserted.

**New standing record** (thread-capped; `serious` unchanged at two):

    activity            1 line    1.28e-03   <-- quotable digits move
    multistep_prep      8 lines   1.07e-03   <-- quotable digits move
    workshop            1 line    1.33e-04   (was 2 lines / 1.98e-04)
    wait_until          4 lines   1.03e-04
    vessel              2 lines   2.40e-05
    competing_pathways  1 line    1.77e-05
    named_routes        RAISES -- the diagnosed entry, unchanged
    esterification, lime_cycle, roasting_and_the_catalyst_gate,
    mercury_retort      0 lines, and mercury_retort at 1.00x is the
                        harness's own self-check

⚠ **The lesson is the one this audit already taught once**: *an instrument that
cannot tell a wall clock from a result will manufacture findings.* It took three
sessions of a stable wrong number and a full bisect to notice it was doing it
again with a byte count -- and the only reason it was catchable is that the
number had been WRITTEN DOWN.

## R2 -- CAP BLAS THREADS  *(~15 min + a measurement)*  ✔ **DONE 2026-09-01**

Measured on identical work: uncapped scipy/BLAS used **7.21 cores**; with
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1` it used **0.99 cores and was FASTER (5.9 s vs 10.1 s)**.
**There is no trade-off**: this engine's arrays are small enough that threading
is pure overhead, and *"single process" is not "one core"* -- sample it rather
than assume.

⚠ **DECIDE WHERE IT BELONGS, BECAUSE THE OBVIOUS PLACE IS THE RUDE ONE.**
`chemsim/__init__` is tempting and would silently reconfigure BLAS for anyone
who imports this as a library. The UI's worker thread is the case that actually
matters -- it would otherwise spread a player's whole machine over one flask --
so `chemsim/ui/__main__.py` and the validation harness are the defensible
places. Nothing in the repo caps threads anywhere today (`grep`ped: zero hits).

### WHAT WAS BUILT (2026-09-01)

`chemsim/threads.py` -- `cap_blas_threads()`, `setdefault` on the four
variables so a count somebody set by hand wins. Called from **four entry
points and no library code**: `chemsim/ui/__main__.py` (before the app import,
which is what loads numpy), `validation/shelf.py` and
`validation/tolerance_audit.py` (both before rdkit/numpy), and
`tests/conftest.py` -- the suite's standing 1260-green record was taken
thread-capped, and capping in `conftest` is what makes that condition
reproducible rather than ambient. `chemsim/__init__` stays import-light and
`tests/test_threads.py` **asserts it does not cap** (plus the other three
contract points: all four variables, hand-set wins, and being called after
numpy loads is loud in the return value -- the pools are sized when numpy
first loads, so a late cap is a no-op and must say so). ⚠ The owed measurement
was already discharged by R1: capped twice and uncapped once, the tolerance
audit's output is identical -- the cap is numerically neutral, so being late
costs speed and nothing else, which is why late is a `bool` and not a raise.

## R3 -- WIRE OR DELETE `Scenario.prune_threshold`  *(~30 min)*  ✔ **DONE 2026-09-01: DELETED, SAVE_VERSION 9**

It is declared, documented as *"0 disables pruning (structural discovery)"*,
round-trips through `to_dict`/`from_dict` into every save file, and **reaches
nothing** -- `build_network` has no pruning parameter at all. Its partner
`T_build` **is** wired, to `T_ref`. **A save-file field that does nothing is a
lie in the format**, and it is the same class as P4's `TemplateSpec` bug: a
field a frontend can set, that the engine never sees.

⚠ Deleting it is a `SAVE_VERSION` bump. Wiring it is R4. **Do not leave it as it
is**, which is the only option that is wrong on its own terms.

### WHAT WAS DECIDED (2026-09-01): DELETED, AND THE ARGUMENT IS STRUCTURAL

**The field could not be wired honestly even if R4 shipped tomorrow, because
it sits on the wrong class.** The machinery it gestured at already exists and
is DORMANT -- `discovery.refine_network` (Layer 4.5), zero callers and zero
tests, which already implements exactly R4's defensible form: promote an edge
species by k x the CONCENTRATIONS ACTUALLY CHARGED, integrating the core-only
network to get them. Its signature is the tell -- it takes `feed:
{SMILES: mol/L}`. **A `Scenario` does not contain the charge**: vessels are
filled by script EVENTS after the world is built, so at `World.__post_init__`
-- the only place a Scenario-resident threshold could act -- there is nothing
to evaluate a rate against. If R4 ships, its knob belongs wherever the charge
lives (the bench pick, or a rebuild-after-charging), not on `Scenario`; the
note where the field used to be says so.

So: field, `to_dict` and `from_dict` entries deleted; `SAVE_VERSION` 8 -> 9,
**the only version that REMOVES a field and the only one where every old save
would replay bit-identically** -- the bump is for the format's contract (a v8
producer could set the field believing it pruned), not the bytes. `T_build`'s
comment lied too ("temperature used for rate-aware pruning") and now says what
it does: the `T_ref` the network's thermochemistry is priced at.
`tests/test_protocol.py` now pins the scenario dict's **key SET** -- P4's
set-of-fields discipline pointed the other way, so the next dead field has to
edit a test to get in. Five version pins moved 8 -> 9 (all already compared
against the CONSTANT, P4's `test_stock` lesson holding); the stale-version
loops learned `8`. Targeted: 42/42 across the six save-format files, ruff
clean. ⚠ Not owed: the suite (nothing read the field, so no trajectory can
move -- the pins were the blast radius and they were run) and the tolerance
audit (no RHS edit, and no argument `build_network` receives changed).

## R4 -- RATE-AWARE PRUNING  *(one session)*

The real answer to the objection, and the headline above is the case for it: the
cost is the solver evaluating 644 reactions, nearly all dead at 298 K, on every
RHS call. Start from `properties/` and `network/builder.py`'s `_expand_once`.

⚠⚠ **THE DESIGN TRAP: PRUNING ON THE RATE CONSTANT ALONE IS WRONG**, because a
slow reaction at high concentration still matters. The defensible form is
**k x the concentrations actually charged**, which makes the network depend on
the charge -- **that is a design decision and not a coding job**, and it has a
consequence worth staring at before starting: two flasks holding the same
species in different amounts would get **different networks**, so a scenario's
network stops being a pure function of (templates, feed species). Everything
`scenario.py`'s own docstring says about determinism has to be re-argued
against that.

⚠ And finding 3 is the warning: a bound that looks like it shrinks the problem
can enlarge it. **Measure the reaction count, not just the clock.**

## R5 -- THE BENCH `generations` BOX SILENTLY RESETS A RAISED BOUND  *(~20 min, UI)*  ✔ **DONE 2026-09-01**

Observed live by the user, who went from 3 generations back to 1 without being
told. `_react_further` (`ui/app.py:645`) raises `scenario.generations` and
`scenario.max_species` and **never writes either back to `self.bench_gens` /
`self.bench_cap`**; `_pour_bench` (`ui/app.py:609`) reads those boxes. So the
next pour silently discards the bound the player raised. **The fix is to write
the raised bounds back into the boxes**, which also makes the current bound
visible in the one place a player would look for it.

### WHAT WAS BUILT (2026-09-01)

Exactly that: `_react_further` writes `gens` and `cap` into the two boxes after
`rebuilt(...)`, both of them, every press -- the boxes show the LIVE scenario's
bounds, so a value typed but never poured is overwritten, which is the honest
reading (after REACT FURTHER the world's bounds ARE these). ⚠ Verified by a
LIVE PROBE rather than a widget test, because the repo has no Tk in tests
anywhere and this is pure widget plumbing over the already-tested `rebuilt`:
a real `App` on a withdrawn root, water+glucose at gens=1, one programmatic
press -- boxes read `2 / 400`, equal to the scenario, and `_pour_bench`'s own
`_float` read of them returns the raised bounds. The P2 Filter-button
precedent, done deliberately the same way.

## R6 -- THE LATTICE/ION GAP  *(P3 named it, did not close it -- unchanged)*

A solid is held two incompatible ways and nothing converts between them:

    the LATTICE as one species    calcination, roasting, gas-solid reduction
    its IONS in the solid block   dissolution and precipitation via a Ksp

Measured, 0.5 mol into 30 mol of water at 298 K for 600 s: **rock salt as ions
dissolves completely; rock salt as its lattice sits there for ever.** So
`shelf.psv` chooses per row, and on **six rows** the choice costs the row its
other mechanic -- calcite, covellite, galena, sphalerite, cinnabar and green
vitriol can be roasted and cannot be dissolved by anything. **Limestone in acid
does nothing.** `validation/shelf.py` panel 2 and `tools/build_shelf.py`'s
docstring carry the measurement and the rule.

⚠ It is not obviously small: a lattice and its ions are different species with
different standard states, and the conversion is the dissolution law
`mineral_data` refuses for a lattice **with reason** (the fusion law is 407x
wrong for NaCl and 11x wrong for CaCO3, in opposite directions). What is
probably right is a term consuming the lattice and producing its ions in the
solid block, priced from the same Ksp `PrecipitationArrays` already uses -- read
`properties/solubility_product.py` and `vessel/vessel.py`'s
`build_precipitation_arrays` before costing it.

## What the R-series must NOT do

The bound may become a **default the player chooses** and it may become
**cheaper**; it may not become **invisible**. Every rule in §8.2 still applies:
a limit the player can see and lift is a choice, and a limit nobody is told
about is the thing §3 forbids. ⚠ And R4 in particular must not turn a coverage
limit into a **silent** one: a pruned reaction is a reaction that was discovered
and then discarded, which is a stronger claim than never having looked, and it
has to say so.

# ⚠ STATED NON-GOALS — the things that are NOT coming, and what they cost

This section exists because the audit that produced M10 and M11 also found three
gaps that appear in **no** planning document, and silence is how a limitation
turns into a surprise. Each is written down here with its measured cost so that
the decision to skip it is a decision rather than an oversight.

**PHOTOCHEMISTRY — not planned, and it costs ONE STEP.** Light is not a driver
anywhere in the engine, and doing it PROPERLY means an intensity field, a quantum
yield per transition and a path length. Measured against `data/catalog`: exactly
**one step** in 377 is `photoreduction`. ⚠ The honest reading is that this is a
CATALOG artefact rather than a fact about chemistry — photochlorination and
photographic development are real, cinematic, and absent from the corpus — so if
either ever gets added, this line has to be re-costed rather than cited.

⚠ **AND THERE IS A CHEAP APPROXIMATION THAT NEEDS NO ENGINE WORK, so "not
planned" must not be read as "impossible".** Explicit catalysis (HANDOFF 37)
folds a catalyst concentration into `A` and DECLARES it — `_maybe_catalyse` and
`_kinetics` in `reactions/library.py`. A lamp is the same shape: a photon flux
folded into the pre-exponential of a template that only exists while the lamp is
on. That buys "the reaction goes in the light and not in the dark", which is the
whole of the game mechanic, and it buys none of the photophysics. It is subject
to the same rule as any other folded constant: **declare it, and say what bounds
it.**

**STEREOCHEMISTRY CONTROL — not planned, and it costs ZERO catalog steps.**
⚠ The cheap approximation here is a DECLARATION rather than a model: a template
could state `retention` / `inversion` / `racemic` on a mapped centre without the
engine gaining any stereochemical reasoning at all. That is worth doing the day a
chiral template is written, and not before.
`matter/molecule.py` is explicit that identity DISTINGUISHES stereoisomers
(RDKit's canonical SMILES is isomeric, so R/S and E/Z are different species) but
that templates cannot SET them. So asymmetric synthesis, chiral resolution and
enantioselective catalysis are out. **No catalog route needs one**, which is why
this is a non-goal rather than a milestone — but note the asymmetry: the engine
would happily let a template produce the wrong enantiomer *silently*, because a
rewrite that does not specify stereochemistry is not an error. ⚠ If M5 ever
authors a template on a chiral centre, that template must say what it does to the
centre or the project acquires exactly the kind of confident wrong answer it
exists to refuse.

**ABSOLUTE REACTION TIME — not achievable, and this one is permanent.**
Pre-exponentials are the last hand-authored parameter and there is no route to
deriving them: barriers set the temperature response and the competition between
pathways (and are sourced), while A-factors set only the absolute timescale.
⚠ **The risk is EROSION, not error** — that a simulated reaction time eventually
gets quoted as a prediction. The sulfur burner is the standing counter-example
(A pinned to the collision limit, the resulting soft threshold asserted rather
than tuned away), and the rule stays: bound an A against a stated observable, or
declare it hand-authored and say what bounds it.

⚠ **What none of these three is: a blocked reaction.** Photochemistry costs one
catalog step, stereochemistry costs none, and the A-factor limitation degrades a
NUMBER rather than removing a transformation. Measured, **121 of the catalog's
173 routes (70%) sit behind no wall at all** and are pure template-and-data work;
of the 52 that do, **32 are behind M6, M8 and M9**, 8 behind M10 and 16 behind
M11. **There is no permanent hard wall in this project's way — only unbuilt
milestones.**

---

# The shape of the plan, in one paragraph

**M0 fixed the last wrong answer, M1 made the instrument honest, M2 made a still
a protocol, M3 made an ion precipitate and M4 made a solvent mixture say when it
was never modelled (all 2026-08-23). Five for five, and in FOUR of them the
MEASUREMENT TAKEN FIRST changed what the milestone was: M0's prescribed fix was
wrong, M1's expected credit would have made the audit less truthful, M3's
blocker was a data file already installed, and M4's single gap turned out to be
two problems — one of which had a ceiling that was itself a measurement of
another library rather than a target. The silent pair is closed. M5 onward is
content and new physics, and should be run against a target rather than against
completeness.** ⚠ **M8-M11 and the STATED NON-GOALS were rewritten 2026-08-24 by
an audit that asked a different question — *what can this engine never do?* — and
the answer is worth carrying: **121 of 173 routes (70%) sit behind no wall at
all**, 32 behind M6/M8/M9, 8 behind M10 and 16 behind M11. Two of those
milestones did not exist before the audit. **Nothing in the catalog is behind a
permanent hard wall** — the only truly unachievable item, absolute reaction
TIME, degrades a number rather than removing a transformation. The catalog's own headline stands: growing the template library,
not the data tables, is what moves the number that matters — but M2, M3 and M4
all beat templates on payoff per unit effort, and none of them is a template.

⚠⚠ **AND S6 MEASURED THE TRAJECTORY, WHICH NO MILESTONE HAD DONE.** Template-ready
routes went **25 at M5 → 28 now**: S1 +1, S3 +0, S4 +1, S5 +0, S6 +0. **Six
consecutive sessions produced +3 routes.** Each found something real — a gas that
attacks a crystal, a bounded Jacobian, a swept tolerance, a trustworthy species
column — but the aggregate is a project spending its measurement discipline on the
ENGINE while its own plan says the constraint is CONTENT. The instruction *"M5
onward is content and new physics, and should be run against a target rather than
against completeness"* is in this document and has not been followed since M5.

⚠ **The fair counter, also measured:** on the INTERSECTION column (§S6) the same
stretch reads better than +3, because species work and template work land on the
same number there — S6 alone moved it **12 → 17**. The engine sessions were not
wasted; they were being scored against a column that could not see half of what
they did. **Both readings are true and the honest summary is: right work, wrong
scoreboard, and the content queue is still untouched since M5.**

⚠⚠ **AND M6 ONWARD KEEPS REFUTING THE SECOND HALF OF THAT SENTENCE, WHICH IS
WORTH SAYING OUT LOUD.** The template count has been **34 since M5** and the
class count has gone **29 → 36**. Every class gained since then was covered by a
TERM — a reaction inside a crystal, a gas arriving at one, an ionic lattice
leaving solution — or by two of them COMPOSING: `solid-carbonation` and, in S4,
`roasting-to-metal`, which is a catalog ROW that falls out of two declarations
neither of which writes it. **A term is worth more than a template when the
mechanism is one the kinetics kernel cannot express at all**, and three
milestones running that is where the coverage came from.
