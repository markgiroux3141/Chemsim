"""P0's standing audit: what actually moves the scoreboard, and what a step costs.

This file exists because a direction was chosen from these numbers, and a
direction chosen from numbers that live in a chat log is a direction nobody can
re-derive. Every figure in `docs/history/MILESTONES.md` section P and in `GAME_DESIGN.md`
section 8 is printed by a panel below.

## The four findings, in the order they change a decision

**PANEL 1 -- THE "NO LEVER" FINDING WAS MEASURED ONE SPECIES AT A TIME.**
`PLAYABLE.md` section 7 grants a single species and re-runs the fixed point; the
best is `aluminium` at **+2**, and it concludes there is no lever. That is true
of singles and says nothing about sets, because routes block each other: a
species is worth +1 only while the thing it would unblock is blocked by
something else too. Granted cumulatively the same species keep paying.

**PANEL 2 -- AND THE TWO WORK STREAMS ARE SUPER-ADDITIVE, WHICH REWRITES THE
WORK ORDER.** Templates alone take 21 to **31**. Prices alone take 21 to **25**.
Both together take 21 to **45**. `PLAYABLE.md` section 8b ranks every class at
"+1" because it prices each one holding everything else fixed -- so **22
template sessions on their own buy +10 routes, not the +24 the ceiling
implies.** The file says 10 of its rows are joint grants; nobody had measured
what the joint is worth.

**PANEL 3 -- TWENTY-THREE ROUTES ARE ALREADY RUNNABLE AND MERELY UNREACHABLE.**
The engine can execute them today. **19 are a CHAIN problem** -- their feedstocks
are made by other routes that are themselves stranded -- and they want 24 species
between them; granting those takes 21 to **40 with no new chemistry of any
kind**. **4 are a BOTTLE problem**: `benzaldehyde`, `malonic-acid`,
`4-nitrophenol` and `bromoethane` are made by NOTHING in 173 routes, and they are
worth only +1 because each of those routes is short of something else too.
Granting all 28 gives **41**. The two are not interchangeable -- a chain species
can be EARNED once the tree is deeper, a bottle has to be bought or the corpus
has to grow a route for it -- and that distinction is the whole of the shelf
design.

**PANEL 4 -- THE ENGINE IS GENERAL; THE SCOREBOARD IS NOT MEASURING GENERALITY.**
One template, `esterification`, matches 166 acids against 190 alcohols -- about
**31 500 reactions** -- and the catalog credits its class with **9 route steps**.
Meanwhile **169 of the 240 catalog classes appear in exactly one route step**,
because the catalog is a list of named industrial processes and a named process
is a one-off by construction. *The slog is a property of the target list, not of
the architecture.*

## And the two engineering facts the game plan rests on

**PANEL 5 -- A GENERATION IS THE WHOLE COST.** Five ordinary bench reagents at
`generations=2` hit the 400-species cap in **12.4 s**; twelve at `generations=1`
give 77 species in **0.43 s**. Step-by-step play is not a simplification of the
chemistry, it is the only tractable way to run an open inventory -- and it is
also the mechanic that was wanted for its own sake.

**PANEL 6 -- A SHELF CANNOT HOLD EVERYTHING, AND THE LIMIT IS DELIBERATE.** 416
of the 1583 corpus compounds are REFUSED a price by the element floor, so an
"all chemicals" inventory tops out near 1167. A refused species cannot enter a
flask at all and the picker has to say so rather than fail late.

Run: ``python validation/playable_levers.py`` (~2 min; importing the scorer runs
the deep chain, which is 50 s of it).

EVERY PRINTED LINE HERE IS ASCII. The console is cp1252 and a warning glyph in a
``print`` kills the script mid-panel. Glyphs belong in docstrings and comments.
"""

from __future__ import annotations

import contextlib
import csv
import importlib.util
import io
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, os.path.join(_ROOT, "tools"))

from rdkit import RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

from rdkit import Chem  # noqa: E402

import catalog as cat  # noqa: E402
from chemsim.matter import Molecule  # noqa: E402
from chemsim.network import build_network  # noqa: E402
from chemsim.properties import (  # noqa: E402
    ThermochemistryProvider,
    VolatilityProvider,
)
from chemsim.reactions import library, synthesis  # noqa: E402


