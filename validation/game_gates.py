"""The four probes behind GAME_DESIGN.md, as a harness rather than as quotes.

Sections 2, 4, 5 and 6 of ``GAME_DESIGN.md`` each rest on numbers that were
measured inline in a design session and never saved. This project's own rule is
that a quoted number is a number that has started to drift, so they live here:

    PANEL 1   the DILUTION GATE            GAME_DESIGN section 2
    PANEL 2   the STIFFNESS table          GAME_DESIGN section 4
    PANEL 3   CHAIN 1 coverage             GAME_DESIGN section 5
    PANEL 4   the ELEMENT / MINERAL floor  GAME_DESIGN section 6

Panel 4 is the one that had a live bug in it, and it is deliberately written to
find that CLASS of bug rather than to check one species: it asks every elemental
species whether the provider prices it, and compares the answer against the
value a reference state must have BY DEFINITION. An estimator confidently
pricing a reference state is a DETECTABLE error rather than a judgement call,
which is what makes this panel a test and not a table.

Windows console is cp1252, so every printed character here is ASCII. (Recorded
in five consecutive handoffs, and it has bitten inside a validation harness.)

    python validation/game_gates.py
"""

from __future__ import annotations

import math

from chemsim.constants import R
from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties.electrolyte import (
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.reactions import esterification
from chemsim.vessel import Vessel

BAR = "=" * 78

ACOH, ETOH, WATER, ESTER, N2 = "CC(=O)O", "CCO", "O", "CCOC(C)=O", "N#N"


# ---------------------------------------------------------------------------
# PANEL 1 -- the dilution gate
# ---------------------------------------------------------------------------
# Water is a PRODUCT of a reversible template, so a dilute feed caps its own
# conversion by Le Chatelier. Nothing reads a concentration and decides an
# outcome; the equilibrium moves because the product is already in the flask.
#
# The charge is deliberately NOT stoichiometric -- 0.83 mol acid against 2.05
# mol ethanol is an ordinary bench ratio -- and holding it fixed while varying
# ONLY the water is what makes the three rows comparable.
def dilution_gate() -> list[tuple[float, float, float]]:
    thermo = ThermochemistryProvider()
    net = build_network(
        [ACOH, ETOH, WATER, N2], [esterification()],
        thermo=thermo, max_species=50,
    )
    rows = []
    for water in (50.0, 12.0, 3.0):
        v = Vessel(net, volume=3.0, T=353.0, T_env=353.0, UA=1.0e4,
                   kla=1.0, k_vent=0.0, k_diss=0.0)
        v.charge({ACOH: 0.83, ETOH: 2.05, WATER: water, N2: 0.02})
        v.run(7200.0)
        ester = v.state().total(ESTER)
        rows.append((water, ester, 100.0 * ester / 0.83))
    return rows


def panel_dilution() -> None:
    print(BAR)
    print("PANEL 1 -- THE DILUTION GATE  (GAME_DESIGN section 2)")
    print(BAR)
    print("   0.83 mol acetic acid + 2.05 mol ethanol, 353 K, sealed under N2,")
    print("   2 h. The ONLY thing that varies is the water charged.")
    print()
    print(f"   {'water / mol':>12s} {'ester / mol':>12s} {'conversion':>12s}")
    for water, ester, conv in dilution_gate():
        print(f"   {water:12.1f} {ester:12.4f} {conv:11.1f}%")
    print()
    print("   No threshold anywhere. Water is a PRODUCT of a reversible")
    print("   template, so a dilute feed caps its own conversion. This is what")
    print("   a purity gate looks like when it is a MECHANISM.")


# ---------------------------------------------------------------------------
# PANEL 2 -- where the time goes
# ---------------------------------------------------------------------------
# Cost is concentrated in stiff transients, and the stiffness is ALL acid/base
# recombination. This panel sizes the prize before anyone spends the largest
# piece of engine work on the list (dissociation as an equilibrium rather than
# an integration) -- GAME_DESIGN section 4.
def stiffness_table(T: float = 298.15) -> list[tuple[str, float]]:
    thermo = ThermochemistryProvider()
    vol = VolatilityProvider(thermo)
    ions = electrolyte_provider(base=thermo, volatility=vol)
    net = build_network(
        [ACOH, ETOH, WATER, N2],
        [esterification(), *dissociation_templates()],
        thermo=ions, volatility=vol, max_species=60,
    )
    out = []
    for rxn in net.reactions:
        k = rxn.A * (T ** rxn.n_exp) * math.exp(-rxn.Ea / (R * T))
        out.append((f"{rxn.name} [{rxn.phase}]", k))
    return sorted(out, key=lambda kv: -kv[1])


def panel_stiffness() -> None:
    print()
    print(BAR)
    print("PANEL 2 -- THE STIFFNESS RATIO  (GAME_DESIGN section 4)")
    print(BAR)
    print("   Every rate constant in an aqueous acid network at 298 K, sorted.")
    print()
    rows = stiffness_table()
    for name, k in rows:
        print(f"   {k:12.3e}   {name}")
    lo = min(k for _, k in rows if k > 0.0)
    hi = max(k for _, k in rows)
    print()
    print(f"   ratio  {hi / lo:.2e}   over {len(rows)} reactions")
    print("   The engine resolves the fastest of those timescales in order to")
    print("   compute a proton concentration. The value integrating gives IS")
    print("   the equilibrium value, so solving it at step boundaries would be")
    print("   a SKIPPED TRANSIENT rather than an approximation -- and the five")
    print("   pH invariants are then the regression test for having done it.")


# ---------------------------------------------------------------------------
# PANEL 3 -- chain 1 coverage
# ---------------------------------------------------------------------------
CHAIN1 = [
    ("methyl salicylate", "COC(=O)c1ccccc1O"),
    ("salicylic acid", "OC(=O)c1ccccc1O"),
    ("aspirin", "CC(=O)Oc1ccccc1C(=O)O"),
    ("acetic acid", "CC(=O)O"),
    ("acetic anhydride", "CC(=O)OC(C)=O"),
    ("salicylaldehyde", "O=Cc1ccccc1O"),
    ("methanol", "CO"),
    ("salicylate ion", "[O-]C(=O)c1ccccc1O"),
    ("acetylsalicylate ion", "CC(=O)Oc1ccccc1C(=O)[O-]"),
    ("acetate ion", "CC(=O)[O-]"),
    ("carbonate ion", "[O-]C(=O)[O-]"),
    ("bicarbonate ion", "OC(=O)[O-]"),
    ("hydroxide", "[OH-]"),
]


def panel_chain1() -> None:
    print()
    print(BAR)
    print("PANEL 3 -- CHAIN 1 COVERAGE  (GAME_DESIGN section 5)")
    print(BAR)
    thermo = ThermochemistryProvider()
    vol = VolatilityProvider(thermo)
    ions = electrolyte_provider(base=thermo, volatility=vol)
    print(f"   {'species':22s} {'Gf kJ/mol':>10s} {'Tm K':>8s}  source")
    weak = []
    for name, smi in CHAIN1:
        mol = Molecule.from_smiles(smi)
        picked = ions if mol.charge != 0 else thermo
        try:
            d = picked.get(mol)
        except Exception as exc:                            # noqa: BLE001
            print(f"   {name:22s} {'REFUSED':>10s} {'--':>8s}  {str(exc)[:36]}")
            continue
        tm = f"{d.Tm:.1f}" if d.Tm else "--"
        print(f"   {name:22s} {d.Gf:10.1f} {tm:>8s}  {d.source[:40]}")
        if "Joback" in d.source.split(";")[0]:
            weak.append(name)
    print()
    print("   Steps 1-3 are the flagship prep with different species and need")
    print("   no new mechanics.")
    if weak:
        print(f"   WEAKEST FORMATION HALVES (Joback): {', '.join(weak)}")
        print("   A curated overlay is the fix -- the same job _CURATED_FUSION")
        print("   already does for four solids.")


# ---------------------------------------------------------------------------
# PANEL 4 -- the floor
# ---------------------------------------------------------------------------
# THE ELEMENTS. For an element in its standard state the data is FREE AND
# EXACT: Hf = Gf = 0, no source, no cross-check possible or needed. So an
# estimator returning non-zero for a reference state is a DETECTABLE ERROR.
#
# The standard state is not always the obvious one, and getting it wrong is the
# same bug one level up: S is rhombic S8(s), C is graphite, P is white, Br2 and
# Hg are LIQUIDS, and H/N/O/F/Cl are diatomic gases. A ThermoData in this
# project is on the IDEAL-GAS basis, so only the species whose reference state
# IS the gas are exactly zero -- a condensed reference state's gas-phase value
# is its sublimation energy, which is a real measured number and must not be
# pinned to zero. ``exact`` below is None for exactly those.
ELEMENTS = [
    # name, SMILES, standard-state phase, exact ideal-gas Gf where one exists
    ("H2", "[H][H]", "gas", 0.0),
    ("N2", "N#N", "gas", 0.0),
    ("O2", "O=O", "gas", 0.0),
    ("F2", "FF", "gas", 0.0),
    ("Cl2", "ClCl", "gas", 0.0),
    ("Br2", "BrBr", "liquid", None),
    ("I2", "II", "solid", None),
    ("S8 rhombic", "S1SSSSSSS1", "solid", None),
    ("P4 white", "P1PPP1", "solid", None),
    ("graphite", "[C]", "solid", None),
    ("Hg", "[Hg]", "liquid", None),
    ("Na", "[Na]", "solid", None),
    ("K", "[K]", "solid", None),
    ("Ca", "[Ca]", "solid", None),
    ("Fe", "[Fe]", "solid", None),
    ("Cu", "[Cu]", "solid", None),
    ("Zn", "[Zn]", "solid", None),
    # NOT reference states: elemental, but a different allotrope or atomicity.
    # These have real measured values and pinning them to zero would be the
    # same error in the opposite direction.
    ("S atom (g)", "[S]", "not a ref state", None),
    ("S2 (g)", "S=S", "not a ref state", None),
    ("ozone", "[O-][O+]=O", "not a ref state", None),
]

MINERALS = [
    ("CaCO3 limestone", "[Ca+2].[O-]C(=O)[O-]"),
    ("CaO quicklime", "[Ca+2].[O-2]"),
    ("Ca(OH)2 slaked lime", "[Ca+2].[OH-].[OH-]"),
    ("FeSO4 green vitriol", "[Fe+2].[O-]S(=O)(=O)[O-]"),
    ("FeS2 pyrite", "[Fe+2].[S-][S-]"),
    ("K2CO3 potash", "[K+].[K+].[O-]C(=O)[O-]"),
    ("KNO3 saltpetre", "[K+].[O-][N+](=O)[O-]"),
    ("NaCl salt", "[Na+].[Cl-]"),
    ("Na2CO3 soda", "[Na+].[Na+].[O-]C(=O)[O-]"),
    ("KHSO4", "[K+].[O-]S(=O)(=O)O"),
]


def _price(provider, smiles):
    """(Gf, source) or (None, refusal) for one species."""
    try:
        d = provider.get(Molecule.from_smiles(smiles))
    except Exception as exc:                                # noqa: BLE001
        return None, str(exc)
    return d.Gf, d.source


def panel_floor() -> None:
    print()
    print(BAR)
    print("PANEL 4 -- THE FLOOR  (GAME_DESIGN section 6)")
    print(BAR)
    thermo = ThermochemistryProvider()
    vol = VolatilityProvider(thermo)
    ions = electrolyte_provider(base=thermo, volatility=vol)

    print("   ELEMENTS. For a reference state the data is FREE AND EXACT, so a")
    print("   non-zero answer where the exact value is 0 is a DETECTED ERROR --")
    print("   which is why this panel prints a verdict and not just a number.")
    print()
    print(f"   {'element':16s} {'ref state':16s} {'plain Gf':>10s} "
          f"{'elec Gf':>10s}  {'verdict':8s} source")
    wrong = 0
    for name, smi, phase, exact in ELEMENTS:
        gp, sp = _price(thermo, smi)
        ge, _ = _price(ions, smi)
        if gp is None:
            verdict, note = "REFUSED", "-"
        elif exact is None:
            verdict, note = "priced", sp[:34]
        elif abs(gp - exact) < 1.0e-9:
            verdict, note = "EXACT", sp[:34]
        else:
            verdict, note = "WRONG", sp[:34]
            wrong += 1
        gps = f"{gp:10.1f}" if gp is not None else f"{'--':>10s}"
        ges = f"{ge:10.1f}" if ge is not None else f"{'--':>10s}"
        print(f"   {name:16s} {phase:16s} {gps} {ges}  {verdict:8s} {note}")
    print()
    print(f"   {wrong} element(s) priced non-zero where the exact answer is 0.")

    print()
    print("   MINERALS, ion by ion. A salt is not a molecule: it resolves when")
    print("   every ion it dissociates into resolves.")
    print()
    print(f"   {'mineral':22s} {'plain Gf':>10s} {'elec Gf':>10s}  "
          f"which ion refused")
    split = 0
    for name, smi in MINERALS:
        cells = []
        for prov in (thermo, ions):
            total, missing = 0.0, []
            for part in smi.split("."):
                g, _ = _price(prov, part)
                if g is None:
                    missing.append(part)
                else:
                    total += g
            cells.append((None if missing else total, missing))
        (gp, _mp), (ge, me) = cells
        if gp is not None and ge is not None and abs(gp - ge) > 1.0:
            split += 1
        gps = f"{gp:10.1f}" if gp is not None else f"{'REFUSED':>10s}"
        ges = f"{ge:10.1f}" if ge is not None else f"{'REFUSED':>10s}"
        print(f"   {name:22s} {gps} {ges}  {' '.join(me) if me else '-'}")
    print()
    print(f"   {split} mineral(s) price DIFFERENTLY under the two providers.")
    print("   Two answers for one species is the shape of thing that goes")
    print("   quietly wrong: a network that cannot price an ion should REFUSE")
    print("   it, not answer differently from one that can.")


def panel_reference_check() -> None:
    """The one INDEPENDENT check available on a condensed reference state.

    A gaseous reference state is exactly zero and no check is possible or
    needed. A CONDENSED one is zero in its own phase, so shifting the ideal-gas
    record back down must return zero:

        Gf(g) + R T ln(Psat/P_std) - Hfus*(1 - T/Tm)  ==  0

    and nothing in that expression touched the formation table -- Psat comes
    from Tb/Tc/Pc through Lee-Kesler and Hfus/Tm are separate measurements. It
    is the same shape as ``formation_data``'s two cross-checks and it is what
    makes Br2 = +3.08 and I2 = +19.29 measurements rather than assertions.
    """
    from chemsim.properties import standard_state
    from chemsim.properties.element_data import ELEMENTAL

    print()
    print(BAR)
    print("PANEL 4b -- THE REFERENCE-STATE CROSS-CHECK")
    print(BAR)
    thermo = ThermochemistryProvider()
    vol = VolatilityProvider(thermo)
    print("   Gf(g) + RT ln(Psat/P0) - Hfus*(1 - T/Tm)  must come back to 0,")
    print("   and no term in it touched the formation table.")
    print()
    print(f"   {'species':10s} {'phase':6s} {'Gf(g)':>8s} {'RTlnPsat':>9s} "
          f"{'dGfus':>7s} {'residual':>9s}  Psat / bar")
    for smi, rec in ELEMENTAL.items():
        if not rec.reference_state or rec.reference_phase == "g":
            continue                      # exactly zero; nothing to check
        d = thermo.get(smi)
        s = standard_state.shift(smi, vol)
        psat = vol.get(smi).coefficient(298.15)
        dgfus = 0.0
        if rec.reference_phase == "s" and rec.Hfus and rec.Tm:
            dgfus = rec.Hfus * max(0.0, 1.0 - 298.15 / rec.Tm)
        res = d.Gf + s.dGf - dgfus
        print(f"   {rec.name:10s} {rec.reference_phase:6s} {d.Gf:8.2f} "
              f"{s.dGf:9.2f} {dgfus:7.2f} {res:9.2f}  {psat:.3e}")
    print()
    print("   Bromine and iodine close to 0.05 / 0.14 kJ/mol, which is what")
    print("   makes their ideal-gas values measurements rather than claims --")
    print("   and with the OLD pinned 0.0 the residuals would have been -3.14")
    print("   and -19.15, so the check would have caught the error that was")
    print("   sitting in this repo.")
    print()
    print("   SULFUR IS THE WEAK ROW AND THE HARNESS SAYS SO. Its residual is")
    print("   ~3 kJ/mol because Lee-Kesler is being extrapolated from Tb =")
    print("   717.8 K down to Tr = 0.23, and because liquid sulfur's vapour is")
    print("   not S8 -- it is an S8/S6/S2 equilibrium that shifts with")
    print("   temperature. So this row is a SANITY BOUND, not a confirmation,")
    print("   and S8's vapour-pressure curve is the weakest number in chain 2.")
    print("   A gaseous reference state is skipped entirely: it is exactly zero")
    print("   and there is no independent quantity to check it against.")


if __name__ == "__main__":
    panel_dilution()
    panel_stiffness()
    panel_chain1()
    panel_floor()
    panel_reference_check()
