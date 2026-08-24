"""Layers 4/5 -- coupled vessels: reflux, distillation, and what edges must obey.

The claim being tested is not that a condenser was implemented. It is that no
condenser was *needed*: vapour arriving in a cold vessel finds ``p > p_eq``, the
existing evaporation term runs backwards, latent heat comes back out, and a
thermal edge carries it away. All this module added was a way for two vessels to
see each other. The azeotrope test at the bottom is the sharpest evidence.
"""

import numpy as np
import pytest

from chemsim.network import build_network
from chemsim.numerics.rig_integrator import DRAIN, THERMAL, VAPOUR
from chemsim.properties import ThermochemistryProvider
from chemsim.reactions import ReactionTemplate
from chemsim.vessel import Rig, Vessel

ETOH, WATER = "CCO", "O"
# N2/O2 are in the network so the room's atmosphere is fully represented and the
# vessels can exchange bulk gas with it -- see ``Vessel.atmosphere_report``.
AIR = ["N#N", "O=O"]


@pytest.fixture(scope="module")
def net():
    return build_network(
        [ETOH, WATER, *AIR], [], thermo=ThermochemistryProvider(), max_species=30
    )


FISCHER = ReactionTemplate(
    name="fischer",
    smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
           ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
    A=1.0e6, Ea=50_000, reversible=True,
)


@pytest.fixture(scope="module")
def reactive_net():
    return build_network(
        ["CC(=O)O", ETOH, WATER], [FISCHER], thermo=ThermochemistryProvider()
    )


# ---------------------------------------------------------------------------
# the guard that protects every Layer 5 result
# ---------------------------------------------------------------------------


def _charged(net, **kw):
    v = Vessel(net, volume=1.0, T=330.0, T_env=330.0, UA=2.0, kla=5.0,
               Q_input=20.0, **kw)
    v.charge({"CC(=O)O": 3.0, ETOH: 3.0})
    v.fill_headspace_with_air()
    return v


def test_a_one_vessel_rig_is_bit_identical_to_a_lone_vessel(reactive_net):
    """The cheapest possible guard against this work regressing all of Layer 5.
    A rig with no edges must add exactly nothing -- not "agree closely", but
    reproduce the same floating-point numbers, because it runs the same RHS on
    the same state through the same solver.

    ``jac_sparsity`` is switched off to make that literal: supplying it changes
    how ``num_jac`` groups its finite differences, which moves the last couple
    of digits. That is a solver path difference, not a physics one, and the test
    below pins it at the tolerance the solver was asked for.
    """
    solo = _charged(reactive_net)
    solo.run(1200.0)

    rig = Rig()
    rig.add("only", _charged(reactive_net))
    rig.run(1200.0, jac_sparsity=None)
    caged = rig.vessels["only"]

    assert caged.T == solo.T
    for s in reactive_net.species:
        assert caged.state().n_liquid[s] == solo.state().n_liquid[s], s


def test_the_sparsity_pattern_only_costs_solver_tolerance(reactive_net):
    """And for a ONE-vessel rig it now costs nothing at all, because a single dense
    block groups nothing and ``useful_sparsity`` therefore declines to pass it --
    see ``test_sparsity_is_only_passed_when_it_buys_column_GROUPS``. The tolerance
    is kept rather than tightened to an equality, because what is being pinned is
    that a solver-path difference stays a solver-path difference."""
    solo = _charged(reactive_net)
    solo.run(1200.0)

    rig = Rig()
    rig.add("only", _charged(reactive_net))
    rig.run(1200.0)                      # default: whatever the gate decides

    assert rig.vessels["only"].T == pytest.approx(solo.T, rel=1e-6)
    assert rig.integrator().useful_sparsity() is None


def test_the_sparsity_pattern_marks_the_diagonal_and_connected_pairs(net):
    rig = Rig()
    for name in ("a", "b", "c"):
        rig.add(name, Vessel(net, volume=1.0))
    rig.vapour("a", "b")

    integ = rig.integrator()
    s = integ.jac_sparsity()
    B, n = integ.block, integ.n

    assert s[:B, :B].all() and s[B : 2 * B, B : 2 * B].all()
    assert not s[:B, 2 * B :].any(), "a and c are not connected"
    # A vapour edge reaches b's GAS rows and its T row from all of a's columns...
    assert s[B + 2 * n : B + 3 * n, :B].all(), "a and b are connected"
    assert s[B + 4 * n, :B].all()
    # ... and NOT b's liquid or solid rows, which is the whole saving.
    assert not s[B : B + 2 * n, :B].any(), "a vapour edge moves no liquid"
    assert not s[B + 3 * n : B + 4 * n, :B].any(), "and no solid"


