# Coverage strategy: changing the slope

The goal the user actually has: simulate as many chemical reactions as possible,
and let a player build from natural materials to real products. The project has
been climbing that hill at +3 to +5 reaction classes per session with a flat
unlock curve. This document is how to change the slope. It is the most important
file in this folder.

## 1. Why the current approach cannot speed up

Measured on 2026-09-01 from `data/catalog/route_steps.psv`:

- 240 reaction classes for 377 steps. 169 classes appear in exactly one step.
- 44 routes are one class away from template-ready, and they want 35 different
  classes. The best single template unlocks 3 routes. After 7 templates, every
  further template unlocks 1.
- A template costs a Python function (median 40 lines, up to 226) plus a
  bespoke test file (250 to 550 lines) plus a validation script (220 to 590
  lines) plus doc paragraphs in three files.

Multiply: 181 uncovered classes × ~700 lines × ~1 class per hour of model time.
The approach is the bottleneck. No amount of doing it harder helps.

## 2. Three moves, in order

### Move 1 — Templates become data (T1 in the work order)

Today a template is a Python function. Make it a row.

`data/templates/templates.psv`:

```
name | tier | smarts | A | Ea_J | reversible | phase | class | source | notes
```

- `tier` is `family` (generic SMARTS, curated) or `literal` (one balanced
  reaction as a mapped SMARTS, generated and reviewed).
- Optional columns for the rarer fields: `alpha`, `orders`, `solid_catalyst`,
  `electrons`, `hammett_rho`, `hammett_slot`.
- `python tools/build_templates.py` reads it and emits
  `src/chemsim/reactions/template_data.py` (the same generated-module pattern
  every `*_data.py` already uses), plus a `load_templates(tier=..., classes=...)`
  function.
- Migrate the 57 existing constructors by writing rows that reproduce them,
  then assert equality of the generated `ReactionTemplate` fields against the
  old functions in one parametrised test. Keep the old functions as thin
  wrappers for a release, then delete them.
- **One table-driven test replaces per-template test files:** for every row, for
  every catalog step carrying its class, build a network from the step's
  reactants with only that template and assert the step's products appear and
  the network has no unbalanced rewrite. That is one function; the rows are the
  cases.

`TEMPLATE_CLASSES` in `validation/catalog_coverage.py:433` goes away; the
`class` column is the mapping.

### Move 2 — Extract literal templates from the catalog (T2)

The catalog has 377 steps with compound ids that resolve to SMILES on both sides.
That is 377 candidate reactions nobody has to invent.

`tools/extract_templates.py`:

1. For each step: resolve reactants and products to SMILES; skip any step
   containing a `*-marker` id (no graph).
2. Balance check by element and charge. Steps that do not balance (75 of 367
   already flagged by `validation/corpus_balance.py`) get written to a
   `needs_stoichiometry.psv` for a human, not skipped silently.
3. Atom-map. Start with the cheap method: RDKit MCS between each product and
   the reactant set, greedy assignment, then fill unmapped atoms by element and
   neighbourhood. This works for the small inorganic and gas steps that make up
   the natural-materials tech tree. For organics with more than ~15 heavy atoms
   changing, optionally call `rxnmapper` (a pip install; treat as a
   curation-time tool exactly like `chemicals`, never a runtime dependency).
4. Extract a reaction SMARTS with the reacting centre plus one bond of context
   (RDChiral's `extract_from_reaction` does this from a mapped reaction SMILES
   and is MIT; its rules for which atoms to generalise are what you want to
   copy or import).
5. Verify: `ReactionTemplate(smarts).run(reactants)` must reproduce the products
   exactly (canonical SMILES). Rows that fail go to `needs_review.psv` with the
   reason.
6. Assign kinetics from the class policy table (below). Set `reversible` from
   the irreversibility rules unless the class overrides.
7. Write rows with `tier=literal`, `source=extracted:<route_id>/<step>`.

Expect 150 to 250 of 377 to pass fully automatically on the first run. Each one
is a template-ready step that cost zero sessions. Then the coverage report
should distinguish "template-ready via family" from "via literal" so nobody
mistakes the second for generality.

Why this is honest and not "a recipe table": a literal template still enters the
same network builder, gets its reverse from detailed balance, competes with
every other template in the flask, and is subject to the same conservation
checks. It is exactly what `sulfur_combustion` and `ammonia_synthesis` are today.
Calling them literal is naming what already exists.

### Move 3 — Generalise the literal templates that cluster (T3, ongoing)

Once the literal rows exist, cluster them by reacting-centre SMARTS. Where five
literal rows share a centre (five different esters hydrolysing, five metal
oxides reducing with CO), write one family template and retire the five. This is
the review work a model is good at, and it is now driven by data rather than by
reading a 462 KB milestones file to decide what is next.

## 3. Kinetics policy table (write once, apply everywhere)

| class family | A | Ea band (kJ/mol) | reversible? |
|---|---|---|---|
| acid/base proton transfer | 1e10 | ~0 (diffusion) | yes |
| esterification / hydrolysis / transesterification | 1e6 to 1e8 | 45 to 70 | yes |
| SN2 at sp3 carbon | 1e8 | 60 to 90 | no (leaving group) |
| E1/E2 elimination | 1e13 uni / 1e9 bi | 100 to 160 | no (into excess) |
| addition to C=C (hydration, HX) | 1e10 | 70 to 90 | yes |
| hydrogenation (heterogeneous) | 1e10, `solid_catalyst=` | 40 to 60 | no (large −ΔG) |
| oxidation of alcohols/aldehydes | 1e9 | 50 to 70 | no (product stable) |
| EAS (nitration, halogenation, FC) | 1e8, `hammett_rho=` | 50 to 80 | no |
| condensation (aldol, Knoevenagel, Perkin) | 1e8 | 60 to 95 | no if loses water/CO₂ into excess, else yes |
| gas-phase inorganic (shift, reforming, Deacon) | 1e10 gas | 60 to 120 | yes |
| combustion | 1e11 with `orders=` | 100 to 170 | no |
| calcination / roasting / reduction of a lattice | term, not template | | |

Cite the band in the `source` column once per class in a `data/templates/kinetics_policy.psv`.
Where NIST Chemical Kinetics Database has a record, use it and put the record id
in `source`. Stop writing the argument per template.

## 4. Change what is measured

Add two headline numbers to the coverage report and put them in the README's
one status table:

1. **Concrete reactions reachable from the shelf.** Run `build_network` to a
   fixpoint (`generations=None`, capped at 400 species) from every pair of
   natural shelf rows. Count distinct reactions. This is what a player can do.
2. **Family coverage.** A checklist of ~70 named organic reaction families (the
   ones in any second-year organic syllabus). Count families with a template.
   Each one amortises over hundreds of catalog species.

Keep the 173-route intersection and the 21-playable tech tree, but stop treating
them as the goal. The goal is "as many reactions as possible"; those two numbers
were a proxy that turned out to have a flat curve.

## 5. The inorganic tech tree is a separate, smaller job

The natural-materials chain (ore → metal → reagent) is where templates are
literal by nature and where the engine has one real gap: a lattice cannot
become its ions and back (R6). Do R6 once. Then the inorganic steps are literal
rows from Move 2, and the shelf's rocks dissolve, precipitate, roast and reduce
without a session per mineral.

## 6. What this changes about a session

Before: read 1.6 MB of history, pick a class from a scoreboard, write a 100-line
function and a 400-line test, re-run three generators, append to four files.
After: run the extractor, review `needs_review.psv`, fix ten SMARTS, run one
table-driven test, commit the PSV. Ten templates a session instead of one, and
each one is a row a human can read.
