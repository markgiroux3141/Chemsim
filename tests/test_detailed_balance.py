"""Detailed balance: the reverse reaction is derived, not declared.

These are the guardrails for the claim that equilibrium is *thermodynamic* rather
than an artifact of two hand-typed rate constants. Two levels of check:

    algebraic -- the derived Arrhenius pair reproduces K(T) at every temperature;
    integrated -- a closed reactor actually comes to rest at that K.

The second is the one that matters: it exercises the whole stack (template ->
network -> arrays -> BDF solver) and would catch a sign error the algebra hides.
"""

import math

import numpy as np
import pytest

from chemsim.constants import R
from chemsim.network import build_network
from chemsim.numerics import Integrator
from chemsim.reactions import (
    ConcreteReaction,
    ReactionTemplate,
    delta_n,
    detailed_balance,
    equilibrium_constant,
    equilibrium_constant_c,
)
from chemsim.reactions.thermo import modified_arrhenius

INITIAL = ["CC(=O)O", "CCO", "O"]
ESTER = "CCOC(C)=O"


def _pair(net, name="fischer_esterification"):
    fwd = next(r for r in net.reactions if r.name == name)
    rev = next(r for r in net.reactions if r.name == f"{name}_rev")
    return fwd, rev


def _k(rxn, T):
    return rxn.A * math.exp(-rxn.Ea / (R * T))


# --------------------------------------------------------------------------
# algebraic: derived parameters reproduce K(T)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("T", [280.0, 298.15, 340.0, 400.0, 450.0])
def test_derived_reverse_reproduces_K_at_every_temperature(fischer_template, thermo, T):
    net = build_network(INITIAL, [fischer_template], thermo=thermo)
    fwd, rev = _pair(net)
    ratio = _k(fwd, T) / _k(rev, T)
    assert ratio == pytest.approx(
        equilibrium_constant_c(fwd, thermo, T, net.volatility), rel=1e-9
    )


def test_reverse_parameters_match_the_closed_form(fischer_template, thermo):
    """A_rev = A_fwd exp(-dS/R) and Ea_rev = Ea_fwd - dH, spelled out."""
    net = build_network(INITIAL, [fischer_template], thermo=thermo)
    fwd, rev = _pair(net)
    db = detailed_balance(
        fwd, thermo, fischer_template.A, fischer_template.Ea,
        volatility=net.volatility,
    )

    assert delta_n(fwd) == 0  # no standard-state factor to muddy this one
    assert rev.A == pytest.approx(fischer_template.A * math.exp(-db.dS / R), rel=1e-12)
    assert rev.Ea == pytest.approx(fischer_template.Ea - db.dH, rel=1e-12)
    assert fwd.Ea == fischer_template.Ea  # forward untouched: dH < Ea, no clamp
    assert not db.barrier_raised


def test_forward_kinetics_are_passed_through_unchanged(fischer_template, thermo):
    net = build_network(INITIAL, [fischer_template], thermo=thermo)
    fwd, _ = _pair(net)
    assert fwd.A == fischer_template.A
    assert fwd.Ea == fischer_template.Ea


# --------------------------------------------------------------------------
# integrated: the reactor comes to rest at K
# --------------------------------------------------------------------------


@pytest.mark.parametrize("T", [320.0, 340.0, 380.0])
def test_integrated_equilibrium_matches_K(fischer_template, thermo, T):
    net = build_network(INITIAL, [fischer_template], thermo=thermo)
    sys = net.to_arrays()
    fwd, _ = _pair(net)

    C0 = sys.vector({"CC(=O)O": 5.0, "CCO": 5.0, "O": 0.5})
    sol = Integrator(sys).run(C0, T=T, t_span=(0.0, 1.0e5))
    final = sys.as_dict(sol.y[:, -1])

    Q = (final[ESTER] * final["O"]) / (final["CC(=O)O"] * final["CCO"])
    assert Q == pytest.approx(
        equilibrium_constant_c(fwd, thermo, T, net.volatility), rel=1e-3
    )


