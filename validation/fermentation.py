"""C4's standing audit: the ABE fermentation, and the class M5 refused.

M5 refused ``fermentation`` as *"a metabolic NETWORK, not a transformation"* and
``PLAYABLE.md`` §8b priced it as the biggest single class left, at **+2
playable**. Both were right, and neither says what to build.

⚠⚠⚠ **THE REFUSAL WAS ABOUT THE LABEL.** Five catalog rows carried the class and
they are five mechanisms -- clostridial solventogenesis, homolactic glycolysis,
aerobic overflow, reductive amination and secondary-metabolite biosynthesis. M1's
rule (*a class must name a MECHANISM, not an outcome*) applies, and
``route_steps.psv`` names five now. **Two are built and three are named gaps, and
the split is what makes the credit honest**: a template written off
``abe-fermentation`` cannot make penicillin G out of a sugar, and the old
five-row class would have credited it for four routes that cannot run.

⚠⚠⚠ **AND THE LUMP THAT MADE THE REFUSAL LOOK RIGHT WAS AN ARTEFACT OF THE ROW'S
FORMATTING.** ``abe-fermentation`` is written 1:1 and balances only at
``5 C6H12O6 -> 2 acetone + 2 butanol + 2 ethanol + 12 CO2 + 8 H2``, which
NEXT_PROMPT correctly called *"not a graph rewrite"*. It is THREE reactions on
one line, and split, each balances exactly on ONE glucose. Panel 1 is that
arithmetic; panel 2 fires the SMARTS.

⚠⚠ **THE SESSION'S ENGINE FINDING IS A REFUTATION (panel 5).** MILESTONES §M10
scopes its cheap version as *"a declared order of ZERO in the substrate ... needs
no kernel change"*. It needs one, and the way it fails is worse than the two
docstrings that describe it: the substrate is CLAMPED at zero in the reported
state while the products keep growing past the stoichiometric ceiling -- 1.79 mol
of ethanol out of 0.5 mol of glucose -- and the run REPORTS SUCCESS for ~1900
simulated hours before the hard guard refuses. ⚠ ``conservation_report`` does see
every mole of it, and calls four tenths of a mole "round-off it could not
settle". Panel 5 runs all of that.

⚠⚠ **AND PANEL 8 IS NOT ABOUT FERMENTATION AT ALL.** Building the homolactic
branch needed a stereocentre suppressed, and measuring that turned up something
general: the property tables are keyed by canonical SMILES, so **a corpus row
spelled with stereochemistry can miss its own measured record and fall through to
an estimator.** Panel 8 counts how many of the 1583 corpus compounds that is.

⚠⚠⚠ **C7 CLOSED THAT, AND PANEL 8 NOW MEASURES ITS OWN SUBJECT OFF A PROVIDER
WITH THE FIX SWITCHED OFF.** The number it prints is the gap that WAS there; the
live provider is shown underneath it. Two of the panel's sentences did not
survive re-measurement and are corrected in place -- the count is 31 only
because the filter is `"@"`, and the advertised opposite-keying is two rows of
forty-nine. `validation/stereo_keying.py` is where that lives now.

Run: ``python validation/fermentation.py`` (~30 s).

⚠ EVERY PRINTED LINE HERE IS ASCII. The console is cp1252 and a warning glyph in
a ``print`` kills the script mid-panel. Glyphs belong in docstrings and comments.
"""

from __future__ import annotations

import csv
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

from rdkit import Chem  # noqa: E402
from rdkit.Chem import AllChem  # noqa: E402

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

# CANONICALISED, for C3's reason: ``state().total()`` is keyed by the network's
# own species strings, which are ``Molecule.from_smiles`` canonical form.
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

THERMO = ThermochemistryProvider()
# ⚠⚠ PANEL 8's SUBJECT IS CLOSED, AND THIS IS HOW IT KEEPS REPORTING ITS SIZE.
# C7 put a stereochemistry-free fallback in the provider lookup, so ``THERMO``
# no longer splits on a spelling. The panel measures the gap that WAS there off
# a provider with the fallback switched off -- the flag exists for exactly this
# -- and then shows what the live provider does with the same two spellings.
THERMO_EXACT = ThermochemistryProvider(stereo_fallback=False)
VOL = VolatilityProvider(THERMO)
TIGHT = dict(rtol=1e-8, atol=1e-12)

