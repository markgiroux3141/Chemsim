"""Layer 0 -- molecular graphs.

``Molecule`` is our domain type for a chemical species' structure. RDKit does the
heavy lifting (parsing, canonicalization, substructure matching) but stays hidden
behind this wrapper: nothing above ``matter`` imports rdkit directly. That keeps
the cheminformatics backend swappable (a future Rust lib, say) and stops RDKit
types from leaking into the engine.

Identity: two Molecules are equal iff their canonical SMILES match. That makes a
Molecule hashable and usable as a dict key / set member -- which is how the
network builder decides whether a freshly generated product is a new species.

Identity DOES distinguish stereochemistry: RDKit's canonical SMILES is isomeric by
default, so R/S and E/Z are different species. That matters for steroids, chiral
drugs and anything where a template must not silently scramble a centre. Note the
converse, though -- templates do not yet *control* stereochemistry, so a rewrite
can lose it; the identity model is ahead of the reaction model here.

LIMITATION (v1): no tautomer resolution -- keto and enol forms are separate
species. Good enough to bootstrap; revisit when tautomers matter.
"""

from __future__ import annotations

from dataclasses import dataclass

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

# Compiled SMARTS queries, keyed by pattern text. Group-contribution
# fragmentation asks the same ~150 patterns of every molecule it sees, and
# compiling a query is far more expensive than running it.
_QUERY_CACHE: dict[str, object] = {}

_BOND_ORDER = {
    Chem.BondType.SINGLE: 1.0,
    Chem.BondType.DOUBLE: 2.0,
    Chem.BondType.TRIPLE: 3.0,
    Chem.BondType.AROMATIC: 1.5,
}


@dataclass(frozen=True)
class AtomView:
    """One heavy atom's local environment, as plain data.

    Deliberately not an RDKit atom: everything above ``matter`` works from this,
    so the backend stays swappable. ``neighbours`` holds heavy-atom indices only
    -- hydrogens are a count, which is the form group-additivity schemes want,
    since they treat H as a ligand rather than as an atom of its own.
    """

    index: int
    element: str
    aromatic: bool
    charge: int
    n_hydrogens: int
    in_ring: bool
    neighbours: tuple[int, ...]
    bond_orders: tuple[float, ...]

    def order_to(self, other: int) -> float:
        """Bond order to a neighbouring heavy atom, or 0 if not bonded."""
        for i, n in enumerate(self.neighbours):
            if n == other:
                return self.bond_orders[i]
        return 0.0

    @property
    def max_bond_order(self) -> float:
        return max(self.bond_orders) if self.bond_orders else 0.0


