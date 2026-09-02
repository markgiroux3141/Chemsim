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
