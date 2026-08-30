# The physical half, and the boiling point nobody will estimate

## Two halves that fail differently

The project splits every species' data into two halves and reports them
separately, because they fail for different reasons and cost different things
when they fail.

| half | what it is | what an error there does |
|---|---|---|
| **formation** | $\Delta H_f$, $\Delta G_f$ | sets every equilibrium constant. An error propagates into yields and never washes out. |
| **physical** | $T_b$, $T_c$, $P_c$, $V_c$ | sets the vapour-pressure correlation. An error moves a boiling point and a headspace composition. |

Averaging them into one coverage number would hide which of the two you are
short of. Chapter 12 covered the formation half; this chapter is the physical
one.

## The chain

For a species with no tabulated Antoine constants, the project builds a
vapour-pressure curve like this:

1. take a **measured boiling point** $T_b$;
2. get $T_c$ and $P_c$ from **Wilson--Jasperson**, which takes $T_b$ as an input;
3. get $V_c$ from **Fedors**, from structure alone;
4. invert **Lee--Kesler** at $T_b$ to obtain the *acentric factor* $\omega$ ---
   a one-number measure of how non-spherical the molecule is, defined so that
   $\omega = 0$ for argon;
5. evaluate Lee--Kesler's corresponding-states vapour-pressure curve over a
   temperature window and **fit it to Antoine form**.

Step 5 is the recurring move: whatever the correlation is, it is sampled and
fitted at setup so that the kernel evaluates one functional form and has never
heard of Lee--Kesler. The same is done for liquid molar volume (Rackett) and
liquid heat capacity (Rowlinson--Bondi), both fitted to cubics in $T$.

::: {.keypoint title="Why Wilson-Jasperson and Fedors exist here at all"}
The reason is architectural rather than numerical. Joback was the *only* source
of critical properties in the project, and Benson --- the better estimator above
him --- says nothing about $T_b/T_c/P_c/V_c$ because group additivity is a
statement about formation. So **a species Joback refused had no physical half
from anywhere, and its Benson formation half was unreachable no matter how well
Benson priced it.**

Benson gets acetic anhydride's formation enthalpy to within 3.7 kJ/mol of
measurement, and before `properties/critical.py` existed that value was
computed, correct, and unusable.

Wilson--Jasperson takes $T_b$ as an *input*, so the whole coverage problem
collapses to one lookup.
:::

Accuracy, measured on acetic anhydride against the CRC handbook:

| | estimated | measured | error |
|---|---:|---:|---:|
| $T_c$ | 600.9 K | 606.0 K | 0.8% |
| $P_c$ | 44.9 bar | 40.0 bar | **12%** |
| $V_c$ | 290.3 cm³ | 294.0 cm³ | 1.3% |

$P_c$ is the weak link, and it feeds $\omega$, which sets the entire
vapour-pressure curve. So every entry enabled by this route has to pass a
boils-at-1-atm cross-check.

## Nothing here estimates a boiling point, and that is deliberate

::: {.keypoint}
The chain above needs $T_b$ as an input and nothing in this project will
estimate one. A species with no measured boiling point is **refused** rather
than served a guess.
:::

The reason is a specific trap, and it is the sharpest data-sourcing lesson in
the repository.

::: {.trap title="A library will hand back your own estimate labelled as data"}
The `chemicals` package serves Joback *predictions* through the same accessor as
its measured compilations. For metformin the only $T_b$ source it offers is
`JOBACK`, returning 609.52 K --- **bit-identical** to what this project's own
Joback implementation computes from the same groups, because it is the same
method.

Looking that up would have closed a coverage gap by relabelling our own estimate
as measured data: the number would move from the "estimated" column to the
"measured" column having changed by exactly zero. Every estimated method is
excluded and the species refused instead, which is why metformin and saccharin
carry no $T_b$ rather than a confident-looking number.
:::

That trap has a second half worth stating separately.

