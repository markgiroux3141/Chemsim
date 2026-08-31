"""Layer 7 -- the frontend's engine-facing half, with no widgets in it.

A user interface for this engine is an EVENT PRODUCER and a state renderer, and
Layer 6 already guarantees that a run is a pure function of (scenario, script).
So the only genuinely hard part of putting a face on it is not the chemistry and
not the layout: it is that **an operation cannot be a blocking call**.

⚠ **COST IS CONCENTRATED IN STIFF TRANSIENTS, NOT IN ELAPSED SIMULATED TIME**, and
that is the single constraint that shapes everything here. Measured in
``validation/wall_clock.py``: an idle flask does an hour in 0.00 s and never calls
the solver at all, a boiling plateau does 1200 s in 0.73 s, and **ten seconds of the
acid quench costs 40 s of wall time -- 4.1x slower than real time, and eight times
what four hours of crystal growth costs.** So the expensive moments are exactly the
ones a player is watching, and a frontend that calls ``world.step`` on its own
thread freezes precisely when the chemistry gets interesting.

Hence the shape of this module, and each part of it is a decision:

**One worker thread owns the ``World``, and nothing else ever touches it.** Not the
view, not a callback, not a "just read the temperature". Every command -- including
the instantaneous ones like charging a reagent -- goes through the same queue and
is executed in submission order by that thread. There is therefore no lock around
the engine at all and no possibility of reading a half-applied event: the only
shared object is a ``Snapshot``, which is immutable, and publishing one is a single
attribute assignment.

**Long operations are CHUNKED, and the chunking is part of the recipe rather than a
rendering trick.** A one-hour step is run as a sequence of shorter steps with a
snapshot published after each, which is what lets a thermometer climb rather than
teleport. ⚠ That is not free and it is not hidden: freezing the layer permittivity
at integration boundaries made the caller's ``dt`` weakly load-bearing, which is
exactly why ``World.script`` records stepped intervals as well as waits. Chunking
therefore changes the answer slightly AND records itself, so a replay of what the
player did reproduces what the player saw. A chunk size is offered as a visible
setting for that reason -- it is a knob on the recipe, not on the graphics.

**⚠ AND CHUNKING BOUNDS THE UPDATE INTERVAL IN SIMULATED TIME, WHICH IS NOT THE
SAME AS BOUNDING IT IN WALL TIME.** Thirty simulated seconds of crystal growth is
instant and thirty of the acid quench is two minutes. Nothing here can promise
otherwise, so this module does not pretend to: it reports the wall time the current
chunk has been running and the measured cost ratio, and ``stop()`` takes effect at
the next chunk boundary rather than immediately. A scipy solve cannot be
interrupted from outside, and claiming a cancel that does not cancel would be
worse than an honest one that arrives late.

**A refusal is content, not an error dialog.** Every guard in this project is
written to name a cause and a fix -- an overfilled vessel, a species with no
Born radius, a solve that failed with a diagnosis attached. Those strings are the
most useful thing the engine produces when something goes wrong, so they are
carried on the snapshot and rendered, never reduced to "operation failed".
"""

from __future__ import annotations

import math
import queue
import threading
import time
import traceback
from dataclasses import dataclass, field, replace

from chemsim.engine.events import ALL_KINDS
from chemsim.engine.scenario import Scenario
from chemsim.engine.stock import Stock, state_to_dict
from chemsim.engine.world import World
from chemsim.vessel import Condition, Vessel

# Simulated seconds per chunk, and the default is a compromise with no right
# answer -- see the module docstring. Small enough that an ordinary heat-up
# redraws often, large enough that a four-hour crystallisation is not ten
# thousand solver calls.
DEFAULT_CHUNK = 30.0

# How long the worker blocks waiting for a command before looking at its stop
# flag again. Only affects how quickly the thread notices a shutdown.
IDLE_POLL = 0.1


