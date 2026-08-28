"""C5's standing audit: the sugar-to-furan dehydrations, and the two-generation
bug they walked into.

``PLAYABLE.md`` §8b's top row after C4 is ``dehydration-cyclisation`` -- +1
playable, +2 runnable, the largest runnable gain left on a table C4 flattened.
Its two catalog rows are ``hmf-route`` step 1 and ``furfural-route`` step 2.

⚠⚠⚠ **AND READING EVERY ROW SAID *DO NOT SPLIT*, WHICH IS THE OPPOSITE OF WHAT
IT SAID TO C3 AND C4.** Both rows are one mechanism -- an acid-catalysed triple
dehydration of a sugar into a furan -- so the class stands and the credit needs
BOTH templates. Credit it off the HMF row alone and ``furfural-route`` goes
template-ready with nothing able to make furfural. Panel 1 is that arithmetic;
panel 2 fires the SMARTS over all 1583 corpus compounds.

⚠⚠ **THE CORPUS SPELLING C4 BOOKED AS A LOST SUBSTRATE IS THIS CLASS'S
LOAD-BEARING ONE -- FOR ONE ROW OF TWO.** Both sugars are spelled as furanoses.
Fructofuranose's ring *is* 5-HMF's furan ring, so that rewrite forms no ring bond
at all; xylofuranose's ring is the WRONG ring, so that one breaks it, sends the
oxygen out as a water and closes a new ring from C5. Panel 3 measures both, out
of RDKit's own reactant-to-product atom tags.

⚠⚠⚠ **THE SESSION'S ENGINE FINDING IS A BUG THAT TOOK TWO GENERATIONS TO SEE,
AND ITS BEST DEMONSTRATION IS ON C4's CHEMISTRY RATHER THAN THIS SESSION'S OWN
(panel 4).** ``ReactionTemplate.run`` handed back products carrying RDKit's
``noImplicit`` flag, and no template can run on such a molecule: it is found by
substructure search, priced, charged and reported exactly as normal, and then
produces NOTHING. Charge the same species by hand and it reacts. **So the engine
could not ferment sugar it had inverted itself** -- C4's docstring says a brewer
*"has to invert the sugar first"*, and a brewer who did got no ethanol. Fixed by
re-parsing every product from its own canonical SMILES.

⚠ **AND REMOVING IT REMOVED AN ACCIDENTAL GENERATION CAP.** ``kolbe_schmitt``
feeds itself through the phenoxide it makes; the bug had been stopping that
network at generation 2, and a test now declares the bound it had been relying
on. Panel 5.

Panel 6 is the flask: sucrose in, inverted, dehydrated, over-cooked. Panel 7 is
the prediction nothing was aimed at -- **selectivity improves with temperature**,
because the side reaction has the LOWER barrier.

Run: ``python validation/furans.py`` (~2 min).

⚠ EVERY PRINTED LINE HERE IS ASCII. The console is cp1252 and a warning glyph in
a ``print`` kills the script mid-panel. Glyphs belong in docstrings and comments.
"""

from __future__ import annotations

import glob
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

import numpy as np  # noqa: E402
from rdkit import Chem  # noqa: E402
from rdkit.Chem import AllChem  # noqa: E402

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
    homolactic_fermentation,
    hydroxymethylfurfural_rehydration,
    ketofuranose_dehydration,
)
from chemsim.reactions.thermo import reaction_deltas  # noqa: E402
from chemsim.vessel import Vessel  # noqa: E402


def _c(smi: str) -> str:
    return Molecule.from_smiles(smi).smiles


WATER = _c("O")
FRUCTOSE = _c("OC[C@H]1O[C@](O)(CO)[C@@H](O)[C@@H]1O")
XYLOSE = _c("OC[C@@H]1O[C@@H](O)[C@H](O)[C@@H]1O")
GLUCOSE = _c("OC[C@H]1O[C@@H](O)[C@H](O)[C@@H](O)[C@@H]1O")
SUCROSE = _c("OC[C@H]1O[C@@](CO)(O[C@H]2O[C@H](CO)[C@@H](O)[C@H](O)[C@H]2O)"
             "[C@@H](O)[C@@H]1O")
