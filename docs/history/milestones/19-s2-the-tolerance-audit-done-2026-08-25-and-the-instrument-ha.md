## S2 — The tolerance audit  ✅ **DONE 2026-08-25 — and the instrument had to be audited before its findings could be**

Two milestones running had quoted a tolerance-limited number, so
`validation/tolerance_audit.py` re-runs every example at rtol 1e-8 / atol 1e-11
and diffs. It patches the two `run` DEFAULTS rather than editing examples, so an
example that already passes its own tolerance is untouched — which is the
built-in self-check: `lime_cycle` and `roasting_and_the_catalyst_gate` come out
**byte-identical at speedup 1.00**, and if they did not, the harness would be
what is wrong.

**Result: 11 examples swept, and after one fix ZERO print a quotable digit that
moves.** 5 move below 0.1%, 6 are identical.

### ⚠ THE ONE REAL MOVE, AND IT WAS IN THE PANEL THAT EXISTS TO SHOW IT

`workshop` Part 2 — melting a dry solid, whose entire point is the latent-heat
plateau:

| t = 800 s | T | solid |
|---|---:|---:|
| rtol 1e-6 (default) | 389.50 K | 2.0000 |
| rtol 1e-8 | **388.38 K** | **1.9656** |

The default says melting has not started. It has: 1.7% of the charge is gone and
the flask is **1.1 K cooler**, because the melt is absorbing latent heat. The
loose run overshoots the temperature by delaying the onset — of the plateau the
line under it points at.

⚠ **AND FIXING IT COST ONE SECOND.** Tightening Part 2 alone takes the example
from **8.1 s to 9.1 s**, not to 58.9 s. The 7.2x belonged to the other panels,
which move by 4e-4 and are deliberately left alone.

### ⚠⚠ ONE EXAMPLE CANNOT BE SWEPT AT ALL, AND ITS NUMBERS ARE STILL CORRECT

`oil_of_vitriol` **RAISES** at rtol 1e-8, in one call —
`burn(690 K, s8=0.002, o2=0.10)`, the panel that demonstrates the dryout-band
fix. `lu_factor` gets `array must not contain infs or NaNs` on `I - c J`: a **NaN
Jacobian**, after 50.7 s of thrashing.

| that call | SO2 / mol | wall |
|---|---:|---:|
| default tolerance | **0.016000** | 0.7 s |
| rtol 1e-8 | **RAISES** | 50.7 s |
| rtol 1e-8 + 1e-9 mol of SO2 charged | **0.016000** | 1.6 s |
| rtol 1e-8 + 1e-6 mol of SO2 charged | 0.016001 | 2.5 s |
| rtol 1e-7 | **0.016000** | 1.5 s |

A trace of the absent species removes the failure and the answer is unchanged to
six figures — **the same diagnostic that identified this trap in the first
place**. So `oil_of_vitriol`'s results are CONFIRMED and what is exposed is the
engine, not the example. **"It moved" and "it refused" are different findings and
the audit reports them in different rows.**

⚠⚠ **THE ZERO-JACOBIAN-COLUMN TRAP THEREFORE HAS A SECOND TRIGGER.** It was
documented as *a species in the network but absent from a sealed flask*. It is
also reachable by *tightening the tolerance on a flask holding a trace* — same
NaN, same fix. That widens the case for the `LAYER_REABSORB`-style honest
diagonal on the gas block, which is still a session of its own.

### ⚠⚠ AND IT REFUTED A CLAIM THIS PROJECT HAD STARTED TO GENERALISE

M6 measured its kiln running FASTER tight (1.4–3.3 s against 5–13 s) and S1
measured the same on a roast (3.67 against 19.94 s). Swept across every example:
**faster in 2 of 11, slower in 9, worst 7.2x.** The speedup is a property of a
stiff vent fed by slow chemistry, not of tightening. Each local measurement was
right; the pattern they suggested is not there, and believing it would tell the
next session that tightening is free.

### ⚠⚠ AND THE INSTRUMENT MANUFACTURED A FINDING BEFORE IT WAS FIXED

Its first version reported `wait_until` moving by **12.5%**. That number was
`0.07 s of wall` against `0.08 s of wall`; the example's real worst move is
**1.04e-4**. A wall clock is now excised as a **token**, not by dropping the
line — because this project prints physics and timing on one line
(`t = 1353.13 s ... (0.89 s of wall)`), so dropping the line would have hidden
the move in `t`. And keying on the word "wall" would have been worse than
coarse: `lime_cycle` prints `±14.374 W wall`, a heat flux, which is exactly the
kind of number the audit exists to check. **An instrument that cannot tell a
wall clock from a result will invent findings** — the same failure shape as a
coverage number counting a route the engine cannot run.

---
