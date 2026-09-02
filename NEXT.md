# NEXT — overwritten 2026-09-02

Rewritten from scratch at the end of every session, never appended to. Anything
still true next time gets re-typed; anything not re-typed is gone.

## State of the box

Every number came from a command run on 2026-09-01 or 2026-09-02. The command is named.

| fact | value | command |
|---|---|---|
| tests | 1,264 collected, 0 skips, 0 xfails | `python -m pytest --co -q` |
| fast check | `./check.ps1`, ~60 s, green | ruff + docs + catalog + 39 smoke tests |
| full suite | ~30 min, no markers yet | ask before running |
| templates | 57: 38 `synthesis.py`, 9 `library.py`, 6 `electrolyte.py`, 4 `electrochemistry.py` | `grep -c 'ReactionTemplate(' src/chemsim/reactions/*.py src/chemsim/properties/electrolyte.py` |
| catalog | 1,583 compounds, 173 routes, 377 steps, 240 classes | `python tools/catalog.py` |
| routes template-ready / species-ready / both | 46 / 85 / 38 | `data/catalog/COVERAGE_REPORT.md` |
| routes playable from natural materials | 21, three tiers deep | `data/catalog/PLAYABLE.md` |
| `SAVE_VERSION` | 9 | `src/chemsim/engine/world.py:122` |
| line endings | mixed — preserve each file's own | `grep -qU $'\r' <file>` |

## Last session, in five lines

Froze the seven root monoliths into `docs/history/`, split the milestones file
into 79 grep-sized sections behind an index, and installed the five-file working
set with `tools/check_docs.py` holding the caps. Fixed the README's stale status,
its false `[done]` on Layer 4.5 and its untrue RDKit-boundary claim. Then took
the three decisions the critique had left open — recorded in `BACKLOG.md` under
T0.3, T4 and R4/E3, with the reasoning, so none of them is relitigated. Added
the `handoff` skill so the close-out is a routine, not a habit.

## Do this now

1. **T1.0 — measure what extraction could actually produce.** This is the gate on
   the whole Tier 1 plan, which rests on an estimate of "150 to 250 of 377" that
   nobody has checked. For each of the 377 rows in `data/catalog/route_steps.psv`,
   answer three questions and cross-tabulate them: does every species resolve to
   a SMILES (no `*-marker`); does the row balance under the LP in
   `validation/corpus_balance.py:104` (return `linprog`'s `x`, do not re-derive
   it); and is its class one of the 181 with no template today.
   *Done when:* the three-way table is in `CHANGELOG.md` with the command, broken
   down by class, and `BACKLOG.md`'s T1/T2 either survive it or are struck out.
   *Read the result honestly:* if the extractable-and-uncovered count is small,
   or concentrates in classes a template already covers, T1 and T2 are two
   sessions that buy nothing and the lever is somewhere else.

2. **R4/E3 — delete `discovery/refine.py`.** Decided; the argument is in
   `BACKLOG.md`. Half an hour, and it removes a false `[done]` and a dormant
   module that judges species on kinetics nothing runs at.
   *Done when:* the module, `discovery/__init__.py`, the README layer row and the
   `chemsim/__init__.py` mention are gone and `./check.ps1` is green.

3. **T0.4 — the fast test subset**, when a full-suite run is being asked for
   anyway. `python -m pytest --durations=0 -q` is 30 minutes on the user's own
   machine, so bundle it with something else that needs the suite. Then mark
   everything over 2 s `slow`, register the marker, and delete `check.ps1`'s
   hand-named `$SmokeTests`.
   *Done when:* `pytest -m "not slow"` is green in under three minutes.

## Decisions already taken — do not reopen

- **`discovery/refine.py` is deleted, not wired.** A fixpoint is cheap for the
  chemistry that matters, the species cap already bounds the expensive case and
  reports itself, and silent pruning breaks rule 10.
- **The organic-family checklist is not a headline metric.** A list the project
  writes and then scores itself against is G4's trap in a new place. The new
  headline is reactions reachable from the shelf, which is computed. The
  173-route intersection stays, because it is anchored to chemistry we did not
  invent.
- **The README stays at 561 lines** until C1 moves the physics prose into
  `docs/manual/chapters/`. The 300-line target was arbitrary; the budget is 400.

## Open questions for the user

- **`rxnmapper` as a curation-time dependency**, if T1.0 clears T2. Same standing
  as `chemicals` and RMG-database: used to build data, never imported at runtime.

## Do not

- Do not read `docs/history/` top to bottom. Grep it.
- Do not start T1 (templates as data) before T1.0 says it is worth it.
- Do not add a physics module. The engine is an order of magnitude ahead of the
  content.
- Do not run the full suite without asking; it is 30 minutes on the user's own
  machine.
