"""Loader and structural validator for the coverage catalog in ``data/catalog``.

The catalog is three pipe-separated tables and nothing else:

    compounds/*.psv   id | name | smiles | class | role | domains | notes
    routes.psv        route_id | name | era | domain | target | notes
    route_steps.psv   route_id | step | name | reactants | products | conditions | class

Pipe-separated rather than CSV because chemical names are full of commas
("2,4-dinitrophenol") and free of pipes, and because one line per record is the
form a human can actually review. No YAML, no JSON, no dependency beyond the
standard library and RDKit.

## The one design decision worth defending

**A route does not declare which of its species are feedstocks and which are
intermediates.** It declares only the steps. ``route_roles`` then derives the
split from the step graph:

    consumed, never produced   ->  primary feedstock
    produced and consumed      ->  intermediate
    produced, never consumed   ->  product or byproduct
    on both sides of one step  ->  catalyst

A declared split would drift from the steps the moment anyone edited a step and
forgot to edit the declaration, and the drift would be silent. A derived one
cannot drift, and it also answers the question the catalog exists to ask -- what
is an intermediate here -- rather than restating an author's opinion of it.

⚠ The derivation is per route and purely graph-based. A species can be an
intermediate in one route and a feedstock in another (acetaldehyde is both), and
that is correct, not a conflict. It also means a route whose steps are written
loosely will produce loose roles; the roles are exactly as good as the steps.

## Markers

Eight species in ``route_steps.psv`` end in ``-marker`` AND have no entry in the
compound tables: coal, coal tar, collagen, sodium amalgam and the like. They are
rocks, mixtures, alloys and proteins -- things with no single molecular graph.
They are carried so the routes stay balanced and readable, and ``is_marker``
excludes them from the coverage audit rather than giving them an invented
structure. Note that some ids ending in ``-marker`` DO have catalog entries
(``sbr-marker``, ``viscose-marker``); those are real and are audited. Membership
in the compound table, not the suffix, is what decides.
"""

from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field

CATALOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "catalog"
)


@dataclass(frozen=True)
class Compound:
    id: str
    name: str
    smiles: str
    cls: str
    role: str
    domains: tuple[str, ...]
    notes: str
    source_file: str
    line: int


@dataclass(frozen=True)
class Route:
    id: str
    name: str
    era: str
    domain: str
    target: str
    notes: str


@dataclass(frozen=True)
class Step:
    route: str
    index: int
    name: str
    reactants: tuple[str, ...]
    products: tuple[str, ...]
    conditions: str
    cls: str


@dataclass
class RouteRoles:
    """The derived feedstock / intermediate / product split for one route."""

    route: str
    feedstocks: list[str] = field(default_factory=list)
    intermediates: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    catalysts: list[str] = field(default_factory=list)


