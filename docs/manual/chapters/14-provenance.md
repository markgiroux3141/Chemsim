# Provenance: how a number earns the right to be used

This chapter has no equations in it. It is about the discipline that surrounds
the numbers, and it is arguably the most transferable content in the project.

## The rule

::: {.keypoint}
**Every value carries its source.** Not a comment --- a field on the record, that
downstream code and the user interface can both read. `ThermoData.source`,
`Volatility.source`, and the tier column in the coverage report all exist so
that "this came from a measurement" and "this came from a group-contribution
estimate" are distinguishable at the point of use.
:::

The reason is that group contribution is at its most dangerous when it
*succeeds*. A refused species is a visible hole. An estimated species is an
invisible one, and it will be quoted with the same confidence as a measured one
by anything that does not ask.

## The provider stack

Properties resolve through a tier list, highest first, and every tier is named
on the result:

1. **curated measured data** --- `formation_data.py`, `physical_data.py`,
   `element_data.py`, `mineral_data.py`;
2. **Benson group additivity** --- better formation values, ~12% refusal rate;
3. **Joback** --- broad coverage, several kJ/mol;
4. **refused** --- with a reason.

Two of those tiers exist as *refusals with a route out* rather than as fallbacks:
an element comes from `element_data` or is refused by name (Chapter 3), and an
ionic lattice comes from `mineral_data` or is refused by name (Chapter 9).

## Derive, do not transcribe

$\Delta G_f$ in `formation_data.py` is **derived** from that entry's own
$\Delta H_f$ and $S^\circ$ against the CODATA element reference states, rather
than transcribed from a table. That is deliberate: the two halves of every entry
are then thermodynamically consistent with each other by construction, which is
what makes the entropy a caller derives from the pair the real one.

The same principle appears three more times:

- `ion_data.py` re-derives each ion's $\Delta G_f$ from its own row's
  $\Delta H_f$ and $S(\mathrm{aq})$, worst residual 0.85 kJ/mol against a
  tolerance of 1.0;
- `mineral_data.py` derives $\Delta G_f$ from $\Delta H_f$ and $S^\circ$ against
  the same element reference states;
- $\Delta H_{\mathrm{vap}}$ is derived from the Antoine curve by
  Clausius--Clapeyron rather than taken from a second correlation, so both
  halves of the standard-state shift come from one source.

::: {.keypoint title="Never mix sources inside one entry"}
Both halves of a record come from the **same** database or the entry is refused.
That rule bites on iron(II) sulfate, whose $S^\circ$ is 107.5 J/(mol K) from CRC
and 120.93 from the WebBook --- 13.4 apart, and worth 4 kJ/mol in $\Delta G_f$.
Taking the enthalpy from one and the entropy from the other produces a
consistent-looking record that describes no substance.
:::

## Cross-checks that touch nothing the entry came from

A curated value is only as good as the independent thing it agrees with. Each
tier here has a check built from correlations that never touched the formation
tables:

**For a species with both gas and liquid formation data**, two identities must
hold to within 3 kJ/mol:

$$ \Delta H_f(g) - \Delta H_f(\ell) = \Delta H_{\mathrm{vap}}(298),
\qquad
\Delta G_f(\ell) - \Delta G_f(g) = RT\ln\frac{P^{\mathrm{sat}}(298)}{P\std}. $$

Agreement means three independent measurements line up. Of 102 candidate
species, 83 gas and 5 liquid entries survived.

**For an element whose reference state is condensed**, shifting the ideal-gas
value back down into its own phase must return zero:

$$ \Delta G_f(g) + RT\ln\frac{P^{\mathrm{sat}}}{P\std}
   - \Delta H_{\mathrm{fus}}\left(1 - \frac{T}{T_m}\right) = 0 $$

and nothing in that expression touched the formation table --- $P^{\mathrm{sat}}$
comes from $T_b/T_c/P_c$ through Lee--Kesler, and $\Delta H_{\mathrm{fus}}$ and
$T_m$ are separate measurements. Residuals: bromine $-0.053$ kJ/mol, mercury
$+0.012$.

**For a transcribed parameter table**, the check is against an independent
implementation. Every Joback group value, every UNIFAC $R$, $Q$ and interaction
parameter, and every PSRK gas parameter is cross-checked entry-by-entry against
the `thermo` package in the test suite. The transcription is *verified*, not
trusted.

## Two rules about calls to other people's libraries

These are stated as a matched pair in the project's notes and they are worth
learning together.

::: {.trap title="A successful call can be a wrong answer"}
The `chemicals` package returned a boiling point for metformin. It was our own
Joback estimate. Chapter 13.
:::

::: {.trap title="A refusal from an API is not evidence that the data is absent"}
The same package returned `None` for every aqueous ion property, which was
recorded as "the data does not exist" and blocked a milestone. The data ships
*inside the package*, in a TSV file no accessor function reads. Chapter 9.
:::

## An absent count is not a wrong count

One more distinction, from milestone S13, that is easy to get backwards when
reporting a gap.

The hand-typed physical-data list was missing 1,202 species. That is **not** the
same as 1,202 wrong numbers: an absent entry falls through to an estimate, and
some estimates are fine. The honest measurement is *how far the estimates were
off*, which is the mean-6.1%-worst-111% figure, not the count of absences.

Reporting the count would have overstated the finding. The project's own
instrument did overstate a related one by 4.6$\times$, by reading a tier out of
prose.

## What this discipline costs and buys

It costs a real amount: every provider has a refusal path, every generated table
has a build script with an argument in its docstring, and several capabilities
were *delayed* because their data could not be sourced honestly.

What it buys is that the project can say things like "31 of 173 named routes can
run, and that is an upper bound rather than a measured count, and here is the
route that proves the difference" --- and be believed. A simulator that cannot
distinguish its measured numbers from its estimated ones cannot make a claim
like that at all.

::: {.keypoint}
The general form: **an estimator outside its domain is the class of bug here,
and it does not announce itself.** Every guard in this project's properties layer
exists to convert one of those into a refusal with a name on it.
:::
