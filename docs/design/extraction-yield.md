# Extraction yield: what T2 could actually produce

Measured 2026-09-02 by `python validation/extraction_yield.py` (~40 s). This is
T1.0, the gate on the Tier 1 plan in `BACKLOG.md`, which rested on the critique's
estimate that "150 to 250 of 377" catalog steps would extract automatically
(`fable analysis/05-COVERAGE-STRATEGY.md:86`). Nobody had checked.

## The three questions

A row can only be turned into a literal template if every species resolves to a
SMILES (no `*-marker`, nothing that fails to parse), and a strictly positive
coefficient vector exists under the LP in `validation/corpus_balance.py`. It only
adds coverage if its class has no template today (181 of 240 classes).

| resolves | balances | uncovered | rows |
|---|---|---|---|
| yes | yes | yes | 174 |
| yes | yes | no | 118 |
| yes | no | yes | 69 |
| yes | no | no | 6 |
| no | no | yes | 10 |
| no | no | no | 0 |

So 174 of 377 rows are extractable and uncovered, inside the estimate's range.
The 75 that resolve and cannot balance are exactly `corpus_balance.py`'s 75; the
10 that do not resolve are its 10 untestable rows.

## The shape of the 174

They fall in 132 classes: 102 classes with one row, 24 with two, 2 with three, 3
with four and 1 with six (`nucleophilic-substitution`). Only 6 classes have three
or more rows, so T3's clustering into family templates has at most 24 rows to work
on; the rest are literal templates, one per row, forever.

## What they would buy

| | today | if all 174 became templates |
|---|---|---|
| routes template-ready | 46 | 110 |
| routes in the intersection (template- and species-ready) | 38 | 66 |

The 64 gained template-ready routes split 28 into the intersection and 36 held
back by an unpriceable species. The species that hold back more than one route:
hydrogen-cyanide (3), vanadium-pentoxide (3), calcium-carbide, sodium-nitrite,
calcium-silicate, silicon-dioxide and phosphorus-white (2 each). Species work is
therefore half of T2's payoff, not a separate concern.

63 routes stay blocked by a step extraction cannot reach: 49 by one step, 12 by
two, 2 by three. Those steps are mostly the `atoms` failures the balance audit
already classifies (a chromium or a chloride with no named fate), plus the
polymer and marker rows.

## What the measurement cannot say

- The LP is a necessary condition and a weak one. `vanillin-lignin` step 1
  balances at 8 rings in and 10 out; `abe-fermentation` step 1 is three
  reactions on one line. Both are inside the 174-style pass. An extractor that
  atom-maps will refuse these, so 174 is an upper bound on what atom-mapping
  accepts, not a count of templates.
- The coefficient vector is not unique when the element matrix has a nullspace
  of dimension two or more. `phthalic-anhydride-route` step 2 came back as
  `1 3.5625 1 1.125 1 1.75 1` from the minimum-sum LP, where the row's own
  stoichiometry is `1 4.5 1 1 2 2 1`. T2 needs an integer step after the LP
  (smallest integer vector in the feasible cone), not the raw `x`.
- Kinetics. Every extracted row would carry a class-policy `A` and `Ea`, and
  S11 measured that selectivity is a rate ratio between templates racing. T2a
  stands: literal rows load per tier, never into the default library.

## Verdict

T1 and T2 survive. The upper bound is +28 routes in the intersection against
the +10 that P0 measured 22 hand-written template sessions would buy, and the
extractable set does not concentrate in classes a template already covers (the
118 already-covered rows are a separate cell). T3 shrinks to a bounded job of
at most 6 families. The plan's next gate is real, not estimated: run atom-mapping
over the 174 and count how many produce a SMARTS that regenerates the products.
