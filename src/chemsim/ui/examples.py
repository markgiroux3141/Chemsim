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

⚠ **AND ``bench`` IS NOT LIKE THE OTHER FOUR** (P4). The first four are worked
examples with hand-chosen chemistry; the bench is whatever the player took off
the shelf, built through ``engine.inventory.scenario_for`` so that the two things
a selection must guarantee -- every charged species in the feed, and the
electrolyte overlay on when an ion is charged -- cannot be got wrong by a widget.
It carries the WHOLE template library rather than a curated handful, because
"mix two things and see" is the promise, and it defaults to ONE generation
because that is what a bench step is.
"""

from __future__ import annotations

import inspect as _inspect
from dataclasses import dataclass, replace

from chemsim.engine.inventory import find, scenario_for
from chemsim.engine.scenario import Scenario, TemplateSpec, VesselSpec
from chemsim.matter import Molecule
from chemsim.properties import dissociation_templates
from chemsim.reactions import ReactionTemplate
from chemsim.reactions import electrochemistry as _electro
from chemsim.reactions import library as _library
from chemsim.reactions import synthesis as _synthesis
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


# ---------------------------------------------------------------------------
# P4 -- the bench: the shelf, a flask, and one generation
# ---------------------------------------------------------------------------

# What the player starts the bench with. Glucose because it is the cheapest
# selection that shows the mechanic: at one generation it gives 26 species and 19
# reactions in 1.3 s, three of them fermentations, and leaves a 22-species
# frontier -- so "this flask has more to give" is true the moment the window
# opens. ⚠ And at TWO generations the same four reagents hit the 400-species cap
# in 25 s, which is the other half of the lesson and the reason the bound is a
# control rather than a constant.
BENCH_DEFAULT = ("water", "glucose", "oxygen", "nitrogen")


def full_library() -> list:
    """Every reaction template in the project, deduplicated by name.

    Read off the modules rather than listed here, because a list here would go
    stale the first time a session adds a template, and that is the one kind of
    rot the bench cannot afford: its whole claim is *mix anything*, and a bench
    missing the newest chemistry would quietly stop being that.

    ⚠⚠ **THE FIRST VERSION COLLECTED ONLY ``*_chemistry`` BUNDLES AND THAT WAS
    WRONG BY MORE THAN HALF.** It is the rule ``validation/playable_levers.py``
    panel 5 uses, it gathers 44 templates, and it silently skips every template
    exported as a function of its own -- ``sulfur_combustion``,
    ``sulfur_dioxide_oxidation``, ``sulfur_trioxide_hydration``,
    ``lead_chamber``, ``esterification``, ``cannizzaro`` and about forty more.
    **Playing it is what found that**: sulfur, air and water off the shelf gave
    four species, no reactions and an EMPTY FRONTIER at every generation count,
    which is the engine correctly reporting that it had been handed a library
    with no sulfur chemistry in it. A blurb claiming "every template in the
    project" was in the window at the time.

    So the sweep is by RESULT TYPE and not by name: every module-level function
    that needs no arguments is called, and whatever hands back a
    ``ReactionTemplate`` -- alone or in a sequence -- is a template factory.
    Anything else is skipped. That cannot be fooled by a naming convention
    nobody promised to keep.
    """
    seen: set[str] = set()
    out: list = []
    for mod in (_library, _synthesis, _electro):
        for name in sorted(dir(mod)):
            fn = getattr(mod, name)
            if not _inspect.isfunction(fn) or name.startswith("_"):
                continue
            if fn.__module__ != mod.__name__:
                continue                        # a re-export; its own module has it
            params = _inspect.signature(fn).parameters.values()
            if any(p.default is p.empty
                   and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
                   for p in params):
                continue                        # parameterised: not a plain factory
            try:
                got = fn()
            except Exception:                                   # noqa: BLE001, S112
                continue
            found = [got] if isinstance(got, ReactionTemplate) else (
                list(got) if isinstance(got, (list, tuple))
                and all(isinstance(x, ReactionTemplate) for x in got) and got
                else []
            )
            for tmpl in found:
                if tmpl.name not in seen:
                    seen.add(tmpl.name)
                    out.append(tmpl)
    return out


def bench(items=(), *, generations: int | None = 1, max_species: int = 400,
          volume: float = 1.0, T: float = 298.15) -> Example:
    """A flask holding exactly what was taken off the shelf.

    ``items`` are ``engine.inventory.ShelfItem``s. The opening script charges
    each one into its DECLARED phase -- a gas into the headspace, a rock into the
    solid block -- because the phase is where a bottle's contents go and the
    shelf declares it rather than deriving it (Joback puts olive oil's melting
    point at 829 K).

    ⚠ The scenario comes from ``inventory.scenario_for`` and not from a
    ``Scenario`` built here. That function owns the two guarantees a selection
    cannot be trusted to make -- every charged species in ``feed_species``,
    because ``Vessel.charge_state`` refuses one the network does not carry, and
    ``electrolyte`` on whenever an ion is being charged.
    """
    chosen = tuple(items) or tuple(find(cid) for cid in BENCH_DEFAULT)
    live = tuple(i for i in chosen if i.chargeable)
    scenario = scenario_for(
        live, templates=full_library(), volume=volume, T=T,
        generations=generations, max_species=max_species, UA=5.0, kla=5.0,
    )
    opening = tuple(
        _event("charge", "flask", amounts=item.amounts(), phase=item.phase)
        for item in live
    )
    names = ", ".join(i.name for i in live) or "nothing"
    gens = "a fixpoint" if generations is None else f"{generations} generation(s)"
    return Example(
        key="bench",
        title="The bench -- pick from the shelf",
        blurb=(
            f"In the flask: {names}.\n"
            f"\n"
            f"Explored to {gens}, with every template in the project loaded. One "
            f"generation is 'what can the things in this flask do, ONCE' -- the "
            f"products of that step become reactants only when you ask for "
            f"another. If the reports heading says the flask has more to give, "
            f"REACT FURTHER raises the bound; it does not hide it.\n"
            f"\n"
            f"Pick a different shelf in the Bench tab. A refused species is "
            f"greyed with the engine's own reason -- 416 of 1583 corpus species "
            f"cannot be priced at all, and that refusal is the element floor "
            f"working rather than a gap."
        ),
        scenario=scenario,
        opening=opening,
    )


def rebuilt(example: Example, *, generations: int | None = None,
            max_species: int | None = None) -> Example:
    """The same example with the network bounds moved. ⚠ THE BOUND, NOT THE RUN.

    What "react further" does: it changes the scenario's limits and nothing else,
    so the recipe replays against a deeper reaction set. That is a different
    claim from "continue from here" and the difference is worth being exact
    about -- a species discovered in the second generation was available from
    t = 0 on the replay, so a run that made C and then poured half of it away
    will see C reacting on to D during the first step too. It is the honest
    reading of *raise the bound*: the experiment is re-done knowing more
    chemistry, rather than the flask being handed a new reaction set mid-run.
    """
    scenario = replace(
        example.scenario,
        generations=(example.scenario.generations if generations is None
                     else generations),
        max_species=(example.scenario.max_species if max_species is None
                     else max_species),
    )
    return replace(example, scenario=scenario)


_BUILDERS = (_bare, _boil, _esterification, _prep, bench)


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
        ("bench", "The bench -- pick from the shelf"),
    ]


def load(key: str) -> Example:
    for build in _BUILDERS:
        example = build()
        if example.key == key:
            return example
    raise KeyError(f"no example {key!r}; have {[k for k, _ in titles()]}")
