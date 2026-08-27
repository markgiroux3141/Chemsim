We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M6, M8, M12, S1–S13, G1, G2 and G5 are DONE.**

⚠⚠⚠ **THE ARC IS THE G-SERIES.** The catalog is a measuring instrument and was
being read as a specification; the goal is a connected tech tree a player can
walk from natural materials. **Read MILESTONES § THE G-SERIES.** Coverage is
DEFERRED to a C-series, not cancelled.

# ⚠ THE BASELINE IS MEASURED. DO NOT START WITH THE SUITE.

**G5 RAN THE WHOLE SUITE AT THE END AND MEASURED 1024 PASSED / 0 FAILED IN
22:28.** Take that number and spend the time on content. ⚠ It was run AFTER every
BEHAVIOURAL `src/` edit — sixth session running that is true. (995 at G2; the +29
are G5's `tests/test_protonation.py`.) ⚠ **Two DOCSTRING-ONLY edits and one test
RENAME landed while it ran**, plus a 12.8 s single-file re-run of
`test_ring_deactivation.py` on another core; the renamed test was re-run green on
its own afterwards. **So 22:28 is an upper bound with minor contention in it, and
it is being reported that way rather than as a clean figure.**

⚠⚠⚠ **AND `--durations=25` WAS FINALLY ATTACHED TO IT — THE PROBE THIS FILE HAS
SAID FOR TWO SESSIONS HAD NEVER BEEN RUN.** The cost is **CONCENTRATED, NOT
BROAD**:

    top 25 tests                                        803.1 s of 1348.3  (59.6%)
    tests/test_still.py, its six rows in the top 25      402.2 s            (29.8%)
    ONE test -- test_temperature_steady_on_a_RIG_vessel  164.1 s            (12.2%)
    test_catalysis::test_a_catalysed_esterification       74.1 s             (5.5%)
    the burner at rtol 1e-8 (engine queue item 15)        52.5 s             (3.9%)
    the OTHER 999 tests                                   545   s   -- 0.55 s each

⚠⚠ **AND THIS DOES NOT DIAGNOSE THE S12->S13 SLOWDOWN, WHICH IS THE WHOLE POINT
OF SAYING IT OUT LOUD. A DURATIONS LIST WITH NO BASELINE CANNOT ATTRIBUTE A
REGRESSION** — nobody has the same list from S12, so the eight minutes remain
unattributed. What the shape DOES say is that a per-test story is at least as
plausible as the standing candidate (*"S13's measured-physical table moved every
trajectory's stiffness"*), because a broad stiffness change should not leave 999
tests averaging 0.55 s while one RIG test takes 164. **That is a re-ranking of two
hypotheses, not a measurement of either.**
⚠ The cheap next step, if the clock ever matters, is a `git stash`-and-rerun of
`--durations=25` across S13's data commit — which is finally possible now that a
list exists to diff against.
⚠ **The burner row is a live cross-check that landed for free**: fragility 10 and
engine queue item 15 both say *"~50 s at rtol 1e-8"*, and it measured **52.47 s**.
The claim was right and it is 3.9% of the suite.

⚠ **G5 TOUCHED NO RHS AND SHIFTED NO DATA TABLE — the 24 pre-existing ion-table
anions are BIT-IDENTICAL and that is asserted in a test** — so
`tolerance_audit.py` was not owed and was NOT re-run. Its last measured state is
S13's and every warning in §S13 about it still stands.

```bash
python validation/protonation.py                # ⚠ G5's, 18 s. NEW -- read panels 3, 4 and 5
python validation/ring_deactivation.py          # G2's, ~25 s. READ PANEL 3
python validation/dropwise.py                   # G1's, 78 s
python validation/boiling_points.py             # S13's, 2 s. READ PANEL 2
python validation/skraup.py                     # S12's, ~10 s
python validation/smelting.py                   # S9's, ~1 min
python validation/hydroformylation.py           # S11's, ~1 min
python validation/wacker.py                     # S11's other one, ~1 min
python validation/gas_processes.py              # S7's, ~1 min
python validation/corpus_balance.py             # S7's other one, ~20 s. READ IT before picking
python validation/catalog_coverage.py           # ⚠ READ THE 'BOTH' LINE: 31/173, ~15 s
python validation/physical_estimation.py        # S13 took its panel 3 to n=254
python validation/game_gates.py                 # the element floor's cross-check, seconds
python tools/build_route_index.py               # the artefact nothing reads
python validation/cell_potentials.py            # M8's standing audit, seconds
python validation/rate_ceiling.py               # ⚠ G2 added TWO NETWORKS to it
python validation/jacobian_bound.py             # S5's standing audit, ~1 min
python -m ruff check src tests examples validation tools
python -m pytest -q                             # ONLY after touching src/
python validation/tolerance_audit.py            # ~10 min. After touching the RHS **or any data table**
```

⚠ **THE SUITE AND THE TOLERANCE AUDIT ARE MINUTES OF SATURATED CPU ON THE USER'S
OWN MACHINE.** Say what a long run will cost before starting one, and ask.
`examples/plate_column.py` alone is 12 minutes.

---

# ⚠⚠⚠ WHAT G5 TURNED OUT TO BE

**G2 posed protonation as a design question — *"is it a barrier shift or a species
split? Measure that before designing a coupling"* — and the question was the right
one. It is a species split, the table row is three lines, and THE ARITHMETIC
BOUND TAKEN FIRST SAYS THE SPLIT DOES NOT FIX ANILINE.**

## ⚠⚠⚠ 1. THE CROSSOVER IS AT pH −9.42, AND THAT IS NOT A WRONG NUMBER

    free base   -NH2   sigma+ -1.300   k/k0 = 2.8184e+08
    anilinium   -NH3+  sigma  +0.860   k/k0 = 2.5704e-06     ratio 1.10e14

    crossover at [H3O+] = Ka * k_free / k_ion = 2.630e+09 mol/L,  pH -9.42

Real aniline gives largely **meta** product only in 90–98% sulfuric acid, whose
Hammett acidity function **H0 falls to roughly −8 at 90 wt% and roughly −10 at
98 wt%**. ⚠ The band is quoted to ONE FIGURE because it is recalled from a
standard H0 table rather than sourced in this repo — the claim being made is that
**−9.42 lands INSIDE the band real aniline nitration is run in**, not that it
matches a tabulated value. The engine's own two table rows land it there without
being told about it. **The split is the right model.**

## ⚠⚠⚠ 2. AND THE WALL IS A SECOND MEASUREMENT NOBODY HAD TAKEN: A DRIER ACID IS A LESS ACIDIC POT

    5 + 5 mol HNO3/H2SO4 in  30 mol water  ->  pH -0.789   <- the FLOOR
    the same acid in         10 mol water  ->  pH -0.233
    the same acid in          2 mol water  ->  pH +4.899

Every dissociation in this project is written with water on **both** sides — a
standard-state decision in `properties/electrolyte`'s docstring — so `[H2O]` is a
mass-action factor and running out of water SUPPRESSES the reaction that makes the
proton. ⚠ **NOT a solver artefact**: dry sulfuric acid autoprotolyses to
H3SO4+/HSO4− and is not a source of hydronium.

⚠⚠ **THE REACHABLE FLOOR IS pH −0.79, TEN DECADES ABOVE THE CROSSOVER. SO THE
LIMIT IS RENAMED, NOT REMOVED: it is not "no protonation in a barrier" any more,
it is "NO ACIDITY FUNCTION"** — H0 is not the concentration of anything and a
molarity cannot reach 1e9 mol/L. That is a better-posed gap than the one G2 named.

## ⚠⚠ 3. WHAT THE SPLIT BUYS: SIX DECADES OF FOURTEEN, AND THE OTHER EIGHT ARE ELSEWHERE

At pH −0.667 the aniline is **100.000% anilinium** and the effective rate is
**380 × benzene** against 2.8e8. ⚠⚠ **And the anilinium carries 1e-7 % of it** —
every remaining decade is a FREE-BASE LEAK surviving at 1e-6 mole fraction.
**Fixing the FRACTION cannot fix that.** See §ITEM 2 below.

## ⚠⚠⚠ 4. THE BIGGEST ACTUAL PAYOFF WAS A DEAD TABLE, PRINTED IN A GENERATED REPORT TWELVE TIMES

`ion_thermochemistry` anchored every pair on its **ACID**. Four rows of `_PAIRS`
are CATION/neutral pairs whose acid IS the ion (ammonium 9.25, methylammonium
10.66, pyridinium 5.23, anilinium 4.62); `anchored(pair.acid)` refused all four —
loudly and correctly, Joback and Benson are fitted to neutral molecules — and a
bare `except Exception: continue` swallowed it. **The table shipped 24 anions, one
hard-coded hydronium, and no cation at all.**

    refused species  430 -> 419      species-ready routes  80 -> 82
    ion-resolvable    84 -> 95      `solvay-process`  0 -> species-ready

Every ammonium salt in the catalog moved. ⚠⚠ **AND `COVERAGE_REPORT.md` HAD BEEN
PRINTING `refusing to price '[NH4+]'` FOR TWELVE OF THEM, SESSION AFTER SESSION**,
where it read as an ordinary Born-domain refusal. ⚠ The refusal message even said
*"add the conjugate acid to `_PAIRS` if it is not there"* — **and it WAS there.**
A refusal that names the wrong fix is worse than one that names none; the message
now says that for a cation the neutral member is the BASE.

## ⚠⚠ 5. AND `ammonium_dissociation` COULD NOT DEPROTONATE AN AMMONIUM

`[NX4H+]` is N with **exactly one** hydrogen in SMARTS — measured False against
`[NH4+]`, anilinium, methylammonium and pyridinium, True only against
`C[NH+](C)C`. **The template named for the ammonium ion was the one ion it could
not touch**, and nothing in the corpus can put a trialkylammonium in a flask to
catch it. Replaced by `amine_protonation`, written PROTONATION-forward because
discovery is forward-only.

## ⚠⚠ 6. THE PLAYABLE RESULT WAS ALREADY BUILDABLE: PROTECT THE AMINE

    benzene              sum(sigma) + 0.000   Ea 60.00 kJ/mol   k/k0 1.0000e+00
    aniline, free base   sum(sigma) - 1.300   Ea 11.77 kJ/mol   k/k0 2.8184e+08
    anilinium            sum(sigma) + 0.860   Ea 91.91 kJ/mol   k/k0 2.5704e-06
    acetanilide          sum(sigma) - 0.600   Ea 37.74 kJ/mol   k/k0 7.9433e+03

Nobody nitrates an aniline — you acetylate it, nitrate the acetanilide, hydrolyse
the amide off. `n_acylation` and the `acylamino` σ⁺ row already existed, and an
amide does not answer `amine_protonation`'s pattern, **so the acetanilide network
BUILDS (21 species) where the aniline one refuses.** Nobody told the engine that
an amide is a protecting group.

---

# ⚠⚠⚠ START HERE: THE G-SERIES IS THE WORK ORDER

⚠⚠ **READ `MILESTONES.md` § THE G-SERIES.** G1, G2 and G5 are marked done there
with what they actually turned out to be.

## ⚠⚠⚠ THE RECOMMENDED ORDER, AND THE REASON, BECAUSE IT IS NOT THE OBVIOUS ONE

    1. G4 -- the granularity audit           <- START HERE. cheap, and it
                                                MEASURES THE INSTRUMENT the
                                                other two are scored against
    2. THE HAMMETT LINE SATURATES            <- the interesting one, and G5
                                                already did its arithmetic
    3. G3 -- PLAYABLE.md                      <- the scoreboard the GOAL needs,
                                                and the expensive one

⚠⚠ **G4 GOES FIRST FOR M1's REASON, NOT BECAUSE IT IS THE BEST WORK.** The
saturation item is more interesting and G4's answer does not change its value one
bit — but G4's answer *could* change what content is worth building at all, and
every session that spends itself against an unmeasured scoreboard is a session
that may have been aimed at a gap that is not a gap. M1 came before the content
work for exactly this reason, and MILESTONES records that the measurement taken
first CHANGED the milestone in four of five cases.

⚠ **THE COUNTER-ARGUMENT, STATED SO THE CHOICE IS A CHOICE:** the G-series exists
because *"the catalog is a measuring instrument and was being read as a
specification"*, and G4 is more instrument work on that same instrument — which is
the trap §"the shape of the plan" names (*"right work, wrong scoreboard, and the
content queue is still untouched since M5"*). If this session wants to move the
GAME rather than the number, take the saturation item and leave G4. **Both are
defensible; pick deliberately and say which.**

## ⚠⚠ ITEM 1 (RECOMMENDED START): **G4 — the granularity audit**  *(possibly free routes)*

How many routes are, like `benzene-nitration`, chemically runnable but scored as
blocked because the catalog spells a mechanism out in steps the engine does in
one? **Nobody has counted.** Until someone does, the BOTH column (**31/173**) is
an unknown amount too low, and every content session is aimed with it.

**The worked example that started this, and it is the template for the audit.**
`benzene-nitration` is written as a three-step arenium mechanism
(`nitronium-generation`, `electrophilic-aromatic-substitution`,
`arenium-deprotonation`), so it scores as NOT template-ready — while the engine
nitrates benzene quantitatively today:

    benzene 1.0 + nitric acid 1.2, 340 K, 2 h
      benzene left  0.0000     NITROBENZENE  1.0000 mol     conservation clean

⚠ **THE INSTRUMENT IS `validation/catalog_coverage.py` AND IT ALREADY KNOWS WHICH
CLASS EACH STEP WANTS**, so the question is answerable without new machinery:
walk the routes that are species-ready but NOT template-ready, and for each ask
whether the engine's existing templates take the OVERALL transformation even
though no single template matches the catalog's step. ⚠⚠ **AND THAT LAST CLAUSE
IS THE WHOLE DIFFICULTY** — it is not a string comparison, so a mechanical answer
is not available and each candidate has to be read.

⚠⚠ **RUNNABLE IS THE ONLY HONEST TEST, AND S7 ALREADY RECORDED WHY: `RUNNABLE`
CANNOT ASK WHETHER A NUMBER IS RIGHT.** So the deliverable is a COUNT plus a
NAMED LIST, not a re-scored headline — crediting a route because a network builds
is exactly the false credit S1 made (`chemsim-surface-reactions`: *"crediting a
class made a FALSE route credit"*). ⚠ If the audit wants to move the BOTH column,
it has to say per route what it ran and what came out.

⚠ **AND M1 IS THE PRECEDENT FOR THE OUTCOME BEING NEGATIVE**: M1 fixed the
instrument and the corrected baseline went DOWN (33/377 steps), because *"a class
must name a MECHANISM not an outcome"*. **A G4 that finds few free routes is a
successful G4** — it retires an unknown that is currently inflating every plan.

## ⚠⚠ ITEM 2: **THE HAMMETT LINE SATURATES**

G5 created this, measured its arithmetic, and deliberately did not build it
because the CONSTANT needs sourcing.

**The gap, measured.** `rho * sum(sigma+)` for aniline is −6.5 × −1.30 = **8.45
decades**, extrapolated off a line fitted on arenes with |σ⁺| < 0.4 (toluene, the
xylenes, the halobenzenes), i.e. **|rho·sigma| < 2.6**. That is a 3.25x
extrapolation of the abscissa, and the real relation does not go there: nitration
of a strongly activated arene is **ENCOUNTER-CONTROLLED**, so mesitylene, anisole
and phenol all react at one rate and the Hammett line SATURATES.

**What a declared saturation would buy, measured in the engine's most acidic
flask:**

    saturation 1e4  ->  aniline at 1.35e-2 x benzene
    saturation 1e5  ->  aniline at 1.35e-1 x benzene
    saturation 1e6  ->  aniline at 1.35e+0 x benzene

— against a real anilinium **slower** than benzene. ⚠ A saturation near 1e5 lands
aniline within a decade or two of benzene instead of eight above it, **on ONE
declared field**.

⚠⚠⚠ **BUT THE DESIGN QUESTION IS WHICH OF TWO THINGS IT IS, AND THEY COST
DIFFERENT AMOUNTS. ASK THIS BEFORE WRITING ANY CODE.**

* **A capped RATIO** — clamp `|rho * sum(sigma+)|` at a declared number of
  decades. Lives at SETUP exactly like `hammett_rho`, bakes into the kinetics
  array, **no RHS edit and no tolerance-audit exposure.** ⚠ But it asserts that
  the ceiling is a fixed *selectivity*, so the capped substrate stays a fixed
  multiple of benzene at every temperature — and a real encounter limit does not
  behave that way.
* **An absolute ENCOUNTER CEILING** — the physically correct statement. Nitration
  of an activated arene saturates because the reaction happens on every encounter,
  so the ceiling is a *diffusion rate* (roughly `A_enc`, weakly
  temperature-dependent) and NOT a ratio to benzene. ⚠⚠ That is a **rate-law
  change**: `min(k_hammett, k_enc)` cannot be baked into an `Ea` because the two
  have different temperature dependences, so it is an RHS edit **and
  `tolerance_audit.py` is owed** (~10 min of the user's CPU).

⚠⚠ **THE RATIO IS THE CHEAP ONE AND MAY STILL BE THE RIGHT ONE — BUT SAY WHICH,
AND SAY WHAT IT ASSERTS.** This is the project's first question (setup vs hot
loop) landing on the aromatic branch, and G2's answer for `hammett_rho` was
setup. ⚠ **Measure the temperature spread before choosing**: if the capped
substrates' rates stay well under the encounter limit across the 300–380 K band
the nitration routes actually run in, then the two forms are
indistinguishable there and the ratio wins on cost. **That measurement is one
script and nobody has run it.**

⚠⚠ **THE WHOLE JOB IS SOURCING THE CONSTANT, AND THAT IS THE POINT.** Coombes and
Ridd measured encounter-controlled nitration; this project's rule for a
hand-authored kinetic constant is *bound it against a stated observable, or
declare it hand-authored and say what bounds it* (the sulfur burner is the
standing example). ⚠ **Do not type 1e5 because it appears above** — the number
above is an ARITHMETIC CONSEQUENCE printed to show the shape, not a measurement.

⚠⚠⚠ **AND BE HONEST THAT THIS IS A DIFFERENT KIND OF SESSION FROM G5.** The
constant is **NOT in `chemicals`** and there is no tier-1 source for it here, so
this cannot follow `chemsim-thermochemical-data-curation`'s *"source from
`chemicals`, never recall"* rule — it is a LITERATURE value, and the project's
only licence for one of those is the A-factor licence in MILESTONES § STATED
NON-GOALS (*"absolute reaction TIME is not achievable ... bound an A against a
stated observable, or declare it hand-authored and say what bounds it"*).
⚠⚠ **So the deliverable is not the number, it is the number PLUS a written bound
and a stated observable it was bounded against.** If neither can be produced
honestly, the right outcome is a measured REFUSAL with the arithmetic above
recorded — which is a perfectly good session result on this project and has been
several times.

⚠ **AND NO EXISTING AUDIT CAN CATCH THE GAP IT CLOSES.** `detailed_balance`'s
collision cap compares the PRE-EXPONENTIAL against a limit; `hammett` moves `Ea`.
With A = 1e10 and the barrier clamped at zero a shifted nitration's ceiling is
1e10 — **one decade UNDER** the 1e11 limit — so the cap never fires on a
substituent-shifted rate at all. Fragility 13 in a new suit.

⚠ **Cost it against the four nitration routes first**, as G2 did.

## ⚠ ITEM 3: **G3 — `PLAYABLE.md`, the scoreboard the goal needs**  *(the expensive one)*

A generated standing audit answering *what can a player make, starting from
what?* `ROUTE_INDEX.md` knows feedstocks but not what runs; `COVERAGE_REPORT.md`
knows what runs but never asks whether a feedstock is obtainable.

⚠ The classification is already written and measured (7 from-the-ground / 6
one-step-up / 14 blocked on an unmakeable intermediate / 4 from a reagent
bottle). ⚠ **The one hand judgement in it — which compounds count as NATURAL —
must be PRINTED, not hidden**, so it can be argued with.

⚠⚠ **AND G1 GAVE IT A SECOND QUESTION TO ANSWER**: `benzene-nitration` went from
0.1762 to 0.8000 mol on a change that touched no species and no template, so
"what a player can make" is not a property of the corpus alone. **A PLAYABLE
scoreboard has to RUN things**, which is what makes it different from the two
artefacts above and also what makes it expensive.

⚠⚠ **AND G5 GAVE IT A THIRD, WHICH IS SHARPER: A ROUTE CAN BE BLOCKED ON WHETHER
ITS NETWORK BUILDS AT ALL.** Aniline + nitric acid with electrolyte support
REFUSES, on a nitroanilinium pKa nobody curated. That is not a species being
unpriced and it is not a template being missing — it is a *combination* failing —
and neither existing artefact can see it.

## The C-series — coverage, deliberately deferred

Where *"grind out the remaining classes, including the boring ones"* lives. The
greedy curve in MILESTONES PART 2 is its work order, subject to the RUNNABLE
warning printed beneath it. ⚠ Nothing in the G-series blocks it and every
G-series template counts toward it.

---

# ⚠ THE ENGINE AND HONESTY QUEUE — **REFERENCE, NOT THE WORK ORDER**

⚠⚠ **THE G-SERIES ABOVE IS THE WORK ORDER.** This queue is kept because every row
is a measured, live finding — but **do not start here**, and do not treat a row's
age as a reason to take it.

1. **⚠⚠ THE HAMMETT LINE DOES NOT SATURATE — NEW IN G5, AND IT IS PROMOTED TO
   §ITEM 2 OF THE WORK ORDER ABOVE.** See that section, which carries the
   arithmetic AND the ratio-vs-encounter-rate design question; it is not repeated
   here.

2. **⚠⚠ NO ACIDITY FUNCTION — NEW IN G5, AND IT REPLACES THE OLD "NO PROTONATION"
   ROW.** A mixed acid's acidity is H0, which is not the concentration of
   anything; this engine's only handle is a mass-action molarity whose measured
   floor is **pH −0.79**. ⚠ **DO NOT BUILD THIS BEFORE ITEM 1.** Even a perfect
   acidity function leaves the free-base leak, because the leak is in how the
   free base is PRICED and not in how much of it there is — measured, the
   anilinium is already 100.000% of the aniline and carries 1e-7 % of the rate.
   ⚠ And an H0 is not a state variable this engine has anywhere to put: it is a
   property of a MEDIUM, which is what `chemsim-ion-transfer`'s "an aqueous pKa
   must not run in an oil" is about. **Scope it as physics, not as a table.**

3. **⚠ NO REGIOSELECTIVITY IN THE SUBSTITUENT MODEL (G2), AND G5 ASSERTED IT.**
   `hammett.survey` sums over the substrate's ring as a whole, so all three
   dinitrobenzenes get the same barrier. `test_protecting_the_amine_is_emergent_and_runs`
   now asserts `ortho == approx(meta)` on the nitroacetanilides (0.1535 each
   against a real ~90% para), **so closing this breaks a test rather than going
   unnoticed.** ⚠ The information EXISTS at rewrite time (`tmpl.run` has the RDKit
   match) and is discarded before the barrier is computed, which is S9's shape
   exactly. ⚠ **Price it against G4 first** — a regioselective nitration may or
   may not move any catalog row.

4. **⚠ AN OPEN-ENDED TEMPLATE OVER A CURATED TABLE — NEW IN G5, AND THE REFUSAL
   IS DELIBERATE.** `amine_protonation` protonates every amine a network reaches;
   the ion table prices the typed ones. Nitrating an aniline REFUSES on
   `[NH3+]c1ccccc1[N+](=O)[O-]`. ⚠ **Curating the nine nitroaniline pKa values is
   MEASURED to buy nothing** (the ion channel carries 1e-7 % of the rate), so the
   refusal stands — the element floor's rule applied to a pKa. ⚠ **The thing that
   WOULD change this is item 1**, after which the free base no longer dominates
   and the ion's pKa starts to matter.

5. **⚠ THE PYRIDINIUM IS PRICED AND UNREACHABLE — NEW IN G5.** The ion is in the
   table (pKa 5.23); an aromatic ring nitrogen is **X2** and `amine_protonation`
   matches X3, so nothing can make it. A heteroaromatic protonation template is
   four lines. ⚠⚠ **AND THE THING TO MEASURE FIRST IS THE SKRAUP**, whose product
   is a pyridine ring in hot sulfuric acid. ⚠ Measured: `validation/skraup.py`
   builds its network from `quinoline_chemistry()` alone, which is ONE template
   and carries no dissociation at all — **so the coupling is conditional on
   somebody adding the bundle there, not automatic.** A protonated quinoline is
   real chemistry and would change that route's answer if they did.

6. **⚠⚠ THE PSRK OVERFLOW IS NO LONGER "MEASURED INERT" (S13), AND IT IS STILL A
   CHEAP REAL ITEM.** `activity.activity_coefficients` overflows `np.exp(-a / T)`
   below **4.28 K** (measured: `max(-a/T)` is 760 at T=4 and 292 at T=10).
   `plate_column` prints **five `RuntimeWarning` lines where it printed none**.
   ⚠ **MEASURED HARMLESS WHERE IT FIRES** — heart 0.8548 against 0.8544, target
   met, replay exact. **The word to change is "inert", not the number.** ⚠ **WHAT
   IS NOT KNOWN IS *WHERE*** — nothing has found which call passes a T that low. A
   `np.errstate(over="raise")` context around the residual term, with the state
   printed, is the whole probe. Worth ZERO routes.

7. **⚠⚠ `multistep_prep` PRINTS `pH = inf`, AND IT IS PRE-EXISTING.** At the
   default tolerance the benzoate flask reports `inf`; at rtol 1e-8, **11.65**.
   ⚠ **A READOUT THAT REPORTS INFINITY IS NOT AN ACCURACY PROBLEM** — same
   mechanism as the Skraup's "exactly zero": a hydronium column the loose solver
   clamps to a literal 0.0, and `-log10(0)` is `inf`. The fix is probably a floor
   on the pH READOUT (the shape `is_boiling` got), but **measure the hydronium
   trajectory first**.

8. **⚠⚠ NOTHING IN `build_phase_arrays` COMPARES T TO Tc.** A CONDENSABLE species
   above its critical temperature still dissolves by Raoult's law against an
   Antoine curve extrapolated past its own domain. Measured: a Wacker flask at
   400 K dissolves **0.165958 of 0.20 mol of ethylene over 20 mol of water —
   83%, against a real ~2%** — because Psat reads **219.9 bar** off a curated
   Antoine **118 K above ethylene's Tc of 282.35 K**.
   ⚠⚠ **A MEASURED BOILING POINT DOES NOT FIX IT** — S11 predicted it would and
   measured that it does not (0.16588 → 0.16596), because the vapour pressure
   comes from `volatility._CURATED_ANTOINE` and Tb does not feed that curve.
   ⚠ **S13 PUT 869 MORE SPECIES ON A FITTED ANTOINE CURVE** and added no Tc
   check, so the exposure grew even though the measured example did not move.

9. **⚠⚠ A METAL THAT BOILS OUT OF THE SOLID BLOCK — STILL THE BEST-SCOPED PURE
   ENGINE ITEM.** Measured after S10's commit by patching iron's volatility in
   place (Alcock's curve) and running thermite insulated:

       vessel Cp    lattice iron    VOLATILE iron    where the iron went
          1 J/K       5469.43 K        3490.99 K     0.0192 gas / 0.0207 liquid
         10 J/K       2329.06 K        2284.28 K     0.0399 liquid (it MELTED)
         50 J/K       1322.45 K        1322.45 K     unchanged

   **The blocker is ONE BRANCH in `build_phase_arrays`** — the
   `if mineral is not None:` arm pinning `vol_A = NONVOLATILE_A`,
   `condensable = False`, `solidifies = False`. Letting a `MineralRecord` carry
   OPTIONAL volatility is a **setup-layer change with NO RHS edit**.
   ⚠ **BUT THE DATA OBJECTIONS SURVIVE THE ENGINE FIX**: `[Fe]` fails S4's
   disambiguation test (three solid allotropes, two transitions inside thermite's
   range) and Alcock tabulates **no sublimation curve** for iron, so zinc's best
   cross-check cannot be run — **ONE check, not four.** ⚠ Worth ZERO routes for
   iron; ⚠⚠ **MEASURE `direct-combination` FIRST** — worth +1 and refused by the
   same `build_surface_arrays` non-lattice check, but `Hg(l) + S8(s)` is not a
   gas attacking a crystal, so `SurfaceArrays`' form may be wrong for it.

10. **⚠⚠ THE 250–450 K FIT WINDOW.** `CondensedProvider.get(mol, T_lo=250.0,
    T_hi=450.0)` is an organic-solvent window and **every caller takes the
    default.** Swept in S11 over each species' OWN Tm→Tb: **99 compounds return a
    NEGATIVE liquid Cp inside their own liquid range** (worst carminic acid at
    **−21482 J/(mol K)**) and 38 more swing over 5x.
    ⚠⚠ **NOBODY HAS RE-SWEPT THE 99 SINCE S13 GAVE 876 SPECIES MEASURED Tb/Tc.**
    The count is a pre-S13 number and **the first thing this item needs is to
    measure it again** — S11 moved ethylene from **+1574 to −1782** by giving it a
    measured Tc, so better inputs do not make an extrapolation safer.
    ⚠ A negative Cp is not an accuracy problem: **adding heat LOWERS the
    temperature**, and S10 measured it reachable (3.96 mol of liquid mercury gave
    a NEGATIVE total thermal mass). ⚠⚠ **DO NOT JUST WIDEN THE WINDOW** — many of
    the 99 have a Joback Tm/Tb that is itself meaningless.

11. **⚠ `slagging` — RE-PRICED IN S11 AND IT WAS PRICED TOO CHEAPLY.**
    `silicon-dioxide` ✔ fully available; **`calcium-silicate` has NO
    thermochemical data under ANY of its three CAS numbers** ✘ (not a curation
    job); `iron-ii-oxide`'s CRC standard row has **`Cps = NaN`**.
    **`blast-furnace` is blocked TWICE over, on SOURCES rather than on work.**

12. **⚠ THE CIS/TRANS BLIND SPOT.** Benson (the RMG group set) has no cis
    correction, so oleic and elaidic acid come back with IDENTICAL Hf and Gf and
    the engine reports a confident 50:50 for a real ~5:1. ⚠ **The data exists and
    is not usable as it stands**: WEBBOOK has both liquid enthalpies (−764.8 and
    −769.0 kJ/mol) and that 4.2 kJ/mol gap agrees with Benson's own historical cis
    NNI term to 0.4% — **two independent sources** — but neither has an S0, so no
    Gf can be derived, and grafting Benson's original correction onto RMG-fitted
    group values **mixes two bases**.

13. **⚠ THE CURRENT BUDGET — M8's OWN NAMED GAP, AND IT IS A LAYER 4 TERM.** Two
    electrode reactions in one cell divide nothing, so both run at full rate:
    k(brine)/k(water) is **4.76e+17 at 2.5 V, 5.94 at 3.0, 1.00 at 4.0**.
    ⚠ Worth **ZERO new routes**.

14. **Pyrite** — one mineral entry, +1 on the intersection. ⚠ **RE-QUERIED IN S11
    AND THE REFUSAL STANDS**: `Hfs` in WEBBOOK, `S0s` in **nothing**.

15. **⚠⚠ THE BURNER — measured at 52.47 s at rtol 1e-8 against 0.8 s at the
    default, and it is the 5th most expensive test in the suite (3.9%).** S5
    bounded the CRASH and explicitly did not bound the THRASHING. BDF is
    struggling with a liquid layer holding **1e-29 mol**, which `LAYER_REABSORB`
    drains toward zero without ever reaching it. **The question nobody has asked
    is whether a layer below `LAYER_EPS` should be *merged discretely* at a step
    boundary rather than drained continuously for ever** — `merge_phases` already
    does exactly that at the `run` boundary. **Measure the layer-2 inventory over
    the failing run before designing anything.**

16. **THE CORPUS BALANCE BACKLOG — 75 ROWS, AND IT IS NOT A TO-DO LIST.** S7
    built the check and deliberately fixed nothing, on the `diels-alder-route`
    precedent. ⚠ But **17 of the 75 are `spurious`** and those are the cheapest to
    correct. ⚠ `tools/catalog.py`'s `validate` still does NOT check balance, so
    the corpus can grow another one silently.

17. **⚠ `hydrolysis`** — it unlocks **exactly ONE route alone,
    `vitriol-distillation`**, and that route's step 1 reads `-> iron-ii-OXIDE`
    while the engine makes HEMATITE. ⚠ **That is item 11's mineral again.**

18. **M7 (⚠ M12 took most of its case away; re-scope)**, **M9 (polymers, 12
    routes)**, **M10 (the site balance S1 did not build, 8 routes)**,
    **⚠⚠ M11 — RE-COST IT BEFORE SCHEDULING.** Its costed starting point was
    *"10 species that need ONE measured boiling point each"*; **S13 closed eight
    and the bucket counts 2**. What is left is the FORMATION half — 267 species
    with no group value in any published tabulation.

19. **NUCLEATION, now that half of it is modelled.** S3 named the gap; S4 turned
    the *deposition-needs-a-seed* half into a real bound in
    `SolidStateArrays.units`. What is still not expressible is a solid appearing
    from NO solid — `hydride-thermal-deposition` is still a mechanism gap.

---

# THE COVERAGE QUEUE — **DEFERRED TO THE C-SERIES; WHAT IS LEFT IS REFUSALS OR ENGINE WORK**

⚠⚠ **What is left here is NOT a work queue.** Five of the seven rows are recorded
REFUSALS or engine prerequisites, and the two that are neither are the hardest
kind of content work. **Read the row, not the rank.**

| class | its route | worth | what it is |
|---|---|---:|---|
| `fischer-tropsch` | `fischer-tropsch` | +1 | `8 CO + 17 H2 -> octane + 8 H2O`, **25 slots**. Claus proves 24 works and Skraup proves the pattern generalises — but read M8 §6 on the lump that was refused. ⚠ **The queue's best CONTENT row**, and its mechanic is chain growth as a lump, which is M9's problem wearing a template |
| `molten-salt-electrolysis` | `downs-cell` | +1 | ⚠ **A MELT is not a phase this project has** — M8's own leftover, ENGINE work |
| `catalytic-air-oxidation` | `p-xylene-oxidation` | +1 | ⚠⚠ **M5 REFUSED THIS CLASS** — its four rows are at least three mechanisms. **Split it before crediting it**; only one of the four is runnable |
| `direct-combination` | `vermilion-route` | +1 | ⚠⚠ **S9 MEASURED AND REFUSED IT**; engine queue item 9 is the only thing that could change that. **Do not re-derive this** |
| ~~`oxidative-cleavage`~~ | `vanillin-lignin` | ⚠⚠ **S11 REFUSED IT** | It cannot be the reaction the row is written as: it balances at **8 C10H12O3 + 7 O2 -> 10 C8H8O3 + 8 H2O** — eight aromatic rings in and TEN out. **Do not re-derive this** |
| `fermentation` | `abe-fermentation`, `msg-route` | +1 | ⚠ **M5 REFUSED IT** as a metabolic NETWORK rather than a transformation |
| `separation` | `coal-tar-distillation` | +1 | ⚠ **M5 REFUSED IT**: a distillation is not a reaction class, and the feedstock has no graph |

⚠⚠ **AND READ `corpus_balance.py`'s LAST PANEL BEFORE PICKING ANY OF THEM.** The
balance audit's test is a WEAK one: it asks whether ANY positive coefficient
vector conserves the elements, and element conservation does not forbid
rearranging carbon skeletons. `vanillin-lignin` PASSES at eight rings in and ten
out. ⚠⚠ **AND S12 IS THE CONVERSE**: `skraup-route` step 2 looked like the
`spurious` pattern, passed, and was REAL. **The check cannot decide either way;
only reading the chemistry can.**

⚠ **`isomerisation` IS DEAD THREE TIMES OVER AND IS STILL THE REPORT'S TOP ROW.**
Two balance failures, plus `oleic -> elaidic` prices at **dH = dG = 0.000
EXACTLY** and `glucose -> fructose` at **K = 4.8e-08** because the corpus spells
one as a pyranose and the other as a furanose. **Do not build it.** The other
seven the report promises and the balance audit kills are tabulated in
`corpus_balance.py`'s own output.

---

The project is under **git**. There is no remote. ⚠ The committer identity is the
machine's global `innovationlabOBS <innovationlab@obsglobal.com>`; set a
repo-local `user.name`/`user.email` if that should be yours.

Start by reading, in order:

MILESTONES.md — the plan, and **§ THE G-SERIES first**. ⚠ **§G1, §G2 and §G5 are
  marked DONE with what they turned out to be, and G1's original brief is kept
  underneath because the measurement that overturned it only means something
  against it.** Then §S13, §S12, §S11, §S10, §S9, §S8, §S7, §M8, §S1, §S3, §S4,
  §S5, §S6.
HANDOFF.md — what exists, and the ethos to preserve. **85 is S1 … 98 is S13,
  99 is G1, 100 is G2, 101 is G5.**
NEXT_SESSION.md — the invariants table at the bottom is the contract, and **G1,
  G2 and G5 each added a block**. ⚠ Read the two warnings above it before
  trusting any row, and note that **G5's "no acidity function" and
  "the Hammett line does not saturate" rows are LIMITS TO REMOVE**, not
  invariants to keep — as is G2's regioselectivity row.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy; plus
  `data/catalog/COVERAGE_REPORT.md`.
the memory files (auto-loaded), especially **chemsim-protonation** and
  **chemsim-ring-deactivation**, then chemsim-dropping-funnel,
  chemsim-skraup-standard-state, chemsim-ion-transfer,
  chemsim-competing-templates, chemsim-solubility-product,
  chemsim-measured-physical-table, chemsim-coverage-catalog and
  chemsim-generated-artefacts.

STATE: Layers 0–7 complete. The engine is open-ended (no recipes), conserves
matter, has an element/mineral floor, a still that is a saveable protocol, a
plate column that reaches its purity target, an ionic lattice that can leave
solution, an energy balance it can report the way it reports a mass one, 46
templates, a reaction that happens INSIDE a crystal, a gas that ATTACKS a
crystal, a catalyst you have to actually put in the flask, a Jacobian that cannot
be probed outside its own state, four inorganic gas processes, three smelters, a
retort that DISTILS its metal off, two templates that RACE for one alkene, a ring
closure whose OXIDANT turns into one of its own reagents, a dropping funnel whose
addition is a CONDITION and not a duration, an aromatic ring that knows what is
already on it, **an amine that PROTONATES in acid — and a measured statement of
why that is not enough to make an aniline behave.** `SAVE_VERSION` is **6**.
Coverage: **51/229 classes**, **46 templates**, **41/173 template-ready**,
**82/173 species-ready** (was 80 — G5's ion-table fix) — and ⚠⚠ **31/173 BOTH,
which is the only one of the three a route can be judged on.**
⚠ The corpus's **PHYSICAL half is measured for 652/1583 (41.2%)** as of S13;
its refusals are down to **419 of 1583** as of G5.

---

# ⚠ THE FRAGILITIES

**1. ⚠⚠ THE HAMMETT LINE DOES NOT SATURATE (G5).** `rho*sigma+` prices aniline
8.45 decades off a line fitted on |rho·sigma| < 2.6, and real nitration of an
activated arene is encounter-controlled. **A LIMIT to remove, and the best-scoped
new item.** ⚠ No existing audit can see it: the collision cap compares `A` and
hammett moves `Ea`.

**2. ⚠⚠ NO ACIDITY FUNCTION (G5).** The reachable hydronium floor is **pH −0.79**
and the aniline crossover is at **−9.42**. H0 is a property of a MEDIUM and there
is nowhere in this engine to put it. **A LIMIT to remove — but AFTER fragility 1**,
because the anilinium is already 100.000% of the aniline and carries 1e-7 % of
the rate.

**3. ⚠ AN OPEN-ENDED TEMPLATE OVER A CURATED ION TABLE (G5).** Nitrating an
aniline REFUSES on a nitroanilinium pKa nobody curated. **The refusal is
deliberate** — curating the nine values is measured to buy nothing.

**4. ⚠ THE PYRIDINIUM IS PRICED AND UNREACHABLE (G5).** An aromatic ring nitrogen
is X2 and `amine_protonation` matches X3. Closing it lands on the Skraup.

**5. ⚠ NO REGIOSELECTIVITY IN A SUBSTITUENT BARRIER (G2, asserted in G5).** All
three dinitrobenzenes are made at one rate, and ortho == meta on the
nitroacetanilides against a real ~90% para. The site exists at rewrite time and
is discarded. **A LIMIT to remove.** Engine queue item 3.

**6. ⚠ A STILL AND A DRIP BENCH CANNOT BE ONE APPARATUS IN AN EXAMPLE'S BUDGET
(G1).** The same 20 s addition costs **3.9 s of wall clock on two vessels and
220 s with a head and receiver attached — 56x.** Not a bug: a rig integrates
every vessel as one stiff system. **Reported in `examples/dropping_funnel.py`.**

**7. ⚠⚠ NOTHING COMPARES T TO Tc (S11).** Ethylene is ~40x too soluble in the
Wacker liquor. Engine queue item 8. **A LIMIT to remove.** ⚠ S13 put 869 more
species on a fitted Antoine curve and did NOT add a Tc check.

**8. ⚠⚠ THE WACKER'S OXYGEN ORDER IS FIRST AND SHOULD BE ZERO (S11).** Measured
at 1.00 / 1.92 / 3.53 / 5.85x. **A LIMIT to remove.**

**9. ⚠⚠ A LATTICE MAY REACT AND MAY NEVER BOIL — HALF CLOSED BY S10.** What
remains is thermite. **Engine queue item 9**, worth ZERO routes.

**10. ⚠⚠ THE BURNER IS STILL ~50 s AT rtol 1e-8 AGAINST 0.8 s AT THE DEFAULT —
AND G5's `--durations=25` MEASURED IT AT 52.47 s, 3.9% OF THE WHOLE SUITE.** The
"~50 s" claim was right. **Engine queue item 15.**

**11. ⚠⚠ NO CURRENT BUDGET (M8).** Selectivity washes out above ~2.7 V.

**12. ⚠⚠ THE ION TABLE'S MIXED BASIS (M8, pre-existing).** dG survives it, dS does
not. Quote E_dec at 298 K; do NOT quote its temperature derivative or a cell's
HEAT.

**13. ⚠⚠ 75 CATALOG ROWS CANNOT BE BALANCED (S7).** Reported, not fixed.

**14. ⚠⚠ THE ESTIMATORS CANNOT TELL A CIS ALKENE FROM A TRANS ONE (S7).**

**15. ⚠ `deacon_oxidation_rev` CROSSES THE BIMOLECULAR CEILING AT 1141 K**, and a
solid decomposition's forward constant crosses the unimolecular one at 3710 K.
⚠ S11 added two rows that cross at 967/969 K, the only ones whose crossing is a
physical statement rather than a ranking.

**16. ⚠ `detailed_balance`'s RATE CAP COMPARES A CATALYSED PRE-EXPONENTIAL
AGAINST A LIMIT NOT IN ITS UNITS.** It does not fire on any catalysed template.
⚠⚠ **AND G5 FOUND ITS SECOND BLIND SPOT: it cannot fire on a HAMMETT-SHIFTED
rate either**, because it compares `A` and hammett moves `Ea`.

**17. THE DEFAULT TOLERANCE, BOUNDED RATHER THAN OPEN.** ⚠ `tolerance_audit.py`
is a STANDING audit: run it after touching the RHS **or any data table**. ⚠
**G1, G2 AND G5 DID NEITHER** — G5's ion-table change is asserted BIT-IDENTICAL
for all 24 pre-existing anions — so its last measured state is S13's.

**18. NOT MODELLED: the SITE BALANCE.** First order in the catalyst for ever. M10.

**19. ⚠⚠ 99 CORPUS ROWS HAVE A NEGATIVE LIQUID HEAT CAPACITY (S10, re-swept
S11).** ⚠ **The count is PRE-S13 and nobody has re-swept it.** Engine item 10.

**20. ⚠ NUCLEATION, HALF modelled.** A solid can only grow where one already is.

**21. ⚠⚠ THERE IS NO REFLUX HEAD (S12).** A reaction at reflux must be modelled
as a SEALED flask, which buys a real pressure (13.7 bar for the Skraup at 450 K).
⚠ An OPEN Skraup loses **98% of its yield**.

**22. ⚠ LIQUID MERCURY IS 99.85% HELD IDEAL.**

**23. ⚠ THE ELEMENT FLOOR'S SOLID HALF IS CURATED AND ITS GAS HALF IS REFUSED.**
33 compounds remain refused as bare elements and none blocks a route.

**24. ⚠ `iron-ii-oxide`, `pyrite` AND `calcium-silicate` ARE ALL SOURCE-BLOCKED.**

**25. ⚠⚠ THE PSRK OVERFLOW IS NO LONGER "MEASURED INERT" (S13).** Overflows below
**4.28 K**; `plate_column` prints five `RuntimeWarning` lines. ⚠ Measured
HARMLESS where it fires. Nothing has found WHICH call passes a T that low.
**Engine queue item 6.**

**26. ⚠⚠ `multistep_prep` PRINTS `pH = inf` (pre-existing, visible since S13).**
**Engine queue item 7.**

**27. ⚠ `named_routes` CANNOT BE SWEPT at rtol 1e-8 (S13) — AND IT IS NOT NEW.**
The PRE-S13 data raises too, at **rtol 1e-7**, one decade closer to the default
than the audit samples.

**28. ⚠ THE 31 SPECIES THAT MISS THE BOILS-AT-1-ATM BAR (S13).** 858 of 889 clear
1.5%; the 31 are NAMED in `BOILS_LOOSELY` and **eight are pre-existing**.

**29. ⚠ BENZOIC ACID'S MOLAR VOLUME GOT WORSE IN S13** — 96 → 87.4 mL/mol against
a real ~96.5. Taken deliberately: a record may not mix two group-contribution
methods.

⚠ **AND THE BLOCK-ORDER TRAP STILL HOLDS:** the state vector is
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not last.**

---

TRAPS SPECIFIC TO THIS ARC:

⚠⚠⚠ **A REFUSAL PRINTED IN A GENERATED AUDIT IS EVIDENCE, AND THIS ONE SAT IN THE
REPO FOR TWELVE ROWS AND SEVERAL SESSIONS.** `COVERAGE_REPORT.md` printed
`refusing to price '[NH4+]'` for twelve ammonium salts, and it read as an ordinary
Born-domain refusal rather than as a bug in the ion table. The refusal even named
a fix — *"add the conjugate acid to `_PAIRS` if it is not there"* — **and it WAS
there.** **A refusal that names the WRONG fix is worse than one that names none**,
because a reader who checks is then satisfied.
⚠⚠⚠ **BOUND THE FIX BEFORE BUILDING IT, EVEN WHEN THE FIX IS THREE LINES.** The
`ammonio` σ row is three lines and it was always going to go in. What mattered was
computing, first, that the two channels cross at pH −9.42 and that the flask's
floor is −0.79 — because that turned the session's headline from *"protonation is
modelled"* into *"the limit is NO ACIDITY FUNCTION"*, which is a different and
much better-posed statement. **Twenty-five times now.**
⚠⚠ **AND THE ANSWER THAT LOOKS WRONG MAY BE THE MODEL AGREEING WITH REALITY IN A
PLACE YOU CANNOT GO.** pH −9.42 reads absurd and is not: it is inside the measured
H0 band of the 90–98% sulfuric acid real aniline nitration is run in. **Ask what a
number would have to be for the model to be right before calling it wrong.**
⚠⚠ **FOLDING TWO TERMS OF A SUM TOGETHER IS A DATA-TABLE CHANGE.** Summing the
pKa term and the solvent correction into one variable before adding it moved **ten
of the 24 ion-table anions in the last bit**. Floating-point addition is not
associative, and a 1e-16 shift in a data table owes `tolerance_audit.py` ten
minutes of the user's CPU. **Not shifting it is cheaper than proving it harmless.**
⚠⚠ **A DIRECTION IS A DECLARATION, BECAUSE DISCOVERY IS FORWARD-ONLY.** A
reversible template's reverse is in the network but is never used to enumerate
species, so a deprotonation-forward template can only find an anilinium in a flask
that already has one. `ester_hydrolysis` recorded this in M5 and it had to be
rediscovered.
⚠⚠ **A SMARTS `H` WITH NO DIGIT MEANS EXACTLY ONE.** `[NX4H+]` matched a
protonated tertiary amine and nothing else, so the template named
`ammonium_dissociation` was the one thing that could not deprotonate an ammonium.
⚠ **AND A MAPPED ATOM KEEPS ITS FORMAL CHARGE**, so `[OX2H2:2]` on a hydronium
oxygen hands back water with a +1 on it — after which the charge-balance check
drops the rewrite and **the symptom is a template that silently does nothing.**
⚠⚠ **AN OPEN-ENDED REWRITE OVER A CURATED TABLE WILL FIND THE EDGE OF THE TABLE.**
A protonation template makes conjugate acids without limit. **Keeping the refusal
was the right call and it was decided by arithmetic**, not by taste: the nine
missing pKa values were measured to buy nothing.
⚠ **A POSITIONAL INDEX INTO A TABLE IS NOT A KEY.** `hammett._TABLE[0]` with an
`assert label == "nitro"` guard under it — the guard earned its keep the first
time a row was inserted. Order in that tuple is a SMARTS-precedence decision.
⚠ **A TABLE ROW WHOSE TWO CONSTANTS INVERT BREAKS A RULE DERIVED FROM THE OTHERS.**
−NH3+ is σm 0.86 / σp 0.60 where every other meta-director has σm < σp, so
"meta-directing iff σp > σm" calls an anilinium an ortho/para director. Second
reason `meta_directing` is declared data; the halogens are the first.
⚠⚠ **A rho IS MEANINGLESS WITHOUT ITS SIGMA SCALE**, exactly as a dH is
meaningless without its standard state. σ⁺ and σ differ by up to 0.6 for resonance
donors and agree within 0.05 for acceptors — **which is exactly what licences the
`ammonio` proxy row**, because −NH3+ has no lone pair to donate.
⚠ **AN UNSOURCED VALUE IS REPORTED, NOT PRICED AT ZERO IN SILENCE.** An aryl
quaternary ammonium has no σ this table can source, so it comes back in `unknown`
rather than borrowing the anilinium's row.
⚠ **A CLAMP IS NOT A FIX, AND IT SHOULD SAY SO.**
⚠ BOUND A MECHANISM ARITHMETICALLY AGAINST THE ACTUAL SIMULATED STATE BEFORE
WRITING CODE. ⚠ **AND THE SOLVER IS PART OF THE ARITHMETIC** (M8).
⚠⚠ **SEARCH FOR THE MECHANIC BEFORE BUILDING IT, AND SEARCH THE OTHER LAYER**
(G1). ⚠⚠ **AND THE HALF A BRIEF CALLS FREE IS THE HALF TO MEASURE.**
⚠⚠ **A COUNT OF THINGS THAT ARE MISSING IS NOT A COUNT OF THINGS THAT ARE WRONG.**
