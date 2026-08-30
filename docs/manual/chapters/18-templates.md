# Layer 2: reaction templates

## The core idea

Instead of storing "acetic acid + ethanol $\to$ ethyl acetate + water", store a
*transformation*:

```
[CX3:1](=[O:2])[OX2H1:3] . [OX2H1:4][CX4:5]
      >>  [CX3:1](=[O:2])[O:4][CX4:5] . [OH2:3]
```

That is this project's Fischer esterification template, verbatim. It says: find
a carboxylic acid group and an alcohol group; make a bond between the acid's
carbonyl carbon (atom 1) and the alcohol's oxygen (atom 4); release the acid's
original hydroxyl (atom 3) as water.

\begin{figure}[htbp]
\centering
\scalebox{0.90}{%
\begin{tikzpicture}[
  node distance=3mm,
  slot/.style={draw=csrule,fill=csbluebg,rounded corners=1pt,
               font=\ttfamily\scriptsize,inner sep=1.6mm},
  sp/.style={draw=csrule,fill=csgreenbg,rounded corners=1pt,
             font=\ttfamily\scriptsize,inner sep=1.6mm},
  lab/.style={font=\sffamily\scriptsize,csgrey},
  ar/.style={->,>=Latex,csgrey}]

  \node[lab] at (-2.3,0.9) {TEMPLATE};
  \node[slot] (r1) at (0,0.9)  {[CX3:1](=[O:2])[OX2H1:3]};
  \node[lab]  (dot) at (3.05,0.9) {\ttfamily .};
  \node[slot] (r2) at (4.7,0.9) {[OX2H1:4][CX4:5]};
  \node[lab]  at (6.9,0.9) {\ttfamily >{}>};
  \node[slot] (p1) at (9.6,0.9) {[CX3:1](=[O:2])[O:4][CX4:5] . [OH2:3]};

  \node[lab] at (-2.3,-0.55) {MATCHES};
  \node[sp] (s1) at (0,-0.55) {CC(=O)O};
  \node[lab] at (1.35,-0.55) {\sffamily acetic acid};
  \node[sp] (s2) at (4.7,-0.55) {CCO};
  \node[lab] at (5.85,-0.55) {\sffamily ethanol};

  \node[lab] at (-2.3,-1.7) {PRODUCES};
  \node[sp] (q1) at (9.6,-1.7) {CCOC(C)=O . O};
  \node[lab] at (12.3,-1.7) {\sffamily ethyl acetate + water};

  \draw[ar] (r1) -- (s1);
  \draw[ar] (r2) -- (s2);
  \draw[ar] (p1) -- (q1);
  \draw[ar,csred] (s2.south) -- ++(0,-0.5) -| (q1.west);
  \draw[ar,csred] (s1.south) -- ++(0,-0.5) -| (q1.west);
\end{tikzpicture}}
\caption{A template is a rule over graphs. The same rule fires on any acid and
any alcohol, with no extra code and no entry in any table.}
\label{fig:template}
\end{figure}

::: {.keypoint}
A few hundred templates generate an effectively unbounded space of concrete
reactions, so the project never enumerates a combinatorial product dictionary.
That is the whole reason this design is tractable, and it is the reason the
simulator can produce a reaction nobody anticipated.
:::

## What a template carries, and how honest each field is

The project states this explicitly and it is the right calibration for anything
the simulator outputs.

| field | honesty |
|---|---|
| `smarts` | **real.** The transformation is chemistry, and its *specificity* is the selectivity mechanism. |
| `Ea` | **sourced.** Each barrier carries the literature band it came from, and the ordering *between* templates is the load-bearing part. |
| `alpha` | **derived where used.** Evans--Polanyi ties the barrier to the reaction enthalpy the network already computes. |
| `A` | the remaining **hand-authored** parameter, and the honest weak point. Order-of-magnitude choices inside the range physically sensible for the molecularity. |
| `reversible` | **never a free parameter.** The reverse Arrhenius pair is derived by detailed balance. There is no hand-typed reverse rate anywhere in this project. |
| `orders` | declared only where the template writes a *global* stoichiometry. |
| `phase` | `"liquid"`, `"gas"`, or `"any"`. |
| `solid_catalyst` | the name of a crystal that must be present. |
| `electrons` | how many cross the external circuit; non-zero makes it an electrode reaction. |

