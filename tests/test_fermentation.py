"""C4 -- the ABE fermentation, and the class M5 refused as a metabolic network.

⚠⚠⚠ **THE REFUSAL WAS ABOUT THE LABEL, NOT THE CHEMISTRY.** Five catalog rows
carried ``fermentation`` and they are five mechanisms, so ``route_steps.psv``
names five classes now (M1's rule: *a class must name a MECHANISM, not an
outcome*). Two are built and three are named gaps.

⚠⚠ **AND THE LUMP THAT MADE THE REFUSAL LOOK RIGHT WAS THE ROW'S FORMATTING.**
``abe-fermentation`` balances only at ``5 glucose -> 2 acetone + 2 butanol +
2 ethanol + 12 CO2 + 8 H2``, which is not a graph rewrite. It is three reactions
on one line, and each of the three balances exactly on ONE glucose.

The standing audit is ``validation/fermentation.py``. Panel 5's refutation of
M10's cheap version and panel 8's stereo-keying finding are pinned here too.
"""

from __future__ import annotations

import csv
import os
import sys

import pytest
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem

RDLogger.DisableLog("rdApp.*")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, os.path.join(_ROOT, "validation"))
sys.path.insert(0, os.path.join(_ROOT, "tools"))

from chemsim.matter import Molecule  # noqa: E402
from chemsim.network import build_network  # noqa: E402
from chemsim.properties import (  # noqa: E402
    ThermochemistryProvider,
    VolatilityProvider,
)
from chemsim.reactions.synthesis import (  # noqa: E402
    acetonic_fermentation,
    butanolic_fermentation,
    ethanolic_fermentation,
    fermentation_chemistry,
    homolactic_fermentation,
)
from chemsim.reactions.template import ReactionTemplate  # noqa: E402
from chemsim.reactions.thermo import reaction_deltas  # noqa: E402
from chemsim.vessel import Vessel  # noqa: E402


def _c(smi: str) -> str:
    return Molecule.from_smiles(smi).smiles


WATER = _c("O")
GLUCOSE = _c("OC[C@H]1O[C@@H](O)[C@H](O)[C@@H](O)[C@@H]1O")
FRUCTOSE = _c("OC[C@H]1O[C@](O)(CO)[C@@H](O)[C@@H]1O")
MANNOSE = _c("OC[C@H]1O[C@@H](O)[C@@H](O)[C@@H](O)[C@@H]1O")
SUCROSE = _c("OC[C@H]1O[C@@](CO)(O[C@H]2O[C@H](CO)[C@@H](O)[C@H](O)[C@H]2O)"
             "[C@@H](O)[C@@H]1O")
ETHANOL, BUTANOL, ACETONE = _c("CCO"), _c("CCCCO"), _c("CC(C)=O")
CO2, H2 = _c("O=C=O"), _c("[H][H]")
LACTIC_FLAT, LACTIC_L = _c("CC(O)C(=O)O"), _c("C[C@H](O)C(=O)O")

TIGHT = {"rtol": 1.0e-8, "atol": 1.0e-12}
VESSEL, GLU_CHARGE, WATER_CHARGE, T_FERM = 2.0, 0.5, 10.0, 310.0


@pytest.fixture(scope="module")
def thermo():
    return ThermochemistryProvider()


@pytest.fixture(scope="module")
def vol(thermo):
    return VolatilityProvider(thermo)


def _net(thermo, vol, templates, species=(WATER, GLUCOSE)):
    return build_network(list(species), list(templates), thermo=thermo,
                         volatility=vol)


@pytest.fixture(scope="module")
def net(thermo, vol):
    return _net(thermo, vol, fermentation_chemistry())


def _flask(network, *, t, T=T_FERM, glu=GLU_CHARGE, water=WATER_CHARGE,
           k_vent=0.0):
    v = Vessel(network, volume=VESSEL, T=T, T_env=T, UA=1.0e6, k_vent=k_vent)
    v.charge({WATER: water, GLUCOSE: glu}, phase="liquid")
    if t > 0.0:
        v.run(t, **TIGHT)
    return v


def _counts(pairs):
    out: dict[str, int] = {}
    for smi, n in pairs:
        for el, c in Molecule.from_smiles(smi).element_counts().items():
            out[el] = out.get(el, 0) + c * n
    return out