def rule(title):
    print()
    print("=" * 74)
    print(title)
    print("=" * 74)


def _scorer():
    """Import ``tools/build_playable.py`` for its fixed point.

    Imported rather than reimplemented: it owns the four scoring rules and every
    one of them was measured wrong first (PLAYABLE.md section 3). A second
    implementation here would be a second thing to get wrong.
    Importing costs ~50 s -- ``CHAIN = run_chain()`` is module level -- and
    writes nothing; only ``main()`` writes.
    """
    spec = importlib.util.spec_from_file_location(
        "bp", os.path.join(_ROOT, "tools", "build_playable.py"))
    bp = importlib.util.module_from_spec(spec)
    sys.modules["bp"] = bp
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        spec.loader.exec_module(bp)
    return bp


BP = _scorer()
BASE = len(BP.PLAYABLE)


def panel1():
    rule("PANEL 1 -- A LEVER MEASURED ONE SPECIES AT A TIME IS NOT A LEVER")
    hubs = sorted({x for _rid, miss, _o in BP.BLOCKED for x in miss}
                  & set(BP.compounds))
    singles = sorted(((len(BP.closure(extra={h})[0]) - BASE, h) for h in hubs),
                     reverse=True)
    print(f"  base playable                                   {BASE:5d}")
    print("  best SINGLE grants (PLAYABLE.md section 7's question):")
    for gain, h in singles[:6]:
        print(f"     +{gain}  {h}")
    print()
    print("  the same species granted CUMULATIVELY, greedily:")
    chosen, cur, pool = [], BASE, set(hubs)
    for _ in range(8):
        best = None
        for h in sorted(pool):
            n = len(BP.closure(extra=set(chosen) | {h})[0])
            if best is None or n > best[0]:
                best = (n, h)
        n, h = best
        if n == cur and chosen:
            break
        chosen.append(h)
        pool.discard(h)
        print(f"     + {h:22s} -> {n:3d} playable   "
              f"(step +{n - cur}, total +{n - BASE})")
        cur = n
    print()
    print("  A species is worth +1 only while the route it unblocks is blocked")
    print("  by something else as well. Sets keep paying where singles do not,")
    print("  and section 7's conclusion is true of singles only.")


def panel2():
    rule("PANEL 2 -- THE TWO WORK STREAMS ARE SUPER-ADDITIVE")
    allc = sorted(BP.CLASS_GAPS)

    def runnable_with(classes=(), price_all=False):
        tc2 = set(BP.TC) | set(classes)
        pr = (lambda x: x in BP.compounds) if price_all else BP.priced
        return {rid for rid in BP.routes
                if cat.route_reachable(BP.steps, rid, BP.routes[rid].target,
                                       pr, tc2, BP.compounds)}

    print(f"     {'grant':34s} {'runnable':>9s} {'playable':>9s}")
    rows = [("nothing (today)", (), False),
            (f"all {len(allc)} missing CLASSES", allc, False),
            ("every species PRICED", (), True),
            ("both", allc, True)]
    out = {}
    for label, cls, pa in rows:
        run = runnable_with(cls, pa)
        play = BP.closure(pool=run)[0]
        out[label] = len(play)
        print(f"     {label:34s} {len(run):9d} {len(play):9d}")
    print()
    a = out[f"all {len(allc)} missing CLASSES"] - BASE
    b = out["every species PRICED"] - BASE
    j = out["both"] - BASE
    print(f"  templates alone  +{a}      prices alone  +{b}      together  +{j}")
    print(f"  the parts sum to {a + b}; the joint is {j}. THE DIFFERENCE IS THE")
    print("  FINDING: section 8b ranks each class holding prices fixed, so it")
    print("  systematically understates what a template is worth -- and the")
    print("  ceiling of 45 is a JOINT grant, not what 22 template sessions buy.")


