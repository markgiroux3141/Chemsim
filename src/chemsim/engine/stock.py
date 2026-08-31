"""Layer 6 -- a bottle on a shelf: a named ``VesselState``, and nothing else.

**A stock is a COMPOSITION, not a noun.** ``GAME_DESIGN.md`` section 1 is the
argument in full and this module is that decision as code: an inventory item is
the full per-phase mole vector plus a temperature -- which is exactly
``VesselState`` -- and never ``(name, purity%)``.

Four consequences follow, and none of them needed engine work:

* **purity is DERIVED, never stored.** ``purity()`` is a label computed for
  display, and it takes a BASIS because "92% pure" is a mass figure at a bench
  and a mole figure in a mole vector. The moment purity becomes state, every gate
  in the design becomes decoration;
* **two bottles labelled "ethanol, 95%" behave differently** if one's 5% is water
  and the other's is acetaldehyde. That difference is the game, which is also why
  ``Shelf.put`` never merges two bottles that arrive under the same name;
* **impurities are carried individually and forever**, so a contaminant
  introduced in step 1 can ruin step 6 and the player can trace it back;
* **a stock carries its own script**, so "how did I make this" is answerable and
  re-runnable. Because ``World.script`` stores CONDITIONS rather than instants,
  re-running it at 10x scale waits the right length of time -- the fork taken in
  the wait-until session was taken for exactly this.

⚠ **AND A STOCK CAN REACT IN THE BOTTLE, which nobody designed and is free.** It
has a temperature and a phase layout, so advancing a stored stock is an ordinary
integration: charge it into a flask, step, bottle it again. Wet aspirin
hydrolyses back to salicylic acid on the shelf; ether under air makes peroxides.
Shelf life is emergent from an inventory of compositions and a bag of nouns
cannot do it at any price.

## What this module is NOT

⚠ **``World.shelf`` is a run's OUTPUT, not the player's inventory.** Bottles land
in it; nothing is ever consumed from it by an event. The player's persistent
shelf -- the thing with three tiers that ``data/catalog/shelf.psv`` will hold --
lives above the engine and draws its own entries down with ``Shelf.take``. Keeping
those two apart is what makes a run replayable: a ``World`` is a pure function of
(scenario, script), and an inventory that events could deplete would put part of
the run outside both.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from chemsim.vessel import VesselState

# Display floor: below this a component is round-off rather than an impurity.
# It is a rendering threshold and nothing else -- ``state`` keeps every number.
_FLOOR = 1.0e-12

# Molar masses, memoised. ``Molecule.from_smiles`` re-parses on every call and a
# mass-basis purity asks for one per component per redraw.
_MASS: dict[str, float] = {}


def molar_mass(smiles: str) -> float:
    """g/mol, memoised. Layer 0 is the only place that knows the answer."""
    m = _MASS.get(smiles)
    if m is None:
        from chemsim.matter import Molecule

        m = float(Molecule.from_smiles(smiles).molar_mass)
        _MASS[smiles] = m
    return m


def _clean(d: dict[str, float] | None) -> dict[str, float]:
    """A mole dict with the zeros dropped and the values made plain floats."""
    return {k: float(v) for k, v in (d or {}).items() if float(v) != 0.0}


def state_to_dict(state: VesselState) -> dict:
    """``VesselState`` -> JSON. By field NAME, as ``World`` saves a vessel."""
    return {
        "T": float(state.T),
        "t": float(state.t),
        "n_liquid": _clean(state.n_liquid),
        "n_liquid2": _clean(state.n_liquid2),
        "n_gas": _clean(state.n_gas),
        "n_solid": _clean(state.n_solid),
    }


def state_from_dict(d: dict) -> VesselState:
    return VesselState(
        n_liquid=_clean(d.get("n_liquid")),
        n_gas=_clean(d.get("n_gas")),
        T=float(d["T"]),
        t=float(d.get("t", 0.0)),
        n_solid=_clean(d.get("n_solid")),
        n_liquid2=_clean(d.get("n_liquid2")),
    )


def scale_state(state: VesselState, fraction: float) -> VesselState:
    """The same composition at a different size. ⚠ The TEMPERATURE does not
    scale -- it is intensive, and half a bottle is not half as hot."""
    return VesselState(
        n_liquid={k: v * fraction for k, v in state.n_liquid.items()},
        n_gas={k: v * fraction for k, v in state.n_gas.items()},
        T=float(state.T),
        t=float(state.t),
        n_solid={k: v * fraction for k, v in state.n_solid.items()},
        n_liquid2={k: v * fraction for k, v in state.n_liquid2.items()},
    )


@dataclass(frozen=True)
class Stock:
    """One bottle: a name, a ``VesselState``, and how it came to exist.

    Frozen, and the mole dicts are COPIED on construction, because a ``Stock`` is
    published to a view thread on a ``Snapshot``. A bottle that aliased a live
    vessel's arrays would be a mutable object read from the wrong thread, which
    is the one thing Layer 7 exists to prevent.
    """

    name: str
    state: VesselState
    # ``World.script`` at the instant it was bottled -- the recipe, not a
    # transcript. See ``World.script`` for why that distinction is load-bearing.
    script: tuple[dict, ...] = ()
    source: str = ""              # the vessel it was bottled from, or a shelf tier
    note: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", state_from_dict(state_to_dict(self.state)))
        object.__setattr__(self, "script", tuple(dict(e) for e in self.script))

    # -- derived, for display: nothing here is state -------------------------

    @property
    def total(self) -> float:
        """Total moles, every phase."""
        s = self.state
        return float(
            sum(s.n_liquid.values()) + sum(s.n_liquid2.values())
            + sum(s.n_gas.values()) + sum(s.n_solid.values())
        )

    def amounts(self) -> dict[str, float]:
        """Moles per species across every phase, biggest first."""
        out: dict[str, float] = {}
        for block in (self.state.n_liquid, self.state.n_liquid2,
                      self.state.n_gas, self.state.n_solid):
            for k, v in block.items():
                out[k] = out.get(k, 0.0) + v
        return {
            k: v for k, v in sorted(out.items(), key=lambda kv: -kv[1])
            if v > _FLOOR
        }

    def fractions(self, basis: str = "mole") -> dict[str, float]:
        """Composition as fractions, biggest first.

        ⚠ THE BASIS IS AN ARGUMENT AND HAS NO SILENT DEFAULT ANSWER. A mole
        vector's own fractions are molar; a chemist quoting "97% pure" means
        mass. For a wet crystalline product the two differ by a lot -- 0.05 mol
        of water in 0.05 mol of benzoic acid is 50 mol% and 13 wt% -- so a figure
        that does not say which it is, is not a figure.
        """
        amounts = self.amounts()
        if basis == "mole":
            weights = amounts
        elif basis == "mass":
            weights = {k: v * molar_mass(k) for k, v in amounts.items()}
        else:
            raise ValueError(f"basis must be 'mole' or 'mass', got {basis!r}")
        total = sum(weights.values())
        if total <= 0.0:
            return {}
        return {
            k: v / total
            for k, v in sorted(weights.items(), key=lambda kv: -kv[1])
        }

    def major(self, basis: str = "mole") -> str:
        """The biggest component on ``basis``, or "" for an empty bottle.

        ⚠ IT TAKES THE BASIS TOO, AND NOT FOR SYMMETRY'S SAKE. A crop of
        benzoic acid wet with an equal NUMBER OF MOLES of water has water as its
        biggest component by mole and benzoic acid by mass, so a ``major`` fixed
        on moles printed beside a ``purity`` quoted by mass would read "water at
        87 wt%" -- two true numbers making one false statement. The pair has to
        be read on one basis, so the basis is an argument to both.
        """
        return next(iter(self.fractions(basis)), "")

    def purity(self, basis: str = "mole") -> float:
        """``major(basis)``'s fraction. **Derived, never stored** -- see
        ``fractions`` for why the basis has to be said out loud."""
        return next(iter(self.fractions(basis).values()), 0.0)

    def describe(self) -> str:
        s = self.state
        phases = [
            name for name, block in (
                ("liquid", s.n_liquid), ("2nd layer", s.n_liquid2),
                ("gas", s.n_gas), ("solid", s.n_solid),
            ) if any(v > _FLOOR for v in block.values())
        ]
        head = (
            f"{self.name}: {self.total:.4g} mol at {s.T:.1f} K"
            f"  [{', '.join(phases) or 'empty'}]"
        )
        major = self.major("mass")
        if not major:
            return head
        others = len(self.amounts()) - 1
        return (
            f"{head}\n  {major} at {100.0 * self.purity('mass'):.2f} wt%"
            + (f", {others} other component(s)" if others else ", nothing else in it")
        )

    # -- taking a share ------------------------------------------------------

    def scaled(self, fraction: float) -> Stock:
        """The same bottle at a different size, keeping its provenance."""
        if fraction < 0.0:
            raise ValueError(f"fraction must be non-negative, got {fraction}")
        return replace(self, state=scale_state(self.state, fraction))

    def split(self, fraction: float) -> tuple[Stock, Stock]:
        """(what is poured out, what is left in the bottle).

        ⚠ NO LOSS IS TAKEN HERE, and that is not an oversight. Holdup is a
        MECHANIC and it belongs to the glassware that suffers it: pouring a
        bottle into a flask wets the flask, and ``Vessel.withdraw`` is where a
        film is withheld. A shelf is bookkeeping, and a tax applied by
        bookkeeping is exactly the kind of loss this project refuses.
        """
        if not 0.0 <= fraction <= 1.0:
            raise ValueError(f"fraction must be in [0, 1], got {fraction}")
        return self.scaled(fraction), self.scaled(1.0 - fraction)

    # -- persistence ---------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "state": state_to_dict(self.state),
            "script": [dict(e) for e in self.script],
            "source": self.source,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Stock:
        return cls(
            name=str(d["name"]),
            state=state_from_dict(d["state"]),
            script=tuple(dict(e) for e in d.get("script", ())),
            source=str(d.get("source", "")),
            note=str(d.get("note", "")),
        )


@dataclass
class Shelf:
    """Bottles, by name, in the order they arrived.

    Ordered because a save has to round-trip and because the picker P4 builds
    reads it back: dict insertion order is the same rule ``build_network`` uses
    for species indices, and for the same reason -- determinism has to come from
    somewhere and a set is not a place.
    """

    stocks: dict[str, Stock] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.stocks)

    def __contains__(self, name: object) -> bool:
        return name in self.stocks

    def __iter__(self):
        return iter(self.stocks.values())

    def get(self, name: str) -> Stock:
        try:
            return self.stocks[name]
        except KeyError:
            raise KeyError(
                f"no stock named {name!r} on this shelf; have "
                f"{sorted(self.stocks) or '(nothing)'}"
            ) from None

    def put(self, stock: Stock) -> Stock:
        """Store a bottle, and return it under the name it actually got.

        ⚠⚠ **TWO BOTTLES UNDER ONE NAME ARE NEVER MERGED, AND THIS IS THE
        SECTION-1 DECISION ENFORCED RATHER THAN RESTATED.** A player who runs the
        same prep twice and calls both "crude aspirin" has two bottles, and the
        whole point of a stock being a composition is that those two are not
        interchangeable -- one may carry unreacted salicylic acid and the other
        acetic acid. Adding their mole vectors together would produce a bottle
        that was never made, at a mole-weighted temperature nothing was ever at,
        and it would erase precisely the difference the design exists to model.
        So the second one is stored beside the first under a suffixed name, and
        the caller is told what it got.
        """
        name = stock.name.strip() or "unnamed"
        final, n = name, 1
        while final in self.stocks:
            n += 1
            final = f"{name} ({n})"
        stored = replace(stock, name=final)
        self.stocks[final] = stored
        return stored

    def take(self, name: str, fraction: float = 1.0) -> Stock:
        """Draw a share off a bottle, depleting it. Returns what came out.

        The verb the PLAYER'S shelf needs and the one ``World.shelf``
        deliberately never sees -- see the module docstring. An emptied bottle is
        removed rather than left as a zero-mole entry: a bottle with nothing in
        it is not a thing on a shelf.
        """
        stock = self.get(name)
        taken, left = stock.split(fraction)
        if left.total > _FLOOR:
            self.stocks[name] = left
        else:
            del self.stocks[name]
        return taken

    def describe(self) -> str:
        if not self.stocks:
            return "the shelf is empty"
        return "\n".join(s.describe() for s in self.stocks.values())

    def to_dict(self) -> dict:
        return {name: s.to_dict() for name, s in self.stocks.items()}

    @classmethod
    def from_dict(cls, d: dict | None) -> Shelf:
        return cls(stocks={
            str(name): Stock.from_dict(blob) for name, blob in (d or {}).items()
        })