# ---------------------------------------------------------------------------
# 1. THE LUMP DOES NOT BALANCE AND EACH BRANCH DOES
# ---------------------------------------------------------------------------
def test_the_catalog_row_does_not_balance_as_written():
    """⚠ The verdict NEXT_PROMPT recorded, pinned: five sugars in and six carbon
    skeletons out, which is not a graph rewrite."""
    lhs = _counts([(GLUCOSE, 1)])
    rhs = _counts([(ACETONE, 1), (BUTANOL, 1), (ETHANOL, 1), (CO2, 1),
                   (H2, 1)])
    assert lhs != rhs
    # and it DOES balance at the fivefold multiple, which is why
    # `corpus_balance` passes it -- the weak test S11 was misled by
    assert _counts([(GLUCOSE, 5)]) == _counts(
        [(ACETONE, 2), (BUTANOL, 2), (ETHANOL, 2), (CO2, 12), (H2, 8)])


@pytest.mark.parametrize("lhs,rhs", [
    ([(GLUCOSE, 1)], [(ETHANOL, 2), (CO2, 2)]),
    ([(GLUCOSE, 1)], [(BUTANOL, 1), (CO2, 2), (WATER, 1)]),
    ([(GLUCOSE, 1), (WATER, 1)], [(ACETONE, 1), (CO2, 3), (H2, 4)]),
    ([(GLUCOSE, 1)], [(LACTIC_FLAT, 2)]),
])
def test_every_branch_balances_exactly_on_ONE_glucose(lhs, rhs):
    """⚠⚠⚠ **THE WHOLE ARGUMENT OF THE SESSION.** The lump was three reactions
    written on one line; split, nothing consumes five sugars."""
    assert _counts(lhs) == _counts(rhs)


# ---------------------------------------------------------------------------
# 2. THE PATTERNS, AND THE TWO REFUSALS THAT ARE THE POINT
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("substrate,fires", [
    (GLUCOSE, True),
    (MANNOSE, True),        # same constitution; the pattern queries no stereo
    (FRUCTOSE, False),      # the corpus spells it a FURANOSE -- S7's finding
    (SUCROSE, False),       # a GLYCOSIDE: the anomeric carbon has no -OH
    (ETHANOL, False),
    (_c("OCC(O)CO"), False),                                    # glycerol
    (_c("OC[C@H]1O[C@H](O)[C@H](O)[C@@H]1O"), False),           # ribose
    (_c("OC1CCCCC1"), False),                                   # cyclohexanol
])
def test_the_hexopyranose_pattern_is_narrow(substrate, fires):
    for t in (ethanolic_fermentation(), butanolic_fermentation(),
              acetonic_fermentation(), homolactic_fermentation()):
        rxn = AllChem.ReactionFromSmarts(t.smarts)
        rxn.Initialize()
        args = (Chem.MolFromSmiles(substrate),)
        if rxn.GetNumReactantTemplates() == 2:
            args = args + (Chem.MolFromSmiles(WATER),)
        assert bool(rxn.RunReactants(args)) is fires, t.name


def test_a_brewer_must_invert_the_sugar_first():
    """⚠ Sucrose is inert to every branch, and that is the corpus's own
    ``ethanol-fermentation`` step 1 (`glycoside-hydrolysis`) being load-bearing
    rather than decorative."""
    rxn = AllChem.ReactionFromSmarts(ethanolic_fermentation().smarts)
    rxn.Initialize()
    assert not rxn.RunReactants((Chem.MolFromSmiles(SUCROSE),))
    assert rxn.RunReactants((Chem.MolFromSmiles(GLUCOSE),))


def test_the_products_are_the_corpus_compounds_and_nothing_else(net):
    """⚠ Five species and no strays -- no partially-rewritten sugar, no second
    lactic enantiomer, no oligomer. The ABE bundle cannot feed itself."""
    assert set(net.species) == {WATER, GLUCOSE, ETHANOL, BUTANOL, ACETONE,
                               CO2, H2}
    assert len(net.reactions) == 3


