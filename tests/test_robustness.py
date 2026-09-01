"""Every state a player can reach must WORK, or REFUSE CLEANLY WITH A REASON.

Never a crash, and never a plausible-looking wrong number. This file is the
assertion side of ``validation/robustness.py``: that harness walks a list of
abusive setups and prints what each one did, and these tests pin the ones whose
behaviour is a promise rather than a measurement.

⚠ THE ORDER OF BADNESS MATTERS AND IS THE REASON THIS FILE EXISTS. A crash is
visible and a wrong number is not, so the sharpest tests below are the ones about
``sol.success`` being necessary and nowhere near sufficient -- the case that made
the point reported SUCCESS and returned a cancelling dipole of 3.07e9 mol, which
the non-negative projection then tidied into a state nothing downstream could tell
from a real one.
"""

import numpy as np
import pytest

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.numerics.vessel_integrator import (
    DRYOUT_MOLES,
    EXCURSION_FLOOR,
    EXCURSION_RATIO,
    LAYER_EPS,
    MOLE_FRACTION_DENOM,
    T_MAX,
    _dryout_gates,
    _layer_gates,
)
from chemsim.properties import dissociation_templates, electrolyte_provider
from chemsim.reactions import aerobic_oxidation, saponification
from chemsim.vessel import TransferLosses, Vessel

WATER, ETOH, N2, O2 = "O", "CCO", "N#N", "O=O"
TOLUENE = Molecule.from_smiles("Cc1ccccc1").smiles
BENZOIC = Molecule.from_smiles("OC(=O)c1ccccc1").smiles
NA = "[Na+]"
HMF = Molecule.from_smiles("OCc1ccc(C=O)o1").smiles
DIFORMYLFURAN = Molecule.from_smiles("O=Cc1ccc(C=O)o1").smiles
TRISTEARIN = Molecule.from_smiles(
    "CCCCCCCCCCCCCCCCCC(=O)OCC(OC(=O)CCCCCCCCCCCCCCCCC)COC(=O)"
    "CCCCCCCCCCCCCCCCC").smiles
STEARATE = Molecule.from_smiles("CCCCCCCCCCCCCCCCCC(=O)[O-]").smiles


@pytest.fixture(scope="module")
def net(thermo_module):
    return build_network([WATER, ETOH, TOLUENE, N2, O2], [], thermo=thermo_module,
                         max_species=30)


@pytest.fixture(scope="module")
def ionic_net():
    return build_network([WATER, BENZOIC, NA, TOLUENE], dissociation_templates(),
                         thermo=electrolyte_provider(), max_species=60)


def _flask(net, **kw):
    base = dict(volume=1.0, T=298.15, T_env=298.15, UA=5.0, kla=5.0)
    base.update(kw)
    return Vessel(net, **base)


# ---------------------------------------------------------------------------
# sol.success is necessary and not sufficient
# ---------------------------------------------------------------------------


def test_a_cancelling_dipole_is_refused_rather_than_projected_away(net):
    """⚠ THE SHARPEST ONE. ``project_non_negative`` exists to settle a cancelling
    numerical pair without creating matter, and it does that job perfectly -- which
    means a catastrophic dipole becomes a plausible state before anything
    downstream gets to look at it. So the RAW solver output is checked first."""
    v = _flask(net)
    v.charge({WATER: 20.0})
    n = v.integrator.n
    y = v.integrator.pack(v._nL, v._nL2, v._nG, v._nS, v.T)

    # A state that is fine, and the same state with a dipole in it. The dipole
    # sums to nothing, so the projection would erase it silently.
    v.integrator.check_raw_solution(y)
    poisoned = y.copy()
    poisoned[0] += 3.07e9
    poisoned[n] -= 3.07e9
    with pytest.raises(RuntimeError, match="not a perturbation of any physical"):
        v.integrator.check_raw_solution(poisoned)

    # ... and the projection really would have hidden it.
    tidied = v.integrator.project(poisoned)
    assert float(np.min(tidied[: 4 * n])) >= 0.0
    assert tidied[0] == pytest.approx(y[0], abs=1e-6)


