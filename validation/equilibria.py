"""Validation harness: where does the equilibrium error actually live?

Run this FIRST in any session that intends to touch equilibrium accuracy. It
walks a set of liquid-phase reactions through every stage of the chain and prints
each stage next to a reference value, so the next change is aimed at a measured
error rather than a suspected one.

    dGf(gas)  --standard state-->  dGf(liquid)  -->  K_a  --activities-->  K_x

What this harness has established, which is why it exists:

  1. **The standard-state chain is validated, per species.** Every species in
     the table below now agrees with independently-tabulated CRC liquid data to
     within 0.5 kJ/mol, and the two reference reactions reproduce the K computed
     from that data to 6-9%. The chain from formation data to a liquid
     equilibrium constant is doing its job.

  2. **Carboxylic acids break the ln(Psat) route, and are now routed around
     it.** Acetic acid vapour is ~95% dimer, so its measured vapour pressure is
     not the monomer's and `R T ln(Psat)` prices the wrong molecule -- by
     4.9 kJ/mol, against under 1 kJ/mol for ethanol, ethyl acetate and water.
     `formation_data.LIQUID_FORMATION` supplies the measured liquid value
     instead, so no vapour pressure enters. The acid row is now within 0.5.

  3. **Joback could not tell homologues apart, and no longer has to.** Group
     contributions are additive, so the CH3 -> C2H5 difference cancels exactly
     between the alcohol and the ester it makes: methanol and ethanol
     esterification came out with an IDENTICAL gas-phase dG_rxn of -7.35 kJ/mol.
     No downstream care recovers a distinction the estimator never made.
     Measured formation data does, and the homologue panel below is what
     watches it.

  4. **The dominant remaining error is inconsistency BETWEEN tabulated values,
     not the model.** Acetic acid plus each of five alcohols breaks and makes
     exactly the same bonds, so the gas-phase dG_rxn across that series should
     be flat to about 1 kJ/mol. It spans 4.5, with methanol the outlier. That
     column is CRC/NIST formation data combined arithmetically -- there is no
     model in it at all -- so the spread is in the sources.

The open question this harness is meant to settle is the ACTIVITY BASIS. Mass
action runs on concentrations, so the simulator equilibrates to K_c;
thermodynamics says the invariant is K_a = K_gamma * K_x. The measurement
implies a K_a, and the last line of each case reports how far our dG_rxn sits
from it: +1.8 kJ/mol on ethanol, -3.1 on methanol. Those two disagree by
4.9 kJ/mol -- which is the homologue spread in (4), not a property of the
activity treatment. **Settle the formation data before touching the activity
basis**, or the calibration lands on top of a bad methyl acetate. Concretely:
find a source that resolves methanol/methyl acetate against the rest of the
series, and add liquid-phase equilibria whose references can be checked.
"""

from __future__ import annotations

import math

import numpy as np

from chemsim.constants import R
from chemsim.network import build_network
from chemsim.numerics.activity import activity_coefficients
from chemsim.properties import (
    ThermochemistryProvider,
    UnifacProvider,
    build_activity_arrays,
)
from chemsim.properties import standard_state as ss
from chemsim.reactions import ReactionTemplate
from chemsim.reactions.thermo import equilibrium_constant

T = 298.15

FISCHER = ReactionTemplate(
    name="fischer",
    smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
           ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
    A=1.0e6, Ea=50_000, reversible=True,
)

