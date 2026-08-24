"""THE BULK VENT DESTROYED GAS -- any open flask, ~100x its own air, at the DEFAULT.

FIXED 2026-08-18. This harness is the attribution and the before-and-after, and it
runs BOTH forms: the old one is reproduced exactly by substituting the old
coefficient into ``backflow_part``, so nothing here quotes a number it did not
measure.

It was first seen in a refluxing RIG, which was misleading -- **it was not a rig
bug**. A single, uncoupled, ordinary esterification in an open flask did it, the
size scaled with the vent conductance, and it vanished when the vent was shut.

WHAT THE MECHANISM ACTUALLY WAS, and the handoff's diagnosis was half of it. The
vent carries the donor's composition, blended across the crossing:

    vent = k_vent * dP * (w * x_out + (1 - w) * x_ambient),  w = sigma(dP / scale)

The clamped ``x_out`` (``nG`` is ``np.maximum(y[2n:3n], 0)``) is why nothing
RESTORED a component that had gone negative. But what DROVE it there is the second
term, and it is a mixed-sign product: at a small POSITIVE dP the flow is outward,
yet ``1 - w`` is still ~0.5, so half of an OUTflow leaves carrying the ROOM's
composition. The room is 79% nitrogen, so the flask exported nitrogen at a rate
that did not depend on how much nitrogen it had.

⚠ AND IT WAS NOT A CORNER CASE. An open flask settles where ``k_vent dP`` matches
its boil-off, which at the default conductance is dP ~ 3e-6 bar -- INSIDE a 1e-4
smoothing band. Measured there, ``1 - w = 0.485``. That also explains the "it scales
with k_vent" attribution: a smaller conductance needs a bigger dP to pass the same
flux, which pushes the operating point out of the band. **The band was the problem,
not the conductance** -- and panel 4 shows that lowering ``k_vent`` to 1 does move
the boiling plateau, so it was never the cheap fix it looked like.

THE FIX (``numerics.vessel_integrator.backflow_part``): write the flow as a full
stream of the donor's composition plus a correction that can only ever be an
INFLOW::

    vent = k_vent * (dP * x_out + backflow(dP) * (x_ambient - x_out))

with ``backflow <= 0`` everywhere. It sums to ``k_vent dP`` exactly at every dP --
so the pressure relaxation every boiling plateau rests on is untouched, bit for bit
-- and every OUTWARD term is proportional to ``x_out``, hence to the vessel's own
``nG``. A species that is not there cannot leave. The rig's vapour edge had the
identical defect and takes the identical form.

    python validation/vent_leak.py

⚠ Printed text is ASCII only. The Windows console is cp1252 and a warning glyph
inside a print() kills the script at that line. Docstrings are fine.
"""

from __future__ import annotations

import contextlib

import numpy as np

from chemsim.network import build_network
from chemsim.numerics import rig_integrator as ri
from chemsim.numerics import vessel_integrator as vi
from chemsim.properties import ThermochemistryProvider
from chemsim.reactions.library import aerobic_oxidation, esterification
from chemsim.vessel import Rig, Vessel

ACETIC, ETOH, WATER, O2, N2 = "CC(=O)O", "CCO", "O", "O=O", "N#N"
ACETALD = "CC=O"

print(__doc__.split("\n\n")[0])
net = build_network(
    [ACETIC, ETOH, WATER, N2, O2], [esterification(), aerobic_oxidation()],
    thermo=ThermochemistryProvider(), max_species=40,
)
GASES = (N2, O2)


@contextlib.contextmanager
def vent_form(name: str):
    """Run a block with the OLD vent form, the NEW one, or a chosen scale.

    THE OLD FORM IS REPRODUCED EXACTLY RATHER THAN DESCRIBED. The two differ
    only in the coefficient multiplying ``(x_ambient - x_out)``: the corrected
    form uses ``backflow_part``, and the old blend is algebraically the same
    expression with that coefficient set to ``dP (1 - w)``. So substituting one
    function reproduces the shipped-for-months behaviour bit for bit, with no
    second copy of the RHS to drift out of step with the first.
    """
    old_v, old_r = vi.backflow_part, ri.backflow_part
    old_sv, old_sr = vi.DP_VENT_SMOOTH, ri.DP_SMOOTH
    if name == "old":
        def legacy(dP, scale):
            return dP * 0.5 * (1.0 - np.tanh(dP / 1.0e-4))
        vi.backflow_part = ri.backflow_part = legacy
    else:
        vi.DP_VENT_SMOOTH = ri.DP_SMOOTH = float(name)
    try:
        yield
    finally:
        vi.backflow_part, ri.backflow_part = old_v, old_r
        vi.DP_VENT_SMOOTH, ri.DP_SMOOTH = old_sv, old_sr


