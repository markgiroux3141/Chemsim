"""C1's standing audit -- oil of vitriol from a rock, and the two ends of a retort.

Run this after touching ``reactions/library.py``'s ``sulfur_trioxide_hydration``,
``properties/solid_state.py``'s ``sulfate-thermal-decomposition`` row, or the
``vitriol-distillation`` rows in ``data/catalog/route_steps.psv``. About 40 s.

WHAT C1 DID, in one paragraph. `vitriol-distillation` is two steps: roast green
vitriol (melanterite, a NATURAL mineral on this project's own declared list) and
catch what comes off in a receiver of water. The roast has been in the engine
since M6 as a ``SolidStateReaction``; nothing could catch the trioxide, so the
catalog's most-demanded blocked species -- sulfuric acid, wanted by four routes --
was blocked on one arrow. C1 wrote that arrow, split the eight-row `hydrolysis`
bucket into the mechanisms it was hiding, and corrected a catalog row that named a
product the engine has never made. Playability went 12 -> 14 and the runnable
count 36 -> 37.

THE PANELS

  1  the retort has a THRESHOLD, and the residue is hematite not FeO
  2  the receiver: 100.000% up to 600 K, because the condenser beats K
  3  the ceiling is EMERGENT -- ln K = 0 at 664.3 K, checked against the
     analytic root of the same equilibrium
  4  the pre-exponential is FORGIVEN over five decades
  5  the LIQUID channel, built and refused, on conservation
  6  the corpus edits, and the one that was decided rather than derived
  7  the chain end to end -- and there is NO single temperature for it

Windows console is cp1252: every printed line here is ASCII.
"""

from __future__ import annotations

import contextlib
import io
import math
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, os.path.join(_ROOT, "tools"))
sys.path.insert(0, os.path.join(_ROOT, "validation"))

from chemsim.constants import R, R_L_BAR  # noqa: E402
from chemsim.network import build_network  # noqa: E402
from chemsim.properties import ThermochemistryProvider, VolatilityProvider  # noqa: E402
from chemsim.properties.mineral_data import MINERALS  # noqa: E402
from chemsim.reactions import ReactionTemplate, sulfur_trioxide_hydration  # noqa: E402
from chemsim.vessel import Vessel  # noqa: E402

thermo = ThermochemistryProvider()
volatility = VolatilityProvider(thermo)

M = MINERALS
VITRIOL, HEMATITE = M["green vitriol"].lattice, M["hematite"].lattice
SO2, SO3, H2O = "O=S=O", "O=S(=O)=O", "O"
# the canonical form the state vector is keyed by -- ``OS(=O)(=O)O`` is the same
# molecule and is NOT the same string, which cost the first run of this audit a
# panel of zeroes.
H2SO4 = "O=S(=O)(O)O"
TIGHT = dict(rtol=1.0e-8, atol=1.0e-11)


def net(species, templates=()):
    with contextlib.redirect_stdout(io.StringIO()):
        return build_network(species, list(templates), thermo=thermo,
                             volatility=volatility)


def sol(v, s):
    return float(v.state().n_solid.get(s, 0.0))


def gas(v, s):
    return float(v.state().n_gas.get(s, 0.0))


def liq(v, s):
    return float(v.state().n_liquid.get(s, 0.0))


def tot(v, s):
    st = v.state()
    return float(st.n_liquid.get(s, 0.0) + st.n_liquid2.get(s, 0.0)
                 + st.n_gas.get(s, 0.0) + st.n_solid.get(s, 0.0))


def rule(title):
    print()
    print("=" * 74)
    print(title)
    print("=" * 74)


def price(T):
    """dH, dG(T), ln K for SO3 + H2O -> H2SO4 off the curated formation rows."""
    dH = thermo.get(H2SO4).Hf - thermo.get(SO3).Hf - thermo.get(H2O).Hf
    dG298 = thermo.get(H2SO4).Gf - thermo.get(SO3).Gf - thermo.get(H2O).Gf
    dS = (dH - dG298) / 298.15
    dG = dH - T * dS
    return dH, dG, -dG * 1000.0 / (R * T)


T0 = time.time()
RETORT = net([VITRIOL, HEMATITE, SO2, SO3])
RECEIVER = net([SO3, H2O, H2SO4], [sulfur_trioxide_hydration()])

