# NEXT — overwritten 2026-09-25

Overwritten whole each session: what is still true is re-typed, the rest is gone.

## State of the box

Every number came from a command run on 2026-09-24 or 25.

| fact | value | command |
|---|---|---|
| **benchmark, the coverage headline** | **56 / 63 classes general; 206 / 216 cases pass on family rows, 152 run in the engine, 54 unpriced** | `data/benchmark/scores.psv` footer (`python tools/benchmark.py`, 3 s) |
| templates | 151 rows: 106 `family`, 45 `literal` | `python tools/build_templates.py --check` |
| literal rows that build a priced reaction | 34 of 45; the footer names what stops the rest | `data/templates/literal.psv` footer |
| template rows against their catalog step | 122 pass / 16 partial / 3 wrong-product / 8 no-substrate / 2 no-class | `python tools/check_template_products.py` |
| routes template-ready / species-ready / both | 81 / 95 / 58, and 63 / 95 / 48 on family rows alone | `python validation/catalog_coverage.py` |
| routes runnable / playable | 56 / 23; ethylene is the biggest single grant, +4 | `data/catalog/PLAYABLE.md` |
| the shelf | 82 rows: 43 natural, 26 intermediate, 13 bottle | `python tools/build_shelf.py` |
| the shelf sweep | 666 pairs, 24,710 reactions, 47 of 106 family templates fire, 1,301 s; 59 silent, classified | `derived/reachable.psv`, `derived/silent_templates.psv` |
| tests | 1,361 collected. CI runs them on every push | `python tools/ci_status.py` |
| CI | fast job green. The SUITE job ran past its 150-min limit twice (no report) while the suite is green locally, 1,361/1,361 in 9m40s on 8 workers. `ci.yml` now writes a reportlog that names what never finished: read it first | `python tools/ci_status.py` |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py` |

## Last session, in five lines

A retro. The benchmark (`data/benchmark/`) now measures coverage of chemistry:
held-out textbook cases a single-substrate row cannot pass. Extractor v2 read
salts as ions and stereo flat (58 -> 79 literal rows before promotion), and 38
textbook family rows took the benchmark from 20 to 56 general classes. CI runs
the suite on every push; memory went 125 -> 26 notes.

## Do this now

1. **Make the CI suite job finish.** The suite is green locally (1,361/1,361,
   9m40s on 8 workers) and has run past CI's time limit three times. What is
   known, all from `python tools/ci_status.py --slowest`: three xdist workers
   were killed at the 900 s per-test timeout in the SETUP of `test_playable`,
   `test_vanillin` and `test_fermentation`, which is `import build_playable`;
   that same import takes 29 s standalone on the runner (the `profile` job).
   The `profile` job on 36b615a times `test_playable` alone (notices titled
   `serial`) and the four scoreboard modules together (`four at once`).
   Read those first. Slow only four-at-once: give the scoreboard modules
   their own CI job and keep them out of the xdist run. Slow serially too:
   the cost is in the pytest process, so profile the fixture under pytest.
   *Done when:* `pytest (full suite)` is `success` on HEAD, and the `profile`
   job is deleted from `ci.yml` once it has answered.
2. **B1 -- price what the new rows wait on.** 54 benchmark cases pass as
   rewrites and cannot run: the `unpriced` column of `scores.psv` and the
   `#! unpriced` footer of `literal.psv` are the work order (phenyl isocyanate,
   triphenylphosphine oxide, the Grignard reagents, diazonium ions, enolates).
   *Done when:* `family_runs` has moved and each entry names its source.
3. **B2 -- ethylene is the +4 grant.** The corpus makes it; find why the route
   that does is not playable.
   *Done when:* playable moves, or the upstream blocker is named here.

## Decisions already taken — do not reopen

- **The benchmark is the coverage metric; the 173 routes are progression.** A
  family row must pass its class's held-out cases. 173 is still not a target.
- **At most one session in four is scoreboard or instrument work** unless a
  check is red. The session skill's Step 0b says how to count.
- **Extractor v2:** an aqueous salt is read as ions, a furnace's is a lattice
  and refused (E1); a stereo step is extracted flat. The checker judges in the
  same engine reading.
- **A literal row that cannot be priced is still written**, and counted.
- **Left out on purpose:** halide as an SN2 nucleophile, radical halogenation,
  secondary alcohols in the acyclic acetal (each row's note says why).
- **CI is the suite.** Running it locally still needs asking. `check_docs`
  ratchets fail only on growth.
- Standing: a class names a mechanism; never declare what detailed balance
  derives; a species the corpus writes on both sides of a step is not made by
  it; a shelf tier is a question about a species; pin the relation, not only
  the level.

## Open questions for the user

- **Make `main` the default branch on GitHub.** It is `p2-shelf-and-stock`
  today, and a scheduled workflow only fires from the default branch, so the
  weekly slow checks in `.github/workflows/slow.yml` will not run until it is.
- **The loop has a goal now** (`tools/loop/GOAL.md`: benchmark 56 -> 60 general
  classes, runs 152 -> 180). `pwsh tools/loop/run-loop.ps1 -MaxSessions 3` is
  yours to start.
- The tolerance audit is still red on the same three pre-existing findings
  (T10); CI runs it and does not gate on it.

## Do not

- Do not hand-edit a generated file (`literal.psv`, `needs_review.psv`,
  `scores.psv`, `COVERAGE_REPORT.md`, `PLAYABLE.md`, `*_data.py`, `derived/*`).
- Do not promote a row to `family` without its class's held-out cases, or add
  cases the tool refuses (they must parse, balance and stay held out).
- Do not read `docs/history/` whole, append to it, or add a physics module.
