"""C1 -- oil of vitriol from a rock, and the class bucket that was hiding it.

The claims, one group each, because each was measured before anything was
written and two of them changed what the milestone was:

  * **the arrow** -- ``SO3 + H2O -> H2SO4`` was the whole of what stood between
    this engine and sulfuric acid made from a natural mineral. The retort half
    has been declared in ``properties/solid_state.py`` since M6.
  * **the SMARTS is narrow on purpose** -- the product of this reaction carries
    the reactant's own functional group in all but the sulfur's DEGREE, so a
    looser pattern would be self-feeding. ``[SX3]`` is what stops it, and the
    five things it must not match are pinned.
  * **the ceiling is emergent** -- ``ln K = 0`` at 664.3 K, which is ``dH/dS`` on
    three experimental formation rows. A receiver has to be cool, and nobody
    typed that. Pinned against the analytic root of the same equilibrium so a
    future solver change cannot quietly report a stall as an equilibrium.
  * **the rate law is forgiven** -- five decades of pre-exponential, one answer.
    That is what licences an APPARENT barrier standing in for a reaction whose
    real gas-phase form is second order in water.
  * **the liquid channel was built and REFUSED** -- pinned as the wrong answer,
    with the conservation residual that decided it, so a future
    ``phase="any"`` shows up as a test failure rather than as a tidier bundle.
  * **the corpus** -- ``hydrolysis`` held eight rows and seven of its own family's
    mechanism names already existed. The split is pinned by name, and so is the
    one row whose class was DECIDED rather than derived.
"""

from __future__ import annotations

import math
import os
import sys

import pytest

from chemsim.constants import R, R_L_BAR
from chemsim.network import build_network
from chemsim.properties.mineral_data import MINERALS
from chemsim.reactions import (
    ReactionTemplate,
    sulfur_trioxide_hydration,
    vitriol_receiver,
)
from chemsim.vessel import Vessel

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in ("tools", "validation"):
    _full = os.path.join(_ROOT, _p)
    if _full not in sys.path:
        sys.path.insert(0, _full)

VITRIOL = MINERALS["green vitriol"].lattice
HEMATITE = MINERALS["hematite"].lattice
SO2, SO3, WATER = "O=S=O", "O=S(=O)=O", "O"
# ⚠ the canonical key, not the way a chemist writes it. ``OS(=O)(=O)O`` is the
# same molecule and a different string, and reading the state vector with it
# gives a panel of silent zeroes.
H2SO4 = "O=S(=O)(O)O"
TIGHT = dict(rtol=1.0e-8, atol=1.0e-11)


@pytest.fixture(scope="module")
def retort(thermo_module):
    from chemsim.properties import VolatilityProvider

    return build_network([VITRIOL, HEMATITE, SO2, SO3], [], thermo=thermo_module,
                         volatility=VolatilityProvider(thermo_module))


@pytest.fixture(scope="module")
def receiver(thermo_module):
    from chemsim.properties import VolatilityProvider

    return build_network([SO3, WATER, H2SO4], vitriol_receiver(),
                         thermo=thermo_module,
                         volatility=VolatilityProvider(thermo_module))


def _total(v, s):
    st = v.state()
    return float(st.n_liquid.get(s, 0.0) + st.n_liquid2.get(s, 0.0)
                 + st.n_gas.get(s, 0.0) + st.n_solid.get(s, 0.0))


# ---------------------------------------------------------------------------
# 1. THE SMARTS, AND THE FIVE THINGS IT MUST NOT MATCH
# ---------------------------------------------------------------------------
def _fires_on(smiles: str) -> bool:
    from rdkit import Chem
    from rdkit.Chem import AllChem

    rxn = AllChem.ReactionFromSmarts(sulfur_trioxide_hydration().smarts)
    return bool(rxn.RunReactants((Chem.MolFromSmiles(smiles),
                                  Chem.MolFromSmiles(WATER))))


def test_the_template_makes_sulfuric_acid_from_the_trioxide():
    from rdkit import Chem
    from rdkit.Chem import AllChem

    rxn = AllChem.ReactionFromSmarts(sulfur_trioxide_hydration().smarts)
    out = set()
    for tup in rxn.RunReactants((Chem.MolFromSmiles(SO3),
                                 Chem.MolFromSmiles(WATER))):
        for m in tup:
            Chem.SanitizeMol(m)
            out.add(Chem.MolToSmiles(m))
    assert out == {H2SO4}