def panel3():
    rule("PANEL 3 -- ROUTES THAT ARE RUNNABLE AND MERELY UNREACHABLE")
    chain = sorted({x for _rid, miss, _o in BP.BLOCKED for x in miss})
    bottle = sorted({x for _rid, _m, orphan in BP.BOTTLE for x in orphan})
    both = sorted(set(chain) | set(bottle))
    print(f"  routes the engine CAN run but a player cannot reach  "
          f"{len(BP.BLOCKED) + len(BP.BOTTLE):4d}")
    print(f"     of them, waiting on a species some route MAKES    "
          f"{len(BP.BLOCKED):4d}   (a CHAIN problem)")
    print(f"     of them, waiting on one NOTHING makes             "
          f"{len(BP.BOTTLE):4d}   (a BOTTLE problem)")
    print()
    print(f"  distinct species the chain-blocked ones want          {len(chain):4d}")
    print(f"  distinct species nothing in 173 routes makes          {len(bottle):4d}")
    print(f"     {bottle}")
    print()
    for label, gset in (("chain species only", chain),
                        ("bottles only", bottle),
                        ("both", both)):
        got = len(BP.closure(extra=set(gset))[0])
        print(f"  grant {label:24s} -> playable {got:4d}   "
              f"(base {BASE}, +{got - BASE})")
    print()
    print("  ONE OF THESE IS A SHELF DECISION AND THE OTHER IS A CORPUS GAP,")
    print("  and they are not interchangeable. A chain species is made by a")
    print("  route that is itself stranded, so it can be EARNED once the tree")
    print("  is deeper; a bottle is made by nothing in the corpus at all, so it")
    print("  is either bought or the corpus grows a route for it.")
    print()
    print("  the union, which is the principled content of a starting shelf:")
    for i in range(0, len(both), 4):
        print("     " + "  ".join(f"{x:22s}" for x in both[i:i + 4]))


def panel4():
    rule("PANEL 4 -- THE ENGINE IS GENERAL; THE SCOREBOARD MEASURES SOMETHING ELSE")
    steps = cat.load_steps()
    sizes = {}
    for s in steps:
        sizes[s.cls] = sizes.get(s.cls, 0) + 1
    one = sum(1 for n in sizes.values() if n == 1)
    print(f"  catalog route steps                              {len(steps):5d}")
    print(f"  distinct reaction classes                        {len(sizes):5d}")
    print(f"  classes used by EXACTLY ONE route step           {one:5d}"
          f"   ({100 * one / len(sizes):.0f}%)")
    print()
    print("  A named industrial process is a one-off by construction. That is a")
    print("  fact about the target list, not about the engine:")
    print()
    t = library.esterification()
    react = t.smarts.partition(">>")[0].split(".")
    pats = [Chem.MolFromSmarts(p) for p in react]
    slots = [0] * len(pats)
    path = os.path.join(_ROOT, "data", "catalog", "compounds")
    for fn in sorted(os.listdir(path)):
        if not fn.endswith(".psv"):
            continue
        with open(os.path.join(path, fn), encoding="utf-8") as fh:
            for row in csv.reader(fh, delimiter="|"):
                if not row or row[0].strip().startswith("#") or len(row) < 3:
                    continue
                m = Chem.MolFromSmiles(row[2].strip())
                if m is None:
                    continue
                for i, p in enumerate(pats):
                    if p is not None and m.HasSubstructMatch(p):
                        slots[i] += 1
    grid = 1
    for n in slots:
        grid *= n
    credited = sum(1 for s in steps if "esterif" in s.cls)
    print(f"  esterification matches                           {slots}")
    print(f"  reactions that one template can make             {grid:5d}")
    print(f"  route steps the catalog credits its class        {credited:5d}")
    print()
    print("  ONE template, four orders of magnitude more chemistry than the")
    print("  scoreboard can see. Nobody is writing code per reaction.")


def _library():
    seen, lib = set(), []
    for mod in (library, synthesis):
        for nm in dir(mod):
            f = getattr(mod, nm)
            if not callable(f) or nm.startswith("_") or not nm.endswith("chemistry"):
                continue
            try:
                r = f()
            except Exception:                                   # noqa: BLE001
                continue
            for t in r:
                if t.name not in seen:
                    seen.add(t.name)
                    lib.append(t)
    return lib


BENCH = ["O", "CCO", "CC(=O)O", "OC(=O)c1ccccc1O", "CC(=O)OC(C)=O",
         "O=S(=O)(O)O", "[Na+].[OH-]", "c1ccccc1", "CO", "CC(C)O",
         "O=C=O", "[H][H]"]


