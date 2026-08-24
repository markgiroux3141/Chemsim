# Equipment catalogue — exhaustive inventory and feasibility

Companion to [EQUIPMENT_PLAN.md](EQUIPMENT_PLAN.md), which holds the architecture.
This file is the *list*: roughly every item that appears on a Nile Red bench or in
a university teaching lab, with what it costs us.

Status: **reference only, nothing implemented.** Written 2026-08-16.

---

## Feasibility legend

| Tier | Meaning |
|---|---|
| **A** | **Free now** — a preset over existing `Vessel` scalars. No new physics. |
| **B** | **Needs edges** (PLAN §5 / M1) — vessel↔vessel vapour, liquid, thermal flux. |
| **C** | **Needs phase-partition events** (M4) — split state by phase. Bookkeeping, not physics. |
| **D** | **Needs liquid–liquid equilibrium** (M5) — a second liquid phase in the state vector. |
| **E** | **Needs a solid↔gas flux** — *does not exist today*; solids only exchange with liquid. |
| **F** | **Needs a staged or spatial model** — N-stage columns, plate models, residence time. |
| **G** | **Blocked on a missing subsystem** — named per row (electrochemistry, adsorption, LHHW, solid-phase reactions, photochemistry). |
| **H** | **Instrument** — reads state, changes nothing. Cost is a property model, if any. |
| **X** | **Cosmetic** — no physics differentiator in our model. Can exist for flavour; will not change an outcome. |

Tiers are cumulative in the obvious way: a Dean-Stark trap marked **B+D** needs
both.

---

## 1. Containers and reaction vessels

| Item | Physically | Tier | Notes |
|---|---|---|---|
| Beaker | Open container, large `k_vent` | **A** | |
| Erlenmeyer / conical flask | Narrower neck, lower evaporative loss | **A** | |
| Round-bottom flask, 1-neck | | **A** | |
| RBF 2/3/4-neck | Container with N ports | **A** | Ports are bookkeeping (PLAN §3) |
| Pear / Florence flask | | **A** | Shape is cosmetic; only `volume` matters |
| Test tube, culture tube | | **A** | |
| Sealed tube / ampoule | `k_vent = 0` | **A** | Pressure builds correctly today |
| Vial, scintillation vial | | **A** | |
| Schlenk flask | Sidearm + stopcock | **A** | Inert fill already possible |
| Thick-walled pressure flask (Ace) | | **A** | Wants a burst-pressure policy — see PLAN §11 |
| Parr bomb / autoclave | High P, high `heat_capacity` | **A** | |
| Dewar flask | `UA ≈ 0` | **A** | |
| Crucible (porcelain, alumina) | Solid held at high T | **A** container / **G** chemistry | ⚠ **There are no solid-phase reactions** — see §14 |
| Evaporating / crystallising dish | Open, high surface area | **A** | Map area to `kla` |
| Watch glass, Petri dish | | **X** | |
| Graduated cylinder, volumetric flask | Measurement | **X** / **H** | |
| Microwave reaction tube | Volumetric heating | **A** | Just `Q_input`; we don't model penetration depth |

## 2. Heating and cooling

| Item | Physically | Tier | Notes |
|---|---|---|---|
| Hotplate, hotplate/stirrer | `Q_input` | **A** | |
| Heating mantle | `Q_input` + shape fit | **A** | |
| Silicone oil bath | `T_env` + `UA` + thermal mass | **A** | Bath as its own container is **B** and more honest |
| Water bath, sand bath | | **A** | |
| Ice bath, ice/salt bath | `T_env` = 273 / 253 | **A** | |
| Dry ice / acetone (−78 °C) | | **A** | |
| Liquid nitrogen (−196 °C) | | **A** | Most species freeze; check the fusion law doesn't misbehave |
| Immersion cooler / cryostat | | **A** | |
| Recirculating chiller | Feeds a condenser jacket | **A** / **B** | **B** for the honest version (thermal edge to the condenser) |
| Heat gun, Bunsen burner, torch | | **A** | Localised heating isn't modelled; it's just watts |
| Tube furnace | High-T gas-phase reactor | **A** + **B** | Equipment is easy; **the pyrolysis templates are the real work** |
| Muffle furnace | Calcination of solids | **G** | Blocked on solid-phase reactions |
| Ultrasonic bath | Accelerates dissolution | **A** | Multiplier on `k_diss` / `kla`. Defensible, not rigorous |
| **PID temperature controller** | Closed loop: set T, not watts | **A**+ | ⭐ **Small feature, disproportionate value.** An actuator whose `Q_input` is a function of measured `T`. "Hold at 80 °C" is what you actually want to write, not "apply 60 W". Build this in M3. |