# ---------------------------------------------------------------------------
# what the view renders
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VesselView:
    """One vessel, flattened to plain data.

    Everything a renderer could want, taken in one pass on the worker thread. It
    is a snapshot rather than a live handle on purpose: a view holding a ``Vessel``
    would be reading a mutable object from the wrong thread, and the numbers on
    screen would not all belong to the same instant.
    """

    name: str
    t: float
    T: float
    pressure: float
    is_boiling: bool
    volume: float
    liquid_volume: float
    solid_volume: float
    gas_volume: float
    pH: float | None
    liquid: dict[str, float]
    liquid2: dict[str, float]
    gas: dict[str, float]
    solid: dict[str, float]
    # The engine's own commentary. Empty strings mean "nothing to say", which is
    # the common case and is why they are joined rather than listed.
    reports: tuple[str, ...] = ()

    @property
    def has_second_layer(self) -> bool:
        return any(v > 0.0 for v in self.liquid2.values())


@dataclass(frozen=True)
class Snapshot:
    """The whole session at one instant. Immutable, so publishing is one assignment."""

    t: float = 0.0
    vessels: tuple[VesselView, ...] = ()
    busy: bool = False
    activity: str = ""
    # Fraction of the current operation completed, in SIMULATED time. -1 when the
    # operation has no knowable extent -- a wait whose condition may fire at any
    # moment is exactly that, and a progress bar that lies is worse than none.
    progress: float = -1.0
    wall: float = 0.0            # seconds of wall clock spent on this operation
    sim: float = 0.0             # simulated seconds covered by it so far
    stopping: bool = False
    log: tuple[str, ...] = ()
    # The recipe so far. Carried here rather than read off ``World`` because the
    # view must never touch the engine -- and because a script read while the
    # worker is appending to it is a list changing underneath the reader.
    script: tuple[dict, ...] = ()
    # The network's species, so a view can offer a picker without reaching into
    # the ``World`` from the wrong thread. Discovered species appear here as the
    # network finds them, which is the point -- a player charges acetic acid and
    # ethanol and ethyl acetate turns up in the list without being asked for.
    species: tuple[str, ...] = ()
    vessel_names: tuple[str, ...] = ()
    # ⚠ WHAT ``build_network`` SAID WHILE DISCOVERING THIS NETWORK. It used to
    # say it to stdout and nowhere else, which for a script is a channel and for
    # a player is a bin: a mix-anything game generates hundreds of these -- 397
    # for five reagents at two generations, measured -- and nobody is watching a
    # console. They are the SAME strings the builder prints, carried rather than
    # replaced, and they include the generation-limit notice, which is the one
    # coverage limit that says something about the CONTENTS of the flask rather
    # than about what was registered.
    #
    # ⚠ NETWORK-WIDE AND NOT PER-VESSEL, which is why they are here and not on
    # ``VesselView``. One world has one network; every flask in a rig shares it,
    # and attaching a network's commentary to a vessel would say it once per
    # vessel and imply it was about that vessel.
    notices: tuple[str, ...] = ()
    # The species the network discovered and never expanded, because a bound --
    # ``generations`` or ``max_species`` -- stopped it. Non-empty means this
    # flask has more to give and the engine has not looked: the state a "react
    # further" control exists to offer, and the reason the notice above is not
    # merely informative.
    #
    # ⚠ ALWAYS EMPTY TODAY, AND THAT IS HONEST RATHER THAN BROKEN.
    # ``World.__post_init__`` passes no ``generations`` to ``build_network``, so
    # a session always builds to a fixpoint and there is nothing left on the
    # frontier. Making it reachable is a ``Scenario`` field and a SAVE_VERSION
    # bump -- P2's, because P2 opens that file anyway.
    unexpanded: tuple[str, ...] = ()
    # ⚠ THE BOTTLES THIS RUN HAS PRODUCED, and they are safe to publish for the
    # same reason everything else here is: a ``Stock`` is frozen and copies its
    # mole dicts on construction, so nothing on this tuple aliases a live vessel.
    # It is the RUN'S OUTPUT and not the player's inventory -- see
    # ``engine.stock``, which is where that distinction is argued out.
    shelf: tuple[Stock, ...] = ()
    # The last refusal, verbatim. Engine refusals name a cause and a fix and are
    # the most useful thing here when something goes wrong.
    error: str = ""
    outcome: str = ""            # what the last completed operation reported

    @property
    def cost_ratio(self) -> float:
        """Wall seconds per simulated second, for the operation in progress.

        The number that makes this project's sharpest performance finding visible
        in the product rather than only in a harness: it is ~0.0006 on a boiling
        plateau and ~4 on the acid quench.
        """
        return self.wall / self.sim if self.sim > 0.0 else 0.0

    def vessel(self, name: str) -> VesselView | None:
        for v in self.vessels:
            if v.name == name:
                return v
        return None


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Command:
    """Base: a thing asked of the world. Executed in submission order."""

    def label(self) -> str:
        return type(self).__name__