def test_sparsity_is_only_passed_when_it_buys_column_GROUPS(net):
    """⚠ THE MEASUREMENT THAT KILLED AN EXPECTED LEVER, and the finding is the
    negative one.

    ``jac_sparsity`` only ever buys column GROUPS -- ``num_jac`` perturbs together
    any columns sharing no non-zero row -- so a group count equal to the state size
    means the sparse path does the dense amount of work and pays sparse ``num_jac``
    and sparse LU on top. For a pot and a receiver joined by a VAPOUR edge, which
    is the topology every slow test in this file has, that is exactly what happens,
    and the reason is physical rather than a marking mistake: a vapour edge is
    driven by a pressure, a pressure divides by the GAS VOLUME, and the gas volume
    is what the liquid and solid do not occupy -- so the receiver's gas rows depend
    on every amount in the donor.

    A rig with a thermal-only leg is different, because a thermal edge touches two
    temperature rows and nothing else. So the pattern is passed when it earns its
    keep and skipped when it does not.
    """
    from scipy.optimize._numdiff import group_columns
    from scipy.sparse import csc_matrix

    pair = Rig()
    pair.add("pot", Vessel(net, volume=1.0))
    pair.add("recv", Vessel(net, volume=0.5))
    pair.vapour("pot", "recv")
    integ = pair.integrator()
    s = integ.jac_sparsity()
    assert int(group_columns(csc_matrix(s)).max()) + 1 == s.shape[0], (
        "two vapour-coupled vessels are an honestly dense Jacobian"
    )
    assert integ.useful_sparsity() is None, "so the pattern must not be passed"

    still = Rig()
    for name in ("pot", "head", "bath", "recv"):
        still.add(name, Vessel(net, volume=1.0))
    still.vapour("pot", "head")
    still.drain("head", "pot")
    still.thermal("head", "bath")
    still.vapour("head", "recv")
    integ = still.integrator()
    s = integ.jac_sparsity()
    groups = int(group_columns(csc_matrix(s)).max()) + 1
    assert groups < s.shape[0], f"{groups} of {s.shape[0]} -- should group"
    assert integ.useful_sparsity() is not None


def test_the_sparsity_pattern_is_a_SUPERSET_of_the_real_jacobian(net):
    """⚠ UNDER-MARKING IS SILENTLY WRONG ANSWERS, so the pattern is not trusted to
    the reasoning that produced it -- the Jacobian is differenced on a live rig
    state and every entry that matters has to be marked.

    This is the test that makes the refined pattern safe. It is deliberately run
    on a rig that is doing something (boiling, condensing, draining, exchanging
    heat) rather than on a settled one, because an idle rig has a nearly empty
    Jacobian and would confirm any pattern at all.
    """
    rig = Rig()
    hot = rig.add("hot", Vessel(net, volume=1.0, T=350.0, T_env=350.0, UA=2.0,
                                kla=5.0, Q_input=40.0))
    cold = rig.add("cold", Vessel(net, volume=0.5, T=290.0, T_env=290.0, UA=20.0,
                                  kla=5.0))
    rig.vapour("hot", "cold", k=3.0)
    rig.drain("cold", "hot", k=0.4)
    rig.thermal("cold", "hot", UA=1.0)
    hot.charge({ETOH: 2.0, WATER: 2.0})
    hot.fill_headspace_with_air()
    cold.charge({WATER: 0.2})
    cold.fill_headspace_with_air()
    rig.step(30.0)                      # get real fluxes flowing

    integ = rig.integrator()
    rhs = integ.make_rhs()
    y = integ.pack([
        v.integrator.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
        for v in rig.vessels.values()
    ])
    f0 = rhs(0.0, y)
    s = integ.jac_sparsity()

    # Central differences on a relative step, column by column. Compared against
    # the column's own scale, so a row that is small only because that whole
    # column is small does not count as a missing entry.
    missing = []
    for j in range(y.size):
        h = 1.0e-7 * max(abs(y[j]), 1.0e-3)
        yp, ym = y.copy(), y.copy()
        yp[j] += h
        ym[j] -= h
        col = (rhs(0.0, yp) - rhs(0.0, ym)) / (2.0 * h)
        scale = float(np.abs(col).max())
        if scale <= 0.0:
            continue
        for i in np.flatnonzero(np.abs(col) > 1.0e-6 * scale):
            if not s[i, j]:
                missing.append((int(i), j, float(col[i]) / scale))
    assert not missing, (
        f"{len(missing)} Jacobian entries are non-zero but unmarked, e.g. "
        f"{missing[:5]} -- jac_sparsity is UNDER-marking and BDF is being handed "
        "a wrong Jacobian"
    )
    del f0


