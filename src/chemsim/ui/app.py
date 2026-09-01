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
  ``lle_report``, ``electrolyte_report`` and the rest, plus everything
  ``build_network`` said while discovering the reaction set. The engine's rule is
  that nothing is silently approximated, which is only worth anything if somebody
  is shown what it said. The refluxing rig destroyed 0.34 mol of its air for
  months on a channel that was reported all along and that nothing read -- and
  the builder's notices were on exactly such a channel until P1, printed to a
  stdout that a windowed application does not have;
* **the recipe panel** -- the script, growing as the player works. A run is a pure
  function of (scenario, script), so this is the artifact, and it is visible
  rather than hidden behind a Save button.

P4 added two more, and both are the same principle one step further on:

* **the Bench tab** -- the shelf as a picker. 71 tiered rows, or all 1167 priced
  species, or all 1583 with the 416 refusals GREYED AND CARRYING THEIR REASON.
  A player who cannot find a species has to be told the engine declines to price
  it, not left to conclude the game is broken (``GAME_DESIGN.md`` 8.3). ⚠ And
  choosing rows BUILDS THE WORLD rather than filling a list: a network is derived
  from its feed, so the selection is the scenario and the world is rebuilt when
  it changes;
* **REACT FURTHER** -- the control that raises the generation bound. One
  generation is an approximation that touches MATTER, which is admissible only
  because it is never silent; a bound the player can see and lift is a choice
  rather than an approximation. ⚠ It raises the SPECIES CAP as well, and that is
  not a convenience: at ``generations=2`` four bench reagents hit 400 species, so
  the bound that BITES is the cap and bumping generations alone would have been a
  button that did nothing. P1 found the same thing from the other side.
