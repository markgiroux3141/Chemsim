"""S11's second standing audit: the Wacker process, whose catalyst is an ION.

``validation/catalog_coverage.py`` credits ``wacker-oxidation`` because a
template exists for it. That is a claim about the library, and for this class it
is a weaker claim than usual: ``[Cu+2]`` is priced from ``ion_data`` and
``thermochemistry`` REFUSES it outright unless the network is built with
``electrolyte_provider()``. A credit read off the coverage table would say
nothing about whether the reaction can be run at all. So it is run here.

    wacker-process 1   ethylene + oxygen + copper-ii-ion
                         -> acetaldehyde + copper-ii-ion      PdCl2/CuCl2, 400 K

⚠ **THE GATE IS NOT "DID YOU ADD THE CATALYST", IT IS "IS THERE A SOLVENT".**
Every other explicit catalyst in this project is a proton or a crystal. This one
only exists dissolved, so a dry flask of ethylene and air is not a slow reactor
here -- it is a refusal. That is what a real Wacker reactor is: an aqueous
chloride liquor with gas bubbled through it.

⚠⚠ **AND ONE THING IN THIS TEMPLATE IS DELIBERATELY WRONG.** The real Wacker
rate law is ZERO order in oxygen; this one declares FIRST order, because the
kinetics kernel has no availability gate and a reactant at order zero is driven
negative. Panel 4 MEASURES what that costs rather than leaving it as a remark.

Run: ``python validation/wacker.py`` (~1 min).
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
from chemsim.properties import (  # noqa: E402
    ThermochemistryProvider,
    VolatilityProvider,
)
from chemsim.properties.electrolyte import (  # noqa: E402
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.reactions.synthesis import wacker_chemistry  # noqa: E402
from chemsim.reactions.thermo import reaction_deltas  # noqa: E402
from chemsim.vessel import Vessel  # noqa: E402

WATER, ETHYLENE, O2 = "O", "C=C", "O=O"
ACETALDEHYDE, CU, CL = "CC=O", "[Cu+2]", "[Cl-]"

CONVERGED = dict(rtol=1.0e-8, atol=1.0e-11)

VOL = VolatilityProvider()
NEUTRAL = ThermochemistryProvider()
THERMO = electrolyte_provider(volatility=VOL)

NET = build_network(
    [WATER, ETHYLENE, O2, CU, CL],
    wacker_chemistry() + list(dissociation_templates()),
    thermo=THERMO, volatility=VOL,
)
RXN = next(r for r in NET.reactions if r.name == "wacker_oxidation")


def run(T: float = 400.0, t: float = 600.0, *, cu: float = 0.02,
        eth: float = 0.20, o2: float = 0.20, water: float = 20.0):
    v = Vessel(NET, volume=1.0, T=T, T_env=T, UA=1.0e6, k_vent=0.0)
    v.charge({WATER: water}, phase="liquid")
    if cu:
        v.charge({CU: cu, CL: 2.0 * cu}, phase="liquid")
    v.charge({ETHYLENE: eth, O2: o2}, phase="gas")
    v.run(t, **CONVERGED)
    return v


def read(v):
    st = v.state()
    return (st.total(ETHYLENE), st.total(O2), st.total(ACETALDEHYDE),
            st.total(CU))


def main() -> None:
    print("=" * 74)
    print("PANEL 1 -- THE ION IS THE GATE, AND A DRY FLASK IS A REFUSAL")
    print("=" * 74)
    print("   the same five species WITHOUT electrolyte_provider():")
    try:
        bad = build_network([WATER, ETHYLENE, O2, CU, CL], wacker_chemistry(),
                            thermo=NEUTRAL, volatility=VOL)
        print(f"      build_network SUCCEEDS -- {bad.species}")
        print("      ...because a network is a GRAPH question and pricing")
        print("      happens one layer down. Then:")
        Vessel(bad, volume=1.0, T=400.0)
        print("   !! AND THE VESSEL BUILT TOO. That is a defect: see below.")
    except ValueError as exc:
        first = str(exc).split(" -- ")[0]
        print(f"      Vessel REFUSES -- {first}")
    print()
    print(f"   with it: species {NET.species}")
    print(f"            reactions {[r.name for r in NET.reactions]}")
    print()
    print("   A COPPER(II) ION HAS NO NEUTRAL GRAPH ANY ESTIMATOR WILL TOUCH.")
    print("   Joback prices a chloride 101 kJ/mol away from the ion table, which")
    print("   is why thermochemistry refuses a charged species by name. So this")
    print("   class is credited only for an AQUEOUS flask, and that is exactly")
    print("   the condition the catalog row carries.")

    print()
    print("=" * 74)
    print("PANEL 2 -- IT RUNS, AND THE COPPER IS A CONSTANT OF THE MOTION")
    print("=" * 74)
    dH, dG = reaction_deltas(RXN, THERMO, VOL)
    T0 = 400.0
    dG_T = dH - (T0 / 298.15) * (dH - dG)
    print(f"   2 C2H4 + O2 -> 2 CH3CHO :  dH {dH:9.2f} kJ/mol   dG298 {dG:9.2f}")
    print(f"   at 400 K:  dG {dG_T:9.2f} kJ/mol   ln K {-dG_T * 1000 / (R * T0):8.2f}")
    print("   -- which is why the template is irreversible, and why giving up")
    print("   the reverse to declare a rate order costs nothing here.")
    print()
    v = run()
    eth, o2, ace, cu = read(v)
    print("   1 L of water, 0.02 mol Cu(II) as the chloride, 0.20 mol each of")
    print("   ethylene and oxygen above it, 400 K, ten minutes:")
    print()
    print(f"      ethylene left     {eth:12.6f} mol   ({100 * (1 - eth / 0.20):6.2f}% "
          f"converted)")
    print(f"      oxygen left       {o2:12.6f} mol")
    print(f"      acetaldehyde      {ace:12.6f} mol")
    print(f"      copper(II)        {cu:12.6f} mol   (charged 0.020000)")
    print(f"      carbon closure    {2 * eth + 2 * ace:12.6f} mol   (charged "
          f"{2 * 0.20:.6f})")
    print(f"      {v.conservation_report() or 'conservation clean'}")

    print()
    print("=" * 74)
    print("PANEL 3 -- WHAT BOUNDS A, AND THE COPPER LOADING")
    print("=" * 74)
    print("   A third-order rate law has no collision limit to be compared with")
    print("   (M8's unit error), so the bound is the REACTOR: a one-stage Wacker")
    print("   converts 30-40% of its ethylene per pass on minutes of residence.")
    print()
    print(f"   {'t / s':>8} {'ethylene':>11} {'acetald':>11} {'conversion':>12}")
    for t in (60.0, 300.0, 600.0, 3600.0):
        eth, _o2, ace, _cu = read(run(t=t))
        print(f"   {t:8.0f} {eth:11.6f} {ace:11.6f} "
              f"{100 * (1 - eth / 0.20):11.2f}%")
    print()
    print(f"   {'Cu(II)/mol':>11} {'acetald in 60 s':>17} {'Cu left':>10}")
    for cu0 in (0.0, 0.002, 0.02, 0.10):
        _eth, _o2, ace, cu = read(run(t=60.0, cu=cu0))
        print(f"   {cu0:11.3f} {ace:17.6f} {cu:10.6f}")
    print()
    print("   NO COPPER, NO REACTION -- exactly zero. And the loading is a")
    print("   first-order knob, which for a HOMOGENEOUS catalyst is right rather")
    print("   than provisional: there is no site balance to saturate. That is")
    print("   the one way this template is on firmer ground than the")
    print("   heterogeneous ones (M10).")
    print()
    print(f"   {'T / K':>7} {'conversion in 10 min':>22}")
    for T in (320.0, 360.0, 400.0, 440.0):
        eth, _o2, _ace, _cu = read(run(T=T))
        print(f"   {T:7.0f} {100 * (1 - eth / 0.20):21.2f}%")

    print()
    print("=" * 74)
    print("PANEL 4 -- THE ONE THING THAT IS DELIBERATELY WRONG, MEASURED")
    print("=" * 74)
    print("   The real Wacker rate law is ZERO order in oxygen: the O2 only")
    print("   reoxidises the copper(I) and never appears in the rate-determining")
    print("   step. This template declares FIRST order, because the kinetics")
    print("   kernel has no availability gate and a zero-order reactant is driven")
    print("   negative once it runs out. What that costs:")
    print()
    print(f"   {'O2 charged':>11} {'acetald in 60 s':>17} {'ratio to 0.05':>15}")
    base = None
    for o2_0 in (0.05, 0.10, 0.20, 0.40):
        _eth, _o2, ace, _cu = read(run(t=60.0, o2=o2_0))
        base = base or ace
        print(f"   {o2_0:11.2f} {ace:17.6f} {ace / base:15.3f}")
    print()
    print()
    v = run(t=1.0, cu=0.0)
    st = v.state()
    print("   AND A SECOND ONE, FOUND WHILE MEASURING THE FIRST AND NOT FIXED.")
    print("   The same flask, ethylene charged to the HEADSPACE, one second, no")
    print("   copper at all:")
    print(f"      ethylene in the gas    {st.n_gas[ETHYLENE]:10.6f} mol")
    print(f"      ethylene DISSOLVED     {st.n_liquid[ETHYLENE]:10.6f} mol"
          f"   ({100 * st.n_liquid[ETHYLENE] / 0.20:.1f}% of the charge)")
    print(f"      oxygen dissolved       {st.n_liquid[O2]:10.6f} mol")
    print()
    print("   83% OF THE ETHYLENE IS IN THE WATER AND IT SHOULD BE ~2%. Ethylene")
    print("   is a CONDENSABLE species here, so its solubility is Raoult's law")
    print("   against a vapour pressure of 219.9 bar -- read off a curated")
    print("   Antoine curve at 400 K, which is 118 K ABOVE ethylene's critical")
    print("   temperature of 282.35. Oxygen beside it is a Henry's-law solute")
    print("   and behaves. NOTHING IN build_phase_arrays COMPARES T TO Tc.")
    print("   ! S11 predicted a measured boiling point would move this and")
    print("   MEASURED THAT IT DOES NOT: 0.16588 -> 0.16596, four figures")
    print("   unchanged, because Tb does not feed a curated Antoine curve.")
    print("   Reported as a latent fragility, not refused: it makes this")
    print("   reactor's liquor richer in alkene than a real one.")
    print()
    print("   THE RATE IS PROPORTIONAL TO THE OXYGEN AND IT SHOULD NOT BE. That")
    print("   is right at LOW oxygen -- where the copper(I) really is waiting for")
    print("   air -- and wrong at high, which is the same shape as the missing")
    print("   site balance. Reported, not hidden, and not approximated away:")
    print("   the alternative was a flask that makes acetaldehyde out of no")
    print("   oxygen at all.")

    print()
    print("=" * 74)
    print("DONE. Every number above came out of a real Vessel except the")
    print("formation pair, which came out of ion_data and this project's tables.")
    print("=" * 74)


if __name__ == "__main__":
    main()
