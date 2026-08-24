"""ION TRANSFER BETWEEN PHASES -- what the Born term buys, and what it costs.

Six panels. The first three are about the model, the last three are about the
judgements: which numbers are robust, which are not, and which are bounds rather
than predictions.

    python validation/ion_partition.py

⚠ Printed text is ASCII only. The Windows console is cp1252 and a warning glyph
inside a print() kills the script at that line. Docstrings are fine.
"""

from __future__ import annotations

import math
import time

import numpy as np

from chemsim.constants import R
from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.numerics import activity as actmod
from chemsim.numerics.activity import (
    LN_GAMMA_BORN_MAX,
    born_ln_gamma,
    oster_permittivity,
)
from chemsim.properties import (
    BORN_PREFACTOR,
    DielectricProvider,
    born_coefficient,
    dissociation_templates,
    electrolyte_provider,
    ionic_radius,
)
from chemsim.vessel import Vessel


def rule(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def smi(s: str) -> str:
    return Molecule.from_smiles(s).smiles


THERMO = electrolyte_provider()
DIELECTRIC = DielectricProvider()
WATER = "O"
TOLUENE, BENZENE, HEXANE = smi("Cc1ccccc1"), smi("c1ccccc1"), smi("CCCCCC")
DCM, ETHER, OCTANOL = smi("ClCCl"), smi("CCOCC"), smi("CCCCCCCCO")
NA, CL = "[Na+]", "[Cl-]"
T = 298.15

print(__doc__.split("\n\n")[0])

# ---------------------------------------------------------------------------
rule("PANEL 1 -- THE TWO INPUTS: a permittivity per solvent, a radius per ion")
# ---------------------------------------------------------------------------
print("""
  A Born transfer term needs exactly two things this project did not have: how
  polar each liquid is, and how big each ion is. Both are tabulated, and both are
  carried with their provenance and their tier like every other parameter here.
""")
print(f"  {'solvent':>18s} {'eps(298 K)':>11s} {'window / K':>14s}  source tier")
for name in (WATER, "CCO", OCTANOL, DCM, "CCOC(C)=O", ETHER, TOLUENE, BENZENE,
             HEXANE):
    d = DIELECTRIC.get(name)
    lo, hi = d.T_range
    print(f"  {name:>18s} {d.at(T):11.3f} {f'{lo:.0f}-{hi:.0f}':>14s}  {d.kind}")

print(f"\n  {'ion':>20s} {'z':>3s} {'r / A':>7s} {'A / kJ/mol':>11s}  radius tier")
for ion in (NA, CL, "[OH-]", "[OH3+]", "[F-]", smi("[O-]C(=O)c1ccccc1"),
            smi("CC(=O)[O-]"), smi("[O-]S(=O)(=O)[O-]")):
    r = ionic_radius(ion)
    A, _ = born_coefficient(ion)
    z = Molecule.from_smiles(ion).charge
    tier = "Shannon" if "Shannon" in r.source else "derived (vdW volume)"
    print(f"  {ion:>20s} {z:+3d} {r.value * 1e10:7.2f} {A / 1000.0:11.1f}  {tier}")
print(f"""
  A = N_A z^2 e^2 / (8 pi eps_0 r) is assembled from SI constants, not
  transcribed: {BORN_PREFACTOR / 1e-10 / 1000.0:.1f} kJ/mol for a unit charge on a 1 angstrom sphere,
  per unit of (1/eps). z comes off the molecular graph, so a divalent ion is four
  times as strongly held with no new datum at all.

  The curated radius table is deliberately SMALL -- Shannon's monatomic set and
  hydroxide. There is no ionic-radius table in any source this project already
  depends on, so every curated value is hand-entered, and the project's rule is
  that a value with no auditable source does not get written down. Benzoate,
  acetate and sulfate fall to the derived tier instead: the sphere of equal
  additive van der Waals volume, built from element radii that ARE sourced.""")

# ---------------------------------------------------------------------------
rule("PANEL 2 -- WHAT IT COSTS AN ION TO LEAVE THE WATER")
# ---------------------------------------------------------------------------
eps_w = DIELECTRIC.get(WATER).at(T)
A_na, _ = born_coefficient(NA)
print(f"""
  ln gamma = A / (RT) * (1/eps_layer - 1/eps_water), so in water it is EXACTLY
  zero and everywhere else it is positive. Below: sodium, and the partition
  coefficient K = exp(-ln gamma) that it implies.

  eps(water) at {T:.2f} K = {eps_w:.2f}
""")
print(f"  {'layer':>18s} {'eps':>7s} {'ln gamma':>10s} {'K = x_org/x_aq':>16s}"
      f" {'reported as':>12s}")
for name in (OCTANOL, DCM, "CCOC(C)=O", ETHER, TOLUENE, BENZENE, HEXANE):
    eps = DIELECTRIC.get(name).at(T)
    raw = A_na / (R * T) * (1.0 / eps - 1.0 / eps_w)
    shown = min(raw, LN_GAMMA_BORN_MAX)
    print(f"  {name:>18s} {eps:7.2f} {raw:10.1f} {math.exp(-raw):16.2e}"
          f" {shown:12.1f}")
print(f"""
  Every one of those is an overwhelming exclusion, which is the right answer: a
  sodium salt is not extracted into toluene. The right-hand column is what the
  model actually reports, capped at {LN_GAMMA_BORN_MAX:.0f} -- see panel 5 for why that cap
  exists and why it changes nothing reportable.""")

# ---------------------------------------------------------------------------
rule("PANEL 3 -- THE FUNNEL THAT USED TO BE REFUSED")
# ---------------------------------------------------------------------------
net = build_network([WATER, TOLUENE, NA, CL], [], thermo=THERMO, max_species=20)
v = Vessel(net, volume=4.0, T=T, T_env=T, UA=50.0, kla=0.0, k_diss=0.0,
           k_vent=0.0)
v.charge({WATER: 27.7, TOLUENE: 4.7, NA: 1.0, CL: 1.0})
before = v.lle_report()
v.run(600.0)
st = v.state()
N1 = sum(st.n_liquid.values())
N2 = sum(st.n_liquid2.values())
print(f"""
  1 L of ~1.7 M brine shaken with 500 mL of toluene. Before this session the
  split was refused outright and the flask was held as one well-mixed liquid.

  before:  {before[:150]}

  after 600 s: two_phase = {v.two_phase}""")
print(f"  {'species':>20s} {'aqueous / mol':>14s} {'organic / mol':>14s} {'K':>11s}")
for s in net.species:
    n1, n2 = st.n_liquid[s], st.n_liquid2[s]
    if max(n1, n2) < 1e-12:
        continue
    K = (n2 / N2) / (n1 / N1) if n1 > 0 and N2 > 0 else float("nan")
    print(f"  {s:>20s} {n1:14.6g} {n2:14.6g} {K:11.3e}")
print(f"""
  layer 1 permittivity {v.layer_permittivity(1):.2f}   layer 2 permittivity """
      f"""{v.layer_permittivity(2):.2f}
  conservation: {v.conservation_report() or 'clean'}

  The salt stays in the water to better than a part in a hundred thousand, and
  nothing about the solvent pair changed -- water and toluene always separated.
  What changed is that the salt no longer has to be pretended away.""")

# ---------------------------------------------------------------------------
rule("PANEL 4 -- AN AQUEOUS pKa DOES NOT APPLY IN AN OIL")
# ---------------------------------------------------------------------------
print("""
  Getting the ions to stay in the water is only half of what the old refusal was
  protecting against. The other half: every pKa here is back-derived from a
  MEASURED AQUEOUS value, so running that constant unchanged inside an organic
  layer makes benzoic acid as dissociated in toluene as in water -- which is the
  exact opposite of what an acid/base extraction relies on.

  The fix is the activity-basis correction over the ions a reaction MAKES, placed
  on the direction that creates them. In water the factor is exp(0) = 1 exactly,
  so nothing aqueous moves. Below, the factor for the two dissociations that
  matter, as a function of the layer they are asked to run in.
""")
BENZOIC = smi("OC(=O)c1ccccc1")
net2 = build_network(
    [WATER, TOLUENE, BENZOIC, NA], dissociation_templates(),
    thermo=THERMO, max_species=60,
)
v2 = Vessel(net2, volume=2.0, T=T, T_env=T, UA=50.0, kla=0.0, k_diss=0.0)
v2.charge({WATER: 55.0})
born = v2.phases.born_block(T)
idx = {s: i for i, s in enumerate(v2.species)}
print(f"  {'layer':>18s} {'eps':>7s} {'ln g(benzoate)':>15s} {'ln g(H3O+)':>11s}"
      f" {'Ka factor':>11s}")
for label, amounts in (
    ("pure water", {WATER: 55.0}),
    ("90:10 water-toluene", {WATER: 50.0, TOLUENE: 5.0}),
    ("pure toluene", {TOLUENE: 9.4}),
):
    x = np.zeros(len(v2.species))
    for s, n in amounts.items():
        x[idx[s]] = n
    ln = born_ln_gamma(x, born, T)
    eps = oster_permittivity(
        x * np.maximum(np.array([v2.phases.v_liq[i] @ [1, T, T ** 2, T ** 3]
                                 for i in range(len(v2.species))]), 0.0),
        v2.phases.permittivity(T),
        medium=v2.phases.born_A <= 0.0,
    )
    b = ln[idx[smi("[O-]C(=O)c1ccccc1")]]
    h = ln[idx["[OH3+]"]]
    print(f"  {label:>18s} {eps:7.2f} {b:15.3f} {h:11.3f} "
          f"{math.exp(-(b + h)):11.3e}")
print("""
  In pure water the factor is 1.000 to the last bit, which is why the five pH
  invariants did not move -- checked, not assumed. In a hydrocarbon it is 1e-10,
  i.e. the acid stays as the free acid. That is the acid/base extraction working,
  and it is also what makes the two-phase system integrable at all: without it,
  the aqueous recombination rate constant acts on an ion pool it has no business
  creating, and the flask is unsolvable.""")

# ---------------------------------------------------------------------------
rule("PANEL 5 -- THE CEILING: WHAT IT COSTS AND WHY IT IS NOT A FUDGE")
# ---------------------------------------------------------------------------
print("""
  The unclipped transfer energy for sodium into toluene is ln gamma 112, i.e. a
  partition coefficient of 2e-50. That is not a number the interphase flux can
  carry: written as k (a1 - a2) with a2 = x2 gamma2, it gives that block a
  Jacobian diagonal of -7.5e22 and a relaxation timescale of 1e-23 s for a
  quantity whose equilibrium value is 1e-24 mol.

  BDF does not merely slow down on that. At the unclipped value it reported
  SUCCESS and returned chloride at +3.07e9 mol in one layer and -3.07e9 in the
  other -- a cancelling dipole fourteen orders of magnitude larger than the
  material present, which the non-negative projection then tidied into a
  plausible-looking answer. THE SILENT WRONG ANSWER WAS ONE PROJECTION AWAY.

  So the ceiling is measured rather than chosen. Sweeping it:
""")
sweep_net = build_network([WATER, TOLUENE, NA, CL], [], thermo=THERMO,
                          max_species=20)
i_cl = {s: k for k, s in enumerate(sweep_net.species)}[CL]
original = actmod.LN_GAMMA_BORN_MAX
print(f"  {'ceiling':>8s} {'gamma':>10s} {'wall / s':>9s} {'nfev':>7s} "
      f"{'K(Cl-)':>11s} {'n2(Cl-) / mol':>14s}  verdict")
try:
    for cap in (6.0, 9.0, 12.0, 15.0, 18.0, 22.0, 30.0, 50.0):
        actmod.LN_GAMMA_BORN_MAX = cap
        w = Vessel(sweep_net, volume=4.0, T=T, T_env=T, UA=50.0, kla=0.0,
                   k_diss=0.0, k_vent=0.0)
        w.charge({WATER: 27.7, TOLUENE: 4.7, NA: 1.0, CL: 1.0})
        it = w.integrator
        y0 = it.split_phases(it.pack(w._nL, w._nL2, w._nG, w._nS, w.T))
        t0 = time.perf_counter()
        sol = it.run(y0, (0.0, 600.0))
        wall = time.perf_counter() - t0
        n = it.n
        L1, L2 = sol.y[:n, -1], sol.y[n:2 * n, -1]
        worst = float(min(L1.min(), L2.min()))
        biggest = float(max(np.abs(L1).max(), np.abs(L2).max()))
        ok = sol.success and worst > -1e-6 and biggest < 1e3
        n1, n2 = L1[i_cl], L2[i_cl]
        K = ((n2 / L2.sum()) / (n1 / L1.sum())) if L2.sum() > 0 and n1 > 0 else (
            float("nan")
        )
        print(f"  {cap:8.0f} {math.exp(min(cap, 50)):10.2e} {wall:8.2f}s "
              f"{sol.nfev:7d} {K:11.3e} {n2:14.4e}  "
              f"{'ok' if ok else 'BROKEN -- dipole of ' + format(biggest, '.2e')}")
finally:
    actmod.LN_GAMMA_BORN_MAX = original
print(f"""
  The ceiling is set at {original:.0f}, and the binding constraint is NOT the
  chemistry: it is that the equilibrium amount must stay resolvable. At 12 it is
  about a micromole, three orders of magnitude above the solver's own 1e-9 atol,
  so the quantity is integrated rather than lost in round-off -- and the implied
  partition coefficient of 6e-6 is a part per million, invisible in any assay or
  mass balance. At 18 the equilibrium amount lands ON the tolerance; at 30 the
  cost is four times the solver work; at 50 it breaks outright.

  Both statements "K is 6e-6" and "K is 2e-50" say the same thing about the
  chemistry. They say very different things about the Jacobian. Every ion whose
  transfer energy is being reported at the ceiling is named as such by
  Vessel.electrolyte_report, so a capped value is never mistaken for a computed
  one.""")

# ---------------------------------------------------------------------------
rule("PANEL 6 -- WHICH NUMBERS ARE ROBUST, AND WHICH ARE NOT")
# ---------------------------------------------------------------------------
print("""
  The radius enters as 1/r, so it is worth knowing where it matters. Sweeping a
  monovalent ion's radius over five-fold -- which spans every tier in panel 1 and
  then some -- and reading off the partition coefficient:
""")
print(f"  {'layer':>18s} {'eps':>7s} " +
      " ".join(f"{f'r={r:.1f}A':>11s}" for r in (1.0, 1.8, 2.8, 3.7, 5.0)))
for name in (HEXANE, TOLUENE, ETHER, DCM, OCTANOL, "CCO"):
    eps = DIELECTRIC.get(name).at(T)
    row = []
    for r in (1.0, 1.8, 2.8, 3.7, 5.0):
        raw = BORN_PREFACTOR / (r * 1e-10) / (R * T) * (1.0 / eps - 1.0 / eps_w)
        row.append(f"{math.exp(-min(raw, 700)):11.2e}")
    print(f"  {name:>18s} {eps:7.2f} " + " ".join(row))
print("""
  READ THIS BEFORE READING A PARTITION COEFFICIENT OFF A POLAR-SOLVENT
  EXTRACTION. For a hydrocarbon layer the whole sweep is between 1e-10 and 1e-64:
  the answer "the ion stays in the water" does not depend on the radius at all,
  and the radius is therefore not a calibration knob. For a moderately polar
  layer -- octanol, dichloromethane, eps around 9 -- the same sweep spans four
  orders of magnitude, and there it IS a real parameter. The tiering in panel 1
  matters for those and not for these.

  Two further limits, both in the same safe direction:

    BORN IS THE ELECTROSTATIC TERM ONLY. There is no cavity term and no
    dispersion term, so a large, greasy, weakly-hydrated ion is over-excluded
    here -- tetrabutylammonium partitions into an organic phase readily enough to
    be sold as a phase-transfer catalyst, and this model would refuse it.

    THERE ARE NO ION PAIRS in this project's species set, and a salt entering a
    low-dielectric solvent really does travel as a neutral pair.

  Both omissions mean too LITTLE ion transfer, never too much -- the same
  direction the UNIFAC-VLE parameters err in, and the reason the old blanket
  refusal could be replaced rather than merely loosened.

  And one number that is a BOUND rather than an estimate: a species with no
  measured permittivity contributes f(eps) = 0 to the mixing rule while still
  counting in the volume. f is monotone with f(1) = 0, so that is the LOWEST
  permittivity the layer could possibly have -- never an invented one. Benzoic
  acid is the case that settled it: a solid, with no measured liquid permittivity
  in any source here. Renormalising over the priced remainder read its layer's
  polarity off the 32% of it that was water and ethanol, called it eps = 50, and
  let the ions in. The bound reads eps = 15 and keeps them out.""")

# ---------------------------------------------------------------------------
rule("WHAT IS STILL REFUSED")
# ---------------------------------------------------------------------------
print("""
  The blanket electrolyte refusal is gone. Two narrow ones survive, and neither
  fires for ordinary chemistry:

    an ION with no resolvable radius has no transfer energy at all, so it would
    move freely between layers. Refused per species, and named.

    (and the coverage of a proposed layer's permittivity is REPORTED rather than
    refused, because the f = 0 bound above already errs in the safe direction.)

  What is NOT modelled, and is a different gap from this one:

    IONIC STRENGTH WITHIN one phase -- Debye-Huckel or Davies. That is what makes
    a concentrated brine's ions less active than its concentration says, and it is
    what salting-out is. Conflating it with ion TRANSFER is the mistake to avoid:
    they are different physics and only the transfer term lifts the refusal.
    Adding Debye-Huckel now would change nothing measurable, because an ion's
    activity coefficient reaches only phase equilibria and the ionic rate
    correction, and both are already dominated by a factor of e^12. SALTING-OUT
    NEEDS THE ACTIVITY BASIS FOR NEUTRAL SPECIES FIRST, not an ionic-strength
    term for the ions.""")
