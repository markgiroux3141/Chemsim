"""C7: reading a property table across a stereochemical spelling.

Every rule in ``properties/stereo_keys.py`` is pinned here, because each of them
is one line away from a silent wrong answer:

* the fallback may cross an AMBIGUITY and never a DIFFERENCE;
* the unspecified side must be answered by EXACTLY ONE record;
* and the strip must not be ``isomericSmiles=False``, which would merge
  deuterium into hydrogen.

The measurement behind all three is ``validation/stereo_keying.py``.
"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from chemsim.matter import Molecule, stereo_free_smiles       # noqa: E402
from chemsim.properties import ThermochemistryProvider        # noqa: E402
from chemsim.properties.stereo_keys import StereoFallback     # noqa: E402


def _c(smi: str) -> str:
    return Molecule.from_smiles(smi).smiles


# ---------------------------------------------------------------------------
# 1. THE STRIP
# ---------------------------------------------------------------------------
def test_the_strip_removes_stereochemistry_and_nothing_else():
    """⚠⚠ **THE OBVIOUS IMPLEMENTATION IS THE WRONG ONE AND IT FAILS SILENTLY.**
    ``Chem.MolToSmiles(mol, isomericSmiles=False)`` drops ISOTOPE labels along
    with stereochemistry: it turns ``[2H][2H]`` into ``[H][H]``. A fallback
    built on it hands deuterium hydrogen's record -- two species merged by a
    flag reached for to do something else. C7's own first probe used it and
    counted deuterium as a stereoisomer.
    """
    assert stereo_free_smiles("C[C@H](O)C(=O)O") == _c("CC(O)C(=O)O")
    assert stereo_free_smiles("O=C(O)/C=C/c1ccccc1") == _c("O=C(O)C=Cc1ccccc1")

    # The isotopes survive, and that is the whole point.
    assert stereo_free_smiles("[2H][2H]") == _c("[2H][2H]")
    assert stereo_free_smiles("[13CH4]") == _c("[13CH4]")

    # Idempotent on a spelling that names nothing.
    assert stereo_free_smiles("CCO") == _c("CCO")


def test_deuterium_is_still_a_different_species_from_hydrogen():
    """The consequence of the test above, at the provider. Both are elements, so
    both are refused -- but they must be refused as THEMSELVES, and a strip that
    merged them would quietly price heavy hydrogen as hydrogen the moment either
    got a curated entry."""
    thermo = ThermochemistryProvider()
    with pytest.raises(ValueError, match="ELEMENTAL"):
        thermo.get("[2H][2H]")
    assert _c("[2H][2H]") != _c("[H][H]")


# ---------------------------------------------------------------------------
# 2. THE TWO LIMITS, ON A TABLE BUILT FOR THE PURPOSE
# ---------------------------------------------------------------------------
def test_an_unspecified_query_takes_a_unique_record_and_refuses_an_ambiguous_one():
    """A query naming no stereochemistry is an AMBIGUITY, and exactly one record
    may resolve it. Two records may not: picking between them by dictionary
    order is how a flat butenedioic acid ends up with maleic acid's boiling
    point when it should have had fumaric's."""
    unique = StereoFallback({_c("C[C@H](O)C(=O)O"): "L"})
    assert unique.key(_c("CC(O)C(=O)O")) == _c("C[C@H](O)C(=O)O")
    assert unique.get(_c("CC(O)C(=O)O")) == "L"

    ambiguous = StereoFallback({
        _c("O=C(O)/C=C/C(=O)O"): "fumaric",
        _c("O=C(O)/C=C\\C(=O)O"): "maleic",
    })
    assert ambiguous.key(_c("O=C(O)C=CC(=O)O")) is None
    assert ambiguous.get(_c("O=C(O)C=CC(=O)O")) is None


