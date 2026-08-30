# Equilibrium: how far, rather than whether

Chapter 3 gave a yes/no answer. Real reactions do not go to completion; they
stop somewhere, with reactants and products both present, and the reverse
reaction running exactly as fast as the forward one. Where they stop is the
subject of this chapter.

## The equilibrium constant

For a reaction $\sum_i \nu_i A_i = 0$ with $\nu$ negative for reactants, define
the **reaction quotient**

$$ Q = \prod_i a_i^{\nu_i} $$

where $a_i$ is the *activity* of species $i$ --- for now, read it as
concentration divided by a reference concentration, so that $Q$ is
dimensionless. Chapter 8 makes it more honest.

The Gibbs energy of the mixture, as a function of how far the reaction has run,
is

$$ \Delta G = \Delta G\std + RT\ln Q, $$

and equilibrium is where $\Delta G = 0$, i.e. where $Q$ takes the particular
value

$$ \boxed{\ K = \exp\!\left(-\frac{\Delta G\std}{RT}\right). \ } $$

$K \gg 1$ means the reaction runs essentially to completion; $K \ll 1$ means it
barely starts; $K \approx 1$ means you get a mixture. Because $\Delta G\std$ is
inside an exponential divided by $RT \approx 2.5$ kJ/mol at room temperature, an
error of 6 kJ/mol in $\Delta G\std$ is a factor of ten in $K$.

::: {.keypoint title="Why formation-data accuracy dominates everything"}
$RT$ at 298 K is 2.48 kJ/mol. Group-contribution estimates of $\Delta G_f$ carry
several kJ/mol of uncertainty *per species*, and a reaction sums four of them.
So a 5 kJ/mol estimator error is a factor of ~7 in $K$, which is the difference
between a 90% yield and a 50% one. This is why Part II is as long as it is, and
why the project's own list of limitations puts "group-contribution formation
data is the dominant error in $K$" first.
:::

## Le Chatelier, as a derivative

Differentiate $\ln K = -\Delta G\std/RT = -\Delta H\std/RT + \Delta S\std/R$
with respect to temperature:

$$ \frac{\dd \ln K}{\dd T} = \frac{\Delta H\std}{RT^2},
\qquad\text{or}\qquad
\frac{\dd \ln K}{\dd(1/T)} = -\frac{\Delta H\std}{R}. $$

This is the **van 't Hoff equation**. Heating increases $K$ for an endothermic
reaction and decreases it for an exothermic one --- which is the quantitative
form of Le Chatelier's qualitative principle, and it is a straight line if you
plot $\ln K$ against $1/T$ (Figure \ref{fig:vanthoff}).

![Heating helps exactly one of these.\label{fig:vanthoff}](figures/vanthoff.pdf)

::: {.keypoint title="This produces a mechanic nobody wrote"}
In this simulator, an exothermic reaction in an insulated flask *heats itself*.
The higher temperature raises $K$'s denominator and, being exothermic, lowers
$K$. So the flask gets less product than a well-cooled one would. Nobody coded
that; it is van 't Hoff plus an energy balance, and it is the reason a real
preparative chemist uses an ice bath.
:::

## The pressure and concentration versions

Chemists write $K$ three ways and it is worth keeping them straight, because
the project's `reactions/thermo.py` has to convert between them.

- $K_a$, on activities, is the thermodynamic one and is dimensionless.
- $K_p$, on partial pressures in bar, for gas reactions.
- $K_c$, on molarities, for solution reactions.

They differ by factors of $RT$ raised to $\Delta n = \sum_i\nu_i$, the change in
the number of moles. For $\Delta n = 0$ they coincide; otherwise they do not.

::: {.trap title="The conversion factor is not Arrhenius, and hiding it in the pre-exponential made K drift"}
Converting activities to molarities carries a factor $T^{\Delta n}$. This
project originally folded that into the reverse pre-exponential $A$ at one
reference temperature, which is exact at $T_{\mathrm{ref}}$ and wrong
everywhere else --- $K$ drifted as $(T/T_{\mathrm{ref}})^{\Delta n}$. The fix
was to give the rate law a temperature *exponent*, a modified Arrhenius form:

$$ k = A\, T^{\,n} \exp(-E_a/RT), \qquad n_{\mathrm{rev}} = n_{\mathrm{fwd}} + \Delta n. $$

$n$ is zero for every *declared* rate in the project --- only detailed balance
ever sets it --- so the common case stays pure Arrhenius and the kernel skips
the exponent entirely when no reaction needs one. That is a good example of how
these fixes are shaped: make the general case expressible, keep the common case
free.
:::

There is a related trick that appears repeatedly: **write the reaction so that
$\Delta n = 0$ and the conversion cancels**. Acid dissociation is written
$\mathrm{HA} + \mathrm{H_2O} \rightleftharpoons \mathrm{A^-} +
\mathrm{H_3O^+}$ rather than the more familiar $\mathrm{HA}
\rightleftharpoons \mathrm{A^-} + \mathrm{H^+}$ for exactly this reason
(Chapter 10).

## What equilibrium is not

Equilibrium says where the system ends up if you wait long enough. It says
nothing about *how long*, and it says nothing about which of several possible
products you get on the way. Diamond is thermodynamically unstable relative to
graphite at room temperature; the conversion takes longer than the age of the
universe. That gap between "allowed" and "happens" is kinetics, and it is the
next chapter.

::: {.keypoint}
Thermodynamics is a statement about the *destination*; kinetics is a statement
about the *journey*. A simulator that models only the first can tell you what a
flask contains after infinite time. This one models both, which is why it can
tell you that a flask makes ester at 320 K and ether at 480 K --- both are
allowed at both temperatures, and only the rates differ.
:::
