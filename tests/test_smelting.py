"""S9 -- the reversible solid-gas term, and the three smelters it makes.

S8 named "a REVERSIBLE solid-gas term" as the most valuable engine item in the
plan that nobody had scoped, blocking the work queue's only +2. It turned out to
be **one algebraic rearrangement of a term that already existed**, plus a
declared barrier for the case M6's derivation was never about.

    net = k_f * prod(p ** consumed_gas)  -  k_r * prod(p ** formed_gas)

against the old ``net = k_f - k_r * Q``. It is ``P_react (k_f - k_r Q)``
algebraically -- the SAME root, so the same equilibrium -- and it never divides,
so the 2.6e15 formula units per second M6 measured as the gas ran out becomes a
finite ``k_r p_prod``.

⚠ WHAT THE OLD REFUSAL GOT WRONG ABOUT ITSELF. It gave two reasons and only one
of them was about this term: the ``p/K = n_A/n_B`` half is about MASS ACTION on a
solid amount, and the affinity form takes ONE ``units`` for both directions
chosen by the sign, so it is a common factor that divides out of ``net = 0``.
That was already true when the refusal was written. Pinned in
``test_the_equilibrium_is_Q_over_K_whatever_the_charge_weighs``.

⚠ AND ROASTING STAYS IN THE OTHER TERM, for the reason that survives: an
affinity form cannot carry DECLARED rate orders, because detailed balance fixes
its exponents at the stoichiometric coefficients. That is this project's own
standing invariant -- *a declared rate order may never be reversible* -- arriving
in a new place. ``test_surface.py`` pins that side.

The integration tests here run at the tight tolerance and are cheap: a furnace
is a sealed or freely-vented flask with no liquid in it at all.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from chemsim.constants import R, R_L_BAR
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties import solid_state as ss
from chemsim.properties import surface as sf
from chemsim.properties.mineral_data import MINERALS
from chemsim.vessel import Vessel
from chemsim.vessel.vessel import build_solid_state_arrays, build_surface_arrays

M = MINERALS
COVELLITE, TENORITE, COPPER = (M["covellite"].lattice, M["tenorite"].lattice,
                               M["copper"].lattice)
GALENA, LITHARGE, LEAD = (M["galena"].lattice, M["litharge"].lattice,
                          M["lead"].lattice)
SPHALERITE, ZINCITE = M["sphalerite"].lattice, M["zincite"].lattice
# ⚠⚠ S10 -- ZINC IS NOT A LATTICE ANY MORE, and that is this milestone. It used
# to be ``M["zinc"].lattice``; it is an ordinary elemental species with a
# melting point and a boiling point, so the retort evolves it as a VAPOUR.
ZINC = "[Zn]"
GRAPHITE = M["carbon-graphite"].lattice
HEMATITE, IRON = M["hematite"].lattice, M["iron"].lattice
CORUNDUM, ALUMINIUM = M["corundum"].lattice, M["aluminium"].lattice
CALCITE, QUICKLIME = M["calcite"].lattice, M["quicklime"].lattice
CO, CO2, N2, O2, SO2 = "[C-]#[O+]", "O=C=O", "N#N", "O=O", "O=S=O"

TIGHT = dict(rtol=1.0e-8, atol=1.0e-11)

REDUCTION = "tenorite-carbon-monoxide-reduction"
BOUDOUARD = "boudouard-gasification"
THERMITE = "metallothermic-reduction"
RETORT = "zincite-carbothermic-reduction"


@pytest.fixture(scope="module")
def thermo():
    return ThermochemistryProvider()


@pytest.fixture(scope="module")
def volatility(thermo):
    return VolatilityProvider(thermo)


def _net(species, thermo, volatility):
    return build_network(species, [], thermo=thermo, volatility=volatility)


def _decl(name):
    for d in ss.SOLID_STATE_REACTIONS:
        if d.name == name:
            return d
    raise AssertionError(name)


def solid(v, s):
    return float(v.state().n_solid.get(s, 0.0))


def gas(v, s):
    return float(v.state().n_gas.get(s, 0.0))


def metal_total(v, s):
    """⚠ S10 -- the metal WHEREVER IT IS. Copper and lead land in the solid
    block; zinc comes off as a vapour above 1180 K and condenses to a liquid
    below it, so a smelter test that reads only ``n_solid`` measures the
    thermometer rather than the yield.
    """
    st = v.state()
    return float(st.n_solid.get(s, 0.0) + st.n_liquid.get(s, 0.0)
                 + st.n_liquid2.get(s, 0.0) + st.n_gas.get(s, 0.0))


# ==========================================================================
# THE DECLARATIONS
# ==========================================================================


def test_the_five_new_rows_price_off_this_projects_own_tables(thermo):
    """No estimator stands behind any of these: a ``mineral_data`` lattice on
    the solid basis against a curated gas on the ideal-gas basis, which is the
    subtraction ``solid_state``'s docstring argues is legal exactly here."""
    expect = {
        REDUCTION: (-125.68, 6.84),
        "litharge-carbon-monoxide-reduction": (-63.98, 14.52),
        # S10 -- was (239.97, 189.80) with a SOLID zinc product; the vapour
        # carries its sublimation energy and entropy into the row
        RETORT: (370.37, 309.20),
        BOUDOUARD: (172.45, 175.68),
        THERMITE: (-851.50, -38.50),
    }
    for name, (dH, dS) in expect.items():
        p = ss.price(_decl(name), thermo)
        assert p.dH / 1000.0 == pytest.approx(dH, abs=0.01), name
        assert p.dS == pytest.approx(dS, abs=0.01), name
        assert "experimental" in p.basis or "reference state" in p.basis


