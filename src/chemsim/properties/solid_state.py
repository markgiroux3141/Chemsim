"""Layer 1 -- M6: a reaction that happens INSIDE a crystal.

⚠⚠ **S9: THAT TITLE IS NO LONGER THE WHOLE OF IT, AND THE CORRECTION IS THE MOST
USEFUL THING IN THIS FILE.** M6 split the solid mechanics along *inside a crystal
/ at its surface* and put a refusal in each direction. S4 had already broken that
line by turning a crystal ENTIRELY into gas, and S9 broke it the rest of the way:
``MO(s) + CO(g) -> M(s) + CO2(g)`` is a gas arriving at a surface and it is a row
of THIS table. **The line that actually holds is REVERSIBLE OR NOT.** An affinity
form's rate-law exponents are fixed at the stoichiometric coefficients by
detailed balance; a mass-action term can DECLARE them. So:

    reversible, exponents forced       -> here (this file, SolidStateArrays)
    irreversible, orders declarable    -> properties/surface.py, SurfaceArrays

which is this project's standing invariant *a declared rate order may never be
reversible*, arriving as a module boundary. What this table now holds is **a
crystal in equilibrium with a headspace**, evolving a gas or consuming one or
neither. See §S9 below.

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

⚠ THE OTHER HALF OF THE QUESTION WAS ANSWERED LATER AND ALSO CAME BACK "A TERM".
M6 predicted that the gas-CONSUMING case -- roasting, and a solid catalyst --
would be the third ``PHASE_INDEX`` entry, because it genuinely IS mass action.
It is a term too, for a reason M6 did not have: the phase label carries a
STANDARD STATE, worth 2.6e10 in K at 500 K. See ``properties/surface.py``.

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

## ⚠⚠ S4: A ROW MAY HAVE NO SOLID PRODUCT, AND THAT COST A BOUND

``2 HgO(s) -> 2 Hg(g) + O2(g)`` is the fifth row here and the first whose
products are ALL GAS -- mercury boils at 629.8 K and its retort runs at 900. The
four rows above it turn one crystal into another, so ``units_rev`` (how many
formula units of the PRODUCT side the solid block can supply) always had
something to take a minimum over. Over an empty side that minimum is ``+inf``,
and the RHS multiplies it by a negative affinity.

⚠ **Measured before it was fixed, not predicted: a sealed 1 L retort holding
0.5 mol of montroydite at 900 K raised ``array must not contain infs or NaNs``**
the moment ``Q`` crossed ``K`` -- which it does at that charge, because ``ln K``
is only +9.2 there. At 0.05 mol it never crosses and the run is clean, so the
bug had a charge threshold as well as a temperature one.

**Infinity was the wrong bound rather than a bound needing softening**, and the
existing rows say what the right one is: calcination's reverse is bounded by
``n(CaO)`` -- the SEED the carbonate grows on -- and not by the CO2 pressure,
which lives in ``Q``. This engine cannot nucleate a solid from nothing (S3 named
that gap). So a row with no solid product deposits onto its own REACTANT crystal,
and ``units_rev`` falls back to ``units_fwd``: the equilibrium stays ``Q = K``
because the factor is common to both directions, and an exhausted charge stops
the reaction both ways -- mercury vapour and oxygen in a cold flask cannot make
montroydite again once the last of it is gone. That is the nucleation gap stated,
not worked around. ``SolidStateArrays.units`` carries the argument.

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

``RECOMBINATION_A`` is the only free number here and it sets the SPEED ALONE:
the equilibrium is carried entirely by ``lnK``, which does not contain it. Two
runs at different ``A0`` reach the same final state at different times.

⚠ **It is the REVERSE pre-exponential, not the forward one, and that inversion
is the correction a second row forced.** Declared forward, one constant makes a
lime kiln work and leaves green vitriol thirteen decades too slow -- measured,
0.00% conversion in 20,000 s at every temperature its thermodynamics allow.
The forward constant is ``A0 exp(dS/R)``: the entropy of making gas belongs in
the pre-exponential, not in a constant shared by rows that make different
amounts of it. The whole argument is at ``RECOMBINATION_A``.

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

## ⚠⚠ §S9 -- WHAT CHANGED, AND IT IS TWO THINGS

**1. THE GAS SIDE IS TWO ONE-SIDED PRODUCTS AND NOT A QUOTIENT.**

    net = k_f * prod(p ** consumed_gas)  -  k_r * prod(p ** formed_gas)

is ``P_react (k_f - k_r Q)`` algebraically, so it has the SAME root and the same
equilibrium, and it never divides -- which is the whole of the "reversible
solid-gas term" S8 named as this plan's most valuable unscoped item. Three rows
consume a gas now: two CO reductions and the Boudouard reaction. ⚠ **The five
pre-S9 rows are BIT-IDENTICAL**, because ``p ** 0`` is exactly 1.0 for every
finite p (zero included) and ``formed_gas`` IS ``nu_gas`` when nothing is
consumed. Verified against ``examples/lime_cycle.py`` and
``examples/mercury_retort.py`` byte for byte, not by argument.

**2. AN EXOTHERMIC ROW MUST DECLARE ITS FORWARD KINETICS.** ``Ea = max(dH, 0)``
is a derivation about an endothermic decomposition whose reverse is barrierless.
On an exothermic row it returns **zero**, i.e. a rate law with no temperature in
it: thermite comes out at 4.15e-6 1/s -- a 2.8-day reaction that goes just as
fast in a cold jar as in a furnace -- and a CO reduction at 9.70e-4 1/(bar s).
Neither is a slow reaction; both are reactions with the wrong SHAPE. So such a
row declares ``Ea`` and ``A`` (both or neither) and still gets its reverse by
detailed balance, and a declared ``Ea`` below ``dH`` is refused because
``SolidStateArrays``' ``max(Ea - dH, 0)`` would clip and silently break
``k_f/k_r = K``.

⚠ **WHAT S9 DID NOT NEED.** ``zincite-carbothermic-reduction`` and
``boudouard-gasification`` are ENDOTHERMIC, so M6's derived pair is right for
both, and the zinc retort comes out with dG = 0 at **1264.3 K** against a real
Belgian retort's 1200-1300 with nothing fitted. The queue had spent a session
believing that class was blocked because it had priced ``ZnO + CO -> Zn + CO2``
(uphill at +63.3 kJ/mol) instead of the catalog's own carbon row. **Read the row,
not the class name.**

⚠ **AND WHAT IS STILL NOT EXPRESSIBLE.** A lattice may react and may never boil,
so the retort's zinc stays SOLID (a real one distils it off at 1180 K, which is
product removal) and nothing caps thermite's temperature (a real one stops near
3135 K because the iron boils). Those are the same limitation, stated twice.
"""

