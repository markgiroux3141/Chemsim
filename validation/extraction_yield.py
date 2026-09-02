"""T1.0: how many catalog rows could a template EXTRACTOR actually produce?

The Tier 1 plan in ``BACKLOG.md`` (T1 templates-as-data, T2 literal extraction)
rests on an estimate of "150 to 250 of 377" that nobody had checked. A row is
extractable only if three things hold at once, and the plan only gains from it
if a fourth does:

  resolves   every species has a SMILES -- no ``*-marker``, nothing that fails
             to parse -- so there is a graph to atom-map;
  balances   a strictly positive coefficient vector exists under the LP in
             ``corpus_balance.py`` (its ``x`` is taken, not re-derived), so
             the SMARTS has a stoichiometry to carry;
  uncovered  the row's class has no template today, so extracting it would
             add coverage rather than duplicate a hand-written family template.

This prints the eight-cell cross-tab and then breaks the cell that matters --
resolves AND balances AND uncovered -- down by class, because a class with one
row is one literal template and a class with three or more is a family
candidate (T3). It also says how many ROUTES the extractable rows would
complete, since a route needs every step and a row count overstates that.

Run: ``python validation/extraction_yield.py`` (~15 s).
"""

from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, os.path.join(_ROOT, "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

import catalog as cat  # noqa: E402
import corpus_balance as cb  # noqa: E402
from catalog_coverage import TEMPLATE_CLASSES  # noqa: E402


def classify(step, compounds):
    """(resolves, balances, uncovered, coefficient vector or None)."""
    sp = list(step.reactants) + list(step.products)
    uncovered = step.cls not in TEMPLATE_CLASSES
    if any(cat.is_marker(x, compounds) for x in sp):
        return False, False, uncovered, None
    try:
        counts = [cb.formula(compounds[x].smiles) for x in sp]
    except Exception:  # noqa: BLE001
        return False, False, uncovered, None
    x = cb.coefficients(counts, len(step.reactants))
    return True, x is not None, uncovered, x


def main() -> int:
    compounds = cat.load_compounds()
    steps = cat.load_steps()
    routes = cat.load_routes()

    rows = [(s, *classify(s, compounds)) for s in steps]
    cells = Counter((r, b, u) for _, r, b, u, _ in rows)

    print("=" * 74)
    print("WHAT COULD AN EXTRACTOR PRODUCE? -- 377 rows, three questions")
    print("=" * 74)
    print(f"   {len(steps)} steps, {len({s.cls for s in steps})} classes, "
          f"{len(TEMPLATE_CLASSES)} classes with a template")
    print()
    print("   resolves  balances  uncovered   rows")
    for r in (True, False):
        for b in (True, False):
            for u in (True, False):
                if r is False and b is True:
                    continue  # cannot balance what has no formula
                print(f"   {str(r):8s}  {str(b):8s}  {str(u):9s}  {cells[(r, b, u)]:4d}")
    n_res = sum(1 for _, r, _, _, _ in rows if r)
    n_bal = sum(1 for _, r, b, _, _ in rows if r and b)
    n_unc = sum(1 for _, _, _, u, _ in rows if u)
    target = [(s, x) for s, r, b, u, x in rows if r and b and u]
    print()
    print(f"   {n_res:3d} resolve to SMILES on every species")
    print(f"   {n_bal:3d} of those balance under the LP")
    print(f"   {n_unc:3d} rows carry a class with no template")
    print(f"   {len(target):3d} are EXTRACTABLE AND UNCOVERED -- the number the plan rests on")

    by_class = defaultdict(list)
    for s, x in target:
        by_class[s.cls].append((s, x))
    sizes = Counter(len(v) for v in by_class.values())

    print()
    print("=" * 74)
    print("THE EXTRACTABLE-AND-UNCOVERED ROWS, BY CLASS")
    print("=" * 74)
    print(f"   {len(by_class)} classes. Rows per class: "
          + ", ".join(f"{k} rows x {sizes[k]} classes" for k in sorted(sizes, reverse=True)))
    print(f"   {sum(v for k, v in sizes.items() if k >= 3):3d} classes with 3+ rows "
          "(family candidates, T3)")
    print(f"   {sizes[1]:3d} classes with exactly 1 row (one literal template each)")
    print()
    for cls in sorted(by_class, key=lambda c: (-len(by_class[c]), c)):
        print(f"   {len(by_class[cls]):3d}  {cls}")
        for s, x in by_class[cls]:
            coef = " ".join(f"{v:g}" for v in x)
            print(f"        {s.route} {s.index}: {' + '.join(s.reactants)} -> "
                  f"{' + '.join(s.products)}   [{coef}]")

    # Rows that resolve and balance but are already covered: an extractor would
    # reproduce a hand-written template here, which buys nothing.
    dup = [s for s, r, b, u, _ in rows if r and b and not u]
    print()
    print("=" * 74)
    print("EXTRACTABLE BUT ALREADY COVERED -- an extractor would duplicate these")
    print("=" * 74)
    dc = Counter(s.cls for s in dup)
    print(f"   {len(dup)} rows in {len(dc)} classes")
    for cls, n in dc.most_common():
        print(f"   {n:3d}  {cls} -> {TEMPLATE_CLASSES[cls]}")

    # The blockers, by class, because those rows are what extraction cannot reach.
    print()
    print("=" * 74)
    print("UNCOVERED ROWS EXTRACTION CANNOT REACH -- by reason and class")
    print("=" * 74)
    for label, pred in (
        ("a marker or unparseable SMILES", lambda r, b: not r),
        ("resolves but cannot balance", lambda r, b: r and not b),
    ):
        blocked = [s for s, r, b, u, _ in rows if u and pred(r, b)]
        bc = Counter(s.cls for s in blocked)
        print(f"   {len(blocked):3d} rows, {len(bc)} classes: {label}")
        for cls, n in bc.most_common():
            print(f"        {n:3d}  {cls}")

    # Routes: a route is completed only when every step it carries is covered
    # by a template today OR extractable. Count what extraction would add.
    print()
    print("=" * 74)
    print("ROUTES -- what the extractable rows would complete")
    print("=" * 74)
    ok_step = {(s.route, s.index) for s, r, b, u, _ in rows if (not u) or (r and b)}
    done_today = [rid for rid in routes
                  if all(s.cls in TEMPLATE_CLASSES for s in steps if s.route == rid)]
    after = [rid for rid in routes
             if all((s.route, s.index) in ok_step for s in steps if s.route == rid)]
    gained = sorted(set(after) - set(done_today))
    print(f"   {len(done_today):3d} routes template-ready today")
    print(f"   {len(after):3d} routes template-ready if every extractable row became a template")
    print(f"   {len(gained):3d} routes gained:")
    for rid in gained:
        mine = [s for s in steps if s.route == rid]
        need = [s for s in mine if s.cls not in TEMPLATE_CLASSES]
        print(f"        {rid}  ({len(need)} of {len(mine)} steps extracted)")
    partial = [rid for rid in routes if rid not in after]
    still = Counter()
    for rid in partial:
        mine = [s for s in steps if s.route == rid]
        blocked = [s for s in mine if (s.route, s.index) not in ok_step]
        still[len(blocked)] += 1
    print(f"   {len(partial):3d} routes still blocked by at least one unextractable step: "
          + ", ".join(f"{still[k]} by {k}" for k in sorted(still)))

    # The number the project quotes is the INTERSECTION -- template-ready AND
    # species-ready -- so a route extraction completes counts only if its
    # species are priceable too. Recomputed here the way corpus_balance does it.
    print()
    print("=" * 74)
    print("THE HEADLINE -- how many gained routes are species-ready as well")
    print("=" * 74)
    import catalog_coverage as cc

    from chemsim.properties import (
        ThermochemistryProvider,
        UnifacProvider,
        VolatilityProvider,
    )
    from chemsim.properties.electrolyte import electrolyte_provider

    thermo = ThermochemistryProvider()
    vol = VolatilityProvider(thermo)
    ionic = electrolyte_provider(base=thermo, volatility=vol)
    unifac = UnifacProvider()
    tier = {c.id: cc.audit_compound(c, thermo, vol, ionic, unifac)["tier"]
            for c in compounds.values()}

    def species_ready(rid):
        sp = {x for s in steps if s.route == rid for x in s.reactants + s.products}
        return all(tier[x] != "refused" for x in sp if x in tier)

    both_today = [rid for rid in done_today if species_ready(rid)]
    both_after = [rid for rid in after if species_ready(rid)]
    print(f"   {len(both_today):3d} routes in the intersection today")
    print(f"   {len(both_after):3d} routes in the intersection if every extractable row "
          "became a template")
    for rid in sorted(set(both_after) - set(both_today)):
        print(f"        {rid}")
    not_ready = sorted(rid for rid in gained if not species_ready(rid))
    print(f"   {len(not_ready):3d} gained routes are template-ready only -- a species is "
          "unpriceable:")
    for rid in not_ready:
        sp = {x for s in steps if s.route == rid for x in s.reactants + s.products}
        bad = sorted(x for x in sp if x in tier and tier[x] == "refused")
        print(f"        {rid}: {', '.join(bad)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