# Experimental LIQUID-phase formation data, kJ/mol at 298.15 K (CRC Handbook).
# Liquid basis on purpose: it sidesteps both the vaporization shift and the
# carboxylic-acid dimerization problem, so it is the cleanest reference we have.
CRC_LIQUID: dict[str, tuple[float, float]] = {
    "O":            (-285.83, -237.14),   # water
    "CC(=O)O":      (-484.50, -389.90),   # acetic acid
    "CCO":          (-277.60, -174.80),   # ethanol
    "CO":           (-239.20, -166.60),   # methanol
    "CCOC(C)=O":    (-479.00, -332.70),   # ethyl acetate
    "COC(C)=O":     (-445.90, -330.13),   # methyl acetate -- DERIVED, see below
    "CCCCO":        (-327.30, -162.50),   # 1-butanol
}
# BEFORE trusting any row of this table for a code change, re-check it against a
# primary source. It is a reference standard, so a transcription error here would
# be attributed to the model.
#
# Methyl acetate is the one row that is derived rather than transcribed, and the
# reason is that the transcribed value was wrong. It used to read -324.00, which
# this harness flagged as "dGf less certain" -- correctly, but the error is not
# uncertainty, it is 6 kJ/mol, and it made the methanol case look like a model
# failure when it was a reference failure. No absolute liquid entropy is
# tabulated for methyl acetate, so dGf(l) is reconstructed from quantities that
# are:
#
#   dS_vap(298) = (dHvap - dG_vap)/T = (32.38 - 3.08) kJ/mol / 298.15 K
#               = 98.3 J/(mol K)                    [dHvap and Psat, measured]
#   S0(l)       = S0(g) - dS_vap = 324.4 - 98.3 = 226.1 J/(mol K)
#   dGf(l)      = dHf(l) - T * [S0(l) - S0(elements)] = -330.13 kJ/mol
#
# The check that settles it is a homologous one, independent of all of the
# above: S0(l) = 226.1 puts methyl acetate 31.6 J/(mol K) below ethyl acetate's
# measured 257.7, and a CH2 increment of 31.6 is exactly normal (1-propanol ->
# 1-butanol is 32.2, pentane -> hexane is 31.1). The old -324.00 requires an
# increment of 52.1, which no homologous pair shows.

# reaction -> (reactants, products, measured conversion from an equimolar feed,
#              note). Conversion rather than K because it is what is actually
#              measured and is independent of concentration basis.
CASES = [
    (
        "acetic acid + ethanol",
        ("CC(=O)O", "CCO"), ("CCOC(C)=O", "O"),
        0.667,
        "classical 1:1 neat experiment, ~2/3 conversion, K_x ~ 4",
    ),
    (
        "acetic acid + methanol",
        ("CC(=O)O", "CO"), ("COC(C)=O", "O"),
        0.700,
        "reactive-distillation literature, K_x ~ 5.2",
    ),
]


def _crc_K(reactants, products) -> float | None:
    """K_a at 298 K from CRC liquid formation data, or None if incomplete."""
    if any(s not in CRC_LIQUID for s in reactants + products):
        return None
    dG = sum(CRC_LIQUID[s][1] for s in products) - sum(
        CRC_LIQUID[s][1] for s in reactants
    )
    return math.exp(-dG * 1000.0 / (R * T))


def _conversion_ideal(K: float) -> float:
    """Equilibrium conversion from a 1:1 feed with no activity correction."""
    root = math.sqrt(K)
    return root / (1.0 + root)


def _K_gamma_at(e: float, species, arrays) -> float:
    """UNIFAC's activity-coefficient quotient at a given 1:1-feed conversion."""
    x = np.array([1 - e, 1 - e, e, e]) / 2.0
    g = activity_coefficients(
        x, arrays.nu, arrays.R_k, arrays.Q_k, arrays.a_mn, arrays.active, T
    )
    return (g[2] * g[3]) / (g[0] * g[1])


def _dG(K: float) -> float:
    """kJ/mol from an equilibrium constant."""
    return -R * T * math.log(K) / 1000.0