# ---------------------------------------------------------------------------
# what each edge must obey
# ---------------------------------------------------------------------------


def test_a_vapour_edge_conserves_matter(net):
    rig = Rig()
    hot = rig.add("hot", Vessel(net, volume=1.0, T=340.0, T_env=340.0, UA=1.0,
                                kla=5.0, k_vent=0.0))
    rig.add("cold", Vessel(net, volume=1.0, T=290.0, T_env=290.0, UA=1.0,
                           kla=5.0, k_vent=0.0))
    rig.vapour("hot", "cold", k=5.0)
    hot.charge({ETOH: 3.0})

    before = {s: hot.state().total(s) for s in net.species}
    rig.run(600.0)

    # The species carrying the material is conserved to ~3e-11 relative, which
    # is solver noise on rtol=1e-6 and is the CONVERGED value for this edge.
    #
    # ⚠ THIS BOUND USED TO READ 1e-12, AND IT WAS MEASURING A LUCKY SOLVER PATH
    # RATHER THAN CONSERVATION. It was written when this run happened to close to
    # -4.3e-15, and the docstring claimed "machine precision" on the strength of
    # that. Changing the solid dissolution gate (SOLID_GATE_TIME) moved the
    # solver's path and it came back -4.5e-11, which looked like a regression and
    # was not. Refining says so:
    #
    #     gate       atol 1e-9      atol 1e-11     atol 1e-13
    #     OLD         -4.293e-15     2.555e-11      3.494e-11
    #     NEW         -4.512e-11     2.556e-11      3.494e-11
    #
    # **The two gates agree to four significant figures once refined.** The
    # converged error of this configuration is ~3e-11 either way; -4.3e-15 was a
    # coincidence at the default tolerance. The new value is also insensitive to
    # the gate's own constant across four decades (-4.512e-11 at tau = 1e-3, 1e-2,
    # 1e-1 and 1.0 alike), which says the residual is the VAPOUR EDGE and not the
    # gate at all.
    #
    # So the bound is set where the measurement is, with room for the path to
    # wander. A tolerance tight enough to be luck is worse than no tolerance: it
    # fails on unrelated changes and says nothing when it passes.
    assert sum(v.total(ETOH) for v in rig.state().values()) == pytest.approx(
        before[ETOH], rel=1e-9
    )
    # And so is a species sitting at exactly zero. This assertion used to be
    # `abs=1e-5`, bounding a defect instead of fixing it: the final state was
    # clamped with `np.maximum(y, 0)`, and water finished this very run with its
    # solid block at -1.26e-6 and its liquid at +1.02e-6 -- a cancelling pair
    # that summed to nothing. Clamping the negative half alone CREATED 1.26e-6
    # mol of water in a vessel that never held any. The trajectory itself was
    # always conservative; only the projection was not. It is now a
    # total-preserving projection (numerics.project_non_negative), so the
    # tolerance here is the solver's, not the clamp's.
    #
    # ⚠ THE ABSOLUTE BOUND IS THE ONE THAT MATTERS HERE AND THE RELATIVE ONE IS
    # NOT A WEAKENING. `abs=1e-12` is what catches created matter in a vessel
    # that never held any -- water's 1.26e-6 above -- and it must stay. But
    # applied alone it also demanded 1e-12 ABSOLUTE on ethanol's 3 mol, i.e.
    # 3e-13 relative, which is below what the solver delivers (~3e-11 converged;
    # see the comment above). `approx` takes the LARGER of the two, so this reads
    # 1e-12 for a species holding nothing and 3e-9 for one holding 3 mol -- which
    # is what each of them is actually being asked.
    for s in net.species:
        after = sum(v.total(s) for v in rig.state().values())
        assert after == pytest.approx(before[s], abs=1e-12, rel=1e-9), s
    # ... and nothing went negative to achieve it.
    for state in rig.state().values():
        for block in (state.n_liquid, state.n_gas, state.n_solid):
            assert min(block.values()) >= 0.0


