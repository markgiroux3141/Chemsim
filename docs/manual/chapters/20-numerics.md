# Layer 4: the numeric core

## The isothermal case, which is the whole idea in six lines

```
rate_j(T, C) = k_j(T) * prod_i C_i ** order_ji
k_j(T)       = A_j * T**n_j * exp(-Ea_j / (R T))
dC/dt        = delta^T @ rate   (+ an optional source term)
```

That is `chemsim/numerics/integrator.py`. No `Molecule`, no RDKit, no unit
objects --- `KineticArrays` in, trajectory out. It is deliberately ignorant of
chemistry, and that ignorance is exactly what makes it the clean swap point for
a Rust/PyO3 kernel.

The optional `source(t, C) -> dC` hook is where higher layers inject
non-reactive flux --- a vessel's oxygen ingress, inter-phase transport, dosing
from a dropping funnel --- without the core needing to know what any of it means.

## Solving it

The system is a set of coupled non-linear first-order ODEs. SciPy's `solve_ivp`
integrates it, and the method is **BDF** --- backward differentiation formulae,
an implicit multistep method --- for reasons that are Chapter 25's subject. The
short version: chemical systems are *stiff*, meaning they contain timescales
many orders of magnitude apart, and an explicit method's step size is bounded by
the fastest one even after it has died away.

An implicit method needs the **Jacobian** $\partial f_i/\partial y_j$ at each
step, and for a mass-action system that is analytically available:

$$ \frac{\partial}{\partial C_k}\left(\Delta^{\mathsf T}\mathbf r\right)_i
   = \sum_j \Delta_{ji}\, \frac{\alpha_{jk}}{C_k}\, r_j. $$

In practice the project lets SciPy difference it numerically for the full vessel
RHS, because the vessel's right-hand side (Chapter 21) contains phase-transfer
terms, gates and an energy balance whose analytic derivatives would be a large
and fragile piece of code. That decision has a cost, and Chapter 26 is entirely
about it.

## Sparsity: a measurement that came out backwards

A large reaction network's Jacobian is sparse --- most species do not appear in
most reactions --- and SciPy accepts a `jac_sparsity` argument to exploit that.

::: {.trap title="Passing jac_sparsity to a rig was costing 10x"}
It was measured, and it was ten times *slower*. Two reasons:

- sparsity buys only **column groups**: SciPy differences several columns
  simultaneously when their non-zero patterns do not overlap. If the pattern
  does not partition well, you save nothing and pay the bookkeeping.
- **the temperature row was blocking all of them.** $T$ appears in every rate
  constant, so the temperature column is dense --- and one dense column prevents
  the grouping from finding any usable partition at all.

The general lesson is that a sparsity optimisation is a *measurement*, not a
deduction, and a single dense row or column can destroy it.
:::

## Tolerances, and an audit whose instrument was wrong first

`rtol` and `atol` control the solver's local error. The project ran a full
tolerance audit (milestone S2) across every example, sweeping from the default
down to $10^{-8}$, and it produced four findings, three of which are about
methodology.

::: {.trap title="1. The instrument invented a finding before it was fixed"}
The audit's first version reported a real-looking movement that was an artefact
of how it re-ran examples. The instrument had to be audited before its findings
could be.
:::

::: {.trap title="2. \"Tight is faster\" does not generalise"}
There is a genuine effect where a tighter tolerance can be *faster*, because the
solver stops rejecting steps. It was observed once and then over-generalised
into a rule. Swept properly, it does not hold across examples.
:::

::: {.trap title="3. A one-point tolerance sweep cannot tell newly-broken from already-broken"}
If you only compare "default" against "tight", a number that moves might be a
regression you just introduced or a pre-existing convergence problem. You need
at least three points to see which.
:::

The one *real* finding was a number that moved, and it was in the panel that
exists to show exactly that.

## Where the layer's boundary actually is

Layer 4 contains four things and nothing else:

| module | what it is |
|---|---|
| `integrator.py` | the isothermal mass-action kernel |
| `vessel_integrator.py` | the full 4$n$+1 flask RHS (Chapter 21) |
| `rig_integrator.py` | several coupled vessels as one system (Chapter 22) |
| `activity.py` | UNIFAC and Born evaluation, per RHS call |
| `lle.py` | the phase-split *decision*, called only between integrations |
| `jacobian.py` | one bound SciPy lacks (Chapter 26) |

Every one of them takes numpy arrays and floats. None of them can name a
chemical species except by integer index.

::: {.keypoint}
The clearest test of whether a layering claim is real: `numerics` could be
handed to somebody who has never heard of chemistry, with the array shapes and
the rate law, and they could reimplement it. That is what "the Rust seam" means
in practice, and it is why the project can defer the Rust question indefinitely
without the design rotting.
:::
