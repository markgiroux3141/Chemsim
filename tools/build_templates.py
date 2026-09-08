"""T1 -- regenerate ``chemsim.reactions.template_data`` from the template table.

    python tools/build_templates.py            # writes the module
    python tools/build_templates.py --check    # verify only; a stale module fails
    python tools/build_templates.py --dry-run  # report only, write nothing

One input, ``data/templates/templates.psv``: 57 rows, one per template, every
field of ``ReactionTemplate`` in a column. The output is a generated Python
module, for the same reason ``ion_data``, ``mineral_data``, ``physical_data``,
``element_data``, ``shelf_data`` and the Benson tables are -- ``src/chemsim``
reads no file under ``data/`` at run time, because the package is installed from
``src`` alone.

## WHY A TEMPLATE STOPS BEING A FUNCTION

A template was a hand-written Python function with a docstring, a comment block
and a place in one of four modules. 240 catalog reaction classes at the
historical +3 to +5 per session is ~40 sessions, and T1.0 measured the ceiling:
174 of the 377 catalog steps are extractable and sit in an uncovered class. A
row is something an extractor can write; a function with a comment block is not.

## THE TWO CHECKS THIS SCRIPT IS, AND THE SECOND IS THE POINT

**The column set covers every field.** ``ReactionTemplate`` has thirteen fields
and this script reads them off the dataclass rather than listing them, so a new
field breaks the build until the table gains a column. That is P4's lesson,
which cost three milestones: ``TemplateSpec`` silently dropped ``orders``,
``solid_catalyst``, ``electrons`` and the three ``hammett_*`` fields, and the
assertion that found the last three was about the SET of fields rather than
about whichever field somebody remembered.

**Every row reproduces its constructor, field for field.** The 57 constructors
still exist; this script walks them with ``ast``, calls each with its default
arguments, and refuses if any field differs from the row of the same name. So
the table is not a transcription anyone has to trust -- it is checked against
the code it will replace, and it stays checked until the switch-over deletes
the constructors.

**THE GENERATED MODULE IS NOT WIRED IN YET.** Nothing imports it; the engine
still builds templates from the constructors. The switch-over -- the
table-driven test, ``TEMPLATE_CLASSES`` going away, and the constructors
becoming thin wrappers -- is the second half of T1.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import os
import sys
from dataclasses import MISSING, fields

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from chemsim.reactions.template import ReactionTemplate  # noqa: E402

PSV = os.path.join(_ROOT, "data", "templates", "templates.psv")
OUT = os.path.join(_ROOT, "src", "chemsim", "reactions", "template_data.py")

TIERS = ("family", "literal")

# The modules whose ``ReactionTemplate`` construction sites this table replaces.
# The same four ``catalog_coverage.template_counts`` walks, and the count it
# reports has to keep agreeing with the number of rows here.
CONSTRUCTOR_MODULES = {
    "chemsim.reactions.library": os.path.join(
        _ROOT, "src", "chemsim", "reactions", "library.py"),
    "chemsim.reactions.synthesis": os.path.join(
        _ROOT, "src", "chemsim", "reactions", "synthesis.py"),
    "chemsim.reactions.electrochemistry": os.path.join(
        _ROOT, "src", "chemsim", "reactions", "electrochemistry.py"),
    "chemsim.properties.electrolyte": os.path.join(
        _ROOT, "src", "chemsim", "properties", "electrolyte.py"),
}


# ---------------------------------------------------------------------------
# the fields, read off the dataclass so a new one cannot be dropped
# ---------------------------------------------------------------------------


def template_fields() -> dict[str, object]:
    """``ReactionTemplate``'s own fields -> their defaults.

    ``_rxn`` is the compiled RDKit reaction, derived in ``__post_init__`` from
    the SMARTS, so it is not data and is not a column.
    """
    out: dict[str, object] = {}
    for f in fields(ReactionTemplate):
        if f.name.startswith("_"):
            continue
        out[f.name] = None if f.default is MISSING else f.default
    return out


FIELD_DEFAULTS = template_fields()

# The curation columns -- what a row says that a ``ReactionTemplate`` does not.
CURATION_COLUMNS = ("tier", "class", "source", "notes")

# Column order in the file. ``Ea`` is spelled ``Ea_J`` so the unit is in the
# header, and the SMARTS sits second from last because it runs to 200 characters
# and would otherwise bury every numeric column.
COLUMNS = (
    "name", "tier", "class", "phase", "reversible", "A", "Ea_J", "alpha",
    "orders", "solid_catalyst", "electrons", "hammett_rho", "hammett_slot",
    "hammett_saturation", "smarts", "source", "notes",
)
_COLUMN_FIELD = {"Ea_J": "Ea"}


def check_columns() -> None:
    """Every ``ReactionTemplate`` field has a column, and no column is spare."""
    covered = {_COLUMN_FIELD.get(c, c) for c in COLUMNS} - set(CURATION_COLUMNS)
    missing = set(FIELD_DEFAULTS) - covered
    spare = covered - set(FIELD_DEFAULTS)
    if missing or spare:
        raise SystemExit(
            f"{PSV}: the column set and ReactionTemplate's fields disagree.\n"
            f"  fields with no column: {sorted(missing)}\n"
            f"  columns with no field: {sorted(spare)}\n"
            "A template field that does not round-trip is a field the game does "
            "not have -- see this script's docstring and TemplateSpec's."
        )


# ---------------------------------------------------------------------------
# reading the table
# ---------------------------------------------------------------------------


def _num(cell: str, where: str) -> float:
    try:
        return float(cell)
    except ValueError:
        raise SystemExit(f"{where}: {cell!r} is not a number") from None


def read_table(path: str = PSV) -> list[dict]:
    """``templates.psv`` -> rows, validated structurally and nothing more.

    An empty optional cell means the ``ReactionTemplate`` default, taken off the
    dataclass, so a default lives in exactly one place.
    """
    rows: list[dict] = []
    seen: set[str] = set()
    with open(path, encoding="utf-8") as fh:
        for n, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            cells = [c.strip() for c in line.split("|")]
            where = f"{path}:{n}"
            if len(cells) != len(COLUMNS):
                raise SystemExit(
                    f"{where}: expected {len(COLUMNS)} fields "
                    f"({' | '.join(COLUMNS)}), got {len(cells)}"
                )
            cell = dict(zip(COLUMNS, cells))
            name = cell["name"]
            if not name:
                raise SystemExit(f"{where}: a template needs a name")
            if name in seen:
                raise SystemExit(
                    f"{where}: {name!r} appears twice. A template's name is what "
                    f"every report and every Snapshot calls the reaction, so it "
                    f"is the key here."
                )
            seen.add(name)
            if cell["tier"] not in TIERS:
                raise SystemExit(
                    f"{where}: tier {cell['tier']!r} is not one of {TIERS}. The "
                    f"tier is what keeps a literal row out of the default "
                    f"library -- see T2a in BACKLOG.md."
                )
            if cell["reversible"] not in ("yes", "no"):
                raise SystemExit(
                    f"{where}: reversible is {cell['reversible']!r}, not "
                    f"'yes' or 'no'"
                )
            row = {
                "tier": cell["tier"],
                "catalog_classes": tuple(
                    c.strip() for c in cell["class"].split("+") if c.strip()),
                "source": cell["source"],
                "notes": cell["notes"],
                "name": name,
                "smarts": cell["smarts"],
                "A": _num(cell["A"], f"{where} A"),
                "Ea": _num(cell["Ea_J"], f"{where} Ea_J"),
                "reversible": cell["reversible"] == "yes",
                "phase": cell["phase"],
                "alpha": (FIELD_DEFAULTS["alpha"] if not cell["alpha"]
                          else _num(cell["alpha"], f"{where} alpha")),
                "orders": (None if not cell["orders"] else tuple(
                    _num(o, f"{where} orders") for o in cell["orders"].split(","))),
                "solid_catalyst": cell["solid_catalyst"] or None,
                "electrons": (FIELD_DEFAULTS["electrons"] if not cell["electrons"]
                              else int(cell["electrons"])),
                "hammett_rho": (
                    FIELD_DEFAULTS["hammett_rho"] if not cell["hammett_rho"]
                    else _num(cell["hammett_rho"], f"{where} hammett_rho")),
                "hammett_slot": (
                    FIELD_DEFAULTS["hammett_slot"] if not cell["hammett_slot"]
                    else int(cell["hammett_slot"])),
                "hammett_saturation": (
                    FIELD_DEFAULTS["hammett_saturation"]
                    if not cell["hammett_saturation"]
                    else _num(cell["hammett_saturation"],
                              f"{where} hammett_saturation")),
            }
            if not cell["source"]:
                raise SystemExit(
                    f"{where}: {name!r} has an empty source. A barrier without "
                    f"its provenance is a number nobody can check."
                )
            rows.append(row)
    if not rows:
        raise SystemExit(f"{path}: no rows")
    return rows


def build(row: dict) -> ReactionTemplate:
    """One row -> the template it describes. Validation is the constructor's."""
    return ReactionTemplate(**{f: row[f] for f in FIELD_DEFAULTS})


