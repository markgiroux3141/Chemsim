"""Layer 6 -- the PLAYER'S shelf: three tiers of data, turned into real bottles.

``engine/stock.py`` says what a bottle IS. This module says what is on the shelf
when the game starts, and it is the other half of the same argument: a `Stock` is
a `VesselState`, so a shelf row has to become a per-phase mole vector and a
temperature, and every question about how -- which phase, which species, how many
of them per formula unit -- has an answer that had to be measured rather than
picked. ``tools/build_shelf.py`` did the measuring; ``shelf_data`` is what it
wrote down; this module is the small amount of behaviour on top.

## ⚠ THIS IS NOT ``World.shelf``, AND KEEPING THEM APART IS LOAD-BEARING

``World.shelf`` is a RUN'S OUTPUT: bottles land in it and no event ever consumes
from it, because a ``World`` is a pure function of (scenario, script) and an
inventory that events could deplete would put part of the run outside both. The
shelf here is the PLAYER'S, it sits above the engine, and it is the one thing
``Shelf.take`` exists for. Both are ``Shelf`` objects; only this one is drawn
down.

## THE THREE TIERS, AND THE ONE AXIS THAT IS NOT A TIER

    natural       out of the ground, the air, or something living      43 rows
    intermediate  a STRANDED route makes it, so it is EARNABLE         24 rows
    bottle        nothing in 173 catalog routes makes it at all         4 rows

Granting the last two takes playable routes from 21 to 41 with no new chemistry
of any kind (``validation/playable_levers.py`` panel 3), and the tier column is
what lets the shelf SHRINK: when a session makes a stranded route reachable its
``intermediate`` rows are deleted from ``shelf.psv`` and the player earns them.

⚠ **``ALL_PRICED`` IS A SEPARATE AXIS AND NOT A FOURTH TIER.** It is every one of
the 1167 priced corpus species at once -- for exploration, and for pointing a
picker at 1167 rows to see what that costs. A cheat, declared as one.

## ⚠ 416 SPECIES MAY NEVER BE CHARGED, AND THEY ARE STILL IN THE ROSTER

The element floor refuses a price to 416 of 1583 corpus compounds, and that
refusal is the floor working: Joback prices Cl2 at -74.81 kJ/mol where the answer
is 0 by definition. ``GAME_DESIGN.md`` 8.3 requires such a species to be VISIBLE
in the picker, greyed, WITH ITS REASON -- never silently absent, and never
chargeable-then-failing. So ``roster()`` returns them, ``ShelfItem.chargeable``
is False, ``ShelfItem.refusal`` carries the engine's own sentence, and
``ShelfItem.stock()`` refuses rather than building a bottle that would fail at
the pour. **Seven of them are on the shelf itself** -- gold, quartz, pyrite,
pyrrhotite, pyrolusite, borax and cryolite -- because "you can dig this up" is a
true statement about the world whatever the estimators say.

## ⚠⚠ A STOCK'S SPECIES MUST BE IN THE NETWORK, WHICH MAKES THE PICKER A BUILDER

P2's finding, and the reason ``scenario_for`` is here rather than in a frontend:
``Vessel.charge_state`` refuses a species the network does not carry, loudly, and
a network is derived from its FEED. So choosing shelf rows is not filling a list
-- it is defining the scenario, and the world has to be rebuilt when the
selection changes. ``scenario_for`` takes the chosen items and guarantees the two
things that cannot be left to a caller: every charged species is in
``feed_species``, and ``electrolyte`` is on whenever an ion is being charged.
"""

from __future__ import annotations

from dataclasses import dataclass

from chemsim.engine.scenario import Scenario, TemplateSpec, VesselSpec
from chemsim.engine.shelf_data import ROSTER, SHELF, RosterEntry, ShelfEntry
from chemsim.engine.stock import Shelf, Stock
from chemsim.vessel import VesselState

TIERS = ("natural", "intermediate", "bottle")

# The tier name ``ALL_PRICED`` items carry. Deliberately not one of the three:
# reading it as a tier is the mistake ``GAME_DESIGN.md`` 8.5 warns about.
CHEAT_TIER = "priced"

# What a roster row that is not on the shelf brings, per phase, in mol. The shelf
# rows declare their own amount; these are for the cheat axis only, where 1167
# species cannot each be given a hand-chosen size. Sized like the shelf's: a
# single bench experiment in a 1 L flask, and a gas kept small because 1 mol of
# gas in a litre is 24 bar.
CHEAT_AMOUNT = {"gas": 0.05, "liquid": 1.0, "solid": 0.5}

# Room temperature. A bottle on a shelf is at the temperature of the room, and
# ⚠ that is a REAL number in the state rather than a placeholder: charging a
# stock carries its temperature into the flask, so a shelf at 298.15 K is why
# pouring something cold into a hot pot cools it.
T_SHELF = 298.15


