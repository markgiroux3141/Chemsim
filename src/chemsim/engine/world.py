"""Layer 6 -- the headless deterministic stepper.

The top of the stack, and the smallest layer in it. A ``World`` owns vessels and a
clock, applies player events at step boundaries, and can write itself to a dict
and read itself back. It contains no chemistry: every physical question is
delegated downward.

Three properties it exists to guarantee:

**Headless.** ``step(dt)`` is the entire interface. A real-time frontend calls it
each frame, a batch experiment calls it in a loop, a test calls it once. None of
them are privileged, and the engine has no opinion about rendering or wall-clock
time.

**Deterministic.** A run is a pure function of (scenario, SCRIPT). Events fire only
between integrations, never inside one, so an outcome can never depend on the
solver's adaptive step size. Randomness -- for future stochastic effects -- comes
from a single seeded generator that is itself saved, so a reload continues the same
stream rather than starting a new one.

⚠ **That sentence used to read "(scenario, event list)", and mending it was the
deliberate half of adding ``wait_until``.** An event is an instant; a wait is a
span whose end is DISCOVERED by a solver root rather than declared by the caller,
so the event list alone no longer says when anything happened. The ``script`` is
the ordered record of everything asked of the world -- events scheduled, intervals
stepped, conditions waited on -- and it is what the guarantee now rests on. It
stores the CONDITION and never the instant it resolved to, for the reason set out
in full on ``World.script``: the instant is derived data, and this project already
declines to store derived data beside its source (a ``Scenario`` keeps templates,
not the network they generate).

**Save/loadable.** The save stores the *recipe* and the *state*, never the derived
network: see ``scenario.py``. The format is version-stamped, because the state
vector will grow as lower layers gain phases, and a save written today must fail
loudly against an incompatible reader rather than silently mis-map fields.
"""

from __future__ import annotations

import heapq
import random
from dataclasses import dataclass, field

import numpy as np

from chemsim.engine.events import (
    ALL_KINDS,
    CHARGE,
    FILL_HEADSPACE,
    FILTER,
    SET_EDGE,
    SET_ENVIRONMENT,
    SET_HEAT,
    SET_SHAKING,
    SET_STIRRING,
    SET_VENT,
    SWAP_RECEIVER,
    TRANSFER,
    Event,
)
from chemsim.engine.scenario import EDGE_KINDS, Scenario, VesselSpec
from chemsim.network import build_network
from chemsim.properties import (
    CondensedProvider,
    ThermochemistryProvider,
    VolatilityProvider,
    electrolyte_provider,
)
from chemsim.vessel import Condition, Rig, TransferLosses, Vessel, WaitOutcome

# 1: liquid+gas. 2: +solid. 3: +a second liquid layer.
# 4: +the SCRIPT -- see ``World._script``. A run stopped being a pure function of
#    (scenario, event list) the moment a duration could be DISCOVERED rather than
#    declared, because the event list no longer says when anything happened. The
#    script is what restores the guarantee, so a save written before it exists
#    cannot be replayed and must not pretend it can.
# 5: +the APPARATUS -- ``Scenario.edges``, plus the SWAP_RECEIVER and SET_EDGE
#    verbs. A rig used to exist only in Python, so a still could not be saved and
#    "collect the fraction boiling between 351 and 355 K" was unsayable rather
#    than unimplemented. A version-4 save has no edges and would silently replay
#    as an uncoupled bench, which is a different experiment; hence the bump.
SAVE_VERSION = 5


