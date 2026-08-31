# Layer 3: building a reaction network

## Discovery, as a fixpoint

Give `build_network` a set of starting molecules and a set of templates. It:

1. matches each template's reactant patterns against the available species;
2. applies the graph rewrite;
3. canonicalises the products, registering any that are new;
4. **iterates to a fixpoint**, so that products can themselves react.

\begin{figure}[htbp]
\centering
\begin{tikzpicture}[
  sp/.style={draw=csrule,fill=csgreenbg,rounded corners=1pt,
             font=\ttfamily\scriptsize,inner sep=1.4mm,minimum width=17mm},
  gen/.style={font=\sffamily\scriptsize,csgrey},
  ar/.style={->,>=Latex,csblue,thin}]
  \node[gen] at (-1.7,0)    {charged};
  \node[gen] at (-1.7,-1.2) {gen 1};
  \node[gen] at (-1.7,-2.4) {gen 2};

  \node[sp] (a) at (0,0)    {CC(=O)O};
  \node[sp] (b) at (2.4,0)  {CCO};
  \node[sp] (w) at (4.8,0)  {O};

  \node[sp] (e)  at (0,-1.2)   {CCOC(C)=O};
  \node[sp] (et) at (2.9,-1.2) {CCOCC};
  \node[sp] (en) at (5.5,-1.2) {C=C};

  \node[sp] (x)  at (2.9,-2.4) {\dots};

  \draw[ar] (a) -- (e); \draw[ar] (b) -- (e);
  \draw[ar] (b) -- (et);
  \draw[ar] (b) -- (en);
  \draw[ar,csred] (e) -- (x);
  \draw[ar,csred] (et) -- (x);
  \node[gen,csred,anchor=west] at (6.4,-2.4)
    {products react too --- iterate to a fixpoint};
\end{tikzpicture}
\caption{Discovery. Nothing here was enumerated in advance; every species below
the top row was produced by applying a template to one above it.}
\label{fig:discovery}
\end{figure}

Two guardrails run during this, and they have been there since the layer was
written:

- **element and charge conservation.** A template that does not balance is
  *rejected*, not silently integrated (Chapter 2).
- **determinism.** Species indices come from dict insertion order and template
  application iterates lists, never sets. A network built twice from the same
  inputs is bit-identical, including row order. Chapter 23 depends on this
  completely.

## Bounded discovery

Structural expansion enumerates every reachable species. For a polymerising feed
--- a diacid and a diol --- that is an unbounded oligomer series: correct
chemistry, fatal computation.

Two changes fix it:

- **incremental expansion.** Only combinations involving a newly-added species
  are tried. Re-running old pairs every round was quadratic waste.
- **`max_molar_mass`**, an explicit bound, with everything dropped **named in
  the log** --- and a diagnosis attached saying that a growing series usually
  means the system polymerises, which species enumeration cannot represent
  properly.

The polyester case went from 24 s with a silent truncation to 0.04 s with an
explicit report.

::: {.keypoint}
A network that silently omitted a pathway would be far more dangerous than one
that is merely incomplete, because the omission would look like a chemical
result.
:::

## The third bound, and the one that was silent

There is a third bound and for a long time it was the exception to the rule
above. `generations=n` stops expansion after *n* rounds instead of running to a
fixpoint. `max_species` reported when it bit, `max_molar_mass` reported and named
what it dropped, a mixed standard state reported --- and the generation limit
broke out of the loop with a **non-empty frontier and said nothing.**

It is the strongest of the three claims, not the weakest. The other two concern
species that were never *registered*; this one concerns species that **are in the
flask** and whose onward chemistry was never looked for. If A + B makes C and C
would go on to D, one generation shows C and never D --- an approximation that
changes the *contents* of a vessel rather than the completeness of a catalogue.

It matters because step-by-step play runs `generations=1` on every single step,
and that is not a compromise but the mechanic: *what can the things in this flask
do, once.* Measured across the full template library, five ordinary bench
reagents explored two generations deep hit a 400-species cap in twelve seconds,
while twelve reagents explored one deep cost under half a second.

So the limit now reports, in two forms:

- a **notice**, naming the count and the species left unexpanded; and
- `ReactionNetwork.unexpanded`, the same set as data, because a frontend asking
  *does this flask have more to give* needs an answer it can act on rather than a
  sentence it has to parse.

