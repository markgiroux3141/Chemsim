"""G6 -- the encounter plateau: the Hammett line stops being a line.

⚠ WHAT THESE TESTS ARE FOR. The plateau is a HAND-AUTHORED constant, which this
project allows only when it is bounded against a stated observable and the bound
is written down (MILESTONES § STATED NON-GOALS, the A-factor licence). So the
tests assert the BOUND as much as the value: that the declared number lies inside
the band its two sources allow, that it reproduces the datum it was taken from,
and that the two places it is measurably wrong stay wrong by the measured amount
rather than drifting quietly.

The audit with the full arithmetic is ``validation/saturation.py``.
"""

from __future__ import annotations

import contextlib
import io
import math

import pytest

from chemsim.constants import R
from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider
from chemsim.reactions import hammett
from chemsim.reactions.synthesis import NITRATION_RHO, aromatic_nitration
from chemsim.reactions.template import ReactionTemplate
from chemsim.vessel import Vessel


def c(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


BENZENE, TOLUENE, PHENOL = c("c1ccccc1"), c("Cc1ccccc1"), c("Oc1ccccc1")
NITRIC, WATER = c("O[N+](=O)[O-]"), c("O")
MESITYLENE, P_XYLENE = c("Cc1cc(C)cc(C)c1"), c("Cc1ccc(C)cc1")
AMINOPHENOL, ANILINE = c("Nc1ccc(O)cc1"), c("Nc1ccccc1")
NB = c("O=[N+]([O-])c1ccccc1")
TNT = c("Cc1cc([N+](=O)[O-])cc([N+](=O)[O-])c1[N+](=O)[O-]")
DECLARED_EA, DECLARED_A = 60_000.0, 1.0e10

# Belson & Strachan, J. Chem. Soc. Perkin Trans. 2, 1989, 15 -- relative rates of
# nitration in aqueous nitric acid at ~30 mol% and 25 C, with p-xylene and
# mesitylene stated to be diffusion-controlled and the other two not.
MEASURED_RATIOS = {TOLUENE: 22.0, P_XYLENE: 256.0, MESITYLENE: 485.0}


@pytest.fixture(scope="module")
def thermo():
    return ThermochemistryProvider()


def sigma(smiles: str) -> float:
    return hammett.survey(Molecule.from_smiles(smiles)._mol).sigma_sum


def _stages(thermo, saturation, T, seconds, two_sided=False):
    """Moles of aromatic material by nitro count. ⚠ Charged and integrated --
    nothing here is credited on an argument."""
    shift = hammett.barrier_shift

    def two(rho, sigma_sum, sat=saturation):
        d = max(min(rho * sigma_sum, sat), -sat)
        return -hammett._PER_DECADE * d

    if two_sided:
        hammett.barrier_shift = two
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            net = build_network(
                [TOLUENE, NITRIC, WATER],
                [aromatic_nitration(saturation=saturation)],
                thermo=thermo, generations=3, max_species=60,
            )
            v = Vessel(net, volume=1.0, T=T, T_env=T, UA=1.0e6, kla=0.0,
                       k_vent=0.0, k_diss=0.0, lle=False)
            v.charge({TOLUENE: 1.0, NITRIC: 3.5, WATER: 5.0})
            v.run(seconds)
        out: dict[int, float] = {}
        st = v.state()
        for s in v.species:
            if s in (NITRIC, WATER) or "c" not in s:
                continue
            n = s.count("[N+](=O)[O-]")
            out[n] = out.get(n, 0.0) + st.total(s)
        return out
    finally:
        hammett.barrier_shift = shift


# ---------------------------------------------------------------------------
# 1. the constant, and the band it had to come from
# ---------------------------------------------------------------------------
def test_the_plateau_is_the_mesitylene_datum_and_sits_inside_its_own_band():
    """⚠ THE CONSTANT IS HAND-AUTHORED, SO THE BOUND IS THE DELIVERABLE.

    Upper end: log10(485), the fastest nitration Belson & Strachan call
    diffusion-controlled. Lower end: toluene's own line value, because toluene is
    measured NOT to be diffusion-controlled and a plateau below it would cap a
    substrate that does not saturate -- which is exactly what the 1968
    sulfuric-acid figure (0.778 decades) would do.
    """
    assert hammett.SATURATION_DECADES == 2.686
    assert hammett.SATURATION_DECADES == pytest.approx(math.log10(485.0), abs=5e-4)

    toluene_line = NITRATION_RHO * sigma(TOLUENE)
    assert toluene_line == pytest.approx(2.022, abs=1e-3)
    # The declared value is the datum ROUNDED to the datum's own three figures
    # -- 485 is quoted to three, so log10(485) = 2.68574 carries precision the
    # source does not have. Below the datum's rounding, above toluene's line.
    assert toluene_line < hammett.SATURATION_DECADES
    assert hammett.SATURATION_DECADES - math.log10(485.0) < 5e-4

    # And the 1968 figure, priced: it would cap toluene at a sixth of its
    # measured ratio, which is why it is recorded and not used.
    assert hammett.rate_ratio(
        NITRATION_RHO, sigma(TOLUENE), saturation=0.778
    ) < MEASURED_RATIOS[TOLUENE] / 3.0


def test_it_reproduces_its_datum_and_the_two_errors_are_asserted_not_hidden():
    """⚠ WHERE A ONE-PARAMETER MODEL IS WRONG IS PART OF THE MODEL. Mesitylene
    is the datum and comes back exactly. p-xylene is 1.9x high -- the factor the
    plateau's own two diffusion-controlled points differ by. Toluene is UNTOUCHED
    and stays 4.8x high, which is `rho`'s error, quoted over a -6.0 to -7.3 band
    in G2, and not something a plateau is asked to fix."""
    got = {s: hammett.rate_ratio(NITRATION_RHO, sigma(s)) for s in MEASURED_RATIOS}

    assert got[MESITYLENE] == pytest.approx(485.0, rel=2e-3)
    assert got[P_XYLENE] == pytest.approx(485.0, rel=2e-3)
    assert got[P_XYLENE] / MEASURED_RATIOS[P_XYLENE] == pytest.approx(1.9, abs=0.05)

    assert not hammett.saturates(NITRATION_RHO, sigma(TOLUENE))
    assert got[TOLUENE] / MEASURED_RATIOS[TOLUENE] == pytest.approx(4.8, abs=0.1)

    # ⚠ AND THE UNSATURATED LINE'S ERROR ON MESITYLENE, kept as the size of what
    # this closes: 1.16e6 against a measured 485.
    bare = hammett.rate_ratio(NITRATION_RHO, sigma(MESITYLENE), saturation=math.inf)
    assert bare / MEASURED_RATIOS[MESITYLENE] == pytest.approx(2395.0, rel=0.01)


# ---------------------------------------------------------------------------
# 2. what must not have moved
# ---------------------------------------------------------------------------
def test_everything_under_the_plateau_is_bit_identical_to_the_bare_line():
    """⚠⚠ BIT FOR BIT, NOT CLOSE. A barrier is baked into the kinetics array, so
    a last-bit change is a data-table change and owes a tolerance audit. The
    unsaturated expression is therefore left word for word rather than rewritten
    through an intermediate -- floating-point multiplication is not associative.
    """
    per_decade = hammett._PER_DECADE
    for s in (0.0, -0.311, -0.066, 0.109, -0.179, 0.674, 1.348, 2.022, -0.4):
        assert not hammett.saturates(NITRATION_RHO, s)
        got = hammett.barrier_shift(NITRATION_RHO, s)
        want = 0.0 if s == 0.0 else -per_decade * NITRATION_RHO * s
        assert got == want, s
    assert repr(hammett.barrier_shift(NITRATION_RHO, 0.0)) == "0.0"


def test_lifting_the_plateau_restores_the_bare_line_exactly():
    """``math.inf`` is how the cost of this is measured rather than argued, so it
    has to return the pre-G6 number and not merely a close one."""
    for s in (-1.30, -0.933, -2.220, -0.920, -0.778):
        assert hammett.saturates(NITRATION_RHO, s)
        assert hammett.barrier_shift(NITRATION_RHO, s, math.inf) == (
            -hammett._PER_DECADE * NITRATION_RHO * s
        )


def test_the_plateau_is_one_sided():
    """⚠ AN ENCOUNTER LIMIT IS A CEILING ON THE FAST SIDE ONLY. Nothing caps how
    slow a deactivated ring gets, and the corpus depends on that: three nitro
    groups really are some thirteen decades below benzene."""
    trinitro = 3.0 * 0.674
    assert not hammett.saturates(NITRATION_RHO, trinitro)
    assert hammett.barrier_shift(NITRATION_RHO, trinitro) == (
        -hammett._PER_DECADE * NITRATION_RHO * trinitro
    )
    assert NITRATION_RHO * trinitro < -13.0
    for s in (0.674, 0.86, 1.5, 5.0, 50.0):
        assert not hammett.saturates(NITRATION_RHO, s)


def test_a_two_sided_plateau_would_destroy_the_staging(thermo):
    """⚠⚠ THE DESIGN DECISION, MEASURED ON G2's OWN LADDER RATHER THAN ARGUED.

    A cap written on |rho*sigma| looks more symmetrical and puts 2,4,6-TNT in the
    flask at 340 K, which is the pre-G2 failure the ring-deactivation session
    existed to remove. The one-sided cap leaves the ladder untouched, because the
    whole ladder is on the DEACTIVATING side.
    """
    bare = _stages(thermo, math.inf, 340.0, 3600.0)
    one_sided = _stages(thermo, hammett.SATURATION_DECADES, 340.0, 3600.0)
    two_sided = _stages(thermo, hammett.SATURATION_DECADES, 340.0, 3600.0,
                        two_sided=True)

    for n in range(4):
        assert one_sided.get(n, 0.0) == pytest.approx(
            bare.get(n, 0.0), abs=1e-12
        ), f"the one-sided plateau moved the ladder at {n} nitro groups"
    assert bare[2] > 0.7, "the staged nitration has to still be staged"
    assert two_sided[3] > 0.99, "the two-sided cap has to break it, or no case"


def test_the_corpus_cost_is_zero_where_it_was_measured(thermo):
    """⚠ COSTED AGAINST A REAL ROUTE, AS G2 DID. `benzene-nitration` runs on an
    UNSUBSTITUTED ring, so the plateau must not be able to touch it at all."""
    def yield_of(saturation):
        with contextlib.redirect_stdout(io.StringIO()):
            net = build_network(
                [BENZENE, NITRIC, WATER],
                [aromatic_nitration(saturation=saturation)],
                thermo=thermo, generations=1, max_species=20,
            )
            v = Vessel(net, volume=1.0, T=340.0, T_env=340.0, UA=1.0e6, kla=0.0,
                       k_vent=0.0, k_diss=0.0, lle=False)
            v.charge({BENZENE: 1.0, NITRIC: 1.2, WATER: 5.0})
            v.run(7200.0)
        return v.state().total(NB)

    capped = yield_of(hammett.SATURATION_DECADES)
    assert capped == yield_of(math.inf)
    assert capped == pytest.approx(1.0, abs=1e-4)


# ---------------------------------------------------------------------------
# 3. the form question -- an absolute ceiling could not have expressed this
# ---------------------------------------------------------------------------
def test_an_absolute_encounter_CEILING_would_fire_only_where_a_floor_already_does():
    """⚠⚠ THE MEASUREMENT THAT CHOSE THE MODEL, so it is a test and not a note.

    ``min(k_hammett, k_enc)`` is the physically correct form for an ELEMENTARY
    step. This template's rate law is written on the arene and HNO3, so the
    nitronium pre-equilibrium is folded into ``Ea`` and ``k`` is a stoichiometric
    constant: with the plateau lifted, every substrate whose barrier is still
    positive sits well under a diffusion ceiling, and the only one that reaches it
    is the one ``clamp_barrier`` has already floored at zero. That form would have
    cost an RHS edit and a tolerance audit to guard a case that is guarded.
    """
    def k_diff(T):                       # anchored 7e9 at 298 K, 16 kJ/mol
        return 7.0e9 * math.exp(-16_000.0 / R * (1.0 / T - 1.0 / 298.15))

    def k(smiles, T):
        Ea = hammett.clamp_barrier(
            DECLARED_EA
            + hammett.barrier_shift(NITRATION_RHO, sigma(smiles), math.inf)
        )
        return DECLARED_A * math.exp(-Ea / (R * T))

    for smiles in (BENZENE, TOLUENE, MESITYLENE, PHENOL, ANILINE):
        for T in (300.0, 340.0, 380.0):
            assert k(smiles, T) < 0.05 * k_diff(T), (smiles, T)

    # The one exception, and it is the clamped case: k = A, a decade under this
    # project's COLLISION_LIMIT but above a diffusion ceiling at 300 K.
    assert k(AMINOPHENOL, 300.0) == pytest.approx(DECLARED_A, rel=1e-12)
    assert k(AMINOPHENOL, 300.0) > k_diff(300.0)

    # And the observable is six decades below that ceiling, which is why an
    # absolute constant could not have carried it.
    plateau_k = DECLARED_A * math.exp(-DECLARED_EA / (R * 340.0)) * 10.0 ** (
        hammett.SATURATION_DECADES
    )
    assert plateau_k < 1e-5 * k_diff(340.0)


# ---------------------------------------------------------------------------
# 4. the guard rails
# ---------------------------------------------------------------------------
def test_the_clamp_can_no_longer_fire_on_a_declared_nitration():
    """⚠ THE FLOOR NEEDS 10.51 DECADES OF ACCELERATION AND THE PLATEAU ALLOWS
    2.686, so ``clamp_barrier`` is unreachable on this template -- and the
    function is kept, because the plateau is declared PER TEMPLATE."""
    needed = DECLARED_EA / hammett._PER_DECADE
    assert needed == pytest.approx(10.512, abs=1e-3)
    assert hammett.SATURATION_DECADES < needed

    tmpl = aromatic_nitration()
    for sub in hammett._TABLE:
        for count in (1, 2, 3):
            s = count * sub.sigma
            Ea = DECLARED_EA + hammett.barrier_shift(
                tmpl.hammett_rho, s, tmpl.hammett_saturation
            )
            assert Ea > 0.0, (sub.label, count)
            assert hammett.clamp_barrier(Ea) == Ea

    # ⚠ NOT DEAD CODE: a template with a barrier under the plateau's worth of
    # acceleration reaches the floor immediately.
    small = 10_000.0
    assert hammett.clamp_barrier(
        small + hammett.barrier_shift(NITRATION_RHO, sigma(ANILINE))
    ) == 0.0


def test_the_plateau_is_reported_rather_than_silently_priced(thermo):
    """⚠ THE PROJECT'S THIRD CASE: not an error, not silence, a report. A ring
    priced AT the plateau is no longer on the line the module documents, so
    ``build_network`` says so once."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        build_network([PHENOL, NITRIC, WATER], [aromatic_nitration()],
                      thermo=thermo, generations=1, max_species=20)
    out = buf.getvalue()
    assert "PAST THE ENCOUNTER PLATEAU" in out
    assert "priced AT the plateau" in out

    # ⚠ AND THE NOTICE IT REPLACES NO LONGER FIRES, which is the visible half of
    # `clamp_barrier` becoming unreachable.
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        build_network([AMINOPHENOL, NITRIC, WATER], [aromatic_nitration()],
                      thermo=thermo, generations=1, max_species=6,
                      max_molar_mass=300.0)
    assert "PAST A ZERO BARRIER" not in buf.getvalue()


def test_a_nonpositive_plateau_is_refused():
    """A plateau of zero decades would say every activating substituent is worth
    nothing, which is not what a saturating line does."""
    for bad in (0.0, -1.0):
        with pytest.raises(ValueError, match="ENCOUNTER PLATEAU"):
            aromatic_nitration(saturation=bad)
    with pytest.raises(ValueError, match="ENCOUNTER PLATEAU"):
        ReactionTemplate(name="x", smarts="[cH:1]>>[cH:1]", A=1.0, Ea=1.0,
                         hammett_rho=-1.0, hammett_saturation=0.0)

    # math.inf is legal and means no plateau at all.
    assert aromatic_nitration(saturation=math.inf).hammett_saturation == math.inf


def test_the_plateau_is_declared_per_template_and_defaults_to_the_nitration_value():
    """⚠ A rho IS DECLARED PER TEMPLATE BECAUSE IT IS A PROPERTY OF THE REACTION,
    and so is the plateau it saturates at -- a different electrophile in a
    different medium meets its encounter limit somewhere else."""
    assert aromatic_nitration().hammett_saturation == hammett.SATURATION_DECADES
    assert ReactionTemplate(
        name="x", smarts="[cH:1]>>[cH:1]", A=1.0, Ea=1.0,
    ).hammett_saturation == hammett.SATURATION_DECADES

    # ⚠ AND A TEMPLATE WITH rho = 0 NEVER LOOKS AT IT: no survey is run, so a
    # non-nitrating network cannot have moved.
    plain = ReactionTemplate(name="x", smarts="[cH:1]>>[cH:1]", A=1.0, Ea=1.0,
                             hammett_saturation=0.5)
    mol = Molecule.from_smiles(MESITYLENE)
    assert plain.substituent_barrier((mol,)) == (1.0, hammett.RingSurvey(0.0, (), ()))
