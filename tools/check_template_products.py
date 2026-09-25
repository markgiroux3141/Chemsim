"""T1b -- does each template row still make what the catalog step says it makes?

    python tools/check_template_products.py            # write the report
    python tools/check_template_products.py --check    # re-derive and compare
    python tools/check_template_products.py --verbose  # every step, not the best

``tools/build_templates.py`` asks two questions about the table and neither is
about chemistry: does the column set cover every field of ``ReactionTemplate``,
and is there a ``ReactionTemplate(...)`` anywhere outside the four loaders. A row
can pass both with a SMARTS that fires on nothing, or that fires and makes
something the catalog never claimed. The only thing that held it before this
tool was one hand-written test file per template -- and those files are not
retired by it, because 132 of their 208 tests build a network or run a vessel
and assert a selectivity, a declared order or a standard state. The argument is
``docs/design/per-template-tests-not-retired.md``.

This is the check those files imply. For each row, for each ``route_steps.psv``
step carrying one of the row's classes, resolve the step's reactants and
products to molecules, fire the template over the slot assignments its own
reactant patterns admit, and compare the product set with the one the step
declares. The catalog is the reference; the row is what is being checked.

## The verdicts, worst to best

``no-class``          the row claims no catalog class, so there is nothing to
                      check it against. Two rows are deliberately here: a
                      fermentation is an outcome and not a mechanism, so the
                      class was refused, and the lumped rows kept the chemistry
                      without the label.
``no-runnable-step``  every step of every class the row claims names a species
                      with no molecular graph -- a rock, an alloy, a mixture, a
                      protein -- or is a cycle written closed. Reported, never
                      skipped: a row nothing can check is a row nothing checks.
``no-substrate``      a reactant slot matches nothing the step names, so there
                      is no assignment to try. The row is not wrong; this class
                      has no step exercising it.
``no-fire``           every slot has a candidate and no assignment survives the
                      rewrite. A match is a substructure and not a substrate,
                      or the product the SMARTS writes does not sanitise. This
                      is the one to read first.
``wrong-product``     the rewrite runs on some step and makes none of what that
                      step declares.
``partial``           some declared products come back and some do not. Read the
                      ``missing`` column before reading this as a defect: the
                      catalog writes a precipitated salt where the engine writes
                      its ions, and a step may declare a product two mechanisms
                      downstream of the one the row names.
``pass``              one step's whole declared product set came back from one
                      product tuple.

A row is reported at its best step, because a family template covering four
steps is doing its job if it reproduces one of them; the count of steps tried is
in the report so a single lucky step is visible. ``--verbose`` prints all of
them.

## The medium is not in the recipe, and saying so is part of the check

No ``route_steps.psv`` step lists its solvent, and none lists the ions the
solvent and the acid in the pot already carry. Two rows were refused by the
first version of this tool for exactly that: ``acetonic_fermentation`` spells
water as a reactant slot and the ABE step names glucose alone, and
``skraup_cyclisation`` spells its homogeneous catalyst ``[OH3+:99]`` while the
step names sulfuric acid. Both work in the engine. The instrument had invented
the finding.

So a slot may also be filled from ``MEDIUM`` -- water, hydronium, hydroxide --
and the ``medium`` column says when a row's verdict needed it. That is a
concession and it reports itself: a row reaching ``pass`` only through the
medium is making a claim about the step's conditions rather than its reactants,
and a reader can see which rows do. Nothing else is offered; the pool is the
step's own reactants and those three.

## What a product set comparison can and cannot say

It compares canonical SMILES, so it asks whether the row makes the right
species. It says nothing about stoichiometry -- ``validation/corpus_balance.py``
owns that, and the corpus carries no coefficients to check against anyway -- and
nothing about the kinetics, which are the source column's business.

A species appearing on both sides of a step is that step's catalyst and is
dropped from the declared set before comparing, which is the rule
``route_steps.psv`` states in its own header.
"""

from __future__ import annotations

import argparse
import itertools
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

import build_templates as bt  # noqa: E402
import catalog as cat  # noqa: E402
from chemsim.matter.molecule import Molecule  # noqa: E402

OUT = os.path.join(_ROOT, "data", "catalog", "derived", "template_products.psv")

