# Next session: two walls down, and the one they were hiding

Read `HANDOFF.md` for project context, ethos and current state (items 67-70 are
this session), and `GAME_DESIGN.md` for the design -- section 3(d) was rewritten
this session and is where the numerics rule now lives.

```bash
python examples/oil_of_vitriol.py           # CHAIN 2, end to end, from NATIVE SULFUR
python validation/game_gates.py             # the four probes -- all unmoved

python -m chemsim.ui                        # the window
python -m pytest -q                         # 618 tests, ~12 min
python -m ruff check src tests examples validation tools
python validation/coverage.py               # 66/70, and which HALF fails
python examples/multistep_prep.py           # the flagship prep, end to end
python validation/robustness.py             # 15 OK, 6 REFUSED, 0 WRONG
python validation/wall_clock.py             # what an operation COSTS
python tools/build_element_data.py --dry-run   # the element lookups, audited
python tools/build_mineral_data.py --dry-run   # the mineral lookups, audited
```

**Both of last session's walls are down, neither needed hot-loop work, and
closing the second one found a third.** This session was engine work, which the
two before it deliberately were not.

---

# WHAT LANDED

**1. THE ROUND-OFF-SEEDED CATALYST IS FIXED.** The carrier-free lead chamber
went from **89% yield on 1.2e-4 mol of phantom NOx** to **0.00% on 1.6e-20**,
and `conservation_report` is now EMPTY rather than reporting on every run. The
diagnosis was confirmed by direct Jacobian measurement before anything was
changed: **-3.61e7 for NO, -3.95e7 for NO2 and H2SO4, -1.83e6 for water**, for
solid blocks holding NOTHING.

⚠ **AND THE PRECEDENT'S FIX WOULD HAVE BEEN THE WRONG ONE.** `_layer_gates`
used a smoothstep -- zero *and flat* at zero -- which is why it then needed
`LAYER_REABSORB` as a companion with strictly disjoint gates. A companion for
the SOLID gate would have had to sit opposite the PRECIPITATION branch, which is
ungated by design because anything can nucleate: exactly the overlapping-gate
arrangement that made the benzoic-acid acidification unsolvable. Only ONE term
may govern that block near zero, so the gate itself had to carry the derivative.

`SOLID_GATE_TIME` makes the gate's scale the DRIVING FORCE rather than a
constant -- `eps = tau * k_diss * excess`, a resistance-in-series form -- so the
empty-block slope collapses to exactly `1/tau` for EVERY species. **That
independence is the property**: the old knee got worse the more dilute a species
was, which is precisely why the most dilute one seeded the cycle.

⚠ **The value is a measurement.** The solid columns' largest entry reads
1.41e6 / 1.36e5 / 1.29e4 / 1.49e4 at tau = 1e-4 / 1e-3 / 1e-2 / 1e-1 -- it stops
shrinking at 1e-2 and 1e-1 is slightly WORSE, so 1e-2 is the least distortion at
which the gate has stopped dominating.

⚠ **IT CLOSED A SECOND ROW NOBODY HAD CONNECTED TO IT.** The chamber's carrier
nitrogen used to close ~0.5% out at a charge four orders LARGER, written up as
"a residual worth naming" rather than as a defect. It now closes to 1e-6 with
nothing in that panel touched -- which is the cleanest confirmation available
that the two were one defect.

**2. DECLARED RATE ORDERS, AND THE KERNEL NEEDED NOTHING.** `builder.to_arrays`
has always emitted `order` separately from `delta`; it simply never had anything
to put in it. So wall 2 was one field -- `ReactionTemplate.orders`, one exponent
per SMARTS reactant SLOT.

⚠ **A DECLARED ORDER MAY NOT BE REVERSIBLE, and it is REFUSED at construction.**
`detailed_balance` derives the reverse from `k_f/k_r = K(T)`, which holds only
because the exponents ARE the coefficients. An apparent order says the reaction
is not an elementary step, and a non-elementary step has no reverse to derive.
Negative orders are refused too (inhibition is a saturation term). ⚠ An order
*below 1* is a knee at zero concentration and is REPORTED rather than refused --
half-order rate laws are real.

**3. THE BURNER SHIPS AND CHAIN 2 BOTTOMS OUT IN NATIVE SULFUR.**
`reactions.sulfur_combustion()` declares `(1, 1, 0, 0, 0, 0, 0, 0, 0)`: eight
oxygens CONSUMED, one in the rate law. With O2 limiting the yield is
**100.000% at A = 1e8, 1e9, 1e10 and 1e11** -- the disqualifying A-dependence
(86.5% vs 96.4%) is gone. ⚠ **The failure mode at the slow end CHANGED, and that
is the real result**: the old form STALLED, this one is merely slow and FINISHES
given ten times as long.

⚠ **Both parameters are hand-authored and the rate law is APPARENT.** They are
BOUNDED, not fitted: `A = 1e10 L/(mol s)` is pinned to the order of the
gas-kinetic collision limit so it cannot be dialled to taste, leaving `Ea` as
the only freedom. **The cost is a soft ignition threshold -- 68% at 500 K,
more than real sulfur does below its ~523 K ignition point -- and it is
asserted rather than tuned away.** A sharper knee needs A = 1e14, a thousand
times the collision limit.

---

# ✔✔ THE WALL THIS SESSION FOUND -- **CLOSED 2026-08-23. WORK ORDER DISCHARGED.**

**690 K went 1.1e-01 -> 1.9e-11 created oxygen.** HANDOFF items 72-73 are the
record and `_dryout_gates` / `MOLE_FRACTION_DENOM` are the code. Two things below
turned out to be WRONG and are corrected here rather than left standing, because
the section is otherwise still the best statement of what the bug was:

⚠ **THE WORK ORDER'S PRESCRIPTION WAS WRONG.** "Make the three gates disjoint the
way `_layer_gates` made its two disjoint" closes the band (690 K -> 1.6e-13) and
**breaks a condenser**: disjoint halves are both zero AT the scale, and a
condenser is exactly the thing that comes to rest there. The head stalled at
9.998e-07 mol against the 1e-4 a working charge needs and **the reflux plateau
went 352.89 -> 370.39 K.** The gates had to stay COMPLEMENTARY; it was the mole-
fraction CLAMP, sharing their scale, that was the whole bug. **Whether a gate pair
should be disjoint or complementary depends on whether its dead zone is
survivable** -- `_layer_gates`'s halves oppose each other and its dead zone is
harmless; these two are one flux written twice and their dead zone stops the
flask changing phase at all.

⚠ **AND "730 K STAYS CLEAN" WAS NOT A PROPERTY TO PRESERVE.** It now reads
5.2e-06 where it read 2.0e-09. That is the depleted reactant, not the band -- with
O2 non-limiting the same flask reads 1.1e-12 -- and nudging the INERT nitrogen
charge by 0.5% swings it five orders of magnitude. Item 71's rule, biting a second
time on the numbers item 70 tabulated.

---

# ⚠⚠ THE WALL, AS IT WAS DIAGNOSED (kept for the diagnosis, not the prescription)

## A DRYOUT BAND, and the burner walked straight into it

Sulfur boils at 717.8 K, so a burn run near that holds only a TRACE of
condensate. If the trace lands inside `DRYOUT_MOLES` (1e-6 mol), **three** terms
overlap in `vessel_integrator.py`'s evaporation block:

    wet1     = N1 / (N1 + DRYOUT_MOLES)              gates layer 1's evaporation
    wet_all  = N_liq / (N_liq + DRYOUT_MOLES)        gates the DRY-FLASK branch
    x1       = nL1 / max(N1, DRYOUT_MOLES)           floors the mole fractions

`evap1` runs at `wet1` strength and `evap_dry` at `1 - wet_all`, so both are
active in the band -- and because `x1` is floored on the *same* scale, **inside
the band the mole fractions sum to LESS THAN ONE and every activity is
understated.** At N1 = 5.7e-7 they sum to 0.57.

**Measured**, `examples/oil_of_vitriol.py` panel 0b, O2 limiting, A = 1e10:

| T / K | liquid held | created O, relative | |
|---|---|---|---|
| 550 | 6.85e-03 mol | 1.8e-12 | |
| 650 | 1.52e-03 | 1.1e-09 | |
| **675** | **8.29e-07** | **2.3e-03** | IN BAND |
| **690** | **5.43e-07** | **1.1e-01** | **reads 111% yield** |
| 730 | 3.81e-07 | 2.0e-09 | |
| 900 | 6.86e-08 | 1.7e-08 | |

**It is a BAND, not a threshold** -- clean on both sides, wrong only inside --
which is the signature of two gates meeting rather than of one bad one.

### ⚠ THE DIAGNOSTIC IS WORTH MORE THAN THE MEASUREMENT, AND IT GENERALISES

The same burner shows a **1.7e-4 residual at 600 K**, where the flask holds
5.2e-3 mol and is nowhere near the band. That one is the ordinary
stiff-reactant-at-zero residual this project reports everywhere. **In a single
run the two are indistinguishable.** They are told apart by REFINING:

    600 K, round-off   atol 1e-9 1.70e-04 -> 1e-11 6.9e-12 -> 1e-14 -5.5e-14
                       60 chunks 4.79e-10
    690 K, the BAND    atol 1e-9 1.10e-01 -> 1e-11 5.0e-09 -> 1e-14  7.4e-04
                       60 chunks 5.25e-02

**A ROUND-OFF RESIDUAL CONVERGES UNDER REFINEMENT; A STRUCTURAL DEFECT DOES
NOT.** The band is non-monotone in `atol` and untouched by chunking. Both halves
are pinned in `tests/test_lead_chamber.py::
test_the_burner_must_not_be_run_INSIDE_the_dryout_band`, deliberately, so that
fixing it breaks a test and says what changed.

### ⚠ WHAT HAS ALREADY BEEN TRIED, SO DO NOT RE-TRY IT

**Lowering the mole-fraction floor alone MOVES the band, it does not remove
it.** Measured: with the floor at 1e-9 the 690 K case goes 1.1e-1 -> 1.4e-8 and
the atol=1e-12 pathology clears, but 700 K gets *worse* (2.9e-5 -> 3.0e-4); at
1e-12 the trouble reappears at 730 and 900 K. That is the same
relocate-the-fight signature `_layer_gates` recorded across its three attempts,
and it says the fix is DISJOINTNESS, not a better constant.

**So the work order is: make the three gates disjoint the way `_layer_gates`
made its two disjoint.** `grow` above a threshold, `drain`/dry below it, flat
where they meet, and the mole fractions NOT floored on the gating scale -- a
clamp that exists to avoid 0/0 must not double as a second gate.

⚠ **THE BLAST RADIUS IS THE WIDEST OF THE THREE KNEES, WHICH IS WHY IT WANTS ITS
OWN SESSION.** `avail` touched dissolution only. This touches EVERY evaporation:
every boiling point, every distillation, the reflux plateau, the azeotrope, the
steam distillation pair. The invariants table below is the contract and roughly
fifteen of its rows run through this code. Budget the full suite.

⚠ **IT IS ALREADY VISIBLE AND MUST STAY SO.** It is on `fragilities` (hence
`Vessel.integrability_report`) and not only on `diagnose`, because **the solve
SUCCEEDS** -- `diagnose` runs only on failure and would never be consulted. A
test asserts the channel names it.

---

# THE PROGRAMME  -- ⚠ SUPERSEDED BY `MILESTONES.md` (2026-08-22)

⚠ **The table below predates `data/catalog` and is kept only as the record of
what was planned before there was a coverage measurement.** `MILESTONES.md` is
the authority now, and it reorders this list on evidence:

* the dryout band is still first, and for a new reason -- it is in the
  EVAPORATION block, and M2 builds a distillation protocol on top of it;
* **rigs and fraction cuts in `World` were promoted above chain 1.** A still
  works but a CUT cannot be expressed -- `World` has no rig at all -- so a
  distillation runs to completion and its enrichment washes back out (measured:
  head x(EtOH) 0.655 -> 0.618 -> 0.500);
* **ionic precipitation was missing entirely and nobody had noticed.** No
  solubility product exists anywhere; `solidifies` is False for every ion, so
  AgCl cannot form. That is a missing MODEL, and the catalog had filed it as a
  missing template;
* the UNIFAC gap was promoted above templates because it is SILENT -- no
  decomposition sets gamma = 1, which asserts the phases do not separate;
* chain 1 and the template work moved down, because the catalog showed there is
  no lever: 61 routes are one class away, from 46 DIFFERENT classes, and the
  best single template unlocks 6 routes of 173.

Everything else in this file stands, including "THE WALL THIS SESSION FOUND"
above and the invariants table below, which is still the contract.

## The original table, for the record

| # | step | why, and what it costs |
|---|---|---|
| **1** | ⚠⚠ **THE DRYOUT BAND** | The wall above. A measured wrong answer (111% yield), a reproduction that runs in seconds, a convergence diagnostic that proves it structural, three overlapping gates already located, and one dead end already ruled out. Last live member of the `N/(N+eps)` class. |
| **2** | **CHAIN 1: aspirin from wintergreen** | Steps 1-3 are the flagship prep with different species. Salicylate's pKa (2.97) is in and the ion prices at Gf -410.3. Still needs an anhydride-FORMATION template and an anhydride-ACYLATION template. ⚠ **The forced dependency is the point and nothing should enforce it**: anhydride formation is reversible with WATER as the product, so you cannot make acetic anhydride in dilute vinegar -- the vinegar must be distilled first, and only Le Chatelier says so. And you NEED the anhydride because a phenol will not esterify with acetic acid in water. ⚠ The CARBONATE lines are NOT a data job -- see below. **Safe to build before item 1**: a non-catalytic network at ordinary temperatures is nowhere near the band. |
| 3 | **A curated overlay for aspirin and salicylic acid** | Both formation halves are Joback (`validation/game_gates.py` panel 3 names them), so the acetylation K is chain 1's weakest number. Joback's aspirin Tm is 433.1 K against a real ~408. Same overlay job `_CURATED_FUSION` already does for four solids. |
| 4 | **SOLID-PHASE REACTIONS** | Chain 2's green-vitriol seed is `FeSO4 -> Fe2O3 + SO3`, a dry decomposition with no liquid for the solid to dissolve into. The solid-basis formation data is curated and waiting. |
| 5 | **Dissociation as an equilibrium** | **M12 TOOK MOST OF THIS ITEM'S JUSTIFICATION AWAY, 2026-08-24.** The stiffness ratio was **7.05e21**, and it was quoted as all acid/base recombination -- water at **9.431e18** against the esterification's 1.157e-2. That 9.431e18 was a rate constant 9.4e7x the collision limit and is now capped at **1.0e11**, so the ratio is **8.6e12**: still stiff, no longer the largest number in the project by eight orders. The value integrating gives IS still the equilibrium value, and the five pH invariants are still the regression test and must come back IDENTICAL. It also still owns the 600 K residual -- the stiff-reactant-at-zero overshoot -- which M12 made MORE visible at the default rung, not less: the prep now creates 2.53e-05 mol of benzoyl there, converging to -4.4e-15 by rtol 1e-8. |
| 6 | A plot against time; a rig in the window; UNIFAC-LLE parameters | The old UI list, unchanged. |

⚠ **THE CARBONATE pKa LINES ARE NOT A ONE-LINE DATA JOB.**
`ion_thermochemistry` skips a pair whose ACID cannot be priced, and carbonic
acid cannot: Benson prices its formation half well (Gf -559.1) but no source has
a boiling point, because it decomposes rather than boiling, and the only melting
point on offer anywhere is **484.65 K from a crowd-sourced compilation, for a
species never isolated as a bulk solid**. The honest anchor is dissolved CO2,
and `CO2 + 2 H2O <=> HCO3- + H3O+` consumes TWO waters with delta_n = -1, which
breaks the delta_n = 0 convention the entire ion table rests on. Both pairs sit
in `_PAIRS` recognised and unpriced, with the reason on them.

---

# Traps this session paid for. The older list is in `HANDOFF.md`.

- ⚠⚠ **A ROUND-OFF RESIDUAL CONVERGES UNDER REFINEMENT; A STRUCTURAL DEFECT DOES
  NOT.** The single most useful thing this session produced. Two defects that
  are indistinguishable in one run separate immediately under an `atol` sweep or
  chunking, and non-monotonicity under refinement is itself the signal. Reach
  for this before theorising about any residual.
- ⚠ **THE FIX FOR A KNEE IS NOT ALWAYS THE FIX THAT WORKED ON ITS TWIN.** A
  smoothstep was right for the liquid layer and wrong for the solid gate,
  because what the companion term would have had to fight differs. **Check what
  the OTHER terms on that block are before copying a precedent** -- here,
  precipitation is ungated by design.
- ⚠ **A "LATENT" VERDICT IS ONLY AS GOOD AS THE PROBE.** `DRYOUT_MOLES` was
  measured and pronounced latent on a dry flask at 400 K holding 0.8 bar, which
  conserved matter to 3.5e-18. The same gate at 690 K with 7 bar and a
  condensing species creates 11% of its oxygen. **A gate's damage scales with
  what multiplies it**, and a gentle probe will report innocence.
- ⚠ **A CLAMP THAT EXISTS TO AVOID 0/0 MUST NOT DOUBLE AS A GATE.**
  `x1 = nL1 / max(N1, DRYOUT_MOLES)` is written as a division guard and behaves
  as a second shutdown, on the same scale as the first -- which is how mole
  fractions come to sum to 0.57.
- ⚠ **THE UNITS OF A NUMERICAL CONSTANT WILL TELL YOU WHAT IT MEANS.**
  `SOLID_GATE_TIME` was first written as a dimensionless "fraction"; working out
  that `eps = f * (mol/s)` forces `f` to be a TIME turned an arbitrary knob into
  the statement *no crop may dissolve faster than its own amount per tau*, which
  is what made a value defensible.
- Windows console is cp1252: a warning glyph inside a `print()` kills a script.
  Docstrings fine, printed text ASCII. (**Seven sessions running.** Not hit this
  session -- `!!` was used in every new printed panel.)

# Invariants that must not move

⚠ **ONE ROW MOVED 2026-08-23, and it moved because it was never measuring what
it claimed** -- the burner's O2-limiting residual, 730 K 2.0e-09 -> 5.2e-06. It is
the DEPLETED REACTANT and not the dryout band (O2 non-limiting: 1.1e-12), and its
default-tolerance value is set by where the solver lands: a 0.5% nudge to the
INERT nitrogen charge moves it between 2.5e-09 and 4.5e-04. **The dryout rows
below were replaced rather than retyped**, and the test now asserts convergence
instead of a value. This is item 71's rule a second time.

⚠ **Four rows MOVED the session before.** Three moved because a bug was fixed.
The fourth moved because it was never measuring what it claimed:

⚠⚠ **`test_a_vapour_edge_conserves_matter` ASSERTED A LUCKY SOLVER PATH.** It
bounded ethanol's closure at 1e-12 relative and its docstring claimed "machine
precision", on the strength of a run that happened to close to -4.3e-15.
Changing the solid gate moved the solver's path and it read -4.5e-11, which
looked like a regression and was not. **The convergence diagnostic settles it:**

    gate    atol 1e-9     atol 1e-11    atol 1e-13
    OLD     -4.293e-15     2.555e-11     3.494e-11
    NEW     -4.512e-11     2.556e-11     3.494e-11

