# Changelog

Newest first. One entry per session, twelve lines an entry and 400 lines the
file, both enforced by `tools/check_docs.py`. At the cap the older half rolls
into `docs/history/changelog-YYYY-MM.md`, where 2026-09-02 to 2026-09-12 is.

## 2026-09-16 — T33: the changelog rolls, and three slow checks come back

`CHANGELOG.md` 458 -> 253 lines: 14 entries, 2026-09-02 to 2026-09-12, moved
verbatim into `docs/history/changelog-2026-09.md` (CRLF both sides, every body
proved byte-identical). Its 400 is now a cap in `check_docs.py` rather than a
sentence in its own header, verified by lowering it in-memory. Then all three
expensive checks at the user's ask: `pytest -q` 1,361 passed / 0 failed in
33m00s, the first wholly green full run on record, against T32's 1 / 1,360 --
T29 fixed the survivor. `tolerance_audit.py` identical to T28 to the digit
(activity 0.1277%, multistep_prep 0.1073%, named_routes raises), so nothing in
T29-T32 moved a trajectory. `build_reachable.py` 1,242 s: 666 pairs, 23,140
reactions, 37 of 68 templates fire, every pair identical -- but it exposed a
stale `silent_templates.psv`, 30 -> 31, T30's `nitrate_esterification`. Next: T2d.

## 2026-09-16 — T29: the corpus does not smelt its own catalysts

`build_playable.MADE_SOMEWHERE` took every step product raw, so a catalyst --
written on BOTH sides of its step -- counted as made by the corpus: ten `nickel`
rows read as smelting nickel, `furfural-route` row 1 (`xylose + water ->
xylose`) as hydrolysing its own pentose. Same guard as `catalog.made_by`, whose
comment already named this file; 21 species leave the set. Second defect: tiers
were read off the per-ROUTE buckets, and a route can miss one species the corpus
makes and one it does not (`steam-reforming` wants `methane` and `nickel`), so
`methane` and `acetic-anhydride` were filed under neither. Tiers are now
species-level. Shelf 71 -> 75 rows, 43/24/4 -> 43/21/11; granting it takes
playable 23 -> 51, every runnable route, against 23 -> 48 before. No chemistry
moved: `check.ps1` green, template products 96/16/9/3/2 unchanged, the other
artefacts byte-identical, and the suite's last red test is green. Next: T33.

## 2026-09-15 — T32: four routes were charged with the thing they exist to make

`needs()` unioned `route_roles().catalysts` in, and a catalyst is derived by
IDENTITY -- both sides of one step -- so `aspirin-route`, `leblanc-process`,
`nitroglycerin-route` and `soap-saponification`, which each make their target in
one row and consume it in the next, demanded it as a starting charge that
`route_reachable` forbids one layer down. Dropping the union IS the
`first_made < first_used` rule and provably so. `route_reachable` had the mirror
defect: `made_by` let a no-op row make its own input, which scored `dissolution`
at +3 atop the C-series ranking; guarded, and no route's verdict moves (51).
Headline holds at 23 playable / 51 runnable, but fed-but-unrunnable 23 -> 24 and
the ceiling 50 -> 52 (`tools/build_playable.py`); `sodium-stearate` off the shelf
(71 rows); six pins re-pinned. Full suite at the user's ask: 1 failed / 1360
passed in 29m51s, from T28's 7 / 1353. Survivor is T29. Glyphs tools 143, tests 819.

## 2026-09-14 — T31: six red scoreboard pins, and four of them were one defect