def test_three_rows_now_CONSUME_a_gas_which_is_the_whole_engine_change():
    """⚠ For five milestones a gas REACTANT was refused where these arrays are
    built. Three rows have one now, and their exponents are STOICHIOMETRIC --
    detailed balance leaves no choice about that, which is why the roasting rows
    stay in the mass-action term where an order can be declared."""
    arr, report = build_solid_state_arrays(
        [TENORITE, COPPER, LITHARGE, LEAD, GRAPHITE, CO, CO2]
    )
    consuming = [
        arr.names[i] for i in range(arr.m) if (arr.nu_gas[i] < 0.0).any()
    ]
    assert sorted(consuming) == sorted([
        BOUDOUARD, "litharge-carbon-monoxide-reduction", REDUCTION,
    ])
    assert not [line for line in report if "REFUSED" in line]
    # and the two halves of the gas side partition it exactly
    assert (arr.gas_consumed - arr.gas_formed == -arr.nu_gas).all()
    assert (arr.gas_consumed >= 0.0).all() and (arr.gas_formed >= 0.0).all()
    assert (arr.gas_consumed * arr.gas_formed == 0.0).all()


def test_the_pre_S9_rows_are_BIT_IDENTICAL_not_merely_close():
    """⚠⚠ THE PROPERTY THAT MAKES THIS CHANGE SAFE, and it is exact rather than
    approximate. Every pre-S9 row has ``nu_gas >= 0``, so ``gas_formed`` IS
    ``nu_gas`` element for element and ``gas_consumed`` is all zeros -- and
    ``p ** 0`` is exactly 1.0 for every finite p, ZERO INCLUDED.

    ⚠ Verified separately against the EXAMPLE SET rather than only by argument:
    ``examples/lime_cycle.py`` and ``examples/mercury_retort.py`` come out
    byte-identical across this change.
    """
    species = [CALCITE, QUICKLIME, CO2, N2]
    arr, _ = build_solid_state_arrays(species)
    i = arr.names.index("calcination-decarbonation")
    assert (arr.gas_consumed[i] == 0.0).all()
    assert (arr.gas_formed[i] == arr.nu_gas[i]).all()

    for p_co2 in (0.0, 1.0e-30, 0.37, 1.0, 55.0):
        p = np.zeros(len(species))
        p[species.index(CO2)] = p_co2
        Q_old = np.prod(p[None, :] ** arr.nu_gas, axis=1)
        P_react = np.prod(p[None, :] ** arr.gas_consumed, axis=1)
        P_prod = np.prod(p[None, :] ** arr.gas_formed, axis=1)
        assert P_react[i] == 1.0                      # exactly, not approx
        assert P_prod[i] == Q_old[i]                  # exactly


# ==========================================================================
# THE BOUND THAT REPLACED THE REFUSAL
# ==========================================================================


def test_the_reverse_flux_is_BOUNDED_where_the_quotient_form_diverged():
    """⚠⚠ M6 MEASURED 2.6e15 FORMULA UNITS PER SECOND AS THE GAS RAN OUT, and
    that is what a quotient does when its denominator goes to zero. The split
    form's reverse branch is ``k_r`` times a PRESSURE, so its bound is the
    reverse rate constant itself -- no clip, no floor, no epsilon.
    """
    species = [TENORITE, COPPER, CO, CO2]
    arr, _ = build_solid_state_arrays(species)
    i = arr.names.index(REDUCTION)
    T = 1400.0
    k_f = arr.A_fwd * np.exp(-arr.Ea_fwd / (R * T))
    k_r = arr.A_rev * np.exp(-arr.Ea_rev / (R * T))

    seen = []
    for p_co in (1.0, 1.0e-6, 1.0e-12, 1.0e-30, 0.0):
        p = np.zeros(len(species))
        p[species.index(CO)] = p_co
        p[species.index(CO2)] = 1.0
        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            Q = np.prod(p[None, :] ** arr.nu_gas, axis=1)
        P_react = np.prod(p[None, :] ** arr.gas_consumed, axis=1)
        P_prod = np.prod(p[None, :] ** arr.gas_formed, axis=1)
        flux = k_f * P_react - k_r * P_prod
        assert np.isfinite(flux).all()
        assert abs(flux[i]) <= max(k_f[i], k_r[i]) * (1.0 + 1.0e-12)
        seen.append((float(Q[i]), float(flux[i])))

    # the OLD branch really does diverge on the same numbers
    assert seen[-2][0] == pytest.approx(1.0e30, rel=1e-9)
    assert (k_r * seen[-2][0])[i] > 1.0e21
    assert math.isinf(seen[-1][0])
    # ...and the NEW one has settled on -k_r p_CO2 exactly
    assert seen[-1][1] == pytest.approx(-k_r[i], rel=1e-12)


