# Work order

Prioritised. Each task is sized for one session of a capable but not
exceptional model, has a definition of done, and names the files. Do them in
order unless the user says otherwise. Do not start an engine task while a T task
is open.

Sizing: S = under 2 hours, M = a session, L = two sessions.

---

## Tier 0 — stop the bleeding (do all of these first, one session total)

### T0.1 — `CLAUDE.md` (S)
Create `CLAUDE.md` at the root, under 150 lines: one-paragraph description,
install and run commands, the layer table from `02-CODEBASE-MAP.md`, a pointer
to `fable analysis/`, and the ten rules from `07-OPERATING-RULES.md`.
**Done when:** a fresh session can add a template using only `CLAUDE.md` and
`fable analysis/03-*.md`.

### T0.2 — Freeze the diaries and install the five-file handoff (M)
Per `08-SESSION-HANDOFF.md` §3 and §4. `git mv` `HANDOFF.md`, `MILESTONES.md`,
`NEXT_SESSION.md`, `NEXT_PROMPT.md`, `ASSESSMENT.md`, `EQUIPMENT_PLAN.md`,
`EQUIPMENT_CATALOG.md` to `docs/history/`. Split `MILESTONES.md` on `## `
headings into `docs/history/milestones/` with an index. Create `BACKLOG.md`
(open items only: R4, R6, this work order), `NEXT.md` (Tier 0, from the
template in 08 §3), `CHANGELOG.md` (one entry). Add `tools/check_docs.py`
enforcing the caps (CLAUDE 150, NEXT 120, BACKLOG 300, CHANGELOG entry 12, no
`⚠` outside `docs/history/`) and wire it into `check.ps1`.
**Done when:** the root has `README.md`, `CLAUDE.md`, `NEXT.md`, `BACKLOG.md`,
`CHANGELOG.md`, `GAME_DESIGN.md` and nothing else in markdown; `check_docs.py`
passes; a fresh session given only "read CLAUDE.md and NEXT.md" can name its
task and its done-when.

### T0.3 — Fix the README status (S)
Replace the Status paragraph and the milestone narrative in `README.md` with one
table whose numbers are copied from `COVERAGE_REPORT.md` and `PLAYABLE.md` on
the day, plus the test count from `pytest --co -q`. Remove every `⚠`. Keep
Architecture, Quickstart, the physics sections, Known limitations.
**Done when:** `README.md` is under 300 lines and every number in it matches a
generated file or a command output.

### T0.4 — Fast test subset (S)
Run `python -m pytest --durations=0 -q` once (ask the user first; 30 min). Mark
every test over 2 s with `@pytest.mark.slow`. Register the marker in
`pyproject.toml`. Add `check.ps1` running `ruff check`, `pytest -m "not slow"`,
and `python tools/catalog.py`.
**Done when:** `pytest -m "not slow"` finishes in under 3 minutes and is green.

### T0.5 — Reconcile the generators (S)
`COVERAGE_REPORT.md` quotes "36 runnable, 12 playable"; `PLAYABLE.md` says 21.
Make `validation/catalog_coverage.py` read the PLAYABLE numbers from
`build_playable`'s output or drop the cross-quote. Fix the template count it
prints (says 47; there are 57). Add a `--check` flag to both generators that
exits non-zero if the committed file differs from a fresh run.
**Done when:** the two files agree and `check.ps1` runs both with `--check`.

---

## Tier 1 — change the slope (the actual work)

### T1 — Templates as data (L)
Per `05-COVERAGE-STRATEGY.md` Move 1.
1. `data/templates/templates.psv` with the column set. Write rows for all 57
   existing templates.
2. `tools/build_templates.py` → `src/chemsim/reactions/template_data.py` and
   `reactions/load_templates(tier=None, classes=None) -> list[ReactionTemplate]`.
3. `tests/test_template_data.py`: (a) every generated template equals the
   constructor it replaces, field by field; (b) table-driven: every row fires on
   every catalog step of its class and reproduces the step's products.
4. Point `ui/examples.py:full_library()` and `validation/catalog_coverage.py`
   at the loader. Delete `TEMPLATE_CLASSES`.
5. Turn the 57 constructors into one-line wrappers over the loader; mark them
   deprecated in the docstring.
**Done when:** `named_routes.py`, the bench, and the coverage report run from
the PSV with identical output, and adding a template is one PSV row.

### T2 — Literal template extraction (L)
Per Move 2. `tools/extract_templates.py` with the six steps. Outputs
`templates.psv` rows with `tier=literal`, `needs_stoichiometry.psv`,
`needs_review.psv`. Add `kinetics_policy.psv` and apply it.
**Done when:** at least 100 extracted rows pass the table-driven test and the
intersection in `COVERAGE_REPORT.md` has moved by at least 20 routes. Report
the family/literal split separately.

