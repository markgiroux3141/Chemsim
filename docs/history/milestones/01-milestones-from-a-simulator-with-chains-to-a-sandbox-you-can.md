# Milestones: from "a simulator with chains" to "a sandbox you can play"

Written 2026-08-22, after auditing `data/catalog` (1,583 compounds, 173 routes)
and probing four capability questions against the running code. Every number
below is measured, not estimated; the probes are reproducible from the snippets
named in each section.

⚠⚠⚠ **THE LIVE ARC IS THE R-SERIES ("react until done"), added 2026-08-31.
The P-SERIES IS COMPLETE (P0-P4) and the C-series is PAUSED. R1 is DONE
2026-09-01 -- an unpriceable species is the fourth REPORTED coverage limit now,
and closing the crash showed the picker's own two-row pick has FIVE unpriceable
species and zero reactions. R2 and R5 are DONE 2026-09-01 -- the BLAS cap
lives at the entry points (`chemsim.threads`, never `chemsim/__init__`) and
REACT FURTHER writes the raised bounds back into the bench boxes the next pour
reads. R3 is DONE 2026-09-01 -- `prune_threshold` is DELETED (SAVE_VERSION 9):
it could not be wired even in principle, because the pruning it promised needs
the CHARGE and a Scenario does not contain the charge. R4 and R6 are open.**
Jump to `# THE R-SERIES`
near the end of this file;
it opens with the measurement that changed the order. Everything above it is
the record of how the engine got here and remains the authority on what was
built and why.

**The one-line finding: the engine is open-ended and the content is not.** There
are no recipes anywhere in this project — templates are SMARTS rewrites applied
to whatever species are present, and `build_network` discovers reactions to a
fixpoint. A player can already mix anything. The reason most mixtures do nothing
was that the library is 10 templates against the catalog's 197 reaction
classes. ⚠ **As of M5 that reads 34 templates against 212 classes, 29 of them
covered** — the shape of the problem changed but not its direction.

---
