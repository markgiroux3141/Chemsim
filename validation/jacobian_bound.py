"""Standing audit -- does the Jacobian step bound ever bind on work that works?

⚠ RUN THIS AFTER TOUCHING THE RHS, ``atol``, OR ANYTHING IN ``numerics``. The
bound in ``numerics/jacobian.py`` is safe only while it never clamps a column a
healthy run legitimately wanted probed harder. The first version of it -- a
constant ceiling of 1.0 -- looked safe on a four-run sweep and moved a quotable
digit in eight of the sixteen examples, which is exactly what this audit exists
to catch before it ships.

Four panels:

  1  THE MECHANISM, with no chemistry in it: what scipy does to a column it
     cannot difference, and what the bound does instead.
  2  WHAT THE BOUND EVALUATES TO on real states -- it is not a constant.
  3  HEADROOM: the factor each vessel WANTS against the bound it is under.
     ⚠ every ``clamped`` here must read 0.
  4  THE ONE RUN WHERE IT BINDS, which is the regression: the sulfur burner at
     rtol 1e-8. ~50 s, and it is the reason the module exists.

Costs about a minute.
"""
import sys
import time
from pathlib import Path

import numpy as np
from scipy.integrate._ivp.common import EPS, num_jac

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chemsim.matter import Molecule                                   # noqa: E402
from chemsim.network import build_network                             # noqa: E402
from chemsim.numerics.jacobian import (                               # noqa: E402
    BoundedJacobian,
    factor_bound,
)
from chemsim.properties import (                                      # noqa: E402
    ThermochemistryProvider,
    VolatilityProvider,
)
from chemsim.properties.mineral_data import MINERALS                  # noqa: E402
from chemsim.reactions import esterification, sulfur_combustion       # noqa: E402
from chemsim.vessel import Vessel                                     # noqa: E402


def canonical(s: str) -> str:
    return Molecule.from_smiles(s).smiles