### T3 — Review and generalise (M, repeating)
Cluster literal rows by reacting centre. For each cluster of 3+, write a family
row, confirm it covers every member, retire the members. Also work through
`needs_review.psv`.
**Done when:** each session retires at least 10 literal rows into families or
clears 20 review rows. Record the count in `CHANGELOG.md`.

### T4 — New headline metrics (M)
Add to `validation/catalog_coverage.py`: reactions reachable from the shelf
(fixpoint from every natural pair, 400-species cap, 60 s budget per pair, cache
results by species pair) and family coverage against a checklist file
`data/templates/families.psv` (~70 rows, you write it from a standard organic
syllabus). Put both in the README status table.
**Done when:** both numbers print in `COVERAGE_REPORT.md` with the command that
produced them.

---

## Tier 2 — engine work that moves playability

### E1 — R6, lattice to ions (M)
A term consuming a `mineral_data` lattice and producing its ions in the solid
block, priced from the same Ksp `PrecipitationArrays` uses, so rock salt as a
lattice dissolves. Read `docs/history/MILESTONES.md` §R6 for the design already
argued (grep `R6`). Both representations of a rock then converge.
**Done when:** 0.5 mol NaCl lattice into 30 mol water dissolves to the same
end state as 0.5 mol of its ions, and the six shelf rows that picked one
representation regain the other mechanic.

### E2 — "React until done" as the default (S)
In `ui/examples.py:bench()` default `generations=None` when no template in the
library is self-feeding for the picked species (a template is self-feeding if
one of its products matches one of its reactant slots; compute once at load).
Fall back to `generations=1` with a visible notice otherwise. Remove the
generations box from the UI's primary view.
**Done when:** sulfur + air + water in the bench runs to sulfuric acid without a
button press, and glucose + water still terminates.

### E3 — Wire or delete `discovery/refine.py` (M)
Decide. If wiring: fix the duplicate `build_network`, make `_rates_of` use
`to_arrays(thermo)`, add tests, call it from `bench()` after the charge is
known. If deleting: remove the module, the `[done]` on Layer 4.5, and the
`discovery` layer from the README.
**Done when:** the module has either callers and tests or does not exist.

### E4 — Decompose `make_rhs` (L)
`numerics/vessel_integrator.py:1781`. Extract the phase blocks the closure
already contains into module-level functions taking arrays and returning
arrays. Define a `Protocol` in `numerics/integrator.py` that both
`VesselIntegrator` and `RigIntegrator` satisfy. Run `validation/tolerance_audit.py`
before and after; trajectories must be bit-identical or within solver tolerance
with the difference reported.
**Done when:** no function in `numerics/` exceeds 120 lines of code (comments
excluded) and the tolerance audit shows no change.

### E5 — RDKit boundary (S)
Either move `AllChem.ReactionFromSmarts` / `RunReactants` behind
`matter.Molecule` (a `matter/rewrite.py`) and route `hammett.survey` through
`Molecule`, adding a test that greps `src/chemsim` outside `matter/` for
`rdkit` and fails on a hit; or delete the claim from `README.md:40` and
`chemsim/__init__.py:14`.
**Done when:** the claim and the code agree.

---

## Tier 3 — cleanup, only after Tier 1 is done

### C1 — Move essays out of source (M, repeating)
For each module over 1,000 lines, move narrative comments (anything with a
milestone tag, a measurement log, or a `⚠`) into `docs/manual/chapters/`, leave a
one-line pointer. Target: `vessel_integrator.py` under 1,800 lines,
`synthesis.py` deleted after T1, `template.py` under 300.
**Done when:** `grep -c '⚠' src/chemsim -r` is under 50 and no comment
mentions a milestone tag.

### C2 — `validation/` becomes tests or checks (M)
Each script either gains asserts and moves to `tests/` under `slow`, or gains a
non-zero exit on regression and is listed in `check.ps1 --full`.
**Done when:** every file in `validation/` exits non-zero on a regression of
the claim it makes.

### C3 — Split `synthesis.py` by family (S, moot after T1)
If T1 is delayed, split into `reactions/families/{esters,aromatics,gas,...}.py`.

---

## What NOT to do (and why)

| do not | because |
|---|---|
| add a Debye–Hückel / electrolyte activity model | γ for ions is not what blocks any route |
| add LHHW or Michaelis–Menten rate laws | no playable route needs one |
| start a Rust kernel | the RHS is 231 µs; numpy dispatch overhead, not arithmetic |
| correct the scoreboard rules again | four corrections in; the instrument is fine |
| append to any file in `docs/history/` | frozen |
| write a new template as a Python function after T1 | it is a row |
| write a markdown file over 300 lines | nobody reads it |
