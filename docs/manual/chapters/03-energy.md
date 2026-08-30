# Energy: enthalpy, entropy, and which way a reaction goes

This is the chapter that does the most work in the rest of the manual. If you
retain one thing from Part I, retain this.

## The question

Mix two things. Does anything happen? Chemistry answers this with a single
scalar, and the physics behind it is one you know: a system at fixed temperature
and pressure, exchanging heat with a reservoir, minimises its **Gibbs free
energy**.

## Enthalpy

At constant pressure, a system that expands does work $p\,\dd V$ on its
surroundings, so the heat it absorbs is not $\dd U$ but $\dd U + p\,\dd V$.
Define

$$ H = U + pV $$

and the heat absorbed at constant pressure is exactly $\Delta H$. That is all
enthalpy is: internal energy with the expansion bookkeeping folded in, so that
"heat released" is a state function.

A reaction with $\Delta H < 0$ releases heat --- **exothermic**; a flask gets
warm. $\Delta H > 0$ absorbs it --- **endothermic**; a flask gets cold, or needs
a burner. Typical magnitudes: 50--200 kJ/mol for making or breaking a bond, and
this project's lime kiln runs at $\Delta H = +179.2$ kJ/mol.

## Entropy

$S = k_B \ln \Omega$, and per mole, $S = R\ln\Omega$. Nothing surprising. What
matters chemically is that entropy has two reliable sources:

- **more particles.** A reaction that turns one molecule into two increases the
  entropy substantially --- roughly $+150$ J/(mol K) per extra gas molecule.
  This is why decompositions are entropy-driven and why heating helps them.
- **more disorder in position.** Gas $\gg$ liquid $>$ solid. Vaporising a mole
  of a liquid costs about $+90$ J/(mol K) (Trouton's rule, and it is
  surprisingly universal).

## Gibbs free energy

$$ G = H - TS, \qquad \Delta G = \Delta H - T\Delta S. $$

A process at constant $T$ and $p$ runs spontaneously if $\Delta G < 0$.

::: {.physics}
This is the Legendre transform you would write down anyway. Maximising the
*total* entropy of system-plus-reservoir, with the reservoir's entropy change
being $-\Delta H / T$, is the same statement as minimising $H - TS$ for the
system alone. Equivalently, $G$ is $-k_BT\ln Z$ for the isothermal--isobaric
ensemble, per mole. Chemists write $G$ because a flask is at fixed $T$ and $p$
by default; nothing deeper is going on.
:::

The two terms compete, and $T$ sets the exchange rate between them. An
endothermic reaction that increases entropy ($\Delta H > 0$, $\Delta S > 0$) is
forbidden when cold and allowed when hot, with the crossover at
$T = \Delta H/\Delta S$. That single sentence explains kilns, cracking,
distillation, and why a lime kiln has to be hot: 179,190 J/mol divided by 160.3
J/(mol K) is 1118 K, and Figure \ref{fig:lime} says the same thing with a curve.

## Standard states, which is the subtle part

$G$ is only defined up to a reference, exactly like a potential. Chemistry fixes
the reference with two conventions.

**First: elements in their standard state have zero.** Define the *standard
enthalpy of formation* $\Delta H_f\std$ of a compound as the enthalpy change
making one mole of it from its elements in their most stable form at 298.15 K
and 1 bar. Then $\Delta H_f\std = 0$ for O₂ gas, for graphite, for liquid
bromine, for rhombic sulfur --- by definition, not by measurement. A reaction's
enthalpy is then a difference of tabulated formation values:

$$ \Delta H_{\mathrm{rxn}}\std = \sum_i \nu_i\, \Delta H_{f,i}\std, $$

and the element terms cancel automatically because the reaction balances. This
is the chemical equivalent of choosing a zero of potential energy: entirely
arbitrary, entirely consistent, and it collapses an $N^2$ table of reaction
energies into an $N$ table of formation energies.

::: {.trap title="An estimator that returns a non-zero value for a reference state is provably wrong"}
Because $\Delta H_f\std = \Delta G_f\std = 0$ for an element in its standard
state is a *definition*, an estimator that returns anything else has been caught
red-handed. This project has caught three:

| species | estimator said | error, as a factor in $K$ |
|---|---|---|
| Cl₂ | $\Delta H_f = -74.81$ kJ/mol | $\sim10^{13}$ |
| F₂ | $\Delta G_f = -440.5$ kJ/mol | astronomical |
| S₈ | $\Delta G_f = +275.96$ kJ/mol | $\sim e^{91}$ |

The first was fixed species by species, which is why the lesson did not
generalise and the other two survived. The class fix is that
`properties/thermochemistry.py` now **refuses to let any estimator price an
elemental species at all** --- it comes from a curated table or it is refused by
name. See `properties/element_data.py`.
:::

