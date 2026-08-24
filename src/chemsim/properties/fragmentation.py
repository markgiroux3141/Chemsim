"""Layer 1 -- group-contribution fragmentation, shared by Joback and UNIFAC.

Both methods answer the same structural question: *which groups is this molecule
made of, and how many of each?* Only the group table differs. The algorithm is:

  1. Try groups in PRIORITY order, highest first. Priority encodes chemical
     specificity -- ``-COOH`` must claim its atoms before ``-OH`` and ``>C=O``
     can split it between them, and ``CH3COO`` (an ester) must be tried before
     the bare ``CH3``.

  2. Each match GREEDILY claims a disjoint set of heavy atoms. A match that
     overlaps an already-claimed atom is rejected, so every atom belongs to
     exactly one group.

  3. VERIFY. Two independent checks: every heavy atom must be claimed, and the
     summed atom tally of the assigned groups (including hydrogens, which the
     patterns never claim explicitly) must equal the molecular formula.

  4. If step 3 REFUSES, SEARCH -- see below. The greedy answer is never
     overruled; the search only ever runs where greedy had no answer at all.

Step 3 is the part that earns its keep. Group patterns are written to be
readable, not airtight, so a pattern intended for an ether will happily match an
alcohol's oxygen and quietly lose a hydrogen. The formula check turns that into
a loud failure instead of a plausible wrong number -- which matters because
group contribution is at its most dangerous when it *succeeds* on a molecule it
does not actually cover.

## Step 4, and why it is a FALLBACK rather than the algorithm

A greedy pass can strand atoms it did not have to strand. Priority says which
group is *preferred*, not which is *possible*, so taking the biggest available
match at every step can consume an atom that the only workable decomposition
needed elsewhere -- and step 3 then refuses a molecule the table does cover.
Measured over ``data/catalog``: with the loose ketone patterns corrected, 20 of
its 1155 neutral organics fail for exactly this reason and no other -- benzyl
chloride, coumarin, warfarin, capsaicin and the like, where an aromatic-carbon
group takes an atom the substituent group needed.

So on failure the atoms are re-covered by depth-first search: take the
lowest-numbered unclaimed atom, try every match that covers it in priority
order, recurse. The running atom tally is bounded by the formula at every node,
which is what makes the search cheap -- a branch that has already spent more
hydrogens than the molecule has is abandoned there rather than at the leaf.

⚠ **The search runs ONLY after the greedy pass has been refused, and that
ordering is load-bearing rather than an optimisation.** Every decomposition this
module returns today, for every method that uses it, is the greedy one; a
molecule that fragments now fragments identically afterwards, because for that
molecule the search is unreachable. What the search can turn into an answer is a
REFUSAL, never another answer. (It also keeps the cost off the common path: the
species that pay for the search are the ones that used to return nothing.)

⚠ **A search that runs out of budget REFUSES, and says which refusal it is.**
"I did not find a cover" is not "there is no cover", and the two must not be
reported as though they were the same statement.

No rdkit here: pattern matching goes through ``matter.Molecule``, so this stays
above Boundary 1.
"""

from __future__ import annotations

from typing import Protocol, Sequence

from chemsim.matter import Molecule

# How many nodes the fallback search may open before giving up. Measured over
# ``data/catalog``'s 1300 fragmentable species: 517 searches run, the deepest
# SUCCESSFUL one opens 18 nodes, and the most expensive REFUSAL -- where the
# whole space is enumerated before concluding there is no cover -- opens 718.
# Nothing came within a factor of 25 of this limit, and the searches together
# cost 0.01 s of the 0.70 s the whole catalog takes to fragment. So this is a
# runaway guard rather than a tuning parameter, and hitting it is reported as a
# refusal to answer rather than as an absence.
SEARCH_NODE_LIMIT = 20_000


class FragmentationError(ValueError):
    """Raised when a molecule cannot be fully decomposed into a group table."""


class Group(Protocol):
    """What the algorithm needs of a group, whichever table it comes from."""

    group_id: int
    priority: int
    atoms: dict[str, int]


def _patterns(group: Group) -> tuple[str, ...]:
    """A group's SMARTS, whether the table stores one pattern or several."""
    smarts = group.smarts  # type: ignore[attr-defined]
    return (smarts,) if isinstance(smarts, str) else tuple(smarts)


def by_priority(groups: Sequence[Group]) -> list[Group]:
    """Fragmentation order: highest priority first, id as a stable tie-breaker."""
    return sorted(groups, key=lambda g: (-g.priority, g.group_id))


def _candidates(
    molecule: Molecule, groups: Sequence[Group]
) -> list[tuple[Group, frozenset[int]]]:
    """Every (group, atom set) this molecule offers, in priority order.

    Computed once and shared by the greedy pass and the search, because the
    substructure matching is the expensive part and both need the same list.
    Atom sets are deduplicated per group: a symmetric pattern reports the same
    atoms in several orders, which the greedy pass rejects as an overlap anyway
    and which would give the search identical branches to explore.
    """
    out: list[tuple[Group, frozenset[int]]] = []
    for group in groups:
        seen: set[frozenset[int]] = set()
        for pattern in _patterns(group):
            for match in molecule.substructure_matches(pattern):
                atoms = frozenset(match)
                if atoms in seen:
                    continue
                seen.add(atoms)
                out.append((group, atoms))
    return out


