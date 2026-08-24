"""M12: an insulated flask may not destroy energy, and it may not do so quietly.

The defect these pin was a measured wrong answer, not a rough edge. An insulated
metathesis (UA = 0, no wall mass, closed) reached its predicted +0.1577 K at
t = 600 s, still read +0.1575 at t = 1200 s, and then decayed to +0.0378 by
t = 3600 s **after the chemistry had stopped** -- 495 J destroyed against a
0.0087 J chemical budget, with every atom conserved to 1e-12.

The cause was not the precipitation term, not the solver's tolerance, and not
the energy equation's algebra -- all three were controlled for (see
``validation/adiabatic_tail.py``). It was a DERIVED rate constant:
``detailed_balance`` handed water autoionization's reverse a barrier of 4.2
kJ/mol and a rate constant of 9.4e18 L/(mol s), 9.4e7 times the collision limit.
Its two heat terms were then +-5.2e9 W either side of a net of a fraction of a
watt, and three BDF steps of 168 s each destroyed 467 J of the total while the
composition did not move by a picomole.

⚠ ASSERTED AS CONVERGENCE AND AS PHYSICS, NEVER AS A DEFAULT-TOLERANCE VALUE.
The number that used to be quoted for this flask, 0.1577, was itself read off an
under-resolved run; the converged answer is 0.15759. So the tests below ask the
two questions that do not depend on which rung the ladder is read at: does the
flask HOLD what it made, and does the tolerance ladder agree with itself.
"""

import numpy as np
import pytest

from chemsim.network import build_network
from chemsim.properties import dissociation_templates, electrolyte_provider
from chemsim.reactions import ReactionTemplate
from chemsim.reactions.thermo import COLLISION_LIMIT
from chemsim.vessel import Vessel

WATER = "O"
SILVER, CHLORIDE, SODIUM = "[Ag+]", "[Cl-]", "[Na+]"
NITRATE = "O=[N+]([O-])[O-]"
R = 8.314462618
T_REF = 298.15


@pytest.fixture(scope="module")
def thermo_e():
    return electrolyte_provider()


@pytest.fixture(scope="module")
def net(thermo_e):
    return build_network(
        [WATER, SILVER, CHLORIDE, SODIUM, NITRATE],
        list(dissociation_templates()), thermo=thermo_e, max_species=40,
    )


def flask(net, thermo_e, T=T_REF, mol=0.01, precipitation=True):
    v = Vessel(net, volume=1.0, thermo=thermo_e, UA=0.0, heat_capacity=0.0,
               T=T, T_env=T_REF, precipitation=precipitation)
    v.charge({WATER: 55.0, SILVER: mol, NITRATE: mol, SODIUM: mol,
              CHLORIDE: mol})
    return v


# ---------------------------------------------------------------------------
# the ceiling on a DERIVED rate constant
# ---------------------------------------------------------------------------


def k_at(r, T=T_REF):
    return float(r.A * np.exp(-r.Ea / (R * T)) * T**r.n_exp)


def test_no_derived_rate_constant_beats_a_collision(net):
    """The bound the project already applied to AUTHORED pre-exponentials.

    ``reactions/library.py`` refuses A = 1e14 for a burner as "an impossible
    pre-exponential". The same standard has to reach the rate constants
    detailed balance derives, which is where the one that mattered was.
    """
    for r in net.reactions:
        if len(r.reactants) < 2:
            continue
        assert k_at(r) <= COLLISION_LIMIT * (1.0 + 1e-9), (
            f"{r.name} runs at {k_at(r):.3e} L/(mol s), "
            f"{k_at(r) / COLLISION_LIMIT:.2e}x the collision limit"
        )


def test_the_cap_fires_on_water_and_nothing_else(net):
    """Exactly one reaction in an aqueous network needed it -- and it is the
    one whose ``Ea`` was chosen to dodge the elementary-barrier clamp."""
    at_limit = [
        r.name for r in net.reactions
        if len(r.reactants) >= 2 and k_at(r) > 0.5 * COLLISION_LIMIT
    ]
    assert at_limit == ["water_autoionization_rev"]


def test_capping_the_rate_does_not_move_the_equilibrium(net, thermo_e):
    """⚠ THE INVARIANT THE CAP MAY NOT TOUCH.

    Both pre-exponentials are scaled by ONE factor, so K = k_f / k_r is
    invariant under it exactly. If this ever fails, the cap has stopped being a
    correction to a rate and has become a change to the chemistry -- and every
    pKa and pH in the project rests on it.
    """
    fwd = next(r for r in net.reactions if r.name == "water_autoionization")
    rev = next(r for r in net.reactions if r.name == "water_autoionization_rev")
    # Kw on the concentration basis the rate law runs on: k_f [H2O]^2 = k_r [H3O][OH]
    Kw = k_at(fwd) * 55.4**2 / k_at(rev)
    assert Kw == pytest.approx(1.0e-14, rel=0.05)


