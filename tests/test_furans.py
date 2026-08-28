"""C5 -- the sugar-to-furan dehydrations, and the two-generation bug they found.

``PLAYABLE.md`` §8b's top row after C4 is ``dehydration-cyclisation``. Its two
catalog rows are ONE mechanism -- an acid-catalysed triple dehydration of a sugar
into a furan -- so unlike C3 and C4 this class is NOT split, and the credit needs
BOTH templates: ``hmf-route`` off the ketohexose and ``furfural-route`` off the
pentose.

⚠⚠⚠ **AND THE SESSION'S ENGINE FINDING IS PINNED HERE RATHER THAN WITH C4's
CHEMISTRY, THOUGH IT IS C4's CHEMISTRY THAT IT BREAKS.** Before C5,
``ReactionTemplate.run`` handed back products carrying RDKit's ``noImplicit``
flag, and no template could run on such a molecule -- so **the engine could not
ferment sugar it had inverted itself.** ``test_a_brewer_can_invert_and_ferment``
is the load-bearing one; ``test_no_template_pair_disagrees...`` is the general
statement.

The standing audit is ``validation/furans.py``.
"""

from __future__ import annotations

import glob
import itertools
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

import numpy as np  # noqa: E402

from chemsim.matter import Molecule  # noqa: E402
from chemsim.network import build_network  # noqa: E402
from chemsim.properties import (  # noqa: E402
    ThermochemistryProvider,
    VolatilityProvider,
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.reactions import kolbe_schmitt  # noqa: E402
from chemsim.reactions.synthesis import (  # noqa: E402
    aldofuranose_dehydration,
    fermentation_chemistry,
    furan_chemistry,
    glycoside_hydrolysis,
    hydroxymethylfurfural_rehydration,
    ketofuranose_dehydration,
)
from chemsim.vessel import Vessel  # noqa: E402


def _c(smi: str) -> str:
    return Molecule.from_smiles(smi).smiles


WATER = _c("O")
FRUCTOSE = _c("OC[C@H]1O[C@](O)(CO)[C@@H](O)[C@@H]1O")
XYLOSE = _c("OC[C@@H]1O[C@@H](O)[C@H](O)[C@@H]1O")
GLUCOSE = _c("OC[C@H]1O[C@@H](O)[C@H](O)[C@@H](O)[C@@H]1O")
ALPHA_GLUCOSE = _c("OC[C@H]1O[C@H](O)[C@H](O)[C@@H](O)[C@@H]1O")
SUCROSE = _c("OC[C@H]1O[C@@](CO)(O[C@H]2O[C@H](CO)[C@@H](O)[C@H](O)[C@H]2O)"
             "[C@@H](O)[C@@H]1O")
HMF = _c("OCc1ccc(C=O)o1")
FURFURAL = _c("O=Cc1ccco1")
LEVULINIC = _c("CC(=O)CCC(=O)O")
FORMIC = _c("O=CO")
ETHANOL = _c("CCO")

TIGHT = {"rtol": 1.0e-8, "atol": 1.0e-12}
VESSEL, SUGAR_CHARGE, WATER_CHARGE, T_REF = 2.0, 0.5, 10.0, 420.0


@pytest.fixture(scope="module")
def thermo():
    return ThermochemistryProvider()


@pytest.fixture(scope="module")
def vol(thermo):
    return VolatilityProvider(thermo)


def net(species, templates, thermo, vol, **kw):
    return build_network(list(species), list(templates), thermo=thermo,
                         volatility=vol, **kw)


def flask(network, charge, *, t, T=T_REF):
    v = Vessel(network, volume=VESSEL, T=T, T_env=T, UA=1.0e6, k_vent=0.0)
    v.charge(dict(charge), phase="liquid")
    if t > 0.0:
        v.run(float(t), **TIGHT)
    return v.state()


# ---------------------------------------------------------------------------
# the class, and why it is NOT split
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sugar,furan,waters", [
    (FRUCTOSE, HMF, 3),
    (XYLOSE, FURFURAL, 3),
])
def test_both_rows_balance_one_to_one_on_their_own_sugar(sugar, furan, waters):
    """C4's arithmetic, and it comes out the OPPOSITE way.

    ``abe-fermentation`` balanced only at 5:2:2:2:12:8 and that was three
    reactions on one line. These two balance 1:1 with three waters each, on one
    sugar each -- so there is nothing to split, and the class stands.
    """
    from collections import Counter

    def atoms(smiles):
        m = Chem.AddHs(Chem.MolFromSmiles(smiles))
        return Counter(a.GetSymbol() for a in m.GetAtoms())

    lhs = atoms(sugar)
    rhs = atoms(furan)
    for _i in range(waters):
        rhs += atoms("O")
    assert lhs == rhs, (sugar, dict(lhs), dict(rhs))