# ---------------------------------------------------------------------------
# 3. THE STANDARD-STATE MIX, AND WHY IT COSTS NOTHING HERE
# ---------------------------------------------------------------------------
def test_every_branch_mixes_standard_states_and_stays_irreversible(
        net, thermo, vol):
    """⚠⚠ Glucose's vapour pressure at 298 K is below the standard-state floor,
    so it gets no liquid shift while its products all do. The two conventions
    differ by >100 kJ/mol in dH and the SIGN OF dS FLIPS -- and the SIGN of dG
    does not, on either basis, by two orders of magnitude.

    **So: no branch is reversible, and no K may be quoted.** C3's
    `vanillin-lignin` notice arriving on a SUBSTRATE.
    """
    for rxn in net.reactions:
        dHg, dGg = reaction_deltas(rxn, thermo, None)
        dHl, dGl = reaction_deltas(rxn, thermo, vol)
        assert abs(dHl - dHg) > 60.0                  # the conventions differ
        dSg = (dHg - dGg) / 298.15 * 1000.0
        dSl = (dHl - dGl) / 298.15 * 1000.0
        assert dSg > 0.0 and dSl < 0.0                # and the sign FLIPS
        assert dGg < -100.0 and dGl < -100.0          # the sign of dG does not
    assert not any(t.reversible for t in fermentation_chemistry())


# ---------------------------------------------------------------------------
# 4. THE FLASK
# ---------------------------------------------------------------------------
def test_glucose_becomes_acetone_and_the_batch_time_is_a_batch(net):
    """⚠ 77.6% conversion in 48 h at 310 K. FITTED, and stated as fitted."""
    v = _flask(net, t=48.0 * 3600.0)
    st = v.state()
    conv = (GLU_CHARGE - st.total(GLUCOSE)) / GLU_CHARGE
    assert 0.70 < conv < 0.85
    assert st.total(ACETONE) > 0.1                # the route's actual target
    assert st.total(BUTANOL) > st.total(ACETONE) > st.total(ETHANOL)


def test_the_solvent_slate_is_the_reported_one(net):
    """⚠⚠ **FITTED, NOT PREDICTED.** The classical ABE yield is 3:6:1 by MASS,
    which is 2.38:3.73:1 by mole, and three pre-exponentials were set to it.
    Selectivity between two CHEMICAL templates is derivable in this project
    (S11); selectivity between two METABOLIC branches is not -- Evans-Polanyi
    over three branches 220 kJ/mol apart in dH would predict pure butanol.
    """
    st = _flask(net, t=48.0 * 3600.0).state()
    e = st.total(ETHANOL)
    assert st.total(ACETONE) / e == pytest.approx(2.38, abs=0.10)
    assert st.total(BUTANOL) / e == pytest.approx(3.73, abs=0.10)


def test_the_fermentation_GAS_is_the_one_number_nothing_was_fitted_to(net):
    """⚠⚠⚠ H2 comes ONLY from the acetonic branch, so the CO2:H2 ratio is a
    consequence of the solvent slate and the three stoichiometries -- and it
    lands at 62:38 against a reported ~60:40. **The one number here that checks
    the model rather than being fed by it.**"""
    st = _flask(net, t=96.0 * 3600.0).state()
    gas = st.total(CO2) + st.total(H2)
    assert st.total(CO2) / gas == pytest.approx(0.60, abs=0.03)


def test_two_invariants_of_the_run_hold_EXACTLY(net):
    """⚠ Panel 1's balance showing up as a property of the trajectory: H2 is
    4:1 with the acetone, and CO2 is 3 / 2 / 1-per-ethanol across the three
    branches. To solver precision, at every point."""
    for hours in (12.0, 48.0, 96.0):
        st = _flask(net, t=hours * 3600.0).state()
        assert st.total(H2) / st.total(ACETONE) == pytest.approx(4.0, rel=1e-9)
        predicted = (3.0 * st.total(ACETONE) + 2.0 * st.total(BUTANOL)
                     + st.total(ETHANOL))
        assert st.total(CO2) == pytest.approx(predicted, rel=1e-9)


