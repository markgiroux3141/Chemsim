"""S12's standing audit: the Skraup, whose oxidant turns into one of its reagents.

``validation/catalog_coverage.py`` credits ``skraup-cyclisation`` because a
template exists for it. That is a claim about the library and not about whether
the reaction runs, and for this row it is worth checking twice, because the row
looks wrong until you read it:

    skraup-route 2 | aniline + acrolein + nitrobenzene + sulfuric-acid
                   -> quinoline + aniline + water + sulfuric-acid

Aniline is on BOTH sides. ``corpus_balance``'s ``spurious`` bucket is full of
rows like that where the repeated reagent is really a catalyst -- but here it is
not. The aniline coming out is the NITROBENZENE, reduced. The row is real, and
the balance it needs is the threefold one:

    3 aniline + 3 acrolein + nitrobenzene -> 3 quinoline + aniline + 5 water

⚠ **THE TEMPLATE IS SEVEN SLOTS IN AND NINE OUT** and the multiple is forced:
each ring closure sheds two hydrogens and one nitroarene takes six.

⚠⚠ **AND THE PREPARATION'S OWN ODDITY FALLS OUT OF THE FLASK RATHER THAN OUT OF
A DECLARATION.** A real Skraup makes its acrolein in situ from glycerol and never
charges it, and the usual explanation is that neat acrolein polymerises. Panel 5
gives the other half of the reason, measured: acrolein boils at 314 K and this
reaction runs at 450, so an OPEN flask loses it before it can react. The
yield falls from 1.000 mol of quinoline to 0.017.

Run: ``python validation/skraup.py`` (~10 s).
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

from chemsim.constants import R  # noqa: E402
from chemsim.network import build_network  # noqa: E402
from chemsim.properties import VolatilityProvider  # noqa: E402
from chemsim.properties.electrolyte import electrolyte_provider  # noqa: E402
from chemsim.reactions.synthesis import quinoline_chemistry  # noqa: E402
from chemsim.reactions.thermo import reaction_deltas  # noqa: E402
from chemsim.vessel import Vessel  # noqa: E402

ANILINE = "Nc1ccccc1"
ACROLEIN = "C=CC=O"
NITROBENZENE = "O=[N+]([O-])c1ccccc1"
QUINOLINE = "c1ccc2ncccc2c1"
HYDRONIUM = "[OH3+]"
BISULFATE = "O=S(=O)([O-])O"
WATER = "O"

# p-toluidine: the generality check in panel 7, and the one that shows the
# oxidant's own reduction product going on to react.
TOLUIDINE = "Cc1ccc(N)cc1"

CONVERGED = dict(rtol=1.0e-8, atol=1.0e-11)

VOL = VolatilityProvider()
THERMO = electrolyte_provider(volatility=VOL)

NET = build_network(
    [ANILINE, ACROLEIN, NITROBENZENE, HYDRONIUM, BISULFATE, WATER],
    quinoline_chemistry(),
    thermo=THERMO, volatility=VOL,
)
RXN = next(r for r in NET.reactions if r.name == "skraup_cyclisation")


def run(T: float = 450.0, t: float = 3600.0, *, aniline: float = 3.0,
        acrolein: float = 1.0, nitro: float = 1.0, acid: float = 0.2,
        water: float = 5.0, vent: float = 0.0, net=None):
    """A sealed flask at reflux temperature. ``vent=0`` IS the reflux condenser.

    This project has no reflux head that returns a vapour to the pot, so a
    Skraup at reflux is modelled as a flask nothing leaves. The price of that is
    a real pressure and panel 4 reports it rather than hiding it.
    """
    net = net or NET
    v = Vessel(net, volume=1.0, T=T, T_env=T, UA=1.0e6, k_vent=vent,
               thermo=THERMO, volatility=VOL)
    v.charge({WATER: water}, phase="liquid")
    if acid:
        v.charge({HYDRONIUM: acid, BISULFATE: acid}, phase="liquid")
    charge = {ACROLEIN: acrolein, NITROBENZENE: nitro}
    charge[ANILINE] = aniline
    v.charge(charge, phase="liquid")
    v.run(t, **CONVERGED)
    return v


def read(v, net=None):
    st = v.state()
    return {s: st.total(s) for s in (net or NET).species}


def main() -> None:
    print("=" * 74)
    print("PANEL 1 -- THE ROW HAS ANILINE ON BOTH SIDES AND IT IS NOT SPURIOUS")
    print("=" * 74)
    print("   catalog row:  aniline + acrolein + nitrobenzene + sulfuric-acid")
    print("                   -> quinoline + aniline + water + sulfuric-acid")
    print()
    print("   The aniline on the right is the NITROBENZENE, reduced. Written")
    print("   out at the multiple the electron count forces:")
    print()
    print("      3 x  aniline + acrolein  ->  quinoline + H2O + 2 [H]")
    print("           PhNO2 + 6 [H]       ->  PhNH2 + 2 H2O")
    print("      ---------------------------------------------------------")
    print("      3 aniline + 3 acrolein + PhNO2 -> 3 quinoline + PhNH2 + 5 H2O")
    print()
    print("   what the template actually generated:")
    print(f"      {' + '.join(RXN.reactants)}")
    print(f"        -> {' + '.join(RXN.products)}")
    print(f"      A {RXN.A:.3e}   Ea {RXN.Ea:.0f} J/mol   orders {RXN.orders}")
    print()
    print("   Four aromatic rings in and four out. A balance check alone could")
    print("   not have told us that -- corpus_balance's own last panel says so,")
    print("   and vanillin-lignin is the row next to this one that passes it and")
    print("   is still not the reaction it is written as.")

    print()
    print("=" * 74)
    print("PANEL 2 -- PRICED TWICE, BECAUSE A PHASE LABEL CARRIES A STANDARD STATE")
    print("=" * 74)
    gasH = sum(THERMO.get(s).Hf for s in RXN.products) - sum(
        THERMO.get(s).Hf for s in RXN.reactants)
    gasG = sum(THERMO.get(s).Gf for s in RXN.products) - sum(
        THERMO.get(s).Gf for s in RXN.reactants)
    gasS = (gasH - gasG) / 298.15 * 1000.0
    dH, dG = reaction_deltas(RXN, THERMO, VOL)
    dS = (dH - dG) / 298.15 * 1000.0
    print("   The same reaction, off the same tables, on two standard states:")
    print()
    print(f"   {'basis':>16} {'dH / kJ':>10} {'dG298 / kJ':>12} "
          f"{'dS / J/K':>10}")
    print(f"   {'ideal gas':>16} {gasH:10.2f} {gasG:12.2f} {gasS:10.2f}")
    print(f"   {'pure liquid':>16} {dH:10.2f} {dG:12.2f} {dS:10.2f}")
    print(f"   {'difference':>16} {dH - gasH:10.2f} {dG - gasG:12.2f} "
          f"{dS - gasS:10.2f}")
    print()
    print("   THE SIGN OF dS IS NOT THE SAME ON THE TWO BASES. Seven molecules")
    print("   become nine, so on the ideal-gas basis dS is POSITIVE -- and this")
    print("   template is phase=\"liquid\", so reaction_deltas puts every")
    print("   condensable species on its own pure liquid instead, and NINE")
    print("   product molecules condense against SEVEN reactant ones. That is")
    print("   the whole difference and it is worth ~150 kJ/mol in dH.")
    print("   The gas-basis number is the one that is wrong for this reaction,")
    print("   and it is the one that is easy to compute by hand.")
    print()
    print(f"   {'T / K':>8} {'dG / kJ/mol':>13} {'ln K':>10}")
    for T in (298.15, 400.0, 450.0, 500.0, 600.0):
        dG_T = dH * 1000.0 - T * dS
        print(f"   {T:8.1f} {dG_T / 1000.0:13.2f} {-dG_T / (R * T):10.1f}")
    print()
    print("   Irreversible is still safe, but NOT for the reason the gas basis")
    print("   would have given. dS is negative, so dG gets less negative as the")
    print("   flask is heated -- it just has ~715 kJ/mol to spend doing it, and")
    print(f"   ln K reaches zero at {dH / dS * 1000.0:.0f} K, which no flask here reaches.")
    print("   S11's rule -- count the moles of gas before giving up a reverse --")
    print("   is answered here by there being NO gas on either side of the rate")
    print("   law: this is a liquid-phase reaction and the condensations are")
    print("   what its entropy is about.")

    print()
    print("=" * 74)
    print("PANEL 3 -- IT RUNS, AND THE STOICHIOMETRY IS EXACT")
    print("=" * 74)
    v = run()
    tot = read(v)
    q = tot[QUINOLINE]
    print("   1 L sealed, 450 K, one hour. 3.0 aniline, 1.0 acrolein,")
    print("   1.0 nitrobenzene, 0.2 hydronium as the bisulfate, 5.0 water:")
    print()
    print(f"      quinoline         {q:12.6f} mol")
    print(f"      acrolein left     {tot[ACROLEIN]:12.6f} mol   "
          f"({100 * (1 - tot[ACROLEIN]):6.2f}% converted)")
    print(f"      nitrobenzene      {tot[NITROBENZENE]:12.6f} mol   "
          f"(expect {1.0 - q / 3.0:.6f} = 1 - quinoline/3)")
    print(f"      aniline           {tot[ANILINE]:12.6f} mol   "
          f"(expect {3.0 - 2.0 * q / 3.0:.6f} = 3 - 2*quinoline/3)")
    print(f"      hydronium         {tot[HYDRONIUM]:12.6f} mol   "
          f"(charged 0.200000 -- a constant of the motion)")
    print(f"      water             {tot[WATER]:12.6f} mol   "
          f"(expect {5.0 + 5.0 * q / 3.0:.6f})")
    print(f"      {v.conservation_report() or 'conservation clean'}")

    print()
    print("=" * 74)
    print("PANEL 4 -- THE ACID IS THE GATE, AND THE TEMPERATURE IS THE CLOCK")
    print("=" * 74)
    print("   no acid at all:")
    tot0 = read(run(acid=0.0))
    print(f"      quinoline {tot0[QUINOLINE]:.6e} mol -- twenty orders below")
    print("      the 1 mol the same flask makes WITH acid, which is the")
    print("      correct answer for a Skraup.")
    print()
    print("      NOTE, and S12 got this wrong by one word: it is not EXACTLY")
    print("      zero and it never was going to be. Water autoprotolyses, so")
    print("      the electrolyte provider hands this flask ~4e-29 mol of")
    print("      hydronium and a rate first order in it is small, not absent.")
    print("      S12 read a 0.0 here and wrote 'exactly zero'; that 0.0 was")
    print("      the solver's trajectory clamping a tiny column, and S13's")
    print("      data change moved the trajectory and un-clamped it.")
    print()
    print("   one MINUTE at each temperature, everything else unchanged:")
    print()
    print(f"   {'T / K':>8} {'quinoline':>12} {'converted':>11} {'P / bar':>10}")
    for T in (350.0, 400.0, 420.0, 450.0, 480.0):
        vt = run(T=T, t=60.0)
        tt = read(vt)
        print(f"   {T:8.1f} {tt[QUINOLINE]:12.6f} "
              f"{100 * (1 - tt[ACROLEIN]):10.2f}% {vt.pressure:10.2f}")
    print()
    print("   A real Skraup is refluxed hard and is over in an hour or two; the")
    print("   barrier is fitted to that and nothing else. The pressure column is")
    print("   the price of having no reflux head: a sealed flask at 450 K IS the")
    print("   condenser here, and it is reported rather than hidden.")

    print()
    print("=" * 74)
    print("PANEL 5 -- WHY THE PREPARATION MAKES ITS ACROLEIN IN SITU")
    print("=" * 74)
    print("   The textbook reason is that neat acrolein polymerises. Here is the")
    print("   other half, measured -- acrolein boils at 314 K and the flask is at")
    print("   450, so an OPEN flask simply loses it:")
    print()
    print(f"   {'k_vent':>12} {'quinoline':>12} {'acrolein left':>15}")
    for vent in (0.0, 1.0e-3, 1.0, 1.0e3):
        tv = read(run(vent=vent))
        print(f"   {vent:12.0e} {tv[QUINOLINE]:12.6f} {tv[ACROLEIN]:15.6f}")
    print()
    print("   Nothing declares that. It is the vapour-pressure curve and the")
    print("   vent conductance, and it is the same mechanic that gives the Claus")
    print("   train its sulfur condenser.")

    print()
    print("=" * 74)
    print("PANEL 6 -- THE OXIDANT IS A STOICHIOMETRIC REAGENT, NOT A CATALYST")
    print("=" * 74)
    print("   Three quinolines per nitrobenzene, so starving it caps the yield:")
    print()
    print(f"   {'PhNO2 in':>10} {'quinoline':>12} {'3 x PhNO2':>12} "
          f"{'acrolein left':>15}")
    for nitro in (0.10, 0.20, 0.3333, 1.00):
        tn = read(run(nitro=nitro))
        print(f"   {nitro:10.4f} {tn[QUINOLINE]:12.6f} {3 * nitro:12.6f} "
              f"{tn[ACROLEIN]:15.6f}")
    print()
    print("   Below 1/3 mol the oxidant runs out and the acrolein sits there.")
    print("   That is the reagent an amateur leaves out, and the flask says so.")

    print()
    print("=" * 74)
    print("PANEL 7 -- IT IS A TEMPLATE, SO A SUBSTITUTED ANILINE WORKS TOO")
    print("=" * 74)
    net2 = build_network(
        [TOLUIDINE, ACROLEIN, NITROBENZENE, HYDRONIUM, BISULFATE, WATER],
        quinoline_chemistry(),
        thermo=THERMO, volatility=VOL,
    )
    print(f"   charged p-toluidine instead of aniline: {len(net2.species)} species")
    for s in net2.species:
        print(f"      {s}")
    print()
    v2 = Vessel(net2, volume=1.0, T=450.0, T_env=450.0, UA=1.0e6, k_vent=0.0,
                thermo=THERMO, volatility=VOL)
    v2.charge({WATER: 5.0, HYDRONIUM: 0.2, BISULFATE: 0.2}, phase="liquid")
    v2.charge({TOLUIDINE: 3.0, ACROLEIN: 1.0, NITROBENZENE: 1.0}, phase="liquid")
    v2.run(3600.0, **CONVERGED)
    st2 = v2.state()
    for s in net2.species:
        n = st2.total(s)
        if n > 1.0e-9:
            print(f"      {s:34s} {n:12.6f} mol")
    print()
    print("   6-methylquinoline, which nobody typed. But read the last line")
    print("   again: there is PLAIN QUINOLINE in the flask too, at exactly half")
    print("   the methyl one, and NO free aniline left at all. The nitrobenzene")
    print("   was reduced to aniline and the aniline then went round again as a")
    print("   SUBSTRATE, because the three amine slots do not have to be the same")
    print("   molecule. Total quinolines 1.000000 = the acrolein charged; the")
    print("   split is 2:1 because one event in three has to spend an aniline.")
    print()
    print("   That is a real nuisance of the real preparation -- a Skraup on a")
    print("   substituted aniline with nitrobenzene as the oxidant contaminates")
    print("   its product with the PARENT quinoline -- and nobody declared it.")
    print()
    print(f"   {v2.conservation_report() or 'conservation clean'}")


if __name__ == "__main__":
    main()