def test_the_equilibrium_is_Q_over_K_whatever_the_charge_weighs(
    thermo, volatility
):
    """⚠⚠ THE HALF OF THE OLD REFUSAL THAT WAS ABOUT A DIFFERENT FORM. It said
    mass action on a solid AMOUNT settles at ``p/K = n_A/n_B`` -- true, and M6
    measured it at 3.0863 against 3.0863 -- but the affinity form takes ONE
    ``units`` for both directions, chosen by the sign, so it is a common factor
    that divides out of ``net = 0``. A gas reactant never threatened that, and
    here is the measurement over a 50x charge range.
    """
    n = _net([TENORITE, COPPER, CO, CO2, N2], thermo, volatility)
    T = 1500.0
    p = ss.price(_decl(REDUCTION), thermo)
    K = math.exp(-(p.dH - T * p.dS) / (R * T))
    assert K == pytest.approx(5.4184e4, rel=1e-3)

    for charge, co_bar in ((0.10, 0.02), (0.02, 0.02), (1.00, 0.05)):
        v = Vessel(n, volume=10.0, T=T, T_env=T, UA=1.0e4, k_vent=0.0)
        v.charge({TENORITE: charge}, phase="solid")
        v.charge({CO: co_bar * 10.0 / (R_L_BAR * T)}, phase="gas")
        v.run(40000.0, **TIGHT)
        assert not v.conservation_report()
        p_co = gas(v, CO) * R_L_BAR * T / 10.0
        p_co2 = gas(v, CO2) * R_L_BAR * T / 10.0
        assert p_co2 / p_co == pytest.approx(K, rel=1.0e-3)
        # and the oxide is NOT exhausted -- the equilibrium is the mechanic
        assert solid(v, TENORITE) > 0.5 * charge


def test_a_declared_pre_exponential_is_under_its_own_arrival_ceiling(thermo):
    """⚠ A CONSTANT'S UNITS ARE WHAT MAKE ITS VALUE DEFENSIBLE. The ceiling for
    a rate written per formula unit of solid per bar is not a collision
    frequency in solution: it is the HERTZ-KNUDSEN arrival rate at a crystal
    face. CO at 1 bar and 1400 K arrives at 2209 mol/(m2 s), and tenorite's
    molar volume over a 100 um grain is 0.756 m2/mol of specific surface.
    """
    kB, NA = 1.380649e-23, 6.02214076e23
    m_CO = 28.01e-3 / NA
    T = 1400.0
    flux = 1.0e5 / math.sqrt(2.0 * math.pi * m_CO * kB * T) / NA   # mol/(m2 s)
    assert flux == pytest.approx(2209.0, rel=0.01)
    # ⚠ Vm_solid is in L/mol, so the m3/mol the geometry wants is /1000. Naming
    # the unit is the whole point of this test.
    Vm = MINERALS["tenorite"].Vm_solid / 1000.0           # m3/mol
    S = 6.0 * Vm / 1.0e-4                                 # m2/mol at 100 um
    assert S == pytest.approx(0.756, rel=0.01)
    ceiling = flux * S                                    # 1/(bar s)
    assert ss.REDUCTION_A / ceiling == pytest.approx(9.6e-4, rel=0.05)
    assert ss.REDUCTION_A < ceiling

    # and thermite's is a unimolecular constant, under this project's own limit
    assert ss.THERMITE_A < 1.0e14
    # ...pinned on the ignition temperature, so tau there is one second
    p = ss.price(_decl(THERMITE), thermo)
    k = p.A * math.exp(-p.Ea / (R * 1200.0))
    assert 1.0 / k == pytest.approx(1.0, rel=0.01)


# ==========================================================================
# THE THREE SMELTERS, RUN RATHER THAN READ
# ==========================================================================


