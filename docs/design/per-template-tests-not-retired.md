# The per-template test files are not retired, and the product check is why

Measured 2026-09-13, the session that built
`tools/check_template_products.py`. T1b in `BACKLOG.md` said to build the
row-level product check "and then, and only then, retire the per-template test
files". The check is built and the retirement is refused. This is the reasoning,
so it is not relitigated the next time the file count under `tests/` looks high.

## What T1b assumed

That a per-template test file exists because nothing else can ask whether a
row's SMARTS still makes the products the catalog step says it makes. That is
true, and `tools/build_templates.py` cannot ask it: the column set covers every
field of `ReactionTemplate` and the construction-site walk says every template
is a row, and neither statement is about chemistry. A row can pass both with a
SMARTS that fires on nothing.

`tools/check_template_products.py` asks it, for all 59 rows, in 2.2 seconds,
against the 191 catalog steps their classes claim. That part of T1b stands and
is in `check.ps1`.

## What the files actually assert

The assumption was wrong about the files. Counted over the fourteen candidates —
`test_wacker.py`, `test_skraup.py`, `test_hydroformylation.py`,
`test_vanillin.py`, `test_furans.py`, `test_fermentation.py`,
`test_ring_deactivation.py`, `test_competing_templates.py`,
`test_lead_chamber.py`, `test_mercury_retort.py`, `test_smelting.py`,
`test_phosphate.py`, `test_vitriol.py`, `test_saturation.py`:

**132 of their 208 tests take a network, a vessel or a provider fixture.** They
build a `ReactionNetwork` or integrate a flask, and what they assert is the half
a product-set comparison cannot reach:

- *the selectivity IS the barrier difference and nothing else*
  (`test_hydroformylation.py`), and that it falls when the reactor is heated,
  and that above 450 K the reverse beats it;
- *the copper is a constant of the motion*, and that the declared order is first
  in the alkene and not second, and what the wrong oxygen order costs
  (`test_wacker.py`);
- *the two standard states disagree on the sign of dS*, and that an open flask
  loses its acrolein before it can react (`test_skraup.py`);
- that pricing an unbalanced row is silent, and that the route needs its
  temperature (`test_vanillin.py`).

Rule 8 says every `A` is an order-of-magnitude choice and every `Ea` a band
midpoint, and that **the ordering between two templates is the load-bearing
part**. Those tests are where the ordering is pinned. Deleting them to retire a
file count would delete the chemistry and keep the graph rewrite.

## The decision

The product check replaces at most one assertion inside each file, and in most
of them not even that — a file whose subject is a selectivity never asserted a
product set to begin with. So:

- `tools/check_template_products.py` and its artefact
  `data/catalog/derived/template_products.psv` are the row-level check T2's
  extracted rows must pass. That is what T1b was for.
- No per-template test file is retired. The file count under `tests/` is not a
  target, and no full-suite run is owed for this.
- If a future session wants the count down, the thing to measure is not "which
  files name one template" but "which assertions are duplicated by an
  instrument". The answer today is: the product-set ones, and there are few.