# ---------------------------------------------------------------------------
# the check that matters: every row reproduces its constructor
# ---------------------------------------------------------------------------


def constructor_templates() -> dict[str, ReactionTemplate]:
    """Every template the 57 construction sites make with their DEFAULT arguments.

    Found by walking the source rather than by a list here, so a constructor
    added or renamed shows up as a disagreement instead of being missed.
    """
    found: dict[str, ReactionTemplate] = {}
    for modname, path in CONSTRUCTOR_MODULES.items():
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), path)
        mod = importlib.import_module(modname)
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            sites = sum(
                1 for x in ast.walk(node)
                if isinstance(x, ast.Call) and isinstance(x.func, ast.Name)
                and x.func.id == "ReactionTemplate"
            )
            if not sites:
                continue
            made = getattr(mod, node.name)()
            made = made if isinstance(made, list) else [made]
            if len(made) != sites:
                raise SystemExit(
                    f"{path}: {node.name}() has {sites} construction sites but "
                    f"returned {len(made)} templates with its default arguments. "
                    f"This walk cannot check a constructor whose defaults do not "
                    f"reach every site."
                )
            for tmpl in made:
                if tmpl.name in found:
                    raise SystemExit(
                        f"two constructors both make a template named "
                        f"{tmpl.name!r}; the table is keyed by name"
                    )
                found[tmpl.name] = tmpl
    return found