**Second: the standard state has to say what phase, and this is where it gets
sharp.** A reference state that is a *gas* has an ideal-gas formation value of
exactly zero. A reference state that is *condensed* does not --- its ideal-gas
record is its vaporisation or sublimation energy, which is a real measured
number:

| element | reference state | $\Delta H_f$(ideal gas) | $\Delta G_f$(ideal gas) |
|---|---|---:|---:|
| H₂, N₂, O₂, F₂, Cl₂ | gas | 0 | 0 |
| Br₂ | liquid | $+30.90$ | $+3.08$ |
| Hg | liquid | $+61.40$ | $+31.85$ |
| I₂ | solid | $+62.40$ | $+19.29$ |
| S₈ (rhombic) | solid | $+100.42$ | $+48.68$ |

::: {.trap}
Bromine and iodine were pinned to 0.0 in this repository before
`element_data.py` existed. The species-by-species fix for the chlorine bug put a
62 kJ/mol error *into* iodine while taking a 75 kJ/mol error *out of* chlorine
--- the same bug one level up. This is the clearest example in the project of
why a fix has to close a class rather than a member.
:::

## Moving between standard states

Group-contribution thermochemistry (Chapter 12) is **ideal-gas** data: it
describes an isolated molecule at 1 bar. Almost every reaction in this simulator
happens in a *liquid*. Using the gas numbers unmodified is not a small
approximation; it is the claim that a molecule costs the same to make whether or
not it is surrounded by solvent.

The fix is exact and cheap. A pure liquid is in equilibrium with its own vapour
at its saturation pressure $P^{\mathrm{sat}}$, so their molar Gibbs energies are
equal:

$$ \mu(\text{liquid}) = \mu(\text{gas at } P^{\mathrm{sat}})
   = \mu(\text{gas at } 1\ \text{bar}) + RT \ln\frac{P^{\mathrm{sat}}}{P\std}. $$

Hence per species

$$ \boxed{\ \Delta G_f(\ell) = \Delta G_f(g) + RT\ln\!\frac{P^{\mathrm{sat}}}{P\std},
   \qquad \Delta H_f(\ell) = \Delta H_f(g) - \Delta H_{\mathrm{vap}}. \ } $$

The Gibbs shift is always negative, since $P^{\mathrm{sat}} < 1$ bar below the
boiling point. And $\Delta H_{\mathrm{vap}}$ is taken from the *same* Antoine
curve by Clausius--Clapeyron rather than from a second correlation, so both
halves come from one source and the entropy you derive from them is real: water
44.1 against a measured 44.0, ethanol 42.7 against 42.3, acetone 31.6 against
31.0 kJ/mol.

For Fischer esterification the effect is a factor of 2.4 --- $K(298\ \mathrm{K})$
moves from 19.4 to 8.1, against a measured value near 4 (Figure
\ref{fig:standardstate}). What remains is group-contribution error in the
formation data itself, which is Chapter 12's problem.

![One change of reference state, in the right direction.\label{fig:standardstate}](figures/standardstate.pdf)

::: {.keypoint}
The same expression serves a dissolved gas, with its Henry constant in place of
$P^{\mathrm{sat}}$ --- one formula, two standard states. Species too involatile
to trust (ions, and anything whose extrapolated $P^{\mathrm{sat}}$ falls below
$10^{-12}$ bar) keep the basis their data was derived on, *and say so on the
record*.
:::

::: {.trap title="A standard state can be wrong in a comment"}
In milestone S12 the project found that a source-code comment had priced its own
reaction on the wrong standard state, flipping the sign of $\Delta S$ and
landing 163 kJ/mol from the right answer. The code was right and the
hand-computed numbers written beside it were wrong. This is exactly why the
project prefers derived quantities to transcribed ones: a derivation can be
re-run, a comment cannot.
:::

## Heat capacity, and what this project does not do

$C_p = (\partial H/\partial T)_p$. It matters twice: a vessel's temperature
response is $\dd T/\dd t = \dot q / C_p$, and strictly $\Delta H$ itself depends
on temperature via Kirchhoff's law,
$\dd(\Delta H)/\dd T = \Delta C_p$.

This project uses temperature-dependent $C_p$ for the *energy balance* (a cubic
in $T$ per species, Chapter 13) but assumes $\Delta H$ and $\Delta S$ of
reaction are temperature-independent when computing $K(T)$ --- that is, van 't
Hoff with a constant enthalpy. The correction was built and rejected in
milestone M6 as not worth its cost at the temperature spans involved; the
decision is recorded rather than assumed.