HMF = _c("OCc1ccc(C=O)o1")
FURFURAL = _c("O=Cc1ccco1")
LEVULINIC = _c("CC(=O)CCC(=O)O")
FORMIC = _c("O=CO")
ETHANOL = _c("CCO")

THERMO = ThermochemistryProvider()
VOL = VolatilityProvider(THERMO)
TIGHT = dict(rtol=1e-8, atol=1e-12)

# THE REFERENCE FLASK, deliberately C4's so the two sessions can be compared:
# 0.5 mol of sugar in 10 mol of water is ~0.19 L of a 2.6 M liquor, in a sealed
# 2 L vessel. The temperature is the corpus row's own, 420 K.
VESSEL, SUGAR_CHARGE, WATER_CHARGE, T_REF = 2.0, 0.5, 10.0, 420.0


def net(species, templates):
    return build_network(species, list(templates), thermo=THERMO, volatility=VOL)


def flask(network, charge, *, t, T=T_REF, volume=VESSEL):
    v = Vessel(network, volume=volume, T=T, T_env=T, UA=1.0e6, k_vent=0.0)
    v.charge(dict(charge), phase="liquid")
    if t > 0.0:
        v.run(float(t), **TIGHT)
    return v


def rule(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def corpus():
    rows = []
    for f in sorted(glob.glob(os.path.join(
            _ROOT, "data", "catalog", "compounds", "*.psv"))):
        for line in open(f, encoding="utf-8"):
            p = [x.strip() for x in line.strip().split("|")]
            if len(p) < 3 or not p[0] or p[0].startswith("#") or p[0] == "id":
                continue
            m = Chem.MolFromSmiles(p[2])
            if m is not None:
                rows.append((p[0], p[2], Molecule(m)))
    return rows


# ---------------------------------------------------------------------------
def panel_1_the_class() -> None:
    rule("1. TWO ROWS, ONE MECHANISM -- so the class is NOT split, and the "
         "credit needs BOTH")
    print("""
`PLAYABLE.md` 8b's top row. C3 bought a class by reading its second row; C4
bought one by SPLITTING it five ways. The same rule -- read every row before
crediting the class -- says DO NOT SPLIT here:

    hmf-route      1   fructose + H2SO4 -> 5-HMF    + water + H2SO4
    furfural-route 2   xylose   + H2SO4 -> furfural + water + H2SO4

Both are an acid-catalysed TRIPLE DEHYDRATION of a sugar into a furan, and each
balances exactly 1:1 on its own sugar once the water is counted:""")
    for label, sub, prod in (("fructose -> 5-HMF", FRUCTOSE, HMF),
                             ("xylose -> furfural", XYLOSE, FURFURAL)):
        f_in = Molecule.from_smiles(sub).formula
        f_out = Molecule.from_smiles(prod).formula
        print(f"    {label:22s} {f_in:>10s}  ->  {f_out:>10s} + 3 H2O")
    print("""
So the class STANDS. But two rows means two substrates and two templates, and
crediting it off the HMF row alone would take `furfural-route` template-ready
with nothing in the engine able to make furfural -- C4's false credit, arriving
from the other direction.""")


def panel_2_the_smarts() -> None:
    rule("2. THE SMARTS, OVER ALL 1583 CORPUS COMPOUNDS -- and every extra hit "
         "is right")
    rows = corpus()
    print(f"\n  corpus molecules read: {len(rows)}\n")
    water = Molecule.from_smiles(WATER)
    for tmpl in (ketofuranose_dehydration(), aldofuranose_dehydration(),
                 hydroxymethylfurfural_rehydration()):
        pat = tmpl.reactant_pattern(0)
        extra = (water,) * (tmpl.n_reactant_slots - 1)
        hits = [r for r in rows if r[2]._mol.HasSubstructMatch(pat)]
        print(f"  {tmpl.name}: {len(hits)} substrate(s)")
        for cid, _smi, mol in hits:
            outs = set()
            for ps in tmpl.run((mol,) + extra):
                outs.add(" + ".join(sorted(p.smiles for p in ps)))
            for o in sorted(outs):
                print(f"      {cid:26s} -> {o}")
    print("""
  Every one of those is correct chemistry and none of it was aimed at.
  EVERY pentose gives furfural in hot acid -- that is what a pentosan assay
  measures -- and sorbose is a ketohexose that dehydrates exactly as fructose
  does. The templates are stereo-blind by construction (C4's `[C;H1;@,@@:n]`
  device) and the generalisation that buys is the chemistry's own.""")
    suc = Molecule.from_smiles(SUCROSE)
    inert = [t.name for t in (ketofuranose_dehydration(),
                              aldofuranose_dehydration())
             if not suc._mol.HasSubstructMatch(t.reactant_pattern(0))]
    print(f"\n  SUCROSE is inert to: {', '.join(inert)}")
    print("  -- because a glycoside has no free anomeric -OH. A syrup has to be")
    print("     INVERTED first, and panel 4 is about why the engine could not.")


def _ring_provenance(tmpl, substrate_smiles):
    """Which atoms of the product's furan ring came from the SUGAR'S own ring?

    RDKit tags every product atom it carried over with ``react_atom_idx``, so
    this is a measurement rather than a reading of the SMARTS.
    """
    rxn = AllChem.ReactionFromSmarts(tmpl.smarts)
    sub = Chem.MolFromSmiles(substrate_smiles)
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
            kept, brought = [], []
            for idx in rings[0]:
                a = p.GetAtomWithIdx(idx)
                src = (a.GetIntProp("react_atom_idx")
                       if a.HasProp("react_atom_idx") else None)
                (kept if src in sugar_ring else brought).append(a.GetSymbol())
            return kept, brought
    return [], []


def panel_3_the_two_rings() -> None:
    rule("3. THE CORPUS SPELLS BOTH SUGARS AS FURANOSES, AND ONLY ONE OF THOSE "
         "RINGS IS THE PRODUCT'S")
    print("""
C4 measured that its hexopyranose pattern does not fire on fructose, "because
the corpus spells fructose as a FURANOSE", and booked it as a lost substrate.
Here that spelling is load-bearing -- for ONE row of the two. Measured out of
RDKit's own reactant-to-product atom tags rather than read off the SMARTS:
""")
    for label, tmpl, sub in (
            ("fructose -> 5-HMF   ", ketofuranose_dehydration(), FRUCTOSE),
            ("xylose   -> furfural", aldofuranose_dehydration(), XYLOSE)):
        kept, brought = _ring_provenance(tmpl, sub)
        print(f"  {label}")
        print(f"      product ring atoms out of the SUGAR'S OWN RING : "
              f"{len(kept)} of 5   {kept}")
        print(f"      product ring atoms brought in from OUTSIDE it  : "
              f"{len(brought)} of 5   {brought}")
    print("""
  fructose  5 of 5. The fructofuranose ring C2-C3-C4-C5-O IS 5-HMF's furan ring;
            NO ring bond is formed or broken. Three hydroxyls leave, C6 goes to
            the aldehyde, and aromaticity perception does the rest.
  xylose    3 of 5, and TWO atoms are brought in. The xylofuranose ring is
            C1-C2-C3-C4-O and furfural's is C2-C3-C4-C5-O -- the WRONG RING.
            C5 and its hydroxyl oxygen are pulled INTO the new ring; the sugar's
            own ring oxygen leaves as one of the three waters, and C1 is pushed
            OUT of the ring to become the aldehyde. Two of the sugar's five ring
            atoms do not survive as ring atoms at all.

  A coefficient vector cannot see that difference: both rows are 1:1 with three
  waters. Reading the MECHANISM is what says one template could not have covered
  both, and this panel is that reading turned into a number.""")


def _old_style_product(tmpl, reactants):
    """The product molecule this engine handed back BEFORE C5's fix.

    Sanitize and RemoveHs and stop there -- no round trip through canonical
    SMILES. Kept so that the standing audit can still SHOW the bug rather than
    assert that it once existed.
    """
    for product_set in tmpl._rxn.RunReactants(tuple(m._mol for m in reactants)):
        out = []
        for p in product_set:
            try:
                Chem.SanitizeMol(p)
                out.append(Molecule(Chem.RemoveHs(p)))
            except Exception:
                out = []
                break
        if out:
            yield tuple(out)


def _the_glucose(maker):
    suc, water = Molecule.from_smiles(SUCROSE), Molecule.from_smiles(WATER)
    for ps in maker(glycoside_hydrolysis(), (suc, water)):
        for p in ps:
            if p.smiles != WATER and "(CO)" not in p.smiles:
                return p
    return None


def panel_4_the_two_generation_bug() -> None:
    rule("4. THE ENGINE FINDING: a template could not run on a species another "
         "template MADE")
    print("""
Found two generations deep in this session's own chain, and then measured on
C4's. `glycoside_hydrolysis` spells its new anomeric hydroxyl `[OX2H1:5]`, so
the glucose it makes out of sucrose came back with RDKit's `noImplicit` flag SET
and its hydrogens counted as EXPLICIT. Substructure matching cannot see that --
the total H count is identical -- so the species is discovered, priced, charged
and reported exactly as normal. But RunReactants on it hands the flag to the
NEXT template's products; any product atom that template did not itself spell an
H count for then inherits an H it must not have; and `run` catches the resulting
valence error and returns an EMPTY list.

`_old_style_product` in this file reproduces the pre-C5 product exactly --
sanitize, RemoveHs, stop -- so the two can be printed side by side.
""")
    water = Molecule.from_smiles(WATER)
    old = _the_glucose(_old_style_product)
    new = _the_glucose(lambda t, r: t.run(r))
    print(f"  the glucose sucrose inversion makes  : {old.smiles}")
    print(f"  identical SMILES both ways           : {old.smiles == new.smiles}")
    print(f"  equal as Molecules                   : {old == new}")
    print("\n  atom flags (noImplicit, explicitH, totalH), first six atoms:")
    for lbl, mol in (("BEFORE the fix", old), ("AFTER  the fix", new)):
        print("    " + lbl + "  " + "  ".join(
            f"{a.GetSymbol()}({int(a.GetNoImplicit())},{a.GetNumExplicitHs()},"
            f"{a.GetTotalNumHs()})" for a in list(mol._mol.GetAtoms())[:6]))
    print("\n  and what C4's four fermentation templates make of each:")
    print("    template                     BEFORE   AFTER")
    for t in fermentation_chemistry() + [homolactic_fermentation()]:
        extra = (water,) * (t.n_reactant_slots - 1)
        print(f"    {t.name:26s} {len(t.run((old,) + extra)):7d} "
              f"{len(t.run((new,) + extra)):7d}")
    print("""
  Two molecules with the SAME canonical SMILES, equal by `Molecule.__eq__`, and
  one of them is inert. That is a violation of the type's own stated identity
  contract -- *two Molecules are equal iff their canonical SMILES match*.

  THE FOURTH ROW IS THE INTERESTING ONE. `homolactic_fermentation` was never
  broken, and not because it is more careful in general: it happens to spell an
  H count for the ONE atom that carried the flag, where the other three send
  that atom into a CO2 they wrote as `[O:6]=[C:9]=[O:10]` and inherit an H onto
  a doubly-bonded oxygen. **Writing an H count on every product atom IS a valid
  fix -- and it is a rule an author has to remember on every atom of every
  template, which is why the fix went into the type instead.**

  The consequence was not subtle:""")
    tm = [glycoside_hydrolysis()] + fermentation_chemistry()
    n_suc = net([WATER, SUCROSE], tm)
    n_glc = net([WATER, GLUCOSE], tm)
    print(f"\n    charge SUCROSE + water: {len(n_suc.species)} species, "
          f"{len(n_suc.reactions)} reactions, ethanol present = "
          f"{ETHANOL in n_suc.species}")
    print(f"    charge GLUCOSE + water: {len(n_glc.species)} species, "
          f"{len(n_glc.reactions)} reactions, ethanol present = "
          f"{ETHANOL in n_glc.species}")
    print("""
  Before the fix the first of those read 4 species, 1 reaction, ethanol FALSE.
  C4's docstring says a brewer "has to invert the sugar first, by
  glycoside_hydrolysis, which is what `ethanol-fermentation` step 1 and a brewer
  both do". A brewer who did got nothing at all. The claim was right about the
  chemistry and false about the engine, and no single-template test could have
  caught it -- catching it takes one template to MAKE what another consumes.""")


def panel_5_the_accidental_cap() -> None:
    rule("5. AND REMOVING THE BUG REMOVED AN UNDECLARED GENERATION CAP")
    th = electrolyte_provider()
    vol = VolatilityProvider(th)
    seed = [_c("Oc1ccccc1"), _c("O=C=O"), WATER]
    tmpl = [kolbe_schmitt()] + list(dissociation_templates())
    print("""
`kolbe_schmitt` FEEDS ITSELF. It carboxylates a phenoxide to salicylate;
dissociation then takes salicylate's PHENOL proton (pKa 13.4, a row C5 had to
add); and the dianion is a phenoxide the same template carboxylates AGAIN. The
old behaviour stopped that walk at generation 2 by accident.
""")
    print("     gen   species   reactions   outcome")
    for g in (1, 2, 3, 4):
        try:
            n = build_network(seed, tmpl, thermo=th, volatility=vol,
                              max_species=40, generations=g)
            print(f"     {g:3d}   {len(n.species):7d}   {len(n.reactions):9d}"
                  f"   ok")
        except Exception as exc:
            first = str(exc).split(":")[0]
            print(f"     {g:3d}         -           -   REFUSED  ({first})")
    print("""
  Generation 4 wants 2-hydroxyisophthalate, which the corpus does not price --
  and the series does not stop there. So the bound is DECLARED now, in
  tests/test_named_routes.py, which is what `aromatic_chemistry` already tells a
  reader to do for a template that feeds itself. An accidental cap is still a
  cap: removing the accident means writing the cap down.""")


def panel_6_the_flask() -> None:
    rule("6. THE FLASK: sucrose in, INVERTED, dehydrated, and then OVER-COOKED")
    n = net([WATER, SUCROSE], [glycoside_hydrolysis()] + furan_chemistry())
    print(f"\n  network from sucrose + water: {len(n.species)} species, "
          f"{len(n.reactions)} reactions")
    for r in n.reactions:
        print(f"    {r.name:36s} {' + '.join(r.reactants)}")
        print(f"    {'':36s}   -> {' + '.join(r.products)}")
    print(f"\n  {SUGAR_CHARGE} mol sucrose in {WATER_CHARGE} mol water, "
          f"sealed {VESSEL} L at {T_REF:.0f} K\n")
    print("      t/h    sucrose   fructose      5-HMF   levulinic   HMF/made%")
    for t in (1.0, 4.0, 10.0, 20.0, 40.0, 100.0):
        st = flask(n, {WATER: WATER_CHARGE, SUCROSE: SUGAR_CHARGE},
                   t=t * 3600.0).state()
        made = st.total(HMF) + st.total(LEVULINIC)
        pc = 100.0 * st.total(HMF) / made if made > 1e-12 else 0.0
        print(f"  {t:7.1f} {st.total(SUCROSE):10.6f} {st.total(FRUCTOSE):10.6f}"
              f" {st.total(HMF):10.6f} {st.total(LEVULINIC):11.6f} {pc:10.2f}")
    print("""
  THE 5-HMF RISES, PEAKS AND FALLS. Nothing declares a stopping time: the peak
  sits where the two rates cross, and both come from a barrier. Without
  `hydroxymethylfurfural_rehydration` this flask would run to 100% HMF and
  report a number no laboratory has ever seen.

  And this whole chain is the fix in panel 4. The sucrose has to be INVERTED
  before anything can dehydrate it, so every row above is two generations deep.""")
    st = flask(n, {WATER: WATER_CHARGE, SUCROSE: SUGAR_CHARGE},
               t=20.0 * 3600.0).state()
    lev, form = st.total(LEVULINIC), st.total(FORMIC)
    print(f"\n  levulinic : formic at 20 h = {lev:.9f} : {form:.9f}"
          f"   ratio {form / lev if lev else 0.0:.12f}")
    print("  -- 1:1 to solver precision, which is the stoichiometry showing up")
    print("     as a property of the run rather than as a claim about it.")


def panel_7_selectivity_vs_temperature() -> None:
    rule("7. THE PREDICTION NOTHING WAS AIMED AT: selectivity IMPROVES with "
         "temperature")
    n = net([WATER, FRUCTOSE], furan_chemistry())
    print("""
The formation barrier is 140 kJ/mol and the destruction barrier is 110, so the
destruction is the LESS temperature-sensitive step and a hotter flask should
keep more of its HMF. Hot-and-short is exactly how this process is run. Neither
barrier was chosen with this in mind; both are literature values, and only the
LEVEL of the yield is fitted -- 52.5% at 420 K against a reported ~50-55%.

     T/K    peak HMF yield     at t/h    fructose left
""")
    for T in (390.0, 405.0, 420.0, 435.0, 450.0):
        best = (0.0, 0.0, 0.0)
        for t in np.geomspace(300.0, 4.0e6, 30):
            st = flask(n, {WATER: WATER_CHARGE, FRUCTOSE: SUGAR_CHARGE},
                       t=float(t), T=T).state()
            y = st.total(HMF) / SUGAR_CHARGE
            if y > best[0]:
                best = (y, float(t), st.total(FRUCTOSE))
        print(f"   {T:5.0f}       {best[0] * 100:8.2f}%   {best[1] / 3600:9.2f}"
              f"     {best[2]:10.6f}")
    print("""
  The yield rises monotonically with temperature and the batch gets shorter.
  That is a consequence of two sourced barriers and of nothing else: the fitted
  pre-exponential sets the LEVEL, and the DIRECTION is the part that could have
  come out wrong. S11's competing-templates finding, on a CONSECUTIVE pair
  instead of a parallel one.""")
    glucose = _c("OC[C@H]1O[C@H](O)[C@H](O)[C@@H](O)[C@@H]1O")
    n2 = net([WATER, FRUCTOSE, glucose], furan_chemistry())
    print("\n  AND THE SECOND LEVER IS AN INERT SPECTATOR, WHICH NOBODY ASKED "
          "FOR:\n")
    for label, charge in (
            ("fructose alone            ", {WATER: WATER_CHARGE,
                                            FRUCTOSE: SUGAR_CHARGE}),
            ("the same, plus 0.5 glucose", {WATER: WATER_CHARGE,
                                            FRUCTOSE: SUGAR_CHARGE,
                                            glucose: 0.5})):
        best = (0.0, 0.0)
        for t in np.geomspace(3.0e3, 3.0e5, 24):
            st = flask(n2, charge, t=float(t)).state()
            y = st.total(HMF) / SUGAR_CHARGE
            if y > best[0]:
                best = (y, float(t))
        print(f"    {label}  peak HMF {best[0] * 100:6.2f}%  at "
              f"{best[1] / 3600:6.2f} h")
    print("""
  GLUCOSE DOES NOTHING IN THIS NETWORK -- no template touches it -- and adding
  it raises the yield by nine points. It takes up liquid volume, so the WATER
  concentration falls, and the rehydration is second order in water while the
  dehydration is zeroth. **A chemically inert spectator moves the yield, through
  the volume.**

  That is the corpus row's own condition column explaining itself: `hmf-route`
  step 1 says "420 K, DMSO or biphasic", and what DMSO and a biphasic solvent
  are FOR is taking the water away from the HMF. This engine has no solvent
  model, and it reproduces the direction of that trick anyway -- because the
  water is a REACTANT in the rate law rather than a background.""")


def panel_8_furfural_and_what_it_cannot_see() -> None:
    rule("8. THE OTHER ROW, AND THE UPPER BOUND IT CANNOT SEE")
    n = net([WATER, XYLOSE], [aldofuranose_dehydration()])
    print(f"\n  xylose + water: {len(n.species)} species, "
          f"{len(n.reactions)} reaction(s)\n")
    print("      t/h     xylose   furfural   conversion%")
    for t in (1.0, 4.0, 12.0, 40.0):
        st = flask(n, {WATER: WATER_CHARGE, XYLOSE: SUGAR_CHARGE},
                   t=t * 3600.0).state()
        conv = 100.0 * (SUGAR_CHARGE - st.total(XYLOSE)) / SUGAR_CHARGE
        print(f"  {t:7.1f} {st.total(XYLOSE):10.6f} {st.total(FURFURAL):10.6f}"
              f"   {conv:10.2f}")
    print("""
  IT RUNS TO COMPLETION, AND THAT IS AN UPPER BOUND. Real furfural yields stop
  near 50% because furfural RESINIFIES -- it condenses with itself and with the
  intermediates into humins, an insoluble tar. The corpus has no row for that
  and this project has no representation for an amorphous polymer, so nothing
  here can express it. `hmf-route` got its yield-limiting step because the
  CORPUS wrote one down; `furfural-route` did not, and the difference between
  the two flasks above is a property of the CATALOG rather than of the
  chemistry.

  C3's rule with a third mechanism under it: every yield here is an upper bound,
  and naming which mechanism is missing is what makes it a bound and not a
  guess.""")


def panel_9_the_standard_state_notice() -> None:
    rule("9. AND THE SUGARS MIX STANDARD STATES, FOR THE THIRD SESSION RUNNING")
    print("""
C3 met this on a co-product and C4 on a substrate. Here it is on a substrate
again: a sugar's vapour pressure at 298 K is below the standard-state floor, so
it takes no liquid shift while its furan and its waters all do.
""")
    n = net([WATER, FRUCTOSE], furan_chemistry())
    print("    reaction                             dH(gas)  dG(gas)  "
          "dH(liq)  dG(liq)")
    for r in n.reactions:
        dh_g, dg_g = reaction_deltas(r, THERMO)
        dh_l, dg_l = reaction_deltas(r, THERMO, VOL)
        print(f"    {r.name:34s} {dh_g:8.1f} {dg_g:8.1f} {dh_l:8.1f} "
              f"{dg_l:8.1f}")
    print("""
  What it costs is the EQUILIBRIUM CONSTANT and nothing else: all three
  templates are irreversible and dG is strongly negative on either basis, so no
  sign is in doubt. Do not quote a K for these reactions -- C4's rule, third
  time, and this time printed beside the numbers it applies to.""")


def main() -> None:
    panel_1_the_class()
    panel_2_the_smarts()
    panel_3_the_two_rings()
    panel_4_the_two_generation_bug()
    panel_5_the_accidental_cap()
    panel_6_the_flask()
    panel_7_selectivity_vs_temperature()
    panel_8_furfural_and_what_it_cannot_see()
    panel_9_the_standard_state_notice()
    print("\n" + "=" * 78)
    print("done")


if __name__ == "__main__":
    main()