def test_a_sealed_fermenter_reaches_25_bar_on_its_own_gas(net):
    """⚠ Two branches make CO2 and one makes four H2 as well, so the headspace
    IS the product. Nothing was told to do this.

    ⚠ And the conversion barely moves when it is vented: no branch is
    reversible, so the pressure cannot push back on the chemistry. **A hazard,
    not a ceiling** -- unlike the vanillin digester, where the steam pressure is
    what makes the route go at all.
    """
    sealed = _flask(net, t=96.0 * 3600.0)
    vented = _flask(net, t=96.0 * 3600.0, k_vent=1.0e-3)
    assert sealed.pressure > 20.0
    assert vented.pressure < 1.1
    s_conv = GLU_CHARGE - sealed.state().total(GLUCOSE)
    v_conv = GLU_CHARGE - vented.state().total(GLUCOSE)
    assert v_conv == pytest.approx(s_conv, rel=0.01)


# ---------------------------------------------------------------------------
# 5. M10's CHEAP VERSION, REFUTED BY RUNNING IT
# ---------------------------------------------------------------------------
def test_an_order_zero_substrate_MANUFACTURES_matter(thermo, vol):
    """⚠⚠⚠ **MILESTONES §M10's CHEAP VERSION IS MEASURED SHUT.** It scopes the
    Michaelis-Menten plateau as *"a declared order of ZERO in the substrate ...
    needs no kernel change"*. It needs one: there is no availability gate
    outside the solid block, so the rate law cannot know the substrate is gone.

    ⚠⚠ **AND THE FAILURE IS WORSE THAN THE TWO DOCSTRINGS THAT DESCRIBE IT.**
    They say the reactant "is driven negative". What happens is that it is
    CLAMPED at zero in the reported state while the products grow past the
    stoichiometric ceiling -- 1.79 mol of ethanol out of 0.5 mol of glucose --
    with the run reporting SUCCESS. ``conservation_report`` does see every mole,
    and calls four tenths of a mole "round-off it could not settle".
    """
    t0 = ethanolic_fermentation()
    zero = ReactionTemplate(name=t0.name, smarts=t0.smarts, A=t0.A, Ea=t0.Ea,
                            phase=t0.phase, orders=(0.0,))
    net = _net(thermo, vol, [zero])
    v = _flask(net, t=1500.0 * 3600.0)
    st = v.state()

    assert st.total(GLUCOSE) == 0.0                  # clamped, looks exhausted
    ceiling = 2.0 * GLU_CHARGE
    assert st.total(ETHANOL) > 1.7 * ceiling         # and 3.6x impossible
    report = v.conservation_report()
    assert "round-off" in report                     # the label it uses
    assert "e-01 mol" in report                      # about four tenths of one

    # mass action, same everything else, stays inside the ceiling
    ok = _flask(_net(thermo, vol, [ethanolic_fermentation()]),
                t=1500.0 * 3600.0)
    assert ok.state().total(ETHANOL) < ceiling
    assert ok.conservation_report() == ""


def test_no_fermentation_template_declares_an_order():
    """⚠ The consequence of the test above, pinned so it cannot be undone by
    tidiness: plain mass action, one glucose per reaction, first order."""
    for t in fermentation_chemistry() + [homolactic_fermentation()]:
        assert t.orders is None, t.name


# ---------------------------------------------------------------------------
# 6. THE STEREOCENTRE THE HOMOLACTIC BRANCH MAKES
# ---------------------------------------------------------------------------
def test_the_plain_pattern_would_make_BOTH_lactic_enantiomers():
    """⚠⚠ RDKit INHERITS an unspecified chirality and REMOVES one the reactant
    pattern specifies and the product pattern does not. So the plain
    hexopyranose pattern emits one L-lactic acid and one D- out of the same
    sugar -- two species where the corpus has one, and where no estimator here
    can tell them apart. `[@,@@]` is what suppresses both.

    That is C3's isoeugenol decision reached through a stereocentre.
    """
    plain = ("[OX2H:1][CH2:2][CH:3]1[OX2:4][CH:5]([OX2H:6])[CH:7]([OX2H:8])"
             "[CH:9]([OX2H:10])[CH:11]1[OX2H:12]"
             ">>[CH3:5][CH1:7]([OH:8])[CH0:9](=[O:10])[OH:6]"
             ".[CH3:2][CH1:3]([OH:4])[CH0:11](=[O:12])[OH:1]")

    def products(smarts):
        rxn = AllChem.ReactionFromSmarts(smarts)
        rxn.Initialize()
        out = []
        for p in rxn.RunReactants((Chem.MolFromSmiles(GLUCOSE),))[0]:
            Chem.SanitizeMol(p)
            out.append(Chem.MolToSmiles(p))
        return out

    assert len(set(products(plain))) == 2                    # L and D
    assert set(products(homolactic_fermentation().smarts)) == {LACTIC_FLAT}


