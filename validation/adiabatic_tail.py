"""HANDOFF 79's open hypothesis, settled -- decisive controls only.

The claim recorded as OPEN: an insulated metathesis warms 0.1578 K at t = 1200 s
(predicted 0.1577) and reads 0.038 K when the SAME run goes to 3600 s in one
call, extent unmoved. Chunking recovers it; rtol 1e-9 recovers it. *Whether that
tail behaviour predates the precipitation term* was never measured, because the
control did not finish inside two minutes.

Only the flasks that settle it, in cost order:

    D  the NULL      -- ions, no precipitation, started AT ambient
    C  no ions       -- water + headspace, started 0.16 K WARM
    B  the CONTROL   -- the metathesis flask, precipitation OFF, started WARM

If C and B decay from +0.16 K the way A decayed to +0.038 K, the tail is generic
and predates the term. If they hold, it belongs to precipitation.

A2 (ten chunked calls to 3600 s) is NOT here. Measured: it burns >25 min of CPU
without finishing, and it settles nothing that ``tests/test_precipitation.py``
does not already assert at 1200 s.

⚠ PROGRESS METER. ``OdeSolver.step`` is wrapped to print the solver's own ``t``
every 200 steps. It is a print and nothing else -- no state is touched, no
tolerance changed -- so the single-call experiment is preserved exactly. Without
it a run that is working looks identical to a run that has hung, which is what
made the first attempt at this opaque.
"""
from __future__ import annotations

import time

from scipy.integrate._ivp.base import OdeSolver

from chemsim.network import build_network
from chemsim.properties import dissociation_templates, electrolyte_provider
from chemsim.vessel import Vessel

WATER = "O"
SILVER, CHLORIDE, SODIUM = "[Ag+]", "[Cl-]", "[Na+]"
NITRATE = "O=[N+]([O-])[O-]"
WARM = 298.15 + 0.16
SPAN = 3600.0

_step = OdeSolver.step
_state = {"n": 0, "t0": time.perf_counter(), "label": ""}


def _traced(self):
    out = _step(self)
    _state["n"] += 1
    if _state["n"] % 200 == 0:
        print(f"        ... {_state['label']}: solver at t = {self.t:8.1f} s "
              f"of {SPAN:.0f}   step {self.h_abs:10.3e} s   "
              f"{_state['n']:6d} steps   {time.perf_counter() - _state['t0']:6.1f}s",
              flush=True)
    return out


OdeSolver.step = _traced

THERMO = electrolyte_provider()
NET = build_network(
    [WATER, SILVER, CHLORIDE, SODIUM, NITRATE],
    list(dissociation_templates()), thermo=THERMO, max_species=40,
)
WATER_NET = build_network([WATER], [], thermo=THERMO, max_species=10)


def flask(net, T, *, precipitation=True, ions=True):
    v = Vessel(net, volume=1.0, thermo=THERMO, UA=0.0, heat_capacity=0.0,
               T=T, T_env=298.15, precipitation=precipitation)
    charge = {WATER: 55.0}
    if ions:
        charge |= {SILVER: 0.01, NITRATE: 0.01, SODIUM: 0.01, CHLORIDE: 0.01}
    v.charge(charge)
    return v


def report(label, v, **kw):
    _state["n"] = 0
    _state["t0"] = time.perf_counter()
    _state["label"] = label.split()[0]
    print(f"  {label} ...", flush=True)
    t0 = time.perf_counter()
    try:
        v.run(SPAN, **kw)
    except Exception as exc:                                # noqa: BLE001
        print(f"  {label:44s} FAILED after "
              f"{time.perf_counter() - t0:.1f}s: {str(exc)[:60]}", flush=True)
        return
    dt = time.perf_counter() - t0
    st = v.state()
    print(f"  {label:44s} dT = {v.T - 298.15:+9.5f} K   "
          f"AgCl {st.n_solid.get(SILVER, 0.0):.7f} mol   "
          f"{_state['n']:6d} steps   {dt:6.1f}s", flush=True)


print("\n=== D -- THE NULL: undisturbed adiabatic flask AT ambient ===",
      flush=True)
report("D1  no precipitation, starts at 298.15", flask(NET, 298.15,
                                                       precipitation=False))

print("\n=== C -- NO IONS AT ALL: water + headspace, STARTED 0.16 K WARM ===",
      flush=True)
report("C1  one call", flask(WATER_NET, WARM, ions=False))
report("C2  one call, rtol 1e-9", flask(WATER_NET, WARM, ions=False),
       rtol=1e-9, atol=1e-12)

print("\n=== B -- THE CONTROL: metathesis flask, precipitation OFF, WARM ===",
      flush=True)
report("B1  one call", flask(NET, WARM, precipitation=False))
report("B2  one call, rtol 1e-9", flask(NET, WARM, precipitation=False),
       rtol=1e-9, atol=1e-12)
print()

# ---------------------------------------------------------------------------
# The two follow-ups that turned "not generic" into "an energy leak".
# ---------------------------------------------------------------------------
print("\n=== WHICH HALF: the term's CODE, or the EVENT? ===", flush=True)
_sat = None
try:
    from chemsim.properties.solubility_product import solubility_product
    _sat = solubility_product("chlorargyrite").Ksp ** 0.5
except Exception:                                           # noqa: BLE001
    pass


def charged(T, *, precipitation, mol):
    v = Vessel(NET, volume=1.0, thermo=THERMO, UA=0.0, heat_capacity=0.0,
               T=T, T_env=298.15, precipitation=precipitation)
    v.charge({WATER: 55.0, SILVER: mol, NITRATE: mol,
              SODIUM: mol, CHLORIDE: mol})
    return v


if _sat is not None:
    dilute = _sat / 10.0
    report("E1  term ON,  dilute (no event), WARM",
           charged(WARM, precipitation=True, mol=dilute))
    report("E2  term OFF, dilute (no event), WARM",
           charged(WARM, precipitation=False, mol=dilute))
    report("E3  term ON,  0.01 mol (EVENT), WARM",
           charged(WARM, precipitation=True, mol=0.01))
    report("E4  term ON,  0.01 mol (EVENT), ambient",
           charged(298.15, precipitation=True, mol=0.01))

print("""
   !! READ THE PAIRS. E1 == E2 to five decimals, so the term's mere presence in
   the RHS is free. E3 against E2 is the same flask with only the EVENT turned
   on, and it is 0.05 K poorer. E4 is the original: it reaches the predicted
   +0.1577 K at t=600s, still reads +0.1575 at t=1200s -- which is why the
   1200 s test passes and is right to -- and then decays to +0.0378 AFTER the
   chemistry has stopped.

   !! AND THE BOUND IS WHAT MAKES IT A DEFECT. Between t=1200 and t=3600 the
   largest mole change in ANY block is 1.332e-07 mol; at 65 kJ/mol that is
   0.0087 J, against 495.6 J of heat actually lost. UA = 0, the gas block holds
   no water, the solid is flat. No sink exists.

   !! conservation_report CANNOT SEE THIS. It audits MATTER. A flask can hold
   every element to 1e-12 while destroying half a kilojoule. See MILESTONES M12.""")