from __future__ import annotations

import math
from typing import NamedTuple

from chemsim.constants import R
from chemsim.properties.mineral_data import MINERALS, MineralRecord

T_REF = 298.15

# 1/(bar s). ⚠⚠ THIS IS THE **REVERSE** PRE-EXPONENTIAL, WHICH IS THE OPPOSITE OF
# THIS PROJECT'S USUAL DIRECTION, AND THE INVERSION IS THE WHOLE POINT.
#
# Everywhere else here a template declares FORWARD kinetics and the reverse is
# derived by detailed balance. For a solid decomposition that is exactly backwards,
# and the first version of this module got it wrong in a way that only showed up on
# the second row:
#
#   * declared as a FORWARD constant, ``A = 1e5 1/s``, calcite calcines in 630 s at
#     1200 K -- a real kiln -- and **green vitriol never decomposes at all.** Its
#     ``dH`` is 340 kJ/mol against calcite's 179, so with ``Ea = dH`` its rate
#     constant at 1000 K is 1.7e-13 1/s. Measured: 0.00% conversion in 20,000 s at
#     every temperature from 700 to 1000 K, where a real retort is done in minutes.
#     **Thirteen decades of clock error**, on a row whose thermodynamics were
#     exactly right.
#
# ⚠ **THE MISSING PHYSICS IS THE ENTROPY OF MAKING GAS, AND FOLDING IT INTO A
# CONSTANT IS THE MISTAKE.** A decomposition that releases two moles of gas has an
# enormous activation entropy; one that releases one has much less. With the
# transition state taken to resemble the products -- which is the same late-TS
# assumption that makes the reverse barrierless and fixes ``Ea = dH`` -- that
# entropy is ``dS`` itself, so the forward pre-exponential is
#
#     A_fwd = A0 * exp(dS / R)
#
# and ``A0`` is what is left over. **``A0`` is the REVERSE constant**, because
#
#     k_rev = A_fwd exp(-(Ea - dH)/RT) exp(-dS/R) = A0     exactly, at every T.
#
# ⚠ AND THAT IS WHY ONE NUMBER CAN COVER EVERY ROW. ``A0`` is the pre-exponential
# of a single elementary event -- a gas molecule arriving at a crystal surface and
# reacting, with no barrier to climb -- and that event is the SAME event for
# calcite, for green vitriol and for baking soda. The forward direction is not one
# event: it is that event run backwards against a different amount of gas-making
# entropy each time, which is precisely what ``exp(dS/R)`` carries.
#
# ⚠ WHAT PINS THE VALUE. Unchanged from the first version's calibration, so that
# nothing measured for the lime cycle moves: it is the reverse constant that a
# 630 s calcination time constant at 1200 K implies. What changed is that it is now
# DECLARED there rather than derived there, and the four rows come out:
#
#     row                                   dH/kJ   dS/J/K   tau at
#     calcination-decarbonation             179.2    160.3   622 s at 1200 K
#     calcination-dehydration               108.5    143.6   149 s at  900 K
#     sulfate-thermal-decomposition         340.0    377.6    26 s at 1000 K
#     bicarbonate-thermal-decomposition     135.6    334.4    44 s at  450 K
#
# A lime kiln in ten minutes, a red-hot retort of green vitriol in half a minute,
# and baking soda in a 450 K calciner in under a minute -- which is the catalog's
# own `calciner, 450 K`. **Three of those four are timescales nothing was
# calibrated against**, and they came out right because the entropy is no longer
# hiding in the constant.
#
# ⚠ IT STILL CANNOT MOVE AN EQUILIBRIUM. ``A0`` multiplies the whole flux, forward
# and reverse alike, so it divides out of ``flux = 0``. A wrong ``A0`` moves the
# clock and nothing else -- the case this project's memory records as "rate errors
# are forgiven and only bad THERMO data snowballs".
#
# ⚠ AND THE FORWARD CONSTANT IS ROW-DEPENDENT AND CAN BE LARGE, stated rather
# than capped. The five rows run from 1.4e4 to 1.9e18 1/s, and ``A0`` is the
# same number in all of them -- the spread is ``exp(dS/R)``, i.e. how much gas
# each row makes.
#
# ⚠⚠ S4 MEASURED WHAT THAT COSTS AND THE ANSWER IS INSIDE THE RHS's CLAMP.
# ``validation/rate_ceiling.py`` now reads this table (it never used to -- these
# rows are not ``Reaction`` objects, so its first two panels cannot see them),
# and it prints the temperature at which each row's ``k_f`` crosses the
# unimolecular ceiling of 1e14 1/s:
#
#     oxide-thermal-decomposition        3710 K     <- inside T_MAX = 5000 K
#     sulfate-thermal-decomposition      7543 K
#     bicarbonate-thermal-decomposition 75136 K
#     the two calcination rows            never
#
# STILL NOT GUARDED, and the reason is the one above rather than an omission:
# ``A0`` multiplies the whole affinity flux, forward and reverse alike, so it
# divides out of ``flux = 0``. An over-ceiling forward constant moves a CLOCK
# and cannot move an equilibrium -- the case this project's memory records as
# "rate errors are forgiven and only bad THERMO data snowballs". The mercury
# retort runs at 900 K, 2810 K below its own crossing.
RECOMBINATION_A = 4.259e-4

