"""T14 -- the plateau domain test, pinned by chemistry rather than by a count.

What this file does NOT pin is the audit's totals. A test asserting "19 plateau
pairs" would pass for ever while the corpus grew underneath it, which is the
trap T0.5 found in a generated report that asserted its own number. What is
worth pinning is the judgement: which acids the domain admits and which it
throws out, and the reason it gives for each -- because the reason is what the
follow-up item is allowed to build a rule on.
"""

from __future__ import annotations

import pathlib
import sys

import pytest
from rdkit import Chem

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "validation"))

from fatty_acid_pka import (  # noqa: E402
    as_pair,
    carboxyl_sites,
    domain,
    fragments,
    table_series,
)

from chemsim.properties import VolatilityProvider, electrolyte  # noqa: E402
from chemsim.properties.thermochemistry import ThermochemistryProvider  # noqa: E402


def classify(smiles: str) -> tuple[str, str]:
    mol = Chem.MolFromSmiles(smiles)
    sites = carboxyl_sites(mol)
    assert sites, f"no carboxyl found in {smiles}"
    return domain(mol, sites[0][0], sites[0][1], len(sites))


@pytest.mark.parametrize(
    ("smiles", "where", "reason"),
    [
        # The series the plateau is quoted from.
        ("CC(=O)O", "strict", ""),                       # acetic
        ("CCC(=O)O", "strict", ""),                      # propanoic
        ("CCCCCCCCCCCCCCCCCC(=O)O", "strict", ""),       # stearic
        (r"CCCCCCCC/C=C\CCCCCCCC(=O)O", "strict", ""),   # oleic
        # Unsaturation far from the carboxyl is inductively silent, so a
        # straight-chain unsaturated acid is still the plateau.
        (r"CC/C=C\C/C=C\C/C=C\CCCCCCCC(=O)O", "strict", ""),   # linolenic
        # A substituent nine bonds out is local-domain, not strict: the whole
        # molecule is no longer a plain chain but the three carbons that set
        # the pKa still are.
        ("CCCCCCC(O)CCCCCCCCCCC(=O)O", "local", ""),     # 12-hydroxystearic
        # And everything the domain refuses, each for its own reason.
        ("OC=O", "outside", "formyl (no carbon on the carboxyl)"),
        ("OC(=O)c1ccccc1", "outside", "aromatic ring on the carboxyl"),
        ("CC(O)C(=O)O", "outside", "heteroatom on the alpha carbon"),
        ("CC(C)C(=O)O", "outside", "alpha branch"),              # isobutyric
        ("C=CC(=O)O", "outside", "alpha unsaturation"),          # acrylic
        ("OC(=O)C(=O)O", "outside", "polyprotic (2 carboxyls)"),  # oxalic
        ("OCCC(=O)O", "outside", "heteroatom on the beta carbon"),
        ("OC(=O)C1CCCCC1", "outside", "alpha ring atom"),
    ],
)
def test_the_domain_admits_a_plain_chain_and_names_what_it_refuses(
    smiles: str, where: str, reason: str
) -> None:
    assert classify(smiles) == (where, reason)


@pytest.mark.parametrize(
    "smiles",
    [
        "NCCCC(=O)O",            # GABA, measured 4.03
        "NCCCCCC(=O)O",          # 6-aminohexanoic, measured 4.43
        "NCCCCCCCCCCC(=O)O",     # the nylon-11 unit
    ],
)
def test_an_omega_amino_acid_is_a_zwitterion_and_not_on_the_plateau(
    smiles: str,
) -> None:
    """The exclusion that the first run of this audit did not have.

    Its amine is beyond the three carbons the inductive test looks at, so a
    purely local rule put GABA on the 4.87 plateau. Its carboxyl is measured at
    4.03, because at any pH that titrates the carboxyl the amine is already
    protonated and what sits four bonds away is a full positive charge.
    """
    assert classify(smiles) == (
        "outside", "zwitterion (basic nitrogen in the molecule)"
    )


def test_an_amide_nitrogen_is_not_basic_and_does_not_trigger_the_exclusion() -> None:
    """The other half of the same rule: nylon-6,6's amide N leaves it alone."""
    where, reason = classify("CC(=O)NCCCCCC(=O)O")
    assert where == "local", reason


def test_a_carboxylate_salt_is_priced_as_its_ion_and_not_as_the_salt() -> None:
    """Keeping the counter-ion in the key invents a gap that is not there.

    ``thermochemistry`` refuses ``CC(=O)[O-].[Na+]`` as one species and prices
    the acetate on its own, so the pair a table row would carry is the
    fragment's. Before this split the audit reported sodium acetate as an
    unpriced pair, with acetate in ``_PAIRS`` since the beginning.
    """
    parts = fragments("CC(=O)[O-].[Na+]")
    assert parts == ["CC(=O)[O-]", "[Na+]"]

    thermo = ThermochemistryProvider()
    priced = set(electrolyte.ion_thermochemistry(
        thermo, volatility=VolatilityProvider(thermo)
    ))
    mol = Chem.MolFromSmiles(parts[0])
    site = carboxyl_sites(mol)[0]
    _, base = as_pair(mol, site[0], site[1])
    assert base in priced


def test_the_plateau_is_narrow_enough_for_one_value_to_stand_for_it() -> None:
    """Derived from ``_PAIRS``, so it cannot drift from the table it describes.

    If the curated rows inside the domain ever spread far apart, the argument
    for a single plateau value collapses and this fails rather than the claim
    quietly becoming false somewhere in a docstring.
    """
    series = table_series()
    flat = [pKa for carbons, pKa, _, _ in series if carbons >= 3]
    assert len(flat) >= 2
    assert max(flat) - min(flat) < 0.5
