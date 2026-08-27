"""G2 -- a substituent-aware barrier, so nitration is a PROCESS and not an EVENT.

The gap, measured before any of this was written: `aromatic_nitration` gave one
`A` and one `Ea` to every nitration on every substrate, so 1.0 mol of toluene and
3.5 mol of nitric acid reached the same four numbers at 300 K after ten seconds
and at 380 K after a thousand. There was no stage to catch.

What is tested here is the four questions the brief said to answer before writing
any code, in the order they bite: where it lives, what it is anchored on, whether
it collapses to the old behaviour, and what it costs the corpus.
"""

from __future__ import annotations

import numpy as np
import pytest
from rdkit import Chem

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider
from chemsim.reactions import hammett
from chemsim.reactions.synthesis import NITRATION_RHO, aromatic_nitration
from chemsim.reactions.template import ReactionTemplate
from chemsim.vessel import Vessel


def c(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


BENZENE, TOLUENE = c("c1ccccc1"), c("Cc1ccccc1")
NITRIC, WATER = c("O[N+](=O)[O-]"), c("O")
NITROBENZENE = c("O=[N+]([O-])c1ccccc1")


@pytest.fixture(scope="module")
def thermo():
    return ThermochemistryProvider()


def _net(thermo, seed, rho=NITRATION_RHO, max_species=80):
    return build_network([seed, NITRIC, WATER], [aromatic_nitration(rho=rho)],
                         thermo=thermo, max_species=max_species,
                         max_molar_mass=300.0)


def _nitro(smiles: str) -> int:
    return smiles.count("[N+](=O)[O-]")


def _stages(v: Vessel) -> dict[int, float]:
    st = v.state()
    out: dict[int, float] = {}
    for s in v.species:
        if s in (NITRIC, WATER) or "c" not in s:
            continue
        out[_nitro(s)] = out.get(_nitro(s), 0.0) + st.total(s)
    return out


# ---------------------------------------------------------------------------
# 3. does it collapse to today's behaviour?  -- the contract, tested first
# ---------------------------------------------------------------------------


def test_an_unsubstituted_ring_keeps_the_declared_barrier_bit_for_bit(thermo):
    """The contract every optional term in this engine carries.

    ⚠ BIT FOR BIT rather than close, and ``barrier_shift`` is written to make
    that true by returning a literal ``0.0`` when either factor is zero -- so the
    addition never happens rather than adding a small float.

    ⚠ The network is capped at FOUR species on purpose. The first draft of the
    matching audit panel used five, which lets one dinitrobenzene in, and then
    reported "not identical" while printing two numbers that both read
    60000.000000 -- the disagreeing entry was the second reaction, on a ring that
    is no longer unsubstituted. A bit-identity claim has to be about the thing it
    is a claim about.
    """
    old = _net(thermo, BENZENE, rho=0.0, max_species=4)
    new = _net(thermo, BENZENE, max_species=4)
    assert len(old.reactions) == 1
    assert old.species == new.species
    a, b = old.to_arrays(thermo), new.to_arrays(thermo)
    assert np.array_equal(a.Ea, b.Ea)
    assert np.array_equal(a.A, b.A)
    assert np.array_equal(a.delta, b.delta)
    assert hammett.barrier_shift(NITRATION_RHO, 0.0) == 0.0
    assert repr(hammett.barrier_shift(NITRATION_RHO, 0.0)) == "0.0"


def test_a_template_that_declares_no_rho_never_runs_a_survey(thermo):
    """Every other template in the library leaves ``hammett_rho`` at 0.0, so no
    network that does not nitrate an arene has moved at all. Tested through the
    template rather than by trusting the default."""
    plain = ReactionTemplate(
        name="plain", smarts="[cH:1].[OX2H1:2][N+:3](=[O:4])[O-:5]"
                             ">>[c:1][N+:3](=[O:4])[O-:5].[OX2H2:2]",
        A=1.0e10, Ea=60_000.0,
    )
    assert plain.hammett_rho == 0.0
    reactants = (Molecule.from_smiles("Cc1ccccc1"),
                 Molecule.from_smiles("O[N+](=O)[O-]"))
    Ea, survey = plain.substituent_barrier(reactants)
    assert Ea == 60_000.0
    assert survey.sigma_sum == 0.0 and survey.found == ()


# ---------------------------------------------------------------------------
# 1. where it lives  -- setup, therefore no RHS exposure
# ---------------------------------------------------------------------------


def test_the_barrier_ladder_is_baked_at_setup_and_is_25_kJ_per_nitro_group(thermo):
    """One declared Ea, four barriers, computed once when the network is built.

    ⚠ THE SPACING IS NOT A CONSTANT ANYBODY TYPED. It is
    ``-ln(10) * R * 298.15 * rho * sigma+_meta(NO2)`` = -5708 * -6.5 * 0.674,
    and the test asserts it against that expression rather than against 25000 --
    a literal would pass just as well if the derivation were wrong.
    """
    net = _net(thermo, TOLUENE)
    arr = net.to_arrays(thermo)
    rungs: dict[int, set[float]] = {}
    for j, r in enumerate(net.reactions):
        substrate = next(x for x in r.reactants if x != NITRIC)
        rungs.setdefault(_nitro(substrate), set()).add(float(arr.Ea[j]))

    assert set(rungs) >= {0, 1, 2, 3}
    for k, values in rungs.items():
        assert len(values) == 1, f"{k} nitro groups gave several barriers"

    step = hammett.barrier_shift(NITRATION_RHO, hammett._TABLE[0].sigma)
    assert hammett._TABLE[0].label == "nitro"
    flat = {k: next(iter(v)) for k, v in rungs.items()}
    for k in (1, 2, 3):
        assert flat[k] - flat[k - 1] == pytest.approx(step, rel=1e-12)
    assert step == pytest.approx(25_010.0, abs=10.0)

    # and toluene's own ring is ACTIVATED, below the declared 60 kJ/mol
    assert flat[0] < 60_000.0
    assert flat[0] == pytest.approx(
        60_000.0 + hammett.barrier_shift(NITRATION_RHO, -0.311), rel=1e-12
    )


# ---------------------------------------------------------------------------
# 2. what it is anchored on
# ---------------------------------------------------------------------------


def test_the_anchor_is_298_K_and_not_the_networks_build_temperature(thermo):
    """⚠ ASK WHAT A FIT WAS ANCHORED ON. sigma+ and rho are tabulated from rate
    ratios measured at 25 C, so 25 C is the only temperature at which this
    conversion reproduces the number it came from. Building the same network at a
    different ``T_ref`` must not move a barrier, or the same template would mean
    different things in two scenarios with no measurement saying it should."""
    assert hammett.T_HAMMETT == 298.15
    cold = build_network([TOLUENE, NITRIC, WATER], [aromatic_nitration()],
                         thermo=thermo, max_species=20, max_molar_mass=300.0,
                         T_ref=280.0)
    hot = build_network([TOLUENE, NITRIC, WATER], [aromatic_nitration()],
                        thermo=thermo, max_species=20, max_molar_mass=300.0,
                        T_ref=500.0)
    assert np.array_equal(cold.to_arrays(thermo).Ea, hot.to_arrays(thermo).Ea)


def test_the_relation_reads_back_as_the_hammett_ratio_at_the_anchor():
    """``dEa`` and ``log10(k/k0) = rho * sigma`` are the same statement, and the
    round trip is exact at 298.15 K by construction."""
    for sigma in (-1.3, -0.311, 0.0, 0.674, 1.348):
        got = hammett.rate_ratio(NITRATION_RHO, sigma)
        assert got == pytest.approx(10.0 ** (NITRATION_RHO * sigma), rel=1e-10)


def test_a_rho_and_an_alpha_may_not_be_declared_together():
    """⚠⚠ THE TRAP THIS ITEM WAS SCOPED AROUND. `alpha` shifts the barrier with
    the REACTION ENTHALPY; `rho` shifts it with the SUBSTRATE'S ELECTRONICS, and
    on an aromatic ring those are two readings of one cause. Measured on this
    network they also disagree in SIGN -- benzene -> nitrobenzene is -141.2
    kJ/mol and nitrobenzene -> dinitrobenzene is -268.1 -- so a positive alpha
    makes the DEACTIVATED ring react faster, which is exactly backwards."""
    with pytest.raises(ValueError, match="BOTH alpha"):
        aromatic_nitration(alpha=0.3)
    with pytest.raises(ValueError, match="hammett_slot"):
        ReactionTemplate(name="x", smarts="[cH:1]>>[cH:1]", A=1.0, Ea=1.0,
                         hammett_rho=-1.0, hammett_slot=4)


def test_the_directing_rule_is_declared_because_the_halogens_break_the_obvious_one():
    """⚠ Chlorine is DEACTIVATING (sigma+_para +0.114) and ORTHO/PARA directing.
    A rule of "meta-directing iff sigma_para > 0" would put the incoming group in
    the wrong place on every halobenzene in the corpus, so it is data."""
    table = {s.label: s for s in hammett._TABLE}
    for halogen in ("fluoro", "chloro", "bromo", "iodo"):
        s = table[halogen]
        assert not s.meta_directing
        assert s.sigma_m > 0.0, "all four deactivate the meta position"
        assert s.sigma is s.sigma_p or s.sigma == s.sigma_p
    assert table["nitro"].meta_directing and table["nitro"].sigma_p > 0.0
    assert not table["amino"].meta_directing and table["amino"].sigma_p < 0.0


def test_the_scale_is_sigma_plus_and_the_two_proxy_rows_are_both_acceptors():
    """⚠⚠ A rho IS MEANINGLESS WITHOUT ITS SIGMA SCALE -- S12's finding in
    another suit. Two rows have no published sigma+ and use the aqueous sigma;
    both must be ELECTRON ACCEPTORS, which is the case where the two scales
    agree, and both must say so in their ``source``."""
    proxies = [s for s in hammett._TABLE if s.source == hammett.SIGMA_PROXY]
    assert proxies, "the labelling is load-bearing; do not silently remove it"
    for s in proxies:
        assert s.sigma_m > 0.0 and s.sigma_p > 0.0, (
            f"{s.label} is a DONOR, where sigma+ and sigma disagree by up to 0.6 "
            f"-- it may not use the proxy"
        )
    others = [s for s in hammett._TABLE if s.source != hammett.SIGMA_PROXY]
    assert all(s.source == hammett.BROWN_OKAMOTO for s in others)
    # the scale is the one that matters: methoxy is -0.27 on sigma, -0.778 here
    assert dict((s.label, s.sigma_p) for s in hammett._TABLE)["alkoxy"] < -0.6


# ---------------------------------------------------------------------------
# the survey itself
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("smiles,expect,labels", [
    ("c1ccccc1", 0.0, ()),
    ("Cc1ccccc1", -0.311, ("alkyl",)),
    ("O=[N+]([O-])c1ccccc1", 0.674, ("nitro",)),
    ("Cc1cc([N+](=O)[O-])ccc1[N+](=O)[O-]", -0.311 + 2 * 0.674,
     ("alkyl", "nitro", "nitro")),
    ("Nc1ccccc1", -1.30, ("amino",)),
    ("CC(=O)Nc1ccccc1", -0.600, ("acylamino",)),
    ("Clc1ccccc1", 0.114, ("chloro",)),
])
def test_the_survey_finds_what_is_on_the_ring(smiles, expect, labels):
    got = hammett.survey(Chem.MolFromSmiles(smiles))
    assert got.sigma_sum == pytest.approx(expect, abs=1e-9)
    assert got.found == tuple(sorted(labels))
    assert got.unknown == ()


def test_the_specific_patterns_win_over_the_general_ones():
    """⚠ ORDER IS SIGNIFICANT IN THE TABLE, and both cases are in the corpus.
    An acetamido group answers ``[c][NX3]`` as readily as an amine does, so
    paracetamol would be priced as an aniline -- -1.30 instead of -0.600, a
    factor of 4e4 in rate."""
    para = hammett.survey(Chem.MolFromSmiles("CC(=O)Nc1ccc(O)cc1"))
    assert set(para.found) == {"acylamino", "hydroxy"}
    assert "amino" not in para.found
    assert para.sigma_sum == pytest.approx(-0.600 + -0.920, abs=1e-9)


def test_an_ester_oxygen_on_the_ring_is_reported_rather_than_priced_as_a_methoxy():
    """⚠ Aspirin's -OC(=O)CH3 is an ester oxygen whose lone pair is tied up in
    the carbonyl, so it is nothing like a methoxy. No sigma+ for it is sourced,
    so it falls through to ``unknown`` and is REPORTED -- the project's third
    case. Pricing it at -0.778 would make aspirin's ring more reactive than
    anisole's, which is the confident wrong number this refuses to give."""
    aspirin = hammett.survey(Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O"))
    assert "alkoxy" not in aspirin.found
    assert aspirin.found == ("carboxy",)
    assert aspirin.unknown == ("-O on an aromatic carbon",)
    anisole = hammett.survey(Chem.MolFromSmiles("COc1ccccc1"))
    assert anisole.found == ("alkoxy",) and anisole.unknown == ()


def test_a_ring_bond_is_not_a_substituent_and_a_biaryl_bond_is():
    """The two ways an aromatic carbon can have an aromatic neighbour."""
    assert hammett.survey(Chem.MolFromSmiles("c1ccccc1")).unknown == ()
    biphenyl = hammett.survey(Chem.MolFromSmiles("c1ccc(-c2ccccc2)cc1"))
    assert biphenyl.found == ("aryl",)
    assert biphenyl.unknown == (), "the bond is claimed from BOTH ends"


def test_a_barrier_may_not_go_negative_and_the_floor_is_reachable(thermo):
    """⚠ NOT A DEFENSIVE FLOOR. 4-aminophenol's sum(sigma+) is -2.220, worth
    -82.4 kJ/mol against a declared 60 -- and a negative activation energy is a
    rate that RISES as the flask cools, which is not a fast reaction but a wrong
    one. The clamp keeps the arithmetic legal; the missing physics is that an
    amine in mixed acid is an ANILINIUM ion, and that is named, not fixed."""
    s = hammett.survey(Chem.MolFromSmiles("Nc1ccc(O)cc1"))
    raw = 60_000.0 + hammett.barrier_shift(NITRATION_RHO, s.sigma_sum)
    assert raw < 0.0, "the floor has to be reachable or the test proves nothing"
    assert hammett.clamp_barrier(raw) == 0.0

    net = build_network([c("Nc1ccc(O)cc1"), NITRIC, WATER],
                        [aromatic_nitration()], thermo=thermo, max_species=6,
                        max_molar_mass=300.0)
    assert (net.to_arrays(thermo).Ea >= 0.0).all()


# ---------------------------------------------------------------------------
# 4. what it costs -- the trajectory, which is the whole point
# ---------------------------------------------------------------------------


def test_the_endpoint_used_not_to_move_with_temperature_and_now_does(thermo):
    """⚠⚠ THE FINDING. The pre-G2 block is identical at every temperature and
    every time; the post-G2 one is a three-stage process."""
    flat = _net(thermo, TOLUENE, rho=0.0)
    staged = _net(thermo, TOLUENE)

    def run(net, T, seconds):
        v = Vessel(net, volume=1.0, T=T, T_env=T, UA=1.0e6, kla=0.0,
                   k_vent=0.0, k_diss=0.0, lle=False)
        v.charge({TOLUENE: 1.0, NITRIC: 3.5, WATER: 5.0})
        v.run(seconds)
        return _stages(v)

    a = run(flat, 300.0, 10.0)
    for T, seconds in ((300.0, 100.0), (340.0, 10.0), (380.0, 1000.0)):
        b = run(flat, T, seconds)
        for k in a:
            # ⚠ 0.5% and not 1e-9. The pre-G2 endpoint is the same at every
            # temperature to three figures and moves by ~2e-4 relative across
            # the sweep, which is BDF's error control and not the chemistry --
            # pinning it tighter would be pinning the solver. Three figures is
            # plenty: the claim being made is that a 80 K change and a 100x
            # change in time move NOTHING, and they move the third decimal.
            assert b[k] == pytest.approx(a[k], rel=5e-3, abs=1e-5), (
                "the pre-G2 endpoint is the same at every temperature -- that is "
                "the gap, and this test exists so removing it is deliberate"
            )

    cool = run(staged, 300.0, 10.0)
    warm = run(staged, 300.0, 100.0)
    hot = run(staged, 380.0, 1000.0)
    assert cool[1] > cool[2], "ten seconds at room temperature is MONOnitration"
    assert warm[2] > warm[1], "a hundred seconds takes it to DI"
    assert hot[3] > 0.5, "only 380 K takes it to TRI"
    assert cool[3] < 1e-3, "and room temperature does not reach tri at all"


def test_deactivation_lets_a_mononitration_stop(thermo):
    """The corpus cost, and it is an IMPROVEMENT on the route the plan named as
    proof the scoreboard understates. 1.0 mol benzene + 1.2 mol nitric acid, 340
    K, 2 h: the pre-G2 engine ran straight past nitrobenzene into di- and
    trinitrobenzene and left 0.18 mol; with a deactivated ring it stops at
    0.80."""
    args = dict(T=340.0, seconds=7200.0)
    def yield_of(rho):
        net = _net(thermo, BENZENE, rho=rho, max_species=30)
        v = Vessel(net, volume=1.0, T=args["T"], T_env=args["T"], UA=1.0e6,
                   kla=0.0, k_vent=0.0, k_diss=0.0, lle=False)
        v.charge({BENZENE: 1.0, NITRIC: 1.2, WATER: 5.0})
        v.run(args["seconds"])
        return v.state().total(NITROBENZENE)

    before, after = yield_of(0.0), yield_of(NITRATION_RHO)
    assert before == pytest.approx(0.176, abs=0.01)
    assert after == pytest.approx(0.800, abs=0.01)
    assert after > 4 * before
