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
**no lever** -- 46 routes are one class away, from 36 DIFFERENT classes -- so it
is a grind with a real slope, not a breakthrough waiting to happen.

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
BUILDABLE:** nobody nitrates an aniline, you acetylate it first. Acetanilide's
ring is activated by 22.3 kJ/mol against aniline's 48.2, and an amide does not
answer `amine_protonation`'s pattern, so the acetanilide network BUILDS where the
aniline one refuses. **Nobody told the engine that an amide is a protecting
group.**

## G3 -- `PLAYABLE.md`, the scoreboard the goal needs

A generated standing audit answering the question no existing artefact does:
**what can a player make, starting from what?** `ROUTE_INDEX.md` knows feedstocks
but not what runs; `COVERAGE_REPORT.md` knows what runs but never asks whether a
feedstock is obtainable. Neither answers *"what can I make from a rock?"*

⚠ The classification is already written and measured (7 from-the-ground / 6
one-step-up / 14 blocked on an unmakeable intermediate / 4 from a reagent bottle).
⚠ **The one hand judgement in it -- which compounds count as NATURAL -- must be
printed, not hidden**, so it can be argued with.

## G4 -- The granularity audit  *(possibly free routes)*

How many routes are, like `benzene-nitration`, chemically runnable but scored as
blocked because the catalog spells a mechanism out in steps the engine does in
one? **Nobody has counted.** Until someone does, the BOTH column is an unknown
amount too low, and content work may be being aimed at gaps that are not gaps.

## The C-series -- coverage, deliberately deferred

Where "grind out the remaining classes, including the boring ones" lives. The
greedy curve in PART 2 is its work order, subject to the RUNNABLE-column warning
printed beneath it. ⚠ Nothing in the G-series blocks it and every G-series
template counts toward it.

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
