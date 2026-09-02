## 1. Can a player mix two arbitrary things and have something happen?

**Yes, mechanically — this is already the architecture.** Nothing is keyed by
recipe. Measured, with `alcohol_chemistry()` loaded and no reaction named:

| charged | reactions found | discovered |
|---|---:|---|
| ethanol + acetic acid | 4 | ethyl acetate, water, diethyl ether, ethene |
| ethanol + toluene | 2 | diethyl ether, water, ethene |
| ethanol + water | 2 | diethyl ether, ethene |
| acetone + hexane | 0 | nothing |
| toluene + water | 0 | nothing |

⚠ **And "nothing happens" is not the same as "the flask is inert."** Where no
SMARTS matches, the vessel is still a real physical mixture: VLE, LLE, mutual
solubility, dissolution, heat capacity. Toluene + water separates into two
layers and steam-distils at 358.31 K without a single reaction.

**So the honest statement is: the mechanism is fully general; the library covers
8-11 of 197 reaction classes.** That is a content problem, not a design one, and
it is what Part 2 is about.

⚠ One engineering consequence to design for: mixing two things means BUILDING A
NETWORK at charge time (0.45 s for a 4-species case, longer for a rich one). A
sandbox where the player mixes freely needs that cached and bounded, or the UI
stalls on every pour.
