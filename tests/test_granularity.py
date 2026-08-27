"""G4: the five routes the coverage instrument scores blocked and the engine RUNS.

The G-series brief asked how many routes are, like ``benzene-nitration``,
chemically runnable but scored as blocked because the catalog spells a mechanism
out in steps the engine does in one. The audit is
``validation/granularity.py``; **the answer is five**, and this file is what
stops the answer rotting.

Three kinds of test here:

  * that each of the five actually RUNS -- the whole credit rests on the moles,
    not on an argument, and S1's ``crediting a class made a FALSE route credit``
    is the precedent for why;
  * that the two INSTRUMENT facts underneath the count stay true: the corpus's
    ``saponification`` class is credited, and the rows that are not reactions are
    still not reactions;
  * that the one candidate the audit's own scorer credited and the RUN REFUTED
    stays refuted. ``starch-unit`` is spelled as a single glucose ring, so row 1
    (``starch-unit + water -> maltose``) is a hydrolysis that would have to make
    a disaccharide out of a monosaccharide. The engine matches nothing at all,
    and that zero is the assertion.
"""

from __future__ import annotations

import pytest

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import VolatilityProvider, electrolyte_provider
from chemsim.reactions import lead_chamber, sulfur_combustion
from chemsim.reactions.synthesis import (
    alkene_hydrogenation,
    aromatic_nitration,
    ester_hydrolysis,
    glycoside_hydrolysis,
    nitro_hydrogenation,
    saponification,
)
from chemsim.vessel import Vessel


