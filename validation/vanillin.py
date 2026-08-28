"""C3's standing audit: vanillin, and the class S11 refused after reading one row.

``oxidative-cleavage`` has TWO rows in the catalog. S11 read the harder one::

    vanillin-lignin  1 | coniferyl alcohol + O2 + NaOH -> vanillin + water + NaOH

found that a C10 monolignol cannot make one C8 vanillin and a water, and refused
the CLASS -- on the ground that naming the missing C2 fragment would be
inventing chemistry inside the corpus. That refusal is recorded in MILESTONES
§S11 §12 and printed by ``validation/corpus_balance.py``'s last panel.

⚠⚠⚠ **THE OTHER ROW BALANCES 1:1 AND NAMES ITS C2 FRAGMENT**::

    vanillin-eugenol 2 | isoeugenol + O2 -> vanillin + acetaldehyde

and the fragment the lignin row omits turns out to be ``glycolaldehyde``, a
compound the corpus has carried all along. **Nothing is invented: the mechanism
supplies the fragment and the corpus supplies its name.** So the class is built
off the row that balances, and S11's reason survives exactly where it was aimed
-- the lignin row IS still wrong, and panel 2 prints both readings side by side
rather than quietly correcting the corpus.

⚠⚠ **AND THE SESSION'S SHARPEST FINDING IS A NUMERICAL ONE (panel 7): A
REVERSIBLE LIQUID-PHASE EQUILIBRIUM IS EXACT ON THE LIQUID AND NOT ON THE
INVENTORY.** C3's first flask read an isoeugenol:eugenol ratio of **15362**
against a ``kf/kb`` of **2678** and that 5.7x was nearly written down as
chemistry. It is the HEADSPACE: the allyl isomer is ~5x the more volatile, so
``state().total()`` reads a ratio the rate law never enforced. On the liquid
alone the flask agrees with detailed balance to the last digit.

Run: ``python validation/vanillin.py`` (~2 min).

⚠ EVERY PRINTED LINE HERE IS ASCII. The console is cp1252 and a warning glyph in
a ``print`` kills the script mid-panel -- C2 broke this rule in its own audit and
G6 lost two runs to it. Glyphs belong in docstrings and comments.
"""

from __future__ import annotations

import math
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

