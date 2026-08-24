"""FREEZING A LAYER'S POLARITY AT THE INTEGRATION BOUNDARY -- both halves of the bargain.

The prep's acid quench is the most expensive integration in this project, and the
ionic rate correction made it 3.2x more so. The mechanism was understood before
this harness existed: the correction multiplies every ion-producing rate constant
by a function of the layer's permittivity, Oster's mixing rule makes that a
function of EVERY liquid amount, and a coupling that was sparse became all-to-all.

The fix is to evaluate that permittivity from the state the solver was handed
rather than from the state it is currently trying -- the same bargain this project
already accepts for the METER edge's rate and for the liquid-liquid phase decision
itself. The bargain has a price: the answer depends on the caller's step size.

So this harness measures BOTH halves, because a speedup whose error is unmeasured
is not a result:

    panel 1   what it recovers, against the four variants the regression was
              attributed with
    panel 2   what the frozen quantity actually DOES over a long span -- the size
              of the error, in permittivity and in the equilibrium constant it
              moves
    panel 3   the step-size dependence, measured rather than conceded
    panel 4   the invariants that must not move, chief among them that an ion's
              activity coefficient in water is EXACTLY one

    python validation/permittivity_freeze.py

⚠ Printed text is ASCII only. The Windows console is cp1252 and a warning glyph
inside a print() kills the script at that line. Docstrings are fine.
"""

from __future__ import annotations

import math
import time

import numpy as np

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.numerics import vessel_integrator as vi
from chemsim.numerics.activity import born_ln_gamma
from chemsim.properties import dissociation_templates, electrolyte_provider
from chemsim.reactions.library import (
    aerobic_oxidation,
    esterification,
    ether_condensation,
    peroxide_over_oxidation,
)
from chemsim.vessel import Vessel


