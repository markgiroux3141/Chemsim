"""Layer 1 demo: properties and equilibrium from molecular structure.

Part 1 estimates thermochemical properties for a spread of molecules straight
from their SMILES -- no per-molecule data entry -- and shows each value's source.

Part 2 is the payoff: the Fischer-esterification equilibrium constant, which we
hand-tuned in Phase 0, now falls out of group-contribution thermochemistry.

Part 3 spends that K: the reverse reaction is no longer a free parameter -- its
Arrhenius pair is derived by detailed balance so that kf/kr = K(T) identically.
"""

import math

from chemsim.constants import R
from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import ThermochemistryProvider
from chemsim.reactions import (
    ReactionTemplate,
    detailed_balance,
    equilibrium_constant,
    reaction_deltas,
)

prov = ThermochemistryProvider()

print("=== Part 1: properties estimated from structure ===")
print(f"{'molecule':<20}{'formula':<11}{'Hf':>9}{'Gf':>9}{'Tb(K)':>8}   source")
for name, smi in [("ethanol", "CCO"), ("acetic acid", "CC(=O)O"),
                  ("ethyl acetate", "CCOC(C)=O"), ("acetone", "CC(C)=O"),
                  ("caffeine (novel)", "CN1C=NC2=C1C(=O)N(C)C(=O)N2C"),
                  ("water", "O"), ("O2", "O=O")]:
    m = Molecule.from_smiles(smi)
    try:
        t = prov.get(m)
        tb = f"{t.Tb:.1f}" if t.Tb else "-"
        print(f"{name:<20}{m.formula:<11}{t.Hf:>9.1f}{t.Gf:>9.1f}{tb:>8}   {t.source}")
    except Exception as e:
        print(f"{name:<20}{m.formula:<11}  (no data: {type(e).__name__})")
print("Hf, Gf in kJ/mol (ideal gas, 298 K)")

print("\n=== Part 2: esterification equilibrium, derived not invented ===")
FISCHER = ReactionTemplate(
    name="fischer_esterification",
    smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
           ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
    A=1.0e6, Ea=50_000, reversible=True,
)
net = build_network(["CC(=O)O", "CCO", "O"], [FISCHER], thermo=prov)
fwd = next(r for r in net.reactions if r.name == "fischer_esterification")

dH, dG = reaction_deltas(fwd, prov, net.volatility)
print(f"  reaction: {' + '.join(fwd.reactants)} -> {' + '.join(fwd.products)}")
print(f"  dH_rxn(298) = {dH:6.2f} kJ/mol   dG_rxn(298) = {dG:6.2f} kJ/mol")
for T in (298.15, 320.0, 340.0, 360.0):
    K = equilibrium_constant(fwd, prov, T, net.volatility)
    print(f"  K({T:6.1f} K) = {K:6.2f}")
print("  (Phase-0 hand-tuned value was ~5.9 at 340 K; experiment ~4. "
      "Group contribution lands in the same place.)")

print("\n=== Part 3: detailed balance -- the reverse rate is not a parameter ===")
db = detailed_balance(
    fwd, prov, FISCHER.A, FISCHER.Ea, volatility=net.volatility
)
print(f"  declared forward:  A={db.A_fwd:.3e}   Ea={db.Ea_fwd:8.0f} J/mol")
print(f"  derived  reverse:  A={db.A_rev:.3e}   Ea={db.Ea_rev:8.0f} J/mol")
print("    from  A_rev = A_fwd*exp(-dS/R),  Ea_rev = Ea_fwd - dH")
print(f"    with  dH = {db.dH:.0f} J/mol,  dS = {db.dS:.2f} J/(mol K)")
for T in (298.15, 340.0, 400.0):
    kf = db.A_fwd * math.exp(-db.Ea_fwd / R / T)
    kr = db.A_rev * math.exp(-db.Ea_rev / R / T)
    print(f"  T={T:6.1f} K:  kf/kr = {kf / kr:7.3f}   "
          f"K(T) = "
          f"{equilibrium_constant(fwd, prov, T, net.volatility):7.3f}")
print("  Both directions are plain Arrhenius reactions in the array hand-off, so")
print("  the integrator never learns what 'reversible' means.")
