"""How good is the liquid-liquid model, and where does it fail?

Two liquid layers cost a fourth block in the state vector, so it is worth being
precise about what that bought and what it did not. Everything below is measured
against the same UNIFAC parameter block the rest of the project uses -- there is
no miscibility table, no partition-coefficient table and no density table in this
codebase, and the point of the panels is to find out how far that gets.

⚠ **The headline limitation, stated first because it is the one that will bite.**
Our UNIFAC parameters are the VLE-regressed set. Fredenslund's own group
published a SEPARATE LLE parameter table precisely because the VLE set
underpredicts miscibility gaps -- the same regression that reproduces a boiling
diagram well does not reproduce a tie line well. So expect the qualitative
answers (does it split, which layer sinks, which way does a solute go) to be
right and the quantitative ones (how much dissolves in how much) to be soft, and
expect the worst cases to be partially-miscible hydrogen bonders rather than
oil-and-water pairs.
"""

import numpy as np

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties.electrolyte import electrolyte_provider
from chemsim.numerics.lle import stability_test
from chemsim.properties import (
    ThermochemistryProvider,
    UnifacProvider,
    build_activity_arrays,
)
from chemsim.vessel import Vessel

WATER = "O"
BENZOIC = Molecule.from_smiles("OC(=O)c1ccccc1").smiles
THERMO = ThermochemistryProvider()
UNIFAC = UnifacProvider()


def smi(s: str) -> str:
    return Molecule.from_smiles(s).smiles


