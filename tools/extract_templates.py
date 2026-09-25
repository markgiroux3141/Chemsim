"""T2 -- write ``data/templates/literal.psv`` from the catalog steps themselves.

    python tools/extract_templates.py            # write the table and the refusals
    python tools/extract_templates.py --check    # regenerate and compare
    python tools/extract_templates.py --dry-run  # report only, write nothing
    python tools/extract_templates.py --step lead-chamber:2   # one row, verbose

T1 made a template a ROW. This is why that was worth doing: a row is something a
program can write, and the corpus already holds 377 reactions nobody has typed
up. ``validation/extraction_yield.py`` measured the pool -- 157 steps resolve to
SMILES, balance under the LP, and carry a class no template covers -- against a
hand-written rate of three to five templates a session.

## THE PIPELINE, AND THE GATE AT THE END IS THE POINT

  1. drop the step's catalysts. A species on both sides is a spectator by
     ``route_steps.psv``'s own header rule, and leaving it in makes the balance
     LEAK: naphthalene + O2 over V2O5 balances its oxygen through the vanadium
     and comes back as ``[16, 57, 16, 18, 16, 28, 16]``.
  2. balance it. The corpus carries no coefficients, so this is an inference.
     ``corpus_balance.coefficients`` answers "can it balance at all" and its LP
     minimises the sum, which is NOT the row's stoichiometry when the nullspace
     is more than one dimensional -- the same naphthalene row comes back
     fractional. So the nullspace is computed directly and a second dimension is
     a REFUSAL, not a choice: two independent balances means the row does not
     determine its own stoichiometry, and picking one would be inventing
     chemistry inside an audit corpus.
  3. map the atoms. Iterated maximum common substructure over the two combined
     graphs, largest fragment first, ties broken on H count, charge and degree.
     No ``rxnmapper``: the mapping does not have to be right, because
  4. extract the reaction centre -- every atom whose bonds, charge or H count
     moved -- plus one bond of context, and write it as reaction SMARTS.
  5. **run it and compare the products with the step's own.** A mapping that is
     wrong makes a SMARTS that does not reproduce the step, and the row is
     refused. That is what buys an approximate mapper: the precision is the
     gate's, not the mapper's.
  6. kinetics from a policy, not from a class name. See ``A_POLICY`` below.

## The two walls, and how v2 (2026-09-24) reads through them

``tools/check_template_products.py`` named two systematic walls on this corpus.
T2 refused both; v2 reads through each where the engine's own representation
settles the question, and refuses where it does not.

``salt``   the catalog spells a salt as ONE species where the engine holds its
           ions. An aqueous step is read as its NET IONIC equation: every lump
           is split into its ions at its coefficient and a fragment on both
           sides cancels as a spectator (``net_ionic``). That is what the
           engine's aqueous phase holds, so it decides nothing the engine has
           not. A step in a furnace or melt (``phase_of`` says gas) is still
           refused: there the salt is a lattice, and turning a lattice into
           ions is engine work (E1), not an extractor's choice. A step whose
           every ion cancels is a metathesis or precipitation -- a solubility
           product's job -- and is refused as ``net-ionic-empty``.
``stereo`` the step declares a stereoisomer and a rewrite emits the flat
           species. Every family template already does exactly that, so v2
           extracts the flat reaction and says so in the row's note; the
           checker still reports the declared isomer missing under ``stereo``.

The rest of the refusals are the ordinary ones -- no coefficient vector (most
often a corpus step that omits a counter-ion or water), an ambiguous one, too
many slots for the network builder to enumerate, a mapping that did not close,
a SMARTS the constructor rejected, and a SMARTS that ran and did not make what
the step declared.

## WHAT THE GATE CANNOT SEE, AND IT IS NOT SMALL

The verification compares CANONICAL SMILES, because that is the engine's own
identity for a species. So it cannot tell a right mapping from a wrong one that
happens to make the same molecule, and on a symmetric product it will not:
butadiene plus ethylene comes back as cyclohexene whichever way round the four
diene carbons are mapped, and the Lebedev row joins the two ethanols at a
different pair of carbons from the one the mechanism does and still writes
butadiene. Both rows are in the table.

On the step they were extracted from, those rows are right, which is all a
``tier="literal"`` row claims. On a SUBSTITUTED substrate they would put the
substituent somewhere else, and that is the difference between a literal row and
a family one -- a family row is a claim about a mechanism, and promoting one of
these to `family` means checking the mapping by hand first. The refusals below
are counted; this one cannot be, because the gate that would count it is the
gate that cannot see it.

## THE GATE IS THE HAND-TYPED HALF, AND READING THE WHOLE MAP IS A LOOP

A step is a candidate when its class has no `family` row. Reading
``TEMPLATE_CLASSES`` instead -- which counts every tier -- makes this script
read its own last output as coverage, so the second run refuses all 54 rows the
first one wrote and ``--check`` compares an empty table with a full one. That is
not a subtle failure once it happens, and it is invisible until the second run:
the first run of a fresh checkout is correct either way.

## WHY THE ROWS LAND IN A FILE OF THEIR OWN

``data/templates/templates.psv`` is hand-typed and ``data/templates/literal.psv``
is generated, and rule 5 says a generated file is regenerated rather than
edited. ``build_templates.read_table`` reads both, so a literal row is a
template in every way that matters -- except that ``load_templates`` defaults to
``tier="family"`` and will not put one in a flask that did not ask for one.
"""

