## M2 — The still as a protocol  ✔ **DONE 2026-08-23**

**Both halves landed. The protocol was done first; the 0.85 heart is now met by a
plate column** — `examples/plate_column.py`, **heart 0.8544 mole fraction ethanol
from a 50/50 ethanol/water charge, 8 plates at reflux ratio 5**, and it replays
from its script to **0.000e+00**.

**The protocol** (HANDOFF 76): `Scenario.edges` (`EdgeSpec(kind, a, b, k)` over
`vapour`/`drain`/`thermal`/`meter`), `SWAP_RECEIVER`, `SET_EDGE`,
`Rig.wait_until` + `RigIntegrator.step_until`, `collect_fraction`. **`SAVE_VERSION`
4 → 5.** Three receivers each held a different mixture and the run replayed
exactly; the script carries only bands, never an instant.

**The column** (HANDOFF 77), and it needed one engine fix plus a defect found:

⚠⚠ **THE FIRST COLUMN ATTEMPT FAILED BECAUSE THE STILL HAD NO OPEN END, NOT
BECAUSE OF STARTUP — the diagnosis in this document was wrong.** Every vessel in a
still is declared `k_vent=0` and a receiver is reached only by a DRAIN, so pot +
plates + head + condenser were one **sealed** volume. Measured: **3.34 bar and the
pot at 385.9 K on two plates, 3.77 bar and 389.6 K on eight** — taller is hotter,
which is exactly why adding plates made it worse, why UNIFAC left the range its
correlations cover, and why a band chosen from atmospheric boiling points was
never entered. ⚠ And the *shipped* `fractional_distillation.py` had the same
defect: it was distilling at **3.09 bar with the pot superheating to 548 K**, so
its published cuts (0.060/0.287/0.580 mol, heart 0.523) were taken on a
pressurised trace. Both are fixed by one vent on the condenser, which is where a
real distillation is open to the room, and both examples' numbers moved.

⚠ **The engine fix: `temperature_steady` on a rig vessel was answered by the
vessel's OWN uncoupled derivative.** Every other condition reads the STATE, so
lifting it onto the rig vector by the owner's slice is exact; this one reads the
DERIVATIVE. Measured: a column pinned at 351.22 K and unmoving for 1200 s **timed
out**, and fires in 0.0 s on the coupled root. Same lesson as `step_until`'s, one
level deeper — *it is not only WHEN a condition is located that belongs to the
coupled trajectory, it is what the condition computes.*

⚠ **Two more, both measured.** **Boilup is a plate-efficiency knob, not a clock**
— the same 8 plates at R=5 plateau at **0.8538 at 250 W and 0.8486 at 500 W**, and
the two runs cost the same wall clock, so a distillation example cannot be made
cheaper by turning the mantle up. And **in a good column the head does not move**
(351.19 K ± 0.002 across the whole take-off), so the head is the wrong instrument
for closing that cut and the band goes on the POT's rising bubble point. That does
not weaken "the head is not the condenser" — it is the flip side of it.

⚠ **What it costs:** `examples/plate_column.py` is ~13 min of saturated CPU on 14
coupled vessels, half of it panel 4's replay, and the cold-start FLOOD dominates
rather than the distillation. Declaring the plates already warm changes it by 1 s
— the transient is the phase change. `tests/test_still.py` pins the mechanism at
0–2 plates for ~2 min instead.
