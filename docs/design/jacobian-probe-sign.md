# A Jacobian probe from a negative amount stays below zero

Decided 2026-09-25. Code: `sign_bound` in `src/chemsim/numerics/jacobian.py`.
Test: `tests/test_jacobian.py`, the smelter and the toy clamped column.

## What happened

CI's suite job ran past its 150-minute limit three times while the suite ran
green locally in under ten minutes. Three xdist workers died at the 900 s
per-test timeout in the setup of `test_playable`, `test_vanillin` and
`test_fermentation`, which is `import build_playable`. On the runner that
import took 29 s on one commit and 584 s and 701 s on the next two, with no
code change between them: 15,021 RHS calls against 1.3 million.

Timing each `Vessel.run` in the import put the cost in one run: the copper
smelter on two retorts' worth of carbon monoxide (10 L, 1500 K, 40,000 s,
rtol 1e-8). Locally it took 27 s inside the import and 56 s standalone, with
1,540 and 2,889 Jacobians, against 0.8 s for the same smelter on one retort's
worth. 5,891 of its 6,348 steps fell between t = 1,000 and 10,000 s.

## The mechanism

The furnace has no liquid, but the state vector carries a liquid block for
every species. BDF let that block drift negative, to -3.4e-4 mol of CO and CO2
by the end of the run. Every RHS in this package reads an amount through
`np.maximum(y, 0)`, so at a negative amount the true Jacobian column is zero.

`num_jac` sees a column that differences to zero, decides it probed too
gently, and multiplies that column's factor by ten on every Jacobian. It steps
in the direction of `f_j`, which here is upward. Once the probe is longer than
`|y_j|` it lands on the positive side, in a liquid layer that at 1500 K
evaporates at a rate of order 1e7 per second, and BDF is handed that as the
diagonal. The real derivative is zero. Simplified Newton with that Jacobian
converges only when `h * 1e7` is of order one, so the step collapses to 1e-7 s.
When the probe first crosses depends on the whole history of factor
inflation, which depends on round-off. That is why two runners and two local
paths gave four different costs for the same code.

The wrong Jacobian also moved answers. The drift conserves each species'
total, but it moves matter from the liquid into the gas, where the chemistry
runs.

## The rule

For a column with `y_j < -atol` and `f_j >= 0`, the factor is capped at
`SIGN_FRACTION = 0.05` before `num_jac` runs, so the probe reaches 5% of
`|y_j|`. `num_jac` retries a flat column at ten times its factor within one
call, so the retry reaches half of `|y_j|` and neither probe crosses zero. The
column differences to exactly zero, its true derivative, and `factor_bound`
keeps the factor finite as before.

Within atol of zero the old probe is kept. The first version applied the rule
at every negative amount, and the mercury retort's HgO then overshot to
-2.7e-10 mol and stayed there, where before the crossing probe had pulled it
back to -3e-13. The projection turned that into 2.7e-10 mol of created
mercury (`tests/test_mercury_retort.py`), and the sealed kiln settled 0.27%
off `K` (`tests/test_solid_state.py`). An amount within atol is round-off
that the solver does not resolve, and the crossing probe is what pulls it
back. An amount beyond atol is a resolved negative excursion, and there the
probe has to measure the flat side.

## Measured, 2026-09-25

| run | Jacobians | wall | raw liquid minimum |
|---|---:|---:|---:|
| smelter, 2x CO, before | 1,540-2,889 | 27-56 s, >500 s under pytest | -3.4e-4 mol |
| smelter, 2x CO, after | 33 | 1.1 s | -9.9e-7 mol |
| `import build_playable`, before | | 46-62 s | |
| `import build_playable`, after | | 19 s | |

`PLAYABLE.md` is byte-identical. Of the 18 examples, 8 print the same and 10
print different digits, most in the fourth to seventh figure. Where a converged
reference settles which answer is right, the new one is nearer or the same:

- `roasting_and_the_catalyst_gate`: SO2 left in the blown flask is 0.00020303
  mol at every rtol from 1e-8 to 1e-11 under both codes run standalone. The
  example now prints 0.000203, where before it printed 0.000201.
- `oil_of_vitriol`: oxygen created by the projection in the 730 K burn at rtol
  1e-8 falls from 7.4e-7 to 1.9e-10 (574 Jacobians to 88). At the default
  tolerance the 900 K row rises from 4.0e-8 to 1.7e-6, inside the default
  rtol's own band. At rtol 1e-8 both codes give about 1e-10.
- `multistep_prep`, `fractional_distillation`, `plate_column`,
  `competing_pathways`: moves in the fourth to seventh figure, all at the
  default tolerance.

The tolerance audit judges every example against a tight run. CI's slow
workflow runs it on this push.

## Not fixed

The mercury retort's empty liquid block still drifts, to -1.5e-4 mol of SO2
under either code, while the RHS returns exactly zero for it. The drift enters
through other columns of the Jacobian, not through this column's own probe.
The projection settles it against the gas, so no matter is created, but the
gas carries that much extra SO2 while it lasts.