def test_the_projection_conserves_a_cancelling_pair_rather_than_clamping_it(net):
    """The unit case behind the run above, stated directly.

    A species split as (+1e-6 liquid, -1e-6 solid) holds nothing: the negative
    entry is one half of a numerical dipole, not a deficit. A hard clamp keeps the
    positive half and creates 1e-6 mol; the projection cancels the pair. The
    distinction is invisible on species carrying real material and is the whole
    error on species sitting at zero, which is why it went unnoticed.
    """
    from chemsim.numerics.vessel_integrator import project_non_negative

    liquid = np.array([5.0, 1.0e-6])
    gas = np.array([0.0, 0.0])
    solid = np.array([0.0, -1.0e-6])
    (nL, nG, nS), created = project_non_negative([liquid, gas, solid])

    assert (nL >= 0).all() and (nG >= 0).all() and (nS >= 0).all()
    assert nL[1] + nG[1] + nS[1] == pytest.approx(0.0, abs=1e-18)
    assert nL[0] == 5.0                       # untouched species stays untouched
    assert created.max() == 0.0               # nothing had to be invented


def test_a_species_with_a_negative_total_is_reported_not_hidden(net):
    """Round-off can leave a species' total slightly negative, and then there is
    no positive holding to settle against -- that residual really is created. It
    is returned rather than swallowed, because a silent adjustment is exactly what
    this projection exists to stop."""
    from chemsim.numerics.vessel_integrator import project_non_negative

    (nL, nG, nS), created = project_non_negative([
        np.array([-1.0e-3]), np.array([0.0]), np.array([0.0])
    ])
    assert nL[0] == 0.0
    assert created[0] == pytest.approx(1.0e-3)

    # Round-off sized residuals are not reported: they are the tolerance the
    # solver was asked for, and flagging them would make the report useless.
    _, tiny = project_non_negative([
        np.array([-1.0e-15]), np.array([0.0]), np.array([0.0])
    ])
    assert tiny[0] == 0.0


def test_a_thermal_edge_moves_heat_from_hot_to_cold(net):
    rig = Rig()
    a = rig.add("a", Vessel(net, volume=1.0, T=350.0, T_env=350.0, UA=0.0,
                            kla=0.0, k_vent=0.0, heat_capacity=100.0))
    b = rig.add("b", Vessel(net, volume=1.0, T=300.0, T_env=300.0, UA=0.0,
                            kla=0.0, k_vent=0.0, heat_capacity=100.0))
    rig.thermal("a", "b", UA=5.0)
    rig.run(30.0)

    assert a.T < 350.0 and b.T > 300.0
    # equal heat capacities and no other path: the pair must stay symmetric
    assert (350.0 - a.T) == pytest.approx(b.T - 300.0, rel=1e-3)


def test_a_drain_runs_one_way(net):
    rig = Rig()
    upper = rig.add("upper", Vessel(net, volume=1.0, T=298.15, T_env=298.15,
                                    UA=50.0, kla=0.0, k_vent=0.0))
    lower = rig.add("lower", Vessel(net, volume=1.0, T=298.15, T_env=298.15,
                                    UA=50.0, kla=0.0, k_vent=0.0))
    rig.drain("upper", "lower", k=0.5)
    upper.charge({ETOH: 2.0})
    rig.run(60.0)

    assert lower.state().n_liquid[ETOH] > 1.9
    assert upper.state().n_liquid[ETOH] < 0.1


def test_a_metered_edge_delivers_its_set_rate_and_a_closed_tap_delivers_nothing(net):
    rig = Rig()
    funnel = rig.add("funnel", Vessel(net, volume=1.0, T=298.15, T_env=298.15,
                                      UA=50.0, kla=0.0, k_vent=0.0))
    rig.add("flask", Vessel(net, volume=1.0, T=298.15, T_env=298.15,
                            UA=50.0, kla=0.0, k_vent=0.0))
    tap = rig.meter("funnel", "flask", rate=0.0)
    funnel.charge({ETOH: 2.0})

    rig.run(100.0)
    assert rig.state()["flask"].n_liquid[ETOH] == pytest.approx(0.0, abs=1e-9)

    rig.set_rate(tap, 0.002)             # mol/s
    rig.run(100.0)
    assert rig.state()["flask"].n_liquid[ETOH] == pytest.approx(0.2, rel=0.02)


