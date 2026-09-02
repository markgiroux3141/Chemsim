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
