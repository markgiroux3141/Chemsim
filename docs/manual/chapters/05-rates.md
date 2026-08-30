# Rates: how fast, and which product

## Mass action

The simplest useful model of a reaction rate says: a reaction between A and B
happens when an A meets a B, so its rate is proportional to how often that
happens, so it is proportional to the product of their concentrations.

$$ \text{for } \mathrm{A} + \mathrm{B} \to \mathrm{P}: \qquad r = k\,[\mathrm{A}][\mathrm{B}]. $$

In general, for a reaction with reactant multiset $\{A_i\}$,

$$ r_j = k_j \prod_i C_i^{\,\alpha_{ji}} $$

where $\alpha_{ji}$ is the **rate-law exponent**, or *order*, of species $i$ in
reaction $j$. The composition then evolves as

$$ \frac{\dd \mathbf C}{\dd t} = \Delta^{\mathsf T} \mathbf r(T, \mathbf C). $$

That pair of equations is the entire content of
`chemsim/numerics/integrator.py`. It is a system of coupled, non-linear,
first-order ODEs, and it is what the whole architecture exists to feed.

## Order is not stoichiometry, except when it is

For an **elementary** step --- one that really is a single collision --- the
order equals the stoichiometric coefficient, because that is how many of each
molecule has to be in the collision. This project assumes elementary steps by
default, so the multiset of reactants supplies the exponents. `2 EtOH -> ...`
records ethanol twice and gets exponent 2.

::: {.trap title="It stops being true the moment a template writes a global stoichiometry"}
Sulfur burning is

$$ \mathrm{S_8} + 8\,\mathrm{O_2} \to 8\,\mathrm{SO_2} $$

and it is *not* an elementary step --- nine molecules do not meet. Taken as
mass action it is ninth order, eighth in O₂, and the project measured what that
costs: it needs $A = 7\times10^{24}$ (L/mol)⁸/s to run at all; it is *forgiven*
where O₂ is in excess, because the attractor does the work; and it is **not**
forgiven where O₂ is limiting, because $[\mathrm{O_2}]^8$ stalls asymptotically
and the reported yield becomes a reading of the author's pre-exponential rather
than of the chemistry.

So `ReactionTemplate` grew an `orders` field: one exponent per reactant slot.
The burner declares $(1,1,0,\dots)$ --- first order in each --- and the eight
oxygens still leave in the stoichiometry.

**And a declared order may never be reversible.** That invariant is enforced,
and Chapter 21 shows it arriving as a module boundary between two different
solid-phase rate laws.
:::

There is one more case where order and stoichiometry part company, and it is the
most important one in practice: a **catalyst** appears on both sides of the
arrow, so its stoichiometric coefficient is zero, but its exponent is 1. It
multiplies the rate and changes nothing else. See Chapter 18.

## The rate constant, and why it is exponential in $1/T$

Empirically, over an enormous range of reactions,

$$ \boxed{\ k(T) = A \exp\!\left(-\frac{E_a}{RT}\right)\ } $$

the **Arrhenius equation**. $E_a$ is the *activation energy* --- an energy
barrier the reactants must climb before they can become products --- and $A$,
the *pre-exponential factor*, is roughly the rate at which the attempt is made.

The exponential is a Boltzmann factor, and it is the fraction of collisions
energetic enough to clear the barrier (Figure \ref{fig:boltzmann}). A rule of
thumb worth memorising: at room temperature, $RT = 2.5$ kJ/mol, so **a
10 kJ/mol change in barrier is a factor of 55 in rate**, and a rate typically
doubles for every 10 K.

![The exponential is counting the shaded tail.\label{fig:boltzmann}](figures/boltzmann.pdf)

![Three barriers, and the log plot that measures them.\label{fig:arrhenius}](figures/arrhenius.pdf)

::: {.physics}
Transition state theory makes this sharper. Treat the barrier top as a species
in equilibrium with the reactants, and you get the Eyring equation

$$ k = \frac{k_B T}{h}\exp\!\left(-\frac{\Delta G^\ddagger}{RT}\right)
     = \frac{k_B T}{h}\,e^{\Delta S^\ddagger/R}\,e^{-\Delta H^\ddagger/RT}, $$

