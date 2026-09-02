## ⚠⚠⚠ THE HEADLINE: THE BOUND IS NOT THERE FOR THE REASON EVERYONE ASSUMED

**It is not a discovery-cost bound. It is an INTEGRATION-cost bound**, and
nothing in this repo said so before now.

    glucose + water + air        species   rxn    build      step   sim s   wall s / sim s
    generations=1                     33    20    1.29s     9.97s    3600           0.0028
    fixpoint (hit the 400 cap)       400   644   20.25s   120.25s     300           0.4008

**A fixpoint is ~145x more expensive to INTEGRATE, and the extra 20 seconds of
BUILD is a rounding error next to it.** The same simulated hour is **10 seconds
against 24 minutes**. The solver evaluates all 644 reactions on every
right-hand-side call, and nearly every one of them is kinetically dead at 298 K.

*Everybody had been looking at the wrong half of the cost.* **That is the case
for rate-aware pruning (R4), and it is the only thing on this list that is
really about performance.*
