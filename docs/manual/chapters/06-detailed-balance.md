# Detailed balance: the hinge of the whole design

Chapters 4 and 5 look independent. They are not, and the constraint that links
them is the single most important structural idea in this project.

## The constraint

A reversible reaction runs both ways. At equilibrium the two rates are equal ---
not just the net flux zero, but *this particular forward process* balanced by
*this particular reverse process*. That is **detailed balance**, and for a
reaction $\mathrm{A} + \mathrm{B} \rightleftharpoons \mathrm{C} + \mathrm{D}$ it
says

$$ k_f [\mathrm A][\mathrm B] = k_r [\mathrm C][\mathrm D]
   \quad\Longrightarrow\quad
   \frac{k_f}{k_r} = \frac{[\mathrm C][\mathrm D]}{[\mathrm A][\mathrm B]}
   \bigg|_{\mathrm{eq}} = K. $$

::: {.keypoint}
$$ \frac{k_f(T)}{k_r(T)} = K(T) \quad\text{at every temperature.} $$
The forward rate, the reverse rate, and the equilibrium constant are three
quantities with two degrees of freedom. You may choose any two; the third is
determined.
:::

::: {.physics}
This is microscopic reversibility: the underlying equations of motion are
time-reversal symmetric, so the transition rate from state $i$ to state $j$ and
back are related by the ratio of the states' Boltzmann weights. Detailed balance
is that statement coarse-grained to whole species. It is the same argument that
gives you the fluctuation--dissipation theorem, and it is equally
non-negotiable: a model that violates it has a perpetual motion machine in it.
:::

## What that buys, structurally

Substitute Arrhenius on both sides:

$$ \frac{A_f e^{-E_{a,f}/RT}}{A_r e^{-E_{a,r}/RT}}
   = \exp\!\left(\frac{-\Delta H + T\Delta S}{RT}\right) $$

and match the temperature-dependent and temperature-independent parts
separately. The result is two lines of arithmetic:

$$ \boxed{\ A_{\mathrm{rev}} = A_{\mathrm{fwd}}\,e^{-\Delta S/R},
   \qquad E_{a,\mathrm{rev}} = E_{a,\mathrm{fwd}} - \Delta H. \ } $$

![The reverse barrier is not a free parameter --- the picture fixes it.\label{fig:db}](figures/detailed_balance.pdf)

Figure \ref{fig:db} is the same statement drawn. The barrier from the product
side is the barrier from the reactant side minus the drop between them. There is
nothing to choose.

## Why this is the design's hinge

Three consequences, and each one shapes a layer of the codebase.

**1. A template declares forward kinetics only.** There is no hand-typed
reverse rate anywhere in this project, by design. The `reversible=True` flag on
a `ReactionTemplate` means "generate the reverse from thermochemistry", and it
therefore requires a thermochemistry provider to be present at network-build
time. A hand-typed reverse would be a free parameter that silently contradicts
the thermodynamics --- you would have a model whose equilibrium constant
disagreed with its own formation data, and nothing would tell you.

**2. The equilibrium is *derived*, never encoded.** The project's esterification
equilibrium is not a number anybody typed. It is $\Delta G_f$ of four species,
put through $K = e^{-\Delta G\std/RT}$, put through detailed balance, put through
an integrator. A closed reactor started from pure reactants and one started from
pure products land on the same quotient, and that is asserted in the test suite.

**3. Layer 4 never learns what "reversible" means.** This is the elegant part.
Because the derived reverse is itself of Arrhenius form, it enters the network
as *an ordinary reaction* --- another row in $\Delta$, another entry in $A$ and
$E_a$. The numeric core stays a pure mass-action integrator with no concept of
reversibility, no pairing of reactions, and no equilibrium logic. All the
thermodynamics happens once, at setup.

::: {.keypoint title="This is the project's characteristic move, and you will see it eight more times"}
Do the model-specific reasoning **once, at assembly time**, and hand the hot
loop a uniform numeric array. Raoult's law and Henry's law become one array of
Antoine coefficients. Lee--Kesler, Rackett and Rowlinson--Bondi become
polynomials in $T$. A forward and a reverse reaction become two rows of the same
matrix. The kernel evaluates one functional form and has never heard of any of
the models that produced it.

That discipline is what makes the `numerics` boundary a clean seam for a future
Rust kernel, and it is what keeps cheminformatics out of the inner loop
entirely.
:::

## The floor, and the notice it prints

$E_{a,\mathrm{rev}} = E_{a,\mathrm{fwd}} - \Delta H$ can come out negative if a
declared forward barrier is smaller than the reaction's endothermicity. A
negative barrier is unphysical --- it would mean a rate that *decreases* with
temperature. The project raises it to zero and **prints a notice**:

> A declared barrier below the reaction's endothermicity is raised to the
> thermodynamic floor ($E_{a,\mathrm{rev}} \ge 0$) with a printed notice.

That is a small thing done in the project's characteristic style: the guard does
not silently repair the input, it says which input it repaired, because the real
problem is a bad declared barrier and the notice is the only thing that will
lead you to it.

::: {.trap title="Ea = max(dH, 0) is zero on an exothermic row"}
A related derivation went wrong in milestone S9. For a *decomposition*, a
reasonable default barrier is the reaction's own endothermicity: you cannot
break the bond for less than the bond is worth, so $E_a = \max(\Delta H, 0)$.
That reasoning is sound *for a decomposition* and was applied to a table that
had grown to include exothermic rows --- where it silently returns a barrier of
**zero**, i.e. a reaction with no temperature dependence at all that runs at its
pre-exponential from absolute zero upward. The lesson recorded is that a default
derived from one mechanism must be re-justified when the table grows a second.
:::

## Catalysis and detailed balance

A catalyst speeds a reaction up. It must therefore speed *both directions* up,
by exactly the same factor --- otherwise adding a catalyst would shift the
equilibrium, which is a perpetual motion machine again.

This project enforces that structurally rather than by a check: a catalyst's
rate-law exponent is applied to the forward reaction and to the derived reverse
identically, so it cancels out of $k_f/k_r$ exactly. A flask with no catalyst
reaches the *same* equilibrium, infinitely slowly.

::: {.keypoint}
That is why the esterification template writes its acid catalyst on **both**
sides of the reaction SMARTS. It is not stylistic. Catalysing one direction only
would make adding acid shift the equilibrium, and the failure would look like
chemistry.
:::
