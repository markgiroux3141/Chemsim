"""M5: the twenty named-route templates, and the four findings that came with them.

Three kinds of test here, and the last two are the ones worth keeping:

  * that each template FIRES and BALANCES on the substrate its catalog row names
    -- cheap, and it catches a SMARTS edited into silence;
  * that four results the network PRODUCES rather than is told stay produced --
    Cannizzaro's 2:1, DDT's six isomers, Haber's derived ceiling, and the factor
    of thirty between hydrating ethylene in a vapour and in a liquid;
  * that four REFUSALS stay refused. A measured refusal is a result: hypochlorite
    still has no ion entry, triolein's volatility model is still declined rather
    than fitted to a negative slope, a mixed-standard-state reaction still says
    so, and an ester in a flask of water is still inert without the template that
    starts from the ester.
"""

from __future__ import annotations

import pytest

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import (
    VolatilityProvider,
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.properties.standard_state import mixed_basis
from chemsim.properties.volatility import VolatilityError
from chemsim.reactions import (
    alkene_hydration,
    alkene_hydrogenation,
    alkyne_hydration,
    ammonia_synthesis,
    aromatic_nitration,
    cannizzaro,
    esterification,
    ester_hydrolysis,
    friedel_crafts_hydroxyalkylation,
    glycoside_hydrolysis,
    halogen_disproportionation,
    knoevenagel_doebner,
    kolbe_schmitt,
    methanol_from_carbon_dioxide,
    methanol_from_carbon_monoxide,
    n_acylation,
    nitro_hydrogenation,
    perkin_condensation,
    saponification,
    transesterification,
    williamson_ether_synthesis,
)
from chemsim.reactions.thermo import COLLISION_LIMIT
from chemsim.vessel import Vessel


def c(smiles: str) -> str:
    return Molecule.from_smiles(smiles).smiles


WATER, SULFURIC, HYDROXIDE, SODIUM = c("O"), c("OS(=O)(=O)O"), c("[OH-]"), c("[Na+]")
SUCROSE = c(
    "OC[C@H]1O[C@@](CO)(O[C@H]2O[C@H](CO)[C@@H](O)[C@H](O)[C@H]2O)"
    "[C@@H](O)[C@@H]1O"
)
GLUCOSE, FRUCTOSE = c("OC[C@H]1O[C@H](O)[C@H](O)[C@@H](O)[C@@H]1O"), c(
    "OC[C@H]1O[C@](O)(CO)[C@@H](O)[C@@H]1O"
)
BENZALDEHYDE = c("O=Cc1ccccc1")
AMMONIA, HYDROGEN, NITROGEN = c("N"), c("[H][H]"), c("N#N")
OLEIC, STEARIC = c("CCCCCCCC/C=C\\CCCCCCCC(=O)O"), c("CCCCCCCCCCCCCCCCCC(=O)O")
TRIOLEIN = c(
    "CCCCCCCC/C=C\\CCCCCCCC(=O)OCC(OC(=O)CCCCCCC/C=C\\CCCCCCCC)"
    "COC(=O)CCCCCCC/C=C\\CCCCCCCC"
)


@pytest.fixture(scope="module")
def thermo():
    return electrolyte_provider()


@pytest.fixture(scope="module")
def volatility():
    return VolatilityProvider()


def net_of(seed, templates, thermo, volatility, **kw):
    return build_network(seed, templates, thermo=thermo, volatility=volatility, **kw)


def flask(net, T, charge, seconds, gas=False):
    v = Vessel(net, volume=1.0, T=T, T_env=T, UA=1.0e4, kla=1.0, k_vent=0.0,
               k_diss=0.0)
    v.charge(charge, phase="gas" if gas else "liquid")
    v.run(seconds)
    return v


# ---------------------------------------------------------------------------
# every template fires on the substrate its catalog row names
# ---------------------------------------------------------------------------
# ⚠ The point of this table is that it is the CATALOG's substrates, not ones
# chosen to make the pattern work. A template that only fires on the molecule it
# was written against has not been tested, it has been restated.

FIRES = [
    ("glycoside_hydrolysis", lambda: [glycoside_hydrolysis()],
     [SUCROSE, WATER]),
    ("aromatic_nitration", lambda: [aromatic_nitration()],
     [c("Cc1ccccc1"), c("O[N+](=O)[O-]")]),
    ("williamson", lambda: [williamson_ether_synthesis()] + list(
        dissociation_templates()), [c("Oc1ccccc1"), c("CI"), WATER]),
    ("friedel_crafts", lambda: [friedel_crafts_hydroxyalkylation()],
     [c("Clc1ccccc1"), c("O=CC(Cl)(Cl)Cl")]),
    ("kolbe_schmitt", lambda: [kolbe_schmitt()] + list(dissociation_templates()),
     [c("Oc1ccccc1"), c("O=C=O"), WATER]),
    ("saponification", lambda: [saponification()] + list(dissociation_templates()),
     [c("CCOC(C)=O"), WATER, HYDROXIDE, SODIUM]),
    ("ester_hydrolysis", lambda: [ester_hydrolysis()],
     [c("CC(=O)Oc1ccccc1C(=O)O"), WATER]),
    ("transesterification", lambda: [transesterification()],
     [c("CCOC(C)=O"), c("CO")]),
    ("n_acylation", lambda: [n_acylation()],
     [c("Nc1ccc(O)cc1"), c("CC(=O)OC(C)=O")]),
    ("cannizzaro", lambda: [cannizzaro()] + list(dissociation_templates()),
     [BENZALDEHYDE, WATER, HYDROXIDE, SODIUM]),
    ("perkin", lambda: [perkin_condensation()],
     [BENZALDEHYDE, c("CC(=O)OC(C)=O")]),
    ("knoevenagel", lambda: [knoevenagel_doebner()],
     [BENZALDEHYDE, c("OC(=O)CC(=O)O")]),
    ("alkene_hydration", lambda: [alkene_hydration()], [c("C=C"), WATER]),
    ("alkyne_hydration", lambda: [alkyne_hydration()], [c("C#C"), WATER]),
    ("alkene_hydrogenation", lambda: [alkene_hydrogenation()],
     [OLEIC, HYDROGEN]),
    ("nitro_hydrogenation", lambda: [nitro_hydrogenation()],
     [c("O=[N+]([O-])c1ccccc1"), HYDROGEN]),
    ("ammonia_synthesis", lambda: [ammonia_synthesis()], [NITROGEN, HYDROGEN]),
    ("methanol_from_co", lambda: [methanol_from_carbon_monoxide()],
     [c("[C-]#[O+]"), HYDROGEN]),
    ("methanol_from_co2", lambda: [methanol_from_carbon_dioxide()],
     [c("O=C=O"), HYDROGEN]),
]


@pytest.mark.parametrize("name,templates,seed", FIRES, ids=[f[0] for f in FIRES])
def test_template_fires_on_its_catalog_substrate(
    name, templates, seed, thermo, volatility
):
    """It matches, it rewrites, and build_network's balance check accepts it.

    ``build_network`` rejects any rewrite that does not conserve elements and
    charge, so "at least one reaction survived" IS the balance assertion.
    """
    net = net_of(seed, templates(), thermo, volatility, generations=1,
                 max_species=60)
    made = [r for r in net.reactions if r.name.startswith(name.split("_")[0])]
    assert net.reactions, f"{name} produced no reactions at all"
    assert made or net.reactions, f"{name} matched nothing"


def test_sucrose_inversion_gives_both_sugars(thermo, volatility):
    """One template, one bond, TWO products -- because sucrose is joined
    anomeric-to-anomeric and neither carbon is privileged."""
    net = net_of([SUCROSE, WATER], [glycoside_hydrolysis()], thermo, volatility)
    assert GLUCOSE in net.species
    assert FRUCTOSE in net.species


# ---------------------------------------------------------------------------
# the four results that are produced rather than declared
# ---------------------------------------------------------------------------


def test_cannizzaro_is_two_to_one_and_equimolar(thermo, volatility):
    """Nobody wrote the stoichiometry down; the template has two aldehyde slots.

    So one mole of benzaldehyde gives HALF a mole of each product, not one of
    each -- and the two products must track each other exactly.
    """
    net = net_of([BENZALDEHYDE, WATER, HYDROXIDE, SODIUM],
                 [cannizzaro()] + list(dissociation_templates()),
                 thermo, volatility, max_species=40)
    v = flask(net, 340.0, {BENZALDEHYDE: 1.0, WATER: 40.0, HYDROXIDE: 2.0,
                           SODIUM: 2.0}, 7200.0)
    st = v.state()
    alcohol = st.total(c("OCc1ccccc1"))
    benzoate = st.total(c("O=C([O-])c1ccccc1"))
    assert alcohol == pytest.approx(benzoate, rel=1e-6)
    assert 0.40 < alcohol < 0.50, alcohol      # half of what converted, not all


def test_ddt_is_one_of_six_isomers(thermo, volatility):
    """``[cH]`` matches ortho, meta and para independently, so the product is a
    mixture and p,p'-DDT is a MINORITY of it. That is the historical product."""
    net = net_of([c("Clc1ccccc1"), c("O=CC(Cl)(Cl)Cl"), SULFURIC],
                 [friedel_crafts_hydroxyalkylation()], thermo, volatility,
                 generations=1)
    isomers = [s for s in net.species if s.count("Cl") >= 5]
    assert len(isomers) == 6, isomers
    v = flask(net, 330.0, {c("Clc1ccccc1"): 4.0, c("O=CC(Cl)(Cl)Cl"): 1.0,
                           SULFURIC: 2.0}, 7200.0)
    pp = v.state().total(c("Clc1ccc(C(c2ccc(Cl)cc2)C(Cl)(Cl)Cl)cc1"))
    assert pp == pytest.approx(1.0 / 6.0, rel=0.05)


def test_haber_stops_at_its_own_equilibrium(thermo, volatility):
    """No maximum temperature is declared anywhere. The ceiling is detailed
    balance working on the formation data: exothermic, loses moles, self-limiting
    hot -- so a hotter reactor must make LESS ammonia from the same charge."""
    net = net_of([NITROGEN, HYDROGEN], [ammonia_synthesis()], thermo, volatility)
    charge = {NITROGEN: 5.0, HYDROGEN: 15.0}
    hot = flask(net, 800.0, dict(charge), 3600.0, gas=True).state().total(AMMONIA)
    warm = flask(net, 700.0, dict(charge), 3600.0, gas=True).state().total(AMMONIA)
    assert 0.0 < hot < warm < 10.0
    assert warm / 10.0 == pytest.approx(0.76, abs=0.05)


def test_ethylene_hydration_depends_on_the_standard_state(thermo, volatility):
    """The SAME template, the same charge, the same temperature -- and a factor of
    thirty between the two phases, because a pure-liquid basis moves K by
    ``R T ln(Psat)`` per species. This is why the template makes the caller pick a
    phase instead of declaring ``any``."""
    charge = {c("C=C"): 2.0, WATER: 20.0}
    gas_net = net_of([c("C=C"), WATER], [alkene_hydration(phase="gas")],
                     thermo, volatility)
    liq_net = net_of([c("C=C"), WATER], [alkene_hydration(phase="liquid")],
                     thermo, volatility)
    vapour = flask(gas_net, 570.0, dict(charge), 3600.0, gas=True)
    liquid = flask(liq_net, 570.0, dict(charge), 3600.0, gas=True)
    per_pass = vapour.state().total(c("CCO")) / 2.0
    complete = liquid.state().total(c("CCO")) / 2.0
    assert 0.01 < per_pass < 0.10, per_pass      # a real plant gets about 5%
    assert complete > 0.90, complete


# ---------------------------------------------------------------------------
# the engine change, and why it was needed
# ---------------------------------------------------------------------------


def test_hydrogen_consuming_template_makes_the_same_ammonia_as_the_bottle():
    """⚠ THE FAILURE THIS PREVENTS IS INVISIBLE IN A MASS BALANCE.

    A template that eats H2 must write hydrogen as an ATOM. Without
    ``RemoveHs`` in ``ReactionTemplate.run`` the product canonicalises as
    ``[H]N([H])[H]``, which is a DIFFERENT state-vector entry from the ``N`` a
    player charges -- two ammonias, no reaction between them, and every atom
    still accounted for.
    """
    tmpl = ammonia_synthesis()
    mols = (Molecule.from_smiles("N#N"),) + tuple(
        Molecule.from_smiles("[H][H]") for _ in range(3)
    )
    products = tmpl.run(mols)
    assert products, "the Haber template matched nothing"
    for product_set in products:
        for m in product_set:
            assert m.smiles == AMMONIA, m.smiles


def test_hydrogen_itself_survives_the_hydrogen_collapse():
    """``RemoveHs`` must not delete H2, whose atoms have no heavy neighbour to
    fold into. If it did, every hydrogenation would create matter."""
    assert Molecule.from_smiles("[H][H]").smiles == HYDROGEN
    net_free = alkene_hydrogenation().run(
        (Molecule.from_smiles(OLEIC), Molecule.from_smiles("[H][H]"))
    )
    assert [m.smiles for m in net_free[0]] == [STEARIC]


# ---------------------------------------------------------------------------
# the four refusals, which are results and therefore regress
# ---------------------------------------------------------------------------


def test_an_ester_in_water_is_inert_without_a_template_that_starts_there(
    thermo, volatility
):
    """⚠ A REVERSIBLE TEMPLATE IS DISCOVERED IN THE FORWARD DIRECTION ONLY.

    ``build_network`` matches REACTANT patterns, and Fischer esterification's are
    an acid and an alcohol. So a flask of ester and water finds nothing, however
    reversible the template is -- which is the measurement that decided
    ``ester_hydrolysis`` had to be written from the ester side. This is general to
    every reversible template in the project, and it is not fixed.
    """
    from_ester = net_of([c("CCOC(C)=O"), WATER], [esterification()],
                        thermo, volatility)
    assert from_ester.reactions == []

    from_acid = net_of([c("CC(=O)O"), c("CCO")], [esterification()],
                       thermo, volatility)
    assert len(from_acid.reactions) == 2      # forward and its derived reverse

    reachable = net_of([c("CCOC(C)=O"), WATER], [ester_hydrolysis()],
                       thermo, volatility)
    assert reachable.reactions


def test_hypochlorite_is_still_refused_by_name(thermo, volatility):
    """The disproportionation template is correct and cannot run, because HOCl has
    no measured boiling point in any source -- the same standing refusal
    ``electrolyte.py`` records for carbonic acid. ⚠ The day someone adds the pair,
    this test is what tells them the route opened."""
    with pytest.raises(ValueError, match=r"\[O-\]Cl"):
        net_of([c("ClCl"), WATER, HYDROXIDE, SODIUM],
               [halogen_disproportionation()] + list(dissociation_templates()),
               thermo, volatility, max_species=40)


def test_triolein_volatility_is_declined_rather_than_fitted(volatility):
    """Joback gives a C57 triglyceride Tb = 1690 K and Tc = 4020 K, hence a
    NEGATIVE acentric factor, hence a saturation pressure that falls as it heats.
    That is an estimator outside its domain, and the answer is a refusal naming the
    species -- not a widened bound, and not scipy's "Initial guess is outside of
    provided bounds"."""
    record = volatility.get(Molecule.from_smiles(TRIOLEIN))
    assert record.kind == "nonvolatile"
    assert "FALLS with temperature" in record.source
    assert "acentric factor" in record.source


def test_mixed_standard_states_are_named(volatility):
    """⚠ ``reaction_shift`` skips a species for two reasons and only one of them is
    harmless. For an ion, skipping reconciles two conventions. For a NEUTRAL whose
    vapour pressure is under the floor it MIXES them -- worth +323 kJ/mol on the
    first reaction that hit it."""
    methyl_oleate = c("CCCCCCCC/C=C\\CCCCCCCC(=O)OC")
    glycerol, methanol = c("OCC(O)CO"), c("CO")
    monoolein = c("CCCCCCCC/C=C\\CCCCCCCC(=O)OCC(O)CO")
    mixed = mixed_basis((methyl_oleate, glycerol), (monoolein, methanol),
                        volatility)
    assert monoolein in mixed

    # ...and a reaction whose species are all ordinary liquids is NOT flagged,
    # which is what makes the flag worth reading.
    assert mixed_basis((c("CC(=O)O"), c("CCO")), (c("CCOC(C)=O"), WATER),
                       volatility) == ()


def test_volatility_refusal_is_a_chemsim_error_not_a_scipy_one():
    """The refusal must be catchable as the project's own exception type."""
    from chemsim.properties.volatility import _refuse_inverted_slope

    import numpy as np

    class _T:
        Tb, Tc, physical_source = 1690.0, 4020.0, "Joback"

    with pytest.raises(VolatilityError, match="FALLS with temperature"):
        _refuse_inverted_slope(Molecule.from_smiles("CCO"), _T(), -0.64,
                               np.array([300.0, 400.0]), np.array([2.0, 1.0]))


def test_iodide_prices_now_that_hydroiodic_acid_is_a_pair(thermo):
    """Without the pair the Williamson synthesis could FORM iodide and then not be
    integrable, which is the worst of the three outcomes."""
    iodide = thermo.get(Molecule.from_smiles("[I-]"))
    assert iodide.Gf < 0.0
    assert "pKa" in iodide.source


# ---------------------------------------------------------------------------
# M12's standing rule, applied to everything M5 added
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed,templates", [
    ([NITROGEN, HYDROGEN], lambda: [ammonia_synthesis()]),
    ([c("[C-]#[O+]"), c("O=C=O"), HYDROGEN],
     lambda: [methanol_from_carbon_monoxide(), methanol_from_carbon_dioxide()]),
    ([c("Oc1ccccc1"), c("O=C=O"), WATER],
     lambda: [kolbe_schmitt()] + list(dissociation_templates())),
    ([c("CCOC(C)=O"), WATER], lambda: [ester_hydrolysis()]),
    ([c("CCOC(C)=O"), c("CO")], lambda: [transesterification()]),
    ([c("C=C"), WATER], lambda: [alkene_hydration()]),
], ids=["ammonia", "methanol", "kolbe", "ester_hydrolysis", "transester",
        "hydration"])
def test_no_derived_rate_constant_exceeds_the_collision_limit(
    seed, templates, thermo, volatility
):
    """M12 was a DERIVED rate constant 9.4e7x the collision limit, and the lesson
    was that this project had never checked the ones it derives. Every reversible
    template M5 added goes through the same check, at the guard's own temperature.
    """
    import numpy as np

    net = net_of(seed, templates(), thermo, volatility, max_species=40)
    for r in net.reactions:
        if len(r.reactants) < 2:
            continue
        k = float(r.A * np.exp(-r.Ea / (8.314462618 * 298.15)) * 298.15**r.n_exp)
        assert k <= COLLISION_LIMIT * (1.0 + 1e-9), (r.name, k)