@dataclass(frozen=True)
class ShelfItem:
    """One thing a player could pour: a shelf row, or any priced species.

    Flat rather than a pair of records because the two inputs answer different
    halves of one question -- ``shelf.psv`` says *how much, and why it is here*,
    the roster says *what species that actually is* -- and a caller wants the
    join, not the seam.
    """

    id: str
    name: str
    tier: str                   # one of TIERS, or CHEAT_TIER
    amount: float               # mol of the FORMULA UNIT
    phase: str                  # liquid | gas | solid -- where the charge lands
    note: str
    # From the roster, and see ``RosterEntry`` for why ``form`` is not decoration.
    form: str
    charge: tuple[tuple[str, float], ...]
    electrolyte: bool
    lattice: str
    price_tier: str
    refusal: str

    @property
    def chargeable(self) -> bool:
        return not self.refusal

    @property
    def species(self) -> tuple[str, ...]:
        return tuple(s for s, _n in self.charge)

    def amounts(self, fraction: float = 1.0) -> dict[str, float]:
        """``{species: mol}`` for ``fraction`` of the bottle.

        The multiplicity is the formula unit's own: fluorite is one calcium to
        two fluoride because its SMILES says ``[Ca+2].[F-].[F-]``, and gypsum's
        two waters of crystallisation become real water in the flask.
        """
        if not 0.0 <= fraction <= 1.0:
            raise ValueError(f"fraction must be in [0, 1], got {fraction}")
        return {s: n * self.amount * fraction for s, n in self.charge}

    def state(self, fraction: float = 1.0) -> VesselState:
        """The bottle as a ``VesselState`` at room temperature."""
        if not self.chargeable:
            raise ValueError(
                f"{self.id!r} may not be charged into a flask.\n\n{self.refusal}"
                f"\n\nThat refusal is the element floor working rather than a "
                f"gap: a group-contribution estimator outside its domain returns "
                f"a well-formed number that means nothing. A picker must show "
                f"this row greyed WITH THE REASON instead of offering it."
            )
        got = self.amounts(fraction)
        blocks: dict[str, dict[str, float]] = {
            "n_liquid": {}, "n_gas": {}, "n_solid": {}, "n_liquid2": {},
        }
        blocks["n_" + self.phase].update(got)
        return VesselState(T=T_SHELF, t=0.0, **blocks)

    def stock(self, fraction: float = 1.0, name: str = "") -> Stock:
        """The bottle as a ``Stock``, ready for ``Shelf.put`` or a pour.

        ⚠ ``script`` IS EMPTY AND THAT IS THE TRUTH ABOUT IT. Every other stock
        in this project carries the recipe that made it, so "how did I make this"
        is answerable and re-runnable. A starting reagent was not made: it was
        dug up, pressed out of a plant or bought, and ``source`` says which. An
        invented one-line script would be a recipe nobody ran.
        """
        return Stock(
            name=name or self.name,
            state=self.state(fraction),
            source=f"shelf: {self.tier}",
            note=self.note,
        )


def _item(entry: ShelfEntry | None, rec: RosterEntry) -> ShelfItem:
    """Join a shelf row (or nothing) to its roster entry.

    ⚠ WHERE THE PHASE COMES FROM IS THE ONE ASYMMETRY. A shelf row's phase is
    DECLARED, and it overrides the engine's estimate because the estimate is
    wrong about olive oil by 550 K -- Joback puts triolein's Tm at 828.9 K, so a
    derived phase would have put a bottle of oil in the solid block. A cheat-axis
    row has no declaration, so it takes the estimate and the estimate is all
    there is.
    """
    if entry is None:
        return ShelfItem(
            id=rec.id, name=rec.name, tier=CHEAT_TIER,
            amount=CHEAT_AMOUNT.get(rec.phase, 1.0), phase=rec.phase,
            note=rec.phase_why, form=rec.form, charge=rec.charge,
            electrolyte=rec.electrolyte, lattice=rec.lattice,
            price_tier=rec.price_tier, refusal=rec.refusal,
        )
    return ShelfItem(
        id=entry.id, name=rec.name, tier=entry.tier, amount=entry.amount,
        phase=entry.phase, note=entry.note, form=rec.form, charge=rec.charge,
        electrolyte=rec.electrolyte, lattice=rec.lattice,
        price_tier=rec.price_tier, refusal=rec.refusal,
    )


# ---------------------------------------------------------------------------
# what a picker is offered
# ---------------------------------------------------------------------------


def shelf(tiers: tuple[str, ...] = TIERS) -> tuple[ShelfItem, ...]:
    """The starting shelf, in file order, optionally filtered by tier."""
    unknown = [t for t in tiers if t not in TIERS]
    if unknown:
        raise ValueError(
            f"unknown shelf tier(s) {unknown}; have {list(TIERS)}. "
            f"{CHEAT_TIER!r} is a separate axis -- see ``all_priced``."
        )
    return tuple(_item(e, ROSTER[e.id]) for e in SHELF if e.tier in tiers)