# THE REFERENCE FLASK. 0.5 mol of glucose in 10 mol of water is ~0.19 L of a
# 2.6 M sugar liquor -- a strong mash -- in a 2 L vessel at 310 K, which is
# blood heat and what a clostridial fermenter runs at. Every number below
# carries it. ⚠ SEALED: k_vent = 0, and panel 6 is what that costs.
VESSEL, GLU_CHARGE, WATER_CHARGE, T_FERM = 2.0, 0.5, 10.0, 310.0


def net(species, templates):
    return build_network(species, list(templates), thermo=THERMO,
                         volatility=VOL)


def flask(templates, *, t, T=T_FERM, glu=GLU_CHARGE, water=WATER_CHARGE,
          k_vent=0.0, volume=VESSEL):
    v = Vessel(net([WATER, GLUCOSE], templates), volume=volume, T=T, T_env=T,
               UA=1.0e6, k_vent=k_vent)
    v.charge({WATER: water, GLUCOSE: glu}, phase="liquid")
    if t > 0.0:
        v.run(t, **TIGHT)
    return v


def counts(pairs):
    out: dict[str, int] = {}
    for smi, n in pairs:
        for el, c in Molecule.from_smiles(smi).element_counts().items():
            out[el] = out.get(el, 0) + c * n
    return out


def fmt(d):
    return "".join(f"{el}{d[el]}" for el in sorted(d) if d[el])


def rule(title):
    print()
    print("=" * 74)
    print(title)
    print("=" * 74)


# ---------------------------------------------------------------------------


def panel1():
    rule("PANEL 1 -- THE LUMP DOES NOT BALANCE 1:1 AND EACH BRANCH DOES")
    print("  the catalog row, as written, one of everything:")
    L = counts([(GLUCOSE, 1)])
    Rr = counts([(ACETONE, 1), (BUTANOL, 1), (ETHANOL, 1), (CO2, 1), (H2, 1)])
    print(f"    abe-fermentation 1        {fmt(L):10s} -> {fmt(Rr):10s} "
          f"{'EXACT' if L == Rr else 'NO'}")
    print("    (it balances only at 5:2:2:2:12:8 -- five sugars in and six")
    print("     carbon skeletons out, which is NOT a graph rewrite. It is")
    print("     three reactions written on one line.)")
    print()
    print("  the three branches, one glucose each:")
    rows = [
        ("ethanolic   1:2:2", [(GLUCOSE, 1)], [(ETHANOL, 2), (CO2, 2)]),
        ("butanolic   1:1:2:1", [(GLUCOSE, 1)],
         [(BUTANOL, 1), (CO2, 2), (WATER, 1)]),
        ("acetonic  1+1:1:3:4", [(GLUCOSE, 1), (WATER, 1)],
         [(ACETONE, 1), (CO2, 3), (H2, 4)]),
        ("homolactic  1:2", [(GLUCOSE, 1)], [(LACTIC_FLAT, 2)]),
    ]
    for label, lhs, rhs in rows:
        L, Rr = counts(lhs), counts(rhs)
        print(f"    {label:24s} {fmt(L):10s} -> {fmt(Rr):10s} "
              f"{'EXACT' if L == Rr else 'NO'}")
    print()
    print("  So M5's refusal was about the LABEL and the ROW's formatting, not")
    print("  about the chemistry. Read every row of a class, and read it as the")
    print("  mechanism rather than as the line.")


