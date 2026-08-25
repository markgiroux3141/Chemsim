"""Layer 3 -- reaction network construction.

Given a set of starting molecules and a set of templates, ``build_network``
*discovers* the concrete reaction set: it matches each template's reactant
patterns against the available species, applies the graph rewrite, canonicalizes
the products (registering novel species), and iterates to a fixpoint so that
products can themselves react. Element and charge conservation are enforced --
a malformed template that doesn't balance is rejected, not silently integrated.

Build time is also where thermodynamic consistency is imposed. Templates declare
FORWARD kinetics only; for a reversible template the reverse reaction's Arrhenius
parameters are derived here from the forward ones plus the reaction thermochemistry
(detailed balance). The reverse is then just another reaction in the list, so Layer
4 keeps integrating pure A*exp(-Ea/RT) mass action with no concept of reversibility.

The output, ``KineticArrays``, is the clean numeric hand-off to Layer 4: pure
numpy plus a species-name list, no molecules, no RDKit. That's the seam a Rust
kernel would sit behind.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np

from chemsim.matter import Molecule
from chemsim.properties import ThermochemistryProvider, VolatilityProvider
from chemsim.properties import standard_state
from chemsim.reactions import (
    ConcreteReaction,
    ReactionTemplate,
    detailed_balance,
    reaction_deltas,
)
from chemsim.reactions.thermo import COLLISION_LIMIT, T_REF

# Reaction phase -> the index Layer 4 splits on. Explicit and total: an
# unrecognised phase RAISES rather than falling through to the liquid block.
# This line is why: it used to read ``1 if rxn.phase == "gas" else 0``, so
# ``phase="any"`` -- a value the template validated and documented -- silently
# became "liquid". A default-to-liquid mapping cannot fail loudly, and the next
# phase added (a solid-phase reaction, say) would have been swallowed the same
# way. ``ReactionTemplate.phases`` now resolves "any" into concrete phases before
# anything reaches here.
PHASE_INDEX = {"liquid": 0, "gas": 1}


@dataclass
class KineticArrays:
    """Pure numeric projection of a reaction network -- the Layer 3/4 contract."""

    order: np.ndarray          # (n_reactions, n_species) mass-action exponents
    delta: np.ndarray          # (n_reactions, n_species) net stoichiometry
    A: np.ndarray              # (n_reactions,) Arrhenius pre-exponentials
    Ea: np.ndarray             # (n_reactions,) activation energies, J/mol
    species: list[str]         # canonical SMILES, in state-vector index order
    dH: np.ndarray = None      # (n_reactions,) reaction enthalpy, J/mol (+ = endothermic)
    phase: np.ndarray = None   # (n_reactions,) 0 = liquid phase, 1 = gas phase
    # (n_reactions,) temperature exponent of the modified Arrhenius form
    #     k = A * T**n * exp(-Ea / R T)
    # Zero for a declared forward rate, so the ordinary case is untouched. It is
    # non-zero only where detailed balance PUTS it there: the activity->molarity
    # standard-state conversion carries a factor T**delta_n which is not
    # Arrhenius, and n is where that factor now lives instead of being folded
    # into A at one reference temperature and left to drift.
    n_exp: np.ndarray = None
    _idx: dict[str, int] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._idx = {s: i for i, s in enumerate(self.species)}
        if self.dH is None:
            # Isothermal use never touches dH; an energy balance requires it, and
            # will say so rather than quietly releasing no heat.
            self.dH = np.full(self.A.shape[0], np.nan)
        if self.phase is None:
            self.phase = np.zeros(self.A.shape[0], dtype=int)
        if self.n_exp is None:
            self.n_exp = np.zeros(self.A.shape[0])

    @property
    def n_species(self) -> int:
        return len(self.species)

    @property
    def n_reactions(self) -> int:
        return self.A.shape[0]

    def vector(self, concentrations: dict[str, float]) -> np.ndarray:
        """Build a state vector from {SMILES: concentration}; unlisted species are 0."""
        c = np.zeros(self.n_species)
        for smi, val in concentrations.items():
            if smi not in self._idx:
                raise KeyError(f"{smi!r} is not a species in this network")
            c[self._idx[smi]] = val
        return c

    def as_dict(self, c: np.ndarray) -> dict[str, float]:
        return {s: float(c[i]) for i, s in enumerate(self.species)}


class ReactionNetwork:
    """A discovered set of species and the concrete reactions among them."""

    def __init__(
        self,
        molecules: dict[str, Molecule],
        reactions: list[ConcreteReaction],
        thermo: ThermochemistryProvider | None = None,
        volatility: VolatilityProvider | None = None,
    ):
        self.molecules = molecules
        self.species = list(molecules.keys())  # insertion order -> stable indices
        self.reactions = reactions
        self.thermo = thermo  # retained so to_arrays() can supply reaction enthalpies
        # Retained for the same reason, and so a Vessel can reuse the fitted
        # volatility models rather than refitting Lee-Kesler for every species.
        self.volatility = volatility

    def to_arrays(
        self, thermo: ThermochemistryProvider | None = None
    ) -> KineticArrays:
        """Project to the numeric contract. Reaction enthalpies are included when a
        thermochemistry provider is available (needed only for an energy balance)."""
        provider = thermo or self.thermo
        idx = {s: i for i, s in enumerate(self.species)}
        n, r = len(self.species), len(self.reactions)
        order = np.zeros((r, n))
        delta = np.zeros((r, n))
        A = np.zeros(r)
        Ea = np.zeros(r)
        n_exp = np.zeros(r)
        dH = np.full(r, np.nan)
        phase = np.zeros(r, dtype=int)
        for j, rxn in enumerate(self.reactions):
            if rxn.phase not in PHASE_INDEX:
                raise ValueError(
                    f"reaction {rxn.name!r} has phase {rxn.phase!r}, which Layer 4 "
                    f"cannot integrate -- expected one of {sorted(PHASE_INDEX)}. A "
                    "template's 'any' is resolved into concrete phases by "
                    "ReactionTemplate.phases before it gets here; a new phase needs "
                    "a block in the vessel RHS, not an entry in this table."
                )
            phase[j] = PHASE_INDEX[rxn.phase]
            # ⚠ ORDER AND DELTA COME APART HERE, and this loop is the only place
            # that knows it. ``delta`` is always the multiset -- stoichiometry is
            # not negotiable -- while ``order`` is the multiset ONLY when the
            # template did not declare a rate law. See ``ReactionTemplate.orders``:
            # a global stoichiometry written as one step (S8 + 8 O2) has a rate
            # law that is not its own coefficients, and taking them for it makes
            # the yield a reading of the pre-exponential.
            exponents = rxn.orders or (1.0,) * len(rxn.reactants)
            for s, e in zip(rxn.reactants, exponents, strict=True):
                order[j, idx[s]] += e
                delta[j, idx[s]] -= 1.0
            for s in rxn.products:
                delta[j, idx[s]] += 1.0
            A[j] = rxn.A
            Ea[j] = rxn.Ea
            n_exp[j] = rxn.n_exp
            if provider is not None:
                dH[j] = (
                    reaction_deltas(rxn, provider, self.volatility)[0] * 1000.0
                )  # kJ -> J/mol
        return KineticArrays(
            order, delta, A, Ea, list(self.species), dH, phase, n_exp
        )

    def describe(self) -> str:
        lines = [f"{len(self.species)} species, {len(self.reactions)} reactions"]
        for s in self.species:
            lines.append(f"  species: {s}  ({self.molecules[s].formula})")
        for rxn in self.reactions:
            lhs = " + ".join(rxn.reactants)
            rhs = " + ".join(rxn.products)
            lines.append(f"  [{rxn.name}] {lhs} -> {rhs}")
        return "\n".join(lines)


def _element_charge_balance(
    reactants: tuple[Molecule, ...], products: tuple[Molecule, ...]
) -> bool:
    left: dict[str, int] = {}
    right: dict[str, int] = {}
    for m in reactants:
        for el, n in m.element_counts().items():
            left[el] = left.get(el, 0) + n
    for m in products:
        for el, n in m.element_counts().items():
            right[el] = right.get(el, 0) + n
    if left != right:
        return False
    return sum(m.charge for m in reactants) == sum(m.charge for m in products)


def build_network(
    initial_smiles: list[str],
    templates: list[ReactionTemplate],
    max_species: int = 500,
    thermo: ThermochemistryProvider | None = None,
    T_ref: float = T_REF,
    generations: int | None = None,
    max_molar_mass: float | None = None,
    volatility: VolatilityProvider | None = None,
    liquid_standard_state: bool = True,
) -> ReactionNetwork:
    """Discover the reaction network reachable from the initial species.

    Iterates template application to a fixpoint. If ``max_species`` is hit, the
    expansion stops and a notice is printed -- coverage limits are never silent.

    Args:
        generations: stop after this many rounds of template application instead
            of running to a fixpoint. One generation is the "edge" of the current
            species set, which is what rate-based refinement needs to look at
            without enumerating an entire oligomer series first -- see
            ``chemsim.discovery``.
        max_molar_mass: refuse to register species heavier than this (g/mol). The
            honest bound for an oligomerising system, which would otherwise grow
            without limit. Everything dropped is reported.
        thermo: required if any template is reversible -- reverse kinetics are
            derived from it rather than declared. A species with no available
            thermochemistry is a hard error, not a silent drop: an unbalanced
            reversible pair would drive to completion and quietly falsify yields.
        T_ref: temperature at which the activity->concentration standard-state
            conversion is folded into the reverse pre-exponential. Only matters
            for reactions that change mole count; see ``detailed_balance``.
        volatility: supplies the ideal-gas -> liquid standard-state correction
            for liquid-phase reactions. Built from ``thermo`` if not given.
        liquid_standard_state: set False to keep formation data on its ideal-gas
            basis, which is what every result before this correction existed
            used. Wrong for a reaction in solution, and kept only so the
            difference can be measured; see ``properties.standard_state``.
    """
    if thermo is None and any(t.uses_thermochemistry for t in templates):
        names = sorted(t.name for t in templates if t.uses_thermochemistry)
        raise ValueError(
            f"template(s) {names} need a ThermochemistryProvider: reverse "
            "kinetics and Evans-Polanyi barriers are derived from reaction "
            "thermochemistry, not declared. Pass "
            "thermo=ThermochemistryProvider() to build_network()."
        )

    if liquid_standard_state and thermo is not None:
        volatility = volatility or VolatilityProvider(thermo)
    else:
        volatility = None

    molecules: dict[str, Molecule] = {}
    for smi in initial_smiles:
        m = Molecule.from_smiles(smi)
        molecules[m.smiles] = m

    reactions: dict[tuple, ConcreteReaction] = {}
    notices: dict[tuple, str] = {}
    state = _ExpansionState(max_species=max_species, max_molar_mass=max_molar_mass)

    frontier = list(molecules.values())   # first round considers everything
    rounds = 0
    while frontier and not state.capped:
        if generations is not None and rounds >= generations:
            break
        rounds += 1
        frontier = _expand_once(
            molecules, reactions, templates, thermo, volatility, T_ref,
            notices, state, frontier,
        )

    for msg in notices.values():
        print(msg)
    state.report(max_species)

    return ReactionNetwork(molecules, list(reactions.values()), thermo, volatility)


@dataclass
class _ExpansionState:
    """Bookkeeping for one expansion run -- caps hit, and what they cost."""

    max_species: int = 500
    max_molar_mass: float | None = None
    capped: bool = False
    oversize: dict[str, float] = field(default_factory=dict)
    tried: set = field(default_factory=set)

    def report(self, max_species: int) -> None:
        if self.oversize:
            heaviest = sorted(self.oversize.items(), key=lambda kv: -kv[1])[:3]
            print(
                f"[build_network] NOTICE: {len(self.oversize)} species exceeded "
                f"max_molar_mass={self.max_molar_mass:.0f} g/mol and were not "
                "registered. A growing series like this usually means the system "
                "polymerises, which species enumeration cannot represent properly. "
                "Heaviest dropped: "
                + ", ".join(f"{s} ({m:.0f})" for s, m in heaviest)
            )
        if self.capped:
            print(
                f"[build_network] NOTICE: hit max_species={max_species}; network "
                f"truncated. Coverage is incomplete -- raise the cap to go further."
            )


def _expand_once(
    molecules: dict[str, Molecule],
    reactions: dict[tuple, ConcreteReaction],
    templates: list[ReactionTemplate],
    thermo: ThermochemistryProvider | None,
    volatility: VolatilityProvider | None,
    T_ref: float,
    notices: dict[tuple, str],
    state: _ExpansionState,
    frontier: list[Molecule],
) -> list[Molecule]:
    """Apply every template one generation outward; return the species added.

    Only reactant combinations involving at least one member of ``frontier`` are
    considered. Combinations drawn entirely from previously-seen species were
    already tried in an earlier round, so re-running them is pure waste -- and it
    is quadratic waste, which is what made running to a fixpoint intractable.
    """
    current = list(molecules.values())
    fresh: set[str] = set(m.smiles for m in frontier)
    added: list[Molecule] = []

    for tmpl in templates:
        slot_matches = [
            [m for m in current if m._mol.HasSubstructMatch(tmpl.reactant_pattern(i))]
            for i in range(tmpl.n_reactant_slots)
        ]
        if any(len(slot) == 0 for slot in slot_matches):
            continue

        for combo in itertools.product(*slot_matches):
            if not any(m.smiles in fresh for m in combo):
                continue                      # nothing new in this pairing
            combo_key = (tmpl.name, tuple(m.smiles for m in combo))
            if combo_key in state.tried:
                continue
            state.tried.add(combo_key)

            for products in tmpl.run(combo):
                if not _element_charge_balance(combo, products):
                    continue                  # reject malformed / unbalanced rewrites

                new_rxns = _concrete_reactions(
                    tmpl, combo, products, thermo, volatility, T_ref, notices
                )
                if all(r.is_null() for r in new_rxns):
                    continue

                too_big = False
                for pm in products:
                    if pm.smiles in molecules:
                        continue
                    if (
                        state.max_molar_mass is not None
                        and pm.molar_mass > state.max_molar_mass
                    ):
                        state.oversize[pm.smiles] = pm.molar_mass
                        too_big = True
                        continue
                    if len(molecules) >= state.max_species:
                        state.capped = True
                        return added
                    molecules[pm.smiles] = pm
                    added.append(pm)
                if too_big:
                    continue                  # skip the reaction, not just the species

                for rxn in new_rxns:
                    if not rxn.is_null() and rxn.key() not in reactions:
                        reactions[rxn.key()] = rxn

    return added


def _concrete_reactions(
    tmpl: ReactionTemplate,
    reactants: tuple[Molecule, ...],
    products: tuple[Molecule, ...],
    thermo: ThermochemistryProvider | None,
    volatility: VolatilityProvider | None,
    T_ref: float,
    notices: dict[tuple, str],
) -> list[ConcreteReaction]:
    """Instantiate the forward reaction, plus a thermodynamically-derived reverse.

    One pair per phase the template runs in. A ``phase="any"`` template yields
    two independent pairs -- the standard state differs between them, so their
    equilibrium constants and hence their reverse rates genuinely differ, and
    ``ReactionTemplate.phases`` explains why they cannot be collapsed into one.

    ``notices`` is keyed by reaction identity so that a warning raised on every
    generation of the fixpoint loop is reported once, not once per pass.
    """
    out: list[ConcreteReaction] = []
    for phase in tmpl.phases:
        out.extend(
            _concrete_in_phase(
                tmpl, phase, reactants, products, thermo, volatility, T_ref, notices
            )
        )
    return out


def _concrete_in_phase(
    tmpl: ReactionTemplate,
    phase: str,
    reactants: tuple[Molecule, ...],
    products: tuple[Molecule, ...],
    thermo: ThermochemistryProvider | None,
    volatility: VolatilityProvider | None,
    T_ref: float,
    notices: dict[tuple, str],
) -> list[ConcreteReaction]:
    """One template, one phase -> the forward reaction and its derived reverse."""
    r_smiles = tuple(m.smiles for m in reactants)
    p_smiles = tuple(m.smiles for m in products)
    fwd = ConcreteReaction(tmpl.name, r_smiles, p_smiles, tmpl.A, tmpl.Ea, phase,
                           orders=tmpl.orders)

    # ⚠ A LIQUID-PHASE REACTION WHOSE SPECIES ARE NOT ALL ON THE SAME BASIS.
    # ``standard_state.mixed_basis`` explains the failure and what measured it;
    # the notice is here rather than there because this is where a reaction
    # exists as a whole. Silent before M5, and worth 323 kJ/mol on the first
    # network that hit it.
    if volatility is not None and phase != "gas":
        mixed = standard_state.mixed_basis(r_smiles, p_smiles, volatility, T_ref)
        if mixed:
            notices[f"{fwd.key()}|basis"] = (
                f"[build_network] NOTICE: '{' + '.join(r_smiles)} -> "
                f"{' + '.join(p_smiles)}' ({phase} phase) MIXES STANDARD STATES. "
                f"These species have no liquid standard-state shift while their "
                f"partners do: {', '.join(mixed)}. Their formation data stays on "
                f"the ideal-gas basis, so the reaction's dH and dG carry the "
                f"difference between two conventions on top of the chemistry. "
                f"Do not read this reaction's equilibrium constant."
            )

    # Evans-Polanyi: this member's barrier follows from its own reaction enthalpy,
    # so one template gives different substrates different rates. With alpha = 0
    # the declared barrier is returned unchanged and nothing here costs anything.
    Ea = tmpl.Ea
    if tmpl.alpha != 0.0:
        dH = reaction_deltas(fwd, thermo, volatility)[0] * 1000.0   # kJ -> J/mol
        Ea = tmpl.barrier(dH)
        fwd = ConcreteReaction(tmpl.name, r_smiles, p_smiles, tmpl.A, Ea, phase,
                               orders=tmpl.orders)

    if not tmpl.reversible:
        return [fwd]

    try:
        db = detailed_balance(
            fwd, thermo, tmpl.A, Ea, T_ref=T_ref, volatility=volatility
        )
    except Exception as exc:  # missing/unfragmentable species -- say which reaction
        lhs, rhs = " + ".join(r_smiles), " + ".join(p_smiles)
        raise ValueError(
            f"cannot derive reverse kinetics for reversible template "
            f"{tmpl.name!r} on '{lhs} -> {rhs}' ({phase} phase): {exc}"
        ) from exc

    if db.barrier_raised:
        notices[fwd.key()] = (
            f"[build_network] NOTICE: template {tmpl.name!r} declares "
            f"Ea={tmpl.Ea:.0f} J/mol for '{' + '.join(r_smiles)} -> "
            f"{' + '.join(p_smiles)}' ({phase} phase), below its endothermicity "
            f"dH={db.dH:.0f} J/mol. An elementary barrier cannot be lower than "
            f"dH; raised to {db.Ea_fwd:.0f} J/mol so the reverse barrier stays "
            f"non-negative. Forward rate is slower than declared."
        )

    if db.rate_capped < 1.0:
        notices[f"{fwd.key()}|capped"] = (
            f"[build_network] NOTICE: template {tmpl.name!r} on "
            f"'{' + '.join(r_smiles)} -> {' + '.join(p_smiles)}' ({phase} phase) "
            f"implies a rate constant above the collision limit "
            f"({COLLISION_LIMIT:.0e} L/(mol s)) in one direction. Both "
            f"pre-exponentials scaled by {db.rate_capped:.3e} so the faster "
            f"direction sits at the limit. K(T) is unchanged -- only how fast "
            f"the equilibrium is reached."
        )

    return [
        ConcreteReaction(
            tmpl.name, r_smiles, p_smiles, db.A_fwd, db.Ea_fwd, phase, db.n_fwd
        ),
        ConcreteReaction(
            f"{tmpl.name}_rev", p_smiles, r_smiles, db.A_rev, db.Ea_rev,
            phase, db.n_rev,
        ),
    ]
