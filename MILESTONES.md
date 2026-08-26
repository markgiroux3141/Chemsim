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

⚠⚠ **AND M6 ONWARD KEEPS REFUTING THE SECOND HALF OF THAT SENTENCE, WHICH IS
WORTH SAYING OUT LOUD.** The template count has been **34 since M5** and the
class count has gone **29 → 36**. Every class gained since then was covered by a
TERM — a reaction inside a crystal, a gas arriving at one, an ionic lattice
leaving solution — or by two of them COMPOSING: `solid-carbonation` and, in S4,
`roasting-to-metal`, which is a catalog ROW that falls out of two declarations
neither of which writes it. **A term is worth more than a template when the
mechanism is one the kinetics kernel cannot express at all**, and three
milestones running that is where the coverage came from.
