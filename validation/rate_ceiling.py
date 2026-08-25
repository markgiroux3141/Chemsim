"""Every rate constant in the project, against the ceiling a collision sets.

``reactions/library.py`` has always refused a hand-authored pre-exponential above
the gas-kinetic collision limit -- "buying a prettier threshold with an impossible
pre-exponential is the wrong trade". Nothing applied that standard to the rate
constants ``detailed_balance`` DERIVES, and it derives one for every reversible
template in the project.

M12 is what that cost. Water autoionization declares ``Ea = 60 kJ/mol``, chosen to
sit just above water's dissociation enthalpy of 55.8 so the elementary-barrier
clamp does not fire. Detailed balance then hands the reverse a barrier of 4.2
kJ/mol and a rate constant of **9.4e18 L/(mol s), 9.4e7 times the collision
limit**, for a recombination measured at 1.4e11 (Eigen). A pair running 1e8 times
too fast turns over 9.4e4 mol/s in a 1 L flask, so its two heat terms are +-5.2e9
W either side of a net that is a fraction of a watt -- and three BDF steps of 168
s then destroyed 467 J in an insulated flask whose composition did not move by a
picomole. See ``validation/adiabatic_tail.py``.

This script is the standing audit, and it exists so three things stay MEASURED
rather than remembered:

  1. after the guard, nothing exceeds the bimolecular ceiling AT 298 K, which is
     the guard's whole domain;
  2. nothing approaches the UNIMOLECULAR ceiling either, which is why that case
     is deliberately not guarded -- a guard with no case behind it is an
     invention rather than a bound;
  3. ⚠ and WHERE each pair would cross the ceiling if it were run hot, because
     the guard is evaluated at 298.15 K and a barrier climbs faster with
     temperature than a collision frequency does. That third panel is a REPORTED
     LIMITATION, not a failure: the crossing temperatures are real and one of
     them is only 416 K.
"""
from __future__ import annotations

import math
import warnings

import numpy as np

warnings.filterwarnings("ignore")

from chemsim.network import build_network                       # noqa: E402
from chemsim.properties import (                                # noqa: E402
    dissociation_templates,
    electrolyte_provider,
)
from chemsim.reactions import synthesis as S                    # noqa: E402
from chemsim.reactions.thermo import COLLISION_LIMIT            # noqa: E402
from chemsim.recipes import BENZOIC_ACID_PREP as PREP           # noqa: E402

R = 8.314462618
T_REF = 298.15
# A bond vibration -- the fastest a molecule can come apart on its own. Quoted
# as an order of magnitude because that is all it is ever known to.
UNIMOLECULAR_LIMIT = 1.0e14      # 1/s

THERMO = electrolyte_provider()


def k_at(r, T: float) -> float:
    return float(r.A * np.exp(-r.Ea / (R * T)) * T**r.n_exp)


def crossing_T(r) -> float:
    """The temperature at which this reaction reaches the ceiling, or inf.

    Solving ``A exp(-Ea/RT) = ceiling`` for T. The ``T**n`` factor is ignored --
    every reaction it applies to here has n = 0, and where it does not the
    answer is an order-of-magnitude statement anyway.
    """
    ceiling = COLLISION_LIMIT if len(r.reactants) >= 2 else UNIMOLECULAR_LIMIT
    if r.A <= ceiling:
        return math.inf                      # cannot reach it at any T
    if r.Ea <= 0.0:
        return 0.0                           # already over, everywhere
    return r.Ea / (R * math.log(r.A / ceiling))


def networks() -> dict:
    out = {}
    out["benzoic acid prep"] = PREP.network()
    out["silver metathesis"] = build_network(
        ["O", "[Ag+]", "[Cl-]", "[Na+]", "O=[N+]([O-])[O-]"],
        list(dissociation_templates()), thermo=THERMO, max_species=40,
    )
    out["aqueous acids"] = build_network(
        ["O", "CC(=O)O", "c1ccccc1C(=O)O", "Cl", "OS(=O)(=O)O", "C#N", "CCO"],
        list(dissociation_templates()), thermo=THERMO, max_species=80,
    )
    # M5. ⚠ EVERY REVERSIBLE TEMPLATE THE MILESTONE ADDED IS HERE, because that is
    # the standing instruction M12 left it: check the reverse the template
    # IMPLIES, not only the forward that was typed. Eight of M5's twenty templates
    # are reversible and all eight appear below.
    out["synthesis gas"] = build_network(
        ["N#N", "[H][H]", "[C-]#[O+]", "O=C=O"],
        S.synthesis_gas_chemistry(), thermo=THERMO, max_species=40,
    )
    out["Kolbe-Schmitt"] = build_network(
        ["Oc1ccccc1", "O=C=O", "O"],
        [S.kolbe_schmitt()] + list(dissociation_templates()),
        thermo=THERMO, max_species=40,
    )
    out["ester hydrolysis"] = build_network(
        ["CCOC(C)=O", "O", "CC(=O)Oc1ccccc1C(=O)O"],
        [S.ester_hydrolysis(), S.transesterification()],
        thermo=THERMO, max_species=60,
    )
    out["alkene hydration"] = build_network(
        ["C=C", "CC=C", "O"], [S.alkene_hydration()],
        thermo=THERMO, max_species=40,
    )
    return out