def test_a_specified_query_takes_a_flat_record_but_never_a_different_spelling():
    """The other direction, and the limit that keeps two species two species.

    A chiral query may take the FLAT record -- an unspecified centre is an
    ambiguity the query resolves, not a contradiction. It may not take a
    differently-specified sibling: ``matter/molecule.py`` is explicit that
    stereoisomers are different species, and elaidic acid taking oleic acid's
    boiling point would be wrong by 128 K with a measurement's authority.
    """
    flat_record = StereoFallback({_c("CC(O)C(=O)O"): "generic"})
    assert flat_record.key(_c("C[C@H](O)C(=O)O")) == _c("CC(O)C(=O)O")

    sibling_only = StereoFallback({_c("C[C@H](O)C(=O)O"): "L"})
    assert sibling_only.key(_c("C[C@@H](O)C(=O)O")) is None


def test_an_exact_key_always_wins_and_is_never_overridden():
    """S6's rule: a fallback and NEVER an override. The flat spelling of
    2-butene is in ``MEASURED_PHYSICAL`` alongside both geometric isomers, so
    this is not hypothetical -- an exact hit has to short-circuit before the
    ambiguity guard ever sees it."""
    t = StereoFallback({
        _c("CC=CC"): "flat",
        _c("C/C=C/C"): "trans",
        _c("C/C=C\\C"): "cis",
    })
    assert t.key(_c("CC=CC")) == _c("CC=CC")
    assert t.get(_c("CC=CC")) == "flat"
    assert t.get(_c("C/C=C/C")) == "trans"


def test_the_fallback_can_be_switched_off_so_the_difference_is_measurable():
    """The same reason ``benson=False`` and ``measured_physical=False`` exist:
    a session that adds a tier has to be able to measure what it bought rather
    than describe it. ``validation/stereo_keying.py`` panel 5 runs both."""
    off = StereoFallback({_c("C[C@H](O)C(=O)O"): "L"}, enabled=False)
    assert off.key(_c("CC(O)C(=O)O")) is None
    assert off.key(_c("C[C@H](O)C(=O)O")) == _c("C[C@H](O)C(=O)O")


# ---------------------------------------------------------------------------
# 3. THE PROVIDER, END TO END
# ---------------------------------------------------------------------------
def test_a_value_that_arrived_through_the_fallback_says_so():
    """Provenance is not decoration in this project. "The same compound, spelled
    without its stereochemistry" is a real qualification on a measurement and a
    caller has to be able to see it."""
    thermo = ThermochemistryProvider()
    d = thermo.get(_c("C[C@H](O)C(=O)O"))
    assert "experimental formation data" in d.source
    assert "stereochemistry-free" in d.source
    assert "CC(O)C(=O)O" in d.source


def test_the_ambiguous_skeletons_still_fall_to_the_estimator():
    """⚠ The guard FIRES on real data, which is why it is not defensive
    programming. ``MEASURED_PHYSICAL`` holds glucose, mannose and galactose
    under one flat skeleton and sorbitol beside mannitol under another; a flat
    query gets Joback, exactly as it did before the fallback existed."""
    thermo = ThermochemistryProvider()
    for flat in ("OCC1OC(O)C(O)C(O)C1O", "OCC(O)C(O)C(O)C(O)CO"):
        d = thermo.get(_c(flat))
        assert "Joback" in (d.physical_source or ""), flat


def test_the_switch_reproduces_the_pre_C7_answer_for_a_template_made_species():
    """The number C7 closed, both ways round. ``alkene_hydrogenation`` emits
    flat menthol in ``menthol-route`` step 2; it used to price its boiling point
    off Joback 43 K away from the corpus row's measured one."""
    flat_menthol = _c("CC1CCC(C(C)C)C(O)C1")
    on = ThermochemistryProvider().get(flat_menthol)
    off = ThermochemistryProvider(stereo_fallback=False).get(flat_menthol)
    assert on.Tb == pytest.approx(487.15, abs=0.1)
    assert off.Tb == pytest.approx(530.35, abs=0.1)
    assert "Joback" in (off.physical_source or "")
    assert "Joback" not in (on.physical_source or "")