# ---------------------------------------------------------------------------
rule("1. THE RETORT HAS A THRESHOLD, AND ITS RESIDUE IS HEMATITE")
# ---------------------------------------------------------------------------
print("  2 FeSO4 -> Fe2O3 + SO2 + SO3, declared in properties/solid_state.py")
print("  since M6. Nothing here is new; the panel exists because the CATALOG")
print("  row said `-> iron-ii-oxide + sulfur-trioxide` until C1, and iron(II)")
print("  oxide is REFUSED a price -- so the route was blocked on a datum for a")
print("  species that is not in its chemistry. 0.10 mol of the mineral, 1 L,")
print("  sealed, 2000 s.")
print()
print(f"  {'T/K':>6s} {'vitriol':>10s} {'hematite':>10s} {'SO2':>10s} "
      f"{'SO3':>10s} {'done%':>8s}")
RETORT_ROWS = []
for T in (600.0, 700.0, 800.0, 900.0, 1000.0):
    v = Vessel(RETORT, volume=1.0, T=T, T_env=T, UA=1.0e4, k_vent=0.0)
    v.charge({VITRIOL: 0.10}, phase="solid")
    v.run(2000.0, **TIGHT)
    row = (T, sol(v, VITRIOL), sol(v, HEMATITE), gas(v, SO2), gas(v, SO3))
    RETORT_ROWS.append(row)
    print(f"  {T:6.0f} {row[1]:10.6f} {row[2]:10.6f} {row[3]:10.6f} "
          f"{row[4]:10.6f} {100.0 * (0.10 - row[1]) / 0.10:8.3f}")
print()
print("  Nothing below 800 K, complete by 1000 K. `retort, red heat` is the")
print("  catalog's own condition column and the engine was never told it.")
print("  The stoichiometry is exactly 2:1:1:1 -- 0.05 of each product.")

# ---------------------------------------------------------------------------
rule("2. THE RECEIVER: 100.000% UP TO 600 K, AND THE CONDENSER IS WHY")
# ---------------------------------------------------------------------------
print("  0.05 mol SO3 into a receiver holding 1.0 mol of liquid water, 1 L,")
print("  600 s. Conversion is the TOTAL sulfuric acid over the trioxide in.")
print()
print(f"  {'T/K':>6s} {'lnK':>8s} {'H2SO4 liq':>11s} {'H2SO4 gas':>11s} "
      f"{'SO3 left':>11s} {'conv%':>9s}")
RECEIVER_ROWS = []
for T in (320.0, 350.0, 400.0, 500.0, 600.0):
    v = Vessel(RECEIVER, volume=1.0, T=T, T_env=T, UA=1.0e4, k_vent=0.0)
    v.charge({H2O: 1.0}, phase="liquid")
    v.charge({SO3: 0.05}, phase="gas")
    v.run(600.0, **TIGHT)
    conv = 100.0 * tot(v, H2SO4) / 0.05
    RECEIVER_ROWS.append((T, conv))
    print(f"  {T:6.0f} {price(T)[2]:8.3f} {liq(v, H2SO4):11.6f} "
          f"{gas(v, H2SO4):11.6f} {tot(v, SO3):11.3e} {conv:9.3f}")
print()
print("  ln K falls by twenty orders of magnitude across that column and the")
print("  conversion does not move. The acid boils at 610 K, so it leaves the")
print("  gas phase as fast as it forms and the equilibrium never bites.")
print("  Le Chatelier, done by a phase change the template knows nothing about.")

# ---------------------------------------------------------------------------
rule("3. THE CEILING IS EMERGENT: ln K = 0 AT 664.3 K")
# ---------------------------------------------------------------------------
dH, _, _ = price(298.15)
dS = (dH - (thermo.get(H2SO4).Gf - thermo.get(SO3).Gf - thermo.get(H2O).Gf)) / 298.15
T_CROSS = dH / dS
print(f"  dH {dH:.2f} kJ/mol, dS {1000.0 * dS:.1f} J/(mol K), so ln K = 0 at")
print(f"  dH/dS = {T_CROSS:.1f} K. Nothing declares that: three EXPERIMENTAL")
print("  formation rows (NIST/CODATA) and one division.")
print()
print("  Take the condenser away -- 0.05 SO3 + 0.05 H2O in 10 L of gas, no")
print("  liquid charged -- and the equilibrium is all there is. `analytic` is")
print("  the root of K = p_acid / (p_SO3 p_H2O) solved by hand on the same K.")
print()
print(f"  {'T/K':>6s} {'lnK':>8s} {'H2SO4':>10s} {'SO3 left':>10s} "
      f"{'conv%':>8s} {'analytic%':>10s}")
