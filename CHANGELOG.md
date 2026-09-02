# Changelog

Newest first. One entry per session, twelve lines at most, enforced by
`tools/check_docs.py`. When this file passes 400 lines the older half rolls into
`docs/history/changelog-YYYY-MM.md`.

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