## 3. Stirring and mixing

| Item | Tier | Notes |
|---|---|---|
| Magnetic stir bar + plate | **A** | `kla`, `k_diss` |
| Overhead stirrer | **A** | Higher `kla`; matters for viscous/heterogeneous |
| Vortex mixer, orbital shaker | **A** | |
| Homogeniser, static mixer | **X** | |
| Mortar and pestle, ball mill | **X** | No particle-size model. Could be a `k_diss` multiplier; be honest that it's a fudge |
| Sieves, boiling chips | **X** | Boiling chips are flavourful — we already superheat a dry flask, but bumping needs a nucleation model |

## 4. Atmosphere and pressure control

| Item | Physically | Tier | Notes |
|---|---|---|---|
| Septum + needle | | **A** | |
| Inert balloon (N₂ / Ar) | Headspace charge | **A** | ⭐ Meaningful today — the Phase-0 spike proved O₂ contamination sensitivity emerges |
| H₂ balloon | Dissolves via Henry | **A** | H₂ is in the PSRK gas set already |
| **Glovebox** | Ambient *is* argon; `ingress = 0` | **A** | ⭐ Free, and it genuinely changes outcomes |
| Schlenk line / vac-inert manifold | Alternating vacuum + inert | **A** / **B** | Crudely `set_vent` + `P_ambient` today; **B** for a real manifold |
| Vacuum pump (diaphragm, rotary vane) | Low `P_ambient` | **A** | Vent term already drives outflow |
| Vacuum manifold + cold trap | | **B** | Cold trap = a cold vessel on the line |
| Gas cylinder + regulator | Steady inflow | **A** / **B** | `ingress` today; **B** for a proper reservoir edge |
| Mass flow controller | Metered gas inflow | **B** | |
| Gas bubbler (oil, backflow guard) | | **X** | |
| **Gas washing bottle / Dreschel / scrubber** | Gas *through* a liquid | **B**+ | ⚠ Needs a small new inlet: `ingress` currently enters the **headspace**, not the liquid |
| Sparge tube / gas dispersion frit | Same | **B**+ | Same fix |
| Drying tube (CaCl₂, Drierite) | Solid sorbent in a gas path | **G** | Adsorption. Hackable as a hydrate-forming reaction — spike it |
| N₂ blowdown / inert sweep | Inflow + vent carries vapour out | **A** | ⭐ **May already work today**: `ingress` + composition-weighted vent |
| Needle valve, stopcock | | **A** | `k_vent` |
| Manometer, pressure gauge | | **H** | `pressure` exists |
| Rupture disk, blast shield | | — | Policy, not physics (PLAN §11) |

## 5. Condensers, distillation, evaporation

Everything here is unlocked by M1 edges. This is the densest payoff block.