which identifies $A$ with $(k_BT/h)\,e^{\Delta S^\ddagger/R}$ --- an attempt
frequency ($k_BT/h \approx 6\times10^{12}$ s⁻¹ at 300 K) times an entropic
factor for how ordered the transition state has to be. This is where the
project's "$10^{11}$--$10^{14}$ s⁻¹ for a unimolecular thermal step" band comes
from: it is not folklore, it is $k_BT/h$ with an entropy correction of a couple
of orders either way.
:::

## The pre-exponential is this project's honest weak point

The project is explicit about this and it deserves repeating here, because it
bounds what any number out of the simulator means.

- **Barriers ($E_a$) are sourced.** Each template in
  `reactions/library.py` and `reactions/synthesis.py` carries the literature
  band its barrier came from, and *the ordering between templates is the
  load-bearing part*: ethanol over sulfuric acid gives diethyl ether at 140 °C
  and ethylene at 180 °C because the elimination has the higher barrier. Get
  that ordering wrong and the temperature response is backwards, however good
  the individual numbers look.
- **Pre-exponentials ($A$) are order-of-magnitude choices** inside the range
  physically sensible for the molecularity. They set the absolute timescale.

::: {.keypoint}
So: read a simulated *branching ratio* or *temperature response* as a
prediction. Do **not** read a simulated reaction *time* as one. The project says
this in its own library docstring and it is the correct calibration for anything
you get out of it.
:::

## A ceiling nobody can exceed

Because $A$ is hand-authored, it can be wrong, and a rate constant that exceeds
the physical collision limit is a detectable error rather than a matter of
taste. Two molecules in solution cannot meet faster than diffusion allows
($\sim10^{10}$ L mol⁻¹ s⁻¹); a bond cannot vibrate faster than $\sim10^{13}$
s⁻¹.

::: {.trap title="An energy leak turned out to be a rate constant 94 million times the collision limit"}
Milestone M12 chased an insulated flask that destroyed 495 J of energy after a
precipitation event, and the project's conservation report could not see it
because the report checks matter. Four candidate causes were measured and
refuted. The actual cause was a **derived** rate constant --- one that came out
of detailed balance, not out of anybody's hand --- sitting at $9.4\times10^7$
times the collision limit. At that speed the solver cannot resolve the
transient, and the energy balance leaks.

The fix is a cap, and the interesting part is its shape: it must scale **both**
pre-exponentials, forward and reverse, by the same factor. Scaling one would
change $K$, which would be a thermodynamic falsehood introduced to fix a
numerical problem. `validation/rate_ceiling.py` now audits every network in the
project, and it audits the *reverse* a reversible template implies, not only the
forward somebody typed.
:::

## Competing reactions: the actual point

Nothing above is interesting for a single reaction. It becomes interesting when
several reactions compete for the same starting material, because then the
*ratio* of their rates decides what you get, and that ratio is

$$ \frac{r_1}{r_2} = \frac{A_1}{A_2}\exp\!\left(-\frac{E_{a,1}-E_{a,2}}{RT}\right). $$

Two consequences:

1. **The branching depends on temperature**, and it does so exponentially in the
   *difference* of barriers. A 20 kJ/mol gap that gives 3000:1 selectivity at
   300 K gives only 20:1 at 700 K.
2. **A reaction with a higher barrier can still win if it has a higher
   prefactor**, at high enough temperature. The crossover is a real, computable
   temperature (Figure \ref{fig:selectivity}), and in chemistry this is the
   distinction between *kinetic* and *thermodynamic* control.

![Two templates racing. The crossing is a prediction.\label{fig:selectivity}](figures/selectivity.pdf)

The simulator demonstrates this on the same flask with nothing declared. One
charge of ethanol and acetic acid, `alcohol_chemistry()` loaded, one hour:

![Nobody wrote "if hot, make ether".\label{fig:competition}](figures/competition.pdf)

| $T$ / K | ethyl acetate | diethyl ether | ethene |
|---:|---:|---:|---:|
| 320 | 1.476 | 0.000 | 0.000 |
| 400 | 1.408 | 0.023 | 0.00003 |
| 480 | 0.421 | 0.751 | 0.017 |

::: {.keypoint}
This table is the project's founding claim in miniature. There is no rule
anywhere that says what happens at 480 K. There are three templates with three
barriers, and an integrator.
:::