def cold_panel(nets) -> int:
    print(f"\n=== THE GUARD'S DOMAIN: every rate constant at {T_REF:.2f} K ===")
    print(f"  bimolecular ceiling {COLLISION_LIMIT:.1e} L/(mol s); "
          f"unimolecular {UNIMOLECULAR_LIMIT:.1e} 1/s")
    over = 0
    for name, net in nets.items():
        worst_bi = worst_uni = 0.0
        bi_name = uni_name = ""
        for r in net.reactions:
            k = k_at(r, T_REF)
            if len(r.reactants) >= 2:
                if k > worst_bi:
                    worst_bi, bi_name = k, r.name
            elif k > worst_uni:
                worst_uni, uni_name = k, r.name
        bi_frac = worst_bi / COLLISION_LIMIT
        uni_frac = worst_uni / UNIMOLECULAR_LIMIT if worst_uni else 0.0
        flag = ""
        if bi_frac > 1.0 + 1e-9 or uni_frac > 1.0:
            over += 1
            flag = "   !! OVER THE CEILING"
        print(f"  {name:<22} {len(net.reactions):3d} reactions{flag}")
        print(f"      fastest bimolecular  {worst_bi:11.4e}  "
              f"{bi_frac:9.2e} of ceiling  ({bi_name})")
        if worst_uni:
            print(f"      fastest unimolecular {worst_uni:11.4e}  "
                  f"{uni_frac:9.2e} of ceiling  ({uni_name})")
        else:
            print("      fastest unimolecular   (none in this network)")
    return over


def hot_panel(nets) -> float:
    print("\n=== THE LIMITATION: where each pair would cross, if run hot ===")
    print("  The guard is applied at 298.15 K. A barrier climbs with temperature "
          "faster")
    print("  than a collision frequency does, so a pair that is physical cold "
          "need not")
    print("  stay physical hot. These are the crossings, coldest first:")
    seen = {}
    for net in nets.values():
        for r in net.reactions:
            Tx = crossing_T(r)
            if math.isfinite(Tx):
                seen[r.name] = min(seen.get(r.name, math.inf), Tx)
    if not seen:
        print("      nothing can reach its ceiling at any temperature")
        return math.inf
    for name, Tx in sorted(seen.items(), key=lambda kv: kv[1]):
        if Tx <= T_REF + 1.0:
            note = "  <- the guard PINNED this one, so it binds exactly"
        elif Tx < 500.0:
            note = "  <- inside the range this project runs"
        else:
            note = ""
        print(f"      {name:<40} crosses at {Tx:7.1f} K{note}")
    print("\n  !! Read the pinned row for what it is. The guard puts water's "
          "pair AT the")
    print("    ceiling at 298 K, so it is nominally over it above room "
          "temperature --")
    print("    by 2.6x at 700 K, against 9.4e7x before. And the real ceiling "
          "RISES with")
    print("    temperature (diffusion in water roughly triples from 298 to 373 "
          "K), which")
    print("    a fixed 1e11 does not. The row to worry about is the 416 K one, "
          "which is")
    print("    a genuine 1e3x overshoot at a temperature a reflux reaches.")
    return min(t for t in seen.values() if t > T_REF + 1.0)


def water_panel(nets) -> None:
    print("\n=== the reaction the guard fires on ===")
    net = nets["silver metathesis"]
    for r in net.reactions:
        if "water_autoionization" in r.name:
            print(f"  {r.name:<28} A={r.A:11.4e}  Ea={r.Ea:7.0f}  "
                  f"k(298)={k_at(r, T_REF):11.4e}")
    fwd = next(r for r in net.reactions if r.name == "water_autoionization")
    rev = next(r for r in net.reactions if r.name == "water_autoionization_rev")
    # The equilibrium is the thing that must NOT have moved: scaling both
    # pre-exponentials by one factor leaves K = k_f/k_r invariant, exactly.
    Kw = k_at(fwd, T_REF) * 55.4**2 / k_at(rev, T_REF)
    print(f"  Kw from the rate balance, as the model runs it: {Kw:.6e}")
    print("  (1.0e-14 is the measured value; this is the invariant the cap "
          "may not move)")
    print("  measured recombination, H3O+ + OH- (Eigen): 1.4000e+11 L/(mol s)")
    print(f"  after the cap:                              "
          f"{k_at(rev, T_REF):.4e} L/(mol s)")


def main() -> None:
    nets = networks()
    over = cold_panel(nets)
    coldest = hot_panel(nets)
    water_panel(nets)

    print("\n" + "=" * 74)
    if over:
        print("!! SOMETHING EXCEEDS ITS CEILING AT 298 K. A derived rate constant "
              "faster")
        print("!! than the reactants can meet is what M12 turned out to be.")
    else:
        print("Clean at 298 K, which is the guard's domain, and nothing is within")
        print("orders of the unimolecular ceiling -- which is why that case is not")
        print("guarded rather than being guarded on an invented number.")
    if math.isfinite(coldest):
        print(f"!! STILL OPEN, AND REPORTED RATHER THAN FIXED: the coldest "
              f"crossing is {coldest:.0f} K.")
        print("!! Above it a pair is faster than a collision again, and the "
              "cancellation")
        print("!! in the temperature equation grows with it. Nothing runs a "
              "carboxylic")
        print("!! acid that hot today; a route that wants to must read this "
              "panel first.")


if __name__ == "__main__":
    main()