def test_the_class_needs_both_templates_because_neither_reaches_the_other_row():
    """Credit ``dehydration-cyclisation`` off ONE row and the other is a false
    credit -- C4's landmine, arriving from the split's other side."""
    keto, aldo = ketofuranose_dehydration(), aldofuranose_dehydration()
    fru, xyl = Molecule.from_smiles(FRUCTOSE), Molecule.from_smiles(XYLOSE)
    assert fru._mol.HasSubstructMatch(keto.reactant_pattern(0))
    assert not xyl._mol.HasSubstructMatch(keto.reactant_pattern(0))
    assert xyl._mol.HasSubstructMatch(aldo.reactant_pattern(0))
    assert not fru._mol.HasSubstructMatch(aldo.reactant_pattern(0))


def test_the_class_is_mapped_and_so_is_the_side_reaction():
    import catalog_coverage as cc

    assert "dehydration-cyclisation" in cc.TEMPLATE_CLASSES
    assert "hydration-ring-opening" in cc.TEMPLATE_CLASSES
    # both templates named, because both rows need one
    named = cc.TEMPLATE_CLASSES["dehydration-cyclisation"]
    assert "ketofuranose_dehydration" in named
    assert "aldofuranose_dehydration" in named


# ---------------------------------------------------------------------------
# the SMARTS, over the whole corpus
# ---------------------------------------------------------------------------


def _corpus():
    rows = []
    for f in sorted(glob.glob(os.path.join(
            _ROOT, "data", "catalog", "compounds", "*.psv"))):
        for line in open(f, encoding="utf-8"):
            p = [x.strip() for x in line.strip().split("|")]
            if len(p) < 3 or not p[0] or p[0].startswith("#") or p[0] == "id":
                continue
            m = Chem.MolFromSmiles(p[2])
            if m is not None:
                rows.append((p[0], Molecule(m)))
    return rows


@pytest.mark.parametrize("factory,expected,product", [
    (ketofuranose_dehydration, {"fructose", "sorbose"}, HMF),
    (aldofuranose_dehydration, {"ribose", "xylose", "arabinose"}, FURFURAL),
])
def test_the_templates_hit_exactly_the_right_corpus_sugars(
    factory, expected, product
):
    """Stereo-blind by construction, and every extra hit it buys is right:
    EVERY pentose gives furfural in hot acid, and sorbose is a ketohexose that
    dehydrates like fructose. Nothing was aimed at either."""
    tmpl = factory()
    hits = {cid for cid, mol in _corpus()
            if mol._mol.HasSubstructMatch(tmpl.reactant_pattern(0))}
    assert hits == expected
    for cid, mol in _corpus():
        if cid not in expected:
            continue
        got = {p.smiles for ps in tmpl.run((mol,)) for p in ps}
        assert product in got, (cid, got)


def test_sucrose_is_inert_until_it_is_inverted():
    """A glycoside has no free anomeric -OH. C4's narrowing, doing the same work
    on a different ring size."""
    suc = Molecule.from_smiles(SUCROSE)
    for t in (ketofuranose_dehydration(), aldofuranose_dehydration()):
        assert not suc._mol.HasSubstructMatch(t.reactant_pattern(0))


def test_furfural_survives_what_opens_hmf():
    """The rehydration needs the HYDROXYMETHYL, and furfural has none. That is
    why `furfural-route` has no yield-limiting row and `hmf-route` does."""
    tmpl = hydroxymethylfurfural_rehydration()
    assert Molecule.from_smiles(HMF)._mol.HasSubstructMatch(
        tmpl.reactant_pattern(0))
    assert not Molecule.from_smiles(FURFURAL)._mol.HasSubstructMatch(
        tmpl.reactant_pattern(0))


