"""Starting points a frontend can offer, as ``Scenario`` objects.

⚠ **A SCENARIO, NOT A SCRIPT THAT BUILDS VESSELS**, and that distinction is the
reason this module is short. ``recipes.BENZOIC_ACID_PREP`` hands back a ``Vessel``
because its three readers each instrument it differently; a user interface needs
the other form -- a ``Scenario`` plus events -- because that is the one Layer 6 can
save, reload and replay. The numbers still come from ``recipes``, so there is still
one home for them and this module cannot drift away from the harness that measures
them.

Each entry is a pair: the scenario (glassware and chemistry, fixed) and an opening
script (what is already in the flask when the player arrives). Keeping them
separate is what makes "reset" mean "empty the glassware" rather than "forget the
experiment".
"""

from __future__ import annotations

from dataclasses import dataclass

from chemsim.engine.scenario import Scenario, TemplateSpec, VesselSpec
from chemsim.matter import Molecule
from chemsim.properties import dissociation_templates
from chemsim.reactions.library import (
    aerobic_oxidation,
    esterification,
    ether_condensation,
    peroxide_over_oxidation,
)
from chemsim.recipes import BENZOIC_ACID_PREP


def _smi(s: str) -> str:
    return Molecule.from_smiles(s).smiles


WATER, ETHANOL, N2, O2 = "O", "CCO", "N#N", "O=O"
ACETIC = "CC(=O)O"
AIR = {N2: 0.79, O2: 0.21}


@dataclass(frozen=True)
class Example:
    """A scenario and what is already in the glassware."""

    key: str
    title: str
    blurb: str
    scenario: Scenario
    opening: tuple[dict, ...] = ()

    @property
    def script(self) -> tuple[dict, ...]:
        return self.opening


def _event(kind: str, vessel: str, **payload) -> dict:
    """One opening move, in the shape ``World.script`` records events in.

    ⚠ The shape is ``World``'s, not one invented here: an opening is replayed by
    ``World.run_script`` exactly as a saved recipe is, so an example and a save are
    the same kind of artifact and there is one walker for both.
    """
    return {"do": "schedule",
            "event": {"t": 0.0, "seq": 0, "kind": kind, "vessel": vessel,
                      "payload": payload}}


# ---------------------------------------------------------------------------


def _bare() -> Example:
    """Somewhere to start: one flask, water, air, nothing to react."""
    return Example(
        key="flask",
        title="A flask of water",
        blurb=(
            "One litre, open to the room, 25 C. Nothing reacts -- heat it, cool "
            "it, seal it, boil it dry. The cheapest way to see what the engine "
            "reports, and an idle flask costs no solver time at all."
        ),
        scenario=Scenario(
            feed_species=[WATER, ETHANOL, N2, O2],
            vessels={"flask": VesselSpec(volume=1.0, T=298.15, T_env=298.15,
                                         UA=5.0, kla=5.0)},
            max_species=20,
        ),
        opening=(
            _event("charge", "flask", amounts={WATER: 30.0}),
            _event("fill_headspace", "flask", composition=AIR),
        ),
    )


def _boil() -> Example:
    """The plateau. A hotplate under 50/50 ethanol and water."""
    return Example(
        key="boil",
        title="Boil ethanol and water",
        blurb=(
            "200 W under a 50/50 mixture. It climbs, then STOPS at its bubble "
            "point -- 352.9 K -- and stays there while the ethanol distils off. "
            "Nothing looks a boiling point up; it is where the vapour pressure "
            "reaches the room's. Try 'wait until it boils', then 'wait until the "
            "temperature is steady'."
        ),
        scenario=Scenario(
            feed_species=[ETHANOL, WATER, N2, O2],
            vessels={"pot": VesselSpec(volume=1.0, T=298.15, T_env=298.15,
                                       UA=2.0, kla=5.0, Q_input=200.0)},
            max_species=20,
        ),
        opening=(
            _event("charge", "pot", amounts={ETHANOL: 4.0, WATER: 4.0}),
            _event("fill_headspace", "pot", composition=AIR),
        ),
    )


