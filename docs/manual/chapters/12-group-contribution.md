\part{Where the numbers come from}

# Estimating properties from structure

Every equation in Part I has constants in it. $\Delta H_f$, $\Delta G_f$,
$C_p(T)$, $T_b$, $T_m$, $\Delta H_{\mathrm{vap}}$, $\Delta H_{\mathrm{fus}}$,
Antoine coefficients, UNIFAC group parameters --- and there are 1,583 compounds
in this project's corpus. Measured values exist for a few hundred of them.

So the properties layer has to *estimate*, and this part is about how, and about
how much that estimate can be trusted.

::: {.keypoint title="The generalisation mechanism, twice"}
Reaction templates generalise *reactions*: one SMARTS rule covers every
substrate bearing the right functional group. Group contribution generalises
*properties*: one table of group values covers every molecule made of those
groups.

They are the same idea applied to the two halves of the problem, and together
they are why a novel molecule --- one nobody has ever tabulated, one this
simulator just invented by applying a template --- still gets a full set of
numbers.
:::

## The idea

If a molecule's energy is roughly a sum over its bonds, then it is roughly a sum
over its *parts*. Chop the molecule into a set of recognised fragments, count
them, and add up tabulated contributions:

$$ \Delta H_f \approx a_0 + \sum_k n_k\, h_k $$

where $n_k$ is how many of group $k$ the molecule has and $h_k$ is that group's
tabulated contribution.

::: {.physics}
This is a linear model, and the group values are its regression coefficients,
fitted by least squares over a training set of measured compounds. Everything
that is true of a linear regression is true here: it interpolates well inside
its training distribution, it extrapolates badly, its residuals are not
independent (a molecule with two errors of the same sign compounds them), and
its failure mode on out-of-distribution inputs is a **confident wrong number**
rather than a refusal.

Two properties are less obvious and both matter downstream. First, some
functional forms are non-linear in the group sums --- Joback's critical
temperature is $T_c = T_b\,[0.584 + 0.965\Sigma - \Sigma^2]^{-1}$ --- so errors
do not simply add. Second, and this is the killer, *contributions that appear on
both sides of a reaction cancel exactly*, which is a feature until it is a bug.
:::

## Step one: fragmentation

Before you can add group values you have to decide which groups a molecule is
made of, and that is a covering problem with genuine ambiguity: the atoms of a
carboxylic acid (`-COOH`) also look like an `-OH` next to a `C=O`.

`properties/fragmentation.py` is the shared machinery --- Joback and UNIFAC use
the same matcher with different tables --- and its algorithm is:

1. **Try groups in priority order, highest first.** Priority encodes chemical
   specificity: `-COOH` must claim its atoms before `-OH` and `>C=O` can split
   it between them, and an ester's `CH3COO` must be tried before a bare `CH3`.
2. **Each match greedily claims a disjoint set of heavy atoms.** A match
   overlapping an already-claimed atom is rejected, so every atom belongs to
   exactly one group.
3. **Verify, twice over.** Every heavy atom must be claimed, *and* the summed
   atom tally of the assigned groups --- including hydrogens, which the patterns
   never claim explicitly --- must equal the molecular formula.
4. If step 3 refuses, **search**.

::: {.keypoint title="Step 3 is the one that earns its keep"}
Group patterns are written to be readable, not airtight. A pattern intended for
an ether will happily match an alcohol's oxygen and quietly lose a hydrogen. The
formula check turns that into a loud failure instead of a plausible wrong number
--- which matters because **group contribution is at its most dangerous when it
succeeds on a molecule it does not actually cover.**
:::

Step 4 is a depth-first re-cover, and its design contains two rules worth
carrying into any similar problem:

- **The search runs only after greedy has been refused, and that ordering is
  load-bearing rather than an optimisation.** Every decomposition the module
  returns today is the greedy one; a molecule that fragments now fragments
  identically afterwards. What the search can turn into an answer is a
  *refusal*, never a *different answer*. Measured over the corpus: 20 of 1,155
  neutral organics fail greedy for exactly this reason and no other.
- **A search that runs out of budget refuses, and says which refusal it is.** "I
  did not find a cover" is not "there is no cover", and the two must not be
  reported as though they were the same statement.

## Joback

Joback and Reid (1987) is the workhorse. Given the group counts it supplies
$\Delta H_f$, $\Delta G_f$, $C_p(T)$ as a cubic, $T_b$, $T_m$, $T_c$, $P_c$,
$V_c$, $\Delta H_{\mathrm{fus}}$ and $\Delta H_{\mathrm{vap}}$ --- everything
Part I needs, from a graph.

It has two structural limits that better data cannot fix.

::: {.trap title="Joback cannot distinguish homologues, and that is exact rather than approximate"}
Group contributions are additive, so the $\mathrm{CH_3} \to \mathrm{C_2H_5}$
difference **cancels exactly** between an alcohol and the ester it makes.
Esterifying methanol and esterifying ethanol therefore came out of this project
with an *identical* gas-phase $\Delta G_{\mathrm{rxn}}$ of $-7.35$ kJ/mol.

