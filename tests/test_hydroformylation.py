"""S11 -- the oxo process: two templates that COMPETE, and a selectivity.

The first reaction class in this project covered by a template PAIR whose members
race rather than chain. The catalog's two ``hydroformylation`` rows are one
reaction with two regiochemistries -- ``butyraldehyde`` and ``isobutyraldehyde``
from the same reactants, the second row's condition column reading literally
"same reactor, n:iso selectivity" -- so the class cannot be covered by one
template and its credit cannot be read off a coverage table.

⚠⚠ WHAT MAKES IT WORTH MORE THAN +1: **the thermodynamics point the wrong way.**
The branched aldehyde is 9.35 kJ/mol more exothermic and wins 2.33 to 1 at
equilibrium; the real reactor makes the linear one about four to one. So this is
a KINETICALLY controlled process running against its own thermodynamics, and
three separate things fall out of it that nobody declared -- see
``validation/hydroformylation.py``.

⚠ ONE NUMBER IS FITTED: a 4.8 kJ/mol barrier difference, set to give n:iso = 4.0
at the catalog row's own 420 K. Every test below is about something that is NOT
fitted.
"""

from __future__ import annotations

import math

import pytest

from chemsim.constants import R
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties.mineral_data import MINERALS
from chemsim.reactions.synthesis import (
    hydroformylation_branched,
    hydroformylation_linear,
    oxo_chemistry,
)
from chemsim.reactions.template import ReactionTemplate
from chemsim.reactions.thermo import reaction_deltas
from chemsim.vessel import Vessel

PROPENE, CO, H2 = "C=CC", "[C-]#[O+]", "[H][H]"
NBAL, IBAL = "CCCC=O", "CC(C)C=O"
ETHYLENE, PROPANAL = "C=C", "CCC=O"
COBALT = MINERALS["cobalt"].lattice

TIGHT = dict(rtol=1.0e-8, atol=1.0e-11)


@pytest.fixture(scope="module")
def providers():
    return ThermochemistryProvider(), VolatilityProvider()


@pytest.fixture(scope="module")
def net(providers):
    thermo, vol = providers
    return build_network([PROPENE, CO, H2], oxo_chemistry(),
                         thermo=thermo, volatility=vol)


def charge_for(P_bar: float, T: float, volume: float = 1.0) -> float:
    """Moles of EACH of the three gases that put a flask at P_bar."""
    return P_bar * volume / (3.0 * 0.083145 * T)


def reactor(net, T: float, n: float, t: float = 3600.0, cobalt: float = 0.1):
    v = Vessel(net, volume=1.0, T=T, T_env=T, UA=1.0e6, k_vent=0.0)
    v.charge({PROPENE: n, CO: n, H2: n}, phase="gas")
    if cobalt:
        v.charge({COBALT: cobalt}, phase="solid")
    v.run(t, **TIGHT)
    return v


# ---------------------------------------------------------------------------
# the credit, RUN
# ---------------------------------------------------------------------------

def test_one_charge_makes_BOTH_catalog_rows(net):
    """The class credit, verified the S1 way: in a Vessel, not in a table.

    ⚠ A template making only the linear aldehyde would read IDENTICALLY in
    ``catalog_coverage``. That is the false credit S1 is the standing example of,
    and this class has exactly its shape.
    """
    n = charge_for(200.0, 420.0)
    v = reactor(net, 420.0, n)
    st = v.state()
    assert st.total(NBAL) > 1.0
    assert st.total(IBAL) > 0.25
    assert not v.conservation_report()
    # carbon closure: 3 per propene, 4 per aldehyde, 1 per CO
    carbon = (3 * st.total(PROPENE) + 4 * st.total(NBAL) + 4 * st.total(IBAL)
              + st.total(CO))
    assert carbon == pytest.approx(4 * n, rel=1e-9)


def test_the_reactor_reaches_its_real_conversion_in_its_real_hour(net):
    """What bounds A, since a third-order pre-exponential has no collision limit.

    ⚠ The rate law is third order in the gas and first order in the cobalt, so
    ``A`` is in L^3/(mol^3 s) and comparing it to a number in L/(mol s) is the
    category error M8 named. What bounds it is the REACTOR: a real cobalt oxo
    plant runs at 420 K and 200 bar with a residence time of tens of minutes to a
    couple of hours, and converts most of its alkene.
    """
    n = charge_for(200.0, 420.0)
    st = reactor(net, 420.0, n).state()
    assert 0.85 < 1.0 - st.total(PROPENE) / n < 0.98