@dataclass
class World:
    """Vessels, a clock, and an event queue."""

    scenario: Scenario
    seed: int = 0

    t: float = 0.0
    vessels: dict[str, Vessel] = field(default_factory=dict, repr=False)
    _queue: list[Event] = field(default_factory=list, repr=False)
    _seq: int = 0
    _log: list[str] = field(default_factory=list, repr=False)
    # Everything that was ever ASKED of this world, in order: events scheduled,
    # intervals stepped, and conditions waited on. See ``script`` and ``replay``.
    _script: list[dict] = field(default_factory=list, repr=False)

    # -- construction --------------------------------------------------------

    def __post_init__(self) -> None:
        self.thermo = (
            electrolyte_provider() if self.scenario.electrolyte
            else ThermochemistryProvider()
        )
        self.volatility = VolatilityProvider(self.thermo)
        self.condensed = CondensedProvider(self.thermo, self.volatility)
        self.rng = random.Random(self.seed)

        templates = [t.build() for t in self.scenario.templates]
        self.network = build_network(
            self.scenario.feed_species,
            templates,
            max_species=self.scenario.max_species,
            thermo=self.thermo,
            T_ref=self.scenario.T_build,
        )

        if not self.vessels:
            for vid, spec in self.scenario.vessels.items():
                self.vessels[vid] = self._make_vessel(spec)
        self._build_rig()

    def _build_rig(self) -> None:
        """Resolve ``scenario.edges`` into a ``Rig``, or leave it None.

        ⚠ NONE IS A REAL STATE AND NOT A DEGENERATE ONE. With no edges the world
        keeps its original per-vessel stepping path exactly, so every number this
        project measured before rigs existed is bit-identical -- the same
        guarantee ``lle=False`` and ``losses=None`` carry. A rig integrates all
        its vessels as ONE stiff system, which is the right answer for coupled
        glassware and a needless expense for a bench of separate flasks.
        """
        self.rig: Rig | None = None
        if not self.scenario.edges:
            return
        rig = Rig()
        for vid, v in self.vessels.items():
            rig.add(vid, v)
        for i, e in enumerate(self.scenario.edges):
            if e.kind not in EDGE_KINDS:
                raise ValueError(
                    f"edge {i} has kind {e.kind!r}; the apparatus verbs are "
                    f"{', '.join(EDGE_KINDS)}"
                )
            for end in (e.a, e.b):
                if end not in self.vessels:
                    raise KeyError(
                        f"edge {i} ({e.kind}) names vessel {end!r}, which the "
                        f"scenario does not declare; have {sorted(self.vessels)}"
                    )
            getattr(rig, e.kind)(e.a, e.b, e.k)
        self.rig = rig

    def _edge(self, index: int):
        """One apparatus edge, by index, refused clearly when there is no rig."""
        if self.rig is None:
            raise ValueError(
                "this world has no apparatus, so there is no edge to change. "
                "Declare Scenario.edges -- an apparatus is part of the scenario"
            )
        if not 0 <= index < len(self.rig.connections):
            raise IndexError(
                f"edge {index} does not exist; this rig has "
                f"{len(self.rig.connections)} "
                f"({', '.join(c.describe() for c in self.rig.connections)})"
            )
        return self.rig.connections[index]

    def _make_vessel(self, spec: VesselSpec) -> Vessel:
        # Transfer losses come through the SPEC, so a prep run as a scenario can
        # have them. They used to be constructible only by calling ``Vessel``
        # directly, which meant the one path that is replayable from a save was
        # also the one path that could not lose anything -- the honest preps and
        # the reproducible preps were disjoint sets.
        losses = (
            None
            if spec.drain_time is None
            else TransferLosses(
                drain_time=spec.drain_time,
                kinematic_viscosity=spec.kinematic_viscosity,
                crystal_size=spec.crystal_size,
                packing_fraction=spec.packing_fraction,
            )
        )
        return Vessel(
            self.network,
            volume=spec.volume,
            T=spec.T,
            T_env=spec.T_env,
            UA=spec.UA,
            Q_input=spec.Q_input,
            P_ambient=spec.P_ambient,
            kla=spec.kla,
            k_vent=spec.k_vent,
            k_diss=spec.k_diss,
            k_lle=spec.k_lle,
            lle=spec.lle,
            losses=losses,
            heat_capacity=spec.heat_capacity,
            ingress=dict(spec.ingress),
            thermo=self.thermo,
            volatility=self.volatility,
            condensed=self.condensed,
        )

    # -- events --------------------------------------------------------------

    def schedule(self, t: float, kind: str, vessel: str = "", **payload) -> Event:
        """Queue a player action for simulated time ``t``.

        Scheduling in the past is rejected rather than silently applied late --
        that would break the guarantee that replaying an event list reproduces a
        run, since the outcome would depend on when the call happened.
        """
        if kind not in ALL_KINDS:
            raise ValueError(f"unknown event kind {kind!r}; expected one of {sorted(ALL_KINDS)}")
        if t < self.t:
            raise ValueError(
                f"cannot schedule {kind!r} at t={t} -- the world is already at t={self.t}"
            )
        if vessel and vessel not in self.vessels:
            raise KeyError(f"no vessel {vessel!r}; have {sorted(self.vessels)}")

        ev = Event(t=t, seq=self._seq, kind=kind, vessel=vessel, payload=payload)
        self._seq += 1
        heapq.heappush(self._queue, ev)
        self._script.append({"do": "schedule", "event": ev.to_dict()})
        return ev

    def now(self, kind: str, vessel: str = "", **payload) -> Event:
        """Schedule an action at the current instant -- it fires on the next step."""
        return self.schedule(self.t, kind, vessel, **payload)

    def flush(self) -> int:
        """Apply every event already due, without integrating. Returns how many.

        ⚠ TRAJECTORY-NEUTRAL BY CONSTRUCTION, which is the only reason it may
        exist. ``_step`` applies an event at exactly the current instant with no
        intervening ``_advance`` -- so these events fire in this order, with this
        state, whether they are flushed now or left for the next step. Nothing is
        added to the script either: the events are already in it, at the instants
        they were already scheduled for, so a replay that never calls this reaches
        the same place. ``_wait_until`` has always done this inline for events that
        come due mid-wait.

        It exists for a LOOK, not for physics. ``now`` schedules for the current
        instant, so a frontend that charges a reagent and then renders the flask
        shows one without the reagent in it until something is stepped -- which
        reads as a lost click rather than as the event queue behaving correctly.
        """
        fired = 0
        while self._queue and self._queue[0].t <= self.t:
            self._apply(heapq.heappop(self._queue))
            fired += 1
        return fired

    def _apply(self, ev: Event) -> None:
        v = self.vessels[ev.vessel] if ev.vessel else None
        p = ev.payload

        if ev.kind == CHARGE:
            v.charge(p["amounts"], phase=p.get("phase", "liquid"))
        elif ev.kind == SET_HEAT:
            v.set_heat(float(p["watts"]))
        elif ev.kind == SET_ENVIRONMENT:
            v.set_environment(float(p["T_env"]))
        elif ev.kind == SET_VENT:
            v.set_vent(float(p["k_vent"]))
        elif ev.kind == SET_STIRRING:
            v.set_stirring(float(p["kla"]))
        elif ev.kind == SET_SHAKING:
            v.set_shaking(float(p["k_lle"]))
        elif ev.kind == FILL_HEADSPACE:
            v.fill_headspace(p.get("composition"))
        elif ev.kind == TRANSFER:
            dest = self.vessels[p["to"]]
            moved = v.pour_into(
                dest, fraction=float(p.get("fraction", 1.0)), phase=p.get("phase", "liquid")
            )
            self._log.append(
                f"t={self.t:.1f} transfer {ev.vessel}->{p['to']}: {moved:.4f} mol"
            )
        elif ev.kind == SWAP_RECEIVER:
            c = self._edge(int(ev.payload["edge"]))
            to = str(ev.payload["to"])
            if to not in self.vessels:
                raise KeyError(
                    f"cannot swap in {to!r}: no such vessel; have "
                    f"{sorted(self.vessels)}"
                )
            end = str(ev.payload.get("end", "b"))
            if end not in ("a", "b"):
                raise ValueError(f"end must be 'a' or 'b', got {end!r}")
            was = getattr(c, end)
            if to == (c.a if end == "b" else c.b):
                raise ValueError(
                    f"swapping {end} to {to!r} would connect it to itself"
                )
            setattr(c, end, to)
            self._log.append(
                f"t={self.t:.3f} swap_receiver edge {ev.payload['edge']} "
                f"{end}: {was} -> {to}"
            )

        elif ev.kind == SET_EDGE:
            c = self._edge(int(ev.payload["edge"]))
            k = float(ev.payload["k"])
            if k < 0.0:
                raise ValueError(f"conductance must be non-negative, got {k}")
            self._log.append(
                f"t={self.t:.3f} set_edge {ev.payload['edge']} k={c.k:g} -> {k:g}"
            )
            c.k = k

        elif ev.kind == FILTER:
            # Either destination may be absent, which is how "filter it off and
            # bin the filtrate" is expressed. Discarding is a real bench action
            # and must be sayable; it is not the same as forgetting to say it,
            # so the log records what was thrown away as well as what was kept.
            # ⚠ A LOUD REFUSAL RATHER THAN A SILENT REINTERPRETATION. ``retention``
            # was a fraction of the LIQUOR and ``porosity`` is the void fraction of
            # the CAKE, so the same number means something entirely different --
            # 0.05 used to leave 50 mL of mother liquor on 17 mL of crystals and now
            # leaves 0.9 mL. Accepting the old key and treating it as the new one
            # would move every purity number in a saved run without saying so.
            if "retention" in p:
                raise ValueError(
                    "FILTER no longer takes 'retention' (a fraction of the "
                    "liquor); it takes 'porosity', the VOID FRACTION OF THE CAKE, "
                    "and the liquor held is porosity*V_solid/(1-porosity). A "
                    "well-pulled Buchner is ~0.4, not ~0.05 -- see "
                    "Vessel.filter_into"
                )
            got = v.filter_into(
                self.vessels.get(p.get("filtrate")) if p.get("filtrate") else None,
                self.vessels.get(p.get("cake")) if p.get("cake") else None,
                porosity=float(p.get("porosity", 0.4)),
                passthrough=float(p.get("passthrough", 0.0)),
            )
            self._log.append(
                f"t={self.t:.1f} filter {ev.vessel}: cake {got.cake_solid:.4f} mol "
                f"solid + {got.cake_liquid:.4f} mol liquor "
                f"-> {p.get('cake') or 'discarded'}; filtrate "
                f"{got.filtrate_liquid:.4f} mol -> {p.get('filtrate') or 'discarded'}"
            )
        else:  # unreachable: schedule() validates the kind
            raise ValueError(f"unhandled event kind {ev.kind!r}")

    # -- stepping ------------------------------------------------------------

    def step(self, dt: float, **kw) -> None:
        """Advance every vessel by dt, firing any events due within the interval.

        The interval is split at each event time so that an action scheduled
        mid-step takes effect at exactly that instant, not at the boundary. That
        keeps the result independent of the caller's choice of dt -- stepping
        once by 100 s and stepping 100 times by 1 s agree to the precision the
        vessel's own boundary decisions allow, which is what ``_script`` is for.
        """
        if dt <= 0.0:
            raise ValueError(f"dt must be positive, got {dt}")
        self._script.append({"do": "step", "dt": float(dt)})
        self._step(dt, **kw)

    def _step(self, dt: float, **kw) -> None:
        """``step`` without the script entry -- what ``replay`` re-executes."""
        target = self.t + dt

        while self._queue and self._queue[0].t <= target:
            ev = heapq.heappop(self._queue)
            if ev.t > self.t:
                self._advance(ev.t - self.t, **kw)
            self._apply(ev)

        if target > self.t:
            self._advance(target - self.t, **kw)
        self.t = target

    def _advance(self, dt: float, **kw) -> None:
        # ⚠ THE UNCOUPLED PATH IS KEPT EXACTLY, not routed through a rig of one.
        # A one-vessel rig is documented as bit-identical to a lone vessel, but
        # "documented" is not "free": the rig integrates every vessel as one
        # system, so a bench of six independent flasks would become one stiff
        # solve six times the size for no physical reason. Edges are the signal
        # that the glassware is actually connected.
        if self.rig is None:
            for v in self.vessels.values():
                v.step(dt, **kw)
        else:
            self.rig.step(dt, **kw)
        self.t += dt

    def run(self, duration: float, dt: float, **kw) -> None:
        """Step repeatedly. dt is the *event resolution*, not a solver timestep --
        the integrator picks its own internal steps inside each call."""
        n = int(round(duration / dt))
        for _ in range(n):
            self.step(dt, **kw)

    # -- waiting, which is stepping with the duration discovered -------------

    def wait_until(
        self,
        vessel: str,
        conditions: Condition | list[Condition],
        timeout: float,
        **kw,
    ) -> WaitOutcome:
        """Advance until a condition holds in ``vessel``, or ``timeout`` elapses.

        The verb that was missing, and the reason it is a DRIVING call rather than
        an ``Event``: an event is an instant, and this is a span whose end is not
        known when it starts. Mixing the two would mean an event queue holding an
        entry with no time in it.

        Semantics worth being explicit about, because each one is a decision:

        * **PENDING EVENTS STILL FIRE ON TIME.** The wait is chopped at the next
          scheduled event, that event is applied at its own instant, and the wait
          resumes with whatever timeout is left. Otherwise a wait would swallow a
          dropwise addition due in the middle of it.
        * **EVERY VESSEL ADVANCES BY THE DISCOVERED TIME**, not by the timeout.
          Vessels in a ``World`` are not coupled to each other -- coupling is what
          a ``Rig`` is for -- so the owning vessel can be run first to learn the
          instant and the rest brought to the same clock exactly. With a rig this
          would need the root to be a function of the whole rig state.
        * **THE TIMEOUT IS REQUIRED.** A condition that never comes true is an
          ordinary thing to ask for by mistake, and an unbounded wait is a hang.
        """
        want = [conditions] if isinstance(conditions, Condition) else list(conditions)
        if vessel not in self.vessels:
            raise KeyError(f"no vessel {vessel!r}; have {sorted(self.vessels)}")
        if timeout <= 0.0:
            raise ValueError(f"timeout must be positive, got {timeout}")
        self._script.append({
            "do": "wait_until",
            "vessel": vessel,
            "timeout": float(timeout),
            "conditions": [c.to_dict() for c in want],
        })
        return self._wait_until(vessel, want, timeout, **kw)

    def _wait_until(
        self, vessel: str, want: list[Condition], timeout: float, **kw
    ) -> WaitOutcome:
        owner = self.vessels[vessel]
        others = [v for k, v in self.vessels.items() if k != vessel]
        # ⚠ SPENT IS SUMMED OVER THE WHOLE WAIT, not taken from the last leg. A
        # wait chopped by two scheduled events is three integrations, and a caller
        # reading the last leg's elapsed time would be told how long the last
        # fragment took rather than how long it waited.
        spent = 0.0
        while spent < timeout:
            horizon = timeout - spent
            if self._queue:
                gap = self._queue[0].t - self.t
                # ⚠ AN EPSILON RATHER THAN ZERO, and it is a liveness guard not a
                # tolerance. A discovered instant lands wherever the root solve puts
                # it, so an event's time can end up a few 1e-16 ahead of the clock;
                # integrating that gap adds nothing to ``spent`` in floating point
                # and the loop would never terminate. An event within a picosecond
                # of now is due now.
                if gap <= 1.0e-12:
                    self._apply(heapq.heappop(self._queue))
                    continue
                horizon = min(horizon, gap)

            # ⚠ COUPLED GLASSWARE MUST LOCATE THE ROOT ON THE COUPLED
            # TRAJECTORY. The uncoupled branch below integrates the OWNER alone
            # and then advances the others by however long that took, which is
            # right for separate flasks on a bench and wrong for a still: a
            # head's temperature is set by what arrives from the pot, so a head
            # integrated on its own crosses 353 K at an instant the real run
            # never passes through -- and a cut is called off exactly that
            # number. See ``Rig.wait_until``.
            if self.rig is not None:
                leg = self.rig.wait_until(vessel, want, horizon, **kw)
            else:
                leg = owner.wait_until(want, horizon, **kw)
                if leg.elapsed > 0.0:
                    for v in others:
                        v.step(leg.elapsed, **kw)
            self.t += leg.elapsed
            spent += leg.elapsed
            if not leg.timed_out:
                out = WaitOutcome(
                    elapsed=spent, fired=leg.fired, already=leg.already,
                    timed_out=False, state=leg.state,
                )
                self._log.append(f"t={self.t:.1f} wait {vessel}: {out.describe()}")
                return out
        self._log.append(
            f"t={self.t:.1f} wait {vessel}: timed out after {spent:.1f} s "
            f"with none of {', '.join(c.describe() for c in want)}"
        )
        return WaitOutcome(
            elapsed=spent, fired=None, already=False, timed_out=True,
            state=owner.state(),
        )

    # -- taking a CUT, which is three of the above composed -----------------

    def collect_fraction(
        self,
        vessel: str,
        edge: int,
        into: str,
        enter: float,
        leave: float,
        timeout: float,
        park: str | None = None,
        **kw,
    ) -> dict:
        """Run until the head enters a temperature band, collect, then stop.

        **This is what "collect the fraction boiling between 351 and 355 K" is,
        and until now it was UNSAYABLE rather than unimplemented.** A still had
        no way to change its receiver, so everything came over into one pot and
        the enrichment the column genuinely achieved washed back out -- measured
        on a 50/50 ethanol/water charge, head mole fraction 0.655 at 200 s and
        back to 0.500 by 1200 s. Nothing was wrong with the physics.

        Composed of three primitives, none of them new: wait until ``vessel``
        reaches ``enter``, re-point the drain ``edge`` at ``into``, wait until it
        reaches ``leave``, then re-point at ``park``.

        ⚠⚠ **A CUT IS A DISCOVERED INSTANT, SO THIS STORES THE CONDITION AND
        NEVER THE TIMESTAMP.** That is why it is a scripted verb of its own rather
        than sugar over ``now(SWAP_RECEIVER)``: an event carries an absolute
        ``t``, so building the swap from one would bake this run's discovered
        crossing into the recipe, and a replay whose root landed a picosecond
        elsewhere would either refuse to schedule in the past or -- worse -- swap
        at an instant it did not itself find. **A replayed distillation has to
        locate its own cut points.** Same rule ``wait_until`` follows and the
        reason SAVE_VERSION reached 4.

        ⚠ The band is a pair of temperatures on the HEAD, not on the pot, because
        that is what a chemist actually watches -- and locating it needs the
        COUPLED trajectory, which is what ``Rig.wait_until`` is for.

        Returns what happened, as data: whether the band was entered and left at
        all, and the elapsed time of each leg. **A cut that never started is a
        result**, not an error -- a band above everything in the pot is an
        ordinary thing to ask for and the honest answer is "nothing came over".
        """
        if self.rig is None:
            raise ValueError(
                "collect_fraction needs an apparatus: there is no receiver to "
                "swap. Declare Scenario.edges with a drain into a receiver"
            )
        if leave <= enter:
            raise ValueError(
                f"the band must rise: enter={enter} K, leave={leave} K. A cut is "
                f"taken while the head CLIMBS through a range"
            )
        for name in (into, *( (park,) if park else () )):
            if name not in self.vessels:
                raise KeyError(f"no vessel {name!r}; have {sorted(self.vessels)}")

        self._script.append({
            "do": "collect_fraction",
            "vessel": vessel, "edge": int(edge), "into": into,
            "enter": float(enter), "leave": float(leave),
            "timeout": float(timeout), "park": park,
        })
        return self._collect_fraction(
            vessel, edge, into, enter, leave, timeout, park, **kw
        )

    def _collect_fraction(
        self, vessel, edge, into, enter, leave, timeout, park, **kw
    ) -> dict:
        """``collect_fraction`` without the script entry -- what replay re-runs."""
        opened = self._wait_until(vessel, [Condition("temperature_above", enter)],
                                 timeout, **kw)
        if opened.timed_out:
            return {"entered": False, "left": False, "into": into,
                    "wait": opened.elapsed, "collected": 0.0}

        self._swap(edge, into)
        left = self._wait_until(vessel, [Condition("temperature_above", leave)],
                                max(timeout - opened.elapsed, 1.0e-9), **kw)
        if park:
            self._swap(edge, park)
        return {
            "entered": True, "left": not left.timed_out, "into": into,
            "wait": opened.elapsed, "collected": left.elapsed,
        }

    def _swap(self, edge: int, to: str) -> None:
        """Re-point an edge NOW, without going through the queue.

        Deliberately not an ``Event``: an event has an absolute ``t``, and the
        instant this happens was discovered rather than declared. See
        ``collect_fraction``.
        """
        self._apply(Event(t=self.t, seq=self._seq, kind=SWAP_RECEIVER,
                          payload={"edge": int(edge), "to": to}))
        self._seq += 1

    # -- observation ---------------------------------------------------------

    @property
    def pending_events(self) -> list[Event]:
        return sorted(self._queue)

    @property
    def transfer_log(self) -> list[str]:
        return list(self._log)

    @property
    def script(self) -> list[dict]:
        """Everything ever asked of this world, in order -- the RECIPE.

        ⚠ THIS IS THE ANSWER TO A FORK THAT HAD TO BE TAKEN DELIBERATELY, and it
        is worth stating in full because getting it wrong would have been worse
        than not building "wait until" at all.

        A run used to be a pure function of (scenario, event list), pinned to 1e-9
        by ``tests/test_protocol.py``. Once a duration can be DISCOVERED, that
        statement needs mending, and there were exactly two ways to mend it:

          (a) record the discovered INSTANT in the event list. Replay is then
              exact, and the saved artifact is no longer a recipe -- it is a
              transcript. Run it against a slightly different charge and it waits
              the wrong number of seconds, which is precisely the failure that made
              fixed durations the wrong shape in the first place. It is fixed
              durations wearing a condition's name.
          (b) record the CONDITION. The artifact stays a recipe -- it means what
              the chemist meant, and it still means it at a different scale -- and
              replay is only as reproducible as the root solve.

        **(b), and the deciding argument is that this project already made the same
        call once.** A ``Scenario`` stores templates and feed species rather than
        the reaction network they generate, because the network is DERIVED data and
        storing derived data beside its source is how the two drift apart. A
        discovered instant is derived data of exactly that kind. So the condition
        is stored, the instant is not, and the instant is instead REPORTED -- in
        ``transfer_log`` and in the vessel clocks -- as the outcome it is.

        What (b) costs, stated rather than glossed: with fixed times, a change in
        solver tolerance perturbs the trajectory but not the schedule. With
        conditions it perturbs both, so a discovered instant moves by about the
        solver's tolerance and everything after it shifts with it. That is bounded
        by the same tolerance every other number here rests on, and it buys an
        artifact that means something.

        Note also that ``step`` intervals are recorded, not only waits. That is not
        redundancy: freezing a layer's polarity at the integration boundary (see
        ``numerics.vessel_integrator.FREEZE_LAYER_PERMITTIVITY``) made the
        caller's ``dt`` weakly load-bearing, so "how it was stepped" is part of the
        recipe now and pretending otherwise would be the silent kind of
        approximation.
        """
        return [dict(entry) for entry in self._script]

    def describe(self) -> str:
        lines = [f"world t={self.t:.1f} s   {len(self.vessels)} vessel(s)"]
        for vid, v in self.vessels.items():
            lines.append(f"  [{vid}] {v.describe()}")
        if self._queue:
            lines.append(f"  {len(self._queue)} pending event(s)")
        return "\n".join(lines)

    # -- persistence ---------------------------------------------------------

    def save(self) -> dict:
        """Serialize to a plain dict -- JSON-ready, no numpy, no molecules."""
        return {
            "version": SAVE_VERSION,
            "t": self.t,
            "seed": self.seed,
            "rng_state": _encode_rng(self.rng),
            "seq": self._seq,
            "scenario": self.scenario.to_dict(),
            "vessels": {vid: _dump_vessel(v) for vid, v in self.vessels.items()},
            "events": [e.to_dict() for e in sorted(self._queue)],
            "script": self.script,
        }

    @classmethod
    def load(cls, data: dict) -> World:
        """Rebuild a world from a save. Rejects a format it cannot read."""
        version = int(data.get("version", 0))
        if version != SAVE_VERSION:
            raise ValueError(
                f"save format version {version} != {SAVE_VERSION} supported by this "
                "build. Field layouts changed when the vessel gained phases; refusing "
                "to guess at a mapping."
            )

        world = cls(scenario=Scenario.from_dict(data["scenario"]), seed=int(data["seed"]))
        world.t = float(data["t"])
        world._seq = int(data.get("seq", 0))
        _decode_rng(world.rng, data.get("rng_state"))

        for vid, vdata in data["vessels"].items():
            if vid not in world.vessels:
                raise KeyError(f"save contains vessel {vid!r} not present in its scenario")
            _restore_vessel(world.vessels[vid], vdata)

        world._queue = [Event.from_dict(e) for e in data.get("events", [])]
        heapq.heapify(world._queue)
        # Carried, not replayed: ``load`` restores the STATE, so the script comes
        # back as the history it is rather than being re-executed. ``replay`` is
        # the other door.
        world._script = [dict(entry) for entry in data.get("script", [])]
        return world

    @classmethod
    def replay(cls, data: dict, **kw) -> World:
        """Rebuild a run from its RECIPE -- scenario plus script -- and re-run it.

        The other half of ``script``. Where ``load`` restores a saved state and
        carries on, this starts from nothing and re-derives the whole trajectory
        from what was asked for, which is the check that the recipe is complete:
        anything a run depended on and the script does not record shows up here as
        a disagreement.

        ⚠ A DISCOVERED INSTANT IS RE-DISCOVERED, not read back. That is the point
        of storing the condition rather than the instant, and it is also the one
        place a replay can legitimately differ from the original -- by about the
        root solve's tolerance. See ``script``.

        ⚠ One consequence worth knowing rather than discovering: an event scheduled
        for an absolute time only a hair AFTER a discovered instant can land in the
        replay's past, and ``schedule`` refuses that rather than applying it late.
        The refusal is loud and the fix is to schedule relative to the wait's
        outcome; silently applying it late would be the thing that makes a replay
        disagree with its original for no visible reason.
        """
        version = int(data.get("version", 0))
        if version != SAVE_VERSION:
            raise ValueError(
                f"cannot replay a version {version} save: the script that records "
                f"what was asked of the world arrived in version {SAVE_VERSION}, "
                "and an older save does not contain one"
            )
        world = cls(scenario=Scenario.from_dict(data["scenario"]),
                    seed=int(data["seed"]))
        world.run_script(data.get("script", []), **kw)
        return world

    def run_script(self, entries, **kw) -> World:
        """Re-execute a script against this world, entry by entry.

        Extracted from ``replay`` so that a caller with a script and a world in
        hand -- a frontend opening a saved recipe, say -- does not have to
        reimplement the walk. A second copy of it is a second thing to keep in
        step with ``script``'s format, which is exactly the drift this project
        avoids elsewhere by keeping one home for a thing.
        """
        for entry in entries:
            do = entry.get("do")
            if do == "schedule":
                ev = Event.from_dict(entry["event"])
                self.schedule(ev.t, ev.kind, ev.vessel, **ev.payload)
            elif do == "step":
                self.step(float(entry["dt"]), **kw)
            elif do == "wait_until":
                self.wait_until(
                    entry["vessel"],
                    [Condition.from_dict(c) for c in entry["conditions"]],
                    float(entry["timeout"]),
                    **kw,
                )
            elif do == "collect_fraction":
                # ⚠ Re-DERIVED from the band, not replayed from a timestamp: the
                # cut points are roots and this run has to find its own.
                self.collect_fraction(
                    entry["vessel"], int(entry["edge"]), entry["into"],
                    float(entry["enter"]), float(entry["leave"]),
                    float(entry["timeout"]), entry.get("park"), **kw,
                )
            else:
                raise ValueError(f"unknown script entry {do!r}")
        return self