# Worst to best. A row is reported at the best verdict any of its steps reached.
RANK = ("no-runnable-step", "no-substrate", "no-fire", "wrong-product",
        "partial", "pass")

# One template against one step is a handful of assignments once the slot
# patterns have filtered the candidates, but a slot matching a sugar can still
# fork. This bounds the work per step rather than trusting it to be small.
MAX_ASSIGNMENTS = 256

# What a flask holds whatever the recipe says. See the docstring: a step lists
# neither its solvent nor the ions the pot already carries, and three of the
# table's reactant slots are a homogeneous catalyst spelled with map 99 --
# hydronium, hydroxide and a copper(II) the Wacker step does name.
MEDIUM = ("O", "[OH3+]", "[OH-]")

HEADER = """\
# TEMPLATE ROWS AGAINST THE CATALOG STEPS THEY CLAIM -- GENERATED, do not edit.
#
#   python tools/check_template_products.py
#
# Columns: template | verdict | steps_tried | medium | class | step | missing | reading
#
# verdict      pass | partial | wrong-product | no-fire | no-substrate |
#              no-runnable-step | no-class, at the row's best step. The tool's
#              docstring says what each means, and what this cannot say.
# steps_tried  how many catalog steps of the row's classes resolved to molecules.
# medium       yes when the verdict needed water, hydronium or hydroxide, which
#              no step lists. A concession, reported rather than assumed.
# step         the route and index the verdict was reached on.
# missing      declared products of that step the row did not make, canonical
#              SMILES, comma-joined. Empty on a pass.
# reading      written, or engine when the verdict needed the step read the way
#              the engine holds it -- a salt as its ions, a stereoisomer flat.
#
# The `#!` keys at the foot are derived from the rows above, never typed.
# `missing_because_salt` and `missing_because_stereo` are the two systematic
# walls: the catalog spells a precipitated salt as one species where the engine
# holds its ions, and it declares a stereoisomer where a template emits the flat
# species. An extractor writing literal rows off this corpus meets both.
"""


STEREO_MARKS = ("@", "/", "\\")


def flat(smiles: str) -> str:
    """The species with its stereochemistry dropped, canonical."""
    if not any(c in smiles for c in STEREO_MARKS):
        return smiles
    from rdkit import Chem
    mol = Chem.MolFromSmiles(smiles)
    return Chem.MolToSmiles(mol, isomericSmiles=False) if mol is not None else smiles


def engine_reading(smiles_list) -> list[str]:
    """Species as the engine holds them: a salt as its ions, every one flat.

    The one reading ``tools/extract_templates.py`` extracts under and this
    checker judges under when a step as written cannot pass, so the two
    instruments cannot disagree about what a row makes.
    """
    out: dict[str, None] = {}
    for s in smiles_list:
        for frag in s.split("."):
            out[Molecule.from_smiles(flat(frag)).smiles] = None
    return list(out)


def molecules(compounds):
    """``compound id -> Molecule or None``, memoised. None means no graph."""
    cache: dict[str, Molecule | None] = {}

    def get(cid: str):
        if cid not in cache:
            c = compounds.get(cid)
            if c is None or not c.smiles or cat.is_marker(cid, compounds):
                cache[cid] = None
            else:
                try:
                    cache[cid] = Molecule.from_smiles(c.smiles)
                except Exception:  # noqa: BLE001
                    cache[cid] = None
        return cache[cid]

    return get


def assignments(template, reactants):
    """Ordered tuples of reactants, one per slot, that the slot patterns admit.

    The same filter ``network/builder.py`` applies before running a template.
    ``None`` when a slot has no candidate at all: that is ``no-substrate``,
    which says something about the class rather than about the row.
    """
    per_slot = [
        [m for m in reactants
         if m._mol.HasSubstructMatch(template.reactant_pattern(i))]
        for i in range(template.n_reactant_slots)
    ]
    if any(not slot for slot in per_slot):
        return None
    out = []
    for combo in itertools.product(*per_slot):
        out.append(combo)
        if len(out) >= MAX_ASSIGNMENTS:
            break
    return out