def test_a_round_off_excursion_is_NOT_treated_as_a_failure(net):
    """The other side of the same bound, and it has to hold or every long run
    would raise. A dipole is bounded by the solver's own tolerance -- the measured
    worst case over a 600 s two-vessel run was 1.26e-6 mol -- so the check has to
    be dimensional rather than tuned: a species may not be more negative than the
    amount of it that exists."""
    v = _flask(net)
    v.charge({WATER: 20.0})
    y = v.integrator.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
    n = v.integrator.n

    ordinary = y.copy()
    ordinary[n] = -1.26e-6            # water, negative in the empty second layer
    v.integrator.check_raw_solution(ordinary)      # must not raise

    assert EXCURSION_FLOOR > 1.26e-6, (
        "the floor has to leave room for a real round-off excursion"
    )
    # ⚠ AND THE BOUND IS A RATIO, which is what separates three cases nine orders
    # of magnitude apart -- a round-off dipole at 6e-8 of the material present, a
    # coupled rig sweeping its air at 6x (a REAL unfixed bug, reported rather than
    # refused -- see Rig.conservation_report), and the unclipped Born term at 3e9x.
    # A ratio of 1e3 classifies all three without being a number chosen to make
    # tests pass.
    assert EXCURSION_RATIO == pytest.approx(1.0e3)
    rig_sized = y.copy()
    rig_sized[2 * n] = -0.34          # the rig's air leak, on a species at zero
    v.integrator.check_raw_solution(rig_sized)     # reported, not refused


def test_a_non_finite_solution_is_refused_even_when_success_is_reported(net):
    v = _flask(net)
    v.charge({WATER: 20.0})
    y = v.integrator.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
    y[3] = float("inf")
    with pytest.raises(RuntimeError, match="non-finite"):
        v.integrator.check_raw_solution(y)


# ---------------------------------------------------------------------------
# states that must be refused, with a reason
# ---------------------------------------------------------------------------


def test_a_nan_in_the_state_is_refused_before_the_solver_sees_it(net):
    v = _flask(net)
    v.charge({WATER: 20.0})
    v._nL[v._index(ETOH)] = float("nan")
    with pytest.raises(ValueError, match="not finite"):
        v.step(10.0)


def test_a_temperature_outside_the_correlation_window_is_refused(net):
    """Every property here is a polynomial or an Antoine fit. Both return
    confident nonsense far outside their window, which is exactly the class of
    answer this project refuses to give."""
    v = _flask(net)
    v.charge({WATER: 20.0})
    v.T = 2.0 * T_MAX
    with pytest.raises(ValueError, match="outside the range"):
        v.step(10.0)


def test_charging_a_species_the_network_does_not_have_names_the_fix(net):
    v = _flask(net)
    with pytest.raises(KeyError, match="not a species in this network"):
        v.charge({"CCCCCCCCCCCC": 1.0})


# ---------------------------------------------------------------------------
# a failure that cannot be avoided must at least be diagnosed
# ---------------------------------------------------------------------------


def test_a_failed_solve_names_the_likely_cause(ionic_net):
    """A crash with no diagnosis is not a clean refusal. Every entry in
    ``diagnose`` is a state this project has actually failed on, so it is a record
    rather than a guess."""
    v = _flask(ionic_net, volume=2.0, kla=0.0, k_diss=0.0, k_lle=5.0)
    v.charge({WATER: 27.7, TOLUENE: 4.7, NA: 0.1, BENZOIC: 0.1})
    y = v.integrator.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
    y[v.integrator.n + v._index(TOLUENE)] = 4.0       # force a second layer

    why = v.integrator.diagnose(y)
    assert any("k_lle" in note for note in why), why
    assert any("SET_SHAKING" in note for note in why), why


def test_a_dry_superheated_flask_is_named_as_the_fragile_state_it_is(net):
    """PRE-EXISTING and still open: a dry flask driven far past its boiling point
    can produce a non-finite Jacobian. It is not fixed here -- it is NAMED, so a
    failure arrives with the reason attached instead of as a LinAlgError."""
    v = _flask(net, volume=0.5, T=600.0, UA=0.2, Q_input=80.0)
    y = v.integrator.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
    why = v.integrator.diagnose(y)
    assert any("DRY" in note and "PLATEAU" in note for note in why), why


def test_the_sealed_flask_is_a_reported_fragility_not_a_refusal(net):
    """⚠ THE DISTINCTION THAT HAD TO BE GOT RIGHT. ``kla=0`` with an empty
    headspace leaves the gas block flat, which BDF's ``num_jac`` cannot difference
    -- but it is per-solve, and sixty-odd setups in this repo sit there quite
    happily. Refusing them would have been as wrong as crashing."""
    v = _flask(net, kla=0.0, k_vent=0.0)
    v.charge({WATER: 20.0, ETOH: 2.0})

    assert "EMPTY HEADSPACE" in v.integrability_report()
    assert "nitrogen blanket" in v.integrability_report()
    v.step(10.0)                                   # and it still works

    # ... and a nitrogen blanket clears the report, which is the point of naming
    # the fix rather than only the problem.
    v.fill_headspace({"N#N": 1.0})
    assert "EMPTY HEADSPACE" not in v.integrability_report()


