"""Layer 4.5 -- rate-based network refinement.

Structural discovery answers "what *can* form?". For a system that oligomerises
-- a diacid and a diol, say -- the honest answer is "an unbounded series", and
``build_network`` will faithfully enumerate it until it hits a cap. Chemically
correct; computationally fatal; and the resulting network is mostly species at
10^-30 M that could not affect any observable.

The question that actually matters is "what forms *in meaningful amounts*?", and
that is not a structural question at all -- it depends on concentrations, on
temperature, and on how long you wait. So this module answers it the only way it
can be answered: by simulating.

The loop is the standard rate-based generation scheme:

    1. take the current CORE species and build one generation outward;
    2. integrate the core-only network from the actual feed concentrations;
    3. with those concentrations, evaluate the rate of every EDGE reaction --
       the ones that would introduce a new species;
    4. promote the edge species whose formation rate clears a threshold;
    5. repeat until a round promotes nothing.

Step 2 is why this module exists at Layer 4.5 rather than inside ``network``:
refinement needs an integrator, and Layer 3 must not import Layer 4. Rather than
invert the dependency for one call, the layer that needs both sits above both.

Everything it drops is reported. A network that silently omitted a pathway would
be far more dangerous than one that is merely incomplete, because the omission
would look like a chemical result.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from chemsim.network import ReactionNetwork, build_network
from chemsim.numerics import Integrator
from chemsim.properties import ThermochemistryProvider
from chemsim.reactions import ReactionTemplate
from chemsim.reactions.thermo import T_REF


@dataclass
class RefinementReport:
    """What the refinement kept, dropped, and why -- never silent."""

    rounds: int = 0
    core_species: list[str] = field(default_factory=list)
    promoted: list[tuple[int, str, float]] = field(default_factory=list)
    rejected: list[tuple[str, float]] = field(default_factory=list)
    hit_cap: bool = False
    max_species: int = 0
    threshold: float = 0.0

    def summary(self) -> str:
        lines = [
            f"[discovery] {len(self.core_species)} species kept after "
            f"{self.rounds} round(s); {len(self.rejected)} candidate(s) rejected "
            f"below a formation rate of {self.threshold:.3e} mol/(L s)"
        ]
        if self.rejected:
            worst = sorted(self.rejected, key=lambda r: -r[1])[:5]
            lines.append(
                "  closest rejections: "
                + ", ".join(f"{s} ({r:.2e})" for s, r in worst)
            )
        if self.hit_cap:
            lines.append(
                f"  NOTICE: hit max_species={self.max_species}. Coverage is "
                "incomplete -- raise the cap or the threshold to go further."
            )
        return "\n".join(lines)


def _rates_of(net: ReactionNetwork, conc: dict[str, float], T: float) -> np.ndarray:
    """Mass-action rate of every reaction in ``net`` at the given composition."""
    arrays = net.to_arrays(thermo=None)
    c = np.array([conc.get(s, 0.0) for s in arrays.species])
    k = arrays.A * np.exp(-arrays.Ea / (8.314462618 * T))
    return k * np.prod(c**arrays.order, axis=1)


def refine_network(
    feed: dict[str, float],
    templates: list[ReactionTemplate],
    thermo: ThermochemistryProvider,
    *,
    T: float = T_REF,
    t_char: float = 3600.0,
    threshold: float = 1.0e-12,
    max_species: int = 500,
    max_rounds: int = 25,
    verbose: bool = True,
) -> tuple[ReactionNetwork, RefinementReport]:
    """Grow a network outward from ``feed``, keeping only what carries real flux.

    Args:
        feed: {SMILES: concentration in mol/L} -- the actual charge, because which
            species matter is a function of what you put in the flask.
        T: temperature for the rate evaluation. A network refined for 300 K is not
            valid at 600 K; refine at the temperature you intend to run.
        t_char: how long to integrate the core before judging edge rates. This is
            the "how long do you wait" knob -- a slow pathway that is irrelevant
            over an hour may dominate over a week.
        threshold: minimum formation rate, mol/(L s), for a new species to be kept.

    Returns the network and a report of everything dropped.
    """
    # Canonicalize up front: everything below keys off network SMILES, and a feed
    # written as "OC(=O)CCC(=O)O" must match the canonical form the builder emits.
    from chemsim.matter import Molecule

    feed = {Molecule.from_smiles(s).smiles: c for s, c in feed.items()}
    core = list(feed)                         # insertion order -> stable indices
    report = RefinementReport(max_species=max_species, threshold=threshold)

    for round_no in range(1, max_rounds + 1):
        report.rounds = round_no

        # 1. one generation outward from the current core
        edge_net = build_network(
            core, templates, max_species=max_species * 4,
            thermo=thermo, T_ref=T, generations=1,
        )
        new_species = [s for s in edge_net.species if s not in core]
        if not new_species:
            break

        # 2. integrate the CORE-ONLY network to get realistic concentrations
        core_net = build_network(
            core, templates, max_species=max_species * 4,
            thermo=thermo, T_ref=T, generations=1,
        )
        core_only = [r for r in core_net.reactions
                     if all(s in core for s in r.reactants + r.products)]
        conc = dict(feed)
        if core_only:
            sub = ReactionNetwork({s: core_net.molecules[s] for s in core},
                                  core_only, thermo)
            arrays = sub.to_arrays(thermo)
            c0 = np.array([feed.get(s, 0.0) for s in arrays.species])
            sol = Integrator(arrays).run(c0, T=T, t_span=(0.0, t_char))
            conc = arrays.as_dict(np.maximum(sol.y[:, -1], 0.0))

        # 3. rate of every edge reaction at that composition
        rates = _rates_of(edge_net, conc, T)
        best: dict[str, float] = {}
        for rxn, rate in zip(edge_net.reactions, rates):
            for s in rxn.products:
                if s not in core:
                    best[s] = max(best.get(s, 0.0), float(rate))

        # 4. promote what clears the bar
        promoted = [s for s, r in best.items() if r >= threshold]
        for s, r in best.items():
            if r < threshold:
                report.rejected.append((s, r))
        if not promoted:
            break

        promoted.sort(key=lambda s: -best[s])   # deterministic, best-first
        for s in promoted:
            if len(core) >= max_species:
                report.hit_cap = True
                break
            core.append(s)
            report.promoted.append((round_no, s, best[s]))
        if report.hit_cap:
            break

    # final full network over the accepted core, one generation to close it out
    final = build_network(core, templates, max_species=max_species,
                          thermo=thermo, T_ref=T, generations=1)
    keep = [r for r in final.reactions
            if all(s in core for s in r.reactants + r.products)]
    net = ReactionNetwork({s: final.molecules[s] for s in core}, keep, thermo)

    report.core_species = list(core)
    if verbose:
        print(report.summary())
    return net, report
