# Counting matter: moles, concentration, and balance

This chapter is short and entirely mechanical, but every equation in the rest of
the manual is dimensionally anchored to it.

## The mole

Molecules are small and numerous, so chemistry does not count them individually.
The **mole** is a fixed count:

$$ 1\ \text{mol} = N_A = 6.02214076\times10^{23}\ \text{entities}. $$

It is a unit in the sense that "dozen" is a unit. Its usefulness is that the
mass of one mole of a substance in grams is numerically its molecular mass in
atomic mass units --- one mole of water (H₂O, mass 18) is 18 g. So a bench
chemist weighing out 18 g of water knows they have $N_A$ molecules without ever
thinking about $N_A$.

::: {.physics}
The mole exists so that the two scales chemists work at --- the molecular and
the weighable --- differ by a constant rather than by an act of imagination.
$R = N_A k_B = 8.314$ J/(mol K) is Boltzmann's constant per mole, and every
$RT$ in this manual is a $k_BT$ that has been rescaled. When you see
$\exp(-E_a/RT)$, read $\exp(-\epsilon/k_BT)$.
:::

## Concentration, and why this project mostly avoids it

**Concentration** is amount per volume. The chemist's unit is *molarity*:

$$ [\mathrm{A}] = \frac{n_A}{V}, \qquad \text{mol/L, written M}. $$

Rate laws are written in concentrations, because a reaction rate depends on how
often two molecules meet, which depends on how crowded the liquid is.

::: {.keypoint title="But the state vector is in moles"}
This project's vessel integrator stores **moles**, not concentrations, and the
reason is worth stating early because it recurs. Concentration needs a volume in
the denominator, and the liquid volume is *itself a state variable*: it shrinks
as things boil off or crystallise out, and it goes to zero when the flask boils
dry. Moles stay meaningful at that limit; concentrations do not. So the state is
moles and the RHS divides by a volume computed on the fly, guarded against zero.
:::

**Mole fraction** is the other common measure --- $x_i = n_i / \sum_j n_j$, so
$\sum_i x_i = 1$. Phase equilibrium is naturally written in mole fractions
(Chapters 7--9); rates are naturally written in molarity. Both appear.

## A reaction, written down

A chemical equation is a statement about counts:

$$ \mathrm{CH_3COOH} + \mathrm{C_2H_5OH} \rightleftharpoons
   \mathrm{CH_3COOC_2H_5} + \mathrm{H_2O} $$

(acetic acid plus ethanol gives ethyl acetate plus water --- this is *Fischer
esterification*, the project's running example). The numbers in front, when
they are not 1, are **stoichiometric coefficients**. Written as a vector
$\nu$, negative for reactants and positive for products, a reaction is exactly a
column of an integer matrix, and the composition changes along it:

$$ \frac{\dd \mathbf{n}}{\dd t} = \nu\, r $$

for a single reaction proceeding at rate $r$. For a network of $m$ reactions
over $n$ species this becomes $\dd\mathbf{n}/\dd t = \Delta^{\mathsf T}
\mathbf{r}$ with $\Delta$ the $m\times n$ stoichiometric matrix, and *that
matrix product is essentially the whole of the numeric core*. It is what
`chemsim/numerics/integrator.py` evaluates.

## Balance is a conservation law, and it is enforced

A chemical equation must balance: the same number of atoms of each element on
both sides, and the same total charge. This is not a convention, it is
conservation of nucleons and of charge, and it means $\Delta$ has a null space.

Let $E$ be the $n \times k$ matrix whose $(i,e)$ entry is the number of atoms of
element $e$ in species $i$, with an extra column for charge. Then balance is

$$ \Delta E = 0. $$

::: {.keypoint}
This project *checks* that identity at network-build time and rejects a template
that violates it, rather than integrating it and producing matter. From the
project's own notes: "Element and charge conservation are enforced --- a
malformed template that doesn't balance is rejected, not silently integrated."
It is the oldest guardrail in the codebase and it has caught real bugs at every
level, including in the hand-authored catalog, where a check added late found
that **75 of 367 rows do not balance**.
:::

Because $\Delta E = 0$ holds exactly in integers, $\mathbf{n}^{\mathsf T} E$ is
conserved by the reaction terms *to machine precision*, not merely to solver
tolerance. Transport between phases moves moles between blocks of the state
vector without changing their identity, so it conserves the same quantity. This
is why the project can assert exact element conservation across all four phase
blocks and mean it. (Energy is a different story; see Chapter 27.)

## Units, once, so it never has to be said again

Internally the project is SI-ish and unit objects never enter the hot loop:

| quantity | unit |
|---|---|
| amount | mol |
| concentration | mol/L (M) |
| temperature | K |
| energy | J/mol |
| pressure | bar |
| volume | L |
| time | s |
| rate constant $A$ | whatever makes rate come out in mol/(L s) |

That last row is not a joke. The units of a rate constant depend on the overall
order of the reaction --- s⁻¹ for first order, L mol⁻¹ s⁻¹ for second, and
(L/mol)⁸ s⁻¹ for the ninth-order sulfur-burning declaration in Chapter 18. This
is a genuine nuisance and the project handles it by not representing units at
all below Layer 4 and being disciplined instead.