def verify(rows: list[dict]) -> list[str]:
    """Field-for-field disagreements between the table and the constructors."""
    made = constructor_templates()
    by_name = {r["name"]: r for r in rows}
    problems: list[str] = []
    for name in sorted(set(made) - set(by_name)):
        problems.append(f"{name}: a constructor makes it, the table has no row")
    for name in sorted(set(by_name) - set(made)):
        row = by_name[name]
        if row["tier"] == "family":
            problems.append(
                f"{name}: a family row with no constructor. Extracted rows are "
                f"tier=literal; a family row is checked against the code.")
    for name in sorted(set(made) & set(by_name)):
        want, row = made[name], by_name[name]
        for f in FIELD_DEFAULTS:
            a, b = getattr(want, f), row[f]
            if a != b:
                problems.append(
                    f"{name}.{f}: constructor {a!r}, table {b!r}")
    return problems


# ---------------------------------------------------------------------------
# the generated module
# ---------------------------------------------------------------------------

HEADER = '''"""Layer 2 -- the reaction templates, as data. GENERATED, do not edit.

    python tools/build_templates.py

Source: ``data/templates/templates.psv``. Adding a template is adding a row to
that file and running the line above; the row carries every field
``ReactionTemplate`` has, plus the tier, the catalog classes it covers, the
barrier\'s provenance and a note.

A ``tier="literal"`` row is extracted from ONE catalog step with kinetics from
a class policy table, and it may not enter the default library implicitly. S11
established that selectivity is a rate ratio between templates racing in the
same flask, so a hundred rows carrying policy-table kinetics would make every
multi-template flask\'s selectivity noise. ``load_templates()`` defaults to the
family tier and says which tier it loaded.
"""

from __future__ import annotations

from dataclasses import dataclass

from chemsim.reactions.template import ReactionTemplate

# Every field of ``ReactionTemplate`` that is data. Generated from the dataclass
# itself, so a field added there breaks the build until the table gains a column
# -- which is the assertion P4 wanted: about the SET of fields, not about
# whichever field somebody remembered.
TEMPLATE_FIELDS = (
'''

BODY = '''

@dataclass(frozen=True)
class TemplateRecord:
    """One row of ``templates.psv``, as data. ``build()`` makes the template."""

    name: str
    tier: str
    catalog_classes: tuple[str, ...]
    source: str
    notes: str
    smarts: str
    A: float
    Ea: float
    reversible: bool
    phase: str
    alpha: float
    orders: tuple[float, ...] | None
    solid_catalyst: str | None
    electrons: int
    hammett_rho: float
    hammett_slot: int
    hammett_saturation: float

    def build(self) -> ReactionTemplate:
        return ReactionTemplate(**{f: getattr(self, f) for f in TEMPLATE_FIELDS})
'''

