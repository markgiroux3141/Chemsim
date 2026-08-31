"""Layer 6 -- the scenario: everything needed to rebuild a world from text.

A save file must not contain molecules. RDKit objects are not serializable, and a
reaction network is derived data anyway -- it is a deterministic function of the
templates and the feed species. So a save stores the *recipe*, and loading
rebuilds the network from it.

That has two consequences worth stating. Saves stay small and human-readable: a
scenario is a few templates and a species list, not thousands of discovered
reactions. And network construction must be deterministic, which it is -- species
indices come from dict insertion order and template application iterates lists,
never sets.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from chemsim.reactions import ReactionTemplate


@dataclass(frozen=True)
class TemplateSpec:
    """A ReactionTemplate reduced to plain data.

    ⚠⚠⚠ **EVERY FIELD OF ``ReactionTemplate`` HAS TO BE HERE, AND SIX OF THEM
    WERE MISSING FOR THREE MILESTONES.** ``alpha``'s comment below records the
    failure mode; P4 found the same hole open for ``orders``, ``solid_catalyst``,
    ``electrons`` and the three ``hammett_*`` fields. The first was found by
    PLAYING the game rather than by any test. Sulfur, air, water and a trace of NO2 off the shelf would not make
    vitriol at one atmosphere, and the reason was that ``sulfur_combustion``
    declares ``orders=(1, 1, 0, 0, 0, 0, 0, 0, 0)`` -- first order in oxygen,
    which S11 spent a session establishing -- and this class dropped it, so the
    network ran the SMARTS' own ninth-body mass action instead. Measured on the
    burner at 700 K, 0.02 mol of S8 in a sealed litre:

        O2 charged    S8 burnt in an hour
          0.05 mol       0.0000%
          0.20 mol       0.0736%
          0.50 mol      77.85%

    That is a threshold where the declared law is a straight line, and it is what
    an exponent of 8 on oxygen looks like. **Any scenario is affected, not only a
    bench one**: the same drop silently un-gates every heterogeneous catalyst
    (``solid_catalyst``, S1 -- so a reaction that requires iron runs without it)
    and takes the driving force out of every electrode reaction (``electrons``,
    M8 -- so an electrolysis stops). A frontend can only reach the engine through
    a ``Scenario``, so a field missing here is a field the game does not have.

    ⚠⚠ **AND THE THREE ``hammett_*`` FIELDS WERE FOUND BY THE TEST, NOT BY THE
    PLAY.** ``tests/test_protocol.py`` asserts that every ``ReactionTemplate``
    field is carried here, and that generic assertion turned up three the play
    had not reached. ``aromatic_nitration()`` ships with ``hammett_rho = -6.5``,
    so this was the DEFAULT being lost rather than an unused option: G2 made
    nitration a PROCESS by deactivating a ring that has already been nitrated,
    and through a ``Scenario`` every stage of a staged nitration ran at the same
    rate. G1's dropping funnel builds exactly that template through exactly this
    class.

    *The lesson is the one this class already carried once, and it is not "add
    the field": a new template field is not finished until it round-trips, and
    the assertion has to be about the SET of fields rather than about whichever
    field somebody remembered.*
    """

    name: str
    smarts: str
    A: float
    Ea: float
    reversible: bool = False
    phase: str = "liquid"
    # Evans-Polanyi. Dropping it silently was a fidelity hole: a template with
    # alpha set would round-trip through a save as alpha=0, so every homologue
    # in the family would come back with the same barrier and the reloaded run
    # would diverge from the saved one for no visible reason.
    alpha: float = 0.0
    # ⚠ A DECLARED RATE LAW. ``None`` is ordinary mass action; a tuple is one
    # exponent per reactant SLOT of the SMARTS. Stored as a plain list-or-tuple
    # so a scenario stays JSON, and normalised back to a tuple on ``build``
    # because that is what ``ReactionTemplate`` validates against its slots.
    orders: tuple[float, ...] | list[float] | None = None
    # ⚠ THE CRYSTAL THAT MUST BE PRESENT, by ``mineral_data`` name. A gate, not a
    # phase: without it the reaction runs with no catalyst at all rather than
    # slowly, which is the opposite of what a gate means.
    solid_catalyst: str | None = None
    # ⚠ ELECTRONS ACROSS THE EXTERNAL CIRCUIT per reaction as written. Zero is
    # ordinary chemistry; non-zero is what makes an electrode reaction driven by
    # ``n F E`` rather than by nothing.
    electrons: int = 0
    # ⚠⚠ THE HAMMETT TRIPLE (G2, G6). ``hammett_rho`` is what makes nitration a
    # PROCESS rather than an event, and it is a sigma-PLUS scale coefficient
    # baked at setup. ``aromatic_nitration()`` ships with -6.5, so dropping it
    # was not a latent hole waiting for someone to set a field -- it was the
    # DEFAULT behaviour being lost, and every stage of a staged nitration ran at
    # the same rate. The saturation is the encounter plateau in decades (G6).
    hammett_rho: float = 0.0
    hammett_slot: int = 0
    hammett_saturation: float = 2.686

    def build(self) -> ReactionTemplate:
        return ReactionTemplate(
            name=self.name,
            smarts=self.smarts,
            A=self.A,
            Ea=self.Ea,
            reversible=self.reversible,
            phase=self.phase,
            alpha=self.alpha,
            orders=None if self.orders is None else tuple(self.orders),
            solid_catalyst=self.solid_catalyst,
            electrons=self.electrons,
            hammett_rho=self.hammett_rho,
            hammett_slot=self.hammett_slot,
            hammett_saturation=self.hammett_saturation,
        )

    @classmethod
    def of(cls, tmpl: ReactionTemplate) -> TemplateSpec:
        orders = getattr(tmpl, "orders", None)
        return cls(
            name=tmpl.name,
            smarts=tmpl.smarts,
            A=tmpl.A,
            Ea=tmpl.Ea,
            reversible=tmpl.reversible,
            phase=getattr(tmpl, "phase", "liquid"),
            alpha=getattr(tmpl, "alpha", 0.0),
            orders=None if orders is None else tuple(orders),
            solid_catalyst=getattr(tmpl, "solid_catalyst", None),
            electrons=int(getattr(tmpl, "electrons", 0)),
            hammett_rho=float(getattr(tmpl, "hammett_rho", 0.0)),
            hammett_slot=int(getattr(tmpl, "hammett_slot", 0)),
            hammett_saturation=float(
                getattr(tmpl, "hammett_saturation", 2.686)),
        )


@dataclass
class VesselSpec:
    """A vessel's fixed configuration -- geometry and boundary, not contents."""

    volume: float = 1.0
    T: float = 298.15
    T_env: float = 298.15
    UA: float = 0.5
    Q_input: float = 0.0
    P_ambient: float = 1.01325
    kla: float = 5.0
    k_vent: float = 1.0e3
    # ⚠ REACHABLE FROM THE SPEC BECAUSE THE FLAGSHIP PREP NEEDS IT AND COULD NOT
    # SAY SO. ``k_diss`` sets how fast a solid dissolves or crystallises, and
    # ``recipes.BENZOIC_ACID_PREP`` runs its pot at 0.05 against the 1e-2 default
    # -- so a scenario built from that recipe silently crystallised five times too
    # slowly and the example a frontend loads was not the example the harness
    # measured. Exactly the same class of gap as transfer losses and ``k_lle``,
    # missed when those were closed.
    k_diss: float = 1.0e-2
    heat_capacity: float = 50.0
    ingress: dict[str, float] = field(default_factory=dict)
    # Liquid-liquid: agitation, and whether a second layer may form at all.
    k_lle: float = 5.0
    lle: bool = True
    # Transfer losses. ``None`` is ideal mode -- every transfer perfectly
    # efficient -- and it is the default so that an invariant cannot move
    # because a default did. Given as plain numbers rather than as a
    # ``TransferLosses`` so a scenario stays JSON without a custom encoder.
    drain_time: float | None = None
    kinematic_viscosity: float = 1.0e-6
    crystal_size: float = 50.0e-6
    packing_fraction: float = 0.6