def judge(template, step, get, medium):
    """One row against one step -> (verdict, missing, used medium, reading).

    The step is judged as written; if that does not pass and the step names a
    salt or a stereoisomer, it is judged again in ``engine_reading`` and the
    better verdict is kept, with ``reading`` saying which one it came from.
    """
    reactants = [get(x) for x in step.reactants]
    products = [get(x) for x in step.products]
    if any(m is None for m in reactants + products):
        return "no-runnable-step", (), False, "written"
    written = _judge(template, reactants, products, medium)
    smiles = [m.smiles for m in reactants + products]
    if written[0] == "pass" or not any(
            "." in s or any(c in s for c in STEREO_MARKS) for s in smiles):
        return (*written, "written")
    r = [Molecule.from_smiles(s)
         for s in engine_reading([m.smiles for m in reactants])]
    p = [Molecule.from_smiles(s)
         for s in engine_reading([m.smiles for m in products])]
    engine = _judge(template, r, p, medium)
    if engine[0] != "no-runnable-step" and RANK.index(engine[0]) > RANK.index(written[0]):
        return (*engine, "engine")
    return (*written, "written")


def _judge(template, reactants, products, medium):
    """One row against resolved species -> (verdict, missing, used medium)."""
    charged = {m.smiles for m in reactants}
    declared = {m.smiles for m in products} - charged
    if not declared:
        # Every product is also a reactant: the step is a catalytic cycle
        # written closed, and there is nothing for a rewrite to add.
        return "no-runnable-step", (), False
    ambient = {m.smiles for m in medium} - charged
    pool = reactants + [m for m in medium if m.smiles in ambient]
    combos = assignments(template, pool)
    if combos is None:
        return "no-substrate", (), False
    fired = False
    best: set[str] = set()
    best_medium = False
    for combo in combos:
        used = any(m.smiles in ambient for m in combo)
        for outcome in template.run(combo):
            fired = True
            made = {m.smiles for m in outcome}
            hit = declared & made
            if len(hit) > len(best):
                best, best_medium = hit, used
            if declared <= made:
                return "pass", (), used
    missing = tuple(sorted(declared - best))
    if best:
        return "partial", missing, best_medium
    return ("wrong-product" if fired else "no-fire"), missing, False


def rows_report(verbose: bool = False):
    """Every template row -> its best verdict, and the per-step lines."""
    compounds = cat.load_compounds()
    get = molecules(compounds)
    medium = [Molecule.from_smiles(s) for s in MEDIUM]
    by_class: dict[str, list] = {}
    for s in cat.load_steps():
        by_class.setdefault(s.cls, []).append(s)

    out = []
    lines = []
    for row in bt.read_table():
        name = row["name"]
        classes = row["catalog_classes"]
        if not classes:
            out.append((name, "no-class", 0, "", "", "", "", ""))
            continue
        template = bt.build(row)
        best = None
        tried = 0
        for cls in classes:
            for step in by_class.get(cls, []):
                verdict, missing, used, reading = judge(template, step, get, medium)
                if verdict != "no-runnable-step":
                    tried += 1
                where = f"{step.route}:{step.index}"
                if verbose:
                    lines.append(f"  {name:44s} {verdict:16s} "
                                 f"{'medium' if used else '      '} {cls:28s} "
                                 f"{where:28s} {','.join(missing)}")
                if best is None or RANK.index(verdict) > RANK.index(best[0]):
                    best = (verdict, "yes" if used else "no", cls, where,
                            ",".join(missing), reading)
                if best[0] == "pass":
                    break
            if best[0] == "pass":
                break
        out.append((name, best[0], tried, best[1], best[2], best[3], best[4],
                    best[5]))
    return out, lines


def cause(missing: str) -> str:
    """Why one row's declared products did not come back. Three answers.

    Derived from the missing SMILES, not asserted anywhere: a count typed into
    a report is a count that drifts. ``salt`` and ``stereo`` are the two walls
    an extractor writing literal rows (T2) will hit on the same corpus, and
    knowing they are systematic is worth more than the 23 row names.
    """
    products = [m for m in missing.split(",") if m]
    if not products:
        return ""
    if all("." in m for m in products):
        # The catalog spells a precipitated salt as one species and the engine
        # holds its ions. The row makes the anion; nothing makes "[Na+].[O-]...".
        return "salt"
    if any(c in m for m in products for c in ("@", "/", "\\")):
        # The step declares a stereoisomer and a template emits the flat
        # species, which is the C7 finding from the other side.
        return "stereo"
    return "other"


