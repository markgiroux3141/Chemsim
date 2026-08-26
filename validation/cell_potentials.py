"""M8's standing audit: what voltage does this project think each cell needs?

Run after touching ``reactions/electrochemistry.py``, the ion table, or the
standard-state shift. Seconds.

WHY THIS FILE EXISTS AT ALL, AND IT IS NOT A UNIT TEST IN DISGUISE

The decomposition potential is the one number M8's whole mechanic turns on, and
it is DERIVED -- from formation data, through a standard-state shift, through an
ion table built from pKa values, and finally divided by ``n F``. Nothing in this
project curates an electrode potential, which is exactly the property worth
having and exactly the property that can rot without anyone noticing: every
input to it is maintained for other reasons.

So the audit compares against the electrochemical series, which is an INDEPENDENT
measurement -- nothing below feeds anything in ``src/``. A drift here is a claim
about the thermochemistry, not about this file.

⚠⚠ **AND IT ALREADY FOUND SOMETHING. READ PANEL 2 BEFORE QUOTING PANEL 1.** dG
survives and dS does not. The brine cell's E_dec lands 0.176 V above the book --
8%, fine -- while its dS is out by hundreds of J/(mol K), which is not a small
error wearing a big number: it REVERSES the sign of dE/dT, so every cell in this
engine needs more voltage when heated and every real one needs less.

The cause is a MIXED BASIS that has never had to cancel before. This project's
ions are derived from measured pKa values against its OWN water reference, and
its own water is priced on the IDEAL-GAS basis (Hf -241.8, not the aqueous
-285.8). For a reaction that conserves water the offset drops out and nothing
notices; **every cell reaction here consumes water and makes hydroxide**, so it
does not. Pre-existing since the electrolyte model was built, and M8 is the first
mechanism to depend on it.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rdkit import RDLogger  # noqa: E402

from chemsim.constants import FARADAY, R  # noqa: E402
from chemsim.properties import ThermochemistryProvider  # noqa: E402
from chemsim.properties.electrolyte import electrolyte_provider  # noqa: E402
from chemsim.properties.volatility import VolatilityProvider  # noqa: E402
from chemsim.reactions import electrochemistry  # noqa: E402
from chemsim.reactions.reaction import ConcreteReaction  # noqa: E402
from chemsim.reactions.thermo import (  # noqa: E402
    decomposition_potential,
    reaction_deltas,
)

# The electrode templates build products with no mapped atoms -- H2 and O2 are
# created fresh rather than tracked, because mapping a hydrogen would need it
# written as an atom and ``run``'s RemoveHs would then look for a heavy
# neighbour it does not have. RDKit says so once per template at Initialize;
# ``validation/catalog_coverage.py`` sets the same precedent for a reporting
# script. It is NOT set anywhere under ``src/``, where a real warning matters.
RDLogger.DisableLog("rdApp.*")

T_REF = 298.15

# The cells, written as they balance, with the electron count they pass and the
# electrochemical series' own answer.
#
# ! THE BOOK COLUMN IS NOT A TARGET AND MUST NOT BECOME ONE. It is standard
# electrode potentials at unit activity, 298 K; this project computes a
# pure-liquid-standard-state dG for a real mixture. They should agree to a few
# tenths of a volt and disagreeing by more is a finding, not a bug to close by
# moving a number in ``src/``.
CELLS = [
    (
        "water splitting", "2 H2O -> 2 H2 + O2",
        ("O", "O"), ("[H][H]", "[H][H]", "O=O"), 4,
        1.229, "O2/H2O +1.229 against H+/H2 0.000",
    ),
    (
        "brine (chloralkali)", "2 Cl- + 2 H2O -> Cl2 + H2 + 2 OH-",
        ("[Cl-]", "[Cl-]", "O", "O"),
        ("ClCl", "[H][H]", "[OH-]", "[OH-]"), 2,
        2.186, "Cl2/Cl- +1.358 against H2O/H2,OH- -0.828",
    ),
    (
        "bromide", "2 Br- + 2 H2O -> Br2 + H2 + 2 OH-",
        ("[Br-]", "[Br-]", "O", "O"),
        ("BrBr", "[H][H]", "[OH-]", "[OH-]"), 2,
        1.894, "Br2/Br- +1.066 against H2O/H2,OH- -0.828",
    ),
    (
        "Kolbe (acetate)", "2 AcO- + 2 H2O -> C2H6 + 2 CO2 + H2 + 2 OH-",
        ("CC([O-])=O", "CC([O-])=O", "O", "O"),
        ("CC", "O=C=O", "O=C=O", "[H][H]", "[OH-]", "[OH-]"), 2,
        None, "no tabulated couple -- the Kolbe radical is not a reversible one",
    ),
    (
        "adiponitrile (the whole cell)", "4 AN + 2 H2O -> 2 ADN + O2",
        ("C=CC#N", "C=CC#N", "C=CC#N", "C=CC#N", "O", "O"),
        ("N#CCCCCC#N", "N#CCCCCC#N", "O=O"), 4,
        None, "not a tabulated couple; see panel 4",
    ),
]

# Cell -> its template's declared activation overpotential, volts. Kept here
# rather than imported so the audit reads what was DECLARED and not what a
# helper recomputed.
ETA_A = {
    "water splitting": 0.80,
    "brine (chloralkali)": 0.40,
    "bromide": 0.40,
    "Kolbe (acetate)": 1.20,
}

SWEEP = (0.0, 1.5, 2.0, 2.5, 3.0, 4.0)


def _rxn(reactants, products) -> ConcreteReaction:
    return ConcreteReaction("audit", reactants, products, A=1.0, Ea=0.0,
                            phase="liquid")


def main() -> int:
    base = ThermochemistryProvider()
    vol = VolatilityProvider(base)
    prov = electrolyte_provider(base=base, volatility=vol)

    print("=" * 78)
    print("PANEL 1 -- THE DECOMPOSITION POTENTIALS, DERIVED")
    print("=" * 78)
    print("  E_dec = dG_chem / (n F). Nothing here reads a table of electrode")
    print("  potentials; the 'book' column is the independent check.")
    print()
    print(f"  {'cell':30s} {'n':>2s} {'dG kJ/mol':>10s} {'E_dec':>7s} "
          f"{'book':>7s} {'diff':>7s}")
    rows = []
    for name, eqn, r, p, n, book, _ in CELLS:
        rx = _rxn(r, p)
        dH, dG = reaction_deltas(rx, prov, vol)
        E = decomposition_potential(rx, prov, n, T_REF, vol)
        rows.append((name, eqn, n, dH, dG, E, book))
        bk = f"{book:7.3f}" if book is not None else "     --"
        df = f"{E - book:+7.3f}" if book is not None else "     --"
        print(f"  {name:30s} {n:2d} {dG:10.1f} {E:7.3f} {bk} {df}")
    print()
    for name, eqn, n, *_ in rows:
        print(f"    {name:30s} {eqn}")

    print()
    print("=" * 78)
    print("PANEL 2 -- THE ENTROPY, WHICH IS THE ONE THAT IS WRONG")
    print("=" * 78)
    print("  dS = (dH - dG)/T is what fixes K(T), so it is what fixes how E_dec")
    print("  moves with temperature. The book value for the brine cell is about")
    print("  +80 J/(mol K): heat a chloralkali cell and it needs LESS voltage,")
    print("  which is one reason a real one runs near 360 K.")
    print()
    # Book dS, J/(mol K), from the same aqueous-convention data the book E_dec
    # comes from. None where there is no book value to build one out of.
    BOOK_dS = {"water splitting": 326.6, "brine (chloralkali)": 79.9,
               "bromide": 121.6}
    print(f"  {'cell':30s} {'dH kJ/mol':>10s} {'dS':>9s} {'book dS':>9s} "
          f"{'error':>9s} {'E(298)':>8s} {'E(360)':>8s} {'dE/dT':>8s}")
    dS_error = {}
    for (name, eqn, n, dH, dG, E, book), (_, _, r, p, *_) in zip(rows, CELLS):
        dS = (dH - dG) * 1000.0 / T_REF
        E360 = decomposition_potential(_rxn(r, p), prov, n, 360.0, vol)
        bs = BOOK_dS.get(name)
        if bs is None:
            bcol, ecol = "       --", "       --"
        else:
            dS_error[name] = dS - bs
            bcol, ecol = f"{bs:9.1f}", f"{dS - bs:+9.1f}"
        print(f"  {name:30s} {dH:10.1f} {dS:9.1f} {bcol} {ecol} "
              f"{E:8.3f} {E360:8.3f} {(E360 - E) / 61.85 * 1000:+8.3f}")
    print()
    print("  units: dS J/(mol K), E volts, dE/dT mV/K.")
    print()
    worst_dS = max(dS_error.items(), key=lambda kv: abs(kv[1]))
    print(f"  !! THE dS COLUMN IS THE ONE THAT IS WRONG: worst is "
          f"{worst_dS[0]}")
    print(f"  at {worst_dS[1]:+.1f} J/(mol K), which REVERSES the sign of dE/dT --")
    print("  every cell here needs MORE voltage when heated and every real one")
    print("  needs less. The cause is a MIXED BASIS that does not cancel:")
    for smi, label, bookH in (("[Cl-]", "Cl- (aq)", -167.2),
                              ("[OH-]", "OH- (aq)", -230.0),
                              ("O", "water", -285.8)):
        t = prov.get(smi)
        print(f"      {label:12s} Hf {t.Hf:8.1f}   aqueous-convention book "
              f"{bookH:8.1f}")
    print("  This project's ions are derived from pKa against its OWN water,")
    print("  which is priced as an IDEAL GAS. For a reaction that conserves")
    print("  water the offset cancels and nothing has ever noticed. Every cell")
    print("  reaction here CONSUMES water and MAKES hydroxide, so it does not.")
    print("  ! Pre-existing, and M8 is the first mechanism to depend on it.")
    print("  ! dG SURVIVES IT AND dS DOES NOT, which is the whole shape of this")
    print("  finding: panel 1's worst disagreement is 0.212 V while the dS")
    print("  above is out by hundreds. Quote E_dec at 298 K; do NOT quote how")
    print("  it moves with temperature, and do not read a cell's HEAT either --")
    print("  to_arrays takes its reaction enthalpy from the same dH.")

    print()
    print("=" * 78)
    print("PANEL 3 -- THE BARRIER ACROSS A VOLTAGE SWEEP, AND WHERE SELECTIVITY GOES")
    print("=" * 78)
    print("  Ea_eff = max(n F eta_a + alpha (dH_chem - n F E), 0), alpha = 0.5.")
    print("  Evans-Polanyi with the cell's work in dH IS Butler-Volmer; the")
    print("  floor at zero is where a real cell would become transport-limited")
    print("  and this one becomes unlimited.")
    print()
    tmpl = {t.name: t for t in electrochemistry()}
    watch = [("water splitting", "water_electrolysis"),
             ("brine (chloralkali)", "halide_electrolysis"),
             ("Kolbe (acetate)", "kolbe_electrolysis")]
    header = "  " + f"{'E (V)':>6s}" + "".join(
        f"{name.split()[0][:9]:>12s}" for name, _ in watch)
    print(header + "     brine/water")
    ks: dict[float, dict[str, float]] = {}
    for E in SWEEP:
        ks[E] = {}
        cells = []
        for cell_name, tname in watch:
            row = next(r for r in rows if r[0] == cell_name)
            _, _, n, dH, _, _, _ = row
            t = tmpl[tname]
            work = n * FARADAY * E / 1000.0        # kJ/mol
            Ea = t.barrier((dH - work) * 1000.0)   # J/mol
            k = t.A * math.exp(-Ea / (R * T_REF))
            ks[E][cell_name] = k
            cells.append(f"{k:12.2e}")
        ratio = ks[E]["brine (chloralkali)"] / ks[E]["water splitting"]
        print(f"  {E:6.2f}" + "".join(cells) + f"   {ratio:12.2e}")
    print()
    print("  !! READ THE LAST COLUMN DOWN, NOT ACROSS. Chlorine outruns oxygen")
    print("  by eighteen orders of magnitude at 2.5 V and by less than one at")
    print("  3.0 V: **the activation selectivity WASHES OUT as the barrier")
    print("  floors at zero**, which is the measured cost of having no current")
    print("  budget. A real cell at 3 V still makes 99% chlorine because the")
    print("  supply's electrons are FINITE and the fast reaction takes them;")
    print("  here both reactions draw as much as they like.")
    print("  ! The usable window for a selective brine cell in THIS engine is")
    print("  therefore roughly 2.2 to 2.7 V, and that is a property of the")
    print("  model, not of chloralkali.")

    print()
    print("=" * 78)
    print("PANEL 4 -- WHY THE ADIPONITRILE ROW IS NOT AN ELECTRODE TEMPLATE")
    print("=" * 78)
    coupling = _rxn(("C=CC#N", "C=CC#N", "[H][H]"), ("N#CCCCCC#N",))
    dH_c, dG_c = reaction_deltas(coupling, prov, vol)
    whole = next(r for r in rows if r[0].startswith("adiponitrile"))
    print(f"  the CELL   4 AN + 2 H2O -> 2 ADN + O2      dG {whole[4]:+8.1f} kJ/mol"
          f"   E_dec {whole[5]:.3f} V")
    print(f"  the COUPLING  2 AN + H2 -> ADN             dG {dG_c:+8.1f} kJ/mol"
          f"   -- downhill on its own")
    print()
    print("  So the voltage does not pay for the carbon-carbon bond. It pays for")
    print("  tearing hydrogen out of water, which is ``water_electrolysis`` and")
    print("  is in every aqueous cell already. The route is two steps and its")
    print("  overall stoichiometry -- the oxygen included -- EMERGES.")
    water = next(r for r in rows if r[0] == "water splitting")
    print()
    print("  ! THE COST, STATED: routing the electrons through free H2 puts the")
    print(f"  route's threshold at water's {water[5]:.3f} V instead of its own")
    print(f"  {whole[5]:.3f} V -- {water[5] - whole[5]:.2f} V too high. Baizer's cell")
    print("  runs near 4 V so nothing about whether it RUNS turns on this, but")
    print("  the threshold this engine reports for it is the wrong one.")

    print()
    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)
    worst = max(
        (abs(E - book), name)
        for name, _, _, _, _, E, book in rows if book is not None
    )
    print(f"  {len(rows)} cells priced; {sum(1 for r in rows if r[6] is not None)} "
          f"have a book value.")
    print(f"  worst dG-side disagreement: {worst[1]} at {worst[0]:.3f} V.")
    print("  ! dS is the one that is wrong -- panel 2. Nothing here is a target.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
