"""Layer 1/4 demo: what a liquid mixture does when it stops being ideal.

Until now every liquid here obeyed Raoult's law exactly, which quietly asserts
that a molecule cannot tell what it is surrounded by. Two consequences followed,
and both were wrong in the same direction:

  * distillation always ran to a pure product, because the vapour was always
    richer in the more volatile component;
  * a solid dissolved as readily in a solvent it hates as in one it loves.

Activity coefficients fix both, from one group-contribution model (UNIFAC) and
one number per species. Nothing below is a lookup: there is no azeotrope table
and no solubility table.

  Part 1  the group decomposition -- what the model actually sees
  Part 2  ethanol/water: an azeotrope, and why distillation stalls at 95.6%
  Part 3  benzoic acid in water: ideal solubility was 300x wrong
  Part 4  oxygen, which now knows what it is dissolved in
  Part 5  what the model does NOT cover, stated rather than assumed
"""

import numpy as np

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import (
    ThermochemistryProvider,
    UnifacProvider,
    electrolyte_provider,
)
from chemsim.properties.unifac import GROUPS_BY_ID
from chemsim.vessel import Vessel

THERMO = ThermochemistryProvider()
UNIFAC = UnifacProvider()

ETHANOL, WATER = "CCO", "O"
BENZOIC = Molecule.from_smiles("OC(=O)c1ccccc1").smiles

MIXTURE = build_network([ETHANOL, WATER], [], thermo=THERMO)
SOLUTION = build_network([BENZOIC, WATER], [], thermo=THERMO)


print("=== Part 1: what the model sees ===")
print("  A molecule is fragmented into UNIFAC groups by the same greedy,")
print("  priority-ordered SMARTS matcher Joback uses -- one algorithm, two tables.")
for smiles in (ETHANOL, WATER, BENZOIC, "CCOC(C)=O", "CC(C)=O"):
    print(f"  {smiles:<20} {UNIFAC.get(smiles).named()}")


print()
print("=== Part 2: ethanol/water, at the bubble point ===")
print("  y is the vapour composition in equilibrium with liquid x. Ideal Raoult")
print("  has y > x everywhere, so distillation would reach pure ethanol. Watch")
print("  the sign of y-x change.")
print(f"  {'x(EtOH)':>9}{'T_bubble':>11}{'y(EtOH)':>10}{'y - x':>10}"
      f"{'gamma(EtOH)':>13}{'gamma(H2O)':>12}")


def state(x_ethanol: float):
    v = Vessel(MIXTURE, volume=1.0, T=298.15)
    v.charge({ETHANOL: x_ethanol, WATER: 1.0 - x_ethanol})
    T = v.bubble_point()
    p = v.integrator.equilibrium_pressures(v._nL, T)
    gamma = v.integrator.activity_coefficients(v._nL, T)
    i = v.species.index(ETHANOL)
    j = v.species.index(WATER)
    return T, float(p[i] / p.sum()), float(gamma[i]), float(gamma[j])


for x in (0.10, 0.30, 0.50, 0.70, 0.85, 0.89, 0.93, 0.97, 1.00):
    T, y, g_e, g_w = state(x)
    print(f"  {x:>9.2f}{T:>11.2f}{y:>10.4f}{y - x:>+10.4f}{g_e:>13.3f}{g_w:>12.3f}")

lo, hi = 0.5, 0.999
for _ in range(60):
    mid = 0.5 * (lo + hi)
    _, y, _, _ = state(mid)
    lo, hi = (mid, hi) if y - mid > 0.0 else (lo, mid)
azeotrope = 0.5 * (lo + hi)
T_az, _, _, _ = state(azeotrope)

mass = azeotrope * 46.07 / (azeotrope * 46.07 + (1.0 - azeotrope) * 18.02)
print(f"  azeotrope (y = x) at x = {azeotrope:.3f} = {mass * 100:.1f} wt%,"
      f" boiling at {T_az:.2f} K")
print("  experiment:                x = 0.894 = 95.6 wt%, boiling at 351.3 K")
print(f"  pure ethanol boils at {state(1.0)[0]:.2f} K, pure water at "
      f"{state(0.0)[0]:.2f} K -- the mixture boils below BOTH,")
print("  which is what makes the azeotrope impossible to distil past.")