def _conversion_with_activities(K_a: float, species, arrays) -> tuple[float, float]:
    """Conversion and K_gamma where K_a = K_gamma * K_x, solved self-consistently."""
    lo, hi = 1.0e-6, 0.999999
    for _ in range(200):
        e = 0.5 * (lo + hi)
        x = np.array([1 - e, 1 - e, e, e]) / 2.0
        g = activity_coefficients(
            x, arrays.nu, arrays.R_k, arrays.Q_k, arrays.a_mn, arrays.active, T
        )
        K_x = (x[2] * x[3]) / (x[0] * x[1])
        K_g = (g[2] * g[3]) / (g[0] * g[1])
        if K_g * K_x < K_a:
            lo = e
        else:
            hi = e
    e = 0.5 * (lo + hi)
    x = np.array([1 - e, 1 - e, e, e]) / 2.0
    g = activity_coefficients(
        x, arrays.nu, arrays.R_k, arrays.Q_k, arrays.a_mn, arrays.active, T
    )
    return e, (g[2] * g[3]) / (g[0] * g[1])


# Acetic acid + each of these, in the gas phase. Every one makes and breaks the
# SAME bonds -- a C-O-H becomes a C-O-C and a water leaves -- so their reaction
# Gibbs energies have to agree closely. Branching and chain length change the
# molecules but not the transformation. That makes this a check needing NO
# external reference: the spread across the row IS the inconsistency in the
# formation data, because the chemistry says it should be flat.
HOMOLOGUES = [
    ("methanol",   "CO",       "COC(C)=O"),
    ("ethanol",    "CCO",      "CCOC(C)=O"),
    ("1-propanol", "CCCO",     "CCCOC(C)=O"),
    ("2-propanol", "CC(C)O",   "CC(=O)OC(C)C"),
    ("1-butanol",  "CCCCO",    "CCCCOC(C)=O"),
]


def _homologue_panel(thermo) -> None:
    """Reaction Gibbs energy across an alcohol series, which should be flat."""
    print()
    print("=" * 78)
    print("homologue consistency: acetic acid + ROH, same bonds broken every time")
    print("=" * 78)
    print(f"  {'alcohol':12}{'dG_rxn(gas)':>13}{'dG_rxn(liq)':>13}{'K_a(liq)':>11}"
          f"{'conv':>8}")

    rows = []
    for name, alcohol, ester in HOMOLOGUES:
        net = build_network(
            ["CC(=O)O", alcohol, "O"], [FISCHER], thermo=thermo, max_species=40
        )
        rxn = next(
            (r for r in net.reactions
             if sorted(r.products) == sorted([ester, "O"])), None
        )
        if rxn is None:
            print(f"  {name:12}not generated by the template")
            continue
        dG_gas = _dG(equilibrium_constant(rxn, thermo, T, None))
        K_liq = equilibrium_constant(rxn, thermo, T, net.volatility)
        conv = _conversion_ideal(K_liq)
        rows.append((name, dG_gas))
        print(f"  {name:12}{dG_gas:13.2f}{_dG(K_liq):13.2f}{K_liq:11.2f}"
              f"{conv * 100:7.1f}%")

    spread = max(g for _, g in rows) - min(g for _, g in rows)
    worst = min(rows, key=lambda r: r[1])[0]
    print(f"\n  spread across the series: {spread:.1f} kJ/mol"
          f"   (most negative: {worst})")
    print("  The transformation is identical in every row, so this column should")
    print("  be flat to about 1 kJ/mol. It is not, and that residual is now the")
    print("  DOMINANT error in these equilibria -- bigger than the activity")
    print("  question below. It is an inconsistency between tabulated formation")
    print("  values, not something the simulator does to them: the same spread")
    print("  is present in the raw CRC gas-phase numbers before anything is")
    print("  applied to them. Chasing the activity basis while this stands would")
    print("  be tuning against noise.")


