\part{Numerics}

# Stiffness, and why the solver is what it is

## What stiffness is

A system of ODEs is **stiff** when it contains processes on timescales many
orders of magnitude apart, and you care about the slow one.

![Two timescales in one flask.\label{fig:stiff}](figures/stiffness.pdf)

Chemistry is stiff essentially always, and the reason is Chapter 5's
exponential. Rate constants go as $e^{-E_a/RT}$; barriers in one flask range
from ~0 (a proton transfer, which is diffusion-limited) to 150 kJ/mol (a bond
being broken). At 300 K that is a spread of $e^{60} \approx 10^{26}$ in rate.

::: {.physics}
Formally, stiffness is about the eigenvalues of the Jacobian
$J = \partial f/\partial y$. The stiffness ratio is
$\max_i|\mathrm{Re}\,\lambda_i| / \min_i|\mathrm{Re}\,\lambda_i|$, and it is the
ratio of the fastest decaying mode to the slowest.

An **explicit** method's stable step is set by the fastest mode, $h \lesssim
2/|\lambda_{\max}|$, *whether or not that mode is still doing anything*. So an
acid--base equilibrium that reaches steady state in a microsecond forces
microsecond steps for the whole hour you want to simulate. That is $3.6\times10^9$
steps to watch an esterification.
:::

## The fix: implicit methods

An implicit method evaluates the right-hand side at the *end* of the step,
$\mathbf y_{k+1} = \mathbf y_k + h\,f(t_{k+1}, \mathbf y_{k+1})$, which requires
solving a non-linear system at every step but is stable for arbitrarily large
$h$ on decaying modes. Fast modes that have already relaxed to their
quasi-steady state stop costing anything.

The project uses SciPy's **BDF** --- backward differentiation formulae, variable
order 1--5, variable step. That is the standard choice for chemical kinetics and
the reason the numbers in Chapter 24's table are as small as they are.

## What that costs: the Jacobian

Solving the implicit step means Newton iteration, which needs
$J = \partial f/\partial y$ --- an $(4n{+}1)\times(4n{+}1)$ matrix for a single
vessel, and $m$ times that for a rig.

The project lets SciPy difference it numerically rather than supplying an
analytic one. That is a real trade: an analytic Jacobian for the pure
mass-action kernel is easy, but the *vessel's* RHS contains evaporation gates,
dryout gates, dissolution limiters, a liquid--liquid transfer, a vent with
backflow, an activity model and an energy balance --- and an analytic derivative
of all that would be a large, fragile piece of code that would have to be kept
in step with every term added.

Chapter 26 is about what that choice cost, and it is the most interesting
numerical story in the project.

## Where the time actually goes

Three observations from the project's measurements, all of them slightly
counterintuitive:

**1. An idle flask is free.** `VesselIntegrator.run` short-circuits when nothing
is happening, and never calls the solver at all. An hour costs 0.00 s.

**2. Cost tracks *events*, not duration.** A boiling plateau is cheap because
after the transient it is a smooth quasi-steady state. An acid quench is
expensive because it is a genuine fast transient with real structure in it.

**3. The RHS is dominated by fixed overhead at these sizes.** The activity kernel
is *flat* from 4 species to 25 (78 µs to 87 µs). Both numbers are numpy dispatch
on small arrays, not arithmetic --- which is why the case for a Rust kernel rests
on per-call overhead rather than on any model being slow (Chapter 15).

## Tolerances, and what a number means

`rtol` and `atol` bound the solver's *local* error per step. They do not bound
the global error and they certainly do not bound the model error --- which, given
Chapter 12, is several kJ/mol in $\Delta G_f$ and therefore a factor of 2--4 in
every equilibrium constant.

::: {.keypoint title="So: how many digits of a simulated number mean anything?"}
The honest answer here has three levels, and they are far apart:

- **solver resolution**: many digits. The tolerance audit swept every example at
  $\mathrm{rtol} = 10^{-8}$ and most numbers do not move.
- **rate parameters**: one digit, generously. Pre-exponentials are
  order-of-magnitude choices, so *times* are order-of-magnitude.
- **equilibrium positions**: a factor of 2--4, dominated by group-contribution
  formation data.

A branching *ratio* between two templates in the same family is better than any
of those, because the shared errors cancel. That is why the project's strongest
claims are comparative --- "ether above 480 K, ester below" --- rather than
absolute.
:::

::: {.trap title="A root is zero to solver precision, and that is not the same as zero"}
`wait_until` locates a root of a scalar function of state. What it returns is a
state where that function is zero **to solver precision** --- which for a
condition like "the crystals have appeared" means the amount is at the threshold,
not comfortably past it.

Anything that reads the state immediately after a wait has to tolerate that. It
is the same class of issue as the micromole threshold in Chapter 23: a numerical
tolerance masquerading as a physical statement, and the fix is always to make the
physical statement explicit.
:::

::: {.trap title="A documented trap that rested on a wrong boiling point"}
One of the project's recorded numerical traps turned out to be visible only
*because* a species had a wrong $T_b$. When milestone S13 fixed the boiling-point
table, the trap stopped reproducing.

The finding was real; the reason recorded beside it was not. That pattern ---
"half the reason written down beside a refusal was about something the code never
did" --- has now happened three times in this project, and it is the argument for
re-measuring a recorded refusal rather than trusting it.
:::
