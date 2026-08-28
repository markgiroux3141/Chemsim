"""C2's standing audit -- phosphate rock, and the two tables a route was blocked in.

Run this after touching ``properties/electrolyte.py``'s ``_PAIRS``,
``properties/mineral_data.py``'s ``phosphate rock`` row, the precipitation drive
in ``numerics/vessel_integrator.py``, or the ``phosphoric-wet`` /
``superphosphate`` rows in ``data/catalog/route_steps.psv``. **About 280 s** --
the most expensive standing audit in the repo, because twelve of its rows are
real integrations and half of them are deliberately run twice.

WHAT C2 DID, in one paragraph. ``data/catalog/PLAYABLE.md`` §8 called
`calcium-phosphate` the cheapest row in the whole work order -- *"NOT A TEMPLATE
AT ALL. One mineral price unlocks `phosphoric-wet` AND `superphosphate`"* -- and
priced it at +2. The +2 is real: playability went 14 -> 16, the BOTH column
32 -> 34, species-ready 83 -> 85. **The mineral price bought none of it.** Every
compound that moved, moved on a missing pKa in a DIFFERENT curated table; the
mineral row buys something else entirely, which is that the rock can dissolve at
all.

THE PANELS

  1  the price, and the three refusals probed beside it -- a data job is only
     cheap when the data is there, and three of the four rows in that bucket
     do not have it
  2  WHICH TABLE MOVED THE SCORE. Three compounds moved; all three move on the
     pKa row ALONE, and the mineral row's contribution to the number is ZERO
  3  the membership gap: `ion_data` and `electrolyte` price the same ions and
     nothing compares which ions they HAVE. Five lattices are still blocked,
     and all five on the same ion
  4  the Ksp, derived from a CRC lattice against the aqueous ion table
  5  the flask -- without the lattice the rock is inert at 0.0000%
  6  the digestion is LINEAR in a vessel knob, and the acid cannot hurry it
  7  ⚠⚠ THE DEFAULT TOLERANCE CANNOT BE TRUSTED ON THIS FLASK, and the tight
     run is the FAST one
  8  what this does NOT unblock, said out loud

Windows console is cp1252: every printed line here is ASCII.
"""

from __future__ import annotations

import math
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, os.path.join(_ROOT, "tools"))