@pytest.mark.parametrize(
    "ore,oxide,metal,T,sulfide_charge",
    [(COVELLITE, TENORITE, COPPER, 1500.0, 0.04),
     (GALENA, LITHARGE, LEAD, 1400.0, 0.04),
     (SPHALERITE, ZINCITE, ZINC, 1400.0, 0.04)],
)
def test_a_smelter_takes_ore_coke_and_AIR_to_metal(
    thermo, volatility, ore, oxide, metal, T, sulfide_charge
):
    """⚠⚠ NOTHING DECLARES THIS ROUTE. Four declarations in two modules share a
    solid block and a headspace:

        surface.py       MS  + O2  -> MO + SO2      a gas at a crystal
        surface.py       C   + O2  -> CO2           the tuyere
        solid_state.py   C   + CO2 -> 2 CO          Boudouard, reversible
        solid_state.py   MO  + CO  -> M  + CO2      the reduction, reversible

    and the catalog's own two-step smelting route falls out. The zinc route
    substitutes ``ZnO + C -> Zn + CO`` for the last line, which needs no gas
    reactant at all and was an ordinary row of that table nobody had written.
    """
    n = _net([ore, oxide, metal, GRAPHITE, CO, CO2, N2, O2, SO2],
             thermo, volatility)
    v = Vessel(n, volume=10.0, T=T, T_env=T, UA=1.0e4, k_vent=0.0)
    v.charge({ore: sulfide_charge, GRAPHITE: 0.20}, phase="solid")
    v.charge({O2: 0.20, N2: 0.75}, phase="gas")
    v.run(40000.0, **TIGHT)
    assert not v.conservation_report()
    # the ore is gone, the metal is there, and the sulfur left as SO2
    assert solid(v, ore) < 1.0e-9
    assert gas(v, SO2) == pytest.approx(sulfide_charge, rel=1.0e-6)
    assert metal_total(v, metal) > 0.5 * sulfide_charge


def test_the_air_is_the_control_which_is_what_a_smelter_adjusts(
    thermo, volatility
):
    """The yield is monotone in the blast and saturates: the sulfide cannot
    roast without oxygen, and once it has roasted the coke does the rest."""
    n = _net([COVELLITE, TENORITE, COPPER, GRAPHITE, CO, CO2, N2, O2, SO2],
             thermo, volatility)
    got = []
    for o2 in (0.02, 0.06, 0.10, 0.20):
        v = Vessel(n, volume=10.0, T=1500.0, T_env=1500.0, UA=1.0e4,
                   k_vent=0.0)
        v.charge({COVELLITE: 0.04, GRAPHITE: 0.20}, phase="solid")
        v.charge({O2: o2, N2: o2 * 79.0 / 21.0}, phase="gas")
        v.run(40000.0, **TIGHT)
        got.append(solid(v, COPPER))
    assert got == sorted(got)
    assert got[0] < 0.4 * 0.04                     # starved
    assert got[-1] == pytest.approx(0.04, rel=1.0e-6)   # total


def test_the_zinc_retort_is_a_THRESHOLD_at_its_own_dG_zero(thermo, volatility):
    """⚠ ``ZnO + C -> Zn(g) + CO`` is endothermic with a big positive dS, so its
    dG changes sign -- at **1197.8 K** off this project's own tables, against a
    real Belgian retort's 1200-1300 and a literature threshold of ~1200 K.
    Nothing was fitted to get that, and nothing gates on temperature anywhere:
    it is one Arrhenius factor and one van 't Hoff K.

    ⚠⚠ S10 MOVED THIS NUMBER, AND TOWARD THE LITERATURE. S9 declared the zinc as
    a SOLID product and got 1264.3 K. Carrying it as the VAPOUR a retort actually
    makes adds the sublimation energy (+130.4 kJ/mol) and the entropy of a mole
    of metal gas (+119.4 J/(mol K)) to the row, and the entropy wins: the
    threshold comes DOWN by 66 K.

    ⚠ AND THE BARRIER WENT UP BY THE SAME 130.4 kJ/mol, because M6 derives it as
    ``max(dH, 0)``. So the reaction is simultaneously more favourable and SLOWER
    at a given temperature -- 370.4 kJ/mol is inside the 300-400 range reported
    for apparent activation energies of carbothermic zinc reduction, so the
    derived barrier is defensible rather than merely arithmetic.

    ⚠⚠ THE FLASK IS SEALED HERE ON PURPOSE. Now that the product is a gas, a
    VENTED retort loses it up the chimney, so total zinc in the flask stops being
    the conversion -- see the two tests below.
    """
    p = ss.price(_decl(RETORT), thermo)
    assert p.dH / p.dS == pytest.approx(1197.8, abs=1.0)
    assert p.dH / 1000.0 == pytest.approx(370.4, abs=0.5)
    assert p.dS == pytest.approx(309.2, abs=0.5)
    assert p.Ea == pytest.approx(p.dH)          # M6's derived pair, unchanged

    n = _net([ZINCITE, ZINC, GRAPHITE, CO, CO2], thermo, volatility)
    got = {}
    for T in (1000.0, 1100.0, 1198.0, 1250.0, 1300.0):
        v = Vessel(n, volume=1.0, T=T, T_env=T, UA=1.0e4, k_vent=0.0)
        v.charge({ZINCITE: 0.04, GRAPHITE: 0.20}, phase="solid")
        v.run(20000.0, **TIGHT)
        assert not v.conservation_report()
        got[T] = metal_total(v, ZINC) / 0.04
    assert list(got.values()) == sorted(got.values())
    assert got[1000.0] < 0.01                      # cold: essentially nothing
    assert 0.20 < got[1198.0] < 0.35               # at dG = 0, part way over
    assert got[1300.0] == pytest.approx(1.0, rel=1.0e-6)   # done