def test_the_uncapped_pair_is_what_the_cap_removed(thermo_e):
    """Hold the code fixed and change the chemistry: an UNCAPPED pair is still
    reachable by declaring a slow enough forward rate, and it is 1e8x hotter."""
    slow = [
        ReactionTemplate(name=t.name, smarts=t.smarts, A=1.0, Ea=t.Ea,
                         reversible=True)
        if t.name == "water_autoionization" else t
        for t in dissociation_templates()
    ]
    n = build_network([WATER], slow, thermo=thermo_e, max_species=10)
    rev = next(r for r in n.reactions if r.name == "water_autoionization_rev")
    # A = 1.0 puts the pair far below the ceiling, so the cap does NOT fire and
    # the reverse keeps whatever detailed balance gave it.
    assert k_at(rev) < COLLISION_LIMIT


# ---------------------------------------------------------------------------
# the flask itself
# ---------------------------------------------------------------------------


def test_an_insulated_flask_holds_the_heat_it_made(net, thermo_e):
    """M12's reproduction, in one call. The 1200 s and 3600 s answers must AGREE.

    This is the assertion the milestone is closed against, and it is written as
    a comparison between two spans of the SAME flask rather than against a
    remembered constant -- 495 J went missing between exactly these two points.
    """
    warm = flask(net, thermo_e)
    warm.run(1200.0)
    at_1200 = warm.T - T_REF

    long_run = flask(net, thermo_e)
    long_run.run(3600.0)
    at_3600 = long_run.T - T_REF

    assert at_1200 > 0.15, "the precipitation heat is missing entirely"
    assert at_3600 == pytest.approx(at_1200, abs=1e-4), (
        f"an insulated flask lost {(at_1200 - at_3600) * 4142.5:.1f} J between "
        f"t=1200 s ({at_1200:+.5f} K) and t=3600 s ({at_3600:+.5f} K) with no "
        f"sink: UA = 0, nothing volatile, the solid flat"
    )


def test_the_answer_no_longer_depends_on_the_tolerance(net, thermo_e):
    """⚠ Rule 4: a value is only worth asserting once the ladder agrees.

    Before the cap this flask read -1.20e-1 K of error at the default rung and
    scattered non-monotonically below it. Now every rung lands on the same
    answer, which is the strongest form of the claim: the DEFAULT tolerance
    produces the converged number.
    """
    answers = []
    for rtol, atol in ((1e-6, 1e-9), (1e-8, 1e-11)):
        v = flask(net, thermo_e)
        v.run(3600.0, rtol=rtol, atol=atol)
        answers.append(v.T - T_REF)
    assert answers[0] == pytest.approx(answers[1], abs=1e-5)


def test_a_warm_flask_keeps_its_head_start_and_the_reaction_heat(net, thermo_e):
    """Started 0.16 K warm, an insulated flask must finish at 0.16 + its own
    heat. The two are independent and used to interfere: this read +0.109 when
    the parts were +0.160 and +0.158."""
    cold = flask(net, thermo_e, T=T_REF)
    cold.run(3600.0)
    warm = flask(net, thermo_e, T=T_REF + 0.16)
    warm.run(3600.0)
    assert warm.T - cold.T == pytest.approx(0.16, abs=1e-4)


# ---------------------------------------------------------------------------
# and the audit, which is the other half of the milestone
# ---------------------------------------------------------------------------


def test_the_energy_terms_sum_to_the_temperature_derivative(net, thermo_e):
    """The balance has to close against the derivative the solver is handed.

    ``conservation_report`` audits matter and cannot see energy at all -- a
    flask held every element to 1e-12 while destroying half a kilojoule. This
    is the corresponding instrument.
    """
    v = flask(net, thermo_e)
    v.run(600.0)
    y = v.integrator.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
    p = v.integrator.energy_terms(y)
    assert p["q_sum"] == pytest.approx(p["dT"] * p["Cp_total"], rel=1e-9)


def test_the_report_shows_the_gross_heat_not_only_the_net(net, thermo_e):
    """⚠ WHY THE REPORT EXISTS AT ALL.

    A net reaction heat of 1e-3 W looks the same whether the flask is at rest or
    whether two terms of 5.2e9 W are cancelling to twelve digits. It was the
    second case, and nothing in the project could say so.
    """
    v = flask(net, thermo_e)
    v.run(600.0)
    text = v.energy_report()
    assert "gross against" in text
    assert "cancellation" in text
    p = v.integrator.energy_terms(
        v.integrator.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
    )
    terms = p["q_rxn_terms"]
    gross = float(np.abs(terms).sum())
    assert gross >= abs(float(terms.sum()))
    # The cap is what keeps this finite. Uncapped it was ~1e12.
    assert gross / max(abs(float(terms.sum())), 1e-30) < 1.0e6


def test_energy_terms_needs_the_runs_own_boundary_state(net, thermo_e):
    """⚠ The trap that cost a whole wrong reading during M12.

    The RHS a ``run`` used froze each layer's permittivity at the state it
    STARTED from. Re-freezing at a later state perturbs the Bronsted-Bjerrum
    factor in the fifth digit, which is a large number of watts out of a
    cancellation -- so a trajectory audit MUST pass the boundary it ran from.
    """
    v = flask(net, thermo_e)
    y0 = v.integrator.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
    v.run(1200.0)
    y1 = v.integrator.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
    self_frozen = v.integrator.energy_terms(y1)
    run_frozen = v.integrator.energy_terms(y1, boundary=y0)
    # Both must still close against their own derivative -- the point is that
    # they are different questions, not that either is malformed.
    for p in (self_frozen, run_frozen):
        assert p["q_sum"] == pytest.approx(p["dT"] * p["Cp_total"], rel=1e-9)
