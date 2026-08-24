"""Render the routes as a readable index: feedstocks -> intermediates -> products.

Writes ``data/catalog/ROUTE_INDEX.md``. Everything in it is derived from
``route_steps.psv`` by ``catalog.route_roles`` -- nothing about which species is
a feedstock and which is an intermediate is written down by hand anywhere, so
this file cannot disagree with the steps it was built from.

Run: ``python tools/build_route_index.py``
"""

from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import catalog as cat  # noqa: E402

ERAS = ["ancient", "alchemical", "1700s", "1800s", "1900s", "modern"]


def main() -> int:
    compounds = cat.load_compounds()
    routes = cat.load_routes()
    steps = cat.load_steps()
    by_route: dict[str, list[cat.Step]] = defaultdict(list)
    for s in steps:
        by_route[s.route].append(s)

    def label(species: str) -> str:
        c = compounds.get(species)
        if c is None:
            return f"*{species}* (no molecular graph)"
        return f"{c.name} `{c.id}`"

    out: list[str] = []
    w = out.append
    w("# Route index: primary compounds, intermediates and products")
    w("")
    w(
        f"{len(routes)} named routes, {len(steps)} steps, "
        f"{len(compounds)} compounds in the catalog."
    )
    w("")
    w(
        "For each route the three lists below are **derived from the steps**, not "
        "declared: a species consumed but never produced inside the route is a "
        "*primary feedstock*; one that is both produced and consumed is an "
        "*intermediate*; one produced and never consumed is a *product or "
        "byproduct*; and one appearing on both sides of a single step is a "
        "*catalyst*. See `tools/catalog.py` for why that is derived rather than "
        "written down."
    )
    w("")
    w(
        "The same species is routinely a feedstock in one route and an "
        "intermediate in another -- acetaldehyde, phenol and sulfuric acid all "
        "are. That is not a conflict; it is the point of indexing them per route. "
        "`data/catalog/derived/species_roles.psv` rolls the counts up per species."
    )
    w("")

    # --- contents -------------------------------------------------------
    w("## Contents")
    w("")
    for era in ERAS:
        ids = [r for r in routes.values() if r.era == era]
        if not ids:
            continue
        w(f"- **{era}** ({len(ids)}): " + ", ".join(f"[{r.name}](#{r.id})" for r in ids))
    w("")

    # --- the routes -----------------------------------------------------
    for era in ERAS:
        era_routes = [r for r in routes.values() if r.era == era]
        if not era_routes:
            continue
        w(f"## {era}")
        w("")
        for route in era_routes:
            roles = cat.route_roles(steps, route.id)
            mine = sorted(by_route[route.id], key=lambda s: s.index)
            w(f'<a id="{route.id}"></a>')
            w("")
            w(f"### {route.name}")
            w("")
            w(f"`{route.id}` &middot; {route.domain} &middot; target: {label(route.target)}")
            w("")
            w(f"> {route.notes}")
            w("")
            w(f"**Primary feedstocks** ({len(roles.feedstocks)})")
            w("")
            w("- " + "\n- ".join(label(s) for s in roles.feedstocks) if roles.feedstocks
              else "- *(none: every species is made inside the route)*")
            w("")
            w(f"**Intermediates** ({len(roles.intermediates)})")
            w("")
            w("- " + "\n- ".join(label(s) for s in roles.intermediates)
              if roles.intermediates
              else "- *(none: a single-step route has no intermediate by definition)*")
            w("")
            w(f"**Products and byproducts** ({len(roles.products)})")
            w("")
            w("- " + "\n- ".join(label(s) for s in roles.products) if roles.products
              else "- *(none)*")
            w("")
            if roles.catalysts:
                w("**Catalysts** (both sides of one step, net stoichiometry zero)")
                w("")
                w("- " + "\n- ".join(label(s) for s in roles.catalysts))
                w("")
            w("| # | step | in | out | conditions | class |")
            w("|--:|---|---|---|---|---|")
            for s in mine:
                rin = " + ".join(s.reactants)
                rout = " + ".join(s.products)
                w(
                    f"| {s.index} | {s.name} | {rin} | {rout} | "
                    f"{s.conditions} | `{s.cls}` |"
                )
            w("")

    # --- the reaction-class index ---------------------------------------
    classes = Counter(s.cls for s in steps)
    w("## Reaction classes used, by frequency")
    w("")
    w(
        "This is the list a template library has to grow into. "
        "`validation/catalog_coverage.py` reports which of them exist today."
    )
    w("")
    w("| class | steps | routes |")
    w("|---|---:|---:|")
    per_class: dict[str, set[str]] = defaultdict(set)
    for s in steps:
        per_class[s.cls].add(s.route)
    for cls, count in classes.most_common():
        w(f"| {cls} | {count} | {len(per_class[cls])} |")
    w("")

    path = os.path.join(cat.CATALOG_DIR, "ROUTE_INDEX.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"wrote {path}  ({len(routes)} routes, {len(steps)} steps)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