## Selectivity is SMARTS specificity

The oxidation template is written `[CX4;!H0:1][OX2H1:2]` --- a carbinol carbon
that still has a hydrogen to lose --- and that one clause is the entire
selectivity model for the family:

- methanol $\to$ formaldehyde, ethanol $\to$ acetaldehyde, propanol $\to$ propanal;
- a **secondary** alcohol gives a ketone (isopropanol $\to$ acetone), because
  the pattern never said how many hydrogens, only "not zero";
- a **tertiary** alcohol is refused, because there is no hydrogen on the
  carbinol carbon and you cannot make a carbonyl there without breaking a C--C
  bond;
- glycerol yields **both** the primary and the secondary oxidation product,
  from one template, because the pattern matches at two different sites.

None of that is enumerated. It follows from the pattern --- which is why growing
this library is cheaper than it looks, and why writing the pattern carelessly is
the main way to get a confidently wrong answer.

::: {.trap title="A library with one template cannot produce a side product"}
Before `reactions/library.py` existed, templates lived inline in whichever
example needed one. The cost was not tidiness: **nothing ever competed.** A
network with one template has purity 100% by construction, and every "impurity"
the simulator could report was unreacted starting material or an ion.

The project's founding claim is that *yields, side products and temperature
sensitivity emerge*, and two thirds of that was untested. The Phase-0 spike had
hand-written three competing reactions and demonstrated exactly this; the real
code had never reproduced it.
:::

## Barriers, and why the *ordering* matters more than the values

Ethanol over sulfuric acid gives **diethyl ether at 140 °C** and **ethylene at
180 °C**. Both are dehydrations of the same alcohol; which one you get is decided
by temperature, because the alkene route has the higher barrier.

::: {.keypoint}
Reproducing that ordering is the whole test of whether two barriers are
defensible, and it is asserted in the test suite. Get the ordering wrong and the
temperature response is backwards, however good the individual numbers look.
:::

## Evans--Polanyi: rates that respond to thermochemistry

One template handing the same barrier to every substrate it matches means the
author, not the model, decides which of two competing products forms faster. The
fix is an empirical linear relation between barrier and reaction enthalpy within
a family:

$$ E_{a,i} = E_a^\circ + \alpha\,\Delta H_i, \qquad \alpha \in [0,1] $$

so a more exothermic member of the family is faster. $\Delta H_i$ is *computed*
by the network from formation data, not declared.

![One template, three alcohols.\label{fig:ep}](figures/evans_polanyi.pdf)

| alcohol | $\Delta H$ / kJ mol⁻¹ | $E_a$ / J mol⁻¹ |
|---|---:|---:|
| isopropanol | $-10.94$ | 44,532 |
| methanol | $-9.96$ | 45,018 |
| ethanol | $-8.69$ | 45,655 |

With $\alpha = 0$ all three get 50,000, which is the old behaviour exactly.

The reverse direction needs nothing extra: detailed balance gives
$E_{a,\mathrm{rev}} = E_a - (1-\alpha)\Delta H$, which is the Evans--Polanyi
relation for the reverse with transfer coefficient $1-\alpha$. It is still an
empirical relation with a fitted $\alpha$ --- it is just no longer a free
parameter *per substrate*.

::: {.trap title="A positive alpha names the WRONG major product when kinetics fight thermodynamics"}
Measured in milestone S11 on the oxo process, where two templates race for the
same substrate. $\alpha$ hands the lower barrier to the more exothermic route
--- which is the *thermodynamic* product --- and real selectivity there is
kinetic. So $\alpha$ is 0.0 on both hydroformylation templates, deliberately.

The general statement: **$\alpha$ is a claim that the barrier tracks the
enthalpy, and that claim is false exactly where a reaction is under kinetic
control.**
:::

## Hammett: what the substituents already on a ring do to the next step

Here is a specific, measured gap and its fix, and it is the best worked example
in the project of choosing the *right* mechanism rather than the convenient one.

**The gap.** The nitration template gives one $A$ and one $E_a$ to every
nitration on every substrate, so 2,4-dinitrotoluene nitrates exactly as fast as
toluene. The consequence is not subtle: 1.0 mol of toluene and 3.5 mol of nitric
acid reach **96% TNT in ten seconds at room temperature**, and the endpoint does
not move with temperature at all --- 300, 340 and 380 K all land on 1.0000 mol
of trinitro. There is no stage to catch and nothing for an addition rate to
control, and real TNT manufacture is a three-stage process with escalating acid
strength and temperature.