The six in `test_fermentation`, `test_vanillin` and `test_vitriol` are green;
the pin files go 7 failed -> 1, the survivor `test_playable_levers` being T32's
`needs()` bug. Four were a crossed measurement path rather than four drifts: T2
split `cc.TEMPLATE_CLASSES` into every-tier and `FAMILY_TEMPLATE_CLASSES`, the
helpers kept the all-tier dict while `bp.RUNNABLE`/`bp.PLAYABLE` are family, so
each compared a level on one path (25) with a set on the other (23). Every
difference they pin is identical on both. Two were real: `CLASS_WORTH` 7 -> 8 at
+1 and 22 -> 19 at +0, because T3's `ketene_acid_addition` left
`pyrolysis-dehydration` as `acetic-anhydride-ketene`'s only gap; and 2 of the 8
hydrolysis classes covered, T2 having written an `oleum-hydrolysis` literal row.
Glyph budget `tests` 826 -> 824. Suite still unrun, owed with T32. T32 next.

## 2026-09-14 — T30: the nitration template, and two scoreboards move on two routes

`nitrate_esterification` into `data/templates/templates.psv` at `tier=family`:
A 1e8 the liquid bimolecular choice, Ea 50000 a band midpoint BELOW
`fischer_esterification`'s 55000, nitric acid being the stronger electrophile
and the steps declaring 283-295 K; reversible for spent-acid denitration. 126
rows, 68 family, 103 classes (`tools/build_templates.py --check`). ONE grant,
two +1s, two DIFFERENT routes, neither moving on both: template-ready 65 -> 66
on `guncotton` (`validation/catalog_coverage.py`), runnable 50 -> 51 on
`nitroglycerin-route` (`tools/build_playable.py`), whose uncovered `formulation`
step the DAG walk never needs. Priced +1, +0 and +2 in three places, the +2 a
queue conditional on its own row 8. All three steps `partial`, the step being a
lump. A `rate_ceiling.py` bench: the derived hydrolysis A 8.6e13 crosses at
1895 K, reported not capped. Three pins re-pinned, same 7 as HEAD. T31 next.

## 2026-09-14 — T28: HCN and the alkyl nitrates get a price, 408 refusals -> 401

HCN into `thermochemistry._CURATED_RAW` (CRC 135.10/124.68, dGf derived, Cp
fitted to JANAF) plus a liquid entry, so its shift is two measurements;
`build_network(['CC=N','C#N'])` returns 2 reactions and `methane_ammoxidation` 1
where both built ZERO. Benson had no nitrate-ester KEY at all -- the builder
folds oxo by bond order and a nitro's second oxygen is anionic -- so two lines
took it 698 -> 700 groups and every alkyl nitrate prices (6 measured esters,
mean |err| 10.5). The mononitrates then dropped on a PHYSICAL half they have
measured, that table being generated from the corpus while a step names its
ENDPOINTS: four CAS rows fixed it and nitroglycerin is reachable. Species-ready
90 -> 95, BOTH 51 -> 53, runnable 49 -> 50 (`andrussow`),
`esterification-nitration` 0 -> +1 route. T28c refused. Suite twice, 11 -> 7
failures, all 7 red at HEAD too (T31); tolerance unmoved, `reachable` re-run.

## 2026-09-14 — T2: a program writes 58 templates off the catalog steps

`tools/extract_templates.py` (1.8 s) balances each uncovered step, maps its
atoms by iterated MCS, writes a SMARTS with one bond of context and RUNS it
against the step before keeping it. 58 rows over 52 classes into a generated
`data/templates/literal.psv`; 178 steps refused and counted in
`needs_review.psv` (75 salt, 35 stoichiometry, 24 stereo, 22 coefficients).
`check_template_products.py` 38 -> 96 pass, every extracted row among them, and
all 58 build a reaction in `build_network`. `COVERAGE_REPORT.md` classes 63 ->
115 and template-ready 49 -> 65 (49 on family rows), BOTH 41 -> 51 (41); both
reports split family from literal, and `PLAYABLE.md` scores `family` alone so
its 23/49 headline is unmoved. Red, pre-existing at 5964f16: the shelf audit
test, now T29. `check.ps1` green, 1,357 tests. Next: T28.

## 2026-09-14 — T3: four of six classes become rows, two are refused