@dataclass(frozen=True)
class Do(Command):
    """An instantaneous event -- charge, set the heat, transfer, filter.

    Goes through the same queue as the driving calls even though it takes no
    simulated time, because ordering is the whole point: "charge the acid, then
    step" and "step, then charge the acid" are different experiments.
    """

    kind: str
    vessel: str = ""
    payload: dict = field(default_factory=dict)

    def label(self) -> str:
        return f"{self.kind} {self.vessel}".strip()


@dataclass(frozen=True)
class Step(Command):
    """Advance every vessel by ``seconds``, in chunks."""

    seconds: float
    chunk: float = DEFAULT_CHUNK

    def label(self) -> str:
        return f"step {self.seconds:g} s"


@dataclass(frozen=True)
class WaitUntil(Command):
    """Advance until a condition holds, or the timeout is spent.

    ⚠ The timeout is REQUIRED by ``World.wait_until`` and is not given a default
    here either. A condition that never comes true is an ordinary thing to ask for
    by mistake, and an unbounded wait in a user interface is a hang with a spinner
    on it.
    """

    vessel: str
    conditions: tuple[Condition, ...]
    timeout: float
    chunk: float = DEFAULT_CHUNK

    def label(self) -> str:
        return "wait until " + " or ".join(c.describe() for c in self.conditions)


@dataclass(frozen=True)
class Reset(Command):
    """Rebuild the world from its scenario. The recipe survives; the run does not.

    ⚠ AND NEITHER DOES THE SHELF, which follows from what the shelf is: bottles
    are a run's OUTPUT (``engine.stock``), so a world rebuilt from its scenario
    has produced none yet. A player's persistent inventory is not this object and
    is not reset by this command.
    """

    def label(self) -> str:
        return "reset"


@dataclass(frozen=True)
class Load(Command):
    """Replace the world. ``script`` replays a recipe against the new scenario."""

    scenario: Scenario
    script: tuple[dict, ...] = ()
    name: str = ""

    def label(self) -> str:
        return f"load {self.name}" if self.name else "load"


# ---------------------------------------------------------------------------
# the session
# ---------------------------------------------------------------------------


