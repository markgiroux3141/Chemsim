## P2 -- `Stock` and the shelf: the two verbs that close the loop -- **DONE 2026-08-31**

    BOTTLE         vessel -> shelf     name the current VesselState and store it
    CHARGE_STOCK   shelf  -> vessel    pour a stored stock into a flask

Both are built, both are events, and `SAVE_VERSION` is **7**. `engine/stock.py`
is the new module: a `Stock` is a name, a `VesselState`, and the script that
made it; a `Shelf` is those by name in arrival order.

**A stock is a `VesselState`** (§1) -- a per-phase mole vector and a
temperature, never `(name, purity)` -- and that claim is now a MEASUREMENT rather
than a design note. Two bottles both honestly labelled "90 mol% ethanol", one's
10% water and the other's 10% acetic acid, charged into identical flasks at 353 K
for two hours: **the sour one makes 9.83e-02 mol of ethyl acetate and the wet
one makes 3.83e-11**, which is below the integrator's own per-component atol and six
orders down. A purity scalar cannot tell those two bottles apart.

Purity is DERIVED, and P2 found that deriving it is not one number:

⚠⚠ **A BARE PERCENTAGE ON A SHELF ROW IS THE ONE FIGURE THAT MEANS NEITHER.**
0.05 mol of benzoic acid wet with 0.05 mol of water is **50 mol% and 13 wt%**
water -- and worse, the BIGGEST COMPONENT of that bottle is water by mole and
benzoic acid by mass. So `major()` takes the basis as well as `purity()` does:
a major fixed on moles printed beside a purity quoted by mass reads *"water at
87 wt%"*, which is two true numbers making one false statement.

⚠ **BOTTLING LOSES A FILM AND A CRUST**, through `Vessel.withdraw` and the same
two mechanics a pour suffers, because bottling wets the glass. Had it moved
matter perfectly, BOTTLE would have been a loss-free transfer sitting beside a
lossy one and **bottle-and-recharge would have been the cheapest route around
holdup in the game.** Cross-checked the other way too: bottling a hot flask and
charging the stock into a cold one gives the same moles and the same final
temperature, to 1e-12, as pouring one flask into the other.

⚠ Impurities are carried individually and forever, which is the whole loop --
measured over three steps at half scale each, the 0.02 mol of water charged in
step 1 is 0.005 mol in the third bottle and the bottle's own script says where it
came from. And **a stock can react in the bottle**, which nobody designed: it has
a temperature and a phase layout, so advancing one is an ordinary integration.

### Three findings, two of them pre-existing bugs

⚠⚠⚠ **A REPLAY DROPPED A TRAILING EVENT, AND "BOTTLE IT AND STOP" IS ONE.**
`now` schedules for the current instant and events fire BETWEEN integrations, so
an action taken after the last step -- which the original run applied with
`flush` -- was left sitting in the replayed world's queue. Measured on a
two-event script: `set_heat` 50 W gave the original `Q_input = 50.0` and the
replay **0.0**, with one event still pending. Pre-existing, and invisible for as
long as it was because only a TRAILING event can be bitten: anything with a
`step` after it is applied by that step. *P2 would have shipped a replay with an
empty shelf.* `run_script` now flushes at the end, which is trajectory-neutral
and adds nothing to the script.

⚠⚠ **A STOCK'S PROVENANCE CANNOT BE "THE SCRIPT AS IT STANDS", BECAUSE THE
SCRIPT RUNS AHEAD OF THE EVENT QUEUE.** Entries are appended when an action is
SCHEDULED. The same run, bottled and then replayed, produced two stocks with
identical compositions to every digit and DIFFERENT provenances -- the replayed
one carrying the `charge_stock` that happened afterwards. So the recipe is sliced
at the entry that scheduled the bottling: a recipe that includes what happened to
a bottle after it was filled is not that bottle's recipe, and reading the live
script would have made the field depend on when the queue was flushed.

⚠⚠ **THE UI'S FILTER BUTTON DISCARDED THE WHOLE FLASK, SILENTLY, AND HAS SINCE
IT EXISTED.** It sent `to=` and the FILTER event reads `filtrate` and `cake`, so
the vessel picked in the dropdown received nothing and both streams were binned.
Measured on a 1 mol charge: *"filter flask: cake 0.0000 mol solid + 0.0000 mol
liquor -> discarded; filtrate 1.0000 mol -> discarded"* -- which is the engine's
own `transfer_log` saying exactly what happened, on a channel nothing in the view
was reading. **The refluxing rig's 0.34 mol of air again, one panel over.** Fixed
with two destination pickers, since a filtration has two streams. ⚠ And the
Transfer tab's `"all"` phase, offered since the first commit, was never
implemented -- `pour_into` raised on it. Implemented, because BOTTLE needs the
same word: the contents of the flask and NOT its headspace, because a bottle
brings its own air.

### And what P1 handed over: `generations` is a `Scenario` field now

`World.__post_init__` called `build_network` with no `generations`, so a world
always built to a fixpoint and **nothing could request one-generation play
through the UI at all** -- `Snapshot.unexpanded` was correct and permanently
empty. It is a field, a `to_dict`/`from_dict` pair that keeps `None` as `None`
(`int(...)` would raise and a default of 0 would build an EMPTY network), and it
reaches the snapshot: a `generations=1` session leaves ethyl acetate on the
frontier and says so in a notice. **P4's "react further" control now has both a
state to offer and a bound to lift.**

Suite **1202 -> 1227 tests, 0 failed in 29:23**. `tolerance_audit.py` is NOT owed: P2
touched no RHS, no data table and no network construction -- `generations` is
plumbed THROUGH `build_network`'s existing argument and changes nothing when it
is `None`, which is every existing scenario.
