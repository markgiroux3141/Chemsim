"""Layer 1 -- UNIFAC activity coefficients: the parameters, not the evaluation.

Everything else in Layer 1 answers "what is this property at temperature T?" and
collapses to a polynomial the kernel can evaluate blind. Activity coefficients
break that pattern, and it is worth being precise about why: gamma depends on
COMPOSITION, and composition *is* the state vector. There is no fixed array to
fit it to.

So the split moves rather than disappears. What this module does at setup:

  * fragment every species into UNIFAC subgroups (the same greedy priority
    matcher Joback uses -- see ``fragmentation.py``);
  * restrict the group basis to the subgroups the vessel's species actually
    contain, so the matrices stay small;
  * expand the published MAIN-group interaction table into a dense SUBGROUP
    matrix, so the hot loop never has to indirect through main groups.

What Layer 4 does per RHS call is then pure array arithmetic over ``nu``,
``R_k``, ``Q_k`` and ``a_mn`` -- see ``numerics/activity.py``. The layering
holds; only the shapes got richer.

Coverage is reported, never assumed. Three things can go wrong, and each is
named rather than silently treated as ideal:

  * a species has no UNIFAC decomposition (dissolved gases, ions, anything with
    an element the table doesn't cover). It gets gamma = 1;
  * a species is an ION. UNIFAC is a model of non-electrolyte mixtures; there is
    no Debye-Huckel term here, so ions get gamma = 1 by policy, not by accident;
  * a main-group PAIR is absent from the published matrix. Roughly half of them
    are -- nobody has regressed the data. A missing pair is not zero, and 0 is
    the strong claim that the two groups mix athermally, so the pair is reported.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from chemsim.matter import Molecule
from chemsim.properties import psrk_data as pd
from chemsim.properties import unifac_data as ud
from chemsim.properties.fragmentation import FragmentationError, by_priority
from chemsim.properties.fragmentation import fragment as _fragment

# The group table is UNIFAC-VLE plus PSRK's gas groups. The two never overlap --
# the extension supplies only main groups UNIFAC lacks -- so every parameter has
# exactly one source and nothing is overwritten. See ``psrk_data`` for why the
# join is sound rather than merely convenient.
GROUPS_BY_ID = {**ud.GROUPS_BY_ID, **pd.GROUPS_BY_ID}
GROUPS_BY_PRIORITY = by_priority(list(GROUPS_BY_ID.values()))
MAIN_GROUPS = {**ud.MAIN_GROUPS, **pd.MAIN_GROUPS}


def interaction(m: int, n: int) -> tuple[float, float, float] | None:
    """a_mn as (a, b, c) with a_mn(T) = a + b*T + c*T^2, or None if unpublished.

    UNIFAC's parameters are the constant case; PSRK's gas parameters are often
    genuinely quadratic in T.
    """
    if m == n:
        return (0.0, 0.0, 0.0)
    scalar = ud.INTERACTIONS.get((m, n))
    if scalar is not None:
        return (scalar, 0.0, 0.0)
    return pd.INTERACTIONS.get((m, n))


class UnifacError(FragmentationError):
    """Raised when a molecule cannot be fragmented into UNIFAC subgroups."""


# ⚠ The "ion: " prefix is a contract, not prose: ``ActivityArrays.report`` reads
# it to keep the ions and the neutrals in separate lists, because only one of
# the two is a gap. Anything that changes it has to change that too.
_IONIC = (
    "ion: UNIFAC is a non-electrolyte model and has no ionic groups, so the "
    "activity coefficient is left at 1 (no Debye-Huckel term in this project)"
)


@dataclass(frozen=True)
class UnifacGroups:
    """A species' subgroup decomposition, or an explicit statement that it has none."""

    counts: dict[int, int]      # subgroup_id -> occurrences
    source: str

    @property
    def modelled(self) -> bool:
        return bool(self.counts)

    def named(self) -> dict[str, int]:
        """The decomposition in group names -- what a chemist would check."""
        return {
            GROUPS_BY_ID[gid].name: n for gid, n in sorted(self.counts.items())
        }


def fragment(molecule: Molecule) -> dict[int, int]:
    """Partition a molecule into UNIFAC subgroups; raise if coverage is incomplete."""
    try:
        return _fragment(
            molecule, GROUPS_BY_PRIORITY, GROUPS_BY_ID, method="UNIFAC"
        )
    except FragmentationError as exc:
        raise UnifacError(str(exc)) from None


class UnifacProvider:
    """Resolves molecules to UNIFAC subgroup counts, with provenance."""

    def __init__(self) -> None:
        self._cache: dict[str, UnifacGroups] = {}

    def get(self, molecule: Molecule | str) -> UnifacGroups:
        mol = (
            molecule
            if isinstance(molecule, Molecule)
            else Molecule.from_smiles(molecule)
        )
        smi = mol.smiles
        if smi in self._cache:
            return self._cache[smi]

        if mol.charge != 0:
            groups = UnifacGroups({}, _IONIC)
        else:
            try:
                counts = fragment(mol)
                groups = UnifacGroups(counts, "UNIFAC group contribution")
            except UnifacError as exc:
                # Not fatal: an unmodelled species is ideal, which is what the
                # whole simulator did until now. It just has to say so.
                groups = UnifacGroups({}, f"no UNIFAC decomposition [{exc}]")
        self._cache[smi] = groups
        return groups


