"""Layer 1 tests: Joback fragmentation and property estimation.

Correctness strategy: (1) hard-coded expectations for a few anchor molecules,
(2) a broad cross-check against the reference `thermo` library -- if our
transcription of the group table or our fragmentation ever drifts, the
cross-check fails across many molecules at once. `thermo` is a dev/test-only
oracle; the tests skip cleanly if it isn't installed.
"""

import math

import pytest

from chemsim.matter import Molecule
from chemsim.properties import JobackError, estimate, fragment

thermo = pytest.importorskip("thermo", reason="thermo oracle not installed")
from thermo import Joback  # noqa: E402


def test_fragmentation_anchor_counts():
    assert fragment(Molecule.from_smiles("CCO")) == {1: 1, 2: 1, 20: 1}
    assert fragment(Molecule.from_smiles("CC(=O)O")) == {1: 1, 27: 1}
    assert fragment(Molecule.from_smiles("CCOC(C)=O")) == {1: 2, 2: 1, 28: 1}
    assert fragment(Molecule.from_smiles("CC(C)=O")) == {1: 2, 24: 1}


def test_estimate_matches_known_values():
    # Acetone is the canonical Joback worked example.
    r = estimate(Molecule.from_smiles("CC(C)=O"))
    assert math.isclose(r.Hf, -217.83, abs_tol=0.05)
    assert math.isclose(r.Gf, -154.54, abs_tol=0.05)
    assert math.isclose(r.Tb, 322.11, abs_tol=0.5)
    assert math.isclose(r.Cp(298.15), 74.97, abs_tol=0.5)


def test_unfragmentable_molecules_raise():
    # Water and methane have no Joback group decomposition.
    with pytest.raises(JobackError):
        fragment(Molecule.from_smiles("O"))
    with pytest.raises(JobackError):
        fragment(Molecule.from_smiles("C"))


CROSS_CHECK = [
    "CCO", "CC(=O)O", "CCOC(C)=O", "CC(C)=O", "CO", "CCOCC", "CCCCC",
    "CC(C)C", "CC(C)(C)C", "C=CC", "CC=O", "c1ccccc1", "Cc1ccccc1",
    "Oc1ccccc1", "CCN", "CC#N", "CCCl", "C1CCCCC1",
]


@pytest.mark.parametrize("smi", CROSS_CHECK)
def test_fragmentation_matches_thermo(smi):
    ours = fragment(Molecule.from_smiles(smi))
    theirs = dict(Joback(smi).counts)
    assert ours == theirs, f"{smi}: {ours} != {theirs}"


@pytest.mark.parametrize("smi", CROSS_CHECK)
def test_properties_match_thermo(smi):
    r = estimate(Molecule.from_smiles(smi))
    counts = Joback(smi).counts
    Tb = Joback.Tb(counts)
    assert math.isclose(r.Tb, Tb, abs_tol=1e-2)
    assert math.isclose(r.Tc, Joback.Tc(counts, Tb), abs_tol=1e-2)
    assert math.isclose(r.Hf * 1000.0, Joback.Hf(counts), rel_tol=1e-4)
    assert math.isclose(r.Gf * 1000.0, Joback.Gf(counts), rel_tol=1e-4)
    # Pc: ours in bar, thermo in Pa.
    assert math.isclose(r.Pc * 1e5, Joback.Pc(counts, sum(_atom_counts(smi).values())),
                        rel_tol=1e-3)


def _atom_counts(smi):
    return Molecule.from_smiles(smi).element_counts()
