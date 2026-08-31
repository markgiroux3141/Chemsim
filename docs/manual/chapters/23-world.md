# Layer 6: the world, and what makes a run reproducible

The top of the stack, and the smallest layer in it. A `World` owns vessels and a
clock, applies player events at step boundaries, and can write itself to a dict
and read itself back. **It contains no chemistry**: every physical question is
delegated downward.

It exists to guarantee three properties.

## Headless

`step(dt)` is the entire interface. A real-time frontend calls it each frame, a
batch experiment calls it in a loop, a test calls it once. None of them are
privileged, and the engine has no opinion about rendering or wall-clock time.

## Deterministic

::: {.keypoint}
A run is a pure function of **(scenario, script)**.
:::

Player actions are **timestamped events** --- the only thing that may mutate a
vessel --- and they fire strictly *between* integrations.

```
CHARGE   SET_HEAT   SET_ENVIRONMENT   SET_VENT   SET_STIRRING
SET_SHAKING   FILL_HEADSPACE   TRANSFER   FILTER   ...
```

An event is instantaneous relative to the chemistry; interleaving it with the
solver's internal timesteps would make the outcome depend on the solver's
adaptive step size, which is precisely the non-determinism this design exists to
prevent.

Randomness --- for future stochastic effects --- comes from a single seeded
generator that is *itself saved*, so a reload continues the same stream rather
than starting a new one.

## `wait_until`: the verb that makes a recipe a recipe

::: {.keypoint title="A real procedure has no durations in it"}
"Heat until it refluxes." "Cool until crystals appear." "Distil until the pot
reaches 110 °C." "Stir until it all dissolves."

Not one of those is a time. A recipe written against fixed durations encodes the
wrong shape into every screen built on top of it.
:::

Every one of those is a **root of a function of the state**, located by
`solve_ivp` to solver tolerance, so the instant is **discovered** rather than
declared:

```python
out = w.wait_until("pot",    boils(),                     timeout=7200.0)
out = w.wait_until("beaker", crystals("OC(=O)c1ccccc1"),  timeout=14400.0)
out = w.wait_until("head",   temperature_steady(0.01),    timeout=3600.0)
out.elapsed     # how long it ACTUALLY took -- the clock moves by this
```

The sign convention is uniform and that is the whole contract:

$$ f(\text{state}) < 0 \ \Rightarrow\ \text{not yet}; \qquad
   f(\text{state}) \ge 0 \ \Rightarrow\ \text{satisfied}, $$

upward crossings only. Not cosmetic: with a direction flag per condition there
are two ways to write each one and one of them is silently backwards, and "is it
already true?" stops being a single comparison.

## Four conditions that are not what they look like

Each condition was **sampled along a real trajectory before it was
implemented** --- the same discipline that killed crystal occlusion in Chapter 9
--- and three of the four findings changed the vocabulary.

::: {.trap title="1. A derivative approaching zero is not a root"}
"The temperature has stabilised" is $\dd T/\dd t \to 0$, and it gets there
**asymptotically**: approached and never crossed, so `dT/dt == 0` would wait
forever.

What *is* a root is a **tolerance** on the derivative --- "the thermometer has
stopped moving" --- which is what a chemist actually means and is a number a
player can be given. Hence `temperature_steady(rate)` takes the rate, and there
is no zero-derivative form at all.
:::

::: {.trap title="2. An amount that starts at exactly zero LEAVES zero rather than crossing it"}
"Crystals appear" is $n_S$ departing from exactly 0. At $10^{-9}$ mol the
crossing is *inside* the solver's own atol. So the threshold is a **micromole**
--- three orders clear of atol and still far below anything a bench could see.

`SOLID_VISIBLE` is a **resolution limit, not a claim about nucleation**, and it
is labelled as one.
:::

::: {.trap title="3. A condition already true is not a root either"}
SciPy locates *sign changes*. "Wait until it is above 300 K" asked of a flask at
340 K would hang. Layer 4 checks before integrating and reports it as
already-satisfied.
:::

::: {.trap title="4. A rate tolerance fires on the first transient, not on the plateau"}
This one the probe was too coarse to see and a test caught instead. A flask
whose headspace has just been filled evaporates hard for a moment: $\dd T/\dd t$
starts at $-24$ K/s, crosses zero inside a second, and only *then* climbs to its
steady $+0.096$ K/s.

So `temperature_steady` on its own fires at 298 K rather than at the boil. The
fix is not in the code: **say what you meant** --- `boils()` first,
`temperature_steady()` after --- which is what a chemist does anyway.
:::

## The script, and why it stores conditions rather than instants

::: {.keypoint}
The determinism guarantee used to read "(scenario, **event list**)", and mending
that sentence was the deliberate half of adding `wait_until`. An event is an
*instant*; a wait is a *span whose end is discovered by a solver root*. The event
list alone no longer says when anything happened.

The **script** is the ordered record of everything asked of the world --- events
scheduled, intervals stepped, conditions waited on --- and it stores the
**condition** and never the instant it resolved to.
:::