def _ring_provenance(tmpl, substrate):
    rxn = AllChem.ReactionFromSmarts(tmpl.smarts)
    sub = Chem.MolFromSmiles(substrate)
    sugar_ring = set(sub.GetRingInfo().AtomRings()[0])
    for products in rxn.RunReactants((sub,)):
        for p in products:
            try:
                Chem.SanitizeMol(p)
            except Exception:
                continue
            rings = p.GetRingInfo().AtomRings()
            if not rings:
                continue
            kept = sum(
                1 for idx in rings[0]
                if p.GetAtomWithIdx(idx).HasProp("react_atom_idx")
                and p.GetAtomWithIdx(idx).GetIntProp("react_atom_idx")
                in sugar_ring
            )
            return kept, len(rings[0])
    raise AssertionError("no ring-bearing product")


def test_the_ketose_keeps_its_ring_and_the_aldose_rebuilds_one():
    """⚠⚠ THE FINDING C4's LOST SUBSTRATE TURNED INTO. The corpus spells both
    sugars as FURANOSES, and only the ketose's ring is the product's."""
    assert _ring_provenance(ketofuranose_dehydration(), FRUCTOSE) == (5, 5)
    assert _ring_provenance(aldofuranose_dehydration(), XYLOSE) == (3, 5)


# ---------------------------------------------------------------------------
# ⚠⚠⚠ the engine finding
# ---------------------------------------------------------------------------


def _old_style_products(tmpl, reactants):
    """The product molecules this engine handed back BEFORE C5's fix: sanitize,
    RemoveHs, and stop -- no round trip through canonical SMILES."""
    out = []
    for product_set in tmpl._rxn.RunReactants(tuple(m._mol for m in reactants)):
        row = []
        for p in product_set:
            try:
                Chem.SanitizeMol(p)
                row.append(Molecule(Chem.RemoveHs(p)))
            except Exception:
                row = []
                break
        if row:
            out.append(tuple(row))
    return out


def _inverted_glucose(old_style: bool):
    suc, water = Molecule.from_smiles(SUCROSE), Molecule.from_smiles(WATER)
    gh = glycoside_hydrolysis()
    sets = (_old_style_products(gh, (suc, water)) if old_style
            else gh.run((suc, water)))
    for ps in sets:
        for p in ps:
            if p.smiles != WATER and "(CO)" not in p.smiles:
                return p
    raise AssertionError("sucrose inversion made no glucose")


def test_the_old_product_and_the_parsed_one_are_equal_and_used_to_behave_differently():
    """⚠⚠⚠ TWO MOLECULES WITH THE SAME CANONICAL SMILES, ONE OF THEM INERT.

    ``Molecule``'s docstring states the identity contract -- *equal iff their
    canonical SMILES match* -- and the pre-C5 product satisfied it while
    behaving differently, because RDKit set ``noImplicit`` on any product atom
    whose H count the product template spelled. This test pins BOTH halves: the
    old object really was equal, and it really was inert.
    """
    old, new = _inverted_glucose(True), _inverted_glucose(False)
    assert old.smiles == new.smiles == ALPHA_GLUCOSE
    assert old == new
    # The OXYGEN is the atom that matters: it is the anomeric hydroxyl
    # `glycoside_hydrolysis` spelled `[OX2H1:5]`, and the three ABE branches
    # send it into a CO2 they wrote `[O:6]=[C:9]=[O:10]` with no H count -- so
    # it arrives as `O=C=[OH]` and the whole product set is discarded.
    # (Chiral carbons carry the flag in BOTH, because `[C@H]` writes its H in
    # brackets; that is normal and harmless, and pinning it here is what keeps
    # this test about the oxygen.)
    def flagged_oxygens(m):
        return sum(1 for a in m._mol.GetAtoms()
                   if a.GetSymbol() == "O" and a.GetNoImplicit())

    assert flagged_oxygens(old) == 1
    assert flagged_oxygens(new) == 0

    water = Molecule.from_smiles(WATER)
    for t in fermentation_chemistry():
        extra = (water,) * (t.n_reactant_slots - 1)
        assert t.run((old,) + extra) == [], t.name        # the bug
        assert t.run((new,) + extra) != [], t.name        # the fix