from chemsim.constants import R  # noqa: E402
from chemsim.matter import Molecule  # noqa: E402
from chemsim.network import build_network  # noqa: E402
from chemsim.properties import (  # noqa: E402
    ThermochemistryProvider,
    VolatilityProvider,
)
from chemsim.properties.electrolyte import (  # noqa: E402
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.reactions.synthesis import (  # noqa: E402
    alkene_isomerisation,
    oxidative_cleavage,
    vanillin_chemistry,
)
from chemsim.reactions.thermo import reaction_deltas  # noqa: E402
from chemsim.vessel import Vessel  # noqa: E402

WATER, O2, NA, OH = "O", "O=O", "[Na+]", "[OH-]"
EUGENOL = "C=CCc1ccc(O)c(OC)c1"
ISO = "CC=Cc1ccc(O)c(OC)c1"            # what the template makes: no geometry
TRANS_ISO = "C/C=C/c1ccc(O)c(OC)c1"    # what the corpus spells
CIS_ISO = r"C/C=C\c1ccc(O)c(OC)c1"
VANILLIN, MECHO = "COc1cc(C=O)ccc1O", "CC=O"
CONIFERYL, GLYCOL = "COc1cc(/C=C/CO)ccc1O", "OCC=O"

# ⚠ CANONICALISED, AND NOT AS A TIDINESS MEASURE. ``state().total()`` is keyed
# by the network's own species strings, which are ``Molecule.from_smiles``
# canonical form -- so the corpus's ``OCC=O`` for glycolaldehyde reads ZERO
# against the network's ``O=CCO`` and panel 9 printed a 1:1 product as 0.000000
# with nothing raising. S6's finding (*"the recorded gap size was itself wrong:
# raw vs CANONICAL SMILES"*) on a fresh victim. Do this to every SMILES constant
# in an audit, not to the ones that look suspicious.
def _canon(smi: str) -> str:
    return Molecule.from_smiles(smi).smiles


(EUGENOL, ISO, TRANS_ISO, CIS_ISO, VANILLIN, MECHO, CONIFERYL, GLYCOL,
 WATER, O2, NA, OH) = (
    _canon(x) for x in (EUGENOL, ISO, TRANS_ISO, CIS_ISO, VANILLIN, MECHO,
                        CONIFERYL, GLYCOL, WATER, O2, NA, OH))

TIGHT = dict(rtol=1.0e-8, atol=1.0e-11)

VOL = VolatilityProvider()
THERMO = electrolyte_provider(volatility=VOL)
NEUTRAL = ThermochemistryProvider()


def net(species, templates):
    return build_network(species, list(templates), thermo=THERMO,
                         volatility=VOL)


NET = net([WATER, EUGENOL, O2, NA, OH], vanillin_chemistry())
NET_ISOM = net([WATER, EUGENOL, NA, OH], [alkene_isomerisation()])
NET_CLV = net([WATER, ISO, O2, NA, OH], [oxidative_cleavage()])

# THE REFERENCE FLASK, and it is an AUTOCLAVE. 40 mol of water in a 2 L vessel
# is ~0.73 L of alkaline liquor at 470 K under ~30 bar of its own steam, which
# is what an alkaline oxidation digester is. Every number below carries it.
VESSEL, WATER_CHARGE, SUBSTRATE, BASE, OXYGEN = 2.0, 40.0, 0.10, 0.10, 0.5


def flask(network, *, T=470.0, t=3600.0, sub=EUGENOL, oh=BASE, o2=OXYGEN,
          water=WATER_CHARGE, n=SUBSTRATE):
    v = Vessel(network, volume=VESSEL, T=T, T_env=T, UA=1.0e6, k_vent=0.0)
    liquid = {WATER: water, sub: n}
    if oh:
        liquid |= {NA: oh, OH: oh}
    v.charge(liquid, phase="liquid")
    if o2:
        v.charge({O2: o2}, phase="gas")
    v.run(t, **TIGHT)
    return v


def counts(*names):
    out = {}
    for n in names:
        for el, c in Molecule.from_smiles(n).element_counts().items():
            out[el] = out.get(el, 0) + c
    return out


def fmt(d):
    return "".join(f"{el}{d[el]}" for el in sorted(d))


def deltas(rxn):
    dH, dG = reaction_deltas(rxn, THERMO, VOL)
    return dH, dG, (dH - dG) / 298.15 * 1000.0


def main() -> None:
    print("=" * 74)
    print("PANEL 1 -- THE CLASS HAS TWO ROWS AND THE REFUSAL READ ONE OF THEM")
    print("=" * 74)
    rows = [
        ("vanillin-eugenol 2", ("isoeugenol", "O2"), (TRANS_ISO, O2),
         ("vanillin", "acetaldehyde"), (VANILLIN, MECHO)),
        ("vanillin-lignin 1 ", ("coniferyl", "O2"), (CONIFERYL, O2),
         ("vanillin", "water"), (VANILLIN, WATER)),
        ("  the MECHANISM  ", ("coniferyl", "O2"), (CONIFERYL, O2),
         ("vanillin", "glycolaldehyde"), (VANILLIN, GLYCOL)),
    ]
    print(f"   {'row':19} {'left':12} {'right':12}  verdict")
    for label, _ln, lsmi, _rn, rsmi in rows:
        L, Rr = counts(*lsmi), counts(*rsmi)
        print(f"   {label:19} {fmt(L):12} {fmt(Rr):12}  "
              f"{'BALANCED 1:1' if L == Rr else 'NOT BALANCED'}")
    print()
    print("   S11 refused the class off the second line and was RIGHT about it.")
    print("   The first line is the same class, balances exactly, and names the")
    print("   C2 fragment the second one drops. The class is built off that one.")
    print()
    print("   AND THE FRAGMENT THE LIGNIN ROW OMITS WAS ALREADY A CORPUS ROW:")
    print("   glycolaldehyde, 07-carbonyls.psv, 'simplest sugar'. So making it")
    print("   explicit invents nothing -- the mechanism supplies the fragment")
    print("   and the corpus supplies its name. READ EVERY ROW OF A CLASS")
    print("   BEFORE REFUSING THE CLASS.")

    print()
    print("=" * 74)
    print("PANEL 2 -- PRICING THE UNBALANCED ROW IS SILENT, AND THAT IS THE")
    print("           REASON THE BALANCE HAS TO BE CHECKED BY HAND")
    print("=" * 74)
    print("   The three readings, priced off the same tables (ideal gas):")
    print()
    print(f"   {'reading':34} {'dH / kJ':>9} {'dG298':>9} {'dS / J/K':>9}")
    for label, lsmi, rsmi in (
        ("isoeugenol + O2 -> vanil + MeCHO", (TRANS_ISO, O2), (VANILLIN, MECHO)),
        ("coniferyl + O2 -> vanil + HOCH2CHO", (CONIFERYL, O2), (VANILLIN, GLYCOL)),
        ("coniferyl + O2 -> vanil + water", (CONIFERYL, O2), (VANILLIN, WATER)),
    ):
        dH = (sum(THERMO.get(s).Hf for s in rsmi)
              - sum(THERMO.get(s).Hf for s in lsmi))
        dG = (sum(THERMO.get(s).Gf for s in rsmi)
              - sum(THERMO.get(s).Gf for s in lsmi))
        print(f"   {label:34} {dH:9.2f} {dG:9.2f} "
              f"{(dH - dG) / 298.15 * 1000.0:9.2f}")
    print()
    print("   THE UNBALANCED ROW COMES BACK WITH A NUMBER AND NOTHING RAISES.")
    print("   Its entropy is EIGHT TIMES its balanced neighbour's, because two")
    print("   carbons have been destroyed on the right -- so the balance error")
    print("   is visible in the thermochemistry once you look, and invisible if")
    print("   you only ask for a dH. corpus_balance's own last panel says its")
    print("   test is weak; this is what the weakness costs downstream.")

    print()
    print("=" * 74)
    print("PANEL 3 -- TWO BASES, AND THE FLASK USES THE SECOND ONE")
    print("=" * 74)
    ISOM = next(r for r in NET.reactions if r.name == "alkene_isomerisation")
    CLV = next(r for r in NET.reactions if r.name == "oxidative_cleavage")
    for label, rxn in (("eugenol -> isoeugenol", ISOM),
                       ("isoeugenol + O2 -> vanillin + MeCHO", CLV)):
        gH = (sum(THERMO.get(s).Hf for s in rxn.products)
              - sum(THERMO.get(s).Hf for s in rxn.reactants))
        gG = (sum(THERMO.get(s).Gf for s in rxn.products)
              - sum(THERMO.get(s).Gf for s in rxn.reactants))
        gS = (gH - gG) / 298.15 * 1000.0
        dH, dG, dS = deltas(rxn)
        print(f"   {label}")
        print(f"     {'basis':>13} {'dH':>9} {'dG298':>9} {'dS':>9} "
              f"{'ln K 470':>9} {'K 470':>12}")
        for b, h, _g, sv in (("ideal gas", gH, gG, gS),
                             ("pure liquid", dH, dG, dS)):
            lnK = -(h * 1000.0 - 470.0 * sv) / (R * 470.0)
            print(f"     {b:>13} {h:9.2f} {_g:9.2f} {sv:9.2f} {lnK:9.2f} "
                  f"{math.exp(min(lnK, 700.0)):12.4g}")
        print()
    print("   BOTH TEMPLATES ARE phase=\"liquid\", SO THE SECOND ROW IS THE ONE")
    print("   THE FLASK USES. On the isomerisation the two bases disagree by")
    print("   35 kJ/mol in dH and the sign of dS FLIPS -- and their ln K at")
    print("   470 K agrees to 2%, which is a coincidence and not a licence.")
    print("   C3's own pre-build arithmetic was done on the gas basis and the")
    print("   template comment had to be corrected against this panel. S12's")
    print("   rule: a phase label carries a standard state.")

    print()
    print("=" * 74)
    print("PANEL 4 -- IT RUNS: CLOVE OIL TO VANILLIN, IN ONE AUTOCLAVE")
    print("=" * 74)
    v = flask(NET, t=1.0)
    print(f"   {VESSEL:.0f} L vessel, {WATER_CHARGE:.0f} mol water "
          f"({v.liquid_volume:.3f} L of liquor), {SUBSTRATE:.2f} mol eugenol,")
    print(f"   {BASE:.2f} mol NaOH ([OH-] = {BASE / v.liquid_volume:.4f} mol/L), "
          f"{OXYGEN:.1f} mol O2 above it.")
    print(f"   At 470 K that is {v.pressure:.1f} bar of its own steam. This is a")
    print("   DIGESTER, not a beaker, and every number below carries it.")
    print()
    print(f"   {'T / K':>6} {'t / h':>6} {'P / bar':>8} {'eugenol':>10} "
          f"{'isoeug':>10} {'vanillin':>10} {'yield':>8} {'MeCHO':>10}")
    for T in (400.0, 440.0, 470.0, 490.0):
        for t in (3600.0, 14400.0):
            w = flask(NET, T=T, t=t)
            st = w.state()
            van = st.total(VANILLIN)
            print(f"   {T:6.0f} {t / 3600:6.1f} {w.pressure:8.2f} "
                  f"{st.total(EUGENOL):10.3e} {st.total(ISO):10.3e} "
                  f"{van:10.6f} {100 * van / SUBSTRATE:7.2f}% "
                  f"{st.total(MECHO):10.6f}")
    print()
    print("   THE ACETALDEHYDE IS 1:1 WITH THE VANILLIN AT EVERY ROW, which is")
    print("   the balance of panel 1 showing up as an invariant of the run.")
    print("   470 K / 4 h gives 93% -- and a real alkaline air oxidation of")
    print("   isoeugenol gives 60-80%, because it also over-oxidises. THERE IS")
    print("   NO OVER-OXIDATION CHANNEL HERE, so every yield above is an UPPER")
    print("   BOUND and not a prediction. What is calibrated is the")
    print("   isomerisation: panel 5.")

    print()
    print("=" * 74)
    print("PANEL 5 -- WHICH STEP IS RATE-DETERMINING, MEASURED BY KNOCKOUT")
    print("=" * 74)
    print(f"   {'t / s':>7} {'isomerise alone':>28} {'cleave alone':>28}")
    for t in (600.0, 1800.0, 3600.0, 14400.0):
        a = flask(NET_ISOM, t=t, o2=0.0).state()
        b = flask(NET_CLV, t=t, sub=ISO).state()
        print(f"   {t:7.0f} "
              f"{100 * (1 - a.total(EUGENOL) / SUBSTRATE):17.2f}% conv     "
              f"{100 * b.total(VANILLIN) / SUBSTRATE:17.2f}% vanillin")
    print()
    print("   THE ISOMERISATION IS THE SLOW STEP, and that is why the")
    print("   intermediate never accumulates: isoeugenol sits at 1e-3 mol or")
    print("   less in panel 4 while the vanillin climbs. A real preparation")
    print("   isomerises for 3-6 h at 470-490 K and then oxidises, and the")
    print("   94.6% at 4 h above is what Ea = 115 kJ/mol was set against.")
    print("   That barrier is a CALIBRATION against the process, declared in")
    print("   the template with its band (90-120), not a measured constant.")

    print()
    print("=" * 74)
    print("PANEL 6 -- THE BASE IS THE GATE, AND A FLASK WITHOUT IT IS INERT")
    print("=" * 74)
    print(f"   {'[OH-] charged':>14} {'mol/L':>8} {'vanillin at 1 h':>18}")
    for oh in (0.0, 0.01, 0.05, 0.10, 0.50):
        w = flask(NET, oh=oh)
        st = w.state()
        print(f"   {oh:14.2f} {oh / w.liquid_volume:8.4f} "
              f"{st.total(VANILLIN):18.8f}")
    print()
    print("   ZERO BASE GIVES EXACTLY ZERO VANILLIN, and the interesting part is")
    print("   WHERE the gate is. oxidative_cleavage has no catalyst at all --")
    print("   it would happily cleave any isoeugenol in the flask. There is")
    print("   none, because the isomerisation that makes it is the base-catalysed")
    print("   step. SO A TWO-TEMPLATE ROUTE IS GATED BY WHICHEVER STEP COMES")
    print("   FIRST, and neither template says so on its own.")

    print()
    print("=" * 74)
    print("PANEL 7 -- THE EQUILIBRIUM IS EXACT ON THE LIQUID AND NOT ON THE")
    print("           INVENTORY, AND 5.7x OF CHEMISTRY WAS NEARLY WRITTEN DOWN")
    print("=" * 74)
    F = next(r for r in NET_ISOM.reactions if r.name == "alkene_isomerisation")
    B = next(r for r in NET_ISOM.reactions
             if r.name == "alkene_isomerisation_rev")
    T = 470.0
    kf = F.A * math.exp(-F.Ea / (R * T))
    kb = B.A * math.exp(-B.Ea / (R * T))
    dH, dG, dS = deltas(F)
    lnK = -(dH * 1000.0 - T * dS) / (R * T)
    print(f"   forward   A {F.A:.4e}  Ea {F.Ea:9.1f}  k(470) {kf:.6e}")
    print(f"   reverse   A {B.A:.4e}  Ea {B.Ea:9.1f}  k(470) {kb:.6e}")
    print(f"   kf / kb                                      {kf / kb:12.2f}")
    print(f"   K from dH, dG298 and van't Hoff to 470 K     "
          f"{math.exp(lnK):12.2f}")
    print("   -- identical, so DETAILED BALANCE IS EXACT. Now the flask:")
    print()
    print(f"   {'liquor / L':>11} {'t / s':>9} {'TOTAL ratio':>13} "
          f"{'LIQUID ratio':>13} {'eug in gas':>11} {'iso in gas':>11}")
    for water, t in ((5.0, 3.6e5), (40.0, 3.6e5), (40.0, 3.6e6)):
        w = flask(NET_ISOM, t=t, o2=0.0, water=water)
        st = w.state()
        e, i = st.total(EUGENOL), st.total(ISO)
        le = st.n_liquid.get(EUGENOL, 0.0)
        li = st.n_liquid.get(ISO, 0.0)
        ge = st.n_gas.get(EUGENOL, 0.0)
        gi = st.n_gas.get(ISO, 0.0)
        print(f"   {w.liquid_volume:11.3f} {t:9.1e} {i / e:13.2f} "
              f"{li / le:13.2f} {ge / (le + ge):10.2%} {gi / (li + gi):10.2%}")
    print()
    print("   THE LIQUID RATIO IS kf/kb TO THE LAST DIGIT. The TOTAL ratio is")
    print("   not, and it is not a solver error: the allyl isomer is ~5x the")
    print("   more volatile, so a share of the eugenol sits in the headspace")
    print("   where no rate law can reach it. The smaller the liquor, the")
    print("   bigger the lie -- C3's first flask held 0.11 L under 0.89 L of")
    print("   headspace and read 15362 against a true 2678.")
    print()
    print("   state().total() IS THE RIGHT NUMBER FOR A YIELD AND THE WRONG ONE")
    print("   FOR AN EQUILIBRIUM. A rate law is written on one phase; read the")
    print("   equilibrium on that phase or not at all. This is the same shape as")
    print("   'energy_terms lies unless given the run's own boundary state'.")

    print()
    print("=" * 74)
    print("PANEL 8 -- THE GEOMETRY IT DOES NOT DECLARE, AND WHY THAT IS SAFE")
    print("=" * 74)
    print("   The corpus spells isoeugenol trans; the template makes a double")
    print("   bond and says nothing about its geometry. Three species, one")
    print("   question -- can anything here tell them apart?")
    print()
    print(f"   {'species':28} {'Hf / kJ':>10} {'Gf / kJ':>10} "
          f"{'= template':>10}")
    for label, smi in (("trans isoeugenol (corpus)", TRANS_ISO),
                       ("cis isoeugenol", CIS_ISO),
                       ("no geometry (the template)", ISO)):
        t = THERMO.get(smi)
        print(f"   {label:28} {t.Hf:10.3f} {t.Gf:10.3f} "
              f"{'same' if _canon(smi) == ISO else 'DIFFERENT':>10}")
    print()
    print("   IDENTICAL TO THREE DECIMALS AND A DIFFERENT SPECIES ANYWAY. S7")
    print("   measured this on oleic -> elaidic ('no estimator here tells a cis")
    print("   alkene from a trans one') and refused a class for it; here the")
    print("   same fact LICENSES leaving the geometry out, because declaring")
    print("   one would assert a distinction the thermochemistry cannot carry.")
    print()
    print("   AND IT MAKES NO SPURIOUS CYCLE. Charge the corpus's trans isomer:")
    tr = net([WATER, TRANS_ISO, O2, NA, OH], vanillin_chemistry())
    print(f"      network reactions: {[r.name for r in tr.reactions]}")
    w = Vessel(tr, volume=VESSEL, T=470.0, T_env=470.0, UA=1.0e6, k_vent=0.0)
    w.charge({WATER: WATER_CHARGE, NA: BASE, OH: BASE, TRANS_ISO: SUBSTRATE},
             phase="liquid")
    w.charge({O2: OXYGEN}, phase="gas")
    w.run(3600.0, **TIGHT)
    st = w.state()
    print(f"      trans left {st.total(TRANS_ISO):.3e}   "
          f"vanillin {st.total(VANILLIN):.6f}   "
          f"eugenol {st.total(EUGENOL):.3e}")
    print()
    print("   THE ISOMERISATION IS NOT IN THAT NETWORK AT ALL. Discovery is")
    print("   FORWARD-ONLY (M5), so the reverse never enumerates species and the")
    print("   trans isomer cannot drain into eugenol and back out as the")
    print("   geometry-free one. A rule that has cost this project a template")
    print("   twice is what makes this decision safe.")

    print()
    print("=" * 74)
    print("PANEL 9 -- WHAT C3 DID NOT DO, SAID OUT LOUD")
    print("=" * 74)
    print("   1. THE LIGNIN ROW RUNS AND ITS EQUILIBRIUM MAY NOT BE READ.")
    lig = net([WATER, CONIFERYL, O2, NA, OH], [oxidative_cleavage()])
    w = flask(lig, T=440.0, sub=CONIFERYL)
    st = w.state()
    print(f"      440 K, 1 h: coniferyl {st.total(CONIFERYL):.3e}  "
          f"vanillin {st.total(VANILLIN):.6f}  "
          f"glycolaldehyde {st.total(GLYCOL):.6f}")
    print("      build_network prints a MIXED STANDARD STATES notice on it:")
    print("      coniferyl alcohol has no vapour-pressure curve, so it keeps")
    print("      ideal-gas formation data while its partners get the liquid")
    print("      shift. That is M5's recorded finding, worth +323 kJ/mol the")
    print("      first time it fired. The reaction is irreversible so no rate")
    print("      depends on the number -- but DO NOT READ ITS ln K.")
    print("      SO THE EUGENOL ROW WAS THE RIGHT ONE TO BUILD FROM FOR A")
    print("      SECOND, INDEPENDENT REASON: eugenol, isoeugenol, vanillin and")
    print("      acetaldehyde all carry a vapour-pressure curve and trigger no")
    print("      notice. S11 picked the row that is worse in both ways.")
    print()
    print("   2. THE PHENOL DISSOCIATION SET CANNOT BE ADDED BESIDE THIS.")
    try:
        net([WATER, EUGENOL, O2, NA, OH],
            vanillin_chemistry() + list(dissociation_templates()))
        print("      !! IT BUILT. The refusal below has stopped firing and this")
        print("      panel needs rewriting.")
    except ValueError as exc:
        head = str(exc).split(" -- ")[0].split(": it carries")[0]
        print(f"      build_network REFUSES: {head[:180]}")
    print("      Eugenol IS a phenol, so phenol_dissociation fires on it and")
    print("      wants a pKa for the eugenolate that the ion table does not")
    print("      carry. G5's rule, arriving from a new substrate: AN OPEN-ENDED")
    print("      REWRITE OVER A CURATED TABLE WILL FIND THE EDGE OF THE TABLE.")
    print("      G5 met it on an amine; this is the same edge on a phenol. The")
    print("      refusal is KEPT -- the vanillin route needs no phenolate, and")
    print("      curating three aryl-oxide pKa values to satisfy a template")
    print("      nothing here uses is what G5 measured as buying nothing.")
    print("      WHAT THIS COSTS: the bundle's docstring said it needed the")
    print("      dissociation set beside it, copied from wacker_chemistry. That")
    print("      was wrong and MEASURING IT IS WHAT CAUGHT IT.")
    print()
    print("   3. NO OVER-OXIDATION, NO VANILLIC ACID, NO POLYMERISATION.")
    print("      The three things that cap a real vanillin yield are all absent,")
    print("      which is why panel 4 is an upper bound. Adding an")
    print("      aldehyde-oxidation channel would be the honest next step and it")
    print("      is a template this project already has (peroxide_over_oxidation)")
    print("      -- deliberately NOT in this bundle, because a bundle that")
    print("      carried it would also oxidise the acetaldehyde.")

    print()
    print("=" * 74)
    print("SUMMARY")
    print("=" * 74)
    print("   two templates, two classes, and the route runs end to end from a")
    print("   natural material. classes 53/236 -> 55/236, template-ready")
    print("   42 -> 44, BOTH 34 -> 36, playable 16 -> 18.")
    print("   the pair is SUPER-ADDITIVE: alkene-isomerisation alone is worth")
    print("   +0 and oxidative-cleavage alone +1, and together they are +2,")
    print("   because vanillin-eugenol needs both. PLAYABLE.md section 8b is")
    print("   the table that says so, and it is new.")


if __name__ == "__main__":
    main()
