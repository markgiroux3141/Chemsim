"""Evans-Polanyi barriers: rates that respond to thermochemistry.

Everything else here derives thermodynamics from structure. Rates were the
exception -- one template handed the same barrier to every substrate it matched,
so which of two competing products formed faster was an author's choice rather
than a prediction. ``alpha`` ties the barrier to the reaction enthalpy the
network already computes:

    Ea_i = Ea + alpha * dH_i

so within one family a more exothermic member is faster. It is still an empirical
relation with a fitted alpha; it is just no longer a free parameter per substrate.
"""

import math

import pytest

from chemsim.constants import R
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider
from chemsim.reactions import ReactionTemplate
from chemsim.reactions.thermo import reaction_deltas

ACID, WATER = "CC(=O)O", "O"
ALCOHOLS = ["CO", "CCO", "CC(C)O"]
SMARTS = (
    "[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
    ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]"
)


@pytest.fixture(scope="module")
def thermo_mod():
    return ThermochemistryProvider()


def _forward_reactions(net):
    return [r for r in net.reactions if r.name == "fischer"]


def _build(thermo, alpha):
    template = ReactionTemplate(
        name="fischer", smarts=SMARTS, A=1.0e6, Ea=50_000,
        reversible=True, alpha=alpha,
    )
    return build_network([ACID, WATER, *ALCOHOLS], [template], thermo=thermo)


def test_without_alpha_every_member_gets_the_same_barrier(thermo_mod):
    """The old behaviour, which must remain the default -- alpha = 0 is not a
    special case in the code, it just makes the correction vanish."""
    reactions = _forward_reactions(_build(thermo_mod, alpha=0.0))
    assert len(reactions) >= 3
    assert {r.Ea for r in reactions} == {50_000.0}


def test_the_barrier_tracks_the_reaction_enthalpy(thermo_mod):
    """The whole point: one template, three substrates, three different rates --
    ordered by how exothermic each one is."""
    net = _build(thermo_mod, alpha=0.5)
    rows = [
        (reaction_deltas(r, thermo_mod, net.volatility)[0] * 1000.0, r.Ea)
        for r in _forward_reactions(net)
    ]
    assert len({Ea for _, Ea in rows}) == len(rows), "barriers must differ"

    for dH, Ea in rows:
        assert Ea == pytest.approx(50_000 + 0.5 * dH, rel=1e-9)

    # More exothermic => lower barrier => faster. That ordering IS the physics.
    by_enthalpy = sorted(rows)
    assert [Ea for _, Ea in by_enthalpy] == sorted(Ea for _, Ea in by_enthalpy)


def test_the_most_exothermic_member_is_the_fastest(thermo_mod):
    """Stated as a rate rather than a barrier, which is what selectivity means."""
    net = _build(thermo_mod, alpha=0.5)
    T = 340.0
    rates = sorted(
        (
            reaction_deltas(r, thermo_mod, net.volatility)[0],
            r.A * math.exp(-r.Ea / (R * T)),
        )
        for r in _forward_reactions(net)
    )
    fastest_dH, fastest_k = rates[0]
    slowest_dH, slowest_k = rates[-1]
    assert fastest_dH < slowest_dH
    assert fastest_k > slowest_k


def test_the_reverse_barrier_follows_automatically(thermo_mod):
    """Detailed balance gives Ea_rev = Ea_fwd - dH, so with Ea_fwd = Ea + alpha*dH
    the reverse comes out as Ea - (1 - alpha)*dH: the Evans-Polanyi relation for
    the reverse direction, with transfer coefficient (1 - alpha). Nothing had to
    be written for that to be true, which is the sign it is consistent."""
    alpha = 0.4
    net = _build(thermo_mod, alpha=alpha)
    for fwd in _forward_reactions(net):
        rev = next(
            r for r in net.reactions
            if r.name == "fischer_rev"
            and sorted(r.reactants) == sorted(fwd.products)
            and sorted(r.products) == sorted(fwd.reactants)
        )
        dH = reaction_deltas(fwd, thermo_mod, net.volatility)[0] * 1000.0
        assert rev.Ea == pytest.approx(50_000 - (1.0 - alpha) * dH, rel=1e-6)


def test_a_barrier_can_never_go_negative(thermo_mod):
    """A hugely exothermic reaction with a large alpha would drive the barrier
    below zero, which is not a rate law, it is a sign error waiting to happen."""
    template = ReactionTemplate(
        name="t", smarts=SMARTS, A=1.0e6, Ea=1_000.0, alpha=1.0, reversible=False,
    )
    assert template.barrier(-500_000.0) == 0.0
    assert template.barrier(0.0) == 1_000.0
    assert template.barrier(20_000.0) == 21_000.0


def test_alpha_outside_its_physical_range_is_rejected():
    """It is a transfer coefficient -- the fraction of the reaction enthalpy the
    transition state has already felt -- so it lives in [0, 1]."""
    for bad in (-0.1, 1.5):
        with pytest.raises(ValueError, match="transfer coefficient"):
            ReactionTemplate(
                name="t", smarts=SMARTS, A=1.0, Ea=1.0, alpha=bad
            )


def test_alpha_requires_thermochemistry():
    """dH is computed, not declared, so a template that needs it must say so
    rather than silently falling back to the declared barrier."""
    template = ReactionTemplate(
        name="t", smarts=SMARTS, A=1.0e6, Ea=50_000, alpha=0.5, reversible=False,
    )
    assert template.uses_thermochemistry
    with pytest.raises(ValueError, match="ThermochemistryProvider"):
        build_network([ACID, "CCO"], [template])