No amount of downstream care recovers a distinction the estimator never made.
:::

The second limit is coverage: Joback has **no groups at all** for whole
functional classes --- aryl aldehydes, formamides, sulfoxides, sulfones,
anhydrides --- and no metals, silicon, boron or phosphorus. Nine such species
have curated records in this project; every other member of those classes was
unreachable.

And its accuracy is a few kJ/mol, which Chapter 4 already told you is a factor
of 2--4 in $K$. For methanol it is 17 kJ/mol --- a factor of a thousand.

## Benson

The second estimator sits above Joback and fixes both structural limits *by
construction*, because a **Benson group is a polyvalent atom together with the
types of its ligands**.

Methanol's carbon is `C-(H)3(O)`. Ethanol's are `C-(C)(H)3` and `C-(C)(H)2(O)`.
Different groups --- so the homologues cannot collapse onto each other.

Measured head to head on 82 curated ideal-gas species:

| | median $\Delta G_f$ error |
|---|---:|
| Benson | **1.6 kJ/mol** |
| Joback | 2.8 kJ/mol |

with the gains concentrated exactly where Joback is weakest: acetanilide 4.7
kJ/mol out against Joback's 89.4, a branched octane 7.7 against 30.6. On a
bench-realistic target set Benson assigns 26 of 26 against Joback's 17.

Benson refuses about 12% of species (unmapped groups, heteroaromatics, anything
under three heavy atoms), which keep Joback's estimate. So Benson improves
**accuracy** rather than coverage --- and note what it does *not* supply:
$T_b$, $T_c$, $P_c$, $V_c$. Group additivity is a statement about *formation*
quantities and says nothing about critical properties. That gap is Chapter 13.

::: {.aside title="Why Benson is not a SMARTS table"}
Joback and UNIFAC groups are overlapping substructure patterns, so something has
to arbitrate, hence the priority-ordered greedy matcher. Benson groups are not
patterns at all: **every polyvalent heavy atom contributes exactly one group**,
decided by its own element and bonding and its neighbours' types.

So there is nothing to arbitrate and no ambiguity to resolve, and expressing it
as SMARTS would need one pattern per ligand combination --- hundreds --- and
would *reintroduce* a matching ambiguity the scheme does not have. It runs off a
plain topology description instead, which is why Layer 0 gained a `topology()`
method and stayed sealed.
:::

## Four traps in the Benson data, all silent

The group values come from MIT's Reaction Mechanism Generator database, the open
machine-readable form of Benson's tabulation plus later revisions. Building
`benson_data.py` from it turned up four failure modes that are worth reading
even if you never touch this code, because each is a general shape.

::: {.trap title="1. The source mixes units inside one file"}
Entries sourced from Benson are in **kcal**/mol; later revisions are in
**kJ**/mol. `Cs-CsHHH` reads $-10.2$ and `Cs-OsHHH` reads $-42.9$ --- values
that agree to within a revision, printed a factor of 4.184 apart.

Assuming one unit throughout makes every oxygen group four times too large,
which **validates fine on alkanes** (they have no oxygen groups) and then
destroys anything with a functional group on it. The parser reads the declared
unit per entry and raises on one it does not recognise.
:::

::: {.trap title="2. Letting file order pick between duplicate entries has measured consequences"}
RMG has ~2700 entries against this project's ~750 keys: its tree carries
second-order nodes and generic bracketed alternatives that all collapse onto one
first-order key. The build picks the **most specific** candidate and prints every
collision with its spread.

Letting file order decide instead made propylamine 15.8 kJ/mol too negative (a
generic nitrogen node) and priced **every vinyl thioether as a sulfoxide** (a
generic sulfur node).
:::

::: {.trap title="3. S298 is INTRINSIC entropy and needs a symmetry correction the caller must apply"}
Benson's scheme does not intend $S_{298}$ to include symmetry; the caller must
apply $-R\ln\sigma$ for the molecule's symmetry number. Omit it and alkanes look
fine while **every symmetric molecule is wrong** --- benzene by $R\ln 12 = 20.7$
J/(mol K), which is 6 kJ/mol in $\Delta G_f$.
:::

::: {.trap title="4. A group value only means anything against the basis it was fitted with"}
This is the general form of the other three, and it is the sentence the project
records as the lesson: a fitted parameter carries its fitting context ---
units, reference state, symmetry convention, which other parameters it was
regressed alongside. Transplanting a value out of that context produces a number
that looks like data and is not.

You will see this again in Chapter 18, where a Hammett $\rho$ turns out to be
meaningless without saying which $\sigma$ scale it was fitted on.
:::

Finally, RMG gives $C_p$ at seven temperatures (300/400/500/600/800/1000/1500 K).
Those are least-squares fitted here to the $a + bT + cT^2 + dT^3$ form the rest
of the codebase uses --- the same move as fitting Lee--Kesler to Antoine form,
so that **one functional form reaches the kernel**.