def _rows(path: str):
    with open(path, encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            yield line_no, [cell.strip() for cell in line.split("|")]


def load_compounds(catalog_dir: str = CATALOG_DIR) -> dict[str, Compound]:
    out: dict[str, Compound] = {}
    pattern = os.path.join(catalog_dir, "compounds", "*.psv")
    for path in sorted(glob.glob(pattern)):
        for line_no, cells in _rows(path):
            if len(cells) != 7:
                raise ValueError(
                    f"{path}:{line_no}: expected 7 fields, got {len(cells)}"
                )
            cid = cells[0]
            if cid in out:
                raise ValueError(f"{path}:{line_no}: duplicate compound id {cid!r}")
            out[cid] = Compound(
                id=cid,
                name=cells[1],
                smiles=cells[2],
                cls=cells[3],
                role=cells[4],
                domains=tuple(d for d in cells[5].split(";") if d),
                notes=cells[6],
                source_file=os.path.basename(path),
                line=line_no,
            )
    return out


def load_routes(catalog_dir: str = CATALOG_DIR) -> dict[str, Route]:
    out: dict[str, Route] = {}
    path = os.path.join(catalog_dir, "routes.psv")
    for line_no, cells in _rows(path):
        if len(cells) != 6:
            raise ValueError(f"{path}:{line_no}: expected 6 fields, got {len(cells)}")
        if cells[0] in out:
            raise ValueError(f"{path}:{line_no}: duplicate route id {cells[0]!r}")
        out[cells[0]] = Route(*cells)
    return out


def load_steps(catalog_dir: str = CATALOG_DIR) -> list[Step]:
    out: list[Step] = []
    path = os.path.join(catalog_dir, "route_steps.psv")
    for line_no, cells in _rows(path):
        if len(cells) != 7:
            raise ValueError(f"{path}:{line_no}: expected 7 fields, got {len(cells)}")
        split = lambda s: tuple(x.strip() for x in s.split("+") if x.strip())  # noqa: E731
        out.append(
            Step(
                route=cells[0],
                index=int(cells[1]),
                name=cells[2],
                reactants=split(cells[3]),
                products=split(cells[4]),
                conditions=cells[5],
                cls=cells[6],
            )
        )
    return out


def is_marker(species: str, compounds: dict[str, Compound]) -> bool:
    """A species with no molecular graph: a rock, a mixture, an alloy, a protein.

    Suffix alone does not decide it -- ``sbr-marker`` is in the compound table and
    is audited like anything else. Absence from the table is what makes something
    a marker, and the ``-marker`` suffix is then required so it is obvious in the
    step file that it was deliberate rather than a typo.
    """
    return species not in compounds


def route_roles(steps: list[Step], route_id: str) -> RouteRoles:
    """Derive the feedstock / intermediate / product split from the step graph."""
    mine = [s for s in steps if s.route == route_id]
    produced: set[str] = set()
    consumed: set[str] = set()
    catalysts: set[str] = set()
    for step in mine:
        both = set(step.reactants) & set(step.products)
        catalysts |= both
        produced |= set(step.products)
        consumed |= set(step.reactants)
    # A catalyst is consumed and produced by the SAME step, so it would otherwise
    # be classified an intermediate. Pulling it out first is what keeps
    # "intermediate" meaning a species the route actually passes through.
    produced -= catalysts
    consumed -= catalysts
    roles = RouteRoles(route=route_id)
    roles.catalysts = sorted(catalysts)
    roles.feedstocks = sorted(consumed - produced)
    roles.intermediates = sorted(consumed & produced)
    roles.products = sorted(produced - consumed)
    return roles



def route_reachable(
    steps: list[Step],
    route_id: str,
    target: str,
    priced,
    covered_classes,
    compounds: dict[str, Compound],
) -> bool:
    """Can the engine's templates get from this route's feedstocks to its TARGET?

    G4's DAG walk, hoisted here so that the two audits that need it cannot
    disagree. ``validation/granularity.py`` scores how much of the coverage
    report's BOTH column is a catalog artefact; ``tools/build_playable.py`` asks
    whether a route is reachable before asking whether it is *fed*. Both ask
    exactly this question, and a copy in each would drift silently.

    ``priced(species) -> bool`` decides whether the engine can put a price on a
    species; ``covered_classes`` is the set of reaction classes a template
    exists for. Both are injected because this module deliberately imports
    nothing but the standard library -- the tier of a compound is an engine
    question and the caller already knows the answer. ``compounds`` is here only
    so that a MARKER product (a rock, a mixture, a protein -- see ``is_marker``)
    does not block a step it appears in; a marker has no molecular graph, so
    "nothing prices it" is not a statement about the chemistry.

    The row scorer that ``COVERAGE_REPORT.md`` uses asks whether EVERY row has a
    template and a price. A route is not a list of rows; it is a DAG with
    alternatives, declared byproducts and workup in it, and the question a
    player asks is whether the target comes out of the end.

    ⚠ **THE TARGET MAY NOT BE CHARGED.** Without that rule ``bayer-process``
    and ``contact-process`` both score reachable by BUYING the thing the route
    exists to make -- Bayer purifies bauxite and the contact process recycles
    its own acid. It is one line and it is the difference between an instrument
    and a flattering one. See MILESTONES §G4.
    """
    mine = sorted((s for s in steps if s.route == route_id), key=lambda s: s.index)
    first_made: dict[str, int] = {}
    first_used: dict[str, int] = {}
    for s in mine:
        for p in s.products:
            first_made.setdefault(p, s.index)
        for r in s.reactants:
            first_used.setdefault(r, s.index)

    def chargeable(x: str) -> bool:
        # priced, and either never made here, or wanted before anything makes it
        if not priced(x):
            return False
        return x not in first_made or first_used.get(x, 1 << 30) <= first_made[x]

    def made_by(x: str, stack: frozenset[str]) -> bool:
        for s in mine:
            if x not in s.products or s.cls not in covered_classes:
                continue
            if not all(priced(p) for p in s.products
                       if not is_marker(p, compounds)):
                continue
            if all(go(r, stack | {x}) for r in s.reactants if r != x):
                return True
        return False

    def go(x: str, stack: frozenset[str]) -> bool:
        if chargeable(x):
            return True
        if x in stack or x not in first_made:
            return False
        return made_by(x, stack)

    if target not in first_made:
        return False
    return made_by(target, frozenset())


def validate(catalog_dir: str = CATALOG_DIR) -> list[str]:
    """Structural check. Returns a list of problems; empty means clean."""
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")

    problems: list[str] = []
    compounds = load_compounds(catalog_dir)
    routes = load_routes(catalog_dir)
    steps = load_steps(catalog_dir)

    for c in compounds.values():
        if Chem.MolFromSmiles(c.smiles) is None:
            problems.append(f"{c.source_file}:{c.line}: unparseable SMILES for {c.id}")

    step_routes = {s.route for s in steps}
    for rid in routes:
        if rid not in step_routes:
            problems.append(f"route {rid} has a header but no steps")
    for rid in step_routes - set(routes):
        problems.append(f"route {rid} has steps but no header")

    for r in routes.values():
        if r.target not in compounds and not r.target.endswith("-marker"):
            problems.append(f"route {r.id}: target {r.target!r} is not a compound id")

    for s in steps:
        for species in s.reactants + s.products:
            if species in compounds:
                continue
            if species.endswith("-marker"):
                continue
            problems.append(
                f"route {s.route} step {s.index}: unknown species {species!r}"
            )

    # A route whose target is never produced by any of its own steps is almost
    # always a copy-paste slip in the header rather than a deliberate statement.
    for r in routes.values():
        made = {p for s in steps if s.route == r.id for p in s.products}
        if r.target not in made:
            problems.append(
                f"route {r.id}: target {r.target!r} is never produced by its steps"
            )

    return problems


def emit(path: str, text: str, *, check: bool = False) -> bool:
    """Write a generated artefact, or in check mode report that it is stale.

    Rule 5 says a generated file is regenerated and never edited, and the only
    way to hold that is to make a stale one FAIL rather than be silently
    rewritten by the next person who runs the generator. ``check=True`` writes
    nothing and returns False with the first differing line named.

    The comparison is on decoded text, not bytes: the reports under
    ``data/catalog`` are CRLF and the generators join with ``
``, so both
    sides go through universal newlines and the terminator never enters it.
    """
    if not check:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {path}")
        return True

    try:
        with open(path, encoding="utf-8") as fh:
            have = fh.read()
    except FileNotFoundError:
        print(f"STALE {path}: does not exist; run the generator")
        return False
    if have == text:
        print(f"ok {path}")
        return True

    # A report line is a whole Markdown paragraph and runs to several hundred
    # characters, so the excerpt is centred on the first differing column
    # rather than taken from the start, where every candidate line looks the
    # same. It is also escaped: the reports carry warning glyphs and em dashes,
    # a Windows console is cp1252, and a diagnostic that raises
    # UnicodeEncodeError buries the staleness it was written to report.
    def _excerpt(line: str, at: int) -> str:
        start = max(0, at - 40)
        cut = line[start:start + 120]
        return cut.encode("ascii", "backslashreplace").decode("ascii")

    old, new = have.splitlines(), text.splitlines()
    for i, (a, b) in enumerate(zip(old, new), 1):
        if a != b:
            at = next(
                (j for j, (x, y) in enumerate(zip(a, b)) if x != y),
                min(len(a), len(b)),
            )
            print(f"STALE {path}: line {i} differs at column {at + 1}")
            print(f"  committed: {_excerpt(a, at)}")
            print(f"  fresh:     {_excerpt(b, at)}")
            break
    else:
        print(f"STALE {path}: {len(old)} committed lines vs {len(new)} fresh")
    print(f"  run the generator and commit the result ({len(old)} -> {len(new)} lines)")
    return False


if __name__ == "__main__":
    issues = validate()
    comp = load_compounds()
    rts = load_routes()
    stp = load_steps()
    print(f"{len(comp)} compounds, {len(rts)} routes, {len(stp)} steps")
    if issues:
        print(f"\n{len(issues)} PROBLEMS")
        for p in issues:
            print("  " + p)
        raise SystemExit(1)
    print("catalog is structurally clean")
