# Changelog

Newest first. One entry per session, twelve lines at most, enforced by
`tools/check_docs.py`. When this file passes 400 lines the older half rolls into
`docs/history/changelog-YYYY-MM.md`.

## 2026-09-02 — T0.5: the report counts its own templates (47 -> 57) and both generators ratchet

`validation/catalog_coverage.py` had five hand-maintained `N_*_TEMPLATES`
constants summing to 47 against 57 in the tree; `template_counts()` now walks
`reactions/*.py` and `properties/electrolyte.py` with `ast` and counts
`ReactionTemplate(` construction sites, so the report reads 57 (38 synthesis,
9 library, 6 electrolyte, 4 electrochemistry) and moves on its own. Its
`PLAYABLE.md` cross-quote said 36 runnable / 12 playable / 21 fed-but-unrunnable
against 44 / 21 / 22; it is now parsed from that file's footer, which gained the
fed-but-unrunnable count and is a declared contract. New `catalog.emit()` gives
both generators `--check`; `check.ps1 -Full` runs playable first, coverage
second, and both are green. `COVERAGE_REPORT.md` was stale on 207 unrelated
lines (`OutsideEstimatorDomain`) and is regenerated. No engine change, no other
number moved. Next: T1 (templates become data).

## 2026-09-02 — T1.0: 174 of 377 rows are extractable and uncovered; T1 and T2 survive

Added `validation/extraction_yield.py` (~40 s), which cross-tabulates every
catalog step by resolves-to-SMILES, balances under the LP, and class-uncovered:
174 / 118 / 69 / 6 / 10 / 0 over the six reachable cells; its 75 unbalanceable
and 10 unresolvable rows match `corpus_balance.py`. The 174 span 132 classes,
102 of them single-row; only 6 classes hold three or more rows, so T3 is bounded.
Upper bound if all became templates: template-ready 46 -> 110, intersection
38 -> 66, with 36 of the 64 gained routes held by an unpriceable species.
`corpus_balance.coefficients()` now returns `linprog`'s vector; it is fractional
where the nullspace is 2-D, so T2 needs an integer step. Argument in
`docs/design/extraction-yield.md`; `BACKLOG.md` T1.0 deleted, T2 and T3
rewritten. `./check.ps1` green, 1,264 tests collected, no other number moved.
Next: T0.5 (the two generators disagree), then T1 (templates as data).

## 2026-09-02 — /session runs one task end to end and pushes main

Added `.claude/skills/session/`: take task 1 from `NEXT.md` (or the user's
steering), do it to its done-when, close out through `handoff`, push, confirm.
One task per invocation; the full suite and the tolerance audit stay ask-first,
so a task that needs them is skipped for the next one and the skip reported.
`handoff` Step 8 is now commit and push (fast-forward, never force); its
description no longer says "never push". `CLAUDE.md` session shape points at
the skill. No code, no numbers moved; `./check.ps1` and `check_docs` green.
Next: `/session` in a fresh context, which should take T1.0.

## 2026-09-02 — the handoff is frozen, capped and made repeatable

Moved the seven root monoliths (1.5 MB, 84% narrative) into `docs/history/`,
rewrote the 53 references, and split the milestones file on its own headings into
79 sections (largest 23 KB) behind an index, verified line by line. Added
`CLAUDE.md`, `NEXT.md`, `BACKLOG.md`, this file, `check.ps1`, and
`tools/check_docs.py`, which caps the working set and ratchets existing debt in
both directions. `README.md` 662 -> 561: the Status paragraph ("Layers 0-6
complete; 275 tests" against 1,264) is a table of regenerable numbers, the false
`[done]` on Layer 4.5 and the untrue RDKit-boundary claim are corrected, 32
glyphs gone, qualitative kinetics stated in Known limitations. Decided in
`BACKLOG.md`: delete `discovery/refine.py`; adopt reachable-reactions and reject
a self-scored family checklist; defer the README trim into C1. Added the
`handoff` skill. Next: T1.0, the extractability measurement.