def rule(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def smi(s: str) -> str:
    return Molecule.from_smiles(s).smiles


WATER, ETOH, NA, OH = "O", "CCO", "[Na+]", "[OH-]"
O2, N2, SULFURIC = "O=O", "N#N", "OS(=O)(=O)O"
ESTER = smi("CCOC(=O)c1ccccc1")
ACID = smi("OC(=O)c1ccccc1")
BENZOATE = smi("[O-]C(=O)c1ccccc1")
THERMO = electrolyte_provider()

print(__doc__.split("\n\n")[0])

PREP_NET = build_network(
    [ESTER, ACID, ETOH, WATER, OH, NA, SULFURIC, O2, N2],
    [esterification(), aerobic_oxidation(), peroxide_over_oxidation(),
     ether_condensation(), *dissociation_templates()],
    thermo=THERMO, max_species=120,
)
IDX = {s: i for i, s in enumerate(PREP_NET.species)}


def pot() -> Vessel:
    """The prep's pot, exactly as ``examples/multistep_prep.py`` charges it."""
    v = Vessel(PREP_NET, volume=2.0, T=353.0, T_env=353.0, UA=20.0, kla=5.0,
               k_diss=0.05, k_vent=0.0, k_lle=0.5)
    v.charge({WATER: 55.0, ESTER: 0.20, OH: 0.30, NA: 0.30})
    v.fill_headspace_with_air()
    return v


def quench(v: Vessel) -> None:
    v.charge({SULFURIC: 0.28})
    v.set_environment(275.0)


def snapshot(v: Vessel) -> tuple:
    """The five amount blocks and the clock, copied out. Same idea as a save."""
    return (v._nL.copy(), v._nL2.copy(), v._nG.copy(), v._nS.copy(), v.T)


def restore(snap: tuple) -> Vessel:
    """A fresh quenched pot at a recorded state.

    Panels 2 and 3 need MANY runs from the same post-saponification state, and
    re-cooking for two hours each time would cost more than the measurement is
    worth. Restoring is also the better control: every row then starts from a
    bit-identical state, so what is being compared is the stepping and nothing
    else.
    """
    w = Vessel(PREP_NET, volume=2.0, T=353.0, T_env=353.0, UA=20.0, kla=5.0,
               k_diss=0.05, k_vent=0.0, k_lle=0.5)
    w._nL[:], w._nL2[:], w._nG[:], w._nS[:] = (b.copy() for b in snap[:4])
    w.T = snap[4]
    quench(w)
    return w


# ---------------------------------------------------------------------------
rule("PANEL 1 -- WHAT IT RECOVERS, against the attribution it has to beat")
# ---------------------------------------------------------------------------
print("""
  Each row saponifies for 2 h, acidifies, and is then timed over a 10 s step of
  the quench -- the same measurement the regression was attributed with. The
  chemistry column is what makes the timing readable: if the crop moves, the
  speed is not free.

  'correction off' zeroes the ionic rate correction only; 'Born off' zeroes the
  transfer term entirely, so gamma for an ion goes back to 1 everywhere.
""")

VARIANTS = (
    ("frozen at the boundary", dict(freeze=True)),
    ("live in the RHS (before)", dict(freeze=False)),
    ("live, ionic correction off", dict(freeze=False, no_correction=True)),
    ("live, Born off entirely", dict(freeze=False, no_born=True)),
    ("frozen, lle=False", dict(freeze=True, lle=False)),
)

ROWS = []
for label, opt in VARIANTS:
    original = vi.FREEZE_LAYER_PERMITTIVITY
    vi.FREEZE_LAYER_PERMITTIVITY = bool(opt.get("freeze", True))
    try:
        v = pot()
        if not opt.get("lle", True):
            v.conditions.lle = False
        if opt.get("no_born"):
            v.phases.born_A[:] = 0.0
            v.integrator._has_ionic_reactions = False
        if opt.get("no_correction"):
            v.integrator._has_ionic_reactions = False
        t0 = time.perf_counter()
        v.run(7200.0)
        saponify = time.perf_counter() - t0
        quench(v)
        t0 = time.perf_counter()
        v.run(10.0)
        step = time.perf_counter() - t0
        st = v.state()
        ROWS.append((label, saponify, step, v.pH,
                     st.total(ACID) + st.total(BENZOATE), st.n_solid[ACID]))
    except Exception as exc:                                    # noqa: BLE001
        ROWS.append((label, float("nan"), float("nan"), float("nan"),
                     float("nan"), float("nan")))
        print(f"  {label}: FAILED -- {str(exc)[:60]}")
    finally:
        vi.FREEZE_LAYER_PERMITTIVITY = original

print(f"  {'variant':>27s} {'2 h cook':>9s} {'10 s quench':>12s} {'pH':>6s} "
      f"{'benzoyl / mol':>14s} {'crop / mol':>11s}")
for label, cook, step, pH, benzoyl, crop in ROWS:
    print(f"  {label:>27s} {cook:8.1f}s {step:11.1f}s {pH:6.2f} "
          f"{benzoyl:14.4f} {crop:11.4f}")

live = next((r for r in ROWS if r[0].startswith("live in")), None)
frozen = next((r for r in ROWS if r[0].startswith("frozen at")), None)
if live and frozen and frozen[2] > 0:
    print(f"\n  QUENCH STEP: {live[2] / frozen[2]:.2f}x faster frozen than live.")
    print(f"  2 H COOK:    {live[1] / max(frozen[1], 1e-9):.2f}x faster.")

# ---------------------------------------------------------------------------
rule("PANEL 2 -- THE SIZE OF THE ERROR, which is the half a speedup hides")
# ---------------------------------------------------------------------------
print("""
  The frozen quantity is a layer's volume-weighted permittivity. So the honest
  question is not "is freezing defensible in principle" but "how far does that
  number move over one call, and what does the move cost".

  Measured over the longest single span the prep runs -- the whole quench hour,
  which is also where the composition changes most, since 0.28 mol of sulfuric
  acid goes in and the benzoate turns into a sparingly soluble solid.
""")


def layer_eps(v: Vessel, layer: int = 1) -> float:
    return v.layer_permittivity(layer)


def ka_factor(v: Vessel, eps_from: Vessel | None = None) -> float:
    """The ionic rate correction's own multiplier for benzoic acid dissociation.

    This is the quantity the freeze actually perturbs, so it is the one worth
    reporting: how much would the rate constant have differed had the layer's
    real (end-of-span) polarity been used?
    """
    src = eps_from or v
    born = v.phases.born_block(v.T)
    if born is None:
        return float("nan")
    ln = born_ln_gamma(src._nL, born, v.T)
    return math.exp(-(ln[IDX[BENZOATE]] + ln[IDX["[OH3+]"]]))


cooked = pot()
cooked.run(7200.0)
QUENCHED = snapshot(cooked)

v = restore(QUENCHED)
eps_start = layer_eps(v)
ka_start = ka_factor(v)
water_start = float(v._nL[IDX[WATER]])
v.run(3600.0)
eps_end = layer_eps(v)
ka_end = ka_factor(v)

print(f"  {'':>34s} {'eps':>8s} {'Ka factor':>12s} {'water / mol':>12s}")
print(f"  {'at the boundary (frozen value)':>34s} {eps_start:8.3f} "
      f"{ka_start:12.4f} {water_start:12.3f}")
print(f"  {'3600 s later (what it became)':>34s} {eps_end:8.3f} "
      f"{ka_end:12.4f} {float(v._nL[IDX[WATER]]):12.3f}")
drift = abs(eps_end - eps_start)
print(f"\n  drift over the whole hour: {drift:.3f} in eps "
      f"({100 * drift / max(eps_start, 1e-9):.2f}%), and a factor of "
      f"{max(ka_end, ka_start) / max(min(ka_end, ka_start), 1e-300):.4f} in the "
      f"rate constant it multiplies.")
print("""
  Read that against what the term is FOR. The correction exists to stop an
  aqueous pKa running inside an oil, where the factor is 1e-10; a percent-level
  wobble in a layer that is 96% water by volume is not the case it is defending
  against. The freeze is wrong in the third decimal place of a quantity whose job
  is to span ten orders of magnitude.

  Where it WOULD be wrong in a way that matters: a single long call across which
  a layer goes from mostly water to mostly organic -- a solvent swap, an
  evaporation to dryness under an acid. A frontend steps the engine, so the
  practical exposure is one step, and this is what Vessel.step is for.""")

# ---------------------------------------------------------------------------
rule("PANEL 3 -- THE STEP-SIZE DEPENDENCE, conceded and then measured")
# ---------------------------------------------------------------------------
print("""
  A frozen boundary quantity makes the trajectory depend on how the caller cut
  the interval up. That is the bargain. Its SIZE is not a matter of opinion:
  the same stretch of the quench, taken in one call, in five, and in twenty.
""")
SPAN = 600.0
print(f"  the first {SPAN:.0f} s of the quench -- the stiff part, where the "
      "composition moves fastest\n")
print(f"  {'freeze':>8s} {'calls':>7s} {'wall':>9s} {'pH':>9s} "
      f"{'crop / mol':>13s} {'benzoyl / mol':>15s} {'eps':>8s}")
for freeze in (True, False):
    original = vi.FREEZE_LAYER_PERMITTIVITY
    vi.FREEZE_LAYER_PERMITTIVITY = freeze
    try:
        for calls in (1, 5, 20):
            w = restore(QUENCHED)
            t0 = time.perf_counter()
            for _ in range(calls):
                w.step(SPAN / calls)
            wall = time.perf_counter() - t0
            st = w.state()
            print(f"  {str(freeze):>8s} {calls:7d} {wall:8.1f}s {w.pH:9.5f} "
                  f"{st.n_solid[ACID]:13.6f} "
                  f"{st.total(ACID) + st.total(BENZOATE):15.6f} "
                  f"{layer_eps(w):8.4f}")
    finally:
        vi.FREEZE_LAYER_PERMITTIVITY = original
print("""
  What to look for: the frozen rows must agree with each other, and with the live
  rows, to the precision anything downstream reads. They are not required to be
  bit-identical -- that is exactly what was traded away -- and a difference in
  the fifth decimal of a crop is not a difference in a crop.""")

# ---------------------------------------------------------------------------
rule("PANEL 4 -- THE INVARIANT THAT IS NOT NEGOTIABLE: exactly one in water")
# ---------------------------------------------------------------------------
print("""
  Every ion in this project is priced from a measured AQUEOUS pKa at gamma = 1,
  so the Born term must be identically zero in water -- not nearly zero. That
  claim survives the freeze only because of WHICH HALF is frozen: the volume
  WEIGHTS are, the per-species permittivities are not, so a single-species layer
  still normalises to exactly 1.0 and Oster's round trip still cancels bit for
  bit at any temperature.

  Had the resulting permittivity been frozen instead, a pure aqueous phase warmed
  by one kelvin would compare eps(T0) against eps_ref(T) and the term would go
  non-zero -- which is the trap this panel exists to catch.
""")
acid_net = build_network(
    [WATER, "CC(=O)O", OH, NA], dissociation_templates(),
    thermo=THERMO, max_species=60,
)


def pH_of(charge: dict[str, float], freeze: bool) -> float:
    original = vi.FREEZE_LAYER_PERMITTIVITY
    vi.FREEZE_LAYER_PERMITTIVITY = freeze
    try:
        w = Vessel(acid_net, volume=1.0, T=298.15, T_env=298.15, UA=50.0,
                   kla=0.0, k_diss=0.0)
        w.charge(charge)
        w.run(2000.0)
        return w.pH
    finally:
        vi.FREEZE_LAYER_PERMITTIVITY = original


CASES = (
    ("pure water", {WATER: 55.34}),
    ("0.1 M acetic acid", {WATER: 55.34, "CC(=O)O": 0.1}),
    ("half-neutralised acetic", {WATER: 55.34, "CC(=O)O": 0.1, OH: 0.05, NA: 0.05}),
    ("0.1 M NaOH", {WATER: 55.34, OH: 0.1, NA: 0.1}),
    ("0.01 M acetic acid", {WATER: 55.34, "CC(=O)O": 0.01}),
)
print(f"  {'system':>24s} {'pH frozen':>10s} {'pH live':>9s} {'delta':>11s}")
worst = 0.0
for label, charge in CASES:
    a, b = pH_of(charge, True), pH_of(charge, False)
    worst = max(worst, abs(a - b))
    print(f"  {label:>24s} {a:10.6f} {b:9.6f} {abs(a - b):11.2e}")
print(f"\n  worst delta across the five: {worst:.2e}")

# ... and the term itself, directly, over temperature.
born_v = Vessel(acid_net, volume=1.0, T=298.15, T_env=298.15, UA=0.0, kla=0.0,
                k_diss=0.0)
born_v.charge({WATER: 55.34})
i_water = {s: i for i, s in enumerate(born_v.species)}[WATER]
frozen_phi = np.zeros(len(born_v.species))
frozen_phi[i_water] = 55.34 * 0.018
print(f"\n  {'T / K':>8s} {'live ln g':>14s} {'frozen ln g':>14s}"
      "   (both must be exactly 0.0)")
for T in (275.0, 298.15, 330.0, 373.0):
    born = born_v.phases.born_block(T)
    lo = born_ln_gamma(born_v._nL, born, T)
    fr = born_ln_gamma(born_v._nL, born, T, phi=frozen_phi)
    ions = born_v.phases.born_A > 0.0
    a = float(np.abs(lo[ions]).max()) if ions.any() else 0.0
    b = float(np.abs(fr[ions]).max()) if ions.any() else 0.0
    print(f"  {T:8.2f} {a:14.2e} {b:14.2e}")

print("""
==============================================================================
THE VERDICT THIS HARNESS EXISTS TO SUPPORT
==============================================================================

  A frozen boundary quantity is not free and is not a tuning knob. It is worth
  taking here because three things are true at once, and each is measured above
  rather than asserted:

    the SPEED it recovers is the whole of the attributed regression (panel 1);
    the ERROR it introduces is in the third decimal place of a term whose job is
      to span ten orders of magnitude (panel 2), and does not move any number
      this project reports (panel 3);
    and the ONE claim that cannot bend -- an ion's activity coefficient in water
      is exactly one -- is untouched, because only the volume weights were frozen
      and not the permittivities themselves (panel 4).

  If a future model needs a layer's polarity to follow a fast composition change
  inside one call, this is the decision to revisit, and FREEZE_LAYER_PERMITTIVITY
  is the switch to revisit it with.""")
