\part{Chemistry from a standing start}

# Matter, and why a molecule is a graph

## Atoms

An atom is a nucleus --- protons and neutrons, carrying essentially all the mass
--- surrounded by electrons. The number of protons, $Z$, is the *element*:
$Z=1$ is hydrogen, $Z=6$ carbon, $Z=8$ oxygen, $Z=26$ iron. Chemistry is almost
entirely about the electrons; the nucleus participates only by setting $Z$ and
by being heavy enough that we may treat it as stationary while electrons move
(the Born--Oppenheimer approximation, which is why molecular *structure* is a
meaningful idea at all).

Electrons occupy orbitals of increasing energy. The ones in the outermost
occupied shell --- the **valence** electrons --- are the ones close enough to
another atom's valence electrons to matter. The energetics work out such that an
atom is unusually stable when its valence shell is full: two electrons for
hydrogen, eight for most of the second row. This is the "octet rule", and while
it is a rule of thumb rather than a law, it is a very good one for the light
elements that make up most of organic chemistry.

## Bonds

Two atoms that each need an electron can share a pair, and both then count it
towards a full shell. That shared pair is a **covalent bond**. It is a genuine
energy minimum: the potential energy of the two-atom system, plotted against
their separation, has a well of depth typically 300--500 kJ/mol and a minimum at
around $10^{-10}$ m.

::: {.physics}
A bond is a bound state. Breaking one costs its well depth; making one releases
it. Almost all of chemical energetics is bookkeeping over which bonds were
broken and which were made, and this is exactly why the *group contribution*
methods of Part II work at all: if a molecule's energy is roughly a sum over
its bonds, then it is roughly a sum over its parts.
:::

An atom's **valence** is how many bonds it wants: hydrogen 1, oxygen 2, nitrogen
3, carbon 4. Two atoms can share two pairs (a *double bond*) or three (a
*triple bond*). Bond *order* is that count, and higher order means shorter and
stronger.

A special case that matters constantly: in a ring of six carbons with
alternating single and double bonds --- benzene --- the electrons are not
localised into three double bonds at all. They are spread over the whole ring,
and the ring is about 150 kJ/mol more stable than the alternating structure
predicts. This is **aromaticity**. It is why benzene rings survive conditions
that destroy almost anything else, and why the whole of Chapter 18's Hammett
machinery exists.

## So: a molecule is a graph

Put those together. A molecule is:

- a set of atoms, each labelled with its element, its charge, and how many
  hydrogens hang off it;
- a set of bonds between them, each labelled with an order.

That is a **labelled undirected graph**. Not "can be modelled as" --- the
correspondence is exact for the purposes of everything in this project. Two
molecules are the same substance if and only if their graphs are isomorphic
with labels preserved.

::: {.keypoint}
The single most consequential representational decision in this project is that
a molecule is a graph and a reaction is a graph rewrite. Everything downstream
--- that reactions generalise across substrates, that products can be
*discovered* rather than enumerated, that properties can be estimated from
structure --- follows from it.
:::

## SMILES: writing a graph on one line

Graphs are awkward to type. **SMILES** (Simplified Molecular Input Line Entry
System) is a compact linear notation for exactly this graph.

The rules you need to read this manual:

| SMILES | means |
|---|---|
| `C` | a carbon, with hydrogens filled in to satisfy valence: methane, CH₄ |
| `CC` | two bonded carbons, each filled with hydrogens: ethane, C₂H₆ |
| `CCO` | carbon--carbon--oxygen: ethanol |
| `O` | one oxygen with two implicit hydrogens: water |
| `C=C` | a double bond: ethene |
| `C#N` | a triple bond |
| `c1ccccc1` | six aromatic carbons in a ring: benzene (lower case = aromatic) |
| `CC(=O)O` | acetic acid: parentheses are branches |
| `CC(=O)OCC` | ethyl acetate |
| `[Na+]` | an explicit atom with a charge |
| `[O-2]` | oxide ion |
| `OC(=O)c1ccccc1` | benzoic acid |

Hydrogens are usually implicit, which is a convenience that will cause exactly
one serious bug later (Chapter 18).

The important property is that SMILES is *canonicalisable*: a given graph has
many valid SMILES strings, but a canonicalisation algorithm maps all of them to
one. This project uses the canonical form as a species' identity, which is why
`chemsim.matter.Molecule` compares equal iff canonical SMILES match, and why a
`Molecule` can be a dictionary key.

## SMARTS: writing a *pattern* over graphs

SMILES describes one molecule. **SMARTS** describes a *class* of substructures
--- it is to SMILES roughly what a regular expression is to a string.

`[CX4;!H0:1][OX2H1:2]` is a SMARTS pattern from this project's oxidation
template, and it reads:

- `[CX4...]` --- a carbon with four connections (i.e. saturated),
- `;!H0` --- which does *not* have zero hydrogens (so it has at least one),
- `:1` --- call this atom number 1,
- `[OX2H1:2]` --- bonded to an oxygen with two connections and one hydrogen
  (i.e. an alcohol's `-OH`), call it atom 2.

That single pattern is a complete selectivity model for a family of reactions,
and the project's notes say so explicitly: it matches a primary alcohol and a
secondary one, it *refuses* a tertiary alcohol (no hydrogen on the carbon to
lose), and on glycerol it matches at two different sites and therefore produces
two different products from one rule. None of that was enumerated. It follows
from the pattern.

::: {.keypoint}
Reaction *selectivity* --- which product forms, and which substrates a rule
applies to --- is encoded as SMARTS specificity. That is where the curation
effort in this project goes, and writing a pattern carelessly is the main way to
get a confidently wrong answer.
:::

## Isomers, and three kinds of sameness

Two molecules can have identical formulas and be different substances.

**Structural isomers** differ in connectivity: `CCO` (ethanol, a drinkable
liquid boiling at 351 K) and `COC` (dimethyl ether, a gas) are both C₂H₆O. The
graphs are not isomorphic, so they are different species and this project
handles them correctly by construction.

**Stereoisomers** have the same connectivity but a different arrangement in
space: a carbon with four different groups on it comes in two mirror-image
forms, and a double bond can have its substituents on the same side (*cis*/Z) or
opposite sides (*trans*/E). This project *does* distinguish them --- RDKit's
canonical SMILES is isomeric by default, so `C/C=C/C` and `C/C=C\C` are
different state-vector entries.

::: {.trap}
The identity model is *ahead of* the reaction model here, and the project says
so in `matter/molecule.py`: templates do not yet control stereochemistry, so a
graph rewrite can silently scramble a stereocentre it was not thinking about.
Distinguishing things you cannot control is the safer of the two failure modes,
but it is still a mismatch.

There is a measured consequence in the corpus. A sugar can be written as a
six-membered ring (*pyranose*) or a five-membered one (*furanose*), and the
catalog spelled glucose one way and fructose the other. The two are genuinely
interconvertible in reality; to the graph model they are unrelated species, and
the isomerisation between them was priced at $K = 4.8\times10^{-8}$ --- a
confident number describing the wrong question.
:::

**Tautomers** are the third kind, and this project does not handle them: they
interconvert by moving a hydrogen and a double bond, fast enough that in
practice you have a mixture, but they are distinct graphs. Keto and enol forms
are separate species here. This is recorded as a known limitation.

## Where this lives in the code

`src/chemsim/matter/molecule.py`, all 263 lines of it, and nothing above it in
the stack imports RDKit. That is the project's **first inversion boundary**:
parsing, canonicalisation, substructure matching and template application are
all RDKit calls, and they all happen inside this one module, so the
cheminformatics backend is replaceable without touching anything else.