# ---------------------------------------------------------------------------
# S9 -- THE TWO DECLARED FORWARD PAIRS, AND WHY THEY EXIST AT ALL
# ---------------------------------------------------------------------------
# ``RECOMBINATION_A`` above is the reverse constant of a DECOMPOSITION, and with
# ``Ea = max(dH, 0)`` it covers every endothermic row here -- including S9's own
# two endothermic additions, which declare nothing:
#
#     zincite + C   -> zinc + CO      dH +240.0 kJ   A 3.50e6 1/s      tau  258 s at 1400 K
#     C + CO2       -> 2 CO           dH +172.5      A 6.40e5 1/(bar s) tau   13 s at 1300 K
#
# ⚠ AN EXOTHERMIC ROW CANNOT USE IT, and the measurement is what forces these
# two constants rather than a preference. ``max(dH, 0)`` is ZERO for an
# exothermic reaction: a barrierless forward step with NO TEMPERATURE DEPENDENCE
# AT ALL. Measured on the two families S9 adds:
#
#     thermite on the derived pair       4.15e-6 1/s        a 2.8-DAY reaction,
#                                                           and just as fast cold
#     tenorite + CO on the derived pair  9.69e-4 1/(bar s)  a furnace whose heat
#                                                           changes nothing
#
# Neither is a slow reaction; both are reactions with the wrong SHAPE. Thermite's
# entire mechanic is that it sits in a jar until something ignites it, and a
# smelter's is that it needs a furnace. So an exothermic row declares its forward
# pair and the reverse still comes from detailed balance -- the direction every
# ``ReactionTemplate`` in this project already declares in.

# J/mol. Apparent barrier for a CO molecule arriving at a metal-oxide surface,
# taking a lattice oxygen and leaving as CO2. Reported values for the CO
# reduction of CuO, PbO, NiO and Fe2O3 cluster in a 60-100 kJ/mol band (wider
# for Fe2O3, and always partly transport); 80 is the middle, and it is SHARED
# across the family, which is the same claim ``surface.ROASTING_EA`` makes and
# the same limitation: the rows then differ only in their thermodynamics.
#
# ⚠ IT MUST CLEAR ``max(dH, 0)`` FOR EVERY ROW IT IS USED ON, and ``price``
# checks that. The tightest case is not a declared row at all: ``zincite + CO ->
# zinc + CO2`` is ENDOTHERMIC at +67.5 kJ/mol, so 80 would only just clear it --
# which is one more reason the zinc route here is the CARBON one.
REDUCTION_EA = 80_000.0