def test_no_cobalt_is_EXACTLY_no_reaction(net):
    """The gate, and it is exact rather than nearly exact."""
    n = charge_for(200.0, 420.0)
    st = reactor(net, 420.0, n, cobalt=0.0).state()
    assert st.total(NBAL) == 0.0
    assert st.total(IBAL) == 0.0
    assert st.total(PROPENE) == n

    # ⚠ IT WAS NOT EXACT UNTIL PROPENE HAD A MEASURED BOILING POINT, AND THE
    # GATE WAS NEVER THE REASON. With Joback's Tb the engine put 0.91 mol of
    # "liquid propene" into a flask 55 K above propene's real critical
    # temperature, and the extra stiff phase left 2.8e-24 mol of butanal in a
    # species with no source at all -- dust from the linear solves, not a leak.
    # ``nS ** 1`` was exactly 0.0 the whole time. See S11 in docs/history/MILESTONES.md.


# ---------------------------------------------------------------------------
# the selectivity: one fitted number, and what is NOT fitted
# ---------------------------------------------------------------------------

def test_the_selectivity_IS_the_barrier_difference_and_nothing_else(net):
    """n:iso in the flask equals ``exp(dEa/RT)`` to three figures at 420 K.

    Both templates carry the same ``A``, so the ratio is one exponential. This is
    the fitted number CHECKED rather than merely declared: if the pair ever
    stopped sharing a pre-exponential, or if Evans-Polanyi were switched on, this
    identity would break.
    """
    n = charge_for(200.0, 420.0)
    st = reactor(net, 420.0, n).state()
    ratio = st.total(NBAL) / st.total(IBAL)
    assert ratio == pytest.approx(math.exp(4800.0 / (R * 420.0)), rel=2e-3)
    assert ratio == pytest.approx(4.0, rel=0.02)


def test_the_selectivity_falls_when_the_reactor_is_heated(net):
    """NOT fitted: only the value at 420 K is. The curve is a consequence."""
    n = charge_for(200.0, 420.0)
    ratios = []
    for T in (380.0, 420.0, 450.0):
        st = reactor(net, T, n).state()
        ratios.append(st.total(NBAL) / st.total(IBAL))
    assert ratios[0] > ratios[1] > ratios[2]
    assert ratios[0] == pytest.approx(4.57, rel=0.02)
    assert ratios[2] == pytest.approx(3.54, rel=0.02)


def test_above_450_K_the_REVERSE_beats_the_barrier_difference(net):
    """⚠⚠ THE COLLAPSE IS STEEPER THAN ARRHENIUS, AND THAT IS THE FINDING.

    Up to ~450 K the flask tracks ``exp(dEa/RT)``. At 520 K the pure kinetic
    ratio would still be 3.03; the flask reads 0.76, because the two reverse
    reactions are now fast enough to matter inside the reactor's own hour and the
    branched product -- the MORE STABLE one -- starts winning. Nothing declares a
    maximum operating temperature; a real cobalt oxo reactor sits at 410-450 K.
    """
    n = charge_for(200.0, 420.0)
    st = reactor(net, 520.0, n).state()
    ratio = st.total(NBAL) / st.total(IBAL)
    assert ratio == pytest.approx(0.76, rel=0.05)
    assert ratio < math.exp(4800.0 / (R * 520.0)) / 3.0


# ---------------------------------------------------------------------------
# the thermodynamics, which point the OTHER WAY
# ---------------------------------------------------------------------------

def test_the_branched_product_is_the_MORE_STABLE_one(net, providers):
    """The whole reason this pair is interesting rather than merely two rows."""
    thermo, vol = providers
    lin = next(r for r in net.reactions if r.name == "hydroformylation_linear")
    bra = next(r for r in net.reactions if r.name == "hydroformylation_branched")
    dH_n, dG_n = reaction_deltas(lin, thermo, vol)
    dH_i, dG_i = reaction_deltas(bra, thermo, vol)
    assert dH_i < dH_n                       # branched more exothermic
    assert dG_i < dG_n                       # and more favourable
    assert dH_n - dH_i == pytest.approx(9.35, abs=0.05)
    assert dG_n - dG_i == pytest.approx(4.82, abs=0.05)


def test_the_flask_walks_to_the_THERMODYNAMIC_ratio_if_left_alone(net, providers):
    """⚠⚠ KINETIC CONTROL AT THE REACTOR'S TIMESCALE, THERMODYNAMIC ELEVEN YEARS ON.

    Nothing declares a crossover. The two templates share a reactant and detailed
    balance supplies both reverses at ``Ea - dH``, so the kinetic product is eaten
    by the stable one through propene. The limit is ``K(n)/K(iso)``.
    """
    thermo, vol = providers
    lin = next(r for r in net.reactions if r.name == "hydroformylation_linear")
    bra = next(r for r in net.reactions if r.name == "hydroformylation_branched")

    def lnK(rxn, T):
        dH, dG = reaction_deltas(rxn, thermo, vol)
        return -(dH - (T / 298.15) * (dH - dG)) * 1000.0 / (R * T)

    limit = math.exp(lnK(lin, 420.0) - lnK(bra, 420.0))
    assert limit == pytest.approx(0.4283, rel=1e-3)

    n = charge_for(200.0, 420.0)
    st = reactor(net, 420.0, n, t=1.0e10).state()
    # ⚠⚠ AGAINST THE **GAS** RATIO, BECAUSE K IS A STATEMENT ABOUT PARTIAL
    # PRESSURES. At 200 bar and 420 K this reactor holds ~1.7 mol of LIQUID
    # product, and butanal (Tb 347.95 K) is the less volatile of the two -- so
    # the INVENTORY ratio settles at 0.513 while the headspace lands on K(n)/
    # K(iso) to four figures. A real cobalt oxo reactor is a liquid-phase
    # process for exactly this reason.
    assert st.n_gas[NBAL] / st.n_gas[IBAL] == pytest.approx(limit, rel=2e-3)
    assert st.total(NBAL) / st.total(IBAL) == pytest.approx(0.513, rel=0.02)
    # ...and an hour in it is still the KINETIC ratio, seven times the other one
    st1 = reactor(net, 420.0, n).state()
    assert st1.total(NBAL) / st1.total(IBAL) > 7 * limit


