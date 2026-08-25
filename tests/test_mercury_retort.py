"""S4 -- the mercury retort: a route nobody declared, out of two that were.

``mercury-from-cinnabar`` is a ONE-STEP route reading ``mercury-sulfide +
oxygen -> mercury + sulfur-dioxide``. S1 built the roast and found it makes the
OXIDE, re-labelled the row ``roasting-to-metal`` and left it uncovered, naming
what was missing: "a second reaction nobody built".

The second reaction is an ordinary row of ``SOLID_STATE_REACTIONS``. Neither
declaration mentions the other; they share one crystal in the solid block:

    surface.py       2 HgS + 3 O2 -> 2 HgO + 2 SO2
    solid_state.py   2 HgO        -> 2 Hg  +   O2
    ---------------------------------------------
    what runs          HgS +   O2 ->   Hg  +   SO2      the catalog row

⚠ These are integration tests over two TERMS and a real integrator, and every run
is at the tight tolerance, for the reason M6 measured on a vented kiln. They are
nonetheless CHEAP -- 4.2 s for the file, against ``test_solid_state.py``'s 24 --
because a retort is a sealed flask with no vent to stiffen it.
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
from chemsim.vessel.vessel import build_solid_state_arrays

CINNABAR = MINERALS["cinnabar"].lattice            # HgS
MONTROYDITE = MINERALS["montroydite"].lattice      # HgO
HG, O2, SO2, N2 = "[Hg]", "O=O", "O=S=O", "N#N"

CONVERGED = dict(rtol=1.0e-8, atol=1.0e-11)
DECOMPOSITION = "oxide-thermal-decomposition"


@pytest.fixture(scope="module")
def thermo():
    return ThermochemistryProvider()


@pytest.fixture(scope="module")
def net(thermo):
    return build_network(
        [CINNABAR, MONTROYDITE, HG, O2, SO2, N2], [],
        thermo=thermo, volatility=VolatilityProvider(thermo),
    )


def _decl(name):
    for d in ss.SOLID_STATE_REACTIONS:
        if d.name == name:
            return d
    raise AssertionError(name)


def _retort(net, T, *, charge, volume=10.0, oxygen_bar=1.0):
    """A SEALED retort with enough oxygen in it that nothing is O2-limited.

    Sealed on purpose: S1's roaster is vented, and a vent carries mercury out of
    the flask, so nothing about a conservation closure could be measured on one.
    """
    v = Vessel(net, volume=volume, T=T, T_env=T, UA=1.0e4, k_vent=0.0)
    v.charge({CINNABAR: charge}, phase="solid")
    v.charge({O2: oxygen_bar * volume / (R_L_BAR * T)}, phase="gas")
    return v


# ==========================================================================
# THE DECLARATION
# ==========================================================================

def test_the_decomposition_prices_off_the_two_tables(thermo):
    """HgO(s) from ``mineral_data``, Hg(g) and O2 from the ideal-gas basis.

    The subtraction is legal here for the reason the module docstring argues:
    every participant is in its own standard state. What makes THIS row worth a
    test of its own is that the gas half is an ELEMENT with a condensed
    reference state, so Hg(g)'s +61.40 kJ/mol is the number carrying the whole
    difference between an oxide and a metal.
    """
    p = ss.price(_decl(DECOMPOSITION), thermo)
    expect = (
        2.0 * thermo.get(HG).Hf - 2.0 * MINERALS["montroydite"].Hf_solid
    ) * 1000.0
    assert p.dH == pytest.approx(expect)
    assert p.dH / 1000.0 == pytest.approx(304.40, abs=0.01)
    assert p.dS == pytest.approx(414.60, abs=0.01)
    # Ea is DERIVED as max(dH, 0) -- an endothermic decomposition whose reverse
    # is barrierless. Nothing was declared.
    assert p.Ea == p.dH
    assert p.A == pytest.approx(1.93e18, rel=0.01)
    assert "CRC" in p.basis and "montroydite" in p.basis


def test_the_oxide_goes_at_689_K_against_the_room_and_the_retort_runs_at_900(net):
    """The catalog's own equipment column says ``retort, 900 K``.

    ⚠ The threshold is not ``K = 1 bar``: this row makes THREE moles of gas, so
    K carries bar^3 and the honest reference state is the three of them sharing
    the ambient pressure. CRC records HgO decomposing near 773 K, so this table
    runs it about 85 K cool -- the same direction and the same cause as every
    other row here, dCp = 0, stated in ``solid_state``.
    """
    arr, _ = build_solid_state_arrays(net.species)
    i = arr.names.index(DECOMPOSITION)
    assert float(arr.threshold_temperature(1.0)[i]) == pytest.approx(688.7, abs=0.5)
    # And it moves with the room, which is what makes it a mechanic: pull a
    # vacuum on the retort and the oxide goes 56 K cooler.
    assert float(arr.threshold_temperature(0.21)[i]) == pytest.approx(632.9, abs=0.5)


def test_the_two_clocks_and_where_they_CROSS(thermo):
    """⚠ NEITHER CONSTANT WAS CHOSEN WITH THE OTHER IN VIEW, and their ratio is
    the whole mechanic.

    ``ROASTING_EA`` is 150 kJ/mol, declared in S1 as the middle of the reported
    band for a sulfide oxidation. The decomposition's barrier is DERIVED as its
    own reaction enthalpy, 304.4 kJ/mol. Two barriers a factor of two apart mean
    the two clocks cross, and where they cross is what decides whether a retort
    gives the metal or the oxide.
    """
    roast = sf.price(
        next(d for d in sf.SURFACE_REACTIONS if d.name == "cinnabar-roasting"),
        thermo,
    )
    dec = ss.price(_decl(DECOMPOSITION), thermo)

    def clocks(T):
        C = 1.0 / (R_L_BAR * T)                       # 1 bar of pure oxygen
        # /2 because the roast is written per TWO formula units of sulfide.
        return (sf.time_constant(roast, T, C) / 2.0,
                1.0 / (dec.A * math.exp(-dec.Ea / (R * T))))

    tr, td = clocks(900.0)
    assert tr / td == pytest.approx(2.46e4, rel=0.05)     # the oxide is invisible
    tr, td = clocks(550.0)
    assert tr / td == pytest.approx(0.0298, rel=0.05)     # the oxide is the product
    # They are equal somewhere in between, and nothing declares that temperature.
    lo, hi = 550.0, 900.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        tr, td = clocks(mid)
        lo, hi = (mid, hi) if tr < td else (lo, mid)
    assert 0.5 * (lo + hi) == pytest.approx(611.7, abs=1.0)


def test_a_declaration_with_no_crystal_at_all_is_refused(thermo):
    """The one case ``units`` cannot bound on either side, refused at the
    declaration rather than discovered as an integrator failure."""
    bogus = ss.SolidStateReaction(
        name="bogus-all-gas", solids=(), gases=((SO2, +1),),
        mechanism="nothing", note="no crystal anywhere",
    )
    with pytest.raises(ss.UnpricedSolidReaction, match="no solid participants"):
        ss.price(bogus, thermo)


# ==========================================================================
# THE BOUND -- ``units`` over an empty product side
# ==========================================================================

def test_a_row_with_no_solid_product_gets_a_FINITE_reverse_bound(net):
    """And it is the reactant crystal, because deposition needs a seed."""
    arr, _ = build_solid_state_arrays(net.species)
    i = arr.names.index(DECOMPOSITION)
    nS = np.zeros(len(net.species))
    nS[net.species.index(MONTROYDITE)] = 0.1
    fwd, rev = arr.units(nS)
    assert math.isfinite(float(rev[i]))
    assert float(rev[i]) == float(fwd[i]) == 0.05      # 0.1 mol / 2 per unit


def test_the_bound_it_replaced_was_INFINITY_and_that_is_not_a_tautology(net):
    """The old expression, evaluated here so the fix has something to reject.

    ``rev`` was a minimum over the solids FORMED, and this row forms none.
    """
    arr, _ = build_solid_state_arrays(net.species)
    i = arr.names.index(DECOMPOSITION)
    nS = np.zeros(len(net.species))
    nS[net.species.index(MONTROYDITE)] = 0.1
    old = np.where(arr.formed > 0.0,
                   nS[None, :] / np.maximum(arr.formed, 1.0),
                   np.inf).min(axis=1)
    assert math.isinf(float(old[i]))
    assert not arr.has_formed[i]


def test_an_exhausted_charge_stops_BOTH_directions(net):
    """The nucleation gap, stated rather than worked around.

    Nothing here can grow a crystal out of a gas with no crystal present, so
    once the last of the oxide is gone the reverse is dead however cold and
    however full of mercury vapour the flask is.
    """
    arr, _ = build_solid_state_arrays(net.species)
    i = arr.names.index(DECOMPOSITION)
    fwd, rev = arr.units(np.zeros(len(net.species)))
    assert float(fwd[i]) == 0.0 and float(rev[i]) == 0.0


def test_the_four_pre_S4_rows_are_bit_for_bit_UNMOVED_by_the_fallback(thermo):
    """Every row that carries a crystal on both sides takes the raw minimum.

    Built on the lime network rather than the mercury one, so the assertion is
    about the four rows M6 and S3 measured and not about this file's.
    """
    lime = [MINERALS[m].lattice for m in
            ("calcite", "quicklime", "slaked lime", "green vitriol",
             "hematite", "nahcolite", "soda ash")]
    net = build_network(
        lime + ["O=C=O", "O", "O=S=O", "O=S(=O)=O"], [],
        thermo=thermo, volatility=VolatilityProvider(thermo),
    )
    arr, _ = build_solid_state_arrays(net.species)
    assert len(arr.names) == 4
    assert bool(arr.has_consumed.all()) and bool(arr.has_formed.all())
    rng = np.random.default_rng(4)
    for _ in range(5):
        nS = rng.random(len(net.species))
        fwd, rev = arr.units(nS)
        raw_f = np.where(arr.consumed > 0.0,
                         nS[None, :] / np.maximum(arr.consumed, 1.0),
                         np.inf).min(axis=1)
        raw_r = np.where(arr.formed > 0.0,
                         nS[None, :] / np.maximum(arr.formed, 1.0),
                         np.inf).min(axis=1)
        assert np.array_equal(fwd, raw_f)
        assert np.array_equal(rev, raw_r)


# ==========================================================================
# THE EQUILIBRIUM -- the charge that used to raise
# ==========================================================================

def test_a_sealed_retort_of_the_OXIDE_stalls_at_Q_equals_K(net):
    """⚠ THE RUN THAT USED TO DIE. 0.5 mol at 900 K crosses K and the reverse
    flux was ``negative * inf``; BDF got a NaN Jacobian and ``lu_factor`` raised.

    What it does instead is the thing this term exists to do: stop at ``Q = K``,
    with ``units`` dividing out so the stall does not depend on how much crystal
    is left. ``ln K`` is only +9.2 at 900 K, which is why a big enough charge in
    a small enough flask reaches it at all.
    """
    v = Vessel(net, volume=1.0, T=900.0, T_env=900.0, UA=1.0e4, k_vent=0.0)
    v.charge({MONTROYDITE: 0.5}, phase="solid")
    v.charge({N2: 1.0 / (R_L_BAR * 900.0)}, phase="gas")
    v.run(60.0, **CONVERGED)
    st = v.state()
    left = st.total(MONTROYDITE)
    assert 0.14 < left < 0.15                      # 71.8% converted
    assert st.total(HG) == pytest.approx(0.5 - left, rel=1e-9)

    p = v.partial_pressures()
    Q = p[HG] ** 2 * p[O2]
    K = math.exp(-(304400.0 - 900.0 * 414.60) / (R * 900.0))
    assert Q == pytest.approx(K, rel=0.01)

    # ...and it is an EQUILIBRIUM, not a slow approach: a hundred times longer
    # lands on the same state.
    v.run(6000.0, **CONVERGED)
    assert v.state().total(MONTROYDITE) == pytest.approx(left, rel=1e-6)


def test_a_smaller_charge_never_reaches_K_and_goes_to_completion(net):
    """The other side of the same mechanic, and the reason the bug hid: at
    0.05 mol in the same flask ``Q`` stays under ``K`` the whole way."""
    v = Vessel(net, volume=1.0, T=900.0, T_env=900.0, UA=1.0e4, k_vent=0.0)
    v.charge({MONTROYDITE: 0.05}, phase="solid")
    v.charge({N2: 1.0 / (R_L_BAR * 900.0)}, phase="gas")
    v.run(60.0, **CONVERGED)
    st = v.state()
    assert st.total(MONTROYDITE) == pytest.approx(0.0, abs=1e-12)
    assert st.total(HG) == pytest.approx(0.05, rel=1e-9)


# ==========================================================================
# THE ROUTE -- and NOTHING DECLARES IT
# ==========================================================================

def test_the_retort_runs_the_CATALOG_ROW_that_neither_declaration_writes(net):
    """``HgS + O2 -> Hg + SO2``, 1:1:1:1, out of a 2:3:2:2 and a 2:2:1.

    This is ``mercury-from-cinnabar`` step 1 in full, and it is the reason the
    class ``roasting-to-metal`` is credited. Compare ``solid-carbonation``,
    which was the first emergent credit: this is the first one where the
    emergent reaction IS a catalog row rather than a by-product of one.
    """
    v = _retort(net, 900.0, charge=0.02)
    v.run(400_000.0, **CONVERGED)
    st = v.state()

    assert st.total(CINNABAR) == pytest.approx(0.0, abs=1e-12)
    assert st.total(HG) == pytest.approx(0.02, rel=1e-9)
    assert st.total(SO2) == pytest.approx(0.02, rel=1e-9)
    # The row's own stoichiometry, and neither declaration has it: the roast is
    # 3 O2 per 2 HgS and the decomposition gives one of them back.
    assert st.total(HG) == pytest.approx(st.total(SO2), rel=1e-9)
    charged_O2 = 1.0 * 10.0 / (R_L_BAR * 900.0)
    assert charged_O2 - st.total(O2) == pytest.approx(0.02, rel=1e-6)

    # Mercury and sulfur both close on the charge, exactly.
    assert (st.total(CINNABAR) + st.total(MONTROYDITE)
            + st.total(HG)) == pytest.approx(0.02, abs=1e-12)
    assert st.total(CINNABAR) + st.total(SO2) == pytest.approx(0.02, abs=1e-12)


def test_the_oxide_is_a_REAL_intermediate_and_an_INVISIBLE_one(net):
    """Under 4e-5 of the charge, because its clock is 24,610x the roast's.

    The two constants that produce that ratio were declared one milestone apart,
    for different reactions, in different modules, and neither was chosen with
    the other in view.
    """
    v = _retort(net, 900.0, charge=0.02)
    peak = 0.0
    for _ in range(20):
        v.run(2_000.0, **CONVERGED)
        peak = max(peak, v.state().total(MONTROYDITE))
    assert 0.0 < peak < 1.0e-6
    assert v.state().total(HG) > 1.0e-3          # meanwhile the metal is coming


def test_COOLING_the_retort_gives_the_OXIDE_instead_and_nobody_wrote_that(net):
    """⚠ THE TWO CLOCKS CROSS, and the barrier ratio is what crosses them.

    The decomposition's Ea is 304 kJ/mol against the roast's 150, so cooling
    slows it far faster. Above the crossing the oxide is a trace and the retort
    gives the metal; below it the oxide piles up. Nothing gates on temperature
    anywhere -- this is two Arrhenius factors with different exponents.
    """
    def oxide_fraction(st):
        released = st.total(MONTROYDITE) + st.total(HG)
        return st.total(MONTROYDITE) / released

    # Run each one to roughly comparable conversion, since the clocks differ by
    # decades: what is compared is WHAT came out, not how fast.
    hot = _retort(net, 900.0, charge=0.02)
    hot.run(20_000.0, **CONVERGED)
    cold = _retort(net, 600.0, charge=0.02)
    cold.run(50_000_000.0, **CONVERGED)

    assert oxide_fraction(hot.state()) < 1.0e-5          # 2e-6: the METAL
    assert oxide_fraction(cold.state()) > 0.85           # 0.913: the OXIDE
    # Monotone in between, and nothing in the engine knows that: 900 K 2.0e-6,
    # 773 K 4.3e-4, 700 K 1.9e-2, 650 K 0.341, 600 K 0.913.
    mid = _retort(net, 700.0, charge=0.02)
    mid.run(1_000_000.0, **CONVERGED)
    assert (oxide_fraction(hot.state()) < oxide_fraction(mid.state())
            < oxide_fraction(cold.state()))


def test_the_mercury_CONDENSES_when_the_retort_is_cooled(net):
    """Which is what a retort is FOR, and it needs the curated Antoine.

    Mercury boils at 629.8 K, so it is entirely gas at the roasting temperature
    and entirely liquid in the receiver. ⚠ Lee-Kesler's curve for a liquid metal
    is 3.8x high at 523 K, so this panel would have been wrong by that factor
    with the estimated vapour pressure -- see ``volatility._CURATED_ANTOINE``.
    """
    v = _retort(net, 900.0, charge=0.02)
    v.run(400_000.0, **CONVERGED)
    assert v.state().n_liquid[HG] == pytest.approx(0.0, abs=1e-12)

    v.set_environment(400.0)
    v.run(50_000.0, **CONVERGED)
    st = v.state()
    assert st.T == pytest.approx(400.0, abs=0.5)
    assert st.n_liquid[HG] / 0.02 > 0.97         # a pool of the metal
    # ...and the OXIDE does not come back, though 400 K is 289 K below its
    # threshold. There is none left to grow on, which is the nucleation gap.
    assert st.n_solid[MONTROYDITE] == 0.0