def test_equilibrium_is_independent_of_the_approach_direction(fischer_template, thermo):
    """Starting from pure ester + water must land on the same K -- true detailed
    balance, not a forward reaction that merely happens to stall in the right place.
    """
    net = build_network(INITIAL, [fischer_template], thermo=thermo)
    sys = net.to_arrays()
    fwd, _ = _pair(net)
    integ = Integrator(sys)
    T = 340.0

    from_left = sys.as_dict(
        integ.run(sys.vector({"CC(=O)O": 4.0, "CCO": 4.0}), T, (0.0, 1.0e5)).y[:, -1]
    )
    from_right = sys.as_dict(
        integ.run(sys.vector({ESTER: 4.0, "O": 4.0}), T, (0.0, 1.0e5)).y[:, -1]
    )

    K = equilibrium_constant_c(fwd, thermo, T, net.volatility)
    for final in (from_left, from_right):
        Q = (final[ESTER] * final["O"]) / (final["CC(=O)O"] * final["CCO"])
        assert Q == pytest.approx(K, rel=1e-3)


def test_higher_temperature_shifts_an_exothermic_equilibrium_back(
    fischer_template, thermo
):
    """Le Chatelier, but emergent: nothing tells the integrator about temperature
    dependence except the two derived Arrhenius pairs."""
    net = build_network(INITIAL, [fischer_template], thermo=thermo)
    sys = net.to_arrays()
    integ = Integrator(sys)
    C0 = sys.vector({"CC(=O)O": 5.0, "CCO": 5.0, "O": 0.5})

    yields = [
        sys.as_dict(integ.run(C0, T, (0.0, 1.0e5)).y[:, -1])[ESTER]
        for T in (300.0, 350.0, 400.0)
    ]
    assert yields[0] > yields[1] > yields[2], yields


# --------------------------------------------------------------------------
# edge cases
# --------------------------------------------------------------------------


def test_reversible_template_without_thermo_is_rejected(fischer_template):
    with pytest.raises(ValueError, match="ThermochemistryProvider"):
        build_network(INITIAL, [fischer_template])


def test_irreversible_template_needs_no_thermo():
    dehydration = ReactionTemplate(
        name="dehydration",
        smarts="[CX4:1][CX4:2][OX2H1:3]>>[C:1]=[C:2].[OH2:3]",
        A=1.0e8, Ea=90_000,
    )
    net = build_network(["CCO"], [dehydration])
    assert net.reactions
    assert all(not r.name.endswith("_rev") for r in net.reactions)


def test_negative_reverse_barrier_is_clamped_and_K_still_holds(thermo):
    """If a template declares Ea below the reaction's endothermicity, an elementary
    reverse barrier would have to be negative. We raise the forward barrier to the
    thermodynamic floor instead -- loudly -- and K(T) is still reproduced exactly.
    """
    # Hydrolysis is the endothermic direction (dH ~ +13 kJ/mol); declare a barrier
    # well below that so the clamp has to fire.
    hydrolysis = ConcreteReaction(
        "impossible", (ESTER, "O"), ("CC(=O)O", "CCO"), A=1.0e6, Ea=5_000.0
    )
    db = detailed_balance(hydrolysis, thermo, 1.0e6, 5_000.0)

    assert db.dH > 5_000.0, "test premise: forward must be endothermic beyond Ea"
    assert db.barrier_raised
    assert db.Ea_rev == 0.0
    assert db.Ea_fwd == pytest.approx(db.dH)

    for T in (300.0, 400.0):
        kf = db.A_fwd * math.exp(-db.Ea_fwd / (R * T))
        kr = db.A_rev * math.exp(-db.Ea_rev / (R * T))
        assert kf / kr == pytest.approx(
            equilibrium_constant_c(hydrolysis, thermo, T), rel=1e-9
        )