**The wrong fix, and why.** Raise $\alpha$. But $\alpha$ scales the barrier with
the reaction *enthalpy*, and on this network the two point in opposite
directions:

| step | $\Delta H$ / kJ mol⁻¹ |
|---|---:|
| benzene $\to$ nitrobenzene | $-141.2$ |
| nitrobenzene $\to$ 1,2-dinitrobenzene | $-268.1$ |

The **deactivated** ring's step is the *more* exothermic one, so any positive
$\alpha$ makes the second nitration **faster** than the first --- exactly
backwards. `ReactionTemplate` refuses the two together for this reason.

**The right fix.** A substituent effect on an aromatic ring is an *electronic*
property of the substrate, not a function of $\Delta H$, and the tabulated
quantity for exactly this is the **Hammett relation**:

$$ \log_{10}\frac{k}{k_0} = \rho \sum \sigma
\qquad\Longrightarrow\qquad
\Delta E_a = -\ln(10)\,R\,T_{\mathrm{H}}\,\rho \sum\sigma $$

where $\sigma$ is a property of the *substituent and its position* and $\rho$ is
a property of the *reaction* --- so $\rho$ is declared per template.

::: {.trap title="A rho is meaningless without saying which sigma scale it was fitted on"}
This table is on **$\sigma^+$** (Brown and Okamoto 1958), not on the ordinary
aqueous $\sigma$, and that is not a detail. Electrophilic aromatic substitution
builds positive charge on the ring in the transition state, so a resonance donor
stabilises it far more than its ionisation-based $\sigma$ says:

| substituent | $\sigma$ | $\sigma^+$ |
|---|---:|---:|
| methoxy | $-0.27$ | $-0.778$ |
| amino | $-0.66$ | $-1.30$ |
| nitro (meta/para) | 0.71 / 0.78 | 0.674 / 0.790 |

A $\rho$ fitted against $\sigma^+$ applied to $\sigma$ constants is two bases
multiplied together --- which is Chapter 12's fourth Benson trap wearing
different clothes. Note that for electron *acceptors* the two scales nearly
agree, because there is no lone pair to donate, which is what makes two
proxy rows in the table tolerable.
:::

::: {.trap title="And the reference temperature is 298.15 K, not the network's build temperature"}
$\sigma^+$ and $\rho$ are tabulated from rate ratios measured at 25 °C, so 25 °C
is the only temperature at which this conversion reproduces the number it came
from. Using the network's own $T_{\mathrm{ref}}$ instead would make the same
template give different barriers in networks built at different temperatures,
with no measurement anywhere saying it should.

Ask what a fit was anchored on.
:::

**And the line saturates.** A Hammett plot is a straight line fitted over a
bounded abscissa --- here, arenes with $|\sigma^+| < 0.4$. Extrapolating it to
a trinitro ring is asking a linear fit for a number three times outside its
range, and it produces barrier shifts of 90 kJ/mol.

![The line, and the clamp that bounds its extrapolation.\label{fig:hammett}](figures/hammett.pdf)

::: {.keypoint title="Why the clamp is not the rate ceiling"}
The obvious fix is the absolute rate ceiling of Chapter 5. It does not apply:
that ceiling is derived for an *elementary* collision, and a Hammett-corrected
nitration is not an elementary rate law --- it is already a clamped, aggregated
expression. Applying a collision-limit argument to it would be a category error.

So the saturation is its own bound, justified by the fit's own range, and it
came from a *second* literature source that supplies the lower bound. In the
process it cost milestone G5 its headline coincidence, which the project
recorded rather than quietly kept.
:::

## Catalysis, made explicit

A catalyst multiplies the rate and changes nothing else. A **homogeneous**
catalyst is written into both sides of the SMARTS: the extra reactant slot
raises its mass-action exponent to 1, and the identical product slot cancels it
out of the stoichiometry. `builder.to_arrays` adds 1 to its `order` as a
reactant and then cancels it in `delta`. Nothing in Layer 3 or Layer 4 needed a
line of code.

