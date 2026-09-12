"""T4 -- the headline metric: distinct reactions reachable from the shelf.

Every PAIR of chargeable rows on the shelf's ``natural`` tier, expanded to a
fixpoint with the whole template table, and the distinct concrete reactions
counted across all of them. This measures what a player can actually do with
what they can dig up, it is COMPUTED rather than declared, and it cannot be
gamed by adding rows to a list -- the trap G4 found in the granularity scorer
and the reason the ~70-row organic-family checklist was refused as a headline.

WHY A PAIR AND NOT THE WHOLE SHELF AT ONCE
------------------------------------------
One flask holding all 45 natural species hits the 400-species cap in its first
round and reports a frontier of hundreds: the number that comes back is the
cap's, not the chemistry's. A pair is the smallest unit that can react at all
and the largest that runs to a fixpoint often enough for the total to mean
something -- and it is also what the bench does, so the metric and the game
agree about what a step is.

WHAT THE NUMBER IS NOT
----------------------
It is a LOWER BOUND, twice over, and both bounds report themselves in the
output file rather than being buried here. Pairs that hit ``max_species`` were
cut short, so their reactions are undercounted; and a reaction needing three
starting materials is invisible to a sweep over pairs. Neither is hidden: the
summary carries the capped-pair count and the per-pair rows carry each one's
own species count and frontier.

Cost: ~35 minutes for 630 pairs, measured 2026-09-12. That is why this writes a
committed artefact and is NOT part of ``check.ps1`` --
``validation/catalog_coverage.py`` READS the file, the same arrangement
``PLAYABLE.md``'s footer already has.

It also SEGFAULTS, and not on any particular pair: exit 139 out of RDKit at pair
397 on one run and 547 on the next, where 547 completes on its own in 11 s. So
the sweep checkpoints every finished pair, names the pair it is attempting on
stderr, resumes where it stopped, and records a pair that dies ``CRASH_LIMIT``
times rather than retrying it forever. Re-run it until it exits 0; the run of
record did so on its first attempt and reproduced the previous run's counts
exactly.

    python tools/build_reachable.py            # regenerate (resumes if it died)
    python tools/build_reachable.py --check     # re-run from scratch and compare
    python tools/build_reachable.py --sample 20 # a cheap smoke of the machinery
"""

from __future__ import annotations

import argparse
import contextlib
import io
import itertools
import json
import pathlib
import random
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chemsim.engine import inventory as inv            # noqa: E402
from chemsim.network import build_network              # noqa: E402
from chemsim.properties import (                       # noqa: E402
    VolatilityProvider,
    electrolyte_provider,
)
from chemsim.ui.examples import LIBRARY_TIER, full_library  # noqa: E402

OUT = ROOT / "data" / "catalog" / "derived" / "reachable.psv"

# The bench's own bound, so the metric and the game stop in the same place.
MAX_SPECIES = 400


def pairs_of(items):
    return list(itertools.combinations(sorted(items, key=lambda i: i.id), 2))


PARTIAL = OUT.with_suffix(".partial.json")
PENDING = OUT.with_suffix(".pending.json")

# How many times one pair may kill the interpreter before it is recorded as a
# refusal and skipped. Two, because the crash is NOT deterministic: the sweep
# segfaulted at pair 397 on one run and 547 on the next, and pair 547 completes
# on its own in 11 s. Whatever it is -- RDKit is a C++ library and this is a
# hard SIGSEGV, not an exception -- it depends on what ran before it, so a
# retry usually gets past. A pair that dies twice is reported, not retried
# forever.
CRASH_LIMIT = 2


def _load_partial() -> dict:
    """Pairs already expanded, as ``(a, b) -> (row, reaction keys)``.

    A crash-resume cache and nothing else: it is not committed, it is deleted
    when the artefact is written, and `--check` ignores it by re-running with
    `resume=False`.
    """
    if not PARTIAL.exists():
        return {}
    out = {}
    for line in PARTIAL.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        out[tuple(rec["pair"])] = (tuple(rec["row"]),
                                   {_retuple(k) for k in rec["keys"]})
    return out


def _retuple(value):
    """JSON gives lists back; a reaction key is NESTED tuples and must hash.

    ``ConcreteReaction.key()`` is ``(name, (reactants...), (products...),
    phase)``, so a one-level ``tuple()`` leaves two lists inside and the set
    build raises ``unhashable type: 'list'`` -- on the RESUME path only, which
    is why the first crash-resume run got past the write and died on the read.
    """
    return tuple(_retuple(v) if isinstance(v, list) else v for v in value)


