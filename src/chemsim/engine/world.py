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
    BOTTLE,
    CHARGE,
    CHARGE_STOCK,
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
from chemsim.engine.stock import Shelf, Stock, state_from_dict, state_to_dict
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
# 6: +``add_dropwise`` -- a scripted verb, so a version-5 reader handed a
#    version-6 script would execute every entry BEFORE it and only then raise
#    "unknown script entry", leaving a half-run world that looks like a
#    completed one. A verb is a format change for the same reason ``edges``
#    was: the failure mode of not saying so is a different experiment wearing
#    the right name. See ``add_dropwise`` for why it could not be an Event.
# 7: +the SHELF and the GENERATION BOUND -- ``World.shelf``, the BOTTLE and
#    CHARGE_STOCK verbs, and ``Scenario.generations``. Two changes, one version,
#    because they are the same session's work and either one alone would earn a
#    bump. ⚠ A v6 reader handed a v7 save is the ``add_dropwise`` failure again,
#    worse: it would execute every script entry before the first ``bottle`` and
#    stop with a world that looks finished and a shelf that is not there. And a
#    v7 save read as a v6 one would lose ``generations`` and rebuild the network
#    to a FIXPOINT -- silently a different flask, with products in it that the
#    saved run never had. That is a different experiment wearing the right name,
#    which is what a version number is for.
# 8: +the THREE TEMPLATE FIELDS ``TemplateSpec`` had been dropping --
#    ``orders``, ``solid_catalyst`` and ``electrons``. Not a new verb and not a
#    new structure: the same bytes MEAN something different now, which is the
#    strongest reason to bump there is. A v7 save of a network holding
#    ``sulfur_combustion`` replayed the burner at ninth-order mass action
#    because the declared ``orders=(1, 1, 0...)`` never reached the network;
#    read as a v8 save it replays at the first-order law S11 measured, and 0.02
#    mol of sulfur under half a mole of oxygen goes from 0.07% burnt to 77.85%.
#    The same drop un-gated every heterogeneous catalyst and took the driving
#    force out of every electrode reaction. **A save written before the fix
#    cannot be replayed to the trajectory it recorded**, which is exactly the
#    condition version 4 was created for. P4 found it by playing the game.
# 9: -``Scenario.prune_threshold`` (R3). The only version here that REMOVES a
#    field, and the only one where every old save replays bit-identically --
#    the field reached nothing, so no trajectory ever depended on it. The bump
#    is for the CONTRACT rather than the bytes: a v8 producer could set the
#    field believing it pruned, and a reader that silently ignored it would be
#    preserving exactly the lie R3 existed to remove. Refusing the version is
#    what tells that producer the field is gone. (Why deleted rather than
#    wired: the pruning it promised needs the CHARGE, which a Scenario does
#    not contain -- see the note where the field used to be, scenario.py.)
SAVE_VERSION = 9