# 1/(bar s) per formula unit of oxide. ⚠ WHAT PINS IT: a smelter's own residence
# time, not a fit. With the affinity form's forward branch
#
#     tau = 1 / (k_f p_CO)
#
# a lead blast furnace or a copper converter takes the oxide down in ten minutes
# of contact with a roughly 1 bar CO stream, so tau = 600 s at 1400 K needs
# k_f = 1.667e-3 1/(bar s), and at ``REDUCTION_EA`` that is A = 1.609.
#
# ⚠⚠ AND THE UNITS ARE WHAT MAKE THE VALUE DEFENSIBLE, which is this project's
# standing rule about a pre-exponential. The ceiling for a rate written per
# formula unit of solid per bar is not a collision frequency in solution -- it is
# the HERTZ-KNUDSEN arrival rate at a crystal face. CO at 1 bar and 1400 K
# arrives at 2209 mol/(m2 s); tenorite's molar volume over a 100 um particle is
# 0.756 m2/mol of specific surface, so no rate law of this shape can exceed
# 1.67e3 1/(bar s). **A is 9.6e-4 of that** -- inside it by three decades, and
# stated rather than assumed. (A 1 mm bed grain moves the bound to 1.67e2 and A
# to 9.6e-3 of it; the conclusion is unchanged over the whole range a furnace
# charges.)
REDUCTION_A = 1.609

# J/mol. Thermite. ⚠ THIS IS AN IGNITION BARRIER AND IT IS THE MECHANIC, not a
# clock: a jar of iron oxide and aluminium powder is indefinitely stable and a
# spark takes it to 3000 K. DTA studies of the Fe2O3/Al reaction report apparent
# activation energies of roughly 230-320 kJ/mol; 250 is inside that band.
THERMITE_EA = 250_000.0

# 1/s. ⚠ PINNED ON THE IGNITION TEMPERATURE, which is the only number about
# thermite anybody quotes: the mixture lights at about 1200 K, so tau = 1 s
# there, so A = exp(Ea / R / 1200). What comes out of that single pin is a
# column nothing was fitted to:
#
#     298 K   8.2e+32 s   -- a jar that keeps for longer than the universe
#     600 K   7.6e+10 s
#     933 K   1.3e+03 s   -- and this is where ALUMINIUM MELTS, which is the
#                            trigger every account of thermite names
#    1200 K   1.0e+00 s   -- pinned
#    1500 K   6.7e-03 s
#
# ⚠ A = 7.62e10 1/s is three and a half decades under this project's
# unimolecular collision ceiling of 1e14, and ``validation/rate_ceiling.py``
# reads this table, so the row is reported rather than asserted.
THERMITE_A = 7.62e10