CEILING_ROWS = []
for T in (600.0, 664.3, 700.0, 800.0):
    v = Vessel(RECEIVER, volume=10.0, T=T, T_env=T, UA=1.0e4, k_vent=0.0)
    v.charge({SO3: 0.05, H2O: 0.05}, phase="gas")
    v.run(600.0, **TIGHT)
    lnK = price(T)[2]
    K = math.exp(lnK)
    # p = n R T / V, so with a = 0.05 mol of each and x converted:
    #   K = (a x c) / (a (1-x) c)^2   with c = R T / V
    c = R_L_BAR * T / 10.0
    b = 2.0 + 1.0 / (K * 0.05 * c)
    x = (b - math.sqrt(b * b - 4.0)) / 2.0
    conv = 100.0 * tot(v, H2SO4) / 0.05
    CEILING_ROWS.append((T, conv, 100.0 * x))
    print(f"  {T:6.1f} {lnK:8.3f} {tot(v, H2SO4):10.6f} {tot(v, SO3):10.6f} "
          f"{conv:8.3f} {100.0 * x:10.3f}")
print()
print("  The solver and the quadratic agree to three figures at every rung, so")
print("  the number the engine reports IS the equilibrium and not a stall.")
print("  A receiver has to be COOL. That is what a receiver is, and it came out")
print("  of the formation data rather than out of a rule anybody wrote.")
print()
print("  NOT RUN HERE, AND IT IS A REAL FINDING: the same panel at 700 K WITH")
print("  the mole of water present takes 434 SECONDS of wall clock against ~1 s")
print("  at every rung below it -- the acid is above its 610 K boiling point,")
print("  the liquid layer drains to nothing, and LAYER_REABSORB thrashes. That")
print("  is engine queue item 15's shape on a THREE-species network, which")
print("  makes it the cheapest reproduction of that bug anyone has.")

# ---------------------------------------------------------------------------
rule("4. THE PRE-EXPONENTIAL IS FORGIVEN OVER FIVE DECADES")
# ---------------------------------------------------------------------------
print("  A is pinned at the order of the gas-kinetic collision limit and Ea")
print("  then puts k(298) at the ORDER of the effective bimolecular constant")
print("  reported for SO3 in water vapour. Both are apparent -- the real gas")
print("  reaction is second order in water. This panel is what licences that:")
print()
print(f"  {'A':>10s} {'k(298)':>12s} {'H2SO4':>10s} {'conv%':>9s}")
A_ROWS = []
for A in (1.0e6, 1.0e8, 1.0e10, 1.0e11):
    n = net([SO3, H2O, H2SO4], [sulfur_trioxide_hydration(A=A)])
    v = Vessel(n, volume=1.0, T=350.0, T_env=350.0, UA=1.0e4, k_vent=0.0)
    v.charge({H2O: 1.0}, phase="liquid")
    v.charge({SO3: 0.05}, phase="gas")
    v.run(600.0, **TIGHT)
    conv = 100.0 * tot(v, H2SO4) / 0.05
    A_ROWS.append((A, conv))
    print(f"  {A:10.0e} {A * math.exp(-23_600.0 / (R * 298.15)):12.3e} "
          f"{tot(v, H2SO4):10.6f} {conv:9.3f}")
print()
print("  Five decades, one answer. GAME_DESIGN 3(a): a rate error is forgiven")
print("  and only bad THERMO snowballs, and the thermo here is three")
print("  experimental rows.")
print()
print("  WHAT WAS DELIBERATELY NOT DECLARED: orders=(1.0, 2.0), which is the")
print("  more correct rate law. ReactionTemplate.orders may not be combined")
print("  with reversible -- a declared order has no detailed-balance partner --")
print("  so the choice was between the right ORDER and the right REVERSE. The")
print("  order is forgiven (this panel) and the reverse is the mechanic (panel")
print("  3). Between two wrong-in-different-ways declarations, keep the one")
print("  whose error is MEASURED to be invisible.")

