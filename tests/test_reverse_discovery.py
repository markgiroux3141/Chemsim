"""T7 -- discovery runs a reversible template in both directions.

The claim under test is narrow and load-bearing: running a template backwards
finds species, and never a rate. A network seeded from the product side must be
the same network, reaction for reaction and constant for constant, as one seeded
from the reactant side -- so nothing here is a second, hand-typed reverse, which
is what ``reactions.template`` forbids and rule 9 turns on.

The second claim is the bound. Backwards is retrosynthesis unless it is
forbidden to build up, and without that an ester hydrolysis walks its acid up a
polyester ladder to the species cap.
"""

import pytest

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties.thermochemistry import ThermochemistryProvider
from chemsim.reactions.template_data import load_templates

CARBON_MONOXIDE = "[C-]#[O+]"


def _template(name):
    return next(t for t in load_templates() if t.name == name)


def _rows(net):
    """Every reaction as (key, A, Ea, phase) -- the whole of its kinetics."""
    return sorted(
        (r.key(), r.A, r.Ea, r.phase) for r in net.reactions
    )


def _build(seed, templates, **kw):
    kw.setdefault("max_species", 40)
    return build_network(seed, templates, thermo=ThermochemistryProvider(), **kw)


def test_reverse_discovery_finds_carbon_monoxide():
    """Carbon dioxide and hydrogen make carbon monoxide, which T6 could not."""
    net = _build(["O=C=O", "[H][H]"], [_template("water_gas_shift")])
    assert CARBON_MONOXIDE in net.molecules
    assert "O" in net.molecules


def test_reverse_seeded_network_is_identical_to_forward():
    """The whole argument: a search for species, not a second rate constant.

    Seed the same template from either side and the two networks must agree on
    every reaction key AND on both Arrhenius constants of each. A reversed SMARTS
    carrying kinetics of its own would pass the key check and fail this one.
    """
    tmpl = [_template("water_gas_shift")]
    forward = _build([CARBON_MONOXIDE, "O"], tmpl)
    reverse = _build(["O=C=O", "[H][H]"], tmpl)
    assert _rows(forward) == _rows(reverse)
    assert len(forward.reactions) == 2       # the pair, forward and derived


def test_reverse_discovery_may_not_build_up():
    """Aspirin and water stay small, and the bound that keeps them so reports.

    Before the bound this reached ``max_species`` by esterifying salicylic acid
    with itself, over and over: every oligomer is again an acid and an alcohol.
    """
    net = _build(
        ["CC(=O)Oc1ccccc1C(=O)O", "O"], [_template("ester_hydrolysis")],
        max_species=200,
    )
    heaviest = max(Molecule.from_smiles(s).molar_mass for s in net.molecules)
    assert len(net.molecules) < 10
    assert heaviest <= Molecule.from_smiles("CC(=O)Oc1ccccc1C(=O)O").molar_mass
    assert any("BACKWARDS" in n for n in net.notices), net.notices


def test_run_reverse_is_refused_on_an_irreversible_template():
    """An irreversible template has no reverse reaction to find."""
    tmpl = next(t for t in load_templates() if not t.reversible)
    with pytest.raises(ValueError, match="not reversible"):
        tmpl.run_reverse((Molecule.from_smiles("O"),))
