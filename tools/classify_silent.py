"""T6 -- why each template the shelf cannot reach stays silent.

``tools/build_reachable.py`` measured that 29 of the 57 templates fire from some
pair of natural shelf rows, and named the rest. That list is a work queue nobody
wrote by hand, but a name alone does not say what to do about it: a template
silent because its substrate is not on the shelf wants a shelf row or a route, a
template silent because a pair cannot hold three things wants a wider sweep, and
a template silent with everything it needs already in the flask is worth more
than the other two together.

WHAT THE SHELF CAN MAKE, IN TWO TIERS
-------------------------------------
The 35-minute pair sweep is not re-run, and the classifier does not guess at
reachability either. It builds its candidate pool out of TIERS, each of which is
a set of species together with what it costs in shelf rows to have them:

* every natural row's own species, one row each;
* the CLOSURE -- the rows whose species are all at most ``SMALL_MOLECULE`` heavy
  atoms, put in one flask with the whole library and expanded to a fixpoint. 43
  species, frontier zero, under a second. Not a bounded estimate: the
  small-molecule half of the shelf is CLOSED, so a "cannot make" resting on this
  tier rests on a fixpoint rather than on a cap;
* for each row too big for the closure, that row PLUS the closure expanded ONE
  generation, written ``<row>@1``. This tier is bounded and says so: its
  frontier is reported and is not zero, so a "cannot make" that had to look
  here is an estimate at one step.

The second tier exists because the first was wrong about the shelf rather than
merely narrow. Coniferyl alcohol is 13 heavy atoms, so it never entered the
closure, and ``oxidative_cleavage`` turns it and air into VANILLIN in one
generation -- an aromatic aldehyde the file used to report as a substrate
nothing on the shelf could make, at the top of its own work order. A whole-shelf
closure is not available to fix that: the sugars alone cap a flask in the first
round, which is why the closure is the small-molecule half to begin with.

THE LABELS, AND HOW A WITNESS DECIDES THEM
------------------------------------------
For each silent template, split the reactant side of its SMARTS into slots and
find the CHEAPEST set of tiers matching every slot, cost being the number of
distinct shelf rows plus one if the closure is among them. Then BUILD that
witness -- one flask, one template, one generation -- because a slot match is
necessary and not sufficient: nitrate matches ``[N;H0]=[O]`` and is not nitric
oxide, and the rewrite that follows makes a five-valent nitrogen.

* ``no-substrate``  -- a slot matches nothing in any tier, or every slot matches
  but no rewrite survives, which means the match was a substructure rather than
  the substrate. The evidence names EVERY such slot, not the first: a template
  whose second substrate is missing too is not unblocked by sourcing the first,
  and the work order below counts both.
* ``needs-more-than-a-pair`` -- the witness fires, and it costs three or more
  shelf rows. Invisible to a sweep over pairs by construction, which is the
  lower bound ``reachable.psv`` declares about itself. An electrode template is
  here too: every sweep runs at ``cell_potential=0``, a condition a pair sweep
  does not vary.
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
import dataclasses
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
from chemsim.properties.thermochemistry import (          # noqa: E402
    OutsideEstimatorDomain,
    UnpricedIon,
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

# A witness is searched up to this many tiers. Larger than any template's
# distinct reactant count, so "no witness at this size" means no witness.
MAX_WITNESS = 4

# Species cap for every flask this tool builds, so a tier that hits it reports
# the same bound the closure would have.
MAX_SPECIES = 400

CLOSURE = "closure"

# Suffix on a one-generation tier's label: ``eugenol@1`` is eugenol and the
# closure, expanded one generation with the whole library.
STEP = "@1"


@dataclasses.dataclass(frozen=True, order=True)
class Tier:
    """A set of species a flask can hold, and what having them costs.

    ``rows`` is the natural shelf rows it spends; ``closure`` says whether it
    also spends the closure, which is one source however many rows built it.
    """

    label: str
    species: tuple[str, ...]
    rows: frozenset[str]
    closure: bool


def cost(chosen) -> int:
    """Shelf rows spent by a set of tiers. The closure is one source, once."""
    rows: set[str] = set()
    uses_closure = False
    for tier in chosen:
        rows |= tier.rows
        uses_closure |= tier.closure
    return len(rows) + (1 if uses_closure else 0)


def rank(chosen):
    """Order two witnesses of the same cost. Weaker evidence loses.

    A witness of plain shelf rows is a flask the PAIR SWEEP ACTUALLY HELD, so
    what happens in it is a measurement; one that reaches through the closure or
    through a one-generation tier is an argument about what the shelf could
    become. They can cost the same -- ``oleic-acid+water`` and
    ``cellulose-unit@1`` are both two -- and taking the second hides the
    ``cannot-fire`` the first was reporting.
    """
    return (cost(chosen),
            sum(1 for t in chosen if STEP in t.label),
            1 if any(t.closure for t in chosen) else 0)


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


def priceable(species, thermo):
    """The species the ion overlay will price, and how many it refused.

    An expansion can DISCOVER an ion the 30-row pKa table cannot price -- gallic
    acid's carboxylate comes off tannic acid -- and ``build_network`` reports
    that through ``notices`` and keeps the species. Such a species cannot be fed
    back in as a REACTANT, so a tier holding one cannot be built into a witness
    at all; nor can it be anybody's substrate, which is the same thing said
    about the chemistry. The pool drops it and the artefact carries the count,
    because that is the unpriceable-species limit T5 exists to measure and it
    must not be lost inside a filter.

    ``UnpricedIon`` and not its parent: a LATTICE and a BARE ELEMENT are refused
    by the same ``get`` and are neither missing nor unusable -- calcite and iron
    are shelf rows, priced from ``mineral_data`` and ``element_data`` when the
    network asks. Filtering on the parent threw 15 of the closure's 43 species
    away and called them missing measurements.
    """
    kept, refused = [], 0
    for smi in species:
        try:
            thermo.get(smi)
        except UnpricedIon:
            refused += 1
            continue
        except OutsideEstimatorDomain:
            pass
        kept.append(smi)
    return kept, refused


def expand(species, thermo, volatility, generations):
    """One flask, the whole library, to a fixpoint or to ``generations``.

    Returns (species, frontier, refused). A non-zero frontier means this ran
    into the cap or the generation limit, and every "cannot make" resting on it
    is an estimate; every caller carries the frontier into the artefact so that
    cannot happen silently. ``refused`` is what ``priceable`` dropped.
    """
    with contextlib.redirect_stdout(io.StringIO()):
        net = build_network(sorted(set(species)), full_library(), thermo=thermo,
                            volatility=volatility, max_species=MAX_SPECIES,
                            generations=generations)
    kept, refused = priceable(sorted(net.species), thermo)
    return kept, len(net.unexpanded), refused


def closure(rows, thermo, volatility):
    """The small-molecule half of the shelf, expanded to a fixpoint."""
    species, frontier, refused = expand({s for i in rows for s in i.species},
                                        thermo, volatility, None)
    return species, frontier, refused


def tiers(rows, small, closed, thermo, volatility):
    """Every way to have species in a flask, with its cost.

    Returns (tiers, how many rows got a one-generation tier, their total
    frontier, how many species ``priceable`` refused). See the module docstring
    for what the three kinds mean.
    """
    out = [Tier(CLOSURE, tuple(closed), frozenset(), True)]
    for item in rows:
        out.append(Tier(item.id, tuple(item.species),
                        frozenset({item.id}), False))
    big = [i for i in rows if i not in small]
    frontier = refused = 0
    for item in big:
        made, unexpanded, dropped = expand(set(closed) | set(item.species),
                                           thermo, volatility, 1)
        frontier += unexpanded
        refused += dropped
        out.append(Tier(item.id + STEP, tuple(made),
                        frozenset({item.id}), True))
    return out, len(big), frontier, refused


def matchers(smiles_list):
    out = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is not None:
            out.append((smi, mol))
    return out


def slot_hits(pats, tier_list, pool):
    """Per slot, the tiers holding a species that matches it.

    An empty list is a slot nothing anywhere matches. Matching is done ONCE
    against the union of every tier's species and then mapped back, rather than
    once per tier: the one-generation tiers overlap heavily and the closure sits
    inside all of them.
    """
    out = []
    for pat in pats:
        if pat is None:
            out.append([])
            continue
        found = {smi for smi, mol in pool if mol.HasSubstructMatch(pat)}
        out.append([t for t in tier_list if found.intersection(t.species)])
    return out


def witness(hits, cap: int = MAX_WITNESS):
    """The cheapest set of tiers covering every slot, as (tiers, cost).

    Exhaustive over the tiers that match SOMETHING rather than greedy -- a
    greedy cover would report three rows where a pair exists, which is the
    whole difference between a bug and a lower bound -- and cheapest by
    ``rank``, so a shelf row is preferred to the closure, and the closure to a
    one-generation tier that spends a row on top of it.
    """
    cands = sorted({t for slot in hits for t in slot})
    best = None
    for size in range(1, cap + 1):
        # Every tier spends at least one row except the closure, so a combo of
        # this size costs at least size - 1. Once a witness is in hand, no
        # larger size can beat it. Searching by SIZE alone is what picked
        # ``cellulose-unit@1`` -- one tier, two sources -- over the genuine
        # ``oleic-acid+water`` pair the sweep had actually held.
        if best is not None and size - 1 > best[0][0]:
            break
        for combo in itertools.combinations(cands, size):
            if all(any(t in slot for t in combo) for slot in hits):
                here = rank(combo)
                if best is None or here < best[0]:
                    best = (here, list(combo))
    if best is None:
        return [], 0
    return best[1], best[0][0]


def flask(chosen, template, thermo, volatility):
    """Build the witness: everything its tiers hold, and one template."""
    species = {s for tier in chosen for s in tier.species}
    with contextlib.redirect_stdout(io.StringIO()):
        net = build_network(sorted(species), [template], thermo=thermo,
                            volatility=volatility, max_species=MAX_SPECIES,
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


def unmapped(smarts: str) -> str:
    """A slot with its atom-map numbers stripped, for grouping only.

    ``[C-:1]#[O+:2]`` and ``[C-:3]#[O+:4]`` are the same carbon monoxide wearing
    two templates' map numbers. Grouping on the raw text reports two missing
    substrates where there is one, which is the difference between a work order
    and a list.
    """
    return re.sub(r":\d+(?=[\]])", "", smarts)


def blockers(raw, keep) -> str:
    """The blocker cell: every slot ``keep`` rejects, unmapped and deduplicated.

    Joined with ' + ' because a template can be short of two substrates at once,
    and then sourcing one of them buys nothing. Reporting only the first is what
    put an aromatic aldehyde at the top of a work order on the strength of three
    templates, exactly one of which it would have unblocked.
    """
    out: list[str] = []
    for slot in raw:
        bare = unmapped(slot)
        if not keep(slot) and bare not in out:
            out.append(bare)
    return " + ".join(out)


def why_it_needs_more(chosen, spend, n_small) -> str:
    """Say what the witness actually spends, rather than quoting its cost.

    ``witness_cost`` counts the closure as ONE source, which is the right unit
    for ordering witnesses and the wrong thing to print: a cost of 2 that names
    the closure is 24 shelf rows and not a pair, and "fires on 2 sources; a pair
    sweep cannot hold them" reads as a contradiction of its own number.
    """
    step = sorted(t.label for t in chosen if STEP in t.label)
    via = any(t.closure for t in chosen)
    own = spend - (1 if via else 0)
    if step:
        return (f"fires on {', '.join(step)} -- a row expanded one generation "
                f"against the closure's {n_small} rows")
    if via:
        return (f"fires on the closure, which is {n_small} rows, and {own} "
                "row(s) of its own")
    return f"fires on {spend} shelf rows; a pair sweep cannot hold them"


def classify():
    thermo = electrolyte_provider()
    volatility = VolatilityProvider(thermo)
    library = {t.name: t for t in full_library()}
    rows = natural_rows()
    small = small_rows(rows)
    closed, frontier, refused = closure(small, thermo, volatility)
    tier_list, n_big, step_frontier, step_refused = tiers(
        rows, small, closed, thermo, volatility)
    pool = matchers(sorted({s for t in tier_list for s in t.species}))
    out = []
    for name in silent_names():
        rec = TEMPLATES[name]
        raw = slots(rec.smarts)
        pats = {s: Chem.MolFromSmarts(s) for s in raw}
        hits = slot_hits([pats[s] for s in raw], tier_list, pool)
        matched = {s: bool(h) for s, h in zip(raw, hits)}
        n_slots = len(raw)
        if not all(matched.values()):
            out.append((name, "no-substrate", n_slots, 0, "",
                        blockers(raw, matched.get),
                        "nothing the shelf holds or can make matches it"))
            continue
        chosen, spend = witness(hits)
        fired, notices = flask(chosen, library[name], thermo, volatility)
        via = any(t.closure for t in chosen)
        label = "cannot-fire"
        blocking = ""
        w = "+".join(t.label for t in sorted(chosen))
        if rec.electrons:
            label = "needs-more-than-a-pair"
            why = (f"an electrode reaction, {rec.electrons} e-; "
                   "every sweep runs at cell_potential=0")
        elif not fired:
            note = _dropped(notices)
            if note and spend <= 2 and not via:
                why = note
            elif note:
                label = "needs-more-than-a-pair"
                why = ("reachable only above a pair (" + w + "), and then "
                       + note)
            else:
                label = "no-substrate"
                blocking = blockers(
                    raw, lambda s: whole_molecule(pats[s], pool))
                why = ("no rewrite survives: the pool matches it only inside "
                       "a larger molecule")
        elif spend <= 2 and not via:
            why = "fires here and not in the sweep -- contradicts reachable.psv"
        else:
            label = "needs-more-than-a-pair"
            why = why_it_needs_more(chosen, spend, len(small))
        out.append((name, label, n_slots, spend, w, blocking, why))
    return (out, len(small), len(closed), frontier, n_big, len(pool),
            step_frontier, refused + step_refused)


def work_order(rows) -> list[str]:
    """The queue: one missing substrate holds several templates.

    Each substrate carries two counts. ``blocked`` is how many templates name
    it; ``alone`` is how many name it and nothing else, which is the number
    sourcing it would actually unblock. They differ, and the difference is the
    whole value of the ordering: an aromatic aldehyde blocked three templates
    and would have unblocked one.
    """
    blocked: dict[str, list[str]] = {}
    alone: dict[str, int] = {}
    for row in rows:
        if not row[5]:
            continue
        parts = row[5].split(" + ")
        for slot in parts:
            blocked.setdefault(slot, []).append(row[0])
            if len(parts) == 1:
                alone[slot] = alone.get(slot, 0) + 1
    out = ["#",
           "# THE WORK ORDER: one missing substrate holds several",
           f"# templates, so the queue is this list and not the {len(rows)}.",
           "# 'blocked' is how many templates name this slot; 'alone' is how",
           "# many name it and nothing else, so 'alone' is what sourcing it",
           "# would unblock.",
           f"#! blocking_substrates = {len(blocked)}",
           f"#! substrates_that_unblock_alone = {sum(alone.values())}"]
    order = sorted(blocked.items(),
                   key=lambda kv: (-alone.get(kv[0], 0), -len(kv[1]), kv[0]))
    for slot, names in order:
        out.append(f"#   {len(names)} blocked, {alone.get(slot, 0)} alone  "
                   f"{slot}")
        out.append(f"#      {', '.join(sorted(names))}")
    return out


def render(rows, n_small, n_closed, frontier, n_big, n_pool,
           step_frontier, unpriceable) -> str:
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
        "#                         rewrite that follows is impossible. The",
        "#                         blocker names EVERY such slot, because a",
        "#                         template short of two substrates is not",
        "#                         unblocked by sourcing one of them.",
        "# needs-more-than-a-pair  every slot is matched, and satisfying them",
        "#                         all costs three or more sources, or a",
        "#                         condition the sweep holds fixed",
        "#                         (cell_potential=0).",
        "# cannot-fire             a flask the sweep ALREADY HELD matched every",
        "#                         slot and yielded nothing. The group worth",
        "#                         taking first.",
        "#",
        "# A witness is the cheapest set of TIERS matching every slot, searched",
        "# exhaustively to 4, then BUILT: the network is the arbiter and the",
        "# SMARTS match only the candidate. There are three kinds of tier:",
        "#",
        "#   <row>      one natural shelf row's own species.",
        "#   closure    the rows whose species are all under 9 heavy atoms, in",
        "#              one flask, expanded to a FIXPOINT. Counts as ONE source",
        "#              however many rows built it, so a witness naming it is",
        "#              above a pair by construction and is never 'cannot-fire'.",
        "#   <row>@1    that row PLUS the closure, expanded ONE generation. Two",
        "#              sources. Bounded, not closed: step_frontier below is",
        "#              not zero, so a 'cannot make' that had to look here is an",
        "#              estimate at one step. A whole-shelf closure is not",
        "#              available -- the sugars cap a flask in the first round.",
        "#",
        "# pool_unpriceable is the species an expansion discovered and the",
        "# thermochemistry then refused to price -- an ion with no measured",
        "# pKa, mostly. They are not in the pool: a flask cannot be CHARGED",
        "# with one, and nothing can react with what has no standard state.",
    ]
    for key in sorted(counts):
        out.append(f"#! {key} = {counts[key]}")
    out.append(f"#! silent = {len(rows)}")
    out.append(f"#! closure_rows = {n_small}")
    out.append(f"#! closure_species = {n_closed}")
    out.append(f"#! closure_frontier = {frontier}")
    out.append(f"#! step_rows = {n_big}")
    out.append(f"#! step_frontier = {step_frontier}")
    out.append(f"#! pool_species = {n_pool}")
    out.append(f"#! pool_unpriceable = {unpriceable}")
    out.extend(work_order(rows))
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
