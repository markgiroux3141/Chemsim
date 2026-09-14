# Two of T3's six classes are refused, and for two different reasons

Measured 2026-09-14. Every number below comes from a command named beside it.
T3 asked for six family templates over the six uncovered classes holding three
or more extractable steps each. Four of them are rows now
(`data/templates/templates.psv`, eight rows over four classes). The other two
are refused here, and the reasons are not the same reason.

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

## What the pair has in common

Both are classes whose catalog step is a LUMP of several applications of one
mechanism, and in both cases the fix is upstream of the SMARTS — four mechanism
classes in one, a group value in the other. Neither is a case where the
transformation could not be typed. The four classes that did become rows
(`ammoxidation`, `nucleophilic-substitution`, `nucleophilic-addition`,
`intramolecular-williamson`) each had at least one step that is a single
mechanistic event, and that is what distinguishes them.