def _crashes() -> dict[str, int]:
    """Pairs that killed a previous run, and how often. See ``CRASH_LIMIT``.

    The marker is written BEFORE the work and cleared after, so a run that comes
    back to find one is looking at the pair that killed its predecessor. This is
    the only way to learn anything from a SIGSEGV: there is no traceback, no
    exception, and stdout was being captured.
    """
    if not PENDING.exists():
        return {}
    return json.loads(PENDING.read_text(encoding="utf-8"))


def _mark(pending: dict, pair) -> None:
    pending["current"] = list(pair)
    PENDING.write_text(json.dumps(pending), encoding="utf-8")


def _append_partial(row, keys) -> None:
    with PARTIAL.open("a", encoding="utf-8") as fh:
        print(json.dumps({"pair": [row[0], row[1]], "row": list(row),
                          "keys": [list(k) for k in keys]}), file=fh)


def credited(names) -> set[str]:
    """Template names, with a reverse reaction credited to its forward.

    ``fischer_esterification_rev`` is not a second capability -- detailed balance
    derives it from the forward, so a shelf that reaches one reaches both. The
    two would otherwise be counted as two of the 57 and the fired count would
    read high by however many reversible templates fired.
    """
    return {n[:-4] if n.endswith("_rev") else n for n in names}


def sweep(limit: int | None = None, seed: int = 0, resume: bool = True):
    """Expand every natural pair and return (rows, summary, silent, top).

    Checkpointed, and that is not a nicety. The first full run SEGFAULTED --
    exit 139, a hard interpreter crash inside RDKit, 35 minutes in and with
    every pair's output swallowed by the ``redirect_stdout`` that keeps the
    notices out of the console. Nothing said which pair. So each finished pair
    is appended to a partial file as it lands, the pair being attempted is
    written to stderr before the work starts, and a re-run skips what is already
    done: a crash then costs one pair and NAMES it.
    """
    thermo = electrolyte_provider()
    volatility = VolatilityProvider(thermo)
    library = full_library()
    natural = [i for i in inv.shelf(("natural",)) if i.chargeable]
    todo = pairs_of(natural)
    if limit is not None:
        todo = todo[:]
        random.Random(seed).shuffle(todo)
        todo = todo[:limit]
        todo.sort(key=lambda p: (p[0].id, p[1].id))

    done = _load_partial() if resume and limit is None else {}
    pending = _crashes() if resume and limit is None else {}
    crashed: dict[str, int] = dict(pending.get("crashed", {}))
    was = pending.pop("current", None)
    if was and tuple(was) not in done:
        label = " + ".join(was)
        crashed[label] = crashed.get(label, 0) + 1
        pending["crashed"] = crashed
        print(f"the previous run died on {label} "
              f"(attempt {crashed[label]} of {CRASH_LIMIT})",
              file=sys.stderr, flush=True)
    dead = {k for k, v in crashed.items() if v >= CRASH_LIMIT}
    seen: set[tuple] = set()
    by_template: dict[str, set] = {}
    rows, capped, inert = [], 0, 0
    started = time.perf_counter()
    for i, (a, b) in enumerate(todo, 1):
        cached = done.get((a.id, b.id))
        label = f"{a.id} + {b.id}"
        print(f"[{i}/{len(todo)}] {label}"
              + ("  (cached)" if cached else ""), file=sys.stderr, flush=True)
        if label in dead and not cached:
            # Reported, not silently dropped: the artefact carries the pair and
            # the count, so "this shelf pair crashes the toolkit" is a visible
            # limit rather than a hole in a total.
            rows.append((a.id, b.id, 0, 0, "crashed", 0))
            continue
        if cached:
            row, keys = cached
        else:
            if limit is None:
                _mark(pending, (a.id, b.id))
            species = sorted(set(a.species) | set(b.species))
            with contextlib.redirect_stdout(io.StringIO()):
                net = build_network(species, library, thermo=thermo,
                                    volatility=volatility,
                                    max_species=MAX_SPECIES, generations=None)
            keys = {r.key() for r in net.reactions if not r.is_null()}
            row = (a.id, b.id, len(net.species), len(keys),
                   "capped" if len(net.species) >= MAX_SPECIES else "fixpoint",
                   len(net.unexpanded))
            if limit is None:
                _append_partial(row, keys)
                pending.pop("current", None)
                PENDING.write_text(json.dumps(pending), encoding="utf-8")
        seen |= keys
        for key in keys:
            by_template.setdefault(key[0], set()).add(key)
        capped += row[4] == "capped"
        inert += not keys
        rows.append(row)
    # A TEMPLATE THAT NEVER FIRES IS THE THING THE TOTAL HIDES. A reaction
    # count is dominated by whichever template is most promiscuous -- one
    # glycosylation over a sugar frontier is thousands of them -- so the count
    # of templates that fire AT ALL is reported beside it, and it is the number
    # that says what a shelf can actually do.
    #
    # A reverse reaction is its forward's own name with '_rev', and it is not a
    # separate capability: both are credited to the forward template.
    fired = credited(by_template)
    summary = {
        "natural_rows": len(natural),
        "pairs": len(todo),
        "distinct_reactions": len(seen),
        "templates_fired": len(fired),
        "capped_pairs": capped,
        "inert_pairs": inert,
        "crashed_pairs": len(dead),
        "templates": len(library),
        "tier": LIBRARY_TIER,
        "seconds": round(time.perf_counter() - started, 1),
    }
    silent = sorted({t.name for t in library} - fired)
    # Merged the same way ``fired`` is: a reverse reaction counts toward its
    # forward template. Listing ``fischer_esterification_rev`` beside
    # ``fischer_esterification`` as two of the busiest reads as two capabilities
    # and is one, and the share taken over that list double-counts every
    # reversible template.
    merged: dict[str, int] = {}
    for name, keys in by_template.items():
        merged[next(iter(credited({name})))] = (
            merged.get(next(iter(credited({name}))), 0) + len(keys)
        )
    top = sorted(((n, k) for k, n in merged.items()), reverse=True)
    return rows, summary, silent, top