def test_a_VENTED_retort_blows_its_own_product_up_the_chimney(
    thermo, volatility
):
    """⚠⚠ NOBODY DECLARED THIS, AND IT IS WHY A REAL RETORT HAS A CONDENSER.

    Once the zinc is a vapour, the vent that pulls the reaction over also carries
    the metal away. So the two things a smelter cares about come apart, and they
    move in OPPOSITE directions with temperature:

      * ore CONSUMED rises to completion -- that is the thermodynamics;
      * metal RETAINED falls, because zinc's partial pressure rises with T and
        the vent is indifferent to which gas it is venting.

    ⚠ Measured, this is not a small effect: at 1200 K the ore is 99.9% gone and
    barely half the metal is still in the flask. A test that read total zinc in a
    vented flask would therefore be measuring the chimney, not the reaction --
    and ⚠ ``conservation_report`` is silent throughout, correctly, because the
    vent is a declared boundary flux and not a leak. "An invariant measured
    across a boundary flux is not an invariant."
    """
    n = _net([ZINCITE, ZINC, GRAPHITE, CO, CO2], thermo, volatility)
    consumed, retained = {}, {}
    for T in (1200.0, 1300.0, 1400.0):
        v = Vessel(n, volume=10.0, T=T, T_env=T, UA=1.0e4, k_vent=1.0e3,
                   atmosphere={})
        v.charge({ZINCITE: 0.10, GRAPHITE: 0.10}, phase="solid")
        v.run(20000.0, **TIGHT)
        assert not v.conservation_report()
        consumed[T] = (0.10 - solid(v, ZINCITE)) / 0.10
        retained[T] = metal_total(v, ZINC) / 0.10

    # the reaction finishes, and more completely the hotter it gets
    assert consumed[1200.0] > 0.99
    assert consumed[1400.0] == pytest.approx(1.0, abs=1.0e-6)
    # ...while what is left in the flask goes the OTHER way
    assert retained[1200.0] < 0.55
    assert retained[1400.0] < retained[1300.0] < retained[1200.0]
    # and the gap is the metal that left as vapour
    assert consumed[1400.0] - retained[1400.0] > 0.5


def test_the_zinc_DISTILS_and_neither_Tb_nor_Tm_is_written_anywhere(
    thermo, volatility
):
    """⚠⚠ S10 -- THIS TEST IS THE INVERSE OF THE ONE IT REPLACED.

    Its predecessor was ``test_the_zinc_stays_a_SOLID_and_that_is_a_stated_
    limitation``, and it pinned the limitation deliberately, ending "if this test
    ever fails it is because ``[Zn]`` became a priceable gas, and then the row
    should be rewritten to evolve it." That is what happened, and the reason is
    worth keeping: BOTH halves of the recorded refusal were about the ENTRY
    rather than about the metal. ``mineral_data`` held zinc as a lattice, and a
    lattice may react and may never boil -- but zinc passes every test S4
    admitted mercury on (a monatomic vapour, one condensed form, an expressible
    reference state), so it belongs in ``element_data``, and once it is there no
    engine change is needed at all.

    What this measures is that the retort's product goes gas -> liquid -> solid
    on the way out, at zinc's OWN transition temperatures, with neither of them
    appearing in the declaration or in this file's arithmetic.
    """
    # it prices now, and on the SOLID reference basis: Hf is the sublimation
    # energy, exactly as bromine's and iodine's are the vaporisation ones
    t = thermo.get("[Zn]")
    assert t.Hf == pytest.approx(130.4, abs=0.1)
    assert t.Tb == pytest.approx(1180.15, abs=0.1)
    assert t.Tm == pytest.approx(692.68, abs=0.1)
    assert "zinc" not in MINERALS          # the lattice row is gone

    n = _net([ZINCITE, ZINC, GRAPHITE, CO, CO2], thermo, volatility)
    v = Vessel(n, volume=1.0, T=1400.0, T_env=1400.0, UA=1.0e4, k_vent=0.0)
    v.charge({ZINCITE: 0.04, GRAPHITE: 0.20}, phase="solid")
    v.run(20000.0, **TIGHT)
    st = v.state()
    # at 1400 K, 220 K above Tb, every atom of it is in the headspace
    assert st.n_gas[ZINC] == pytest.approx(0.04, rel=1.0e-6)
    assert st.n_solid[ZINC] == 0.0
    assert st.n_liquid[ZINC] == 0.0

    # now cool the receiver. The vapour condenses, then it freezes.
    seen = {}
    for T in (900.0, 600.0):
        v.set_environment(T_env=T)
        v.T = T
        v.run(20000.0, **TIGHT)
        st = v.state()
        seen[T] = (st.n_gas[ZINC], st.n_liquid[ZINC], st.n_solid[ZINC])
        assert not v.conservation_report()
    # 900 K is between Tm and Tb: a LIQUID metal in the receiver
    assert seen[900.0][1] > 0.99 * 0.04
    assert seen[900.0][2] == 0.0
    # 600 K is below Tm: it has frozen
    # 99.9996% of it, not all: zinc has a small but real vapour pressure at
    # 600 K and the melting range has a finite width. Both are the engine's
    # own terms rather than a fudge, so the residue is asserted, not hidden.
    assert seen[600.0][2] == pytest.approx(0.04, rel=1.0e-4)
    assert seen[600.0][2] / 0.04 > 0.9999
    assert seen[600.0][1] < 1.0e-9


