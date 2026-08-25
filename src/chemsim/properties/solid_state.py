"""Layer 1 -- M6: a reaction that happens INSIDE a crystal.

``CaCO3(s) -> CaO(s) + CO2(g)`` is a lime kiln, and it is the first reaction in
this project that neither block of the RHS could write. It is not a liquid-phase
reaction, not a gas-phase one, and not a transport term either: matter changes
identity while staying a solid.

## THE QUESTION M6 HAD TO ANSWER FIRST: a third phase, or a second term?

``network/builder.PHASE_INDEX`` is ``{"liquid": 0, "gas": 1}`` and raises on
anything else, with a comment naming a solid-phase reaction as the case it was
written to refuse loudly rather than swallow. So the choice was to add
``"solid": 2`` and let mass action run on the solid block, or to write a term
next to precipitation. **It was decided by arithmetic, and the arithmetic says
mass action cannot express this reaction at all.**

A pure solid has **unit activity**. Its equilibrium is therefore a statement
about the GAS ALONE -- calcite and quicklime sitting together fix ``p_CO2`` at
``K(T)`` no matter how much of each is present. Write the pair as mass action on
the solid amounts and you get

    k_f n(CaCO3) = k_r n(CaO) p_CO2      ->      p_CO2 = (k_f/k_r) n_A / n_B

which sweeps from infinity to zero as the charge converts. That is not a
perturbation of the right answer, it is a different shape of answer: real
calcite either decomposes completely (``p < K``) or not at all (``p > K``), and
the mass-action form always stops somewhere in between.

⚠ **AND FORWARD-ONLY IS NOT A WAY OUT.** Measured on the curated data, a sealed
1 L flask charged with 0.1 mol of calcite:

    T / K     equilibrium conversion     forward-only
      900              0.12 %               100 %
     1000              1.23 %               100 %
     1100              7.95 %               100 %
     1200             37.32 %               100 %

and in an open flask under 1 bar of air the equilibrium says calcite does NOT
calcine below ~1150 K while forward-only calcines it at any temperature you are
willing to wait at. **The lime kiln's entire mechanic -- sweep the CO2 away or
it stalls -- is the part forward-only deletes.**

So a solid-phase reaction is a TERM, for exactly the reason
``PrecipitationArrays`` is one, and ``PHASE_INDEX`` keeps both of its entries.

## THE FORM

    flux = k(T) * [ units_fwd  -  units_rev * exp(lnQ - lnK) ]        mol/s

    k(T)  = A exp(-Ea/RT)                       1/s
    lnQ   = sum over GAS participants of nu_i ln p_i        (bar; solids are 1)
    lnK   = -(dH - T dS) / RT                   van 't Hoff from the 298 K pair

``units_fwd`` is how many formula units of the reactant side the solid block can
supply, ``units_rev`` the same for the product side -- the ``units`` bound
``PrecipitationArrays`` already uses, and gated by the same ``_avail`` so that an
empty block's Jacobian diagonal is bounded. First order in the amount present,
which is the constant-particle-count idealisation; real calcination is
shrinking-core (``n^(2/3)``), whose slope at zero is INFINITE and which this
project refuses for the reason ``SOLID_GATE_TIME`` records.

## ⚠ Ea IS NOT DECLARED. IT IS THE REACTION ENTHALPY, AND THAT IS A DERIVATION

An endothermic decomposition whose reverse is a gas landing on an oxide surface
has **no reverse barrier** -- there is nothing for the recombination to climb.
That fixes the forward barrier at ``dH``, which is also the floor
``detailed_balance`` already enforces everywhere else in this project ("an
elementary barrier cannot be lower than dH").

It has a consequence worth stating, because it is what makes the reverse
direction numerically safe. The reverse rate constant is

    k(T) exp(-lnK) = A exp((dH - Ea)/RT) exp(-dS/R)  =  A exp(-dS/R)

-- **independent of temperature**, once ``Ea = dH``. So a cold flask full of CO2
does not acquire an exploding recombination rate the way it would if the two
exponentials did not cancel. For calcination that constant is 4.26e-4 and for
the lime dehydration 3.15e-3, both in 1/(bar s).

And it is measured against reality: calcite's barrier comes out at 179.2 kJ/mol,
where the experimental activation energies quoted for calcination cluster at
170-200 kJ/mol. Nothing was fitted to get that.

## ⚠ WHAT IS A CLOCK AND WHAT IS PHYSICS

``DECOMPOSITION_A`` is the only free number here and it sets the SPEED ALONE:
the equilibrium is carried entirely by ``lnK``, which does not contain it. Two
runs at different ``A`` reach the same final state at different times, and
``validation/`` measures that rather than asserting it.

## ⚠ dCp = 0, STATED -- AND THE CORRECTION WAS BUILT AND REJECTED

Same van 't Hoff discipline as ``PrecipitationArrays.ln_Ksp``, and the same
honesty about it. The cost is measurable: the 1 bar decomposition temperature
comes out at 1118.2 K for calcite (literature ~1170 K) and 755.2 K for slaked
lime (~785 K), so this table runs its kilns roughly 30-50 K cool.

A ``dCp(T)`` correction was written and MEASURED before being dropped. It moves
calcite to 1107.7 K -- **worse by 10 K** -- and slaked lime to 774.9 K, better by
20 K. One row improves and one degrades, which is the signature of a correction
that is not consistently applied rather than of missing physics: a mineral's
``Cp_solid`` is a 298 K constant while a gas ``Cp`` here is a real cubic, so the
``dCp`` built from the pair is half-corrected. A half-correction that helps one
row and hurts another is worse than a stated omission, so the omission stays.

## THE BASIS, WHICH IS THE ONE THING THIS MODULE MUST NOT GET WRONG

``mineral_data`` is the SOLID basis and ``thermochemistry`` is the IDEAL-GAS
basis, and this module subtracts one from the other on purpose. That is legal
here and nowhere else in this project, because **every participant is in its own
standard state**: a crystal is a crystal, and a gas at 1 bar is an ideal gas at
1 bar. This is exactly the subtraction ``standard_state`` exists to prevent for a
LIQUID-phase reaction, where a species dissolved in a solvent is in neither.

Two guards keep it that way:

  * the gas half must be **curated**, not estimated. Joback prices CO2 by group
    additivity and would return a well-formed number with no business in a
    lattice subtraction, so an estimated source is refused by name.
  * the solid half must carry ``Cp_solid`` and ``Vm_solid``, because Layer 4
    asks every species in the solid block how much room it takes and how much
    heat it holds, and a lattice with no answer would borrow an ion's
    placeholder silently.
"""