@pytest.mark.parametrize("smiles, what", [
    ("OS(=O)(=O)O", "its own product -- a looser pattern would be self-feeding"),
    ("O=S(=O)(O)OS(=O)(=O)O", "disulfuric acid: `oleum-hydrolysis` is a "
                              "SEPARATE class and is NOT credited by this"),
    ("O=S=O", "sulfur dioxide, which the same retort makes in equal amount"),
    ("CS(=O)(=O)O", "any other sulfonyl group in the corpus"),
    ("O=S(=O)([O-])[O-].[Fe+2]", "the sulfate lattice this route starts from"),
])
def test_the_pattern_is_narrow(smiles, what):
    """``[SX3]`` and three terminal oxygens. Degree is what separates them."""
    assert not _fires_on(smiles), what


# ---------------------------------------------------------------------------
# 2. THE RETORT -- a threshold nobody typed, and the residue the catalog denied
# ---------------------------------------------------------------------------
def test_the_retort_has_a_threshold_and_leaves_hematite(retort):
    """Nothing at 700 K, complete at 1000 K, and the residue is Fe2O3.

    ⚠ The catalog row read ``-> iron-ii-oxide + sulfur-trioxide`` until C1 and
    ``iron-ii-oxide`` is REFUSED a price, so `vitriol-distillation` was blocked
    on a datum for a species the engine has never made. ``solid_state.py`` has
    said hematite since M6 and said in its own comment that the row was wrong.
    """
    cold = Vessel(retort, volume=1.0, T=700.0, T_env=700.0, UA=1.0e4, k_vent=0.0)
    cold.charge({VITRIOL: 0.10}, phase="solid")
    cold.run(2000.0, **TIGHT)
    # ⚠ THE THRESHOLD IS SOFT AND THAT IS ASSERTED RATHER THAN ROUNDED AWAY.
    # 700 K converts 1.9e-07 mol -- two parts per million of the charge -- which
    # a six-decimal panel prints as 0.100000. It is a smooth K(T), not a switch.
    left = float(cold.state().n_solid[VITRIOL])
    assert 0.10 - left < 1.0e-6
    assert 0.10 - left > 0.0

    hot = Vessel(retort, volume=1.0, T=1000.0, T_env=1000.0, UA=1.0e4, k_vent=0.0)
    hot.charge({VITRIOL: 0.10}, phase="solid")
    hot.run(2000.0, **TIGHT)
    st = hot.state()
    assert float(st.n_solid[VITRIOL]) == pytest.approx(0.0, abs=1e-9)
    # 2 FeSO4 -> Fe2O3 + SO2 + SO3, so 0.05 of each from 0.10 of the mineral
    assert float(st.n_solid[HEMATITE]) == pytest.approx(0.05, rel=1e-6)
    assert float(st.n_gas[SO2]) == pytest.approx(0.05, rel=1e-6)
    assert float(st.n_gas[SO3]) == pytest.approx(0.05, rel=1e-6)


# ---------------------------------------------------------------------------
# 3. THE RECEIVER, AND THE CONDENSER IS WHY IT IS QUANTITATIVE
# ---------------------------------------------------------------------------
def test_the_receiver_is_quantitative_up_to_six_hundred_kelvin(receiver):
    """100.000% at 350 K and at 600 K, across twelve orders of magnitude of K.

    Not because the equilibrium is generous at 600 K -- ``ln K`` is 1.89 there --
    but because sulfuric acid boils at 610 K and leaves the gas phase as fast as
    it forms. Le Chatelier, done by a phase change the template knows nothing
    about. The panel that shows the equilibrium ALONE is the next test.
    """
    for T in (350.0, 600.0):
        v = Vessel(receiver, volume=1.0, T=T, T_env=T, UA=1.0e4, k_vent=0.0)
        v.charge({WATER: 1.0}, phase="liquid")
        v.charge({SO3: 0.05}, phase="gas")
        v.run(600.0, **TIGHT)
        assert _total(v, H2SO4) / 0.05 == pytest.approx(1.0, abs=1.0e-3)
        assert v.conservation_report() == ""


# ---------------------------------------------------------------------------
# 4. THE CEILING IS EMERGENT, AND IT AGREES WITH THE QUADRATIC
# ---------------------------------------------------------------------------
def test_the_acid_cracks_back_above_six_six_four_kelvin(receiver, thermo_module):
    """``ln K = 0`` at ``dH/dS`` = 664.3 K, and the solver lands on the root.

    ⚠ THE ANALYTIC CHECK IS THE POINT OF THIS TEST rather than the temperature.
    A conversion falling with heat is also what a solver that has stopped early
    looks like; agreeing with the closed-form root of the same K is what
    distinguishes an equilibrium from a stall.
    """
    th = thermo_module
    dH = th.get(H2SO4).Hf - th.get(SO3).Hf - th.get(WATER).Hf
    dG = th.get(H2SO4).Gf - th.get(SO3).Gf - th.get(WATER).Gf
    dS = (dH - dG) / 298.15
    assert dH / dS == pytest.approx(664.3, abs=0.5)

    for T in (664.3, 800.0):
        lnK = -(dH - T * dS) * 1000.0 / (R * T)
        K = math.exp(lnK)
        c = R_L_BAR * T / 10.0          # bar per mole in a 10 L flask
        b = 2.0 + 1.0 / (K * 0.05 * c)
        x = (b - math.sqrt(b * b - 4.0)) / 2.0

        v = Vessel(receiver, volume=10.0, T=T, T_env=T, UA=1.0e4, k_vent=0.0)
        v.charge({SO3: 0.05, WATER: 0.05}, phase="gas")
        v.run(600.0, **TIGHT)
        assert _total(v, H2SO4) / 0.05 == pytest.approx(x, rel=1.0e-3)
    # and it really is a ceiling: 46.8% at 600 K against 1.6% at 800 K
    assert x < 0.02