The reason is a principle the project applies everywhere: *the instant is derived
data, and this project declines to store derived data beside its source.* A
`Scenario` keeps templates, not the network they generate; a script keeps
"until it boils", not "at $t = 1183.7$ s".

## Save and load

A save stores:

- the **scenario** --- templates as SMARTS text, feed species, vessel config;
- the **script** --- everything ever asked of the world;
- **moles and temperature**.

and never the derived network, which is rebuilt deterministically on load.

::: {.keypoint}
So a run is a pure function of (scenario, script), and `World.replay` re-runs one
from its recipe alone. Saves are small, readable JSON. No RDKit object is ever
serialised. The format is version-stamped and **refuses an incompatible reader
rather than mis-mapping fields** --- because the state vector will keep growing
as lower layers gain phases, and a save written today must fail loudly against a
future reader instead of silently shifting one block into another.
:::

The version has been bumped for real several times --- a second liquid layer, the
script, the apparatus, the dropping funnel's conditional drip (Chapter 22), and
the shelf below. Each time for the same reason: an older save would have *loaded
cleanly and meant something different*.

## The shelf: two verbs, and a stock is a composition

The loop a player actually plays is: take two things off a shelf, pour them into
a flask, do something, read what came out, put the result back on the shelf under
a name. Two verbs close it.

| | | |
|---|---|---|
| **`BOTTLE`** | vessel $\rightarrow$ shelf | name the current `VesselState` and store it |
| **`CHARGE_STOCK`** | shelf $\rightarrow$ vessel | pour a stored stock into a flask |

::: {.keypoint title="A stock is a VesselState, never (name, purity)"}
An inventory item is the full per-phase mole vector plus a temperature. Purity is
**derived** for display and is never state.

Two bottles honestly labelled "90 mol% ethanol" behave differently if one's 10%
is water and the other's is acetic acid --- measured, at 353 K for two hours: one
makes ethyl acetate and the other makes none. A purity scalar cannot tell them
apart, and every gate in the game design reads a composition.
:::

Three consequences fall out without any new physics.

**Impurities are carried individually and forever**, because they are simply *in*
the mole vector. A contaminant introduced in step 1 is still there in step 6, in
the amount arithmetic says, and the player can trace it back --- because a stock
also carries the **script that made it**, which is a recipe rather than a
transcript and therefore re-runs at a different scale.

**A stock can react in the bottle**, which nobody designed. It has a temperature
and a phase layout, so advancing one is an ordinary integration: wet aspirin
hydrolyses back to salicylic acid on a shelf, ether under air makes peroxides.
Shelf life is emergent from an inventory of compositions and a bag of nouns
cannot do it at any price.

**Bottling loses a film and a crust**, through the same two mechanics a pour
suffers, because bottling wets the glass. Had it moved matter perfectly it would
have been a loss-free transfer sitting beside a lossy one --- and
bottle-and-recharge would have been the cheapest route around holdup in the game.

::: {.trap title="The composition is inlined in the event; the label is not what replays"}
`CHARGE_STOCK` carries the mole vector in its payload and never looks the stock
up by name. A run is a pure function of (scenario, script), so a charge that
named an inventory entry would depend on something living outside both --- and
since two bottles labelled the same are not the same bottle, a recipe recording
the *label* would mean something else when replayed.

For the same reason `World.shelf` is a run's **output**: bottles land in it and
no event ever consumes from it. The player's persistent shelf lives above the
engine and draws itself down there.
:::

::: {.trap title="A replay used to drop a trailing event, and BOTTLE is one"}
`now` schedules for the current instant and events fire *between* integrations,
so an action taken after the last step --- which the original run applied with
`flush` --- was left sitting in the replayed world's queue. Measured on a
two-event script: `set_heat` 50 W gave the original `Q_input = 50.0` and the
replay `0.0`.

Pre-existing, and invisible for as long as it was because only a *trailing* event
can be affected: anything with a `step` after it is applied by that step.
"Bottle it and stop" is exactly a trailing event, so the shelf would have
replayed empty. `run_script` now flushes at the end, which is trajectory-neutral
and adds nothing to the script.
:::

::: {.trap title="A stock's provenance cannot be `the script as it stands`"}
The script runs **ahead of the event queue** --- entries are appended when an
action is *scheduled*. So the same run, bottled and then replayed, produced two
stocks with identical compositions to every digit and different provenances: the
replayed one carried the `charge_stock` that happened *afterwards*.

The recipe is therefore sliced at the entry that scheduled the bottling. A recipe
that includes what happened to a bottle after it was filled is not that bottle's
recipe, and reading the live script would have made the field depend on when the
queue was flushed rather than on what was done.
:::

## What this buys, concretely

Because `(scenario, script)` determines everything:

- **a replay reproduces a run exactly**, including what the player saw;
- **a bug report is a JSON file**, not a description;
- **a test can assert on a trajectory** rather than on an endpoint;
- **the UI's recipe panel is the artefact**, growing as the player works, rather
  than something assembled at Save time (Chapter 24);
- **a run can be re-run at a different solver tolerance** to see whether any of
  its numbers were resolution rather than chemistry --- which is exactly what
  the tolerance audit of Chapter 20 does.