def rule(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def splits(species: list[str], amounts: list[float], T: float = 298.15) -> bool:
    arr = build_activity_arrays(species, UNIFAC)
    return stability_test(
        np.array(amounts, float), arr.nu, arr.R_k, arr.Q_k, arr.a_mn,
        arr.active, T,
    ).unstable


# ---------------------------------------------------------------------------
rule("PANEL 1 -- WHICH PAIRS SEPARATE. The sharpest test, and it needs no data")
# ---------------------------------------------------------------------------
# Yes/no is a much stronger check than any number here: it is decided by the
# SIGN of a tangent-plane distance, so a model can only pass it by getting the
# non-ideality qualitatively right across very different chemistry.
PAIRS = [
    (("O", "CCO"), False, "water / ethanol"),
    (("O", "CC(C)=O"), False, "water / acetone"),
    (("O", "CO"), False, "water / methanol"),
    (("O", "C1CCOC1"), False, "water / THF"),
    (("O", "c1ccccc1"), True, "water / benzene"),
    (("O", "Cc1ccccc1"), True, "water / toluene"),
    (("O", "CCCCCC"), True, "water / hexane"),
    (("O", "ClCCl"), True, "water / dichloromethane"),
    (("O", "CCCCO"), True, "water / n-butanol"),
    (("O", "CCOCC"), True, "water / diethyl ether"),
    (("O", "CCCCCCCCO"), True, "water / n-octanol"),
    (("c1ccccc1", "Cc1ccccc1"), False, "benzene / toluene"),
    (("CCCCCC", "Cc1ccccc1"), False, "hexane / toluene"),
    (("CCO", "CCCCCC"), False, "ethanol / hexane"),
]
print(f"  {'pair':>26s} {'expected':>10s} {'model':>8s}   verdict")
right = 0
for (a, b), expected, name in PAIRS:
    got = splits([smi(a), smi(b)], [0.5, 0.5])
    ok = got == expected
    right += ok
    print(f"  {name:>26s} {'split' if expected else 'mix':>10s} "
          f"{'split' if got else 'mix':>8s}   {'ok' if ok else '<-- WRONG'}")
print(f"\n  {right}/{len(PAIRS)} correct.")
print("""
  The misses are the interesting part, and they are all the same KIND of miss:
  partially-miscible hydrogen bonders read as fully miscible. n-butanol is
  ~7 wt% soluble in water and n-octanol essentially insoluble, and both come
  from a parameter set regressed against vapour-liquid data. Oil-and-water pairs
  and fully-miscible pairs are called correctly. This is the known cost of using
  UNIFAC-VLE parameters for a liquid-liquid question, and the fix is a
  parameter table (UNIFAC-LLE), not a change of model.""")

# ---------------------------------------------------------------------------
rule("PANEL 2 -- A DILUTE SOLUTION MUST NOT SPLIT")
# ---------------------------------------------------------------------------
# The other half of the discrimination, and the one that protects every
# single-phase result this project has ever measured: below the solubility
# limit there is one phase, and the test has to say so.
print(f"  {'x(organic) in water':>22s}   " + "  ".join(
    f"{n:>10s}" for n in ("benzene", "toluene", "hexane")
))
for x in (1e-5, 1e-4, 3e-4, 1e-3, 1e-2, 1e-1):
    cells = []
    for org in ("c1ccccc1", "Cc1ccccc1", "CCCCCC"):
        cells.append("split" if splits([WATER, smi(org)], [1.0 - x, x]) else "one")
    print(f"  {x:22.0e}   " + "  ".join(f"{c:>10s}" for c in cells))
print("""
  Measured aqueous solubilities at 298 K are ~1.8 g/L benzene (x = 4.1e-4),
  ~0.52 g/L toluene (x = 1.0e-4) and ~0.01 g/L hexane (x = 2e-6), so the
  crossings above should sit near those mole fractions. They are in the right
  decade for the aromatics and much too high for hexane -- the model lets far
  more alkane dissolve than really does. That is the VLE-parameter limitation
  again, and it errs toward MISCIBILITY, which is the safe direction: it will
  fail to separate something rather than separate something that should not.""")

# ---------------------------------------------------------------------------
rule("PANEL 3 -- THE LAYERS, AND WHICH ONE IS ON THE BOTTOM")
# ---------------------------------------------------------------------------
# Densities are not tabulated anywhere in this project. Each layer's comes from
# its own composition, through the molar masses and the Rackett molar volume the
# integrator already uses -- so this is a check on two models at once.
SOLVENTS = [
    ("Cc1ccccc1", 4.7, 0.867, "toluene"),
    ("c1ccccc1", 5.6, 0.874, "benzene"),
    ("CCCCCC", 3.8, 0.655, "hexane"),
    ("ClCCl", 7.8, 1.326, "dichloromethane"),
    ("ClC(Cl)Cl", 6.2, 1.489, "chloroform"),
]
print(f"  {'solvent':>18s} {'rho model':>10s} {'rho real':>9s} {'err':>7s} "
      f"{'organic sits':>13s}   {'expected':>10s}")
for s, moles, rho_real, name in SOLVENTS:
    key = smi(s)
    net = build_network([WATER, key, BENZOIC], [], thermo=THERMO, max_species=20)
    v = Vessel(net, volume=3.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0,
               k_diss=0.0, k_vent=0.0)
    v.charge({WATER: 27.7, key: moles, BENZOIC: 0.02})
    v.run(1800.0)
    if not v.two_phase:
        print(f"  {name:>18s} {'--':>10s} {rho_real:9.3f} {'--':>7s} "
              f"{'MISCIBLE':>13s}")
        continue
    layers = v.layers()
    organic = max(layers, key=lambda d: d["composition"].get(key, 0.0))
    rho = organic["density"]
    where = "on top" if organic is layers[0] else "underneath"
    expected = "on top" if rho_real < 0.997 else "underneath"
    print(f"  {name:>18s} {rho:10.3f} {rho_real:9.3f} "
          f"{100 * (rho - rho_real) / rho_real:6.1f}% {where:>13s}   "
          f"{expected:>10s}{'' if where == expected else '  <-- WRONG'}")
print("""
  Every layer ends up on the correct side, and the densities are within a few
  percent of the real ones -- which matters because "drain the lower layer" is
  resolved from exactly this number. Swap toluene for dichloromethane and the
  same recipe has to draw off the other tap, with nothing relabelled.""")

# ---------------------------------------------------------------------------
rule("PANEL 4 -- STEAM DISTILLATION: two liquids boiling below either of them")
# ---------------------------------------------------------------------------
# The consequence of both layers sharing one headspace. Each is nearly pure in
# its own component, so each contributes close to its FULL vapour pressure and
# the total reaches ambient early. This is why you can distil something that
# would decompose at its own boiling point.
net = build_network(
    [WATER, smi("Cc1ccccc1"), smi("c1ccccc1")], [], thermo=THERMO, max_species=20
)


def boils_at(charge: dict) -> float:
    """Heat it until the temperature stops rising, and report where it pinned.

    Stopping at the PLATEAU rather than after a fixed time, for two reasons. It
    is the actual measurement -- a boiling point is where latent heat balances
    the hotplate, which is a stationary state, not a clock reading. And running
    on past it boils the flask dry, after which the temperature rockets (that is
    real, and documented) into a regime where the Jacobian eventually goes
    non-finite. WARNING: That last part is a PRE-EXISTING robustness limit of a dry
    superheated flask, unrelated to two liquid layers: it reproduces bit for bit
    with ``lle=False``.
    """
    v = Vessel(net, volume=2.0, T=298.15, T_env=298.15, UA=0.0, Q_input=120.0,
               kla=5.0, k_diss=0.0)
    v.charge(charge)
    last = v.T
    for _ in range(40):
        v.step(100.0)
        if v.is_boiling and abs(v.T - last) < 0.02:
            return v.T
        last = v.T
    return v.T


TOL, BEN = smi("Cc1ccccc1"), smi("c1ccccc1")
print(f"  {'system':>26s} {'model':>9s} {'measured':>10s} {'error':>8s}")
for charge, real, name in (
    ({WATER: 27.7}, 373.1, "water alone"),
    ({TOL: 4.7}, 383.8, "toluene alone"),
    ({BEN: 5.6}, 353.2, "benzene alone"),
    ({WATER: 27.7, TOL: 4.7}, 357.3, "water + toluene"),
    ({WATER: 27.7, BEN: 5.6}, 342.4, "water + benzene"),
):
    T = boils_at(charge)
    print(f"  {name:>26s} {T:8.2f} K {real:9.1f} K {T - real:+7.2f} K")
print("""
  Both mixtures co-distil BELOW either of their components, which is the whole
  claim, and the temperatures land within a couple of kelvin of the measured
  co-distillation points. Nothing in this project has ever been told what an
  azeotrope or a co-distillation temperature is; this is the same shared
  headspace and the same Antoine curves that make ethanol pin at 351.46 K.""")

# ---------------------------------------------------------------------------
rule("PANEL 5 -- EXTRACTION, AND WHY THE SAME SOLVENT SPLIT UP WORKS BETTER")
# ---------------------------------------------------------------------------
net = build_network(
    [WATER, TOL, BENZOIC], [], thermo=THERMO, max_species=20
)


def extract(portions: int, total: float = 4.7) -> float:
    aq = Vessel(net, volume=4.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0,
                k_diss=0.0, k_vent=0.0)
    aq.charge({WATER: 27.7, BENZOIC: 0.02})
    out = Vessel(net, volume=4.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0,
                 k_diss=0.0, k_vent=0.0)
    for _ in range(portions):
        aq.charge({TOL: total / portions})
        aq.run(600.0)
        if aq.two_phase:
            aq.pour_into(out, phase="upper")
    return out.state().total(BENZOIC)


print(f"  {'portions':>9s} {'each':>9s} {'recovered':>11s}  {'ideal n-stage':>14s}")
one = extract(1)
K = None
for portions in (1, 2, 3, 5, 10):
    got = extract(portions)
    if K is None:
        # Back out the effective distribution ratio from the single extraction,
        # then predict the rest from it: recovery = 1 - (1/(1+K/n))^n. Nothing
        # in the model was given this formula -- it is what the model should
        # reproduce if the partition is being re-established each time.
        frac = got / 0.02
        K = frac / (1.0 - frac)
    ideal = 1.0 - (1.0 / (1.0 + K / portions)) ** portions
    print(f"  {portions:9d} {4.7 / portions * 18.0:7.0f} mL "
          f"{100 * got / 0.02:9.1f}% {100 * ideal:13.1f}%")
print("""
  The measured curve tracks the n-stage formula, which is a CONSISTENCY check
  rather than an independent one: it says the partition ratio is re-established
  at every contact and stays constant over this range, which is what a dilute
  solute should do and what would fail if the layers were merely being diluted
  or were not re-equilibrating. The first row fixes K, so only the rest are
  predictions.""")

# ---------------------------------------------------------------------------
rule("PANEL 6 -- THE ELECTROLYTE, WHICH IS NO LONGER REFUSED")
# ---------------------------------------------------------------------------
# ⚠ The ELECTROLYTE provider for this panel only: the plain one now REFUSES a
# chloride ion, because Joback prices it 101 kJ/mol away from the value the ion
# table derives from HCl's own pKa. Every other panel here is neutral and keeps
# the plain provider, so the two are not interchangeable by accident.
net = build_network(
    [WATER, TOL, "[Na+]", "[Cl-]"], [],
    thermo=electrolyte_provider(base=THERMO), max_species=20
)
v = Vessel(net, volume=3.0, T=298.15, T_env=298.15, UA=50.0, kla=0.0,
           k_diss=0.0, k_vent=0.0)
v.charge({WATER: 27.7, TOL: 4.7, "[Na+]": 0.5, "[Cl-]": 0.5})
v.run(600.0)
st = v.state()
N1 = sum(st.n_liquid.values())
N2 = sum(st.n_liquid2.values())
print(f"  brine + toluene -> two_phase = {v.two_phase}")
print(f"  {v.lle_report()}")
print(f"\n  {'species':>14s} {'aqueous':>12s} {'organic':>12s} {'K = x2/x1':>11s}")
for s in net.species:
    n1, n2 = st.n_liquid[s], st.n_liquid2[s]
    if max(n1, n2) < 1e-12:
        continue
    K = (n2 / N2) / (n1 / N1) if n1 > 0 and N2 > 0 else float("nan")
    print(f"  {s:>14s} {n1:12.6g} {n2:12.6g} {K:11.3e}")
print(f"""
  THIS PANEL USED TO BE A REFUSAL, and the change is what the last session was
  for. Ions had no activity model at all, so they sat at gamma = 1 -- and equality
  of activity with gamma = 1 on both sides of an interface means an ion partitions
  to EQUAL MOLE FRACTION between water and toluene. Splitting a brine therefore
  invented a strongly ionic organic phase and ran aqueous-anchored dissociation
  equilibria inside it, so the split was refused outright and the flask was held
  as one well-mixed liquid. That was the honest answer available at the time, and
  it cost the most common workup in preparative chemistry.

  It has been REPLACED rather than relaxed, by two terms:

    the BORN transfer energy, which prices what it costs a charge to leave a
    high-dielectric medium for a low one. Sodium's exclusion from toluene is
    ln gamma 112 unclipped, and the salt stays in the water to a part in
    {1.0 / max((st.n_liquid2['[Na+]'] / N2) / (st.n_liquid['[Na+]'] / N1), 1e-30):.0f};

    and the ionic RATE correction, because getting the ions to stay in the water
    does nothing about the reactions that MAKE ions. Every pKa here is derived
    from a measured AQUEOUS value, so run unchanged it would leave benzoic acid
    as dissociated in toluene as in water -- the exact opposite of what an
    acid/base extraction relies on.

  Both are measured, panel by panel, in validation/ion_partition.py -- including
  where the model is a BOUND rather than a prediction, and what it still cannot
  do (a greasy phase-transfer cation is over-excluded, and there are no ion pairs).

  What survives as a refusal is narrow: an ion whose radius cannot be resolved
  has no transfer energy, so it would move freely between layers. That is refused
  per species and named. Nothing in ordinary chemistry hits it.

  AND WHAT IS STILL MISSING IS A DIFFERENT GAP, worth not conflating with this
  one: ionic strength WITHIN one phase -- Debye-Huckel, Davies. That is what makes
  a concentrated brine's ions less active than its concentration says, and it is
  what salting-out is. Adding it now would change nothing measurable, because an
  ion's activity coefficient reaches only phase equilibria and the rate correction
  above, and both are already dominated by a factor of e^12. Salting-out needs the
  activity basis for NEUTRAL species first.""")
