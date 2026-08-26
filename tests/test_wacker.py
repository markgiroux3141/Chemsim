"""S11 -- the Wacker process, and the first template whose catalyst is an ION.

``wacker-process`` writes ``copper-ii-ion`` on both sides of its only row, which
is ``library._maybe_catalyse``'s own case -- except that ``[Cu+2]`` is priced
from ``ion_data`` and ``thermochemistry`` refuses a charged species by name. So
the gate this template carries is not "did you add the catalyst" but "is there a
SOLVENT for it to be an ion in", and a flask built without
``electrolyte_provider()`` REFUSES rather than running slowly.

⚠⚠ AND ONE THING IN IT IS DELIBERATELY WRONG. The real Wacker rate law is ZERO
order in oxygen; this declares FIRST, because the kinetics kernel has no
availability gate and a zero-order reactant is driven negative once it runs out.
``test_the_oxygen_order_is_wrong_on_purpose_and_here_is_the_cost`` measures the
price rather than leaving it in a docstring.
"""

from __future__ import annotations

import pytest

from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties.electrolyte import (
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.reactions.synthesis import wacker_chemistry, wacker_oxidation
from chemsim.reactions.thermo import reaction_deltas
from chemsim.vessel import Vessel

WATER, ETHYLENE, O2 = "O", "C=C", "O=O"
ACETALDEHYDE, CU, CL = "CC=O", "[Cu+2]", "[Cl-]"

TIGHT = dict(rtol=1.0e-8, atol=1.0e-11)


@pytest.fixture(scope="module")
def vol():
    return VolatilityProvider()


@pytest.fixture(scope="module")
def thermo(vol):
    return electrolyte_provider(volatility=vol)


@pytest.fixture(scope="module")
def net(thermo, vol):
    return build_network(
        [WATER, ETHYLENE, O2, CU, CL],
        wacker_chemistry() + list(dissociation_templates()),
        thermo=thermo, volatility=vol,
    )


def reactor(net, T=400.0, t=600.0, cu=0.02, eth=0.20, o2=0.20):
    v = Vessel(net, volume=1.0, T=T, T_env=T, UA=1.0e6, k_vent=0.0)
    v.charge({WATER: 20.0}, phase="liquid")
    if cu:
        v.charge({CU: cu, CL: 2.0 * cu}, phase="liquid")
    v.charge({ETHYLENE: eth, O2: o2}, phase="gas")
    v.run(t, **TIGHT)
    return v


def test_a_flask_with_no_electrolyte_support_REFUSES(vol):
    """⚠ AND IT REFUSES AT THE VESSEL, NOT AT THE NETWORK, which is layering.

    ``build_network`` asks a GRAPH question and succeeds; pricing happens one
    layer down, in ``build_phase_arrays``. So the refusal names the ion and says
    what to do about it rather than reporting an empty reaction list.
    """
    neutral = build_network([WATER, ETHYLENE, O2, CU, CL], wacker_chemistry(),
                            thermo=ThermochemistryProvider(), volatility=vol)
    assert CU in neutral.species
    with pytest.raises(ValueError, match="net charge"):
        Vessel(neutral, volume=1.0, T=400.0)


def test_it_runs_and_the_copper_is_a_constant_of_the_motion(net):
    v = reactor(net)
    st = v.state()
    assert st.total(ACETALDEHYDE) > 0.19
    assert st.total(CU) == pytest.approx(0.02, rel=1e-12)
    # two carbons per ethylene, two per acetaldehyde
    assert 2 * st.total(ETHYLENE) + 2 * st.total(ACETALDEHYDE) == pytest.approx(
        0.40, rel=1e-9)
    assert not v.conservation_report()


def test_no_copper_is_no_reaction_to_solver_dust(net):
    """⚠ THE RATE IS EXACTLY ZERO; THE STATE CARRIES DUST, AND THEY ARE DIFFERENT.

    ``prod(C ** order)`` with the catalyst absent is ``0.0 ** 1.0``, which is
    exactly 0.0 -- there is no gate constant and no smoothstep involved. What
    comes back is ~1e-28 mol of acetaldehyde in a species with no source at all:
    that is BDF's linear solves on a stiff two-phase flask, seventeen decades
    under the run's own ``atol``. Asserted as a BOUND rather than as an equality,
    because an equality here would be pinning the solver rather than the physics.
    """
    st = reactor(net, cu=0.0).state()
    assert st.total(ACETALDEHYDE) < 1.0e-20
    # ...and the ethylene total is only approx, because it is summed across a
    # headspace and a liquid layer that the flask has partitioned it between.
    assert st.total(ETHYLENE) == pytest.approx(0.20, rel=1e-12)


def test_the_reactor_converts_a_real_pass_in_a_real_minute(net):
    """What bounds A: a one-stage Wacker takes 30-40% per pass in minutes.

    ⚠ A third-order rate law's pre-exponential is in L^2/(mol^2 s) and the
    collision limit is a number in L/(mol s), so the usual ceiling cannot be
    applied -- M8's unit error, documented on ``deacon_oxidation`` first.
    """
    assert 0.35 < 1.0 - reactor(net, t=60.0).state().total(ETHYLENE) / 0.20 < 0.45
    assert 1.0 - reactor(net, t=600.0).state().total(ETHYLENE) / 0.20 > 0.95


def test_the_copper_loading_is_a_first_order_knob(net):
    """⚠ AND FOR A HOMOGENEOUS CATALYST THAT IS RIGHT, not provisional.

    The site balance M10 is missing is a statement about a SURFACE. There are no
    sites to saturate in a chloride liquor, so ten times the copper really is ten
    times the rate here -- the one place this project's catalysis is on firmer
    ground than its heterogeneous templates.
    """
    a = reactor(net, t=60.0, cu=0.002).state().total(ACETALDEHYDE)
    b = reactor(net, t=60.0, cu=0.02).state().total(ACETALDEHYDE)
    assert b / a == pytest.approx(10.0, rel=0.25)     # 10x, bent by depletion


def test_the_oxygen_order_is_wrong_on_purpose_and_here_is_the_cost(net):
    """⚠⚠ THE REAL WACKER IS ZERO ORDER IN OXYGEN. This one is first.

    The reason is mechanical, not chemical: the kinetics kernel has no
    availability gate (``_avail`` serves the solid block only), so a reactant at
    order zero keeps reacting after it has run out and is driven negative.
    ``hydrogen_sulfide_combustion`` keeps one O2 slot at order 1 for the same
    reason. The price is that the rate tracks the oxygen, which a real reactor
    does not -- right at LOW oxygen, wrong at high, and MEASURED here rather than
    described.
    """
    lo = reactor(net, t=60.0, o2=0.05).state().total(ACETALDEHYDE)
    hi = reactor(net, t=60.0, o2=0.20).state().total(ACETALDEHYDE)
    assert hi / lo > 3.0                     # a real Wacker would give ~1.0


def test_the_declared_order_is_first_in_the_ALKENE_not_second(net):
    """The half of the rate law that IS right, and why it had to be declared.

    The SMARTS consumes two ethylenes to balance one O2, so mass action would
    make the reaction second order in the alkene. The measured law is first.
    """
    t = wacker_oxidation()
    assert t.orders == (1.0, 0.0, 1.0, 1.0)
    assert t.reversible is False             # a declared order may never reverse
    assert t.phase == "liquid"
    rxn = next(r for r in net.reactions if r.name == "wacker_oxidation")
    assert rxn.reactants.count(ETHYLENE) == 2
    assert rxn.orders == (1.0, 0.0, 1.0, 1.0)


def test_giving_up_the_reverse_costs_nothing(net, thermo, vol):
    """ln K is +129 at 400 K, so there is no equilibrium to lose."""
    rxn = next(r for r in net.reactions if r.name == "wacker_oxidation")
    dH, dG = reaction_deltas(rxn, thermo, vol)
    assert dH < -400.0
    dG_400 = dH - (400.0 / 298.15) * (dH - dG)
    assert dG_400 < -400.0