def test_clamp_is_reported_once_by_the_builder(thermo, capsys):
    """The notice must fire, and must not repeat per fixpoint generation."""
    template = ReactionTemplate(
        name="impossible_hydrolysis",
        smarts="[CX3:1](=[O:2])[OX2:3][CX4:4].[OX2H2:5]"
               ">>[CX3:1](=[O:2])[OX2H1:5].[O:3][C:4]",
        A=1.0e6, Ea=1_000.0,
        reversible=True,
    )
    build_network([ESTER, "O"], [template], thermo=thermo)
    out = capsys.readouterr().out
    assert out.count("NOTICE") == 1, out
    assert "raised to" in out


def test_standard_state_conversion_applies_only_when_moles_change(thermo):
    """K_a and K_c differ by ~RT per net mole -- ignoring it would be a ~28x error."""
    balanced = ConcreteReaction(
        "balanced", ("CC(=O)O", "CCO"), (ESTER, "O"), A=1.0, Ea=0.0
    )
    splitting = ConcreteReaction(
        "splitting", ("CCO",), ("C=C", "O"), A=1.0, Ea=0.0
    )
    T = 340.0

    assert delta_n(balanced) == 0
    assert equilibrium_constant_c(balanced, thermo, T) == pytest.approx(
        equilibrium_constant(balanced, thermo, T)
    )

    assert delta_n(splitting) == 1
    ratio = equilibrium_constant_c(splitting, thermo, T) / equilibrium_constant(
        splitting, thermo, T
    )
    assert ratio == pytest.approx(1.0 / (R / 100.0 * T), rel=1e-12)
    assert ratio < 0.05  # i.e. a factor of ~28 -- not a rounding detail


@pytest.mark.parametrize("T", [280.0, 340.0, 400.0, 500.0, 600.0])
def test_a_mole_changing_reverse_reproduces_Kc_at_every_temperature(thermo, T):
    """The delta_n != 0 case used to be exact only at a reference temperature.

    The activity->molarity conversion carries a factor T**delta_n, which is not
    Arrhenius. Folding it into A_rev at one temperature left K drifting as
    (T/T_ref)**delta_n -- about 1.3x per unit delta_n over a 100 K excursion.
    Putting it in the temperature EXPONENT instead makes it exact everywhere,
    which is what this asserts across a 320 K span.
    """
    splitting = ConcreteReaction(
        "splitting", ("CCO",), ("C=C", "O"), A=1.0e12, Ea=120_000.0
    )
    db = detailed_balance(splitting, thermo, 1.0e12, 120_000.0)
    assert db.n_rev - db.n_fwd == delta_n(splitting) == 1

    kf = modified_arrhenius(db.A_fwd, db.n_fwd, db.Ea_fwd, T)
    kr = modified_arrhenius(db.A_rev, db.n_rev, db.Ea_rev, T)
    assert kf / kr == pytest.approx(
        equilibrium_constant_c(splitting, thermo, T), rel=1e-9
    )


def test_a_balanced_reaction_needs_no_temperature_exponent(thermo, fischer_template):
    """delta_n = 0 is the common case and must stay pure Arrhenius, so the kernel
    can skip the exponent entirely."""
    net = build_network(INITIAL, [fischer_template], thermo=thermo)
    fwd, rev = _pair(net)
    assert fwd.n_exp == 0.0 and rev.n_exp == 0.0
    assert not np.any(net.to_arrays().n_exp)


def test_conservation_survives_derived_reverse_kinetics(fischer_template, thermo):
    """The derived reverse must not perturb the element balance the network enforces."""
    net = build_network(INITIAL, [fischer_template], thermo=thermo)
    sys = net.to_arrays()
    C0 = sys.vector({"CC(=O)O": 5.0, "CCO": 5.0, "O": 0.5})

    def totals(c):
        out = {}
        for smi, conc in sys.as_dict(c).items():
            for el, n in net.molecules[smi].element_counts().items():
                out[el] = out.get(el, 0.0) + n * conc
        return out

    start = totals(C0)
    end = totals(Integrator(sys).run(C0, T=340.0, t_span=(0.0, 1.0e5)).y[:, -1])
    for el in start:
        assert np.isclose(start[el], end[el], rtol=1e-4), f"{el}"
