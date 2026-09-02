## ✔ M12 — The adiabatic energy leak  **DONE 2026-08-24**  *(engine)*

**An insulated flask destroyed 495 J after a precipitation event, against a
0.0087 J chemical budget.** Now reads **+0.15759 K at 3600 s in one call**,
agreeing with itself at every tolerance rung from 1e-6 to 1e-9, with **+0.005 J**
unaccounted over the post-event window. HANDOFF 82 has the full account.

**The cause was in Layer 2, not in the solver, the energy equation or the
precipitation term.** `dissociation_templates` sets `Ea = 60 kJ/mol` for water
autoionization so the elementary-barrier clamp does not fire on water's 55.8
kJ/mol dissociation enthalpy — which leaves detailed balance handing the REVERSE
a 4.2 kJ/mol barrier and a rate constant of **9.4e18 L/(mol s), 9.4e7 times the
collision limit**, for a recombination measured at 1.4e11. Its two heat terms
then sat at ±5.2e9 W around a net of a fraction of a watt, and three consecutive
BDF steps of 167.63 s destroyed 467 of the 495 J while the composition did not
move by a picomole.

⚠ **The asymmetry that allowed it, in one sentence: this project has always
refused an impossible hand-authored pre-exponential and never checked the ones it
DERIVES.** `reactions.thermo.COLLISION_LIMIT` closes that — both pre-exponentials
scaled by one factor, so `K = k_f/k_r` is invariant exactly and Kw stays
1.0022e-14. Exactly one reaction in the project needed it.

**Four fixes were refuted by measurement first**, and each will be proposed
again: the precipitation term (controlled for), the energy equation's algebra
(`q_rxn / (-dH·dn) = 1.000000` pointwise), tolerance in BOTH directions
(tightening the temperature's own budget made it *worse* — 31,324 steps), and the
integrator (Radau and LSODA both get it right and neither survives the prep).

**The audit shipped too**, which was the other half: `Vessel.energy_report()`
prints the GROSS reaction heat beside the net — a net of 1e-3 W looks identical
whether a flask is at rest or whether two 5.2e9 W terms are cancelling to twelve
digits — plus `VesselIntegrator.energy_terms`, `validation/rate_ceiling.py` and
`tests/test_energy_balance.py`.

**It also made everything faster.** The stiffest mode in every aqueous flask got
6.7e7× slower: the benzoic-acid prep runs in **6.0 s where it took 39.4 s**, and
its converged benzoate is unchanged to nine figures (0.199993746).

⚠ **STILL OPEN, REPORTED RATHER THAN FIXED:** the guard is evaluated at 298.15 K,
and `carboxylic_acid_dissociation_rev` **crosses the ceiling at 416.6 K** — a
temperature a reflux reaches. `validation/rate_ceiling.py` prints every crossing.
⚠ And `born_A` is zero for `[Ag+]`, so silver is carried as a NEUTRAL by the ion
transfer term; harmless in one aqueous phase, wrong in an extraction, and
nothing says so.

---
