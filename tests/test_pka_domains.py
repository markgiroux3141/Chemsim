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


# ---------------------------------------------------------------------------
# T23 -- the four rows written for the shelf, and what they have to do
# ---------------------------------------------------------------------------
def test_every_t23_row_is_actually_priced_and_not_silently_skipped():
    """``ion_thermochemistry`` swallows an unanchorable pair with ``continue``.

    That is right -- there is nothing to hang the ion off -- but it means a row
    can be typed, committed and buy nothing, which is what the module docstring
    records happening to four cation rows for a whole milestone. So each of
    T23's four ions is asked of the live provider by name.
    """
    from chemsim.properties import electrolyte_provider

    provider = electrolyte_provider()
    for ion in ("O=C([O-])CC(=O)O", "O=C([O-])CC(=O)[O-]",
                "O=[N+]([O-])c1ccc([O-])cc1", "COc1cc(/C=C/CO)ccc1[O-]"):
        key = Molecule.from_smiles(ion).smiles
        assert provider.get(key) is not None, key


def test_the_malonate_dianion_is_anchored_on_the_monoanion():
    """A second proton whose acid is an ION, priced from the row before it.

    Not a restatement of the oxalate test above: that one asks whether the
    SWEEP reaches a dianion, this asks whether the TABLE can price one. The
    two malonic rows are ordered in ``_PAIRS`` for exactly this reason, and
    reversing them would leave the dianion unpriceable with both rows present.
    """
    from chemsim.properties import electrolyte

    ions = electrolyte.ion_thermochemistry(
        electrolyte.ThermochemistryProvider()
    )
    mono = ions[Molecule.from_smiles("O=C([O-])CC(=O)O").smiles]
    di = ions[Molecule.from_smiles("O=C([O-])CC(=O)[O-]").smiles]
    second = next(p for p in electrolyte.known_pairs()
                  if p.name == "malonic acid, 2nd")
    assert di.Gf == (mono.Gf + electrolyte._dG_from_pKa(second.pKa)
                     + electrolyte._solvent_correction(1))


def test_coniferyl_alcohol_is_the_phenol_rule_s_second_refutation():
    """The engine's substituent sum puts this row on the wrong SIDE of phenol.

    A rule fitted on ``hammett``'s scale is monotone in it, so a curated pair
    the sum orders backwards is one the rule gets the wrong way round rather
    than merely off. Pinned because it is the measurement the refusal in
    ``docs/design/phenol-pka-rule-refused.md`` rests on, and because it is the
    one of panel 4's three inversions that salicylate's hydrogen bond does not
    already explain.
    """
    from chemsim.reactions import hammett

    from chemsim.properties import electrolyte

    rows = {p.name: p for p in electrolyte.known_pairs()}
    coniferyl, phenol = rows["coniferyl alcohol"], rows["phenol"]
    sums = {n: hammett.survey(molecule(p.acid)._mol).sigma_sum
            for n, p in (("coniferyl", coniferyl), ("phenol", phenol))}
    assert sums["coniferyl"] < sums["phenol"]     # the scale says less acidic
    assert coniferyl.pKa < phenol.pKa             # the measurement says more
