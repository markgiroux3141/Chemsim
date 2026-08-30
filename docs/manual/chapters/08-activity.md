# Activity: when the liquid stops being ideal

## What Raoult quietly asserted

$p_i = x_i P^{\mathrm{sat}}_i$ says a molecule's tendency to escape the liquid
depends only on how much of the liquid is that molecule --- not on what the rest
of it is. That is the assertion that **a molecule cannot tell what it is
surrounded by**, and it is false in an obvious way: ethanol molecules
hydrogen-bond to water, and to each other, and not equally.

Two things followed from that assumption in this project, wrong in the same
direction:

- distillation always ran to a pure product;
- a solid dissolved as readily in a solvent it hates as in one it loves.

One model fixes both, because both were the same missing term.

## Activity and the activity coefficient

Define the **activity** $a_i$ as the thing that actually appears in every
equilibrium expression, and the **activity coefficient** $\gamma_i$ as the
correction factor:

$$ a_i = \gamma_i x_i, \qquad \gamma_i \to 1 \text{ as } x_i \to 1. $$

Then Raoult becomes $p_i = \gamma_i x_i P^{\mathrm{sat}}_i$ and everything else
carries through unchanged. $\gamma_i > 1$ means "this molecule is less
comfortable here than in its own pure liquid, so it escapes more readily than
its mole fraction says"; $\gamma_i < 1$ means the opposite.

::: {.physics}
$\gamma$ is an excess free energy in disguise. Write
$G^{\mathrm{E}} = RT\sum_i n_i\ln\gamma_i$: the difference between the real
mixture's free energy and an ideal one at the same composition. Then
$RT\ln\gamma_i = \partial G^{\mathrm E}/\partial n_i$ --- it is a partial molar
excess quantity, i.e. an interaction term in a mean-field free energy. Every
activity-coefficient model is a model of $G^{\mathrm E}$, and UNIFAC below is a
particular functional form for it with the parameters fitted to group pairs
rather than to species pairs.
:::

## UNIFAC

The model this project uses is **UNIFAC** (Fredenslund, 1975), and its
organising idea is the same one that Chapter 12 will use for thermochemistry: a
molecule is a bag of functional groups, and the interactions are between
*groups* rather than between *molecules*. That is the only way to get coverage
--- there are $O(N^2)$ molecule pairs and only $O(G^2)$ group pairs, and $G$ is
about 50.

$$ \ln\gamma_i = \underbrace{\ln\gamma_i^{\mathrm C}}_{\text{combinatorial}}
              + \underbrace{\ln\gamma_i^{\mathrm R}}_{\text{residual}}. $$

The **combinatorial** part is entropic and depends only on molecular size and
surface area (parameters $R_k$ and $Q_k$ per group): big molecules and small
ones do not mix ideally even if they like each other perfectly. The
**residual** part is enthalpic and comes from a matrix of group--group
interaction parameters $a_{mn}$.

::: {.keypoint title="Why this one model would not collapse into a polynomial"}
Every other property in this project is a function of temperature alone, so it
is evaluated once at setup and handed to the kernel as polynomial coefficients.
An activity coefficient depends on **composition**, and composition *is the
state vector*. Fitting it in advance would mean fitting a function of the
solution.

So the setup/hot-loop split *moves* rather than vanishing. What is precomputed
is the *parameter block* --- the group-count matrix $\nu$, the $R_k$/$Q_k$
vectors, and the interaction matrix already expanded from main groups to a dense
subgroup basis. What runs per RHS call is the evaluation. The contract is
unchanged: numpy in, numpy out, no domain types. The arrays are simply bigger,
and the loop finally does real work.
:::

There is one implementation detail that is not cosmetic. The combinatorial part
is written using $J_i = \Phi_i/x_i$ and $L_i = \theta_i/x_i$ rather than
$\Phi_i$ and $\theta_i$ themselves. Algebraically identical --- but the $x_i$
cancels *analytically* instead of numerically, so a species at exactly zero
concentration has a well-defined activity coefficient rather than a $0/0$. In a
reaction network, most species are at zero for part of the run.

## What it buys: azeotropes, from nothing

If $\gamma$ can bend the vapour-liquid equilibrium line, it can bend it across
the diagonal --- and where $y = x$, distillation stops working. That composition
is an **azeotrope**: a mixture that boils without changing composition.

![Ethanol and water, computed by the engine.\label{fig:txy}](figures/txy.pdf)

Figure \ref{fig:txy} is engine output. The dotted lines are Raoult's law applied
to the *same* Antoine curves, so the only difference between dotted and solid is
$\gamma$. Note two things: the real bubble-point curve dips *below both pure
boiling points*, and the $y$-$x$ curve crosses the diagonal.

| result | chemsim | reference |
|---|---|---|
| ethanol/water azeotrope | $x = 0.899$ | 0.894 (95.6 wt%) |
| its boiling temperature | 351.17 K | 351.3 K |
| below both pure components? | yes (351.45 / 372.45 K) | minimum-boiling, as observed |

::: {.keypoint}
**There is no azeotrope table in this project.** The azeotrope is simply the
composition where $y = x$, and it exists because $\gamma$ bends the equilibrium
line across the diagonal. Distillation of ethanol stalls at 95% here for the
reason it stalls at 95% in a real column.
:::

## Two reference states, one expression

A condensable species uses the **symmetric** convention: $\gamma \to 1$ as the
liquid becomes pure in it. A dissolved gas cannot --- it has no pure liquid at
these temperatures --- so it uses the **unsymmetric** convention, referenced to
infinite dilution in the solvent its Henry constant was measured in:

