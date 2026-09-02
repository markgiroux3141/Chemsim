## 3. ⚠⚠⚠ A MOLAR-MASS CAP IS DEAD AS AN IDEA, AND THE REASON OUTLIVES THE MEASUREMENT

Measured on the same pick, and **refuted**. ⚠ The table below is the R1 one:
**two of its four rows could not be measured before R1**, because they crashed
on an unpriceable species -- that is what *"it turns two picks into crashes"*
used to mean.

    max_molar_mass   rxn   frontier    build    outcome
    none             644        367    10.6s    hit the 400-species cap
    500 g/mol        519        367   100.6s    hit it too -- and is SMALLER
    400 g/mol        458         83   126.1s    smaller still
    250 g/mol        842        199   380.7s    hit it -- and is BIGGER

**It never closes the fixpoint at any cap, and every cap is ~10x to ~36x
slower.** ⚠⚠ **AND THE TWO ROWS R1 UNLOCKED CHANGE THE FINDING'S SHAPE: THE
REACTION COUNT IS NOT MONOTONIC IN THE CAP.** 519 and 458 are both BELOW the
uncapped 644 and only 250 g/mol goes above it, so *a tighter bound makes a
bigger network* is **true at 250 g/mol and is not a law** -- and it was stated
as one only because the two rows that contradict it were the two that crashed.

What survives all of it, and does not depend on the arithmetic: **the cost is in
the SEARCH and not in the RESULT.** 500 g/mol takes 100 s to produce FEWER
reactions than 10.6 s of uncapped work, because a cap makes the expansion try
combinations it then refuses. And where the bound bites hardest it also
**REDIRECTS** the search into a denser region -- 842 against 644 -- because
refusing the heavy products leaves the light ones to recombine with each other.

⚠⚠⚠ **AND THIS FINDING'S OWN CORRECTION WAS ITSELF WRONG, WHICH IS THE PART
TO READ.** The first write-up recorded the uncapped build at **10.9 s**, making
388 s a **35x** slowdown. The R-series overturned that to **19x**, on the grounds
that sub-panel B builds the identical network at 19.8 / 20.1 / 20.2 s and so the
10.9 s did not reproduce. **It reproduces**: re-running sub-panel F itself gives
**10.5 and 10.6 s**. B and F were never measuring the same thing -- **B builds a
WORLD and F calls `build_network`** -- so the R-series divided F's numerator by
B's denominator, *which is the exact mistake it was accusing the first write-up
of.* Interleaved in one process, identical networks (400 species / 644
reactions) both ways:

    build_network    11.14s   10.67s   10.85s
    World(bench)     20.46s   20.35s

Not a warm cache, and it does not drift with order: the ~9.6 s gap is World and
Vessel construction on top of the network build. **Like for like it is 36x, and
the original 35x was right.** ⚠ A consequence worth carrying forward: **"build"
in sub-panels B and C is a WORLD build and roughly half of it is not discovery
at all** -- which leaves panel C's conclusion untouched, because 10.8 s of
discovery against 107 s of stepping is the same argument as 19.8 against 107.
*A number quoted across two measurement paths is wrong however carefully it is
divided.*