def panel5():
    rule("PANEL 5 -- WHAT A GENERATION COSTS, AND WHY A STEP IS ONE")
    lib = _library()
    th = ThermochemistryProvider()
    vol = VolatilityProvider(th)
    print(f"  template library                                 {len(lib):5d}")
    print()
    print(f"     {'gens':>4} {'charged':>8} {'species':>8} {'reactions':>10}"
          f" {'seconds':>8} {'notices':>8} {'frontier':>9}")
    for gens in (1, 2):
        for n in (3, 5, 8, 12):
            sp = [Molecule.from_smiles(s).smiles for s in BENCH[:n]]
            buf = io.StringIO()
            t0 = time.time()
            with contextlib.redirect_stdout(buf):
                net = build_network(sp, list(lib), thermo=th, volatility=vol,
                                    max_species=400, generations=gens)
            print(f"     {gens:>4} {n:>8} {len(net.species):>8} "
                  f"{len(net.reactions):>10} {time.time() - t0:>8.2f} "
                  f"{len(net.notices):>8} {len(net.unexpanded):>9}")
    print()
    print("  Five ordinary reagents explored two deep hit the cap. Twelve")
    print("  explored one deep cost under half a second. STEP-BY-STEP PLAY IS")
    print("  THE TRACTABLE CASE, and it is also the mechanic that was wanted.")
    print()
    print("  THE LAST TWO COLUMNS ARE P1, AND BOTH USED TO BE UNREADABLE.")
    print("  'notices' is what build_network SAID while discovering each row --")
    print("  it printed them to a stdout no windowed application has, and they")
    print("  are now carried on the network and published in the Snapshot the")
    print("  reports panel already renders. 'frontier' is species DISCOVERED and")
    print("  never expanded: the generation limit used to break out of the loop")
    print("  with a non-empty frontier and say nothing, while max_species,")
    print("  oversize molecules and mixed standard states all reported.")
    print()
    print("  IT IS THE STRONGEST OF THE THREE CLAIMS AND WAS THE SILENT ONE.")
    print("  The other two are about species never REGISTERED; this one is about")
    print("  species that are in the flask and whose onward chemistry was never")
    print("  looked for -- an approximation touching MATTER, which GAME_DESIGN")
    print("  section 3 forbids outright and section 8.2 readmits only because a")
    print("  coverage limit is never silent.")
    print()
    print("  AND THIS PANEL CAUGHT P1'S OWN FIRST VERSION BEING WRONG. The gens=2")
    print("  rows hit max_species BEFORE the generation bound, so the generation")
    print("  branch never ran, and reading the frontier only on that branch")
    print("  reported 0 for a 400-species network truncated mid-round. THE BOUND")
    print("  THAT BIT IS NOT ALWAYS THE BOUND THAT WAS DECLARED: the frontier is")
    print("  now taken on either exit and the notice says which one stopped it.")
    print("  On a capped row it is a LOWER bound -- the interrupted round left")
    print("  combinations of the previous frontier untried as well.")


def panel6():
    rule("PANEL 6 -- WHAT A SHELF MAY HOLD, AND WHY IT IS NOT EVERYTHING")
    refused = [c for c in BP.compounds if BP._tier.get(c) == "refused"]
    print(f"  corpus compounds                                 "
          f"{len(BP.compounds):5d}")
    print(f"  ... REFUSED a price by the element floor         {len(refused):5d}")
    print(f"  ... so the largest possible inventory is         "
          f"{len(BP.compounds) - len(refused):5d}")
    print()
    print(f"  natural starting materials today                 "
          f"{len(BP.NATURAL_IDS):5d}")
    print()
    print("  A refused species cannot enter a flask: the estimators are fitted")
    print("  to neutral multi-element molecules and outside that domain they")
    print("  return a well-formed number that means nothing. The refusal is the")
    print("  feature. A picker must show them greyed WITH THE REASON rather")
    print("  than let a player charge one and fail late.")


def main() -> None:
    panel1()
    panel2()
    panel3()
    panel4()
    panel5()
    panel6()
    print()


if __name__ == "__main__":
    main()
