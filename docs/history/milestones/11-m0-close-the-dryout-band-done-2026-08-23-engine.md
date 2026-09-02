## M0 — Close the dryout band  ✔ **DONE 2026-08-23**  *(engine)*

The one live wrong answer, and it is closed: **690 K went 1.1e-01 → 1.9e-11**
created oxygen. HANDOFF items 72 and 73 are the record.

**The fix was the CLAMP, not the gates.** `x1 = nL1 / max(N1, DRYOUT_MOLES)` put
the mole-fraction floor on the same scale as the gate multiplying it, so a flask
below that scale had x summing to 0.57 and every activity understated by that
factor. The floor is now `MOLE_FRACTION_DENOM = 1e-30` — 24 decades below the
gate — and the rule is *a clamp that exists to avoid 0/0 must not double as a
gate.*

⚠ **And the work order's own prescription — make the gates DISJOINT, as item 25
did — is WRONG here, measured.** It closes the band and breaks a condenser:
disjointness leaves a dead zone where both halves are zero, and a condenser comes
to rest exactly there. The head stalled at 9.998e-07 mol and **the reflux plateau
went 352.89 → 370.39 K.** The pair stayed complementary (`wet + dry == 1`
exactly for a single liquid). **Whether a gate pair should be disjoint or
complementary depends on whether its dead zone is survivable** — item 25's halves
oppose each other, these two are one flux written twice.

**What is left at 690 K with O2 limiting (~1e-5) is the depleted reactant, not
the band** — with O2 non-limiting the same flask reads 1.9e-11 — and **its value
at default tolerance is luck**: nudging the INERT nitrogen charge by 0.5% swings
it five orders of magnitude. So the burner's 730 K row moved from 2.0e-09 to
5.2e-06 and that is **reported as a finding**, not a regression: it was never an
invariant. The residual belongs to **M7**.

**What it hands the rest of the plan:**
* **M2 inherits a sound evaporation block** — the reflux plateau is now steady
  indefinitely rather than drifting, which is what a fractional-distillation
  protocol has to build on.
* **M3 and M6 inherit the gate-shape rule above.** A solubility product and a
  solid-phase reaction each need a "is this phase here" gate, and the question to
  ask first is now *what happens in my dead zone*, not *is it smooth*.

---
