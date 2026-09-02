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