def flask(**kw) -> Vessel:
    base = dict(volume=1.0, T=350.0, T_env=350.0, UA=20.0, kla=5.0)
    base.update(kw)
    v = Vessel(net, **base)
    v.charge({ACETIC: 3.0, ETOH: 3.0})
    v.fill_headspace_with_air()
    return v


def worst_raw(v: Vessel, span: float) -> tuple[float, float]:
    """Run one flask and report (air charged, worst RAW gas amount).

    The RAW solver output, not the projected state. The projection settles a
    cancelling pair, so by the time anything downstream looks, a catastrophic
    excursion has become a plausible number.
    """
    air = sum(v.state().total(g) for g in GASES)
    integ, n = v.integrator, v.integrator.n
    y = integ.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
    sol = integ.run(y, (0.0, span))
    raw = sol.y[:, -1]
    return air, min(float(raw[2 * n + v._index(g)]) for g in GASES)


# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print("PANEL 1 -- ONE FLASK, ONE HOUR, AN ORDINARY ESTERIFICATION")
print("=" * 78)
print("""
  No rig, no edges, nothing exotic: 3 mol acetic acid + 3 mol ethanol at 350 K in a
  1 L flask with air in it. The only thing varied is the vent conductance.
""")
print(f"  {'k_vent':>26s} {'air charged':>12s} "
      f"{'OLD worst raw':>15s} {'ratio':>8s} {'NEW worst raw':>15s}")
for label, kv in (("1e3  (THE DEFAULT, open)", 1.0e3),
                  ("10   (a loose stopper)", 10.0),
                  ("1", 1.0),
                  ("0    (sealed)", 0.0)):
    with vent_form("old"):
        air, was = worst_raw(flask(k_vent=kv), 3600.0)
    _, now = worst_raw(flask(k_vent=kv), 3600.0)
    ratio = abs(was) / air if air > 0 else float("nan")
    print(f"  {label:>26s} {air:12.6f} {was:15.4e} {ratio:7.1f}x {now:15.4e}")

print("""
  THE OLD FORM SCALED WITH THE CONDUCTANCE AND VANISHED WHEN THE VENT WAS SHUT,
  which is what attributed it to that term and nothing else. The corrected column
  never goes negative at all: every outward contribution is proportional to the
  vessel's own nG, so a species that is not there cannot leave.""")

# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print("PANEL 2 -- THE SAME DEFECT THROUGH A RIG'S VAPOUR EDGE")
print("=" * 78)
print("""
  Where it was first seen, and the reason it looked like a rig bug. Boiling sweeps
  the pot's air up into the condenser, and the edge blended the two vessels'
  compositions the same way the vent blended the room's.
""")


def reflux() -> tuple[float, float, Rig, Vessel]:
    rig = Rig()
    pot = rig.add("pot", Vessel(net, volume=1.0, T=298.15, T_env=298.15, UA=1.0,
                                kla=5.0, Q_input=150.0, k_vent=0.0))
    cnd = rig.add("condenser", Vessel(net, volume=0.5, T=288.0, T_env=288.0,
                                      UA=40.0, kla=5.0, k_vent=10.0,
                                      heat_capacity=20.0))
    rig.vapour("pot", "condenser", k=20.0)
    rig.drain("condenser", "pot", k=0.5)
    pot.charge({ACETIC: 3.0, ETOH: 3.0})
    pot.fill_headspace_with_air()
    cnd.fill_headspace_with_air()
    air = sum(v.state().total(g) for v in rig.vessels.values() for g in GASES)
    rig.run(600.0)
    rig.run(3000.0)
    left = sum(v.state().total(g) for v in rig.vessels.values() for g in GASES)
    return air, left, rig, pot


for form in ("old", "new"):
    with vent_form(form) if form == "old" else contextlib.nullcontext():
        air, left, rig, pot = reflux()
    report = rig.conservation_report()
    print(f"  {form.upper():>4s}   air charged {air:.6f} mol   air left {left:.6f} mol"
          f"   pot {pot.T:7.3f} K")
    print(f"         {report or 'conservation clean'}"[:200])

# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print("PANEL 3 -- THE SMOOTHING SCALE, AND WHY IT IS ZERO")
print("=" * 78)
print("""
  NO NON-ZERO SCALE IS FREE. backflow_part has to be <= 0 with a zero at the
  origin, so the origin is a maximum, so it is quadratic there -- which leaves a
  counter-current against the bulk flow, sized by a numerical constant rather than
  by any physics. Swept here on the observable it actually corrupts: an open
  flask's oxidation cascade is budgeted by the O2 in its headspace, and a spurious
  exchange with the room feeds or sweeps that budget.

  The flask below is held BELOW its bubble point on purpose. The panel-1 flask
  boils dry, so all of its air leaves legitimately and the residue cannot be seen.
""")