::: {.keypoint title="What it did need was honesty about the pre-exponential"}
An apparent rate is
$$ \text{rate} = A_{\mathrm{apparent}}\,e^{-E_a/RT}\,[\text{acid}][\text{alcohol}] $$
and an explicit one is
$$ \text{rate} = A_{\mathrm{intrinsic}}\,e^{-E_a/RT}\,[\text{acid}][\text{alcohol}][\mathrm{H_3O^+}] $$

so the two agree at exactly one catalyst concentration, and
$A_{\mathrm{apparent}} = A_{\mathrm{intrinsic}}\times[\mathrm{H_3O^+}]_{\text{folded}}$.
**That folded concentration was invisible for three sessions and is now
declared** as `CATALYST_REFERENCE = 0.1` M. The catalysed and uncatalysed forms
of each template are therefore the *same rate* at the reference loading ---
asserted in the tests --- and away from it, "add more acid" is a real lever with
the right slope.

The barrier does not change, and that is deliberate: $E_a$ here has always been
the *catalysed* apparent barrier, so re-declaring the catalyst does not license
re-declaring the barrier.
:::

A **heterogeneous** catalyst --- iron in the Haber process --- cannot be written
that way, for two reasons that are both about representation:

- **a lattice is not a graph.** `[Fe]` has no bonds for a rewrite to match, so
  there is no SMARTS slot to put it in;
- **it is on a different basis.** A crystal lives in the solid block, which is an
  inventory in *mol*; every other exponent in this project is on a concentration
  in mol/L.

So it is *declared*, as `solid_catalyst`, and becomes a second exponent matrix.

::: {.trap title="What it is NOT is a new phase, and that was measured"}
Labelling $\mathrm{N_2} + 3\mathrm{H_2} \to 2\mathrm{NH_3}$ a "solid"-phase
reaction because iron is involved moves it off the ideal-gas standard state,
because `reaction_deltas` applies the pure-liquid shift to anything that is not
`"gas"`. Measured: **$\Delta G$ moves by $-99.7$ kJ/mol and $K$ at 500 K by a
factor of $2.6\times10^{10}$.**

The reaction is a gas-phase reaction. Every participant that *has* an activity
is a gas, and a pure solid's activity is 1. The catalyst multiplies the rate and
touches nothing else. `PHASE_INDEX` still has two entries.
:::

And the same reference-charge bargain applies: `SOLID_CATALYST_REFERENCE = 0.1`
mol, which is 5.6 g of iron --- an ordinary bench charge --- so that
`ammonia_synthesis()` and `ammonia_synthesis(catalyst=None)` are the *same
reaction* at that charge rather than two unrelated calibrations.

::: {.aside title="What a solid catalyst still does not do"}
A real surface saturates: doubling the catalyst stops doubling the rate once the
sites are full. That is a Langmuir--Hinshelwood form, and the kernel cannot
express it --- it evaluates $A T^n e^{-E_a/RT}$ times a product of powers, and
nothing else. So the rate here is strictly first order in catalyst amount, for
ever: **ten times the iron is ten times the rate at any loading.** Right at low
coverage, wrong at high, and stated rather than approximated.
:::

## What the library refuses, and why refusals are content

Twenty templates were added in one milestone to make named historical routes
runnable. Six candidate reaction *classes* were refused rather than credited, on
the standard that **a reaction class is a mechanism claim, not an outcome**:

| refused class | why |
|---|---|
| `fermentation` | glucose $\to$ acetone + butanol + ethanol + CO₂ + H₂ by *Clostridium*. A metabolic **network**, not a transformation. |
| `pyrolysis` | rows read "coal-marker $\to$ coal-tar-marker". Lumped decompositions of things with no molecular graph. |
| `isomerisation` | three mechanisms wearing one label. |
| `thermal-cracking` | a lumped product slate from a radical chain. |
| `catalytic-air-oxidation` | ranked third by routes unlocked; its four rows are at least three mechanisms. |
| `separation` | a distillation is not a reaction class, and the engine genuinely fractionates anyway. |

A seventh, `catalytic-hydrogenation`, was **split** into five mechanism labels
instead --- because unlike the others, every one of its rows *is* a clean
mechanism.

::: {.keypoint}
Crediting a class the engine cannot actually run makes the coverage audit *less*
truthful, and the number it produces is then a description of the label rather
than of the engine. Chapter 29 is about how much this discipline is worth.
:::