def test_a_vessel_with_nothing_wrong_reports_nothing(net):
    v = _flask(net)
    v.charge({WATER: 20.0})
    v.fill_headspace_with_air()
    assert v.integrability_report() == ""


# ---------------------------------------------------------------------------
# degenerate states a game reaches constantly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("charge,phase", [
    ({}, "liquid"),
    ({WATER: 20.0}, "liquid"),
    ({BENZOIC: 0.02}, "solid"),
])
def test_degenerate_vessels_step_without_complaint(ionic_net, charge, phase):
    """An empty flask, a plain solution, a heap of solid with no solvent. All
    three are one click away in any interface."""
    v = _flask(ionic_net, k_diss=0.05)
    if charge:
        v.charge(charge, phase=phase)
    v.fill_headspace_with_air()
    v.step(600.0)
    assert np.all(np.isfinite(v._nL)) and np.isfinite(v.T)


def test_a_vessel_at_rest_still_gets_no_solver_and_still_works(net):
    """Fixed once already -- a vanishing derivative makes ``num_jac`` inflate its
    perturbation to infinity and then reject every step forever. Confirming it
    stays fixed, because an idle vessel is the common case in a game."""
    # ⚠ POURED OUT, which is the state the fix was written for: a flask with liquid
    # still in it and an open vent is never EXACTLY at rest -- it loses solvent
    # forever, slowly -- so it does not qualify and should not. Twenty thousand
    # seconds of settling still left it with 40 solver calls to make, which is the
    # honest answer and not a regression.
    v = _flask(net, kla=1.0)
    v.fill_headspace_with_air()
    before = v._nG.copy()

    sol = v.run(3600.0)
    assert sol.nfev <= 1, "a resting vessel must not be integrated at all"
    assert "stationary" in sol.message
    assert np.allclose(v._nG, before, rtol=0, atol=1e-12)


def test_the_dryout_pair_is_COMPLEMENTARY_and_the_layer_pair_is_DISJOINT():
    """⚠ THE TWO GATE PAIRS HAVE OPPOSITE SHAPES ON PURPOSE, and each shape was
    measured wrong in the other's place. This is the cheap guard on both.

    ``_layer_gates`` is DISJOINT: a second layer sitting where both halves are
    live had the liquid-liquid flux and the reabsorption fighting over it, and the
    benzoic-acid acidification would not solve.

    ``_dryout_gates`` is COMPLEMENTARY, because disjointness leaves a DEAD ZONE
    where both halves are zero -- and for the flask's own liquid that pair is the
    ONLY phase-change channel, so a condenser comes to rest in the dead zone and
    stops accumulating. Measured, with the disjoint shape in place: the head
    stalled at 9.998e-07 mol against the 1e-4 a working charge needs and the
    reflux plateau went 352.89 -> 370.39 K. So ``wet + dry`` must be EXACTLY one
    for a single liquid -- not approximately, or the pot leaks latent heat.
    """
    # the flask's own liquid: complementary, everywhere, exactly
    for scale in (0.0, 0.1, 0.5, 0.9, 1.0, 1.5, 2.0, 10.0, 1.0e6):
        wet, dry = _dryout_gates(scale * DRYOUT_MOLES, scale * DRYOUT_MOLES)
        assert wet + dry == 1.0, f"a dead zone at N = {scale} * DRYOUT_MOLES"
        assert 0.0 <= wet <= 1.0 and 0.0 <= dry <= 1.0

    # with liquid in layer 2 as well, the pair may only ever UNDER-count -- layer
    # 2's own gate covers the rest, and nothing is allowed to double up
    for f2 in (0.5, 1.0, 5.0):
        wet, dry = _dryout_gates(DRYOUT_MOLES, (1.0 + f2) * DRYOUT_MOLES)
        assert wet + dry <= 1.0 + 1e-15

    # the second liquid layer: disjoint, and that is the OTHER pair's promise
    for scale in (0.1, 0.5, 0.9, 1.0, 1.5, 2.0):
        grow, drain = _layer_gates(scale * LAYER_EPS)
        assert grow == 0.0 or drain == 0.0, (
            f"the layer gates overlap at N2 = {scale} * LAYER_EPS"
        )

    # ...and both pairs are FLAT at zero, which is what keeps an empty phase's
    # Jacobian column honestly zero instead of worth 1/eps. See LAYER_EPS.
    tiny = DRYOUT_MOLES * 1.0e-6
    assert _dryout_gates(tiny, tiny)[0] / tiny < 1.0e-3 / DRYOUT_MOLES, (
        "the wet gate has a 1/DRYOUT_MOLES slope at zero -- it is a ramp again"
    )


