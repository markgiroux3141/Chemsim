"""T5 -- the pKa sweep's judgements, pinned; its totals deliberately not.

A test asserting "1,030 unpriceable ions" would pass for ever while the corpus
moved underneath it, which is the trap T0.5 found in a generated report that
asserted its own number. What is worth pinning is what the instrument DECIDES:
which product of a rewrite is the ion, which class a curated pair belongs to,
and that a second dissociation is reached at all -- because each of those was
wrong in a first run and each silently changed the count rather than failing.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "validation"))

from pka_domains import classes, fixpoint, ion_of, molecule, pair_class  # noqa: E402

from chemsim.matter import Molecule  # noqa: E402


def test_a_dissociation_hands_back_hydronium_and_the_ion_is_the_other_half():
    """The first run of the sweep reached ZERO ions and raised nothing.

    Each row takes water in and hands HYDRONIUM back, so dropping the partner
    the run was GIVEN drops nothing and the tuple looks like two ions. The
    filter is the solvent in every spelling, not the molecule passed in.
    """
    rows = {t.name: (t, p) for t, p in classes()}
    tmpl, partner = rows["carboxylic_acid_dissociation"]
    assert partner.smiles == "O"
    runs = tmpl.run((Molecule.from_smiles("OC(=O)c1ccccc1"), partner))
    ions = [ion_of(products) for products in runs]
    assert [i.smiles for i in ions if i is not None] == ["O=C([O-])c1ccccc1"]


def test_water_autoionization_is_not_a_class_and_a_protonation_takes_hydronium():
    """The partner is read off the row, so a row's own direction is respected."""
    rows = dict((t.name, p.smiles) for t, p in classes())
    assert "water_autoionization" not in rows
    assert rows["amine_protonation"] == "[OH3+]"
    assert rows["phenol_dissociation"] == "O"


def test_a_pair_belongs_to_the_row_that_interconverts_it_not_to_its_ring():
    """Salicylic acid answers the phenol pattern and its 2.97 is the carboxyl's.

    Keying the class on a substructure put a carboxylic pKa into the list of
    phenol pKas the rule candidate is judged from. Pyridinium is the third
    answer and it is a LIMIT the amine row's own comment names: an aromatic
    ring nitrogen is X2, so no row reaches it and the curated pair is priced
    and unreachable.
    """
    where = pair_class(classes())
    assert where["salicylic acid"] == "carboxylic_acid_dissociation"
    assert where["salicylic acid, 2nd"] == "phenol_dissociation"
    assert where["pyridinium"] == "unreachable"


def test_the_sweep_reaches_a_second_dissociation():
    """One round would miss every dianion, which is where the gap concentrates.

    Oxalic acid is the cheapest case: ``_PAIRS`` carries its first proton and
    not its second, so a sweep that stopped at one round would report the class
    complete for it.
    """
    edges = fixpoint({"OC(=O)C(=O)O": "oxalic-acid"}, classes())
    reached = {e["ion"] for e in edges}
    assert "O=C([O-])C(=O)O" in reached
    assert "O=C([O-])C(=O)[O-]" in reached
    assert max(e["round"] for e in edges) >= 2
    assert molecule("O=C([O-])C(=O)[O-]").charge == -2