def test_a_brewer_can_invert_and_ferment(thermo, vol):
    """⚠⚠⚠ C4's DOCSTRING SAYS A BREWER *"has to invert the sugar first"*, AND
    BEFORE C5 A BREWER WHO DID GOT NOTHING.

    Sucrose is inert to all four fermentation templates by design; the inversion
    is ``glycoside_hydrolysis``; and the glucose it made could not be fermented.
    Every fermentation test C4 wrote charges glucose directly, so nothing saw
    it. This is the load-bearing test of the fix.
    """
    tm = [glycoside_hydrolysis()] + fermentation_chemistry()
    from_sucrose = net([WATER, SUCROSE], tm, thermo, vol)
    assert ETHANOL in from_sucrose.species
    assert len(from_sucrose.reactions) == 4


def test_no_template_pair_disagrees_about_a_species_one_of_them_made(
    thermo, vol
):
    """The general statement of the same thing, swept over the library.

    For every unimolecular template and every species any template can MAKE from
    a corpus substrate: running it on the made molecule and on the same SMILES
    parsed must give the same number of product sets. Before C5 there were EIGHT
    disagreements and every one was C4's chemistry -- seven a fermentation
    template on sugar `glycoside_hydrolysis` had inverted, and the eighth C4's
    own lactic acid failing to reach `alkene_dehydration`.
    """
    import inspect

    from chemsim.reactions import library, synthesis
    from chemsim.reactions.template import ReactionTemplate

    tmpls = {}
    for mod in (library, synthesis):
        for nm, fn in vars(mod).items():
            if nm.startswith("_") or not inspect.isfunction(fn):
                continue
            sig = inspect.signature(fn)
            if any(p.default is inspect.Parameter.empty
                   for p in sig.parameters.values()):
                continue
            try:
                t = fn()
            except Exception:
                continue
            if isinstance(t, ReactionTemplate):
                tmpls[t.name] = t

    corpus = [m for _cid, m in _corpus()]
    made = {}
    for t in tmpls.values():
        slots = []
        for i in range(t.n_reactant_slots):
            pat = t.reactant_pattern(i)
            hits = [m for m in corpus if m._mol.HasSubstructMatch(pat)][:3]
            slots.append(hits)
        if any(not sl for sl in slots):
            continue
        for combo in itertools.islice(itertools.product(*slots), 24):
            try:
                outs = t.run(combo)
            except Exception:
                continue
            for ps in outs:
                for p in ps:
                    made.setdefault(p.smiles, p)

    assert len(made) > 300, len(made)
    for smi, mol in made.items():
        ref = Molecule.from_smiles(smi)
        for t in tmpls.values():
            if t.n_reactant_slots != 1:
                continue
            if not ref._mol.HasSubstructMatch(t.reactant_pattern(0)):
                continue
            assert len(t.run((mol,))) == len(t.run((ref,))), (smi, t.name)


def test_the_kolbe_cascade_needs_its_generation_cap_declared():
    """⚠⚠ REMOVING THE BUG REMOVED AN ACCIDENTAL CAP. ``kolbe_schmitt`` feeds
    itself through the phenoxide it makes, and generation 4 wants a dianion the
    corpus does not price. The bound is declared in ``test_named_routes.py``
    now; this pins WHY it has to be."""
    th = electrolyte_provider()
    vl = VolatilityProvider(th)
    seed = [_c("Oc1ccccc1"), _c("O=C=O"), WATER]
    tm = [kolbe_schmitt()] + list(dissociation_templates())
    n3 = build_network(seed, tm, thermo=th, volatility=vl, max_species=40,
                       generations=3)
    assert _c("O=C([O-])c1ccccc1[O-]") in n3.species
    with pytest.raises(ValueError, match="cannot derive reverse kinetics"):
        build_network(seed, tm, thermo=th, volatility=vl, max_species=40,
                      generations=4)


def test_the_salicylate_second_pka_is_priced(thermo):
    """The row C5 had to add -- exposed, not missed: nothing could reach the
    mono-anion with a template before the fix."""
    dianion = electrolyte_provider().get(_c("O=C([O-])c1ccccc1[O-]"))
    assert dianion.Gf < 0.0
    assert "pKa" in dianion.source


# ---------------------------------------------------------------------------
# the flask
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def hmf_net(thermo, vol):
    return net([WATER, FRUCTOSE], furan_chemistry(), thermo, vol)


def test_the_hmf_rises_peaks_and_falls(hmf_net):
    """⚠⚠ THE POINT OF BUILDING THE +0 ROW. Without the rehydration this flask
    runs to 100% HMF; with it the peak is where two barriers cross."""
    ys = [flask(hmf_net, {WATER: WATER_CHARGE, FRUCTOSE: SUGAR_CHARGE},
                t=h * 3600.0).total(HMF) for h in (2.0, 11.0, 60.0)]
    assert ys[0] < ys[1] > ys[2]
    assert ys[1] / SUGAR_CHARGE == pytest.approx(0.5234, abs=5e-3)