def _tally(counts: dict[int, int], groups_by_id: dict[int, Group]) -> dict[str, int]:
    """What the assigned groups add up to as a formula, hydrogens included."""
    tally: dict[str, int] = {}
    for gid, n in counts.items():
        for element, k in groups_by_id[gid].atoms.items():
            if k:
                tally[element] = tally.get(element, 0) + k * n
    return tally


def _search(
    candidates: list[tuple[Group, frozenset[int]]],
    n_heavy: int,
    formula: dict[str, int],
) -> tuple[dict[int, int] | None, bool]:
    """Cover every heavy atom exactly once, with an atom tally equal to ``formula``.

    Returns ``(counts, exhausted)``. ``counts`` is the decomposition if one was
    found, otherwise None -- and then ``exhausted`` distinguishes "the whole
    space was searched and there is no cover" from "the node budget ran out and
    none was found", which are different claims.
    """
    full = (1 << n_heavy) - 1
    # Matches indexed by the atoms they cover, so a node enumerates only the
    # candidates that can settle the atom it is trying to settle.
    covering: list[list[tuple[int, Group]]] = [[] for _ in range(n_heavy)]
    for group, atoms in candidates:
        mask = 0
        for a in atoms:
            mask |= 1 << a
        for a in atoms:
            covering[a].append((mask, group))

    counts: dict[int, int] = {}
    tally: dict[str, int] = {}
    budget = SEARCH_NODE_LIMIT

    def recurse(claimed: int) -> dict[int, int] | None:
        nonlocal budget
        if claimed == full:
            return dict(counts) if tally == formula else None
        if budget <= 0:
            return None
        budget -= 1
        # Settle the lowest unclaimed atom. Fixing WHICH atom each node settles
        # is what makes this a search over covers rather than over orderings of
        # the same cover.
        rest = ~claimed & full
        atom = (rest & -rest).bit_length() - 1
        for mask, group in covering[atom]:
            if mask & claimed:
                continue
            atoms = group.atoms
            for element, k in atoms.items():
                if k and tally.get(element, 0) + k > formula.get(element, 0):
                    break
            else:
                gid = group.group_id
                counts[gid] = counts.get(gid, 0) + 1
                for element, k in atoms.items():
                    if k:
                        tally[element] = tally.get(element, 0) + k
                found = recurse(claimed | mask)
                if found is not None:
                    return found
                for element, k in atoms.items():
                    if k:
                        tally[element] -= k
                        if not tally[element]:
                            del tally[element]
                if counts[gid] > 1:
                    counts[gid] -= 1
                else:
                    del counts[gid]
        return None

    result = recurse(0)
    return result, budget > 0


def fragment(
    molecule: Molecule,
    groups: Sequence[Group],
    groups_by_id: dict[int, Group],
    *,
    method: str,
) -> dict[int, int]:
    """Partition a molecule into groups; raise if coverage is incomplete.

    ``groups`` must already be in priority order (see :func:`by_priority`).
    """
    candidates = _candidates(molecule, groups)

    claimed: set[int] = set()
    counts: dict[int, int] = {}
    for group, atoms in candidates:
        if atoms & claimed:
            continue  # an atom here already belongs to a better group
        claimed |= atoms
        counts[group.group_id] = counts.get(group.group_id, 0) + 1

    n_heavy = molecule.n_heavy_atoms
    formula = molecule.element_counts()
    complete = len(claimed) == n_heavy
    tally = _tally(counts, groups_by_id)
    if complete and tally == formula:
        return counts

    # The greedy pass has been refused, and its diagnostic is built here, before
    # the search: it names what went wrong with the decomposition the table
    # PREFERS, which is the useful thing to read. The search's own failure is a
    # statement about the search and is appended rather than substituted.
    if not complete:
        symbols = molecule.atom_symbols()
        missing = [s for i, s in enumerate(symbols) if i not in claimed]
        greedy_says = (
            f"{molecule.smiles!r}: incomplete {method} fragmentation "
            f"(unassigned heavy atoms: {missing})"
        )
    else:
        greedy_says = (
            f"{molecule.smiles!r}: {method} group atom tally {tally} "
            f"!= formula {formula}"
        )

    found, exhausted = _search(candidates, n_heavy, formula)
    if found is not None:
        return found
    raise FragmentationError(
        greedy_says + (
            " -- and no other assignment of these patterns covers it either"
            if exhausted else
            f" -- and the fallback search hit its {SEARCH_NODE_LIMIT}-node budget "
            "without finding one, so this is a refusal to answer rather than a "
            "statement that no decomposition exists"
        )
    )
