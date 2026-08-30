# The Jacobian bound, which is one inequality and a long argument

This chapter is about a single line of code. It is here because the reasoning
that produced it is the best worked example in the project of *how a numerical
bug is actually found*, and because the shape of the answer --- a bound derived
from the state itself rather than a constant somebody chose --- is transferable.

## The failure

BDF is handed a NaN Jacobian. The LU factorisation fails with "array must not
contain infs or NaNs", several tens of seconds after anything actually went
wrong.

## The mechanism

SciPy's `num_jac` differences column $j$ at a step
$h = \texttt{factor}_j \cdot \max(\mathrm{atol}, |y_j|)$. When the difference it
gets back is small compared with the rates elsewhere in the system, it concludes
it probed too gently and **multiplies that column's `factor` by ten** --- on
every Jacobian, for ever.

SciPy *floors* `factor` at a minimum and **never ceilings it**. So a column it
cannot difference is probed harder without bound until `factor` overflows to
`inf`, $h$ becomes `nan`, and the Jacobian is poisoned.

## Why the column could not be differenced

This is the part worth reading.

The column that overflows is the **second liquid layer's SO₂**, holding
$8.21\times10^{-29}$ mol. Its $f$ is the layer-reabsorption drain, which is
strictly *negative* for any positive holding --- so `num_jac` takes the sign as
$-1$ and steps **downward**, straight into the RHS's own `np.maximum(y, 0.0)`
clamp.

Every downward step, at every size, lands on the same clamped state:

![Constant over thirty decades. No step size can measure this.\label{fig:jac}](figures/jacobian.pdf)

| $h$ | $-2.2\times10^{-24}$ | $-2.2\times10^{-19}$ | $-2.2\times10^{-14}$ | $-2.2\times10^{-9}$ | $-2.2\times10^{-4}$ | $-2.2\times10^{6}$ |
|---|---|---|---|---|---|---|
| $\max|\text{diff}|$ | 8.84e-29 | 8.84e-29 | 8.84e-29 | 8.84e-29 | 8.84e-29 | 8.84e-29 |

Constant over **thirty decades of step size**, against a scale of
$8.37\times10^{-14}$ taken from another species' row. So "the difference is too
small" is true no matter what, the factor climbs a decade per Jacobian ---
twenty-eight of those calls at one unchanged state --- and about two hundred
later it reads $2.220\times10^{307}$.

::: {.keypoint}
**No step size can measure a derivative the model has deliberately projected
away.**

Probing harder is not always a question that can be answered, and a loop that
assumes it is will run until it overflows.
:::

## Four wrong answers on the way to the right one

This bug had been met **three times** before and named three different ways --- a
vessel at rest, an empty second liquid layer, a sealed flask with no headspace
--- and worked around three times, each time *in the chemistry*.

::: {.trap title="1. The fix was scheduled for the wrong block"}
It was planned as an "honest diagonal" on the **gas** block, on the reasoning
that an absent gas species has a flat column. That is true --- the gas block *is*
a route in. But of the five recorded triggers, **the only one that still
reproduces overflows in liquid layer 2**, and a diagonal on the gas block could
not have reached it.
:::

::: {.trap title="2. The named precedent was the cause"}
The fix was to copy the layer-reabsorption drain's approach. That drain is
**what makes $f$ negative** and so points the probe at the clamp in the first
place. The precedent to copy was the thing to remove.
:::

::: {.trap title="3. The first bound was wrong, and the examples said so"}
The obvious cap is $\texttt{factor} \le 1$, on the reading that `factor` is the
step as a fraction of the variable's own scale, so 1 moves the variable by all of
itself.

**That reading is false exactly where it matters.** The scale is
$\max(\mathrm{atol}, |y_j|)$, so for a species at or below atol the fraction is
of **atol**, not of the variable. `factor = 149` on an absent species is a
$1.5\times10^{-7}$ mol probe of a 0.1 mol flask, which is a perfectly good probe.

Measured on a real example:

| ceiling | SO₂ in the flask | what the solver wanted |
|---|---:|---:|
| `inf` | 0.000201 mol | $1.490\times10^{2}$ |
| $10^{6}$ | 0.000201 mol | $1.490\times10^{2}$ |
| $10^{2}$ | 0.000201 mol | $1.490\times10^{2}$ |
| **1.0** | **0.000197 mol** | clamped --- **and the answer moved** |

A ceiling of 1.0 moved a quotable digit in a *healthy* run, and eight of the
sixteen examples moved under it.
:::

::: {.trap title="4. Four of the five recorded triggers do not reproduce"}
They had been fixed in the chemistry, or the conditions had changed. Re-measuring
the list before acting on it is what located the one that was live.
:::

## The bound that survived

So the bound cannot be on `factor`. It has to be on the **step**, and the honest
statement is:

::: {.keypoint}
A difference quotient is a derivative of *this* system only while the probe stays
inside it. You cannot learn anything about a state by moving one of its
components further than the whole state extends.

$$ |h_j| \le \max_i |y_i|
\qquad\Longleftrightarrow\qquad
\texttt{factor}_j \le \frac{\max_i |y_i|}{\max(\mathrm{atol}, |y_j|)} $$

A bound per column and per call, computed from the state, **with no constant in
it at all.**
:::

On a single vessel it never binds: the largest factor any single-vessel example
asks for is $1.49\times10^{9}$, against a bound of order $10^{11}$--$10^{12}$ for
a state carrying a temperature at $\mathrm{atol} = 10^{-9}$. Where it binds *by
design* is the runaway itself --- the sulfur burner's frozen column reaches the
bound at $6.9\times10^{13}$ (690 K over $\mathrm{atol} = 10^{-11}$) and stops
there instead of at `inf`.

## Where the fix belongs

Not in the chemistry. `chemsim/numerics/jacobian.py` sees a callable and two
float arrays, like everything else in Layer 4, and the whole module is that
inequality plus the argument for it.

::: {.keypoint title="The general shape"}
Three times, a numerical failure was worked around by changing a physical model
--- adding a drain, adding a short-circuit, avoiding a flask configuration. Each
workaround was locally reasonable and each one made the *next* occurrence harder
to find, because it moved the symptom rather than the cause.

The bound belongs in the layer that owns the differencing. Ask, when a physical
model grows a term whose only job is to keep a solver happy, whether the fix is
in the wrong layer.
:::

## What it does not fix, stated

The bound stops the overflow. It does not make the column's derivative
*correct* --- it is still zero, because the model really has projected that
direction away. What it buys is that BDF gets a finite, honest zero instead of a
NaN, and the run continues with the same answer it would have had.

The species in question is at $10^{-29}$ mol. If it ever mattered, the model
would be wrong for a different reason.
