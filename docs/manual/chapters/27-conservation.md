# Conservation: what holds exactly, and the one thing that does not

## Matter is exact everywhere

Chapter 2 set this up: because $\Delta E = 0$ holds in *integers*, the quantity
$\mathbf n^{\mathsf T}E$ --- moles of each element, plus total charge --- is
conserved by the reaction terms to machine precision, not to solver tolerance.

Transport terms move moles between blocks of the state vector without changing
species identity, so they conserve the same quantity trivially. Therefore:

::: {.keypoint}
A sealed vessel conserves every element **across all four phase blocks**, and a
rig conserves them across every vessel in it. `conservation_report()` measures
this on demand, and the test suite asserts it.
:::

The guardrail that makes this true is upstream, at network build: a template that
does not balance is rejected rather than integrated. Everything after that is
bookkeeping.

## Energy is not

::: {.trap title="An insulated flask destroyed 495 J after a precipitation event, and conservation_report could not see it"}
This is milestone M12 and it is the most important known limitation in the
numerics.

`conservation_report` checks **matter**. There is no equivalent invariant on
energy, because energy is not a linear function of the state the way element
counts are --- it involves $C_p(T)$ integrals, latent heats, heats of reaction
and boundary fluxes, and the RHS assembles $\dd T/\dd t$ from those rather than
tracking a conserved total.

So a leak is invisible to the instrument that exists to catch leaks.
:::

The M12 investigation is worth following because of how the wrong answers were
eliminated.

**Four candidate causes were measured and refuted:** the precipitation term's
enthalpy accounting, the dryout gates, the vent, and the activity model's
temperature dependence. Each was instrumented and each was clean.

**The actual cause was a derived rate constant $9.4\times10^7$ times the
collision limit.** Not one somebody typed --- one that came out of detailed
balance from a forward rate that was itself only order-of-magnitude. At that
speed the transient is faster than anything the solver can resolve, and the
energy balance loses the heat of a reaction it never took a step inside.

**The fix must scale both pre-exponentials.** Capping only the offending
direction would change $k_f/k_r$, i.e. change $K$ --- a thermodynamic falsehood
introduced to fix a numerical problem. So the cap scales the pair.

::: {.keypoint}
The general form: **an unphysical rate constant is a numerical bug wearing a
chemistry costume**, and it will show up somewhere other than where it is. Here
it showed up as an energy leak, several layers away from the reaction that
caused it.
:::

`validation/rate_ceiling.py` now audits every network in the project, including
the reverse that each reversible template implies.

## Two things about reading the energy report

::: {.trap title="Report the GROSS heat beside the net"}
`q_rxn` for a fast reversible pair is a *difference of two large terms*. The
project measured one case reading $-4.69\times10^{6}$ W frozen at one state and
$-5\times10^{-3}$ W frozen at another --- nine orders apart, for the same
physical situation, because the two directions nearly cancel and the residue
depends on exactly where you froze it.

Reporting only the net makes a catastrophically ill-conditioned number look like
a small one. The gross terms go beside it.
:::

::: {.trap title="energy_terms lies unless it is given the run's own boundary state"}
The energy report needs to know what the boundary was doing --- ambient
temperature, heat input, vent state --- and it will happily compute a
plausible-looking balance against *default* boundary conditions that the run
never had. The interface now requires the run's own state to be passed in.
:::

## A leak whose driver was a blended composition

One more, because the mechanism is subtle and generalisable.

::: {.trap title="The vent leak, and a donor composition that was an average"}
A refluxing rig destroyed 0.34 mol of its air over a long run. The vent term
carries the *donor's* headspace composition, $\dot n_i = k(P_a - P_b)x_{g,i}$ ---
and where the flow could reverse within a step, the composition being carried was
a **blend** of the two ends rather than whichever end was actually donating.

A blended composition is not a small error in the flux; it is matter of the
wrong *identity* crossing the boundary. The fix is that the flux carries a
one-sided composition chosen by the sign of the driving force, which is the same
algebraic shape as the fix in Chapter 21 that made the reversible solid--gas term
work: **write a two-sided expression as two one-sided products, so that nothing
is ever divided by --- or averaged across --- a quantity that can change sign.**
:::

## What this means for reading a result

::: {.keypoint}
- **Element counts and charge**: trust them completely. They are exact and they
  are checked.
- **Volumes and mole fractions**: trust them to solver tolerance.
- **Temperature trajectories**: trust the *shape* --- plateaux, runaways,
  crossovers --- and treat the absolute energy budget as approximate unless
  `energy_report` has been read with the run's own boundary state.
- **Any number from a run in which the rate-ceiling audit reports a capped
  reaction**: read the report first.
:::

And the standing rule the project applies to all of this, from the dryout-band
finding in Chapter 21:

> A green test suite is no evidence that the invariants table holds.

The suite passed throughout the 111%-yield bug, throughout the 495 J leak, and
throughout the months of vented air. Each was found by an audit written to ask
one specific question, and each audit is now a file in `validation/`.
