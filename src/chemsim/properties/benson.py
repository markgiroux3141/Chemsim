"""Layer 1 -- Benson group additivity.

A second thermochemistry estimator, sitting below curated data and above Joback.
It supplies formation properties only -- Hf, Gf, S and Cp -- because group
additivity says nothing about Tb/Tc/Pc, which stay Joback's. So it improves
ACCURACY rather than coverage: a species Joback cannot fragment is still refused
even where Benson could price it.

Measured head to head on the 82 curated ideal-gas species: **median dGf error
1.6 kJ/mol against Joback's 2.8**, refusing ~12% (unmapped groups,
heteroaromatics, anything under three heavy atoms), which keep Joback's estimate.
The gains are concentrated exactly where Joback is weakest -- acetanilide
4.7 kJ/mol out against Joback's 89.4, a branched octane 7.7 against 30.6.

## Why Benson at all

Joback has two structural limits that better data cannot fix:

* **It cannot distinguish homologues.** Its groups are additive fragments, so
  the CH3 -> C2H5 difference cancels *exactly* between an alcohol and the ester
  it makes. Methanol and ethanol esterification came out with an identical
  gas-phase dG_rxn of -7.35 kJ/mol.
* **It has no groups for whole functional classes** -- aryl aldehydes,
  formamides, sulfoxides, sulfones, anhydrides. Nine such species have curated
  records; every other member of those classes is unreachable.

Benson fixes both *by construction*, because a Benson group is a polyvalent atom
**together with the types of its ligands**. Methanol's carbon is ``C-(H)3(O)``
while ethanol's are ``C-(C)(H)3`` and ``C-(C)(H)2(O)`` -- different groups, so
the homologues cannot collapse onto each other. Measured here, the scheme
assigns 26/26 of a bench-realistic target set against Joback's 17/26, and there
is no species Joback can fragment that it cannot.

## Why this is not a SMARTS table

Joback and UNIFAC both go through ``properties.fragmentation``: a greedy,
priority-ordered SMARTS matcher with a formula check, because their groups are
overlapping substructure patterns and something has to arbitrate. Benson groups
are not patterns at all -- every polyvalent heavy atom contributes exactly one
group, decided by its own element and bonding and its neighbours' types.

So there is nothing to arbitrate and no ambiguity to resolve, and expressing it
as SMARTS would need one pattern per ligand combination (hundreds) and would
*reintroduce* a matching ambiguity the scheme does not have. It runs off
``Molecule.topology()`` instead -- added for this, and plain data, so Layer 0
stays sealed.

The one thing the two approaches share is the discipline: an atom this module
cannot type raises, rather than being quietly dropped into a catch-all.

## Where the values come from, and one that failed

``benson_data`` carries them, parsed from MIT's RMG-database. Read its docstring
before touching the numbers -- in particular, **RMG mixes kcal and kJ within one
file**, and assuming either throughout makes every oxygen group 4.184x wrong in a
way that validates fine on alkanes.

Regressing the values from measured data instead was tried first and **does not
work** -- recorded here so it is not retried. On 247 unique structures with
ideal-gas Hf and S0 from CRC and NIST WebBook, ridge-regularised and 5-fold
cross-validated, the groups turn out heavily collinear because the ones that
matter only ever co-occur: ``CO-(C)(O)`` and ``O-(C)(CO)`` appear in esters and
nowhere else, so five species must determine both and the fit splits them
arbitrarily. Cross-validated error was 35-38 kJ/mol against Joback's 33-42 -- no
better overall, and catastrophic exactly where it matters, with methyl acetate
187 kJ/mol out. Published parameters carry decades of fitting on thousands of
curated species; a few hundred noisy rows cannot reconstruct them.

## What is still missing

* **Gauche, ortho and other non-nearest-neighbour corrections.** RMG has them
  (``gauche.py``, ``other.py``, ``longDistanceInteraction_*.py``); they are not
  wired in. This is the main reason branched and ortho-substituted species carry
  more error than they need to.
* **Rings beyond the twelve named in ``benson_data.RING_CORRECTIONS``.** An
  unnamed ring refuses the estimate rather than omitting a correction worth up to
  115 kJ/mol, so heteroaromatics (pyridine, thiophene, furan-fused) are declined.
* **Some group keys are unmapped**, mostly nitriles, nitroaromatics and
  sulfoxide-adjacent carbons. They refuse and fall back to Joback.
* **Radicals**, which RMG handles via hydrogen bond increments (``radical.py``).
  Not needed until the network has radical chemistry.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from chemsim.constants import R
from chemsim.matter import AtomView, Molecule
from chemsim.properties.benson_data import (
    CORRECTIONS,
    GROUP_VALUES,
    RING_CORRECTIONS,
)

__all__ = [
    "BensonError", "BensonEstimate", "CORRECTIONS", "GROUP_VALUES",
    "RING_CORRECTIONS", "RING_SIGNATURES", "assign", "atom_type",
    "benson_views", "benzenoid_atoms", "can_assign", "can_estimate",
    "corrections", "estimate", "ring_key", "ring_signature", "symmetry_number",
]

T_REF = 298.15

# Absolute entropies of the elements in their REFERENCE states, J/(mol K),
# 298.15 K (CODATA). Needed to turn S298 into a formation Gibbs energy.
# Explicit rather than looked up: resolving "C" by symbol returns GASEOUS carbon
# at 158.1 instead of graphite's 5.74, which is 45 kJ/mol per carbon.
ELEMENT_S0 = {
    "C": 5.74, "H": 130.68, "O": 205.15, "N": 191.61, "S": 32.05,
    "F": 202.79, "Cl": 223.08, "Br": 152.21, "I": 116.14,
}
# Elements whose reference state is a diatomic molecule, so the tabulated value
# is per mole of X2 and one atom carries half. Iodine belongs here -- its
# reference state is a solid, but the solid is I2, and treating it as monatomic
# is 17 kJ/mol in every iodide.
DIATOMIC = frozenset({"H", "O", "N", "F", "Cl", "Br", "I"})

# Below this many heavy atoms the scheme is not applicable: a group is an atom
# plus its ligands, which says nothing about a two-atom molecule, and the
# symmetry model is wrong there too (methane reads 1 against a true 12). Benson
# excludes them himself; here they are curated instead.
MIN_HEAVY_ATOMS = 3

HALOGENS = frozenset({"F", "Cl", "Br", "I"})

# Elements this scheme can type. Anything else raises rather than being guessed
# at -- a silently mistyped atom is a wrong group is a wrong number.
SUPPORTED = frozenset({"C", "H", "N", "O", "S"}) | HALOGENS


class BensonError(ValueError):
    """Raised when a molecule cannot be assigned Benson groups."""


def _is_terminal_oxo(a: AtomView, atoms: list[AtomView]) -> bool:
    """A doubly-bonded (or anionic nitro/carboxylate) oxygen.

    Not a group of its own: Benson folds it into the central atom's identity, so
    a carbonyl is ONE group ``CO-(...)`` rather than a carbon group plus an
    oxygen group. Getting this wrong double-counts every C=O in the network.
    """
    if a.element != "O" or len(a.neighbours) != 1:
        return False
    nb = atoms[a.neighbours[0]]
    if a.order_to(nb.index) >= 2.0:
        return True
    return a.charge < 0 and nb.element in {"N", "C", "S"}


def _oxo_count(a: AtomView, atoms: list[AtomView]) -> int:
    return sum(1 for i in a.neighbours if _is_terminal_oxo(atoms[i], atoms))


def atom_type(a: AtomView, atoms: list[AtomView]) -> str:
    """Benson central-atom / ligand type for one heavy atom.

    The type is what makes the scheme sensitive to environment: a carbon bonded
    to a carbonyl (``C-(CO)(H)3``) is a different group from one bonded to a
    plain carbon (``C-(C)(H)3``), which is exactly the distinction Joback's
    additive fragments cannot make.

    ``aromatic`` here means *benzenoid* -- see ``benson_views``. Only carbon ever
    arrives aromatic, because a heteroaromatic ring is presented in its Kekule
    form; an aromatic heteroatom would mean the caller built the views wrongly, so
    it raises rather than inventing a ``Nb``/``Ob`` type there is no value for.
    """
    el = a.element
    if el in HALOGENS:
        return el
    if a.aromatic and el != "C":
        raise BensonError(
            f"aromatic {el} reached atom_type; heteroaromatics must be typed from "
            "the Kekule view (benson_views), where RMG's values live"
        )
    if el == "C":
        if a.aromatic:
            # A carbon shared between two aromatic rings is a different group:
            # it has three aromatic neighbours where an ordinary benzenoid carbon
            # has two plus a substituent, and Benson prices the two separately.
            ring_neighbours = sum(
                1 for i in a.neighbours
                if atoms[i].aromatic and atoms[i].element == "C"
            )
            return "Cbf" if ring_neighbours >= 3 else "Cb"
        if _oxo_count(a, atoms):
            return "CO"
        if 3.0 in a.bond_orders:
            partner = atoms[a.neighbours[a.bond_orders.index(3.0)]]
            return "CN" if partner.element == "N" else "Ct"
        if 2.0 in a.bond_orders:
            return "Cd"
        return "C"
    if el == "O":
        return "O"
    if el == "N":
        if _oxo_count(a, atoms) >= 2:
            return "NO2"
        if 3.0 in a.bond_orders:
            return "Nt"
        if 2.0 in a.bond_orders:
            return "Nd"
        return "N"
    if el == "S":
        return {0: "S", 1: "SO", 2: "SO2"}[_oxo_count(a, atoms)]
    raise BensonError(f"no Benson atom type for element {el!r}")


def benzenoid_atoms(mol: Molecule) -> frozenset[int]:
    """Atoms in an aromatic six-membered all-carbon ring.

    The dividing line between the two conventions RMG's values use, and it is not
    arbitrary. Benzene rings are priced with delocalised ``Cb`` groups and a ring
    correction of exactly ZERO, because the ``Cb`` value already carries the
    resonance. Every other aromatic ring is priced on its KEKULE structure --
    localised ``Cd``/``O``/``S`` groups plus a large ring correction (-26.4 kJ/mol
    for furan, -72.1 for thiophene) that is what makes the aromaticity show up.

    So the two are not interchangeable, and RMG has no aromatic-heteroatom group
    values to pair with a delocalised view at all: an aromatic-typed furan needed
    ``Ob-(Cb)2``, which does not exist, so furan and furfural refused despite
    having a ring correction sitting unused in the table.
    """
    atoms = mol.topology()
    out: set[int] = set()
    for ring in mol.ring_atom_indices():
        if len(ring) != 6:
            continue
        if all(atoms[i].aromatic and atoms[i].element == "C" for i in ring):
            out.update(ring)
    return frozenset(out)


def benson_views(mol: Molecule) -> list[AtomView]:
    """One atom view per heavy atom, benzenoid rings delocalised, the rest Kekule.

    Mixing the two views atom by atom is safe because ``kekulized_topology``
    preserves indices, and it is what the group table requires -- see
    ``benzenoid_atoms``. A ring fused across the two conventions (benzofuran)
    ends up with a bond pattern no exemplar matches, so ``ring_key`` cannot name
    it and the estimate refuses, which is the right answer: RMG has no fused
    heteroaromatic correction either.
    """
    atoms = mol.topology()
    if not any(a.aromatic for a in atoms):
        return atoms
    benzenoid = benzenoid_atoms(mol)
    if len(benzenoid) == sum(1 for a in atoms if a.aromatic):
        return atoms                     # purely benzenoid; nothing to localise
    kek = mol.kekulized_topology()
    return [atoms[i] if i in benzenoid else kek[i] for i in range(len(atoms))]


def assign(molecule: Molecule | str) -> dict[str, int]:
    """Benson groups and their counts, plus a ring correction per ring.

    Keys are written the conventional way -- ``C-(C)(H)3``, ``CO-(C)(O)``,
    ``Cb-(Cb)2(H)`` -- with ligands sorted so the key is canonical.

    Ring terms appear as ``ring5``/``ring6``/... because ring strain is not
    additive over atoms: cyclopropane's carbons are ordinary CH2 groups plus
    ~27 kcal/mol that no atom-local scheme can see. They are per ring, from the
    smallest set of smallest rings.
    """
    mol = molecule if isinstance(molecule, Molecule) else Molecule.from_smiles(molecule)
    atoms = benson_views(mol)

    unsupported = {a.element for a in atoms} - SUPPORTED
    if unsupported:
        raise BensonError(
            f"{mol.smiles!r}: no Benson groups for {sorted(unsupported)}"
        )

    types = {a.index: atom_type(a, atoms) for a in atoms}
    counts: Counter[str] = Counter()
    for a in atoms:
        # Ligand-only atoms contribute to their neighbour's group, not their own.
        if a.element in HALOGENS or _is_terminal_oxo(a, atoms):
            continue
        if types[a.index] == "Nt":            # nitrile N, folded into the CN carbon
            continue
        ligands: Counter[str] = Counter()
        for i in a.neighbours:
            if _is_terminal_oxo(atoms[i], atoms) or types[i] == "Nt":
                continue
            t = types[i]
            if types[a.index] == "Cb" and t == "Cbf":
                # Benson's convention, which the table follows: an ordinary
                # benzenoid carbon's two ring neighbours are named ``Cb``
                # whether or not either is a fusion carbon. RMG does not even
                # write them down -- ``Cb-H`` lists only the substituent -- so
                # distinguishing them here would ask for keys like
                # ``Cb-(Cb)(Cbf)(H)`` that no tabulation has, and every carbon
                # next to a naphthalene fusion would refuse.
                t = "Cb"
            ligands[t] += 1
        if a.n_hydrogens:
            ligands["H"] = a.n_hydrogens
        parts = "".join(
            f"({k})" if v == 1 else f"({k}){v}" for k, v in sorted(ligands.items())
        )
        counts[f"{types[a.index]}-{parts}"] += 1

    for size in mol.ring_sizes():
        counts[f"ring{size}"] += 1
    return dict(counts)


def can_assign(molecule: Molecule | str) -> bool:
    """Whether the scheme can type every atom. Used to report coverage."""
    try:
        assign(molecule)
    except (BensonError, ValueError):
        return False
    return True


# ---------------------------------------------------------------------------
# symmetry
# ---------------------------------------------------------------------------


def symmetry_number(molecule: Molecule | str) -> int:
    """sigma = sigma_external x product(sigma_internal).

    **Group additivity gives INTRINSIC entropy and this correction is not
    optional.** Benson's S298 values carry no symmetry term, so the caller owes
    ``-R ln(sigma)``. Skip it and alkanes still look fine while every symmetric
    molecule is wrong -- benzene by ``R ln 12`` = 20.7 J/(mol K), which is
    6 kJ/mol in dGf.

    External symmetry comes from the automorphism group of the HEAVY-ATOM graph.
    Hydrogens are excluded deliberately: counted, a methyl contributes all 3! = 6
    permutations of its hydrogens where only the 3 cyclic rotations are physical,
    which makes ethane 72 instead of 18. Internal symmetry is then added back per
    terminal rotor.

    Exact for the polyatomics this is used on and verified against known values
    (ethane 18, ethanol 3, benzene 12, toluene 6, acetone 18). It is WRONG for a
    single-heavy-atom species -- methane reads 1 against a true 12 -- which is
    harmless only because every such species is curated. ``estimate`` refuses
    them rather than relying on that.
    """
    mol = molecule if isinstance(molecule, Molecule) else Molecule.from_smiles(molecule)
    sigma_ext = mol.graph_automorphism_count()
    sigma_int = 1
    for a in mol.topology():
        if len(a.neighbours) != 1:
            continue                      # only a terminal group is a free rotor
        if a.element == "C" and a.n_hydrogens == 3:
            sigma_int *= 3                # a methyl, or any -CX3 top
        elif a.element in HALOGENS or a.n_hydrogens == 0:
            continue
    return sigma_ext * sigma_int


# ---------------------------------------------------------------------------
# ring identification
# ---------------------------------------------------------------------------


_BOND_CHAR = {1.0: "-", 1.5: ":", 2.0: "=", 3.0: "#"}


def _ring_cycle(atoms: list[AtomView], ring: tuple[int, ...]) -> list[int] | None:
    """Ring atom indices walked around the cycle, or None if it is not a cycle."""
    members = set(ring)
    adj = {i: [j for j in atoms[i].neighbours if j in members] for i in ring}
    if any(len(v) != 2 for v in adj.values()):
        return None
    order = [min(ring)]
    prev = None
    while len(order) < len(ring):
        a, b = adj[order[-1]]
        nxt = a if a != prev else b
        prev = order[-1]
        order.append(nxt)
    return order


def ring_signature(atoms: list[AtomView], ring: tuple[int, ...]) -> str | None:
    """A canonical name for one ring's own structure, independent of the molecule.

    Built by walking the cycle and recording, per atom, its element, whether it
    carries an exocyclic double-bonded oxygen, and the bond order onward -- then
    taking the smallest of all rotations and both directions, so the same ring
    always produces the same string however the atoms happen to be numbered.

    Naming a ring by its cyclic SEQUENCE rather than by (size, element tally,
    double-bond count) is what makes the table extensible. The tally cannot tell
    1,3-dioxane from 1,4-dioxane, or 1,3-cyclohexadiene from 1,4-, and those have
    ring corrections 6.4 and 13.6 kJ/mol apart respectively -- so a tally-based
    scheme has to either refuse both or silently pick one.
    """
    cycle = _ring_cycle(atoms, ring)
    if cycle is None:
        return None
    n = len(cycle)
    in_ring = set(cycle)
    toks = []
    for k, i in enumerate(cycle):
        a = atoms[i]
        label = a.element
        if any(
            j not in in_ring and o == 2.0 and atoms[j].element == "O"
            for j, o in zip(a.neighbours, a.bond_orders)
        ):
            label += "*"                      # exocyclic C=O, e.g. cyclohexanone
        order = a.order_to(cycle[(k + 1) % n])
        char = _BOND_CHAR.get(order)
        if char is None:
            return None
        toks.append((label, char))

    def render(seq):
        return "".join(f"{lab}{ch}" for lab, ch in seq)

    forward = toks
    # Reversing the walk pairs each atom with the bond on its other side.
    backward = [(toks[k][0], toks[(k - 1) % n][1]) for k in reversed(range(n))]
    return min(
        render(seq[r:] + seq[:r])
        for seq in (forward, backward)
        for r in range(n)
    )


# Ring identity -> the name ``benson_data.RING_CORRECTIONS`` is keyed by, derived
# from one exemplar SMILES each rather than from hand-written signature strings.
# The exemplar IS the specification: it is readable chemistry, it cannot drift out
# of step with the signature algorithm, and a typo produces a name that never
# matches instead of one that matches the wrong ring.
_RING_EXEMPLARS = {
    # 3-membered
    "cyclopropane": "C1CC1",
    "cyclopropene": "C1=CC1",
    "cyclopropanone": "O=C1CC1",
    "oxirane": "C1CO1",
    "aziridine": "C1CN1",
    "thiirane": "C1CS1",
    "dioxirane": "C1OO1",
    # 4-membered
    "cyclobutane": "C1CCC1",
    "cyclobutene": "C1=CCC1",
    "cyclobutanone": "O=C1CCC1",
    "oxetane": "C1COC1",
    "azetidine": "C1CNC1",
    "thietane": "C1CSC1",
    # 5-membered
    "cyclopentane": "C1CCCC1",
    "cyclopentene": "C1=CCCC1",
    "cyclopentadiene": "C1=CC=CC1",
    "cyclopentanone": "O=C1CCCC1",
    "tetrahydrofuran": "C1CCOC1",
    "23dihydrofuran": "C1=COCC1",
    "25dihydrofuran": "C1=CCOC1",
    "furan": "c1ccoc1",
    "13dioxolane": "C1OCOC1",
    "12dioxolane": "C1CCOO1",
    "pyrrolidine": "C1CCNC1",
    "thiolane": "C1CCSC1",
    "thiophene": "c1ccsc1",
    "13dithiolane": "C1SCSC1",
    "12dithiolane": "C1CCSS1",
    "succinic_anhydride": "O=C1CCC(=O)O1",
    "maleic_anhydride": "O=C1C=CC(=O)O1",
    # 6-membered
    "benzene": "c1ccccc1",
    "cyclohexane": "C1CCCCC1",
    "cyclohexene": "C1=CCCCC1",
    "13cyclohexadiene": "C1=CC=CCC1",
    "14cyclohexadiene": "C1=CCC=CC1",
    "cyclohexanone": "O=C1CCCCC1",
    "piperidine": "C1CCNCC1",
    "tetrahydropyran": "C1CCOCC1",
    "14dioxane": "C1COCCO1",
    "13dioxane": "C1COCOC1",
    "12dioxane": "C1CCCOO1",
    # 7- and 8-membered
    "cycloheptane": "C1CCCCCC1",
    "cycloheptene": "C1=CCCCCC1",
    "cyclooctane": "C1CCCCCCC1",
}


def _build_signatures() -> dict[str, str]:
    out: dict[str, str] = {}
    for name, smiles in _RING_EXEMPLARS.items():
        mol = Molecule.from_smiles(smiles)
        atoms = benson_views(mol)
        rings = mol.ring_atom_indices()
        if len(rings) != 1:
            raise BensonError(f"ring exemplar {smiles!r} for {name!r} is not one ring")
        sig = ring_signature(atoms, rings[0])
        if sig is None:
            raise BensonError(f"ring exemplar {smiles!r} for {name!r} has no signature")
        if sig in out:
            raise BensonError(
                f"ring exemplars {out[sig]!r} and {name!r} have the same signature "
                f"{sig!r} -- one of them is misdrawn, or the signature is too coarse"
            )
        out[sig] = name
    return out


RING_SIGNATURES = _build_signatures()


def ring_key(molecule: Molecule, ring: tuple[int, ...]) -> str | None:
    """Name one ring so a strain correction can be looked up, or None.

    Ring strain is not additive over atoms and a missing correction is a silent
    error of up to 115 kJ/mol (cyclopropane), so a ring this cannot name makes
    the whole estimate refuse rather than proceed without it.
    """
    atoms = benson_views(molecule)
    sig = ring_signature(atoms, ring)
    return None if sig is None else RING_SIGNATURES.get(sig)


# ---------------------------------------------------------------------------
# non-nearest-neighbour corrections
# ---------------------------------------------------------------------------
# The terms a first-order group scheme structurally cannot see: two groups that
# are not neighbours and still interact. Two families are read from RMG (see
# ``tools/build_benson_data.py`` for the label grammar and the halving trap):
#
#   * 1,3 and 1,4 BRANCHING, Benson's gauche corrections -- two substituted sp3
#     centres crowding each other. Up to 13.4 kJ/mol for a tertiary next to a
#     quaternary carbon.
#   * AROMATIC ortho/meta/para interaction between two ring substituents. Up to
#     -27.4 kJ/mol for an ortho hydroxyl and aldehyde, which is the intramolecular
#     hydrogen bond in salicylaldehyde -- by far the largest correction here, and
#     one no amount of group refinement could ever produce.
#
# **A missing correction is zero, not a refusal.** That is the opposite of the
# rule for groups and rings, and deliberately so: a correction is a refinement on
# top of a complete estimate, RMG's own tree carries explicit zero-valued parents
# for the combinations it has not measured, and refusing on absence would refuse
# essentially every molecule. A missing GROUP or RING correction is different --
# there the estimate is incomplete rather than unrefined.

_RANK = {2: "S", 3: "T", 4: "Q"}

# Our atom type -> the token the correction keys use. Only the atom kinds RMG
# gives interaction values for; anything else yields no key and hence no term.
_NN_TOKEN = {"C": "Cs", "O": "Os", "S": "Ss", "Cd": "Cd", "CO": "CO"}


def _single_heavy(a: AtomView) -> int:
    """Heavy neighbours joined by a SINGLE bond.

    The substitution rank RMG's labels count. Excluding a double-bond partner is
    what makes the rank consistent across atom kinds -- a vinyl carbon with two
    single-bonded neighbours ranks as secondary, which is how ``CdCs-ST`` is
    written.
    """
    return sum(1 for o in a.bond_orders if o == 1.0)


def _nn_side(a: AtomView, atoms: list[AtomView]) -> str | None:
    """One end of a branching interaction, as ``<token><rank>``, or None."""
    token = _NN_TOKEN.get(atom_type(a, atoms))
    rank = _RANK.get(_single_heavy(a))
    return None if token is None or rank is None else f"{token}{rank}"


def _substituent_class(a: AtomView, atoms: list[AtomView], ring: set[int]) -> str | None:
    """Classify a benzene-ring substituent into the six classes RMG measured."""
    if a.element == "O":
        others = [i for i in a.neighbours if i not in ring]
        if not others:
            return "OH" if a.n_hydrogens == 1 else None
        if len(others) == 1 and a.n_hydrogens == 0:
            m = atoms[others[0]]
            return "MeO" if m.element == "C" and m.n_hydrogens == 3 else None
        return None
    if a.element != "C":
        return None
    others = [i for i in a.neighbours if i not in ring]
    if _oxo_count(a, atoms) == 1 and a.n_hydrogens == 1:
        return "CHO"
    if 2.0 in a.bond_orders and a.n_hydrogens == 1:
        partner = atoms[a.neighbours[a.bond_orders.index(2.0)]]
        if partner.element == "C" and partner.n_hydrogens == 2:
            return "vinyl"
        return None
    if a.n_hydrogens == 3 and not others:
        return "CH3"
    if a.n_hydrogens == 2 and len(others) == 1:
        m = atoms[others[0]]
        if m.element == "C" and m.n_hydrogens == 3 and len(m.neighbours) == 1:
            return "C2H5"
    return None


def corrections(
    molecule: Molecule | str, table: dict | None = None
) -> dict[str, int]:
    """Non-nearest-neighbour correction terms and their multiplicities.

    Every unordered interacting pair is counted ONCE. RMG's own matcher tries both
    assignments of its two labelled atoms and so stores symmetric entries at half
    value; the build doubles those, which is why counting once here is correct and
    why doing both would be a factor of two on exactly the symmetric cases.

    ``table`` selects which corrections count, and defaults to the applied ones.
    Pass ``{**CORRECTIONS, **AROMATIC_INTERACTIONS}`` to include the withheld
    aromatic family -- which is how ``validation/benson_accuracy.py`` re-measures
    the decision to withhold it, rather than taking it on trust.
    """
    mol = molecule if isinstance(molecule, Molecule) else Molecule.from_smiles(molecule)
    atoms = benson_views(mol)
    known = CORRECTIONS if table is None else table
    out: Counter[str] = Counter()

    def add(key: str) -> None:
        if key in known:
            out[key] += 1

    # -- 1,3: two substituted centres one bond apart ------------------------
    sides = {}
    for a in atoms:
        try:
            sides[a.index] = _nn_side(a, atoms)
        except BensonError:
            sides[a.index] = None
    for a in atoms:
        if sides[a.index] is None:
            continue
        for j, order in zip(a.neighbours, a.bond_orders):
            if j <= a.index or order != 1.0 or sides[j] is None:
                continue
            add("nn13_" + "_".join(sorted((sides[a.index], sides[j]))))

    # -- 1,4: the same, across one bridging atom ----------------------------
    for b in atoms:
        token = (
            _NN_TOKEN.get(atom_type(b, atoms))
            if b.element in {"C", "O", "S"} else None
        )
        if token is None or _single_heavy(b) < 2:
            continue
        ends = [
            j for j, o in zip(b.neighbours, b.bond_orders)
            if o == 1.0 and sides.get(j) is not None
        ]
        for x in range(len(ends)):
            for y in range(x + 1, len(ends)):
                pair = sorted((sides[ends[x]], sides[ends[y]]))
                add(f"nn14_{token}_" + "_".join(pair))

    # -- aromatic ortho / meta / para ---------------------------------------
    # Recognised in full, but currently priced at zero: the values live in
    # ``benson_data.AROMATIC_INTERACTIONS`` and are withheld from ``CORRECTIONS``
    # because Ince & Reyniers fitted them against their own group values, and
    # against ours they make things worse (mean |Hf| error over eleven
    # disubstituted benzenes 7.94 -> 9.57 kJ/mol; salicylaldehyde 6.0 -> 33.4).
    # The recognition stays because it is what
    # ``validation/benson_accuracy.py`` re-measures the rejection with, and it is
    # the one line that has to change to adopt them later.
    for ring in mol.ring_atom_indices():
        if len(ring) != 6 or not all(atoms[i].aromatic for i in ring):
            continue
        cycle = _ring_cycle(atoms, ring)
        if cycle is None:
            continue
        members = set(cycle)
        classes: dict[int, str] = {}
        for k, i in enumerate(cycle):
            outside = [j for j in atoms[i].neighbours if j not in members]
            if len(outside) != 1:
                continue
            cls = _substituent_class(atoms[outside[0]], atoms, members)
            if cls is not None:
                classes[k] = cls
        positions = sorted(classes)
        for x in range(len(positions)):
            for y in range(x + 1, len(positions)):
                gap = abs(positions[x] - positions[y])
                gap = min(gap, 6 - gap)
                prefix = {1: "o", 2: "m", 3: "p"}.get(gap)
                if prefix is None:
                    continue
                pair = sorted((classes[positions[x]], classes[positions[y]]))
                add(f"{prefix}_" + "_".join(pair))

    return dict(out)


# ---------------------------------------------------------------------------
# the estimate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BensonEstimate:
    """Ideal-gas thermochemistry at 298.15 K, plus what produced it."""

    Hf: float                       # kJ/mol
    Gf: float                       # kJ/mol
    S: float                        # J/(mol K), symmetry-corrected
    Cp_coeffs: tuple[float, float, float, float]    # J/(mol K)
    groups: dict[str, int]
    sigma: int
    sources: tuple[str, ...]        # provenance of every group used
    # Non-nearest-neighbour terms applied, so a caller can see whether the
    # estimate leaned on one. Empty for most species -- see ``corrections``.
    nn_corrections: dict[str, int] = field(default_factory=dict)


def estimate(molecule: Molecule | str, nn: bool = True) -> BensonEstimate:
    """Benson group additivity for one species. Raises rather than guessing.

    ``nn=False`` omits the non-nearest-neighbour corrections, reproducing the
    first-order-only estimate. Kept for the same reason as
    ``ThermochemistryProvider(benson=False)`` and
    ``build_network(liquid_standard_state=False)``: so the difference a correction
    makes can be measured rather than only described. ``validation/
    benson_accuracy.py`` uses it, and it matters here because the 82-species
    reference set contains no species with an adjacent branched pair at all, so
    the branching terms have to be measured against a set chosen to exercise them.

    Three things happen here that additive schemes get wrong when rushed:

    * **The symmetry correction is applied.** ``-R ln(sigma)`` on the group sum.
      Group values are intrinsic entropies; without this benzene is out by
      ``R ln 12``, which is 6 kJ/mol in dGf.
    * **dGf is derived from the fitted pair**, against the CODATA element
      reference states, so the reaction entropy a caller gets from
      ``(Hf - Gf)/T`` is the same one that went in.
    * **An unpriced group or an unnamed ring refuses the whole estimate.** A
      missing ring correction is up to 115 kJ/mol of silent error, and a silent
      wrong answer is worse than a loud failure -- the lesson from Joback
      confidently reporting -74.8 kJ/mol for elemental chlorine.
    """
    mol = molecule if isinstance(molecule, Molecule) else Molecule.from_smiles(molecule)
    if mol.charge != 0:
        raise BensonError(f"{mol.smiles!r}: group additivity is for neutral species")
    if mol.n_heavy_atoms < MIN_HEAVY_ATOMS:
        raise BensonError(
            f"{mol.smiles!r}: only {mol.n_heavy_atoms} heavy atoms -- group "
            "additivity has nothing to say below three, and these are curated"
        )

    groups = assign(mol)
    H = S = 0.0
    cp = [0.0, 0.0, 0.0, 0.0]
    sources: list[str] = []

    for key, n in groups.items():
        if key.startswith("ring"):
            continue                      # handled per ring below, by identity
        rec = GROUP_VALUES.get(key)
        if rec is None:
            raise BensonError(
                f"{mol.smiles!r}: no group value for {key!r} "
                f"(assigned groups: {sorted(groups)})"
            )
        dH, dS, dcp, src = rec
        H += n * dH
        S += n * dS
        for i in range(4):
            cp[i] += n * dcp[i]
        sources.append(f"{key} x{n}: {src}")

    for ring in mol.ring_atom_indices():
        name = ring_key(mol, ring)
        if name is None or name not in RING_CORRECTIONS:
            raise BensonError(
                f"{mol.smiles!r}: no strain correction for a {len(ring)}-membered "
                "ring this scheme can name; refusing rather than omitting it"
            )
        dH, dS, dcp, src = RING_CORRECTIONS[name]
        H += dH
        S += dS
        for i in range(4):
            cp[i] += dcp[i]
        sources.append(f"ring {name}: {src}")

    nn_terms = corrections(mol) if nn else {}
    for key, n in sorted(nn_terms.items()):
        dH, dS, dcp, src = CORRECTIONS[key]
        H += n * dH
        S += n * dS
        for i in range(4):
            cp[i] += n * dcp[i]
        sources.append(f"correction {key} x{n}: {src}")

    sigma = symmetry_number(mol)
    S -= R * math.log(sigma)

    elements = mol.element_counts()
    missing = set(elements) - set(ELEMENT_S0)
    if missing:
        raise BensonError(
            f"{mol.smiles!r}: no element reference entropy for {sorted(missing)}"
        )
    s_elements = sum(
        ELEMENT_S0[e] * (c / 2.0 if e in DIATOMIC else c) for e, c in elements.items()
    )
    Gf = H - T_REF * (S - s_elements) / 1000.0

    return BensonEstimate(
        Hf=H, Gf=Gf, S=S, Cp_coeffs=tuple(cp), groups=groups, sigma=sigma,
        sources=tuple(sources), nn_corrections=nn_terms,
    )


def can_estimate(molecule: Molecule | str) -> bool:
    """Whether a full estimate is available -- groups, rings and all."""
    try:
        estimate(molecule)
    except (BensonError, ValueError):
        return False
    return True
