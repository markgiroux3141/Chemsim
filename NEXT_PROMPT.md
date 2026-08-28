We're building chemsim, an emergent chemistry simulator (game inspired by Nile
Red) in d:\Claude Code Projects\Chemistry Simulator.

**The plan is `MILESTONES.md`. Read it first — it is the authority on what to
build and in what order.** **M0–M6, M8, M12, S1–S13, G1–G6, C1 and C2 are DONE.**

# ⚠⚠⚠ START HERE: THE SUITE IS GREEN AND NOTHING IS OWED

**C1's owed suite was run and came back `1081 passed / 0 failed`, discharging it.
C2's own tree was then run twice more; the final state is**

    1097 passed / 0 failed in 29:55        <- run ALONE, nothing else on the box

⚠⚠ **AND THE MIDDLE RUN CAME BACK 7 FAILED, WHICH IS THE THING TO READ.** C2
re-ran every generated artefact, read every headline they printed, and wrote
those headlines into the docs by hand — and did not run
`tests/test_playable.py`, which PINS the same headlines. Six failures there and
one in `test_protonation`, **every one a number C2 had already measured.** All
seven are corrected. *The generated report and the test that pins it are two
different consumers of the same number, and running one is not running the
other.*

```bash
python -m pytest -q --durations=25          # ~30 min. expect 1097
```

⚠⚠⚠ **AND RUNNING IT IS WHAT CAUGHT C2's OWN BUG, WITH THE SUITE GREEN.** The
headroom fix below went in as `max(math.log(scale), 0.0)` — the same function as
`math.log(max(scale, 1.0))` **only where the log is defined** — and `scale` is
`k_diss * V_L1`, exactly **zero** whenever a vessel declares `k_diss = 0.0`.
Three do: `workshop` part 3, `named_routes`, and `recipes`' crystallise stage (so
`multistep_prep`). All three began raising `ValueError: math domain error` at
rtol 1e-8, **and nothing in `tests/` charges a `k_diss = 0` vessel through the
precipitation branch, so the suite would have stayed green.** A `git stash` of C2
confirmed the three were healthy before. Fixed and asserted
(`test_a_vessel_may_declare_k_diss_ZERO`). **This is the clearest case the
project has for the rule that an RHS edit owes this audit ten minutes.**

⚠⚠ **AND ITS LAST MEASURED STATE IS C2's NOW, NOT S13's.** After the fix the
full audit is back at the recorded baseline: **ONE** example raises
(`named_routes`, the diagnosed entry), `multistep_prep` sweeps at 6 lines / worst
`inf` and `workshop` at 2 lines / 1.98e-04, `activity` at 1.28e-03,
`competing_pathways` 1.77e-05, `vessel` 2.40e-05, `wait_until` 1.03e-04, and
`esterification` / `extraction` / `lime_cycle` / `roasting_and_the_catalyst_gate`
/ `mercury_retort` byte-identical. ⚠ `mercury_retort` is the harness's own
self-check and it passes at **0 lines and 1.02x** — if that row ever moves,
the tolerance rebinding has stopped working and every other row is suspect.