def test_a_vanishing_liquid_still_has_mole_fractions_that_sum_to_ONE(net):
    """⚠ THE CLAMP THAT DOUBLED AS A GATE, WHICH IS WHAT CREATED MATTER.

    Layer 1's mole fractions used to be floored on ``DRYOUT_MOLES`` -- the same
    scale that gated its evaporation -- so a flask holding less than that had
    ``x`` summing to LESS THAN ONE (0.57 at 5.7e-7 mol) and every activity
    understated by the same factor, while both evaporation branches were live.
    A sulfur burner at 690 K created 11% of its oxygen that way.

    ``MOLE_FRACTION_DENOM`` is 24 decades below the gate and exists ONLY to keep
    0/0 out, so this now holds for every reachable holding. Layer 2 is exempt for
    a stated reason: its floor IS its gating scale, and that is safe only because
    ``gate2`` is identically zero wherever the floor binds.
    """
    assert MOLE_FRACTION_DENOM < DRYOUT_MOLES * 1.0e-12, (
        "the 0/0 guard has drifted up into gate territory"
    )
    integ = Vessel(net, volume=1.0, T=300.0, T_env=300.0, UA=1.0, kla=5.0,
                   k_diss=0.0).integrator
    n = integ.n
    for total in (1.0, 1e-3, DRYOUT_MOLES, 1e-7, 1e-9, 1e-12):
        nL1 = np.zeros(n)
        nL1[0] = 0.75 * total
        nL1[1] = 0.25 * total
        x = nL1 / max(float(nL1.sum()), MOLE_FRACTION_DENOM)
        assert x.sum() == pytest.approx(1.0, rel=1e-14), (
            f"mole fractions sum to {x.sum():.4f} at {total:.3e} mol of liquid"
        )


def test_a_second_layer_in_the_transition_band_survives(net):
    """⚠ The band between ``DRYOUT_MOLES`` and ``LAYER_EPS`` made the prep's
    acidification unsolvable once: a layer there survived the merge AND sat inside
    the smoothstep, so the growth and drain gates fought over it. They are
    strictly disjoint now, and this is the regression guard."""
    v = _flask(net, kla=0.0, k_lle=0.5)
    v.charge({WATER: 30.0})
    v.charge({TOLUENE: 0.5 * (DRYOUT_MOLES + LAYER_EPS)}, phase="liquid2")
    v.step(600.0)

    assert np.isfinite(v.T)
    assert v.integrator.created.sum() < 1e-9
    # the trace layer is gone, reabsorbed rather than stranded
    assert float(v._nL2.sum()) <= LAYER_EPS


# ---------------------------------------------------------------------------
# retrying an experiment
# ---------------------------------------------------------------------------


def test_reset_clears_the_loss_records_a_previous_attempt_left(ionic_net):
    """⚠ A player retrying an experiment used to be shown the PREVIOUS attempt's
    holdup and crust. None of it is in the state vector, which is exactly why
    emptying the four amount blocks looked complete."""
    losses = TransferLosses(drain_time=5.0, crystal_size=50.0e-6)
    v = Vessel(ionic_net, volume=1.0, T=275.0, T_env=275.0, UA=5.0, kla=0.0,
               k_diss=0.0, losses=losses)
    v.charge({WATER: 27.7})
    v.charge({BENZOIC: 0.05}, phase="solid")
    v.filter_into(None, Vessel(ionic_net, volume=1.0, T=275.0, kla=0.0))

    assert v.crust_report() and v.holdup_report()
    v.reset()
    assert v.crust_report() == "", "the crust record outlived the experiment"
    assert v.holdup_report() == "", "so did the film record"
    assert v.conservation_report() == ""
    assert v.integrator.last_stability is None
    assert v.integrator.refused_reason == ""


# ---------------------------------------------------------------------------
# R1 -- a species nothing can price is a COVERAGE LIMIT, not a traceback
# ---------------------------------------------------------------------------