def _esterification() -> Example:
    """Two templates meeting: an ester, and the air making something else."""
    return Example(
        key="ester",
        title="Fischer esterification, open to the air",
        blurb=(
            "Three moles each of acetic acid and ethanol at 350 K, with the "
            "flask OPEN. The ester is the point; the oxidation is not. Headspace O2 "
            "turns some ethanol into acetaldehyde and then into more acetic "
            "acid, which re-esterifies. Seal it (vent = 0) and all of that "
            "stops -- the oxygen budget is the whole lever."
        ),
        scenario=Scenario(
            feed_species=[ACETIC, ETHANOL, WATER, N2, O2],
            templates=[TemplateSpec.of(esterification()),
                       TemplateSpec.of(aerobic_oxidation()),
                       TemplateSpec.of(peroxide_over_oxidation())],
            vessels={"flask": VesselSpec(volume=1.0, T=350.0, T_env=350.0,
                                         UA=20.0, kla=5.0)},
            max_species=40,
        ),
        opening=(
            _event("charge", "flask", amounts={ACETIC: 3.0, ETHANOL: 3.0}),
            _event("fill_headspace", "flask", composition=AIR),
        ),
    )


def _prep() -> Example:
    """The flagship preparation, as a scenario rather than as three vessels.

    ⚠ EVERY NUMBER COMES FROM ``recipes.BENZOIC_ACID_PREP``, including the two
    counter-intuitive ones. ``k_lle = 0.5`` rather than the default 5.0, or the
    two-phase pot does not integrate at all; and ``k_diss = 0.05``, which a
    ``VesselSpec`` could not express until this session and which is why the
    crystallisation happens on the timescale the harness measured.

    The receiver is here so the player has somewhere to filter INTO. A mass
    balance has to be able to look everywhere the material could be, which is what
    made an early version of the harness read 99.97% closure -- not a loss
    destroying matter, a reader failing to look.
    """
    r = BENZOIC_ACID_PREP
    templates = [
        TemplateSpec.of(t) for t in (
            esterification(), aerobic_oxidation(), peroxide_over_oxidation(),
            ether_condensation(), *dissociation_templates(),
        )
    ]
    feed = [_smi("CCOC(=O)c1ccccc1"), _smi("OC(=O)c1ccccc1"), ETHANOL, WATER,
            "[OH-]", "[Na+]", "OS(=O)(=O)O", O2, N2]
    pot = VesselSpec(
        volume=r.pot_volume * r.scale, T=r.cook_T, T_env=r.cook_T, UA=r.UA,
        kla=r.kla, k_diss=r.k_diss, k_vent=0.0, k_lle=r.k_lle,
        drain_time=r.drain_time, crystal_size=r.crystal_size,
    )
    receiver = VesselSpec(
        volume=1.0 * r.scale, T=r.crystallise_T, T_env=r.crystallise_T, UA=5.0,
        kla=0.0, k_diss=0.0, k_vent=0.0, lle=False,
        drain_time=r.drain_time, crystal_size=r.crystal_size,
    )
    return Example(
        key="prep",
        title="Benzoic acid from ethyl benzoate",
        blurb=(
            "The worked preparation. Saponify at 80 C, quench with sulfuric "
            "acid, cool to 275 K, filter, wash. It yields ~84% at ~99.6% purity "
            "with the crust loss on, and the crystals stuck to the pot are 7.9% "
            "of the crop. Its own liberated ethanol oxidises in the headspace, "
            "so the route makes its own contaminant.\n"
            "\n"
            "⚠ The acid quench is the most expensive integration in this "
            "project: ten simulated seconds of it cost more wall time than four "
            "hours of crystal growth. Watch the cost meter."
        ),
        scenario=Scenario(
            feed_species=feed, templates=templates,
            vessels={"pot": pot, "receiver": receiver},
            max_species=120, electrolyte=True,
        ),
        opening=(
            _event("charge", "pot", amounts={
                WATER: r.water * r.scale,
                _smi("CCOC(=O)c1ccccc1"): r.ester * r.scale,
                "[OH-]": r.hydroxide * r.scale,
                "[Na+]": r.sodium_charge * r.scale,
            }),
            _event("fill_headspace", "pot", composition=AIR),
        ),
    )


_BUILDERS = (_bare, _boil, _esterification, _prep)


def catalogue() -> list[Example]:
    """Every starting point, built fresh.

    Built on demand rather than at import: the prep's network is 120 species over
    eight templates and discovering it is not free, so a frontend that offers four
    examples should pay for the one that is chosen.
    """
    return [build() for build in _BUILDERS]


def titles() -> list[tuple[str, str]]:
    """(key, title) for every example, without building any of them."""
    return [
        ("flask", "A flask of water"),
        ("boil", "Boil ethanol and water"),
        ("ester", "Fischer esterification, open to the air"),
        ("prep", "Benzoic acid from ethyl benzoate"),
    ]


def load(key: str) -> Example:
    for build in _BUILDERS:
        example = build()
        if example.key == key:
            return example
    raise KeyError(f"no example {key!r}; have {[k for k, _ in titles()]}")
