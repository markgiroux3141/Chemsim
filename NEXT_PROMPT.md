We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M6, M8, M12, S1–S13, G1, G2, G4, G5 and G6 are
DONE.**

⚠⚠⚠ **THE ARC IS THE G-SERIES, AND G3 IS THE ONLY UNBUILT ITEM IN IT.** The
catalog is a measuring instrument and was being read as a specification; the goal
is a connected tech tree a player can walk from natural materials. **Read
MILESTONES § THE G-SERIES.** Coverage is DEFERRED to a C-series, not cancelled.

# ⚠ THE BASELINE IS MEASURED. DO NOT START WITH THE SUITE.

**G6 RAN THE WHOLE SUITE AND MEASURED 1045 PASSED / 0 FAILED IN 23:03.** Take that
number and spend the time on content. ⚠ It was run AFTER every `src/` edit —
seventh session running that is true — and **the only edits that landed while it
ran were to `NEXT_PROMPT.md` and the memory files**, neither of which pytest
reads, so **23:03 is a CLEAN figure** rather than G5's upper bound.
⚠ The count reconciles exactly: 1024 (G5) + 9 (G4's `test_granularity`, never in
a full-suite figure before) + 12 (G6's `test_saturation`) = **1045**.

⚠ **G6 TOUCHED NO RHS AND SHIFTED NO DATA TABLE.** The encounter plateau lives at
SETUP, exactly where `hammett_rho` does, and **everything under the plateau is
asserted BIT-IDENTICAL** — so `tolerance_audit.py` was not owed and was NOT
re-run. Its last measured state is S13's and every warning in §S13 about it still
stands.

⚠⚠⚠ **AND THE TWO `--durations=25` LISTS HAVE NOW BEEN DIFFED, WHICH GIVES
THE THING TWO NEXT_PROMPTS ASKED FOR: A MEASURED NOISE FLOOR.**

                        G5        G6      change
    top 25           803.1 s   819.8 s   59.6% -> 59.3% of the suite
    test_still x6    402.2 s   415.8 s   29.8% -> 30.1%
    the ONE RIG test 164.1 s   176.9 s   **+7.8%**
    catalysis         74.1 s    75.1 s   +1.4%
    burner @rtol 1e-8 52.5 s    52.8 s   +0.7%
    the long tail     0.55 s    0.55 s   **IDENTICAL to two decimals**
                                         (999 tests then, 1020 now)

⚠⚠ **SO THE SHAPE IS STABLE AND THE NOISE FLOOR IS ~8% ON THE BIGGEST SINGLE
ROW AND ~1% ON THE MID ROWS.** That is what makes the list an instrument: the
suite's +35 s between G5 and G6 is **noise plus 16.6 s of new test files** and
must not be attributed to anything, while the S12->S13 eight minutes is **20x
outside** the floor and remains a real unexplained regression.
⚠ It still does NOT diagnose S12->S13 — no list exists on either side of that
commit — and the cheap next step is unchanged: a `git stash`-and-rerun of
`--durations=25` across S13's data commit. **What has changed is that the answer
would now be readable, because the measurement's own repeatability is known.**

```bash
python validation/saturation.py                # ⚠ G6's, 27 s. NEW -- read panels 1, 3 and 5
python validation/protonation.py               # G5's, 20 s. ⚠ REWRITTEN BY G6 -- panels 3 and 5
python validation/ring_deactivation.py         # G2's, 14 s. ⚠ REWRITTEN BY G6 -- panels 1 and 5
python validation/granularity.py               # G4's, 18 s. read panels 3 and 4
python validation/dropwise.py                  # G1's, 78 s
python validation/boiling_points.py            # S13's, 2 s. READ PANEL 2
python validation/skraup.py                    # S12's, ~10 s
python validation/smelting.py                  # S9's, ~1 min
python validation/hydroformylation.py          # S11's, ~1 min
python validation/wacker.py                    # S11's other one, ~1 min
python validation/gas_processes.py             # S7's, ~1 min
python validation/corpus_balance.py            # S7's other one, ~20 s. READ IT before picking
python validation/catalog_coverage.py          # ⚠ 'BOTH' is 31/173, ~9 s. ⚠⚠ AND IT IS A
                                               #   LOWER BOUND TOO -- G4 measured 31+5
python validation/physical_estimation.py       # S13 took its panel 3 to n=254
python validation/game_gates.py                # the element floor's cross-check, seconds
python tools/build_route_index.py              # the artefact nothing reads
python validation/cell_potentials.py           # M8's standing audit, seconds
python validation/rate_ceiling.py              # ⚠ G6 moved its fastest activated
                                               #   nitration by EIGHT DECADES
python validation/jacobian_bound.py            # S5's standing audit, ~1 min
python -m ruff check src tests examples validation tools
python -m pytest -q                            # ONLY after touching src/
python validation/tolerance_audit.py           # ~10 min. After touching the RHS **or any data table**
```

⚠ **THE SUITE AND THE TOLERANCE AUDIT ARE MINUTES OF SATURATED CPU ON THE USER'S
OWN MACHINE.** Say what a long run will cost before starting one, and ask.
`examples/plate_column.py` alone is 12 minutes.

⚠⚠⚠ **AND THERE IS A TRAP IN WRITING A NEW AUDIT THAT COST G6 TWO CRASHES: THE
CONSOLE IS cp1252 AND THE WARNING GLYPH CANNOT BE PRINTED.** Every audit in this
repo keeps `⚠` in docstrings and comments and out of `print`, and that is not a
style choice — `python validation/x.py` dies with `UnicodeEncodeError` mid-panel.
⚠⚠ **`validation/protonation.py` HAD EXACTLY ONE IN A PRINTED STRING AND DIED AT
PANEL 3**, so G5's panels 4–7 could not be read on this machine at all; G6 fixed
it. ⚠ **A `build_network` NOTICE is printed too**, so a glyph in one crashes every
audit and example that reaches that reaction.

---

# ⚠⚠⚠ WHAT G6 TURNED OUT TO BE

**G6 asked what number to declare for the encounter plateau the Hammett line
flattens into, and NEXT_PROMPT told it to ask a design question first: a capped
RATIO or an absolute ENCOUNTER CEILING. THE MEASUREMENT ANSWERED THE QUESTION,
AND IT ANSWERED IT DIFFERENTLY FROM THE COST ARGUMENT THAT WAS EXPECTED.**

The deliverables are `hammett.SATURATION_DECADES = 2.686` with a written bound,
`validation/saturation.py` (six panels, 27 s) and `tests/test_saturation.py`
(12 tests, 7.3 s). **Every route is charged into a real `Vessel` and its moles
printed** — S1's precedent, now a four-time finding.

## ⚠⚠⚠ 1. THE ABSOLUTE CEILING CANNOT FIRE, SO IT WAS NEVER THE RIGHT MODEL HERE

The brief called `min(k_hammett, k_enc)` *"the physically correct statement"* and
priced it as an RHS edit plus ten minutes of tolerance audit. Measured over
300–380 K with the plateau lifted:

    substrate       k at 300 K   k at 380 K   of a diffusion ceiling
    benzene           0.357         56.6        5e-11 .. 2e-9
    mesitylene        3.81e5        3.24e6      5e-5  .. 1e-4
    aniline           8.94e7        2.41e8      1.2%  .. 0.86%
    4-aminophenol     1.00e10       1.00e10     137%  .. 36%    <- CLAMPED

**It can only bind on the one case a floor already catches.** 4-aminophenol
reaches a diffusion ceiling only because `clamp_barrier` has already floored its
barrier at zero, leaving `k = A = 1e10`. ⚠⚠ **So `clamp_barrier` was already an
absolute rate ceiling in disguise** — pinning `k` at the declared `A` rather than
at a diffusion rate — and eight milestones of reading that function had not
noticed.

⚠⚠⚠ **AND THE STRUCTURAL REASON IS THE TRANSFERABLE HALF: THE OBSERVABLE IS SIX
DECADES BELOW ANY DIFFUSION CONSTANT, BECAUSE THIS RATE LAW IS NOT ELEMENTARY.**
`aromatic_nitration` is written on the arene and HNO3, so the nitronium
pre-equilibrium is folded into `Ea` and `k` is a stoichiometric constant. An
absolute ceiling in these units would have to be `k_enc * [NO2+]/[HNO3]` — a
property of the MEDIUM'S ACIDITY, which is exactly the thing G5 measured this
engine has nowhere to put. **The capped ratio is not the cheap approximation to
the right model; it is the only one of the two that can express what was
measured.** ⚠ *Ask what quantity the rate constant actually IS before importing a
bound that belongs to a different one.*

## ⚠⚠⚠ 2. THE SECOND SOURCE WAS THE LOWER BOUND, NOT A RIVAL VALUE

Two sources, both new to this repo, and the second one is the one that decided
the number:

* **Belson & Strachan, *J. Chem. Soc., Perkin Trans. 2*, 1989, 15** — aqueous
  nitric acid, 24–41 mol% HNO3, 293–333 K: **benzene : toluene : p-xylene :
  mesitylene = 1 : 22 : 256 : 485** at ~30 mol% and 25 °C, and *"with p-xylene
  and mesitylene the nitration is diffusion-controlled, but not so with the
  others"*. log10(485) = **2.686**, and that is the declared value.
* **Coombes, Moodie & Schofield, *J. Chem. Soc. B*, 1968, 800** — the limit exists
  and IS the encounter rate; in the strongest acids benzene's own rate comes
  **within a sixth** of it.

The 1968 figure reads as **0.778 decades** and looks like a rival candidate — the
mixed-acid medium the corpus routes actually run in. **Applying it caps TOLUENE at
6.0 against a measured 22**, damaging a substrate the same literature says is NOT
diffusion-controlled. ⚠⚠ **A plateau cannot sit below the fastest substrate that
does not saturate**, so the honest band is **2.02 to 2.69 decades** and the
declared value is its top. *Two sources that disagree may not be two candidates;
one of them may be a bound on the other.*

## ⚠⚠ 3. WHAT IT BUYS: ANILINE, AND IT TOOK G5 AND G6 TOGETHER

    channel-weighted, at the engine's acidity floor of pH -0.789
      G2 alone (free base, bare line)      2.82e8 x benzene
      G5's split, bare line                3.81e2 x benzene   still FASTER
      G5's split + G6's plateau            1.89e-3 x benzene  SLOWER -- correct

**The observable is that aniline in strong acid nitrates slower than benzene and
gives largely meta product, and the model is finally on that side of it.** G5
moved the FRACTION and measured that it could not be enough; G6 moved the PRICE.
`validation/protonation.py` panel 5 prints both and splits the credit.

Also fixed: mesitylene **1.16e6 → 485**, the datum, a **2400x** correction.
Toluene is **untouched** at 105 against 22, and that 4.8x is `rho`'s error.

## ⚠⚠⚠ 4. AND IT COST G5 ITS HEADLINE, WHICH IS THE MOST USEFUL THING HERE

G5's strongest claim was that the free-base/anilinium crossover at **pH −9.42**
lands inside the measured H0 band of the 90–98% sulfuric acid real aniline
nitration is run in, *"without being told about it"* — read as the engine's own
arithmetic finding the right answer unprompted.

**That agreement was a property of the 8.45-decade extrapolation.** With the free
base at a sourced plateau the crossover is **−3.66**: the pot needs 2.87 decades
more acidity than its floor instead of 8.63. ⚠ The wall is still a wall, and the
split is still the right model — **but the number was not evidence for it.**
⚠⚠ *A number that agrees with reality is only evidence if the model behind it is
inside its own domain.* Asserted both ways in `tests/test_protonation.py`, with
G5's value kept as the plateau-lifted one.

## ⚠⚠ 5. THE ONE-SIDED DECISION, AND THE CORPUS COST OF ZERO

A cap on `|rho * sigma|` looks more symmetrical. Measured on G2's TNT ladder it
puts **0.0345 mol of trinitro in the flask in ten seconds at 300 K** and
**1.0000 at 340 K** — G2's failure restored. One-sided leaves that ladder bit for
bit. **Nothing caps how slow a deactivated ring gets.**

    route                target        bare line   PLATEAU
    benzene-nitration    nitrobenzene    1.0000     1.0000
    tnt-route            2,4,6-TNT       0.0643     0.0643
    picric-acid-route    picric acid     0.1250     0.1250

⚠⚠ **PHENOL'S FIRST NITRATION IS SLOWED 1968x AND THE TWO-HOUR YIELD DOES NOT
MOVE**, because that step was never rate-limiting. *A measurement of what a rate
change buys is not a measurement of the rate change.* ⚠ G4's 137-of-142 predicted
this: **the plateau buys no route.** What it buys is the number being right.
⚠ G2's four-route cost table lived in HANDOFF and nowhere else; **it is a script
now.**

---

# ⚠⚠⚠ START HERE: G3 IS THE LAST UNBUILT G-SERIES ITEM

⚠⚠ **READ `MILESTONES.md` § THE G-SERIES.** G1, G2, G4, G5 and G6 are marked done
there with what they actually turned out to be.

    1. G3 -- PLAYABLE.md    <- the scoreboard the GOAL needs, the expensive one,
                               and now the only thing between here and the
                               C-series
    2. the C-series         <- content. ⚠ Nothing blocks it and it has a real
                               slope (20 templates take template-ready 41 -> 72)

⚠⚠ **AND THE HEDGE IS GONE.** Three sessions of standing worry — that content
work was being aimed at gaps that are not gaps — was closed by G4 (137 of the 142
routes outside the BOTH column are real work) and confirmed by G6 (whose corpus
cost came out at exactly the zero G4's number predicted). **There is no remaining
instrument question standing between this project and content**, and G3 is the
one artefact question left, because it asks something no existing report does.

## ⚠⚠ ITEM 1: **G3 — `PLAYABLE.md`, the scoreboard the goal needs**

A generated standing audit answering *what can a player make, starting from
what?* `ROUTE_INDEX.md` knows feedstocks but not what runs; `COVERAGE_REPORT.md`
knows what runs but never asks whether a feedstock is obtainable.

⚠ The classification is already written and measured (7 from-the-ground / 6
one-step-up / 14 blocked on an unmakeable intermediate / 4 from a reagent
bottle). ⚠ **The one hand judgement in it — which compounds count as NATURAL —
must be PRINTED, not hidden**, so it can be argued with.

⚠⚠ **G1 GAVE IT A SECOND QUESTION**: `benzene-nitration` went from 0.1762 to
0.8000 mol on a change that touched no species and no template, so "what a player
can make" is not a property of the corpus alone. **A PLAYABLE scoreboard has to
RUN things**, which is what makes it different from the two artefacts above and
also what makes it expensive.

⚠⚠ **G4 GAVE IT A THIRD, THE CHEAPEST: G4's FIVE ARE ALREADY-RUN ROUTES A
PLAYABLE SCOREBOARD MUST NOT SCORE AS BLOCKED.** More usefully,
`validation/granularity.py`'s `reachable()` is the DAG walk G3 needs and it
already carries the rule that took three sessions' worth of trap out of it —
**the target may not be charged.** ⚠ Do not re-derive that; a scorer without it
credits every recycle loop in the corpus (`bayer-process`, `contact-process`).

⚠⚠ **G5 GAVE IT A FOURTH, WHICH IS SHARPER: A ROUTE CAN BE BLOCKED ON WHETHER ITS
NETWORK BUILDS AT ALL.** Aniline + nitric acid with electrolyte support REFUSES,
on a nitroanilinium pKa nobody curated. That is not a species being unpriced and
it is not a template being missing — it is a *combination* failing — and neither
existing artefact can see it.

⚠⚠ **AND G6 GAVE IT A FIFTH, WHICH IS THE MOST AWKWARD ONE: A YIELD IS NOT A
PROPERTY OF THE ROUTE, IT IS A PROPERTY OF THE DECLARED CONSTANTS ON THE DAY.**
G6 changed no species, no template and no route, and moved one substrate's rate
by 2400x while leaving all three nitration yields identical to four decimals.
**So a scoreboard that prints yields will print numbers that move under sessions
that were not about it** — which is fine if it says what it ran and prints its
conditions beside every number, and misleading if it reads as a property of the
corpus. ⚠ `validation/saturation.py` panel 3 is the shape to copy: the same route,
run twice, under two declarations.

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

1. **⚠⚠ ~~THE HAMMETT LINE DOES NOT SATURATE~~ — CLOSED BY G6.** The plateau is
   declared at 2.686 decades with two sources and a written bound; see
   §"WHAT G6 TURNED OUT TO BE" above. ⚠ What is left of this row is one
   deliberate non-goal: **the plateau is a fixed RATIO, so a capped substrate
   stays a fixed multiple of benzene at every temperature.** A real encounter
   limit is a diffusion rate with its own weak temperature dependence, and the
   two forms are indistinguishable over 300–380 K only because this rate law's
   `k` is six decades under any diffusion constant (measured,
   `validation/saturation.py` panel 1). **If a future template's `k` ever
   approaches an encounter rate in its own units, that argument has to be
   re-measured rather than reused.**

2. **⚠⚠ NO ACIDITY FUNCTION — G5's ROW, AND G6 SHRANK IT FROM 8.63 DECADES TO
   2.87 WITHOUT CLOSING IT. IT IS NOW THE BEST-SCOPED LIMIT ON THIS BRANCH.**
   A mixed acid's acidity is H0, which is not the concentration of anything; this
   engine's only handle is a mass-action molarity whose measured floor is
   **pH −0.79**, against a free-base/anilinium crossover that G6 moved to
   **−3.66**. ⚠⚠ **AND G6 REMOVED THE REASON THIS ROW WAS DEFERRED.** G5 said
   not to build it first because the leak was in how the free base is PRICED,
   not in how much of it there is; the price is now sourced, so an acidity
   function would move the mixture honestly for the first time. ⚠ It is still
   not a table: an H0 is a property of a MEDIUM, which is what
   `chemsim-ion-transfer`'s "an aqueous pKa must not run in an oil" is about.
   **Scope it as physics.** ⚠ And measure what it BUYS first: 2.87 decades is a
   long way for a molarity to travel, and the answer may be that a medium's
   acidity cannot be a molarity at all.

3. **⚠⚠ NO REGIOSELECTIVITY IN THE SUBSTITUENT MODEL (G2), ASSERTED IN G5, AND
   G6 PROMOTED IT TO THE TOP AROMATIC ITEM BY TAKING THE OTHER TWO AWAY.**
   `hammett.survey` sums over the substrate's ring as a whole, so all three
   dinitrobenzenes get the same barrier. `test_protecting_the_amine_is_emergent_and_runs`
   now asserts `ortho == approx(meta)` on the nitroacetanilides (0.1535 each
   against a real ~90% para), **so closing this breaks a test rather than going
   unnoticed.** ⚠ The information EXISTS at rewrite time (`tmpl.run` has the RDKit
   match) and is discarded before the barrier is computed, which is S9's shape
   exactly. ⚠ **Price it against G4 first** — a regioselective nitration may or
   may not move any catalog row.
   ⚠⚠ **AND G6 ADDS A WARNING THAT WAS NOT AVAILABLE BEFORE: A SITE-AWARE SUM
   WOULD BE SMALLER THAN THE RING-WIDE ONE, SO MORE SUBSTRATES WOULD FALL BELOW
   THE PLATEAU AND THE PLATEAU WOULD DO LESS.** The two terms interact and the
   interaction is measurable: `saturates()` is a comparison against
   `rho * sum(sigma+)`, and every number in `validation/saturation.py` panel 2 is
   computed from a ring-wide sum. **Re-measure that panel as part of the
   regioselectivity session, not after it.**

4. **⚠ AN OPEN-ENDED TEMPLATE OVER A CURATED TABLE (G5) — THE REFUSAL STILL
   STANDS, BUT ITS ARITHMETIC MOVED IN G6 AND IS NO LONGER OVERWHELMING.**
   `amine_protonation` protonates every amine a network reaches; the ion table
   prices the typed ones. Nitrating an aniline REFUSES on
   `[NH3+]c1ccccc1[N+](=O)[O-]`. ⚠⚠ G5 measured the nine nitroaniline pKa values
   as buying nothing because the ion channel carried **1e-7 %** of the rate;
   under the plateau **it carries 0.39 %** (`validation/protonation.py` panel 5,
   last column) — five decades closer to mattering, still not enough at this
   pot's acidity. ⚠ **G5 named item 1 as the thing that would change this and it
   was right about the direction, wrong about the size.** Re-measure the last
   column before curating anything; the refusal is the element floor's rule
   applied to a pKa and it is cheap to keep.

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

MILESTONES.md — the plan, and **§ THE G-SERIES first**. ⚠ **§G1, §G2, §G4 and
  §G5 are marked DONE with what they turned out to be, and G1's and G4's original
  briefs are kept underneath because the measurements that overturned them only
  mean something against them.** Then §S13, §S12, §S11, §S10, §S9, §S8, §S7, §M8, §S1, §S3, §S4,
  §S5, §S6.
HANDOFF.md — what exists, and the ethos to preserve. **85 is S1 … 98 is S13,
  99 is G1, 100 is G2, 101 is G5, 102 is G4.**
NEXT_SESSION.md — the invariants table at the bottom is the contract, and **G1,
  G2, G5 and G4 each added a block**. ⚠ Read the two warnings above it before
  trusting any row, and note that **G5's "no acidity function" and
  "the Hammett line does not saturate" rows are LIMITS TO REMOVE**, not
  invariants to keep — as is G2's regioselectivity row.
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy; plus
  `data/catalog/COVERAGE_REPORT.md`.
the memory files (auto-loaded), especially **chemsim-granularity-audit** and
  **chemsim-protonation**, then chemsim-ring-deactivation, chemsim-dropping-funnel,
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
already on it, an amine that PROTONATES in acid, **and a Hammett line that
SATURATES at a sourced encounter plateau — after which an aniline in a hot mixed
acid is finally SLOWER than benzene, which is what it is.** `SAVE_VERSION` is
**6**.
Coverage: **52/229 classes** (was 51 — G4's `saponification` credit), **46
templates**, **41/173 template-ready**, **82/173 species-ready** — and ⚠⚠ **31/173
BOTH, which is the only one of the three a route can be judged on.**
⚠⚠ **AND G4 MEASURED THAT 31 IS ALSO A LOWER BOUND: FIVE MORE ROUTES RUN TODAY
AND ARE SCORED BLOCKED (31 + 5 = 36), while 137 of the remaining 142 are real
work.** See `validation/granularity.py`.
⚠ The corpus's **PHYSICAL half is measured for 652/1583 (41.2%)** as of S13;
its refusals are down to **419 of 1583** as of G5.

---

# ⚠ THE FRAGILITIES

**1. ⚠⚠ THE PLATEAU IS A FIXED RATIO AND NOT A RATE (G6, deliberate).** The
Hammett line saturates now, at a sourced 2.686 decades — but as a ratio to
benzene, so **a capped substrate stays a fixed multiple of benzene at every
temperature** where a real encounter limit is a diffusion rate. ⚠⚠ That is
defensible ONLY because this template's `k` runs six decades below any diffusion
constant across 300–380 K (measured, `validation/saturation.py` panel 1), which
is a property of the nitronium pre-equilibrium being folded into `Ea`. **A
template whose `k` approaches an encounter rate in its own units needs the
argument re-measured, not reused.**
⚠ And the audit that cannot see any of this is still blind: `detailed_balance`'s
collision cap compares `A` while hammett moves `Ea`.

**2. ⚠⚠ NO ACIDITY FUNCTION (G5, and G6 shrank it to 2.87 decades).** The
reachable hydronium floor is **pH −0.79** and the aniline crossover is now
**−3.66** rather than −9.42. H0 is a property of a MEDIUM and there is nowhere in
this engine to put it. **A LIMIT to remove, and G6 removed the reason it was
deferred** — the free base's price is sourced now, so the mixture is the only
wrong part left. ⚠ Measure what it buys before building it: 2.87 decades is a
long way for a molarity to travel.

**3. ⚠ AN OPEN-ENDED TEMPLATE OVER A CURATED ION TABLE (G5).** Nitrating an
aniline REFUSES on a nitroanilinium pKa nobody curated. **The refusal still
stands** — but G5's *"measured to buy nothing"* was measured against the
unsaturated line, and under the plateau the ion channel carries **0.39 %** of
the rate rather than 1e-7 %. Five decades closer to mattering; still not enough.

**4. ⚠ THE PYRIDINIUM IS PRICED AND UNREACHABLE (G5).** An aromatic ring nitrogen
is X2 and `amine_protonation` matches X3. Closing it lands on the Skraup.

**5. ⚠⚠ NO REGIOSELECTIVITY IN A SUBSTITUENT BARRIER (G2, asserted in G5, and
G6 MADE IT THE TOP AROMATIC ITEM).** All three dinitrobenzenes are made at one
rate, and ortho == meta on the nitroacetanilides against a real ~90% para. The
site exists at rewrite time and is discarded. **A LIMIT to remove.** Engine queue
item 3. ⚠ A site-aware sum is SMALLER than the ring-wide one, so it interacts
with the plateau: re-measure `validation/saturation.py` panel 2 inside that
session rather than after it.

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

**29b. ⚠⚠ FIVE CORPUS ROWS CAN NEVER MATCH ANY TEMPLATE (G4).** Their products
are a SUBSET of their reactants — `leblanc` 3, `nitroglycerin` 2, `aspirin` 2,
`soap` 2, `furfural` 1 (`xylose + water -> xylose`). They are workup, not
chemistry, and every coverage number counts them as uncovered mechanisms.
**Asserted by count AND by route id in `tests/test_granularity.py`.**

**29c. ⚠⚠ `starch-hydrolysis` CANNOT START FROM ITS OWN FEEDSTOCK (G4).**
`starch-unit` is spelled as a single α-D-glucopyranose ring, so row 1
(`starch-unit + water -> maltose`) is a hydrolysis making a disaccharide from a
monosaccharide. The engine builds **ZERO reactions** — asserted. ⚠ From maltose
the same template gives 0.9986 mol glucose, so **this is a CORPUS spelling bug,
not an engine gap**, and no template would move it.

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
⚠⚠⚠ **A REACHABILITY SCORER THAT DOES NOT FORBID *CHARGING THE TARGET* CREDITS
EVERY RECYCLE LOOP IN THE CORPUS (G4).** `bayer-process` and `contact-process`
both write their own target on the left of step 1 — Bayer purifies bauxite, the
contact process recycles its acid — and both scored "reachable" by buying the
thing the route exists to make. **The rule is one line and it is the difference
between an instrument and a flattering one.**
⚠⚠⚠ **AND THE LAST SURVIVOR OF THAT RULE WAS STILL WRONG, AND ONLY *RUNNING* IT
SAID SO (G4).** `starch-hydrolysis` passed every static check and built ZERO
reactions. **Three false credits in one session, all three caught by charging a
flask** — S1's *"crediting a class made a FALSE route credit"* is now a three-time
finding, not an anecdote.
⚠⚠ **AN INSTRUMENT THAT SCORES *ROWS* CANNOT SEE A ROUTE'S SHAPE (G4).** A route
is a DAG with alternatives, declared byproducts and workup in it, and the corpus
says which is which **in its own prose** — 9 rows are named `... byproduct` /
`side reaction` / `alternative` and nothing had ever read them.
⚠⚠ **THE THING THE MAP CREDITS IS NOT ALWAYS THE THING THE MAP IS KEYED BY (G4).**
`saponification` was built in M5 and credited under `ester-hydrolysis`'s NAME, so
the catalog class of the same name read as a gap for eight milestones. **Grep the
template names against the class names; it is one command and it found a real one.**
⚠ **HOIST A PROVIDER OUT OF A COMPREHENSION.** Building `electrolyte_provider()`
inside a comprehension over 1583 compounds constructs one per compound: **290 s
against 18 s**, with no symptom but the clock.
⚠⚠ **A COUNT OF THINGS THAT ARE MISSING IS NOT A COUNT OF THINGS THAT ARE WRONG.**