def panel2():
    rule("PANEL 2 -- WHAT THE SMARTS FIRE ON, AND WHAT THEY REFUSE")
    subs = [("glucose", GLUCOSE), ("mannose", MANNOSE),
            ("fructose", FRUCTOSE), ("sucrose", SUCROSE),
            ("ethanol", ETHANOL), ("glycerol", _c("OCC(O)CO")),
            ("ribose", _c("OC[C@H]1O[C@H](O)[C@H](O)[C@@H]1O")),
            ("cyclohexanol", _c("OC1CCCCC1"))]
    tmpls = [ethanolic_fermentation(), butanolic_fermentation(),
             acetonic_fermentation(), homolactic_fermentation()]
    for t in tmpls:
        rxn = AllChem.ReactionFromSmarts(t.smarts)
        rxn.Initialize()
        n_slots = rxn.GetNumReactantTemplates()
        print(f"  -- {t.name}  ({n_slots} reactant slot(s))")
        for name, smi in subs:
            m = Chem.MolFromSmiles(smi)
            args = (m, Chem.MolFromSmiles(WATER)) if n_slots == 2 else (m,)
            outs = rxn.RunReactants(args)
            if not outs:
                print(f"       {name:14s} refuses")
                continue
            got = []
            for p in outs[0]:
                Chem.SanitizeMol(p)
                got.append(_c(Chem.MolToSmiles(p)))
            print(f"       {name:14s} {' + '.join(got)}")
    print()
    print("  THE TWO REFUSALS THAT ARE THE POINT:")
    print("   * sucrose. The anomeric carbon must carry an -OH, so a GLYCOSIDE")
    print("     does not match. A brewer inverts the sugar first and so must a")
    print("     player -- `glycoside_hydrolysis` is the step, and")
    print("     `ethanol-fermentation` step 1 is exactly that row.")
    print("   * fructose. Real clostridia eat it; this pattern cannot, because")
    print("     the corpus spells fructose as a FURANOSE and this is a")
    print("     six-ring pattern. S7's pyranose/furanose finding, costing a")
    print("     substrate instead of an equilibrium constant.")
    print("  And mannose IS eaten, which is right: same constitution, and the")
    print("  pattern queries no stereochemistry.")


def panel3():
    rule("PANEL 3 -- EVERY BRANCH MIXES STANDARD STATES, AND STILL CANNOT "
         "REVERSE")
    n = net([WATER, GLUCOSE], fermentation_chemistry()
            + [homolactic_fermentation()])
    print("     branch                    dH(ideal gas)  dH(pure liquid)"
          "   dS(gas)  dS(liquid)")
    for rxn in n.reactions:
        dHg, dGg = reaction_deltas(rxn, THERMO, None)
        dHl, dGl = reaction_deltas(rxn, THERMO, VOL)
        print(f"     {rxn.name:24s} {dHg:12.2f}  {dHl:14.2f}  "
              f"{(dHg - dGg) / 298.15 * 1000.0:8.2f}  "
              f"{(dHl - dGl) / 298.15 * 1000.0:9.2f}")
    print()
    print("  Glucose's vapour pressure at 298 K is below the standard-state")
    print("  floor -- its Tb is an unanchored 825.6 K estimate on a sugar that")
    print("  decomposes -- so it gets NO liquid shift while its products all")
    print("  do. The two conventions differ by 64-219 kJ/mol in dH and the")
    print("  SIGN OF dS FLIPS. That is C3's `vanillin-lignin` notice arriving")
    print("  on a SUBSTRATE rather than a co-product.")
    print()
    print("  WHAT IT COSTS: the equilibrium constant, and nothing else. dG is")
    print("  between -121 and -353 kJ/mol on either basis, so no branch is")
    print("  reversible under any reading and none declares itself so. DO NOT")
    print("  QUOTE A K FOR A FERMENTATION IN THIS PROJECT.")


