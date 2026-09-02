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
