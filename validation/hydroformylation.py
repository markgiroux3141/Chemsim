"""S11's standing audit: the oxo process, and a SELECTIVITY that is a rate ratio.

``validation/catalog_coverage.py`` credits ``hydroformylation`` because two
templates exist for it. That is a claim about the library and not about the
engine, and this class is exactly the shape S1's false credit had: the catalog's
two rows are ONE reaction with TWO regiochemistries, so a mechanism that makes
only the linear aldehyde would look identical in that table and would be wrong.
So both products are read out of a real ``Vessel`` here.

    oxo-process 1   propene + CO + H2 -> butyraldehyde       420 K, 200 bar
    oxo-process 2   propene + CO + H2 -> isobutyraldehyde    "same reactor,
                                                              n:iso selectivity"

⚠ **WHAT THIS AUDIT IS ACTUALLY FOR IS THE THREE THINGS NOBODY DECLARED.** One
number is fitted -- a 4.8 kJ/mol barrier difference, set to give n:iso = 4.0 at
the catalog row's own 420 K. Everything below that is a consequence:

  * the selectivity FALLS when the reactor is heated, 4.57 at 380 K to 3.95 at
    420 K to 3.54 at 450 -- and then COLLAPSES, 1.87 at 480 K and 0.76 at 520,
    because above ~450 K the reverse reactions get inside the reactor's own hour
    and the more stable branched product starts winning. A real cobalt oxo
    reactor sits at 410-450 K and nothing here was told that;
  * the process needs PRESSURE, because three moles of gas become one -- at 600 K
    and 1 bar the equilibrium has turned over and the flask does nothing;
  * and left for years the reactor CROSSES FROM KINETIC TO THERMODYNAMIC CONTROL
    on its own, because the branched aldehyde is the more stable one and the two
    templates share a reactant. The thermodynamics of this reaction point the
    OPPOSITE WAY from the process.

Run: ``python validation/hydroformylation.py`` (~1 min).
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
    hydroformylation_branched,
    hydroformylation_linear,
    oxo_chemistry,
)
from chemsim.reactions.thermo import reaction_deltas  # noqa: E402
from chemsim.vessel import Vessel  # noqa: E402

PROPENE, CO, H2 = "C=CC", "[C-]#[O+]", "[H][H]"
NBAL, IBAL = "CCCC=O", "CC(C)C=O"
COBALT = MINERALS["cobalt"].lattice

CONVERGED = dict(rtol=1.0e-8, atol=1.0e-11)

thermo = ThermochemistryProvider()
vol = VolatilityProvider()

NET = build_network([PROPENE, CO, H2], oxo_chemistry(), thermo=thermo,
                    volatility=vol)
LIN = next(r for r in NET.reactions if r.name == "hydroformylation_linear")
BRA = next(r for r in NET.reactions if r.name == "hydroformylation_branched")


def lnK(reaction, T: float) -> float:
    """ln K for one concrete reaction at T, off the tables the engine uses."""
    dH, dG = reaction_deltas(reaction, thermo, vol)
    dG_T = dH - (T / 298.15) * (dH - dG)
    return -dG_T * 1000.0 / (R * T)


def charge_for(P_bar: float, T: float, volume: float = 1.0) -> float:
    """Moles of EACH of the three gases that put the flask at P_bar."""
    return P_bar * volume / (3.0 * 0.083145 * T)


def run(T: float, n: float, t: float = 3600.0, *, cobalt: float = 0.1,
        templates=None, volume: float = 1.0):
    net = (NET if templates is None
           else build_network([PROPENE, CO, H2], templates, thermo=thermo,
                              volatility=vol))
    v = Vessel(net, volume=volume, T=T, T_env=T, UA=1.0e6, k_vent=0.0)
    v.charge({PROPENE: n, CO: n, H2: n}, phase="gas")
    if cobalt:
        v.charge({COBALT: cobalt}, phase="solid")
    v.run(t, **CONVERGED)
    return v


def read(v):
    st = v.state()
    return st.total(PROPENE), st.total(NBAL), st.total(IBAL), st.total(CO)


def irreversible():
    """The same pair with the reverse taken away, for panel 4."""
    lin = hydroformylation_linear()
    bra = hydroformylation_branched()
    return [
        type(lin)(name=lin.name, smarts=lin.smarts, A=lin.A, Ea=lin.Ea,
                  phase="gas", reversible=False, solid_catalyst="cobalt"),
        type(bra)(name=bra.name, smarts=bra.smarts, A=bra.A, Ea=bra.Ea,
                  phase="gas", reversible=False, solid_catalyst="cobalt"),
    ]


def main() -> None:
    print("=" * 74)
    print("PANEL 1 -- THE CREDIT, RUN. BOTH ROWS OUT OF ONE FLASK")
    print("=" * 74)
    print(f"   species   {NET.species}")
    print(f"   reactions {[r.name for r in NET.reactions]}")
    print()
    n = charge_for(200.0, 420.0)
    v = run(420.0, n)
    p, nb, ib, co = read(v)
    print(f"   1 L at 420 K, charged to 200 bar ({n:.4f} mol each), 0.1 mol")
    print("   cobalt in the solid block, sealed, one hour:")
    print()
    print(f"      propene left        {p:12.6f} mol   ({100 * (1 - p / n):6.2f}% "
          f"converted)")
    print(f"      butyraldehyde       {nb:12.6f} mol")
    print(f"      isobutyraldehyde    {ib:12.6f} mol")
    print(f"      n : iso             {nb / ib:12.4f}")
    print(f"      carbon closure      {3 * p + 4 * nb + 4 * ib + co:12.6f} mol"
          f"   (charged {4 * n:.6f})")
    print(f"      {v.conservation_report() or 'conservation clean'}")
    print()
    print("   BOTH catalog rows come out of ONE charge. That is what the class")
    print("   credit means and it is not a thing this project's coverage table")
    print("   can ask -- a template making only the linear aldehyde would read")
    print("   identically there.")

    print()
    print("=" * 74)
    print("PANEL 2 -- THE THERMODYNAMICS POINT THE WRONG WAY, WHICH IS THE POINT")
    print("=" * 74)
    dH_n, dG_n = reaction_deltas(LIN, thermo, vol)
    dH_i, dG_i = reaction_deltas(BRA, thermo, vol)
    print(f"   {'':26} {'dH / kJ':>10} {'dG298':>10} {'lnK 420':>10} "
          f"{'K 420':>10}")
    print(f"   {'-> butanal (linear)':26} {dH_n:10.2f} {dG_n:10.2f} "
          f"{lnK(LIN, 420.0):10.3f} {math.exp(lnK(LIN, 420.0)):10.3f}")
    print(f"   {'-> 2-methylpropanal':26} {dH_i:10.2f} {dG_i:10.2f} "
          f"{lnK(BRA, 420.0):10.3f} {math.exp(lnK(BRA, 420.0)):10.3f}")
    print()
    print(f"   THE BRANCHED PRODUCT IS THE MORE STABLE ONE, by "
          f"{dH_n - dH_i:.2f} kJ/mol of")
    print(f"   enthalpy and {dG_n - dG_i:.2f} of free energy -- so at equilibrium "
          f"it wins")
    print(f"   {math.exp(lnK(BRA, 420.0)) / math.exp(lnK(LIN, 420.0)):.2f} to 1. "
          f"The real reactor makes the LINEAR one about four to")
    print("   one. The oxo process runs AGAINST its own thermodynamics, which is")
    print("   why the aldehyde the industry wants has to be taken out of a")
    print("   reactor rather than waited for -- and why Evans-Polanyi is OFF in")
    print("   both templates. Any alpha > 0 would give the more exothermic")
    print("   branched route the lower barrier and name the wrong major product.")

    print()
    print("=" * 74)
    print("PANEL 3 -- ONE FITTED NUMBER, AND THE CURVE IS A PREDICTION")
    print("=" * 74)
    print("   dEa = 4.8 kJ/mol is set so exp(dEa/RT) = 4.0 at the catalog row's")
    print("   own 420 K. Nothing below is fitted:")
    print()
    irr = irreversible()
    print(f"   {'T / K':>7} {'propene':>10} {'n':>10} {'iso':>10} "
          f"{'conv':>8} {'n:iso':>8} {'exp(dEa/RT)':>12} {'kinetic':>9}")
    for T in (380.0, 400.0, 420.0, 450.0, 480.0, 520.0):
        nn = charge_for(200.0, 420.0)          # the SAME charge, so only T moves
        pp, nb, ib, _ = read(run(T, nn))
        _, nbk, ibk, _ = read(run(T, nn, templates=irr))
        print(f"   {T:7.0f} {pp:10.6f} {nb:10.6f} {ib:10.6f} "
              f"{100 * (1 - pp / nn):7.2f}% {nb / ib:8.3f} "
              f"{math.exp(4800.0 / (R * T)):12.3f} {nbk / ibk:9.3f}")
    print()
    print("   RUNNING AN OXO REACTOR HOT COSTS LINEAR SELECTIVITY -- and the")
    print("   LAST TWO COLUMNS ARE WHY THE COLLAPSE IS STEEPER THAN THE")
    print("   ARRHENIUS RATIO. Up to ~450 K the flask tracks exp(dEa/RT) to")
    print("   three figures and that is pure kinetics. Above it the reverse")
    print("   reactions become fast enough to matter INSIDE the reactor's own")
    print("   hour, and the branched product -- the more stable one -- starts")
    print("   winning: 1.87 at 480 K against a kinetic 3.33, and 0.76 at 520 K")
    print("   against 3.03. The conversion turns over in the same place.")
    print("   NOBODY DECLARED A MAXIMUM OPERATING TEMPERATURE. A real cobalt oxo")
    print("   reactor sits at 410-450 K, and this is the reason, arrived at from")
    print("   one barrier difference and a formation table.")

    print()
    print("=" * 74)
    print("PANEL 4 -- THREE MOLES OF GAS BECOME ONE, SO PRESSURE IS THE PROCESS")
    print("=" * 74)
    print("   The same hour, at each temperature's own 1 bar and 200 bar charge,")
    print("   with the reverse ON and with it taken AWAY:")
    print()
    irr = irreversible()
    print(f"   {'T / K':>7} {'P / bar':>9} {'charge':>9} {'lnK(n)':>9} "
          f"{'reversible':>12} {'irreversible':>14}")
    for T in (420.0, 500.0, 600.0):
        for P in (1.0, 200.0):
            nn = charge_for(P, T)
            p_rev = read(run(T, nn))[0]
            p_irr = read(run(T, nn, templates=irr))[0]
            print(f"   {T:7.0f} {P:9.0f} {nn:9.4f} {lnK(LIN, T):9.3f} "
                  f"{100 * (1 - p_rev / nn):11.3f}% "
                  f"{100 * (1 - p_irr / nn):13.3f}%")
    print()
    print("   AT 600 K AND 1 BAR AN IRREVERSIBLE PAIR REPORTS 78% CONVERSION AND")
    print("   THE REVERSIBLE ONE REPORTS 0.01%. A factor of ~6000, on a flask a")
    print("   player can build. That is why alkene_hydrogenation's 'irreversible")
    print("   is a claim about temperature' argument does not transfer here:")
    print("   retro-hydroformylation is real, it is industrial, and it is the")
    print("   reason the process is run at 200 bar at all.")

    print()
    print("=" * 74)
    print("PANEL 5 -- IT CROSSES FROM KINETIC TO THERMODYNAMIC CONTROL ON ITS OWN")
    print("=" * 74)
    print("   420 K, 200 bar charge, left alone. Nothing declares a crossover;")
    print("   the two templates share a reactant and detailed balance supplies")
    print("   both reverses at Ea - dH, which nobody typed:")
    print()
    n = charge_for(200.0, 420.0)
    print(f"   {'t / s':>10} {'':>12} {'propene':>10} {'n':>10} {'iso':>10} "
          f"{'n:iso':>8} {'n:iso (GAS)':>12}")
    for t, label in ((3.6e3, "1 hour"), (3.6e4, "10 hours"), (3.6e5, "4 days"),
                     (3.6e6, "6 weeks"), (3.6e7, "1 year"), (3.6e8, "11 years"),
                     (1.0e10, "settled")):
        v = run(420.0, n, t=t)
        pp, nb, ib, _ = read(v)
        g = v.state().n_gas
        print(f"   {t:10.2e} {label:>12} {pp:10.6f} {nb:10.6f} {ib:10.6f} "
              f"{nb / ib:8.3f} {g[NBAL] / g[IBAL]:12.4f}")
    ratio = math.exp(lnK(LIN, 420.0)) / math.exp(lnK(BRA, 420.0))
    print()
    print(f"   THE EQUILIBRIUM RATIO IS K(n)/K(iso) = {ratio:.4f} and THE GAS")
    print("   PHASE LANDS ON IT TO FOUR FIGURES. Kinetic control at the")
    print("   reactor's own timescale, thermodynamic control eleven years later,")
    print("   and the barrier that separates them is derived rather than")
    print("   declared. Nothing a player does reaches this; it is the")
    print("   equilibrium the pair is anchored to, made visible.")
    print()
    print("   AND THE LAST TWO COLUMNS DISAGREE, WHICH IS ALSO CORRECT AND ALSO")
    print("   UNDECLARED. An equilibrium constant is a statement about PARTIAL")
    print("   PRESSURES; the flask's INVENTORY ratio settles at 0.513 instead,")
    print("   because at 200 bar and 420 K this reactor holds ~1.7 mol of LIQUID")
    print("   product and butanal (Tb 347.95 K) is the less volatile of the two,")
    print("   so it hides in the layer. A real cobalt oxo reactor is a")
    print("   liquid-phase process for exactly this reason. READ THE GAS")
    print("   column against K, never the inventory column.")

    print()
    print("=" * 74)
    print("PANEL 6 -- THE COBALT IS A GATE AND A KNOB")
    print("=" * 74)
    print(f"   {'cobalt / mol':>13} {'propene':>10} {'n':>10} {'iso':>10} "
          f"{'conv':>9}")
    for co in (0.0, 0.001, 0.01, 0.1, 0.5):
        p, nb, ib, _ = read(run(420.0, n, cobalt=co))
        print(f"   {co:13.3f} {p:10.6f} {nb:10.6f} {ib:10.6f} "
              f"{100 * (1 - p / n):8.3f}%")
    print()
    print("   NO METAL, NO REACTION -- exactly zero, not nearly zero. And the")
    print("   loading is a first-order knob for ever, because the SITE BALANCE")
    print("   is still not modelled (M10). Ten times the cobalt is ten times the")
    print("   rate at any loading, which is right at low coverage and wrong at")
    print("   high, and is stated rather than approximated.")

    print()
    print("=" * 74)
    print("DONE. Every number above came out of a real Vessel except the two")
    print("formation pairs, which came out of this project's own tables.")
    print("=" * 74)


if __name__ == "__main__":
    main()