def panel4():
    rule("PANEL 4 -- THE BATCH, AND THE SLATE THAT IS FITTED")
    print("     t/h   glucose     EtOH     BuOH  acetone      CO2       H2"
          "   conv%   A : B : E")
    for hours in (0.0, 12.0, 24.0, 36.0, 48.0, 72.0, 96.0):
        v = flask(fermentation_chemistry(), t=hours * 3600.0)
        st = v.state()
        g, e = st.total(GLUCOSE), st.total(ETHANOL)
        slate = (f"{st.total(ACETONE) / e:5.2f} :{st.total(BUTANOL) / e:5.2f}"
                 " : 1.00") if e > 0 else ""
        print(f"  {hours:6.1f} {g:9.5f} {e:8.5f} {st.total(BUTANOL):8.5f} "
              f"{st.total(ACETONE):8.5f} {st.total(CO2):8.4f} "
              f"{st.total(H2):8.4f} {100 * (GLU_CHARGE - g) / GLU_CHARGE:6.2f}"
              f"   {slate}")
    print()
    print("  FITTED: the batch time (77.6% in 48 h is an ABE batch) and the")
    print("  SOLVENT SLATE. The classical yield is 3:6:1 by MASS, which is")
    print("  2.38:3.73:1 by mole, and three pre-exponentials were set to it.")
    print("  That is a FIT and not a prediction: a real slate is set by the")
    print("  organism's regulation, and Evans-Polanyi over three branches that")
    print("  differ by 220 kJ/mol in dH would predict pure butanol.")
    print("  Selectivity between two CHEMICAL templates is derivable here")
    print("  (S11). Selectivity between two METABOLIC branches is not.")
    print()
    v = flask(fermentation_chemistry(), t=96.0 * 3600.0)
    st = v.state()
    gas = st.total(CO2) + st.total(H2)
    print("  NOT FITTED, AND IT IS THE ONE NUMBER THAT CHECKS THE MODEL:")
    print(f"    fermentation gas   CO2 {100 * st.total(CO2) / gas:5.2f}%  "
          f"H2 {100 * st.total(H2) / gas:5.2f}%     reported ~60 / ~40")
    print("    H2 comes ONLY from the acetonic branch, so the gas ratio is a")
    print("    consequence of the solvent slate and the three stoichiometries.")
    print()
    print("  AND TWO INVARIANTS OF THE RUN, which is panel 1's balance showing")
    print("  up as a property of the trajectory:")
    print(f"    H2 / acetone         {st.total(H2) / st.total(ACETONE):.12f}"
          "   (exactly 4, from the acetonic branch alone)")
    predicted = (3.0 * st.total(ACETONE) + 2.0 * st.total(BUTANOL)
                 + st.total(ETHANOL))
    print(f"    CO2 predicted        {predicted:.9f}")
    print(f"    CO2 in the flask     {st.total(CO2):.9f}   (3:2:1 per branch,"
          " and ethanol is 2 per glucose)")


def panel5():
    rule("PANEL 5 -- M10's CHEAP VERSION, RUN: IT MANUFACTURES SUGAR AND "
         "REPORTS SUCCESS")
    print("  MILESTONES M10: 'a declared order of ZERO in the substrate IS the")
    print("  saturated limit of Michaelis-Menten ... needs no kernel change'.")
    print("  It needs one. There is no availability gate outside the solid")
    print("  block (`_avail`), so an order-zero reactant keeps reacting after")
    print("  it has run out. Same template, same flask, one declared order --")
    print("  and run PAST the end of the sugar, which is the only place the")
    print("  difference lives:")
    print()
    print("     orders             t/h      glucose        EtOH    EtOH/max")
    t0 = ethanolic_fermentation()
    ceiling = 2.0 * GLU_CHARGE          # 2 ethanol per glucose, and no more
    for label, orders, hrs in (
        ("mass action (ours)", None, (48.0, 1500.0)),
        ("(0.0,) -- M10's  ", (0.0,), (200.0, 800.0, 1100.0, 1500.0, 3000.0)),
    ):
        t = ReactionTemplate(name=t0.name, smarts=t0.smarts, A=t0.A, Ea=t0.Ea,
                             phase=t0.phase, orders=orders)
        for hours in hrs:
            try:
                v = flask([t], t=hours * 3600.0)
                st = v.state()
                g, e = st.total(GLUCOSE), st.total(ETHANOL)
                flag = "   <-- IMPOSSIBLE" if e > ceiling * 1.000001 else ""
                print(f"     {label:18s} {hours:6.0f} {g:12.6f} {e:11.5f} "
                      f"{e / ceiling:9.3f}{flag}")
            except Exception as exc:                          # noqa: BLE001
                print(f"     {label:18s} {hours:6.0f} REFUSED  "
                      f"{type(exc).__name__}: {str(exc)[:44]}")
    print()
    print("  THE FAILURE IS WORSE THAN 'THE REACTANT GOES NEGATIVE', AND THAT")
    print("  IS THE FINDING. Two docstrings in this project say an order-zero")
    print("  reactant 'is driven negative'. What actually happens is:")
    print("    * the substrate is CLAMPED at 0.0 in the reported state, so it")
    print("      looks merely exhausted;")
    print("    * the products keep growing PAST the stoichiometric ceiling --")
    print("      1.79 mol of ethanol out of 0.5 mol of glucose, which is 3.6x")
    print("      the most that sugar can give;")
    print("    * and the run REPORTS SUCCESS for ~1900 simulated hours before")
    print("      the hard non-negativity guard finally refuses.")
    print()
    v = flask([ReactionTemplate(name=t0.name, smarts=t0.smarts, A=t0.A,
                                Ea=t0.Ea, phase=t0.phase, orders=(0.0,))],
              t=1500.0 * 3600.0)
    print("  THE ONE WITNESS, AND READ WHAT IT CALLS 0.4 MOL:")
    print("   ", v.conservation_report() or "(nothing reported)")
    print()
    print("  So the guard IS load-bearing -- it sees every mole -- but its own")
    print("  wording says 'round-off it could not settle' about four tenths of")
    print("  a mole of manufactured sugar. A caller who does not read it sees a")
    print("  successful run and an impossible yield. **`conservation_report` is")
    print("  the check, and its label is calibrated for the round-off case it")
    print("  was written for.**")
    print()
    print("  M10 stays OPEN and its cheap door is measured shut: a saturating")
    print("  form needs the denominator after all, or the kernel needs the")
    print("  availability gate the solid block already has.")