def test_the_vent_does_NOTHING_until_the_retort_beats_the_room(
    thermo, volatility
):
    """⚠⚠ PRODUCT REMOVAL IS THE RETORT'S MECHANIC, and it switches on at a
    temperature nothing declares.

    ``solid_state_report`` computes that this row needs **1156 K** for its two
    evolved gases to reach one bar between them. Below that a retort vented to
    atmosphere vents nothing, because its own pressure never beats the room --
    so sealed and vented agree to every digit. Above it, venting takes the
    reaction from a stalled equilibrium to completion. The 1156 K is derived from
    a van 't Hoff K; the crossover below is measured by running the flask, and
    the two agree.
    """
    n = _net([ZINCITE, ZINC, GRAPHITE, CO, CO2], thermo, volatility)

    def run(T, *, vented):
        v = Vessel(n, volume=1.0, T=T, T_env=T, UA=1.0e4,
                   k_vent=1.0e3 if vented else 0.0)
        v.charge({ZINCITE: 0.04, GRAPHITE: 0.20}, phase="solid")
        v.run(20000.0, **TIGHT)
        assert not v.conservation_report()
        return (0.04 - solid(v, ZINCITE)) / 0.04, v.pressure

    # 1150 K: the sealed flask sits UNDER one bar, so the vent is inert
    lo_sealed, p_lo = run(1150.0, vented=False)
    lo_vented, _ = run(1150.0, vented=True)
    assert p_lo < 1.013
    assert lo_vented == pytest.approx(lo_sealed, rel=1.0e-6)

    # 1198 K: over the bar, and now removing the product finishes the job
    hi_sealed, p_hi = run(1198.0, vented=False)
    hi_vented, _ = run(1198.0, vented=True)
    assert p_hi > 1.013
    assert hi_sealed < 0.35
    assert hi_vented > 0.99


# ==========================================================================
# THE CARRIER, AND THE FAILURE MODE IT COULD HAVE BEEN
# ==========================================================================


def test_a_carrier_free_furnace_is_EXACTLY_inert_at_four_tolerances(
    thermo, volatility
):
    """⚠⚠ THE QUESTION ``chemsim-solid-gate-fix`` EXISTS TO ASK. A cycle with
    gain on its own carrier is exactly the shape that let round-off seed the
    lead chamber to an 89% yield on 1.2e-4 mol of phantom NOx. This one cannot
    be seeded, and the reason is the FORM rather than a guard: the arriving gas
    enters as ``p ** 1`` with no denominator, so zero in is zero out with a
    bounded slope. There is no smoothstep and no constant scale anywhere in it.
    """
    n = _net([TENORITE, COPPER, GRAPHITE, CO, CO2, N2], thermo, volatility)
    for kw in ({}, dict(rtol=1.0e-6), TIGHT,
               dict(rtol=1.0e-10, atol=1.0e-14)):
        v = Vessel(n, volume=10.0, T=1500.0, T_env=1500.0, UA=1.0e4,
                   k_vent=0.0)
        v.charge({TENORITE: 0.10, GRAPHITE: 0.10}, phase="solid")
        v.run(20000.0, **kw)
        assert solid(v, COPPER) == 0.0             # exactly
        assert gas(v, CO) == 0.0
        assert gas(v, CO2) == 0.0
        assert solid(v, TENORITE) == 0.10


def test_the_carrier_MULTIPLIES_once_it_is_seeded(thermo, volatility):
    """⚠ And that is real chemistry rather than a leak: Boudouard makes 2 CO out
    of 1 CO2 and the reduction hands one CO2 back, so the cycle GAINS a carrier
    per turn. A blast furnace's gas volume really does grow that way. **The
    carbon is the reagent; the carbon oxide is only the vehicle** -- 1e-12 mol
    of CO2, one part in 1e11 of the charge, reduces the whole 0.10 mol.
    """
    n = _net([TENORITE, COPPER, GRAPHITE, CO, CO2, N2], thermo, volatility)
    for seed in (1.0e-12, 1.0e-6):
        v = Vessel(n, volume=10.0, T=1500.0, T_env=1500.0, UA=1.0e4,
                   k_vent=0.0)
        v.charge({TENORITE: 0.10, GRAPHITE: 0.10}, phase="solid")
        v.charge({CO2: seed}, phase="gas")
        v.run(20000.0, **TIGHT)
        assert not v.conservation_report()
        assert solid(v, COPPER) == pytest.approx(0.10, rel=1.0e-6)
        # the CARBON is what was consumed, essentially all of it
        assert solid(v, GRAPHITE) < 1.0e-3
        # ...and the gas inventory is now nine decades above what was charged
        assert gas(v, CO) > 0.09