The frontier is taken on **either** exit from the expansion loop, which was a
correction to the first version of this: the two bounds compete, and at
`generations=2` the species cap bit first, so reading the frontier only on the
generation branch reported an empty one for a 400-species network that had been
truncated mid-round. Against a species cap the set is a lower bound and the cap's
notice says so --- the interrupted round left combinations untried as well.

::: {.keypoint}
A limit the player can see and lift is not an approximation; it is a choice. The
same notices are carried on the network itself, because `print` is a channel a
script reads and a windowed application does not have one.
:::

## Rate-based refinement, and why it lives at Layer 4.5

Structural discovery answers *what can form?* The question that actually matters
is *what forms in meaningful amounts?* --- and that is not a structural question
at all. It depends on concentrations, on temperature, and on how long you wait.

`chemsim/discovery/refine.py` answers it the only way it can be answered: **by
simulating.** The loop is the standard rate-based generation scheme:

1. take the current *core* species and build one generation outward;
2. integrate the core-only network from the actual feed concentrations;
3. with those concentrations, evaluate the rate of every *edge* reaction --- the
   ones that would introduce a new species;
4. promote the edge species whose formation rate clears a threshold;
5. repeat until a round promotes nothing.

Step 2 is why this module sits at Layer 4.5 rather than inside `network`:
refinement needs an integrator, and Layer 3 must not import Layer 4. Rather than
invert the dependency for one call, **the layer that needs both sits above
both.**

## Where the thermodynamics gets imposed

Build time is also where thermodynamic consistency is enforced. For every
reversible template, the reverse Arrhenius pair is derived here from the forward
pair plus the reaction thermochemistry (Chapter 6):

$$ A_{\mathrm{rev}} = A_{\mathrm{fwd}}\,e^{-\Delta S/R},
   \qquad E_{a,\mathrm{rev}} = E_{a,\mathrm{fwd}} - \Delta H, $$

with the $T^{\Delta n}$ conversion landing in the modified-Arrhenius exponent
$n$, and a floor at $E_{a,\mathrm{rev}} \ge 0$ that prints a notice.

The reverse then enters the network as **an ordinary reaction**. That is the
whole trick: Layer 4 stays a mass-action integrator with no concept of
reversibility.

## The output: `KineticArrays`

This is the clean numeric handoff --- pure numpy plus a species-name list, no
molecules, no RDKit. It is the seam a Rust kernel would sit behind.

| array | shape | meaning |
|---|---|---|
| `delta` | $(m, n)$ | stoichiometric matrix, integers |
| `order` | $(m, n)$ | rate-law exponents, one row per reaction |
| `order_solid` | $(m, n)$ | exponents on the *solid* block (a declared solid catalyst) |
| `A`, `Ea`, `n` | $(m,)$ | modified-Arrhenius parameters |
| `phase` | $(m,)$ | which block's concentrations this reaction reads |
| `species` | $(n,)$ | canonical SMILES, in index order |

`PHASE_INDEX` is `{"liquid": 0, "gas": 1}` and **raises on anything else**, with
a comment naming a solid-phase reaction as the case it was written to refuse
loudly rather than swallow.

::: {.keypoint title="That refusal has held twice, for two different reasons"}
Both times the brief said to add `PHASE_INDEX["solid"] = 2`, and both times
measurement said no:

- **a reaction inside a crystal** cannot be written as mass action at all --- the
  rate law comes out the wrong *shape*, not merely the wrong size (Chapter 21);
- **a solid catalyst** would move its gas-phase reaction onto the pure-liquid
  standard state, worth $2.6\times10^{10}$ in $K$ at 500 K (Chapter 18).

So both are *terms* rather than phases, and the two-entry index stands. A guard
that has correctly refused two different attempts to widen it is a good guard.
:::

## What `cell_potential` does

`build_network(cell_potential=...)` is the one other knob. It multiplies each
template's declared `electrons` into $nFE$ joules of electrical work, which come
off that reaction's Gibbs energy before $K$ is computed and before detailed
balance runs. A reaction whose chemistry costs less than the cell supplies then
simply *has a favourable $K$*, and everything downstream is unchanged
(Chapter 11).

## Cost, and the one engineering consequence

Building a network is not free: 0.45 s for a four-species case, longer for a
rich one. Since mixing two things in a sandbox means *building a network at
charge time*, a UI that lets a player pour freely needs that cached and bounded
or it stalls on every pour. That is noted in the project's own capability
assessment as the single engineering consequence of "the player can mix anything".