# Liquid holdup below which a dropping funnel counts as EMPTY, mol. The solver
# is asked for atol=1e-9 per component and a meter edge drains its donor to a
# clamped zero rather than through it (measured exact to 1e-12 at rates from
# 0.001 to 10 mol/s), so anything at this scale is round-off and not reagent.
# ⚠ A MOLAR FLOOR AND NOT A FRACTION OF THE CHARGE: "the funnel is empty" is a
# statement about the funnel, and scaling it by what was put in would make the
# same residue count as empty in a small run and as reagent in a large one.
_DRY_MOLES = 1.0e-9


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
    # ⚠ THE RUN'S OUTPUT, NOT THE PLAYER'S INVENTORY. Bottles land here and
    # nothing is ever consumed from it by an event, which is what keeps a run a
    # pure function of (scenario, script): an inventory that events could deplete
    # would put part of the run in neither. The player's persistent shelf -- the
    # three-tier one ``data/catalog/shelf.psv`` will hold -- lives above the
    # engine and draws itself down with ``Shelf.take``. See ``engine.stock``.
    shelf: Shelf = field(default_factory=Shelf, repr=False)

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
            # ⚠ P2. This argument was not passed at all, so a world always built
            # to a fixpoint and ``generations=1`` play -- the mechanic
            # ``GAME_DESIGN.md`` section 8.2 is written around -- was unreachable
            # from anything that goes through a ``Scenario``, which is everything
            # saveable. ``None`` is the default and is the fixpoint, so nothing
            # measured before this line moved.
            generations=self.scenario.generations,
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
        elif ev.kind == BOTTLE:
            state = v.withdraw(
                fraction=float(p.get("fraction", 1.0)),
                phase=str(p.get("phase", "all")),
            )
            stored = self.shelf.put(Stock(
                name=str(p.get("name", "") or f"{ev.vessel} at t={self.t:.0f} s"),
                state=state,
                script=tuple(self._provenance(ev.seq)),
                source=ev.vessel,
                note=str(p.get("note", "")),
            ))
            self._log.append(
                f"t={self.t:.1f} bottle {ev.vessel} -> {stored.name!r}: "
                f"{stored.total:.4f} mol at {stored.state.T:.1f} K"
                + (f" ({stored.major('mass')} at "
                   f"{100.0 * stored.purity('mass'):.1f} wt%)"
                   if stored.major('mass') else " (empty)")
            )

        elif ev.kind == CHARGE_STOCK:
            # ⚠ READ OFF THE PAYLOAD AND NEVER OFF THE SHELF -- see
            # ``events.CHARGE_STOCK``. Two bottles labelled the same behave
            # differently, so a recipe that recorded the label would mean
            # something else on replay.
            state = state_from_dict(p["state"])
            moved = v.charge_state(state, fraction=float(p.get("fraction", 1.0)))
            self._log.append(
                f"t={self.t:.1f} charge_stock {p.get('label', '?')!r} -> "
                f"{ev.vessel}: {moved:.4f} mol from a stock at "
                f"{state.T:.1f} K; the flask is now at {v.T:.1f} K"
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

    def _provenance(self, seq: int) -> list[dict]:
        """The script up to and including the entry that scheduled event ``seq``.

        What a bottled ``Stock`` records as "how did I make this", and it is a
        SLICE rather than the whole script for a reason that took a replay to
        show. ⚠⚠ **THE SCRIPT RUNS AHEAD OF THE EVENT QUEUE**: entries are
        appended when an action is SCHEDULED and events are applied at step
        boundaries, so a bottling flushed late sees a script containing
        everything asked afterwards as well. Measured -- the same run bottled and
        then replayed produced two stocks with identical compositions to every
        digit and different provenances, the replayed one carrying the
        ``charge_stock`` that came after it. A recipe that includes what happened
        to the bottle after it was filled is not the recipe for the bottle, and
        it would have made the field quietly depend on when the queue was
        flushed rather than on what was done.

        Falls back to the whole script when the event was never scheduled, which
        is the ``_swap``/``_set_edge`` path: those construct an ``Event`` and
        apply it directly, precisely because their instant was discovered.
        """
        for i, entry in enumerate(self._script):
            if (
                entry.get("do") == "schedule"
                and entry.get("event", {}).get("seq") == seq
            ):
                return [dict(e) for e in self._script[: i + 1]]
        return [dict(e) for e in self._script]

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

    # -- the DROPPING FUNNEL, which is a tap and a condition ----------------

    def add_dropwise(
        self,
        edge: int,
        rate: float,
        watch: str,
        until: Condition | list[Condition],
        timeout: float,
        close: bool = True,
        **kw,
    ) -> dict:
        """Open a metered tap, run until a condition holds, then shut it.

        **"Drip the acid in slowly, and stop when the pot reaches 320 K."** The
        plumbing this rides on is not new -- a ``meter`` edge has been a dropping
        funnel since Layer 5, it carries the donor's sensible heat, and it stops
        of its own accord when the funnel runs dry. What was missing is the same
        thing that was missing from a distillation before ``collect_fraction``:
        **a way to say it that survives being saved.**

        ⚠⚠ **THIS IS NOT SUGAR OVER ``wait_until`` FOLLOWED BY
        ``now(SET_EDGE)``, AND THE DIFFERENCE IS MEASURED.** An ``Event`` carries
        an absolute ``t``, so scheduling the tap-close after a discovered instant
        bakes THIS run's crossing into the recipe. Measured on a nitration with a
        1.0 mol charge, the pot reached 340 K at t=20.351135 s and the recipe
        recorded ``set_edge`` at that timestamp; replayed against a **2.0 mol**
        charge the same pot reached 340 K at t=31.515137, and ``schedule``
        refused the recorded event as being in the past:

            ValueError: cannot schedule 'set_edge' at t=20.35113461689465 --
            the world is already at t=31.515137100210648

        A loud refusal is the good case. The bad case is a crossing that lands a
        hair EARLIER on the replay, where the event is still in the future and
        the tap shuts at an instant this run never found. Either way the artifact
        has stopped being a recipe and become a transcript -- exactly the fork
        argued out in full on ``script``, and settled there the same way.

        So this stores the CONDITION and never the instant, and both taps are
        turned through ``_set_edge`` rather than through the queue.

        Parameters
        ----------
        edge
            index of the ``meter`` edge to open. ⚠ It must BE a meter edge: a
            drain's ``k`` is a reciprocal residence time and a vapour edge's is
            mol/(bar s), so opening one of those "at 0.01 mol/s" would be a
            number in the wrong units wearing the right name.
        rate
            mol/s to open the tap to, while the addition runs.
        watch
            which vessel the conditions are read on. Usually the POT (drip until
            it is hot enough) but a funnel is just as legitimate a thing to watch
            -- ``consumed(ACID, 1e-6)`` on the funnel is "add all of it", and it
            is a condition rather than a duration for the same reason everything
            else here is.
        until, timeout
            as ``wait_until``. The timeout is required, and it is what "drip for
            600 s" is: pass a condition that cannot fire and read ``timed_out``.
        close
            shut the tap at the end. ``False`` leaves it running, which is how a
            two-stage addition is written -- drip until warm, then keep dripping
            at a lower rate.

        Returns what happened, as data. ⚠⚠ **``ran_dry`` IS READ OFF WHAT IS
        LEFT IN THE FUNNEL, NOT OFF A SHORTFALL IN THE DELIVERY**, and the first
        draft got that wrong in a way worth recording. The obvious test is
        ``delivered < rate * elapsed``, and it does not survive contact with a
        real funnel. Measured on a nitration funnel with a LIVE HEADSPACE
        (``kla = 1.0``): ``rate * elapsed`` was 0.40702 mol and the donor's
        liquid inventory fell by **0.40799** -- MORE, not less, because the
        funnel was also evaporating into its own headspace. Two numbers that
        each have their own error term cannot be subtracted to decide a third
        thing. ⚠ A SEALED funnel does agree to the integrator's tolerance, which
        is exactly why the bad test would have passed every check written for it. ``donor_left`` is a direct measurement of the
        question actually being asked, so that is what the flag reads.

        ⚠ ``delivered`` is still reported, and it is the donor's own liquid
        inventory falling -- which is the tap PLUS anything else that took
        liquid out of that vessel. It is a diagnostic, not the tap's throughput.
        A funnel emptying early is an ordinary bench event either way, and the
        honest answer is to say so rather than to report the rate that was asked
        for.
        """
        want = [until] if isinstance(until, Condition) else list(until)
        if not want:
            raise ValueError("add_dropwise needs at least one condition")
        if rate <= 0.0:
            raise ValueError(
                f"a dropwise addition needs a positive rate, got {rate}. A tap "
                "opened to zero delivers nothing and would sit here until the "
                "timeout; if that is what you mean, say it with SET_EDGE"
            )
        if timeout <= 0.0:
            raise ValueError(f"timeout must be positive, got {timeout}")
        if watch not in self.vessels:
            raise KeyError(f"no vessel {watch!r}; have {sorted(self.vessels)}")
        c = self._edge(int(edge))
        # ⚠ By NAME, not by ``rig_integrator``'s integer. Layer 6 already
        # spells edges as the strings ``EDGE_KINDS`` holds, and reaching
        # into Layer 4 for a constant to compare against would be the one
        # place this file knew an edge kind was an int.
        if c.kind_name != "meter":
            raise ValueError(
                f"edge {edge} is a {c.kind_name} edge ({c.describe()}), and a "
                f"dropwise addition needs a METER edge. Their conductances are "
                f"not the same quantity -- a meter's k is mol/s, a drain's is a "
                f"reciprocal residence time and a vapour edge's is mol/(bar s) "
                f"-- so opening this one at {rate:g} mol/s would be a number in "
                f"the wrong units. Declare EdgeSpec(kind='meter', ...)"
            )

        self._script.append({
            "do": "add_dropwise",
            "edge": int(edge), "rate": float(rate), "watch": watch,
            "until": [w.to_dict() for w in want],
            "timeout": float(timeout), "close": bool(close),
        })
        return self._add_dropwise(edge, rate, watch, want, timeout, close, **kw)

    def _add_dropwise(
        self, edge, rate, watch, want, timeout, close, **kw
    ) -> dict:
        """``add_dropwise`` without the script entry -- what replay re-executes."""
        c = self._edge(int(edge))
        donor = self.vessels[c.a]
        before = _liquid_moles(donor)

        was = c.k
        self._set_edge(edge, rate)
        out = self._wait_until(watch, want, timeout, **kw)
        if close:
            self._set_edge(edge, 0.0)

        left = _liquid_moles(donor)
        delivered = before - left
        nominal = rate * out.elapsed
        self._log.append(
            f"t={self.t:.1f} add_dropwise edge {edge} ({c.a}->{c.b}) at "
            f"{rate:g} mol/s for {out.elapsed:.1f} s: {delivered:.4f} mol "
            f"delivered; {out.describe()}"
        )
        return {
            "edge": int(edge), "rate": float(rate), "from": c.a, "to": c.b,
            "was": float(was), "elapsed": out.elapsed,
            "fired": out.fired, "timed_out": out.timed_out,
            "delivered": delivered, "nominal": nominal,
            "donor_left": left,
            # ⚠ MEASURED, not inferred from a shortfall -- see the docstring.
            "ran_dry": left <= _DRY_MOLES,
            "state": out.state,
        }

    def _set_edge(self, edge: int, k: float) -> None:
        """Open or shut a tap NOW, without going through the queue.

        The twin of ``_swap`` and it exists for the same reason: the instant a
        dropwise addition ends was DISCOVERED by a root solve, and an ``Event``
        carries an absolute ``t``. See ``add_dropwise``.
        """
        self._apply(Event(t=self.t, seq=self._seq, kind=SET_EDGE,
                          payload={"edge": int(edge), "k": float(k)}))
        self._seq += 1

    # -- the SHELF: two events, one of which reads its amounts off a state ---

    def bottle(
        self,
        vessel: str,
        name: str = "",
        fraction: float = 1.0,
        phase: str = "all",
        note: str = "",
    ) -> Stock:
        """Take what is in a flask, name it, and put it on the shelf.

        **One of the two verbs that close the loop** (``GAME_DESIGN.md`` section
        8.1), and the one that did not exist in any form. A convenience over
        ``now(BOTTLE, ...)`` plus ``flush``, because a caller wants the ``Stock``
        back -- to show it, to write it to the player's shelf, or to charge it
        somewhere else -- and an event returns nothing but itself.

        ⚠ ``flush`` is trajectory-neutral (see ``flush``), so bottling here and
        bottling on the next step are the same experiment. The event is in the
        script either way, at the instant it was scheduled for.

        ⚠ It LOSES a film and a crust, through ``Vessel.withdraw``, for the same
        reason a pour does: bottling wets the glass. Without that, bottle-and-
        recharge would have been the cheapest way around holdup in the game.
        """
        self.now(BOTTLE, vessel, name=name, fraction=fraction, phase=phase,
                 note=note)
        before = set(self.shelf.stocks)
        self.flush()
        made = [n for n in self.shelf.stocks if n not in before]
        # One BOTTLE event produces exactly one entry, and ``Shelf.put`` never
        # merges, so this is a lookup rather than a search. It is written as one
        # anyway because ``flush`` may have applied other events that were due.
        return self.shelf.stocks[made[-1]]

    def charge_stock(
        self, vessel: str, stock: Stock, fraction: float = 1.0
    ) -> Event:
        """Pour a stored stock into a flask, carrying its temperature.

        The other verb, and it is CHARGE with its amounts read off a stored
        ``VesselState`` rather than typed -- plus the heat, which plain CHARGE
        does not carry because "add 2 mol of acetic acid" says nothing about
        temperature and a bottle off a hot plate does.

        ⚠ A ``Stock``, never a shelf NAME. ``World.shelf`` is this run's output
        and events never consume from it; a player's inventory is drawn down
        above the engine with ``Shelf.take``, and the composition that arrives
        here is inlined into the event so that the recipe means the same thing
        when it is replayed. See ``engine.stock`` and ``events.CHARGE_STOCK``.
        """
        return self.now(
            CHARGE_STOCK, vessel,
            label=stock.name, state=state_to_dict(stock.state),
            fraction=float(fraction),
        )

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
            "shelf": self.shelf.to_dict(),
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
        # The shelf comes back the same way and for the same reason. ⚠ Under
        # ``replay`` it is not restored at all -- it is REBUILT, because the
        # bottle events are in the script and re-running them fills it. That the
        # two doors agree is a test rather than an assumption; see
        # ``tests/test_stock.py``.
        world.shelf = Shelf.from_dict(data.get("shelf"))
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

        ⚠⚠ **IT FLUSHES AT THE END, AND WITHOUT THAT A REPLAY DID NOT REPRODUCE
        ITS RUN.** Found in P2 and PRE-EXISTING: ``now`` schedules for the
        current instant and events fire between integrations, so an action taken
        after the last step -- which the original run applied with ``flush`` --
        was left sitting in the replayed world's queue. Measured on a two-event
        script, ``set_heat`` 50 W applied and then replayed: the original had
        ``Q_input = 50.0`` and the replay had ``0.0`` with one pending event. It
        was invisible for as long as it was because a trailing event is the only
        one it can bite: anything with a ``step`` after it gets applied by that
        step. ⚠ BOTTLE is exactly a trailing event -- "bottle it and stop" is how
        every session ends -- so P2 would have shipped a replay with an empty
        shelf.

        ⚠ The flush is trajectory-neutral and adds nothing to the script (see
        ``flush``), so this cannot change what a replay MEANS; it only stops it
        from ending early. Events scheduled for a future instant stay queued,
        because they are not due.
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
            elif do == "add_dropwise":
                # ⚠ Re-DERIVED from the condition, not replayed from a
                # timestamp: the instant the tap shuts is a root and this run
                # has to find its own. See ``add_dropwise``.
                self.add_dropwise(
                    int(entry["edge"]), float(entry["rate"]), entry["watch"],
                    [Condition.from_dict(c) for c in entry["until"]],
                    float(entry["timeout"]), bool(entry.get("close", True)),
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
        self.flush()
        return self


# ---------------------------------------------------------------------------
# vessel <-> dict. By field NAME, never by array position, so that a future
# phase can be added without silently shifting every other field.
# ---------------------------------------------------------------------------


def _liquid_moles(v: Vessel) -> float:
    """Total moles in BOTH liquid layers -- what a funnel has left to give.

    Both layers, because a ``meter`` edge moves both in the proportion the donor
    holds them (see ``rig_integrator``), so a figure taken from layer 1 alone
    would under-report a funnel holding two.
    """
    st = v.state()
    return float(sum(st.n_liquid.values()) + sum(st.n_liquid2.values()))


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