def test_carbon_combustion_is_a_declared_pair_and_not_the_sulfide_one(thermo):
    """⚠ THE SHARED-CONSTANT CLAIM IS A CLAIM THAT TWO ROWS ARE THE SAME EVENT.
    ``ROASTING_A``/``ROASTING_EA`` assert that the rate-determining step is an
    O2 molecule arriving at a metal-SULFIDE surface. Carbon burning has neither
    a metal nor a sulfur in it, so it declares its own pair -- which is a
    loosening of the claim and not a retreat from it.
    """
    priced = {d.name: sf.price(d, thermo) for d in sf.SURFACE_REACTIONS}
    roasts = [p for name, p in priced.items() if name.endswith("-roasting")]
    assert len(roasts) == 4
    for p in roasts:
        assert p.A == sf.ROASTING_A and p.Ea == sf.ROASTING_EA
    carbon = priced["carbon-combustion"]
    assert carbon.A == sf.CARBON_COMBUSTION_A
    assert carbon.Ea == sf.CARBON_COMBUSTION_EA
    assert carbon.A != sf.ROASTING_A

    # ⚠ AND IT IS THE TIGHTEST ROW IN THAT TABLE AGAINST THE IRREVERSIBILITY
    # BAR, by 46 nats -- because above ~1000 K carbon dioxide over carbon is
    # increasingly taken to CO, which is the row declared in the OTHER module.
    assert carbon.ln_K_run == pytest.approx(21.87, abs=0.01)
    assert carbon.ln_K_run > sf.LN_K_IRREVERSIBLE
    assert min(p.ln_K_run for p in roasts) - carbon.ln_K_run > 45.0


def test_half_a_surface_kinetic_declaration_is_refused(thermo):
    """An Arrhenius pair is not separable, so half a declaration would pair a
    barrier with a pre-exponential fitted to a different event."""
    base = dict(
        solids=(("carbon-graphite", -1, 1.0),),
        gases=(("O=O", -1, 1.0), ("O=C=O", +1, 0.0)),
        mechanism="carbon-combustion", T_run=2200.0, note="",
    )
    with pytest.raises(sf.UnpricedSurfaceReaction, match="declares A and not"):
        sf.price(sf.SurfaceReaction(name="half-a", A=1.0, **base), thermo)
    with pytest.raises(sf.UnpricedSurfaceReaction, match="declares Ea and not"):
        sf.price(sf.SurfaceReaction(name="half-b", Ea=1.0e5, **base), thermo)


def test_the_roasting_rows_are_unmoved_by_the_new_field():
    """A new optional field must be exactly inert on every row that does not
    use it -- the ``losses=None`` discipline, applied to a declaration."""
    arr, report = build_surface_arrays(
        [SPHALERITE, ZINCITE, GRAPHITE, O2, SO2, CO2]
    )
    assert not [line for line in report if "REFUSED" in line]
    i = arr.names.index("sphalerite-roasting")
    assert arr.A[i] == sf.ROASTING_A
    assert arr.Ea[i] == sf.ROASTING_EA
    j = arr.names.index("carbon-combustion")
    assert arr.A[j] == sf.CARBON_COMBUSTION_A


# ==========================================================================
# THERMITE -- A ROW WITH NO GAS AT ALL
# ==========================================================================


def test_a_row_with_no_gas_has_an_affinity_with_no_quotient_in_it():
    """⚠ STRUCTURALLY A FIRST rather than a bigger one of the same thing. Every
    other row in either solid table exchanges at least one gas; this one has
    none, so BOTH one-sided pressure products are empty -- exactly 1.0 -- and
    the affinity collapses to ``k_f - k_r``, a constant. That is correct: with
    no gas there is no quotient to move, so the row is effectively irreversible
    at ln K +29.5 and runs to completion.
    """
    species = [HEMATITE, ALUMINIUM, IRON, CORUNDUM, N2]
    arr, _ = build_solid_state_arrays(species)
    i = arr.names.index(THERMITE)
    assert (arr.nu_gas[i] == 0.0).all()
    for p_any in (0.0, 1.0, 1.0e6):
        p = np.full(len(species), p_any)
        assert np.prod(p[None, :] ** arr.gas_consumed, axis=1)[i] == 1.0
        assert np.prod(p[None, :] ** arr.gas_formed, axis=1)[i] == 1.0