class Session:
    """A ``World`` driven from a worker thread, with an immutable view of it.

    Use it headless -- ``submit`` then ``wait_idle`` -- or behind a widget layer
    that polls ``snapshot()``. Both are the same object, which is deliberate: the
    interesting behaviour here is the threading and the chunking, and neither is
    testable through a GUI toolkit.
    """

    def __init__(self, scenario: Scenario, *, seed: int = 0,
                 chunk: float = DEFAULT_CHUNK) -> None:
        self.chunk = float(chunk)
        self._commands: queue.Queue[Command | None] = queue.Queue()
        self._snapshot = Snapshot()
        self._stop = threading.Event()          # cancel the operation in progress
        self._shutdown = threading.Event()
        self._idle = threading.Event()
        self._idle.set()
        # ⚠ Guards the two-step transitions on ``_idle`` ONLY, and it is not a lock
        # on the engine -- there is none of those, because only the worker ever
        # touches the ``World``. Without it, "clear then put" in ``submit`` can
        # interleave with "queue is empty, so set" in the worker, and ``wait_idle``
        # returns true with a command still queued.
        self._gate = threading.Lock()
        self._log: list[str] = []
        self.world = World(scenario)
        self._publish(activity="", busy=False)
        self._thread = threading.Thread(
            target=self._loop, name="chemsim-engine", daemon=True
        )
        self._thread.start()

    # -- the view's half -----------------------------------------------------

    def snapshot(self) -> Snapshot:
        """The latest published state. Safe from any thread; never blocks."""
        return self._snapshot

    def submit(self, command: Command) -> None:
        """Queue a command. Returns at once -- nothing here ever runs inline."""
        with self._gate:
            self._idle.clear()
            self._commands.put(command)

    def stop(self) -> None:
        """Ask the operation in progress to end at the next CHUNK BOUNDARY.

        ⚠ Not immediately, and the difference is honest rather than lazy: a scipy
        solve cannot be interrupted from outside, so the earliest truthful moment
        is when the current chunk returns. A stiff transient can make that several
        seconds of wall time, which is why the snapshot carries ``stopping`` and
        the view says "stopping" rather than pretending it already has.
        """
        self._stop.set()
        # ⚠ NOT ``_publish``, which reads the ``World`` -- and this runs on the
        # caller's thread while the worker is mid-integration. A ``replace`` on the
        # immutable snapshot touches nothing but the flag. If the worker publishes
        # at the same instant the flag can be lost for one chunk, which is a
        # display detail; reading a half-stepped vessel would not be.
        self._snapshot = replace(self._snapshot, stopping=True)

    def wait_idle(self, timeout: float | None = None) -> bool:
        """Block until the queue is empty. For tests and scripts, not for a view."""
        return self._idle.wait(timeout)

    def close(self) -> None:
        self._shutdown.set()
        self._stop.set()
        self._commands.put(None)
        self._thread.join(timeout=5.0)

    def __enter__(self) -> Session:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- convenience, so a view does not build dataclasses inline ------------

    def do(self, kind: str, vessel: str = "", **payload) -> None:
        if kind not in ALL_KINDS:
            raise ValueError(f"unknown event kind {kind!r}; have {sorted(ALL_KINDS)}")
        self.submit(Do(kind, vessel, dict(payload)))

    def step(self, seconds: float, chunk: float | None = None) -> None:
        self.submit(Step(float(seconds), float(chunk or self.chunk)))

    def wait_until(self, vessel: str, conditions, timeout: float,
                   chunk: float | None = None) -> None:
        want = (conditions,) if isinstance(conditions, Condition) else tuple(conditions)
        self.submit(WaitUntil(vessel, want, float(timeout), float(chunk or self.chunk)))

    def bottle(self, vessel: str, name: str = "", fraction: float = 1.0,
               phase: str = "all", note: str = "") -> None:
        """Name what is in a flask and put it on the shelf.

        An ordinary ``Do``, because BOTTLE is an ordinary event: the instant a
        player bottles something is declared, not discovered. The ``Stock`` it
        produces appears on the next ``Snapshot``'s ``shelf`` -- the view never
        gets a return value from anything here, and must not.
        """
        self.do("bottle", vessel, name=name, fraction=fraction, phase=phase,
                note=note)

    def charge_stock(self, vessel: str, stock: Stock,
                     fraction: float = 1.0) -> None:
        """Pour a stored stock into a flask, carrying its temperature.

        ⚠ The composition is INLINED into the event here, not looked up by name
        when it runs. Two bottles labelled the same behave differently, so a
        recipe that recorded the label would mean something else on replay --
        see ``events.CHARGE_STOCK``.
        """
        self.do("charge_stock", vessel, label=stock.name,
                state=state_to_dict(stock.state), fraction=float(fraction))

    # -- the worker's half ---------------------------------------------------

    def _loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                command = self._commands.get(timeout=IDLE_POLL)
            except queue.Empty:
                with self._gate:
                    if self._commands.empty():
                        self._idle.set()
                continue
            if command is None:
                break
            self._stop.clear()
            try:
                self._execute(command)
            except Exception as exc:                            # noqa: BLE001
                # ⚠ THE MESSAGE IS THE PRODUCT. Every refusal in this engine is
                # written to name a cause and a fix, and several of them are
                # several lines long. Reducing that to "failed" would throw away
                # the most useful thing the engine has to say.
                self._note(f"REFUSED: {command.label()}")
                self._publish(
                    busy=False, activity="", stopping=False,
                    error=f"{command.label()}\n\n{exc}",
                    outcome=f"refused: {type(exc).__name__}",
                )
                if not isinstance(exc, (ValueError, KeyError, RuntimeError)):
                    self._note(traceback.format_exc(limit=3).strip().splitlines()[-1])
            finally:
                self._commands.task_done()
                with self._gate:
                    if self._commands.empty():
                        self._idle.set()

    def _execute(self, command: Command) -> None:
        if isinstance(command, Do):
            self._publish(busy=True, activity=command.label(), error="")
            self.world.now(command.kind, command.vessel, **command.payload)
            # ⚠ ``now`` schedules for the current instant and events fire between
            # integrations, so without this a charged reagent would not appear in
            # the flask until something was stepped -- which reads as a lost
            # click. ``flush`` is trajectory-neutral: see ``World.flush``.
            self.world.flush()
            self._note(f"t={self.world.t:.1f} {command.label()}")
            self._publish(busy=False, activity="", outcome=command.label())
        elif isinstance(command, Step):
            self._run_step(command)
        elif isinstance(command, WaitUntil):
            self._run_wait(command)
        elif isinstance(command, Reset):
            self.world = World(self.world.scenario)
            self._log.clear()
            self._note("reset to the scenario")
            self._publish(busy=False, activity="", error="", outcome="reset")
        elif isinstance(command, Load):
            self._load(command)
        else:
            raise TypeError(f"unknown command {command!r}")

    def _load(self, command: Load) -> None:
        self._publish(busy=True, activity=command.label(), error="")
        world = World(command.scenario)
        # ⚠ Replayed by re-executing the SCRIPT, not by restoring a state vector.
        # That is what makes a saved run a recipe rather than a transcript: the
        # instants a ``wait_until`` resolved to are re-discovered against whatever
        # was actually charged. See ``World.script``.
        world.run_script(command.script)
        # ⚠ Belt and braces: ``run_script`` flushes at the end itself, since P2
        # found that a replay left a trailing event pending and did not reproduce
        # its own run. Kept here because it is the line that says why a freshly
        # loaded world already shows its opening charge in the flask.
        world.flush()
        self.world = world
        self._log.clear()
        self._note(f"loaded {command.name or 'a scenario'}")
        self._publish(busy=False, activity="", outcome=command.label())

    def _run_step(self, command: Step) -> None:
        """A long step as a sequence of short ones, publishing between them.

        ⚠ The remainder is folded into the LAST chunk rather than run as a stub.
        A 100 s step at a 30 s chunk is 30/30/30/10, not 30/30/30/9.999999 plus a
        nanosecond -- and a nanosecond step is not harmless here, because every
        chunk boundary re-takes the phase-stability decision and re-freezes the
        layer permittivity.
        """
        left, done = float(command.seconds), 0.0
        started = time.perf_counter()
        chunk = max(float(command.chunk), 1.0e-9)
        while left > 1.0e-9:
            take = chunk if left > chunk * 1.5 else left
            self._publish(
                busy=True, activity=command.label(), error="",
                progress=done / command.seconds if command.seconds > 0 else -1.0,
                wall=time.perf_counter() - started, sim=done,
            )
            self.world.step(take)
            done += take
            left -= take
            if self._stop.is_set():
                self._note(
                    f"t={self.world.t:.1f} stopped after {done:g} s of "
                    f"{command.seconds:g}"
                )
                break
        self._publish(
            busy=False, activity="", stopping=False, progress=-1.0,
            wall=time.perf_counter() - started, sim=done,
            outcome=f"stepped {done:g} s",
        )

    def _run_wait(self, command: WaitUntil) -> None:
        """A wait as a sequence of bounded waits, publishing between them.

        ⚠ EACH CHUNK IS A REAL ``wait_until`` WITH A SHORT TIMEOUT, not a step
        followed by a poll, and that distinction is the whole value of the verb:
        the instant is located by a scipy ROOT inside whichever chunk contains it,
        so the answer is the crossing rather than the end of the chunk that
        straddled it. Chopping a wait therefore costs resolution nowhere.

        It does put one script entry per chunk into the recipe, which is correct
        rather than untidy -- those legs are what happened, they replay to the same
        trajectory, and pretending a chopped wait was a single one would be storing
        something that was never run.
        """
        spent = 0.0
        started = time.perf_counter()
        chunk = max(float(command.chunk), 1.0e-9)
        fired = None
        while spent < command.timeout:
            self._publish(
                busy=True, activity=command.label(), error="",
                progress=-1.0, wall=time.perf_counter() - started, sim=spent,
            )
            horizon = min(chunk, command.timeout - spent)
            outcome = self.world.wait_until(
                command.vessel, list(command.conditions), horizon
            )
            spent += outcome.elapsed
            if not outcome.timed_out:
                fired = outcome
                break
            if self._stop.is_set():
                break
        if fired is not None:
            what = fired.fired.describe() if fired.fired else "the condition"
            note = (
                f"{what} after {spent:.2f} s"
                + (" (already true)" if fired.already else "")
            )
        elif self._stop.is_set():
            note = f"stopped after {spent:.2f} s"
        else:
            note = (
                f"TIMED OUT after {spent:.2f} s with none of "
                + " or ".join(c.describe() for c in command.conditions)
            )
        self._note(f"t={self.world.t:.1f} {note}")
        self._publish(
            busy=False, activity="", stopping=False, progress=-1.0,
            wall=time.perf_counter() - started, sim=spent, outcome=note,
        )

    # -- publishing ----------------------------------------------------------

    def _note(self, line: str) -> None:
        self._log.append(line)
        del self._log[:-200]

    def _publish(self, **fields) -> None:
        base = replace(
            self._snapshot,
            t=self.world.t,
            vessels=tuple(
                self._view(name, v) for name, v in self.world.vessels.items()
            ),
            log=tuple(self._log),
            script=tuple(self.world.script),
            species=tuple(str(sp) for sp in self.world.network.species),
            vessel_names=tuple(self.world.vessels),
            notices=tuple(self.world.network.notices),
            unexpanded=tuple(self.world.network.unexpanded),
            shelf=tuple(self.world.shelf),
        )
        self._snapshot = replace(base, **fields)

    @staticmethod
    def _view(name: str, v: Vessel) -> VesselView:
        state = v.state()
        reports = tuple(
            r for r in (
                v.conservation_report(),
                v.integrability_report(),
                v.atmosphere_report,
                v.lle_report(),
                v.electrolyte_report(),
                v.holdup_report(),
                v.crust_report(),
            ) if r
        )
        # ⚠ pH IS ONLY A QUANTITY WHERE THE NETWORK PRICES IONS AT ALL, and a
        # network without them answers ``nan`` rather than raising. "There is no
        # pH here" and "the pH is 7" are different claims, and rendering a nan
        # would be the second one wearing the first one's clothes -- so it is
        # None, and the view omits the field entirely.
        # ⚠ INF AS WELL AS NAN. A flask charged with hydroxide and not yet stepped
        # has no protons at all, so pH is +inf -- a true statement about an
        # unrelaxed state and a useless thing to put on a gauge. Both go to None
        # and the view omits the field rather than rendering "pH inf".
        try:
            pH = float(v.pH)
            pH = None if not math.isfinite(pH) else pH
        except Exception:                                       # noqa: BLE001
            pH = None
        return VesselView(
            name=name,
            t=v.t,
            T=float(v.T),
            pressure=float(v.pressure),
            is_boiling=bool(v.is_boiling),
            volume=float(v.volume),
            liquid_volume=float(v.liquid_volume),
            solid_volume=float(v.solid_volume),
            gas_volume=float(v.gas_volume),
            pH=pH,
            liquid=_nonzero(state.n_liquid),
            liquid2=_nonzero(state.n_liquid2),
            gas=_nonzero(state.n_gas),
            solid=_nonzero(state.n_solid),
            reports=reports,
        )


def _nonzero(d: dict[str, float], floor: float = 1.0e-12) -> dict[str, float]:
    """Species actually present, biggest first.

    A discovered network can carry a hundred species of which four are in the
    flask, so listing all of them would bury the four. The floor is a display
    threshold and nothing else -- nothing is dropped from the engine.
    """
    return {
        k: float(val)
        for k, val in sorted(d.items(), key=lambda kv: -kv[1])
        if val > floor
    }