from __future__ import annotations

from typing import NamedTuple

from chemsim.properties.mineral_data import MINERALS, MineralRecord

T_REF = 298.15

# 1/s. The forward pre-exponential of a solid decomposition -- a CLOCK, not a
# measurement, and the only free number in this module.
#
# ⚠ WHAT PINS IT, since this project does not accept a constant nobody chose.
# With ``Ea = dH`` derived above, ``A`` is fixed by one observable: how long a
# lime kiln takes. At 1200 K -- the temperature the catalog's own `lime-cycle`
# row runs its kiln at -- this value gives ``k = 1.59e-3 1/s``, i.e. a time
# constant of 630 s. A real kiln calcines a charge in tens of minutes. The same
# constant gives the lime dehydration a 20 s time constant at 900 K, which is
# likewise the right order for a hydroxide well past its decomposition point.
#
# ⚠ AND IT CANNOT MOVE AN EQUILIBRIUM, which is why one number covers both rows.
# It multiplies the whole flux, forward and reverse alike, so it divides out of
# ``flux = 0``. A wrong ``A`` moves the clock and nothing else -- the case this
# project's memory records as "rate errors are forgiven and only bad THERMO data
# snowballs". There is no source that would distinguish the two rows'
# pre-exponentials, so inventing two would be decoration.
DECOMPOSITION_A = 1.0e5

# Formation sources this module will subtract a lattice from. Anything else is
# an ESTIMATE, and a group-contribution number on one side of a lattice
# subtraction is the failure ``solubility_product`` records at 25-29 decades.
CURATED_FORMATION = ("experimental", "element reference state")