$$ \gamma^*_i = \frac{\gamma_i(x)}{\gamma_i^{\infty}(\text{reference solvent})}. $$

That division is what transfers a measured constant to a *different* solvent,
because the solute's hypothetical pure-liquid fugacity cancels out of the ratio:
$H(S)/H(\mathrm{ref}) = \gamma^\infty(S)/\gamma^\infty(\mathrm{ref})$. In water
the correction is 1 by construction and the calibrated number comes back
untouched; anywhere else it is computed.

![One tabulated constant, transferred to four solvents.\label{fig:henry}](figures/henry.pdf)

Every one of those solvents used to return water's 0.27 mM.

::: {.aside}
Standard UNIFAC has no group for a permanent gas, so the group table carries
PSRK's gas extension --- added as main groups UNIFAC *does not have*, so no
existing parameter is overwritten and every previously validated result is
unchanged to the last digit. The join is defensible because PSRK's organic
backbone *is* UNIFAC's: 1124 of UNIFAC's 1174 pairs are bit-identical in PSRK.
It is still a join of two regressions rather than one self-consistent fit, and
the project says so in its limitations.

The divisor $\gamma^\infty(T)$ depends only on temperature, so it collapses to
four numbers at setup like everything else --- and it is fitted in $1/T$ rather
than $T$, because it is a ratio of Boltzmann factors and van 't Hoff is the
right basis. That choice is worth an order of magnitude: 0.15% error for N₂
against 2.5%.
:::

## Two liquid layers

If $\gamma$ gets large enough, the free energy of mixing becomes non-convex, and
the system lowers its energy by splitting into two liquids of different
composition --- oil and water. The equilibrium *condition* is easy and has the
same form as every other phase equilibrium: equal activity on both sides,

$$ \gamma_i(x^{\mathrm I})\,x_i^{\mathrm I} = \gamma_i(x^{\mathrm{II}})\,x_i^{\mathrm{II}}. $$

![A miscibility gap is a non-convex free energy.\label{fig:gmix}](figures/gmix.pdf)

::: {.keypoint title="But that condition cannot live in the right-hand side"}
The condition above is *also satisfied by the two phases being identical*. That
trivial solution always exists, it is where a relaxation started from a
well-mixed flask sits, and no amount of integrating will leave it: **a single
phase is a fixed point of its own splitting dynamics.**

Deciding whether that fixed point is a stable minimum or a saddle is a *global*
question about the Gibbs surface, and answering it takes an iteration. So the
work is split the way this project splits everything discrete: the smooth
relaxation lives in the RHS, and the *decision* lives at an event boundary,
between integrations. That is `numerics/lle.py`, and it is the only module in
Layer 4 that is never called from inside a solve.
:::

The test it uses is Michelsen's **tangent-plane criterion**: a phase of
composition $z$ is stable iff the Gibbs surface lies above its own tangent plane
at $z$ for every trial composition $w$, i.e. iff

$$ \mathrm{tpd}(w) = \sum_i w_i\left[\ln w_i + \ln\gamma_i(w) - \ln z_i - \ln\gamma_i(z)\right] \ge 0 $$

everywhere. Working with unnormalised $W_i$ turns the stationary points of that
surface into fixed points of a plain successive substitution, and because
$\mathrm{tpd}$ can have several minima the iteration is run from several
starting points and the deepest wins.

It does **not** flash. It reports "this liquid is unstable, and here is a
composition that is better", and the caller seeds a second phase with a little
material; the ordinary activity-equality term in the RHS then does the rest.
That is deliberate --- the discrete decision and the continuous relaxation stay
separate.

## What is stated rather than assumed

Three things can go wrong, and each is *named* rather than silently treated as
ideal:

- a species has **no UNIFAC decomposition** (dissolved gases, ions, anything
  with an element the table does not cover). It gets $\gamma = 1$ and is listed
  in `vessel.activity_model.report()`;
- a species is an **ion**. UNIFAC is a non-electrolyte model; ions get
  $\gamma = 1$ *by policy*, not by accident --- and see Chapter 10, where a Born
  term supplies what UNIFAC cannot;
- a main-group **pair** is absent from the published matrix. Roughly half are.
  A missing pair is not zero: zero is the strong claim that two groups mix
  athermally.

::: {.trap title="Silence about gamma = 1 was an argument, not a neutral default"}
This is milestone M4 and it is the sharpest instrumentation finding in the
project. A species with no decomposition got $\gamma = 1$ and nothing said so.
In a *single* liquid that is a bounded error. In a **two-phase** calculation it
is not an approximation at all --- $\gamma = 1$ on both sides of an interface
means every species partitions to equal mole fraction, i.e. **an ideal liquid
never splits.** So the silent default was quietly asserting the answer to the
question being asked.

Fixing the flag came before fixing the matcher, deliberately, because until the
model says what it does not know, improving what it does know is unmeasurable.
UNIFAC coverage over the corpus is now 54.1% and reported.
:::

## Cost

The RHS goes from about 140 µs to 231 µs per call for a four-species vessel ---
1.7$\times$. Notably the $\gamma$ kernel is *flat* from 4 species to 25 (78 µs to
87 µs): at these sizes both numbers are numpy dispatch overhead on small arrays,
not arithmetic.

That is a useful negative result. It means UNIFAC does **not** by itself justify
dropping to a Rust kernel; the case for that rests on fixed per-call overhead,
which was already there and which Rust would collapse for the whole RHS rather
than for this part of it.