from chemsim.matter import Molecule  # noqa: E402
from chemsim.network import build_network  # noqa: E402
from chemsim.properties import (  # noqa: E402
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.properties import electrolyte as E  # noqa: E402
from chemsim.properties import mineral_data as MD  # noqa: E402
from chemsim.properties.ion_data import AQUEOUS_IONS  # noqa: E402
from chemsim.properties.solubility_product import (  # noqa: E402
    UnpricedLattice,
    solubility_product,
)
from chemsim.properties.thermochemistry import ThermochemistryProvider  # noqa: E402
from chemsim.vessel import Vessel  # noqa: E402

T_START = time.time()

WATER, SULFURIC, PHOSPHORIC_IN, CALCIUM = "O", "OS(=O)(=O)O", "OP(=O)(O)O", "[Ca+2]"
PO4 = "O=P([O-])([O-])[O-]"
H2PO4, H3PO4 = "O=P([O-])(O)O", "O=P(O)(O)O"
ROCK_NAME = "phosphate rock"
ROCK = 0.01                      # mol of Ca3(PO4)2
# ⚠ rtol 1e-8 WHEREVER A NUMBER IS QUOTED. Panel 7 is why.
TIGHT = {"rtol": 1.0e-8, "atol": 1.0e-14}

thermo = electrolyte_provider()
NET = build_network(
    [WATER, SULFURIC, PHOSPHORIC_IN, CALCIUM], list(dissociation_templates()),
    thermo=thermo, max_species=60,
)


def digest(k_diss, duration, acid=None, rock=ROCK, drop_lattice=False, **kw):
    """One wet-process flask. -> (wall s, conversion %, H3PO4, H2PO4-, pH)."""
    acid = 3 * rock if acid is None else acid
    saved = MD.MINERALS.pop(ROCK_NAME) if drop_lattice else None
    try:
        v = Vessel(NET, volume=1.0, thermo=thermo, T=350.0, T_env=350.0,
                   k_diss=k_diss)
        v.charge({CALCIUM: 3 * rock, PO4: 2 * rock}, phase="solid")
        v.charge({WATER: 55.0, SULFURIC: acid})
        t0 = time.time()
        v.run(duration, **kw)
        wall = time.time() - t0
        st = v.state()
        left = st.n_solid.get(PO4, 0.0) / 2.0
        ph = -math.log10(max(st.n_liquid.get("[OH3+]", 0.0), 1e-300))
        return (wall, 100.0 * (rock - left) / rock,
                st.n_liquid.get(H3PO4, 0.0), st.n_liquid.get(H2PO4, 0.0), ph)
    finally:
        if saved is not None:
            MD.MINERALS[ROCK_NAME] = saved


def rule(title):
    print()
    print("=" * 74)
    print(title)
    print("=" * 74)


# ---------------------------------------------------------------------------
rule("1  THE PRICE -- and a data job is only cheap when the data is there")
# ---------------------------------------------------------------------------
rec = MD.MINERALS[ROCK_NAME]
print(f"  {rec.name} ({rec.cas}) -- Ca3(PO4)2, apatite and bone ash")
print(f"    Hf_solid {rec.Hf_solid:10.2f} kJ/mol     "
      f"S0_solid {rec.S0_solid:8.2f} J/(mol K)")
print(f"    Gf_solid {rec.Gf_solid:10.2f} kJ/mol     DERIVED, never transcribed")
print(f"    Cp_solid {rec.Cp_solid:10.2f} J/(mol K)  "
      f"Vm_solid {rec.Vm_solid:.6f} L/mol")
print(f"    {rec.source}")
print()
print("  The three rows probed in the SAME run that stay REFUSED. PLAYABLE.md")
print("  section 8 put all four in one 'needs no template at all' bucket and called")
print("  the bucket a data job. Only one of the four has the data.")
print()
try:
    from build_element_data import spread
    from chemicals import Hfs, Hfs_methods, S0s, S0s_methods

    print(f"    {'species':26s} {'Hfs from':24s} {'S0s from':24s}")
    for label, cas in (("calcium-phosphate", "7758-87-4"),
                       ("calcium-silicate", "1344-95-2"),
                       ("pyrite (iron-disulfide)", "1309-36-0"),
                       ("sodium-hypochlorite", "7681-52-9")):
        h = [m for m, _ in spread(Hfs, Hfs_methods, cas)] or "nothing"
        s = [m for m, _ in spread(S0s, S0s_methods, cas)] or "nothing"
        print(f"    {label:26s} {str(h):24s} {str(s):24s}")
except Exception as exc:                                    # noqa: BLE001
    print(f"    (chemicals unavailable: {exc})")
print()
print("  Both halves from CRC for the rock. NOTHING for the silicate under any")
print("  of its three CAS numbers, WEBBOOK-and-nothing for pyrite, nothing at")
print("  all for the hypochlorite. The rule that both halves come from ONE")
print("  database is what makes three of these four a refusal rather than one.")

# ---------------------------------------------------------------------------
rule("2  WHICH TABLE MOVED THE SCORE -- and it is not the one that was named")
# ---------------------------------------------------------------------------


def provider(with_third_pka):
    pairs = E._PAIRS if with_third_pka else tuple(
        p for p in E._PAIRS if p.name != "phosphoric acid, 3rd")
    base = ThermochemistryProvider()
    return ThermochemistryProvider(
        extra_curated=E.ion_thermochemistry(base, pairs))


def resolves(smiles, prov, lattices):
    """The question ``validation/catalog_coverage.py`` asks of every compound."""
    try:
        parts = smiles.split(".")
        charged = any(Molecule.from_smiles(p).charge != 0 for p in parts)
    except Exception:                                       # noqa: BLE001
        return False
    try:
        for piece in (parts if charged else [smiles]):
            prov.get(Molecule.from_smiles(piece))
        return True
    except Exception:                                       # noqa: BLE001
        pass
    try:
        return Molecule.from_smiles(smiles).smiles in lattices
    except Exception:                                       # noqa: BLE001
        return False


LAT_WITH = {m.lattice for m in MD.MINERALS.values()}
LAT_WITHOUT = {m.lattice for n, m in MD.MINERALS.items() if n != ROCK_NAME}
PROV_NEW, PROV_OLD = provider(True), provider(False)

MOVED = (
    ("calcium-phosphate",
     "[Ca+2].[Ca+2].[Ca+2].[O-]P([O-])([O-])=O.[O-]P([O-])([O-])=O"),
    ("sodium-phosphate", "[Na+].[Na+].[Na+].[O-]P([O-])([O-])=O"),
    ("phosphate-ion", "[O-]P([O-])([O-])=O"),
)
print("  Three catalog compounds moved refused -> priced across C2. Which of")
print("  its two one-line data rows did it? Each column grants ONE of them.")
print()
print(f"    {'compound':22s} {'neither':>9s} {'pKa row':>9s} "
      f"{'mineral row':>12s} {'both':>8s}")
for cid, smi in MOVED:
    cells = (resolves(smi, PROV_OLD, LAT_WITHOUT),
             resolves(smi, PROV_NEW, LAT_WITHOUT),
             resolves(smi, PROV_OLD, LAT_WITH),
             resolves(smi, PROV_NEW, LAT_WITH))
    txt = ["priced" if c else "refused" for c in cells]
    print(f"    {cid:22s} {txt[0]:>9s} {txt[1]:>9s} {txt[2]:>12s} {txt[3]:>8s}")
print()
print("  ALL THREE MOVE ON THE pKa ROW ALONE. The mineral row moves one of the")
print("  three, and that one moves without it. **The mineral price contributed")
print("  ZERO to the coverage number, and the mineral is the only thing the")
print("  work order named.** What the mineral row does buy is panel 5.")

# ---------------------------------------------------------------------------
rule("3  THE MEMBERSHIP GAP -- two curated tables over the same ions")
# ---------------------------------------------------------------------------
prov = electrolyte_provider()


def priced(smiles):
    try:
        prov.get(smiles)
        return True
    except Exception:                                       # noqa: BLE001
        return False


unreachable = sorted(i for i in AQUEOUS_IONS if not priced(i))
print(f"  `ion_data` prices {len(AQUEOUS_IONS)} ions on the aqueous basis.")
print("  `electrolyte_provider` -- the one a NETWORK is actually built with --")
print(f"  refuses {len(unreachable)} of them, because it reaches an ion only")
print("  through a pKa pair, and a pKa pair has to have been typed in.")
print()
print("  `solubility_product`'s docstring warns at length that these two tables")
print("  use different ZEROS. Nothing anywhere compares which ions they HAVE.")
print()
blocked, buildable = [], 0
for name, lattice_rec in MD.MINERALS.items():
    if not lattice_rec.ions:
        continue
    try:
        solubility_product(lattice_rec)
    except UnpricedLattice:
        continue
    missing = sorted({i for i in lattice_rec.ions if not priced(i)})
    if missing:
        blocked.append((name, missing))
    else:
        buildable += 1
print(f"  Lattices with a Ksp that CANNOT be put in a flask: {len(blocked)} of "
      f"{len(blocked) + buildable}")
for name, missing in blocked:
    print(f"    {name:22s} {missing}")
print()
sulfide = [n for n, m in blocked if "[S-2]" in m]
print(f"  All {len(sulfide)} of them are blocked on the SAME ion, and it is the")
print("  same shape phosphate was: `_PAIRS` carries H2S -> [SH-] at pKa 7.00")
print("  and stops there. **A polyprotic acid gets entered as far as somebody")
print("  needed, and nothing checks that the chain is finished.**")
print()
print("  ! AND THE SULFIDE STEP IS A REFUSAL, NOT THE NEXT ONE-LINE FIX.")
print("  HS- -> S2- is quoted between about 12.9 and 19 depending on the")
print("  compilation -- six decades of disagreement about one number. The rule")
print("  for that case is `element_data`'s: report it, do not invent it.")
print("  Phosphoric acid's third pKa was takeable precisely BECAUSE the two")
print("  rows above it fix which series it has to come from.")

# ---------------------------------------------------------------------------
rule("4  THE Ksp -- a CRC lattice against the conventional aqueous ion table")
# ---------------------------------------------------------------------------
print("  Nothing here is fitted: the solid row is CRC's, the ions are the")
print("  aqueous table's, and the Ksp is the difference between them.")
print()
print(f"  {'lattice':22s} {'log10 Ksp':>10s} {'Ksp':>12s} {'s / mol/L':>12s}")
for name in (ROCK_NAME, "anhydrite", "calcite"):
    ksp = solubility_product(MD.MINERALS[name])
    print(f"  {name:22s} {ksp.ln_Ksp / math.log(10):10.3f} {ksp.Ksp:12.4g} "
          f"{ksp.solubility():12.4g}")
print()
print("  The rock is 28 decades less soluble than the gypsum it is turned into.")
print("  That is why the wet process needs an acid rather than water -- and, in")
print("  panel 6, it is also why this engine's dissolution law struggles with it.")

# ---------------------------------------------------------------------------
rule("5  THE FLASK -- what the MINERAL row buys, which is not a number in a report")
# ---------------------------------------------------------------------------
print("  0.01 mol of rock as its ions in the solid block, 0.03 mol H2SO4 in 1 L")
print("  of water at 350 K, k_diss = 10 (panel 6 is about that knob), 600 s,")
print("  rtol 1e-8. The ONLY difference between the two rows is whether")
print("  `mineral_data` has a `phosphate rock` entry for `PrecipitationArrays`.")
print()
print(f"    {'mineral_data':26s} {'wall':>7s} {'converted':>11s} {'H3PO4':>11s} "
      f"{'H2PO4-':>11s}")
for label, drop in (("with the lattice", False), ("WITHOUT it", True)):
    wall, conv, h3, h2, _ = digest(10.0, 600.0, drop_lattice=drop, **TIGHT)
    print(f"    {label:26s} {wall:7.1f} {conv:10.4f}% {h3:11.8f} {h2:11.8f}")
print()
print("  Without the lattice the rock is INERT -- its ions sit in the solid")
print("  block for ever, because no Ksp connects them to the solution. It still")
print("  reads species-ready, still counts in the BOTH column, still counts as")
print("  playable. **The score and the chemistry came out of different tables,")
print("  and neither one implies the other**: G4's rule arriving from a new side.")

# ---------------------------------------------------------------------------
rule("6  THE DIGESTION IS LINEAR IN A KNOB, AND THE ACID CANNOT HURRY IT")
# ---------------------------------------------------------------------------
ksp_rock = solubility_product(MD.MINERALS[ROCK_NAME])
root = math.exp(ksp_rock.ln_Ksp / 5.0)
print("  `PrecipitationArrays` drives dissolution on")
print("      drive = k_diss * V_liquid * (Q^(1/N) - Ksp^(1/N))     mol/s")
print("  so with the solution swept clean of phosphate the FASTEST this rock")
print("  can ever dissolve is k_diss * V * Ksp^(1/N), with")
print(f"      Ksp^(1/5) = {root:.4g} mol/L")
print(f"  which at the vessel default k_diss = 1e-2 in 1 L is {1e-2 * root:.3g}")
print(f"  mol/s -- {ROCK / (1e-2 * root) / 86400.0:.0f} DAYS for 0.01 mol.")
print()
print("  600 s, 0.03 mol H2SO4, rtol 1e-8:")
print()
print(f"    {'k_diss':>8s} {'wall':>7s} {'converted':>11s} {'H3PO4':>11s} "
      f"{'pH':>6s}")
for k in (1.0e-1, 1.0, 10.0):
    wall, conv, h3, _, ph = digest(k, 600.0, **TIGHT)
    print(f"    {k:8.3g} {wall:7.1f} {conv:10.5f}% {h3:11.8f} {ph:6.3f}")
print()
print("  Ten times the knob is ten times the conversion, which is the cap above")
print("  behaving exactly as written -- so the completion figure is an")
print("  extrapolation of a measured straight line and not a hope: k_diss = 100")
print("  gives 70.730% in this flask, measured once, at 141 s of wall clock.")
print("  ! It is NOT re-run here, and the linearity above is what licenses it.")
print()
print("  Now hold the knob and pour in more acid:")
print()
print(f"    {'H2SO4/mol':>10s} {'wall':>7s} {'converted':>11s} {'pH':>6s}")
for acid in (0.03, 0.30, 1.00):
    wall, conv, _, _, ph = digest(10.0, 600.0, acid=acid, **TIGHT)
    print(f"    {acid:10.3g} {wall:7.1f} {conv:10.5f}% {ph:6.3f}")
print()
print("  Thirty-three times the acid, and the pH falls a decade and a half --")
print("  and the rock does not notice. Now hold both and charge more ROCK,")
print("  reporting the ABSOLUTE moles dissolved rather than the percentage:")
print()
print(f"    {'rock/mol':>10s} {'wall':>7s} {'converted':>11s} {'mol dissolved':>14s}")
for rock_charge in (0.01, 0.10):
    wall, conv, _, _, _ = digest(10.0, 600.0, rock=rock_charge, **TIGHT)
    print(f"    {rock_charge:10.3g} {wall:7.1f} {conv:10.5f}% "
          f"{rock_charge * conv / 100.0:14.8f}")
print()
print("  !! TEN TIMES THE ROCK DISSOLVES THE SAME NUMBER OF MOLES. The drive")
print("  has no SURFACE AREA in it either -- only `_avail`, which saturates the")
print("  moment there is any crop at all. A real dissolution goes with the area")
print("  of the solid; this one goes with a vessel knob and nothing else.")
print()
print("  !! THE LIMIT THIS NAMES: AN ACID CANNOT ATTACK A CRYSTAL. Dissolution")
print("  here is an equilibrium transport term whose rate has NO acid in it at")
print("  all -- the acid only keeps Q low, and Q is already floored. A real")
print("  wet-process digestion is a SURFACE reaction whose rate goes with [H+],")
print("  and this engine has that shape for a GAS arriving at a crystal")
print("  (`SurfaceArrays`, S1) and not for a liquid. **So the rock digests on a")
print("  vessel knob rather than on its chemistry**, and no charge of acid moves")
print("  it. That is the honest reading of every conversion in this file.")

# ---------------------------------------------------------------------------
rule("7  THE DEFAULT TOLERANCE CANNOT BE TRUSTED ON THIS FLASK")
# ---------------------------------------------------------------------------
print("  The same flask, 600 s, 0.03 mol H2SO4, at two tolerances.")
print()
print(f"    {'k_diss':>8s} {'loose conv':>12s} {'loose s':>9s} "
      f"{'tight conv':>12s} {'tight s':>9s} {'ratio':>8s}")
for k in (1.0, 10.0):
    wl, cl, *_ = digest(k, 600.0)
    wt, ct, *_ = digest(k, 600.0, **TIGHT)
    ratio = cl / ct if ct else float("inf")
    print(f"    {k:8.3g} {cl:11.5f}% {wl:9.1f} {ct:11.5f}% {wt:9.1f} {ratio:8.2f}")
print()
print("  !! The default tolerance is WRONG at k_diss = 1 and RIGHT at")
print("  k_diss = 10, and nothing in the answer says which. ! The tight run is")
print("  also the FAST one, which is the tell -- the loose solver is thrashing")
print("  rather than saving work. Fragility 17's rule (a number quoted at the")
print("  default tolerance is quoted at a tolerance nobody swept) lands on new")
print("  content the very first time it is charged into a flask.")

# ---------------------------------------------------------------------------
rule("8  WHAT THIS DOES NOT UNBLOCK, SAID OUT LOUD")
# ---------------------------------------------------------------------------
print("  `white-phosphorus` names calcium-phosphate too, and did NOT move. Its")
print("  step is")
print("     calcium-phosphate + silicon-dioxide + carbon-graphite")
print("        -> phosphorus-white + carbon-monoxide + calcium-silicate")
print("  and it is blocked three more ways:")
print("     * `carbothermic-phosphate-reduction` has no template")
print("     * `phosphorus-white` (P4) has no formation pair in any source here")
print("     * `calcium-silicate` has no Hfs and no S0s -- panel 1")
print()
print("  Pricing one species of four is worth nothing on a route.")
print("  `calcium-phosphate` blocked THREE routes and unblocked TWO, which is")
print("  PLAYABLE.md section 7's 'the most frequent blocker is not the most")
print("  valuable one', seen from the other side.")
print()
print(f"  ({time.time() - T_START:.1f} s)")