def render(rows, summary, silent, top) -> str:
    out = [
        "# DERIVED by tools/build_reachable.py -- do not hand-edit.",
        "# Every pair of chargeable natural shelf rows, expanded to a fixpoint",
        f"# with all {summary['templates']} '{summary['tier']}' templates and a "
        f"{MAX_SPECIES}-species cap.",
        "# a | b | species | reactions | stop | frontier",
        "#",
        "# A capped pair is a LOWER bound on its own reaction count, and the",
        "# total is a lower bound on what a shelf holds: a reaction needing a",
        "# third starting material is invisible to a sweep over pairs.",
    ]
    for key in ("natural_rows", "pairs", "distinct_reactions", "templates_fired",
                "capped_pairs", "inert_pairs", "crashed_pairs", "templates",
                "tier"):
        out.append(f"#! {key} = {summary[key]}")
    out.append(f"#! silent_templates = {', '.join(silent) or '(none)'}")
    out.append("# the ten busiest templates, distinct reactions each")
    out.append("# (a reverse counts toward its forward, as in templates_fired):")
    for n, name in top[:10]:
        out.append(f"#   {n:6d}  {name}")
    out.append("#")
    for r in rows:
        out.append(" | ".join(str(x) for x in r))
    return "\n".join(out) + "\n"


def read_summary(path: pathlib.Path = OUT) -> dict[str, str]:
    """The ``#!`` header of the artefact, as a dict. Empty if it is not there.

    The reader ``validation/catalog_coverage.py`` uses. A missing file is not an
    error here: the report says the number has not been computed rather than
    inventing one.
    """
    if not path.exists():
        return {}
    got, busiest = {}, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#! "):
            key, _, value = line[3:].partition(" = ")
            got[key.strip()] = value.strip()
        elif line.startswith("#   "):
            count, _, name = line[4:].strip().partition("  ")
            if count.isdigit():
                busiest.append((int(count), name.strip()))
        elif not line.startswith("#"):
            break
    # The busiest templates are in the file already; the SHARE is arithmetic on
    # them and is derived here rather than written into the artefact, so it
    # cannot disagree with the rows it is computed from.
    got["busiest"] = busiest
    return got


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="re-run and compare with the committed file")
    ap.add_argument("--sample", type=int, default=None,
                    help="only N randomly chosen pairs -- a smoke, never committed")
    args = ap.parse_args()

    rows, summary, silent, top = sweep(limit=args.sample, resume=not args.check)
    text = render(rows, summary, silent, top)
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print(f"  silent: {len(silent)} templates never fired")

    if args.sample is not None:
        print("  (sample run -- nothing written)")
        return 0
    if args.check:
        if not OUT.exists():
            print(f"MISSING {OUT}: run the generator and commit the result")
            return 1
        if OUT.read_text(encoding="utf-8") != text:
            print(f"STALE {OUT}: run the generator and commit the result")
            return 1
        print(f"ok {OUT}")
        return 0
    OUT.write_text(text, encoding="utf-8")
    PARTIAL.unlink(missing_ok=True)
    PENDING.unlink(missing_ok=True)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