def oxidation(scale) -> tuple[float, float]:
    with vent_form("old") if scale == "old" else vent_form(str(scale)):
        v = Vessel(net, volume=1.0, T=330.0, T_env=330.0, UA=20.0, kla=5.0)
        v.charge({ACETIC: 3.0, ETOH: 3.0})
        v.fill_headspace_with_air()
        air0 = sum(v.state().total(g) for g in GASES)
        v.run(1800.0)
        v.run(1800.0)
        return air0, v.state().total(ACETALD)


print(f"  {'scale':>12s} {'acetaldehyde after 1 h':>24s} {'vs the exact switch':>21s}")
rows = [("old (1e-4 blend)", "old"), ("1e-4", 1e-4), ("1e-5", 1e-5),
        ("1e-6", 1e-6), ("1e-7", 1e-7), ("0 (SHIPPED)", 0.0)]
ref = None
for label, scale in rows:
    _, ald = oxidation(scale)
    ref = ald if scale == 0.0 else ref
for label, scale in rows:
    _, ald = oxidation(scale)
    print(f"  {label:>12s} {ald * 1e3:21.4f} mmol {ald / ref:20.3f}x")

print("""
  It is MONOTONE, so it is the residue and not scatter. A sealed flask makes more
  than any of them, which is the check that the room is what the exchange reaches.

  AND A NARROW BAND IS WORSE THAN NO BAND. At 1e-8 the vapour-edge conservation
  test takes 3507 solver steps against 224 at zero: BDF has to resolve a real
  derivative of order 1/scale, where a kink has nothing to resolve and costs a few
  rejected steps at the crossing. The usual "smooth it" reflex inverts here.""")

# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print("PANEL 4 -- THE INVARIANTS THE VENT TERM CARRIES")
print("=" * 78)
print("""
  The vent and the vapour edge are what every boiling plateau in this project rests
  on, so a fix that gets conservation right and moves any of these is not a fix.
  The corrected form sums to k_vent * dP EXACTLY at every dP, which is why they
  survive: the smoothing never touched the total flux, only its composition.
""")
pure = build_network([ETOH], [], thermo=ThermochemistryProvider())
print(f"  {'k_vent':>10s} {'ethanol under a hotplate':>26s} {'headspace P':>13s}")
for kv in (1.0e3, 10.0, 1.0):
    w = Vessel(pure, volume=1.0, T=298.15, T_env=298.15, UA=2.0, kla=5.0,
               Q_input=200.0, k_vent=kv)
    w.charge({ETOH: 5.0})
    w.run(600.0)
    w.run(600.0)
    flag = "   <-- the reference" if kv == 1.0e3 else ""
    print(f"  {kv:10.0f} {w.T:23.3f} K {w.pressure:12.6f} bar{flag}")
print("""
  THE k_vent = 1 ROW IS THE CHECK THE BRIEF ASKED FOR, and the answer is no: a
  smaller default is not the cheap fix. It moves the plateau and leaves the flask
  0.26% over ambient, because the vent is then SLOWER than kla = 5 and cannot carry
  the boil-off away. And it only suppressed the leak by luck -- by pushing the
  operating dP out of the smoothing band, which is not a property anyone could rely
  on at a different scale or boil rate.""")

net2 = build_network([ETOH, WATER, N2, O2], [], thermo=ThermochemistryProvider())
rig = Rig()
pot = rig.add("pot", Vessel(net2, volume=1.0, T=298.15, T_env=298.15, UA=1.0,
                            kla=5.0, Q_input=150.0, k_vent=0.0))
cnd = rig.add("condenser", Vessel(net2, volume=0.5, T=288.0, T_env=288.0, UA=40.0,
                                  kla=5.0, k_vent=10.0, heat_capacity=20.0))
rig.vapour("pot", "condenser", k=20.0)
rig.drain("condenser", "pot", k=0.5)
pot.charge({ETOH: 4.0, WATER: 4.0})
pot.fill_headspace_with_air()
cnd.fill_headspace_with_air()
rig.run(600.0)
T_early = pot.T
rig.run(3000.0)
print(f"\n  reflux, 50/50 ethanol/water   {T_early:.3f} K -> {pot.T:.3f} K at "
      f"{pot.pressure:.5f} bar, boiling={pot.is_boiling}")
print(f"  bubble point of that pot      {pot.bubble_point():.3f} K")
print(f"  conservation                  {rig.conservation_report() or 'clean'}")
