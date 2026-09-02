## 4. Condenser — boil a mixture and capture a cut?

**The physics: yes.** A pot, a vapour edge and a cold receiver *are* a still, and
the enrichment is real. Measured, 2 mol ethanol + 2 mol water, 300 W:

| t / s | pot T | head T | head EtOH | head H₂O | x(EtOH) |
|---:|---:|---:|---:|---:|---:|
| 200 | 302.43 | 300.62 | 0.665 | 0.351 | **0.655** |
| 600 | 303.63 | 299.57 | 1.841 | 1.139 | 0.618 |
| 1200 | 313.00 | 290.00 | 2.000 | 1.998 | **0.500** |

Reflux holds a plateau at 352.892 K indefinitely; a still finds the
ethanol/water azeotrope at x = 0.888, 351.17 K. All of that works today.

⚠ **The protocol: NO, and the last row above is why it matters.** The enrichment
*washes back out to 50%* because everything comes over eventually and there is no
way to stop and change the receiver. Fractional distillation IS taking a cut, and
the cut cannot be expressed:

* `World` — the replayable, saveable, scriptable layer — **has no rig at all.**
  Its event kinds are `CHARGE`, `SET_HEAT`, `SET_ENVIRONMENT`, `SET_VENT`,
  `SET_STIRRING`, `SET_SHAKING`, `FILL_HEADSPACE`, `TRANSFER`, `FILTER`. No
  vapour edge, no condenser, no receiver.
* There is no `SWAP_RECEIVER` verb, so **"collect the fraction boiling between
  351 and 355 K" is unsayable** — not merely unimplemented.
* `wait_until` exists and can watch a temperature, but it can only watch the
  vessel it is given, and the head is not a vessel `World` knows about.

**This is the single largest gap between "the physics is there" and "you can play
it", and it is plumbing rather than science.**

---