# ---------------------------------------------------------------------------
# 5. THE PRE-EXPONENTIAL IS FORGIVEN, WHICH IS WHAT LICENCES AN APPARENT BARRIER
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("A", [1.0e6, 1.0e11])
def test_five_decades_of_pre_exponential_give_one_answer(A, thermo_module):
    """The real gas reaction is second order in water; this one is not.

    That is only defensible because the answer does not read the constant. Ends
    of the swept range are pinned here; ``validation/vitriol.py`` panel 4 prints
    all four rungs.
    """
    from chemsim.properties import VolatilityProvider

    n = build_network([SO3, WATER, H2SO4], [sulfur_trioxide_hydration(A=A)],
                      thermo=thermo_module,
                      volatility=VolatilityProvider(thermo_module))
    v = Vessel(n, volume=1.0, T=350.0, T_env=350.0, UA=1.0e4, k_vent=0.0)
    v.charge({WATER: 1.0}, phase="liquid")
    v.charge({SO3: 0.05}, phase="gas")
    v.run(600.0, **TIGHT)
    assert _total(v, H2SO4) == pytest.approx(0.05, rel=1.0e-6)


def test_the_declared_order_was_refused_and_the_reverse_is_why():
    """``orders`` and ``reversible`` cannot both be set -- the trade, asserted.

    The more correct rate law is second order in water and it is not declared,
    because a declared order has no detailed-balance partner and the reverse is
    the mechanic (test 4). Pinned as an engine CONSTRAINT so that a future
    relaxation of it is a prompt to revisit this template rather than a silent
    new freedom.
    """
    assert sulfur_trioxide_hydration().orders is None
    assert sulfur_trioxide_hydration().reversible
    with pytest.raises(ValueError):
        ReactionTemplate(
            name="x", smarts=sulfur_trioxide_hydration().smarts,
            A=1.0e10, Ea=23_600.0, phase="gas", reversible=True,
            orders=(1.0, 2.0),
        )


# ---------------------------------------------------------------------------
# 6. THE LIQUID CHANNEL WAS BUILT AND REFUSED -- pinned as the WRONG answer
# ---------------------------------------------------------------------------
def test_the_liquid_channel_buys_nothing_and_costs_conservation(thermo_module):
    """``phase="any"`` converts identically and cannot settle its own residual.

    ⚠ Pinned so that widening the phase shows up as a failure. The refusal was
    decided by arithmetic, not by taste: the conversion is the same to six
    figures and the liquid pseudo-first-order constant is 1.4e6 1/s against a
    600 s run, so the trioxide is gone inside the first microsecond and the
    non-negative projection has nothing left to settle against.
    """
    from chemsim.properties import VolatilityProvider

    vol = VolatilityProvider(thermo_module)
    out = {}
    for phase in ("gas", "any"):
        t = ReactionTemplate(name="sulfur_trioxide_hydration",
                             smarts=sulfur_trioxide_hydration().smarts,
                             A=1.0e10, Ea=23_600.0, phase=phase, reversible=True)
        n = build_network([SO3, WATER, H2SO4], [t], thermo=thermo_module,
                          volatility=vol)
        v = Vessel(n, volume=1.0, T=320.0, T_env=320.0, UA=1.0e4, k_vent=0.0)
        v.charge({WATER: 1.0}, phase="liquid")
        v.charge({SO3: 0.05}, phase="gas")
        v.run(600.0, **TIGHT)
        out[phase] = (_total(v, H2SO4), _total(v, SO3) + _total(v, H2SO4) - 0.05,
                      v.conservation_report())

    # it buys nothing
    assert out["gas"][0] == pytest.approx(out["any"][0], rel=1.0e-4)
    # and it costs this, which the engine SAYS rather than swallows
    assert abs(out["gas"][1]) < 1.0e-12
    assert out["any"][1] > 1.0e-6
    assert "O=S(=O)=O" in out["any"][2]
    assert out["gas"][2] == ""


