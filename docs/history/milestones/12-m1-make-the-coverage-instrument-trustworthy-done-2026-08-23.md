## M1 — Make the coverage instrument trustworthy  ✔ **DONE 2026-08-23**

All three parts landed. **The corrected baseline is 33/377 steps (8.8%) and
4/173 routes**, against the 46/377 and ~6 routes predicted here — and the reason
for the gap is the milestone's own finding.

**1. The instrument was miscounting in three separate ways.**
* It knew only `reactions/library.py`, missing the six dissociation templates in
  `properties/electrolyte.py`. **14 templates, not 10** — and `library.py` holds
  8, so even the 10 was wrong.
* ⚠ **Crediting the six was NOT the lookup-table edit predicted.** The 21 → 46
  arithmetic needed `deprotonation` (6 steps) to be proton transfer. **Five of
  its six rows are carbanion generation** — malonate and acetoacetate anions, a
  Wittig ylide, two enolates — exactly the capability §2(b) says has no template.
  Crediting the class would have made the audit *less* truthful, which is the
  failure this milestone exists to prevent.
* And the summary print had a variable-shadowing bug reporting **"20 compounds"
  and coverage of 5520%**. Fixed.

**2. The fix was the TAXONOMY, not a "partial" coverage level.** `acid-base`,
`redox`, `oxidation` and `deprotonation` were OUTCOME labels spanning several
mechanisms each, and a template is SMARTS on a MECHANISM. **32 rows re-labelled**
to the mechanism their own reactants and products show; the full decision table
is in `data/catalog/README.md`. Once classes are specific enough, "is there a
template" has a yes/no answer and the mapping needs no notion of partial.

⚠ It also **reconciled a contradiction in this document**: `acid-displacement`
was listed both as covered and as a top *missing* class. Both were right about
different rows — 1 of its 4 steps needs only proton transfer, and 3 need a
gypsum precipitation, i.e. **M3**.

⚠ Two rules fell out, both in the catalog README: *the class is the mechanism;
whether a reagent is priced is a SPECIES question the audit counts separately*
(so Kjeldahl's boric-acid titration is `proton-transfer` even though boron has no
oxyacid template), and *a step's NAME can lie; its reactants cannot* —
`williamson-ether`'s "alkoxide formation" reads `phenol + NaOH → phenoxide`, so
the phenol template does cover it.

**3. The marginal-unlock table is in `COVERAGE_REPORT.md`, and it revises the
numbers this document was planned against.** Splitting outcome classes into
mechanisms necessarily *lowers* per-class unlock, so:

| | this document estimated | measured after M1 |
|---|---|---|
| routes one class away | 61, from 46 classes | **64, from 50 classes** |
| best single template | 6 routes | **3 routes** (`electrolysis`, `catalytic-air-oxidation`) |
| best twelve templates | 31/173 | **30/173** |
| best twenty | — | **43/173** |

⚠ **The shape of the conclusion is unchanged and now measured: there is no
lever.** 64 routes are one class away and they want 50 different classes. Plan
for a target, never for completeness — M5's framing stands.

⚠ **A note on the greedy curve's tie-break, because it is easy to get wrong.**
Maximising "routes unlocked outright" hits zero after ~15 classes: every route
left needs two or more. A loop that stops there reports a curve that flattens
because *it* gave up. So when nothing unlocks a route alone, the next class is
the one appearing in the most remaining routes — those rows show `+0` honestly. A
template can be the right thing to build next and still unlock nothing yet.

---
