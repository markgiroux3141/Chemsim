## S6 — Teach `species-ready` about `mineral_data`  ✅ **DONE 2026-08-25 — the gap was real, and the RECORDED SIZE OF IT was itself wrong**

**The brief:** `species-ready` asks the plain `ThermochemistryProvider`, which
refuses an ionic lattice by name. A lattice has had a home since M3 —
`mineral_data`, on the solid basis — and it is the table precipitation,
`SolidStateArrays` and `SurfaceArrays` all price from. S4 recorded the gap at
**14 routes, 49 → at most 63 of 173**, and deferred it because it redefines a
published column.

**What shipped:** `_mineral_fallback` in `validation/catalog_coverage.py`, a new
`mineral` tier, and two generated report sections. **No `src/` file was touched
and no chemistry moved.** 19 compounds move refused → `mineral`; species-ready
goes **49 → 65**, fully-sourced **5 → 14**.

| column | before | after |
|---|---:|---:|
| routes species-ready | 49 (28.3%) | **65 (37.6%)** |
| routes fully sourced | 5 (2.9%) | **14 (8.1%)** |
| compounds resolving | 1118 (70.6%) | **1137 (71.8%)** |
| formation measured/Benson | 716 (45.2%) | **735 (46.4%)** |
| refused | 465 (29.4%) | **446 (28.2%)** |
| UNIFAC-decomposable | 836 | 836 — **unchanged, by design** |
| reaction classes | 36/218 | 36/218 — unchanged |
| routes template-ready | 28/173 | **28/173 — unchanged** |

### ⚠⚠ THE PREDICTION WAS 14 AND THE ANSWER IS 16 — THE RECORDED NUMBER WAS THE BUG, ONE LAYER DOWN

The standing check was run: predict, then measure. The prediction was S4's
recorded 14, and it came out **16**. The cause is not the corpus and not the
engine — it is how the recorded estimate was measured. It compared the catalog's
SMILES to the `by_lattice` key as a **raw string**, and the catalog spells its
salts in a different fragment order than the canonical table:

    catalog   [Ca+2].[O-]C([O-])=O          [Zn+2].[O-2]
    table     O=C([O-])[O-].[Ca+2]          [O-2].[Zn+2]

| matching rule | routes moved |
|---|---:|
| raw lattice string | 14 ← **the recorded estimate** |
| raw, or the sorted dissolved-ion tuple | 15 |
| **canonical lattice — what the engine itself does** | **16** |

The two it missed are `vulcanisation` and **`lime-cycle`** — and `lime-cycle` is
the route S4's own note names *in its prose* as the headline case ("which M6
declared complete from limestone and whose example demonstrably runs") while its
list of fourteen route ids does not contain it. **The recorded number, the
recorded list and the recorded prose disagreed with each other, and only
re-measuring showed it.** This is the same lesson as S5's four dead triggers in a
different costume: a recorded measurement is a claim about a past state, and it
can be wrong about its own subject.

Canonical is not a convenience — it is what the engine does. `network/builder.py`
line 320 rebuilds every input SMILES through `Molecule.from_smiles` before the
species list exists, so `vessel.py`'s raw `by_lattice()` lookup is reached with
the canonical key. That was **verified rather than inferred**: all 19 rescued
minerals were charged into a real `Vessel` solid block, 19 of 19 holding their
full 0.02 mol. The opposite failure — `pyrite-roasting`, which reads
template-ready and does not run — is exactly what that check exists to prevent.

### ⚠⚠ THE RULE IS A FALLBACK, NEVER AN OVERRIDE, AND THAT IS THE WHOLE DESIGN

The obvious implementation — *is this compound a mineral?* — is wrong, and
measurably so. 36 catalog compounds sit on a mineral lattice, but 17 of them
**already resolve as `ion`**: `sodium-chloride`'s ions are priced, it genuinely
dissolves, and with `precipitation=True` it can also leave solution. Labelling it
`mineral` would **downgrade** a species the engine handles in two phases to one
it handles in one, and would have silently cut the published UNIFAC count.

So `_mineral_fallback` is consulted **only where all three providers have already
refused**. That is not a new precedence, it is the engine's own: `thermochemistry`
prices the ions when it can, and `mineral_data` is what the solid block falls back
to when it cannot. Because every rescued species was previously refused, the
branch returns exactly where the refusal did — and **the UNIFAC count does not
move by one**, which is the honest answer: a lattice cannot enter a liquid
mixture, by the same verdict that sent it down this branch.

### ⚠ `mineral` IS A SEPARATE TIER, NOT PART OF `measured`

It is measured data — CRC `Hf` and `S0`, `Gf` derived against the same element
reference states, same-database rule enforced — so it counts on the measured side
of the formation headline. But it is reported under its own name, because a
solid-basis `Hf`/`Gf` **is not on the ideal-gas basis every `ThermoData` uses**.
Folding it into `measured` in the report would make exactly the conflation the
separate `MineralRecord` type upstream exists to prevent.

### ⚠⚠ THE COLUMN NOBODY WAS COMPUTING: THE INTERSECTION IS 17, NOT 28

Asked afterwards what the coverage actually is, S6 measured the one thing none of
the three readiness columns says. **They answer INDEPENDENT questions, and the
smallest does not bound the others.**

| | routes |
|---|---:|
| species-ready | 65 |
| template-ready | 28 |
| **BOTH — the only one a route can be judged on** | **17** |

**11 of the 28 template-ready routes have a refused species and cannot run** —
`pyrite-roasting`, `tnt-route`, `superphosphate`, `chrome-yellow-route`,
`biodiesel-route` and six more. Quoting 28 as *what could run* overstates it by a
factor of 1.6, and this project has quoted 28 since S4.