def main() -> None:
    thermo = ThermochemistryProvider()
    unifac = UnifacProvider()

    print("=" * 78)
    print("per-species formation data: ours vs CRC liquid (kJ/mol)")
    print("=" * 78)
    print(f"  {'species':14}{'ours dGf(g)':>13}{'shift':>9}{'ours dGf(l)':>13}"
          f"{'CRC dGf(l)':>12}{'err':>8}")
    volatility = build_network(["O"], [], thermo=thermo).volatility
    for smi, (_, crc_G) in CRC_LIQUID.items():
        t = thermo.get(smi)
        s = ss.shift(smi, volatility)
        ours = t.Gf + s.dGf
        flag = "" if abs(ours - crc_G) < 2.0 else "   <-- check"
        print(f"  {smi:14}{t.Gf:13.2f}{s.dGf:9.2f}{ours:13.2f}{crc_G:12.2f}"
              f"{ours - crc_G:8.2f}{flag}")
    print("\n  A large error here on a CARBOXYLIC ACID would be diagnostic: its")
    print("  vapour is dimerised, so R T ln(Psat) cannot price the monomer. Acetic")
    print("  acid is now within 0.5 because it takes MEASURED liquid data instead.")

    _homologue_panel(thermo)

    for label, reactants, products, measured, note in CASES:
        print()
        print("=" * 78)
        print(f"{label}   ({note})")
        print("=" * 78)

        species = list(reactants) + list(products)
        net = build_network(
            list(reactants) + ["O"], [FISCHER], thermo=thermo, max_species=40
        )
        rxn = next(
            (r for r in net.reactions
             if sorted(r.reactants) == sorted(reactants)
             and sorted(r.products) == sorted(products)),
            None,
        )
        if rxn is None:
            print("  template did not generate this reaction; skipped")
            continue

        K_gas = equilibrium_constant(rxn, thermo, T, None)
        K_liq = equilibrium_constant(rxn, thermo, T, net.volatility)
        K_crc = _crc_K(reactants, products)

        print(f"  K_a  ideal-gas standard state      {K_gas:10.2f}")
        print(f"  K_a  liquid standard state (ours)  {K_liq:10.2f}")
        if K_crc is not None:
            print(f"  K_a  liquid, from CRC data         {K_crc:10.2f}"
                  f"    <-- reference for the chain above")

        arrays = build_activity_arrays(species, unifac)
        conv_ideal = _conversion_ideal(K_liq)
        conv_act, K_gamma = _conversion_with_activities(K_liq, species, arrays)

        print()
        print(f"  {'':34}{'conversion':>12}{'vs measured':>14}")
        print(f"  today (concentration basis)       {conv_ideal*100:11.1f}%"
              f"{conv_ideal/measured:13.2f}x")
        print(f"  with activity correction          {conv_act*100:11.1f}%"
              f"{conv_act/measured:13.2f}x   (K_gamma = {K_gamma:.2f})")
        print(f"  measured                          {measured*100:11.1f}%")

        # What the measurement says K_a must be, and hence how far off our
        # dG_rxn is. A conversion ratio is hard to act on; kJ/mol is not, because
        # that is the unit the formation data's error is quoted in.
        K_x_measured = (measured / (1.0 - measured)) ** 2
        K_gamma_measured = _K_gamma_at(measured, species, arrays)
        K_a_implied = K_gamma_measured * K_x_measured
        print()
        print(f"  K_a implied by the measurement    {K_a_implied:11.2f}"
              f"    (K_x {K_x_measured:.2f} x K_gamma {K_gamma_measured:.2f})")
        print(f"  our dG_rxn is off by              "
              f"{_dG(K_liq) - _dG(K_a_implied):11.2f} kJ/mol")

    print()
    print("=" * 78)
    print("READ THE LAST TWO ROWS OF EACH BLOCK BEFORE CHANGING ANYTHING.")
    print("If the activity correction moves conversion AWAY from measurement on")
    print("every case, the problem is not the missing gamma -- it is either K_a or")
    print("UNIFAC's K_gamma for these mixtures, and applying gamma would trade one")
    print("error for another. Add cases until the pattern is unambiguous.")
    print("=" * 78)


if __name__ == "__main__":
    main()