from __future__ import annotations

import argparse
import os
import sys
from fractions import Fraction
from math import gcd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "validation"))

import numpy as np  # noqa: E402
from rdkit import Chem, RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

from rdkit.Chem import rdFMCS  # noqa: E402

import build_templates as bt  # noqa: E402
import catalog as cat  # noqa: E402
from check_template_products import STEREO_MARKS, engine_reading, flat  # noqa: E402
import corpus_balance as cb  # noqa: E402
from catalog_coverage import FAMILY_TEMPLATE_CLASSES  # noqa: E402
from chemsim.matter.molecule import Molecule  # noqa: E402
from chemsim.reactions.template import ReactionTemplate  # noqa: E402

OUT = os.path.join(_ROOT, "data", "templates", "literal.psv")
REVIEW = os.path.join(_ROOT, "data", "templates", "needs_review.psv")

# ---------------------------------------------------------------------------
# bounds -- every one of these is a cost, not a taste
# ---------------------------------------------------------------------------

# A reactant slot is a loop in ``network/builder.py``: a four-slot template over
# a 300-species pool is 300**4 candidate assignments before any pattern filters
# them, and the repeated-slot bomb that took a 23 s tool to 35 minutes was three.
MAX_REACTANT_SLOTS = 3
MAX_PRODUCT_SLOTS = 4

# A coefficient above this makes a rewrite nobody can read and a slot count
# nothing can enumerate -- 9 O2 in one SMARTS is not a template.
MAX_COEFFICIENT = 2

# Bounds on the mapper, which is quadratic in the candidate matches.
MCS_TIMEOUT = 5
MAX_MATCHES = 64
MAX_PAIRS = 512

# ---------------------------------------------------------------------------
# the kinetics policy -- one rule, applied a hundred times, stated once
# ---------------------------------------------------------------------------
#
# Rule 8: every ``A`` is an order-of-magnitude choice for the molecularity and
# every ``Ea`` a band midpoint. A per-class table of a hundred hand-picked
# barriers would be the queue-grinding this tool exists to replace, so the
# policy is derived from two things the corpus already carries -- the
# molecularity of the rewrite, and the temperature the step declares.
#
#   A   the collision-theory order of magnitude for that molecularity and phase.
#   Ea  chosen so the reaction has a minutes timescale AT THE STEP'S OWN
#       TEMPERATURE: Ea = R T ln(A / k_target). A step that says 1100 K gets a
#       barrier that needs 1100 K, and one that names no temperature gets 298 K.
#
# What this policy is NOT is a measurement. It puts the barrier in the right
# band for the conditions the step declares and no closer, which is the whole
# reason ``tier="literal"`` exists and why ``load_templates`` will not load one
# by default: a hundred rows carrying policy kinetics racing in one flask would
# make every selectivity in it noise (S11).

R_GAS = 8.314462618

A_POLICY = {
    ("liquid", 1): 1e13, ("liquid", 2): 1e8, ("liquid", 3): 1e6,
    ("gas", 1): 1e13, ("gas", 2): 1e10, ("gas", 3): 1e7,
}

# the rate constant the barrier is solved for: a minutes timescale.
K_TARGET = 1e-3

# when the step names no temperature
DEFAULT_T = 298.15

# conditions that put the rewrite in the vapour whatever the temperature says
GAS_WORDS = ("burner", "furnace", "kiln", "retort", "roaster", "reformer",
             "flame", "vapour", "vapor", "combustion", "converter")


def temperature(conditions: str) -> float | None:
    """The highest temperature the step's conditions name, in K, or None.

    The conditions column is free text -- ``"burner, 600-1200 K"``,
    ``"700-900 K, V2O5"``, ``"450 K"``. A range is read at its TOP, because the
    barrier is being solved for the condition under which the step is claimed to
    go, and a range's bottom is where it does not yet.
    """
    best = None
    tokens = conditions.replace(",", " ").replace("-", " ").split()
    for i, tok in enumerate(tokens):
        if i == 0 or tok.upper().strip(".") != "K":
            continue
        try:
            value = float(tokens[i - 1])
        except ValueError:
            continue
        if 100.0 <= value <= 4000.0:
            best = value if best is None else max(best, value)
    return best


