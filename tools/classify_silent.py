"""T6 -- why each template the shelf cannot reach stays silent.

``tools/build_reachable.py`` measured that 25 of the 57 templates fire from some
pair of natural shelf rows, and named the rest. That list is a work queue nobody
wrote by hand, but a name alone does not say what to do about it: a template
silent because its substrate is not on the shelf wants a shelf row or a route, a
template silent because a pair cannot hold three things wants a wider sweep, and
a template silent with everything it needs already in the flask is worth more
than the other two together.

WHAT THE SHELF CAN MAKE, EXACTLY
--------------------------------
The 35-minute pair sweep is not re-run, and the classifier does not guess at
reachability either. The 23 natural rows whose species are all at most
``SMALL_MOLECULE`` heavy atoms go into ONE flask with the whole library and
expand to a fixpoint: 41 species, frontier zero, under a second. That is not a
bounded estimate, it is the closure -- the small-molecule half of the shelf is
CLOSED, and every "the shelf cannot make X" below rests on it rather than on a
cap. The threshold separates sulfur (8 heavy atoms) from alpha-pinene (10) with
nothing in between, and it exists because the sugars and fats are what make a
whole-shelf flask hit its cap in the first round.

So the candidate pool is the 36 rows' own species plus that closure. A slot with
no match anywhere in the pool has no substrate, full stop.

THE LABELS, AND HOW A WITNESS DECIDES THEM
------------------------------------------
For each silent template, split the reactant side of its SMARTS into slots and
find the SMALLEST set of shelf rows matching every slot. Then BUILD that
witness -- one flask, one template, one generation -- because a slot match is
necessary and not sufficient: nitrate matches ``[N;H0]=[O]`` and is not nitric
oxide, and the rewrite that follows makes a five-valent nitrogen.

* ``no-substrate``  -- a slot matches nothing in the pool, or every slot matches
  but no rewrite survives, which means the match was a substructure rather than
  the substrate. The evidence names the slot.
* ``needs-more-than-a-pair`` -- the witness fires, and it costs three or more
  shelf rows, or a species only the closure makes. Invisible to a sweep over
  pairs by construction, which is the lower bound ``reachable.psv`` declares
  about itself. An electrode template is here too: every sweep runs at
  ``cell_potential=0``, a condition a pair sweep does not vary.
* ``cannot-fire`` -- a flask the sweep ALREADY HELD has a match for every slot
  and still yields nothing. Either the template applied and the rewrite was
  thrown away (an ion with no pKa), or it fires here and not in the sweep. Both
  are defects and both are the group worth taking first.

    python tools/classify_silent.py            # regenerate the artefact
    python tools/classify_silent.py --check    # re-derive and compare
"""

from __future__ import annotations

import argparse
import contextlib
import io
import itertools
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rdkit import Chem, RDLogger                          # noqa: E402

from chemsim.engine import inventory as inv               # noqa: E402
from chemsim.network import build_network                 # noqa: E402
from chemsim.properties import (                          # noqa: E402
    VolatilityProvider,
    electrolyte_provider,
)
from chemsim.reactions.template_data import TEMPLATES     # noqa: E402
from chemsim.ui.examples import full_library              # noqa: E402

RDLogger.DisableLog("rdApp.*")

REACHABLE = ROOT / "data" / "catalog" / "derived" / "reachable.psv"
OUT = ROOT / "data" / "catalog" / "derived" / "silent_templates.psv"

# Heavy atoms per species below which a natural row joins the closure flask.
# The shelf jumps from sulfur's 8 to alpha-pinene's 10 with nothing between, so
# the constant is not a tuning knob: any value in (8, 10) gives the same 23 rows.
SMALL_MOLECULE = 9

# A witness is searched up to this many shelf rows. Larger than any template's
# distinct reactant count, so "no witness at this size" means no witness.
MAX_WITNESS = 4

CLOSURE = "closure"


def silent_names() -> list[str]:
    """The silent list, READ from the sweep's artefact and never re-declared."""
    for line in REACHABLE.read_text(encoding="utf-8").splitlines():
        if line.startswith("#! silent_templates"):
            body = line.split("=", 1)[1].strip()
            return [] if body == "(none)" else [n.strip()
                                                for n in body.split(",")]
    raise SystemExit(f"no silent_templates line in {REACHABLE}")


def slots(smarts: str) -> list[str]:
    """The reactant side of a reaction SMARTS, split on its TOP-LEVEL dots.

    A bare ``split('.')`` is wrong: a dot inside ``[$(...)]`` is a recursive
    SMARTS and a dot inside a bracket atom is not a separator at all.
    """
    left = smarts.split(">>")[0]
    out, depth, cur = [], 0, []
    for ch in left:
        if ch in "[(":
            depth += 1
        elif ch in "])":
            depth -= 1
        if ch == "." and depth == 0:
            out.append("".join(cur))
            cur = []
            continue
        cur.append(ch)
    out.append("".join(cur))
    return [s for s in out if s]


