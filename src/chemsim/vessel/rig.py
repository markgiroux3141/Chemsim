"""Layer 5 -- a rig: vessels plus what connects them.

``build_phase_arrays`` is the translation from molecules to numbers; this is the
same move for *topology*. A ``Rig`` holds vessels and typed connections, resolves
them to the flat index/coefficient arrays Layer 4 integrates, and reports the
result back in glassware terms. After ``arrays()`` nothing downstream knows what
a condenser is.

The whole point is that "condenser" is not a class. A condenser is a cold vessel
with a vapour path in and a liquid path back, so it is built the same way a
flask is and differs only in its parameters and its edges:

    rig = Rig()
    flask = rig.add("flask", Vessel(net, volume=1.0, Q_input=80.0, ...))
    cond  = rig.add("condenser", Vessel(net, volume=0.5, T_env=288.0, UA=40.0, ...))
    rig.vapour("flask", "condenser", k=2.0)   # vapour rises
    rig.drain("condenser", "flask", k=0.5)    # condensate runs back
    rig.run(1800.0)

That is reflux. Nothing else was needed, because the condensation itself is the
vessel's existing phase model discovering that ``p > p_eq`` in a cold vessel.

**Vessels in a rig must share one network.** That is not a simplification of
convenience -- it is what makes every block of the state vector the same shape,
and Layer 5 already required it for ``pour_into``. The cost is that a condenser
carries state for species it will never see; the benefit is that the coupled
system is a uniform array rather than a ragged one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from chemsim.numerics.rig_integrator import (
    DRAIN,
    EDGE_NAMES,
    METER,
    THERMAL,
    VAPOUR,
    EdgeArrays,
    RigIntegrator,
)
from chemsim.vessel.vessel import Vessel, VesselState, WaitOutcome


@dataclass
class Connection:
    """One typed link between two vessels. Data, like ``ReactionTemplate``."""

    kind: int
    a: str
    b: str
    k: float

    @property
    def kind_name(self) -> str:
        return EDGE_NAMES[self.kind]

    def describe(self) -> str:
        arrow = "<->" if self.kind in (VAPOUR, THERMAL) else "->"
        return f"{self.a} {arrow} {self.b}  [{self.kind_name} k={self.k:g}]"


@dataclass
class Rig:
    """Vessels and the connections between them, integrated as one system."""

    vessels: dict[str, Vessel] = field(default_factory=dict)
    connections: list[Connection] = field(default_factory=list)
    t: float = 0.0

    # -- assembly ------------------------------------------------------------

    def add(self, name: str, vessel: Vessel) -> Vessel:
        if name in self.vessels:
            raise ValueError(f"a vessel named {name!r} is already in this rig")
        if self.vessels:
            first = next(iter(self.vessels.values()))
            if vessel.species != first.species:
                raise ValueError(
                    f"vessel {name!r} is built on a different network -- every "
                    "vessel in a rig must share one, so their state blocks align"
                )
        self.vessels[name] = vessel
        return vessel

    def _connect(self, kind: int, a: str, b: str, k: float) -> Connection:
        for name in (a, b):
            if name not in self.vessels:
                raise KeyError(f"no vessel {name!r}; have {sorted(self.vessels)}")
        if a == b:
            raise ValueError(f"cannot connect {a!r} to itself")
        if k < 0.0:
            raise ValueError(f"conductance must be non-negative, got {k}")
        c = Connection(kind, a, b, float(k))
        self.connections.append(c)
        return c

    def vapour(self, a: str, b: str, k: float = 1.0) -> Connection:
        """A vapour path. Bidirectional -- flow follows the pressure difference."""
        return self._connect(VAPOUR, a, b, k)

    def drain(self, a: str, b: str, k: float = 1.0) -> Connection:
        """Liquid running out of ``a`` into ``b``, first order in a's holdup.

        A drain, not a level-driven flow: no geometry is modelled and none is
        implied. ``k`` is a reciprocal residence time, so 1.0 empties in ~1 s.
        """
        return self._connect(DRAIN, a, b, k)

    def thermal(self, a: str, b: str, UA: float = 1.0) -> Connection:
        """Heat conduction between two vessels, W/K. A bath, a jacket, coolant."""
        return self._connect(THERMAL, a, b, UA)

    def meter(self, a: str, b: str, rate: float = 0.0) -> Connection:
        """A dropping funnel or pump: liquid from ``a`` to ``b`` at mol/s.

        Set ``rate`` to zero to close the tap. Changing it is how addition is
        started and stopped -- deliberately a parameter rather than a time
        window inside the RHS, so the change lands on a step boundary and the
        run stays reproducible.
        """
        return self._connect(METER, a, b, rate)

    def set_rate(self, connection: Connection, rate: float) -> Rig:
        """Open or close a metered connection."""
        connection.k = float(rate)
        return self

    # -- Layer 4 translation -------------------------------------------------

    def arrays(self) -> EdgeArrays:
        """Resolve named connections to flat index/coefficient arrays."""
        order = list(self.vessels)
        idx = {name: i for i, name in enumerate(order)}
        return EdgeArrays(
            kind=np.array([c.kind for c in self.connections], dtype=int),
            a=np.array([idx[c.a] for c in self.connections], dtype=int),
            b=np.array([idx[c.b] for c in self.connections], dtype=int),
            k=np.array([c.k for c in self.connections], dtype=float),
        )

    def integrator(self) -> RigIntegrator:
        """A fresh integrator over the current topology and conditions.

        Rebuilt per call rather than cached, because a connection's rate and a
        vessel's conditions are both mutable between steps -- that is how a tap
        is opened and a mantle turned up. Construction is index bookkeeping.
        """
        return RigIntegrator(
            [self.vessels[name].integrator for name in self.vessels], self.arrays()
        )

    # -- stepping ------------------------------------------------------------

    def _pack(self, integ: RigIntegrator) -> np.ndarray:
        return integ.pack([
            v.integrator.pack(v._nL, v._nL2, v._nG, v._nS, v.T)
            for v in self.vessels.values()
        ])

    def _unpack_into(self, integ: RigIntegrator, y: np.ndarray) -> None:
        for (nL, nL2, nG, nS, T), v in zip(integ.unpack(y), self.vessels.values()):
            v._nL, v._nL2, v._nG, v._nS, v.T = nL, nL2, nG, nS, T

    def step(self, dt: float, **kw) -> dict[str, VesselState]:
        """Advance every vessel together by dt seconds."""
        integ = self.integrator()
        y = integ.step(self._pack(integ), dt, **kw)
        self._unpack_into(integ, y)
        self.t += dt
        for v in self.vessels.values():
            v.t += dt
        return self.state()

    def wait_until(self, vessel: str, conditions, timeout: float, **kw):
        """Advance the rig until a condition holds IN ONE VESSEL, or time out.

        ⚠ THE CONDITION IS ON ONE VESSEL AND THE TRAJECTORY IS THE WHOLE RIG'S,
        and that separation is the whole reason this is not just
        ``Vessel.wait_until``. "The head has reached 353 K" is a statement about
        the head; WHEN it happens depends on the pot, the mantle and the vapour
        edge between them. A cut in a fractional distillation is called off
        exactly that number, so locating it against a head integrated on its own
        would find an instant the real run never passes through.

        The condition vocabulary is unchanged -- ``vessel.conditions`` compiles
        against the named vessel's own integrator, and the resulting root is
        LIFTED to the rig's state vector by that vessel's slice. So every
        condition that works on a lone flask works here, on any vessel in the rig.

        ⚠⚠ **EXCEPT ONE, AND LIFTING IS NOT ENOUGH FOR IT.** Every other condition
        in the vocabulary reads the STATE -- a temperature, a pressure, an amount --
        so a lifted slice of the rig's state vector answers it exactly.
        ``temperature_steady`` reads the DERIVATIVE, and it is the only one that
        does: ``compile_condition`` builds it from the owner vessel's OWN
        ``make_rhs``, which knows nothing about the edges. **On a still head that is
        not an approximation, it is a different question** -- nearly all of a head's
        heat arrives through the vapour edge, so its uncoupled dT/dt is the cooling
        rate of a small flask of hot ethanol sitting in a cold room. MEASURED: a
        column at steady total reflux, head pinned at 351.22 K and unmoving to two
        decimals for 1200 s, gives ``temperature_steady(0.005)`` a **timeout** on
        the lifted root and fires it in **0.0 s** on the coupled one. A protocol
        that floods a column and waits for it to settle -- exactly what the first
        column attempt was missing -- cannot be written with the lifted version.

        So this one root is built against the RIG's own RHS at the owner's
        temperature index. Same lesson as ``step_until``'s, one level deeper: it is
        not only WHEN a condition is located that belongs to the coupled
        trajectory, it is what the condition itself computes.
        """
        from chemsim.vessel.conditions import Condition, compile_condition

        if vessel not in self.vessels:
            raise KeyError(f"no vessel {vessel!r}; have {sorted(self.vessels)}")
        want = [conditions] if isinstance(conditions, Condition) else list(conditions)
        if not want:
            raise ValueError("wait_until needs at least one condition")
        if timeout <= 0.0:
            raise ValueError(f"timeout must be positive, got {timeout}")

        owner = self.vessels[vessel]
        integ = self.integrator()
        where = integ.slice_of(list(self.vessels).index(vessel))
        # The owner's temperature row in the RIG's vector -- the last entry of its
        # block, the same place ``VesselIntegrator`` puts it in a lone one.
        T_row = where.stop - 1
        coupled = None
        roots = []
        for cond in want:
            if cond.kind == "temperature_steady":
                if coupled is None:
                    coupled = integ.make_rhs()
                roots.append(
                    lambda t, y, _l=float(cond.value): (
                        _l - abs(float(coupled(t, y)[T_row]))
                    )
                )
                continue
            f = compile_condition(cond, owner)
            roots.append(lambda t, y, _f=f: float(_f(t, y[where])))
        stop = integ.step_until(self._pack(integ), timeout, roots, **kw)
        self._unpack_into(integ, stop.y)
        self.t += stop.elapsed
        for v in self.vessels.values():
            v.t += stop.elapsed
        return WaitOutcome(
            elapsed=stop.elapsed,
            fired=None if stop.fired is None else want[stop.fired],
            already=stop.already,
            timed_out=stop.fired is None,
            state=owner.state(),
        )

    def run(self, duration: float, **kw):
        """Integrate the whole rig over a duration in one solve."""
        integ = self.integrator()
        y0 = self._pack(integ)
        sol = integ.run(y0, (0.0, float(duration)), **kw)
        if not sol.success:
            lines = [
                f"rig integration failed after {float(sol.t[-1]):.4g} s of "
                f"{duration:.4g} s: {sol.message}"
            ]
            for v, sub in enumerate(integ.integrators):
                for note in sub.diagnose(y0[integ.slice_of(v)]):
                    lines.append(f"  - vessel {v}: {note}")
            raise RuntimeError(chr(10).join(lines))
        # ⚠ Raw, per vessel, BEFORE the projection: the rig projects across ALL
        # vessels at once, so a cancelling dipole straddling two of them would be
        # settled and invisible by the time anything looked.
        for v, sub in enumerate(integ.integrators):
            sub.check_raw_solution(sol.y[integ.slice_of(v), -1])
        self._unpack_into(integ, integ.project(sol.y[:, -1]))
        self.t += float(duration)
        for v in self.vessels.values():
            v.t += float(duration)
        return sol

    # -- reporting -----------------------------------------------------------

    def state(self) -> dict[str, VesselState]:
        return {name: v.state() for name, v in self.vessels.items()}

    def conservation_report(self) -> str:
        """What the non-negative projection could not conserve across the rig, or "".

        ⚠ **THIS CHANNEL EXISTED AND NOTHING WAS READING IT, WHICH IS HOW A REAL
        CONSERVATION BUG STAYED HIDDEN.** ``project_non_negative`` keeps every
        species' total exactly, except for a species whose total has itself gone
        negative -- there is nothing positive left to settle that against, so the
        residual is genuinely created. Its docstring says such a residual "is
        bounded by round-off", and for a lone vessel it is.
        **Wherever a BULK FLOW term is involved it is not**, and that is not
        rig-specific however it looks from here. Both the rig's vapour edge and the
        lone vessel's VENT take the donor's composition (or its pressure) from a
        CLAMPED gas block, so once a component drifts below zero the flux cannot see
        it and nothing restores it. After 3000 s of reflux a rig's total nitrogen is
        about **-0.34 mol against the 0.06 mol of air it started with**; a single
        open flask running an ordinary esterification at the DEFAULT ``k_vent`` of
        1e3 manages **-2.30 mol against 0.023 charged, i.e. 100x**. Matter destroyed,
        not a dipole. The physics results survive because the projection conserves
        what it can and the air is not what those tests measure, but the trajectory
        is visiting states that cannot exist. ``validation/vent_leak.py`` is the
        attribution and it is the top item of docs/history/NEXT_SESSION.md.

        Aggregated across vessels because the rig conserves each species as ONE
        system -- that is the whole reason it is one state vector -- and because
        ``RigIntegrator.project`` hangs the residual on vessel 0, so reading a single
        vessel's report would attribute a coupled failure to an arbitrary flask.
        """
        totals: dict[str, float] = {}
        for v in self.vessels.values():
            created = v.integrator.created
            for i, sp in enumerate(v.species):
                if created[i] > 0.0:
                    totals[sp] = totals.get(sp, 0.0) + float(created[i])
        if not totals:
            return ""
        worst = sorted(totals.items(), key=lambda kv: -kv[1])
        shown = ", ".join(f"{sp} {amt:.3e} mol" for sp, amt in worst[:4])
        return (
            f"the non-negative projection CREATED matter for {len(totals)} "
            f"species whose totals went negative: {shown}. This is a real "
            f"conservation failure rather than round-off: a BULK FLOW term reads a "
            f"CLAMPED gas block, so it cannot see a component that has gone "
            f"negative and nothing restores it. Not rig-specific -- the same defect "
            f"reaches an ordinary OPEN FLASK through the vent, ~100x its own air at "
            f"the default k_vent. See validation/vent_leak.py"
        )

    def describe(self) -> str:
        lines = [
            f"rig t={self.t:.1f} s   {len(self.vessels)} vessel(s), "
            f"{len(self.connections)} connection(s)"
        ]
        for name, v in self.vessels.items():
            lines.append(f"  [{name}] {v.describe()}")
        for c in self.connections:
            lines.append(f"  {c.describe()}")
        return "\n".join(lines)