def phase_of(step) -> str:
    """``gas`` or ``liquid`` for the rewrite. Never ``any``.

    ``any`` doubles the reaction into both phases with different standard
    states, which is a claim a policy table has no business making.
    """
    low = step.conditions.lower()
    if any(w in low for w in GAS_WORDS):
        return "gas"
    T = temperature(step.conditions)
    return "gas" if T is not None and T >= 600.0 else "liquid"


def kinetics(step, n_slots: int, phase: str) -> tuple[float, float, str]:
    """(A, Ea, the source cell that says where both came from)."""
    molecularity = min(max(n_slots, 1), 3)
    A = A_POLICY[(phase, molecularity)]
    T = temperature(step.conditions)
    used = T if T is not None else DEFAULT_T
    Ea = round(R_GAS * used * float(np.log(A / K_TARGET)) / 5000.0) * 5000.0
    where = (f"{used:.0f} K from the step's conditions" if T is not None
             else f"{used:.0f} K, the step naming none")
    return A, float(Ea), (
        f"extracted: A the {phase} order-of-magnitude choice at molecularity "
        f"{molecularity}; Ea = R T ln(A/k) for a minutes timescale at {where}"
    )


# ---------------------------------------------------------------------------
# stoichiometry
# ---------------------------------------------------------------------------