def natural_rows():
    return [i for i in inv.shelf(("natural",)) if i.chargeable]


def small_rows(rows):
    """The rows that go in the closure flask -- see ``SMALL_MOLECULE``."""
    out = []
    for item in rows:
        sizes = [Chem.MolFromSmiles(s).GetNumHeavyAtoms() for s in item.species
                 if Chem.MolFromSmiles(s) is not None]
        if sizes and max(sizes) < SMALL_MOLECULE:
            out.append(item)
    return out


def closure(rows, thermo, volatility):
    """The small-molecule half of the shelf, expanded to a fixpoint.

    Returns (species, frontier). A non-zero frontier would mean this ran into
    the cap and every "cannot make" below became an estimate; the artefact
    carries the frontier so that cannot happen silently.
    """
    species = sorted({s for i in rows for s in i.species})
    with contextlib.redirect_stdout(io.StringIO()):
        net = build_network(species, full_library(), thermo=thermo,
                            volatility=volatility, max_species=400,
                            generations=None)
    return sorted(net.species), len(net.unexpanded)


def matchers(smiles_list):
    out = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is not None:
            out.append((smi, mol))
    return out


def slot_sources(pats, rows, pool):
    """Per slot: the shelf rows that match it, and the closure species that do.

    ``None`` for a slot nothing matches -- that is the blocking slot and the
    caller names it.
    """
    out = []
    for pat in pats:
        if pat is None:
            return None, None
        hit = {item.id for item in rows
               if any(m.HasSubstructMatch(pat)
                      for _, m in matchers(item.species))}
        via = [smi for smi, mol in pool if mol.HasSubstructMatch(pat)]
        if not hit and not via:
            return None, None
        out.append((hit, via))
    return out, True


def witness(sources, row_ids, cap: int = MAX_WITNESS):
    """The cheapest way to satisfy every slot, as (rows, uses_closure).

    Exhaustive over shelf rows rather than greedy -- 36 rows and at most four
    slots makes the size-3 search 7,140 combinations, and a greedy cover would
    report three rows where a pair exists, which is the whole difference
    between a bug and a lower bound.
    """
    shelf_only = [hit for hit, _ in sources]
    if all(shelf_only):
        for size in range(1, cap + 1):
            for combo in itertools.combinations(row_ids, size):
                picked = set(combo)
                if all(picked & h for h in shelf_only):
                    return sorted(picked), False
    # At least one slot needs something only the closure makes, so the witness
    # is the closure plus whatever rows the remaining slots need.
    rest = [hit for hit, via in sources if hit and not via] or []
    need: list[str] = []
    for hit in rest:
        if not any(r in need for r in hit):
            need.append(sorted(hit)[0])
    return sorted(need), True


def flask(row_ids, extra, template, thermo, volatility):
    """Build the witness: those rows' species (plus the closure) and one template."""
    species = {s for item in natural_rows() if item.id in row_ids
               for s in item.species}
    species |= set(extra)
    with contextlib.redirect_stdout(io.StringIO()):
        net = build_network(sorted(species), [template], thermo=thermo,
                            volatility=volatility, max_species=400,
                            generations=1)
    live = [r for r in net.reactions if not r.is_null()]
    return bool(live), net.notices


def _dropped(notices) -> str:
    """How many rewrites a reported limit threw away, phrased for one cell.

    The notice itself is a paragraph -- it is written for a player who needs the
    whole claim -- so the artefact carries its COUNT and its cause and
    ``build_network`` keeps the prose.
    """
    for note in notices:
        if "could not be priced" in note.lower():
            found = re.search(r"(\d+) species were DISCOVERED", note)
            count = found.group(1) if found else "some"
            return ("the template applies and the rewrite is discarded: "
                    f"{count} product species cannot be priced")
    return ""


def whole_molecule(pat, pool) -> bool:
    """Does some pool species match this slot as ITSELF, not as a fragment?

    The diagnostic that separates nitrate from nitric oxide. Nitrate matches
    ``[N;H0]=[O]`` inside a larger ion, the rewrite that follows makes a
    five-valent nitrogen, and the template is silent for want of a substrate
    rather than for any defect.
    """
    for _, mol in pool:
        match = mol.GetSubstructMatch(pat)
        if match and len(set(match)) == mol.GetNumHeavyAtoms():
            return True
    return False