⚠⚠ **`tolerance_audit.py` WAS OWED BY C2 AND WAS RUN** — C2 edited the RHS
(`PrecipitationArrays`'s saturation cap). ⚠ The pKa row is separately **measured
bit-identical for all 28 pre-existing ions** (`test_adding_it_is_BIT_IDENTICAL_
for_every_pre_existing_ion`), so the data half owed nothing; the RHS edit is what
owed it, and the RHS edit is **bit-identical wherever `k_diss * V_L1 <= 1`**,
which is every vessel in this repo.

---

# ⚠⚠⚠ WHAT C2 TURNED OUT TO BE

**C2 was the second C-series item, taken off `data/catalog/PLAYABLE.md` §8:
`calcium-phosphate`, the row that file called "THE CHEAPEST ROW IN THE TABLE AND
IT IS A LOOKUP". 14 → 16 playable, 37 → 39 runnable, 83 → 85 species-ready,
32 → 34 BOTH, 419 → 416 refused. Classes 53/236 and template-ready 42 are
UNCHANGED — no class, no template. HANDOFF §106, MILESTONES §C2, NEXT_SESSION's
last block.**

## ⚠⚠⚠ 1. THE +2 WAS EXACTLY RIGHT AND THE REASON GIVEN FOR IT WAS ENTIRELY WRONG

The catalog spells the rock as its IONS, so `catalog_coverage` prices it
**fragment by fragment** through `electrolyte_provider`, and the fragment it
choked on was `[O-]P([O-])([O-])=O`. `ion_data` has carried phosphate, hydrogen
phosphate and dihydrogen phosphate on the aqueous basis since M3;
`electrolyte._PAIRS` carried phosphoric acid's **1st and 2nd** dissociations and
stopped. **The route was blocked on a missing pKa, in a table nobody was looking
at, while the work order named a mineral.**

Measured as a 2x2 rather than guessed:

    compound              neither   pKa row   mineral row     both
    calcium-phosphate     refused    priced        priced   priced
    sodium-phosphate      refused    priced       refused   priced
    phosphate-ion         refused    priced       refused   priced

**All three move on the pKa row alone. The mineral row's contribution to every
published coverage number is ZERO.**

⚠⚠⚠ *A ROUTE'S BLOCKER CAN BE IN A DIFFERENT TABLE FROM THE ONE THE WORK ORDER
NAMES.* C1 found a route blocked on a price for a species **not in its
chemistry**; C2 found one blocked on a price **in the wrong table**. Both had been
recorded as a mineral-curation job for three milestones and neither was one.
**That is twice in two sessions. Check what the refusal actually IS before
costing it.**

## ⚠⚠⚠ 2. AND THE MINERAL ROW IS WHY IT RUNS, WHICH IS A DIFFERENT QUESTION

Drop the `MineralRecord` and keep the pKa: `phosphoric-wet` still reads
species-ready, still counts in BOTH, still scores playable — and the rock is
**INERT at 0.0000 %**, its ions sitting in the solid block for ever because no
Ksp connects them to the solution. With it, **8.03 %** in 600 s at k_diss 10.

⚠⚠ **THE SCORE AND THE CHEMISTRY CAME OUT OF DIFFERENT TABLES AND NEITHER ONE
IMPLIES THE OTHER.** G4's *"only RUNNING it said so"* from a new side: G4's three
false credits were routes that scored and did not run; this is a route that
scores on one table and needs a second one to move.

## ⚠⚠ 3. THE MEMBERSHIP GAP, AND FIVE LATTICES ARE STILL IN IT

`solubility_product`'s docstring warns at length that `ion_data` and
`electrolyte` price the same ions on different **ZEROS**. **Nothing anywhere
compares which ions they HAVE.** Of the 30 lattices that can be given a Ksp,
**25 can be put in a flask and 5 cannot** — `sphalerite`, `galena`, `covellite`,
`chalcocite`, `cinnabar`, **all five on `[S-2]`**. Same shape: `_PAIRS` carries
`H2S -> [SH-]` at pKa 7.00 and stops.

⚠⚠ **THE SULFIDE STEP IS A REFUSAL, NOT THE NEXT ONE-LINE FIX.** `HS- -> S2-` is
quoted between about **12.9 and 19** depending on the compilation — six decades
of disagreement about one number. Phosphoric acid's third pKa was takeable
*because* the two rows above it fix the series: **2.15 / 7.20 / 12.35**, not
CRC's 2.16 / 7.21 / 12.32, which is the iodide row's decision made a second time.
⚠ **The trigger is written down in `data/catalog/README.md`** in C1's landmine
form: the day anything credits a sulfide route, it will score and refuse to build.

## ⚠⚠⚠ 4. exp() BEING FINITE IS NOT k*V*exp() BEING FINITE — AND IT ANSWERS ENGINE QUEUE ITEM 6

`LN_SATURATION_CAP` exists, in its own words, *"so that a transient absurd state
during a Jacobian perturbation cannot produce an inf"* — **and it did not.** It
bounds a CONCENTRATION; the next line multiplies by the liquid volume, which a
Newton iterate does not bound. Instrumented, the failing state is

    T = 1.0 K     nL1 = 5.0e10 mol     V_L1 = 9.2e8 L     roots -> exp(700)

⚠⚠⚠ **AND `T = 1.0 K` IS ENGINE QUEUE ITEM 6's OPEN QUESTION, ANSWERED.** That row
records a PSRK overflow below 4.28 K and says *"nothing has found WHICH call
passes a T that low"*. **Nothing does: `T_MIN = 1.0` manufactures it.** A Newton
iterate proposes a temperature below 1 K and the RHS's
`min(max(float(y[-1]), T_MIN), T_MAX)` hands every term exactly 1.0 — so every
`1/T` in the right-hand side is evaluated 297 K outside its domain at once.
**Item 6's probe does not need writing.**
⚠ The overflow was **measured harmless in both the answer and the clock** —
identical digits, 79.1 s against 81.2 s. The word that changed is "unbounded".

## ⚠⚠⚠ 5. THE DEFAULT TOLERANCE CANNOT BE TRUSTED ON THIS FLASK

    k_diss   loose conv   loose s    tight conv   tight s   ratio
      1       46.059%      36.3        0.823%       2.4     56.0
     10        8.032%      58.5        8.032%      16.6      1.00

⚠⚠ **The default is wrong at one knob setting and right at another, and nothing
in the answer says which.** ⚠ The tight run is also the **fast** one — 15x — which
is the tell: the loose solver is thrashing, not saving work.
⚠⚠ **C2's FIRST SWEEP WAS RUN AT THE DEFAULT AND WAS ENTIRELY WRONG**, non-
monotonic in both k_diss and time (46 % at 600 s against 4.9 % at 3600 s; 8 % at
k_diss 10 against 46 % at k_diss 1). *A non-monotonic sweep is not a finding
about chemistry; it is a solver saying it has not converged, and reading it as
chemistry is how a wrong number gets written down.* **Every number in C2 is at
rtol 1e-8, tests included.**

## ⚠⚠⚠ 6. THE LIMIT: AN ACID CANNOT ATTACK A CRYSTAL

Dissolution is `k_diss * V * (Qroot - Ksproot)` — **no acid term and no
surface-area term.**

    33x the acid       conversion 8.032% -> 8.363%,  pH 1.487 -> -0.001
    10x the ROCK       the SAME 8.0e-4 mol dissolved (8.03e-4 vs 8.20e-4)
    10x the knob       10x the conversion, exactly

At the vessel default the cap is `k_diss * V * Ksp^(1/5)` = 2.9e-9 mol/s —
**40 days for 0.01 mol.** A real wet-process digestion is a SURFACE reaction
going with [H+]; this engine has that shape for a **gas** arriving at a crystal
(`SurfaceArrays`, S1) and **not for a liquid**. **So the rock digests on a vessel
knob rather than on its chemistry.** ⚠ No gypsum drops either, and that is
arithmetic, not a bug: **Q/Ksp = 0.26**, genuinely undersaturated at this dilution.

## ⚠⚠ 7. THE WORK ORDER SHRANK, WHICH IS C1's LESSON IN REVERSE

    fed but unrunnable   24 -> 22        ceiling   41 -> 41  (UNCHANGED)
    need NO template      4 ->  2        ethylene  +1 -> +2

C1 granted one row and the list grew 21 → 24. C2 granted two and it shrank,
because phosphoric acid feeds no route that was not fed already. ⚠ But the shelf
still re-priced a lever: **`ethylene` was +1 and is +2**, because
`ethanol-hydration` was blocked on ethylene *and phosphoric acid*.
*Re-run `tools/build_playable.py` after every content item; the worths move in
both directions, and not where you expect.*

## ⚠ 8. WHAT C2 DID NOT DO, SAID OUT LOUD

* **`superphosphate` is SCORED, NOT DEMONSTRATED.** Its catalog row is a "den,
  ambient" paste with **no water**, and an engine whose only ionic chemistry is
  aqueous cannot express a solventless acidulation. It scores through the same
  two data rows.
* **`white-phosphorus` did NOT move** and names calcium-phosphate too: no
  `carbothermic-phosphate-reduction` template, no P4 formation pair in any source
  here, `calcium-silicate` refused. **Pricing one species of four is worth
  nothing on a route.**
* **A data job is only cheap when the data is there.** Of PLAYABLE §8's four
  *"needs no template at all"* rows, only the rock had both halves in one
  database: `calcium-silicate` has **nothing** under three CAS numbers, `pyrite`
  WEBBOOK-and-nothing, `sodium-hypochlorite` nothing. Engine-queue items 11 and
  14 are re-confirmed rather than re-derived.

---

# ⚠ WHERE THE WORK ORDER STANDS: `data/catalog/PLAYABLE.md` §8, RE-GENERATED

**22 routes are already FED from natural materials and blocked only on a template
or a price. Grant all 22 and playability goes 16 → 41.** Read §8 before picking
anything; it is the only ranking in the repo tied to the GOAL, and it disagrees
with `COVERAGE_REPORT.md`'s greedy curve.

    +3  hall-heroult          molten-salt-electrolysis  -- ENGINE work (a MELT is
                                not a phase this project has) and cryolite is
                                refused a price. The top row is not the cheap one
    +2  abe-fermentation      fermentation  -- M5 REFUSED this class as a
                                metabolic network. Read that refusal first
    +2  blast-furnace         slagging  -- blocked TWICE on SOURCES, and C2
                                re-confirmed one of them: `calcium-silicate` has
                                NO Hfs and NO S0s under any of three CAS numbers
    +1  hypochlorite-bleach   a refused `sodium-hypochlorite` price -- and C2
                                probed it: NEITHER half exists. Not a lookup
    +1  pyrite-roasting       `iron-disulfide` refused -- engine queue 14's own
                                source-blocked entry (Hfs in WEBBOOK, S0s in
                                nothing), re-confirmed by C2's probe.
                                **RE-QUERYING IT IS NOT WORK; READ THE REFUSAL**
    +1  x17 more

⚠⚠⚠ **THE TWO "NEEDS NO TEMPLATE AT ALL" ROWS LEFT ARE BOTH SOURCE-BLOCKED, AND
C2 MEASURED BOTH.** That bucket was four rows and read as a data job; C2 took the
one that had data and probed the other three in the same run. `calcium-silicate`,
`pyrite` and `sodium-hypochlorite` **do not have an Hfs and an S0s in one
database**, and the rule that both halves come from one tabulation is what makes
them refusals rather than entries. ⚠ **There is no cheap data row left in §8.**

⚠⚠⚠ **AND C2's REAL LESSON FOR WHOEVER PICKS THE NEXT ONE: THE BLOCKER NAMED IN
THE TABLE MAY NOT BE THE BLOCKER.** §8's `refused species` column is derived from
`catalog_coverage`'s tier, which asks whether the *providers* price a species —
it does not say WHICH table the price would have to go in. C2's row said
`calcium-phosphate` and the actual block was a **pKa** in
`properties/electrolyte.py`. C1's said `iron-ii-oxide` and the species **was not
in the reaction at all**. *Two for two. Before costing a refused species, print
the refusal and read what it says.*

⚠⚠ **AND CHECK BOTH HALVES, BECAUSE THEY ARE DIFFERENT TABLES.** A pKa (or an
`ion_data` row) makes a route **SCORE**; a `MineralRecord` is what gives a lattice
a **Ksp** so it can actually dissolve. C2 measured them one at a time and they
were disjoint: with the pKa and no mineral row, `phosphoric-wet` counts as
species-ready, counts in BOTH, counts as playable — and converts **0.0000 %**.

⚠⚠ **THE NOx ITEM IS STILL WORTH +1**, unchanged by C2. Fragility 31 stands: the
lead chamber is blocked on a pinch of NO2 nothing reachable makes, and the corpus
holds saltpetre as a natural material with no step that turns it into NOx.
⚠ `ethylene` is now the joint-biggest single grant at **+2** (with `aluminium`),
which is new: C2's phosphoric acid removed the other half of `ethanol-hydration`'s
blocker. **A content item can re-price a lever it never touched.**

---

# THE STANDING AUDITS

```bash
python validation/phosphate_rock.py            # ⚠⚠ C2's, ~280 s -- the most
                                               #   EXPENSIVE audit here. NEW -- read panels
                                               #   2, 5, 6 and 7. ⚠ Panel 7 is why every
                                               #   number in it is at rtol 1e-8
python validation/vitriol.py                   # C1's, 18 s. read panels 3, 5 and 7
python validation/saturation.py                # G6's, 27 s. read panels 1, 3 and 5
python validation/protonation.py               # G5's, 20 s. REWRITTEN BY G6 -- panels 3 and 5
python validation/ring_deactivation.py         # G2's, 14 s. REWRITTEN BY G6 -- panels 1 and 5
python validation/granularity.py               # G4's, 20 s. ⚠ NOW 34 + 5. panels 3 and 4
python validation/dropwise.py                  # G1's, 78 s
python validation/boiling_points.py            # S13's, 2 s. READ PANEL 2
python validation/skraup.py                    # S12's, ~10 s
python validation/smelting.py                  # S9's, ~1 min
python validation/hydroformylation.py          # S11's, ~1 min
python validation/wacker.py                    # S11's other one, ~1 min
python validation/gas_processes.py             # S7's, ~1 min
python validation/corpus_balance.py            # S7's other one, ~20 s. ⚠⚠ C1 measured that
                                               #   it CANNOT decide a wrong row: the old
                                               #   vitriol row balanced too
python validation/catalog_coverage.py          # ⚠ 'BOTH' is 34/173, ~9 s. ⚠⚠ AND IT IS A
                                               #   LOWER BOUND TOO -- G4's rule gives 34+5
python validation/physical_estimation.py       # S13 took its panel 3 to n=254
python validation/game_gates.py                # the element floor's cross-check, seconds
python tools/build_playable.py                 # ⚠⚠ G3's, ~56 s. WRITES
                                               #   data/catalog/PLAYABLE.md -- it RUNS
                                               #   the deep chain. ⚠ 16/173 playable
python tools/build_route_index.py              # the artefact nothing reads -- ⚠ and
                                               #   PLAYABLE is the one that now HAS tests
python validation/cell_potentials.py           # M8's standing audit, seconds
python validation/rate_ceiling.py              # G6 moved its fastest activated
                                               #   nitration by EIGHT DECADES
python validation/jacobian_bound.py            # S5's standing audit, ~1 min
python -m ruff check src tests examples validation tools
python -m pytest -q --durations=25             # ~23 min, expect 1097. ⚠⚠ RUN IT ALONE --
                                               #   C2 measured +25% wall clock from ONE
                                               #   concurrent single-threaded job
python validation/tolerance_audit.py           # ~10 min. ⚠⚠ C2 OWED it (RHS edit),
                                               #   RAN it, and it CAUGHT a crash the whole
                                               #   green test suite missed
```

⚠ **THE SUITE AND THE TOLERANCE AUDIT ARE MINUTES OF SATURATED CPU ON THE USER'S
OWN MACHINE.** Say what a long run will cost before starting one, and ask.
`examples/plate_column.py` alone is 12 minutes.

⚠⚠⚠ **AND THERE IS A TRAP IN WRITING A NEW AUDIT THAT COST G6 TWO CRASHES: THE
CONSOLE IS cp1252 AND THE WARNING GLYPH CANNOT BE PRINTED.** Every audit in this
repo keeps `⚠` in docstrings and comments and out of `print`, and that is not a
style choice — `python validation/x.py` dies with `UnicodeEncodeError` mid-panel.
⚠⚠ **A `build_network` NOTICE is printed too**, so a glyph in one crashes every
audit and example that reaches that reaction.
⚠⚠ **AND IT BITES `python -` HEREDOCS TOO (C1):** a one-off probe that prints a
line out of `NEXT_PROMPT.md` dies the same way unless `PYTHONIOENCODING=utf-8` is
set. Cheaper to set it than to discover it.

⚠⚠ **THE `--durations=25` LISTS ARE AN INSTRUMENT NOW, AND THE NOISE FLOOR IS
MEASURED.** G5 against G6:

                        G5        G6      change
    top 25           803.1 s   819.8 s   59.6% -> 59.3% of the suite
    test_still x6    402.2 s   415.8 s   29.8% -> 30.1%
    the ONE RIG test 164.1 s   176.9 s   **+7.8%**
    catalysis         74.1 s    75.1 s   +1.4%
    burner @rtol 1e-8 52.5 s    52.8 s   +0.7%
    the long tail     0.55 s    0.55 s   **IDENTICAL to two decimals**
                                         (999 tests then, 1020 now)

⚠⚠ **SO THE NOISE FLOOR IS ~8% ON THE BIGGEST SINGLE ROW AND ~1% ON THE MID
ROWS**, which is what makes the list an instrument: G6's +35 s over G5 is noise
plus 16.6 s of new test files and must not be attributed to anything, while the
S12->S13 eight minutes is **20x outside** the floor and remains a real unexplained
regression. ⚠ It still does NOT diagnose S12->S13 — no list exists on either side
of that commit — and the cheap next step is unchanged: a `git stash`-and-rerun of
`--durations=25` across S13's data commit.

---

# ⚠ THE ENGINE AND HONESTY QUEUE — **REFERENCE, NOT THE WORK ORDER**

⚠⚠ **`data/catalog/PLAYABLE.md` §8 IS THE WORK ORDER NOW.** This queue is kept
because every row is a measured, live finding — but **do not start here**, and do
not treat a row's age as a reason to take it.
⚠⚠⚠ **AND C1 CLOSED ONE ROW AND RE-PRICED THREE.** Item 17 (`hydrolysis`) is
DONE; item 11's `iron-ii-oxide` turned out never to have been in
`vitriol-distillation`'s chemistry at all; item 14's `pyrite` is still refused but
is now one of FOUR playability blockers rather than two; and item 15 has the
cheapest reproduction anyone has found.
⚠⚠ **AND G3 GAVE THIS QUEUE A NEW WAY TO BE PRICED: ASK WHAT A ROW BUYS IN
PLAYABILITY, NOT IN ROUTES.** Three rows below already cash out there — item 11's
`calcium-silicate` blocks `blast-furnace`, which is worth **+2**; item 14's
`pyrite` blocks `pyrite-roasting`, which needs **no template at all**; and item
17's `hydrolysis` unlocks `vitriol-distillation`, worth **+2**. ⚠ Each was priced
at "+1 route" or "zero routes" before. **A row worth zero coverage can still be
worth two tiers of a tech tree**, and nothing measured that until now.

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

6. **⚠⚠⚠ THE PSRK OVERFLOW -- AND C2 ANSWERED THE HALF THIS ROW SAID WAS UNKNOWN.**
   ⚠⚠⚠ *"WHAT IS NOT KNOWN IS WHERE -- nothing has found which call passes a T
   that low."* **Nothing does: `T_MIN = 1.0` manufactures it.** A BDF Newton
   iterate proposes a temperature below 1 K and the RHS's
   `min(max(float(y[-1]), T_MIN), T_MAX)` hands every term in the right-hand
   side exactly 1.0 at once. C2 found it in a DIFFERENT term -- the
   precipitation drive -- by instrumenting the state at the overflow, and the
   probe this row asks for does not need writing. ⚠ What is LEFT of the row is
   the same question the precipitation cap turned out to have: `np.exp(-a/T)`
   being finite is not the same claim as the term that CONSUMES it being
   finite. **Check the multiply, not the exponential.**
   The rest of the row, unchanged: `activity.activity_coefficients` overflows `np.exp(-a / T)`
   below **4.28 K** (measured: `max(-a/T)` is 760 at T=4 and 292 at T=10).
   `plate_column` prints **five `RuntimeWarning` lines where it printed none**.
   ⚠ **MEASURED HARMLESS WHERE IT FIRES** — heart 0.8548 against 0.8544, target
   met, replay exact. **The word to change is "inert", not the number.**
   ⚠ ~~*WHAT IS NOT KNOWN IS WHERE*~~ — **ANSWERED BY C2, above.** Worth ZERO
   routes, and now worth less work than it was.

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
    ⚠⚠ **C2 RE-CONFIRMED THE `calcium-silicate` THIRD**: no `Hfs` and no `S0s`
    under **any** of its three CAS numbers, printed in
    `validation/phosphate_rock.py` panel 1. It is not a curation job and it never
    was one.
    ⚠⚠ **C1 RESOLVED THE `iron-ii-oxide` THIRD OF THIS ROW WITHOUT CURATING
    ANYTHING**: it was in `vitriol-distillation` only because the catalog row was
    wrong, and the engine has always made hematite there. It is still refused, and
    it is still named by `blast-furnace` — where it may well be right. **Check
    whether a refused species is actually in the chemistry before pricing the
    refusal as work.**

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
    AND AGAIN IN C2, AND THE REFUSAL STANDS BOTH TIMES**: `Hfs` in WEBBOOK,
    `S0s` in **nothing**. ⚠⚠ C2 probed it for free alongside the row it was
    actually taking, which is the cheap move — **probe the neighbours of the row
    you take**. `validation/phosphate_rock.py` panel 1 re-measures all four.

15. **⚠⚠ THE BURNER — measured at 52.47 s at rtol 1e-8 against 0.8 s at the
    default, and it is the 5th most expensive test in the suite (3.9%).** S5
    bounded the CRASH and explicitly did not bound the THRASHING. BDF is
    struggling with a liquid layer holding **1e-29 mol**, which `LAYER_REABSORB`
    drains toward zero without ever reaching it. **The question nobody has asked
    is whether a layer below `LAYER_EPS` should be *merged discretely* at a step
    boundary rather than drained continuously for ever** — `merge_phases` already
    does exactly that at the `run` boundary. **Measure the layer-2 inventory over
    the failing run before designing anything.**
    ⚠⚠⚠ **C1 FOUND A MUCH CHEAPER REPRODUCTION AND THAT IS THE NEWS ON THIS ROW.**
    A one-pot flask of green vitriol and water — **six species, one template** —
    at the DEFAULT tolerance:

        800 K, 2000 s     0.4 s      liquid layer 3.4e-17 mol
        900 K,  500 s    44.4 s      liquid layer 6.6e-17 mol
       1000 K,  200 s    > 9 MINUTES, did not finish

    ⚠ The same charge with NO water is `validation/vitriol.py` panel 1 and costs
    0.3 s, so the water is the trigger.
    ⚠⚠⚠ **AND C2 ADDS A THIRD REPRODUCTION WITH THE OPPOSITE SIGN, WHICH IS THE
    USEFUL HALF.** The wet-process flask is **ELEVEN species and no second
    layer**, and at k_diss = 1 it takes **36.3 s at the default tolerance and
    2.4 s at rtol 1e-8** — 15x FASTER tight, with a **56x** different answer.
    So the loose solver is thrashing on a flask with no `LAYER_REABSORB` in it at
    all: the mechanism here is the PRECIPITATION drive against a Ksp of 1e-33,
    not a vanishing liquid layer. **Two different terms produce the same
    symptom**, and item 15's diagnosis has only ever been checked against one of
    them. ⚠ `validation/phosphate_rock.py` panel 7. **This is the instrumentable version of
    the burner**, and the layer-2 inventory the row asks for is now cheap to
    print. ⚠ A gas-phase receiver at 700 K (above the acid's 610 K Tb) is a third
    reproduction at **434 s**. See `validation/vitriol.py` panel 7.

16. **THE CORPUS BALANCE BACKLOG — 75 ROWS, AND IT IS NOT A TO-DO LIST.** S7
    built the check and deliberately fixed nothing, on the `diels-alder-route`
    precedent. ⚠ But **17 of the 75 are `spurious`** and those are the cheapest to
    correct. ⚠ `tools/catalog.py`'s `validate` still does NOT check balance, so
    the corpus can grow another one silently.

17. **⚠⚠ ~~`hydrolysis`~~ — CLOSED BY C1, AND BOTH HALVES OF THE ROW WERE
    WRONG.** It was not a template-shaped thing at all: eight rows and at least
    six mechanisms, sitting next to seven `*-hydrolysis` classes the taxonomy had
    already named. Split eight ways; only `sulfur-trioxide-hydration` is built.
    ⚠ And *"step 1 reads `-> iron-ii-OXIDE` while the engine makes HEMATITE"* was
    right about the fact and wrong about the consequence — **FeO's refusal was
    never a curation job, because FeO is not in the reaction.** The row is
    corrected. See MILESTONES §C1 and `data/catalog/README.md`.

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
⚠⚠⚠ **AND G3 RE-PRICES TWO OF THEM UPWARD AND THE BEST ONE DOWNWARD.**
`molten-salt-electrolysis` is worth **+1 route** here and **+3 playable** via
`hall-heroult` (aluminium → thermite → iron → haber-bosch), which makes it the
single most valuable class in the corpus — still ENGINE work, and its cryolite is
refused a price, so it is not the cheapest. `direct-combination` reaches
`vermilion-route`, which is fed. ⚠⚠ But `fischer-tropsch`, called *"the queue's
best CONTENT row"*, is **not in PLAYABLE's fed list at all, and it is blocked on
its IRON CATALYST** rather than on its syngas — measured, `needs - shelf ==
{iron}`. So a 25-slot lump template buys **nothing a player can reach** until
`blast-furnace` or `thermite` lands first. ⚠ **Price a content row against
PLAYABLE §8 before taking it**, and note that this is the catalyst rule biting a
third time.

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

⚠⚠ **`data/catalog/PLAYABLE.md` FIRST, AND §8 OF IT IS THE WORK ORDER.** It is
  the only artefact that scores against the GOAL, and it is new. §1 for the
  shape, §3 for the four scoring rules, §5 for what the runs bought, §8 for what
  to build.
MILESTONES.md — the plan, and **§ THE C-SERIES first: §C1 and §C2 are DONE and
  they are the only worked examples of what a C-series item looks like. Read
  §C2 §1 and §2 before pricing any row of the work order.** Then § THE G-SERIES,
  which is COMPLETE. ⚠ **§G1, §G2, §G3, §G4, §G5 and §G6 are marked DONE with
  what they turned out to be, and G1's, G3's and G4's original briefs are kept
  underneath because the measurements that overturned them only mean something
  against them.** Then §S13, §S12, §S11, §S10, §S9, §S8, §S7, §M8, §S1, §S3,
  §S4, §S5, §S6.
HANDOFF.md — what exists, and the ethos to preserve. **85 is S1 … 98 is S13,
  99 is G1, 100 is G2, 101 is G5, 102 is G4, 103 is G6, 104 is G3, 105 is C1,
  106 is C2.**
NEXT_SESSION.md — the invariants table at the bottom is the contract, and **G1,
  G2, G3, G4, G5, G6, C1 and C2 each added a block**. ⚠ **C2's block opens with
  what is wrong with the suite run that discharged C1's debt.** ⚠ Read the two warnings above it
  before trusting any row, and note that **G5's "no acidity function" row and
  G2's regioselectivity row are LIMITS TO REMOVE**, not invariants to keep — as
  is G3's `lead-chamber` NOx row. ⚠ **G3's block adds no ENGINE invariant**:
  every row in it is a property of the corpus as scored. ⚠⚠ **C1's block opens
  with the fact that the full suite was not run.**
GAME_DESIGN.md — the settled design.
data/catalog/README.md — the reaction-class taxonomy, ⚠ **its paragraph on why
  the THREE generated reports answer three different questions and are routinely
  confused for one**, and ⚠⚠ **C1's two new sections plus C2's: the landmine
  S3 recorded and C1 tripped on purpose, the `hydrolysis` split table, and C2's
  own landmine with its trigger named -- a sulfide route will SCORE and refuse
  to BUILD**; plus
  `data/catalog/COVERAGE_REPORT.md`.
the memory files (auto-loaded), especially **chemsim-phosphate-rock**,
  **chemsim-oil-of-vitriol** and **chemsim-playable-scoreboard**, then
  **chemsim-granularity-audit**, chemsim-protonation,
  chemsim-hammett-saturation, chemsim-ring-deactivation,
  chemsim-dropping-funnel, chemsim-skraup-standard-state, chemsim-ion-transfer,
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
already on it, an amine that PROTONATES in acid, a Hammett line that SATURATES at
a sourced encounter plateau — after which an aniline in a hot mixed acid is
finally SLOWER than benzene, which is what it is — **a scoreboard that says what
a PLAYER can reach, and OIL OF VITRIOL MADE FROM A ROCK: green vitriol roasted at
red heat and its trioxide caught in a cool receiver, with a 664 K ceiling nobody
declared** — **and PHOSPHATE ROCK DIGESTED IN OIL OF VITRIOL, whose blocker was
a pKa in a table nobody was looking at. `SAVE_VERSION` is **6**.
Coverage: **53/236 classes**, **47 templates**, **42/173 template-ready**,
**85/173 species-ready** — and ⚠⚠ **34/173 BOTH, which is the only one of the
three a route can be judged on.** ⚠ C2 added NO class and NO template: its two
lines were a pKa and a mineral.
⚠⚠ **AND G4 MEASURED THAT IT IS ALSO A LOWER BOUND: FIVE MORE ROUTES RUN TODAY
AND ARE SCORED BLOCKED (34 + 5 = 39), while 137 of the remaining 139 are real
work.** See `validation/granularity.py`.
⚠⚠⚠ **AND PLAYABILITY IS A THIRD NUMBER, LOWER THAN BOTH OF THOSE AND THE ONLY
ONE TIED TO THE GOAL: 16 of 173 (G3's instrument, C2's number).** 39 runnable,
**16 playable from natural materials** — tiers **9 / 6 / 1** — and the ceiling on
the declared natural list is **41** once the 22 fed-but-unrunnable routes land.
⚠ Both of C2's routes landed in tier 2, so the BUSH is still a bush: 9 of the 16
touch nothing another route made.
⚠ A route can be fully covered, fully indexed and unreachable.
`data/catalog/PLAYABLE.md`.
⚠ The corpus's **PHYSICAL half is measured for 652/1583 (41.2%)** as of S13;
its refusals are down to **416 of 1583** as of C2.

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
for all 24 pre-existing anions. **C2 RAN IT, AND IT PAID.** C2's own RHS fix
raised `ValueError: math domain error` in three examples on `k_diss = 0.0` and
**the whole test suite stayed green**; the audit caught it against its own
baseline. ⚠⚠⚠ *This row is no longer a discipline argument —
it is a measured save.* ⚠ C2's pKa row is separately measured BIT-IDENTICAL
for all 28 pre-existing ions, so the data half owed nothing.

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

**30. ⚠⚠⚠ ONLY 14 OF 173 ROUTES ARE PLAYABLE, AND 9 OF THE 14 ARE TIER 1
(G3's instrument, C1's number).** The GOAL asks for a connected tech tree; the
corpus is a fan of one-step routes off the ground with **one** three-tier chain
hanging off it, and that chain runs through a zinc retort's **byproduct**.
⚠ C1 added one route to each of the first two tiers, so the SHAPE did not change.
Not a bug in anything — it is the measurement the G-series existed to get, and it
is what the C-series is aimed at. `data/catalog/PLAYABLE.md`, asserted in
`tests/test_playable.py`.

**31. ⚠⚠ `lead-chamber` IS BLOCKED ON A PINCH OF NOx THAT NOTHING REACHABLE
MAKES (G3), AND C1 HALVED WHAT CLOSING IT IS WORTH.** Its carrier is catalytic —
G4's run charged 0.004 mol of NO2 and measured it recovered — but the corpus holds
saltpetre as a natural material with **no step that turns it into NOx**, which is
historically where the charge came from. ⚠ **A CORPUS gap, not an engine one**,
and still a LIMIT to remove. ⚠⚠ **But it is worth +1 now, not +2**: G3's second
point was `saltpetre-nitric` off the chamber's acid, and C1 gave that route its
acid from a rock instead. Sulfuric acid is no longer a blocker of anything.

**32. ⚠⚠ THE PLAYABILITY SCOREBOARD RESTS ON A HAND JUDGEMENT, AND IT IS
GENEROUS (G3).** 45 species are declared NATURAL where the GOAL says ~10, so **12
is an UPPER bound**. The list and its arguable half are printed in
`PLAYABLE.md` §2 precisely so they can be argued with; **argue with that list and
every number in the file moves.**

**33. ⚠ A YIELD IN `PLAYABLE.md` §5 IS NOT A CORPUS PROPERTY (G3, deliberate).**
G6 moved one substrate's rate 2400x while changing no species, template or route,
so §5 prints T, charge, tolerance and catalyst loading beside every number and
says what it ran. ⚠ Methanol converts **7.7%** on the retort's own gas and
**99.8%** at the corpus's declared charge: *"reachable" and "worth doing" are
different questions.*

**34. ⚠⚠ A ROUTE CAN BE BLOCKED ON A PRICE FOR A SPECIES THAT IS NOT IN ITS
CHEMISTRY (C1).** `vitriol-distillation` named `iron-ii-oxide`, which the engine
has never made there — `solid_state.py` has declared hematite since M6 — and the
refusal read as a curation job for three milestones. ⚠ **Check whether a refused
species is actually in the reaction before pricing its refusal as work.** Two of
the remaining refusals in the engine queue (`calcium-silicate`, `pyrite`) have not
been checked that way.

**35. ⚠⚠ ONE OF G3's FOUR SCORING RULES NOW HAS NO MEASURABLE COST (C1).**
Rule 3 — *a route shelves its target AND its byproducts* — was justified by 13
against 14; every cell is equal now, because the route it bought got its sulfuric
acid from somewhere else. **The rule is KEPT and the zero is asserted**, with the
reason written above the grid in `tests/test_playable.py`. *A rule justified by a
difference must not be reverted the day the difference goes away.*

**36. ⚠ THE GAS-PHASE SO3 HYDRATION IS AN APPARENT BARRIER OVER A RECALLED
CONSTANT (C1, deliberate).** The real reaction is second order in water; `A` is
pinned at the collision limit's order and `Ea` puts `k(298)` at the ORDER of a
literature figure that is **recalled, not sourced from anything in this repo**.
Defensible only because the answer is 100.000% across five decades of `A` —
`validation/vitriol.py` panel 4. ⚠ If a future template ever puts this reaction
somewhere the rate matters, that panel has to be re-measured, not cited.

**37. ⚠⚠⚠ AN ACID CANNOT ATTACK A CRYSTAL (C2). A LIMIT TO REMOVE.**
`PrecipitationArrays` drives dissolution on `k_diss * V * (Qroot - Ksproot)`,
which has **no acid term and no surface-area term**. Measured on the wet process:
33x the sulfuric acid moves conversion **8.032% -> 8.363%** while the pH goes
1.487 -> -0.001, and **10x the ROCK dissolves the same 8.0e-4 mol**. Conversion is
exactly linear in the vessel knob and in nothing else, and at the default k_diss
the cap is 2.9e-9 mol/s — **40 days for 0.01 mol.** A real digestion is a SURFACE
reaction going with [H+]; `SurfaceArrays` (S1) is that shape for a GAS at a
crystal and there is no liquid equivalent. ⚠ So a rock digests on a knob rather
than on its chemistry, and `PLAYABLE.md` §5's *a yield is not a corpus property*
is what every conversion involving a lattice has to be read under.

**38. ⚠⚠⚠ THE DEFAULT TOLERANCE IS WRONG ON THE WET-PROCESS FLASK, BY 56x (C2).**
600 s, k_diss = 1: **46.059% loose against 0.823% tight**, and the tight run is
**15x FASTER** (2.4 s against 36.3 s). At k_diss = 10 the two agree to six
figures. ⚠⚠ **Nothing in the answer says which case you are in**, and C2's first
sweep was run loose and was entirely wrong — non-monotonic in both k_diss and
time. *A non-monotonic sweep is not a finding about chemistry; it is a solver
saying it has not converged.* Every number in `tests/test_phosphate.py` and
`validation/phosphate_rock.py` is at rtol 1e-8 for this reason. ⚠ This is
fragility 17 arriving on new content the first time it was charged into a flask.

**39. ⚠⚠ `ion_data` AND `electrolyte._PAIRS` HAVE DIFFERENT MEMBERSHIP, AND
NOTHING BUT C2's AUDIT COMPARES IT (C2).** They are known to use different ZEROS
and that is documented at length; **which ions they HAVE is not.** Five lattices
have a real Ksp and cannot be put in a flask — `sphalerite`, `galena`,
`covellite`, `chalcocite`, `cinnabar` — **all five on `[S-2]`**, because `_PAIRS`
carries `H2S -> [SH-]` and stops. ⚠ The next step is a **REFUSAL**: `HS- -> S2-`
is quoted between ~12.9 and 19. `validation/phosphate_rock.py` panel 3 re-measures
it; the landmine with its trigger is in `data/catalog/README.md`.

**40. ⚠⚠ A SATURATION CAP BOUNDED A CONCENTRATION AND NOT THE FLOW (C2, FIXED).**
`LN_SATURATION_CAP` said it existed to stop a Jacobian perturbation producing an
`inf` and did not, because the next line multiplies by an unbounded `V_L1`. ⚠ The
fix carries the multiply's headroom and is **bit-identical while
`k_diss * V_L1 <= 1`**. ⚠⚠ **The general form is the live one: `exp()` being
finite is not the same claim as the term that consumes it being finite**, and
engine queue item 6 is the other known instance. ⚠⚠⚠ **AND THE FIX ITSELF SHIPPED
A BUG FOR AN HOUR**: written `max(log(scale), 0)` it raised on `k_diss = 0.0`,
three examples broke, and the test suite stayed green. Only `tolerance_audit.py`
saw it.

**41. ⚠ `superphosphate` IS SCORED AND NOT DEMONSTRATED (C2).** Its catalog row is
a "den, ambient" paste with **no water**; this engine's only ionic chemistry is
aqueous, so a solventless acidulation is not expressible. It counts as playable
through the same two data rows as `phosphoric-wet`.

⚠ **AND THE BLOCK-ORDER TRAP STILL HOLDS:** the state vector is
`pack(n_liquid, n_liquid2, n_gas, n_solid, T)` — **liquid2 is SECOND, not last.**

---

TRAPS SPECIFIC TO THIS ARC:

⚠⚠⚠ **REGENERATING AN ARTEFACT IS NOT THE SAME ACT AS RUNNING ITS TESTS,
AND C2 GOT THIS WRONG (C2).** C2 re-ran `tools/build_playable.py`,
`catalog_coverage.py`, `corpus_balance.py`, `granularity.py` and
`build_route_index.py` and read every headline they printed — and did not run
`tests/test_playable.py`, which PINS those headlines. The full suite came back
**7 failed**: six in `test_playable` (14 → 16 playable, 24 → 22 fed,
the whole 2x3 scoring grid, the species-only bucket) and one in
`test_protonation` (the ion table 28 → 29). **Every one was the instrument
working exactly as G3 built it** — *assert a generated artefact or it will
rot* — and every one was a number C2 had already measured and written into
the docs by hand. ⚠ **The generated report and the test that pins it are two
different consumers of the same number. Run both.** C1's own handoff listed
`test_playable` among what it ran; C2 read that list and still skipped it.

⚠⚠ **A TEST THAT PREDICTS A GAIN HAS TO BE REWRITTEN BY THE SESSION THAT
DELIVERS IT (C2).** `test_four_of_the_work_order_need_no_template_at_all` ended
with *"grant `phosphoric-wet` and `superphosphate` and playability goes up 2"*.
C2 delivered exactly that, so the line now measures **zero** — granting two
routes that are already playable adds nothing. Rewritten to assert where the +2
actually landed, rather than left as a claim that had quietly stopped meaning
anything.

⚠⚠⚠ **`max(log(x), 0)` IS NOT `log(max(x, 1))` WHERE THE LOG IS UNDEFINED, AND
A VESSEL MAY DECLARE `k_diss = 0.0` (C2).** C2's own overflow fix crashed three
examples with `ValueError: math domain error` and **the whole test suite stayed
green** — nothing in `tests/` charges a zero-`k_diss` vessel through the
precipitation branch. `validation/tolerance_audit.py` caught it against its own
baseline. **Write the guard inside the function, not around it**, and remember
that `k_diss = 0` is a deliberate configuration ("no dissolution in this flask"),
not an edge case.

⚠⚠⚠ **A ROUTE'S BLOCKER CAN BE IN A DIFFERENT TABLE FROM THE ONE THE WORK ORDER
NAMES (C2), AND THAT IS NOW TWO SESSIONS RUNNING.** C1: blocked on a price for a
species **not in its chemistry**. C2: blocked on a price **in the wrong table** —
the row said `calcium-phosphate` (a mineral) and the block was phosphoric acid's
**third pKa** in `properties/electrolyte.py`. Both had been recorded as a
mineral-curation job for three milestones. **PRINT THE REFUSAL AND READ WHAT IT
SAYS before costing it.** `PLAYABLE.md` §8's `refused species` column comes from
`catalog_coverage`'s tier, which knows a species is unpriced and does not know
which table the price would go in.
⚠⚠⚠ **MEASURE TWO DATA ROWS AS A GRID, EXACTLY AS G3 MEASURED TWO SCORING RULES
(C2).** C2 shipped two one-line rows and they bought **disjoint** things: the pKa
moved every compound that moved and none of the chemistry; the mineral moved none
of the score and is the only reason the rock dissolves. Granting them one at a
time is what showed it, and *"we changed two things and the number went up"* would
have credited the wrong one. **A score and a run are different questions and can
have different answers in different files.**
⚠⚠⚠ **A NON-MONOTONIC SWEEP IS NOT A FINDING (C2).** C2's first k_diss sweep ran
at the default tolerance and reported 46% at 600 s against 4.9% at 3600 s, and 8%
at k_diss 10 against 46% at k_diss 1. That is not chemistry, it is a solver that
has not converged — and the converged answers are 56x away. **When a sweep is not
monotonic in a knob it should be monotonic in, tighten the tolerance before
writing anything down.** ⚠ The tight run was also 15x FASTER, which is the tell.
⚠⚠⚠ **C2 BLAMED A CONCURRENT JOB FOR A SLOWDOWN AND THEN REFUTED ITSELF BY
RUNNING THE SUITE AGAIN (C2).** The first run had a `k_diss` sweep alongside it
and came back **+25% over G6**, every big row 14–23% up; that went into these
notes as *"never run anything during the suite, measured at +25%"*. The clean
re-run, with nothing else on the box, came back **29:55 — SLOWER than the
contaminated 28:47** — and agrees with it row for row:

                        G6      C2 contaminated   C2 alone   the two C2 runs
    total            23:03          28:47          29:55        +3.9%
    the ONE RIG test 176.9 s        201.40         199.26       -1.1%
    catalysis         75.1 s         89.17          91.50       +2.6%
    burner @1e-8      52.8 s         64.90          64.81       -0.1%

**One concurrent single-threaded job cost nothing measurable on a 16-core box** —
the two runs agree inside the recorded noise floor on every row. ⚠⚠ *A plausible
cause measured ONCE is a guess; the second run is what made it a finding, and it
made it the opposite finding.* Running the suite alone is still the tidy habit —
it is just not worth the sentence C2 first wrote about it.
⚠⚠ **WHAT IS REAL IS A +30% THAT NOTHING EXPLAINS, AND IT IS THE S12->S13 SHAPE
AGAIN.** G6's 1045 tests ran in 1383 s; 1097 now take 1795 s. New test files
since G6 account for roughly **179 s** (`test_phosphate` ~104, `test_playable`
~57, `test_vitriol` ~18), leaving about **230 s spread across tests that did not
change** — far outside the ~8%/~1% floor. ⚠ The project already records one of
these (S12->S13, *"20x outside the floor and remains a real unexplained
regression"*); this is a second, and **nothing has bisected either.** A `git
stash`-and-rerun of `--durations=25` across the suspect commits is still the
cheap next step and is worth more now that there are two data points.
⚠⚠ **A DATA JOB IS ONLY CHEAP WHEN THE DATA IS THERE (C2).** PLAYABLE §8's
"needs no template at all" bucket read as four lookups; C2 probed all four in one
run and **three have no Hfs and no S0s in any shared database**. Probing the
neighbours of the row you are taking costs one query each and re-prices the rest
of the table.
⚠ **A `print()` IN A validation/ SCRIPT MAY NOT CONTAIN A WARNING GLYPH, AND C2
BROKE ITS OWN DOCSTRING'S RULE WRITING ONE (C2).** The file said *"every printed
line here is ASCII"* four lines above seven `print("⚠⚠ ...")` calls, and the bare
`python validation/phosphate_rock.py` that the audit list actually runs died on
cp1252. ⚠ **The probe written to FIND them died the same way.** Set
`PYTHONIOENCODING=utf-8` for probes, and check the printed lines mechanically —
`⚠` in a docstring is fine, in a `print` it is a crash.
⚠ **`vessel_integrator.py` IS LF WHERE `mineral_data.py` AND THE MARKDOWN ARE
CRLF (C2).** The line endings are MIXED per file in this repo. A replace script
that assumes either one silently matches nothing; check the file first.

⚠⚠⚠ **A RECORDED LANDMINE WITH A NAMED TRIGGER IS THE CHEAPEST DOCUMENTATION
THIS PROJECT WRITES, AND C1 IS THE PROOF (C1).** S3 wrote, three milestones
early, *"the day `hydrolysis` is credited, `vitriol-distillation` goes
template-ready on a step whose stated product does not exist in the run — whoever
builds it owes this row a second look."* The session that credited `hydrolysis`
read it, took the second look, and found that the refused species had never been
in the reaction at all. **Write the trigger, not just the fact.**
⚠⚠⚠ **A REFUSED SPECIES IN A ROUTE'S BLOCKER LIST MAY BE A CORPUS ERROR RATHER
THAN A CURATION JOB (C1).** `iron-ii-oxide` blocked `vitriol-distillation` for
three milestones and the engine has never made it there. **Check whether the
species is in the chemistry before pricing its refusal as work** — it moved
species-ready 82 → 83 for the cost of one line.
⚠⚠⚠ **A WORK ORDER DERIVED FROM A FIXED POINT IS NOT A BURNDOWN LIST (C1).**
Granting one of G3's 21 rows made the list **24** and the ceiling **37 → 41**,
because the shelf grew and four routes that were not fed became fed. Re-run
`tools/build_playable.py` after every content item and read §8 again; the WORTHS
overlap and they re-price each other (`iron-gall-ink` +2 → +1, `nitrogen-dioxide`
+2 → +1, both because C1 delivered their second point first).
⚠⚠⚠ **A RULE JUSTIFIED BY A MEASURED DIFFERENCE MUST NOT BE REVERTED THE DAY THE
DIFFERENCE GOES AWAY (C1).** C1 dissolved the only evidence for one of G3's four
scoring rules. The rule is a statement about `route_roles` and is still true; its
COST is a property of today's corpus. **What changed is the number, and the number
is now asserted as zero with the reason above it.** Reverting it is how a
corrected instrument un-corrects itself.
⚠⚠ **BETWEEN TWO WRONG-IN-DIFFERENT-WAYS DECLARATIONS, KEEP THE ONE WHOSE ERROR
IS MEASURED TO BE INVISIBLE (C1).** `orders=(1.0, 2.0)` is the more correct rate
law for SO3 + H2O and it was refused, because a declared order may not be
reversible. The order is forgiven over five decades of `A`; the reverse is the
664 K ceiling and the whole mechanic. **Measure both errors before choosing.**
⚠⚠ **A SPLIT THAT LOWERS THE HEADLINE IS A SPLIT WORKING, AND THE ARGUMENT CAN BE
THE TAXONOMY'S OWN (C1).** `hydrolysis` was not split because eight rows are eight
mechanisms — that is a judgement — but because the same file already carried
`amide-`, `ester-`, `epoxide-`, `glycoside-`, `nitrile-`, `isocyanate-` and
`disproportionation-hydrolysis`. **When a taxonomy has named every case but one,
the one is the bin.**
⚠⚠ **A CLASS ASSIGNMENT CAN BE A FALSE CREDIT, AND THE CHEAP TIME TO REFUSE IT IS
BEFORE IT PAYS (C1).** `furfural-route` 1 is chemically a glycoside hydrolysis and
belongs to the COVERED class by convention; it is filed separately because the row
can never match a template. **Measured: zero either way today.** That is exactly
G3's masked-cell shape pointing forward, and the test asserts BOTH cells.
⚠⚠ **A GENERATED ARTEFACT MAY NOT SPELL A COUNT IN WORDS (C1).**
`build_playable.py` said *"four more routes fall out for free"* beside a derived
list; one content item later the list had three in it. `len(free)` now.
⚠ **THE cp1252 TRAP BITES `python -` HEREDOCS TOO (C1).** A throwaway probe that
prints a line out of `NEXT_PROMPT.md` dies with `UnicodeEncodeError` unless
`PYTHONIOENCODING=utf-8` is set. Cheaper to set it than to rediscover it.
⚠ **AND `sed -i` STILL DESTROYS A CRLF FILE HERE.** Every edit in C1 went through
a short Python script that reads with `newline=""` and writes the same way.

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
⚠⚠⚠ **MEASURE TWO SUSPECTED RULES AS A GRID, NOT AS A LIST (G3).** Two of G3's
four scoring rules were wrong at once, and **fixing the first one MASKED the
second**: under the corrected needs rule the shelf rule's bug costs nothing (12
either way) and is only visible under the wrong needs rule (13 against 14). In the
other order the shelf rule would have looked like a distinction without a
difference, gone in wrong, and started costing routes silently later. **A 2x3
table found in one run what a sequence of single fixes would have hidden.**
⚠⚠⚠ **A REACHABILITY CLAIM HAS TO BE ITERATED TO A FIXED POINT OR IT IS NOT ONE
(G3).** The recorded 7/6/14/4 classification was a LOOSE one-step count that
credits a hop onto any route's *target* whether or not that route runs. **Eight of
its thirteen hops landed on routes that cannot run**, and a one-step count cannot
see that because it never asks the question twice.
⚠⚠ **A CATALYST IS A TECH-TREE NODE (G3).** Treating one as free was measured at
two routes and one whole tier: the corpus's entire third tier is a copper catalyst
that has to be smelted from the byproduct of smelting a different metal.
⚠⚠ **A ROUTE'S TARGET IS NOT ALWAYS AMONG ITS PRODUCTS, AND A CLOSED CYCLE NEEDS
NOTHING (G3).** `route_roles` answers the question ROUTE_INDEX asks and the wrong
one here: `lead-chamber`'s fouling row makes its own acid an *intermediate*, and
`lime-cycle` derives an **empty** feedstock list because row 3 regenerates what
row 1 calcined. **Whether a species is a need is a question about ORDER.**
⚠⚠ **HOIST A DUPLICATED SCORER INTO ONE PLACE THE FIRST TIME A SECOND AUDIT WANTS
IT (G3).** G4's DAG walk is `catalog.route_reachable` now and both audits call it;
two copies of a scorer drift silently, and G4's own 9 tests are what proved the
extraction was faithful.
⚠⚠ **ASSERT A GENERATED ARTEFACT OR IT WILL ROT (S3, acted on in G3).**
`ROUTE_INDEX.md` was stale by three milestones because no audit read it. ⚠ And the
assertion paid for itself in one run: `test_the_report_on_disk_matches_the_code`
caught a generator that **shadowed its own output buffer** and wrote a 200-byte
file of route names instead of a 326-line report. ⚠ Pin the numbers a reader would
quote rather than diffing the file — a report that cannot be diffed is one nobody
diffs.
⚠ **A HISTOGRAM OF BLOCKERS IS NOT A WORK ORDER (G3).** `sulfuric-acid` blocks
the most routes (4) and is worth the least of the top (+1), because every route it
blocks is blocked by something else too. **The fixed point is the work order, and
the two disagree.**