def test_thermite_is_INERT_cold_and_total_hot(thermo, volatility):
    """⚠⚠ THE MECHANIC IS ENTIRELY IN THE BARRIER, and one pin on the reported
    1200 K ignition temperature buys a column nothing was fitted to -- including
    that the reaction becomes appreciable around **933 K, where aluminium
    melts**, which is the trigger every account of thermite names and which
    nothing in this engine knows.
    """
    n = _net([HEMATITE, ALUMINIUM, IRON, CORUNDUM, N2], thermo, volatility)
    got = {}
    for T in (298.15, 600.0, 933.0, 1000.0, 1200.0):
        v = Vessel(n, volume=1.0, T=T, T_env=T, UA=1.0e4, k_vent=0.0)
        v.charge({HEMATITE: 0.02, ALUMINIUM: 0.04}, phase="solid")
        v.run(600.0, **TIGHT)
        assert not v.conservation_report()
        got[T] = solid(v, IRON)
    assert got[298.15] == 0.0
    assert got[600.0] < 1.0e-9
    assert 0.3 < got[933.0] / 0.04 < 0.45
    assert got[1000.0] / 0.04 > 0.98
    assert got[1200.0] == pytest.approx(0.04, rel=1.0e-9)

    # the barrier that makes it so, against the collision ceiling
    p = ss.price(_decl(THERMITE), thermo)
    assert p.Ea == 250_000.0
    assert 1.0 / (p.A * math.exp(-p.Ea / (R * 298.15))) > 1.0e30   # seconds


def test_thermite_runs_away_on_its_own_enthalpy_and_nothing_caps_it(
    thermo, volatility
):
    """⚠ AN INSULATED FLASK IGNITES ITSELF -- the energy balance was already
    there, and 851.5 kJ/mol into a few J/K is a runaway nobody declared.

    ⚠ **STATED LIMITATION**: nothing caps the temperature. A real thermite stops
    near 3135 K because the IRON BOILS. The RHS clamps T at 5000 K for RATE
    evaluation only, so a low-heat-capacity flask can report a state above it.

    ⚠⚠ S10 -- AND THIS IS NO LONGER "THE SAME STATEMENT THE ZINC RETORT MAKES",
    which is what that pairing cost. S9 filed both under one sentence -- *a
    lattice may react and may never boil* -- and half of it was a DATA job that
    needed no engine change at all (see the zinc tests above). Separating them
    LOCATED the real gap, and it is smaller than the one S9 handed forward:

    **iron cannot leave ``mineral_data`` the way zinc did.** It is a declared
    ``solid_catalyst`` -- ``ammonia_synthesis(catalyst="iron")``, resolved
    through ``MINERALS["iron"].lattice`` -- as well as this row's own solid
    product. So iron would have to be BOTH a ``mineral_data`` lattice and a
    ``thermochemistry`` gas, and ``PhaseArrays.lattice`` is one boolean picking
    both a species' basis and its destination block. Zinc never needed that:
    nothing else referenced its lattice entry.

    ⚠ The data is nearly there and the mechanism would work -- Alcock's liquid
    equation converts to Antoine exactly (A = 6.352717, B = 19574, C = 0) and
    unanchored puts Tb at 3083.98 K against 3134.15 measured, and boiling the
    2 mol of iron a mole of thermite makes would absorb 88.0% of the 851.5 kJ it
    releases. Two things still say no: ``[Fe]`` fails S4's DISAMBIGUATION test
    (three solid allotropes, two transitions inside this reaction's own range,
    against zinc's single condensed form), and Alcock tabulates no SUBLIMATION
    curve for iron, so the 298 K reference-state identity zinc closed at
    -0.184 kJ/mol cannot be evaluated at all -- ONE cross-check, not four.
    """
    n = _net([HEMATITE, ALUMINIUM, IRON, CORUNDUM, N2], thermo, volatility)
    # cold and insulated: still nothing
    v = Vessel(n, volume=1.0, T=298.15, T_env=298.15, UA=0.0, k_vent=0.0,
               heat_capacity=50.0)
    v.charge({HEMATITE: 0.02, ALUMINIUM: 0.04}, phase="solid")
    v.run(600.0, **TIGHT)
    assert v.state().T == pytest.approx(298.15, abs=1.0e-6)
    assert solid(v, IRON) == 0.0

    # lit and insulated: the rise is the arithmetic, to a few percent
    Cp_products = 0.04 * 25.1 + 0.02 * 79.0
    for hc in (50.0, 500.0):
        v = Vessel(n, volume=1.0, T=1000.0, T_env=1000.0, UA=0.0, k_vent=0.0,
                   heat_capacity=hc)
        v.charge({HEMATITE: 0.02, ALUMINIUM: 0.04}, phase="solid")
        v.run(600.0, **TIGHT)
        assert not v.conservation_report()
        rise = v.state().T - 1000.0
        assert rise == pytest.approx(0.02 * 851_500.0 / (Cp_products + hc),
                                     rel=0.05)
        assert solid(v, IRON) > 0.039
    # ⚠ and the refusal above is pinned, so it cannot quietly become an
    # acceptance: iron is still a lattice, and still a declared catalyst.
    assert "iron" in MINERALS
    with pytest.raises(ValueError, match="bare element symbol"):
        thermo.get("[Fe]")