"""

from __future__ import annotations

import json
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from chemsim.engine import inventory as inv
from chemsim.engine.scenario import Scenario
from chemsim.ui.examples import Example, bench, load, rebuilt, titles
from chemsim.ui.session import DEFAULT_CHUNK, Load, Session
from chemsim.vessel import Condition

POLL_MS = 120

# How far REACT FURTHER moves each bound. The generation step is 1 because a
# generation is the mechanic; the species step is large because the cap is a
# tractability limit rather than a chemical one and a 400 -> 401 rebuild would be
# a button that appeared to do nothing.
GENERATION_STEP = 1
SPECIES_STEP = 300

# The reports panel's heading, kept as a constant because the panel appends the
# unexplored-frontier count to it and has to be able to take it off again.
REPORTS_HEAD = "What the engine has to say"

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

        self.reports_head = ttk.Label(parent, text=REPORTS_HEAD, style="Head.TLabel")
        self.reports_head.pack(anchor=tk.W, pady=(6, 0))
        # ⚠ THE ONLY SCROLLBAR IN THIS WINDOW, and it is here because this panel
        # was given something it cannot fit. It used to hold at most seven short
        # vessel reports; it now also holds everything ``build_network`` said,
        # which is 397 lines for five reagents two generations deep. A panel that
        # shows the first seven of four hundred notices and offers no way to
        # reach the rest is the same failure as printing them to a console nobody
        # reads -- one that lets the engine claim it reported something nobody
        # could have seen.
        box = ttk.Frame(parent)
        box.pack(fill=tk.BOTH, expand=False, pady=(2, 4))
        bar = ttk.Scrollbar(box, orient=tk.VERTICAL)
        bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.reports = tk.Text(box, height=9, wrap=tk.WORD, relief=tk.FLAT,
                               background="#fbf8f2", font=("Segoe UI", 9),
                               yscrollcommand=bar.set)
        self.reports.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bar.configure(command=self.reports.yview)

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

        # ⚠ THE CONTROL THAT LIFTS THE BOUND, next to the one that spends time,
        # because "this flask has more to give" is an answer to the same question
        # Step is. The reports heading is where the player is told there is a
        # frontier at all; this is where they do something about it.
        self.further = ttk.Button(drive, text="React further",
                                  command=self._react_further)
        self.further.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))
        self.further_label = ttk.Label(drive, text="", style="Dim.TLabel")
        self.further_label.grid(row=2, column=2, columnspan=6, sticky=tk.W,
                                pady=(8, 0))

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
        # ⚠ TWO DESTINATIONS, BECAUSE A FILTRATION HAS TWO STREAMS AND THIS
        # PANEL USED TO OFFER ONE. It sent ``to=`` in the payload, which the
        # FILTER event does not read -- its keys are ``filtrate`` and ``cake`` --
        # so the vessel picked in the dropdown received nothing and the whole
        # flask was DISCARDED, silently and every time. Measured on a 1 mol
        # charge: "filter flask: cake 0.0000 mol solid + 0.0000 mol liquor ->
        # discarded; filtrate 1.0000 mol -> discarded". The engine said so in the
        # transfer log all along; nothing was reading it. Present since the
        # button existed.
        ttk.Label(move, text="Filter: filtrate to").grid(row=1, column=0,
                                                         sticky=tk.W, pady=(8, 0))
        self.filter_target = ttk.Combobox(move, width=16, state="readonly", values=[])
        self.filter_target.grid(row=1, column=1, sticky=tk.W, pady=(8, 0))
        ttk.Label(move, text="cake to").grid(row=1, column=2, padx=4)
        self.cake_target = ttk.Combobox(move, width=16, state="readonly", values=[])
        self.cake_target.grid(row=1, column=3, sticky=tk.W, pady=(8, 0))
        ttk.Label(move, text="cake porosity").grid(row=1, column=4, padx=4)
        self.porosity = _entry(move, "0.4", 6, row=1, col=5)
        ttk.Button(move, text="Filter", command=self._filter).grid(
            row=1, column=6, padx=8, pady=(8, 0))

        # --- the shelf: the two verbs that close the loop
        shelf = ttk.Frame(book, padding=6)
        book.add(shelf, text="Shelf")
        ttk.Label(shelf, text="Bottle").grid(row=0, column=0, sticky=tk.W)
        self.bottle_fraction = _entry(shelf, "1.0", 6, row=0, col=1)
        ttk.Label(shelf, text="of the").grid(row=0, column=2, padx=4)
        self.bottle_phase = ttk.Combobox(
            shelf, width=10, state="readonly",
            values=("all", "liquid", "lower", "upper", "gas", "solid"))
        self.bottle_phase.current(0)
        self.bottle_phase.grid(row=0, column=3)
        ttk.Label(shelf, text="as").grid(row=0, column=4, padx=4)
        self.bottle_name = _entry(shelf, "", 26, row=0, col=5)
        ttk.Button(shelf, text="Bottle it", command=self._bottle).grid(
            row=0, column=6, padx=8)

        ttk.Label(shelf, text="On the shelf").grid(row=1, column=0, sticky=tk.NW,
                                                   pady=(8, 0))
        self.shelf_list = tk.Listbox(shelf, height=4, width=72,
                                     exportselection=False,
                                     font=("Consolas", 8))
        self.shelf_list.grid(row=1, column=1, columnspan=5, sticky=tk.W,
                             pady=(8, 0))
        pour = ttk.Frame(shelf)
        pour.grid(row=1, column=6, sticky=tk.NW, padx=8, pady=(8, 0))
        ttk.Button(pour, text="Charge it", command=self._charge_stock).pack()
        self.stock_fraction = ttk.Entry(pour, width=6)
        self.stock_fraction.insert(0, "1.0")
        self.stock_fraction.pack(pady=2)
        ttk.Label(shelf, style="Dim.TLabel",
                  text="A stock is the whole composition and its temperature -- "
                       "purity is derived for display, and every impurity in it "
                       "is carried into whatever you charge it into.").grid(
            row=2, column=0, columnspan=7, sticky=tk.W, pady=(6, 0))

        self._build_bench(book)

    def _build_bench(self, book) -> None:
        """The picker: the shelf as data, and choosing rows BUILDS the world.

        ⚠ It is a Treeview and not a Listbox for one reason that is not
        cosmetic: a refused row has to be VISIBLE, GREYED and CARRYING ITS
        REASON, and a Listbox has no per-row colour and no second column. 416 of
        1583 corpus species cannot be priced, and a picker that hid them would
        make the element floor look like a missing feature.
        """
        bench_tab = ttk.Frame(book, padding=6)
        book.add(bench_tab, text="Bench")

        top = ttk.Frame(bench_tab)
        top.pack(fill=tk.X)
        self.tier_vars: dict[str, tk.BooleanVar] = {}
        for tier in inv.TIERS:
            var = tk.BooleanVar(value=True)
            self.tier_vars[tier] = var
            ttk.Checkbutton(top, text=tier, variable=var,
                            command=self._refill_bench).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Separator(top, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        # ⚠ A SEPARATE AXIS AND NOT A FOURTH TIER (GAME_DESIGN.md 8.5). Every
        # priced species at once, for exploration and for pointing the picker at
        # 1167 rows to find out what that costs.
        self.cheat = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="all priced species (cheat)", variable=self.cheat,
                        command=self._refill_bench).pack(side=tk.LEFT)
        self.show_refused = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="show refused", variable=self.show_refused,
                        command=self._refill_bench).pack(side=tk.LEFT, padx=8)
        ttk.Label(top, text="find").pack(side=tk.LEFT, padx=(12, 2))
        self.search = ttk.Entry(top, width=18)
        self.search.pack(side=tk.LEFT)
        self.search.bind("<KeyRelease>", lambda _e: self._refill_bench())

        box = ttk.Frame(bench_tab)
        box.pack(fill=tk.BOTH, expand=True, pady=(6, 2))
        bar = ttk.Scrollbar(box, orient=tk.VERTICAL)
        bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.bench_tree = ttk.Treeview(
            box, columns=("tier", "mol", "phase", "why"), show="tree headings",
            height=8, selectmode="extended", yscrollcommand=bar.set)
        for col, title, width, anchor in (
            ("#0", "species", 200, tk.W), ("tier", "tier", 90, tk.W),
            ("mol", "mol", 60, tk.E), ("phase", "phase", 60, tk.W),
            ("why", "where it comes from, or why it is refused", 420, tk.W),
        ):
            self.bench_tree.heading(col, text=title)
            self.bench_tree.column(col, width=width, anchor=anchor,
                                   stretch=(col == "why"))
        self.bench_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bar.configure(command=self.bench_tree.yview)
        self.bench_tree.tag_configure("refused", foreground="#999999")
        self.bench_tree.bind("<<TreeviewSelect>>", lambda _e: self._bench_picked())

        foot = ttk.Frame(bench_tab)
        foot.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(foot, text="Pour selected into a fresh flask",
                   command=self._pour_bench).pack(side=tk.LEFT)
        ttk.Label(foot, text="generations").pack(side=tk.LEFT, padx=(12, 2))
        self.bench_gens = ttk.Entry(foot, width=5)
        self.bench_gens.insert(0, "1")
        self.bench_gens.pack(side=tk.LEFT)
        ttk.Label(foot, text="species cap").pack(side=tk.LEFT, padx=(10, 2))
        self.bench_cap = ttk.Entry(foot, width=6)
        self.bench_cap.insert(0, "400")
        self.bench_cap.pack(side=tk.LEFT)
        self.bench_count = ttk.Label(foot, text="", style="Dim.TLabel")
        self.bench_count.pack(side=tk.RIGHT)
        self._refill_bench()

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
        filtrate = self.filter_target.get()
        cake = self.cake_target.get()
        if not filtrate and not cake:
            self._show_error(
                "Pick where the filtrate and the cake go. Leaving one blank "
                "discards that stream, which is a real bench action -- but "
                "discarding both is not a filtration."
            )
            return
        self.session.do("filter", self._vessel(),
                        filtrate=filtrate or None, cake=cake or None,
                        porosity=_float(self.porosity, 0.4))

    def _bottle(self) -> None:
        self.session.bottle(
            self._vessel(),
            name=self.bottle_name.get().strip(),
            fraction=_float(self.bottle_fraction, 1.0),
            phase=self.bottle_phase.get(),
        )

    def _charge_stock(self) -> None:
        picked = self.shelf_list.curselection()
        shelf = self.session.snapshot().shelf
        if not picked or picked[0] >= len(shelf):
            self._show_error("Pick a stock on the shelf to charge.")
            return
        self.session.charge_stock(self._vessel(), shelf[picked[0]],
                                  _float(self.stock_fraction, 1.0))

    # -- the bench --------------------------------------------------------

    def _bench_rows(self) -> list:
        """What the picker should be showing, given the toggles and the search."""
        if self.cheat.get():
            items = list(inv.roster() if self.show_refused.get()
                         else inv.all_priced())
        else:
            tiers = tuple(t for t in inv.TIERS if self.tier_vars[t].get())
            items = list(inv.shelf(tiers)) if tiers else []
            if not self.show_refused.get():
                items = [i for i in items if i.chargeable]
        needle = self.search.get().strip().lower()
        if needle:
            items = [i for i in items
                     if needle in i.name.lower() or needle in i.id.lower()]
        return items

    def _refill_bench(self) -> None:
        """Rebuild the picker's rows, keeping what was selected where it survives.

        ⚠ Rebuilt only from a TOGGLE, never from the poll -- the vessel list and
        the shelf list both learned that lesson. A tree rebuilt eight times a
        second loses the selection under the player's cursor, which is the
        selection the Pour button reads.
        """
        keep = {self.bench_tree.item(i, "text") for i in self.bench_tree.selection()}
        self.bench_tree.delete(*self.bench_tree.get_children())
        self._bench_items = {}
        for item in self._bench_rows():
            why = item.refusal.splitlines()[0] if item.refusal else item.note
            iid = self.bench_tree.insert(
                "", tk.END, text=item.name,
                values=(item.tier, f"{item.amount:g}", item.phase, why),
                tags=() if item.chargeable else ("refused",),
            )
            self._bench_items[iid] = item
            if item.name in keep:
                self.bench_tree.selection_add(iid)
        refused = sum(1 for i in self._bench_items.values() if not i.chargeable)
        self.bench_count.configure(
            text=f"{len(self._bench_items)} rows"
                 + (f", {refused} refused a price" if refused else "")
        )

    def _bench_picked(self) -> None:
        """Say why a greyed row is greyed, in the engine's own words.

        ⚠ 8.3: a refused species may not be silently absent AND may not be
        chargeable-then-failing. Greying it satisfies the first; putting the
        reason where a click lands satisfies the second, because the player finds
        out before pouring rather than after.
        """
        picked = [self._bench_items[i] for i in self.bench_tree.selection()
                  if i in self._bench_items]
        bad = [i for i in picked if not i.chargeable]
        if bad:
            self._show_error(
                f"{bad[0].name} cannot be charged into a flask.\n\n"
                f"{bad[0].refusal}\n\n"
                f"That refusal is the element floor working rather than a gap: a "
                f"group-contribution estimator outside its domain returns a "
                f"well-formed number that means nothing -- Joback prices Cl2 at "
                f"-74.81 kJ/mol where the answer is 0 by definition. "
                f"{inv.counts()['refused']} of {inv.counts()['corpus']} corpus "
                f"species are refused."
            )

    def _pour_bench(self) -> None:
        """Build a world from the selection. ⚠ THE SELECTION *IS* THE SCENARIO.

        P2's finding: ``Vessel.charge_state`` refuses a species the network does
        not carry, and a network is derived from its feed -- so choosing shelf
        rows is not filling a list, it is defining the world, and the world has
        to be rebuilt. ``inventory.scenario_for`` owns the two guarantees; this
        method only collects the rows and says what happened.
        """
        picked = [self._bench_items[i] for i in self.bench_tree.selection()
                  if i in self._bench_items]
        live = [i for i in picked if i.chargeable]
        if not live:
            self._show_error(
                "Pick at least one species that is not greyed. A greyed row is "
                "refused a price by the element floor and cannot enter a flask."
            )
            return
        gens = int(_float(self.bench_gens, 1.0))
        self.example = bench(
            live, generations=(None if gens <= 0 else gens),
            max_species=int(_float(self.bench_cap, 400.0)),
        )
        self.example_box.set(self.example.title)
        self._selected = ""
        self._open(self.example)
        skipped = len(picked) - len(live)
        self._show_error(
            f"Poured {len(live)} species into a fresh 1 L flask at "
            f"{'a fixpoint' if gens <= 0 else f'{gens} generation(s)'}"
            + (f"; skipped {skipped} refused row(s)" if skipped else "")
            + ".\n\nThe network is being built on the worker thread -- watch the "
              "reports panel. Its heading says whether the flask has more to "
              "give, and REACT FURTHER on the Drive tab is how you ask for it."
        )

    def _react_further(self) -> None:
        """Raise the network bounds and replay the recipe against a deeper set.

        ⚠⚠ **IT RAISES THE SPECIES CAP AS WELL, AND THAT IS THE WHOLE REASON THIS
        IS NOT A ONE-LINER.** The two bounds compete, and at ``generations=2``
        four ordinary bench reagents hit 400 species -- so on a capped network the
        bound that BIT is the cap, and a button that only bumped ``generations``
        would rebuild an identical network and look broken. Measured: glucose,
        water and air give 400 species and 653 reactions at both 2 and 3
        generations. P1 found the same competition from the other side, in the
        frontier report.

        ⚠ And it replays the RECIPE, which is a different claim from "continue
        from here" -- see ``examples.rebuilt``. Stated in the message rather than
        left for a player to infer from a number that moved.
        """
        snap = self.session.snapshot()
        scenario = self.example.scenario
        if scenario.generations is None:
            self._show_error(
                "This world is already built to a FIXPOINT -- every reaction the "
                "templates can find on these species is in the network, so there "
                "is no bound left to raise. An empty frontier here is a fact "
                "about the chemistry rather than a limit."
            )
            return
        gens = scenario.generations + GENERATION_STEP
        capped = len(snap.species) >= scenario.max_species
        cap = scenario.max_species + (SPECIES_STEP if capped else 0)
        self.example = rebuilt(self.example, generations=gens, max_species=cap)
        # ⚠ R5: the boxes are what _pour_bench reads, so a raised bound that is
        # not written back is DISCARDED by the very next pour -- observed live,
        # a player went 3 generations back to 1 without being told. Writing the
        # scenario's bounds back also puts the current bound in the one place a
        # player would look for it.
        for box, bound in ((self.bench_gens, gens), (self.bench_cap, cap)):
            box.delete(0, tk.END)
            box.insert(0, str(bound))
        # ⚠ The CURRENT script, not the opening: the player has done things and a
        # replay of the opening alone would throw the experiment away.
        self.session.submit(Load(self.example.scenario, snap.script,
                                 self.example.title))
        self._show_error(
            f"Generation bound {scenario.generations} -> {gens}"
            + (f", species cap {scenario.max_species} -> {cap} (the cap is what "
               f"stopped the last build, not the generation bound)" if capped
               else f", species cap left at {scenario.max_species}")
            + f".\n\nThe {len(snap.script)}-step recipe is being replayed against "
              f"the deeper reaction set. ⚠ That is 'the experiment re-done knowing "
              f"more chemistry', not 'the flask carried on from here': a species "
              f"discovered in the new generation was available from t = 0 on the "
              f"replay. The bound is raised, not hidden."
        )

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
        #
        # ⚠⚠ AND THE WHOLE SCENARIO, NOT ONLY ITS KEY, WHICH P4 HAD TO FIX BEFORE
        # IT COULD SHIP EITHER OF ITS CONTROLS. The file used to hold
        # ``{"example": key, "script": [...]}``, which is enough only while every
        # world is one of four hard-coded ones. A bench world is a shelf
        # selection and has no key; a world that has been REACTED FURTHER differs
        # from its key's scenario by exactly the bound that was raised. Both would
        # have reloaded as something else -- silently, and looking fine.
        payload = {"example": self.example.key,
                   "title": self.example.title,
                   "scenario": self.example.scenario.to_dict(),
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
            # ⚠ THE SAVED SCENARIO WINS WHERE THERE IS ONE, and a file without
            # one still opens: pre-P4 saves hold only the key, and the key's own
            # scenario is the right answer for them.
            if payload.get("scenario"):
                from dataclasses import replace as _replace

                self.example = _replace(
                    self.example,
                    scenario=Scenario.from_dict(payload["scenario"]),
                    title=payload.get("title", self.example.title),
                )
            script = tuple(payload["script"])
        except Exception as exc:                                # noqa: BLE001
            messagebox.showerror("chemsim", f"{path}\n\n{exc}")
            return
        self.example_box.set(
            self.example.title if self.example.title in
            [t for _k, t in titles()] else self.example_box.get()
        )
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
        self.cake_target.configure(values=[""] + others)
        if others and not self.pour_target.get():
            self.pour_target.set(others[0])
            self.filter_target.set(others[0])
        self.charge_species.configure(values=list(snap.species))
        self.cond_species.configure(values=list(snap.species))

        # ⚠ REBUILT ONLY WHEN IT CHANGES, like the vessel list above it: this
        # runs on every poll, and a Listbox rebuilt eight times a second loses
        # the selection under the player's cursor -- which is the selection the
        # Charge button reads. The same reason ``_set_text`` restores a scroll
        # position rather than resetting it.
        lines = [_stock_line(st) for st in snap.shelf]
        if list(self.shelf_list.get(0, tk.END)) != lines:
            keep = self.shelf_list.curselection()
            self.shelf_list.delete(0, tk.END)
            for line in lines:
                self.shelf_list.insert(tk.END, line)
            if keep and keep[0] < len(lines):
                self.shelf_list.selection_set(keep[0])

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
        # ⚠ THE FLASK'S REPORTS AND THE NETWORK'S NOTICES IN ONE PANEL, IN THAT
        # ORDER, AND LABELLED. The vessel's are about the state on screen right
        # now; the network's are about how the reaction set that produced it was
        # discovered, and were said once at build time. Both are the engine
        # refusing to approximate silently and both belong where the player is
        # already looking -- but running them together unlabelled would make a
        # standing property of the network read as something that just happened.
        blocks = list(view.reports)
        if snap.notices:
            plural = "" if len(snap.notices) == 1 else "s"
            blocks.append(f"--- from building the reaction network "
                          f"({len(snap.notices)} notice{plural}) ---")
            blocks.extend(snap.notices)
        _set_text(self.reports, "\n\n".join(blocks)
                  or "Nothing to report: no conservation residue, no capped "
                     "activity coefficient, no refused phase split, no latent "
                     "integration fragility, and the network was built to a "
                     "fixpoint with nothing dropped.")
        # ⚠ THE UNEXPLORED FRONTIER GOES IN THE HEADING RATHER THAN IN THE TEXT,
        # because it is a fact about the flask and not a note about it: one
        # generation showed what these species ARE and never what they would
        # become. Its notice is the last of possibly hundreds, so leaving it only
        # in the panel would put the one line that changes what the player should
        # do next below the fold. The control that LIFTS the bound is P4's; this
        # is the state that control exists to offer.
        self.reports_head.configure(
            text=REPORTS_HEAD if not snap.unexpanded else
            f"{REPORTS_HEAD}   [{len(snap.unexpanded)} species discovered and "
            f"not reacted further -- this flask has more to give]"
        )
        # ⚠ THE CONTROL SAYS WHICH BOUND IS IN FORCE, ALWAYS -- not only when
        # there is a frontier. "Built to a fixpoint" and "bounded at one
        # generation with nothing left over" are different states of the world
        # and a blank label would make them look the same.
        scenario = self.example.scenario
        if scenario.generations is None:
            self.further_label.configure(
                text="built to a FIXPOINT -- no bound to raise")
            self.further.state(["disabled"])
        else:
            capped = len(snap.species) >= scenario.max_species
            self.further_label.configure(
                text=f"bound: {scenario.generations} generation(s), "
                     f"{len(snap.species)} of at most {scenario.max_species} "
                     f"species"
                     + ("  <- THE CAP IS WHAT BIT, so this raises it too"
                        if capped else "")
                     + (f"  ({len(snap.unexpanded)} on the frontier)"
                        if snap.unexpanded else "  (frontier empty)")
            )
            self.further.state(["!disabled"])

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
    """Replace a Text widget's contents without throwing away the reader.

    ⚠ THE EARLY RETURN AND THE RESTORED SCROLL POSITION ARE BOTH LOAD-BEARING,
    and they became so the moment a panel here grew longer than its own height.
    This runs on every poll -- eight times a second -- so a bare
    delete-and-insert scrolls a reader back to the top before they can finish a
    sentence. The engine's reports are only worth carrying to the view if they
    can be read while the run they describe is still going.
    """
    if widget.get("1.0", tk.END).rstrip("\n") == text.rstrip("\n"):
        return
    top = widget.yview()[0]
    widget.delete("1.0", tk.END)
    widget.insert(tk.END, text)
    widget.yview_moveto(top)


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
            p = ev.get("payload", {})
            if ev["kind"] == "bottle":
                out.append(
                    f"bottle {ev.get('vessel', '')} as "
                    f"{p.get('name') or '(unnamed)'}"
                    + ("" if p.get("phase", "all") == "all"
                       else f"  [{p['phase']} only]")
                )
            elif ev["kind"] == "charge_stock":
                # ⚠ The line names the LABEL and what replays is the
                # COMPOSITION, which are deliberately not the same thing --
                # see ``events.CHARGE_STOCK``. So it says how much of what went
                # where and leaves the mole vector in the file.
                n = len(p.get("state", {}).get("n_liquid", {}))
                out.append(
                    f"pour   {p.get('fraction', 1.0):g} of the stock "
                    f"{p.get('label') or '(unnamed)'} into "
                    f"{ev.get('vessel', '')}  ({n} dissolved species)"
                )
            else:
                out.append(f"do     {ev['kind']} {ev.get('vessel', '')}")
    return "\n".join(out) or "(nothing yet)"


def _stock_line(stock) -> str:
    """One shelf row. ⚠ The purity is a LABEL and it says which basis it is on.

    ``GAME_DESIGN.md`` section 1: purity is derived for display and is never
    state. A wet crop is 50 mol% and 13 wt% water, so a bare percentage on a
    shelf row would be the one number that means neither -- and the count of
    what else is in the bottle is beside it because that is the thing a player
    actually has to reason about.
    """
    major = stock.major("mass")
    if not major:
        return f"{stock.name:<26.26}  (empty)"
    others = len(stock.amounts()) - 1
    return (
        f"{stock.name:<26.26} {stock.total:9.4g} mol {stock.state.T:7.1f} K  "
        f"{100.0 * stock.purity('mass'):6.2f} wt% {major:<18.18}"
        + (f" +{others}" if others else "")
    )


def launch(example_key: str = "flask") -> None:
    """Open the window. Blocks until it is closed."""
    root = tk.Tk()
    app = App(root, load(example_key))

    def shutdown() -> None:
        app.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", shutdown)
    root.mainloop()