def test_a_stereo_spelling_SELECTS_A_DATA_TIER(thermo):
    """⚠⚠⚠ **AND MEASURING THAT TURNED UP SOMETHING GENERAL.** The property
    tables are keyed by canonical SMILES, so a stereocentre changes the key --
    and the two HALVES of a ThermoData are keyed the opposite way round:

      * the PHYSICAL tables carry the chiral spelling. 29 corpus compounds
        reach a measured Tb chiral and fall to Joback flat, sorbitol by 184 K.
      * the FORMATION table carries the FLAT spelling. Lactic acid's flat form
        reaches an experimental record; the corpus's chiral one falls to Benson.

    A spelling carries no thermochemical information at all -- no estimator here
    tells one enantiomer from another (S7) -- so for these compounds the tier is
    selected by an orthographic accident. ``validation/fermentation.py`` panel 8
    counts it: **31 of 146 stereo-spelled corpus rows.**

    ⚠ NOT fixed here. The fix is a stereo-insensitive FALLBACK in the lookup
    (S6's rule: a fallback, never an override), which touches the provider every
    number in this project comes out of.
    """
    chiral, flat = thermo.get(LACTIC_L), thermo.get(LACTIC_FLAT)
    assert "Benson" in chiral.source
    assert "experimental" in flat.source
    assert abs(chiral.Tb - flat.Tb) > 100.0

    sorb_c = thermo.get(_c("OC[C@H](O)[C@@H](O)[C@H](O)[C@H](O)CO"))
    sorb_f = thermo.get(_c("OCC(O)C(O)C(O)C(O)CO"))
    assert "Joback" not in sorb_c.physical_source     # chiral wins HERE
    assert "Joback" in sorb_f.physical_source
    assert abs(sorb_c.Tb - sorb_f.Tb) > 100.0


def test_the_size_of_the_stereo_keying_gap_is_pinned():
    """⚠ 146 corpus rows carry a stereo marker. The count is pinned so a data
    session that fixes the keying has to come here and say so."""
    path = os.path.join(_ROOT, "data", "catalog", "compounds")
    n = 0
    for fn in sorted(os.listdir(path)):
        if not fn.endswith(".psv"):
            continue
        with open(os.path.join(path, fn), encoding="utf-8") as fh:
            for row in csv.reader(fh, delimiter="|"):
                if not row or row[0].strip().startswith("#") or len(row) < 3:
                    continue
                if "@" in row[2].strip():
                    n += 1
    assert n == 146


# ---------------------------------------------------------------------------
# 7. THE TAXONOMY SPLIT, AND WHAT IT BOUGHT
# ---------------------------------------------------------------------------
def test_the_class_was_split_into_five_mechanisms():
    """⚠⚠⚠ **THE SPLIT IS WHAT MAKES THE CREDIT HONEST.** A template written off
    `abe-fermentation` cannot make citric acid, glutamic acid or penicillin G
    out of a sugar; crediting the old five-row class off it would have
    template-readied four routes `build_network` cannot run. G4's *only RUNNING
    it said so*, arriving before the run for once because the rows were read
    first.
    """
    import catalog as cat

    steps = cat.load_steps()
    classes = {}
    for s in steps:
        if "fermentation" in s.cls:
            classes.setdefault(s.cls, []).append((s.route, s.index))

    assert "fermentation" not in classes         # the outcome label is GONE
    assert set(classes) == {
        "solventogenic-fermentation",
        "homolactic-fermentation",
        "aerobic-overflow-fermentation",
        "amino-acid-fermentation",
        "secondary-metabolite-fermentation",
    }
    assert classes["solventogenic-fermentation"] == [("abe-fermentation", 1)]
    assert classes["homolactic-fermentation"] == [("lactic-acid-pla", 1)]


