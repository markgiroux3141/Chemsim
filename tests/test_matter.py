"""Layer 0 tests: molecular graph identity and structure-derived properties."""

import math

import pytest

from chemsim.matter import Molecule


def test_canonical_identity_independent_of_input_form():
    # Two SMILES for the same molecule must be one species.
    a = Molecule.from_smiles("CCO")
    b = Molecule.from_smiles("OCC")
    assert a == b
    assert hash(a) == hash(b)
    assert a.smiles == b.smiles


def test_distinct_molecules_are_not_equal():
    assert Molecule.from_smiles("CCO") != Molecule.from_smiles("CO")


def test_element_counts_include_implicit_hydrogens():
    # ethanol C2H6O
    assert Molecule.from_smiles("CCO").element_counts() == {"C": 2, "H": 6, "O": 1}


def test_molar_mass_and_formula():
    ethanol = Molecule.from_smiles("CCO")
    assert ethanol.formula == "C2H6O"
    assert math.isclose(ethanol.molar_mass, 46.07, abs_tol=0.05)


def test_charge():
    assert Molecule.from_smiles("CCO").charge == 0
    assert Molecule.from_smiles("[OH-]").charge == -1


def test_invalid_smiles_raises():
    with pytest.raises(ValueError):
        Molecule.from_smiles("this-is-not-smiles")