def classify():
    thermo = electrolyte_provider()
    volatility = VolatilityProvider(thermo)
    library = {t.name: t for t in full_library()}
    rows = natural_rows()
    row_ids = [i.id for i in rows]
    small = small_rows(rows)
    closed, frontier = closure(small, thermo, volatility)
    pool = matchers(sorted(set(closed) | {s for i in rows for s in i.species}))
    out = []
    for name in silent_names():
        rec = TEMPLATES[name]
        raw = slots(rec.smarts)
        pats = [Chem.MolFromSmarts(s) for s in raw]
        n_slots = len(pats)
        sources, ok = slot_sources(pats, rows, pool)
        if not ok:
            blocking = next(
                (s for s, p in zip(raw, pats)
                 if p is None or not any(m.HasSubstructMatch(p)
                                         for _, m in pool)), raw[0])
            out.append((name, "no-substrate", n_slots, 0, "", blocking,
                        "nothing the shelf holds or can make matches it"))
            continue
        found, via = witness(sources, row_ids)
        extra = closed if via else []
        fired, notices = flask(found, extra, library[name], thermo, volatility)
        label = "cannot-fire"
        blocking = ""
        cost = len(found) + (1 if via else 0)
        w = "+".join([*found, "closure"] if via else found)
        if rec.electrons:
            label = "needs-more-than-a-pair"
            why = (f"an electrode reaction, {rec.electrons} e-; "
                   "every sweep runs at cell_potential=0")
        elif not fired:
            note = _dropped(notices)
            if note and cost <= 2 and not via:
                why = note
            elif note:
                label = "needs-more-than-a-pair"
                why = ("reachable only through the closure, and then "
                       + note)
            else:
                label = "no-substrate"
                blocking = next((s for s, pat in zip(raw, pats)
                                 if not whole_molecule(pat, pool)), raw[0])
                why = ("no rewrite survives: the pool matches it only inside "
                       "a larger molecule")
        elif cost <= 2 and not via:
            why = "fires here and not in the sweep -- contradicts reachable.psv"
        else:
            label = "needs-more-than-a-pair"
            why = f"fires on {cost} sources; a pair sweep cannot hold them"
        out.append((name, label, n_slots, cost, w, blocking, why))
    return out, len(small), len(closed), frontier


def unmapped(smarts: str) -> str:
    """A slot with its atom-map numbers stripped, for grouping only.

    ``[C-:1]#[O+:2]`` and ``[C-:3]#[O+:4]`` are the same carbon monoxide wearing
    two templates' map numbers. Grouping on the raw text reports two missing
    substrates where there is one, which is the difference between a work order
    and a list.
    """
    return re.sub(r":\d+(?=[\]])", "", smarts)


def render(rows, n_small, n_closed, frontier) -> str:
    counts: dict[str, int] = {}
    for r in rows:
        counts[r[1]] = counts.get(r[1], 0) + 1
    out = [
        "# DERIVED by tools/classify_silent.py -- do not hand-edit.",
        "# Why each template named on reachable.psv's silent_templates line",
        "# never fires from a pair of natural shelf rows.",
        "# template | label | slots | witness_cost | witness | blocker |",
        "#   evidence",
        "#",
        "# no-substrate            no species the shelf holds or can make",
        "#                         matches one of its reactant slots -- or one",
        "#                         matches only as a substructure and the",
        "#                         rewrite that follows is impossible.",
        "# needs-more-than-a-pair  every slot is matched, and satisfying them",
        "#                         all costs three or more sources, or a",
        "#                         condition the sweep holds fixed",
        "#                         (cell_potential=0).",
        "# cannot-fire             a flask the sweep ALREADY HELD matched every",
        "#                         slot and yielded nothing. The group worth",
        "#                         taking first.",
        "#",
        "# A witness is the smallest set of shelf rows matching every slot,",
        "# searched exhaustively to 4, then BUILT: the network is the arbiter",
        "# and the SMARTS match only the candidate.",
        "#",
        "# 'closure' in a witness is the small-molecule half of the shelf",
        "# expanded to a fixpoint. Its frontier is reported below: a non-zero",
        "# frontier would make every 'cannot make' here an estimate. It counts",
        "# as ONE source in witness_cost and is 23 rows, so a witness naming it",
        "# is above a pair by construction and is never 'cannot-fire'.",
    ]
    for key in sorted(counts):
        out.append(f"#! {key} = {counts[key]}")
    out.append(f"#! silent = {len(rows)}")
    out.append(f"#! closure_rows = {n_small}")
    out.append(f"#! closure_species = {n_closed}")
    out.append(f"#! closure_frontier = {frontier}")
    blockers: dict[str, list[str]] = {}
    for r in rows:
        if r[5]:
            blockers.setdefault(unmapped(r[5]), []).append(r[0])
    out.append("#")
    out.append("# THE WORK ORDER: one missing substrate holds several")
    out.append("# templates, so the queue is this list and not the 32.")
    out.append(f"#! blocking_substrates = {len(blockers)}")
    for slot, names in sorted(blockers.items(), key=lambda kv: (-len(kv[1]),
                                                               kv[0])):
        out.append(f"#   {len(names)}  {slot}")
        out.append(f"#      {', '.join(sorted(names))}")
    out.append("#")
    for r in rows:
        out.append(" | ".join(str(x) for x in r))
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="re-derive and compare with the committed artefact")
    args = ap.parse_args()
    text = render(*classify())
    if args.check:
        if not OUT.exists():
            print(f"{OUT.name} is missing")
            return 1
        if OUT.read_text(encoding="utf-8") != text:
            print(f"{OUT.name} is stale -- re-run tools/classify_silent.py")
            return 1
        print(f"{OUT.name} is current")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