def test_the_two_classes_are_credited_and_named():
    """⚠ Credited by NAME against the template functions, so a rename breaks a
    test rather than silently un-crediting a class."""
    import catalog_coverage as cc

    assert (cc.TEMPLATE_CLASSES["solventogenic-fermentation"]
            == "acetonic_fermentation")
    assert (cc.TEMPLATE_CLASSES["homolactic-fermentation"]
            == "homolactic_fermentation")
    assert acetonic_fermentation().name == "acetonic_fermentation"
    assert homolactic_fermentation().name == "homolactic_fermentation"
    # and the three aerobic rows are NOT credited
    for gap in ("aerobic-overflow-fermentation", "amino-acid-fermentation",
                "secondary-metabolite-fermentation"):
        assert gap not in cc.TEMPLATE_CLASSES


def test_the_class_is_worth_the_TWO_PLAYABLE_ROUTES_section_8b_priced():
    """⚠⚠ §8b said `fermentation` was the biggest single class left at **+2**,
    and it is: `abe-fermentation` itself at tier 1, and `acetic-fermentation`
    at tier 2 once ethanol reaches the shelf.

    ⚠ **AND THE SECOND ROUTE IS BOUGHT BY A BRANCH THAT IS NOT THE TARGET.**
    `abe-fermentation`'s catalog target is propanone, but what unblocks
    `acetic-fermentation` is the ETHANOL -- the minority branch, at a seventh of
    the butanol. A route's own target is not what it is worth downstream.
    """
    import build_playable as bp
    import catalog as cat
    import catalog_coverage as cc

    def playable(drop):
        tc = {k: v for k, v in cc.TEMPLATE_CLASSES.items() if k not in drop}
        pool = {rid for rid in bp.routes
                if cat.route_reachable(bp.steps, rid, bp.routes[rid].target,
                                       bp.priced, tc, bp.compounds)}
        return len(bp.closure(pool=pool)[0])

    both = playable(set())
    assert both == 20
    base = playable({"solventogenic-fermentation"})
    assert base == 18                                # C3's number, recovered
    assert both - base == 2
    # homolactic buys no PLAYABILITY at all -- `lactic-acid-pla` needs a
    # polymerisation as well. It was built for the class and the stereo finding.
    assert playable({"homolactic-fermentation"}) == 20


def test_granting_the_top_row_made_the_work_order_LONGER_again():
    """⚠⚠ C1 granted one row and the list grew 21 -> 24; C2 shrank it to 22; C3
    to 20. C4 grants the top row and it grows to **23**, because acetone,
    ethanol, butanol and (via `acetic-fermentation`) acetic acid reach the shelf
    and four more routes become FED: `white-lead-route`, `chloral-route`,
    `acetic-anhydride-ketene`, `mercury-fulminate-route`.

    ⚠⚠⚠ **AND THE CEILING MOVED FOR THE FIRST TIME SINCE C1: 41 -> 45.** Two
    sessions running it sat still because vanillin and superphosphate feed
    nothing. A fermentation feeds four routes, so *a work order derived from a
    fixed point is not a burndown list* -- and the goal it is measured against
    moves with it.
    """
    import build_playable as bp

    assert len(bp.FED_BUT_UNRUNNABLE) == 23
    assert "abe-fermentation" not in bp.FED_BUT_UNRUNNABLE
    assert "acetic-fermentation" not in bp.FED_BUT_UNRUNNABLE
    for grown in ("white-lead-route", "chloral-route",
                  "acetic-anhydride-ketene", "mercury-fulminate-route"):
        assert grown in bp.FED_BUT_UNRUNNABLE
    ceiling, _ = bp.closure(pool=bp.RUNNABLE | set(bp.FED_BUT_UNRUNNABLE))
    assert len(ceiling) == 45


def test_the_work_order_no_longer_has_a_PLUS_TWO_ROW():
    """⚠⚠⚠ C4 took the only +2 in §8b and what is left is a flat table: six
    classes tied at +1 and 23 at +0. **The cheap end of the C-series is over**
    -- from here every row buys one route or none.

    ⚠ And `ethylene` was joint-biggest single SPECIES grant at +2 in §7 before
    this session and is +1 after it, having been nowhere near the work. *A
    content item re-prices a lever it never touched.*
    """
    import build_playable as bp

    worths = {c: g for g, _r, c, _ in bp.CLASS_WORTH}
    assert max(worths.values()) == 1
    assert sum(1 for w in worths.values() if w == 1) == 6
