# A map from ideas to files

Sizes are lines, as a rough guide to where the weight is.

## `src/chemsim` --- the engine (about 46,000 lines)

### Layer 0 --- `matter/`

| file | lines | what |
|---|---:|---|
| `molecule.py` | 263 | molecular graphs, canonical identity, the RDKit boundary |

### Layer 1 --- `properties/`

| file | lines | what |
|---|---:|---|
| `physical_data.py` | 13,736 | **generated.** Measured $T_b$/$T_c$/$P_c$/$V_c$, 1,239 species |
| `benson_data.py` | 2,413 | **generated.** Benson group values from RMG |
| `unifac_data.py` | 1,520 | UNIFAC groups and the interaction matrix |
| `mineral_data.py` | 940 | **generated.** Ionic lattices on the solid basis |
| `solid_state.py` | 922 | reactions *inside* a crystal (the affinity form) |
| `thermochemistry.py` | 853 | the provider: tiers, refusals, provenance |
| `benson.py` | 818 | Benson group additivity |
| `psrk_data.py` | 782 | PSRK's gas extension to UNIFAC |
| `ion_data.py` | 684 | **generated.** Aqueous ions on the conventional scale |
| `surface.py` | 641 | a gas reacting *at* a crystal's surface |
| `element_data.py` | 492 | **generated.** The elements; the floor every chain stands on |
| `electrolyte.py` | 488 | pKa-anchored ions, and pH as ordinary chemistry |
| `dielectric_data.py` | 477 | permittivities and Born radii |
| `critical.py` | 472 | Wilson--Jasperson, Fedors, Lee--Kesler |
| `dielectric.py` | 448 | the Born transfer term |
| `volatility.py` | 437 | Antoine, and Henry through the same array |
| `formation_data.py` | 367 | curated $\Delta H_f$/$\Delta G_f$, in both standard states |
| `condensed.py` | 343 | Rackett molar volume, Rowlinson--Bondi liquid $C_p$ |
| `solubility_product.py` | 306 | $K_{\mathrm{sp}}$ from two tables on one basis |
| `unifac.py` | 280 | the parameter block, not the evaluation |
| `fragmentation.py` | 262 | the shared greedy priority matcher + search fallback |
| `standard_state.py` | 244 | ideal gas $\to$ liquid |
| `joback.py` | 121 | Joback group contribution |
| `joback_data.py` | 111 | the Joback table |

### Layer 2 --- `reactions/`

| file | lines | what |
|---|---:|---|
| `synthesis.py` | 2,626 | the named-route template library |
| `library.py` | 845 | the curated templates the engine was built on |
| `template.py` | 563 | `ReactionTemplate`: SMARTS + kinetics + every declaration |
| `hammett.py` | 450 | ring deactivation, on the $\sigma^+$ scale |
| `thermo.py` | 434 | reaction $\Delta H$/$\Delta G$/$K$, and detailed balance |
| `electrochemistry.py` | 301 | four whole-cell templates |
| `reaction.py` | 75 | `ConcreteReaction` |

### Layer 3 --- `network/`

| file | lines | what |
|---|---:|---|
| `builder.py` | 711 | discovery, conservation checks, `KineticArrays` |

### Layer 4 --- `numerics/`

| file | lines | what |
|---|---:|---|
| `vessel_integrator.py` | 3,103 | **the flask.** The $4n{+}1$ RHS, every term |
| `rig_integrator.py` | 708 | several coupled vessels as one system |
| `lle.py` | 369 | the phase-split decision (Michelsen tangent plane) |
| `activity.py` | 360 | UNIFAC + Born evaluation, per RHS call |
| `jacobian.py` | 227 | one bound SciPy lacks |
| `integrator.py` | 96 | the isothermal mass-action kernel |

### Layers 4.5--7

| file | lines | what |
|---|---:|---|
| `vessel/vessel.py` | 2,563 | assembly, reporting, `pour_into`, `filter_into` |
| `engine/world.py` | 1,040 | the stepper, the script, save/load |
| `ui/session.py` | 579 | the worker thread; no widgets |
| `ui/app.py` | 572 | the Tkinter view; never calls the engine |
| `vessel/conditions.py` | 359 | the `wait_until` vocabulary |
| `vessel/rig.py` | 343 | glassware as a graph |
| `ui/examples.py` | 240 | four worked starting points |
| `discovery/refine.py` | 183 | rate-based network refinement |
| `recipes.py` | 181 | curated preparations, as data |
| `engine/scenario.py` | 168 | what a save contains |
| `engine/events.py` | 108 | the only things that may mutate a vessel |

## `data/catalog/` --- the coverage corpus

| file | what |
|---|---|
| `compounds/*.psv` | 1,583 compounds: id, name, SMILES, class, role, domains |
| `routes.psv` | 173 route headers |
| `route_steps.psv` | 377 steps, each with a mechanism class |
| `COVERAGE_REPORT.md` | **generated.** Can the engine do this chemistry? |
| `ROUTE_INDEX.md` | **generated.** Feedstocks $\to$ intermediates $\to$ products |
| `PLAYABLE.md` | **generated.** Can a player get there from a rock? Runs things. |
| `README.md` | the class-relabelling argument, and the two rules that follow |

## `validation/` --- the audits

Each file answers one question and most were written because a specific number
turned out to be wrong. A representative selection:

| file | asks |
|---|---|
| `catalog_coverage.py` | how much of the corpus resolves and runs |
| `rate_ceiling.py` | is any rate constant above the collision limit |
| `tolerance_audit.py` | which numbers are solver resolution rather than chemistry |
| `jacobian_bound.py` | does the `num_jac` bound bind, and where |
| `wall_clock.py` | what does each operation actually cost |
| `boiling_points.py` | how far off were the estimates the measured table replaced |
| `corpus_balance.py` | do the catalog's own rows balance |
| `granularity.py` | is the playability scorer right |
| `wait_conditions.py` | what does each proposed `wait_until` look like on a real trajectory |
| `process_losses.py` | where does the yield actually go |
| `unifac_gap.py` | what is not decomposable, and what does that cost |
| `physical_estimation.py` | how good are Wilson--Jasperson and Fedors here |

## `examples/` --- runnable narratives

`esterification`, `thermochemistry`, `vessel`, `workshop`, `activity`,
`wait_until`, `multistep_prep`, `extraction`, `competing_pathways`,
`fractional_distillation`, `plate_column`, `named_routes`, `lime_cycle`,
`mercury_retort`, `roasting_and_the_catalyst_gate`, `electrolysis_cell`,
`oil_of_vitriol`, `dropping_funnel`.

## `tools/` --- the generators

```
build_benson_data.py      build_ion_data.py         build_playable.py
build_dielectric_data.py  build_mineral_data.py     build_route_index.py
build_element_data.py     build_physical_data.py    catalog.py
```

Each generated table says **GENERATED --- do not hand-edit** at the top and names
its build script, because the derivation is where the reasoning lives and a
generated file cannot carry the collision report its build prints.

## The project's own documents

| file | lines | what |
|---|---:|---|
| `README.md` | 625 | the thesis and the current state |
| `MILESTONES.md` | 6,545 | **the primary record.** Every milestone, with its measurements and its refusals |
| `HANDOFF.md` | 7,751 | session-to-session context |
| `NEXT_SESSION.md`, `NEXT_PROMPT.md` | 2,900 | the work queue |
| `GAME_DESIGN.md` | 581 | what this is ultimately for |
| `ASSESSMENT.md` | 327 | an outside-view review |
| `EQUIPMENT_PLAN.md`, `EQUIPMENT_CATALOG.md` | 788 | glassware, planned and built |