class UnpricedSolidReaction(ValueError):
    """A declared solid-state reaction that cannot be priced. Says why."""


class SolidStateReaction(NamedTuple):
    """One declared reaction between crystals, plus whatever gas it exchanges.

    ⚠ **DECLARED, NOT DISCOVERED, AND THAT IS FORCED.** Every other reaction in
    this project comes out of ``build_network`` applying a SMARTS rewrite to a
    molecular graph. A lattice is not a graph -- ``[Ca+2].[O-2]`` has no bonds to
    rewrite -- so there is no template that could generate this. It is a curated
    table for the same reason ``SOLUBILITY_PRODUCTS`` is one.

    ``solids`` and ``gases`` are signed: negative consumed, positive formed.
    """

    name: str
    solids: tuple           # ((mineral name, nu), ...)   nu signed
    gases: tuple            # ((canonical SMILES, nu), ...)   nu signed
    mechanism: str          # the catalog CLASS this row is, as a mechanism
    note: str


class PricedSolidReaction(NamedTuple):
    """A declaration plus the numbers Layer 4 integrates it with."""

    decl: SolidStateReaction
    dH: float               # J/mol at T_REF, + = endothermic
    dS: float               # J/(mol K) at T_REF, from the dH/dG pair
    Ea: float               # J/mol -- DERIVED: max(dH, 0), see the module docstring
    A: float                # 1/s
    minerals: tuple         # ((MineralRecord, nu), ...) resolved
    basis: str              # what the two halves came from


# ---------------------------------------------------------------------------
# The declarations
# ---------------------------------------------------------------------------
# ⚠ THE CATALOG CALLS BOTH OF THESE `calcination` AND M5's STANDARD SAYS THAT IS
# TWO MECHANISMS, NOT ONE. Its three rows are `CaCO3 -> CaO + CO2` twice
# (decarbonation) and `Al(OH)3 -> Al2O3 + H2O` once (dehydration), and crediting
# the class on the decarbonation alone would be the `deprotonation` mistake M1
# named. So both mechanisms are built.
#
# ⚠ The dehydration built here is NOT the catalog's own row. Bayer's
# `Al(OH)3 -> Al2O3 + H2O` needs two minerals that are not in `mineral_data` and
# would have to be curated first; `Ca(OH)2 -> CaO + H2O` is the same mechanism on
# species that already price, so the MECHANISM is covered honestly and the ROW is
# not claimed. `data/catalog` scores rows, and this one still reads uncovered.
#
# ⚠ AND `roasting` IS NOT HERE, which is a data refusal rather than an engine
# one. All five of its rows are `metal sulfide + O2 -> metal oxide + SO2`; of the
# five sulfides only ZnS prices, and NONE of the five oxides does. So zero rows
# are complete. The engine below would run them unchanged the day the oxides are
# curated -- and `mercury-from-cinnabar` would still need its own template,
# because HgO decomposes at roasting temperature and that row gives the METAL.
SOLID_STATE_REACTIONS: tuple[SolidStateReaction, ...] = (
    SolidStateReaction(
        name="calcination-decarbonation",
        solids=(("calcite", -1), ("quicklime", +1)),
        gases=(("O=C=O", +1),),
        mechanism="decarbonation",
        note=(
            "the lime kiln. `lime-cycle` step 1 and `solvay-process` step 5 are "
            "this same reaction. Reversible, and the reverse is what makes a "
            "sealed kiln stall at a few percent conversion"
        ),
    ),
    SolidStateReaction(
        name="calcination-dehydration",
        solids=(("slaked lime", -1), ("quicklime", +1)),
        gases=(("O", +1),),
        mechanism="dehydration",
        note=(
            "the OTHER mechanism inside the catalog's `calcination` class. Run "
            "backwards it is SLAKING -- `lime-cycle` step 2 -- and nothing "
            "declares that: it is this row's own reverse. ⚠ It is priced "
            "against water VAPOUR, so slaking with liquid water gets the "
            "condensation enthalpy from the vessel's own evaporation term "
            "rather than from here, which is why the two must not both carry it"
        ),
    ),
)


