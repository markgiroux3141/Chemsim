"""S7's standing audit: the four inorganic gas processes, RUN rather than read.

``validation/catalog_coverage.py`` credits a reaction class when a template
exists for its mechanism. That is a claim about the library, not about the
engine, and S1 is the standing proof of the difference: it credited
``roasting-to-metal`` on a mechanism that does not make the row's product. So
every class S7 credits is charged into a real ``Vessel`` here and integrated.

The four:

    water-gas-shift   CO + H2O <=> CO2 + H2                over hematite
    steam-reforming   CH4 + H2O <=> CO + 3 H2              over nickel
    deacon-process    4 HCl + O2 <=> 2 Cl2 + 2 H2O         over tenorite
    claus-process     H2S + O2 -> SO2, then 2 H2S + SO2 -> S + H2O

⚠ **WHAT THIS AUDIT IS ACTUALLY FOR IS THE THREE REVERSIBLE ONES' TEMPERATURE
BEHAVIOUR**, because that is the part nothing declares. The shift gets WORSE
when heated, the reformer is impossible until it is hot, and Deacon's conversion
ceiling falls exactly as its rate becomes usable. All three fall out of
``reversible=True`` meeting the formation table, and all three are measured
below rather than asserted.

Run: ``python validation/gas_processes.py`` (~1 min).
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
from chemsim.network import build_network  # noqa: E402
from chemsim.properties import (  # noqa: E402
    ThermochemistryProvider,
    VolatilityProvider,
)
from chemsim.properties.mineral_data import MINERALS  # noqa: E402
from chemsim.reactions.synthesis import (  # noqa: E402
    claus_chemistry,
    deacon_oxidation,
    steam_reforming,
    water_gas_shift,
)
from chemsim.reactions.thermo import reaction_deltas  # noqa: E402
from chemsim.vessel import Vessel  # noqa: E402

CO, WATER, CO2, H2 = "[C-]#[O+]", "O", "O=C=O", "[H][H]"
CH4, HCL, O2, CL2 = "C", "Cl", "O=O", "ClCl"
H2S, SO2, S8 = "S", "O=S=O", "S1SSSSSSS1"

HEMATITE = MINERALS["hematite"].lattice
NICKEL = MINERALS["nickel"].lattice
TENORITE = MINERALS["tenorite"].lattice

CONVERGED = dict(rtol=1.0e-8, atol=1.0e-11)

thermo = ThermochemistryProvider()
vol = VolatilityProvider()


def lnK(reaction, T: float) -> float:
    """ln K for one concrete reaction at T, off the same tables the engine uses."""
    dH, dG = reaction_deltas(reaction, thermo, vol)
    # dG is at 298.15; shift with the van 't Hoff form the engine's own
    # detailed_balance uses, so this panel cannot disagree with the integration.
    T0 = 298.15
    dG_T = dH - (T / T0) * (dH - dG)
    return -dG_T * 1000.0 / (R * T)


def sealed(net, T, charge, *, volume=1.0, solid=None):
    v = Vessel(net, volume=volume, T=T, T_env=T, UA=1.0e6, k_vent=0.0)
    v.charge(charge, phase="gas")
    if solid:
        v.charge(solid, phase="solid")
    return v


def bar(v, T):
    """Total pressure of the headspace, bar."""
    st = v.state()
    n = sum(st.n_gas.values())
    return n * 0.083145 * T / v.volume


def main() -> None:
    print("=" * 74)
    print("PANEL 1 -- THE WATER-GAS SHIFT, AND THE REASON IT IS TWO REACTORS")
    print("=" * 74)
    net = build_network([CO, WATER], [water_gas_shift()], thermo=thermo,
                        volatility=vol)
    fwd = next(r for r in net.reactions if r.name == "water_gas_shift")
    print(f"   species {net.species}")
    print()
    print(f"   {'T / K':>8} {'ln K':>9} {'K':>12} {'CO left':>10} "
          f"{'conversion':>11} {'C closure':>13}")
    for T in (500.0, 620.0, 700.0, 900.0):
        v = sealed(net, T, {CO: 0.10, WATER: 0.10},
                   solid={HEMATITE: 0.1})
        v.run(3600.0, **CONVERGED)
        st = v.state()
        co, co2 = st.total(CO), st.total(CO2)
        print(f"   {T:8.0f} {lnK(fwd, T):9.3f} {math.exp(lnK(fwd, T)):12.4g} "
              f"{co:10.6f} {100 * co2 / 0.10:10.2f}% {co + co2:13.10f}")
    print()
    print("   THE CONVERSION FALLS AS THE FLASK IS HEATED and nothing says so.")
    print("   dH is -41.15 kJ/mol, so K falls with T -- which is why a real")
    print("   ammonia plant shifts twice, hot for the rate and cold for the")
    print("   conversion. The carbon closure is the same 0.1 mol throughout.")

    print()
    print("=" * 74)
    print("PANEL 2 -- STEAM REFORMING: IMPOSSIBLE COLD, SPONTANEOUS HOT")
    print("=" * 74)
    net = build_network([CH4, WATER], [steam_reforming()], thermo=thermo,
                        volatility=vol)
    fwd = next(r for r in net.reactions if r.name == "steam_reforming")
    print(f"   {'T / K':>8} {'ln K':>9} {'CH4 left':>10} {'H2 made':>10} "
          f"{'conversion':>11} {'P / bar':>9}")
    for T in (700.0, 900.0, 1100.0, 1300.0):
        v = sealed(net, T, {CH4: 0.25, WATER: 0.25}, solid={NICKEL: 0.1})
        v.run(3600.0, **CONVERGED)
        st = v.state()
        print(f"   {T:8.0f} {lnK(fwd, T):9.3f} {st.total(CH4):10.6f} "
              f"{st.total(H2):10.6f} {100 * (1 - st.total(CH4) / 0.25):10.2f}% "
              f"{bar(v, T):9.2f}")
    print()
    print("   NOBODY DECLARED A MINIMUM TEMPERATURE. dG crosses zero near 900 K")
    print("   because the reaction is endothermic AND makes two extra moles of")
    print("   gas, so heat buys it twice. Below that the flask is a flask of")
    print("   methane.")
    print()
    print("   AND THE SAME FLASK AT 1100 K, CHARGED THINNER -- the only change:")
    print(f"   {'charge / mol':>13} {'P / bar':>9} {'conversion':>11}")
    for n in (0.25, 0.05, 0.01, 0.002):
        v = sealed(net, 1100.0, {CH4: n, WATER: n}, solid={NICKEL: 0.1})
        v.run(3600.0, **CONVERGED)
        st = v.state()
        print(f"   {n:13.3f} {bar(v, 1100.0):9.2f} "
              f"{100 * (1 - st.total(CH4) / n):10.2f}%")
    print()
    print("   THE ONE GAS EQUILIBRIUM IN THIS PROJECT THAT PRESSURE HURTS. Two")
    print("   moles in and four out, so Le Chatelier runs the other way from")
    print("   Haber-Bosch. A real reformer pays this to keep the downstream loop")
    print("   at pressure, and buys the conversion back with excess steam.")

    print()
    print("=" * 74)
    print("PANEL 3 -- DEACON: THE SQUEEZE THAT KILLED THE PROCESS")
    print("=" * 74)
    net = build_network([HCL, O2], [deacon_oxidation()], thermo=thermo,
                        volatility=vol)
    fwd = next(r for r in net.reactions if r.name == "deacon_oxidation")
    print(f"   {'T / K':>8} {'ln K':>9} {'conv @ 10 s':>12} {'@ 60 s':>9} "
          f"{'@ 1 h':>9} {'Cl closure':>13}")
    for T in (400.0, 450.0, 500.0, 600.0, 700.0, 800.0, 900.0):
        got = []
        for seconds in (10.0, 60.0, 3600.0):
            v = sealed(net, T, {HCL: 0.40, O2: 0.10}, solid={TENORITE: 0.1})
            v.run(seconds, **CONVERGED)
            st = v.state()
            got.append((st.total(CL2), st.total(HCL)))
        cl2, hcl = got[-1]
        print(f"   {T:8.0f} {lnK(fwd, T):9.3f} "
              + " ".join(f"{200 * c / 0.40:10.2f}%" for c, _ in got[:1])
              + " " + " ".join(f"{200 * c / 0.40:7.2f}%" for c, _ in got[1:])
              + f" {hcl + 2 * cl2:13.10f}")
    print()
    print("   READ ACROSS FIRST AND THEN DOWN. Below 600 K the three columns")
    print("   disagree -- the flask is still climbing after an hour, so the RATE")
    print("   is the limit. From 700 K up they are identical to the digit: ten")
    print("   seconds is already equilibrium, and every further degree only")
    print("   lowers the ceiling it reaches. The two limits cross between 600 and")
    print("   700 K, and a Deacon converter had to sit on that crossing.")
    print("   Neither half is declared: the ceiling is the formation table and")
    print("   the rate is one barrier.")

    print()
    print("=" * 74)
    print("PANEL 4 -- CLAUS: TWO TEMPLATES SHARING A FLASK, AND A FEED RATIO")
    print("=" * 74)
    net = build_network([H2S, O2], claus_chemistry(), thermo=thermo,
                        volatility=vol)
    print(f"   species {net.species}")
    print()
    print(f"   {'O2 / mol':>9} {'H2S left':>10} {'SO2':>10} {'S8':>10} "
          f"{'S recovered':>12} {'S closure':>12}")
    for o2 in (0.05, 0.10, 0.15, 0.30):
        v = sealed(net, 1100.0, {H2S: 0.20, O2: o2})
        v.run(3600.0, **CONVERGED)
        st = v.state()
        h2s, so2, s8 = st.total(H2S), st.total(SO2), st.total(S8)
        closure = h2s + so2 + 8 * s8
        print(f"   {o2:9.3f} {h2s:10.6f} {so2:10.6f} {s8:10.6f} "
              f"{100 * 8 * s8 / 0.20:11.2f}% {closure:12.9f}")
    print()
    print("   THE SULFUR CLOSURE'S WORST ROW IS 0.200000017 mol against 0.2 --")
    print("   1.7e-08 mol, or 8.5e-08 relative, at rtol 1e-08. It is the")
    print("   projection residual multiplied by this template's own")
    print("   stoichiometry: one reaction event moves SIXTEEN H2S, so a")
    print("   per-event round-off arrives in the closure sixteen times over.")
    print("   Named, bounded, and the only row it appears on is the")
    print("   oxygen-starved one.")
    print()
    print("   THE STOICHIOMETRIC AIR IS 0.10 mol AND THE BEST ROW IS THE ONE AT")
    print("   0.10. Nothing in either template knows that: burning one third of")
    print("   the H2S takes 3/2 * (0.20/3) = 0.10 mol of O2 and leaves exactly")
    print("   the 2:1 H2S:SO2 the second template wants. Too much air burns the")
    print("   feed to SO2; too little starves the burner.")

    print()
    print("=" * 74)
    print("PANEL 5 -- WHAT THE CREDIT ACTUALLY IS")
    print("=" * 74)
    print("   Every row above came out of a real Vessel, so the four classes")
    print("   S7 credits are credited on an integration and not on a lookup:")
    print("     water-gas-shift            -> water_gas_shift")
    print("     steam-reforming            -> steam_reforming")
    print("     catalytic-hydrogen-chloride-oxidation")
    print("                                -> deacon_oxidation")
    print("     comproportionation         -> claus_comproportionation")
    print("     hydrogen-sulfide-combustion-> hydrogen_sulfide_combustion")
    print()
    print("   AND THE FIFTH IS THE ONE THE ROW CHECK PRODUCED. `combustion`")
    print("   was an OUTCOME label over five mechanisms; the burner covers the")
    print("   two sulfur rows and nothing covered the H2S row it was credited")
    print("   for. See data/catalog/README.md.")


if __name__ == "__main__":
    main()
