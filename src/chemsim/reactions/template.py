"""Layer 2 -- reaction templates.

A ``ReactionTemplate`` is the emergence engine's core idea: instead of storing
"acetic acid + ethanol -> ethyl acetate", we store a *transformation* -- a
SMARTS graph-rewrite rule ("carboxylic acid + alcohol -> ester + water") plus
its kinetics. It then applies to ANY molecules bearing the matched functional
groups. A few hundred templates cover a huge space of concrete reactions, which
is how we avoid a combinatorial dictionary of products.

The template carries Arrhenius kinetics (A, Ea) for the FORWARD direction only.
If it is reversible, the reverse parameters are *derived* at network-build time
from these plus the reaction's thermochemistry, via detailed balance -- see
``chemsim.reactions.thermo.detailed_balance``. A hand-typed reverse rate would be
a free parameter that silently contradicts the thermodynamics; there is no such
knob here by design.

Actual rate constants k = A*exp(-Ea/RT) are computed later, at integration time,
because they depend on temperature.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rdkit import Chem
from rdkit.Chem import AllChem

from chemsim.matter import Molecule


@dataclass
class ReactionTemplate:
    """A SMARTS graph-rewrite rule plus its kinetics.

    Args:
        name: human-readable label (e.g. "fischer_esterification").
        smarts: atom-mapped reaction SMARTS, "reactants>>products".
        A, Ea: forward Arrhenius pre-exponential and activation energy (J/mol).
            With ``alpha`` non-zero, ``Ea`` is the INTRINSIC barrier -- the value
            for a thermoneutral member of the family -- rather than the barrier
            every member gets.
        alpha: Evans-Polanyi transfer coefficient, in [0, 1]. The barrier of each
            concrete reaction becomes

                Ea_i = Ea + alpha * dH_i

            so a more exothermic member of the same family is faster, which is
            the single most important thing a template cannot otherwise express.
            Leave at 0 for a fixed barrier, which is what every template did
            before this existed. Requires a ThermochemistryProvider, since dH is
            computed rather than declared.
        reversible: if True, the reverse reaction is generated too -- with kinetics
            derived from thermochemistry, which is why ``build_network`` then
            requires a ThermochemistryProvider.
        phase: which phase the reaction runs in -- "liquid", "gas", or "any".
            A gas-phase template's rate is computed from headspace concentrations,
            which is what makes Haber/Ostwald-style chemistry expressible at all.
            "any" generates the reaction in BOTH phases -- see ``phases``.
        orders: rate-law exponents, ONE PER REACTANT SLOT of the SMARTS, or None
            (the default) for ordinary mass action. See below -- this is the one
            field that lets a template's rate law differ from its stoichiometry.

    ⚠ DECLARED ORDERS, AND WHY THE STOICHIOMETRY IS NOT ALWAYS THE RATE LAW.
    Everywhere else in this project the exponents come from the reactant multiset,
    which is correct for an ELEMENTARY step and is what "we assume elementary
    steps" bought. It stops being correct the moment a template writes a GLOBAL
    stoichiometry, and the case that forced this is sulfur burning:

        S8 + 8 O2 -> 8 SO2

    is not an elementary step -- nine molecules do not meet -- but it is the
    reaction. Taken as mass action it is NINTH ORDER, eighth in O2, and the
    measurements are recorded in ``library.sulfur_combustion``: it needs
    A = 7e24 (L/mol)^8/s to run at all, it is FORGIVEN wherever O2 is in excess
    (the attractor does the work), and it is NOT forgiven where O2 is limiting,
    because [O2]^8 stalls asymptotically and the yield becomes a reading of the
    author's pre-exponential rather than of the chemistry.

    ``orders`` is one exponent per reactant SLOT, in SMARTS order, and it is
    summed into the same exponent matrix the multiset would have built -- so the
    burner declares ``(1, 1, 0, 0, 0, 0, 0, 0, 0)``: eight oxygens are CONSUMED,
    one appears in the rate law. Nothing in Layer 4 changes; the kernel has always
    carried ``order`` as a matrix separate from ``delta`` and simply never had
    anything to put in it.

    ⚠ **A DECLARED ORDER MAY NOT BE REVERSIBLE, AND THIS IS REFUSED AT
    CONSTRUCTION.** ``detailed_balance`` derives the reverse from ``k_f / k_r =
    K(T)``, and that identity holds only because the forward and reverse exponents
    ARE the stoichiometric coefficients -- it is what makes the ratio of the two
    rate laws equal the mass-action quotient. With an apparent order it is not,
    so the derived "reverse" would be a reaction that reaches the wrong
    equilibrium while looking exactly like one that does not. The honest reading
    is simpler: an apparent order says the written reaction is NOT an elementary
    step, and a non-elementary step has no reverse to derive. Write the elementary
    steps if the equilibrium matters; declare an order only where it does not.

    ⚠ **AN ORDER BELOW 1 IS A KNEE AT ZERO CONCENTRATION**, and it is allowed
    because half-order rate laws are real (radical chains) -- but ``C**0.5`` has
    an infinite slope at C = 0, which is the same shape as the solid dissolution
    gate ``SOLID_GATE_TIME`` exists to flatten. Nothing here refuses it; declare
    one knowing that is what you are asking the solver for.

    WHY ALPHA MATTERS. Everything else in this project derives thermodynamics from
    structure -- equilibrium constants, reverse rates, phase behaviour. Rates were
    the exception: one template handed the same barrier to every substrate it
    matched, so which of two competing products formed faster was an author's
    choice, not a prediction. Evans-Polanyi ties the barrier to the reaction
    enthalpy the network already computes, so selectivity within a family follows
    from the chemistry. It is still an empirical relation with a fitted alpha; it
    is just no longer a per-substrate free parameter.

    The reverse direction needs nothing extra. Detailed balance gives
    Ea_rev = Ea_fwd - dH, so with Ea_fwd = Ea + alpha*dH the reverse comes out as
    Ea - (1 - alpha)*dH -- the Evans-Polanyi relation for the reverse reaction,
    with transfer coefficient (1 - alpha), exactly as it should be.
    """

    name: str
    smarts: str
    A: float
    Ea: float
    reversible: bool = False
    phase: str = "liquid"
    alpha: float = 0.0
    orders: tuple[float, ...] | None = None
    _rxn: AllChem.ChemicalReaction = field(default=None, repr=False, compare=False)

    # The phases a CONCRETE reaction may run in. "any" is not one of them: it is
    # a request for both, resolved by ``phases`` at network-build time, so
    # nothing below Layer 3 ever sees the word.
    CONCRETE_PHASES = ("liquid", "gas")
    VALID_PHASES = ("liquid", "gas", "any")

    def __post_init__(self) -> None:
        rxn = AllChem.ReactionFromSmarts(self.smarts)
        if rxn is None:
            raise ValueError(f"invalid reaction SMARTS in template {self.name!r}")
        rxn.Initialize()
        self._rxn = rxn
        if self.phase not in self.VALID_PHASES:
            raise ValueError(
                f"template {self.name!r}: phase must be one of {self.VALID_PHASES}, "
                f"got {self.phase!r}"
            )
        if not 0.0 <= self.alpha <= 1.0:
            raise ValueError(
                f"template {self.name!r}: Evans-Polanyi alpha is a transfer "
                f"coefficient and must lie in [0, 1], got {self.alpha}"
            )
        if self.orders is not None:
            self._check_orders()

    def _check_orders(self) -> None:
        """Validate a declared rate law. See the class docstring for the argument."""
        slots = self.n_reactant_slots
        if len(self.orders) != slots:
            raise ValueError(
                f"template {self.name!r}: orders has {len(self.orders)} entries "
                f"but the SMARTS has {slots} reactant slots. There must be one "
                f"exponent per slot, in SMARTS order -- a global stoichiometry "
                f"that consumes 8 O2 in 8 slots but is first order in oxygen "
                f"declares (1, 0, 0, 0, 0, 0, 0, 0) for those slots"
            )
        if any(o < 0.0 for o in self.orders):
            raise ValueError(
                f"template {self.name!r}: a negative rate order ({self.orders}) "
                f"makes the rate diverge as the species is consumed. Inhibition "
                f"is a saturation term (LHHW / Michaelis-Menten), which this "
                f"kernel does not express -- a bare negative exponent is not it"
            )
        if self.reversible:
            raise ValueError(
                f"template {self.name!r} declares BOTH reversible=True and "
                f"orders={self.orders}, and the two are incompatible. Detailed "
                f"balance derives the reverse from k_f/k_r = K(T), which holds "
                f"only because the exponents ARE the stoichiometric coefficients; "
                f"with an apparent order the ratio of the two rate laws is not "
                f"the mass-action quotient, so the derived reverse would reach "
                f"the WRONG equilibrium while looking like one that does not. An "
                f"apparent order means this is not an elementary step, and a "
                f"non-elementary step has no reverse to derive. Either write the "
                f"elementary steps (each mass-action, each reversible), or drop "
                f"reversible=True because the equilibrium lies hard over"
            )

    @property
    def phases(self) -> tuple[str, ...]:
        """The concrete phases this template instantiates in.

        ``"any"`` means the transformation is not tied to a phase -- a thermal
        rearrangement, say, which proceeds in solution and in the vapour alike --
        so it becomes TWO concrete reactions, one per phase, and the vessel runs
        each on that phase's own concentrations.

        Two reactions rather than one flagged reaction, because the two are not
        the same reaction. Their equilibrium constants differ: a liquid-phase
        reaction is moved into the pure-liquid standard state and a gas-phase one
        keeps the ideal-gas basis (see ``reactions.thermo.reaction_deltas``), so
        detailed balance derives a different reverse rate for each. Collapsing
        them would force one of the two onto the wrong standard state.

        This used to be broken in a way worth remembering: ``phase`` validated
        ``"any"`` and then ``network.builder.to_arrays`` mapped everything that
        was not ``"gas"`` to the liquid index, so ``"any"`` silently meant
        ``"liquid"``. The value was accepted, documented, and did nothing.
        """
        if self.phase == "any":
            return self.CONCRETE_PHASES
        return (self.phase,)

    @property
    def uses_thermochemistry(self) -> bool:
        """True if this template's kinetics cannot be built without reaction thermo."""
        return self.reversible or self.alpha != 0.0

    def barrier(self, dH: float) -> float:
        """The Evans-Polanyi barrier for one member of the family, J/mol.

        Floored at zero: a barrier cannot be negative however exothermic the
        reaction is. The complementary floor -- a barrier below the
        endothermicity, which would make the REVERSE barrier negative -- is
        applied by ``detailed_balance``, which is where dH is already in hand.
        """
        return max(self.Ea + self.alpha * dH, 0.0)

    @property
    def n_reactant_slots(self) -> int:
        return self._rxn.GetNumReactantTemplates()

    def reactant_pattern(self, i: int) -> Chem.Mol:
        """Query molecule for reactant slot i -- used to find matching species."""
        return self._rxn.GetReactantTemplate(i)

    def run(self, reactants: tuple[Molecule, ...]) -> list[tuple[Molecule, ...]]:
        """Apply the forward rewrite to one ordered tuple of reactant molecules.

        Returns a de-duplicated list of product tuples. RDKit can yield several
        product sets for one input (symmetry / multiple matches); we sanitize
        each product and collapse duplicates by canonical SMILES.

        ⚠ **EXPLICIT HYDROGENS ARE COLLAPSED, AND WITHOUT THAT A TEMPLATE THAT
        MOVES AN H ATOM SILENTLY FORKS THE SPECIES LIST.** A rewrite that writes
        hydrogen as an ATOM -- which anything consuming H2 must, because ``[H][H]``
        has no heavy atom to hang an implicit count on -- hands back a product
        whose hydrogens are still separate atoms, and ``Molecule`` canonicalises
        that as ``[H]N([H])[H]`` rather than ``N``. Ammonia made by the Haber
        template would then be a DIFFERENT species from ammonia charged into the
        flask: two state-vector entries, no reaction connecting them, and a mass
        balance that closes perfectly while the answer is wrong. ``RemoveHs``
        collapses them onto their heavy atom, and it correctly leaves H2 itself
        alone -- neither of its atoms has a heavy neighbour to fold into.
        """
        rd_reactants = tuple(m._mol for m in reactants)
        outcomes = self._rxn.RunReactants(rd_reactants)

        results: list[tuple[Molecule, ...]] = []
        seen: set[tuple[str, ...]] = set()
        for product_set in outcomes:
            mols: list[Molecule] = []
            ok = True
            for p in product_set:
                try:
                    Chem.SanitizeMol(p)
                    p = Chem.RemoveHs(p)
                except (Chem.AtomValenceException, Chem.KekulizeException, ValueError):
                    ok = False
                    break
                mols.append(Molecule(p))
            if not ok:
                continue
            key = tuple(sorted(m.smiles for m in mols))
            if key in seen:
                continue
            seen.add(key)
            results.append(tuple(mols))
        return results