def panel6():
    rule("PANEL 6 -- A SEALED FERMENTER IS A PRESSURE VESSEL")
    print("     k_vent      t/h    P/bar    glucose   acetone   conv%")
    for k_vent in (0.0, 1.0e-3):
        for hours in (24.0, 96.0):
            v = flask(fermentation_chemistry(), t=hours * 3600.0,
                      k_vent=k_vent)
            st = v.state()
            g = st.total(GLUCOSE)
            print(f"     {k_vent:8.1e} {hours:6.1f} {v.pressure:8.3f} "
                  f"{g:10.5f} {st.total(ACETONE):9.5f} "
                  f"{100 * (GLU_CHARGE - g) / GLU_CHARGE:7.2f}")
    print()
    print("  Two of the three branches make CO2 and one makes four H2 as well,")
    print("  so the headspace IS the product. 24.7 bar out of half a mole of")
    print("  sugar, and nothing was told to do that. A real fermenter vents;")
    print("  give the vessel a k_vent unless the pressure is the point.")
    print("  NOTE the conversion barely moves: no branch is reversible, so the")
    print("  pressure cannot push back on the chemistry. It is a hazard, not a")
    print("  ceiling -- unlike the vanillin digester, where the 30 bar of")
    print("  steam is what makes the route go at all.")


def panel7():
    rule("PANEL 7 -- THE HOMOLACTIC BRANCH, AND THE STEREOCENTRE IT MAKES")
    plain = ("[OX2H:1][CH2:2][CH:3]1[OX2:4][CH:5]([OX2H:6])[CH:7]([OX2H:8])"
             "[CH:9]([OX2H:10])[CH:11]1[OX2H:12]"
             ">>[CH3:5][CH1:7]([OH:8])[CH0:9](=[O:10])[OH:6]"
             ".[CH3:2][CH1:3]([OH:4])[CH0:11](=[O:12])[OH:1]")
    for label, sma in (("chirality UNSPECIFIED in the pattern", plain),
                       ("chirality [@,@@] in the pattern",
                        homolactic_fermentation().smarts)):
        rxn = AllChem.ReactionFromSmarts(sma)
        rxn.Initialize()
        outs = rxn.RunReactants((Chem.MolFromSmiles(GLUCOSE),))
        got = []
        for p in outs[0]:
            Chem.SanitizeMol(p)
            got.append(Chem.MolToSmiles(p))
        print(f"  {label:38s} -> {' + '.join(got)}")
    print()
    print("  RDKit inherits an unspecified chirality and REMOVES one that the")
    print("  reactant pattern specifies and the product pattern does not. So")
    print("  the plain pattern makes one L-lactic acid and one D- out of the")
    print("  same sugar -- two species where the corpus has one, and where no")
    print("  estimator here can tell them apart. `[@,@@]` matches either")
    print("  configuration and suppresses both. That is C3's isoeugenol")
    print("  decision reached through a stereocentre.")


