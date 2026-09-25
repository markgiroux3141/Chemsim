"""Score the template library against held-out reactions it was never written from.

    python tools/benchmark.py            # write data/benchmark/scores.psv
    python tools/benchmark.py --check    # re-derive and fail if the file is stale
    python tools/benchmark.py --class diels-alder-cycloaddition   # one class, verbose

The catalog (173 named routes) measures game progression, and a template that
reproduces its one step scores there exactly like one that works on every
substrate of its mechanism. ``data/benchmark/reactions.psv`` is the other
question: for each reaction class, 2-4 textbook substrate pairs that are NOT
catalog steps, and the template rows claiming that class are fired at each.

Two levels per case, per tier (``family`` is what a flask loads; ``literal`` is
reported beside it so the generality gap is visible):

``template``  the rewrite alone -- the same judge as
              ``tools/check_template_products.py``: fire every row of the class
              over the slot assignments the pool admits (the case's reactants
              plus water, hydronium and hydroxide) and compare products.
              pass | partial | wrong-product | no-fire | no-substrate | no-template
``engine``    ``build_network`` over the same pool for one generation with the
              class's rows only: does the engine REGISTER every expected
              product? It cannot when a species has no price, and that is the
              difference between a SMARTS that is right and a reaction a player
              can run. runs | unpriced | no | - (not tried: the template failed)

A ``wrong-product`` on a held-out case is how a mis-mapped row shows itself: on
its own step a symmetric product hid the mapping, and on a substituted
substrate the substituent lands somewhere else.

What this cannot say: which product WINS. Selectivity is a rate ratio between
templates racing in a flask, and a pass here means the expected product is one
the row can make, not the one it makes most of.

The case file's rules -- every case parses, balances, names no
stereochemistry and is not a catalog step of its class -- are checked on every
run, and a broken case fails the run rather than scoring.
"""

from __future__ import annotations

import argparse
import io
import itertools
import os
import sys
from contextlib import redirect_stdout

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "validation"))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

import build_templates as bt  # noqa: E402
import catalog as cat  # noqa: E402
import corpus_balance as cb  # noqa: E402

from chemsim.matter.molecule import Molecule  # noqa: E402
from chemsim.network.builder import build_network  # noqa: E402
from chemsim.properties import ThermochemistryProvider  # noqa: E402
from chemsim.properties.electrolyte import electrolyte_provider  # noqa: E402

CASES = os.path.join(_ROOT, "data", "benchmark", "reactions.psv")
OUT = os.path.join(_ROOT, "data", "benchmark", "scores.psv")

MEDIUM = ("O", "[OH3+]", "[OH-]")
MAX_ASSIGNMENTS = 256
MAX_COEFF = 4
TIERS = ("family", "literal")
RANK = ("no-template", "no-substrate", "no-fire", "wrong-product", "partial", "pass")

HEADER = """\
# THE REACTION BENCHMARK, SCORED -- GENERATED, do not edit.
#
#   python tools/benchmark.py
#
# Columns: case | class | family | family_engine | literal | literal_engine | template | missing
#
# family, literal   the best template verdict any row of that tier claiming the
#                   class reached on this case (tools/benchmark.py says what each
#                   verdict means).
# *_engine          runs | unpriced | no | -  -- did build_network register every
#                   expected product, one generation, that tier's rows only.
# template          the row that reached the family verdict, else the literal one.
# missing           expected products that did not come back, canonical SMILES.
#
# The `#!` keys at the foot are derived from the rows above, never typed.
# `classes_general` counts classes whose family rows pass EVERY case: the
# headline, because it is the one a single-substrate row cannot move.
"""


# ---------------------------------------------------------------------------
# the case file
# ---------------------------------------------------------------------------


def _species(cell: str) -> list[str]:
    return [s.strip() for s in cell.split(" + ") if s.strip()]


