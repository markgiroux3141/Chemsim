"""Conservation invariants -- the non-negotiable correctness guardrails.

Every generated reaction must balance atoms and charge, and a closed reactor
must conserve every element through integration. If these ever fail, the physics
is wrong regardless of how plausible the numbers look.
"""

import numpy as np

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.numerics import Integrator

INITIAL = ["CC(=O)O", "CCO", "O"]


def _element_totals(concentrations, molecules):
    """Total moles of each element in a {SMILES: conc} state."""
    totals = {}
    for smi, c in concentrations.items():
        for el, n in molecules[smi].element_counts().items():
            totals[el] = totals.get(el, 0.0) + n * c
    return totals


def test_ester_is_discovered(fischer_template, thermo):
    net = build_network(INITIAL, [fischer_template], thermo=thermo)
    assert Molecule.from_smiles("CCOC(C)=O").smiles in net.species


def test_every_reaction_balances(fischer_template, thermo):
    net = build_network(INITIAL, [fischer_template], thermo=thermo)
    assert net.reactions, "expected at least one reaction"
    for rxn in net.reactions:
        left, right = {}, {}
        for smi in rxn.reactants:
            for el, n in net.molecules[smi].element_counts().items():
                left[el] = left.get(el, 0) + n
        for smi in rxn.products:
            for el, n in net.molecules[smi].element_counts().items():
                right[el] = right.get(el, 0) + n
        assert left == right, f"{rxn.name} does not balance: {left} != {right}"


def test_closed_reactor_conserves_every_element(fischer_template, thermo):
    net = build_network(INITIAL, [fischer_template], thermo=thermo)
    sys = net.to_arrays()
    integ = Integrator(sys)

    C0 = sys.vector({"CC(=O)O": 5.0, "CCO": 5.0, "O": 0.5})
    start = _element_totals(sys.as_dict(C0), net.molecules)

    sol = integ.run(C0, T=340.0, t_span=(0.0, 3600.0))
    end = _element_totals(sys.as_dict(sol.y[:, -1]), net.molecules)

    for el in start:
        assert np.isclose(start[el], end[el], rtol=1e-4), f"{el}: {start[el]} -> {end[el]}"


def test_reversible_generates_forward_and_reverse(fischer_template, thermo):
    net = build_network(INITIAL, [fischer_template], thermo=thermo)
    names = {r.name for r in net.reactions}
    assert "fischer_esterification" in names
    assert "fischer_esterification_rev" in names
