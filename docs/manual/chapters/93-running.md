# Running it

## Install

```bash
python -m pip install -e ".[dev,viz]"
```

Runtime dependencies are numpy, scipy and RDKit, and nothing else. `dev` adds
pytest and `thermo` --- which is a **test-only oracle**: the suite cross-checks
this project's Joback table, its fragmentation, and every UNIFAC and PSRK
parameter against it. `viz` adds matplotlib. Python 3.11+.

Tkinter is standard library, which is most of why the interface is Tkinter.

## The window

```bash
python -m chemsim.ui          # or the chemsim-ui script
```

Glassware, the selected vessel's temperature / pressure / pH / phase volumes /
per-phase composition, the engine's own reports, and the recipe as it
accumulates. Four worked starting points including the benzoic-acid preparation.

Watch the **cost meter** --- it is the single most useful thing on screen for
understanding the engine's behaviour.

## Examples, roughly in order of what they teach

```bash
python examples/esterification.py     # graph -> template -> network -> equilibrium
python examples/thermochemistry.py    # properties and equilibrium from structure alone
python examples/vessel.py             # boiling, boiling dry, self-heating, distillation
python examples/workshop.py           # crystallisation, melting, pH/titration, the engine
python examples/activity.py           # azeotropes and real solubilities, from UNIFAC
python examples/wait_until.py         # a recipe with no durations in it
python examples/competing_pathways.py # the same flask at three temperatures
python examples/extraction.py         # two liquid layers and an acid/base workup
python examples/fractional_distillation.py
python examples/plate_column.py       # eight plates, reflux ratio 5
python examples/multistep_prep.py     # the benzoic-acid preparation, end to end
python examples/lime_cycle.py         # a reaction inside a crystal
python examples/roasting_and_the_catalyst_gate.py
python examples/mercury_retort.py     # a route that EMERGES from two declarations
python examples/electrolysis_cell.py
python examples/oil_of_vitriol.py
python examples/dropping_funnel.py    # drip it too fast and the pot runs away
python examples/named_routes.py       # the named historical routes, integrated
```

## Tests

```bash
python -m pytest -q
```

::: {.trap title="This takes about twelve minutes"}
It is a real integration suite --- it builds networks and integrates stiff
systems --- not a unit-test suite. Run it deliberately rather than in a loop, and
prefer a targeted file while iterating:

```bash
python -m pytest tests/test_vessel.py -q
python -m pytest tests/test_conservation.py -q
```
:::

Some tests worth knowing about by name:

| file | what it pins |
|---|---|
| `test_conservation.py` | element and charge conservation across all four phase blocks |
| `test_detailed_balance.py` | $k_f/k_r = K$, and equilibrium reached from both directions |
| `test_joback.py`, `test_benson.py` | the group tables against the `thermo` oracle |
| `test_activity.py` | UNIFAC parameters, and the azeotrope |
| `test_standard_state.py` | the gas $\to$ liquid shift, and the pH invariants that must survive it |
| `test_competing_templates.py` | that ether beats ethene at 140 °C and loses at 180 |
| `test_playable.py` | the tech-tree headline numbers and all four scoring rules |
| `test_ui.py` | the session layer, without opening a window |

## Regenerating the catalog artefacts

```bash
python tools/catalog.py                # structural validation only
python tools/build_route_index.py      # writes ROUTE_INDEX.md
python validation/catalog_coverage.py  # writes COVERAGE_REPORT.md + derived/
python tools/build_playable.py         # writes PLAYABLE.md -- ~1 min, RUNS the deep chain
```

::: {.trap}
Run **all** of them. `ROUTE_INDEX.md` went stale by three milestones because it is
the one generated file no audit reads, so a stale index changes no measured
number and produces no failure.
:::

## Regenerating the data tables

Each requires its upstream source and each prints an argument as it goes:

```bash
python tools/build_physical_data.py    # from `chemicals`, keyed off data/catalog
python tools/build_element_data.py     # from `chemicals` + `thermo`
python tools/build_mineral_data.py
python tools/build_ion_data.py
python tools/build_dielectric_data.py
python tools/build_benson_data.py      # needs an RMG-database clone
```

## The audits

These are the files that found most of what is in Part IV of this manual. They
are cheap to run and each answers one question:

```bash
python validation/rate_ceiling.py      # any rate constant above the collision limit?
python validation/tolerance_audit.py   # which numbers are resolution, not chemistry?
python validation/wall_clock.py        # what does each operation actually cost?
python validation/boiling_points.py    # 2 s; how far off were the old estimates?
python validation/corpus_balance.py    # do the catalog's own rows balance?
python validation/game_gates.py        # the standing verdicts, re-measured
```

## Regenerating this manual

```bash
python docs/manual/make_figures.py     # ~2 min; several figures RUN the engine
bash   docs/manual/build.sh            # pandoc + xelatex -> chemsim-manual.pdf
bash   docs/manual/build.sh --figures  # both
```

Requires pandoc and a LaTeX distribution with xelatex. The sources are the
markdown files under `chapters/`, with `preamble.tex` for the styling,
`callouts.lua` for the coloured boxes, and `metadata.yaml` for the fonts and
page setup.

## A short orientation route, if you have an hour

1. `python examples/vessel.py` --- watch a flask boil, boil dry and superheat,
   and note that no boiling point exists in the code.
2. `python examples/competing_pathways.py` --- the same charge at three
   temperatures giving three different products.
3. Read `src/chemsim/numerics/vessel_integrator.py`'s docstring. It is the
   clearest single statement of what the project is.
4. `python -m chemsim.ui`, load the benzoic-acid preparation, and watch the
   recipe panel fill in as you work.
5. Read `docs/history/MILESTONES.md` §M6 (a reaction inside a crystal) --- it is the best
   single example of the project's habit of deciding a modelling question *by
   arithmetic* rather than by argument.
