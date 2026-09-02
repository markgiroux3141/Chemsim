# Codebase map

The 30 files that matter, what each owns, and where the load-bearing functions
are. Line numbers are from 2026-09-01; re-check with `grep -n` before editing.

## Layers (strict downward imports, one known leak)

```
ui/         Tkinter window + worker thread + Session (the testable half)
engine/     World (clock, events, script, save/load), Scenario, Stock, shelf_data
vessel/     Vessel (3 phases + energy), Rig (edges between vessels), conditions (wait_until roots)
discovery/  refine_network  -- DORMANT, zero callers, zero tests
numerics/   integrators + RHS builders + UNIFAC/LLE evaluation. Arrays only. No molecules.
network/    build_network: templates x species -> ConcreteReaction list -> KineticArrays
reactions/  ReactionTemplate, template libraries, detailed balance, Hammett, electrochemistry
properties/ thermochemistry (curated > Benson > Joback), volatility, condensed, UNIFAC data, minerals, ions
matter/     Molecule (canonical SMILES identity). The ONLY place RDKit is supposed to live.
```

Known leak: `properties/electrolyte.py:406` lazily imports `reactions.ReactionTemplate`.
Known broken claim: `reactions/template.py:25`, `reactions/hammett.py:182`,
`properties/fragmentation.py` import rdkit directly.

## Data flow for one run

```
shelf.psv / picker  -->  feed species (SMILES) + templates
                          |
                          v
network.build_network(species, templates, thermo, T_ref, generations, max_species)
   _expand_once (builder.py:606)   substructure-match every template slot, run rewrites,
                                   reject unbalanced, price products, derive reverse
   -> ReactionNetwork.to_arrays()  -> KineticArrays (A, Ea, n, order, delta, phase...)
                          |
                          v
vessel.Vessel(...)  build_phase_arrays (vessel.py:466)  Antoine/Henry/Rackett/UNIFAC -> PhaseArrays
                          |
                          v
numerics.VesselIntegrator.make_rhs (vessel_integrator.py:1781)  the 506-line closure `rhs`
   scipy solve_ivp (stiff), events for wait_until roots
                          |
                          v
engine.World.step / wait_until / collect_fraction / bottle   -> script (replayable) -> save JSON v9
                          |
                          v
ui.Session (worker thread, chunked ops, snapshots)  ->  ui.App (Tk widgets)
```

## Files that matter

### Layer 0 — matter
| file | owns |
|---|---|
| `matter/molecule.py` (290) | `Molecule.from_smiles`, canonical `.smiles` identity, `.molar_mass`, `._mol` (the RDKit handle other layers reach into) |

### Layer 1 — properties
| file | owns |
|---|---|
| `properties/thermochemistry.py` (925) | `ThermochemistryProvider.get(smiles) -> ThermoData`. Resolution: curated > Benson > Joback for formation; curated physical > measured Tb + Wilson-Jasperson for Tb/Tc/Pc; `OutsideEstimatorDomain` refusals for elements and ions (`:649`). |
| `properties/formation_data.py` (367) | hand-curated `IDEAL_GAS_FORMATION` / `LIQUID_FORMATION` dicts, kJ/mol at 298 K, with the exclusion list at the bottom |
| `properties/physical_data.py` (13,736, GENERATED) | measured Tb/Tm/Hfus for 1,239 species. Regenerate with `python tools/build_physical_data.py`. |
| `properties/benson.py` + `benson_data.py` (GENERATED from RMG-database) | second formation estimator |
| `properties/joback.py`, `joback_data.py`, `fragmentation.py` | group-contribution estimator; `fragmentation.py` is the shared SMARTS group matcher that UNIFAC also uses |
| `properties/mineral_data.py` (940, GENERATED) | lattices on the solid basis: Hf/Gf/S0/Cp_solid/Vm_solid. `MINERALS` dict. `python tools/build_mineral_data.py`. |
| `properties/element_data.py` (492, GENERATED) | elements with a monatomic vapour (Hg, Zn) — these can boil |
| `properties/ion_data.py`, `electrolyte.py`, `dielectric.py` | ions back-derived from pKa; `dissociation_templates()`; Born transfer between layers |
| `properties/solubility_product.py`, `solid_state.py`, `surface.py` | Ksp precipitation, solid-phase reaction terms, solid-gas surface terms. These cover 13 catalog classes as *terms*, not templates. |
| `properties/unifac.py`, `unifac_data.py`, `psrk_data.py` | activity coefficients; PSRK gas extension |
| `properties/volatility.py`, `condensed.py`, `critical.py` | Antoine/Lee-Kesler, Rackett, Rowlinson-Bondi fitted to polynomials at setup |

### Layer 2 — reactions
| file | owns |
|---|---|
| `reactions/template.py` (563, ~150 of code) | `ReactionTemplate` dataclass: `name, smarts, A, Ea, reversible, phase, alpha, orders, solid_catalyst, electrons, hammett_rho/slot/saturation`. `run()` applies the rewrite, collapses explicit H, re-parses products from canonical SMILES (`:535-563`). |
| `reactions/library.py` (845) | 9 templates: esterification, ether condensation, dehydration, two oxidations, SO₂ oxidation, NO reoxidation, sulfur combustion, SO₃ hydration. Also `_maybe_catalyse`, `_kinetics`, `CATALYST_REFERENCE`, `SOLID_CATALYST_REFERENCE`. |
| `reactions/synthesis.py` (2,626) | 38 templates + 17 `*_chemistry()` bundle functions at `:2373-2626` |
| `reactions/electrochemistry.py` (301) | 4 electrode templates |
| `reactions/thermo.py` (434) | `reaction_deltas`, `detailed_balance`, standard-state shift, `T_REF` |
| `reactions/hammett.py` (450) | sigma-plus survey of a ring, barrier shift, saturation plateau |