| Item | Tier | Notes |
|---|---|---|
| Reflux condenser (Allihn, coil, Graham) | **B** | Cold vessel, vapour in, liquid back |
| Liebig condenser | **B** | |
| Air condenser | **B** | Just a poorer `UA` |
| Cold finger | **B** | |
| Distillation head, simple | **B** | |
| Still head + thermometer | **B**+**H** | The thermometer reading *is* the vapour composition readout |
| Vigreux column | **B** | 1–3 stages; fine as a single cold vessel |
| Packed fractionating column | **F** | N stages. Free-ish via N coupled vessels; HETP is the modelling choice |
| Reflux-ratio control head | **B** + control | |
| Cow / multi-receiver, fraction collector | **B** | |
| Vacuum takeoff adapter | **B** | |
| Short-path head, **Kugelrohr** | **B** | Vacuum + bulb-to-bulb |
| **Rotary evaporator** | **B** | Vacuum + bath + vapour edge + cold receiver. All four already exist bar the edge |
| **Steam distillation** | **B**+**D** | ⚠ The whole point is that immiscible liquids each exert full vapour pressure. One liquid phase with large γ gives *partial credit* — qualitatively right, quantitatively wrong. Honest version needs LLE |
| **Dean-Stark trap** | **B**+**D** | The trap works by *separating layers*. Same caveat |
| Sublimation apparatus (cold finger) | **E** | No solid↔gas flux exists |
| Molecular / wiped-film still | **F** | |
| Zone refining, fractional freezing | **E**/**F** | |

## 6. Extraction and liquid separation

Almost entirely gated on **D (LLE)**. This is the core-workflow block.

| Item | Tier | Notes |
|---|---|---|
| **Separatory funnel** | **D** | The single most-used item on the list |
| Aqueous workup (wash, brine, dry) | **D** | |
| **Acid–base extraction** | **D** | ⭐ Ions and pH already work — this is blocked on *nothing but* LLE |
| Continuous liquid–liquid extractor | **D**+**B** | |
| **Soxhlet extractor** | **B** + trigger | ⭐ **Feasible without LLE** — solid in a thimble, one solvent. The siphon is a root on "liquid level = siphon height", which PLAN §8's machinery gives you free. Very Nile Red |
| Salting out | **D** + electrolyte activity | Double-blocked (γ for ions is on the open-problems list) |
| Countercurrent extraction | **D**+**F** | |
| Centrifugal extractor | **D**+**C** | |

## 7. Filtration and solid handling

All cheap. **C** is bookkeeping, not physics — solids already exist.

| Item | Tier | Notes |
|---|---|---|
| Gravity filtration, fluted paper | **C** | |
| Büchner funnel + filter flask | **C** | Needs a retained-mother-liquor fraction to be honest |
| Hirsch funnel, sintered frit | **C** | |
| Cannula / filter-tipped transfer | **C**+**B** | |
| Centrifuge | **C** | Same partition, different retention |
| Decanting | **C** | |
| Washing a filter cake | **C** | |
| Trituration | **C**+**A** | |
| **Recrystallisation** | **works today** | Already demoed end-to-end in `examples/workshop.py`; **C** only to *isolate* the crop |
| Celite / filter aid | **X** | |
| Spatula, powder funnel, weighing paper | **X** | |

## 8. Drying

| Item | Tier | Notes |
|---|---|---|
| **Vacuum oven / vacuum drying** | **A** | ⭐ Already works — residual *liquid* solvent evaporates under low `P_ambient` |
| Air drying | **A** | |
| Vacuum desiccator (silica, P₂O₅) | **A** + getter | |
| Rotovap to dryness | **B** | |
| Drying agents (MgSO₄, Na₂SO₄) | **D**-adjacent | ⭐ Possibly nearly free — model hydrate formation as a reversible reaction. **Spike this before assuming it's hard** |
| Molecular sieves | **G** | Adsorption |
| Azeotropic drying (Dean-Stark) | **B**+**D** | |
| **Freeze dryer / lyophiliser** | **E** | Frozen solvent → vapour directly |

## 9. Chromatography and adsorption

The weakest block for us. All of it needs an adsorption isotherm, a stationary
phase, and usually a plate model.

| Item | Tier | Notes |
|---|---|---|
| TLC (as a *separation*) | **F** | |
| TLC (as an *instrument*) | **H** | Rf from logP. Needs a logP estimator (Crippen) — not currently in Layer 1 |
| Flash / gravity silica column | **F**+**G** | |
| Reverse phase, size exclusion | **F**+**G** | |
| Ion exchange | **F**+**G** | Plus electrolyte activity |
| HPLC, GC (as *separations*) | **F** | |
| GC, LC (as *instruments*) | **H** | Nearly free — see §12 |
| Activated carbon decolourising | **G** | |

## 10. Specialised reactors

| Item | Tier | Blocker |
|---|---|---|
| Electrolysis cell, divided cell, anodising | **G** | Electrochemistry. Already on the open-problems list; gates chlor-alkali, chlorates, plating, PEDOT |
| Photoreactor, UV lamp, blue LED | **G**, medium | Needs a non-Arrhenius rate hook: rate ∝ photon flux, not `A·exp(−Ea/RT)`. Hackable as `Ea = 0` with `A` set by intensity — workable, not honest |
| Ozone generator | **A**-ish | Feed O₃ via `ingress`; needs O₃ thermochemistry curated |
| **Hydrogenation, Pd/C or Raney Ni** | **G** | LHHW / heterogeneous catalysis |
| **Hydrogenation, homogeneous (Wilkinson's)** | **A** | ⭐ Works *today* — the coverage audit confirmed homogeneous catalysis needs no new machinery |
| Parr shaker hydrogenator | **G** | Same as Pd/C |
| Microwave synthesiser | **A** | |
| Flow reactor / CSTR cascade | **B** | ⭐ N vessels + flow edges *is* flow chemistry. Essentially free once edges exist |
| Plug-flow / microfluidic reactor | **F** | Needs residence-time distribution |
| Tube furnace pyrolysis under Ar | **B** | Equipment is easy; the radical templates are the work |
| Plasma reactor, mechanochemistry | **G** | |

## 11. Instruments and analysis

Cheapest high-value block in the whole document. See PLAN §9 for why.

| Instrument | Tier | Cost |
|---|---|---|
| Thermometer / thermocouple | **H** | exists (`T`) |
| pH meter, pH paper | **H** | exists (`pH`) |
| Balance / tare | **H** | exists (`state()`) |
| Boiling point | **H** | exists (`bubble_point`) |
| Pressure gauge | **H** | exists (`pressure`) |
| **Melting point apparatus** | **H** | ⭐ Nearly free, and **impurity-depressed, broadened mp falls out of the existing fusion law** |
| **GC-MS** | **H** | ⭐ Nearly free — composition + MW + retention ordered by `Tb`, all of which exist |
| Mass spec | **H** | Free — formula and isotope pattern from the molecular graph |
| **Elemental analysis (CHN)** | **H** | Free — straight from the formula |
| **Karl Fischer titrator** | **H** | Free — water is a state variable |
| Density meter | **H** | Free — molar volumes exist (`v_liq`) |
| Titration / burette | **H** | Works today; `workshop.py` already titrates acetic acid |
| Flash point | **H** | Nearly free from `Psat` |
| **IR / FTIR** | **H** | ⭐ Nearly free — group frequencies off the existing SMARTS fragmenter (`properties/fragmentation.py`) |
| NMR (¹H / ¹³C) | **H**, medium | Crude version: count environments via SMARTS. Real shift prediction is hard |
| **UV-Vis / colour** | **H**, medium | ⭐⭐ See §13 — the biggest "wanted but missing" item |
| Refractometer | **H**, medium | Needs a refractive-index estimator |
| Polarimeter | **H**, medium | Stereochemistry is already part of identity; optical rotation is not |
| Conductivity meter | **H**, medium | Needs ion mobilities |
| Viscometer | **H**, medium | Needs a viscosity model |
| Gas syringe / eudiometer / gas burette | **H** | Free — `nG` |
| Rotameter | **H** | Free once flow edges exist |

## 12. Bench miscellany — all **X**

Clamps, stands, bosses, Keck clips, cork rings, tubing, joint grease, parafilm,
stir-bar retriever, powder funnels, fume hood, PPE. Worth *rendering* for a game;
none of it changes a number.

---

## 13. Missing physics, ranked by equipment unblocked

The most useful output of this catalogue. Build in this order.

| # | Missing capability | Items unblocked | Effort |
|---|---|---|---|
| 1 | **Vessel↔vessel edges** (M1) | **~30** — every condenser, all distillation, rotovap, cold traps, Soxhlet, addition funnels, gas lines, flow reactors, tube furnace | Medium. Dominant win |
| 2 | **Liquid–liquid equilibrium** (M5) | ~10 — sep funnel, all workup, acid–base extraction, steam distillation, Dean-Stark | Large, but they're *core workflow* |
| 3 | **Phase-partition events** (M4) | ~8 — filtration, Büchner, centrifuge, decant, cake wash, isolating a crop | Small. Best effort:value ratio |
| 4 | **Instrument readouts** | ~12, of which 8 are nearly free | Small |
| 5 | **Adsorption isotherms** | ~7 — all chromatography, ion exchange, drying tubes, molecular sieves, decolourising | Large |
| 6 | **Non-Arrhenius rate hooks** (LHHW, photon flux) | ~6 — Pd/C hydrogenation, photochemistry, enzymes, packed beds | Medium; already on the open-problems list |
| 7 | **Electrochemistry** | ~5 — electrolysis, chlor-alkali, anodising, plating, conducting polymers | Large; already on the list |
| 8 | **Solid↔gas flux** | ~4 — sublimation, freeze-drying, cold-finger sublimator | **Small** — a genuine gap, cheap to close |
| 9 | **Solid-phase reactions** | ~3 — calcination, muffle furnace, thermal decomposition of solids | Medium. ⚠ Not previously flagged anywhere |
| 10 | **Staged/spatial models** | ~6 — fractionating columns, PFR, countercurrent, prep chromatography | Medium |
| 11 | **Optical properties (colour, Rf, n_D)** | ~5 instruments | Medium; see §14 |
| 12 | **Particle size / surface area** | Mortar, mill, sieve, dissolution-rate limits | Low value, mostly cosmetic |

### Two gaps found by writing this list

- **No solid-phase reactions.** `ReactionTemplate(phase=…)` accepts only
  `gas` / `liquid` / `any`, and the RHS calls `_phase_rates` on the liquid and gas
  blocks only. Anything that decomposes as a solid — calcination, most furnace
  chemistry — is currently unrepresentable. New, not on any existing list.
- **`ingress` enters the headspace, never the liquid.** Sparging, gas scrubbing,
  and bubbling a reagent gas through a solution all want a liquid inlet. Small fix,
  several items depend on it.

---

## 14. The thing this list makes obvious: **colour**

Every other gap is a process-chemistry gap. This one is a *presentation* gap, and
for a Nile Red-inspired project it may matter more than several items above it.

Half of what makes those videos watchable is a flask turning deep blue, or a
solution going from orange to colourless at an endpoint. We can compute yields,
pH, boiling points and crystal crops — and we cannot say what any of it looks like.

Feasibility is better than it sounds: a crude conjugation-length → λmax model,
driven by the SMARTS fragmenter that already exists, would get dyes and indicators
approximately right and everything else correctly colourless. It is a Layer 1
property estimator with **no architectural change** — it sits beside Joback,
behind the existing provider interface.

Recommend treating it as a first-class milestone rather than polish.

---

## 15. Recommended coverage set

The minimum that puts most of a Nile Red video in reach, in build order:

1. **M1 edges** — condensers, distillation, rotovap, Soxhlet, addition funnels, cold traps.
2. **Partition events** — filtration, Büchner, centrifuge, decanting. Cheap; completes recrystallisation into a full isolate-and-weigh loop.
3. **PID temperature controller** — tiny, and it's how procedures are actually written.
4. **The free instrument set** — GC-MS, mp, IR, density, KF, elemental analysis. This is the player's entire feedback loop, for very little work.
5. **LLE** — sep funnel and aqueous workup.
6. **Colour** — §14.

Rough estimate: that reaches **85–90 %** of what appears on screen in a typical
video. What stays out of reach after all of it: electrochemistry, column
chromatography, Pd/C hydrogenation, photochemistry, and solid-state furnace work.