def test_the_shipped_template_is_the_gas_one():
    t, = vitriol_receiver()
    assert t.phase == "gas"
    assert t.A == 1.0e10 and t.Ea == 23_600.0


# ---------------------------------------------------------------------------
# 7. THE CORPUS -- the split, and the row whose class was DECIDED
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def steps():
    import catalog as cat

    return cat.load_steps()


def test_the_hydrolysis_bucket_is_gone_and_named(steps):
    """Eight rows, eight mechanisms, and seven of the names already existed.

    The argument is not that they are eight mechanisms -- it is that the taxonomy
    already carried amide-, ester-, epoxide-, glycoside-, nitrile-, isocyanate-
    and disproportionation-hydrolysis. ``hydrolysis`` was the bin for whatever it
    had not got round to naming, which is M1's finding sitting next to seven
    counter-examples.
    """
    classes = {s.cls for s in steps}
    assert "hydrolysis" not in classes
    for c in ("oleum-hydrolysis", "sulfur-trioxide-hydration",
              "sulfide-carbonation", "cyanamide-hydrolysis",
              "amalgam-decomposition", "carbide-hydrolysis",
              "pentosan-hydrolysis", "organometallic-protonolysis"):
        assert c in classes, c


def test_only_one_of_the_eight_is_covered(steps):
    """The split moves the DENOMINATOR by seven and the numerator by one.

    S7's shape: a split that lowers the headline is a split working. Crediting
    all eight off one template is the false credit S1, S9 and G4 each measured.
    """
    import catalog_coverage as cc

    covered = [c for c in ("oleum-hydrolysis", "sulfur-trioxide-hydration",
                           "sulfide-carbonation", "cyanamide-hydrolysis",
                           "amalgam-decomposition", "carbide-hydrolysis",
                           "pentosan-hydrolysis", "organometallic-protonolysis")
               if c in cc.TEMPLATE_CLASSES]
    assert covered == ["sulfur-trioxide-hydration"]


def test_the_vitriol_row_names_what_the_engine_actually_makes(steps):
    """The corrected row, and it balances: 2 FeSO4 -> Fe2O3 + SO2 + SO3."""
    row, = [s for s in steps if s.route == "vitriol-distillation" and s.index == 1]
    assert set(row.reactants) == {"iron-ii-sulfate"}
    assert set(row.products) == {"iron-iii-oxide", "sulfur-dioxide",
                                 "sulfur-trioxide"}
    assert row.cls == "sulfate-thermal-decomposition"


def test_the_pentosan_row_keeps_an_uncovered_class_and_it_is_free_today(steps):
    """The decision that was measured both ways rather than argued.

    ``furfural-route`` step 1 is chemically a glycoside hydrolysis and the
    taxonomy's convention would file it under the COVERED
    ``glycoside-hydrolysis``. It is not there, because the row as spelled is
    fragility 29b -- ``xylose + water -> xylose``, products a SUBSET of reactants
    -- so no template can ever match it and a covered class would manufacture a
    false credit.

    ⚠⚠ AND THE MEASUREMENT SAYS IT COSTS NOTHING EITHER WAY TODAY, which is the
    G3 grid lesson and the reason this test asserts the OTHER cell too: the route
    needs three more classes, so the wrong answer is currently invisible. It
    stops being invisible the moment they land, and a false credit is cheapest to
    refuse before it can pay.
    """
    import catalog as cat
    import catalog_coverage as cc

    row, = [s for s in steps if s.route == "furfural-route" and s.index == 1]
    assert row.cls == "pentosan-hydrolysis"
    assert list(row.products) == ["xylose"]
    assert set(row.products) <= set(row.reactants)   # 29b: it can never match

    gaps = {s.cls for s in steps if s.route == "furfural-route"} - set(
        cc.TEMPLATE_CLASSES)
    assert len(gaps) == 4

    routes = cat.load_routes()
    compounds = cat.load_compounds()

    def runnable(tc):
        return sum(1 for rid in routes
                   if cat.route_reachable(steps, rid, routes[rid].target,
                                          lambda x: x in compounds and
                                          x not in _REFUSED, tc, compounds))

    counterfactual = dict(cc.TEMPLATE_CLASSES)
    counterfactual["pentosan-hydrolysis"] = "glycoside_hydrolysis (WRONG)"
    assert runnable(cc.TEMPLATE_CLASSES) == runnable(counterfactual)


# The species the engine refuses a price for, among the ones ``furfural-route``
# and its neighbours touch. Hard-coded rather than audited because the tier audit
# is 18 s and this test is about a CLASS assignment, not about pricing -- the
# real scorer is ``tools/build_playable.priced``.
_REFUSED: frozenset[str] = frozenset()