def read_cases(path: str = CASES) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, start=1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            cells = [c.strip() for c in line.rstrip("\n").split("|")]
            if len(cells) != 6:
                raise SystemExit(f"{path}:{n}: {len(cells)} columns, want 6")
            case, cls, react, prod, coprod, note = cells
            out.append({"case": case, "class": cls, "reactants": _species(react),
                        "products": _species(prod), "coproducts": _species(coprod),
                        "note": note, "line": n})
    return out


def validate(cases, steps) -> list[str]:
    """Every rule the case file's header states, as the list of breaches."""
    bad = []
    seen = set()
    by_class: dict[str, list] = {}
    for s in steps:
        by_class.setdefault(s[0], []).append(s)
    for c in cases:
        where = f"{c['case']} (line {c['line']})"
        if c["case"] in seen:
            bad.append(f"{where}: duplicate case name")
        seen.add(c["case"])
        smiles = c["reactants"] + c["products"] + c["coproducts"]
        if any(ch in s for s in smiles for ch in "@/\\"):
            bad.append(f"{where}: names stereochemistry")
            continue
        try:
            counts = [cb.formula(s) for s in smiles]
        except Exception as exc:  # noqa: BLE001
            bad.append(f"{where}: a SMILES does not parse ({type(exc).__name__})")
            continue
        if not balances(counts, len(c["reactants"])):
            bad.append(f"{where}: no coefficients of 1 to {MAX_COEFF} balance it "
                       f"by element and charge")
        react = {Molecule.from_smiles(s).smiles for s in c["reactants"]}
        prod = {Molecule.from_smiles(s).smiles for s in c["products"]}
        for _cls, s_react, s_prod in by_class.get(c["class"], []):
            if prod <= s_prod and react - set(_medium_smiles()) <= s_react:
                bad.append(f"{where}: is a catalog step of its own class")
                break
    return bad


def balances(counts, n_react) -> bool:
    """Is there a balance with every coefficient in 1..MAX_COEFF?

    Not a uniqueness test: a five-species C/H/O equation has a two-dimensional
    nullspace however it is written, and an enolate plus water is itself a
    balance. This guards the typing -- a dropped hydrogen balances nowhere.
    """
    keys = sorted({k for c in counts for k in c})
    rows = [[(c.get(k, 0) if j < n_react else -c.get(k, 0))
             for j, c in enumerate(counts)] for k in keys]
    for x in itertools.product(range(1, MAX_COEFF + 1), repeat=len(counts)):
        if all(sum(a * b for a, b in zip(row, x)) == 0 for row in rows):
            return True
    return False


def catalog_steps():
    """(class, reactant set, product set) of every catalog step with graphs."""
    comp = cat.load_compounds()
    out = []
    for s in cat.load_steps():
        try:
            r = {Molecule.from_smiles(comp[x].smiles).smiles for x in s.reactants
                 if x in comp and comp[x].smiles}
            p = {Molecule.from_smiles(comp[x].smiles).smiles for x in s.products
                 if x in comp and comp[x].smiles}
        except Exception:  # noqa: BLE001
            continue
        out.append((s.cls, r, p))
    return out


_MEDIUM_CACHE: list[str] = []


def _medium_smiles() -> list[str]:
    if not _MEDIUM_CACHE:
        _MEDIUM_CACHE.extend(Molecule.from_smiles(s).smiles for s in MEDIUM)
    return _MEDIUM_CACHE


# ---------------------------------------------------------------------------
# the two judges
# ---------------------------------------------------------------------------


def _assignments(template, pool):
    per_slot = [[m for m in pool
                 if m._mol.HasSubstructMatch(template.reactant_pattern(i))]
                for i in range(template.n_reactant_slots)]
    if any(not slot for slot in per_slot):
        return None
    return list(itertools.islice(itertools.product(*per_slot), MAX_ASSIGNMENTS))


