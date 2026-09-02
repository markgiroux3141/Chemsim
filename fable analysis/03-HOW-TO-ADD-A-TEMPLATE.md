# How to add a reaction template

No document in the repo says this. This is the procedure as the code actually
enforces it today, followed by the shorter procedure once `06-WORK-ORDER.md`
task T1 (templates as data) is done.

## The fields

```python
ReactionTemplate(
    name="saponification",                       # snake_case, unique
    smarts="[CX3:1](=[O:2])[OX2:3][#6:4].[OH-:5]"
           ">>[CX3:1](=[O:2])[O-:5].[OX2H1:3][#6:4]",
    A=1.0e8,            # L/(mol s) for bimolecular, 1/s for unimolecular
    Ea=46_000.0,        # J/mol
    reversible=False,   # True derives the reverse by detailed balance (needs thermo for every species)
    phase="liquid",     # "liquid" | "gas" | "any" (any = two concrete reactions, one per phase)
    alpha=0.0,          # Evans-Polanyi transfer coefficient; 0 = fixed barrier
    orders=None,        # per-slot rate exponents; ONLY for a lumped non-elementary step; forbids reversible
    solid_catalyst=None,# a mineral_data name; gates the rate, does not enter stoichiometry
    electrons=0,        # >0 makes this an electrode reaction driven by cell_potential
    hammett_rho=0.0,    # aromatic substituent effect on the sigma-plus scale; forbids alpha
)
```

Defined at `src/chemsim/reactions/template.py:231-256`. Validation in `__post_init__`
will refuse illegal combinations with an explanatory error; read the error.

## Rules the engine will not tell you until build time

1. **Atom-map every heavy atom on both sides.** Unmapped product atoms are
   created from nothing and `_element_charge_balance` (`builder.py:317`) rejects
   the rewrite silently. Check with the balance test below.
2. **Write H₂ as `[H][H]`** with mapped atoms if the template consumes hydrogen.
   `run()` collapses explicit hydrogens afterwards (`template.py:535`).
3. **Spell an H count on product atoms whose valence changes** (`[OH1:3]`,
   `[CH:2]`). RDKit does not infer it. Products are re-parsed from canonical
   SMILES so a missing count is a wrong molecule, not a flag.
4. **A reversible template needs a price for every species it can make.**
   `build_network` drops a rewrite whose product cannot be priced and reports it
   in `ReactionNetwork.unpriced`. Run `ThermochemistryProvider().get(smiles)` on
   each expected product first (see `04-HOW-TO-ADD-A-SPECIES.md`).
5. **Irreversible is a claim.** The accepted reasons: a gas leaves the flask, the
   product is an anion nothing attacks, elimination into a large excess of the
   eliminated species. Anything else should be reversible.
6. **Do not put two channels between the same pair of species in one bundle**
   unless you have decided which one you are running. See the `alkene_hydration`
   / `alkene_dehydration` note at `synthesis.py:593-616`.
7. **Never declare a reverse rate.** There is no field for one on purpose.
8. **A homogeneous catalyst is written into both sides of the SMARTS** by
   `library._maybe_catalyse`. A heterogeneous one is `solid_catalyst=`.
9. **Gas-phase reaction between gases is `phase="gas"`**, even with a solid
   catalyst. Labelling it liquid moves it onto the wrong standard state by a
   factor of ~1e10 in K (`template.py:88-96`).

## Kinetics policy (use this instead of writing an essay)

| molecularity | A |
|---|---|
| unimolecular | 1e13 1/s |
| bimolecular, liquid | 1e8 to 1e10 L/(mol s); 1e11 is the collision limit, do not exceed |
| bimolecular, gas | 1e10 to 1e11 |
| catalysed via `_maybe_catalyse` | pass the uncatalysed A; `_kinetics` rescales by `CATALYST_REFERENCE` |

`Ea`: the midpoint of the class's literature band, in J/mol. Put the band and
its source (a NIST Kinetics record id, a review DOI, or "textbook band") in a
one-line comment. `validation/rate_ceiling.py` checks the derived reverse does
not exceed the collision limit; run it if `reversible=True`.

## Procedure today (Python function)

1. Write a constructor in `src/chemsim/reactions/synthesis.py` following
   `saponification` (`:385`). Docstring: one sentence for the transformation, one
   for reversibility, one for the barrier source. Under ten lines.
2. Export it from `src/chemsim/reactions/__init__.py` and add it to the right
   `*_chemistry()` bundle at `synthesis.py:2373+`. If the bench should see it,
   check `ui/examples.py:241 full_library()` picks up that bundle.
3. Add a row to `TEMPLATE_CLASSES` in `validation/catalog_coverage.py:433`
   mapping the catalog `reaction_class` to the template name. Without this the
   coverage report will not credit it.
4. Test, in an existing family test file or a new one under 80 lines:

```python
def test_saponification_fires_and_balances(thermo):
    tmpl = saponification()
    net = build_network(["CC(=O)OCC", "[OH-]", "[Na+]"], [tmpl], thermo=thermo)
    names = {r.name for r in net.reactions}
    assert "saponification" in names
    assert "CC(=O)[O-]" in net.species and "CCO" in net.species
    # element/charge balance is asserted by build_network; a rejected rewrite is absent, so:
    assert not net.unpriced
```

5. Run the fast checks: `ruff check`, the family test file, `python
   validation/catalog_coverage.py`, `python tools/build_playable.py`. Quote the
   new intersection number from `COVERAGE_REPORT.md`, not from memory.
6. One `CHANGELOG.md` line. No `HANDOFF.md`, no `MILESTONES.md` append.

## Procedure after T1 (templates as data)

Add one row to `data/templates/templates.psv`:

```
saponification | family | [CX3:1](=[O:2])[OX2:3][#6:4].[OH-:5]>>[CX3:1](=[O:2])[O-:5].[OX2H1:3][#6:4] | 1e8 | 46000 | no | liquid | saponification | textbook band 40-50 | 
```

Then `python tools/check_templates.py`, which parses every row, applies it to the
catalog steps carrying its class, and asserts products and balance. No Python
function, no bespoke test file.

## Debugging a template that does not fire

| symptom | cause | check |
|---|---|---|
| reaction absent, no notice | SMARTS slot does not match the reactant | `Molecule.from_smiles(s)._mol.HasSubstructMatch(tmpl.reactant_pattern(i))` per slot |
| reaction absent, `unpriced` non-empty | a product has no thermo | `ThermochemistryProvider().get(product_smiles)` |
| reaction absent, RDKit prints "Explicit valence..." | product atom H count wrong | spell `[XHn:k]` on the changed atoms |
| product is a different SMILES than expected | canonicalisation | compare `Molecule.from_smiles(expected).smiles` |
| fires on the wrong substrate too | SMARTS too loose | add `!$(...)` exclusions as `ester_hydrolysis` does |
| `ValueError` at construction | illegal field combination | read the message; it names the rule |