Eight family rows in `data/templates/templates.psv` (59 -> 67, 46 -> 50 catalog
classes): two ammoxidations, two nucleophilic substitutions, three nucleophilic
additions, one intramolecular Williamson. `check_template_products.py` 31 -> 38
pass; `COVERAGE_REPORT.md` template-ready 46 -> 49 and BOTH 40 -> 41;
`PLAYABLE.md` runnable 47 -> 49, playable unmoved at 23; `silent_templates.psv`
pool 290 -> 325 and the shelf closure 48 -> 50. Two classes refused with the
measurement in `docs/design/two-refused-template-classes.md`: air oxidation
needs three O2 slots per rewrite, and nitration's polynitrate is unreachable
because `build_network` cannot price the mononitrate it runs through. Two tests
pinned counts a new row must move and now derive the split instead. `check.ps1`
green, 1,353 tests collected, suite and `reachable` still due. Next: T2.

## 2026-09-13 — T1b: every template row against the catalog step it claims

`tools/check_template_products.py` (2.2 s) fires each of the 59 rows over the
`route_steps.psv` steps its class names and compares the product set. 191 steps
tried: 31 pass, 14 partial, 9 wrong-product, 3 no-substrate, 0 no-fire, 2
no-class. Committed as `data/catalog/derived/template_products.psv`, counts
derived as `#!` keys; `--check` is a new `check.ps1` step and eight tests went
into `tests/test_template_table.py`, not a new file (1,345 -> 1,353). Offered
only what a step names it refused `skraup_cyclisation` and a fermentation, so a
slot may draw on a declared three-species medium and the row says when it did.
Retiring the per-template tests is refused: 132 of their 208 build a network or
run a vessel (`docs/design/per-template-tests-not-retired.md`). Chemistry
unmoved. Next: T2, whose two walls are now counted — 8 rows miss only a salt.
## 2026-09-13 — T27: four pKa rows in route-demand order, and three routes come clear

`electrolyte._PAIRS` 37 -> 41 rows, ions 38 -> 42: vanillin 7.40, `dH_diss`
+14.4 off its own 10/25/40/55 C series (Kenttamaa 1970, the determination the
coniferyl alcohol row already used); adipic acid 5.41 with its first proton
re-sourced 4.43 -> 4.42 so both are Howell and Fisher 1958; cinnamic acid 4.42
(Nordstrom and Lindberg 1965); dimethylammonium 10.77, `dH_diss` +50.0 off five
stated temperatures (Everett and Wynne-Jones 1941). `pka_domains.py` panel 3:
corpus ions wanting a pKa 448 -> 444, the routes behind them 51 -> 48, and
`adipic-acid-route`, `perkin-route` and `vanillin-lignin` now have no pKa-shaped
hole. Coverage does not move, for the T23 reason (`COVERAGE_REPORT.md`,
`PLAYABLE.md`, `ROUTE_INDEX.md`, `silent_templates.psv` byte-identical);
`named_routes` diffs only to the refusal notice's ion count and the clock, so no
tolerance run is owed. 1,345 tests, check green. Next: T23's ranking, then T26.
## 2026-09-13 — T23: four pKa rows a player can reach, and both slow checks run

`electrolyte._PAIRS` gains malonic acid's two protons (2.85 / 5.70, Ives and
Prasad 1970, one determination for both), 4-nitrophenol (7.16) and coniferyl
alcohol (9.54), from PubChem's `iupacpka`, each with a `dH_diss` derived from
its own source's temperature series. `python validation/pka_domains.py` panel 2:
shelf ions unpriceable 39 -> 35 over FOUR compounds -> ONE, and it now derives
tannic acid's 35 as a bound rather than rows to write. Coverage does NOT move
and that is the finding: the catalog names its ions one row at a time and none
of these four is one, so `COVERAGE_REPORT.md` (408 refused, 46/90/40) and
`PLAYABLE.md` (23 playable) regenerate byte-identical. Panel 4 now counts the
pairs the scale orders BACKWARDS, 3 of 10 -- a second refutation of a phenol
rule (`docs/design/phenol-pka-rule-refused.md`). 1,342 -> 1,345 tests, check
green, suite twice (28m39s / 30m09s, exit 0), tolerance to the same T10 three.

