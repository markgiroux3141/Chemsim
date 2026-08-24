"""Layer 7 -- the Tkinter view. Polls a ``Session``; knows no chemistry.

Tkinter because it is in the standard library. This project installs numpy, scipy
and RDKit and nothing else it did not have to, and a browser stack for a desktop
laboratory would be a server, a build step and a websocket to say what
``root.after`` already says.

⚠ **THE VIEW NEVER CALLS THE ENGINE.** Not once, not for a temperature, not for a
species list. It submits commands and it reads ``Session.snapshot()``, which is an
immutable object published by the worker thread. That is the whole reason the
window keeps repainting through the acid quench, which is 4x slower than real time
and is exactly the moment a player is staring at it.

Three things on screen exist because of measurements rather than taste:

* **the cost meter** -- wall seconds per simulated second, live. This project's
  sharpest performance finding is that cost has nothing to do with elapsed
  simulated time, and a player who cannot see that will read a slow moment as a
  hung program;
* **the reports panel** -- ``conservation_report``, ``integrability_report``,
  ``lle_report``, ``electrolyte_report`` and the rest. The engine's rule is that
  nothing is silently approximated, which is only worth anything if somebody is
  shown what it said. The refluxing rig destroyed 0.34 mol of its air for months
  on a channel that was reported all along and that nothing read;
* **the recipe panel** -- the script, growing as the player works. A run is a pure
  function of (scenario, script), so this is the artifact, and it is visible
  rather than hidden behind a Save button.
"""

from __future__ import annotations

import json
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from chemsim.ui.examples import Example, load, titles
from chemsim.ui.session import DEFAULT_CHUNK, Load, Session
from chemsim.vessel import Condition

POLL_MS = 120

# (label, condition kind, default value, needs a species). The eleven conditions,
# named the way a chemist would ask for them rather than by their kind strings.
CONDITIONS = [
    ("it reaches",              "temperature_above", 353.0, False),
    ("it cools to",             "temperature_below", 298.0, False),
    ("the temperature steadies", "temperature_steady", 0.01, False),
    ("it boils",                "boiling",           0.0,   False),
    ("crystals appear of",      "solid_at_least",    1.0e-6, True),
    ("the solid dissolves",     "solid_at_most",     1.0e-6, True),
    ("it is consumed below",    "dissolved_at_most", 0.01,  True),
    ("it accumulates above",    "dissolved_at_least", 0.01, True),
    ("the pH falls below",      "pH_below",          3.0,   False),
    ("the pH rises above",      "pH_above",          10.0,  False),
    ("the pressure exceeds",    "pressure_above",    1.5,   False),
]

PHASES = ("liquid", "liquid2", "gas", "solid")