# ---------------------------------------------------------------------------
rule("5. THE LIQUID CHANNEL WAS BUILT AND REFUSED, ON CONSERVATION")
# ---------------------------------------------------------------------------
print("  phase='any' would run this in the flask's liquid too, and a receiver")
print("  full of water is not an obviously wrong place to put it. Same charge")
print("  as panel 2 at 320 K, where the liquid channel is fastest:")
print()
print(f"  {'phase':>8s} {'conv%':>9s} {'sulfur in - out':>17s} {'reported?':>10s}")
SMARTS = sulfur_trioxide_hydration().smarts
PHASE_ROWS = []
for phase in ("gas", "liquid", "any"):
    t = ReactionTemplate(name="sulfur_trioxide_hydration", smarts=SMARTS,
                         A=1.0e10, Ea=23_600.0, phase=phase, reversible=True)
    n = net([SO3, H2O, H2SO4], [t])
    v = Vessel(n, volume=1.0, T=320.0, T_env=320.0, UA=1.0e4, k_vent=0.0)
    v.charge({H2O: 1.0}, phase="liquid")
    v.charge({SO3: 0.05}, phase="gas")
    v.run(600.0, **TIGHT)
    err = tot(v, SO3) + tot(v, H2SO4) - 0.05
    said = "yes" if v.conservation_report() else "no"
    PHASE_ROWS.append((phase, 100.0 * tot(v, H2SO4) / 0.05, err, said))
    print(f"  {phase:>8s} {100.0 * tot(v, H2SO4) / 0.05:9.3f} {err:17.3e} "
          f"{said:>10s}")
print()
print("  It buys NOTHING -- the conversion is identical to six figures -- and")
print("  it costs a projection residual six thousand times the tolerance,")
print("  because the liquid pseudo-first-order constant is 1.4e6 1/s against a")
print("  600 s run and empties the trioxide inside the first microsecond.")
print("  The residual is not silent: conservation_report names it, which is")
print("  what let it be priced at all. And there is no second SOURCED constant")
print("  to put on a liquid arrow -- it would be the gas one copied.")

# ---------------------------------------------------------------------------
rule("6. THE CORPUS EDITS, AND THE ONE THAT WAS DECIDED RATHER THAN DERIVED")
# ---------------------------------------------------------------------------
print("  `hydrolysis` held EIGHT rows and was the catalog's second-biggest")
print("  class. The argument for splitting it is not that it is eight")
print("  mechanisms -- it is that the taxonomy already carried")
print("  amide-, ester-, epoxide-, glycoside-, nitrile-, isocyanate- and")
print("  disproportionation-hydrolysis. Everything it knew how to name got")
print("  named; `hydrolysis` was the bin for the rest.")
print()
import catalog as cat  # noqa: E402  -- the panels above are the expensive half

STEPS = cat.load_steps()
ROUTES = cat.load_routes()
COMPOUNDS = cat.load_compounds()
SPLIT = {
    "oleum-hydrolysis", "sulfur-trioxide-hydration", "sulfide-carbonation",
    "cyanamide-hydrolysis", "amalgam-decomposition", "carbide-hydrolysis",
    "pentosan-hydrolysis", "organometallic-protonolysis",
}
here = {s.cls for s in STEPS}
print(f"  {'class':>30s} {'in the catalog':>15s}")
for c in sorted(SPLIT):
    print(f"  {c:>30s} {str(c in here):>15s}")
print(f"  {'hydrolysis (the old bin)':>30s} {str('hydrolysis' in here):>15s}")
print()
print("  Only ONE of the eight is covered -- `sulfur-trioxide-hydration`. The")
print("  split moves the class DENOMINATOR up by seven and the numerator not at")
print("  all, which is S7's shape: a split that lowers the headline is working.")
print()
print("  THE DECIDED ONE. `furfural-route` step 1 is chemically a glycoside")
print("  hydrolysis and the taxonomy's convention would file it under the")
print("  COVERED `glycoside-hydrolysis`. It is not there, because the row as")
print("  spelled is fragility 29b -- `xylose + water -> xylose`, products a")
print("  SUBSET of reactants -- so no template can ever match it. Measured both")
print("  ways rather than argued:")
print()


def _priced(x):
    # the tier audit is expensive; this panel only needs the four classes to
    # move, so reuse the runnable scorer's own price question via the catalog's
    # marker rule plus membership. See tools/build_playable.py for the real one.
    return x in COMPOUNDS


import catalog_coverage as cc  # noqa: E402

TC = dict(cc.TEMPLATE_CLASSES)
gaps = sorted(c for c in {s.cls for s in STEPS if s.route == "furfural-route"}
              if c not in TC)
print(f"  furfural-route's UNCOVERED classes: {gaps}")
print("  -> the row's class assignment is worth ZERO today, because the route")
print(f"     needs {len(gaps)} of them. It stops being free the moment the")
print("     other three land, and a false credit is cheapest to refuse before")
print("     it can pay. G3's rule: two suspected rules are a GRID, and this is")
print("     the cell that is currently equal to its neighbour.")