@dataclass
class ActivityArrays:
    """The UNIFAC parameter block, as the arrays Layer 4 consumes.

    ``nu`` is (n_species, n_groups); ``R_k``/``Q_k`` are (n_groups,); ``a_mn`` is
    (n_groups, n_groups, 3) -- already expanded from main groups to subgroups,
    and quadratic in temperature, a_mn(T) = a + b*T + c*T^2. UNIFAC's own
    parameters are the constant case, so one array carries both tables.
    ``active`` marks the species that have a decomposition at all -- the rest are
    held at gamma = 1.
    """

    nu: np.ndarray
    R_k: np.ndarray
    Q_k: np.ndarray
    a_mn: np.ndarray
    active: np.ndarray
    subgroup_ids: tuple[int, ...] = ()
    unmodelled: dict[str, str] = field(default_factory=dict)
    missing_pairs: tuple[tuple[str, str], ...] = ()
    # solute -> worst relative error of its fitted infinite-dilution reference
    reference_fits: dict[str, float] = field(default_factory=dict)

    @property
    def n_groups(self) -> int:
        return self.nu.shape[1]

    def report(self, fit_tolerance: float = 0.01) -> str:
        """A human-readable statement of what this model does NOT cover.

        ⚠ THE IONS AND THE NEUTRALS ARE LISTED SEPARATELY, because they are two
        different things wearing the same gamma = 1. An ion is held ideal by a
        stated POLICY -- this project has no Debye-Huckel term -- and it still
        has the Born term for the part that decides partitioning between layers.
        A neutral species is held ideal because nothing could be computed for it
        at all. Only the second list is a gap; running them together made the
        gap look like a policy. What that gap is WORTH in a given flask is a
        question about amounts rather than about the model, and
        ``Vessel.held_ideal`` answers it.
        """
        lines = []
        neutral = {
            smi: why for smi, why in self.unmodelled.items()
            if not why.startswith("ion:")
        }
        ionic = {
            smi: why for smi, why in self.unmodelled.items()
            if why.startswith("ion:")
        }
        if neutral:
            lines.append(
                f"{len(neutral)} NEUTRAL species have no decomposition and are "
                "held at gamma = 1 (ideal) -- this is the gap, not a policy:"
            )
            lines += [f"    {smi}: {why}" for smi, why in neutral.items()]
        if ionic:
            lines.append(
                f"{len(ionic)} ION(S) are held at gamma = 1 by policy (no "
                "Debye-Huckel term here); transfer between layers is priced by "
                "the Born term instead:"
            )
            lines += [f"    {smi}" for smi in ionic]
        if self.missing_pairs:
            lines.append(
                f"{len(self.missing_pairs)} main-group pairs have no published "
                "interaction parameter and are treated as athermal (a_mn = 0):"
            )
            lines += [f"    {m} <-> {n}" for m, n in self.missing_pairs]
        loose = {
            smi: err
            for smi, err in self.reference_fits.items()
            if err > fit_tolerance
        }
        if loose:
            lines.append(
                "Henry's-law reference states fitted to worse than "
                f"{fit_tolerance:.0%} over the reference temperature window:"
            )
            lines += [f"    {smi}: {err:.1%}" for smi, err in loose.items()]
        return "\n".join(lines)


def build_activity_arrays(
    species: list[str], provider: UnifacProvider | None = None
) -> ActivityArrays:
    """Assemble the UNIFAC parameter arrays for one vessel's species list.

    The group basis is restricted to subgroups that actually occur, which is what
    keeps the per-call cost proportional to the chemistry present rather than to
    the size of the published table.
    """
    provider = provider or UnifacProvider()
    n = len(species)

    decompositions = [provider.get(smi) for smi in species]
    present = sorted({gid for d in decompositions for gid in d.counts})
    g = len(present)
    index = {gid: i for i, gid in enumerate(present)}

    nu = np.zeros((n, g))
    active = np.zeros(n, dtype=bool)
    unmodelled: dict[str, str] = {}
    for i, (smi, d) in enumerate(zip(species, decompositions)):
        if not d.modelled:
            unmodelled[smi] = d.source
            continue
        active[i] = True
        for gid, count in d.counts.items():
            nu[i, index[gid]] = count

    R_k = np.array([GROUPS_BY_ID[gid].R for gid in present], dtype=float)
    Q_k = np.array([GROUPS_BY_ID[gid].Q for gid in present], dtype=float)

    # Expand main-group interactions to the subgroup basis. Subgroups of one main
    # group interact identically with everything, and not at all with each other.
    main = [GROUPS_BY_ID[gid].main_group_id for gid in present]
    a_mn = np.zeros((g, g, 3))
    missing: set[tuple[int, int]] = set()
    for i, mi in enumerate(main):
        for j, mj in enumerate(main):
            if mi == mj:
                continue
            value = interaction(mi, mj)
            if value is None:
                missing.add((mi, mj))
                continue
            a_mn[i, j] = value

    missing_pairs = tuple(
        (MAIN_GROUPS[m], MAIN_GROUPS[n]) for m, n in sorted(missing)
    )
    return ActivityArrays(
        nu=nu,
        R_k=R_k,
        Q_k=Q_k,
        a_mn=a_mn,
        active=active,
        subgroup_ids=tuple(present),
        unmodelled=unmodelled,
        missing_pairs=missing_pairs,
    )
