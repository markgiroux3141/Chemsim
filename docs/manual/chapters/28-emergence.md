\part{What comes out}

# Behaviour nobody wrote down

The whole point of the design is that things happen which nobody coded. This
chapter is a catalogue of them, in roughly the order they were discovered, with
the mechanism named in each case. Every one has been measured.

## A liquid pins at its boiling point

**What happens.** Ethanol under a hotplate holds **351.46 K** for as long as
there is liquid, then rockets.

**Why.** Evaporation runs away when $\sum_i p_i$ reaches ambient; latent heat
absorbs the input. There is no boiling point anywhere in the code (Chapter 7).

## The boil-off rate is $(Q - \text{losses})/\Delta H_{\mathrm{vap}}$

Falls straight out of the energy balance. Asserted in the tests, written down
nowhere.

## A flask boiled dry superheats

The plateau lasts exactly as long as there is liquid, not one second longer.

## An insulated exotherm gets *less* product

**Why.** Self-heating raises $T$; $T$ lowers $K$ via detailed balance for an
exothermic reaction. Le Chatelier arriving from a heat-transfer coefficient
(Chapters 4 and 6).

## 50/50 ethanol/water gives 71% ethanol vapour

Raoult alone. Distillation with no separation model.

## Air-saturated water holds 0.28 mM oxygen

Henry's law through the *same array* as Raoult. Measured value $\approx$ 0.27 mM.

## There is an azeotrope at $x = 0.899$, 351.17 K

No azeotrope table. It is simply where $y = x$, and it exists because $\gamma$
bends the equilibrium line across the diagonal (Chapter 8). Reference: 0.894 and
351.3 K.

## Which product forms depends on temperature

One flask, one charge, three templates, one hour:

| $T$ / K | ethyl acetate | diethyl ether | ethene |
|---:|---:|---:|---:|
| 320 | 1.476 | 0.000 | 0.000 |
| 400 | 1.408 | 0.023 | 0.00003 |
| 480 | 0.421 | 0.751 | 0.017 |

Nobody wrote "if hot, make ether". The barriers differ, so the branching does.

## A catalytic cycle turns over, and can be lost

The lead chamber process runs a genuine NOx catalytic cycle: **80.3 turnovers on
a 0.5 mmol charge**, watchable and losable. Not a rate multiplier --- a species
that is consumed and regenerated, with its own inventory that a badly-run process
can destroy.

And a **carrier-free** chamber is now inert. Both walls it found are closed, which
is a way of saying the mechanic is real rather than incidental.

## A cooling solution crops crystals

Benzoic acid under water, nothing declared:

| $T$ / K | dissolved | solid |
|---:|---:|---:|
| 330.0 | 0.050000 | 0.000000 |
| 298.1 | 0.026681 | 0.023319 |
| 275.0 | 0.012236 | 0.037764 |

The fusion law against $\gamma$ (Chapter 9). Filtration, cake porosity and the
crystal-crust loss are built on top of it.

## Toluene and water separate, and steam-distil

Two layers and a boiling point at **358.31 K** --- below *both* components ---
without a single reaction. "Nothing happens" is not the same as "the flask is
inert."

## A kiln has a threshold temperature

Calcite does not calcine below about 1120 K under 1 bar of air, and sweeping the
CO₂ away makes it go lower. Both are consequences of a pure solid having unit
activity (Chapters 9 and 21).

## A gas-shift reaction peaks and falls away

The water-gas shift peaks at **620 K** and declines above it --- exothermic, so
$K$ falls with temperature while the rate rises. The reformer beside it is inert
until **900 K**. Deacon's ceiling and its rate cross near **650 K**.

Three different shapes, from three sets of $(\Delta H, \Delta S, E_a)$ and one
integrator.

## A Claus flask recovers 100.0% of its sulfur at exactly the stoichiometric air rate

**Why**: burning a third of the feed is what leaves the 2:1 ratio the second
template wants. Two templates, one flask, and an optimum nobody declared.

## A smelter emerges from two independent declarations

Ore + coke + air $\to$ metal. One term burns the coke to carbon monoxide; a
different term reduces the ore with it. **Neither declares the route**, and the
coverage audit credited a catalog route that nothing in the code had named
(Chapter 21).

## A zinc retort distils its product

Zinc evolves as a vapour and condenses in a cool receiver at **1180.15 K**,
which is a real Belgian retort's actual mechanic --- from moving one data entry
between two tables, with no engine code changed.

## Two templates racing cross from kinetic to thermodynamic control

The oxo process's two products swap ranks at a computable temperature. The
crossing is a prediction of the two barriers and two prefactors, not a
declaration (Chapter 5).

## An electrolysis cell has a decomposition potential

**1.441 V for water** (book: 1.229) and **2.362 V for brine** (book: 2.186), out
of formation data alone. Nothing declares a threshold; it is where $nFE$
overtakes $\Delta G_{\mathrm{chem}}$ (Chapter 11).

## A brine cell makes chlorine rather than oxygen

Thermodynamics prefers oxygen. Kinetics --- the two activation overpotentials,
declared as barriers --- decides otherwise. This is the industrial fact that
makes the chlor-alkali process possible, reproduced from two numbers.

## An oxidant that becomes one of its own reagents

In the Skraup synthesis the oxidant's *reduction product* is itself a substrate
for the reaction, so the system feeds itself. The network found that; nobody
wrote it.

## An open flask loses 98% of the yield

Same Skraup preparation, vented instead of sealed. The volatile intermediate
leaves. That is a real preparative fact and it arrives here as a boundary flux.

## Drip too fast and the pot runs away

The dropping funnel (Chapter 22). And the negative result beside it: **sensible
heat alone cannot make an addition rate matter** --- the rate matters when the
addition drives a reaction whose heat is large.

## Nitration stages

With ring deactivation, a nitration becomes a *process* rather than an event:
each nitro group makes the next substitution slower, which is why real TNT
manufacture escalates its acid strength and temperature through three stages
(Chapter 18). Before that, one flask reached 96% trinitro in ten seconds at room
temperature and the endpoint did not move with temperature at all.

## An inert spectator moves a yield

Found in milestone C5. A species that participates in no reaction still changes
the answer --- it dilutes, it carries heat capacity, it shifts mole fractions and
therefore activities and therefore partial pressures. "Inert" is a statement
about chemistry, not about the state vector.

::: {.keypoint title="The pattern"}
Look at what those twenty-four have in common. Almost none of them came from
adding a *feature*. They came from putting two existing terms in the same flask
and integrating.

That is the return on the design decision in Chapter 1 --- and it is also why the
project's coverage work (Chapter 29) is about *templates and data* rather than
about engine capability. The engine has been finished, in a real sense, for a
long time; what is short is chemistry to put in it.
:::

## And two that went the other way

Not everything emergent is welcome, and both of these were caught by audits
rather than by anything failing:

- **a flask reported 111% yield**, by manufacturing oxygen inside a dryout band
  three overlapping gates all thought they owned (Chapter 21);
- **an insulated flask destroyed 495 J**, because a derived rate constant was
  $9.4\times10^7$ times the collision limit (Chapter 27).

Both are exactly as emergent as the twenty-four above. That is the cost of the
design, and it is why Part IV exists.