def judge_template(templates, case):
    """(verdict, template name, missing, medium species used) at the best row."""
    if not templates:
        return "no-template", "", tuple(case_products(case)), ()
    reactants = [Molecule.from_smiles(s) for s in case["reactants"]]
    charged = {m.smiles for m in reactants}
    ambient = [Molecule.from_smiles(s) for s in MEDIUM]
    ambient = [m for m in ambient if m.smiles not in charged]
    pool = reactants + ambient
    declared = set(case_products(case)) - charged
    best = ("no-template", "", tuple(sorted(declared)), ())
    for t in templates:
        combos = _assignments(t, pool)
        if combos is None:
            verdict = ("no-substrate", t.name, tuple(sorted(declared)), ())
        else:
            verdict = ("no-fire", t.name, tuple(sorted(declared)), ())
            hit_best: set[str] = set()
            for combo in combos:
                used = tuple(sorted({m.smiles for m in combo
                                     if m.smiles not in charged}))
                for outcome in t.run(combo):
                    made = {m.smiles for m in outcome}
                    if declared <= made:
                        return "pass", t.name, (), used
                    hit = declared & made
                    if len(hit) > len(hit_best):
                        hit_best = hit
                        verdict = ("partial", t.name,
                                   tuple(sorted(declared - hit)), used)
                    elif verdict[0] == "no-fire":
                        verdict = ("wrong-product", t.name,
                                   tuple(sorted(declared)), ())
        if RANK.index(verdict[0]) > RANK.index(best[0]):
            best = verdict
    return best


def case_products(case):
    return [Molecule.from_smiles(s).smiles for s in case["products"]]


def judge_engine(templates, case, medium_used, providers):
    """runs | unpriced | no -- does build_network register the products?

    Ions are priced by the electrolyte overlay whenever the pool holds one or a
    template can make one -- ``engine.inventory.needs_electrolyte``'s rule, so
    this asks the question a flask would.
    """
    pool = list(dict.fromkeys(case["reactants"] + list(medium_used)))
    ionic = (any(t.touches_ions for t in templates)
             or any(Molecule.from_smiles(s).charge for s in pool))
    thermo = providers["ionic" if ionic else "plain"]
    try:
        with redirect_stdout(io.StringIO()):
            net = build_network(pool, templates, thermo=thermo, generations=1,
                                max_species=200)
    except Exception as exc:  # noqa: BLE001
        text = f"{type(exc).__name__}: {exc}".lower()
        return "unpriced" if "price" in text or "thermo" in text else "no"
    want = set(case_products(case))
    if want <= set(net.species):
        return "runs"
    if any(s in (net.unpriced or {}) for s in want):
        return "unpriced"
    return "no"


# ---------------------------------------------------------------------------
# the report
# ---------------------------------------------------------------------------


def score(only_class: str | None = None, verbose: bool = False):
    cases = read_cases()
    bad = validate(cases, catalog_steps())
    if bad:
        return None, bad
    rows = bt.read_table()
    by_tier: dict[str, dict[str, list]] = {t: {} for t in TIERS}
    for r in rows:
        if r["tier"] not in by_tier:
            continue
        tmpl = None
        for cls in r["catalog_classes"]:
            if tmpl is None:
                tmpl = bt.build(r)
            by_tier[r["tier"]].setdefault(cls, []).append(tmpl)
    providers = {"plain": ThermochemistryProvider(),
                 "ionic": electrolyte_provider()}
    report = []
    for c in cases:
        if only_class and c["class"] != only_class:
            continue
        line = {"case": c["case"], "class": c["class"]}
        name = ""
        missing = ()
        for tier in TIERS:
            templates = by_tier[tier].get(c["class"], [])
            verdict, tname, miss, used = judge_template(templates, c)
            line[tier] = verdict
            line[f"{tier}_engine"] = (judge_engine(templates, c, used, providers)
                                      if verdict == "pass" else "-")
            if not name and tname and (tier == "family" or verdict != "no-template"):
                name, missing = tname, miss
            if verbose:
                print(f"  {c['case']:60s} {tier:7s} {verdict:14s} "
                      f"{line[f'{tier}_engine']:9s} {tname} {','.join(miss)}")
        line["template"] = name
        line["missing"] = ",".join(missing) if line["family"] != "pass" else ""
        report.append(line)
    return report, []