**The two agree to four significant figures once refined**, and the new value is
insensitive to the gate's own constant across four decades -- so the residual is
the VAPOUR EDGE, not the gate. The bound is now 1e-9 relative with `abs=1e-12`
kept alongside it, because the absolute bound is the one that catches created
matter in a vessel holding nothing (water's 1.26e-6) and `approx` takes the
larger. **A tolerance tight enough to be luck is worse than no tolerance: it
fails on unrelated changes and says nothing when it passes.**

| | value |
|---|---|
| ⚠ **carrier-free chamber** | **0.00% yield; 1.6e-20 mol NOx** (was 89% on 1.2e-4 -- THE BUG, now fixed) |
| ⚠ **lead chamber, carrier N closure** | **100.0000%, report CLEAN** (was ~0.5% out and reported) |
| ⚠ **the burner, O2 limiting** | **100.000% at A = 1e8 to 1e11** (was 86.5-96.4%, A-dependent, and refused) |
| the burner, ignition | 0.00% at 298/400 K, 68.1% at 500 K, 100.00% at 550/600/650 K |
| ✔ **the dryout band -- CLOSED** | **1.9e-11 created O at 690 K with nothing else driven to zero** (was 1.1e-01) |
| ... a flask placed IN the band | conserves to **1e-21 mol**, 3 species x 5 holdings from 0.1x to 5x DRYOUT_MOLES |
| ... layer-1 mole fractions | sum to **1.0** at every holding (were 0.57 at 5.7e-7 mol) |
| ... `wet + dry`, single liquid | **exactly 1.0** -- a dead zone here stalls a condenser and costs 17 K of plateau |
| ⚠ **the burner's O2-limiting residual** | **NOT AN INVARIANT.** 690 K 2.9e-05, 730 K 5.2e-06 at default atol -- and an INERT N2 nudge of 0.5% swings it 2.5e-09 to 4.5e-04. Was "2.0e-09, clean". See below |
| ... and its convergence signature | 600 K 1.84e-04 -> 2.5e-14 under 60 chunks; 690 K 2.94e-05 -> 6.0e-10 at atol 1e-12 (the band went the WRONG way, to 7.4e-04) |
| solid-block Jacobian diagonal, empty | exactly 1/SOLID_GATE_TIME = 100 for every species |
| benzoic acid dissolved, sweep flask | 0.026826 mol at every tau, identical to 6 dp |
| a 1e-5 mol crop under water | dissolves to EXACTLY 0.0 (was -9.4e-10) |
| **every gaseous element reference state** | **Hf = Gf = 0.0 EXACTLY** (H2, N2, O2, F2, Cl2) |
| **Br2 / I2 / S8, ideal-gas Gf** | **+3.08 / +19.29 / +48.68 kJ/mol**, derived |
| **the reference-state cross-check** | **Br2 -0.05, I2 +0.14, S8 +3.05 kJ/mol** |
| **elements priced non-zero where 0 is exact** | **0 of 17** |
| **minerals pricing differently under the two providers** | **0 of 10** |
| **the fusion law against ionic solubility** | **0.0017x to 11.0x, 6445x spread, sign flips** |
| ⚠⚠ **a naive Ksp against ionic solubility** | **2.2e-25x and 6.8e-29x, sign flips (blue vitriol 76 mol/L).** 9 of 13 minerals return a NUMBER, not an error -- the cation is a SPECTATOR zero. 20 decades worse than the fusion law |
| ... the cation zero, as a bound | **46 decades** (Na+, ~262 kJ/mol), **97** (Ca2+, ~554) |
| ... the anion half, pKa vs aqueous | chloride **-111.73 vs -131.2 kJ/mol = 3.4 decades** |
| ... lattices that now REFUSE by name | **13 of 13** (was: 9 returned a float) |
| ... `chemicals` 1.5.2 for Na+ | Hfs/S0s/Hfl **None**; **Hfg +609343 J/mol** -- the GAS-PHASE cation, ~850 kJ/mol from aqueous, from a call that SUCCEEDS |
| **derived mineral Gf(s) vs CRC tabulated** | **within 0.25 kJ/mol on 5 of 6 anchors** |
| **the dilution gate** | **21.6 / 49.9 / 74.7% at 50 / 12 / 3 mol water** |
| **the stiffness ratio** | **7.05e21**; water recombination 9.431e18, esterification 1.157e-2 |
| **lead chamber, sealed** | **100.0% yield; 7 species, 4 reactions** |
| **lead chamber, carrier turnovers** | **80.3 on a 0.5 mmol charge** |
| **lead chamber, vented** | **22.4 / 23.4 / 41.7% at k_vent 1 / 10 / 1e3** -- non-monotone |
| **lead chamber at 650 K** | **carrier flips to NO by 100x; yield 94.1%** |
| the vent's worst raw gas excursion, open flask, 1 h | -4.8e-11 mol against 0.0227 charged |
| ⚠ **a vapour edge's ethanol closure** | **~3e-11 relative, CONVERGED** (the old 1e-12 bound was one lucky solver path -- see below) |
| a refluxing rig's conservation report | clean |
| ethanol under a hotplate | 351.466 K |
| a 50/50 pot's bubble point, air-saturated | 352.887 K |
| reflux holds that pot | 352.892 K at 1.01336 bar, boiling, indefinitely |
| a still finds the azeotrope | enrichment crosses 0 at x = 0.894, T min 351.2 K |
| ethanol/water azeotrope | x = 0.888, 351.17 K |
| robustness sweep | 15 OK, 6 REFUSED, 0 UNCLEAR, 0 WRONG |
| a chunked run, replayed from its script | agrees to 1e-9 |
| a chopped wait vs an unchopped one | same discovered instant to 1e-3 |
| the five pH values | 7.00 / 4.76 / 2.89 / 1.00 |
| benzoic acid in water, 298 K / 275 K | 3.26 / 1.62 g/L |
| a one-vessel rig | bit-identical to a lone vessel by default |
| **brine/toluene, K(Na+) organic/aqueous** | **6.155e-6** |
| layer permittivities, brine/toluene | 78.32 / 2.39, computed |
| Born term in pure water | exactly 0.0 at 275 / 298 / 330 / 373 K |
| Ka factor, water vs toluene | 1.000 vs 3.8e-11 |
| single-phase reduction with `lle=True` | BIT-IDENTICAL to `lle=False` |
| miscibility discrimination | 13/14 pairs (miss: water/n-butanol) |
| steam distillation, water + toluene / benzene | 358.31 / 345.52 K |
| extraction, 1 x 85 mL vs 3 x 28 mL | 92.4% -> 99.2% |
| event path vs direct path | agree to 1e-9 |
| ⚠ `examples/wait_until.py`: 340 K / boils / steadies | **t = 576.31 / 1353.13 / 1353.13 s** -- and this row was ALREADY STALE, not moved 2026-08-23. Proved by monkeypatching the old ramp+floor back under the same script: it gives 576.31 / 1353.14 / 1353.14, i.e. this session moved it by 0.00 s and 0.01 s (the root-solve tolerance) |
| save version | **5** (was 4; +Scenario.edges, SWAP_RECEIVER, SET_EDGE) |
| a distillation replayed from its script | **0.000e+00** mol disagreement across three receivers |
| **S5 -- the Jacobian step bound** | `factor_j <= max_i abs(y_i) / max(atol, abs(y_j))`. No constant in it |
| ... a flat column, 400 Jacobians | **inf** unbounded (it needs ~316 in ONE solve); **max abs(y)/atol** bounded, and its J column reads exactly 0 |
| ... the burner at rtol 1e-8 | **SO2 0.0160000000 in ~53 s** -- it RAISED after 52.7 s before. Slow and correct; the bound stops the NaN, not the struggle |
| ... the burner at the default | **0.0160000005** (O2-limited) and **0.1600000374** (O2-rich), bit-identical to unbounded |
| ⚠ ... what a single vessel WANTS | at most **1.490e+09** (`extraction`) against a bound of order 1e11-1e12: it never binds on a vessel |
| ⚠⚠ ... what a RIG wants | `fractional_distillation` **3.252e+12**, clamped in **232 of 1833** Jacobians -- so it DOES bind, and the row below is how that was judged |
| ⚠ ... and how the rig was judged | against a CONVERGED rtol 1e-8 run, where heart and tail are **bit-identical** bounded and unbounded. At the default neither is nearer; every difference **<= 1e-6 relative**, three decades under the audit's own 1e-3 quotable-digit band |
| ⚠ three cuts, VENTED, after the bound | **0.43671561 / 0.55620765 / 0.07016229 mol** (was 0.43671550 / 0.55620760 / 0.07016210). To the four figures the row above quotes, UNMOVED |
| ⚠ ... four of the five recorded triggers | **DO NOT REPRODUCE.** M6's kiln at 0.05 mol reads `p/K - 1 = -1.56e-04` where it raised; S4 changed `SolidStateArrays.units`, nothing was fixed |
| ⚠ three cuts by head temperature, VENTED | **0.4367 / 0.5562 / 0.0702 mol**, heart 0.459 mole fraction. Was 0.060/0.287/0.580 and heart 0.523 -- taken at **3.09 bar** on a SEALED rig, see below. Bands moved 300-366/366-374/374-500 -> 300-342/342-356/356-500 K |
| ⚠⚠ **a still with no open end** | **SEALED.** `fractional_distillation` t=100 s: **3.09 bar, pot 370.75 K** (was reported as a distillation); pot **548.15 K** once dry |
| ... the column, sealed, t=300 s | **2 plates 3.343 bar / 385.86 K; 8 plates 3.770 bar / 389.61 K** -- taller is HOTTER, which is why adding plates made the first attempt worse |
| ... the same column, condenser vented | **1.014 bar, pot 352.97 K** -- the reflux plateau, which is what a distillation sits on |
| ✔ **a plate column, 8 plates at R=5** | **heart 0.8544 mole fraction ethanol**, 0.2987 mol, 0.2552 mol EtOH = **12.8% of the 2 mol charged**. Target 0.85 **MET** |
| ... the total-reflux ladder | pot **0.492** -> 0.562, 0.611, 0.652, 0.687, 0.719, 0.747, 0.772, 0.794, head 0.812, condenser **0.828**; monotone, ~one theoretical stage per plate |
| ... purity is a PLATEAU not a peak | **0.845** in the first 50 s of take-off, **0.8538** after 2000 s; a longer cut reaches **46.5% recovery at 0.8535** |
| ... boilup is a plate-EFFICIENCY knob | **0.8538 at 250 W, 0.8486 at 500 W** (misses), and the two runs cost the same wall clock (403 vs 409 s) |
| ... the head across the whole cut | **351.186 -> 351.188 K.** In a good column the head does not move, so the band goes on the POT (353.08 -> 354.28 K) |
| ... its replay | **0.000e+00** mol across three receivers |
| ⚠ **temperature_steady on a rig vessel** | lifted (owner's own rhs): **TIMES OUT at 1200 s** on a column pinned at 351.22 K. Coupled: fires in **0.0 s**. FIXED |
| ⚠ column Jacobian column groups | **60 of 238** at 8 plates (52/136 at 2, 56/170 at 4) -- sparsity DOES pay on a banded chain, unlike the two-vessel rigs |
| ... a pre-warmed column (plates at 345 K) | flood **134.7 s vs 135.7 s** simulated -- the transient is the phase change, not the heat-up |
| a coupled wait vs an uncoupled one | head reaches 330 K on the rig; **never** on its own (times out at 298.15 K) |
| prep network size | 18 species, 15 reactions from 4 templates |
| ester selectivity, 340 K vs 510 K | 100.00% -> 6.18% |
| ether/ethylene ratio, 340 K vs 510 K | 5660 -> 11, falling monotonically |
| film / crust scale laws | 0.2154x and 0.2150x per decade |
| Benson vs Joback, 82 curated species | median 1.56 vs 2.82, mean 2.94 vs 6.54 |
| coverage audit | 66/70; baseline 64 with both new tiers off |
| multistep prep, crust on, two washes | 84.0% yield, 99.6% purity, 100.0000% closure |
| ... the CRUDE cake, as filtered | 97.5% purity at 86.0% yield |
| ... crystals left stuck to the pot | 0.0147 mol = 1.79 g = 7.9% of the crop |
| **M5 -- routes template-ready** | **25 / 173** (was 7; re-measured at the previous commit, not read off the stale report) |
| ... reaction classes covered | **29 / 212** (was 12 / 206; 6 classes GREW by the re-label) |
| ... templates in the project | **34** (8 library + 20 synthesis + 6 dissociation) |
| ... `examples/named_routes.py` | **17 routes end to end in 24 s** |
| Cannizzaro, 1 mol benzaldehyde | benzyl alcohol **0.4666** = benzoate **0.4666** exactly (two aldehyde slots) |
| p,p'-DDT from 1 mol chloral | **0.1667 mol = one sixth**; six isomers share the product |
| Haber-Bosch, 5 N2 + 15 H2 at 700 K | **7.63 mol NH3 = 76.3% of theoretical**, and LESS at 800 K |
| ethylene hydration, same template | **2.9% per pass gas / 99.7% liquid** at 570 K -- the standard state is the whole difference |
| toluene nitration, generations=3 | **18 species, 29 reactions**; 2,4,6-TNT is 15.3% of the toluene |
| sucrose inversion, 360 K / 1 h | **99.3%**, and it gives glucose AND fructose from one template |
| ⚠ mixed-standard-state reaction shift | **+323 kJ/mol** on `methyl oleate + glycerol -> monoolein + methanol`; now a NOTICE |
| ⚠ Joback vs ATCT on HOCl | **-211.3 vs -76.8 kJ/mol**, a 134.5 kJ/mol error that would have been silent |
| ⚠ Joback on triolein | Tb **1690 K**, Tc **4020 K**, omega **-0.64** -> refused by name, not by scipy |
| **M6 -- calcination, dH / dS at 298 K** | calcite **+179.19 kJ/mol, +160.25 J/(mol K)**; slaked lime **+108.47 / +143.62** |
| ... `Ea` DERIVED as `max(dH, 0)` | calcite **179.19 kJ/mol** vs experimental 170-200; reverse barrier **exactly 0** |
| ... the reverse rate constant | `A exp(-dS/R)` = **4.259e-4** and **3.150e-3** 1/(bar s), TEMPERATURE-INDEPENDENT |
| ... `K(T)` = P_ambient, i.e. the kiln | **1119 K** (literature ~1170) and **756 K** (~785); `dCp = 0` costs 30-50 K |
| ⚠⚠ **mass action on the solid amounts** | settled at `p/K` = **3.0863 vs n_A/n_B 3.0863** (1100 K) and **1.2139 vs 1.2139** (1200 K). BUILT, measured, REPLACED |
| ... sealed 1 L, 0.1 mol calcite | conversion **0.12 / 1.23 / 7.95 / 37.3%** at 900 / 1000 / 1100 / 1200 K; forward-only reads 100% at all four |
| ⚠ ... swept, 1 bar of air, 20 ks, CONVERGED | **1.30 / 6.54 / 13.97 / 43.53 / 99.75 / 100.00%** at 1000 / 1073 / 1100 / **1119** / 1150 / 1200 K, and p(CO2) lands on **K(T) exactly** below the threshold |
| ⚠⚠ ... the same run at the DEFAULT tolerance | **39.04%** at 1100 K, p(CO2) = 0. rtol 1e-6/atol 1e-9 is NOT converged for a vented kiln -- 2.6x in the answer, and the tight run is FASTER (1.4-3.3 s vs 5-13 s) |
| ... what an open flask does NOT do | below the threshold its CO2 sits at K(T) and is not swept: a vent only flows when the TOTAL beats ambient. Sweeping needs `Vessel.ingress` |
| ... the equilibrium is amount-INDEPENDENT | 0.05 / 0.2 / 0.8 mol charged -> `n_A/n_B` **5.30 / 24.33 / 102.62**, p(CO2) **0.727497 / 0.727507 / 0.727507 bar** |
| ... `RECOMBINATION_A` is a CLOCK | 0.1x / 1x / 10x -> sealed p(CO2) **3.7231 bar** at all three (6 figures) |
| ⚠⚠ **the constant is the REVERSE one** | declared FORWARD, green vitriol runs at **1.7e-13 1/s** and converts **0.00% in 20 ks at every temperature its thermodynamics allow** -- 13 decades. `A_fwd = A0 exp(dS/R)` |
| ... and calcination is unmoved by the correction | `A_fwd` comes back as **100000.34** against the 1e5 it was declared at -- 3 ppm |
| ... the four rows' time constants | **631 s** at 1200 K, **146 s** at 900, **25 s** at 1000, **44 s** at 450 -- three of the four calibrated against nothing |
| M6 -- `mineral_data` after the second push | **37 minerals**; FeO REFUSED on its crystal Cps, which CRC does not tabulate at all |
| ... chain 2's seed, 1000 K swept | `2 FeSO4 -> Fe2O3 + SO2 + SO3` complete in **~300 s**, ending at p(SO2) = p(SO3) = **0.5066 bar** (they share ambient exactly) |
| ... solvay step 3, 450 K swept | `2 NaHCO3 -> Na2CO3 + CO2 + H2O` complete in under **2000 s**; derived threshold **392 K** against the catalog's own `calciner, 450 K` |
| ... a two-gas threshold is NOT `K = P` | green vitriol **874 K** against the **918 K** where K reaches 1 bar^2 |
| ... the sign-switch kink, parked at equilibrium | 2,000,000 s in **0.2 s** wall, `p/K - 1` = **+3.8e-10**, at `units_f/units_r` up to **129.5** |
| ... a kiln's fuel bill | **-14.374 W** solid-state against **+14.374 W** wall at 1200 K, 0.1 mol |
| ... carbonation, EMERGENT (nothing declares it) | 0.02 mol slaked lime + CO2, 700 K, 50 ks -> **4.391e-3 mol limestone**; calcium exact to 1e-9 |
| ... `mineral_data` | **25 minerals, 23 with `Cp_solid` and `Vm_solid`**; calcite 83.5 J/(mol K) and 0.036932 L/mol |
| ⚠ a zero Jacobian column in a sealed flask | N2/O2 in the network but absent: 0.05 mol **RAISES** (CO2 to -2.572 mol); 0.1 / 0.4 / 1.0 mol fine. Pre-existing, refuses loudly |
| `tests/test_solid_state.py` | **31 tests in 23 s** |
| **M6 -- routes template-ready** | **26 / 173** (was 25); `lime-cycle` is COMPLETE end to end from limestone |
| ... reaction classes covered | **32 / 214** (was 29 / 212); `calcination`, `lime-slaking`, `solid-carbonation` |
| ... templates in the project | **34, UNCHANGED** -- M6 covered three classes with a TERM and no new template |
| ⚠ classes split by M6's row reading | `hydration` -> `lime-slaking` + `carbonyl-hydration`; `carbonation` -> `solid-carbonation` + `basic-carbonate-precipitation`. 5 rows re-labelled |
| the whole suite | **750 tests in 11:19** (was 727 in 11:34) |
| **S1 -- THE GATE: a flask with NO iron** | `N2 + 3 H2` at 700 K, 600 s -> **0.00000000 mol NH3. EXACTLY zero, not small** |
| ... the same flask with 0.1 mol of iron | **0.15853790 mol = 31.71%** of theoretical; 1e-6 mol gives 0.00004368, 1e-3 gives 0.03715817 |
| ... `A_cat * SOLID_CATALYST_REFERENCE` | **1e7 x 0.1 == 1e6**, exactly equal to the folded template's `A`. Arithmetic, not a run |
| ⚠ ... and the reference charge is NOT bit-exact | a VENTED flask differs by **+0.086%**, and a vented comparison is not a comparison. SEALED with the flask enlarged by the iron's own 0.0007096 L: **-4.6e-11 mol**. The residual is a crystal DISPLACING GAS |
| ... `examples/named_routes.py` haber-bosch | **7.6310 mol = 76.3%**, UNMOVED, now with iron in the flask |
| ⚠⚠ ... the catalyst is a CONSTANT OF THE MOTION | charged 1e-12 / 0.1 / 1.0 mol -> drift **+0.000e+00** at all three. Not "conserved to 1e-12" -- unchanged, bit for bit. `delta` column is identically zero |
| ⚠⚠ ... what a "solid" phase LABEL would cost | dH **-22.889**, dG **-99.722** kJ/mol, K(500 K) **x 2.616e10**. `reaction_deltas` shifts anything that is not "gas" onto the pure-liquid basis -- so PHASE_INDEX keeps two entries |
| ... no site balance, as an INITIAL RATE | 0.01 / 0.1 / 1.0 mol of iron -> **exactly 10.0x** each step (1e-9). ⚠ As a YIELD after 1 s it reads **9.75** -- that 2.5% is depletion, not saturation |
| S1 -- roasting, sealed 1 L, 0.1 mol ZnS | **1.53%** in 20 ks; O2 available **2.296 mmol** against 150 needed. The stall is the mechanic |
| ... blown (0.25 mmol O2/s), walled | **78.26%** in 1800 s at 1100 K; zinc closure **0.100000000000** |
| ⚠ ... blown and INSULATED -- autothermal | **100.00%** and the bed heats itself **1100 -> 1908.6 K**. Nothing declares this; -882.7 kJ/mol does it |
| ... two ores, one blast | 0.05 ZnS + 0.05 PbS -> **0.039131 mol each**; both closures exact to 1e-12 |
| ... the four rows' dH / ln K at `T_run` | **-882.7 / +78.8**, **-830.9 / +70.6**, **-802.1 / +67.6** at 1100 K; **-658.9 / +70.8** at 900 K. Bar is +20, tightest clears by **20.7 decades** |
| ... `ROASTING_A`, and what pins it | **3.21e6 L/(mol s)** = **3.2e-5** of the collision limit; it is the constant a 1800 s roast at 1100 K in 1 bar of air implies (`k` = 0.242) |
| ⚠⚠ ... the shared clock is PARTLY REFUTED | cinnabar's own 900 K retort gives **tau 56,358 s** against a zinc roaster's **1,800 s** -- 31x slower at its own temperature |
| ⚠⚠ ... and Evans-Polanyi gets it BACKWARDS | sphalerite is the MOST exothermic (-882.7) and needs the HOTTEST furnace (1100 K vs cinnabar's 900). So `alpha` is 0 and the ordering is not claimed |
| ⚠ ... the default tolerance again | sealed roast at rtol 1e-6: S closure **1.3e-6** off and **19.94 s** wall; at 1e-8: **9.4e-11** and **3.67 s**. The tight run is 5.4x FASTER |
| S1 -- `mineral_data` | **40 entries** (was 37); iron / nickel / copper all price at `Hf = Gf = 0.0` **EXACTLY**, and a non-zero result is REFUSED as an allotrope mismatch |
| **S1 -- routes template-ready** | **27 / 173** (was 26). ⚠ The one added is `pyrite-roasting`, which DOES NOT RUN -- pyrite has `Hfs` in WEBBOOK and `S0s` in nothing |
| ... reaction classes covered | **33 / 215** (was 32 / 214); `roasting` |
| ⚠⚠ ... and the class had to be SPLIT | crediting `roasting` unsplit made `mercury-from-cinnabar` template-ready on a mechanism that makes the OXIDE, not the metal. Re-labelled `roasting-to-metal` |
| ... honest summary of the coverage gain | **+1 class, +1 template-ready route, ZERO new routes that run end to end** |
| ... templates in the project | **34, UNCHANGED** -- five gained a declared catalyst; no new template |
| ⚠ ... `ammonia_synthesis_rev` ceiling crossing | **1335.1 K**, UNMOVED, but only because `rate_ceiling.apparent_A` undoes the catalyst's units. Raw it reads 1178.1 K, which is a units error |
| `tests/test_surface.py` | **38 tests in 12 s** |
| `examples/roasting_and_the_catalyst_gate.py` | **5 panels in 11.6 s** |
| **THE TOLERANCE AUDIT -- 11 examples swept, default vs rtol 1e-8** | **ZERO** now print a quotable digit that moves. 5 move below 0.1%, 6 are byte-identical |
| ⚠ ... `lime_cycle` and `roasting_and_the_catalyst_gate` | **identical, speedup 1.00** -- they pass their own rtol 1e-8, so the harness patches DEFAULTS and cannot touch them. That is the audit's self-check |
| ⚠⚠ ... the ONE real move it found | `workshop` Part 2, the latent-heat plateau: at t = 800 s the default reads **T 389.50 K / solid 2.0000** and converged reads **388.38 K / 1.9656**. The default says melting has not started; it has, and the flask is 1.1 K cooler because the melt absorbs latent heat |
| ... and fixing it cost 1 second | Part 2 alone tightened: the example goes **8.1 s -> 9.1 s**, not 8.1 -> 58.9. The 7.2x was the OTHER panels, which move by 4e-4 and are left alone |
| ⚠⚠ ... `oil_of_vitriol` CANNOT BE SWEPT | **RAISES** at rtol 1e-8 in `burn(690 K, s8=0.002, o2=0.10)` -- `lu_factor` gets a NaN Jacobian after **50.7 s** of thrashing |
| ... and its numbers are CONFIRMED, not suspect | SO2 = **0.016000** at the default, **0.016000** at rtol 1e-8 with a 1e-9 mol trace of SO2 charged, **0.016001** with 1e-6 mol, **0.016000** at rtol 1e-7 |
| **S3 -- reaction classes covered** | **35 / 218** (was 33 / 215); `thermal-decomposition` split into four mechanisms, NO engine work |
| ... covered steps | **97 / 377** (was 95) |
| **S3 -- routes template-ready** | **27 / 173, UNCHANGED.** Predicted before crediting and then measured: all four affected routes are blocked on a SECOND uncovered class |
| ⚠ ... what DID move | `solvay-process` and `vitriol-distillation` went from two classes away to ONE. Routes one-class-away **58 -> 60**, from **44 -> 46** distinct classes, and `hydrolysis` is now greedy **rank 4 (+2 routes)** |
| ⚠⚠ ... the LATENT false credit | `sulfate-thermal-decomposition` is credited and `vitriol-distillation` step 1 still reads `-> iron-ii-OXIDE`, where the declaration makes HEMATITE. Inert only because step 2 `hydrolysis` is uncovered. **Crediting `hydrolysis` trips it** |
| ⚠⚠ ... and how near that is | `hydrolysis` unlocks **exactly ONE route alone, and it is `vitriol-distillation`**. The whole standalone payoff of the 4th-ranked template is the landmine route |
| ⚠⚠ **S3 -- the COVERAGE REPORT was not byte-stable** | `sorted(covered, ...)` sorted a SET with no tie-break: **17 lines of pure `PYTHONHASHSEED` noise per regeneration, every number identical.** Fixed in one line |
| ⚠⚠ **S3 -- `ROUTE_INDEX.md` was STALE BY THREE MILESTONES** | not regenerated since the **initial commit**, while `route_steps.psv` was re-labelled by M5, M6 and S1. Regenerating moved **21 labels: 11 M5, 5 M6, 1 S1, 4 S3**. No audit reads it, so it broke nothing and warned nobody |
| ... and verified S2's way | **byte-identical across `PYTHONHASHSEED=0` and `=1`**. The only unstable site; the greedy `max` already had a `c` tie-break |
| ... templates in the project | **34, UNCHANGED** -- S3 added no template and no engine code |
| **S4 -- the RETORT, sealed 10 L / pure O2 / 0.02 mol cinnabar / 900 K** | **0.020000000000 mol Hg and 0.020000000000 mol SO2 on 0.020000 mol O2 consumed.** `HgS + O2 -> Hg + SO2`, the catalog row, from a 2:3:2:2 and a 2:2:1 that do not mention each other |
| ⚠ ... the montroydite that carries it | **8e-7 mol at the start, 3.4e-8 by 20 ks** -- rate x clock, never 4e-5 of the charge. Its clock at 900 K is **0.2405 s** against the roast's **5,918 s** |
| ⚠⚠ ... the two clocks CROSS at | **611.7 K** under 1 bar of O2 (304.4 kJ/mol DERIVED against 150 DECLARED). Nothing gates on temperature anywhere |
| ⚠ ... the oxide's share of the mercury released | **2.0e-6 / 4.3e-4 / 1.9e-2 / 0.341 / 0.913** at 900 / 773 / 700 / 650 / 600 K |
| ... cool the retort to 400 K | **97.9%** of the mercury condenses into the liquid block |
| ⚠⚠ ... and NO oxide re-forms at 400 K | **289 K below its own threshold**, in a flask full of Hg vapour and O2. There is none left to grow ON -- the nucleation gap, as a modelled bound |
| ⚠⚠ **S4 -- a row with NO solid product BROKE `units_rev`** | sealed 1 L, 0.5 mol montroydite, 900 K: **RAISES `array must not contain infs or NaNs`** once Q crosses K. The minimum over an empty set is `+inf`, times a negative affinity |
| ⚠ ... and the failure had a CHARGE threshold too | **0.05 mol in the same flask is clean** -- Q never reaches K -- and the small charge is the one an example would have been written with |
| ... fixed, and the sealed 0.5 mol run now | stalls at **71.8%** with **Q = 9764.8 vs K = 9764.8 bar^3**; identical at 60 s and 6000 s |
| ... the four pre-S4 solid-state rows | **bit-for-bit UNMOVED** by the fallback (both sides carry a crystal), pinned by a test |
| **S4 -- mercury in `element_data`** | **Hf +61.40, Gf +31.853 kJ/mol**, reference phase `'l'`. Removed from `LATTICE_ELEMENTS`; `REFERENCE_SMILES['Hg'] = '[Hg]'` |
| ⚠ ... its Cp is EXACT, not a fit | **5R/2 = 20.786 J/(mol K)** at every temperature; JANAF returns it to four figures. The only non-fitted Cp in that table besides the gaseous zeros |
| ⚠ ... the reference-state cross-check | **+0.012 kJ/mol** -- the TIGHTEST of the four (Br2 -0.053, I2 +0.139, S8 +3.052) |
| ⚠⚠ ... and Lee-Kesler had to go | over a liquid METAL it reads **38.3 kPa at 523 K against CRC's 10.0 (3.8x)** while matching at Tb to five figures, because it is ANCHORED there. Curated NIST Antoine: within **2%** of CRC over five decades; residual **+2.808 -> +0.012** |
| ⚠ ... and `Hvap` follows the curve the engine EVALUATES | **59.444 kJ/mol** by Clausius-Clapeyron on the curated Antoine, against Lee-Kesler's 57.344 and CRC's measured **59.11**. The generator's "cannot disagree" invariant kept, not traded |
| ⚠⚠ **S4 -- `CURATED_FORMATION` falsely refused CRC's own row** | it is a PREFIX MATCH ON PROSE: a GASEOUS reference state passes, a CONDENSED one says "Hf and S0 both from CRC ..." and read as an ESTIMATE. **Would have refused Br2, I2 and S8 identically** |
| ⚠⚠ **S4 -- `rate_ceiling` could not see `SOLID_STATE_REACTIONS`** | its panels walk `net.reactions` and those rows never become one, while its summary claims "nothing approaches the unimolecular ceiling". Fourth panel added |
| ... what the fourth panel says | at 298 K the claim HOLDS by 26 decades. Hot: **oxide-thermal-decomposition 1.93e18 1/s, crosses 1e14 at 3710 K -- INSIDE the RHS's 5000 K clamp**; sulfate 7543 K; bicarbonate 75,136 K; the two calcination rows never |
| **S4 -- routes template-ready** | **28 / 173** (was 27). `mercury-from-cinnabar`, a ONE-STEP route -- predicted before crediting, then measured -- and unlike `pyrite-roasting` it RUNS |
| ... reaction classes covered | **36 / 218** (was 35 / 218); `roasting-to-metal`, credited to an EMERGENT pair of TERMS |
| ⚠⚠ ... the re-label was NOT reversed, and both ways were measured | keep: **36/218, 28 routes**. Fold back into `roasting`: **35/217, 28 routes**. Routes identical, so the choice is only what the class column SAYS |
| ... covered steps | **98 / 377** (was 97) |
| ... the species line | **refused 466 -> 465, measured 141 -> 142** -- one species, mercury. S3's byte-stability fix held: EVERY changed line is a real consequence, no noise |
| ... routes one class away | **60 -> 59**, from **46 -> 45** distinct classes |
| ⚠ ... a route that is not this one | **`castner-kellner` became species-ready AND fully sourced** (48 -> 49, 4 -> 5). Curating one element paid where nobody was looking |
| ⚠⚠ **S4 -- `species-ready` IS BLIND TO `mineral_data`** | it asks the plain provider, which REFUSES a lattice by name. Recorded as **14 routes**, 49/173 where the honest number is at most 63. ⚠⚠ **BOTH NUMBERS ARE WRONG -- see the S6 rows below** |
| ... which routes | 2-ethylhexanol, aniline, copper-smelting, deacon, fischer-tropsch, **haber-bosch**, hydrogenation-margarine, mercury-from-cinnabar, **methanol-synthesis**, nylon66, phenacetin, steam-reforming, vermilion, water-gas-shift -- **plus `lime-cycle`**, which M6 declared complete end to end. ⚠ `lime-cycle` is named here and ABSENT from the fourteen; that contradiction was the tell |
| ⚠⚠ **S6 -- the gap CLOSED, and it is 16 not 14** | `_mineral_fallback` + a `mineral` tier in `catalog_coverage.py`. **species-ready 49 -> 65**, fully-sourced **5 -> 14**, resolve 1118 -> 1137, refused 465 -> 446. **No `src/` file touched, no chemistry moved** |
| ⚠⚠ ... why the recorded 14 was wrong | it matched the catalog SMILES to the `by_lattice` key as a **RAW STRING**, and the catalog spells salts in a different fragment order: `[Ca+2].[O-]C([O-])=O` vs `O=C([O-])[O-].[Ca+2]`. Raw **14**, sorted-ion-tuple **15**, **canonical 16** |
| ⚠ ... and canonical is what the ENGINE does | `network/builder.py` line 320 rebuilds every input SMILES through `Molecule.from_smiles` before the species list exists. **Verified, not inferred: all 19 rescued minerals charged into a real `Vessel` solid block, 19/19 at their full 0.02 mol** |
| ⚠⚠ ... the rule is a FALLBACK, never an override | 36 catalog compounds sit on a mineral lattice but **17 already resolve as `ion`**. Labelling `sodium-chloride` a mineral would DOWNGRADE a two-phase species to one phase. Fires only after all three providers refuse |
| ... so the UNIFAC count | **836, UNCHANGED, by design** -- every rescued species was already refused, and a lattice cannot enter a liquid mixture anyway |
| ⚠⚠ **S6 -- THE COLUMN NOBODY COMPUTED: the INTERSECTION** | species-ready **65**, template-ready **28**, **BOTH 17**. The three answer INDEPENDENT questions and the smallest does NOT bound the others. **11 template-ready routes have a refused species and cannot run** -- `pyrite-roasting`, `tnt-route`, `superphosphate` +8 |
| ⚠ ... and it re-prices S6 itself | intersection **without** the mineral tier **12**, **with** it **17**. The milestone that moved NO template-ready route moved runnable **+5**. Curating a species and writing a template are the SAME axis here |
| ⚠⚠ ... and the WORK QUEUE was ranked on the overstated column | re-ranked by RUNNABLE: `isomerisation` 3/**2**, `crosslinking` 2/**2**, `electro-organic-coupling` 2/**2**, `electrolysis`(=M8) 3/**1**, **`catalytic-air-oxidation` 3/0 -- greedy row 3, worth ZERO**. Both tables now carry a generated RUNNABLE column |
| ⚠ ... one scoping question, NOT an assumption | `electro-organic-coupling` (`kolbe-electrolysis`, `adiponitrile-route`) is electrochemistry too and M8's brief names only `electrolysis`. **If one milestone covers both: +5 unlocked / +3 runnable**, back to the top |
| ⚠ ... and 17 is an UPPER BOUND, not a count | a class is credited when a template would fire on the right substrate at all. `pyrite-roasting` is the standing proof that is not the same as running |
| ⚠⚠ **S6 -- the TRAJECTORY, measured** | template-ready **25 at M5 -> 28 now**: S1 +1, S3 +0, S4 +1, S5 +0, S6 +0. **Six sessions, +3 routes.** Right work, wrong scoreboard -- and the content queue is untouched since M5 |
| ⚠ ... and `template-ready` | **28 / 173, UNCHANGED.** None of the 16 becomes template-ready; a mineral resolves **as a crystal** and still cannot dissolve. Template-readiness is still the binding constraint |
| ⚠ **S6 -- the NEXT gap, same shape, now measured** | **45 compounds refused as a bare ELEMENT block 15 routes and nothing else.** Leverage: `cobalt` **+3**, then `carbon-graphite` / `platinum` / `silver` at **+2** each |
| ⚠ ... and it has a LAYERING question in front of it | `element_data.REFERENCE_STATES` already has S0 for Zn(s)/Ag(s)/C(graphite) but with **`smiles=None`** -- a SOLID reference state had nowhere to live until the solid block existed. Mercury resolves only because its state is LIQUID. **A metal is not a mineral** |
| ⚠⚠ ... and it is the OPPOSITE shape to `pyrite-roasting` | pyrite reads template-ready and does NOT run; `mercury-from-cinnabar` reads species-unready and DOES. Two columns, two directions of error, neither a bug in the engine |
| ... NOT FIXED by S4, deliberately | it redefines a PUBLISHED column, so it owed the "which routes does it move" check and a verification pass. **S6 ran both** -- and the check is what caught that the recorded 14 was itself wrong |
| ... `ROUTE_INDEX.md` | **unchanged** -- no row was re-labelled |
| ... templates in the project | **34, UNCHANGED** -- two curated declarations, no template, no new term |
| ⚠ ... liquid mercury is HELD IDEAL | **99.85%.** A metal has no UNIFAC groups so its gamma is DECLARED 1. Visible cost: O2 and SO2 dissolve in the pool on Henry constants measured IN WATER -- **0.14% of the SO2** |
| `tests/test_mercury_retort.py` | **14 tests in 4.2 s** |
| **the whole suite** | **815 passed in 11:50** -- and this is the first MEASURED green number since S1's last fix (which left it at 796 passed / 1 failed and never re-run) |
| ⚠ `COVERAGE_REPORT.md` re-verified S3's way | **byte-identical across `PYTHONHASHSEED=0`, `=1` and unseeded** |
| `examples/mercury_retort.py` | **6 panels in 4.2 s** |
| **S4 -- THE TOLERANCE AUDIT RE-RUN, 12 examples** | **S2's finding UNMOVED: NO example prints a quotable digit that moves.** 5 move below 0.1% (identical list to S2), **7 are byte-identical** (was 6; `mercury_retort` joins them) |
| ⚠ ... the three self-check examples | `lime_cycle` **1.00**, `roasting_and_the_catalyst_gate` **0.99**, `mercury_retort` **1.00** -- all three OUTPUT IDENTICAL, which is what says the harness's default-rebinding still cannot touch an example that passes its own rtol |
| ⚠ ... and ONE COUNTER MOVED, which is JITTER and not a finding | "tight is faster in **1 of 12**, worst 7.1x" against S2's "**2 of 11**, worst 7.2x". The example that left the FASTER column is a self-check one landing at 0.99 instead of 1.00 -- its OUTPUT is identical by construction, so the counter is measuring wall clock on a run that did not change. ⚠ Do not read that 2 -> 1 as a regression |
| ... `oil_of_vitriol` | **STILL NOT SWEPT**, unchanged: RAISES at rtol 1e-8, numbers CONFIRMED correct |
| ⚠⚠ ... so the zero-column trap has a SECOND trigger | not only "a species absent from a sealed flask" but "a TIGHT TOLERANCE on a flask holding a trace". Same NaN, same fix, same diagnostic |
| ⚠⚠ ... and "THE TIGHT RUN IS ALSO FASTER" DOES NOT GENERALISE | faster in **2 of 11**, SLOWER in **9**, worst **7.2x**. It held for M6's vented kiln and S1's roast -- a stiff vent fed by slow chemistry -- and nowhere else. Tightening usually COSTS time |
| ⚠ ... and the audit's own first version manufactured a finding | it reported `wait_until` moving **12.5%**, and that was `0.07 s of wall` against `0.08 s of wall`. Real worst move **1.04e-4**. A wall clock is now excised as a TOKEN, not by dropping the line -- which also stops it hiding `lime_cycle`'s `±14.374 W wall` heat flux |
| the whole suite | **797 tests in 11:50** -- ran **796 passed / 1 failed**, and the failure was real |
| ⚠ ... the one thing the suite caught | `test_every_mineral_records_the_ions_it_dissolves_into` asserted `rec.ions` for EVERY row, and a METAL has none. Narrowed to exempt a one-element row priced at `Hf = Gf = 0`, so it still catches a salt that lost its ions -- verified against three simulated mistakes, all three CAUGHT |
| ⚠ ... and the full suite has NOT been re-run since that fix | the fixed file passes in a targeted run (79 tests with `test_surface.py`, 13 s). Re-run the suite before quoting a green number |

⚠ **The prep's numbers have NOT been re-measured for three sessions.** The suite
pins them and `tests/test_prep_side_products.py` passes. Re-run
`examples/multistep_prep.py` before quoting the yield again.

⚠⚠ **AND THAT WARNING WAS UNDERSTATED -- `wait_until.py`'s three rows turned out
to be stale too, by 60% on one of them, while its test passed the whole time.**
The tests pin these numbers at tolerances far looser than the digits quoted here
(the reflux plateau is asserted at `abs=2.0` K against a value written to three
decimals), so **a green suite is not evidence that a row in this table still
holds.** The technique that settles it cheaply, and it should be the habit:
`_dryout_gates` and `MOLE_FRACTION_DENOM` are resolved from module globals inside
the RHS, so the previous behaviour can be **monkeypatched back at runtime** and
the same script run twice. No file edit, so no half-reverted state, and the
answer is a difference rather than a recollection.

⚠ These rows WERE re-measured to their quoted digits on 2026-08-23 and are
unmoved: reflux plateau **352.892 K at 1.01336 bar**, steam distillation
**358.31 / 345.52 K**, the ethanol/water azeotrope **351.17 K**. `bubble_point`,
`volatile_pressure` and `is_boiling` could not have moved by construction --
they run on `equilibrium_pressures`, whose own `wet` ramp deliberately SURVIVED
this session (its docstring says why, and why it must not be "fixed" to match).

## ⚠⚠ M8 ADDED SEVEN ROWS, AND THE FIRST IS THE ONE THAT PROTECTS EVERY OTHER ROW ABOVE

**A network built without `cell_potential` is BIT-IDENTICAL to the one this
project built before M8.** Not close — identical, because `reaction_deltas`
skips the term on a falsy `electrical_work` and every non-electrode template
leaves it at exactly `0.0`. Verified against the EXAMPLE SET rather than argued:
all 14 of `esterification`, `thermochemistry`, `competing_pathways`, `vessel`,
`activity`, `extraction`, `multistep_prep`, `wait_until`, `workshop`,
`lime_cycle`, `mercury_retort`, `roasting_and_the_catalyst_gate`, `named_routes`
and `oil_of_vitriol` come out byte-identical apart from RDKit log timestamps and
two wall-clock readings. ⚠ S5's lesson is why the check was run this way: a
four-run sweep is not the example set.

| row | value | how it is pinned |
|---|---|---|
| **water splitting E_dec** | **1.441 V** (book 1.229) | `validation/cell_potentials.py` panel 1; `tests/test_electrochemistry.py` at `abs < 0.25` |
| **brine E_dec** | **2.362 V** (book 2.186) | same. ⚠ Always HIGHER than the book, every cell, and the test asserts the sign |
| **bromide E_dec** | **2.061 V** (book 1.894) | same |
| **the coupling `2 AN + H2 -> ADN`** | **−171.7 kJ/mol** | downhill, which is why it carries `electrons=0` |
| **the whole ADN cell** | **+212.7 kJ/mol**, E_dec 0.551 V | `cell_potentials.py` panel 4 |
| **k(brine)/k(water)** | **4.76e+17 at 2.5 V, 5.94 at 3.0, 1.00 at 4.0** | pinned as a LIMIT, not a target |
| **brine cell, 1 h, 0.20 mol NaCl** | 2.5 V: **0.0177 mol Cl2 / 8.9e-19 O2**; 4.0 V: 0.0169 / **0.53** | `examples/electrolysis_cell.py` panel 2 |

⚠ **THE dS COLUMN IS NOT AN INVARIANT AND MUST NOT BE QUOTED.** `cell_potentials.py`
panel 2 reports the brine cell's dS out by **−591 J/(mol K)** and bromide's by
−738 against the aqueous convention, which REVERSES the sign of dE/dT. The cause
is pre-existing and is named there: this project's ions are derived from pKa
against its own water, and its own water is priced on the ideal-gas basis, so the
offset cancels for a reaction that conserves water and every cell reaction here
does not. **E_dec at 298 K is quotable. Its temperature derivative is not, and
neither is a cell's HEAT** — `to_arrays` takes its enthalpy from the same dH.

⚠ **AND THE SELECTIVITY ROW IS A LIMIT, NOT AN ACHIEVEMENT.** It records that
this engine has NO CURRENT BUDGET: two electrode reactions in one cell divide
nothing, so both run at full rate and activation selectivity washes out as the
barrier floors at zero. If a later milestone makes the 4.0 V ratio hold,
`test_the_activation_selectivity_washes_out_at_high_voltage` SHOULD fail — and
should then be rewritten, not deleted.

⚠ **`A` FOR AN ELECTRODE TEMPLATE IS A CURRENT, NOT A COLLISION FREQUENCY**, and
the solver is what said so: at `1e10` a cell at 3.0 V ate 0.2 mol of chloride in
a nanosecond and `Vessel.run` died after 4.2e-09 s of 3600. `5e-8 = j0 * a /
(n F)` comes back out as 1e-2 A at unit concentrations. The test pins the ORDER
of magnitude (`1e-9 < A < 1e-6`), not the digits.

## S7 — the four inorganic gas processes, and the corpus checks that found them

⚠ **EVERY ROW BELOW CAME OUT OF A REAL `Vessel`**, not off a table:
`validation/gas_processes.py` is the standing audit and
`tests/test_gas_processes.py` (19 tests) is the pin.

| row | value | how it is pinned |
|---|---|---|
| **water-gas shift, 1 h, 0.10 mol CO** | **10.4% at 500 K, 81.3% at 620 K, 73.3% at 700, 55.6% at 900** | `gas_processes.py` panel 1; the test asserts the SHAPE (rate-limited cold, ceiling-limited hot), not the digits |
| **steam reforming, 1 h, 0.25 mol CH4** | **0.01% at 700 K, 6.3% at 900, 18.6% at 1100, 36.1% at 1300** | panel 2; test asserts `>0.2499 mol` left at 700 K and `<0.17` at 1300 |
| ⚠ ... and the SAME 1100 K flask, thinned | **18.6% at 54 bar -> 73.5% at 0.63 bar** | panel 2; two moles in and four out, the one gas equilibrium here that pressure HURTS |
| **Deacon, 0.40 mol HCl** | 10 s / 1 h: **14.8/70.7% at 400 K, 90.6/91.2% at 600, 84.6/84.6% at 700** | panel 3. The two columns agreeing from 700 K up is the pin, not the value |
| **Claus, 0.20 mol H2S at 1100 K** | **50.0% at 0.05 mol O2, 100.0% at 0.10, 98.2% at 0.15, 93.7% at 0.30** | panel 4; the peak at the stoichiometric rate is the assertion |
| ⚠ ... and the Claus sulfur closure | **0.200000017 mol against 0.2** on the oxygen-starved row only — 8.5e-08 relative at rtol 1e-08 | the projection residual times a stoichiometry that moves SIXTEEN H2S per event. Named, bounded; test asserts `rel=1e-6` |
| **the cis/trans pair** | **oleic and elaidic acid price IDENTICALLY** — dH and dG equal to the last bit | `test_the_cis_trans_pair_prices_at_exactly_zero`. ⚠ **NOT an invariant to preserve — a LIMIT to remove.** The day a cis correction lands, that test SHOULD fail and be rewritten |
| **`deacon_oxidation_rev` crossing** | **1141 K**, coldest of the high-order reverse rows (ammonia's 1335) | `validation/rate_ceiling.py`. Reported, not guarded: it moves a CLOCK, not an equilibrium |
| the whole suite | **866 passed in 12:46** — 847 + S7's 19, zero failures | run at the top of the session (847, clearing M8's unverified changes) and again at the end |

⚠ **THE FIVE COVERAGE NUMBERS, AND ALL FIVE WERE PREDICTED BEFORE MEASURING.**
43/224 classes, 43 templates, 34 template-ready, 24 BOTH, and species-ready
65 -> **63** (the fragment refusal's cost, predicted at "≤4 and 0 in the BOTH
column", measured at 2 and 0).

⚠⚠ **`RUNNABLE` CANNOT ASK WHETHER THE NUMBER IS RIGHT, AND TWO ROWS PROVE IT.**
The queue's top two entries by RUNNABLE were `isomerisation` (+3/+2) and
`crosslinking` (+2/+2), and both are worth zero honest routes — a cis/trans pair
priced at exactly zero, a glucose/fructose row priced at K = 4.8e-08 because the
corpus spells one as a pyranose and the other as a furanose, an ionic pair that
is not species-ready, and two products with no chemistry behind them. **The
marker half is now mechanised** (a marker on the product side excludes the route
from RUNNABLE); the "is the number right" half cannot be. **Read the rows.**

⚠ **AND `combustion` WAS AN OUTCOME LABEL.** Six rows, five mechanisms, credited
to the sulfur burner since M1. Split, and `match-chemistry` LOSES template-ready
for it — **the first split here whose measured headline effect is negative**, and
the intersection is untouched because that route was never species-ready.

⚠⚠ **TWO NEW CORPUS FACTS THAT ARE NOT FIXED AND MUST NOT BE FORGOTTEN:**

* **75 of 367 testable catalog rows cannot be balanced by any positive
  coefficient vector** (`validation/corpus_balance.py`): 17 `spurious`, 1
  `charge`, 57 `atoms`. Exactly ONE of them is in the BOTH column —
  `perkin-route` step 1, whose sodium acetate is the base — and it is INERT
  because `perkin_condensation`'s SMARTS never mentions a base. **Left alone on
  the `diels-alder-route` precedent: this is a third readiness bar, reported so
  it cannot rot, not a to-do list.**
* **`tools/catalog.py`'s `validate` still does not check balance.** The audit is
  a separate script on purpose — it needs `numpy`/`scipy` and 15 s — but that
  means the corpus can grow an unbalanceable row without anything failing. ⚠ A
  session that adds catalog rows should run it.

## S8 — the nine element solids, and the reduction this engine cannot hold

| row | value | how it is pinned |
|---|---|---|
| **every element solid's formation pair** | **Hf = Gf = 0.0 EXACTLY** on the solid basis, DERIVED not copied | `tests/test_element_solids.py`. ⚠ A non-zero result proves the CAS names a different allotrope — which is why TIN is absent (CRC's row is GREY tin at −2.1 kJ/mol) |
| **the ion-less exemption in `mineral_data`** | exactly **12** rows: iron, nickel, copper (S1) + the nine S8 added | `test_every_mineral_records_the_ions_it_dissolves_into_unless_it_is_a_METAL`. Spelled out so widening it is a deliberate edit |
| **all nine in one flask** | 0.01 mol each at 800 K under air, held to **twelve figures** over 600 s, `conservation_report` empty | `test_all_nine_charge_into_a_real_vessel_and_stay`. S6's precedent: reading `priced_solid` is a different claim from charging it |
| ⚠ **the ideal-gas refusal** | `thermo.get("[C]")` STILL REFUSES, and `game_gates` still lists graphite/Na/K/Ca/Fe/Cu/Zn as REFUSED there | curating the solid basis and refusing the gas basis are the same statement twice. Not softened by one digit |
| **`gas-solid-reduction`, all four rows** | ln K **10.90** (tenorite, 1500 K), **7.24** (litharge, 1400), **4.20** (hematite, 1300), **−4.10** (zincite, 1400), against a bar of **20** | `test_a_gas_solid_reduction_cannot_clear_the_irreversibility_bar`, which asserts the values AND that `surface.price` refuses the declaration |
| **the roasting family, for contrast** | every declared row is **above ln K 60** at its own temperature | same file. The bar is not unreachable, which is what makes the four refusals a statement about chemistry |
| **species-ready** | **63 → 77**, and BOTH unchanged at **24** | predicted at +0 on the intersection before the work was done, and measured at +0 |
| the whole suite | **904 passed in 13:02** — 866 + S8's 38, zero failures | third full run of the session |

⚠⚠ **THE ELEMENT GAP'S VALUE IS A MULTIPLIER, NOT A HEADLINE, AND THE QUEUE IS
WHERE IT SHOWS.** `gas-solid-reduction` went 1 → 2 runnable;
`catalytic-air-oxidation`, `carbothermic-reduction`,
`metal-ion-aldehyde-oxidation`, `molten-salt-electrolysis` and `pyrolysis` each
went 0 → 1; and `disproportionation-hydrolysis` (`ostwald-process`),
`hydroformylation` (`oxo-process`) and `metallothermic-reduction` (`thermite`)
appeared for the first time. **+0 today, +9 opportunities that did not exist
before. Species work should FOLLOW the template it enables, not lead it.**

⚠⚠ **AND `gas-solid-reduction` IS NOW A NAMED ENGINE GAP, WITH TWO
SPECIES-READY ROUTES WAITING ON IT** — `copper-smelting` and `lead-smelting`. It
needs a REVERSIBLE solid-gas term, which is M6's `p/K = n_A/n_B` measurement and
the reason `SurfaceArrays` is forward-only. **Do not close it by lowering
`LN_K_IRREVERSIBLE`**: a blast furnace's top gas contains CO because the reaction
really is reversible, and the zinc row is uphill at every temperature (a real
retort boils the zinc off at 1180 K, which is product removal). It is the second
gap of that shape after NUCLEATION and the more valuable of the two.

## S9 — the reversible solid-gas term, and the three smelters

| row | value | how it is pinned |
|---|---|---|
| ⚠⚠ **the five pre-S9 solid-state rows** | **BIT-IDENTICAL.** `P_react` is an empty product of exactly 1.0 and `P_prod` IS the old `Q` element for element, at p = 0 as well as at p = 55 bar | `test_the_pre_S9_rows_are_BIT_IDENTICAL_not_merely_close`, and `examples/lime_cycle.py` + `examples/mercury_retort.py` come out **byte-identical** |
| **the bound that replaced the refusal** | at p_CO → 0 the old `k_r Q` reads 1.5e-2, 1.5e+22, `inf`; the new `net` is **bounded by `k_r` = 1.4973e-08** at 1400 K | `test_the_reverse_flux_is_BOUNDED_where_the_quotient_form_diverged`. No clip, no floor, no epsilon |
| ⚠⚠ **the equilibrium, over a 50x charge range** | **Q/K = 1.0000, 1.0000, 1.0000** — `units` is a common factor chosen by the sign of the affinity | `test_the_equilibrium_is_Q_over_K_whatever_the_charge_weighs`. **This was ALREADY true before S9** and is half of what the old refusal wrongly claimed to be about |
| **every row's barrier vs its enthalpy** | `Ea >= max(dH, 0)` on all ten rows, and `max(Ea - dH, 0)` never clips | a declared `Ea` under `dH` would leave `k_f/k_r != K` silently. Refused by name |
| **the exothermic derived pair, measured not asserted** | thermite `A = 4.15e-6 1/s` (a **2.8-day** reaction) and the CO reduction 9.70e-4 1/(bar s) — **at EVERY temperature, because `Ea = 0` leaves no exponential** | `test_an_exothermic_row_may_not_take_the_derived_pair`. The finding is the missing exponential, not the size |
| **the three smelters, from ore + coke + AIR** | 0.04 mol ore → **0.040000 mol metal and 0.040000 mol SO2**, no ore and no coke left, `conservation_report` empty | `test_a_smelter_takes_ore_coke_and_AIR_to_metal`, three parametrised cases. **Nothing declares the route** |
| **the air is the control** (copper) | 0.02 mol O2 → **29.01%**, 0.06 → **80.41%**, 0.10 → **99.89%**, 0.20 → **100.00%** | monotone and saturating; `test_the_air_is_the_control_which_is_what_a_smelter_adjusts` |
| ⚠⚠ ~~**and the ZINC flask goes DOWN at 0.20 mol**~~ **WITHDRAWN BY S10 — IT WAS A RATE ARTEFACT** | S9 measured 0.032476 mol at 0.06 against 0.025515 at 0.20. S10 measures it **monotone and saturating**: .0117 / .0229 / .0328 / .0400, flat to 0.50 mol O2 | The competition is real — the reduction and the tuyere DO want the same carbon — but **which side won was decided by two DERIVED pre-exponentials**, and making the zinc a vapour moved one by 24x (tau 256.9 s → 10.9 s). ⚠⚠ **THE SIGN OF THE EFFECT DEPENDED ON A CLOCK.** A real furnace does waste an overblown charge, for transport reasons this engine does not model. **Thermodynamic conclusions here survive a phase change in a product; kinetic ones need not** |
| ⚠⚠ **the carrier-free furnace** | **EXACTLY zero** copper, CO and CO2 at the default rung, rtol 1e-6, 1e-8 and 1e-10 | `test_a_carrier_free_furnace_is_EXACTLY_inert_at_four_tolerances`. The lead chamber's round-off-seeded cycle CANNOT happen here, and the reason is the form (`p ** 1`, no denominator) and not a guard |
| ⚠ **and the carrier MULTIPLIES once seeded** | **1e-12 mol of CO2** — one part in 1e11 — reduces the whole 0.10 mol of oxide; the carbon is what is consumed | `test_the_carrier_MULTIPLIES_once_it_is_seeded`. Real chemistry: Boudouard makes 2 CO from 1 CO2 and the reduction hands one back |
| **the zinc retort's threshold** — ⚠ **MOVED BY S10, TOWARD THE LITERATURE** | **dG = 0 at 1197.8 K** (was 1264.2 with a SOLID zinc product), and SEALED at 1 L: 0.47% at 1000 K, 5.32% at 1100, 12.29% at 1150, **25.67% at 1198**, 53.38% at 1250, 100% at 1300 | `test_the_zinc_retort_is_a_THRESHOLD_at_its_own_dG_zero`. Carrying the zinc as the VAPOUR a retort makes adds +130.4 kJ/mol and +119.4 J/(mol K), and the entropy wins. Literature ~1200 K. ⚠ **SEALED on purpose — a vented flask now loses the product**, so total zinc stops being the conversion |
| **thermite's barrier column** | 0.0000% at 298.15 K, 3.1e-10 mol at 600, 0.2171% at 800, **36.95% at 933** (aluminium's melting point), 98.16% at 1000, 100% at 1200 | `test_thermite_is_INERT_cold_and_total_hot`, from ONE pin on the reported 1200 K ignition temperature |
| **thermite's self-ignition** | insulated at 298.15 K it stays there to six figures; lit at 1000 K it goes to 100% and rises **+322.45 K** against +323.86 predicted (50 J/K flask) | `test_thermite_runs_away_on_its_own_enthalpy_and_nothing_caps_it` |
| **`carbon-combustion`'s irreversibility margin** | **ln K +21.87 at 2200 K** against a bar of +20 — the tightest row in `SURFACE_REACTIONS` by 46 nats | `test_carbon_combustion_is_a_declared_pair_and_not_the_sulfide_one`. Not a marginal constant: above ~1000 K CO2 over carbon goes to CO, which is the row declared next door |
| **the declared pre-exponentials, in their own units** | `REDUCTION_A` = 1.609 1/(bar s) is **9.6e-4 of the HERTZ-KNUDSEN arrival rate** (2209 mol/(m2 s) over 0.756 m2/mol); `THERMITE_A` = 7.62e10 1/s is under 1e14 | `test_a_declared_pre_exponential_is_under_its_own_arrival_ceiling`. ⚠ `Vm_solid` is in **L/mol** — the /1000 is the point of that test |
| **`rate_ceiling` reads the SURFACE table now** | every pre-exponential there is **below the collision limit outright**, so no row crosses at any temperature | `validation/rate_ceiling.surface_panel`. ⚠ Against the BIMOLECULAR ceiling — a surface rate is order 1 in one gas |

**S10 — a metal that vaporises. ⚠ NO ENGINE CODE CHANGED; every row below is the
existing evaporation and melt terms acting on a curated species.**

| what | the number | where it is pinned, and the trap |
|---|---|---|
| ⚠⚠ **the retort DISTILS** | sealed 1 L at 1400 K: **0.040000 mol of zinc, every atom in the headspace**, no ore and no coke left | `test_the_zinc_DISTILS_and_neither_Tb_nor_Tm_is_written_anywhere`. **Tb = 1180.15 K and Tm = 692.68 K appear in no declaration and in no script** |
| **and the metal comes back** | cooled: 0.028404 mol LIQUID at 1180 K, 0.039665 at 900 K, **0.040000 SOLID at 600 K** (99.9996%) | same test. ⚠ The residue is real — zinc has a small vapour pressure at 600 K and the melting range has a finite width — so it is asserted at rel 1e-4, not hidden |
| ⚠⚠ **the vent does NOTHING until the retort beats the room** | sealed vs vented: **12.29% / 12.29% at 1150 K** (0.9325 bar) against **13.52% / 18.63% at 1156 K** (1.0312 bar), and 25.67% / 99.84% at 1198 K | `test_the_vent_does_NOTHING_until_the_retort_beats_the_room`. `solid_state_report` DERIVES 1156 K from a van 't Hoff K; the crossover is measured by running the flask. **They agree to the degree** |
| ⚠⚠ **a vented retort blows its product up the chimney** | ore consumed **99.91% → 100.00%** while metal KEPT falls **51.04% → 46.93% → 43.53%** at 1200/1300/1400 K | `test_a_VENTED_retort_blows_its_own_product_up_the_chimney`. The two numbers a smelter cares about move in OPPOSITE directions. ⚠ `conservation_report` is silent, correctly: the vent is a declared boundary flux. **An invariant measured across one is not an invariant** |
| **zinc's four cross-checks, and CRC never meets Alcock in any** | `Gf(g) + RT ln(Psub/P0)` = **-0.184 kJ/mol**; the same curve's slope **130.674 vs CRC's 130.400 (+0.21%)**; the unanchored **Tb 1168.84 vs 1180.15 (-0.96%)**; sublimation and liquid fits at the triple point **+0.103%** | `test_zinc_closes_TWO_independent_cross_checks_against_Alcock`, `validation/game_gates.py` panel 4b. ⚠⚠ **Alcock's fit is NOT anchored at Tb, which is what makes the boiling point independent here** — the trap in `chemsim-physical-data-sourcing`, read from the other side |
| **the Antoine conversion is ALGEBRA** | Alcock's `log10(p/atm) = 5.378 - 6286/T` has C = D = 0, so the two forms agree to **4e-15** over 700–3000 K | `_CURATED_ANTOINE["[Zn]"]`. A change of base and of pressure unit; **nothing is fitted**, and the round trip reproduces Alcock's published numbers to four figures |
| ⚠ **the retort is FASTER despite a higher barrier** | `Ea` +240.0 → +370.4 kJ/mol, but tau **256.9 s → 10.92 s** at 1400 K | `test_the_four_rows_land_on_four_real_timescales`. **An Arrhenius pair is not separable**: the derived `A` carries `exp(dS/R)`, and `exp(119.4/R)` = 1.7e6 beats `exp(-130400/RT)` = 1.4e-5 by ~24x. Equilibrium untouched — both directions scale by one factor |
| ⚠⚠ **a liquid metal's heat capacity was NEGATIVE, since S4** | mercury **-25.26 at Tm, -12.62 at 298 K** against a real 27.98; zinc **+462.51 at Tb** against 31.38 | `test_a_liquid_metals_heat_capacity_is_curated_and_POSITIVE`. `CondensedProvider.get` fits Rowlinson-Bondi over a **hardcoded 250–450 K** and every caller takes the default |
| ⚠⚠ **and it was REACHABLE** | with 50 J/K glassware, **over 3.96 mol of liquid mercury (795 g, 59 mL) gave a NEGATIVE TOTAL thermal mass** — measured **-12.808 J/K** at 5 mol | i.e. heating the flask cooled it. Fixed from measurement (three sources inside 0.2% for mercury; the WebBook Shomate curve over its OWN window for zinc) |
| ⚠⚠ **THE GENERAL FAULT IS STILL OPEN — 103 ROWS** | **103 corpus compounds still return a negative liquid Cp inside their own liquid range** (worst carminic acid, **-21482**) and 41 more swing over 5x | `test_the_250_450_K_FIT_WINDOW_IS_STILL_THE_GENERAL_FAULT`. ⚠ Mostly on Joback Tm/Tb that is itself meaningless, which is what made the two metals the clean cases. ⚠ **It bites at BOTH ends** — ethylene reads ~1574 at its 113.9 K melting point. **A LATENT fragility: reported, not refused** |
| ⚠⚠ **an audit invented a 90 kJ/mol finding** | `game_gates` printed "zinc, residual **+90.78 kJ/mol**" for a formation pair that is fine | it differenced a shift `standard_state.shift` had REFUSED (2e-16 bar, under `PSAT_FLOOR_BAR` = 1e-12) without checking `.applied`. Every other row has an applied shift, so the hole was unreachable until a solid with that vapour pressure arrived. `test_zincs_cross_check_needs_the_SUBLIMATION_curve_and_the_liquid_one_REFUSES` |
| ⚠ **the fusion law on a metal in water, PRE-EXISTING** | zinc x_sat = **0.197** at 298 K (89 g/100 mL against a real ~1e-8) — but iodine is over by **1.5e4x** and sulfur by **1.1e8x** on the same law, and zinc's mole fraction is SMALLER than either | so zinc JOINS a bounded, reported fragility rather than creating one. Reachable only by putting metal in water, which no route does |
| ⚠ **iron is REFUSED, and that is where the engine gap is** | the mechanism would work — boiling thermite's 2 mol of iron absorbs **88.0%** of the 851.5 kJ it releases, and Alcock's iron curve is unanchored-accurate to **-1.60%** | `test_thermite_runs_away_on_its_own_enthalpy_and_nothing_caps_it`. ⚠⚠ **Iron cannot LEAVE `mineral_data`**: it is a declared `solid_catalyst` (`ammonia_synthesis`) AND thermite's solid product, so it must be BOTH a lattice and a gas — one boolean, two jobs. Plus three solid allotropes and **no sublimation curve** |
| coverage | **48/229 classes, 38/173 template-ready, 77/173 species-ready, 28/173 BOTH — ALL FOUR UNCHANGED, all four predicted** | `validation/catalog_coverage.py`. An honesty and mechanic milestone, taken as one |

| the whole suite | ⚠⚠ **932 passed / 0 FAILED in 13:20 (S10)** — run AFTER every `src/` edit, so it is a real baseline and not arithmetic. S9's reading was 927/1 of 928 and the clean number was never measured as one run | `python -m pytest -q`, once at the end. ⚠ S10 did NOT touch the RHS, so `tolerance_audit.py` was not re-run; the one example that could move (`mercury_retort`, via the liquid-Cp curation) was measured directly at **1 part in 1e8** |
| **the tolerance audit** | **"NO example prints a quotable digit that moves"**, and `lime_cycle` / `roasting_and_the_catalyst_gate` / `mercury_retort` are all **OUTPUT IDENTICAL** | `validation/tolerance_audit.py`, 12 examples. ⚠ The strongest single check on the engine change, because those three are the solid-phase ones. `oil_of_vitriol` is skipped without `--all` |

⚠⚠ **THE FOUR COVERAGE NUMBERS, ALL PREDICTED BEFORE MEASURING.** 48 classes,
38 template-ready, **28 BOTH**, and species-ready holding at 77. ⚠ The class
DENOMINATOR moved 224 → **229**, because S9 made TWO splits and only one of them
was planned: `catalytic-gas-oxidation` came apart under the RANKING check.

⚠⚠ **M6 DREW THE SOLID/SURFACE LINE IN THE WRONG PLACE.** It was recorded as
*inside a crystal / at its surface*, and S4 had already broken that by turning a
crystal entirely into gas. The line that holds is **reversible or not**: an
affinity form cannot carry DECLARED rate orders, because detailed balance fixes
its exponents at the stoichiometric coefficients. That is this file's own
standing invariant — *a declared rate order may NEVER be reversible* — arriving
in a new place. Roasting stays in `SurfaceArrays` **for the order, not for the
denominator.**

⚠⚠ **TWO STATED LIMITATIONS THAT ARE THE SAME LIMITATION.** A lattice in this
engine may react and may never boil, so:

* **the zinc stays SOLID.** A real retort distils it off at 1180 K, which is
  product removal. `thermo.get("[Zn]")` refuses the monatomic vapour as a bare
  element. ⚠ The row does not need the escape — ln K is +2.21 at 1400 K — but the
  mechanic is absent. `test_the_zinc_stays_a_SOLID_and_that_is_a_stated_limitation`
  will FAIL the day `[Zn]` becomes priceable, and then the row should be
  rewritten to evolve it.
* **nothing caps thermite's temperature.** A real one stops near 3135 K because
  the IRON BOILS. A 1 J/K flask reports **5469 K**, above the RHS's `T_MAX` clamp
  of 5000 — which bounds RATE evaluation and not the state. Reported, not
  refused.

⚠ **AND `direct-combination` IS STILL REFUSED, MEASURED.** `Hg + S8 -> HgS` was
on the queue as "probably" part of this work. Mercury is a curated LIQUID element
and S8 is a MOLECULAR solid, which `build_surface_arrays` refuses by name because
`PhaseArrays.lattice` cannot answer "how much solid is there" for a species with
a solid block AND a liquid block AND a headspace. Neither table's shape.

⚠ **`blast-furnace` IS NOW ONE CLASS AND ONE MINERAL AWAY** — `slagging` has no
template (and neither `silicon-dioxide` nor `calcium-silicate` has a lattice),
and both its `gas-solid-reduction` rows want an `iron-ii-oxide` `mineral_data`
refuses on the crystal Cp. The closest any five-step route has been.
⚠⚠ **S11 RE-QUERIED THAT AND IT WAS PRICED TOO CHEAPLY.** Silica is fully
available (CRC: Hfs -910700, Gfs -856300, S0s 41.5, Cps 44.4) — but **calcium
silicate has NO thermochemical data in `chemicals` 1.5.2 under any of its three
CAS numbers** (10101-39-0, 1344-95-2, 13983-17-0), so `slagging` is not a
curation job at all. And FeO's CRC standard row has `Cps = NaN`, confirming the
recorded refusal. `blast-furnace` is blocked TWICE over, on sources rather than
on work.

⚠ **A FALSE CITATION SURVIVED FOUR MILESTONES.** `surface.ROASTING_A`'s comment
has said *"validation/rate_ceiling.py re-measures it"* since S1 and that audit
had never read the table. **The sentence claiming the check existed is why nobody
looked.** Fixed, and the near-miss is kept in the source.

**S11 — two competing templates, an ion for a catalyst, and a hand-typed list.
⚠ NO ENGINE CODE CHANGED (no `numerics/`, no `vessel/`), second milestone
running. ⚠⚠ BUT `properties/physical_data.py` DID change, and two examples moved
because of it — that is row 6 below and it is the one to read before trusting an
old number.**

| row | value | how it is pinned |
|---|---|---|
| **the oxo reactor** — 1 L at 200 bar, 420 K, 0.1 mol cobalt, 1 h | **94.32% converted, n 1.437050, iso 0.363599, n:iso 3.9523**, carbon closure exact, conservation clean | `validation/hydroformylation.py` panel 1; `tests/test_hydroformylation.py` |
| **n:iso IS `exp(dEa/RT)` up to ~450 K** | 380/400/420/450 K: **4.569 / 4.234 / 3.952 / 3.543** against a kinetic 4.569 / 4.235 / 3.953 / 3.607 | panel 3. ⚠ Only the 420 K value is FITTED (4.8 kJ/mol); the curve is a consequence |
| ⚠⚠ **and it COLLAPSES above ~450 K, steeper than Arrhenius** | 480 K **1.867** against a kinetic 3.329; 520 K **0.760** against 3.035, with the conversion turning over too | panel 3, `test_above_450_K_the_REVERSE_beats_the_barrier_difference`. The reverses get inside the reactor's own hour. **Nobody declared a maximum operating temperature** |
| ⚠⚠ **the branched aldehyde is the MORE STABLE one** | dH -113.73 vs **-123.08**, dG298 -38.72 vs **-43.54**; at equilibrium iso wins **2.33 to 1** | `test_the_branched_product_is_the_MORE_STABLE_one`. **The process runs against its own thermodynamics**, which is why Evans-Polanyi is OFF in both templates — any alpha > 0 names the wrong major product |
| **kinetic -> thermodynamic control, unaided** | headspace n:iso 3.304 (1 h) -> 0.993 (1 yr) -> **0.4283 (settled)**, against `K(n)/K(iso)` = **0.4283** | panel 5. ⚠⚠ **The INVENTORY ratio settles at 0.513 instead**, because the reactor holds ~1.7 mol of liquid and butanal is the less volatile. **Read K against the HEADSPACE, never the inventory** |
| **irreversible would lie, measured** | 600 K / 1 bar: **0.013% reversible against 77.933% irreversible** (~6000x). 600 K / 200 bar: 53.3% | panel 4, `test_irreversible_would_report_a_conversion_the_equilibrium_forbids` |
| **the Wacker reactor** — 1 L water, 0.02 mol Cu(II), 400 K | **40.06% in 60 s, 88.83% in 300 s, 98.20% in 600 s**; copper out = copper in to 1e-12 | `validation/wacker.py` panel 3; `tests/test_wacker.py` |
| ⚠ **a flask with no electrolyte support REFUSES** | `build_network` SUCCEEDS and names `[Cu+2]`; **`Vessel` raises** on the net charge | `test_a_flask_with_no_electrolyte_support_REFUSES`. A network is a GRAPH question; pricing is one layer down |
| ⚠⚠ **the Wacker's oxygen order is DELIBERATELY WRONG** | acetaldehyde in 60 s against O2 charged: **1.00 / 1.92 / 3.53 / 5.85x**. A real reactor gives 1.00 throughout | `test_the_oxygen_order_is_wrong_on_purpose_and_here_is_the_cost`. ⚠ **NOT an invariant to preserve — a LIMIT.** The kernel has no availability gate, so order zero drives O2 negative |
| ⚠⚠ **ethylene is ~40x too soluble at 400 K** | **0.165958 of 0.20 mol dissolves in 20 mol of water** — 83%, against a real ~2% | `validation/wacker.py` panel 4. A CONDENSABLE species' Raoult law against Psat = **219.9 bar**, read off a curated Antoine **118 K above ethylene's critical temperature**. ⚠ **NOTHING IN `build_phase_arrays` COMPARES T TO Tc.** Reported, not fixed |
| **`tolerance_audit` on `oil_of_vitriol`** | ⚠⚠ **1 moved line, worst 6.60e-05, "(below 0.1%)"** — was 5 lines and 99.85% | `CONVERGING_ABS = 5e-4`, asymmetric. All four numbers PREDICTED before the 19-minute run |
| ⚠ ... and `CONVERGING_ABS` fires on **zero tokens** across the twelve cheap examples | the safety measurement that mattered: the relaxation touched nothing but the column it was made for | `/tmp` run of `validation/tolerance_audit.py`, no `--only` |
| **the oxo reverse pre-exponentials** | **2.0e26 and 1.2e27 1/s**, crossing the unimolecular ceiling at **969.4 / 966.8 K** | `validation/rate_ceiling.py`, new oxo panel. ⚠ The one flagged row whose crossing IS physical — a genuinely FIRST-order reverse. An entropy of gas-making in a pre-exponential, third appearance |
| ⚠⚠ **310 catalog species have a measured Tb that this engine is not using** | 229 price a Tb today; mean/median/worst |error| **5.81% / 2.94% / 84.89%**; 138 over 2%, 34 over 10%, 11 over 20% | measured against `chemicals` 1.5.2. Cause: `CANDIDATES` in `tools/build_physical_data.py` is a **hand-typed list of 33 names** |
| ⚠ **four records were deliberately overridden** | propene Tb 264.92 -> 225.53 and Tc 427.64 -> 364.21; ethylene Tb 234.56 -> **169.38**; butanal 339.78 -> 347.95; 2-methylpropanal 339.34 -> 337.25 | `DELIBERATE_OVERRIDES` in `tests/test_critical.py`, plus a second test refusing a stale entry |
| ⚠⚠ **and TWO EXAMPLES MOVED because of it** | `competing_pathways` worst **0.20380 -> 0.20485 (0.5%)**; `named_routes` ethanol-hydration **2.9% -> 2.7%** | measured before/after, example by example. The other three species appear in no example |
| **propene's Tc error was not cosmetic** | the oxo flask condensed **0.91 mol of "liquid propene"** 55 K above propene's real Tc and read **167 bar where it was charged to 200**; one candidate line gives **200.00 bar and no liquid** | ⚠ And the 2.8e-24 mol of butanal in a zero-cobalt flask went with it — solver dust from the extra stiff phase, never a gate leak |
| **four provenance tiers upgrade** | ethylene `joback -> measured`; propylene, butyraldehyde and isobutyraldehyde `joback -> benson` | `data/catalog/derived/species_roles.psv`. A measured Tb lets Benson's formation half assemble where Joback's was standing in — the part of S11's data work a coverage report CAN see |
| the whole suite | **952 passed / 0 failed in 13:15**, run AFTER every `src/` edit, and run TWICE — the first read 951/1 and 952/0 would have been ARITHMETIC | `python -m pytest -q`. ⚠ `tolerance_audit.py` re-run too, because a DATA table changed: **NO example prints a quotable digit that moves**, and the three self-check examples are OUTPUT IDENTICAL at speedup 1.00 |


⚠⚠ **TWO ROWS ABOVE ARE LIMITS TO REMOVE, NOT INVARIANTS TO KEEP**: the Wacker's
oxygen order, and ethylene's solubility. Both are marked.

**S12 — the Skraup, whose oxidant becomes one of its own reagents. ⚠ NO ENGINE
CODE CHANGED (no `numerics/`, no `vessel/`) and NO DATA TABLE either, third
milestone running — so `tolerance_audit.py` carries no new exposure and was NOT
re-run. ⚠⚠ THE ROW TO READ FIRST IS THE SECOND ONE: the source comment's own
hand-priced numbers were wrong, and the audit is what caught them.**

| row | value | how it is pinned |
|---|---|---|
| **the Skraup flask** — 1 L sealed, 450 K, 1 h; 3.0 aniline, 1.0 acrolein, 1.0 nitrobenzene, 0.2 hydronium, 5.0 water | **quinoline 1.000000 mol**, acrolein 0.000000, nitrobenzene 0.666667, aniline 2.333333, water 6.666667, hydronium 0.200000 | `validation/skraup.py` panel 3; `tests/test_skraup.py`. Stoichiometry checked AGAINST the oxidant (`1 - q/3`, `3 - 2q/3`, `5 + 5q/3`), not assumed |
| ⚠⚠ **THE TWO STANDARD STATES DISAGREE ON THE SIGN OF dS** | ideal gas **dH -561.63, dG298 -572.55, dS +36.65**; pure liquid **dH -715.04, dG298 -623.12, dS -308.31** (⚠ S13; was -725.16 / -627.05 / -329.08). Difference **-153.41 kJ/mol** in dH | `test_the_two_standard_states_disagree_on_the_sign_of_dS` pins BOTH rows. The template is `phase="liquid"`, so **NINE product molecules condense against SEVEN reactant ones** — and *"seven molecules become nine"* is an IDEAL-GAS sentence. ⚠ **The gas-basis numbers were written into `synthesis.py`'s comment first, off a hand calculation** |
| **irreversible is safe — for the other reason** | ln K **251.4 at 298 K, 177.9 at 400, 154.0 at 450, 106.3 at 600**; dG crosses zero at **2319 K** (⚠ S13; was 252.9 / 178.5 / 154.2 / 105.8 and 2204 K) | same test. dS is NEGATIVE, so dG gets LESS negative as the flask is heated — it simply has 725 kJ/mol to spend. S11's count-the-gas-moles rule is answered here by there being no gas in the rate law at all |
| **7 reactant slots and 9 product slots**, plus the acid as an eighth | `3 aniline + 3 acrolein + PhNO2 -> 3 quinoline + PhNH2 + 5 water`, C33H38N4O5 both sides, four aromatic rings in and four out | `test_the_row_is_three_anilines_and_one_nitrobenzene`. ⚠ **The aniline on the right is the NITROBENZENE, reduced** — not `_maybe_catalyse`'s case and not `corpus_balance`'s `spurious` case |
| ⚠⚠ **a substituted aniline makes the PARENT quinoline too, at exactly 2:1** | p-toluidine alone in: **6-methylquinoline 0.666667, quinoline 0.333333, free aniline 0.000000**, totalling the 1.0 mol of acrolein charged | `test_a_substituted_aniline_makes_the_parent_quinoline_too`. The oxidant's reduction product is ITSELF a substrate, because the three amine slots need not be the same molecule. **Nobody declared it**, and it is a real nuisance of the real preparation |
| ⚠ **an OPEN flask loses 95% of the yield** | quinoline against `k_vent` 0 / 1e-3 / 1e0 / 1e3: **1.000000 / 0.938408 / 0.089411 / 0.053578** (⚠ S13; acrolein's Tb was Joback's 313.58 K and is now CRC's 325.45, so the vent carries less of it away) | `validation/skraup.py` panel 5, `test_an_open_flask_loses_its_acrolein_before_it_can_react`. Acrolein boils at **314 K** and the flask is at 450. ⚠ **This is the other half of why the preparation makes its acrolein in situ**, and it is the vapour-pressure curve rather than a declaration |
| **the acid is the gate** | no acid at all: **under 1e-12 mol** of quinoline (⚠⚠ S12 wrote *exactly* 0.0 and that was one word too strong — water autoprotolyses, so the flask holds ~4e-29 mol of hydronium and makes ~2.4e-25 mol of quinoline in ten hours, flat thereafter. The literal 0.0 was the solver clamping a column that never left the floor) | `test_a_flask_with_no_acid_does_nothing`. Spelled as `ACID_CATALYST` (hydronium), so the network needs `electrolyte_provider()` — the Wacker's gate again |
| **the oxidant is stoichiometric, not catalytic** | 0.10 / 0.20 mol PhNO2 cap the yield at **0.300000 / 0.600000** = exactly 3x, with the acrolein left over | `test_the_oxidant_is_stoichiometric_and_starving_it_caps_the_yield` |
| **the temperature is the clock** | one minute at 350 / 400 / 420 / 450 / 480 K: **2.01% / 37.53% / 70.66% / 98.51% / 100.00%**, at 0.76 / 3.88 / 6.54 / 13.64 / 26.73 bar (⚠ S13 moved these; the shape did not) | panel 4. ⚠ The pressure column is the price of having **no reflux head**: `k_vent=0` IS the condenser here, and it is printed rather than hidden |
| **every slot it consumes keeps order 1** | `orders=(1,1,0,0,0,0,1,1)`; per-species totals aniline 1.0, acrolein 1.0, nitrobenzene 1.0, hydronium 1.0 | `test_every_species_it_consumes_keeps_at_least_order_one`, read off the CONCRETE reaction where the three amine slots collapse onto one species. ⚠ Unlike the Wacker, **obeying S11's rule here costs nothing**: a real Skraup does slow as its oxidant is spent |
| **the Skraup's pre-exponential, audited** | **2.90e-18 of the bimolecular ceiling** at 298 K | `validation/rate_ceiling.py` gained a Skraup panel, because a template not in that file is not audited. ⚠ Its crossing column is meaningless for this row — a fourth-order `A` is in L^3/(mol^3 s), the Deacon caveat again |
| the whole suite | **S12: 961 passed / 0 failed in 13:20.** ⚠ S13's number is in its own block below | `python -m pytest -q` |

## ⚠⚠ S13 -- the hand-typed list, closed, and FOUR OF THESE ROWS ARE LIMITS TO REMOVE

**⚠⚠ THE FIRST ROW IS THE ONE TO READ, AND IT IS ABOUT S13's OWN INSTRUMENT.**

| row | value | how it is pinned |
|---|---|---|
| ⚠⚠ **NEITHER CAS KEY ALONE IS ENOUGH -- and the fix for S11's trap became the next trap** | `CAS_from_any("smiles=Nc1ccccc1")` **REFUSES**; `CAS_from_any("aniline")` returns 62-53-3. Of 1069 corpus species with no graph-resolved CAS, **874 resolve by NAME with a matching formula and 508 carry a measured Tb**. A graph-only sweep reported the gap as **322** where it is **830** | `validation/boiling_points.py` panel 3 demonstrates both traps live and ASSERTS the two keys still disagree. `tools/build_physical_data.collect` tries the graph first, then the name, with the formula cross-check as arbiter -- **it refuses 72 name matches outright** |
| **`MEASURED_PHYSICAL` is generated from the CORPUS now, not a hand list** | **1239 entries, 896 with a measured Tb**, against 37 and 20 | `tools/build_physical_data.corpus_candidates`. `CORPUS_SWEEP` names the 1202 that came in that way; two tests keep it DISJOINT from `DELIBERATE_OVERRIDES` and a subset of the table |
| **the physical half of the corpus** | **measured 652/1583 (41.2%)**, compilation 47, Joback **333 (21.0%)** -- against measured 40 (2.5%) and Joback 964 (60.9%) | `data/catalog/COVERAGE_REPORT.md`, regenerated and byte-stable across `PYTHONHASHSEED` |
| **what the correction was worth** | 881 estimates replaced: mean 6.10%, median 1.94%, **worst 110.94%**; 437 over 2%, 68 over 20% | `validation/boiling_points.py` panel 2, measured through `ThermochemistryProvider(measured_physical=False)` -- not a reconstruction of the old behaviour, it IS the old behaviour |
| ⚠⚠ **A COUNT OF ABSENT SPECIES IS NOT A COUNT OF WRONG ONES** | 322 absent, **213 would change the resolved record**. Water, O2 and HCl are "absent" and irrelevant -- `_CURATED_RAW` short-circuits them | `boiling_points.would_move` resolves all 322 TWICE, through two providers |
| ⚠⚠ **A COVERAGE TIER WAS BEING READ OUT OF PROSE** -- **A LIMIT REMOVED** | `_thermo_tier` took the WHOLE composite `source` and said `measured` if "experimental" appeared anywhere. After the sweep it reported **669 measured FORMATION halves** where the answer is **135**. Its twin defaulted to `benson` and reported **659 Benson PHYSICAL halves**, of which there is no such thing | `catalog_coverage.formation_half` splits the string on its own structure; `_volatility_tier` takes `physical_source` as the FIELD it is and **raises** on an unrecognised provenance. ⚠ The fix also found a pre-existing overcount: 144 -> 135 |
| ⚠ **`compilation` is a coverage tier now** | 47 boiling points come from YAWS/WIKIDATA, which `chemicals` calls published-but-unsourced. Before S13 exactly ONE corpus species carried one | `TIER_ORDER` in `catalog_coverage.py`. Folding them into `measured` would relabel an unauditable compilation as a measurement |
| ⚠⚠ **A FIT WINDOW MAY NEVER EXCLUDE THE BOILING POINT IT BRACKETS** -- **A LIMIT REMOVED** | `T_lo = max(0.30*Tc, Tb-120, 150.0)` put methane's window 38 K ABOVE its Tb: **+16.50%** at the normal boiling point, nitric oxide **+14.53%**. Both PRE-EXISTING and invisible, because the check walked `MEASURED_PHYSICAL` and both are in `_CURATED_RAW` | `volatility.py`, one line: `min(150.0, t.Tb)`. `test_the_loose_boilers_are_a_measured_list_and_not_a_wildcard` refuses to let either back onto the exception list |
| **the boils-at-1-atm bar, re-measured over 44x the population** | **889 condensable records checked against 20; 858 clear 1.5%.** The 31 that do not are NAMED with their residuals, and **eight are pre-existing** -- water +2.57%, SO2, SO3, HF, formaldehyde, nitric acid, the nitrite pair, zinc | `BOILS_LOOSELY` in `tests/test_critical.py`. Nearly all are polar or associating and boil between 250 and 375 K |
| ⚠⚠ **A BAR IN TEMPERATURE AND A BAR IN PRESSURE ARE NOT THE SAME BAR** | zinc's curated Alcock curve: **-0.96% in T** (S10's own number) is **+12.61% in P** at the measured Tb | same list. Quoting one against the other would have manufactured a regression in an entry behaving exactly as its own session measured it |
| **what the sweep cost the examples**, measured by RUNNING all fifteen before and after | `esterification`, `lime_cycle`, `roasting_and_the_catalyst_gate`, `mercury_retort`, `oil_of_vitriol` **IDENTICAL**. Worst movers: `multistep_prep` yield **84.0% -> 82.7%**, `fractional_distillation` 11.8%, `workshop` 8.7%, `wait_until` **the boil at 1353 s -> 1418 s** | `run_examples.py` + `tolerance_audit.diff`. ⚠ **`plate_column`'s HEART is 0.8548 against 0.8544 -- target still MET**, replay determinism still exact at 0.000e+00 mol |
| ⚠⚠ **`named_routes` LOST FOUR MIXED-STANDARD-STATE WARNINGS AND GAINED A BARRIER GUARD** | four `MIXES STANDARD STATES` notices gone (DDT isomers, dinitrotoluenes, the stearic/oleic pair). One new: `ester_hydrolysis` declares Ea 70 kJ/mol below aspirin hydrolysis's dH of 75.6, raised. `aspirin-impurity` **99.8% -> 59.2%** | Nobody changed a barrier. The reaction's enthalpy moved onto a measured basis and a guard that was already there fired |
| ⚠⚠ **A ONE-POINT TOLERANCE SWEEP CANNOT TELL "NEWLY BROKEN" FROM "ALREADY BROKEN WHERE IT DOES NOT LOOK"** | `named_routes` raises at rtol 1e-8 now. Measured on both bases: **pre-S13 data ALSO raises, at rtol 1e-7** -- one decade CLOSER to the default than this audit samples | `KNOWN_REFUSAL["named_routes"]`. The answer is confirmed at the default on both bases: 1.000000 mol of aniline, complete conversion |
| ⚠ **`is_boiling` needed a boundary tolerance** -- **A LIMIT REMOVED** | after `wait_until(boils())` the flask sat **-1.110e-15 bar** below ambient and read NOT boiling; +9.7e-08 exactly 0.05 s later. A ROOT is zero to solver precision and the last bit is not physics | `vessel.is_boiling` gained `P_ambient * (1 - 1e-12)`. `test_waiting_for_a_boil_agrees_with_the_boiling_readout` had been passing on which side of the root the last bit fell |
| ⚠⚠ **A DOCUMENTED TRAP WENT BELOW THE DEFAULT TOLERANCE, AND A WRONG Tb WAS WHAT HAD MADE IT VISIBLE** -- **A LIMIT TO REMEMBER, NOT ONE REMOVED** | the hotplate's opening evaporative swing was **-24 K/s** on Joback's ethanol and is **-1.42 K/s** on CRC's. `temperature_steady(0.01)` now reaches the plateau at 966.9 s instead of firing at 298 K. ⚠ `max_step` 0.1 and 0.01 do NOT recover it; **rtol 1e-9 does, at 0.08 s and 297.78 K** | `test_a_rate_tolerance_fires_on_the_FIRST_transient_not_the_plateau` and its new companion. The loose error control smooths the spike OUT of the computed solution rather than merely stepping over it |
| ⚠ **the acentric-factor check, the one INDEPENDENT link in the chain, went from n~20 to n=254** | **measured Tc/Pc mean abs d-omega 0.029; Wilson-Jasperson 0.121** | `validation/physical_estimation.py` panel 3. The design held under 12x the population |
| ⚠ **a better record made ONE number worse, and it is written down rather than widened away** | benzoic acid's molar volume **96 -> 87.4 mL/mol** against a real ~96.5, because a measured Tb brings a FEDORS Vc (326.43) where Joback's (343.50) was closer to the literature's ~341 | `test_the_crust_volume_is_the_wetted_area_times_one_particle_layer`. Taken anyway: a record may not mix two group-contribution methods, and Fedors' 7.7% mean error is MEASURED |
| ⚠⚠ **THE PSRK OVERFLOW IS NO LONGER "MEASURED INERT"** | `plate_column` prints five `RuntimeWarning` lines where it printed none: something in the fourteen-vessel rig evaluates an activity coefficient **below 4.28 K**. ⚠ **Measured HARMLESS where it fires** -- heart 0.8548 vs 0.8544, replay exact | The word to change is "inert", not the number. Still open |
| ⚠ **M11's costed starting point is gone** | `COVERAGE_REPORT.md`'s "needs only a boiling point" bucket went **10 -> 2**: `performic-acid` and `phenyl-radical`, neither of which has a non-estimated Tb under either key | ⚠⚠ **RE-COST M11 BEFORE SCHEDULING IT.** What remains is the FORMATION half -- 267 species with no group value anywhere |
| the whole suite | **965 passed / 0 failed in 21:36**, run AFTER every `src/` edit (961 at S12; +4 is `test_the_hand_list_and_the_corpus_sweep_are_disjoint`, `test_the_corpus_sweep_is_a_subset_of_the_table_it_describes`, `test_the_loose_boilers_are_a_measured_list_and_not_a_wildcard`, `test_the_opening_swing_is_still_there_at_a_tighter_TOLERANCE`) | `python -m pytest -q`. ⚠⚠ `tolerance_audit.py` WAS re-run — a data table changed — and its result is two rows above |

# Still open

- ✔ ~~**THE DRYOUT BAND.**~~ CLOSED 2026-08-23, HANDOFF 72. Was the last live member of the
  `N/(N+eps)` class.
- **A stiff reactant driven to EXACTLY zero still overshoots**, at the 1e-4
  level, reported and converging. Belongs with item 5 (dissociation as an
  equilibrium) and now has a convergence test to measure a fix against.
- **SOLID-PHASE REACTIONS**, for chain 2's green-vitriol seed. ⚠ M5 added a
  second reason to want them: five of its templates are HETEROGENEOUS and are
  written homogeneous with the catalyst folded into the barrier, so a flask with
  no iron in it makes ammonia and "you need a catalyst" cannot be a gate.
- ⚠⚠ **A REVERSIBLE TEMPLATE IS DISCOVERED IN THE FORWARD DIRECTION ONLY** --
  found by M5, general to every reversible template in the project, and NOT
  fixed. `build_network` matches REACTANT patterns, so an ester and water in a
  flask are inert however reversible the esterification is:
  `build_network(["CCOC(C)=O", "O"], [esterification()])` gives **0 reactions**
  while `["CC(=O)O", "CCO"]` gives 2. The workaround is to write the template
  from the side a chemist starts on; the fix is expanding on reverse patterns
  too, which roughly doubles every build's match cost. Measured and pinned by
  `tests/test_named_routes.py`.
- **`halogen_disproportionation` is correct and cannot run.** HOCl has no
  measured boiling point in any source, the same standing refusal carbonic acid
  carries, so `[O-]Cl` has no ion entry. ⚠ Curating it is a trap: ATCT has the
  formation half but nothing has the physical half, and the reaction is
  LIQUID-phase, where the standard-state shift decides the answer.
- **Three named hydrogenation gaps** from M5's re-label of
  `catalytic-hydrogenation`: `nitro-partial-hydrogenation` (the whole difficulty
  of the paracetamol route), `arene-hydrogenation`, `carbonyl-hydrogenation`.
- ✔ ~~**NO ION CAN PRECIPITATE.**~~ CLOSED 2026-08-23, HANDOFF 79. A metathesis
  drops AgCl. ⚠ What is LEFT of it, and each is stated rather than hidden:
  * **The solid block is an ION INVENTORY, not a set of distinct crystals.** Two
    coexisting lattices sharing an ion cannot be told apart. Bounded by
    `units = min nS_i/nu_i` and reported as LATENT.
  * **No nucleation barrier**, refused rather than forgotten: `S_crit` is a
    measured substance-specific width with no source here.
  * **The factor of 4** on the five measured solubilities is gamma, i.e.
    Debye-Huckel, i.e. the ionic-strength item already on this list.
  * **Sodium bicarbonate and Prussian blue have no lattice entry**, and PbCrO4
    is refused for want of an S0s in any database shared with its Hfs -- three
    of the five `precipitation-metathesis` rows.
  * OK ~~**AN ADIABATIC FLASK'S TEMPERATURE TAIL**~~ -- **CLOSED 2026-08-24 as
    MILESTONES M12.** HANDOFF 82. Two hypotheses died on the way: it was not a
    generic solver weakness (HANDOFF 81 refuted that), and it was not the
    precipitation term, the energy equation's algebra, the tolerance or the
    integrator either -- all four measured. **The cause was a DERIVED rate
    constant 9.4e7 times the collision limit**: water autoionization's `Ea = 60
    kJ/mol` is chosen so the barrier clamp misses water's 55.8 kJ/mol
    dissociation enthalpy, which hands the reverse a 4.2 kJ/mol barrier and
    9.4e18 L/(mol s). Its two heat terms sat at +-5.2e9 W around a net of a
    fraction of a watt, and three BDF steps of 167.63 s destroyed 467 J with the
    composition unmoved. `reactions.thermo.COLLISION_LIMIT` scales BOTH
    pre-exponentials by one factor, so Kw is invariant at 1.0022e-14 and no pH
    moves. The flask now reads **+0.15759 K at 3600 s**, converged at every
    rung, and the prep got **6.6x faster**.
    STILL OPEN, reported: the guard runs at 298 K only, and
    `carboxylic_acid_dissociation_rev` crosses the ceiling at **416.6 K**.
  * ⚠ **`anhydrite`, NOT gypsum.** M1's three `acid-displacement-precipitating`
    steps want the DIHYDRATE; the engine is anhydrous and the entry is named for
    what it actually is.
- ✔ ~~**UNIFAC'S MATCHER IS GREEDY WITHOUT BACKTRACKING**~~ and ~~**A SPECIES
  HELD AT GAMMA = 1 SAYS NOTHING**~~. Both CLOSED 2026-08-23, HANDOFF 80. The
  ketone SMARTS got the `;H0` they always meant (+14) and a backtracking FALLBACK
  went in behind the greedy pass (+20): 730 -> 764 of 1155, 63.2% -> 66.1%. And
  `Vessel.lle_report()` is no longer empty for a liquid held ideal.
  ⚠ What is LEFT of it:
  * **391 organics still have no decomposition**, named by atom environment in
    `validation/unifac_gap.py` PANEL 2. Going past them means a DIFFERENT MODEL
    (Dortmund, NIST-UNIFAC) with its own combinatorial term -- the basis error
    M3 exists as the warning about, and a separate argued decision.
  * ⚠ **WE STOP THREE SHORT OF THE 66.4% CEILING ON PURPOSE.** That ceiling was
    a measurement of `thermo`, and its last three species are ones thermo
    decomposes by counting hydrogens off the MOLECULE rather than off the GROUP.
    A refusal is right three times. *A number measured off another
    implementation is a measurement of that implementation, not a target.*
  * **The flag is a report, not a refusal**, and it fires at an ideal mole
    fraction of 0.003 -- where the worst measured case can move a PRINTED digit,
    not where the answer becomes wrong. The error is linear in that fraction
    with NO dead zone; there is no fraction at which the model becomes correct.
  * **Nothing salts out yet.** Within-phase electrolyte non-ideality is still
    absent, which is the Debye-Huckel item below.
- ⚠ **`exp(-a_mn/T)` OVERFLOWS BELOW 4.28 K FOR THE PSRK `H2O <-> N2` PAIR, AND
  THE RHS CLAMP `T_MIN` IS 1.0.** The clamp that protects the correlations lands
  inside the band that breaks this one, so `num_jac` probing the temperature
  column puts `inf` into the psi matrix and NaN through three matmuls. PRE-DATES
  M4 (the pair is unchanged); M4 only made a standing test reach it. **Measured
  inert** -- clipping the exponent changes no number, no timing, no residual --
  so it is reported, not refused. HANDOFF 80. The fix has a precedent in the same
  file (`gamma_ref_range`) and wants the full suite behind it.
- ✔ ~~**THE BENZOIC-ACID PREP'S PROJECTION ROUND-OFF GREW 34x.**~~ SETTLED
  2026-08-24, HANDOFF 80: it CONVERGES (1.88e-03 at rtol 1e-6 down to 1.39e-07 at
  1e-9), so it is a tolerance artefact. ⚠ **But it is NOT MONOTONE** -- the 1e-7
  rung is 34x worse than 1e-6 in the current state and outright FAILS with
  "infs or NaNs" in the pre-M4 one. A projection residual on a near-zero species
  is luck-of-the-step, so **two default-tolerance residuals are not a comparison.**
  ⚠ And the pot's tight-tolerance delicacy PRE-DATES M4: the state that fails at
  rtol 1e-7 is the old one. Left open as a known softness, not as a defect.
- **A dry, superheated flask can still produce a non-finite Jacobian.**
  PRE-EXISTING and open; NAMED by `VesselIntegrator.diagnose`. ⚠ Measured this
  session: a dry flask's largest Jacobian entry is `d(T)/d(liquid)` at -2.2e6,
  i.e. an empty flask having no thermal mass -- **not a gate**.
- **`kla = 0` with a gas headspace is still the flat-column cliff**, and it is
  what the one awkward robustness row sits on. Refuses cleanly with a diagnosis.
- **`validation/process_losses.py` is still stale since `retention` became
  `porosity`.** Not run this session either.
- **`validation/permittivity_freeze.py`**: panel 4 still does not finish inside
  ten minutes. Not cheap debt.
- **The UI has no plot, no rig, and no undo**, and no chain-2 example either --
  `chemsim/ui/examples.py` still offers four flasks and none of them is a
  chamber.
- **A settling model** would separate `k_lle`'s two jobs.
- **Debye-Huckel / Davies**; a dielectric decrement for ions; the activity basis
  for neutrals (still blocked by the 4.5 kJ/mol homologue SOURCING spread);
  UNIFAC-LLE parameters; no excess enthalpy of mixing anywhere; no viscosity
  model; crystal occlusion (bounded); nucleation barrier / metastable zone; the
  uncatalysed pathway; electrochemistry; polymers as chain-length distributions;
  solid-gas flux; `k_diss` as one global constant.
- **The carbonate anchor** (a two-water, mole-changing dissociation), which gates
  chain 1's wood-ash detour. Reasoned out above; not a data line.
- **Saturation-form rate laws (LHHW, Michaelis-Menten) -- now M10.** `orders` was
  the cheap first case of this backlog item and does NOT close it: there is still
  no site balance and no denominator term, so heterogeneous catalysis and enzymes
  have nowhere to live. But the field to hang them off now exists. ⚠ **Measured
  2026-08-24: this was the largest UNOWNED wall in the project -- 8 routes,
  including `ethanol by fermentation`, which is the oldest applied chemistry in
  the catalog.**
- ⚠ **THE UNPRICEABLE FAMILIES -- now M11, and they had no owner either.** 16
  routes touch a compound class nothing here can price: isocyanates (4),
  sulfonic acids (4), organometallics (3 -- Grignard, Wittig), pigments (2),
  azo dyes, organosilicons, sulfonamides. ⚠⚠ **RE-COST THIS BEFORE SCHEDULING
  IT. S13 TOOK ITS COSTED STARTING POINT AWAY BY DOING SOMETHING ELSE.** It read
  "10 species that need ONE measured boiling point each"; the corpus sweep closed
  eight of them and `COVERAGE_REPORT.md`'s bucket now counts **2** --
  `performic-acid` and `phenyl-radical`, neither of which has a non-estimated Tb
  in `chemicals` under either key. What is left of M11 is the FORMATION half
  (267 species with no group value in any published tabulation), which is a
  different problem with a different answer.
- ⚠ **THREE THINGS ARE NOW STATED NON-GOALS rather than silence** (MILESTONES has
  the section): photochemistry costs ONE catalog step, stereochemistry control
  costs ZERO, and absolute reaction TIME is permanently unachievable -- A-factors
  cannot be derived, only bounded against an observable or declared
  hand-authored. ⚠ The stereochemistry one has a trap attached: a template on a
  chiral centre that does not SAY what it does to that centre is a silent wrong
  answer, not an error.

## ⚠⚠ G1 -- the dropping funnel, where the PLUMBING was already there

**⚠⚠ READ THE FIRST TWO ROWS TOGETHER. They are the same finding twice: the four
things the brief asked to be BUILT already existed, and the one thing it said
came FOR FREE did not.** ⚠ **NO RHS EDIT AND NO DATA TABLE, so
`tolerance_audit.py` carries no new exposure and was NOT re-run.**

| row | value | how it is pinned |
|---|---|---|
| ⚠⚠ **the rig's `meter` edge IS a dropping funnel, and has been since Layer 5** | it delivers a set rate, it CARRIES SENSIBLE HEAT (a 270 K funnel leaves the pot at **298.13 K** where a 370 K one leaves it at **364.12 K**, on the same 0.55 mol), its reservoir empties EXACTLY (0.001 / 0.1 / 1.0 / **10 mol/s** all land the funnel on 0.0 with the pair conserved to **1e-12**), and `SET_EDGE` opens and shuts it inside a saveable scenario | `validation/dropwise.py` panels 1-2. ⚠ **`VesselConditions.feed` was REFUSED as a second home for all of it** — and a `feed_T` is a DECLARED constant where a funnel VESSEL's temperature is a solved one you can put in an ice bath |
| ⚠⚠ **"it composes with `wait_until` for free" is FALSE, and this is the row the milestone is for** | the free way discovers 340 K at **t = 20.348728 s** and records `set_edge` at that timestamp; replayed against **twice the charge** it raises `cannot schedule 'set_edge' at t=20.348728... the world is already at t=31.513289` | `validation/dropwise.py` panel 5; `test_stopping_a_drip_with_an_event_bakes_this_runs_instant_into_the_recipe`. ⚠ **The refusal is the GOOD case** — a crossing landing a hair EARLIER stays in the future and the tap shuts at an instant the run never found, silently |
| **`World.add_dropwise` stores the CONDITION** | the same protocol replays at 1x **bit-identically** (0.000e+00 K) and at 2x finds its own crossing at **31.513289 s** | `test_add_dropwise_stores_the_condition_so_the_recipe_survives_a_rescale`. Same fork `collect_fraction` was built for, same answer, argued on `World.script` |
| **SAVE_VERSION 5 -> 6** | v4 and v5 saves are refused by both `load` and `replay` | `test_the_save_format_moved_because_an_unknown_verb_fails_too_late`. ⚠ **A new VERB, not a new field**: `run_script` discovers an unknown entry part-way through the walk, so a v5 reader executes everything BEFORE it and stops holding a world that looks finished |
| ⚠⚠ **`ran_dry` is read off WHAT IS LEFT IN THE FUNNEL, not off a delivery shortfall** | the obvious `delivered < rate*elapsed` test does not survive a real funnel: with a headspace over it the donor's liquid falls FASTER than the tap takes it — **0.40799 mol delivered against a nominal 0.40702** | `test_a_funnel_that_empties_early_is_reported_rather_than_hidden`. **Two numbers that each carry their own error term cannot be subtracted to decide a third** |
| ⚠⚠ **`total / rate` is wrong twice over, and it caught its own author** | 0.2 mol of acid in 0.1 mol of water at 0.01 mol/s takes **30 s and not 20**, because a meter moves the donor's SOLUTION | `test_the_funnel_itself_can_be_what_is_watched`. The brief's derived duration would have shut the tap with a THIRD of the charge still in the funnel and reported success |
| **a non-meter edge is REFUSED** | a drain's `k` is a reciprocal residence time and a vapour edge's is mol/(bar s) | `test_a_dropwise_addition_refuses_an_edge_that_is_not_a_meter`. ⚠ `SET_EDGE` cannot catch this, because setting a conductance is what `SET_EDGE` is FOR |
| **the runaway, and it is emergent** | 1.0 mol nitric acid into 1.0 mol benzene over a 278 K bath: peak pot temperature **382.03 / 346.47 / 296.17 / 282.71 K** at taps of 0.05 / 0.01 / 0.002 / 0.0005 mol/s over 5 W/K, and **320.38 / 287.28 / 279.89 / 278.48 K** over 50 W/K | `examples/dropping_funnel.py` panels 1-2. Nobody wrote a runaway: it is `q_rxn` against `UA*(T - T_env)` |
| ⚠⚠ **SENSIBLE HEAT ALONE CANNOT DO THE VIGNETTE, and this is why the playground is a nitration** | same moles at 0.05 / 0.01 / 0.002 mol/s into an INSULATED pot: **338.422 / 338.480 / 338.567 K** — 0.15 K across a 25x rate change | `validation/dropwise.py` panel 3. The same joules arrive however fast they arrive. **A rate only matters against another rate**, so the playground needs an EXOTHERM: nitration is -141.2 kJ/mol, esterification -3.2 |
| ⚠ **a still and a drip bench cannot be one apparatus inside an example's budget** | the SAME 20-second addition: **3.9 s of wall clock on two vessels, 220 s with a head and a receiver bolted on — 56x**. And the cut was poor: the head entered the 345-368 K band at 89 s and had not left it **2911 s** later, having passed 0.016 mol | `examples/dropping_funnel.py` panel 4, which reports it instead of running it. ⚠ **NOT a missing capability** — a cut has been sayable since M2 and `fractional_distillation.py` and `plate_column.py` are both it |

## ⚠⚠ G2 -- ring deactivation, and a rho is meaningless without its SIGMA SCALE

**⚠ NO RHS EDIT — the shifted barrier is baked into the kinetics array at SETUP,
so `tolerance_audit.py` carries no new exposure and was NOT re-run.** ⚠⚠ **AND
TWO OF THE FOUR CORPUS ROWS ARE IMPROVEMENTS, WHICH THE BRIEF DID NOT PREDICT.**

| row | value | how it is pinned |
|---|---|---|
| ⚠⚠ **the endpoint used not to move with temperature AT ALL** | 1.0 toluene + 3.5 nitric acid + 5.0 water, 1 L: at rho = 0 the four stage totals are **0.0045 / 0.0303 / 0.0745 / 0.2422** at 300 K/10 s, 300 K/100 s, 340 K/10 s, 340 K/1 h AND 380 K/1000 s — the same to three figures | `validation/ring_deactivation.py` panel 3; `test_the_endpoint_used_not_to_move_with_temperature_and_now_does`, which pins BOTH blocks so removing the gap stays deliberate |
| **and now it is a three-stage process** | at rho = -6.5: **mono 0.634** at 300 K/10 s, **di 0.928** at 300 K/100 s, **di 0.997** at 340 K/10 s, **tri 0.876** at 380 K/1000 s | same panel. The escalating-temperature sequence real TNT manufacture uses, out of three barriers 25 kJ/mol apart |
| **the barrier ladder** | **48.46 / 73.47 / 98.47 / 123.48 kJ/mol** for a substrate carrying 0/1/2/3 nitro groups, from ONE declared 60 | `test_the_barrier_ladder_is_baked_at_setup_and_is_25_kJ_per_nitro_group`. ⚠ **The 25.0 spacing is not a constant anybody typed** — it is `-ln(10)*R*298.15*rho*sigma+_meta(NO2)`, and the test asserts the expression, not the literal |
| ⚠⚠ **A rho IS MEANINGLESS WITHOUT ITS SIGMA SCALE — S12's finding in another suit** | the table is **sigma-PLUS** (Brown & Okamoto 1958): methoxy is **-0.27 on sigma and -0.778 on sigma+**, amino **-0.66 and -1.30** | `test_the_scale_is_sigma_plus_and_every_proxy_row_is_an_acceptor`. Electrophilic substitution builds positive charge on the ring; a sigma+-fitted rho on aqueous sigma multiplies two bases together |
| **the two PROXY rows are both ACCEPTORS** | `sulfo` and `carboxylate-ester` have no published sigma+ and use aqueous sigma; both have sigma_m and sigma_p POSITIVE | same test, which refuses a DONOR in that set. The scales agree for acceptors (nitro 0.71/0.78 vs 0.674/0.790) and disagree by up to 0.6 for donors |
| ⚠ **anchored at 298.15 K, NOT at `T_ref`** | the same network built at 280 K and at 500 K has array-equal barriers | `test_the_anchor_is_298_K_and_not_the_networks_build_temperature`. sigma+ and rho are tabulated from 25 C rate ratios; **ask what a fit was anchored on** |
| ⚠ **`meta_directing` is DECLARED, not derived from the sign of sigma** | all four halogens have `sigma+_meta` **+0.35 to +0.41** and all four are ORTHO/PARA directors | `test_the_directing_rule_is_declared_because_the_halogens_break_the_obvious_one` |
| ⚠⚠ **rho and alpha may not be declared together** | benzene -> nitrobenzene is **-141.2 kJ/mol** and nitrobenzene -> dinitrobenzene is **-268.1**, so a positive alpha makes the DEACTIVATED ring react FASTER | `test_a_rho_and_an_alpha_may_not_be_declared_together`. S11's Evans-Polanyi trap, arriving on a ring |
| **an unsubstituted ring keeps the declared barrier BIT FOR BIT** | `Ea`, `A` and `delta` all `array_equal`; `barrier_shift` returns a literal `0.0` (`repr` == `"0.0"`) | `test_an_unsubstituted_ring_keeps_the_declared_barrier_bit_for_bit`. ⚠ Capped at **FOUR** species on purpose — five lets a dinitrobenzene in, and the first draft reported "not identical" while printing two numbers that both read 60000.000000 |
| **the corpus cost, all four measured** | `tnt-route` **0.1528 -> 0.0662** mol (worse and righter — real TNT needs ~380 K); `benzene-nitration` **0.1762 -> 0.8000**; `picric-acid-route` **0.0481 -> 0.1208**; `ddt-route` **unchanged** | `test_deactivation_lets_a_mononitration_stop`; `examples/named_routes.py`. ⚠ **Two of the four are IMPROVEMENTS, because a mononitration can now STOP** |
| **+0 classes, +0 templates, +0 on the BOTH column** | all four catalog artefacts came out byte-identical | `git status data/` after `catalog_coverage.py` and `build_route_index.py`. Predicted before running: a barrier is not a template |
| ⚠⚠ **NO REGIOSELECTIVITY, and it is named rather than discovered** | each rung of the ladder is ONE number, so all three dinitrobenzenes are still made at the same rate | `reactions/hammett.py`, "three things this does NOT do". The sum has no attacked carbon in it; a `ConcreteReaction` is a pair of SMILES tuples and the site is discarded before the barrier is computed. **A builder change, not a data one** |
| ⚠⚠ **NO PROTONATION — a LIMIT to remove, not an invariant to keep** | aniline is priced as a FREE BASE at **2.8e8 x benzene**, where the real anilinium ion in mixed acid is meta-directing and SLOWER than benzene; 4-aminophenol's Σσ+ of **-2.220** is a **-82.4 kJ/mol** shift and drives the barrier through zero | `test_a_barrier_may_not_go_negative_and_the_floor_is_reachable`; `hammett.clamp_barrier`, and `build_network` emits a NOTICE naming the missing physics. **⚠⚠ SUPERSEDED BY G5: the split was BUILT, it moved 2.8e8 -> 380 x benzene, and the residual is NOT the protonation. Read the G5 block.** |
| ⚠ **and where it is measurably wrong is printed beside the successes** | toluene predicts `k/k0` = **105** against a measured **~25** — 4x high, out of a one-parameter model whose rho is quoted over a -6.0 to -7.3 band | `validation/ring_deactivation.py` panel 1 |
| ⚠ **an unsourced substituent is REPORTED, not priced at zero in silence** | aspirin's acetoxy oxygen has no sigma+ sourced here, so the survey returns it in `unknown` and `build_network` says the barrier is a bound rather than a value | `test_an_ester_oxygen_on_the_ring_is_reported_rather_than_priced_as_a_methoxy`. Pricing it as a methoxy would make aspirin's ring more reactive than anisole's |
| the whole suite | **995 passed / 0 failed in 22:06**, run AFTER every `src/` edit and with **NOTHING else on the CPU** | `python -m pytest -q`. ⚠⚠ **AND IT REFUTES S13's EXPLANATION OF ITS OWN CLOCK.** S13 measured 21:36 against S12's 13:20 and attributed it to CONTENTION; this uncontended run is 22:06, within 30 s of it. The 30 tests added this session are **47 s combined** (35.1 + 12.4), so they are one of the eight minutes. ⚠ **The cause is NOT measured** -- the likeliest candidate is S13's data regeneration moving every trajectory's stiffness, but nobody has bisected it and `pytest --durations=25` has never been run |
| **the nitration templates are audited now** | activated nitration's fastest constant is **1.0e10, one tenth of the collision ceiling**; the deactivated network's is 3.24e-10 of it | `validation/rate_ceiling.py` gained two networks. ⚠ It is the ONE template whose barrier is not the one it declares, and the floored case is where `A` IS the rate |

## ⚠⚠ G5 -- protonation, where the SPLIT was right and the FLASK could not get there

**⚠⚠ READ THE FIRST THREE ROWS TOGETHER. They are one finding: the split is the
correct model, its own arithmetic reproduces the acidity real aniline nitration
needs, and this engine cannot express that acidity — so the LIMIT IS RENAMED, not
removed.** ⚠ **NO RHS EDIT AND NO DATA-TABLE SHIFT (the 24 anions are
bit-identical), so `tolerance_audit.py` carries no new exposure and was NOT
re-run.**

| row | value | how it is pinned |
|---|---|---|
| ⚠⚠⚠ **the two channels cross at pH -9.42, and that is NOT a wrong number** | free base sigma+ **-1.300** -> k/k0 **2.8184e+08**; anilinium sigma **+0.860** -> **2.5704e-06**; ratio **1.10e14**, so the crossover is at `Ka*k_free/k_ion` = **2.630e+09 mol/L**. Real aniline gives largely META product only in 90-98% sulfuric acid, whose **H0 falls to roughly -8 at 90 wt% and roughly -10 at 98 wt%** (quoted to ONE FIGURE because it is recalled, not sourced here -- the claim is that -9.42 is INSIDE the band) | `test_the_crossover_acidity_is_ten_decades_below_what_the_engine_can_reach`; `validation/protonation.py` panel 3. **The engine's own two table rows land the crossover inside the measured band without being told about it** |
| ⚠⚠⚠ **and the pot gets LESS acidic as the acid gets DRIER — nobody had measured this** | 5 + 5 mol HNO3/H2SO4 in 30 mol water reads **pH -0.789**; in 10 mol **-0.233**; in 2 mol **+4.899**. **The reachable floor is about pH -0.79** | `test_a_drier_acid_is_a_less_acidic_pot`; panel 4. ⚠ **NOT a solver artefact** — every dissociation here is written with water on BOTH sides, so `[H2O]` is a mass-action factor. Real: dry sulfuric acid autoprotolyses to H3SO4+/HSO4- and is not a source of hydronium |
| ⚠⚠ **THE LIMIT IS "NO ACIDITY FUNCTION", not "no protonation"** | the floor is **ten decades** above the crossover, and H0 is not the concentration of anything | the two rows above, together. ⚠ **When somebody gives this engine an acidity function the crossover test FAILS, which is the intent** |
| **what the split DOES buy: six of fourteen decades** | at pH **-0.667** the aniline is **100.000% anilinium** and the effective rate is **380 x benzene** against 2.8e8 | `test_the_split_moves_six_decades_and_leaves_eight`; panel 5. ⚠ The sigma sums are read out of `survey` and NOT out of literals — the first draft hard-coded them and survived deleting the table row |
| ⚠⚠ **and the other eight decades are NOT in the protonation model** | the anilinium is 100.000% of the aniline present and carries **1e-7 %** of the rate. The residual is a FREE-BASE LEAK at 1e-6 mole fraction | same test. `rho*sigma+` = **8.45 decades** off a line fitted on arenes with `|rho*sigma| < 2.6` — a 3.25x extrapolation. Real nitration of an activated arene is **ENCOUNTER-CONTROLLED** and the Hammett line SATURATES; a declared saturation of 1e4/1e5/1e6 lands aniline at **1.35e-2 / 1.35e-1 / 1.35** x benzene. ⚠ **The constant needs its own sourcing session and is NOT asserted** |
| ⚠ **and no existing audit can catch that** | `detailed_balance`'s cap compares the PRE-EXPONENTIAL; hammett moves `Ea`. With A = 1e10 and the barrier clamped at zero the ceiling is 1e10, **one decade under** the 1e11 limit | panel 5's last note. **Fragility 13 in a new suit** |
| ⚠⚠⚠ **FOUR CURATED ION ROWS HAD BEEN PRODUCING NOTHING, and a generated report printed the refusal twelve times** | ammonium 9.25 / methylammonium 10.66 / pyridinium 5.23 / anilinium 4.62 are CATION/neutral pairs whose acid IS the ion; `ion_thermochemistry` anchored on the ACID and `anchored()` refuses a charge, and a bare `except Exception: continue` swallowed all four. **24 anions, one hard-coded hydronium, no cation at all** | `test_every_cation_neutral_pair_is_priced_and_they_used_not_to_be`; panel 1. ⚠ `COVERAGE_REPORT.md` had been printing `refusing to price '[NH4+]'` for twelve corpus salts, session after session, where it read as an ordinary Born-domain refusal |
| **the corpus cost, and it is a GAIN nobody predicted** | refused species **430 -> 419**; ion-resolvable **84 -> 95**; species-ready routes **80 -> 82**; `solvay-process` **0 -> species-ready**. Every ammonium salt in the catalog moved | `git diff data/catalog/` after `catalog_coverage.py`. ⚠ **BOTH is unchanged at 31/173**, classes at 51, templates at 46 — a data fix is not a template |
| ⚠ **the 24 anions are BIT-IDENTICAL, and the grouping of one sum is why** | folding the pKa term and the solvent correction into a single `dG_diss` before adding it moved **ten of the 24 in the last bit** | `test_an_anion_is_still_anchored_on_its_acid_bit_for_bit`, which asserts `==` against the exact expression in the old grouping. Floating-point addition is not associative, and a data table that shifts by 1e-16 owes `tolerance_audit.py` ten minutes |
| ⚠⚠ **`ammonium_dissociation` could not deprotonate an ammonium** | `[NX4H+]` is N with EXACTLY ONE hydrogen: measured **False** against `[NH4+]`, anilinium, methylammonium and pyridinium, **True** only against `C[NH+](C)C` | `test_the_old_pattern_could_not_deprotonate_an_ammonium`, kept as a regression guard. **The template named for the ammonium ion was the one ion it could not touch**, and nothing in the corpus can put a trialkylammonium in a flask to catch it |
| **`amine_protonation` is written PROTONATION-forward** | it protonates an aryl amine, ammonia, an alkyl amine and 4-aminophenol; it leaves an amide, a nitro group, **a pyridine**, a nitrile and an alcohol alone (all five return `[]`) | `test_what_amine_protonation_protonates` / `..._leaves_alone`. ⚠ Discovery is FORWARD-ONLY, so a deprotonation-forward template can only find an anilinium in a flask that already has one — **the `ester_hydrolysis` decision again** |
| ⚠ **`[OX2H2;+0:2]` and not `[OX2H2:2]`** | a mapped atom keeps its formal charge, so the un-annotated form hands back water with **+1** on it, `_element_charge_balance` drops the rewrite, and the template silently does nothing | the same tests assert `WATER in products`. **The bug's symptom is a no-op, not a wrong number** |
| ⚠⚠ **the `ammonio` row is the one whose two constants INVERT, and it is the second reason `meta_directing` is declared** | -NH3+ is **0.86 / 0.60**, so `meta_directing=True` picks the LARGER where nitro's 0.674/0.790 picks the smaller. A rule of "meta iff sigma_p > sigma_m" would call an anilinium an ortho/para director | `test_the_ammonio_row_is_the_one_whose_two_constants_invert`, which also re-asserts the halogens failing the same rule the other way |
| ⚠ **it is a labelled PROXY and no sigma+ for it can exist** | aqueous sigma, on `sulfo`'s argument: -NH3+ has all three of nitrogen's hydrogens and NO lone pair to donate, which is exactly where the two scales agree. The Brown-Okamoto scale is built from substitution rates and an anilinium must be measured in acid strong enough that H0 is the variable | `test_the_ammonio_row_is_a_labelled_proxy_and_is_meta_directing` |
| ⚠ **an aryl QUATERNARY ammonium is REPORTED, not priced from that row** | `C[N+](C)(C)c1ccccc1` comes back `found=()`, `unknown=('-N on an aromatic carbon',)` | `test_a_quaternary_aryl_ammonium_is_reported_and_not_guessed`. The aspirin-acyloxy precedent |
| ⚠⚠ **a protonation TEMPLATE is open-ended where the ion table is a CURATED LIST — a new structural mismatch, and the REFUSAL IS KEPT** | aniline + nitric acid + `dissociation_templates()` raises on `[NH3+]c1ccccc1[N+](=O)[O-]`, a nitroanilinium nobody curated | `test_a_protonation_template_over_a_curated_ion_table_refuses`; panel 6. ⚠ **Curating the nine pKa values is MEASURED to buy nothing** — the ion channel carries 1e-7 % of the rate, so a network that built would report a direct aniline nitration at up to 1e3 x benzene. The element floor's rule, applied to a pKa |
| ⚠ **the pyridinium is PRICED and still UNREACHABLE** | the ion is in the table; an aromatic ring nitrogen is **X2** and `amine_protonation` matches X3, so `tmpl.run` on pyridine returns `[]` | `test_the_pyridinium_is_priced_and_still_unreachable`. ⚠ The thing to measure first is the **Skraup**, whose product is a pyridine ring in hot sulfuric acid — though measured, `validation/skraup.py` builds from `quinoline_chemistry()` alone (ONE template, no dissociation), so the coupling is CONDITIONAL on somebody adding the bundle there rather than automatic |
| ⚠⚠ **PROTECTING THE AMINE IS EMERGENT, and it is the playable result** | benzene 60.00 / **aniline 11.77** / **anilinium 91.91** / **acetanilide 37.74** kJ/mol from ONE declared 60. Aniline + anhydride at 330 K/30 min gives **1.00000 acetanilide**, and the acetanilide network **BUILDS (21 species)** where the aniline one refuses: 0.5331 mono / 0.4669 dinitro at 300 K/10 min | `test_protecting_the_amine_is_emergent_and_runs`; panel 7. **Nobody told the engine that an amide is a protecting group** — `acylamino`'s sigma+ of -0.600 and a nitrogen that does not answer the protonation pattern, both already declared |
| ⚠ **and the isomer ratio is still flat — G2's other named limit, now ASSERTED** | ortho and meta nitroacetanilide come out at **0.1535 each** against a real ~90% para | the same test asserts `ortho == approx(meta)`, so closing the regioselectivity gap breaks a test rather than going unnoticed |
| ⚠ **a positional index into `hammett._TABLE` broke, and its own guard caught it** | `test_ring_deactivation` read `_TABLE[0]` with `assert label == "nitro"` under it; the new row went in at the top of the meta-directing block and it failed in one run | now looked up by LABEL. Position in that tuple is a SMARTS-precedence decision (most specific first) and was never a key that test had an opinion about |
| the whole suite | **1024 passed / 0 failed in 22:28** (995 at G2; the +29 are `tests/test_protonation.py`) | `python -m pytest -q --durations=25`. ⚠ Run after every BEHAVIOURAL `src/` edit, but two docstring-only edits and one test RENAME landed while it ran plus a 12.8 s single-file re-run on another core — **22:28 is an upper bound with minor contention in it and is reported that way**; the renamed test was re-run green alone |
| ⚠⚠⚠ **`--durations=25` FINALLY RAN, AND THE COST IS CONCENTRATED** | top 25 = **803.1 s of 1348.3 (59.6%)**; `test_still.py`'s six rows = **402.2 s (29.8%)**; ONE test (`test_temperature_steady_on_a_RIG_vessel`) = **164.1 s (12.2%)**; the other **999 tests share 545 s — 0.55 s each** | the same run. ⚠⚠ **IT DOES NOT DIAGNOSE THE S12->S13 SLOWDOWN and must not be read as doing so: a durations list with NO BASELINE cannot attribute a regression.** The SHAPE re-ranks two hypotheses — a broad stiffness change should not leave 999 tests at 0.55 s while one RIG test takes 164 — but it measures neither. The cheap next step is a stash-and-rerun across S13's data commit, now that a list exists to diff against |
| ⚠ **and one standing claim was cross-checked for free** | the burner at rtol 1e-8 measured **52.47 s**, against fragility 10 and engine queue item 15's *"~50 s"* — and it is **3.9% of the whole suite** | the same run. The claim was right |

## ⚠⚠ G4 -- the granularity audit, where the INSTRUMENT SCORES ROWS and a route is a DAG

**⚠⚠ THE HEADLINE IS THAT THE NUMBER IS SMALL.** Five routes are scored
blocked and run today; 142 sit outside the BOTH column, so **4% of them are
catalog bookkeeping and 137 are real work.** The BOTH column was not hiding a
content backlog. ⚠ **NO `src/` EDIT** — `validation/catalog_coverage.py`
plus two new files — so `tolerance_audit.py` carries no new exposure and was
NOT re-run, and the suite baseline is still G5's.

| row | value | how it is pinned |
|---|---|---|
| ⚠⚠⚠ **five routes are scored blocked and RUN, and each is a MEASUREMENT** | `benzene-nitration` **1.000000** mol nitrobenzene; `aniline-route` **0.998860** aniline; `hydrogenation-margarine` **1.000000** tristearin; `tanning-route` **1.999999** gallic acid; `lead-chamber` **0.104063** sulfuric acid | `tests/test_granularity.py`, one test each; `validation/granularity.py` panel 4. **Nothing here is credited on an argument** — S1's *"crediting a class made a FALSE route credit"* is the reason |
| ⚠⚠⚠ **the brief's own worked example is NOT in the bucket the brief points at** | `benzene-nitration` is **species**-blocked: `nitronium` and `arenium-benzene` are refused a price, correctly | panel 1. Walking the species-ready-but-not-template-ready bucket — the obvious search — **would have missed the case that started the audit.** Granularity is STEP granularity **and** SPECIES granularity |
| ⚠⚠ **the instrument scores ROWS; a route is a DAG with alternatives, byproducts and workup in it** | four of the five are blocked by a row that is not on the path to the target: ALTERNATIVE (`aniline-route`), declared BYPRODUCT (`hydrogenation-margarine`), a MARKER past the target (`tanning-route`), the FOULING product (`lead-chamber` row 4, chamber crystals) | panel 3. ⚠ **The corpus says so in its own prose and nothing had read it**: 9 rows in 8 routes are named `... byproduct`/`side reaction`/`alternative` |
| ⚠⚠ **five corpus rows can never match ANY template, whatever anyone builds** | products are a **subset** of reactants: `leblanc` 3 lixiviation, `nitroglycerin` 2 kieselguhr, `aspirin` 2 crystallisation, `soap` 2 salting-out, `furfural` 1 (`xylose + water -> xylose`) | `test_the_corpus_still_has_rows_that_make_nothing_new`, which asserts the count **and** the five route ids; panel 2a. They are workup, not chemistry |
| ⚠⚠⚠ **a reachability scorer that does not forbid CHARGING THE TARGET credits every recycle loop** | before the rule it said **38**, crediting `bayer-process` and `contact-process` — in both the target is also a step-1 reactant. Bayer PURIFIES bauxite; the contact process recycles its own acid. With the rule, **36** | panel 3's closing block, which prints both false credits. **The rule is one line and it is the difference between an instrument and a flattering one** |
| ⚠⚠⚠ **and the scorer's LAST survivor was refuted by RUNNING it** | `starch-hydrolysis` scored reachable; the engine builds **ZERO reactions** from its declared feedstock. `starch-unit` is a single α-D-glucopyranose ring and row 1 reads `starch-unit + water -> maltose` — a hydrolysis making a disaccharide from a monosaccharide | `test_starch_hydrolysis_is_refuted_from_its_declared_feedstock` asserts `net.reactions == []`. ⚠ From MALTOSE the same template gives **0.9986** mol glucose (`..._reaches_glucose_from_the_intermediate`), so the blockage is the corpus's spelling of its own FEEDSTOCK and **no engine work would move it** |
| ⚠⚠ **`saponification` was a catalog class the coverage map had never keyed** | the M5 template was credited under `ester-hydrolysis`'s name, so `soap-saponification` step 1 read as an uncovered mechanism for eight milestones. Classes **51 -> 52**, steps **114 -> 115**, one-class-away routes **46 -> 47** from **36 -> 37** classes | `test_saponification_fires_on_the_catalog_s_own_substrate` — tristearin + hydroxide, 10 species, 7 saponification reactions, all three esters off down to glycerol. ⚠ **+0 template-ready and +0 BOTH**: `salting-out` is a phase split and `sodium-stearate` is REFUSED (no stearate pKa) |
| ⚠ **the BOTH column in `COVERAGE_REPORT.md` still says 31, DELIBERATELY** | that table is a mechanical measure of the CORPUS; the five rest on a hand judgement about five specific rows | the report gained a **pointer** to `validation/granularity.py` instead. **Folding a judgement into a mechanical column is how M1's `deprotonation` credit happened** |
| ⚠ **hoisting a provider out of a comprehension took this audit 290 s -> 18 s** | `electrolyte_provider(...)` inside a dict comprehension over 1583 compounds constructs one provider per compound | measured on the first version of `granularity.py`; the comment is in the file. A 16x cost with no visible symptom but the clock |
