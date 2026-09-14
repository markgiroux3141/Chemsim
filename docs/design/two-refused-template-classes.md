# Two of T3's six classes were refused, and for two different reasons

Measured 2026-09-14. Every number below comes from a command named beside it.
T3 asked for six family templates over the six uncovered classes holding three
or more extractable steps each. Four of them are rows now
(`data/templates/templates.psv`, eight rows over four classes). The other two
were refused here, and the reasons were not the same reason — which is why one
of them has since been lifted and the other has not.

**Where they stand now, both settled the same day the refusals were written:**
`esterification-nitration` was refused on a DATA gap, T28a closed it, and the
template job is open with a route behind it. `catalytic-air-oxidation` was
refused on a lumping, and T28c re-refused the split on arithmetic rather than
on judgement. Each section carries its own dated addendum.

## `catalytic-air-oxidation` — a balanced rewrite needs three O2 slots

The class has four steps (`awk -F'|' '$7 ~ /catalytic-air-oxidation/'
data/catalog/route_steps.psv`). Balance each one and the oxygen count is the
whole story:

| step | balanced as written |
|---|---|
| p-xylene -> terephthalic acid | C8H10 + **3** O2 -> C8H6O4 + 2 H2O |
| o-xylene -> phthalic anhydride | C8H10 + **3** O2 -> C8H4O3 + 3 H2O |
| naphthalene -> phthalic anhydride | 2 C10H8 + **9** O2 -> 2 C8H4O3 + 4 CO2 + 4 H2O |
| butane -> maleic anhydride | C4H10 + **3** O2 -> C4H2O3 + 3 H2O + H2 |

Three of the four take three O2 and the fourth takes four and a half. A SMARTS
that balances one of them therefore writes `[OX1]=[OX1]` three times, and a
repeated slot multiplies by its match count — the finding that took a 23 s tool
to 35 minutes once already. A four-slot template is also four nested loops in
`_concrete_reactions` over the discovered species.

The refusal is narrow: it is the *lumping*, not the chemistry. Each row is a
six- to nine-electron oxidation written as one step, and the mechanism under it
is a radical autoxidation — one O2 per rewrite, through a hydroperoxide, an
aldehyde and an acid. Those are four mechanisms and four classes, each of which
would be a family row of its own with two slots. That is the way in, and it is
a work item rather than a refusal of the chemistry.

### The split is REFUSED, 2026-09-14 (T28c), and now on arithmetic

T28 asked for the four rows. They cannot reach `pass`, and the reason is in the
instrument's definition rather than in the chemistry.

`check_template_products.judge` scores ONE application of ONE row against a
step's own reactants and requires `declared <= made` — every declared product
back from a single rewrite. A two-slot mechanism row applied once to p-xylene
and O2 makes a hydroperoxide. It cannot make terephthalic acid, whatever its
barrier says, so each of the four rows scores `partial` on each of the four
steps by construction. "Four rows at `pass`" was never available against these
steps; only a step that names ONE mechanism could be passed, and the corpus does
not carry one for p-xylene.

And the split buys no new chemistry, which is the second half of the refusal.
The four stages the lump decomposes into are already catalog classes on other
routes, and three of them already have templates:

| stage | catalog class | template today |
|---|---|---|
| benzylic C–H + O2 -> hydroperoxide | `autoxidation` | `autoxidation_phenol_cumene_2` (`literal`) |
| carbinol/hydroperoxide -> carbonyl | `alcohol-oxidation` | `aerobic_oxidation` (`family`) |
| aldehyde -> acid | `aldehyde-oxidation` | `peroxide_over_oxidation` (`family`) |
| diacid -> anhydride | — | — |

So the honest work item is smaller and different from "four rows": the existing
`autoxidation` row is cumene's TERTIARY benzylic carbon written literally
(`[C:1][CH1+0:2]([C:3])[c:4]`), and a primary methyl does not match it —
measured, `build_network(['Cc1ccc(C)cc1', 'O=O'], ...)` over the three rows
above returns 2 species and 0 reactions. A `family` `autoxidation` row that
generalises the benzylic C–H would fire on a xylene, and it credits no new class
(`autoxidation` already has a row) and passes no new step. It is worth writing
for the BENCH — a player oxidising p-xylene — and it is worth nothing to the
scoreboard, and those two facts should be stated together rather than one of
them being used to justify the work.

Crediting `catalytic-air-oxidation` to any of these rows would put a six-electron
oxidation's route in the template-ready column on a rewrite that moves one
electron pair. That is the failure mode `validation/catalog_coverage.py:1015`
names, and it is the same one the `esterification-nitration` section above was
right to refuse before its data gap closed.

## `esterification-nitration` — the declared product is unreachable in a run

The mechanism is one line and it fires. This row was written and tried:

```
[CX4:1][OX2H1:2].[OX2H1:3][N+:4](=[O:5])[O-:6]
   >> [CX4:1][O:2][N+:4](=[O:5])[O-:6].[OX2H2:3]
```

`tools/check_template_products.py` scores it `partial` on all three steps,
missing the declared product every time, because each step declares an
*exhaustively* nitrated polyol — glycerol to the trinitrate, pentaerythritol to
the tetranitrate, the cellulose unit to the trinitrate — and one rewrite makes
the mononitrate. So far that is a granularity complaint about the instrument,
and the obvious answer is to let the judge apply a row to its own products.

`build_network` says otherwise. Charging glycerol and nitric acid with that one
template:

```
[build_network] NOTICE: 2 species were DISCOVERED and could not be PRICED, so
the 2 template application(s) that make them were discarded ... Dropped:
O=[N+]([O-])OCC(O)CO, O=[N+]([O-])OC(CO)CO
```

Both mononitrates are refused by all three formation providers: no curated
entry, Joback cannot fragment them, Benson has no value for at least one group.
The network keeps two species and zero reactions. **Nitroglycerin is not one
step further away; it is unreachable, because the intermediate the path runs
through has no standard state.**

That is what makes this a refusal rather than a partial. Crediting the class
would put `guncotton` in the template-ready column on a step whose product does
not exist in any run — the failure mode `validation/catalog_coverage.py:1015`
already names in its own comment. It also settles the instrument question in
the opposite direction from the one the `partial` suggested: a judge that
iterates a row over its own products would have credited this class and hidden
the data gap that actually blocks it.

The way in is a thermochemistry job, not a template job: price an alkyl
nitrate. One curated group value moves all three steps at once, and the
template above is ready for it.

### Done, 2026-09-14 (T28a), and the diagnosis above was half the blocker

The group value was the right lever and there were TWO walls behind it, not one.

**Wall 1, the formation half, as diagnosed.** Benson had no nitrate-ester group
at all -- not a missing number but a missing KEY: `NO2-(O)` and `O-(C)(NO2)`
were never written, because `tools/build_benson_data.py` folded a terminal oxo
oxygen by BOND ORDER and a nitro group's second oxygen is single-bonded and
anionic. RMG's `N5dc-OdO0scO` therefore came out at one oxo instead of two and
was refused, while `benson._is_terminal_oxo` had always counted the anionic
oxygen -- the two halves of one pipeline disagreed about one atom. Two lines in
the builder, 698 -> 700 groups, and the table now prices every alkyl nitrate.
Measured against CRC's own ideal-gas values on the six nitrate esters that have
them: methyl +11.7, ethyl +9.7, n-propyl +9.1, isopropyl +15.2, nitroglycerin
-8.0, PETN +9.1 kJ/mol. Mean |error| 10.5, worst 15.2 -- inside Benson's worst
case over the curated set (17.1) and well outside its median, which is what a
Ridge fit over six DFT species buys.

**Wall 2, and it was invisible until wall 1 came down: the physical half.** With
a formation value in hand both mononitrates still dropped, now for "no Tb/Tc/Pc
from any source and no measured melting point". They are measured -- 1-mono-
nitroglycerin boils at 430.65 K -- and `properties/physical_data.py` had never
heard of them, because that table is generated from the CORPUS and a catalog
step names its ENDPOINTS. `nitroglycerin-route` step 1 lists glycerol and
nitroglycerin; nothing ever asked a database about what the rewrite passes
through. Four CAS numbers in `build_physical_data.CANDIDATES` closed it (and
note they resolve by CAS ONLY: `search_chemical("smiles=...")` raises for every
one, so the corpus sweep's graph key could not have found them even had they
been in the corpus).

**What it bought.** `build_network(['OCC(O)CO', 'O[N+](=O)[O-]'], [the row
above])` now returns 7 species and 4 reactions and nitroglycerin is one of them
-- the claim this section was written to make, inverted. `COVERAGE_REPORT.md`
moved species-ready 90 -> 95 and the intersection 51 -> 53, and `PLAYABLE.md`
re-scored `esterification-nitration` from **+0 routes to +1** (`guncotton`): the
class was worth nothing while its intermediate had no price, and writing the
template is now worth a route. The one species still dropped is the 1,2-di-
nitrate (CAS 621-65-8), which no consulted source gives a boiling or melting
point; the path runs 1-mono -> 1,3-di -> trinitrate around it, and the drop is
reported. **The refusal in this section is lifted and the template job is open.**

## What the pair has in common

Both are classes whose catalog step is a LUMP of several applications of one
mechanism, and in both cases the fix is upstream of the SMARTS — four mechanism
classes in one, a group value in the other. Neither is a case where the
transformation could not be typed. The four classes that did become rows
(`ammoxidation`, `nucleophilic-substitution`, `nucleophilic-addition`,
`intramolecular-williamson`) each had at least one step that is a single
mechanistic event, and that is what distinguishes them.
