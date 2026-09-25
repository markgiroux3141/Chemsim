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
| `build_playable` | 19 s here, was 46-62 s; the smelter on 2x CO is 33 Jacobians, was 1,540-2,889 | `python tools/build_playable.py --check` |
| the shelf | 82 rows: 43 natural, 26 intermediate, 13 bottle | `python tools/build_shelf.py` |
| the shelf sweep | 666 pairs, 24,710 reactions, 47 of 106 family templates fire, 1,301 s; 59 silent, classified | `derived/reachable.psv`, `derived/silent_templates.psv` |
| tests | 1,364 collected; 380 run locally on the 18 modules nearest the change, all pass | `python -m pytest --co -q` |
| CI | this push is the first with the Jacobian sign bound; the suite, the tolerance audit and the shelf sweep all run on it | `python tools/ci_status.py` |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py` |

## Last session, in five lines

CI's suite timed out because `import build_playable` cost 29 s on one runner
and 700 s on another, same code. The cost was one stiff solve whose empty liquid
block drifted negative while `num_jac`'s probe grew until it crossed zero into
a liquid evaporating at 1500 K. `numerics/jacobian.py::sign_bound` keeps that
probe on the negative side; `docs/design/jacobian-probe-sign.md` has the numbers.

## Do this now

1. **Read CI on this push and record it.** `python tools/ci_status.py`, then
   `--record`. If `pytest (full suite)` failed, its test ids are printed: a
   moved pin in an example-backed test is the sign bound, and the design note
   says which examples moved and which way the converged answer lies. The
   tolerance audit has stood red on T10's three findings (activity 0.1277%,
   multistep_prep 0.1073%, named_routes raising at rtol 1e-8); read whether
   those moved and whether anything new appeared.
   *Done when:* the suite job is `success` on HEAD and the `suite` and
   `tolerance` rows of `tools/cadence.py` are stamped from it.
2. **B1 -- price what the new rows wait on.** 54 benchmark cases pass as
   rewrites and cannot run: the `unpriced` column of `scores.psv` and the
   `#! unpriced` footer of `literal.psv` are the work order (phenyl isocyanate,
   triphenylphosphine oxide, the Grignard reagents, diazonium ions, enolates).
   *Done when:* `family_runs` has moved and each entry names its source.
3. **B2 -- ethylene is the +4 grant.** The corpus makes it; find why the route
   that does is not playable.
   *Done when:* playable moves, or the upstream blocker is named here.

## Decisions already taken — do not reopen

- **A Jacobian probe from an amount below -atol stays below zero.** Within atol
  the old crossing probe is kept, because it is what pulls a round-off
  overshoot back (the retort's HgO). The argument and the measurements are in
  `docs/design/jacobian-probe-sign.md`.
- **The benchmark is the coverage metric; the 173 routes are progression.** A
  family row must pass its class's held-out cases. 173 is still not a target.
- **At most one session in four is scoreboard or instrument work** unless a
  check is red. The session skill's Step 0b says how to count.
- **Extractor v2:** an aqueous salt is read as ions, a furnace's is a lattice
  and refused (E1); a stereo step is extracted flat.
- **A literal row that cannot be priced is still written**, and counted.
- **CI is the suite.** Running it locally still needs asking. `check_docs`
  ratchets fail only on growth.
- Standing: a class names a mechanism; never declare what detailed balance
  derives; a species the corpus writes on both sides of a step is not made by
  it; pin the relation, not only the level.

## Open questions for the user

- **The `profile` job in `.github/workflows/ci.yml` and `.github/profile_import.py`
  have done their job and can be deleted.** This session's attempt to remove
  them was refused by the permission check as a CI change, so it is yours to
  do or to allow. Nothing depends on them; the job is `continue-on-error`.
- **Make `main` the default branch on GitHub.** It is `p2-shelf-and-stock`
  today, and a scheduled workflow only fires from the default branch, so the
  weekly slow checks in `.github/workflows/slow.yml` will not run until it is.
- **The loop has a goal** (`tools/loop/GOAL.md`: benchmark 56 -> 60 general
  classes, runs 152 -> 180). `pwsh tools/loop/run-loop.ps1 -MaxSessions 3` is
  yours to start.

## Known and not scheduled

- The mercury retort's empty liquid block drifts to -1.5e-4 mol of SO2 under
  either Jacobian while the RHS returns zero for it; it enters through other
  columns. No matter is created. Engine work, so it waits for a check to say
  it matters.

## Do not

- Do not hand-edit a generated file (`literal.psv`, `needs_review.psv`,
  `scores.psv`, `COVERAGE_REPORT.md`, `PLAYABLE.md`, `*_data.py`, `derived/*`).
- Do not promote a row to `family` without its class's held-out cases.
- Do not read `docs/history/` whole, append to it, or add a physics module.