def all_priced() -> tuple[ShelfItem, ...]:
    """THE CHEAT: every priced corpus species, by name.

    A separate axis from the tiers, and the reason it exists twice over: a player
    exploring wants everything, and a picker that has only ever been shown 71
    rows has not been tested. Sorted by name because 1167 rows in corpus-file
    order is not a list anybody can find anything in.
    """
    rows = [r for r in ROSTER.values() if r.chargeable]
    return tuple(_item(None, r) for r in sorted(rows, key=lambda r: r.name))


def roster(*, refused: bool = True) -> tuple[ShelfItem, ...]:
    """Every corpus species, refused ones included and marked.

    ⚠ ``refused=True`` IS THE DEFAULT ON PURPOSE. A player who cannot find a
    species must be told the engine declines to price it, not left to conclude
    the game is broken -- so the picker's default content includes the 416 that
    cannot be charged, greyed, each carrying its own reason.
    """
    rows = ROSTER.values() if refused else [
        r for r in ROSTER.values() if r.chargeable
    ]
    return tuple(_item(None, r) for r in sorted(rows, key=lambda r: r.name))


def find(cid: str) -> ShelfItem:
    """One species by catalog id, whether or not it is on the shelf."""
    rec = ROSTER.get(cid)
    if rec is None:
        raise KeyError(
            f"no corpus species {cid!r}. A shelf row is a "
            f"`data/catalog/compounds/*.psv` id -- {len(ROSTER)} of them."
        )
    entry = next((e for e in SHELF if e.id == cid), None)
    return _item(entry, rec)


def counts() -> dict[str, int]:
    """The scoreboard this module is measured by. Cheap; no chemistry."""
    out = {t: sum(1 for e in SHELF if e.tier == t) for t in TIERS}
    out["rows"] = len(SHELF)
    out["corpus"] = len(ROSTER)
    out["priced"] = sum(1 for r in ROSTER.values() if r.chargeable)
    out["refused"] = out["corpus"] - out["priced"]
    out["shelf refused"] = sum(
        1 for e in SHELF if not ROSTER[e.id].chargeable
    )
    return out


# ---------------------------------------------------------------------------
# turning a selection into a world
# ---------------------------------------------------------------------------


def feed_species(items) -> list[str]:
    """Every species the chosen items would charge, deduplicated, in order.

    Order matters and is not cosmetic: network species indices come from dict
    insertion order, so a stable order here is part of what makes a run
    reproducible from its scenario.
    """
    out: list[str] = []
    for item in items:
        for smiles in item.species:
            if smiles not in out:
                out.append(smiles)
    return out


def needs_electrolyte(items) -> bool:
    """True if any chosen item charges an ion.

    Without ``Scenario.electrolyte`` the network cannot price an ion at all, so
    this is not a preference: charging rock salt into a non-electrolyte world is
    a refusal waiting to happen at build time.
    """
    return any(item.electrolyte for item in items)


def open_shelf(items) -> Shelf:
    """A depletable ``Shelf`` of the chosen items, as bottles.

    The player's inventory, and the object ``Shelf.take`` was written for. Refused
    items are SKIPPED rather than raising: a caller handing over a whole tier
    should get the bottles that exist, and the greyed rows belong in the picker
    where the reason can be read.
    """
    out = Shelf()
    for item in items:
        if item.chargeable:
            out.put(item.stock())
    return out


def scenario_for(items, *, templates=(), volume: float = 1.0,
                 T: float = T_SHELF, generations: int | None = 1,
                 max_species: int = 400, **vessel) -> Scenario:
    """A one-flask ``Scenario`` that can actually hold the chosen items.

    ⚠ **THE TWO GUARANTEES ARE THE WHOLE POINT** and neither can be left to a
    caller. Every species the selection would charge is in ``feed_species``,
    because ``Vessel.charge_state`` refuses one the network does not carry and a
    network is derived from its feed. And ``electrolyte`` is on whenever an ion
    is in the selection, because ion formation energies are an overlay the plain
    provider does not have.

    ⚠ ``generations=1`` IS THE DEFAULT, AND IT IS THE MECHANIC RATHER THAN A
    BUDGET. "What can the things in this flask do, once" is what a bench step
    feels like, and it is also the only tractable bound on an open inventory:
    five ordinary reagents explored two generations deep hit a 400-species cap
    in twelve seconds. It is an approximation that touches MATTER, so it may not
    be silent -- ``build_network`` reports the frontier it did not expand and
    ``Snapshot.unexpanded`` carries it. Pass ``None`` for a fixpoint.
    """
    chosen = tuple(items)
    return Scenario(
        templates=[
            t if isinstance(t, TemplateSpec) else TemplateSpec.of(t)
            for t in templates
        ],
        feed_species=feed_species(chosen),
        vessels={"flask": VesselSpec(volume=volume, T=T, T_env=T, **vessel)},
        max_species=max_species,
        generations=generations,
        electrolyte=needs_electrolyte(chosen),
    )