⚠ **AND IT CHANGES WHAT S6 IS WORTH.** Measured both ways: the intersection
without the `mineral` tier is **12**, with it **17**. So the milestone that
"moved no template-ready route" moved the runnable count by **+5** — more than the
last three content milestones combined. Curating a species and writing a template
are the SAME axis on this column, which neither of the published ones can show.

⚠⚠ **AND THE WORK QUEUE WAS RANKED ON THE OVERSTATED COLUMN.** The greedy curve
and the one-class-away table both counted template unlocks alone. Re-ranked by
routes that would clear BOTH bars, the top changes hands:

| class | unlocks ALONE | of those, RUNNABLE |
|---|---:|---:|
| `isomerisation` | 3 | **2** |
| `crosslinking` | 2 | **2** |
| `electro-organic-coupling` | 2 | **2** |
| `electrolysis` (= M8) | 3 | **1** |
| `catalytic-air-oxidation` | 3 | **0** |

⚠ `catalytic-air-oxidation` is the third row of the greedy curve and is worth
**ZERO** runnable routes. Both tables now carry a RUNNABLE column, generated.

⚠ One thing the re-rank does NOT settle: `electro-organic-coupling`
(`kolbe-electrolysis`, `adiponitrile-route`) is electrochemistry too, and M8's
brief names only `electrolysis`. If one milestone covers both it is +5 unlocked /
**+3 runnable**, which would put it back on top. **That is a scoping question to
answer before scheduling M8, not an assumption to make.**

> ⚠⚠ **M8 ANSWERED IT, AND THE RUNNABLE HALF WAS RIGHT WHILE THE UNLOCKED HALF
> WAS NOT.** One mechanism does cover both — an applied cell potential supplying
> `n F E` — so the milestone was scoped to both, and the measured outcome is
> **+3 runnable, exactly as predicted, on +3 unlocked rather than +5.**
>
> The two missing unlocks are the price of M1's row check landing on the greedy
> curve's own top row. `electrolysis`'s four rows are THREE mechanisms, split at
> the CATHODE: `aqueous-electrolysis` (chloralkali — reduces water, BUILT),
> `molten-salt-electrolysis` (downs-cell, hall-heroult — a melt is not a phase
> here) and `amalgam-electrolysis` (castner-kellner — reduces the sodium, and
> the product is a marker). **The row that has led the greedy curve since M1 is
> worth +1, not +3.**
>
> ⚠ Note which of the two columns survived. `RUNNABLE` was right because both
> melt rows are ALSO blocked on a bare element, so the split cost nothing there —
> the column that counts what can actually run was insensitive to the very error
> that halved the other one. **That is the second time in two milestones that
> the intersection was the trustworthy column.** See §M8.

⚠ **And the claim it makes is narrow.** A mineral resolves here *as a crystal*:
it can be charged, held and reacted, and it still cannot dissolve. A step needing
one in solution is still not expressible. **None of the 16 routes becomes
template-ready**, and template-readiness remains the binding constraint — which is
why the honest headline of this milestone is the unchanged 28, not the 65.

### ⚠ THE NEXT ONE ALONG IS THE SAME SHAPE, AND IT IS NOW MEASURED: 15 ROUTES

45 compounds are still refused as *a bare element symbol*, and the refusal is
right — the ideal-gas value for `[C]` is the atom at Gf +671 kJ/mol while the
charcoal in the flask is 0. `iron`, `copper` and `nickel` escaped it only because
**S1 needed them as solid catalysts** and curated them into `mineral_data`; the
other 45 did not. **15 routes are blocked by nothing else**, and the leverage is
now a table rather than a hunch: `cobalt` +3, then `carbon-graphite`, `platinum`
and `silver` at +2 each.

⚠ It is a curation job with a **layering question in front of it**.
`element_data.REFERENCE_STATES` already carries S0 and the reference state for
these — Zn(s), Ag(s), C(graphite) — but with `smiles=None`, because a SOLID
reference state had nowhere to live until the solid block existed. Mercury
resolves today precisely because its standard state is a LIQUID and so it got a
SMILES. What is missing is that binding plus the `Cp_solid`/`Vm_solid` pair
`priced_solid` demands. **Whether that belongs in `element_data` or in
`mineral_data` is a real decision — a metal is not a mineral — and it owes its own
predict-then-measure pass.**

### ⚠ BOTH NEW REPORT SECTIONS ARE GENERATED, AND THAT IS THE POINT

The estimate this milestone replaces was a hand-written comment that drifted from
its own corpus. Both replacements — *the 16 routes species-ready on a lattice* and
*the 15 blocked only by a bare element* — are computed on every run, so they
cannot rot the way it did. `COVERAGE_REPORT.md` remains byte-identical across
`PYTHONHASHSEED` values (checked at 12345, 999 and 4242), as do
`route_roles.psv` and `species_roles.psv`.

**Touched:**
* `validation/catalog_coverage.py` — `_mineral_fallback`, the `mineral` tier,
  `SOURCED_TIERS`, and the two generated sections. ⚠ The three hard-coded
  `measured + benson + ion` sums now go through `SOURCED_TIERS`; adding a tier
  without adding it there is how a headline silently under-counts.
* `data/catalog/COVERAGE_REPORT.md`, `data/catalog/derived/species_roles.psv` —
  regenerated. `ROUTE_INDEX.md` and `route_roles.psv` regenerated and unchanged.
* `README.md` — the coverage table, plus the new `routes species-ready` row.

**NOT touched:** anything under `src/`. The engine, the 826-test suite and every
example are untouched by construction, and no invariant in `NEXT_SESSION.md`
moves.

---