### Layer 3 — network
| file | owns |
|---|---|
| `network/builder.py` (1,002) | `build_network` (`:333`), `_expand_once` (`:606`), `_unpriceable` (`:701`), `_concrete_in_phase` (`:819`), `KineticArrays` (`:123`), `ReactionNetwork` (`:189`). Reports: capped, oversize, unpriced, unexpanded frontier. |

### Layer 4 — numerics
| file | owns |
|---|---|
| `numerics/vessel_integrator.py` (3,103) | `VesselIntegrator`: `pack/unpack`, `make_rhs` (`:1781`, closure `rhs` at `:1948-2453`), `_dryout_gates` (`:463`), non-negative projection, events |
| `numerics/rig_integrator.py` (708) | `RigIntegrator`: block state over several vessels + edges. Delegates to `vessel_integrator` helpers. Same 11 method names, no shared Protocol. |
| `numerics/activity.py`, `lle.py`, `jacobian.py`, `integrator.py` | UNIFAC evaluation per RHS call; the liquid-liquid split (runs between steps, never inside the RHS); Jacobian sparsity; the simple concentration-only `Integrator` used by tests and `refine.py` |

### Layer 5 — vessel
| file | owns |
|---|---|
| `vessel/vessel.py` (2,747) | `Vessel`: state, `build_phase_arrays` (`:466`), reports (`lle_report`, `activity_model.report()`), filtration |
| `vessel/rig.py` (343) | edges: vapour, drain, meter (the dropping funnel) |
| `vessel/conditions.py` (359) | `boils()`, `crystals(smiles)`, `temperature_steady(tol)`, etc. Root functions for `wait_until`. |

### Layer 6 — engine
| file | owns |
|---|---|
| `engine/world.py` (1,233) | `World`: `schedule/now/flush`, `_apply` (`:323`, every event kind), `step`, `wait_until` (`:529`), `collect_fraction` (`:630`), `add_dropwise` (`:730`), `bottle/charge_stock` (`:895/:929`), `script`, `save/load/replay` (`:1017-1101`). `SAVE_VERSION = 9` at `:122`. |
| `engine/scenario.py` (297) | `Scenario`: templates as `TemplateSpec` text, feed species, vessel specs. The network is rebuilt from this on load. |
| `engine/stock.py` (340), `inventory.py` (334) | `Stock` = per-phase mole vector + T + provenance script |
| `engine/shelf_data.py` (12,894, GENERATED) | the shelf. `python tools/build_shelf.py` from `data/catalog/shelf.psv`. |
| `engine/events.py` (142) | event kinds |

### Layer 7 — ui
| file | owns |
|---|---|
| `ui/session.py` (649) | worker thread owning the `World`; command queue; immutable `Snapshot`; chunking. Tested by `tests/test_ui.py` without a window. |
| `ui/app.py` (1,069) | Tk widgets. `_pour_bench` (`:609`), `_react_further` (`:645`) |
| `ui/examples.py` (399) | the worked examples; `full_library()` (`:241`) gathers 44 templates for the bench; `bench()` (`:297`) builds a World from picked shelf rows |

### Data and tools
| path | owns |
|---|---|
| `data/catalog/compounds/*.psv` | `id | name | smiles | class | role | domains | notes` |
| `data/catalog/routes.psv`, `route_steps.psv` | `route_id | step | name | reactants | products | conditions | reaction_class` (compound ids joined with ` + `) |
| `data/catalog/shelf.psv` | `id | tier | amount | phase | note` — the player's starting shelf |
| `data/catalog/COVERAGE_REPORT.md`, `PLAYABLE.md`, `ROUTE_INDEX.md` | GENERATED. Do not edit. |
| `validation/catalog_coverage.py` | the coverage audit; `TEMPLATE_CLASSES` at `:433` maps catalog class → template name. **Adding a template is not credited until it has a row here.** |
| `tools/build_playable.py` | the tech-tree scoreboard; runs its deepest chain (~50 s) |
| `tools/build_*_data.py` | regenerate every `*_data.py` module. Never hand-edit those. |

## Things that look like they do something and do not

- `discovery/refine.py` — dormant, untested, builds the same network twice.
- `Scenario.prune_threshold` — deleted in R3; if you see it in a doc, the doc is stale.
- `generations=1` in the bench — a UI choice; `generations=None` runs to a fixpoint and is safe for non-polymerising chemistry.
- The `[done]` on Layer 4.5 in the README.

## Commands

```
python -m pip install -e ".[dev,viz]"
python -m chemsim.ui                              # the window
python -m pytest -q tests/test_conservation.py    # fast sanity (< 5 s)
python -m pytest -q                               # full suite, ~30 min, ask first
ruff check src tests tools validation
python tools/catalog.py                           # structural validation of the PSVs
python validation/catalog_coverage.py             # regenerates COVERAGE_REPORT.md
python tools/build_playable.py                    # regenerates PLAYABLE.md (~50 s)
python tools/build_route_index.py                 # regenerates ROUTE_INDEX.md
python examples/named_routes.py                   # 17 routes end to end (~30 s)
```