def test_levulinic_and_formic_come_out_exactly_one_to_one(hmf_net):
    st = flask(hmf_net, {WATER: WATER_CHARGE, FRUCTOSE: SUGAR_CHARGE},
               t=20.0 * 3600.0)
    assert st.total(FORMIC) == pytest.approx(st.total(LEVULINIC), rel=1e-9)
    assert st.total(LEVULINIC) > 0.05


def test_selectivity_improves_with_temperature(hmf_net):
    """⚠⚠⚠ THE PREDICTION NOTHING WAS AIMED AT. The side reaction has the LOWER
    barrier (110 against 140 kJ/mol), so it is the less temperature-sensitive
    step and a hotter flask keeps more of its HMF. Hot-and-short is how this
    process is actually run, and only the LEVEL of the yield was fitted."""
    peaks = []
    for T in (390.0, 420.0, 450.0):
        best = 0.0
        for t in np.geomspace(1.0e3, 2.0e6, 16):
            y = flask(hmf_net, {WATER: WATER_CHARGE, FRUCTOSE: SUGAR_CHARGE},
                      t=float(t), T=T).total(HMF)
            best = max(best, y)
        peaks.append(best / SUGAR_CHARGE)
    assert peaks[0] < peaks[1] < peaks[2]
    assert peaks[0] == pytest.approx(0.399, abs=0.02)
    assert peaks[2] == pytest.approx(0.633, abs=0.02)


def test_an_inert_spectator_raises_the_yield_through_the_volume(thermo, vol):
    """⚠⚠ GLUCOSE DOES NOTHING IN THIS NETWORK AND ADDING IT IS WORTH NINE
    POINTS. The rehydration is second order in WATER and the dehydration is
    zeroth, so anything that takes up liquid volume protects the HMF. That is
    what the corpus row's "DMSO or biphasic" is for, reproduced by an engine
    with no solvent model at all -- because water is a reactant in the rate law
    rather than a background."""
    n = net([WATER, FRUCTOSE, ALPHA_GLUCOSE], furan_chemistry(), thermo, vol)
    assert not [r for r in n.reactions if ALPHA_GLUCOSE in r.reactants]
    out = []
    for charge in ({WATER: WATER_CHARGE, FRUCTOSE: SUGAR_CHARGE},
                   {WATER: WATER_CHARGE, FRUCTOSE: SUGAR_CHARGE,
                    ALPHA_GLUCOSE: 0.5}):
        best = 0.0
        for t in np.geomspace(3.0e3, 3.0e5, 12):
            best = max(best, flask(n, charge, t=float(t)).total(HMF))
        out.append(best / SUGAR_CHARGE)
    assert out[1] - out[0] == pytest.approx(0.09, abs=0.02)


def test_furfural_runs_to_completion_and_that_is_an_upper_bound(thermo, vol):
    """⚠ NO RESINIFICATION. Real furfural stops near 50% because it condenses
    into humins, and this project has no representation for an amorphous
    polymer. `hmf-route` got a yield-limiting row because the CORPUS wrote one;
    `furfural-route` did not, and the difference is the catalog's, not the
    chemistry's."""
    n = net([WATER, XYLOSE], [aldofuranose_dehydration()], thermo, vol)
    st = flask(n, {WATER: WATER_CHARGE, XYLOSE: SUGAR_CHARGE}, t=12.0 * 3600.0)
    assert st.total(FURFURAL) == pytest.approx(SUGAR_CHARGE, rel=1e-6)


def test_the_whole_playable_chain_runs_from_sucrose(thermo, vol):
    """`invert-sugar` then `hmf-route`: the route is tier 2 because sucrose is
    natural here and fructose is not."""
    n = net([WATER, SUCROSE], [glycoside_hydrolysis()] + furan_chemistry(),
            thermo, vol)
    st = flask(n, {WATER: WATER_CHARGE, SUCROSE: SUGAR_CHARGE},
               t=10.0 * 3600.0)
    assert st.total(SUCROSE) == pytest.approx(0.0, abs=1e-9)
    assert st.total(HMF) > 0.25
