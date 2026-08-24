"""M12: an insulated flask that destroyed 495 J -- the controls, and the cause.

The symptom: an insulated metathesis (UA = 0, no wall mass) reached its predicted
+0.1577 K at t = 600 s, still read +0.1575 at t = 1200 s, and then decayed to
+0.0378 by t = 3600 s in the SAME single call -- **after the chemistry had
stopped**. Between those two points the largest mole change in any block was
1.4e-07 mol, worth 0.0087 J at 65 kJ/mol, against 495.6 J of heat. No sink
existed, and ``conservation_report`` could not see it because it audits matter.

WHAT EACH CONTROL BELOW REFUTED, in the order they were run:

    D  ions, no precipitation, at ambient      -- no drift without an event
    C  water only, started 0.16 K WARM         -- no generic evaporative loss
    B  the metathesis flask, precipitation OFF -- no generic BDF weighting problem
    E1/E2  the term present but nothing supersaturated -- the CODE is free
    E3/E4  the event actually happening        -- the EVENT is what cost

So it needed the event, and it was not the term's arithmetic. Two more controls
finished it, and both are worth remembering because each refuted a fix:

    * TOLERANCE IS NOT THE LEVER, IN EITHER DIRECTION. Tightening ``atol`` alone
      recovered the answer (-1.2e-1 K -> -1.5e-4 K) even though ``atol`` never
      reaches the temperature, whose scale is ``rtol * 298 K``. And integrating
      (T - T0) instead of T -- which tightens the temperature's error budget by
      three orders -- made it WORSE, +2.0e-2 K at default and 31,324 steps at
      rtol 1e-8. A fix aimed at the temperature's tolerance was the obvious one
      and it was wrong.
    * IT WAS NOT THE FORMULATION EITHER. Same RHS, same tolerances: Radau lands
      at -5.5e-5 K and LSODA at +8.8e-5 K where BDF lands at -1.2e-1. But
      neither survives the project's real work -- Radau does not finish the
      benzoic-acid prep in 8 minutes where BDF takes 39 s, and LSODA fails it
      outright at t = 0.013 s -- so "use another integrator" was not available.

THE CAUSE, and it was in Layer 2 rather than in the solver at all. Water
autoionization declares ``Ea = 60 kJ/mol``, chosen to sit just above water's
dissociation enthalpy of 55.8 so the elementary-barrier clamp does not fire.
``detailed_balance`` then hands the REVERSE a barrier of 4.2 kJ/mol and a rate
constant of **9.4e18 L/(mol s) -- 9.4e7 times the collision limit**, for a
recombination measured at 1.4e11 (Eigen). The very choice that avoids one clamp
put the derived reverse eight orders past what a collision can deliver.

A pair running 1e8 times too fast turns over 9.4e4 mol/s in a 1 L flask, so its
two heat terms sit at +-5.2e9 W either side of a net of a fraction of a watt: a
twelve-order cancellation, on the stiffest mode in the vessel, invisible to a
solver whose error control is denominated in kelvin and moles and never in
joules. Per-step, three consecutive BDF steps of exactly 167.63 s destroyed
253 + 145 + 69 = 467 of the 495 J while the composition did not move by a
picomole.

THE FIX is ``reactions.thermo.COLLISION_LIMIT``: if either direction's rate
constant at 298 K exceeds it, BOTH pre-exponentials are scaled by the same
factor, which leaves K = k_f/k_r invariant EXACTLY -- Kw stays 1.0022e-14, so no
pKa and no pH can move. Water's equilibrium then arrives in ~0.3 ms instead of
~0.5 ps, which is still instant against any chemistry here. Measured after:
E4 reads +0.15759 K at 3600 s, agrees with itself at every tolerance rung from
1e-6 to 1e-9, and costs 132 steps instead of 186.

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
   the RHS is free. E3 against E2 was once 0.05 K poorer and E4 read +0.0378
   where it should read +0.1576; both are now whole. E3 finishes at its 0.16 K
   head start PLUS its own reaction heat, which are independent quantities that
   used to interfere.

   !! WHAT MADE IT A DEFECT WAS THE BOUND. Between t=1200 and t=3600 the largest
   mole change in ANY block was 1.4e-07 mol; at 65 kJ/mol that is 0.0087 J,
   against 495.6 J of heat actually lost. UA = 0, the gas block held no water,
   the solid was flat. No sink existed.

   !! AND THE CAUSE WAS A DERIVED RATE CONSTANT, NOT THE SOLVER. Detailed
   balance gave water's reverse 9.4e18 L/(mol s), 9.4e7x the collision limit,
   so its two heat terms were +-5.2e9 W around a net of a fraction of a watt.
   Three BDF steps of 167.63 s destroyed 467 J of the 495. The guard is
   reactions.thermo.COLLISION_LIMIT; the standing audit is
   validation/rate_ceiling.py; Kw is unmoved at 1.0022e-14.""")

# ---------------------------------------------------------------------------
# THE STEP AUDIT. This is the panel that localised it, and it is kept because a
# per-step energy budget is the only view in which "the composition did not move
# and the temperature did" is a single readable line.
# ---------------------------------------------------------------------------
print("\n=== PER-STEP ENERGY BUDGET of the E4 flask, worst steps ===",
      flush=True)
v = charged(298.15, precipitation=True, mol=0.01)
_itg = v.integrator
_y0 = _itg.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
_sol = _itg.run(_y0, (0.0, SPAN))
_n = _itg.n
_jh = list(NET.species).index("[OH3+]")
_dH = float(_itg.kin.dH[0])
_Cp = _itg.energy_terms(_sol.y[:, 0], boundary=_y0)["Cp_total"]
_rows = []
for _i in range(1, len(_sol.t)):
    _dT = _sol.y[-1, _i] - _sol.y[-1, _i - 1]
    _dn = _sol.y[_jh, _i] - _sol.y[_jh, _i - 1]
    _rows.append((_sol.t[_i - 1], _sol.t[_i] - _sol.t[_i - 1], _dT, _dn,
                  _Cp * _dT + _dH * _dn))
_late = [r for r in _rows if r[0] >= 1182.0]
print(f"  Cp {_Cp:.2f} J/K   steps {len(_rows)}   "
      f"unaccounted after t=1182 s: {sum(r[4] for r in _late):+.3f} J")
print(f"  {'t_from':>9} {'h/s':>9} {'dT/K':>13} {'dn(H3O+)':>13} "
      f"{'unaccounted J':>15}")
for _r in sorted(_rows, key=lambda r: -abs(r[4]))[:5]:
    print(f"  {_r[0]:9.1f} {_r[1]:9.2f} {_r[2]:+13.4e} {_r[3]:+13.3e} "
          f"{_r[4]:+15.3f}")
print("""
   !! BEFORE THE GUARD this table's top three rows were three CONSECUTIVE steps
   of exactly 167.63 s, at -253.4, -145.2 and -69.0 J, with dn(H3O+) of order
   1e-10 -- a temperature falling on its own while the composition stood still.
   That shape is the signature to look for: energy leaving with no matter
   moving. If it comes back, read validation/rate_ceiling.py first.""")