def panel8():
    rule("PANEL 8 -- AND THE PRICE OF SPELLING A STEREOCENTRE, ACROSS THE "
         "WHOLE CORPUS")
    print("  lactic acid, two spellings of one compound, WITH THE FALLBACK")
    print("  SWITCHED OFF -- which is what every session before C7 saw:")
    print("     spelling                  Hf(gas)     Gf(gas)      Tb    "
          "source")
    for label, smi in (("corpus  C[C@H](O)C(=O)O", LACTIC_L),
                       ("flat    CC(O)C(=O)O   ", LACTIC_FLAT)):
        d = THERMO_EXACT.get(smi)
        tb = f"{d.Tb:7.1f}" if d.Tb else "      -"
        print(f"     {label:24s} {d.Hf:9.2f}  {d.Gf:10.2f} {tb}  "
              f"{d.source[:30]}")
    print()
    print("  107 K apart in Tb, and off DIFFERENT TIERS. The tables are keyed")
    print("  by canonical SMILES and a stereocentre changes the key, so a")
    print("  corpus row spelled with stereochemistry can silently miss its own")
    print("  measured record. So: how many corpus compounds is that?")
    print()
    path = os.path.join(_ROOT, "data", "catalog", "compounds")
    total = stereo = moved = 0
    stereo_better = flat_better = 0
    examples = []

    phys_moved = form_moved = 0

    def tier(text):
        """0 measured / experimental, 1 estimated off a real input, 2 the
        weakest estimator. Applied to whichever HALF's provenance moved."""
        t = (text or "").lower()
        if "joback" in t:
            return 2
        if any(k in t for k in ("experimental", "curated", "measured",
                                "yaws", "crc", "common_chemistry", "atct")):
            return 0
        return 1

    def form_half(d):
        """The formation half's provenance, cut out of the composite string."""
        s = d.source
        return s.split("; physical half:")[0]

    for fn in sorted(os.listdir(path)):
        if not fn.endswith(".psv"):
            continue
        with open(os.path.join(path, fn), encoding="utf-8") as fh:
            for row in csv.reader(fh, delimiter="|"):
                if not row or row[0].strip().startswith("#") or len(row) < 3:
                    continue
                smi = row[2].strip()
                if "@" not in smi:
                    continue
                total += 1
                try:
                    mol = Molecule.from_smiles(smi)
                except Exception:                             # noqa: BLE001
                    continue
                flat = Chem.MolToSmiles(Chem.MolFromSmiles(
                    Chem.MolToSmiles(Chem.MolFromSmiles(mol.smiles),
                                     isomericSmiles=False)))
                if flat == mol.smiles:
                    continue
                stereo += 1
                try:
                    a = THERMO_EXACT.get(mol.smiles)
                except Exception:                             # noqa: BLE001
                    a = None
                try:
                    b = THERMO_EXACT.get(_c(flat))
                except Exception:                             # noqa: BLE001
                    b = None
                if a is None or b is None:
                    if (a is None) != (b is None):
                        moved += 1
                        examples.append((row[0].strip(), "one is REFUSED",
                                         "-", "-"))
                    continue
                if a.source != b.source:
                    moved += 1
                    fa, fb = form_half(a), form_half(b)
                    pa, pb = a.physical_source, b.physical_source
                    which = []
                    if fa != fb:
                        form_moved += 1
                        which.append("formation")
                    if pa != pb:
                        phys_moved += 1
                        which.append("physical")
                    ta = min(tier(fa), tier(pa))
                    tb_ = min(tier(fb), tier(pb))
                    if tier(fa) != tier(fb):
                        ta, tb_ = tier(fa), tier(fb)
                    elif tier(pa) != tier(pb):
                        ta, tb_ = tier(pa), tier(pb)
                    if ta < tb_:
                        stereo_better += 1
                        verdict = "stereo WINS"
                    elif tb_ < ta:
                        flat_better += 1
                        verdict = "FLAT WINS  "
                    else:
                        verdict = "same tier  "
                    if len(examples) < 13 or verdict == "FLAT WINS  ":
                        examples.append((
                            row[0].strip(), verdict, "+".join(which),
                            f"{(a.Tb or 0) - (b.Tb or 0):+7.1f}"))
    print(f"  corpus rows whose SMILES carries a stereo marker   {total:5d}")
    print(f"  ... and whose canonical form differs when flat     {stereo:5d}")
    print(f"  ... and which PRICE OFF A DIFFERENT SOURCE flat    {moved:5d}")
    print(f"        the PHYSICAL half is what moved                "
          f"{phys_moved:5d}")
    print(f"        the FORMATION half is what moved               "
          f"{form_moved:5d}")
    print(f"        of those, the STEREO spelling prices better    "
          f"{stereo_better:5d}")
    print(f"        of those, the FLAT spelling prices better      "
          f"{flat_better:5d}")
    print()
    if examples:
        print("     compound                 which wins   which half     "
              "     dTb")
        for name, verdict, half, dtb in examples[:17]:
            print(f"     {name:24s} {verdict}  {half:18s} {dtb}")
    print()
    print("  AND THE TWO HALVES OF A RECORD ARE KEYED THE OPPOSITE WAY ROUND,")
    print("  WHICH IS THE FINDING. A ThermoData is assembled from two")
    print("  independently-resolved halves, and with respect to")
    print("  stereochemistry they disagree:")
    print("    * the PHYSICAL tables carry the chiral spelling. Sorbitol's")
    print("      chiral form reaches a measured Tb (YAWS, 704.0 K); flatten it")
    print("      and it falls to Joback at 888.2 K, 184 K away. 29 of the 31")
    print("      rows are that shape.")
    print("    * the FORMATION table carries the FLAT spelling. Lactic acid's")
    print("      flat form reaches an experimental formation record; the")
    print("      corpus's chiral one misses it and falls to Benson.")
    print("  So the spelling SELECTS THE DATA TIER, in whichever direction the")
    print("  half in question happens to be keyed -- and a spelling carries no")
    print("  thermochemical information at all, because no estimator here")
    print("  tells one enantiomer from another (S7, and panel 7).")
    print()
    print("  CLOSED BY C7, AND THE NUMBER ABOVE IS WHAT IT CLOSED. The fix is")
    print("  the stereo-insensitive FALLBACK this panel called for (S6's rule")
    print("  -- a fallback, never an override), in the provider lookup. The")
    print("  same two spellings, off the LIVE provider:")
    print()
    print("     spelling                  Hf(gas)     Gf(gas)      Tb    "
          "source")
    for label, smi in (("corpus  C[C@H](O)C(=O)O", LACTIC_L),
                       ("flat    CC(O)C(=O)O   ", LACTIC_FLAT)):
        d = THERMO.get(smi)
        tb = f"{d.Tb:7.1f}" if d.Tb else "      -"
        print(f"     {label:24s} {d.Hf:9.2f}  {d.Gf:10.2f} {tb}  "
              f"{d.source[:30]}")
    print()
    print("  Two corrections this panel earned by being re-run, both in")
    print("  validation/stereo_keying.py:")
    print("    * the count above is 31 because the row filter is '@' in the")
    print("      SMILES, which is TETRAHEDRAL stereochemistry only. Counting")
    print("      E/Z as well makes it 49.")
    print("    * 'the two halves are keyed the opposite way round' is TWO of")
    print("      those 49. The real shape is ONE table against all the others:")
    print("      the only table with stereochemistry in its keys is the")
    print("      GENERATED one, which inherited the corpus's spelling.")


def main() -> None:
    panel1()
    panel2()
    panel3()
    panel4()
    panel5()
    panel6()
    panel7()
    panel8()
    print()
    print("=" * 74)
    print("DONE. Panels 1, 4, 5 and 8 are the session's findings.")
    print("=" * 74)


if __name__ == "__main__":
    main()