::: {.trap title="Boils-at-1-atm is NOT an independent check if the fit was anchored on Tb"}
The natural cross-check on a vapour-pressure curve is "does it predict the
measured normal boiling point?" --- and if $\omega$ was obtained by *inverting
the correlation at $T_b$*, that check is circular. It is guaranteed to pass and
it measures nothing.

The project found this and fixed it in milestone S10 by making the fit
*unanchored* for the species where an independent check was needed, at which
point boils-at-1-atm becomes a real measurement again.
:::

## Two data tiers, and the empirical test that separates them

Measured data is not all the same kind of thing, and the project keeps a
distinction on every value:

**`experimental`** --- critically evaluated measurement: IUPAC, CRC, the NIST
WebBook, Common Chemistry, Open Notebook melting points.

**`compilation`** --- published, widely used, and **not auditable to a
measurement**. The `chemicals` package says of one such source that "no data
points are sourced in the work"; another mixes experimental with estimated
values; a third is supporting material from an equation-of-state paper.

The decisive test for that distinction is empirical rather than bibliographic:
one compilation source gives **saccharin a critical temperature of 968 K**, and
saccharin decomposes near 500 K without ever boiling. That is not a measurement
of anything.

So $T_c/P_c/V_c$ are taken from the experimental tier only; where none exists
the record falls to Wilson--Jasperson and Fedors, whose error is *known* because
`validation/physical_estimation.py` measures it. A number of unrecorded origin
may itself be a group-contribution estimate from a method you cannot inspect,
and a known error beats an unknown provenance. $T_b$ gets no such choice ---
nothing here estimates one --- so a compilation-tier $T_b$ is accepted where it
is the only source, and stamped.

## The hand-typed list, and how big that gap turned out to be

::: {.trap title="A table generated from 37 hand-typed names, in a 1583-compound corpus"}
`properties/physical_data.py` is a generated file. Until milestone S13 it was
generated from a **hand-typed list of 37 species names**, and everything else in
the corpus fell to Joback --- silently, because a Joback record *resolves*
without complaint.

Regenerating it from `data/catalog` itself gives **1,239 species, 896 with a
measured boiling point**. The 881 estimates it replaced were off by a **mean of
6.1% and a worst of 111%**.

Two further findings came out of the same session, and both are about
instruments rather than chemistry:

- **The gap was not exotic. It was the bench solvent.** Not obscure species ---
  the things actually in the flask.
- **The instrument built to expose the gap undercounted it by 60%**, because the
  coverage audit's tier classifier was *parsing prose* out of provenance strings.
  The `thermochemistry` module had already written down why that would fail.
:::

The effect on the two coverage halves, before and after:

| | before S13 | after |
|---|---:|---:|
| physical half **measured** | 40 (2.5%) | **652 (41.2%)** |
| physical half falls back to Joback | 964 (61%) | 333 (21%) |

## What the two halves look like now

![Both bars are measured by running the corpus through the real providers.\label{fig:coverage}](figures/coverage.pdf)

Figure \ref{fig:coverage} is the current state over all 1,583 compounds. Read
the formation half first: a Joback-only formation half integrates without
complaint and reports a confidently wrong equilibrium constant.

| overall | count | of 1583 |
|---|---:|---:|
| both halves resolve | 1167 | 73.7% |
| formation half measured or Benson (not Joback) | 766 | 48.4% |
| formation half falls back to Joback | 401 | 25.3% |
| refused outright | 416 | 26.3% |
| decomposes for UNIFAC (can enter a phase split) | 857 | 54.1% |

::: {.aside title="A negative heat capacity had been in the engine since S4"}
Rowlinson--Bondi is a corresponding-states correlation for liquid $C_p$, good to
about 5% for non-polar species and poor for hydrogen-bonding ones (it
overestimates ethanol by ~40%, so alcohols, water and acids are curated). It can
also, outside its domain, return a **negative** heat capacity --- and it had
been doing so for mercury since milestone S4. 103 rows still carry one.

A negative $C_p$ means a vessel that cools when you heat it. It was found by an
audit, not by anything going wrong, which is the usual way.
:::