## 2026-09-13 — T5: the pKa gap is counted, and the phenol rule is refused

`validation/pka_domains.py` (new, ~5 s) sweeps the six ion-producing template
rows over the corpus and the shelf to a fixpoint, so the classes are the rows
rather than a re-typed list of groups. Corpus: 1,078 ions reached, 1,030
unpriceable over 395 compounds, and only 451 of those WANT a pKa -- the other
579 have no priceable parent, so a row for them would be skipped the day it was
written. By class, 208 amine / 139 carboxylic / 104 phenoxide want one, behind
27 / 20 / 21 routes; mineral oxyacid wants ZERO of its 89, which makes it a
thermochemistry gap (T25). Shelf: 39 unpriceable ions over FOUR compounds, 35 of
them tannic acid's powerset. A phenol plateau is refused on two measured
grounds: 39 of 79 gap phenols sit outside the curated substituent range, and two
curated rows share a sigma_sum 3.45 pKa units apart. `./check.ps1` green, 1,338
-> 1,342 tests; T5 and T0.3 out of `BACKLOG.md`, T23 and T25 in.

## 2026-09-13 — T13: an unpriceable species never reaches the integrator

Which half moves was decided by `vessel.build_phase_arrays`: it prices EVERY
species for heat capacity and molar volume before a reaction is looked at, so a
flask holding an unpriceable one cannot integrate whatever its reactions are.
So `_unpriceable` drops unconditionally -- T1d's `tmpl.uses_thermochemistry`
condition read the templates, the wrong half of the engine -- and a new
`_refuse_unpriceable_feed` refuses a CHARGED one at `build_network`'s door,
naming the species, since dropping it would delete matter the caller put in.
Measured: a branched-acid triglyceride + hydroxide went 10 species / 7
reactions / `to_arrays` raising -> 4 / 0 / runnable; `silent_templates.psv`
reads `pool_unpriceable` 41 -> 0, `step_frontier` 306 -> 265. PLAYABLE.md,
COVERAGE_REPORT.md and the 17 named routes regenerate byte-identical (23
playable, 46/90/40). `./check.ps1` green plus 371 tests in 13 modules.

## 2026-09-13 — T18: the plateau is a rule, and a soap route starts running

`properties/carboxylic_pka.py` (new) holds T14's domain predicate, moved out of
`validation/` and rewritten against `Molecule` so Layer 1 gains no RDKit edge --
`matter.Molecule.reprotonated` is the one graph edit it needed. Its plateau
value is DERIVED from `_PAIRS` (4.95, the mean of the two in-domain rows from C3
up, span 4.87-5.02) and never typed. `ThermochemistryProvider` takes an
`ion_fallback` consulted after the curated table misses and before the refusal,
so a measurement is never overridden; `build_network` reports every ion the rule
priced through `notices`. Stearic acid + water: 12 species / 4 reactions -> 21 /
21. Corpus pairs priced 14 -> 32 (`validation/fatty_acid_pka.py --corpus-only`),
species-ready 89 -> 90, runnable 46 -> 47 (`soap-saponification`), shelf 70 -> 72
rows as its two feeds are newly STRANDED, playable unmoved at 23. `./check.ps1`
green, 18 test files + the 17 named routes byte-identical; suite/tolerance due.

## 2026-09-13 — T17: the scorer credits every step product, and a route falls out

`tools/build_playable.shelves` credited `route_roles.products`, so a species a
route makes and then consumes earned nothing -- while `needs` has read step
order since G4. `lime-cycle` row 2 slakes lime and row 3 carbonates it away, so
slaked lime was invisible and `bleaching-powder` stayed chain-blocked behind a
test red for three sessions. Every step product is credited now. Playable 22 ->
23 (`bleaching-powder`, tier 2), ceiling 46 -> 50, fed-but-unrunnable 21 -> 23,
target-only shortfall 6 -> 7; `copper-ii-oxide` is earned off the copper roaster
so its shelf row is deleted, 71 -> 70 rows and intermediates 24 -> 23. The
fouling-rule grid's difference is no longer zero, +1 in both rows, because the
rule it prices was strengthened. Nine pins re-measured over five test files;
`./check.ps1` green and 127 tests pass in the six files that import the scorer.
Suite and tolerance still due at 8; the deep chain's digits are unchanged.