class Molecule:
    """A chemical structure, identified by canonical SMILES."""

    __slots__ = ("_mol", "_smiles", "_mol_h")

    def __init__(self, rdmol: Chem.Mol):
        # Store a sanitized copy; compute canonical SMILES once as the identity.
        self._mol = rdmol
        self._smiles = Chem.MolToSmiles(rdmol)
        # Built on first use by ``substructure_matches(explicit_hydrogens=True)``;
        # most molecules are never asked, and AddHs is not free.
        self._mol_h: Chem.Mol | None = None

    # ---- construction -------------------------------------------------------
    @classmethod
    def from_smiles(cls, smiles: str) -> "Molecule":
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError(f"invalid SMILES: {smiles!r}")
        return cls(mol)

    # ---- identity -----------------------------------------------------------
    @property
    def smiles(self) -> str:
        """Canonical SMILES -- the molecule's identity."""
        return self._smiles

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Molecule) and other._smiles == self._smiles

    def __hash__(self) -> int:
        return hash(self._smiles)

    def __repr__(self) -> str:
        return f"Molecule({self._smiles!r})"

    # ---- properties derived purely from structure ---------------------------
    @property
    def formula(self) -> str:
        return rdMolDescriptors.CalcMolFormula(self._mol)

    @property
    def molar_mass(self) -> float:
        """g / mol."""
        return Descriptors.MolWt(self._mol)

    @property
    def charge(self) -> int:
        return Chem.GetFormalCharge(self._mol)

    def element_counts(self) -> dict[str, int]:
        """Atom tally including implicit hydrogens -- basis for conservation checks."""
        counts: dict[str, int] = {}
        for atom in self._mol.GetAtoms():
            sym = atom.GetSymbol()
            counts[sym] = counts.get(sym, 0) + 1
            h = atom.GetTotalNumHs()
            if h:
                counts["H"] = counts.get("H", 0) + h
        return counts

    # ---- substructure queries ----------------------------------------------
    # Group-contribution methods (Joback, UNIFAC) decompose a molecule by
    # matching SMARTS patterns against it. Exposing that here rather than
    # letting Layer 1 reach for rdkit itself is what keeps Boundary 1 real: the
    # fragmentation algorithm is ours, the pattern matcher is swappable.

    @property
    def n_heavy_atoms(self) -> int:
        return self._mol.GetNumAtoms()

    def atom_symbols(self) -> list[str]:
        """Element symbol of each heavy atom, indexed as substructure matches are."""
        return [a.GetSymbol() for a in self._mol.GetAtoms()]

    def topology(self) -> list["AtomView"]:
        """Every heavy atom as plain data: element, bonding, and neighbours.

        Added for Benson group additivity, whose groups are not substructure
        patterns at all -- a Benson group IS a polyvalent atom together with the
        *types* of its ligands, which is precisely local topology. Expressing
        that as SMARTS would need one pattern per ligand combination and would
        reintroduce the matching ambiguity the scheme does not have.

        Returns plain dataclasses, never RDKit objects, so Boundary 0 stays
        sealed exactly as ``substructure_matches`` keeps it. Indices agree with
        ``atom_symbols`` and with substructure match tuples.
        """
        return Molecule._views(self._mol)

    @staticmethod
    def _views(mol: Chem.Mol) -> list["AtomView"]:
        out = []
        for atom in mol.GetAtoms():
            bonds = {}
            for bond in atom.GetBonds():
                other = bond.GetOtherAtom(atom).GetIdx()
                bonds[other] = _BOND_ORDER.get(bond.GetBondType(), 1.0)
            out.append(AtomView(
                index=atom.GetIdx(),
                element=atom.GetSymbol(),
                aromatic=atom.GetIsAromatic(),
                charge=atom.GetFormalCharge(),
                n_hydrogens=atom.GetTotalNumHs(),
                in_ring=atom.IsInRing(),
                neighbours=tuple(sorted(bonds)),
                bond_orders=tuple(bonds[i] for i in sorted(bonds)),
            ))
        return out

    def kekulized_topology(self) -> list["AtomView"]:
        """``topology()`` with alternating single/double bonds instead of aromatic.

        Same atom indices, so the two views can be mixed atom by atom. Aromatic
        flags are cleared, because a caller asking for the Kekule structure wants
        localised bonds -- reporting a bond as 1.0 while still calling the atom
        aromatic is a state nothing downstream can reason about.

        Added for Benson group additivity, whose values for heteroaromatics are
        tabulated on the Kekule structure: the ring correction for furan is
        -26.4 kJ/mol *against* localised C=C and C-O groups, and there are no
        aromatic-oxygen group values to pair with an aromatic view. Benzene is the
        exception and keeps the aromatic view, because its ``Cb`` group already
        carries the resonance.
        """
        m = Chem.Mol(self._mol)
        Chem.Kekulize(m, clearAromaticFlags=True)
        return Molecule._views(m)

    def ring_sizes(self) -> tuple[int, ...]:
        """Sizes of the smallest set of smallest rings.

        Benson prices a ring separately from its atoms: cyclopropane's carbons
        are ordinary CH2 groups plus 27 kcal/mol of strain that no additive
        scheme can see. The correction is per ring, so the caller needs the
        ring sizes and not merely whether an atom is in one.
        """
        return tuple(sorted(len(r) for r in self._mol.GetRingInfo().AtomRings()))

    def graph_automorphism_count(self) -> int:
        """|Aut(G)| for the heavy-atom graph -- how many ways it maps onto itself.

        This is the external rotational symmetry number a group-additivity
        entropy needs. Hydrogens are excluded on purpose: with them, a methyl
        contributes all 3! permutations of its hydrogens where only the 3 cyclic
        rotations are physical, which makes ethane 72 instead of 18. Terminal
        rotors are added back by the caller, which knows which are free.
        """
        heavy = Chem.RemoveHs(self._mol)
        return len(heavy.GetSubstructMatches(
            heavy, uniquify=False, useChirality=False, maxMatches=100_000
        ))

    def ring_atom_indices(self) -> tuple[tuple[int, ...], ...]:
        """The smallest set of smallest rings, as heavy-atom index tuples."""
        return tuple(self._mol.GetRingInfo().AtomRings())

    def substructure_matches(
        self, smarts: str, explicit_hydrogens: bool = False
    ) -> tuple[tuple[int, ...], ...]:
        """Every distinct match of a SMARTS pattern, as atom index tuples.

        An unparseable pattern is an error in our own group table, not a
        property of the molecule, so it is raised rather than skipped.

        ``explicit_hydrogens`` matches against the graph with hydrogens added as
        real atoms. This is NOT cosmetic and it is not interchangeable with the
        default: SMARTS connectivity primitives count explicit hydrogens, so a
        pattern's meaning changes between the two views. A primary amine's
        nitrogen is ``NX1`` with implicit hydrogens and ``NX3`` with explicit
        ones, and a clause like ``!$([N]~[!#6])`` -- "no non-carbon neighbour" --
        excludes every N-H bond once hydrogens are atoms. Fedors' critical-volume
        method is published against the explicit-hydrogen view, so it must ask
        for it; Joback, UNIFAC and Benson are written against the implicit one.
        Indices in the returned tuples are only comparable with ``atom_symbols``
        and ``topology`` in the default view -- added hydrogens are appended
        after the heavy atoms and shift nothing, but they do appear in matches.
        """
        query = _QUERY_CACHE.get(smarts)
        if query is None:
            query = Chem.MolFromSmarts(smarts)
            if query is None:
                raise ValueError(f"invalid SMARTS pattern: {smarts!r}")
            _QUERY_CACHE[smarts] = query
        target = self._mol
        if explicit_hydrogens:
            if self._mol_h is None:
                self._mol_h = Chem.AddHs(Chem.Mol(self._mol))
            target = self._mol_h
        return target.GetSubstructMatches(query, uniquify=True)


# ---------------------------------------------------------------------------
# THE STEREOCHEMISTRY-FREE SPELLING OF A MOLECULE
# ---------------------------------------------------------------------------
def stereo_free_smiles(smiles: str) -> str:
    """The same canonical SMILES with every stereochemical annotation removed.

    This is NOT an identity operation on species -- see the module docstring:
    two stereoisomers are two species and nothing here merges them. It exists so
    that a table keyed by one spelling can be ASKED about another, which the
    property providers do as a last-resort fallback and describe in their own
    terms.

    ⚠⚠ **IT IS NOT ``MolToSmiles(mol, isomericSmiles=False)``, AND THAT
    DISTINCTION IS LOAD-BEARING.** That flag drops ISOTOPE labels as well as
    stereochemistry: it turns ``[2H][2H]`` into ``[H][H]`` and ``[13CH4]`` into
    ``C``. A fallback built on it would hand deuterium hydrogen's record -- two
    species merged by a flag that was reached for to do something else.
    ``RemoveStereochemistry`` touches only stereochemistry, which is what the
    name of this function claims.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"invalid SMILES: {smiles!r}")
    Chem.RemoveStereochemistry(mol)
    return Chem.MolToSmiles(mol)