@dataclass
class EdgeSpec:
    """One connection between two vessels -- the APPARATUS, as saved data.

    ⚠ THIS IS WHAT MADE A STILL UNSAYABLE. ``Rig`` has had vapour, drain,
    thermal and metered edges since Layer 5, but only in Python: a ``World`` --
    the replayable, saveable, scriptable layer -- had no rig at all, so every
    coupled apparatus in this repo was assembled by hand in an example and could
    not be saved, replayed or scripted. The physics was never the gap.

    ``kind`` is the plain edge name (``vapour``, ``drain``, ``thermal``,
    ``meter``) rather than ``rig_integrator``'s integer, so a scenario stays
    readable JSON and a frontend can build one without importing the engine --
    the same rule ``TemplateSpec`` and the event kinds follow.
    """

    kind: str
    a: str
    b: str
    k: float = 1.0


# The edge names a scenario may use, mapped to the Rig method that builds one.
EDGE_KINDS = ("vapour", "drain", "thermal", "meter")


@dataclass
class Scenario:
    """The rebuildable definition of a world."""

    templates: list[TemplateSpec] = field(default_factory=list)
    feed_species: list[str] = field(default_factory=list)
    vessels: dict[str, VesselSpec] = field(default_factory=dict)
    # The apparatus. EMPTY means an uncoupled world, and that case must stay
    # BIT-IDENTICAL to what it was before rigs existed -- see ``World._advance``,
    # which keeps the old per-vessel path when there are no edges. Every number
    # this project has measured was measured without them.
    edges: list[EdgeSpec] = field(default_factory=list)
    max_species: int = 500
    # ⚠⚠ HOW MANY ROUNDS OF TEMPLATE APPLICATION, OR None FOR A FIXPOINT. This
    # is the field ``GAME_DESIGN.md`` section 8.2 rests on and it did not exist
    # until P2: ``World.__post_init__`` called ``build_network`` with no
    # ``generations``, so **nothing could request one-generation play through the
    # UI at all** and ``Snapshot.unexpanded`` was correct and permanently empty.
    #
    # One generation is "what can the things in this flask do, ONCE", which is
    # both the mechanic the game wants and the only tractable bound: measured in
    # ``validation/playable_levers.py`` panel 5, five bench reagents explored two
    # generations deep hit the 400-species cap in twelve seconds, and twelve
    # reagents explored one deep cost under half a second.
    #
    # ⚠ IT IS AN APPROXIMATION THAT TOUCHES MATTER, so it may not be silent: if
    # A + B makes C and C would react on to D, one generation shows C and never
    # D. That is admissible only because ``build_network`` reports the frontier
    # it did not expand, as a notice and as ``ReactionNetwork.unexpanded``, which
    # ``Snapshot`` publishes and the reports panel puts in its heading. None --
    # the default -- is a fixpoint, so every number this project measured before
    # this field existed is unchanged.
    generations: int | None = None
    T_build: float = 340.0        # temperature used for rate-aware pruning
    prune_threshold: float = 0.0  # 0 disables pruning (structural discovery)
    # Whether the network prices IONS. Without this a scenario cannot express
    # any acid/base chemistry at all -- no pH, no salting a product out, no
    # acidified workup -- because ion formation energies are an overlay the
    # plain provider does not carry. It is a flag rather than a provider object
    # so that a scenario stays plain JSON.
    electrolyte: bool = False

    def to_dict(self) -> dict:
        return {
            "templates": [asdict(t) for t in self.templates],
            "feed_species": list(self.feed_species),
            "vessels": {k: asdict(v) for k, v in self.vessels.items()},
            "edges": [asdict(e) for e in self.edges],
            "max_species": self.max_species,
            "generations": self.generations,
            "T_build": self.T_build,
            "prune_threshold": self.prune_threshold,
            "electrolyte": self.electrolyte,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Scenario:
        return cls(
            # ⚠ ``orders`` COMES BACK FROM JSON AS A LIST and has to become a
            # tuple again, or the template it builds compares a list against its
            # slot count and a saved declared rate law reloads as a different
            # object than the one that was saved. ``None`` stays ``None``.
            templates=[
                TemplateSpec(**{
                    **t,
                    "orders": (None if t.get("orders") is None
                               else tuple(t["orders"])),
                })
                for t in d.get("templates", [])
            ],
            feed_species=list(d.get("feed_species", [])),
            vessels={k: VesselSpec(**v) for k, v in d.get("vessels", {}).items()},
            edges=[EdgeSpec(**e) for e in d.get("edges", [])],
            max_species=int(d.get("max_species", 500)),
            # ⚠ None survives the round trip as None. ``int(d.get(...))`` would
            # turn "build to a fixpoint" into a TypeError, and a default of 0
            # would turn it into "apply no templates at all" -- a saved scenario
            # that quietly built an empty network.
            generations=(
                None if d.get("generations") is None
                else int(d["generations"])
            ),
            T_build=float(d.get("T_build", 340.0)),
            prune_threshold=float(d.get("prune_threshold", 0.0)),
            electrolyte=bool(d.get("electrolyte", False)),
        )