def test_vapour_carries_its_enthalpy_into_the_receiver(net):
    """Without this, hot vapour entering a cold condenser is a free lunch and
    reflux runs on invented energy. The receiver is insulated from the room, so
    the only way it can warm is by what arrives."""
    rig = Rig()
    hot = rig.add("hot", Vessel(net, volume=1.0, T=360.0, T_env=360.0, UA=1.0,
                                kla=5.0, k_vent=0.0))
    cold = rig.add("cold", Vessel(net, volume=1.0, T=290.0, T_env=290.0, UA=0.0,
                                  kla=5.0, k_vent=0.0, heat_capacity=5.0))
    rig.vapour("hot", "cold", k=5.0)
    hot.charge({ETOH: 4.0})
    rig.run(600.0)

    assert cold.T > 291.0, "arriving vapour must warm what it lands in"


def test_a_rig_rejects_topology_that_cannot_mean_anything(net):
    rig = Rig()
    rig.add("a", Vessel(net, volume=1.0))
    with pytest.raises(ValueError, match="itself"):
        rig.vapour("a", "a")
    with pytest.raises(KeyError):
        rig.vapour("a", "nonexistent")
    with pytest.raises(ValueError, match="already in this rig"):
        rig.add("a", Vessel(net, volume=1.0))


def test_a_rig_refuses_vessels_from_different_networks(net, reactive_net):
    rig = Rig()
    rig.add("a", Vessel(net, volume=1.0))
    with pytest.raises(ValueError, match="different network"):
        rig.add("b", Vessel(reactive_net, volume=1.0))


# ---------------------------------------------------------------------------
# the apparatus
# ---------------------------------------------------------------------------


def test_reflux_holds_the_pot_at_its_bubble_point_indefinitely(net):
    """Boil, rise, condense, return -- a feedback loop with latent heat coupling
    the two temperatures, which is exactly why the rig has to be one stiff
    system rather than two vessels stepped in turn.

    Nothing here knows what a condenser is. The condensation is the cold
    vessel's ordinary phase model noticing that p exceeds p_eq at 288 K.
    """
    rig = Rig()
    flask = rig.add("flask", Vessel(net, volume=1.0, T=298.15, T_env=298.15,
                                    UA=1.0, kla=5.0, Q_input=150.0, k_vent=0.0))
    cond = rig.add("condenser", Vessel(net, volume=0.5, T=288.0, T_env=288.0,
                                       UA=40.0, kla=5.0, k_vent=10.0,
                                       heat_capacity=20.0))
    rig.vapour("flask", "condenser", k=20.0)
    rig.drain("condenser", "flask", k=0.5)

    flask.charge({ETOH: 4.0, WATER: 4.0})
    flask.fill_headspace_with_air()
    cond.fill_headspace_with_air()

    rig.run(600.0)
    T_early, held_early = flask.T, sum(cond.state().n_liquid.values())
    rig.run(3000.0)

    # A 50/50 ethanol/water mixture boils at ~353 K, and the pot must SIT there
    # rather than drifting: the condenser returns what it takes.
    assert flask.T == pytest.approx(353.0, abs=2.0)
    assert flask.is_boiling
    assert flask.T == pytest.approx(T_early, abs=0.5), "reflux must be steady"
    assert held_early > 1e-4, "the condenser must hold a working charge"
    # The atmosphere fix is what makes this meaningful -- vented one way only,
    # boiling sweeps the air out and the rig settles at the cold end's vapour
    # pressure instead of at 1 atm.
    assert flask.pressure == pytest.approx(1.013, abs=0.02)

    # ⚠ A STANDING CHECK ON A BUG THAT IS NOW FIXED, AND THE ASSERTION IS INVERTED
    # RATHER THAN DELETED. Boiling sweeps the pot's air out through the condenser,
    # and the vapour edge used to blend the two vessels' compositions across the
    # crossing -- so at a small positive dP the pot exported the CONDENSER's
    # composition, i.e. nitrogen it did not have, and its gas block ran negative
    # without bound. The projection then had to CREATE ~0.3 mol of air to bring
    # those totals back to zero, against the 0.06 mol the rig started with.
    #
    # It hid because the reflux result above survives it: the air is not what this
    # test measures, and the projection conserves everything it can. So the check
    # stays here, the other way round, on the same channel that reported it.
    # ``backflow_part`` is where the corrected form is argued.
    assert rig.conservation_report() == "", (
        "the vapour edge must not create or destroy matter"
    )