def footer(report) -> str:
    """The derived counts, as ``#!`` keys the way ``silent_templates.psv`` does."""
    counts: dict[str, int] = {}
    for _, verdict, *_ in report:
        counts[verdict] = counts.get(verdict, 0) + 1
    causes: dict[str, int] = {}
    for _, verdict, _, _, _, _, missing, _ in report:
        if verdict in ("pass", "no-class", "no-substrate", "no-runnable-step"):
            continue
        key = cause(missing)
        causes[key] = causes.get(key, 0) + 1
    out = [""]
    for v in ("pass", "partial", "wrong-product", "no-fire", "no-substrate",
              "no-runnable-step", "no-class"):
        out.append(f"#! {v} = {counts.get(v, 0)}")
    out.append(f"#! steps_tried = {sum(t for _, _, t, *_ in report)}")
    out.append(f"#! through_the_medium = "
               f"{sum(1 for r in report if r[3] == 'yes')}")
    out.append(f"#! in_the_engine_reading = "
               f"{sum(1 for r in report if r[7] == 'engine')}")
    for key in ("salt", "stereo", "other"):
        out.append(f"#! missing_because_{key} = {causes.get(key, 0)}")
    return "\n".join(out) + "\n"


def render(report) -> str:
    body = "\n".join(" | ".join((name, verdict, str(tried), med, cls, where, missing,
                                reading))
                     for name, verdict, tried, med, cls, where, missing, reading
                     in report)
    return HEADER + "\n" + body + "\n" + footer(report)


def summarise(report) -> list[str]:
    counts: dict[str, int] = {}
    for _, verdict, *_ in report:
        counts[verdict] = counts.get(verdict, 0) + 1
    order = ("pass", "partial", "wrong-product", "no-fire", "no-substrate",
             "no-runnable-step", "no-class")
    lines = [f"{len(report)} template rows against "
             f"{sum(t for _, _, t, *_ in report)} catalog steps"]
    for v in order:
        if counts.get(v):
            lines.append(f"  {counts[v]:3d}  {v}")
    med = sum(1 for r in report if r[3] == "yes")
    lines.append(f"  {med:3d}  reached that verdict through the medium")
    eng = sum(1 for r in report if r[7] == "engine")
    lines.append(f"  {eng:3d}  reached it only read as the engine holds it "
                 f"(salts as ions, flat)")
    causes: dict[str, int] = {}
    for _, verdict, _, _, _, _, missing, _ in report:
        if verdict not in ("pass", "no-class", "no-substrate", "no-runnable-step"):
            key = cause(missing)
            causes[key] = causes.get(key, 0) + 1
    lines.append("why the declared products did not come back:")
    for key, why in (("salt", "the step spells a salt the engine holds as ions"),
                     ("stereo", "the step declares a stereoisomer, the row emits the flat species"),
                     ("other", "read the row")):
        lines.append(f"  {causes.get(key, 0):3d}  {key:7s} {why}")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="re-derive and fail if the committed report is stale")
    ap.add_argument("--verbose", action="store_true",
                    help="print every step, not only the best one per row")
    args = ap.parse_args()

    report, lines = rows_report(verbose=args.verbose)
    text = render(report)

    for line in lines:
        print(line)
    for name, verdict, tried, _med, _cls, where, missing, _reading in report:
        if verdict not in ("pass", "no-class"):
            print(f"{name:44s} {verdict:16s} {tried:2d} step(s)  "
                  f"{where:28s} {missing}")
    print()
    for line in summarise(report):
        print(line)

    if args.check:
        if not os.path.exists(OUT):
            print(f"\n{OUT} does not exist; run without --check")
            return 1
        with open(OUT, encoding="utf-8", newline="") as fh:
            current = fh.read()
        if current.replace("\r\n", "\n") != text:
            print(f"\n{OUT} is stale; run without --check")
            return 1
        print(f"\n{os.path.basename(OUT)} is current")
        return 0

    # CRLF, which is what every sibling in ``data/catalog/derived/`` carries.
    # ``--check`` normalises before comparing, so a checkout that rewrote them
    # fails on content and never on a line terminator.
    with open(OUT, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(text)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