def test_an_unpriceable_product_is_reported_rather_than_raised(thermo, capsys):
    """⚠⚠ THE ONE COVERAGE LIMIT THAT USED TO HAND THE PLAYER A TRACEBACK.

    5-HMF and oxygen are both offered UNGREYED by the picker, and this is ONE
    generation off its own roster -- not a deep exploration. ``aerobic_oxidation``
    makes 2,5-diformylfuran, whose formation half resolves through Benson and
    whose physical half does not exist, because no source anywhere tabulates a
    boiling point for it. ``thermochemistry`` is right to refuse: the record
    would otherwise be silently treated as non-volatile. What was wrong was
    letting that refusal out of ``build_network``, where ``max_species``,
    ``max_molar_mass`` and ``generations`` all DROP, NOTICE and carry on.
    """
    net = build_network([HMF, O2], [aerobic_oxidation()], thermo=thermo,
                        generations=1, max_species=40)

    assert DIFORMYLFURAN not in net.species, "the species must not be registered"
    assert DIFORMYLFURAN in net.unpriced, "...and it must be NAMED, not just gone"

    why = net.unpriced[DIFORMYLFURAN]
    assert "no thermochemistry available" in why
    assert "Benson" in why, "the notice must say which half of the record resolved"
    assert "physical_data" in why, "...and what would fix it"

    notice = [n for n in net.notices if "could not be PRICED" in n]
    assert len(notice) == 1
    assert DIFORMYLFURAN in notice[0]
    assert why in notice[0], "the refusal is ROUTED, not paraphrased"
    assert notice[0] in capsys.readouterr().out, "carried AND printed, as P1 requires"


def test_the_unpriced_drop_takes_the_REACTION_with_it(thermo):
    """⚠ DROP THE REWRITE, NOT ONLY THE SPECIES.

    A half-registered reaction whose product has no thermochemistry is worse
    than either alternative: it would consume its reactants into an index the
    energy balance and the vapour-liquid split cannot price. So no surviving
    reaction may mention the dropped species on either side.
    """
    net = build_network([HMF, O2], [aerobic_oxidation()], thermo=thermo,
                        generations=1, max_species=40)
    for r in net.reactions:
        assert DIFORMYLFURAN not in r.reactants + r.products, r.name


def test_the_5_HMF_PICK_HAS_NO_CHEMISTRY_AT_ALL_AND_SAYS_SO(thermo):
    """⚠⚠ WHAT THE CRASH WAS HIDING, WHICH IS THE POINT OF CLOSING IT.

    The traceback reported the FIRST refusal and stopped. With all of them
    reported, this pick's real answer appears: three templates make five
    unpriceable species between them -- the dialdehyde, its ether dimer and
    three bis-furylmethanes -- and with all five refused the flask has NO
    reactions.

    ⚠ THE PICK IS EXACTLY THE TWO ROWS AND NOTHING ELSE, WHICH MATTERS.
    Add water and ``hydroxymethylfurfural_rehydration`` fires and the flask
    is no longer inert -- so the claim is about what the PICKER offered, not
    about 5-HMF. A crash says something went wrong; the notice says what is
    missing and what would fix it, and only one of those is a limit a player can
    act on.
    """
    from chemsim.ui.examples import full_library

    net = build_network([HMF, O2], list(full_library()),
                        thermo=thermo, generations=1, max_species=60)
    assert len(net.unpriced) == 5, sorted(net.unpriced)
    assert net.reactions == []


def test_a_species_the_WRONG_PROVIDER_refuses_is_not_dropped(thermo):
    """⚠⚠ THE DISTINCTION R1 TURNS ON, AND IT IS NOT A DETAIL.

    ``OutsideEstimatorDomain`` -- an element, an ion, a mixture -- does not say
    the species is unknown. It says THIS provider is the wrong one, and it names
    the right one. Dropping it would report a hole in the data where the truth
    is a hole in the setup, and it would delete chemistry this engine can do:
    the stearate ion below is priced perfectly well by
    ``electrolyte_provider()``. Every network in this repo that carries an ionic
    product under a neutral provider has always carried it, because
    ``VolatilityProvider`` short-circuits a charged species to non-volatile
    without ever consulting thermochemistry.
    """
    net = build_network([TRISTEARIN, "[OH-]", NA, WATER], [saponification()],
                        thermo=thermo, max_species=60)
    assert STEARATE in net.species, "an ion is not a coverage limit"
    assert net.unpriced == {}
    assert not [n for n in net.notices if "could not be PRICED" in n]
    with pytest.raises(ValueError, match="carries a net charge"):
        thermo.get(STEARATE)          # and the refusal is still there, unchanged
