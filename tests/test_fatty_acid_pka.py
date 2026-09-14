"""T14/T18 -- the plateau domain, pinned by chemistry rather than by a count.

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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "validation"))

from fatty_acid_pka import fragments  # noqa: E402

from chemsim.matter import Molecule  # noqa: E402
from chemsim.network import build_network  # noqa: E402
from chemsim.properties import VolatilityProvider, electrolyte  # noqa: E402
from chemsim.properties.carboxylic_pka import (  # noqa: E402
    as_pair,
    carboxyl_sites,
    domain,
    plateau,
)
from chemsim.properties.electrolyte import PLATEAU_RULE, electrolyte_provider  # noqa: E402
from chemsim.properties.thermochemistry import (  # noqa: E402
    ThermochemistryProvider,
    UnpricedIon,
)
from chemsim.ui.examples import full_library  # noqa: E402


def classify(smiles: str) -> tuple[str, str]:
    mol = Molecule.from_smiles(smiles)
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
    mol = Molecule.from_smiles(parts[0])
    site = carboxyl_sites(mol)[0]
    _, base = as_pair(mol, site[0], site[1])
    assert base in priced


def test_the_plateau_is_narrow_enough_for_one_value_to_stand_for_it() -> None:
    """Derived from ``_PAIRS``, so it cannot drift from the table it describes.

    If the curated rows inside the domain ever spread far apart, the argument
    for a single plateau value collapses and this fails rather than the claim
    quietly becoming false somewhere in a docstring.
    """
    level = plateau(electrolyte.known_pairs())
    assert level is not None
    assert level.n >= 2
    assert level.width < 0.5
    assert level.low <= level.pKa <= level.high


# ---------------------------------------------------------------------------
# T18 -- the rule in the engine, not only in the audit
# ---------------------------------------------------------------------------

def test_an_acid_inside_the_domain_prices_with_no_hand_typed_row() -> None:
    """The whole point of the item: a stearate, and nothing was curated for it.

    Stearate is NOT in ``_PAIRS`` and never will be -- T14 counted 243 of the
    270 in-domain pairs as oligomers of one self-esterifying acid, a series with
    no last member. So the test is in two halves: the table does not carry it,
    and the provider prices it anyway.
    """
    stearate = "CCCCCCCCCCCCCCCCCC(=O)[O-]"
    assert stearate not in {p.base for p in electrolyte.known_pairs()}

    data = electrolyte_provider().get(stearate)
    assert PLATEAU_RULE in data.source
    # The derived record says which three carbons decided it, because a derived
    # pKa that reads like a measured one is the failure rule 10 exists to stop.
    assert "alpha/beta/gamma" in data.source


def test_the_rule_is_consulted_only_where_the_table_misses() -> None:
    """A curated measurement is never overridden by a generalisation of itself.

    Acetate is inside the domain AND in ``_PAIRS`` at 4.76, which is the
    shoulder of the plateau rather than the plateau. If the rule ran first it
    would quietly move acetic acid by two tenths of a pKa unit.
    """
    data = electrolyte_provider().get("CC(=O)[O-]")
    assert PLATEAU_RULE not in data.source
    assert "4.76" in data.source


@pytest.mark.parametrize(
    "smiles",
    [
        "NCCCC(=O)[O-]",          # GABA: a zwitterion, measured 4.03
        "[O-]C(=O)CCC(=O)O",      # succinate: polyprotic, and 4.21 not 4.9
        "CC(C)C(=O)[O-]",         # isobutyrate: alpha branch
        "[O-]C(=O)CCCCl",         # 4-chlorobutanoate: a gamma heteroatom, 4.5
        "OCCC(=O)[O-]",           # 3-hydroxypropanoate: a beta heteroatom
    ],
)
def test_an_acid_outside_the_domain_is_still_refused(smiles: str) -> None:
    """The refusal is the rule's other half and it has to survive.

    None of these is in ``_PAIRS`` -- benzoate and lactate ARE, so they would
    have tested the table and not the rule -- and each is a measurably
    different acid. A rule that priced them at the plateau would be inventing a
    number, which is worse than the ``UnpricedIon`` the builder already knows
    how to report.

    T23 had to fix the guard below and then the witness it guarded. Malonate
    was the polyprotic case here, written ``[O-]C(=O)CC(=O)O`` while ``_PAIRS``
    canonicalises to ``O=C([O-])CC(=O)O`` -- so when T23 curated malonic acid
    the raw string comparison still said the witness was outside the table
    while the provider, which canonicalises, priced it. The guard compared two
    spellings of one molecule; it now compares molecules, and succinate is the
    polyprotic witness instead.
    """
    c = Molecule.from_smiles
    assert c(smiles).smiles not in {c(q.base).smiles
                                    for q in electrolyte.known_pairs()}
    with pytest.raises(UnpricedIon):
        electrolyte_provider().get(smiles)


def test_the_rule_reports_itself_through_the_builder_notices() -> None:
    """Rule 10: an approximation touching matter is visible or it is not allowed.

    The record's ``source`` is not enough on its own -- nothing shows it to the
    player. ``build_network`` carries the claim to ``ReactionNetwork.notices``,
    which is what ``Snapshot.notices`` renders.
    """
    thermo = electrolyte_provider()
    net = build_network(
        ["CCCCCCCCCCCCCCCCCC(=O)O", "O"], full_library(), thermo=thermo,
        volatility=VolatilityProvider(thermo), max_species=60,
    )
    said = [n for n in net.notices if PLATEAU_RULE in n]
    assert len(said) == 1
    assert "CCCCCCCCCCCCCCCCCC(=O)[O-]" in said[0]
    assert "unbranched saturated CH2" in said[0]


def test_the_rule_is_what_lets_the_acid_dissociate_at_all() -> None:
    """The measurement, rather than the mechanism: what the rule bought.

    Stearic acid in water builds 12 species and 4 reactions with the rule off --
    its own dissociation is dropped, because a reversible template whose reverse
    rate cannot be derived is dropped in both directions -- and 21 of each with
    it on. This pins the DIRECTION and the refusal, not the counts, which move
    whenever the library does.
    """
    charge = ["CCCCCCCCCCCCCCCCCC(=O)O", "O"]
    lib = full_library()
    off = electrolyte_provider(plateau_rule=False)
    without = build_network(charge, lib, thermo=off,
                            volatility=VolatilityProvider(off), max_species=60)
    on = electrolyte_provider()
    with_rule = build_network(charge, lib, thermo=on,
                              volatility=VolatilityProvider(on), max_species=60)

    assert "CCCCCCCCCCCCCCCCCC(=O)[O-]" in without.unpriced
    assert not with_rule.unpriced
    assert len(with_rule.reactions) > len(without.reactions)