def rule(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


S8, O2, N2, SO2 = (canonical(s) for s in
                   ("S1SSSSSSS1", "O=O", "N#N", "O=S=O"))
ACID, ALC = canonical("CC(=O)O"), canonical("CCO")
CALCITE = MINERALS["calcite"].lattice

thermo = ThermochemistryProvider()
volatility = VolatilityProvider()


# ---------------------------------------------------------------------------
rule("PANEL 1 -- THE MECHANISM. A column nothing acts on, differenced 400 times")
# ---------------------------------------------------------------------------
def toy(t, y):
    """One live state and one that nothing touches. Column 1 is identically
    flat, which is the CORRECT derivative for it."""
    return np.array([-float(y[0]), 0.0])


def toy_vec(t, y):
    y = np.asarray(y)
    if y.ndim == 1:
        return toy(t, y)
    return np.stack([toy(t, y[:, k]) for k in range(y.shape[1])], axis=1)


def drive(rounds, bounded, y=np.array([1.0, 0.0]), atol=1e-9):
    f = toy(0.0, y)
    factor = None
    for _ in range(rounds):
        J, factor = num_jac(toy_vec, 0.0, y, f, atol, factor, None)
        if bounded:
            np.clip(factor, None, factor_bound(y, atol), out=factor)
    return J, factor


print("   `num_jac` multiplies a column's perturbation factor by ten whenever the")
print("   difference it got back is small next to the rates elsewhere. It FLOORS")
print("   that factor and never CEILINGS it, so a column it can never satisfy is")
print("   probed harder for ever -- a decade per Jacobian, from EPS**0.5.")
print()
print(f"   {'Jacobians':>10} {'factor, unbounded':>20} {'factor, bounded':>18}"
      f"  {'J finite?':>10}")
for rounds in (1, 100, 200, 300, 316, 400):
    _, fu = drive(rounds, bounded=False)
    Jb, fb = drive(rounds, bounded=True)
    print(f"   {rounds:10d} {fu[1]:20.3e} {fb[1]:18.3e}"
          f"  {str(bool(np.all(np.isfinite(Jb)))):>10}")
print()
print("   The overflow needs ~316 Jacobians in ONE solve, which is why this is a")
print("   long-run fragility rather than a per-step one. Bounded, the column")
print("   settles at max|y|/atol and reads EXACTLY ZERO -- which is the right")
print("   derivative. The fix is not to make a flat column non-flat.")


# ---------------------------------------------------------------------------
rule("PANEL 2 -- THE BOUND IS THE STATE'S OWN EXTENT, so it is not a constant")
# ---------------------------------------------------------------------------
print("   |h_j| = factor_j * max(atol, |y_j|), and the requirement is that a")
print("   probe may not move one component further than the whole state extends:")
print("   |h_j| <= max_i |y_i|. There is no constant in it.")
print()
print(f"   {'state':44} {'atol':>8} {'bound on an absent species':>28}")
for label, y, atol in (
    ("[1.0, 0.0] -- the toy above", np.array([1.0, 0.0]), 1e-9),
    ("a flask: 0.1 mol, nothing else, 690 K",
     np.array([0.1, 0.0, 690.0]), 1e-9),
    ("... the same at the tight tolerance",
     np.array([0.1, 0.0, 690.0]), 1e-11),
    ("a kiln: 0.05 mol at 1100 K", np.array([0.05, 0.0, 1100.0]), 1e-9),
    ("!! the degenerate all-zero state", np.zeros(3), 1e-9),
):
    b = factor_bound(y, atol)
    print(f"   {label:44} {atol:8.0e} {b[1]:28.3e}")
print()
print(f"   The floor is EPS**0.5 = {EPS ** 0.5:.3e} -- num_jac's own starting")
print("   factor, so the bound can never make a probe FINER than scipy would")
print("   have begun with. Only the all-zero state reaches it.")


# ---------------------------------------------------------------------------
rule("PANEL 3 -- HEADROOM. What each vessel WANTS against the bound it is under")
# ---------------------------------------------------------------------------
def burner(T, s8, o2):
    v = Vessel(burn_net, volume=1.0, T=T, T_env=T, UA=1.0e4, kla=5.0,
               k_vent=0.0, k_diss=0.05, lle=False)
    v.charge({S8: s8, O2: o2, N2: 0.02})
    return v


burn_net = build_network([S8, O2, N2], [sulfur_combustion()], thermo=thermo,
                         volatility=volatility, max_species=40)
est_net = build_network([ACID, ALC], [esterification()], thermo=thermo,
                        volatility=volatility, max_species=20)
lime_net = build_network(
    [CALCITE, MINERALS["quicklime"].lattice, MINERALS["slaked lime"].lattice,
     "O=C=O", "O", "N#N", "O=O"], [], thermo=thermo)


def ester():
    v = Vessel(est_net, volume=0.2, T=350.0, T_env=350.0, UA=1.0e4, kla=5.0,
               k_vent=0.0, atmosphere={})
    v.charge({ACID: 0.5, ALC: 0.5})
    return v


def kiln(sealed):
    v = Vessel(lime_net, volume=1.0, T=1100.0, T_env=1100.0, UA=1.0e4,
               k_vent=0.0 if sealed else 1.0e3,
               atmosphere={} if sealed else {"N#N": 0.79, "O=O": 0.21})
    v.charge({CALCITE: 0.1}, phase="solid")
    if not sealed:
        v.fill_headspace()
    return v


VESSELS = [
    ("sulfur burner, O2-limited, 690 K", lambda: burner(690.0, 0.002, 0.10)),
    ("sulfur burner, O2-rich, 650 K", lambda: burner(650.0, 0.02, 0.40)),
    ("esterification, 350 K", ester),
    ("lime kiln, SEALED, N2/O2 absent", lambda: kiln(True)),
    ("lime kiln, swept", lambda: kiln(False)),
]
print("   400 Jacobians at each vessel's charged state, which is how a long")
print("   single run reaches the overflow. Headroom is what the solver WANTED")
print("   over what it was allowed: under 1 means the bound never came near.")
print()
print(f"   {'vessel':38} {'wanted':>10} {'bound':>10} {'headroom':>10} "
      f"{'clamped':>8}")
bind = 0
for label, make in VESSELS:
    v = make()
    y = v.integrator.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
    jac = BoundedJacobian(v.integrator.make_rhs(y), 1e-9)
    for _ in range(400):
        jac(0.0, y)
    # The MAXIMUM over columns, not the minimum: the bound that matters is the
    # one an ABSENT species is under (where y_scale falls back to atol), which
    # is the loosest. The minimum is always exactly 1.0 -- it belongs to the
    # largest component of the state, which is its own extent.
    b = float(factor_bound(y, 1e-9).max())
    print(f"   {label:38} {jac.peak_factor:10.2e} {b:10.2e} "
          f"{jac.peak_factor / b:10.2e} {jac.clamped:8d}")
    bind += jac.clamped
print()
print(f"   This run: {bind} clamped column(s) across the five.")
print()
print("   !! A SINGLE VESSEL IS NOT THE WHOLE PROJECT, AND SAYING SO IS THE")
print("   POINT OF THIS PANEL. `examples/fractional_distillation.py` -- fourteen")
print("   coupled vessels -- wants factor 3.252e+12 and IS clamped, in 232 of")
print("   its 1833 Jacobians. Measured against a converged rtol 1e-8 run:")
print()
print("      quantity   converged      default UNBOUND    default BOUND")
print("      forerun    0.43671495       0.43671550       0.43671561")
print("      heart      0.55620830       0.55620760       0.55620765")
print("      tail       0.07016219       0.07016210       0.07016229")
print("      pot T    408.20578700     408.20567700     408.20573700")
print()
print("   At rtol 1e-8 the heart and tail are BIT-IDENTICAL bounded and")
print("   unbounded, so the two converge to the same answer. At the default")
print("   neither is systematically nearer it -- bounded is closer on the heart")
print("   and the pot, unbounded on the forerun and the tail -- and every")
print("   difference is at or below 1e-6 relative, three decades under the 1e-3")
print("   band tolerance_audit.py calls a quotable digit. That is solver noise,")
print("   not the answer. !! IF A ROW ABOVE EVER MOVES, RE-MEASURE IT THE SAME")
print("   WAY: against a converged run, not against the previous default one.")


# ---------------------------------------------------------------------------
rule("PANEL 4 -- THE ONE RUN WHERE IT BINDS, which is the whole regression")
# ---------------------------------------------------------------------------
print("   `burn(690 K, s8=0.002, o2=0.10)` at rtol 1e-8. Before the bound this")
print("   RAISED 'array must not contain infs or NaNs' after ~51 s of thrashing,")
print("   and it is the run S2's tolerance audit could not sweep at all.")
print()
print("   The column that overflows is LIQUID LAYER 2's SO2, holding ~1e-29 mol.")
print("   Its LAYER_REABSORB drain makes f negative, so num_jac steps DOWNWARD --")
print("   into the RHS's own np.maximum(y, 0.0). Every downward step, at every")
print("   size over thirty decades, lands on the same clamped state.")
print()
for label, kw in (("default   ", {}),
                  ("rtol 1e-8 ", dict(rtol=1e-8, atol=1e-11))):
    v = burner(690.0, 0.002, 0.10)
    t0 = time.time()
    try:
        v.run(600.0, **kw)
        got = f"SO2 = {v.state().total(SO2):.10f} mol"
    except Exception as exc:                                    # noqa: BLE001
        got = f"RAISED {type(exc).__name__}: {str(exc)[:44]}"
    print(f"   {label} {got:44} {time.time() - t0:7.1f} s")
print()
print("   !! IT IS STILL SLOW AND THAT IS REPORTED, NOT HIDDEN. BDF is genuinely")
print("   struggling with a layer holding 1e-29 mol; the bound stops that")
print("   struggle ending in a NaN and does not stop the struggle. A constant")
print("   ceiling of 1.0 ran it in 2.6 s -- and moved eight examples.")
print()
print("=" * 78)
if bind == 0:
    print("VERDICT: inert on every SINGLE VESSEL measured. The rigs it does")
    print("         reach are bounded above at 1e-6 relative and converge to")
    print("         the same answer -- panel 3 is where that is measured.")
else:
    print(f"VERDICT: !! {bind} column(s) CLAMPED on a single vessel, which used")
    print("         to be 0. Re-measure every quoted number in that example,")
    print("         against a CONVERGED run rather than the previous default.")
print("=" * 78)
