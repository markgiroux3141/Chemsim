"""Chain 2's chemistry: a catalytic CYCLE, its ceiling, and the wall next to it.

The mechanics pinned here are the ones nobody wrote down -- a carrier that turns
over 80 times, a temperature ceiling derived from formation data, and a cycle you
lose by opening the vessel. And the last two tests pin the WALL, because a
measured refusal is a result and results regress.
"""

from __future__ import annotations

import pytest

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.reactions import (
    ReactionTemplate,
    lead_chamber,
    nitric_oxide_reoxidation,
    sulfur_dioxide_oxidation,
)
from chemsim.vessel import Vessel


def c(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


S8 = c("S1SSSSSSS1")
SO2, NO, NO2 = c("O=S=O"), c("[N]=O"), c("[O-][N+]=O")
H2O, O2, N2 = c("O"), c("O=O"), c("N#N")
H2SO4 = c("OS(=O)(=O)O")

CHARGED_SO2 = 0.04
CHARGED_NOX = 0.004


@pytest.fixture(scope="module")
def thermo():
    return ThermochemistryProvider()


@pytest.fixture(scope="module")
def net(thermo):
    return build_network(
        [SO2, NO, NO2, H2O, O2, N2], lead_chamber(),
        thermo=thermo, volatility=VolatilityProvider(thermo), max_species=40,
    )


def chamber(net, T=350.0, k_vent=0.0, nox=CHARGED_NOX, duration=3600.0):
    v = Vessel(net, volume=2.0, T=T, T_env=T, UA=1.0e4, kla=5.0,
               k_vent=k_vent, k_diss=0.05, lle=False)
    v.charge({SO2: CHARGED_SO2, O2: 0.05, N2: 0.10, H2O: 0.60, NO2: nox})
    v.run(duration)
    return v


# ---------------------------------------------------------------------------
# the network
# ---------------------------------------------------------------------------
def test_the_network_is_bounded_and_stays_that_size(net):
    """The species bound the brief asked for.

    A self-feeding template is what explodes a network, not the number of
    templates -- one polyesterification reached 80 species while five alcohol
    templates give 10. Neither of these two regenerates its own matched group,
    so this number must not move; if it does, a template has started re-attacking
    its own products.
    """
    assert len(net.species) == 7
    assert len(net.reactions) == 4          # two forward, two derived reverses


def test_both_reverses_are_derived_and_not_declared(net):
    forward = {r.name for r in net.reactions if not r.name.endswith("_rev")}
    reverse = {r.name for r in net.reactions if r.name.endswith("_rev")}
    assert len(forward) == 2 and len(reverse) == 2
    for r in net.reactions:
        assert r.phase == "gas"


def test_the_reoxidation_barrier_is_negative_and_that_is_deliberate():
    """2 NO + O2 -> 2 NO2 runs through an ONOONO dimer and speeds up on cooling.

    Measured k = 1.2e-31 exp(+530/T) cm^6 molecule^-2 s^-1, so Ea = -R*530.
    Both parameters are SOURCED, which is rare in this library -- and a sign
    flip here would silently invert one of the two reasons a real lead chamber
    is run cool.
    """
    t = nitric_oxide_reoxidation()
    assert t.Ea < 0.0
    assert t.Ea == pytest.approx(-4400.0, abs=100.0)
    assert t.A == pytest.approx(4.35e10, rel=0.01)
    assert t.reversible


def test_the_core_step_makes_sulfuric_acid_and_not_bisulfate():
    """Two atom-level traps, each of which sanitised happily and was wrong.

    The oxygen transferred from NO2 arrives carrying its formal -1, so without
    ``[O+0...]`` the product is BISULFATE; and neutralising the charge without
    declaring the hydrogen count leaves an oxygen RADICAL on the sulfur. Neither
    raised anything -- both were caught by reading the product SMILES.
    """
    thermo = ThermochemistryProvider()
    n = build_network([SO2, NO2, H2O], [sulfur_dioxide_oxidation()],
                      thermo=thermo, max_species=20)
    products = {p for r in n.reactions if not r.name.endswith("_rev")
                for p in r.products}
    assert H2SO4 in products, "the core step must make H2SO4"
    assert NO in products
    assert c("[O-]S(=O)(=O)O") not in products, "bisulfate: the charge trap"
    assert "[O]S(=O)(=O)O" not in products, "an oxygen radical: the H-count trap"


# ---------------------------------------------------------------------------
# the mechanics that nobody wrote
# ---------------------------------------------------------------------------
def test_the_cycle_turns_and_the_yield_is_essentially_complete(net):
    st = chamber(net, T=350.0).state()
    assert st.total(H2SO4) == pytest.approx(CHARGED_SO2, rel=0.02)
    assert st.total(SO2) < 1.0e-4


def test_the_carrier_is_CATALYTIC_and_the_turnover_proves_it(net):
    """A reagent caps the product at what was charged. A catalyst does not.

    0.5 mmol of NOx makes 40 mmol of acid: 80 turnovers. This is the test that
    separates a real cycle from the FOLDED catalyst in ``library`` -- there,
    hydronium's net stoichiometry is zero because it sits on both sides of one
    SMARTS, and there is no cycle to count turnovers of.
    """
    st = chamber(net, nox=0.0005, duration=7200.0).state()
    turnovers = st.total(H2SO4) / 0.0005
    assert turnovers > 50.0, f"only {turnovers:.1f} turnovers"
    assert st.total(H2SO4) > 0.9 * CHARGED_SO2


def test_the_chamber_has_a_TEMPERATURE_CEILING_and_nobody_declared_one(net):
    """Above ~600 K the carrier sits as NO, which cannot oxidise SO2.

    The regeneration is written reversible, so ``2 NO2 -> 2 NO + O2`` takes over
    when it becomes favourable. There is no maximum operating temperature
    anywhere in this project: detailed balance derives it from the formation
    data. That is why a real lead chamber is a big cool room.
    """
    cool = chamber(net, T=350.0).state()
    hot = chamber(net, T=650.0).state()
    # cool: the carrier is oxidised and waiting to work
    assert cool.total(NO2) > 10.0 * cool.total(NO)
    # hot: it has flipped, and the flip is what costs yield
    assert hot.total(NO) > 10.0 * hot.total(NO2)
    assert hot.total(H2SO4) < cool.total(H2SO4)


def test_the_carrier_is_LOSABLE_by_opening_the_vessel(net):
    """The carrier is a gas, so the headspace-budget mechanic reaches it."""
    sealed = chamber(net, k_vent=0.0).state()
    vented = chamber(net, k_vent=1.0).state()
    assert sealed.total(H2SO4) == pytest.approx(CHARGED_SO2, rel=0.02)
    assert vented.total(H2SO4) < 0.5 * sealed.total(H2SO4)
    assert vented.total(NO) + vented.total(NO2) < \
        sealed.total(NO) + sealed.total(NO2)


def test_a_chamber_with_no_carrier_SPECIES_is_inert(net):
    """The honest baseline: no NOx in the NETWORK means no reaction at all.

    ``build_network`` cannot warn when a template matches nothing -- "matched
    nothing" is indistinguishable from a template that legitimately does not
    apply -- so this test is the warning. The historical process needed a nitre
    bed for exactly this reason.
    """
    thermo = ThermochemistryProvider()
    bare = build_network([SO2, H2O, O2, N2], lead_chamber(), thermo=thermo,
                         volatility=VolatilityProvider(thermo), max_species=40)
    assert len(bare.reactions) == 0
    assert H2SO4 not in bare.species
    v = Vessel(bare, volume=2.0, T=350.0, T_env=350.0, UA=1.0e4, kla=5.0,
               k_vent=0.0, k_diss=0.05, lle=False)
    v.charge({SO2: CHARGED_SO2, O2: 0.05, N2: 0.10, H2O: 0.60})
    v.run(3600.0)
    assert v.state().total(SO2) == pytest.approx(CHARGED_SO2, rel=1.0e-9)


def test_A_CATALYTIC_CYCLE_CANNOT_START_FROM_ZERO_CATALYST(net):
    """A chamber with no carrier does NOTHING. This is the assertion the bug hid.

    ⚠ **THIS REPLACES A TEST THAT PINNED A BUG.** Until the solid dissolution gate
    was fixed, a chamber charged with SO2, water and air and **no carrier at all**
    -- the carrier species present in the network but at exactly ZERO -- reached
    **89% yield**, on 1.2e-4 mol of NOx that nothing had put there. That test
    (``test_A_CATALYTIC_CYCLE_SEEDS_ITSELF_FROM_ROUND_OFF``) asserted the broken
    behaviour deliberately, so that fixing it would break a test and say so. It
    did, and this is what it was written instead of.

    ## What was wrong, and why a catalytic cycle is what found it

    Two halves, each individually correct. **The seed was a knee in the
    crystallisation term**: ``avail = nS/(nS + 1e-9)`` is zero at ``nS = 0`` but
    its slope there is 1e9, so an EMPTY solid block carried a Jacobian diagonal of
    ``k_diss * excess / eps`` -- measured at **-3.61e7 for NO, -3.95e7 for NO2 and
    H2SO4** on this very flask. BDF overshot those blocks negative,
    ``project_non_negative`` zeroed them, and a species with no positive holding to
    settle against had matter CREATED. **The amplification was the chemistry**: a
    catalytic cycle has no fixed gain on its catalyst (80 turnovers, measured
    above), so a round-off-sized carrier charge made a macroscopic amount of acid.
    296x.

    The drift was UNIVERSAL -- every undersaturated species' solid block had it,
    and the entry grew with the undersaturation, so the most dilute species got the
    worst of it. What was not universal was the damage: an esterification with no
    alcohol charged absorbed the same drift silently, because acetic acid's solid
    block settles against its own 0.83 mol liquid holding. **The precondition is a
    species near zero that is a CATALYST**, which is why three sessions of
    esterification chemistry never saw it and one afternoon of chain 2 did.

    ``SOLID_GATE_TIME`` is the fix: the gate's scale is now the driving force times
    a time rather than a constant, so the empty-block slope is exactly ``1/tau``
    for every species instead of growing with how dilute it is.

    ## What this test now asserts

    That nothing happens. Not "a little happens" -- the created NOx is **1.6e-20
    mol**, which is round-off on 0.11 mol of nitrogen, and the acid is the same
    number. A chamber with no carrier is inert, which is the physically correct
    answer and the one the chain's framing depends on: the nitre is a REAGENT you
    have to supply, and panel 3's 80 turnovers only mean something if zero
    turnovers is also reachable.

    ⚠ The bound below is deliberately loose in one direction and tight in the
    other. It does not pin 1.6e-20 -- that is a round-off value and will move with
    any solver change. It pins that the acid is **below the 1e-6 mol scale the
    game can see at all** (``SOLID_VISIBLE``), which is what "nothing happened"
    means to anything downstream.
    """
    v = Vessel(net, volume=2.0, T=350.0, T_env=350.0, UA=1.0e4, kla=5.0,
               k_vent=0.0, k_diss=0.05, lle=False)
    v.charge({SO2: CHARGED_SO2, O2: 0.05, N2: 0.10, H2O: 0.60})
    v.run(3600.0)
    st = v.state()

    created = st.total(NO) + st.total(NO2)
    assert created < 1.0e-9, (
        f"a carrier-free chamber created {created:.3e} mol of NOx from nothing. "
        f"This is the round-off-seeded-catalyst bug returning -- look at the "
        f"solid dissolution gate's Jacobian diagonal (SOLID_GATE_TIME) first"
    )
    assert st.total(H2SO4) < 1.0e-6, (
        f"a carrier-free chamber made {st.total(H2SO4):.3e} mol of acid. The "
        f"chain's whole framing is that the nitre is a reagent you must supply"
    )
    # the SO2 is all still there, unconverted
    assert st.total(SO2) == pytest.approx(CHARGED_SO2, rel=1.0e-6)
    # and with nothing created, conservation is now CLEAN rather than reported
    assert not v.conservation_report()


def test_sulfur_and_the_carrier_BOTH_close_exactly(net):
    """Both elements close, and the carrier's old residual is gone.

    ⚠ **THIS TEST WAS LOOSER THAN IT IS NOW, AND THE SLACK WAS THE SAME BUG.**
    It used to allow the carrier's nitrogen 2% and assert only that any residual
    was REPORTED, because the projection created ~2e-5 mol of NO it could not
    take back -- ~0.5% of a 4 mmol charge. That is the solid-gate knee of
    ``test_A_CATALYTIC_CYCLE_CANNOT_START_FROM_ZERO_CATALYST``, seen at a charge
    four orders larger than the one that made it obvious. ``SOLID_GATE_TIME``
    closed both, and nothing in this chamber was touched to do it.

    So the tolerances are now tight in both places and the report must be EMPTY.
    A residual coming back here is the same defect returning at a magnitude the
    carrier-free test would not catch, which is why this is worth asserting
    separately rather than folding into that one.
    """
    v = chamber(net, T=350.0)
    st = v.state()
    assert st.total(SO2) + st.total(H2SO4) == pytest.approx(
        CHARGED_SO2, rel=1.0e-6
    )
    assert st.total(NO) + st.total(NO2) == pytest.approx(
        CHARGED_NOX, rel=1.0e-6
    )
    assert not v.conservation_report()


# ---------------------------------------------------------------------------
# THE BURNER, WHICH SHIPS NOW -- and the wall that moved one level down
# ---------------------------------------------------------------------------
def _burner(A: float, orders=(1.0, 1.0) + (0.0,) * 7) -> ReactionTemplate:
    """The burner, with ``orders=None`` recovering the old mass-action form."""
    ring = "[S:1]1[S:2][S:3][S:4][S:5][S:6][S:7][S:8]1"
    o2 = ".".join(f"[OX1:{9 + 2 * i}]=[OX1:{10 + 2 * i}]" for i in range(8))
    so2 = ".".join(f"[O:{9 + 2 * i}]=[S:{1 + i}]=[O:{10 + 2 * i}]"
                   for i in range(8))
    return ReactionTemplate(name="sulfur_combustion",
                            smarts=f"{ring}.{o2}>>{so2}",
                            A=A, Ea=100_000.0, phase="gas", orders=orders)


def _burn(thermo, tmpl, T, charge, t=600.0, chunks=1, **kw):
    """``**kw`` reaches ``run``, which is how ``atol`` gets refined below."""
    n = build_network([S8, O2, N2], [tmpl], thermo=thermo,
                      volatility=VolatilityProvider(thermo), max_species=40)
    v = Vessel(n, volume=1.0, T=T, T_env=T, UA=1.0e4, kla=5.0,
               k_vent=0.0, k_diss=0.05, lle=False)
    v.charge(charge)
    for _ in range(chunks):
        v.run(t / chunks, **kw)
    return v


def test_the_declared_order_is_what_reaches_the_kernel(thermo):
    """ORDER and DELTA come apart, and only the exponent moves.

    Eight oxygens are still CONSUMED -- the stoichiometry is not negotiable and
    the element balance depends on it -- but ONE appears in the rate law. The
    kernel has always carried ``order`` as a matrix separate from ``delta`` and
    simply never had anything to put in it, so Layer 4 needed no change at all.
    """
    n = build_network([S8, O2, N2], [_burner(1.0e10)], thermo=thermo,
                      volatility=VolatilityProvider(thermo), max_species=40)
    assert len(n.species) == 4 and len(n.reactions) == 1
    arr = n.to_arrays()
    idx = {s: i for i, s in enumerate(n.species)}
    order, delta = arr.order[0], arr.delta[0]
    assert order[idx[S8]] == pytest.approx(1.0)
    assert order[idx[O2]] == pytest.approx(1.0)     # was 8.0, and that was the wall
    assert order.sum() == pytest.approx(2.0)        # was 9.0
    # ...while the stoichiometry is untouched
    assert delta[idx[S8]] == pytest.approx(-1.0)
    assert delta[idx[O2]] == pytest.approx(-8.0)
    assert delta[idx[SO2]] == pytest.approx(8.0)
    # and the OLD form is still reachable, so the comparison below is like-for-like
    old = build_network([S8, O2, N2], [_burner(1.0e10, orders=None)],
                        thermo=thermo, volatility=VolatilityProvider(thermo),
                        max_species=40).to_arrays()
    assert old.order[0].sum() == pytest.approx(9.0)


def test_the_LIMITING_case_has_stopped_reading_the_pre_exponential(thermo):
    """⚠ THE RESULT THAT MADE THE BURNER SHIPPABLE. This test used to assert the
    opposite.

    With O2 limiting, the ninth-order form gave 86.5% at A = 1e20 and 96.4% at
    A = 1e24: [O2]^8 stalls asymptotically, the last oxygen never burns, and the
    yield was a reading of the author's pre-exponential rather than of the
    chemistry. That corrupts the headspace-budget gate, which is one of the six
    purity gates that already work, and it is why the burner was refused.

    Declared first order in oxygen, the same charge burns out completely across
    FIVE DECADES of A. Below 1e7 it falls off, and that is not a stall returning
    -- it is honest kinetics, the burn simply not finishing inside ten minutes.
    """
    charge = {S8: 0.02, O2: 0.10, N2: 0.02}     # needs 0.16 O2; O2 is limiting
    for A in (1.0e8, 1.0e9, 1.0e10, 1.0e11):
        got = _burn(thermo, _burner(A), 650.0, charge).state().total(SO2)
        assert got == pytest.approx(0.10, rel=1.0e-4), f"A={A:g}"

    # ⚠ AND THE FAILURE MODE AT THE ENDS IS A DIFFERENT ONE, which is the point.
    # The old form failed by STALLING: [O2]^8 never finished however long you
    # waited, so the yield read A. This one fails by not being FINISHED, which
    # is what a rate constant is supposed to mean -- at A = 1e7 the same charge
    # reaches 0.0930 at 650 K and 0.0012 at 550 K, i.e. the burn is simply slow.
    slow = _burn(thermo, _burner(1.0e7), 650.0, charge).state().total(SO2)
    assert 0.08 < slow < 0.098, f"the slow end moved: {slow:.6f}"
    # Ten times as long and it FINISHES, which a stall never does. The tolerance
    # here is 1e-3 rather than the 1e-4 above, and the slack is the ordinary
    # reported round-off residual (+1.6e-4) rather than anything about the rate
    # law -- see the dryout-band test for how the two are told apart.
    assert _burn(thermo, _burner(1.0e7), 650.0, charge, t=6000.0
                 ).state().total(SO2) == pytest.approx(0.10, rel=1.0e-3), (
        "given ten times as long the slow burn must FINISH -- if it does not, "
        "the rate law is stalling again rather than merely being slow"
    )


def test_the_burn_needs_heat_and_the_threshold_is_SOFT(thermo):
    """Sulfur does not burn cold, and the shipped parameters say where it does.

    ⚠ **BOTH PARAMETERS ARE HAND-AUTHORED** and the rate law is an APPARENT one
    -- real sulfur combustion is a branched chain, not a bimolecular collision.
    They are bounded rather than fitted: ``A = 1e10 L/(mol s)`` is pinned to the
    order of the gas-kinetic collision limit so it cannot be dialled to taste,
    which leaves ``Ea`` as the only freedom.

    The cost of that discipline is a SOFT threshold, asserted here rather than
    tuned away: 68% at 500 K is more than real sulfur does below its ~523 K
    ignition point. A sharper knee needs A = 1e14, a thousand times the collision
    limit, and buying a prettier threshold with an impossible pre-exponential is
    the wrong trade.
    """
    excess = {S8: 0.02, O2: 0.40, N2: 0.02}     # 0.16 needed, so S8 is limiting

    def yield_at(T):
        return _burn(thermo, _burner(1.0e10), T, excess).state().total(SO2) / 0.16

    # cold: nothing. 4.3e-14 mol at 298 K, 3.2e-9 at 350 K.
    assert yield_at(298.15) < 1.0e-9
    assert yield_at(350.0) < 1.0e-6
    # molten but not lit: real, and tiny. 0.0034% at 400 K, 0.95% at 450 K.
    assert yield_at(400.0) < 1.0e-3
    assert 1.0e-3 < yield_at(450.0) < 0.05
    # ...and complete once lit
    for T in (550.0, 600.0, 650.0):
        assert yield_at(T) == pytest.approx(1.0, rel=1.0e-4), f"T={T}"
    # THE SOFT EDGE, pinned as the honest cost rather than hidden
    assert 0.5 < yield_at(500.0) < 0.85, f"the 500 K shoulder moved: {yield_at(500.0)}"


def test_a_DECLARED_ORDER_MAY_NOT_BE_REVERSIBLE_and_is_refused(thermo):
    """The decision, made deliberately and enforced at construction.

    ``detailed_balance`` derives the reverse from ``k_f / k_r = K(T)``, and that
    identity holds only because the forward and reverse exponents ARE the
    stoichiometric coefficients -- it is what makes the ratio of the two rate
    laws equal the mass-action quotient. With an apparent order it is not, so a
    derived "reverse" would reach the WRONG equilibrium while looking exactly
    like one that does not. That is the silent-wrong-answer shape this project
    refuses, so it is refused at template construction rather than at build time.

    The burner does not need it: ln K = 988.
    """
    with pytest.raises(ValueError, match="incompatible"):
        ReactionTemplate(name="x", smarts="[S:1]=[O:2]>>[S:1][O:2]", A=1.0,
                         Ea=0.0, orders=(1.0,), reversible=True)
    # one exponent per SLOT, not per species -- a mismatch is a refusal
    with pytest.raises(ValueError, match="reactant slots"):
        ReactionTemplate(name="x", smarts="[S:1]=[O:2].[O:3]=[O:4]>>[S:1][O:2]",
                         A=1.0, Ea=0.0, orders=(1.0,))
    # and a negative order is inhibition, which this kernel cannot express
    with pytest.raises(ValueError, match="negative rate order"):
        ReactionTemplate(name="x", smarts="[S:1]=[O:2]>>[S:1][O:2]", A=1.0,
                         Ea=0.0, orders=(-1.0,))


def test_the_dryout_band_is_CLOSED_and_what_is_left_is_the_DEPLETED_REACTANT(
    thermo,
):
    """⚠ THE WALL IS DOWN, and this test is the inversion of the one that pinned it.

    Sulfur boils at 717.8 K, so a burn run NEAR that holds only a TRACE of
    condensate. That trace used to land inside ``DRYOUT_MOLES`` (1e-6 mol) where
    THREE terms overlapped: layer 1's evaporation gated by a ``wet`` ramp, the
    dry-flask branch by ``1 - wet``, and the mole fractions floored on the SAME
    scale -- so inside the band they summed to 0.57, every activity was
    understated by that factor, and the solve CREATED oxygen:

        T / K    liquid held     created O, before   after
          550     6.85e-03 mol        1.8e-12        1.2e-15
          650     1.52e-03            1.1e-09        8.1e-11
          675     8.29e-07  IN BAND   2.3e-03        5.6e-07
          690     5.43e-07  IN BAND   1.1e-01        2.9e-05   read 111% yield
          700     5.73e-07  IN BAND   2.9e-05        3.1e-06
          730     3.81e-07            2.0e-09        5.2e-06

    ``_dryout_gates`` and ``MOLE_FRACTION_DENOM`` are the fix and they argue
    themselves. What this test has to establish is the harder half: **that the
    residual still in the right-hand column is a DIFFERENT residual, and not a
    smaller version of the same one.** Three measurements say so.

    ## 1. With nothing driven to zero, the evaporation path is EXACT

    Make oxygen non-limiting -- same flask, same trace of condensate, but the
    reaction stops before anything empties -- and 690 K reads **1.9e-11**, against
    the 1.1e-01 it read in the band. The gates are not approximately better; on
    their own they are clean to eleven decimals.

    ## 2. What is left is the OXYGEN CROSSING ZERO, measured by removing it

    O2 limiting ends at exactly 0.000e+00 and reads 2.9e-05; O2 in excess ends
    holding 8.4e-02 and reads 1.9e-11 at the same temperature. That is the
    ordinary stiff-reactant-at-zero residual this project reports everywhere and
    which ``docs/history/MILESTONES.md`` M7 owns -- the same one the 600 K case below has read
    at the 1e-4 level all along, nowhere near any band.

    ## 3. ⚠ AND ITS VALUE AT DEFAULT TOLERANCE IS LUCK, SO NOTHING ASSERTS ONE

    This is the trap the previous session wrote down (``a tolerance tight enough
    to be luck is worse than no tolerance``) and it applies to the OLD numbers in
    the table above as much as to the new. Nudging the charge of NITROGEN -- which
    takes no part in the burn and cannot move a real conservation property, only
    the solver's step selection:

        n(N2)     730 K dO     690 K dO
        0.0200     5.23e-06     2.94e-05
        0.0201     2.73e-04     3.46e-06
        0.0202     5.31e-06     1.22e-05
        0.0205     4.47e-04     1.00e-05
        0.0210     2.55e-09     9.76e-06

    Five orders of magnitude from an inert species. So the old 730 K = 2.0e-09 was
    where the solver happened to land and never was an invariant -- **reported as
    a finding rather than retyped**. The stable statements are the two above plus
    convergence, and those are what is asserted.

    ## The diagnostic that separated them, kept because it still separates them

    A ROUND-OFF RESIDUAL CONVERGES UNDER REFINEMENT; A STRUCTURAL DEFECT DOES NOT.

        690 K, the BAND    atol 1e-9  1.10e-01 -> 1e-11  5.0e-09 -> 1e-14  7.4e-04
        690 K, now         atol 1e-9  2.94e-05 -> 1e-12  6.0e-10 -> 1e-14  2.5e-12
        600 K, round-off   atol 1e-9  1.84e-04 -> 60 chunks 2.5e-14

    The band was non-monotone in ``atol`` and untouched by chunking. What is left
    is monotone in ``atol``, which is what says the structural defect is gone.
    """
    charge = {S8: 0.02, O2: 0.10, N2: 0.02}
    # S8 limiting instead: the reaction stops before O2 empties, so NOTHING is
    # driven to zero and the only thing left acting is the evaporation pair.
    charge_excess_O2 = {S8: 0.002, O2: 0.10, N2: 0.02}

    def created(T, charge=charge, **kw):
        v = _burn(thermo, _burner(1.0e10), T, charge, **kw)
        st = v.state()
        O_in = 2 * charge[O2]
        return (2 * st.total(O2) + 2 * st.total(SO2) - O_in) / O_in, v

    # the window sulfur_combustion() documents, at the ends where it is exact
    for T in (550.0, 650.0):
        dO, _ = created(T)
        assert abs(dO) < 1.0e-6, (
            f"the shipped burner window is no longer clean at {T} K ({dO:.3e})"
        )

    # ⚠ 1. THE BAND ITSELF, WHICH USED TO READ 111% YIELD. With nothing else
    # driven to zero the flask holds its trace of condensate and conserves.
    dO_band, v = created(690.0, charge_excess_O2)
    assert abs(dO_band) < 1.0e-9, (
        f"690 K held a trace of condensate and did not conserve ({dO_band:.3e}) "
        f"-- this is the dryout band and it is supposed to be CLOSED"
    )
    assert v.conservation_report() == "", "and the projection must have nothing to do"
    # ...and the state that used to be advertised as a live wrong answer no longer
    # is. The fragility entry was REMOVED WITH THIS ASSERTION, deliberately: the
    # solve succeeds and a warning that no longer describes anything is worse than
    # none. ``diagnose`` still names the crossover, but diagnose runs on failure.
    assert "dryout band" not in (v.integrability_report() or ""), (
        "the retired fragility entry is back; if the band has REOPENED that is "
        "the finding, and if it has not then this warning is describing nothing"
    )

    # ⚠ 2. what is left with O2 limiting is the OXYGEN, and refining says so
    dO_lim, v_lim = created(690.0)
    assert float(v_lim.state().total(O2)) == 0.0, (
        "this case is only interesting while the oxygen is driven to exactly zero"
    )
    dO_refined, _ = created(690.0, atol=1.0e-12)
    assert abs(dO_refined) < 1.0e-8 < abs(dO_lim), (
        f"the remaining 690 K residual must CONVERGE under refinement "
        f"({dO_lim:.3e} -> {dO_refined:.3e}); non-convergence is what made the "
        f"band structural, and it is the only reason to call this one round-off"
    )

    # ...where the ordinary residual at 600 K, which was never in the band,
    # converges under CHUNKING as well. That contrast is the original diagnostic.
    dO_600, _ = created(600.0)
    dO_600_chunked, _ = created(600.0, chunks=60)
    assert abs(dO_600) > 1.0e-5 and abs(dO_600_chunked) < 1.0e-8, (
        f"the 600 K residual should CONVERGE under chunking "
        f"({dO_600:.3e} -> {dO_600_chunked:.3e}); that contrast is the diagnostic"
    )


def test_the_low_order_workaround_is_blocked_by_the_element_table(thermo):
    """S8 <=> 4 S2 then S2 + 2 O2 -> 2 SO2 is third order and well posed.

    It needs S2, and S2 REFUSES: its formation half is measured and good
    (Hf +128.60, Gf +79.70, both CRC) but no source has a Tb, Tc or Pc for a
    diatomic that never condenses as itself. Inventing two critical constants to
    get past that is exactly the confident estimate of an unmeasured quantity
    that ``element_data`` exists to prevent -- so the block is correct, and this
    test says so rather than leaving it looking like an oversight.

    ⚠ Kept after the burner shipped, because it is now the record of a road NOT
    taken: the declared order made the honest route work instead of the clever
    one, and the clever one is still blocked for the same good reason.
    """
    with pytest.raises(ValueError, match="ELEMENTAL"):
        thermo.get("S=S")