class App:
    """One window over one ``Session``."""

    def __init__(self, root: tk.Tk, example: Example) -> None:
        self.root = root
        self.example = example
        self.session = Session(example.scenario)
        self._open(example)
        self._last: object = None
        self._busy_since = 0.0
        self._selected = ""

        root.title("chemsim")
        root.geometry("1180x820")
        root.minsize(940, 660)
        self._style()
        self._build()
        self._tick()

    # -- construction --------------------------------------------------------

    def _style(self) -> None:
        style = ttk.Style()
        with_theme = "clam" if "clam" in style.theme_names() else style.theme_use()
        style.theme_use(with_theme)
        style.configure("Head.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Big.TLabel", font=("Consolas", 15))
        style.configure("Warn.TLabel", foreground="#a03000")
        style.configure("Dim.TLabel", foreground="#666666")

    def _build(self) -> None:
        root = self.root
        top = ttk.Frame(root, padding=(8, 6))
        top.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(top, text="Example", style="Head.TLabel").pack(side=tk.LEFT)
        self.example_box = ttk.Combobox(
            top, width=34, state="readonly",
            values=[title for _, title in titles()],
        )
        self.example_box.set(self.example.title)
        self.example_box.pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Load", command=self._load_example).pack(side=tk.LEFT)
        ttk.Button(top, text="Reset", command=self._reset).pack(side=tk.LEFT, padx=6)
        ttk.Separator(top, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(top, text="Save recipe",
                   command=self._save).pack(side=tk.LEFT)
        ttk.Button(top, text="Open recipe",
                   command=self._open_file).pack(side=tk.LEFT, padx=6)
        self.clock = ttk.Label(top, text="t = 0.0 s", style="Big.TLabel")
        self.clock.pack(side=tk.RIGHT)

        body = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8)
        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=1)
        body.add(right, weight=3)
        self._build_vessels(left)
        self._build_state(right)
        self._build_drive(root)
        self._build_footer(root)

    def _build_vessels(self, parent) -> None:
        ttk.Label(parent, text="Glassware", style="Head.TLabel").pack(
            anchor=tk.W, pady=(4, 2))
        self.vessel_list = tk.Listbox(parent, height=6, exportselection=False)
        self.vessel_list.pack(fill=tk.X)
        self.vessel_list.bind("<<ListboxSelect>>", lambda _e: self._pick_vessel())
        self.blurb = tk.Text(parent, height=10, wrap=tk.WORD, relief=tk.FLAT,
                             background="#f4f4f2", font=("Segoe UI", 9))
        self.blurb.pack(fill=tk.BOTH, expand=True, pady=(8, 4))
        ttk.Label(parent, text="Recipe so far", style="Head.TLabel").pack(anchor=tk.W)
        self.recipe = tk.Text(parent, height=10, wrap=tk.NONE, relief=tk.FLAT,
                              background="#f7f7f5", font=("Consolas", 8))
        self.recipe.pack(fill=tk.BOTH, expand=True, pady=(2, 6))

    def _build_state(self, parent) -> None:
        head = ttk.Frame(parent)
        head.pack(fill=tk.X, pady=(4, 2))
        self.headline = ttk.Label(head, text="", style="Big.TLabel")
        self.headline.pack(side=tk.LEFT)
        self.flags = ttk.Label(head, text="", style="Warn.TLabel")
        self.flags.pack(side=tk.LEFT, padx=12)
        self.volumes = ttk.Label(parent, text="", style="Dim.TLabel")
        self.volumes.pack(anchor=tk.W)

        cols = ttk.Frame(parent)
        cols.pack(fill=tk.BOTH, expand=True, pady=4)
        self.tables: dict[str, ttk.Treeview] = {}
        for phase, title in (("liquid", "liquid"), ("liquid2", "second layer"),
                             ("gas", "headspace"), ("solid", "solid")):
            frame = ttk.LabelFrame(cols, text=title, padding=2)
            frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
            tree = ttk.Treeview(frame, columns=("mol",), show="tree headings",
                                height=9)
            tree.heading("#0", text="species")
            tree.heading("mol", text="mol")
            tree.column("#0", width=130, stretch=True)
            tree.column("mol", width=80, anchor=tk.E, stretch=False)
            tree.pack(fill=tk.BOTH, expand=True)
            self.tables[phase] = tree

        ttk.Label(parent, text="What the engine has to say", style="Head.TLabel").pack(
            anchor=tk.W, pady=(6, 0))
        self.reports = tk.Text(parent, height=7, wrap=tk.WORD, relief=tk.FLAT,
                               background="#fbf8f2", font=("Segoe UI", 9))
        self.reports.pack(fill=tk.BOTH, expand=False, pady=(2, 4))

    def _build_drive(self, parent) -> None:
        book = ttk.Notebook(parent)
        book.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(4, 2))

        # --- drive
        drive = ttk.Frame(book, padding=6)
        book.add(drive, text="Drive")
        ttk.Label(drive, text="Step").grid(row=0, column=0, sticky=tk.W)
        self.step_secs = _entry(drive, "600", 8, row=0, col=1)
        ttk.Label(drive, text="s, in chunks of").grid(row=0, column=2, padx=(4, 2))
        self.chunk = _entry(drive, f"{DEFAULT_CHUNK:g}", 6, row=0, col=3)
        ttk.Label(drive, text="s").grid(row=0, column=4, sticky=tk.W)
        ttk.Button(drive, text="Step", command=self._step).grid(
            row=0, column=5, padx=8)

        ttk.Label(drive, text="Wait until").grid(row=1, column=0, sticky=tk.W,
                                                 pady=(6, 0))
        self.cond_box = ttk.Combobox(drive, width=24, state="readonly",
                                     values=[c[0] for c in CONDITIONS])
        self.cond_box.current(0)
        self.cond_box.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=(6, 0))
        self.cond_box.bind("<<ComboboxSelected>>", lambda _e: self._condition_changed())
        self.cond_value = _entry(drive, "353.0", 10, row=1, col=3)
        self.cond_species = ttk.Combobox(drive, width=22, values=[])
        self.cond_species.grid(row=1, column=4, padx=4, pady=(6, 0))
        ttk.Label(drive, text="timeout").grid(row=1, column=5, padx=(8, 2))
        self.timeout = _entry(drive, "7200", 8, row=1, col=6)
        ttk.Button(drive, text="Wait", command=self._wait).grid(
            row=1, column=7, padx=8, pady=(6, 0))
        ttk.Button(drive, text="Stop", command=self.session.stop).grid(
            row=0, column=7, padx=8)

        # --- charge
        charge = ttk.Frame(book, padding=6)
        book.add(charge, text="Charge")
        ttk.Label(charge, text="Add").grid(row=0, column=0, sticky=tk.W)
        self.charge_amount = _entry(charge, "1.0", 8, row=0, col=1)
        ttk.Label(charge, text="mol of").grid(row=0, column=2, padx=4)
        self.charge_species = ttk.Combobox(charge, width=30, values=[])
        self.charge_species.grid(row=0, column=3)
        ttk.Label(charge, text="to the").grid(row=0, column=4, padx=4)
        self.charge_phase = ttk.Combobox(charge, width=10, state="readonly",
                                         values=PHASES)
        self.charge_phase.current(0)
        self.charge_phase.grid(row=0, column=5)
        ttk.Button(charge, text="Charge", command=self._charge).grid(
            row=0, column=6, padx=8)
        ttk.Button(charge, text="Fill headspace with air",
                   command=lambda: self._fill({"N#N": 0.79, "O=O": 0.21})).grid(
            row=1, column=0, columnspan=3, sticky=tk.W, pady=(6, 0))
        ttk.Button(charge, text="Blanket with nitrogen",
                   command=lambda: self._fill({"N#N": 1.0})).grid(
            row=1, column=3, columnspan=2, sticky=tk.W, pady=(6, 0))

        # --- conditions of the vessel
        setup = ttk.Frame(book, padding=6)
        book.add(setup, text="Apparatus")
        self.knobs: dict[str, tk.Entry] = {}
        for i, (label, kind, key, default) in enumerate((
            ("Heater, W", "set_heat", "watts", "0.0"),
            ("Surroundings, K", "set_env", "T_env", "298.15"),
            ("Vent, mol/(bar s)  (0 seals it)", "set_vent", "k_vent", "1000.0"),
            ("Stirring, kla", "set_stir", "kla", "5.0"),
            ("Shaking, k_lle", "set_shake", "k_lle", "5.0"),
        )):
            ttk.Label(setup, text=label).grid(row=i, column=0, sticky=tk.W, pady=1)
            box = _entry(setup, default, 12, row=i, col=1)
            self.knobs[kind] = box
            ttk.Button(
                setup, text="Set",
                command=lambda k=kind, kk=key, b=box: self._set(k, kk, b),
            ).grid(row=i, column=2, padx=8)

        # --- transfers
        move = ttk.Frame(book, padding=6)
        book.add(move, text="Transfer")
        ttk.Label(move, text="Pour").grid(row=0, column=0, sticky=tk.W)
        self.pour_fraction = _entry(move, "1.0", 6, row=0, col=1)
        ttk.Label(move, text="of the").grid(row=0, column=2, padx=4)
        self.pour_phase = ttk.Combobox(
            move, width=10, state="readonly",
            values=("liquid", "lower", "upper", "gas", "solid", "all"))
        self.pour_phase.current(0)
        self.pour_phase.grid(row=0, column=3)
        ttk.Label(move, text="into").grid(row=0, column=4, padx=4)
        self.pour_target = ttk.Combobox(move, width=16, state="readonly", values=[])
        self.pour_target.grid(row=0, column=5)
        ttk.Button(move, text="Pour", command=self._transfer).grid(
            row=0, column=6, padx=8)
        ttk.Label(move, text="Filter into").grid(row=1, column=0, sticky=tk.W,
                                                 pady=(8, 0))
        self.filter_target = ttk.Combobox(move, width=16, state="readonly", values=[])
        self.filter_target.grid(row=1, column=1, columnspan=2, sticky=tk.W,
                                pady=(8, 0))
        ttk.Label(move, text="cake porosity").grid(row=1, column=3, padx=4)
        self.porosity = _entry(move, "0.4", 6, row=1, col=4)
        ttk.Button(move, text="Filter", command=self._filter).grid(
            row=1, column=6, padx=8, pady=(8, 0))

    def _build_footer(self, parent) -> None:
        bar = ttk.Frame(parent, padding=(8, 2))
        bar.pack(side=tk.TOP, fill=tk.X)
        self.progress = ttk.Progressbar(bar, mode="determinate", length=220)
        self.progress.pack(side=tk.LEFT)
        self.activity = ttk.Label(bar, text="idle", style="Head.TLabel")
        self.activity.pack(side=tk.LEFT, padx=10)
        self.cost = ttk.Label(bar, text="", style="Dim.TLabel")
        self.cost.pack(side=tk.RIGHT)

        self.message = tk.Text(parent, height=6, wrap=tk.WORD, relief=tk.FLAT,
                               background="#f7f7f5", font=("Consolas", 9))
        self.message.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(0, 8))

    # -- commands ------------------------------------------------------------

    def _vessel(self) -> str:
        return self._selected or (
            self.session.snapshot().vessel_names[:1] or ("",))[0]

    def _step(self) -> None:
        self.session.step(_float(self.step_secs, 600.0),
                          chunk=_float(self.chunk, DEFAULT_CHUNK))

    def _wait(self) -> None:
        label = self.cond_box.get()
        _, kind, _, needs = next(c for c in CONDITIONS if c[0] == label)
        try:
            condition = Condition(
                kind=kind,
                value=_float(self.cond_value, 0.0),
                species=self.cond_species.get().strip() if needs else "",
            )
        except ValueError as exc:
            self._show_error(str(exc))
            return
        self.session.wait_until(self._vessel(), condition,
                                _float(self.timeout, 3600.0),
                                chunk=_float(self.chunk, DEFAULT_CHUNK))

    def _charge(self) -> None:
        species = self.charge_species.get().strip()
        if not species:
            self._show_error("Pick a species to charge.")
            return
        self.session.do("charge", self._vessel(),
                        amounts={species: _float(self.charge_amount, 0.0)},
                        phase=self.charge_phase.get())

    def _fill(self, composition: dict[str, float]) -> None:
        self.session.do("fill_headspace", self._vessel(), composition=composition)

    def _set(self, kind: str, key: str, box) -> None:
        self.session.do(kind, self._vessel(), **{key: _float(box, 0.0)})

    def _transfer(self) -> None:
        target = self.pour_target.get()
        if not target:
            self._show_error("Pick a vessel to pour into.")
            return
        self.session.do("transfer", self._vessel(), to=target,
                        fraction=_float(self.pour_fraction, 1.0),
                        phase=self.pour_phase.get())

    def _filter(self) -> None:
        target = self.filter_target.get()
        if not target:
            self._show_error("Pick a vessel to filter into.")
            return
        self.session.do("filter", self._vessel(), to=target,
                        porosity=_float(self.porosity, 0.4))

    def _condition_changed(self) -> None:
        label = self.cond_box.get()
        _, _, default, needs = next(c for c in CONDITIONS if c[0] == label)
        self.cond_value.delete(0, tk.END)
        self.cond_value.insert(0, f"{default:g}")
        self.cond_species.configure(state="normal" if needs else "disabled")

    def _reset(self) -> None:
        # Re-loading rather than Reset-then-load: ``Load`` already builds a fresh
        # world and replays the opening, and ``Reset`` before it would discover
        # the prep's 120-species network a second time for nothing.
        self.session.submit(Load(self.example.scenario, self.example.opening,
                                 self.example.title))

    def _open(self, example: Example) -> None:
        self.session.submit(Load(example.scenario, example.opening, example.title))

    def _load_example(self) -> None:
        chosen = self.example_box.get()
        key = next((k for k, title in titles() if title == chosen), None)
        if key is None:
            return
        self.example = load(key)
        self._open(self.example)
        self._selected = ""

    def _save(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("chemsim recipe", "*.json")])
        if not path:
            return
        # ⚠ THE SCRIPT, NOT THE STATE VECTOR. A saved run here is a RECIPE -- it
        # stores the conditions waited on and never the instants they resolved to,
        # so replaying it against a different charge waits the right length of
        # time rather than the remembered one. See ``World.script``.
        payload = {"example": self.example.key,
                   "script": list(self.session.snapshot().script)}
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        self._show_error(f"Saved {len(payload['script'])} recipe steps to {path}")

    def _open_file(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("chemsim recipe", "*.json"), ("all files", "*.*")])
        if not path:
            return
        # ⚠ The whole read is inside the guard, including pulling the script out
        # of it. A hand-edited or truncated file is an ordinary thing to open, and
        # a KeyError raised from a Tk callback goes to a traceback nobody sees.
        try:
            with open(path, encoding="utf-8") as fh:
                payload = json.load(fh)
            self.example = load(payload.get("example", "flask"))
            script = tuple(payload["script"])
        except Exception as exc:                                # noqa: BLE001
            messagebox.showerror("chemsim", f"{path}\n\n{exc}")
            return
        self.example_box.set(self.example.title)
        self.session.submit(Load(self.example.scenario, script, self.example.title))

    def _show_error(self, text: str) -> None:
        self.message.delete("1.0", tk.END)
        self.message.insert(tk.END, text)

    # -- rendering -----------------------------------------------------------

    def _pick_vessel(self) -> None:
        picked = self.vessel_list.curselection()
        if picked:
            self._selected = self.vessel_list.get(picked[0])
            self._last = None                     # force a redraw of the tables

    def _tick(self) -> None:
        snap = self.session.snapshot()
        # ⚠ The wall clock is computed HERE and not read off the snapshot. A chunk
        # publishes once when it starts, so between publishes the snapshot's own
        # wall figure is frozen -- and a stiff transient is exactly where that gap
        # is longest and where a player most needs to see the seconds moving.
        if snap.busy and not self._busy_since:
            self._busy_since = time.perf_counter()
        elif not snap.busy:
            self._busy_since = 0.0
        if snap is not self._last:
            self._draw(snap)
            self._last = snap
        self._draw_activity(snap)
        self.root.after(POLL_MS, self._tick)

    def _draw_activity(self, snap) -> None:
        if snap.busy:
            live = time.perf_counter() - (self._busy_since or time.perf_counter())
            wall = max(snap.wall, live)
            word = "stopping after this chunk" if snap.stopping else snap.activity
            self.activity.configure(text=f"IN PROGRESS: {word}")
            ratio = wall / snap.sim if snap.sim > 0 else 0.0
            self.cost.configure(
                text=f"{snap.sim:8.1f} simulated s   {wall:6.1f} wall s   "
                     f"{ratio:8.3f} wall s per simulated s"
            )
            if snap.progress >= 0.0:
                self.progress.configure(mode="determinate",
                                        value=100.0 * snap.progress)
            else:
                self.progress.configure(mode="indeterminate")
                self.progress.step(6)
        else:
            self.activity.configure(text=snap.outcome or "idle")
            self.progress.configure(mode="determinate", value=0.0)
            if snap.sim > 0:
                self.cost.configure(
                    text=f"last: {snap.sim:.1f} simulated s in {snap.wall:.1f} "
                         f"wall s   ({snap.cost_ratio:.3f} wall s per simulated s)"
                )

    def _draw(self, snap) -> None:
        self.clock.configure(text=f"t = {snap.t:,.1f} s")
        names = list(snap.vessel_names)
        if list(self.vessel_list.get(0, tk.END)) != names:
            self.vessel_list.delete(0, tk.END)
            for name in names:
                self.vessel_list.insert(tk.END, name)
            if names:
                self.vessel_list.selection_set(0)
                self._selected = self._selected if self._selected in names else names[0]
        if self._selected not in names and names:
            self._selected = names[0]
        others = [n for n in names if n != self._selected]
        self.pour_target.configure(values=others)
        self.filter_target.configure(values=others)
        if others and not self.pour_target.get():
            self.pour_target.set(others[0])
            self.filter_target.set(others[0])
        self.charge_species.configure(values=list(snap.species))
        self.cond_species.configure(values=list(snap.species))

        _set_text(self.blurb, f"{self.example.title}\n\n{self.example.blurb}")
        _set_text(self.recipe, _recipe_lines(snap.script))
        if snap.error:
            _set_text(self.message, snap.error)
        elif snap.log:
            _set_text(self.message, "\n".join(snap.log[-12:]))

        view = snap.vessel(self._selected)
        if view is None:
            return
        self.headline.configure(
            text=f"{view.T:8.2f} K   {view.pressure:7.4f} bar"
                 + (f"   pH {view.pH:5.2f}" if view.pH is not None else "")
        )
        flags = []
        if view.is_boiling:
            flags.append("BOILING")
        if view.has_second_layer:
            flags.append("TWO LIQUID LAYERS")
        if view.solid:
            flags.append("SOLID PRESENT")
        self.flags.configure(text="   ".join(flags))
        self.volumes.configure(
            text=f"liquid {view.liquid_volume * 1e3:8.1f} mL     "
                 f"solid {view.solid_volume * 1e3:8.1f} mL     "
                 f"headspace {view.gas_volume * 1e3:8.1f} mL     "
                 f"of {view.volume * 1e3:.0f} mL"
        )
        for phase, tree in self.tables.items():
            tree.delete(*tree.get_children())
            for species, mol in getattr(view, phase).items():
                tree.insert("", tk.END, text=species, values=(f"{mol:.6g}",))
        _set_text(self.reports, "\n\n".join(view.reports)
                  or "Nothing to report: no conservation residue, no capped "
                     "activity coefficient, no refused phase split, no latent "
                     "integration fragility.")

    def close(self) -> None:
        self.session.close()


