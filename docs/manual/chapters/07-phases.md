# Phases: boiling, and why there is no boiling point in the code

## Vapour pressure

Put a liquid in a sealed flask with some empty space above it. Molecules leave
the surface and rejoin it; at equilibrium the two rates match, and the gas above
sits at a definite pressure that depends only on temperature and on what the
liquid is. That is the **saturation vapour pressure** $P^{\mathrm{sat}}(T)$.

It rises steeply with temperature, because escaping costs an energy
$\Delta H_{\mathrm{vap}}$ and the fraction of molecules with that much energy is
a Boltzmann factor. Equating the chemical potentials of the two phases and
differentiating gives the **Clausius--Clapeyron** relation,

$$ \frac{\dd \ln P^{\mathrm{sat}}}{\dd T} = \frac{\Delta H_{\mathrm{vap}}}{RT^2}, $$

which integrates (with $\Delta H_{\mathrm{vap}}$ taken constant) to
$\ln P^{\mathrm{sat}} = -\Delta H_{\mathrm{vap}}/RT + \text{const}$. In
practice a three-parameter empirical fit does better over a wide range, and the
standard one is **Antoine's equation**:

$$ \log_{10}\!\left(\frac{P^{\mathrm{sat}}}{\text{bar}}\right) = A - \frac{B}{C+T}. $$

::: {.keypoint}
Every volatile species in this project carries exactly three numbers, $(A,B,C)$,
and Layer 5 asks them exactly one question: *given a liquid mole fraction $x_i$,
what partial pressure is that in equilibrium with?*
:::

![Vapour-pressure curves, computed by the engine's own provider.\label{fig:psat}](figures/psat.pdf)

## Raoult's law, and the same array serving Henry's law

For an ideal liquid mixture, each component contributes its vapour pressure in
proportion to how much of the liquid it is:

$$ p_i = x_i\, P^{\mathrm{sat}}_i(T). \qquad \textbf{(Raoult)} $$

For a **permanent gas** --- O₂ or N₂, which are above their critical
temperature and have no vapour pressure at all --- the same *shape* of law
holds, but the constant means something different: it is a solubility constant
measured in a particular solvent.

$$ p_i = x_i\, H_i(T). \qquad \textbf{(Henry)} $$

Henry constants follow van 't Hoff, $H(T) = H_{\mathrm{ref}}\exp[-C(1/T -
1/T_{\mathrm{ref}})]$, which is *already Antoine-shaped with $C = 0$* --- no
fitting required, just algebra.

::: {.keypoint title="Two physical laws, one array"}
So `properties/volatility.py` emits one three-number record per species and the
integrator evaluates $10^{A - B/(C+T)}$ for all of them at once. Raoult's law
and Henry's law are the same line of code, and the hot loop cannot tell which
species is which.

This is the setup/hot-loop split again, and it is the cleanest instance of it in
the project.
:::

The provider has three sources in preference order, each stamped on the result:
curated Antoine constants (NIST) for the solvents that matter; curated Henry
constants for permanent gases; and Lee--Kesler estimation from $T_b/T_c/P_c$,
fitted to Antoine form, so a molecule nobody has ever tabulated still gets a
curve. Chapter 13 is about that third route.

## Boiling is a condition, not a number

Here is the payoff, and it is characteristic of the whole project.

A liquid boils when its vapour pressure reaches the ambient pressure --- at
that point a bubble can form in the bulk, because the vapour inside it can push
the surroundings back. Ethanol's normal boiling point is 351.4 K because that is
where its Antoine curve crosses 1.013 bar (Figure \ref{fig:psat}).

**There is no boiling point stored anywhere in this codebase.** What exists is:

- an evaporation flux driven by the difference between equilibrium and actual
  partial pressure, $\dot n_i \propto k_{la}(x_i\gamma_i P^{\mathrm{sat}}_i - p_i)$;
- an energy balance in which that flux carries latent heat away;
- a vent that opens when the total pressure exceeds ambient.

Run those together and a flask on a hotplate does this:

![Engine output. Plateau, dryout, superheat.\label{fig:boil}](figures/boilplateau.pdf)

The temperature climbs, then **pins at 351.46 K** --- against a measured 351.4
--- and holds there for as long as there is liquid. It holds because once
$\sum_i p_i$ reaches ambient, any further heat goes into evaporation instead of
into temperature: the evaporation term runs away, and latent heat absorbs the
entire hotplate input. Then the liquid runs out, there is nothing left to absorb
the heat, and the temperature rockets.

::: {.keypoint}
The boil-off rate is $(Q_{\mathrm{in}} - \text{losses})/\Delta H_{\mathrm{vap}}$
and that too is not written down anywhere. It falls out of the energy balance,
and the test suite asserts it.
:::

## Distillation

If two components have different volatilities, the vapour is richer in the more
volatile one. That is separation, and it is the oldest unit operation there is.

For an ideal binary mixture the vapour composition is

$$ y_1 = \frac{x_1 P^{\mathrm{sat}}_1}{x_1 P^{\mathrm{sat}}_1 + x_2 P^{\mathrm{sat}}_2}. $$

A 50/50 ethanol--water liquid gives a vapour that is 71% ethanol --- and the
project reproduces that from Raoult alone, with no separation model whatsoever.
Condense that vapour, boil it again, and you enrich further. Do it many times
and you have **fractional distillation**; the project builds an eight-plate
column that reaches 85.4% purity at a reflux ratio of 5 (Chapter 22).

::: {.trap title="A still with no open end is a pressure vessel"}
The project's first attempt at a plate column diagnosed its poor separation as a
startup transient. It was not. The still had **no open end**, so it ran at
3--3.8 bar, at which the whole vapour--liquid equilibrium is different. The
diagnosis was wrong and the fix was a vent. The recorded lesson is that when a
separation underperforms, check the pressure before you check the model.
:::

## What is still missing from this picture

Everything above assumes the liquid is **ideal** --- that a molecule cannot tell
what it is surrounded by. Under that assumption distillation always runs to a
pure product, because the vapour is always richer in the more volatile
component. Reality disagrees, sometimes spectacularly, and fixing it is Chapter
8.