def footer(report) -> list[str]:
    classes: dict[str, list] = {}
    for r in report:
        classes.setdefault(r["class"], []).append(r)
    general = sorted(c for c, rs in classes.items()
                     if all(r["family"] == "pass" for r in rs))
    runs = sorted(c for c, rs in classes.items()
                  if all(r["family_engine"] == "runs" for r in rs))
    covered = sorted(c for c, rs in classes.items()
                     if any(r["family"] != "no-template" for r in rs))
    literal_only = sorted(c for c, rs in classes.items()
                          if c not in covered
                          and any(r["literal"] != "no-template" for r in rs))

    def n(key, value):
        return sum(1 for r in report if r[key] == value)

    out = [
        f"#! cases = {len(report)}",
        f"#! classes = {len(classes)}",
        f"#! classes_general = {len(general)}",
        f"#! classes_general_and_running = {len(runs)}",
        f"#! classes_with_a_family_row = {len(covered)}",
        f"#! classes_with_only_a_literal_row = {len(literal_only)}",
        f"#! classes_with_no_row = {len(classes) - len(covered) - len(literal_only)}",
        f"#! family_pass = {n('family', 'pass')}",
        f"#! family_runs = {n('family_engine', 'runs')}",
        f"#! family_unpriced = {n('family_engine', 'unpriced')}",
        f"#! family_wrong_product = {n('family', 'wrong-product')}",
        f"#! literal_pass = {n('literal', 'pass')}",
        f"#! literal_runs = {n('literal_engine', 'runs')}",
        f"#! literal_wrong_product = {n('literal', 'wrong-product')}",
    ]
    return out


def render(report) -> str:
    cols = ("case", "class", "family", "family_engine", "literal",
            "literal_engine", "template", "missing")
    body = "\n".join(" | ".join(r[c] for c in cols) for r in report)
    return HEADER + "\n" + body + "\n\n" + "\n".join(footer(report)) + "\n"


def summarise(report) -> list[str]:
    keys = dict(line[3:].split(" = ") for line in footer(report))
    return [
        f"{keys['cases']} held-out cases over {keys['classes']} reaction classes",
        f"  classes general (family rows pass every case)  {keys['classes_general']}",
        f"  ...and the engine runs every case              "
        f"{keys['classes_general_and_running']}",
        f"  classes with a family row                      "
        f"{keys['classes_with_a_family_row']}",
        f"  classes with only a literal row                "
        f"{keys['classes_with_only_a_literal_row']}",
        f"  classes with no row at all                     {keys['classes_with_no_row']}",
        f"  cases: family pass {keys['family_pass']}, runs {keys['family_runs']}, "
        f"unpriced {keys['family_unpriced']}, wrong-product "
        f"{keys['family_wrong_product']}",
        f"  cases: literal pass {keys['literal_pass']}, runs {keys['literal_runs']}, "
        f"wrong-product {keys['literal_wrong_product']}",
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="re-derive and fail if the committed scores are stale")
    ap.add_argument("--class", dest="cls", help="one class, every case, verbose")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    report, bad = score(only_class=args.cls, verbose=bool(args.cls))
    if bad:
        print(f"{CASES}: {len(bad)} case(s) break the file's own rules")
        for line in bad:
            print(f"  - {line}")
        return 1
    if args.cls:
        return 0
    for line in summarise(report):
        print(line)
    text = render(report)
    if args.check:
        try:
            with open(OUT, encoding="utf-8", newline="") as fh:
                current = fh.read().replace("\r\n", "\n")
        except FileNotFoundError:
            current = ""
        if current != text:
            print(f"\n{OUT} is stale; run tools/benchmark.py")
            return 1
        print(f"\n{os.path.basename(OUT)} is current")
        return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
