# Layer 0: molecules in code

A short chapter, because the layer is short --- 263 lines --- and because
Chapter 1 already covered what a molecule *is*. This is about what the type
guarantees.

## `Molecule`

```python
from chemsim.matter import Molecule

m = Molecule.from_smiles("CC(=O)Oc1ccccc1C(=O)O")   # aspirin
m.smiles          # the CANONICAL form, which is the identity
m.formula         # "C9H8O4"
m.topology()      # plain data: per-atom element, charge, H count, neighbours
```

Three guarantees, and each one is used somewhere upstream.

**1. Identity is canonical SMILES.** Two `Molecule`s are equal iff their
canonical SMILES match. That makes a `Molecule` hashable and usable as a dict key
or set member --- which is *how the network builder decides whether a freshly
generated product is a new species*. Without a canonical form, applying a
template twice by different routes would register the same substance twice, and
the state vector would silently double-count.

**2. Identity distinguishes stereochemistry.** RDKit's canonical SMILES is
isomeric by default, so R/S and E/Z are different species. That matters for
steroids, chiral drugs, and anything where a template must not silently scramble
a centre.

::: {.trap title="The identity model is ahead of the reaction model"}
Templates do not yet *control* stereochemistry, so a graph rewrite can lose it.
Distinguishing what you cannot control is the safer of the two failure modes,
but it is still a mismatch --- and it costs something measurable.

**Not one template in the library spells stereochemistry on its product side**
(0 of 50). So a rewrite that makes or touches a centre emits the *flat* species,
and the flat species is not the one the corpus spells: hydrogenating isopulegol
gives `CC1CCC(C(C)C)C(O)C1` where the catalog's menthol is
`CC(C)[C@@H]1CC[C@@H](C)C[C@H]1O`. Both are real species by the rule above, and
only one of them used to reach menthol's measured boiling point --- the other
fell to Joback, 43 K away, in the middle of a route the engine runs.

The *identity* half of that mismatch stands, deliberately. The *lookup* half is
closed: a property table will now answer across an unspecified centre, under
rules that never merge two species (Chapter 17). Making templates control
stereochemistry remains future work.
:::

**3. No RDKit object escapes.** Every method returns a string, a number, a
`Molecule`, or plain data. `topology()` exists specifically so that Benson group
additivity (Chapter 12) --- which needs per-atom neighbour types rather than
substructure matching --- can be written above this layer without reaching
through it.

## Substructure matching and rewriting

Two more operations live here, both delegated to RDKit and both wrapped:

- **match a SMARTS pattern**, returning atom index tuples. Used by the
  fragmentation matcher (Joback, UNIFAC) and by template applicability tests.
- **apply a reaction SMARTS**, returning product `Molecule`s, canonicalised.

::: {.trap title="Implicit hydrogens, and the ammonia that was two different species"}
Chapter 1 mentioned that implicit hydrogens would cause exactly one serious bug.
Here it is.

SMILES normally leaves hydrogens implicit, hung off their heavy atom's valence.
But **hydrogen gas has no heavy atom** --- `[H][H]` is two explicit hydrogen
*atoms*, and any template that consumes H₂ must write it that way. Apply such a
template and the ammonia it produces comes back as `[H]N([H])[H]`, which is a
**different canonical string** from the `N` somebody charged into the flask.

Two state-vector entries for one substance, no reaction connecting them, and a
mass balance that closes perfectly while the answer is wrong. `ReactionTemplate.run`
now collapses explicit hydrogens after every rewrite. It is one line, and without
it the entire Haber process is silently broken in a way no conservation check can
see.
:::

## The one limitation that is deliberate

No tautomer resolution. Keto and enol forms are separate species. Good enough to
bootstrap; revisit when tautomers matter. It is written in the module docstring
so that nobody rediscovers it as a bug.

## Why a wrapper at all

It would be simpler to pass RDKit `Mol` objects around. The reasons not to,
in the order they bite:

1. **Serialisation.** A save file must not contain molecules, and RDKit objects
   are not serialisable. Because identity is a string, a `Scenario` (Chapter 23)
   stores SMILES text and rebuilds the network on load.
2. **Hashability.** Discovery is a fixpoint over a set of species. Sets need
   hashing.
3. **Replaceability.** The whole backend is one module's worth of calls.
4. **Determinism.** Species indices come from dict insertion order, and template
   application iterates lists, never sets --- so a network built twice from the
   same inputs is identical, including the order of its rows. Chapter 23 depends
   on that completely.