def price(
    decl: SolidStateReaction, thermo, T_ref: float = T_REF
) -> PricedSolidReaction:
    """Resolve one declaration against the two tables, or refuse and say why.

    ``thermo`` is a ``ThermochemistryProvider``. Only its GAS participants are
    asked of it; the solids come from ``mineral_data`` on the solid basis, and
    the module docstring argues why that subtraction is legal here.
    """
    dH = 0.0
    dG = 0.0
    resolved: list[tuple[MineralRecord, int]] = []
    sources: list[str] = []

    for name, nu in decl.solids:
        rec = MINERALS.get(name)
        if rec is None:
            raise UnpricedSolidReaction(
                f"{decl.name!r}: no mineral called {name!r} in mineral_data. "
                "Add it with tools/build_mineral_data.py -- a solid-state "
                "reaction is priced from the solid basis and there is no "
                "estimator standing behind that table."
            )
        if rec.Cp_solid is None or rec.Vm_solid is None:
            missing = [
                k for k, v in (("Cp_solid", rec.Cp_solid),
                               ("Vm_solid", rec.Vm_solid)) if v is None
            ]
            raise UnpricedSolidReaction(
                f"{decl.name!r}: {name!r} has no {' and no '.join(missing)}. "
                "Its formation pair is fine, but a crystal in the solid block "
                "also has to say how much room it takes and how much heat it "
                "holds -- Layer 4 asks that of every species, and borrowing an "
                "ion's placeholder for a mineral would be silent."
            )
        dH += nu * rec.Hf_solid * 1000.0
        dG += nu * rec.Gf_solid * 1000.0
        resolved.append((rec, nu))
        sources.append(f"{name}: {rec.source}")

    for smiles, nu in decl.gases:
        data = thermo.get(smiles)
        if not any(data.source.startswith(p) for p in CURATED_FORMATION):
            raise UnpricedSolidReaction(
                f"{decl.name!r}: the gas {smiles!r} is priced from "
                f"{data.source!r}, which is an ESTIMATE. A lattice subtraction "
                "puts a solid-basis formation value against a gas one and the "
                "whole answer is the difference; a group-contribution number on "
                "one side of it is the failure solubility_product measured at "
                "25-29 decades. Curate this species in "
                "properties/thermochemistry.py or drop the reaction."
            )
        dH += nu * data.Hf * 1000.0
        dG += nu * data.Gf * 1000.0
        sources.append(f"{smiles}: {data.source}")

    dS = (dH - dG) / T_ref
    return PricedSolidReaction(
        decl=decl,
        dH=dH,
        dS=dS,
        # ⚠ DERIVED, NOT DECLARED. See the module docstring: an endothermic
        # decomposition whose reverse is barrierless has Ea = dH exactly, which
        # is also the floor detailed_balance enforces on every other reaction
        # here. An EXOTHERMIC row as written would get Ea = 0 -- barrierless
        # forward -- and its reverse would carry the whole |dH|.
        Ea=max(dH, 0.0),
        A=DECOMPOSITION_A,
        minerals=tuple(resolved),
        basis="; ".join(sources),
    )


def decomposition_pressure(priced: PricedSolidReaction, T: float) -> float:
    """``K(T)`` in bar -- the gas pressure this pair of crystals sits at.

    For a one-gas decomposition that IS the equilibrium partial pressure, and it
    is the number the kiln mechanic is about: below it the solid is stable, above
    it the reaction runs. Reported rather than only integrated, so a route can be
    checked against it without running a vessel.
    """
    import math

    from chemsim.constants import R

    return math.exp(-(priced.dH - T * priced.dS) / (R * T))


def lattice_species() -> frozenset:
    """Every mineral SMILES a solid-state reaction in this table touches.

    What a caller charges into a flask. Kept as a function rather than a
    constant so it cannot go stale against the declarations above.
    """
    return frozenset(
        MINERALS[name].lattice
        for decl in SOLID_STATE_REACTIONS
        for name, _ in decl.solids
        if name in MINERALS
    )