# ---------------------------------------------------------------------------


def _entry(parent, default: str, width: int, row: int, col: int):
    box = ttk.Entry(parent, width=width)
    box.insert(0, default)
    box.grid(row=row, column=col, padx=2, sticky=tk.W)
    return box


def _float(box, fallback: float) -> float:
    try:
        return float(box.get())
    except (TypeError, ValueError):
        return fallback


def _set_text(widget, text: str) -> None:
    widget.delete("1.0", tk.END)
    widget.insert(tk.END, text)


def _recipe_lines(script) -> str:
    """The script as something a person can read back.

    ⚠ A chopped wait appears as the several legs it was actually run as, because
    that is what happened and what will replay. Folding them together on screen
    would be showing a recipe that was never executed.
    """
    out = []
    for entry in script:
        do = entry.get("do")
        if do == "step":
            out.append(f"step   {entry['dt']:g} s")
        elif do == "wait_until":
            what = " or ".join(
                Condition.from_dict(c).describe() for c in entry["conditions"]
            )
            out.append(f"wait   {what}  (timeout {entry['timeout']:g} s)")
        elif do == "schedule":
            ev = entry["event"]
            out.append(f"do     {ev['kind']} {ev.get('vessel', '')}")
    return "\n".join(out) or "(nothing yet)"


def launch(example_key: str = "flask") -> None:
    """Open the window. Blocks until it is closed."""
    root = tk.Tk()
    app = App(root, load(example_key))

    def shutdown() -> None:
        app.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", shutdown)
    root.mainloop()
