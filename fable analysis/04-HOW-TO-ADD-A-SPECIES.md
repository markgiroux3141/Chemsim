# How to add or price a species

A species needs two independent halves. The engine resolves them separately and
refuses loudly when it cannot.

| half | what it is | resolution order | where it lives |
|---|---|---|---|
| formation | ΔHf, ΔGf, S°, Cp(T) | curated > Benson > Joback; elements and ions refused unless curated | `properties/formation_data.py` (hand), `benson_data.py`, `joback_data.py` (generated), `mineral_data.py` / `element_data.py` / `ion_data.py` (generated) |
| physical | Tb, Tm, ΔHfus, Tc, Pc, Vc, Antoine | curated measured > measured Tb + Wilson-Jasperson/Fedors > Joback | `properties/physical_data.py` (generated from the catalog), `critical_data.py` |

Also, for a liquid: UNIFAC group decomposition (`unifac.py`); missing means γ = 1
and it is named in `vessel.activity_model.report()`. For an ion: a Born radius
(`dielectric.py`) and a pKa pair (`electrolyte.py`).

## Step 0: find out what is missing

```python
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
t = ThermochemistryProvider().get("CCOC(=O)C")     # raises OutsideEstimatorDomain or returns ThermoData
print(t.source, t.physical_source)
v = VolatilityProvider().get("CCOC(=O)C")
```

Or for many: `python validation/catalog_coverage.py` lists every refused catalog
species with the engine's reason. Read the reason; it names the table.

## Case A: an organic molecule that Joback can fragment

Usually nothing to do. If the catalog has a measured boiling point, `physical_data.py`
already carries it. If formation accuracy matters (it is in a reversible template
where K matters), add a curated pair:

1. Get ΔHf(g), S°(g), and if available ΔHf(l), S°(l) from `chemicals` at
   curation time (never at runtime):
   ```python
   from chemicals import CAS_from_any, Hfg, S0g, Hfl, S0l
   cas = CAS_from_any("ethyl acetate")   # not the SMILES; see memory: formula cross-check is the arbiter
   ```
2. Derive ΔGf from ΔHf and S° against CODATA element reference entropies. Do not
   transcribe a tabulated ΔGf. The pattern is at the top of `formation_data.py`.
3. Add to `IDEAL_GAS_FORMATION[smiles]` and, if you have the liquid pair,
   `LIQUID_FORMATION[smiles]`. Use the canonical SMILES
   (`Molecule.from_smiles(s).smiles`).
4. Run `tests/test_formation_data.py` (it applies the two cross-checks:
   ΔHf(g) − ΔHf(l) ≈ ΔHvap, ΔGf(l) − ΔGf(g) ≈ RT ln Psat). Carboxylic acids are
   exempt; anything else failing by more than 3 kJ/mol goes in the exclusion
   list with its residual, not in the table.

## Case B: a new compound the catalog does not know

1. Add a row to the right `data/catalog/compounds/NN-*.psv`:
   `id | name | smiles | class | role | domains | notes`. Stereo SMILES selects
   a data tier (measured tables are keyed by exact stereo); a flat SMILES is
   what a template emits. Prefer the flat one unless you have a reason.
2. `python tools/catalog.py` (structural validation).
3. `python tools/build_physical_data.py` regenerates `physical_data.py` and
   `critical_data.py` from `chemicals`. Read its dry-run report first
   (`--dry-run`): `chemicals` will return a Joback estimate labelled as data for
   species with no measurement, and the script's trap notes explain how it filters
   that.
4. Commit the PSV and the regenerated module together.

## Case C: a mineral or a metal (a lattice)

The engine holds a solid two ways with disjoint mechanics: as a **lattice**
(`mineral_data`; can calcine, roast, be reduced, catalyse; cannot dissolve) or as
**ions in the solid block** (`solubility_product` + `ion_data`; can dissolve and
precipitate; cannot roast). Nothing converts between them yet (work-order R6).
Pick the representation whose mechanics the route needs; `shelf.psv`'s `phase`
column is that declaration.

To add a lattice: `python tools/build_mineral_data.py` after adding the species
to the script's source list. It needs solid-basis Hf, S0, Cp_solid, Vm_solid. A
solid catalyst additionally requires Cp_solid and Vm_solid to be non-null
(`template.py:365`).

To add an element that boils (Hg, Zn class): `tools/build_element_data.py`. An
element with one condensed form and a measured sublimation curve goes here, not
in `mineral_data`; the difference is that this one can distil.

## Case D: an ion

Ions are back-derived from a measured pKa against this project's own water
entry, so the two standard states are consistent. Add the acid/base pair in
`properties/electrolyte.py` (`known_pairs`) with the pKa and its source, and a
Born radius in `dielectric.py` if the ion should transfer between layers. Charged
organics larger than a small hard ion are refused by the Born model on purpose;
that refusal is correct and is counted as a known coverage limit.

## What not to do

- Never hand-edit any `*_data.py` module. They carry a "regenerate" banner and a
  regenerating run will destroy your edit.
- Never mix sources within one entry (ΔHf from one compilation, S° from another).
- Never accept a `chemicals` value without checking its source list; if the list
  is `['JOBACK']` you have been handed your own estimate.
- Never key a curated table on a raw SMILES. Canonicalise first.