# ---------------------------------------------------------------------------
# vessel <-> dict. By field NAME, never by array position, so that a future
# phase can be added without silently shifting every other field.
# ---------------------------------------------------------------------------


def _dump_vessel(v: Vessel) -> dict:
    st = v.state()
    return {
        "t": st.t,
        "T": st.T,
        "n_liquid": {k: val for k, val in st.n_liquid.items() if val != 0.0},
        "n_gas": {k: val for k, val in st.n_gas.items() if val != 0.0},
        "n_solid": {k: val for k, val in st.n_solid.items() if val != 0.0},
        "n_liquid2": {k: val for k, val in st.n_liquid2.items() if val != 0.0},
        "Q_input": v.Q_input,
        "T_env": v.T_env,
        "k_vent": v.k_vent,
        "kla": v.kla,
        "k_lle": v.k_lle,
    }


def _restore_vessel(v: Vessel, d: dict) -> None:
    v.reset()
    v.charge(d.get("n_liquid", {}), phase="liquid")
    v.charge(d.get("n_gas", {}), phase="gas")
    v.charge(d.get("n_solid", {}), phase="solid")
    # Restored into its own block rather than merged and re-split: a save has
    # to reproduce the state exactly, and re-deriving the layers would make
    # loading depend on the stability test agreeing with itself across builds.
    v.charge(d.get("n_liquid2", {}), phase="liquid2")
    v.T = float(d["T"])
    v.t = float(d.get("t", 0.0))
    v.set_heat(float(d.get("Q_input", v.Q_input)))
    v.set_environment(float(d.get("T_env", v.T_env)))
    v.set_vent(float(d.get("k_vent", v.k_vent)))
    v.set_stirring(float(d.get("kla", v.kla)))
    v.set_shaking(float(d.get("k_lle", v.k_lle)))


def _encode_rng(rng: random.Random) -> list:
    version, internal, gauss = rng.getstate()
    return [version, list(internal), gauss]


def _decode_rng(rng: random.Random, state) -> None:
    if not state:
        return
    version, internal, gauss = state
    rng.setstate((version, tuple(internal), gauss))


def as_float_dict(d: dict[str, float]) -> dict[str, float]:
    """numpy scalars are not JSON-serializable; state() already returns floats,
    but this makes the guarantee explicit at the boundary."""
    return {k: float(np.asarray(v)) for k, v in d.items()}