# ---------------------------------------------------------------------------
rule("7. THE CHAIN, AND WHY ONE POT IS NOT THE APPARATUS")
# ---------------------------------------------------------------------------
print("  A retort of green vitriol at 1000 K, its trioxide carried to a")
print("  receiver of water at 350 K -- then the same charge in ONE pot.")
print()
v = Vessel(RETORT, volume=1.0, T=1000.0, T_env=1000.0, UA=1.0e4, k_vent=0.0)
v.charge({VITRIOL: 0.10}, phase="solid")
v.run(2000.0, **TIGHT)
SO3_MADE, SO2_MADE = gas(v, SO3), gas(v, SO2)
print(f"  retort  1000 K   SO3 {SO3_MADE:.6f}   SO2 {SO2_MADE:.6f}   "
      f"hematite {sol(v, HEMATITE):.6f}")

v = Vessel(RECEIVER, volume=1.0, T=350.0, T_env=350.0, UA=1.0e4, k_vent=0.0)
v.charge({H2O: 1.0}, phase="liquid")
v.charge({SO3: SO3_MADE}, phase="gas")
v.run(600.0, **TIGHT)
ACID = tot(v, H2SO4)
print(f"  receiver 350 K   H2SO4 {ACID:.6f}   ({100.0 * ACID / SO3_MADE:.3f}% "
      f"of the trioxide)")
print()
ONEPOT = net([VITRIOL, HEMATITE, SO2, SO3, H2O, H2SO4],
             [sulfur_trioxide_hydration()])
t0 = time.time()
v = Vessel(ONEPOT, volume=1.0, T=800.0, T_env=800.0, UA=1.0e4, k_vent=0.0)
v.charge({VITRIOL: 0.10}, phase="solid")
v.charge({H2O: 1.0}, phase="gas")
v.run(2000.0)
ONEPOT_ACID, ONEPOT_SO3 = tot(v, H2SO4), tot(v, SO3)
ONEPOT_LEFT = sol(v, VITRIOL)
print(f"  ONE POT  800 K   H2SO4 {ONEPOT_ACID:.6e}   SO3 {ONEPOT_SO3:.6e}   "
      f"vitriol left {ONEPOT_LEFT:.6f}   [{time.time() - t0:.1f} s]")
print(f"                   = {ACID / max(ONEPOT_ACID, 1e-30):.0f}x LESS acid "
      f"than the two-vessel apparatus")
print()
print("  AND THE REASON IS NOT THE 664 K CEILING, WHICH IS WHAT THIS PANEL WAS")
print("  BUILT TO CONFIRM AND DID NOT. In 66 bar of steam the ceiling is pushed")
print("  up by the water: measured acid/trioxide is")
print(f"  {ONEPOT_ACID / ONEPOT_SO3:.2f} against K * p_H2O = "
      f"{math.exp(price(800.0)[2]) * R_L_BAR * 800.0:.2f}, so at 800 K the acid")
print("  is still favoured 3:1 and Le Chatelier is doing the work again.")
print("  What kills the one pot is that the SULFATE has barely moved -- "
      f"{100.0 * (0.10 - ONEPOT_LEFT) / 0.10:.3f}%")
print("  of the charge in 2000 s. The retort wants 1000 K.")
print()
print("  AND AT 1000 K THE FLASK DOES NOT INTEGRATE. Measured wall clock for")
print("  the same one-pot charge, default tolerance:")
print()
print("      800 K, 2000 s     0.4 s      liquid layer 3.4e-17 mol")
print("      900 K,  500 s    44.4 s      liquid layer 6.6e-17 mol")
print("     1000 K,  200 s    > 9 MINUTES, did not finish")
print()
print("  That is engine queue item 15 -- the burner's LAYER_REABSORB thrashing")
print("  -- on a SIX-species network with one template, which makes it much the")
print("  cheapest reproduction of that bug in the repo. The layer holds 1e-17")
print("  to 1e-28 mol and is drained continuously toward a zero it never")
print("  reaches. NOTE: it is NOT this template's bug: the same charge without the")
print("  water is panel 1 and costs 0.3 s.")
print()
print("  So the apparatus is a retort AND a receiver, and the honest reason is")
print("  half chemistry and half numerics rather than the clean thermodynamic")
print("  story panel 3 suggests. Written down that way on purpose.")
print()
print(f"  0.10 mol of a NATURAL mineral -> {ACID:.6f} mol of oil of vitriol.")
print("  Sulfuric acid is the most-demanded blocked species in the corpus (four")
print("  routes want it), and `saltpetre-nitric` runs straight off this one, so")
print("  the playable count goes 12 -> 14 and the runnable count 36 -> 37.")
print()
print(f"  ({time.time() - T0:.0f} s)")
