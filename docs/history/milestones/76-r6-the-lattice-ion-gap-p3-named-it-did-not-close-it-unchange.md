## R6 -- THE LATTICE/ION GAP  *(P3 named it, did not close it -- unchanged)*

A solid is held two incompatible ways and nothing converts between them:

    the LATTICE as one species    calcination, roasting, gas-solid reduction
    its IONS in the solid block   dissolution and precipitation via a Ksp

Measured, 0.5 mol into 30 mol of water at 298 K for 600 s: **rock salt as ions
dissolves completely; rock salt as its lattice sits there for ever.** So
`shelf.psv` chooses per row, and on **six rows** the choice costs the row its
other mechanic -- calcite, covellite, galena, sphalerite, cinnabar and green
vitriol can be roasted and cannot be dissolved by anything. **Limestone in acid
does nothing.** `validation/shelf.py` panel 2 and `tools/build_shelf.py`'s
docstring carry the measurement and the rule.

⚠ It is not obviously small: a lattice and its ions are different species with
different standard states, and the conversion is the dissolution law
`mineral_data` refuses for a lattice **with reason** (the fusion law is 407x
wrong for NaCl and 11x wrong for CaCO3, in opposite directions). What is
probably right is a term consuming the lattice and producing its ions in the
solid block, priced from the same Ksp `PrecipitationArrays` already uses -- read
`properties/solubility_product.py` and `vessel/vessel.py`'s
`build_precipitation_arrays` before costing it.