def smallest_integers(vec) -> list[int] | None:
    """A float coefficient vector -> the smallest positive integer one, or None."""
    fracs = [Fraction(float(v)).limit_denominator(96) for v in vec]
    lcm = 1
    for f in fracs:
        lcm = lcm * f.denominator // gcd(lcm, f.denominator)
    ints = [int(f * lcm) for f in fracs]
    if any(v <= 0 for v in ints):
        return None
    g = 0
    for v in ints:
        g = gcd(g, v)
    return [v // g for v in ints] if g else None


def _nullspace(A):
    """The one-dimensional nullspace of A as a vector, or None."""
    _u, s, vh = np.linalg.svd(A)
    tol = max(A.shape) * (s[0] if s.size else 1.0) * np.finfo(float).eps
    null = vh[int(np.sum(s > tol)):]
    return null[0] if null.shape[0] == 1 else None


def stoichiometry(counts, n_react) -> tuple[list[int] | None, str]:
    """The row's coefficients, or None with the reason it has none.

    The LP in ``corpus_balance`` answers "can this balance at all" and hands
    back the minimum-SUM point of the feasible cone. That is the row's own
    stoichiometry exactly when the cone is a RAY -- one dimension of nullspace.
    With two, the minimum-sum point is a MIXTURE of two independent balances and
    comes back fractional and meaningless: naphthalene over V2O5 is partial
    oxidation and complete combustion at once, and the LP returns
    ``[1, 3.5625, 1.125, 1, 1.75]``, which is both of them at a ratio nothing
    chose.
    """
    elements = sorted({k for c in counts for k in c if c[k] and k != "<charge>"})
    A = cb._matrix(counts, n_react, elements + ["<charge>"])
    nullity = A.shape[1] - int(np.linalg.matrix_rank(A))
    if nullity == 0:
        return None, "no coefficient vector: the elements do not balance"
    if nullity > 1:
        return None, (
            f"the balance is not unique -- {nullity} independent coefficient "
            f"vectors, so the row does not determine its own stoichiometry"
        )
    ns = _nullspace(A)
    if ns is None:
        return None, "the nullspace could not be computed"
    if float(np.sum(ns)) < 0.0:
        ns = -ns
    if float(np.min(ns)) <= 1e-9:
        return None, "the only balance sets a species to zero or negative"
    ints = smallest_integers(ns / float(np.min(ns)))
    if ints is None:
        return None, "the coefficients do not rationalise to positive integers"
    if float(np.max(np.abs(A @ np.array(ints, dtype=float)))) > 1e-9:
        return None, "the rationalised coefficients do not balance"
    return ints, ""


# ---------------------------------------------------------------------------
# atom mapping
# ---------------------------------------------------------------------------


def combine(mols):
    out = Chem.Mol(mols[0])
    for m in mols[1:]:
        out = Chem.CombineMols(out, m)
    return out


def _submol(mol, keep):
    """The sub-molecule induced by ``keep`` -> (mol, index in the parent)."""
    order = sorted(keep)
    em = Chem.RWMol()
    at: dict[int, int] = {}
    for i in order:
        src = mol.GetAtomWithIdx(i)
        copy = Chem.Atom(src)
        # The sub-molecule is never sanitized -- it is a fragment and often has
        # an open valence -- so the hydrogen count has to be carried over as an
        # EXPLICIT one or ``GetTotalNumHs`` raises on it.
        copy.SetNumExplicitHs(src.GetTotalNumHs())
        copy.SetNoImplicit(True)
        at[i] = em.AddAtom(copy)
    for b in mol.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if i in at and j in at:
            em.AddBond(at[i], at[j], b.GetBondType())
    out = em.GetMol()
    Chem.rdmolops.FastFindRings(out)
    return out, order


def _score(rsub, psub, rm, pm) -> int:
    """How well one candidate match pair agrees on what MCS ignores."""
    total = 0
    for i, j in zip(rm, pm):
        a, b = rsub.GetAtomWithIdx(i), psub.GetAtomWithIdx(j)
        total += int(a.GetTotalNumHs() == b.GetTotalNumHs())
        total += int(a.GetFormalCharge() == b.GetFormalCharge())
        total += int(a.GetDegree() == b.GetDegree())
    return total


def map_atoms(R, P) -> dict[int, int] | None:
    """Heavy-atom mapping reactants -> products, or None if it does not close.

    Iterated MCS: take the largest common connected substructure of what is
    still unmapped, map it, repeat. Totality is a free correctness check -- a
    balanced row has the same multiset of atoms on both sides, so a mapping that
    leaves anything over is a mapping that is wrong.
    """
    if R.GetNumAtoms() != P.GetNumAtoms():
        return None
    mapping: dict[int, int] = {}
    r_left = set(range(R.GetNumAtoms()))
    p_left = set(range(P.GetNumAtoms()))
    while r_left and p_left:
        rsub, r_idx = _submol(R, r_left)
        psub, p_idx = _submol(P, p_left)
        res = rdFMCS.FindMCS(
            [rsub, psub],
            atomCompare=rdFMCS.AtomCompare.CompareElements,
            bondCompare=rdFMCS.BondCompare.CompareOrder,
            ringMatchesRingOnly=False,
            completeRingsOnly=False,
            timeout=MCS_TIMEOUT,
        )
        if res.numAtoms == 0:
            break
        q = Chem.MolFromSmarts(res.smartsString)
        if q is None:
            break
        Chem.rdmolops.FastFindRings(q)
        rms = rsub.GetSubstructMatches(q, uniquify=False, maxMatches=MAX_MATCHES)
        pms = psub.GetSubstructMatches(q, uniquify=False, maxMatches=MAX_MATCHES)
        if not rms or not pms:
            break
        best = None
        pairs = 0
        for rm in rms:
            for pm in pms:
                pairs += 1
                s = _score(rsub, psub, rm, pm)
                if best is None or s > best[0]:
                    best = (s, rm, pm)
                if pairs >= MAX_PAIRS:
                    break
            if pairs >= MAX_PAIRS:
                break
        _s, rm, pm = best
        for i, j in zip(rm, pm):
            mapping[r_idx[i]] = p_idx[j]
        r_left -= {r_idx[i] for i in rm}
        p_left -= {p_idx[j] for j in pm}
    # Whatever MCS left over is a lone atom or two; match on element alone,
    # which is all there is to go on once it has stopped finding bonds.
    for i in sorted(r_left):
        z = R.GetAtomWithIdx(i).GetAtomicNum()
        hit = next((j for j in sorted(p_left)
                    if P.GetAtomWithIdx(j).GetAtomicNum() == z), None)
        if hit is None:
            return None
        mapping[i] = hit
        p_left.discard(hit)
    return mapping if not p_left else None


# ---------------------------------------------------------------------------
# the reaction centre, and one bond of context around it
# ---------------------------------------------------------------------------


def reaction_centre(R, P, mapping) -> set[int]:
    """Reactant atoms whose bonds, charge or hydrogen count moved."""
    changed: set[int] = set()
    for i, j in mapping.items():
        a, b = R.GetAtomWithIdx(i), P.GetAtomWithIdx(j)
        if (a.GetFormalCharge() != b.GetFormalCharge()
                or a.GetTotalNumHs() != b.GetTotalNumHs()):
            changed.add(i)
            continue
        before = {(mapping[n.GetIdx()],
                   R.GetBondBetweenAtoms(i, n.GetIdx()).GetBondTypeAsDouble())
                  for n in a.GetNeighbors()}
        after = {(n.GetIdx(),
                  P.GetBondBetweenAtoms(j, n.GetIdx()).GetBondTypeAsDouble())
                 for n in b.GetNeighbors()}
        if before != after:
            changed.add(i)
    return changed


def _charge(n: int) -> str:
    return f"+{n}" if n >= 0 else f"-{abs(n)}"


def _symbol(atom, map_no: int, tight: bool) -> str:
    """The bracket text for one atom of a template.

    A centre atom is written TIGHT -- element, hydrogen count and charge -- so
    the rewrite says what it does to them. A context atom is written LOOSE --
    element only -- so the hydrogen count and charge it did not touch are
    inherited from whatever the slot matched, which is what makes one bond of
    context a context and not a second substrate.
    """
    sym = atom.GetSymbol()
    if atom.GetIsAromatic():
        sym = sym.lower()
    if not tight:
        return f"[{sym}:{map_no}]"
    return f"[{sym}H{atom.GetTotalNumHs()}{_charge(atom.GetFormalCharge())}:{map_no}]"


def _side(mol, keep, bounds, symbols, literal=()) -> str | None:
    """One side of the rewrite as SMARTS, or None if a fragment came apart.

    ``bounds`` are the half-open atom ranges of the original species, so the
    dot-separated pieces of the SMARTS are the SLOTS -- and a fragment whose
    kept atoms are not connected to each other would silently become two slots
    that any two molecules could fill. That is refused rather than written.
    """
    pieces = []
    for lo, hi in bounds:
        atoms = sorted(a for a in keep if lo <= a < hi)
        if not atoms:
            return None
        bonds = [b.GetIdx() for b in mol.GetBonds()
                 if b.GetBeginAtomIdx() in atoms and b.GetEndAtomIdx() in atoms]
        if len(bonds) < len(atoms) - 1:
            return None
        smarts = Chem.MolFragmentToSmiles(
            mol, atomsToUse=atoms, bondsToUse=bonds, atomSymbols=symbols,
            isomericSmiles=False, canonical=True, allBondsExplicit=False,
        )
        if "." in smarts:
            return None
        pieces.append(smarts)
    pieces.extend(literal)
    return ".".join(pieces) if pieces else None


# Hydrogen is the one species with no heavy atom, so it cannot be mapped by a
# graph algorithm and it cannot be written as an implicit count either. It is
# carried through the rewrite as a LITERAL, unmapped fragment on whichever side
# it appears -- the same shape ``methane_ammoxidation`` writes by hand -- and the
# hydrogen it gives or takes shows up as the H count of a mapped atom moving,
# which is what puts that atom in the reaction centre.
LITERAL_FRAGMENTS = {"[H][H]": "[H][H]"}


def extract_smarts(R, P, mapping, r_bounds, p_bounds,
                   r_literal=(), p_literal=()) -> tuple[str, str] | None:
    """(reaction SMARTS, what the centre did) for one mapped step, or None."""
    centre = reaction_centre(R, P, mapping)
    if not centre:
        return None
    core = set(centre)
    for i in centre:
        core |= {n.GetIdx() for n in R.GetAtomWithIdx(i).GetNeighbors()}
    numbers = {i: n for n, i in enumerate(sorted(core), start=1)}
    r_symbols = [""] * R.GetNumAtoms()
    for i in core:
        r_symbols[i] = _symbol(R.GetAtomWithIdx(i), numbers[i], i in centre)
    p_core = {mapping[i] for i in core}
    p_symbols = [""] * P.GetNumAtoms()
    for i in core:
        # NOTE: a context atom is loose on this side too, and writing it tight
        # makes hydrogen out of nothing. The H count and charge of a context atom are
        # read off the ONE molecule the row was extracted from, so a product
        # atom spelled ``[CH1:2]`` forces one hydrogen onto whatever the slot
        # matched -- ``carbanion-generation`` was extracted from acetaldehyde
        # and, written tight, handed acetone's carbonyl carbon an H it never
        # had. Loose, the atom keeps what the reactant brought, which for an
        # atom the rewrite did not touch is the whole point of context.
        p_symbols[mapping[i]] = _symbol(P.GetAtomWithIdx(mapping[i]),
                                        numbers[i], i in centre)
    left = _side(R, core, r_bounds, r_symbols, r_literal)
    right = _side(P, p_core, p_bounds, p_symbols, p_literal)
    if left is None or right is None:
        return None
    return f"{left}>>{right}", f"{len(centre)} atoms change, {len(core)} written"


# ---------------------------------------------------------------------------
# one step -> one row, or one refusal
# ---------------------------------------------------------------------------

# A row extracted from one step's forward direction is irreversible, and that is
# a default with a reason rather than a shrug. ``reversible=True`` would have
# detailed balance derive a reverse rate from a forward barrier this script
# CHOSE, so the reverse would carry no provenance at all; and T7 measured what a
# reversible template does to discovery -- it runs backwards, which is
# retrosynthesis, over a table nobody hand-checked. The family tier is where a
# reversible row belongs, because somebody argued for that one.
LITERAL_REVERSIBLE = "no"


def _name(step) -> str:
    return f"{step.cls}_{step.route}_{step.index}".replace("-", "_")


def _species(step, compounds):
    """(reactant ids, product ids, catalyst ids) with the catalysts dropped."""
    both = [x for x in step.reactants if x in step.products]
    return ([x for x in step.reactants if x not in both],
            [x for x in step.products if x not in both],
            both)


def assignments(template, pool):
    """Ordered reactant tuples the slot patterns admit. ``check_template_products``'s."""
    per_slot = [[m for m in pool
                 if m._mol.HasSubstructMatch(template.reactant_pattern(i))]
                for i in range(template.n_reactant_slots)]
    if any(not s for s in per_slot):
        return []
    out = []
    for combo in _product(per_slot):
        out.append(combo)
        if len(out) >= 256:
            break
    return out


def _product(slots):
    import itertools
    return itertools.product(*slots)


def verify(template, reactant_smiles, product_smiles) -> bool:
    """Does the extracted rewrite make what the step declares, from the step?"""
    pool = [Molecule.from_smiles(s) for s in dict.fromkeys(reactant_smiles)]
    declared = {Molecule.from_smiles(s).smiles for s in product_smiles}
    for combo in assignments(template, pool):
        for outcome in template.run(combo):
            if declared <= {m.smiles for m in outcome}:
                return True
    return False


def net_ionic(r_smiles, p_smiles, coeffs):
    """The step's salts as their ions, spectators cancelled.

    -> (reactant species, their coefficients, product species, theirs, the
    spectators dropped). Every dot-separated species is split into its
    fragments at its own coefficient, and a fragment on both sides cancels at
    the smaller count: the net ionic equation, which is what the engine's
    aqueous phase holds. Neutral lumps (an adduct written with a dot) split the
    same way, and for the same reason.
    """
    def side(smiles, cs):
        out: dict[str, int] = {}
        for s, c in zip(smiles, cs):
            for frag in s.split("."):
                key = Molecule.from_smiles(frag).smiles
                out[key] = out.get(key, 0) + c
        return out

    n = len(r_smiles)
    left, right = side(r_smiles, coeffs[:n]), side(p_smiles, coeffs[n:])
    spectators = []
    for key in sorted(set(left) & set(right)):
        k = min(left[key], right[key])
        left[key] -= k
        right[key] -= k
        spectators.append(key)
    left = {k: v for k, v in left.items() if v}
    right = {k: v for k, v in right.items() if v}
    return (list(left), list(left.values()), list(right), list(right.values()),
            spectators)


_PROVIDERS: dict[str, object] = {}


def builds(template, reactant_smiles) -> tuple[bool, tuple[str, ...]]:
    """(does build_network price a reaction from the pool, what it could not price).

    The rewrite reproducing the step is a SMARTS fact; this is the reaction
    fact. A row that fails it is still written -- whether its species have a
    price is the species-ready axis of every scoreboard, and refusing the row
    here would count that gap twice -- but the table's footer counts it, so a
    literal row that scores a class and cannot run is never mistaken for one
    that can. Ions are priced by the electrolyte overlay whenever the pool or
    the row touches one (``engine.inventory.needs_electrolyte``'s rule).
    """
    import contextlib
    import io

    from chemsim.network import build_network
    from chemsim.properties import ThermochemistryProvider
    from chemsim.properties.electrolyte import electrolyte_provider

    pool = engine_reading(reactant_smiles)
    ionic = template.touches_ions or any(Molecule.from_smiles(s).charge
                                         for s in pool)
    key = "ionic" if ionic else "plain"
    if key not in _PROVIDERS:
        _PROVIDERS[key] = (electrolyte_provider() if ionic
                           else ThermochemistryProvider())
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            net = build_network(pool, [template], thermo=_PROVIDERS[key],
                                generations=1, max_species=120)
    except ValueError as exc:
        # A CHARGED species with no price refuses before discovery starts.
        return False, (str(exc).split("'")[1] if "'" in str(exc) else "?",)
    return bool(net.reactions), tuple(sorted(net.unpriced))


def extract(step, compounds) -> tuple[dict | None, str, str]:
    """One step -> (row, reason, detail). Exactly one of row / reason is set."""
    r_ids, p_ids, cats = _species(step, compounds)
    if not r_ids or not p_ids:
        return None, "closed-cycle", "every product is also a reactant"
    ids = r_ids + p_ids
    if any(cat.is_marker(x, compounds) for x in ids):
        return None, "no-graph", "a species has no molecular graph"
    smiles = [compounds[x].smiles for x in ids]
    flattened = [s for s in smiles if any(c in s for c in STEREO_MARKS)]
    smiles = [flat(s) for s in smiles]
    try:
        counts = [cb.formula(s) for s in smiles]
    except Exception as exc:  # noqa: BLE001
        return None, "no-graph", type(exc).__name__
    coeffs, why = stoichiometry(counts, len(r_ids))
    if coeffs is None:
        return None, "stoichiometry", why
    r_smiles, p_smiles = smiles[:len(r_ids)], smiles[len(r_ids):]
    spectators: list[str] = []
    if any("." in s for s in smiles):
        if phase_of(step) == "gas":
            return None, "salt", (
                "a salt in a furnace or melt is a lattice, not a pair of ions, "
                "and the engine turns a lattice into ions nowhere yet (E1)")
        r_smiles, r_c, p_smiles, p_c, spectators = net_ionic(
            r_smiles, p_smiles, coeffs)
        if not r_smiles or not p_smiles:
            return None, "net-ionic-empty", (
                "every ion is a spectator once the salts are read as ions: a "
                "metathesis or precipitation, which a solubility product does, "
                "not a rewrite")
        coeffs = r_c + p_c
        ids = r_smiles + p_smiles
    if max(coeffs) > MAX_COEFFICIENT:
        return None, "coefficients", (
            f"a coefficient of {max(coeffs)} is more slots than a rewrite can "
            f"carry: {dict(zip(ids, coeffs))}")
    n_r = sum(coeffs[:len(r_smiles)])
    n_p = sum(coeffs[len(r_smiles):])
    if n_r > MAX_REACTANT_SLOTS or n_p > MAX_PRODUCT_SLOTS:
        return None, "slots", f"{n_r} reactant and {n_p} product slots"
    smiles = r_smiles + p_smiles
    mols = [Molecule.from_smiles(s) for s in smiles]
    r_frags, p_frags = [], []
    r_literal, p_literal = [], []
    for k, m in enumerate(mols):
        literal = LITERAL_FRAGMENTS.get(m.smiles)
        if m._mol.GetNumHeavyAtoms() == 0:
            if literal is None:
                return None, "no-heavy-atom", (
                    f"{m.smiles} has no heavy atom, so no graph algorithm can "
                    f"map it and no implicit count can carry it")
            (r_literal if k < len(r_smiles) else p_literal).extend(
                [literal] * coeffs[k])
            continue
        (r_frags if k < len(r_smiles) else p_frags).extend([m._mol] * coeffs[k])
    if not r_frags or not p_frags:
        return None, "no-heavy-atom", "one side is hydrogen and nothing else"
    R, P = combine(r_frags), combine(p_frags)
    r_bounds, p_bounds = _bounds(r_frags), _bounds(p_frags)
    mapping = map_atoms(R, P)
    if mapping is None:
        return None, "mapping", "the atom mapping did not close over the row"
    made = extract_smarts(R, P, mapping, r_bounds, p_bounds,
                          r_literal, p_literal)
    if made is None:
        return None, "centre", (
            "no reaction centre, or a slot whose written atoms are not "
            "connected to each other")
    smarts, shape = made
    phase = phase_of(step)
    A, Ea, source = kinetics(step, n_r, phase)
    try:
        template = ReactionTemplate(
            name=_name(step), smarts=smarts, A=A, Ea=Ea,
            reversible=LITERAL_REVERSIBLE == "yes", phase=phase)
    except Exception as exc:  # noqa: BLE001
        return None, "smarts", f"{type(exc).__name__}: {exc}"
    if not verify(template, r_smiles, p_smiles):
        return None, "unverified", (
            "the rewrite does not make what the step declares -- the mapping "
            "is wrong, or the step is not one mechanism")
    note = f"extracted from {step.route} step {step.index}; {shape}"
    if flattened:
        note += ("; stereo flattened -- the rewrite emits the flat species, as "
                 "every template does")
    if spectators:
        note += (f"; net ionic reading, {', '.join(spectators)} cancelled as "
                 f"spectators")
    if cats:
        note += f"; {', '.join(cats)} dropped as the step's own catalyst"
    return {
        "name": _name(step), "tier": "literal", "class": step.cls,
        "phase": phase, "reversible": LITERAL_REVERSIBLE,
        "A": f"{A:g}", "Ea_J": f"{Ea:g}", "alpha": "", "orders": "",
        "solid_catalyst": "", "electrons": "", "hammett_rho": "",
        "hammett_slot": "", "hammett_saturation": "", "smarts": smarts,
        "source": source, "notes": note,
    }, "", ""


def _bounds(frags):
    out, at = [], 0
    for m in frags:
        out.append((at, at + m.GetNumAtoms()))
        at += m.GetNumAtoms()
    return out


# ---------------------------------------------------------------------------
# the two files
# ---------------------------------------------------------------------------

TABLE_HEADER = """\
# LITERAL REACTION TEMPLATES -- GENERATED, do not edit.
#
#   python tools/extract_templates.py
#
# One row per catalog step that survived the whole pipeline in
# tools/extract_templates.py, which is where the columns, the kinetics policy
# and every refusal are explained. Same columns as data/templates/templates.psv,
# which is the HAND-TYPED half of the same table; build_templates.py reads both.
#
# tier is `literal` on every row here and that is load-bearing: load_templates()
# defaults to `family`, so none of these enters a flask that did not ask for it.
#
# The `#!` keys at the foot are derived: how many rows build_network turns into
# a PRICED reaction, and which unpriced species stop the rest.
"""

REVIEW_HEADER = """\
# CATALOG STEPS THE EXTRACTOR REFUSED -- GENERATED, do not edit.
#
#   python tools/extract_templates.py
#
# Columns: route | step | class | reason | detail
#
# Every step whose class has no template and which tools/extract_templates.py
# did not turn into a row, with the reason. That tool's docstring says how v2
# reads through the salt and stereo walls, and where it still refuses.
#
# The `#!` keys at the foot are derived from the rows above, never typed.
"""


def rows_and_refusals(only: str | None = None):
    """Every uncovered step -> (rows written, refusals)."""
    compounds = cat.load_compounds()
    rows, refused, seen = [], [], set()
    for step in cat.load_steps():
        where = f"{step.route}:{step.index}"
        if only is not None and where != only:
            continue
        if only is None and step.cls in FAMILY_TEMPLATE_CLASSES:
            continue
        row, reason, detail = extract(step, compounds)
        if row is None:
            refused.append((step, reason, detail))
            continue
        if row["smarts"] in seen:
            refused.append((step, "duplicate",
                            "another step of this corpus extracts the same rewrite"))
            continue
        seen.add(row["smarts"])
        template = ReactionTemplate(
            name=row["name"], smarts=row["smarts"], A=float(row["A"]),
            Ea=float(row["Ea_J"]), reversible=False, phase=row["phase"])
        r_ids, _p, _c = _species(step, compounds)
        runs, unpriced = builds(template, [compounds[x].smiles for x in r_ids])
        row["_runs"] = runs
        row["_unpriced"] = unpriced
        rows.append(row)
    return rows, refused


def render_table(rows) -> str:
    body = "\n".join(" | ".join(r[c] for c in bt.COLUMNS) for r in rows)
    blocked: dict[str, int] = {}
    for r in rows:
        for s in r["_unpriced"]:
            blocked[s] = blocked.get(s, 0) + 1
    foot = [f"#! rows = {len(rows)}",
            f"#! rows_that_build_a_priced_reaction = {sum(r['_runs'] for r in rows)}"]
    foot += [f"#! unpriced {s} = {n}"
             for s, n in sorted(blocked.items(), key=lambda kv: (-kv[1], kv[0]))]
    return TABLE_HEADER + "\n" + body + "\n\n" + "\n".join(foot) + "\n"


def render_review(refused) -> str:
    body = "\n".join(
        " | ".join((s.route, str(s.index), s.cls, reason, detail))
        for s, reason, detail in refused)
    counts: dict[str, int] = {}
    for _s, reason, _d in refused:
        counts[reason] = counts.get(reason, 0) + 1
    foot = [""] + [f"#! {k} = {counts[k]}" for k in sorted(counts)]
    foot.append(f"#! refused = {len(refused)}")
    foot.append(f"#! classes_refused = "
                f"{len({s.cls for s, _r, _d in refused})}")
    return REVIEW_HEADER + "\n" + body + "\n" + "\n".join(foot) + "\n"


def summarise(rows, refused) -> list[str]:
    counts: dict[str, int] = {}
    for _s, reason, _d in refused:
        counts[reason] = counts.get(reason, 0) + 1
    out = [
        f"{len(rows) + len(refused)} catalog steps carry a class with no template",
        f"{len(rows):4d} became a literal row, over "
        f"{len({r['class'] for r in rows})} reaction classes",
        f"     {sum(r['_runs'] for r in rows):4d} of them build a priced reaction; "
        f"the rest make or take a species with no thermochemistry",
        f"{len(refused):4d} refused:",
    ]
    for k in sorted(counts, key=lambda k: (-counts[k], k)):
        out.append(f"     {counts[k]:4d}  {k}")
    return out


def _write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            return fh.read().replace("\r\n", "\n")
    except FileNotFoundError:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="regenerate and compare; a stale file fails")
    ap.add_argument("--dry-run", action="store_true", help="report only")
    ap.add_argument("--step", help="one step, as route:index, however it ends")
    args = ap.parse_args()

    if args.step:
        compounds = cat.load_compounds()
        route, _, idx = args.step.partition(":")
        for step in cat.load_steps():
            if step.route == route and step.index == int(idx):
                row, reason, detail = extract(step, compounds)
                print(f"{step.route}:{step.index}  {step.cls}")
                print(f"  {' + '.join(step.reactants)} -> "
                      f"{' + '.join(step.products)}")
                if row is None:
                    print(f"  REFUSED [{reason}] {detail}")
                    return 1
                for k in ("name", "phase", "A", "Ea_J", "smarts", "source", "notes"):
                    print(f"  {k:9s} {row[k]}")
                return 0
        print(f"no such step: {args.step}")
        return 2

    rows, refused = rows_and_refusals()
    table, review = render_table(rows), render_review(refused)
    for line in summarise(rows, refused):
        print("  " + line)

    if args.dry_run:
        return 0
    if args.check:
        bad = [p for p, want in ((OUT, table), (REVIEW, review))
               if _read(p) != want]
        if bad:
            print("\n".join(f"{p}: stale -- rerun tools/extract_templates.py"
                            for p in bad))
            return 1
        print(f"  {OUT} and {REVIEW} are current")
        return 0
    _write(OUT, table)
    _write(REVIEW, review)
    print(f"  wrote {OUT}")
    print(f"  wrote {REVIEW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
