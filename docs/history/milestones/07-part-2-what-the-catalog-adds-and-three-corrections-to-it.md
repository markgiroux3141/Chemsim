# PART 2 — WHAT THE CATALOG ADDS, AND THREE CORRECTIONS TO IT

`data/catalog` is a genuinely good instrument and its headline is right: the
species side is in decent shape and the reaction side is not. Three of its
numbers need correcting before planning on them.

**(a) It undercounts templates.** `TEMPLATE_CLASSES` in
`validation/catalog_coverage.py:195` only knows `reactions/library.py` and misses
the six proton-transfer templates in `properties/electrolyte.py:305`. Crediting
them: **3 → 6 template-ready routes, 21 → 46 steps covered (6% → 12%)**, with no
code written.

**(b) `acid-base` is two capabilities wearing one label.** Its 15 steps split
into proton transfer with a tabulated pKa (sodium phenoxide + HCl, salicylate
acidification, KNO₃ + H₂SO₄ — all working today) and **carbanion generation**
(malonate + ethoxide, ylides from *n*-BuLi, enolates), which needs C-H pKa values
the electrolyte table does not have. `redox` and `oxidation` have the same
problem: they are outcome labels, and a template is SMARTS on a *mechanism*.
**The taxonomy is too coarse to drive work at this granularity.**

**(c) The 50% UNIFAC headline is diluted.** Split by whether UNIFAC means
anything: **molecular organics 59%, salts/ions/elements/minerals 27%**. The real
gap is 41% of organics. Still the largest *silent* failure in the project — no
decomposition means γ = 1, which in a two-phase calculation asserts the phases do
not separate — but quote it at its true size.