FOOTER = '''

def load_templates(
    tier: str = "family",
    classes: tuple[str, ...] | None = None,
) -> list[ReactionTemplate]:
    """The templates of one tier, optionally narrowed to some catalog classes.

    ``tier`` defaults to ``"family"`` and that default is load-bearing: it is
    what keeps an extracted literal row out of a flask that did not ask for one.
    Pass ``tier="any"`` to load every row, which is a deliberate act.

    ``classes`` narrows to rows carrying at least one of the named
    ``route_steps.psv`` reaction classes.
    """
    out = []
    for rec in TEMPLATES.values():
        if tier != "any" and rec.tier != tier:
            continue
        if classes is not None and not set(rec.catalog_classes) & set(classes):
            continue
        out.append(rec.build())
    return out


def template_classes(tier: str = "any") -> dict[str, tuple[str, ...]]:
    """catalog reaction class -> the template names covering it.

    Several templates may cover one class: that is a class covered by a FAMILY,
    and the credit belongs to the family rather than to a member.
    """
    out: dict[str, list[str]] = {}
    for rec in TEMPLATES.values():
        if tier != "any" and rec.tier != tier:
            continue
        for cls in rec.catalog_classes:
            out.setdefault(cls, []).append(rec.name)
    return {c: tuple(n) for c, n in sorted(out.items())}


def tier_counts() -> dict[str, int]:
    """How many rows per tier -- COUNTED, so a report cannot assert it."""
    out: dict[str, int] = {}
    for rec in TEMPLATES.values():
        out[rec.tier] = out.get(rec.tier, 0) + 1
    return dict(sorted(out.items()))
'''


def render(rows: list[dict]) -> str:
    out = [HEADER]
    for f in FIELD_DEFAULTS:
        out.append(f"    {f!r},")
    out.append(")")
    out.append(BODY)
    out.append("")
    out.append("TEMPLATES: dict[str, TemplateRecord] = {")
    for row in rows:
        out.append(f"    {row['name']!r}: TemplateRecord(")
        out.append(f"        name={row['name']!r},")
        out.append(f"        tier={row['tier']!r},")
        out.append(f"        catalog_classes={row['catalog_classes']!r},")
        out.append(f"        source={row['source']!r},")
        out.append(f"        notes={row['notes']!r},")
        out.append(f"        smarts={row['smarts']!r},")
        out.append(f"        A={row['A']!r}, Ea={row['Ea']!r},")
        out.append(f"        reversible={row['reversible']!r}, "
                   f"phase={row['phase']!r},")
        out.append(f"        alpha={row['alpha']!r}, orders={row['orders']!r},")
        out.append(f"        solid_catalyst={row['solid_catalyst']!r}, "
                   f"electrons={row['electrons']!r},")
        out.append(f"        hammett_rho={row['hammett_rho']!r}, "
                   f"hammett_slot={row['hammett_slot']!r},")
        out.append(f"        hammett_saturation={row['hammett_saturation']!r},")
        out.append("    ),")
    out.append("}")
    out.append(FOOTER)
    return "\n".join(out)


# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify only; a stale module or a drifted row fails")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    check_columns()
    rows = read_table()
    for row in rows:
        build(row)                       # the constructor's own validation

    problems = verify(rows)
    print(f"{PSV}")
    print(f"  {len(rows)} rows, tiers "
          f"{ {t: sum(1 for r in rows if r['tier'] == t) for t in TIERS} }")
    print(f"  {len({c for r in rows for c in r['catalog_classes']})} catalog "
          f"classes covered")
    if problems:
        print(f"\n{len(problems)} disagreement(s) with the constructors:")
        for p in problems:
            print(f"    {p}")
        return 1
    print("  every row reproduces its constructor, field for field")

    text = render(rows)
    if args.dry_run:
        print(f"\n--dry-run: nothing written "
              f"({len(text)} bytes would go to {OUT})")
        return 0
    if args.check:
        try:
            with open(OUT, encoding="utf-8") as fh:
                have = fh.read()
        except FileNotFoundError:
            print(f"\n{OUT} does not exist; run without --check")
            return 1
        if have != text:
            print(f"\n{OUT} is stale. Run: python tools/build_templates.py")
            return 1
        print(f"  {OUT} is current")
        return 0
    # CRLF, matching every other generated module in this repo. A generator
    # that flips a file's line endings makes its own output undiffable.
    with open(OUT, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(text)
    print(f"\nwrote {OUT}  ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