print()
print("=== Part 3: benzoic acid in water ===")
v = Vessel(SOLUTION, volume=1.0, T=298.15)
v.charge({WATER: 55.0, BENZOIC: 0.02})
i = v.species.index(BENZOIC)
print(f"  {'T (K)':>7}{'gamma':>9}{'ideal (g/L)':>14}{'with gamma':>12}"
      f"{'experiment':>12}")
for T, measured in ((298.15, 3.44), (313.15, 6.0), (333.15, 17.7)):
    gamma = v.integrator.activity_coefficients(v._nL, T)
    ideal = float(v.integrator.saturation_activity(T)[i]) * 55.3 * 122.12
    real = float(v.integrator.solubility(T, gamma)[i]) * 55.3 * 122.12
    print(f"  {T:>7.2f}{gamma[i]:>9.1f}{ideal:>14.0f}{real:>12.2f}{measured:>12.2f}")
print("  The ideal law is not slightly wrong, it is wrong by a factor of ~300:")
print("  it says benzoic acid and water mix like benzoic acid and benzoic acid.")
print("  Note the residual error grows with temperature -- UNIFAC understates how")
print("  fast an associating solute's solubility climbs. Reported, not hidden.")


print()
print("=== Part 4: oxygen, which now knows what it is dissolved in ===")
print("  Henry's constants are measured in water. A dissolved gas uses the")
print("  UNSYMMETRIC convention -- its reference is infinite dilution in that")
print("  same water, not its own pure liquid, which it does not have. So")
print("  gamma* = 1 in water by construction, and elsewhere it is the ratio of")
print("  infinite-dilution coefficients, which IS the ratio of Henry constants:")
print("  the solute's pure-liquid fugacity cancels out of it.")
print(f"  {'solvent':11}{'gamma*':>9}{'O2 (mM)':>10}{'measured':>10}   under air, 298 K")
for smiles, name, moles, measured in (
    ("O", "water", 55.0, 0.27),
    ("CO", "methanol", 24.7, 2.10),
    ("CCO", "ethanol", 17.0, 2.10),
    ("c1ccccc1", "benzene", 11.2, 1.80),
    ("CCCCCC", "n-hexane", 7.6, 3.10),
):
    net = build_network([smiles, "O=O"], [], thermo=THERMO)
    flask = Vessel(net, volume=2.0, T=298.15, T_env=298.15, UA=50.0, kla=2.0)
    flask.charge({smiles: moles})
    flask.charge({"O=O": 2.0}, phase="gas")
    flask.run(40_000.0)
    j = flask.species.index("O=O")
    p = flask.partial_pressures()["O=O"]
    mM = flask.concentrations()["O=O"] / p * 0.21 * 1e3
    g = flask.integrator.activity_coefficients(flask._nL, flask.T)[j]
    print(f"  {name:11}{g:>9.4f}{mM:>10.2f}{measured:>10.2f}")
print("  Every one of these used to return water's 0.27 mM, because the aqueous")
print("  constant was the only number available. Acetone is the poor case (2.6x).")


print()
print("=== Part 5: the edges of the model ===")
net = build_network(
    [WATER, ETHANOL, "O=O", "[OH-]", "[Na+]"], [], thermo=electrolyte_provider()
)
v = Vessel(net, volume=1.0, T=298.15)
print("  Every species either has a group decomposition or is held at gamma = 1")
print("  and named. Nothing is quietly assumed to be ideal:")
for line in v.activity_model.report().splitlines():
    print(f"  {line}")
print()
print("  Group basis for this vessel:",
      [UNIFAC.get(s).named() for s in v.species if v.phases.gamma_active[
          v.species.index(s)]])
print(f"  nu is {v.phases.nu.shape}, a_mn is {v.phases.a_mn.shape} -- plain numpy,")
print("  so Layer 4 still sees only arrays. It just evaluates them every step,")
print("  because gamma depends on composition and composition is the state.")
print()
print("  The interaction matrix at 298 K (K). It is stored as a quadratic in T,")
print("  a + bT + cT^2: UNIFAC's organic parameters are the constant case, PSRK's")
print("  gas parameters genuinely are not.")
T = 298.15
a_298 = v.phases.a_mn[:, :, 0] + T * (
    v.phases.a_mn[:, :, 1] + T * v.phases.a_mn[:, :, 2]
)
names = [GROUPS_BY_ID[gid].name for gid in v.activity_model.subgroup_ids]
print("            " + "".join(f"{n:>10}" for n in names))
for name, row in zip(names, np.round(a_298, 1)):
    print(f"  {name:>9} " + "".join(f"{x:>10.1f}" for x in row))