# Formation sources this module will subtract a lattice from. Anything else is
# an ESTIMATE, and a group-contribution number on one side of a lattice
# subtraction is the failure ``solubility_product`` records at 25-29 decades.
#
# ⚠⚠ THE THIRD PREFIX IS HERE BECAUSE THIS GUARD FALSELY REFUSED CRC's OWN
# MEASUREMENT, and the near-miss is worth keeping: it is a PREFIX MATCH ON A
# PROVENANCE STRING, so what it actually tests is how a sentence begins. A
# GASEOUS element reference state says "element reference state (gaseous)" and
# passes; a CONDENSED one -- mercury, bromine, iodine, S8 -- says "Hf and S0
# both from CRC via chemicals 1.5.2; Gf DERIVED ...", which is the same CRC row
# arriving through ``element_data``'s derivation and was being called an
# estimate. Measured in S4, on ``[Hg]``, and it would have refused a row
# evolving Br2 or I2 identically.
#
# ⚠ The weakness is the mechanism, not the list: a tier belongs in the RECORD
# and this reads it out of prose. Left as a list because widening it is a
# one-line data change while moving the tier into ``ThermoData`` reaches every
# provider in Layer 1 -- stated, so the next row that trips it knows why.
CURATED_FORMATION = (
    "experimental",
    "element reference state",
    "Hf and S0 both from",
)


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

    ⚠⚠ **S9 -- ``Ea`` AND ``A`` MAY BE DECLARED, AND FOR AN EXOTHERMIC ROW THEY
    MUST BE.** ``None`` keeps M6's derivation (``Ea = max(dH, 0)`` and
    ``A = RECOMBINATION_A exp(dS/R)``), which is right for every row that
    DECOMPOSES: its reverse is a gas landing on a crystal with nothing to climb,
    so the forward barrier IS the enthalpy. Write an EXOTHERMIC row and that
    derivation says ``Ea = 0`` -- a barrierless reaction with no temperature
    dependence at all, which for thermite means a mixture that reacts in a cold
    jar and for a CO reduction means a furnace whose heat does nothing. The
    numbers are in the module docstring. So an exothermic row declares its
    forward pair and gets its reverse by detailed balance, which is what every
    ``ReactionTemplate`` in this project already does; ``price`` refuses a
    declaration with ``Ea < max(dH, 0)``, because the ``max`` in ``Ea_rev``
    would otherwise silently break ``k_f/k_r = K``.

    ⚠ A row may declare BOTH or NEITHER. Half a declaration is refused: ``A``
    without ``Ea`` is a pre-exponential belonging to a barrier nobody wrote
    down, and ``Ea`` without ``A`` gets ``RECOMBINATION_A exp(dS/R)`` -- a
    constant calibrated as the reverse of a decomposition, which is not this
    row's elementary event.
    """

    name: str
    solids: tuple           # ((mineral name, nu), ...)   nu signed
    gases: tuple            # ((canonical SMILES, nu), ...)   nu signed
    mechanism: str          # the catalog CLASS this row is, as a mechanism
    note: str
    Ea: float | None = None  # J/mol -- None DERIVES max(dH, 0); see above
    A: float | None = None   # 1/(bar^n s) -- None DERIVES from RECOMBINATION_A


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
# ⚠⚠ AND `roasting` IS STILL NOT HERE, BUT S9 CHANGED THE REASON. This comment
# read "a gas REACTANT puts its pressure in the denominator of Q, so `price`
# refuses such a declaration by name". That refusal is GONE -- the quotient is
# split into two one-sided products and three rows below consume a gas. **What
# keeps roasting in `properties/surface.py` is the ORDER**: an affinity form's
# exponents are fixed at the stoichiometric coefficients by detailed balance, and
# `2 ZnS + 3 O2 -> 2 ZnO + 2 SO2` taken third order in oxygen stalls
# asymptotically as the atmosphere is consumed. That is this project's standing
# invariant "a declared rate order may never be reversible", from the other side.
#
# ⚠⚠ THE ONE THING THIS COMMENT USED TO SAY THAT S4 REFUTED: it read
# "`mercury-from-cinnabar` would still need its own template, because HgO
# decomposes at roasting temperature and that row gives the METAL." It needs no
# template. The decomposition is an ORDINARY ROW of this table -- the last one
# below -- and the row falls out of that row and the roasting one sharing a
# crystal. The reason the oxide decomposes at roasting heat is not an obstacle
# to expressing the route; it IS the route.
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
    # ⚠ CHAIN 2's SEED, AND ITS PRODUCT IS NOT WHAT THE CATALOG ROW SAYS.
    # `vitriol-distillation` step 1 reads `iron-ii-sulfate -> iron-ii-OXIDE +
    # sulfur-trioxide`, which balances and is not the reaction. FeO does not
    # survive red heat; anhydrous green vitriol gives HEMATITE with half its
    # sulfur reduced. So this row is written as the chemistry rather than as the
    # catalog entry, and `mineral_data` records that FeO was tried and refused --
    # on the crystal Cps, which CRC does not tabulate for it.
    #
    # ⚠ AND IT IS THIS PROJECT'S FIRST REACTION WITH TWO GAS PRODUCTS, which
    # makes `K` carry units of bar^2 and changes what "hot enough" means. See
    # `threshold_temperature`.
    SolidStateReaction(
        name="sulfate-thermal-decomposition",
        solids=(("green vitriol", -2), ("hematite", +1)),
        gases=(("O=S=O", +1), ("O=S(=O)=O", +1)),
        mechanism="sulfate-thermal-decomposition",
        note=(
            "the dry distillation of green vitriol -- where oil of vitriol came "
            "from before the lead chamber. The SO3 half is what a receiver of "
            "water turns into sulfuric acid; the SO2 half is the reduction that "
            "makes the residue hematite rather than FeO"
        ),
    ),
    SolidStateReaction(
        name="bicarbonate-thermal-decomposition",
        solids=(("nahcolite", -2), ("soda ash", +1)),
        gases=(("O=C=O", +1), ("O", +1)),
        mechanism="bicarbonate-thermal-decomposition",
        note=(
            "`solvay-process` step 3, and the reason a cake rises. Two gases "
            "again, and it goes at 392 K against the catalog's own 450 K "
            "calciner -- the closest agreement of any row here"
        ),
    ),
    # ⚠⚠ S4 -- THE FIRST ROW HERE WITH NO SOLID PRODUCT AT ALL, and that is a
    # structural first rather than a bigger one of the same thing. Every row
    # above turns one crystal into another; this one turns a crystal ENTIRELY
    # into gas, because mercury boils at 629.8 K and this runs at 900.
    #
    # ⚠ IT BREAKS ``SolidStateArrays.units`` AS THAT FUNCTION WAS WRITTEN, and
    # the break is measured, not predicted: ``units_rev`` is a minimum over the
    # solids FORMED, and the minimum of an empty set was ``np.inf``. The reverse
    # flux is ``net * units_rev``, so the instant the affinity turns negative --
    # which happens in any sealed retort, because ln K is only +9.2 at 900 K --
    # the term returns -inf and BDF gets a NaN Jacobian. See ``units`` for the
    # fix and for why the honest bound is not infinity.
    #
    # ⚠ AND THE MECHANISM NAME IS NOT A CATALOG CLASS ON ITS OWN. No route step
    # reads `mercury-oxide -> mercury + oxygen`; this is one HALF of
    # `mercury-from-cinnabar`'s single row, whose other half is
    # `cinnabar-roasting` in properties/surface.py. The class it helps cover is
    # `roasting-to-metal`, and it is covered by the two of them TOGETHER --
    # nothing declares the row itself. See validation/catalog_coverage.py.
    SolidStateReaction(
        name="oxide-thermal-decomposition",
        solids=(("montroydite", -2),),
        gases=(("[Hg]", +2), ("O=O", +1)),
        mechanism="oxide-thermal-decomposition",
        note=(
            "`mercury-from-cinnabar`'s second half, and the reaction oxygen "
            "was discovered by. HgO does not survive the retort that makes it "
            "-- it goes at 689 K against the room and the roast runs at 900 -- "
            "so a cinnabar roast never accumulates the oxide it makes, and what "
            "comes over is the METAL. Nothing declares that: it is this row and "
            "`cinnabar-roasting` sharing one crystal in the solid block"
        ),
    ),
    # -----------------------------------------------------------------------
    # S9 -- THE SMELTER. Five rows, and the first two of them are the first
    # reactions in this table that CONSUME a gas.
    # -----------------------------------------------------------------------
    # ⚠⚠ THE FIRST TWO ROWS ARE WHAT THE OLD REFUSAL REFUSED. `gas-solid-
    # reduction` sat on the work queue as its only +2 for a whole milestone,
    # blocked on "a REVERSIBLE solid-gas term" -- and the term was this one all
    # along, one algebraic rearrangement short. See the module docstring §S9.
    #
    # ⚠ AND THEY ARE REVERSIBLE FOR A REASON A BLAST FURNACE IS BUILT AROUND:
    # ln K is only +10.90 and +7.24 at their own furnace temperatures, so the
    # top gas keeps carbon monoxide in it. `surface.LN_K_IRREVERSIBLE` refused
    # all four catalog rows on exactly that reading and was RIGHT to -- an
    # irreversible term cannot hold them. This one can.
    SolidStateReaction(
        name="tenorite-carbon-monoxide-reduction",
        solids=(("tenorite", -1), ("copper", +1)),
        gases=(("[C-]#[O+]", -1), ("O=C=O", +1)),
        mechanism="gas-solid-reduction",
        note=(
            "`copper-smelting` step 2 -- the converter, and the second half of "
            "the first ore-to-metal chain in this project that is not mercury. "
            "`covellite-roasting` in properties/surface.py makes the tenorite "
            "this consumes and neither declaration mentions the other"
        ),
        Ea=REDUCTION_EA,
        A=REDUCTION_A,
    ),
    SolidStateReaction(
        name="litharge-carbon-monoxide-reduction",
        solids=(("litharge", -1), ("lead", +1)),
        gases=(("[C-]#[O+]", -1), ("O=C=O", +1)),
        mechanism="gas-solid-reduction",
        note=(
            "`lead-smelting` step 2. `galena-roasting` makes the litharge, so "
            "chain 2's lead chamber now has a route to its own vessel metal "
            "from galena in two declared reactions and no template"
        ),
        Ea=REDUCTION_EA,
        A=REDUCTION_A,
    ),
    # ⚠⚠ NO DECLARED KINETICS, AND THAT IS THE INTERESTING PART: this row is
    # ENDOTHERMIC (+240.0 kJ/mol), so M6's derivation is exactly right for it and
    # the retort comes out at tau = 258 s at the catalog's own 1400 K. The
    # reverse -- CO landing on hot zinc -- is the barrierless event
    # ``RECOMBINATION_A`` was calibrated as.
    #
    # ⚠ AND THE ZINC IS A SOLID HERE WHILE A REAL RETORT DISTILS IT OFF AT
    # 1180 K. That is a STATED limitation and not a hidden one: ``mineral_data``
    # holds zinc as a lattice, ``thermo.get("[Zn]")`` refuses the monatomic
    # vapour as a bare element, and a lattice in this engine may react and may
    # never boil. What is lost is the product removal that pulls the reaction
    # over; what is kept is the reaction's own thermodynamics, which do not need
    # it -- dG = 0 at 1264 K against a real retort's 1200-1300, and ln K is
    # +2.21 at 1400 K, so it runs against one bar of its own CO without help.
    SolidStateReaction(
        name="zincite-carbothermic-reduction",
        solids=(("zincite", -1), ("carbon-graphite", -1), ("zinc", +1)),
        gases=(("[C-]#[O+]", +1),),
        mechanism="carbothermic-oxide-reduction",
        note=(
            "`zinc-smelting` step 2 -- the Belgian retort, and the third "
            "ore-to-metal chain, with `sphalerite-roasting` making the zincite. "
            "⚠ It needs no gas REACTANT and no declared kinetics: it is an "
            "ordinary row of this table that nobody had written, and the only "
            "reason it was blocked is that the queue priced the CO route "
            "(uphill at +63.3 kJ/mol) instead of the catalog's own carbon one"
        ),
    ),
    # ⚠⚠ THE ROW THAT MAKES THE OTHER TWO INTO A FURNACE, and it is here for the
    # MECHANIC rather than for a route -- `blast-furnace` is still blocked on
    # `slagging` and on an FeO ``mineral_data`` refuses. What it buys is that a
    # flask given CARBON and a trace of CO2 regenerates its own reductant:
    #
    #     C + CO2 -> 2 CO        this row, reversible, ln K +5.18 at 1300 K
    #     CuO + CO -> Cu + CO2   the row above, which hands the CO2 back
    #
    # so the carbon monoxide is a CARRIER and the carbon is the reagent. Nothing
    # declares that; it is two rows sharing a headspace, which is the same shape
    # as the mercury retort's two rows sharing a crystal.
    #
    # ⚠ ENDOTHERMIC (+172.5 kJ/mol) and therefore on the derived pair again --
    # and its reverse, 2 CO landing on carbon to lay down soot, is the classic
    # Boudouard deposition that really is barrierless-ish. dG = 0 at 981.6 K,
    # which is the temperature every ironmaking text puts the Boudouard reversal
    # at.
    SolidStateReaction(
        name="boudouard-gasification",
        solids=(("carbon-graphite", -1),),
        gases=(("O=C=O", -1), ("[C-]#[O+]", +2)),
        mechanism="boudouard",
        note=(
            "`blast-furnace` step 2, and the reason a furnace is charged with "
            "coke rather than carbon monoxide. ⚠ Its reverse is what puts soot "
            "in a cool flue, and it is this row run backwards -- nothing "
            "declares that either"
        ),
    ),
    # ⚠⚠ THE FIRST ROW HERE WITH NO GAS AT ALL, and it is a structural first
    # rather than a bigger one of the same thing. Every row above exchanges at
    # least one gas, so ``Q`` always had something in it; here both one-sided
    # pressure products are empty, i.e. exactly 1.0, and the affinity collapses
    # to ``k_f - k_r`` -- a constant. That is CORRECT and it is what a
    # condensed-phase reaction with no gas participant means: there is no
    # quotient to move, so the row is effectively irreversible at ln K +29.5 and
    # runs to completion.
    #
    # ⚠ AND IT IS THE ROW THAT FORCED THE DECLARED PAIR. dH is -851.5 kJ/mol, so
    # ``max(dH, 0)`` is zero: on the derived pair thermite is a 2.8-day reaction
    # that runs at the same speed in a cold jar as in a furnace. See
    # ``THERMITE_A`` for what one pin on the ignition temperature buys instead.
    SolidStateReaction(
        name="metallothermic-reduction",
        solids=(("hematite", -1), ("aluminium", -2),
                ("iron", +2), ("corundum", +1)),
        gases=(),
        mechanism="metallothermic-reduction",
        note=(
            "`thermite`, the whole route in one row. Four crystals and no gas, "
            "which makes it the only row here whose affinity has no quotient in "
            "it at all -- and the only one whose mechanic is entirely in its "
            "BARRIER: 8e32 s at room temperature against 1 s at 1200 K"
        ),
        Ea=THERMITE_EA,
        A=THERMITE_A,
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

    # ⚠ S4. A row with NO crystal on either side is the one case
    # ``SolidStateArrays.units`` cannot bound at all -- both of its fallbacks
    # are empty, so both directions return +inf and the flux is a NaN. It is
    # also not a solid-state reaction: with every participant a gas, the
    # kinetics kernel is what should be running it, on the ideal-gas basis
    # rather than on a lattice subtraction. Refused here, where the declaration
    # is, rather than left for the arrays to discover as an integrator failure.
    if not decl.solids:
        raise UnpricedSolidReaction(
            f"{decl.name!r}: no solid participants at all. A reaction that "
            "happens INSIDE a crystal needs a crystal; with every species in "
            "the gas block this is an ordinary gas-phase reaction and belongs "
            "in reactions/library.py, priced on the ideal-gas basis. (The "
            "arrays cannot bound such a row either: units() takes a minimum "
            "over each side's solids and both sides would be empty.)"
        )

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

    # ⚠⚠ S9 -- HALF A KINETIC DECLARATION IS REFUSED. Both or neither: ``A``
    # alone is a pre-exponential for a barrier nobody wrote down, and ``Ea``
    # alone would take ``RECOMBINATION_A exp(dS/R)``, a constant calibrated as
    # the REVERSE of a decomposition and not this row's elementary event.
    if (decl.Ea is None) != (decl.A is None):
        given, missing = (("Ea", "A") if decl.A is None else ("A", "Ea"))
        raise UnpricedSolidReaction(
            f"{decl.name!r}: declares {given} and not {missing}. A row here "
            "either takes M6's derived pair (Ea = max(dH, 0) with "
            "A = RECOMBINATION_A exp(dS/R), which is the barrierless-reverse "
            "decomposition) or declares BOTH halves of its own forward "
            "kinetics. Half of one silently mixes a declared barrier with a "
            "pre-exponential fitted to a different elementary event."
        )

    if decl.Ea is None:
        # ⚠ DERIVED, NOT DECLARED, AND THIS IS THE ENDOTHERMIC-DECOMPOSITION
        # CASE ONLY. See the module docstring: a decomposition whose reverse is
        # barrierless has Ea = dH exactly, which is also the floor
        # detailed_balance enforces on every other reaction here.
        Ea = max(dH, 0.0)
        # DERIVED from the reverse constant and this row's own entropy -- see
        # RECOMBINATION_A. ``math.exp(dS/R)`` is the entropy of making gas, and
        # it is the difference between a retort that works and one that is
        # thirteen decades too slow.
        A = RECOMBINATION_A * math.exp(dS / R)
        # ⚠ AN EXOTHERMIC ROW CANNOT TAKE THE DERIVATION, and S9 measured what
        # it costs rather than assuming it: ``max(dH, 0)`` is ZERO, so the
        # forward rate has no temperature dependence at all. Thermite comes out
        # at 4.15e-6 1/s -- a 2.8-DAY reaction that runs just as fast in a cold
        # jar as in a furnace, i.e. no ignition -- and a CO reduction at
        # 9.7e-4 1/(bar s) with a furnace whose heat does nothing. Refused
        # here, at the declaration, rather than integrated.
        if dH < 0.0:
            raise UnpricedSolidReaction(
                f"{decl.name!r}: dH = {dH / 1000.0:.2f} kJ/mol is EXOTHERMIC "
                "and no forward kinetics are declared. The derived pair here "
                "is the barrierless reverse of a DECOMPOSITION, so it gives "
                "Ea = max(dH, 0) = 0: a reaction with no temperature "
                "dependence, which is a thermite that goes off in a cold jar "
                "and a smelting reduction whose furnace does nothing. Declare "
                "Ea and A on the row; the reverse still comes from detailed "
                "balance."
            )
    else:
        Ea = float(decl.Ea)
        A = float(decl.A)
        # ⚠⚠ THE FLOOR IS NOT A CONVENIENCE, IT IS WHAT KEEPS ``K`` RIGHT.
        # ``SolidStateArrays`` derives the reverse barrier as
        # ``max(Ea - dH, 0)``, and that max is inert for the derived pair
        # (``max(dH,0) - dH >= 0`` always). A declared ``Ea`` below ``dH``
        # would CLIP there, and the clip breaks ``k_f/k_r = K`` silently --
        # the equilibrium would no longer be the thermodynamics. It is also
        # ``detailed_balance``'s own floor everywhere else in this project.
        if Ea < max(dH, 0.0):
            raise UnpricedSolidReaction(
                f"{decl.name!r}: declared Ea = {Ea / 1000.0:.2f} kJ/mol is "
                f"below dH = {dH / 1000.0:.2f} kJ/mol. An elementary barrier "
                "cannot be lower than the reaction enthalpy -- and here it is "
                "worse than wrong: the reverse barrier is max(Ea - dH, 0), so "
                "the clip would leave k_f/k_r no longer equal to K and the "
                "equilibrium would stop being the thermodynamics."
            )
    return PricedSolidReaction(
        decl=decl,
        dH=dH,
        dS=dS,
        Ea=Ea,
        A=A,
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