@pytest.mark.parametrize(
    "x_charged, expect",
    [(0.20, "enriches"), (0.894, "neither"), (0.95, "depletes")],
)
def test_distillation_finds_the_azeotrope_by_itself(net, x_charged, expect):
    """The headline. Distilling enriches the vapour in ethanol -- until it does
    not, and the composition where it stops is not written down anywhere.

    Below x = 0.894 the distillate is richer in ethanol than the pot; at 0.894 it
    is the same; above it, distilling enriches WATER instead. That sign change
    IS the azeotrope, and it emerges from Raoult plus UNIFAC activity
    coefficients with no azeotrope table in the codebase.
    """
    rig = Rig()
    pot = rig.add("pot", Vessel(net, volume=1.0, T=298.15, T_env=298.15,
                                UA=1.0, kla=5.0, Q_input=120.0, k_vent=0.0))
    recv = rig.add("receiver", Vessel(net, volume=0.5, T=283.0, T_env=283.0,
                                      UA=60.0, kla=5.0, k_vent=10.0,
                                      heat_capacity=20.0))
    rig.vapour("pot", "receiver", k=20.0)      # over the top; nothing returns

    pot.charge({ETOH: 8.0 * x_charged, WATER: 8.0 * (1.0 - x_charged)})
    pot.fill_headspace_with_air()
    recv.fill_headspace_with_air()
    rig.run(1200.0)

    d, p = recv.state().n_liquid, pot.state().n_liquid
    collected = d[ETOH] + d[WATER]
    assert collected > 0.1, "the still must actually distil something"

    x_distillate = d[ETOH] / collected
    x_pot = p[ETOH] / (p[ETOH] + p[WATER])
    enrichment = x_distillate - x_pot

    if expect == "enriches":
        assert enrichment > 0.05
    elif expect == "neither":
        assert abs(enrichment) < 0.02, f"azeotrope must not separate: {enrichment}"
    else:
        assert enrichment < 0.0, "past the azeotrope, distilling enriches water"


def test_the_boiling_point_is_lowest_at_the_azeotrope(net):
    """The other half of the same fact, and independent of composition
    measurements: a minimum-boiling azeotrope boils BELOW both pure components.
    Ethanol alone is 351.4 K and water 373 K, and the mixture beats both."""
    temps = {}
    for x in (0.60, 0.894, 1.0):
        rig = Rig()
        pot = rig.add("pot", Vessel(net, volume=1.0, T=298.15, T_env=298.15,
                                    UA=1.0, kla=5.0, Q_input=120.0, k_vent=0.0))
        recv = rig.add("recv", Vessel(net, volume=0.5, T=283.0, T_env=283.0,
                                      UA=60.0, kla=5.0, k_vent=10.0,
                                      heat_capacity=20.0))
        rig.vapour("pot", "recv", k=20.0)
        pot.charge({ETOH: 8.0 * x, WATER: 8.0 * (1.0 - x)})
        pot.fill_headspace_with_air()
        recv.fill_headspace_with_air()
        rig.run(1200.0)
        temps[x] = pot.T

    assert temps[0.894] < temps[0.60], "the azeotrope boils below a leaner mix"
    assert temps[0.894] < temps[1.0], "and below pure ethanol -- that is the point"
    assert temps[0.894] == pytest.approx(351.2, abs=1.0)


def test_edge_arrays_are_the_layer_4_contract(net):
    """Layer 4 must receive index and coefficient arrays, not vessel objects --
    the same discipline that keeps the numerics a Rust seam."""
    rig = Rig()
    for name in ("a", "b"):
        rig.add(name, Vessel(net, volume=1.0))
    rig.vapour("a", "b", k=2.0)
    rig.drain("b", "a", k=0.5)
    rig.thermal("a", "b", UA=3.0)

    e = rig.arrays()
    assert e.count == 3
    assert list(e.kind) == [VAPOUR, DRAIN, THERMAL]
    assert list(e.a) == [0, 1, 0] and list(e.b) == [1, 0, 1]
    assert np.allclose(e.k, [2.0, 0.5, 3.0])
    for arr in (e.kind, e.a, e.b, e.k):
        assert isinstance(arr, np.ndarray)
