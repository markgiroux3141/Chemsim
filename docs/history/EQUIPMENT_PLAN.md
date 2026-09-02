# Equipment & Experiment Protocol — design plan

Status: **plan only, nothing implemented.** Written 2026-08-16 against the tree at
275 tests / Layers 0–6 complete. No existing file was modified to produce this.

Purpose: define the equipment model and the experiment-authoring interface so a
later session can build it without re-deriving the analysis. Read
`chemsim-architecture` / `chemsim-status` memory first for the layer rules this
plan obeys.

Deliberate non-goal: ease of use. This targets *expressive power and honesty* —
being able to set up any apparatus in the ambition list and run it. A friendlier
GUI comes later and consumes the same data format (see §7).

---

## 1. What exists today

Worth stating precisely, because the gap is smaller than it looks.

`Vessel` ([src/chemsim/vessel/vessel.py:246](src/chemsim/vessel/vessel.py#L246)) is
one generic container. Every piece of "equipment" is currently a scalar on it:

| Real thing | Today |
|---|---|
| Hotplate / mantle | `Q_input` (W) |
| Ice bath, oil bath, the room | `T_env` + `UA` (W/K) |
| Stirrer | `kla` (mol/bar·s, gas↔liquid mass transfer) |
| Stopper / vent / septum | `k_vent` — conductance **to ambient only** |
| Vacuum line | `P_ambient` — a free parameter nobody has turned down |
| Leaking joint / gas sparge | `ingress` (mol/s per species into headspace) |
| The glassware itself | `heat_capacity` (J/K) |
| Beaker vs. RBF vs. autoclave | nothing but `volume` |
| Condenser, funnel, column, trap | **absent** |

Vessels in a `World` are **completely uncoupled**. `World._advance`
([src/chemsim/engine/world.py:185](src/chemsim/engine/world.py#L185)) steps each
one independently; the only interaction is the `TRANSFER` event calling
`pour_into`, an instantaneous discrete move of a fraction of one phase.

Also true and load-bearing:

- **All vessels share one reaction network.** `World.__post_init__`
  ([world.py:78](src/chemsim/engine/world.py#L78)) builds a single network from
  `scenario.feed_species`; `pour_into` refuses vessels whose species lists differ
  ([vessel.py:388](src/chemsim/vessel/vessel.py#L388)). **Keep this invariant** —
  it makes every vessel's state block the same shape, which §4 depends on.
- **The network is derived, never saved.** A save holds templates + moles and
  rebuilds. Any rig format must follow the same rule.
- The RHS ([numerics/vessel_integrator.py:350](src/chemsim/numerics/vessel_integrator.py#L350))
  already contains, per vessel: liquid/gas reaction, Raoult+Henry evaporation
  with UNIFAC γ, dissolution/melting, venting, and a full energy balance with
  latent heat. **The physics a condenser needs is already written.** What is
  missing is a way for two vessels to see each other.

---

## 2. Taxonomy: equipment is four kinds of thing, not a class hierarchy

Resist a `Condenser` class. A condenser is *a cold vessel with a vapour inlet and
a liquid outlet*. Everything decomposes into:

1. **Containers** — own state (`nL | nG | nS | T`). Flasks, beakers, traps,
   receivers, funnels, columns, condensers. All are `Vessel` + parameters + ports.
2. **Connections** — carry flux between containers, or between a container and a
   reservoir. Vapour paths, liquid paths, thermal contact. **This is the one new
   physical concept in the whole plan** (§5).
3. **Actuators** — write a container's boundary conditions. Mantles, baths,
   stirrers, vacuum pumps, gas cylinders. Almost all already exist as scalars;
   they just need names and an attachment model.
4. **Instruments** — read state, change nothing. Thermometer, pH meter, balance,
   TLC, GC, mp apparatus. Nearly free, and see §8 — they are the most valuable
   cheap thing on this list.

An equipment *item* is therefore: a `VesselSpec` (or a set of condition
overrides) + a list of typed ports + a display name. **Data, not code** — the same
shape as `ReactionTemplate` and `VesselSpec`.

---

## 3. The port model

A port is `(kind, id, height)`.

- `kind ∈ {vapour, liquid, thermal, solid, electrical}` — validated strictly. A
  liquid line may not be joined to a thermal jacket.
- Real ground-glass sizes (14/20, 19/22, 24/40) can ride along as an advisory
  `size` field. **Do not enforce it yet**; it is realism, not physics, and it will
  only obstruct experimentation.
- `height` (m, relative to the container's base) is reserved. Gravity drain,
  Dean-Stark's decanting arm, and "the condenser is above the flask" all genuinely
  depend on levels. **Phase 1: ignore it and declare edge direction explicitly.**
  Do not silently fake it — an edge either states its direction or it is
  pressure-driven.

A three-neck flask is a container with three `vapour|liquid` ports. That is the
entire difference from a one-neck flask. Pure bookkeeping, no physics.

---

## 4. The architectural decision: one coupled state vector

**Coupled vessels must be integrated as ONE stiff system.** This is not an
optimisation — it is the same principle the vessel integrator's docstring already
states ("all in ONE stiff system, so the feedback loops are resolved by the solver
rather than smeared across an outer stepping loop").

Reflux *is* such a feedback loop: boil → vapour rises → condenses → returns →
reboils, with latent heat coupling the two temperatures. Operator-splitting that
across two independently-stepped vessels at `dt = 1 s` smears the loop and makes
the answer depend on `dt`, destroying the determinism guarantee Layer 6 exists to
provide.

So: **a new Layer 4 module, `numerics/rig_integrator.py`.**

```
y = [ vessel_0 (3n+1) | vessel_1 (3n+1) | ... | vessel_{m-1} (3n+1) ]
```

Uniform blocks, because all vessels share one network (§1). Construction:

- Reuse the existing per-vessel RHS **unchanged** for the diagonal blocks. Factor
  `make_rhs` so the body can be called on a slice; do not rewrite it.
- Add edge terms that write into two blocks each.
- Stay **pure numpy** — this is still the Rust/PyO3 seam. Edges arrive as index
  arrays + coefficient arrays, exactly like `KineticArrays.phase` splits
  reactions at setup. No dicts, no vessel objects, no branching in the RHS.

### Performance note — do this from the start

For `n=20` species and `m=4` vessels the state is 244 long. BDF's default dense
`num_jac` costs ~245 RHS evaluations per Jacobian; at ~200 µs each that is ~50 ms
per Jacobian. Pass **`jac_sparsity`** to `solve_ivp`. The structure is known
exactly at setup: each vessel block is dense within itself, and off-diagonal
entries exist only where an edge connects. This is cheap to build and turns the
cost back into something linear-ish in `m`.

### Where things live

Extending the existing strict-downward chain:

```
matter(0) → properties(1) → reactions(2) → network(3) → numerics(4)
  → discovery(4.5) → vessel(5) → equipment(5.5) → engine(6) → protocol(7)
```

| New module | Layer | Contents |
|---|---|---|
| `numerics/rig_integrator.py` | 4 | Block state vector, edge flux kernels, `jac_sparsity`. Arrays only. |
| `vessel/rig.py` | 5 | `Rig`: vessels + edges → assembles the Layer 4 arrays. The `build_phase_arrays` analogue for topology. |
| `equipment/` | 5.5 | Preset catalogue. Data: params + ports per item. |
| `protocol/` | 7 | Authoring API, `Protocol` document, trigger conditions, runner. |

`Vessel` keeps working standalone. A one-vessel `Rig` must reproduce current
results bit-identically — make that a test, it is the cheapest possible guard
against regressing the whole Layer 5 result set.

---

## 5. Edge types and their laws

### 5.1 Vapour edge

Generalise the existing vent term
([vessel_integrator.py:437](src/chemsim/numerics/vessel_integrator.py#L437)) from
"to ambient" to "to another headspace":

```
flux_i = k_edge · (P_A − P_B) · x_gas,i(donor)
```

signed, with **upwind** composition — the gas that moves carries the composition
of whichever side it left. Ambient becomes a degenerate edge with a fixed-pressure,
fixed-composition far end, so `k_vent` collapses into the same code path rather
than remaining a special case.

### 5.2 Liquid edge

Two flavours, and both are needed:

- **Gravity / pressure driven** — drain-back from a condenser, a running still
  head. `flux = k · max(level_A − level_B, 0)` in the simple version, or just
  "everything that condenses returns" for a reflux edge.
- **Metered** — dropping funnel, syringe pump, peristaltic. A *prescribed* molar
  rate over a time window. This is the important one: **slow addition to control
  an exotherm is a real technique and chemsim would reproduce it emergently** —
  dropwise keeps the vessel controlled, dumping it in runs away. Cheap, and one of
  the best demos available.

### 5.3 Thermal edge

`UA` between two containers instead of to `T_env`. Jackets, cooling water,
condenser coolant, a flask sitting in a bath. Trivially an extension of the
existing `q_loss` term.

### 5.4 Enthalpy transport — do not forget this

Venting to ambient does not currently need an explicit enthalpy term (gas leaves
at `T`, and shrinking `Cp_total` accounts for it correctly). **An edge into
another vessel does.** The receiver needs

```
dT_B += Σ_i flux_i · Cp_i(T_A) · (T_A − T_B) / Cp_total,B
```

Without it, hot vapour entering a cold condenser is a free lunch.

Note what you get for free once this exists: vapour enters the cold condenser,
`evap` goes negative because `p > p_eq` at that temperature, `q_vap` flips sign
and *releases* latent heat, and the thermal edge to the coolant carries it away.
**Reflux thermodynamics emerges from code that is already written.**

### 5.5 The numerical warning — the lesson this codebase already learned twice

`DRYOUT_MOLES` and `MELT_BLEND` both exist because **a hard switch in the RHS is a
discontinuity BDF cannot step across.** Edges will tempt you into exactly that
mistake: upwind composition flips discretely at `P_A == P_B`, so the per-species
flux is C⁰ but not C¹ there, and a naive `if P_A > P_B:` is worse.

Blend the upwind weight smoothly (a sigmoid in `ΔP` over a small pressure scale),
the same way `wet` blends the dry-flask law. Budget debugging time for this; it
will not be optional.

---

## 6. Equipment inventory

> **The exhaustive item-by-item catalogue lives in
> [EQUIPMENT_CATALOG.md](EQUIPMENT_CATALOG.md)** — ~110 items across containers,
> heating, atmosphere, distillation, extraction, filtration, drying,
> chromatography, specialised reactors and instruments, each with a feasibility
> tier, plus missing physics ranked by how many items it unblocks. The summary
> below is kept for orientation.

Ranked by what each costs. Anything in the first two blocks is reachable in the
first two milestones.

### Free today — presets over existing parameters, zero new physics

| Item | Realisation |
|---|---|
| Beaker / Erlenmeyer / RBF / vial / test tube | `volume`, `heat_capacity`, `k_vent` (open = large, sealed = 0) |
| Hotplate, heating mantle | `Q_input` |
| Oil / water / ice bath, dry-ice acetone, cryostat | `T_env` + `UA` |
| Magnetic stirrer, overhead stirrer | `kla` (and arguably `k_diss`) |
| Vacuum pump | low `P_ambient` — the vent term already drives outflow |
| Inert atmosphere (N₂/Ar) | charge headspace instead of `fill_headspace_with_air` |
| Gas sparge / bubbler | `ingress` (currently into headspace; into the liquid is a small fix) |
| Sealed tube, autoclave, pressure reactor | `k_vent = 0` + heat capacity + `volume` |
| Thermometer, pH meter, balance | already readouts: `T`, `pH`, `state()` |

### Unlocked by edges (§5) — no further physics

Reflux condenser · Liebig / Graham / cold finger · distillation head + receiver ·
cow / multi-receiver · vacuum takeoff adapter · cannula transfer · gas line from a
cylinder · multi-neck flask · **dropping funnel / syringe pump** ·
**rotovap** (vacuum + bath + vapour edge + cold receiver) · Dean-Stark (partly —
see LLE caveat) · fractionating column as *N* coupled stages.

**Distillation is the milestone-1 demo.** It needs nothing beyond a vapour edge
and a cold vessel, and the vapour composition is already right — the 71 %-ethanol
vapour and the x=0.888 azeotrope both emerge from `PhaseArrays` + UNIFAC. A still
that finds the azeotrope by itself, with no azeotrope table anywhere, is the
single best demonstration this project can produce.

### Moderate — new bookkeeping, contained

| Item | What it needs |
|---|---|
| Büchner / gravity filtration | Partition the state by phase: solid → cake, liquid → filtrate, with a retained-mother-liquor fraction. Instantaneous relative to chemistry ⇒ it is an **event**, not an edge. Fits the existing model. |
| Decant, wash a cake, dry in vacuo | Same machinery as filtration + an existing vacuum. |
| Fractionating column | *N* stages via edges is free; the modelling choice is HETP / stage count. |
| Centrifuge | Same partition as filtration, different retention. |
| **Sublimation / freeze-drying** | ⚠ **Genuine gap found while reading the RHS: there is no solid↔gas path at all.** Solid exchanges only with liquid via the `solute` term. A direct flux needs adding. Freeze-drying and iodine sublimation are blocked on it. |

### Hard — real new physics

| Item | Blocker |
|---|---|
| **Separatory funnel, extraction, washing** | **Liquid–liquid equilibrium.** State grows to `[nL1 \| nL2 \| nG \| nS \| T]`; needs a phase-stability test (tangent-plane / flash) to decide when a second liquid phase exists. **UNIFAC already supplies γ, so this is reachable rather than blocked** — but it touches the integrator and the whole Layer 5 assembly. Highest-value hard item by a distance: "wash, extract, separate the layers, dry" is most of practical organic chemistry and most of what makes a Nile Red video look like one. |
| Drying agent (MgSO₄, Na₂SO₄) | Possibly nearly free — model hydrate formation as an ordinary reversible reaction on a solid. Worth a spike before assuming it is hard. |
| Packed bed / supported catalyst (Pd/C, Raney Ni) | Needs LHHW. Already on the open-problems list. |
| Electrolysis cell, electroplating | Needs electrochemistry. Already on the list. |
| Chromatography column, TLC as a *separation* | Needs a spatial/plate model. Defer. (TLC as an *instrument* is free — see §8.) |
| Photochemical reactor | Photon flux as a rate term; not hard, but no rate-law hook exists. |

---

## 7. Setting up and running an experiment

### The decision: a Python builder that emits a declarative document

Three options were considered — bare Python API, declarative YAML/JSON, or a
parsed mini-DSL. **Take the first two together and skip the third.** You script in
Python (loops, parameter sweeps, no parser to write, full debugger) and what it
*builds* is plain serializable data.

This is not a compromise, it is the pattern the codebase already uses twice:
`Scenario` is declarative data that rebuilds a network deterministically, and
`Event` is "a timestamped, serializable intention". A `Protocol` is the same idea
extended over topology and time:

```
Protocol = Rig (containers + edges + actuators)  +  Steps (ordered, timed)
```

Writing a real DSL buys nothing Python does not already give, and costs a parser,
an error-reporting story, and an editor mode.

### Sketch

```python
from chemsim.protocol import Protocol, minutes, hours
from chemsim import equipment as eq

p = Protocol("fischer-reflux")

# Every species that will EVER appear must be declared up front — the network is
# built once, from this list plus the templates. See the gotcha below.
p.reagents("CC(=O)O", "CCO", "O")
p.templates(FISCHER)

flask  = p.add("flask",  eq.RoundBottom(volume=0.5, necks=3))
cond   = p.add("cond",   eq.RefluxCondenser(coolant_T=288.0))
mantle = p.add("mantle", eq.HeatingMantle(max_watts=150))

p.connect(flask.top, cond.bottom)     # vapour up, condensate back down
p.attach(mantle, flask)               # thermal

p.charge(flask, {"CC(=O)O": 3.0, "CCO": 3.0})
p.set(mantle, watts=60)
p.until(flask.refluxing)              # solver root — not a guessed time
p.hold(hours(2))
p.set(mantle, watts=0)
p.until(flask.T < 313.0)
p.transfer(flask, receiver, fraction=1.0)

result = p.run()                      # → trajectory + final state + a log
```

`p.save()` emits the equivalent YAML/JSON. A future GUI emits that document
directly and never needs to generate Python. That is the whole point of the split.

### Two distinct step kinds

Do not conflate them:

- **Instants** — `charge`, `set`, `transfer`, `filter`, `sample`. These are today's
  events, applied strictly between integrations. Unchanged.
- **Spans** — `hold(t)`, `ramp(mantle, 0→150 W, over=minutes(20))`,
  `add_over(funnel, flask, minutes(30))`. These *modify the RHS* for a duration.
  A metered liquid edge with an on-window is exactly this. Needs a small amount
  of new machinery: a time-varying condition, evaluated inside the RHS, kept
  continuous.

### ⚠ Gotcha: reagents must be declared before they are added

`World` builds one network from `feed_species`. A reagent poured in at t = 2 h
must still appear in that list at t = 0, or its species index does not exist. The
protocol format therefore needs a `reagents:` section **separate from** the steps
that add them. Make the error message say this explicitly — it will be hit
constantly otherwise.

### ⚠ Gotcha: rig changes are expensive, step changes are not

Network construction is the slow part (seconds, for anything polymerising). Adding
a container or an edge is cheap; adding a *reagent* means a rebuild. Structure the
API so `p.run()` is the explicit commit point — ComfyUI's "Queue Prompt" button is
honest design here, not a wart.

---

## 8. Triggers: `until(...)` via solver root-finding

This is the sharpest idea in the plan and the one most worth getting right.

Real procedures are conditional: "heat until reflux, then hold 2 h", "add dropwise
keeping T below 30 °C", "stop when gas evolution ceases". Absolute timestamps
cannot express any of it — you do not know in advance when it will boil.

The naive fix is a predicate checked at step boundaries. **Reject it.** It makes
the outcome depend on `dt`, which is precisely what
[events.py](src/chemsim/engine/events.py#L1) was designed to prevent.

The correct fix already exists in scipy: **`solve_ivp(events=..., terminal=True)`
locates a root of a scalar function of state, to solver tolerance, independently
of `dt`.** A trigger becomes a root function:

| Condition | Root function |
|---|---|
| `flask.refluxing` | `Σ p_eq(nL, T) − P_ambient` |
| `flask.T > 353` | `T − 353` |
| `flask.pH < 7` | `pH − 7` |
| gas evolution ceased | `d(Σ nG)/dt − ε` |
| solid fully dissolved | `nS,i − ε` |

The runner then applies the step and resumes from the located instant. This
preserves the determinism guarantee *exactly* — it extends "events fire strictly
between integrations" so that the **instant is discovered rather than declared**.
It is entirely in the spirit of the existing design, and scipy does the hard part.

Build `Probe` / `Condition` objects so `flask.T < 313` returns a condition rather
than a bool — a ~30-line expression builder, and it makes the protocol read like a
procedure.

---

## 9. Instruments — cheapest high-value item on the list

Instruments read state and change nothing, so they cost almost nothing. Several
already exist (`pH`, `bubble_point`, `concentrations`, `describe`). They are worth
building out early for two independent reasons:

1. **Validation.** A "GC" readout — normalised liquid-phase composition of the
   species above a threshold — is directly comparable to literature yields. That
   is the `validation/equilibria.py` harness generalised to whole procedures.
2. **It is the eventual game.** You should not be able to read the full species
   dict. You should have to run a TLC, take an NMR, or check a melting point to
   find out what you made — and a wrong answer should be *interpretable*, not
   hidden. Impurity showing up as a depressed, broadened mp is free: `Tm` and the
   solubility law are already there.

Cheap ones: thermometer, pH meter, balance/tare, mp apparatus, GC/MS (composition
+ MW), TLC (a retention proxy from logP — crude but fine), IR (functional groups
via the existing SMARTS fragmenter — genuinely nearly free, `properties/fragmentation.py`
already does the matching).

---

## 10. Milestones

**M1 and M2 touch disjoint files and can proceed in parallel** (M1 is Layers 4–5,
M2 is Layer 6–7). Relevant given concurrent sessions.

### M1 — Rig and the coupled integrator  ⟵ *the load-bearing one*
`numerics/rig_integrator.py`, `vessel/rig.py`. Block state vector, `jac_sparsity`,
vapour + liquid + thermal edges, enthalpy transport, smooth upwinding.
**Test first: a one-vessel rig reproduces current results bit-identically.**
Unlocks reflux, distillation, rotovap, dropwise addition, cannula.
**Demo: a still that finds the ethanol/water azeotrope with no azeotrope table.**

### M2 — Protocol layer
`protocol/`. Builder API, serializable `Protocol` document, `Probe`/`Condition`,
solver-root `until(...)`, spans (`hold`/`ramp`/`add_over`), run + trajectory log.

### M3 — Equipment catalogue
`equipment/`. Presets for everything in §6's first two blocks. Mostly data.
Realistic default parameters are the actual work — a 250 mL RBF's heat capacity,
a Liebig's UA, a mantle's wattage.

### M4 — Solid handling
Filtration, decant, wash, dry. Partition events, no new physics. Plus the
solid↔gas flux if sublimation is wanted.

### M5 — Liquid–liquid equilibrium
Sep funnel, extraction, washing. The big one. Scope it properly before starting;
it changes the state vector.

### M6+
Column stages · chromatography · LHHW + packed beds · electrochemistry · photochemistry.

---

## 11. Open questions

- **Column stage count.** *N* coupled vessels is free but arbitrary. Tie it to
  HETP and a declared column length, or let the user set stages directly?
- **Geometry and levels.** Deferred in §3. Dean-Stark, gravity drain, and "did the
  flask overflow" all want it. How far can we get before it becomes dishonest?
- **Is a Rig's shared network still right?** One network across a 6-piece rig means
  every species exists everywhere, including a condenser that will only ever see
  two of them. Cheap in memory, but it inflates every block of the state vector.
  Measure before optimising; per-vessel species subsets would be a large change.
- **Does `k_vent` survive?** §5.1 folds it into a degenerate edge. Cleaner, but it
  is a public field on `Vessel` and in save format v2. Decide whether to keep it as
  an alias or bump `SAVE_VERSION`.
- **Protocol failure semantics.** What does a rig do when it is wrong — pressure
  past the glass rating, a flask overflowing, a sealed vessel heated? Currently
  pressure just rises. Failure modes are the *fun*, but they need a policy.
- **Drying agents as hydrate reactions** — spike this early; it may collapse a
  "hard" item into a template.