def c(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


@pytest.fixture(scope="module")
def thermo():
    return electrolyte_provider()


@pytest.fixture(scope="module")
def volatility():
    return VolatilityProvider()


def flask(net, T, liquid, seconds, gas=None, solid=None):
    v = Vessel(net, volume=1.0, T=T, T_env=T, UA=1.0e4, kla=1.0, k_vent=0.0,
               k_diss=0.0, lle=False)
    v.charge(liquid)
    if gas:
        v.charge(gas, phase="gas")
    if solid:
        v.charge(solid, phase="solid")
    v.run(seconds)
    return v


WATER, H2, NICKEL = c("O"), c("[H][H]"), "[Ni]"
BENZENE, NITRIC = c("c1ccccc1"), c("O[N+](=O)[O-]")
NITROBENZENE, ANILINE = c("O=[N+]([O-])c1ccccc1"), c("Nc1ccccc1")
TRIOLEIN = c(r"CCCCCCCC/C=C\CCCCCCCC(=O)OCC(OC(=O)CCCCCCC/C=C\CCCCCCCC)"
             r"COC(=O)CCCCCCC/C=C\CCCCCCCC")
TRISTEARIN = c("CCCCCCCCCCCCCCCCCC(=O)OCC(OC(=O)CCCCCCCCCCCCCCCCC)"
               "COC(=O)CCCCCCCCCCCCCCCCC")
TANNIC = c("OC[C@H]1O[C@@H](OC(=O)c2cc(O)c(O)c(O)c2)[C@H](O)[C@@H](O)"
           "[C@@H]1OC(=O)c1cc(O)c(O)c(O)c1")
GALLIC = c("OC(=O)c1cc(O)c(O)c(O)c1")
STARCH_UNIT = c("OC[C@H]1O[C@H](O)[C@H](O)[C@@H](O)[C@@H]1O")
MALTOSE = c("OC[C@H]1O[C@H](O[C@@H]2[C@@H](CO)O[C@@H](O)[C@H](O)[C@H]2O)"
            "[C@H](O)[C@@H](O)[C@@H]1O")
GLUCOSE = c("OC[C@H]1O[C@@H](O)[C@H](O)[C@@H](O)[C@@H]1O")
S8, O2, SO2, NO2, NO, N2 = (c("S1SSSSSSS1"), c("O=O"), c("O=S=O"),
                            c("[O-][N+]=O"), c("[N]=O"), c("N#N"))
SULFURIC = c("OS(=O)(=O)O")


# ---------------------------------------------------------------------------
# the five that RUN
# ---------------------------------------------------------------------------
def test_benzene_nitration_three_catalog_rows_are_one_template(thermo, volatility):
    """SPECIES granularity: the nitronium and the arenium never exist.

    The catalog writes this as ``nitronium-generation`` ->
    ``electrophilic-aromatic-substitution`` -> ``arenium-deprotonation``, and
    both intermediates are correctly REFUSED a price -- a mechanism has them and
    a flask never holds them. So the route fails the SPECIES bar, not the
    template bar, which is why searching the species-ready bucket for it fails.
    """
    net = build_network([BENZENE, NITRIC, WATER], [aromatic_nitration()],
                        thermo=thermo, volatility=volatility, generations=1)
    v = flask(net, 340.0, {BENZENE: 1.0, NITRIC: 1.2, WATER: 5.0}, 7200.0)
    assert v.state().total(c("O=[N+]([O-])c1ccccc1")) == pytest.approx(1.0, abs=1e-3)


def test_aniline_route_row_two_is_an_alternative_to_row_one(thermo, volatility):
    """Nobody has to do the Bechamp reduction; row 2 makes the same product.

    The two rows are ALTERNATIVES from the same substrate to the same product,
    and the row scorer reads them as a sequence -- so one missing template
    (``dissolving-metal-reduction``) blocks a route the other row completes.
    """
    net = build_network([NITROBENZENE, H2, WATER, NICKEL], [nitro_hydrogenation()],
                        thermo=thermo, volatility=volatility)
    v = flask(net, 470.0, {NITROBENZENE: 1.0, WATER: 5.0}, 7200.0,
              gas={H2: 4.0}, solid={NICKEL: 0.1})
    assert v.state().total(ANILINE) > 0.99


def test_margarine_row_two_is_the_corpus_s_own_byproduct(thermo, volatility):
    """The blocking row's own name is "trans isomer byproduct".

    ⚠ And its class is ``isomerisation``, which is dead three times over --
    ``oleic -> elaidic`` prices at dH = dG = 0.000 EXACTLY because the estimators
    cannot tell a cis alkene from a trans one. So the row that blocks this route
    is one the project has already decided it will not build.
    """
    net = build_network([TRIOLEIN, H2, NICKEL], [alkene_hydrogenation()],
                        thermo=thermo, volatility=volatility)
    v = flask(net, 450.0, {TRIOLEIN: 1.0}, 7200.0, gas={H2: 6.0},
              solid={NICKEL: 0.1})
    assert v.state().total(TRISTEARIN) == pytest.approx(1.0, abs=1e-3)


def test_tanning_route_reaches_its_target_before_the_marker_row(thermo, volatility):
    """The target is row 1's product; row 2 crosslinks collagen into a MARKER.

    ⚠ TWO moles of gallic acid, not one, and nobody wrote that down: the
    ``tannic-acid-core`` carries two galloyl esters and the template takes both.
    """
    net = build_network([TANNIC, WATER], [ester_hydrolysis()], thermo=thermo,
                        volatility=volatility)
    v = flask(net, 360.0, {TANNIC: 1.0, WATER: 20.0}, 7200.0)
    assert v.state().total(GALLIC) == pytest.approx(2.0, abs=1e-3)


def test_lead_chamber_runs_from_native_sulfur_in_two_stages(thermo, volatility):
    """The blocking row makes CHAMBER CRYSTALS -- the process's fouling product.

    ⚠ TWO VESSELS AT TWO TEMPERATURES, and that is the chemistry rather than a
    workaround: sulfur burns hot and the gas is absorbed cold. The NOx carrier
    coming back out untouched is the assertion that this is a real catalytic
    cycle and not a reagent being consumed.
    """
    burn = build_network([S8, O2, N2], [sulfur_combustion()], thermo=thermo,
                         volatility=volatility)
    vb = Vessel(burn, volume=1.0, T=650.0, T_env=650.0, UA=1.0e4, kla=5.0,
                k_vent=0.0, k_diss=0.05, lle=False)
    vb.charge({S8: 0.02, O2: 0.40, N2: 0.02})
    vb.run(600.0)
    so2 = vb.state().total(SO2)
    assert so2 == pytest.approx(0.16, abs=1e-4)

    chamber = build_network([SO2, NO2, NO, WATER, O2, N2], lead_chamber(),
                            thermo=thermo, volatility=volatility)
    vc = Vessel(chamber, volume=2.0, T=350.0, T_env=350.0, UA=1.0e4, kla=5.0,
                k_vent=0.0, k_diss=0.05, lle=False)
    vc.charge({SO2: so2, O2: 0.05, N2: 0.10, WATER: 0.60, NO2: 0.004})
    vc.run(3600.0)
    st = vc.state()
    assert st.total(SULFURIC) > 0.10
    # the carrier is a constant of the motion
    assert st.total(NO2) + st.total(NO) == pytest.approx(0.004, rel=1e-6)


# ---------------------------------------------------------------------------
# the one the scorer credited and the RUN refuted
# ---------------------------------------------------------------------------
def test_starch_hydrolysis_is_refuted_from_its_declared_feedstock(thermo, volatility):
    """⚠⚠ THE AUDIT'S OWN SCORER GOT THIS ONE WRONG AND ONLY RUNNING SAID SO.

    ``starch-unit`` is spelled in the corpus as a single alpha-D-glucopyranose
    ring, and row 1 reads ``starch-unit + water -> maltose``. A hydrolysis
    cannot make a disaccharide out of a monosaccharide and water, and the engine
    says so by matching NOTHING -- zero reactions, not a slow one.

    ⚠ The zero is the assertion. The day someone re-spells ``starch-unit`` as a
    real polymer fragment, this test is what tells them the route opened.
    """
    net = build_network([STARCH_UNIT, WATER], [glycoside_hydrolysis()],
                        thermo=thermo, volatility=volatility)
    assert net.reactions == []


def test_starch_hydrolysis_reaches_glucose_from_the_intermediate(thermo, volatility):
    """...and it is not the TEMPLATE that is missing, which is the other half.

    From maltose -- the thing row 1 was supposed to make -- the same template
    delivers the target. So the blockage is the corpus's spelling of its own
    feedstock, and no engine work would move it.
    """
    net = build_network([MALTOSE, WATER], [glycoside_hydrolysis()], thermo=thermo,
                        volatility=volatility)
    v = flask(net, 360.0, {MALTOSE: 1.0, WATER: 20.0}, 7200.0)
    assert v.state().total(GLUCOSE) > 0.99


# ---------------------------------------------------------------------------
# the two INSTRUMENT facts the count rests on
# ---------------------------------------------------------------------------
def test_saponification_fires_on_the_catalog_s_own_substrate(thermo, volatility):
    """The class the coverage map never keyed, checked the S1 way: by running it.

    ``TEMPLATE_CLASSES`` credited this template under ``ester-hydrolysis``'s
    name, so the catalog's own ``saponification`` class read as an uncovered
    mechanism for eight milestones. It is not: all three esters of the
    ``soap-saponification`` row's tristearin come off, down to glycerol.
    """
    net = build_network([TRISTEARIN, c("[OH-]"), c("[Na+]"), WATER],
                        [saponification()], thermo=thermo, volatility=volatility,
                        max_species=60)
    made = [r for r in net.reactions if r.name.startswith("saponification")]
    assert len(made) >= 5
    assert c("OCC(O)CO") in net.species          # glycerol, all three esters off
    assert c("CCCCCCCCCCCCCCCCCC(=O)[O-]") in net.species


def test_the_corpus_still_has_rows_that_make_nothing_new():
    """Five rows whose products are a SUBSET of their reactants.

    ⚠ These can never match a template, whatever anyone builds -- they are
    workup (crystallisation, salting out, lixiviation, absorption into
    kieselguhr) and one row that is simply wrong (``furfural-route`` 1 reads
    ``xylose + water -> xylose``). A coverage number that counts them as
    uncovered mechanisms is counting a gap that no template can close.

    ⚠ The count is asserted so that a row ADDED to this shape is noticed. If
    this fails, read ``validation/granularity.py`` panel 2a and decide which of
    the two numbers is wrong.
    """
    import os
    import sys

    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
    import catalog as cat

    dead = [s for s in cat.load_steps() if set(s.products) <= set(s.reactants)]
    assert len(dead) == 5
    assert {s.route for s in dead} == {
        "leblanc-process", "nitroglycerin-route", "aspirin-route",
        "soap-saponification", "furfural-route",
    }