## 2026-09-13 — T14: the plateau is a rule, and the pool is why

`validation/fatty_acid_pka.py` (new, 118 s) counts the carboxylic pKa wall
before anything is written. Corpus: 172 compounds carry a carboxyl, 182 distinct
conjugate pairs, 11 priced, 19 inside the plateau domain, 152 needing their own
measurement. Pool (oleic acid against each of the 36 other natural shelf rows,
11 capped at 400 species): 446 pairs, 253 in the domain — but 243 of those are
oligomers of ONE acid self-esterifying, a series with no last member. Corpus and
pool share 4 of 624. So rows close a list and this is not a list: T14 is
replaced by T18 (the rule), T19 (230 diacids, a different question) and T20 (the
oligoester series is a bound question). The plateau's width is derived from
`_PAIRS` rather than asserted: 4.87 to 5.02 from C3 up. Tests 1309 -> 1329.
No `src/` change, so no trajectory moved; suite and tolerance still due at 7.

## 2026-09-13 — T15: pyrrhotite saturates its own water, and pyrite is FeS2

Two repairs, both curation. `troilite` joins `build_mineral_data.CANDIDATES`
(CRC 1317-37-9, Hfs -100.0, S0s 60.3, Cps and Vm from one compilation), so
`iron-ii-sulfide` stops being the shelf row whose ions sit in the solid block for
ever: `build_shelf` moves it from SOLID IONS, INERT to a crop that dissolves,
lattices 49 -> 50, buildable-with-a-Ksp 28 -> 29, still 2 cation-blocked. pKsp
18.775 is derived, and the flask reaches exactly sqrt(Ksp) = 4.10e-10 M in each
ion and holds femtomoles of H2S over T12's two sulfide pKa rows. Acid keeps it
going and cannot speed it up -- the drive is `k_diss*V*(Qroot - Ksproot)`, so HCl
buys nanomoles an hour. `iron-disulfide` was `[Fe+2].[S-]S[S-]`, FeS3; now FeS2,
a formula fix for `corpus_balance` and not a price. Tests 1307 -> 1309; 46/89/40
and 22 playable unmoved; `./check.ps1` green, `routes` pass (149 tests, 223 s).
NOTE: `test_playable_levers` is RED and already was -- bisected to 188f22a, T8.

## 2026-09-13 — T12: the sulfide is priced by subtraction, and [S;H2] leaves the work order

C2 refused a pKa for HS- -> S2- because the compilations span 12.9 to 19; it was
never a pick. `ion_data` holds [SH-] and [S-2] on one CRC basis, so their
difference IS the dissociation Gibbs energy: 73.7 kJ/mol, pKa 12.91. Anything else
prices [S-2] twice, here and in five sulfide Ksp. `_PAIRS` 32 -> 33 rows (34 priced
ions); `sulfide_protonation` and `hydrosulfide_protonation` go protonation-first,
the reverse sweep refusing a proposal heavier than its flask. Templates 57 -> 59,
chargeable 1167 -> 1174, species-ready 88 -> 89, natural rows 36 -> 37, lattices
with a Ksp that cannot be flasked 5 -> 2 (both now cation-blocked). Work order
20 -> 19 and its head `[S;H2]` is gone: both Claus templates fire on the closure,
24 rows / 48 species, still a fixpoint -- which took 16 MINUTES until the Claus SO2
slot was tightened, `[O]=[S]=[O]` matching a sulfate too and eight such slots being
6561 rewrites of a 24-molecule template (T16 is the twin). `./check.ps1` green.
