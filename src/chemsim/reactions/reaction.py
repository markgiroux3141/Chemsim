"""Layer 2 -- concrete reactions.

A ``ConcreteReaction`` is what a template produces once it has matched actual
species: a fully specified reaction with a reactant multiset, a product multiset,
and Arrhenius kinetics. Multisets are tuples of canonical SMILES *with*
repetition, so "2 EtOH -> ..." records ethanol twice -- and that multiplicity is
the mass-action rate-law exponent unless ``orders`` says otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConcreteReaction:
    name: str
    reactants: tuple[str, ...]  # canonical SMILES, with repetition
    products: tuple[str, ...]   # canonical SMILES, with repetition
    A: float
    Ea: float
    phase: str = "liquid"   # which phase this reaction runs in
    n_exp: float = 0.0      # modified-Arrhenius exponent: k = A T**n exp(-Ea/RT)
    # Rate-law exponents, one per entry of ``reactants``, or None for mass action.
    # ⚠ NOT the stoichiometry -- that is what ``reactants`` already is, and the
    # whole point of this field is that the two can differ. See
    # ``ReactionTemplate.orders``, which is where the argument lives; a
    # ConcreteReaction only carries what the template declared.
    orders: tuple[float, ...] | None = None
    # The SOLID CATALYST this reaction needs present, as a ``mineral_data``
    # lattice SMILES, or None. Order 1 on its AMOUNT in mol; stoichiometry
    # identically zero on both sides.
    #
    # ⚠ WHY THIS IS A FIELD AND NOT AN EXTRA ENTRY IN ``reactants``/``products``.
    # ``library._maybe_catalyse`` makes a HOMOGENEOUS catalyst explicit by
    # putting it on both sides of the SMARTS, which works because a dissolved
    # acid is an ordinary species on an ordinary basis -- its exponent lands in
    # ``order`` and its stoichiometry cancels out of ``delta``, and the kernel
    # needs to know nothing. A solid catalyst cannot go there: it is a LATTICE,
    # which has no molecular graph to match and lives in a different block on a
    # different basis (an amount, not a concentration). So it is declared, and
    # the one thing the kernel gains is a second exponent matrix.
    solid_catalyst: str | None = None

    def key(self) -> tuple:
        """Identity for de-duplication: same template + same multisets."""
        return (
            self.name,
            tuple(sorted(self.reactants)),
            tuple(sorted(self.products)),
            self.phase,
        )

    def is_null(self) -> bool:
        """A reaction whose products equal its reactants changes nothing."""
        return sorted(self.reactants) == sorted(self.products)