# ---------------------------------------------------------------------------
# reversibility: measured, not argued
# ---------------------------------------------------------------------------

def irreversible_pair():
    lin, bra = hydroformylation_linear(), hydroformylation_branched()
    return [
        ReactionTemplate(name=t.name, smarts=t.smarts, A=t.A, Ea=t.Ea,
                         phase="gas", reversible=False, solid_catalyst="cobalt")
        for t in (lin, bra)
    ]


def test_irreversible_would_report_a_conversion_the_equilibrium_forbids(providers):
    """⚠⚠ WHY ``reversible=True`` HERE AND NOT IN ``alkene_hydrogenation``.

    Three moles of gas become one, so this equilibrium turns over on heating: ln
    K(linear) is +2.31 at 420 K and -7.46 at 600. At 600 K and 1 bar an
    irreversible pair reports 78% conversion where the reversible one reports
    0.01%. That is a factor of ~6000 on a flask a player can build, and it is
    also why the process is run at 200 bar -- the same flask at 200 bar converts
    53% with the reverse fully on.
    """
    thermo, vol = providers
    rev = build_network([PROPENE, CO, H2], oxo_chemistry(),
                        thermo=thermo, volatility=vol)
    irr = build_network([PROPENE, CO, H2], irreversible_pair(),
                        thermo=thermo, volatility=vol)
    n = charge_for(1.0, 600.0)
    c_rev = 1.0 - reactor(rev, 600.0, n).state().total(PROPENE) / n
    c_irr = 1.0 - reactor(irr, 600.0, n).state().total(PROPENE) / n
    assert c_irr > 0.70
    assert c_rev < 0.001
    assert c_irr / c_rev > 1000.0

    n200 = charge_for(200.0, 600.0)
    c_hi = 1.0 - reactor(rev, 600.0, n200).state().total(PROPENE) / n200
    assert 0.45 < c_hi < 0.65               # pressure buys back what heat cost


# ---------------------------------------------------------------------------
# the patterns themselves
# ---------------------------------------------------------------------------

def test_ethylene_has_no_regiochemistry_to_get_wrong(providers):
    """Both templates collapse onto propanal, which is the correct answer.

    ``[CX3H2:1]`` requires the formyl-bearing carbon to carry two hydrogens. In a
    1-alkene that picks the terminal end; in ethylene BOTH ends qualify, so the
    linear and branched templates become the same reaction -- and hydroformylating
    ethylene really does have one product.
    """
    thermo, vol = providers
    net = build_network([ETHYLENE, CO, H2], oxo_chemistry(),
                        thermo=thermo, volatility=vol)
    assert PROPANAL in net.species
    assert NBAL not in net.species and IBAL not in net.species
    v = Vessel(net, volume=1.0, T=420.0, T_env=420.0, UA=1.0e6, k_vent=0.0)
    n = charge_for(200.0, 420.0)
    v.charge({ETHYLENE: n, CO: n, H2: n}, phase="gas")
    v.charge({COBALT: 0.1}, phase="solid")
    v.run(3600.0, **TIGHT)
    assert v.state().total(PROPANAL) > 1.0


def test_evans_polanyi_is_OFF_and_that_is_a_declaration(net):
    """⚠ ``alpha > 0`` would name the WRONG major product with confidence.

    The barrier would be scaled by dH, and the branched route is the more
    exothermic one -- so any transfer coefficient above zero hands it the lower
    barrier. The regiochemistry of a cobalt hydroformylation is set by which
    alkyl-cobalt forms, not by how stable the aldehyde is.
    """
    for t in oxo_chemistry():
        assert t.alpha == 0.0
        assert t.reversible is True
        assert t.solid_catalyst == "cobalt"
    lin, bra = oxo_chemistry()
    assert lin.A == bra.A                       # the ratio is ONE exponential
    assert bra.Ea - lin.Ea == pytest.approx(4800.0)
