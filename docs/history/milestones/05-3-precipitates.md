## 3. Precipitates?

**Molecular solids: yes, and emergently.** Benzoic acid, 0.05 mol under 55 mol
water, nothing declared — cooling crystallises it out of the fusion law against
γ:

| T / K | dissolved | solid |
|---:|---:|---:|
| 330.0 | 0.050000 | 0.000000 |
| 298.1 | 0.026681 | 0.023319 |
| 275.0 | 0.012236 | 0.037764 |

Filtration, cake porosity and the crystal-crust loss are all built on top.

⚠ **Ionic precipitates: NO, and this is a missing MODEL rather than a missing
template.** `solidifies` is set only where Tm *and* Hfus *and* condensable
(`vessel.py:502`), and an ion has none of those — measured, `[Na+]` and `[Cl-]`
both read `solidifies = False`. **There is no solubility product anywhere in
`src/chemsim`.** So AgCl, BaSO₄, chrome yellow, and every "add A to B and it goes
cloudy" moment cannot happen. The catalog lists `precipitation-metathesis` at 5
steps / 5 routes, and the report files it under "no template" — it is worse than
that, and Milestone 4 is the fix.

⚠ Also absent: any **nucleation barrier or metastable zone**. Precipitation is
ungated by design ("anything can nucleate"), so a supersaturated solution crashes
out instantly. No seeding, no supersaturation, no oiling-out.
