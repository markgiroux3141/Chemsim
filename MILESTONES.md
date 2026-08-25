# Milestones: from "a simulator with chains" to "a sandbox you can play"

Written 2026-08-22, after auditing `data/catalog` (1,583 compounds, 173 routes)
and probing four capability questions against the running code. Every number
below is measured, not estimated; the probes are reproducible from the snippets
named in each section.

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

## M6 — Solid-phase reactions  *(13 steps, ~5 routes, already queued)*

Chain 2's own green-vitriol seed (`FeSO₄ → Fe₂O₃ + SO₃`) is a dry decomposition
with no liquid for the solid to dissolve into. Unlocks `roasting`, `calcination`,
`carbothermic-reduction`.

⚠ **"Solid-basis formation data is curated and waiting" was checked at the end of
M5 and is half wrong.** `green vitriol` is curated; **Fe₂O₃ has no entry**, and of
the five `roasting` rows only ZnS prices while ZnO does not — so zero roasting
rows are complete. What IS complete is the **lime cycle**: `calcite` and
`quicklime` both carry measured CRC data, so `CaCO₃ → CaO + CO₂` can be the first
solid-phase reaction built against species that already price. **Start there**, so
that a failure is unambiguously the engine's and not the data's.

⚠ **And M5's standard applies here too, with the rows already read:** `roasting`
IS one mechanism across all five rows (`metal sulfide + O₂ → metal oxide + SO₂`)
except `mercury-from-cinnabar`, which gives the metal because HgO decomposes at
that temperature. **`calcination` is TWO mechanisms** — decarbonation in two rows,
dehydration in the third.

**Also here:** the lead chamber's missing fourth step (nitrosylsulfuric acid,
chamber crystals) — a real side reaction in a water-starved chamber, and exactly
the emergent-failure content the design wants.

---

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

## M8 — Electrochemistry  *(4 routes, all of them famous)*

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
