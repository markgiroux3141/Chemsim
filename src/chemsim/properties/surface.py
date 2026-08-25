"""Layer 1 -- a GAS-CONSUMING surface reaction: roasting an ore.

``2 ZnS(s) + 3 O2(g) -> 2 ZnO(s) + 2 SO2(g)`` is a roaster, and it is the
reaction M6 measured its way to without being able to run. M6 built the reaction
that happens INSIDE a crystal and evolves a gas; this is the other one -- a
crystal that reacts with a gas ARRIVING at its surface -- and the two are
deliberately kept apart, with a refusal in each direction.

## ⚠ WHY THIS IS NOT M6's TERM, WHICH M6 MEASURED RATHER THAN ARGUED

``SolidStateArrays`` uses the AFFINITY form, ``k_f - k_r Q``, because a pure
solid has unit activity and its equilibrium is a statement about the gas alone.
That form is only a rate law while every gas participant is a PRODUCT. Put a gas
on the reactant side and its pressure lands in the DENOMINATOR of ``Q``, so an
atmosphere depleted of it drives the reverse flux without bound -- measured on a
roasting declaration at **2.6e15 formula units per second** as ``p_O2 -> 0``.
``build_solid_state_arrays`` refuses such a declaration by name, and this module
is where the refusal points.

So roasting is MASS ACTION: first order in an arriving gas, gated on a solid
being present. Which is also why it needs no equilibrium at all -- see below.

## ⚠⚠ WHY THIS IS NOT A THIRD ``PHASE_INDEX`` ENTRY EITHER, AND THAT *IS* NEW

The brief for this work said to add ``PHASE_INDEX["solid"] = 2`` and let one
mechanism cover both roasting and a solid CATALYST. Measured, the two are not one
mechanism, and the phase label is the wrong home for either:

  * **A solid catalyst is a factor in the rate law of a GAS-phase reaction.**
    Its stoichiometry is zero on both sides, so its ``delta`` never leaves the
    gas block, and thermodynamically every participant that HAS an activity is a
    gas -- the catalyst's is 1. Labelling ``N2 + 3 H2 -> 2 NH3`` a "solid"-phase
    reaction moves it onto the pure-liquid standard state, because
    ``reaction_deltas`` shifts anything that is not ``"gas"``: **dG moves by
    -99.7 kJ/mol and K at 500 K by a factor of 2.6e10.** That is verbatim the
    failure the ``PHASE_INDEX`` comment was written to prevent, arriving at the
    line it is written on. So a solid catalyst is
    ``ReactionTemplate.solid_catalyst`` -- an extra column in ``order``, and
    nothing else.

  * **Roasting cannot be priced on the ideal-gas basis at all.** Its reactant is
    a lattice and ``thermochemistry`` refuses a lattice SMILES by name, for the
    reason ``mineral_data`` records at 407x. Its enthalpy has to come from the
    SOLID basis against a curated gas -- the subtraction ``solid_state`` argues
    is legal exactly here and nowhere else -- so it is a curated TABLE with its
    own pricing, like ``SOLID_STATE_REACTIONS`` and ``SOLUBILITY_PRODUCTS``.

``PHASE_INDEX`` therefore still has two entries, for the second time and for a
different reason. M6's was *the kernel cannot express this rate law*; this one is
*the label would put the reaction on the wrong standard state*.

## THE FORM

    rate = k(T) * prod over SOLID participants of nS_i ^ order_i     [mol/s]
                * prod over GAS   participants of C_i  ^ order_i

    k(T) = A exp(-Ea / R T)

⚠ **THE BASIS IS MIXED AND THAT IS THE ONE THING THIS MODULE MUST GET RIGHT.**
The solid enters on an AMOUNT (mol) and the gas on a CONCENTRATION (mol/L), so
the rate comes out in mol/s directly and is NOT multiplied by a volume the way
every other rate law here is. Both halves of that are forced:

  * **A solid's "concentration" has no referent.** The solid block is an
    inventory in mol and ``V_S`` is nominal (solids are given the liquid molar
    volume, which the vessel says out loud). ``nS/V`` would be a number divided
    by a convention.
  * **A gas's amount is not what a surface sees.** The flux of molecules onto a
    crystal face goes with the collision rate, i.e. with the CONCENTRATION. Written
    on ``nG`` instead, compressing the flask would not speed the reaction up --
    and a roaster is a machine for blowing air through a bed.

So the rate is EXTENSIVE in the solid and INTENSIVE in the gas, and one
consequence is worth stating because it is a mechanic: with order 1 in the solid,
``tau = n/rate = 1/(k C_gas)`` does **not** depend on how much ore is charged.
Doubling the bed doubles the throughput and does not change the time.

⚠ ``nS^(2/3)`` -- the shrinking-core law -- is physically better and is REFUSED,
for the reason ``SOLID_GATE_TIME`` records: its slope at ``nS = 0`` is infinite.
First order is the constant-particle-count idealisation and is what M6 uses.

## ⚠⚠ IRREVERSIBLE, AND THAT IS A MEASUREMENT TWICE OVER

A surface reaction here may not be reversible, and both halves of the argument
are numbers rather than preferences:

  * **Mass action on a solid AMOUNT reaches the wrong equilibrium.** This is
    M6's measurement and it is not re-derived: a pure solid has unit activity, so
    a reversible pair written on the amounts settles at ``p/K = n_A/n_B`` --
    observed at 3.0863 against 3.0863 at 1100 K. Any reversible declaration whose
    solid stoichiometry is non-zero would inherit that exactly.
  * **And for roasting the reverse is not a mechanic anybody could see.**
    ``ln K`` at each row's own run temperature is **+67.6 to +78.8** -- K between
    2e29 and 2e34 -- against a reaction quotient of order 1 in a real roaster.
    ``LN_K_IRREVERSIBLE`` is the bar every row must clear, and the tightest row
    (covellite) clears it by **20.7 decades**.

The consequence is that ``dG`` is used HERE, at pricing time, to justify dropping
the reverse -- and then never again. What the integrator gets is ``A``, ``Ea``
and ``dH``, and ``dH`` only for the energy balance.

## ⚠ THE BARRIER IS SHARED AND EVANS-POLANYI IS REFUSED, MEASURED

M6's lesson is that **a constant shared between rows is a claim that they are the
same event**. The claim made here is that the rate-determining event is an O2
molecule arriving at a metal-sulfide surface, which is the same event for
sphalerite, galena and covellite -- so ``ROASTING_A`` and ``ROASTING_EA`` are
shared, and the rows then differ only in their thermodynamics, which an
irreversible rate law does not see. **So all three roast on the same clock**, and
that is a stated limitation rather than a hidden one.

⚠ **The obvious fix is wrong, and it is wrong in a measurable direction.** This
project has one mechanism for making rates differ within a family --
``ReactionTemplate.alpha``, Evans-Polanyi on the reaction enthalpy -- and applied
here it gets the answer BACKWARDS. Per two formula units of sulfide:

    sphalerite  dH -882.7 kJ/mol      cinnabar roasts in a 900 K retort
    galena      dH -830.9             sphalerite needs a 1100 K roaster
    covellite   dH -802.1             (the catalog's own equipment column)
    cinnabar    dH -658.9

Evans-Polanyi makes the most exothermic row the fastest, so it would put
sphalerite first and cinnabar last; the catalog says cinnabar is the easy one.
The reason is that the overall enthalpy is not the barrier of the rate-determining
step -- what orders these rows is the metal-sulfur bond, and this project has no
table for that. So ``alpha`` is zero and the ordering is NOT claimed.

## WHAT IS HERE AND WHAT IS REFUSED

FOUR of the catalog's five ``roasting`` rows now run end to end. The fifth is
refused for a reason that is not this module's:

  * ``pyrite-roasting`` -- pyrite has ``Hfs`` in WEBBOOK and ``S0s`` in nothing,
    so ``mineral_data`` refuses it under the same-database rule. A DATA refusal,
    recorded there.

⚠ ``mercury-from-cinnabar`` USED TO BE THE SECOND ENTRY IN THAT LIST AND IS NOW
CLAIMED, WITHOUT ONE LINE OF THIS MODULE CHANGING. S1 wrote here that the roast
to the OXIDE was as far as this project could take it, because "the row gives
the metal and mercury metal is not a species here". S4 curated mercury as an
element (its reference state is a LIQUID, so its ideal-gas record is a real
vaporisation number) and declared ``2 HgO -> 2 Hg + O2`` in ``solid_state``.
Neither declaration mentions the other; they share one crystal in the solid
block, and what a retort does falls out:

    this module      2 HgS + 3 O2 -> 2 HgO + 2 SO2       a gas at a surface
    solid_state.py   2 HgO        -> 2 Hg  +   O2        inside the crystal
    -----------------------------------------------------------------------
    the catalog row    HgS +   O2 ->   Hg  +   SO2       nobody wrote this

Measured on a sealed 10 L retort of pure oxygen holding 0.02 mol of cinnabar at
900 K: **0.020000000000 mol of mercury and 0.020000000000 mol of SO2**, 1:1 to
twelve figures, on 0.020000 mol of oxygen consumed. The montroydite standing in
the solid block is this roast's rate times the decomposition's own clock -- 0.24
s at 900 K against this row's 5,918 s -- so it starts at **8e-7 mol** and FALLS
with the ore, never reaching 4e-5 of the charge. The intermediate is real, and
invisible.

⚠ AND THE TWO CLOCKS CROSS, WHICH IS A MECHANIC NOBODY WROTE EITHER. The
decomposition's barrier is 304 kJ/mol against this module's 150, so cooling the
retort slows it far faster than it slows the roast. Under 1 bar of oxygen they
are equal at **611.7 K**; above that the oxide is a vanishing intermediate and
the retort gives the METAL, below it the oxide piles up and the retort gives
the OXIDE instead. Measured, as the fraction of the mercury released from the
cinnabar that is still sitting in the solid block as montroydite:

    900 K   2.0e-6        700 K   1.9e-2        600 K   0.913
    773 K   4.3e-4        650 K   0.341

⚠ Nothing gates on temperature anywhere in either term. That column is two
Arrhenius factors with different exponents, and the exponents were written in
different modules one milestone apart.
"""

from __future__ import annotations

import math
from typing import NamedTuple

from chemsim.constants import R
from chemsim.properties.mineral_data import MINERALS, MineralRecord

T_REF = 298.15

# L/(mol s) per mole of solid -- see the module docstring for the mixed basis
# and for the claim this shared value makes.
#
# ⚠ WHAT PINS IT. Not a fit: it is the constant a ROASTER's own residence time
# implies. A fluidised-bed sulfide roaster works in tens of minutes, so with
#
#     tau = 1 / (k C_O2)
#
# and 1 bar of air at 1100 K (C_O2 = 0.00230 mol/L), tau = 1800 s needs
# k = 0.242 L/(mol s). At the barrier below that is A = 3.21e6 L/(mol s), which
# is 3.2e-5 of this project's bimolecular COLLISION_LIMIT -- comfortably inside
# it, and stated rather than assumed, because a heterogeneous pre-exponential
# with a sub-collision value is the one property that makes it a rate and not a
# knob. ``validation/rate_ceiling.py`` re-measures it.
ROASTING_A = 3.21e6

# J/mol. Apparent activation energy for the oxidation of a metal sulfide, whose
# reported band is wide (roughly 100-250 kJ/mol, moving with particle size and
# regime because the measurement is never purely chemical). 150 is the middle.
#
# ⚠ SHARED WITH ``ROASTING_A`` AND THEREFORE PART OF THE SAME CLAIM. The two
# together are one clock for the whole family; the module docstring measures what
# that costs and why the available alternative is worse.
ROASTING_EA = 150_000.0

# The bar a declaration must clear for its reverse to be droppable. ln K = 20 is
# K = 4.9e8: eight decades between the equilibrium and any quotient a flask can
# reach, so the reverse flux is not a rounding error's worth of the forward one.
# Checked at the row's OWN declared temperature, because K moves with T and a row
# that is irreversible in a roaster need not be at room temperature.
LN_K_IRREVERSIBLE = 20.0

# Formation sources a lattice may be subtracted from. Identical to
# ``solid_state.CURATED_FORMATION`` and for the identical reason: the answer IS
# the difference between a solid-basis number and a gas-basis one, so a
# group-contribution estimate on either side of it is the 25-29 decade failure
# ``solubility_product`` recorded.
#
# ⚠ The third prefix, and why a prefix match is the weak part of this guard, is
# recorded once at ``solid_state.CURATED_FORMATION``. The short version: a
# CONDENSED element reference state's provenance begins with the derivation
# rather than the tier, so CRC's own row for mercury was being read as an
# estimate.
CURATED_FORMATION = (
    "experimental",
    "element reference state",
    "Hf and S0 both from",
)


class UnpricedSurfaceReaction(ValueError):
    """A declared surface reaction that cannot be priced or run. Says why."""


class SurfaceReaction(NamedTuple):
    """One declared reaction between a crystal and a gas at its surface.

    ⚠ **DECLARED, NOT DISCOVERED, AND THAT IS FORCED** -- the same force as
    ``SolidStateReaction``. A ``ReactionTemplate`` matches SMARTS on a molecular
    graph and a lattice is not a graph: ``[S-2].[Zn+2]`` has no bonds to rewrite,
    and there is no rewrite that could pull a sulfur atom out of a crystal to
    make SO2. So it is a curated table.

    ``solids`` and ``gases`` are signed -- negative consumed, positive formed --
    and ``orders`` names the rate law separately, because the written
    stoichiometry is a GLOBAL one and not an elementary step. Three O2 do not
    meet one crystal; the reaction is first order in each.

    ``T_run`` is the temperature the irreversibility check is made at, and it is
    the temperature the catalog's own equipment column gives for this row. It is
    NOT a threshold and nothing gates on it: the rate law runs at every
    temperature, and how fast is Arrhenius' business.
    """

    name: str
    solids: tuple           # ((mineral name, nu, order), ...)   nu signed
    gases: tuple            # ((canonical SMILES, nu, order), ...)   nu signed
    mechanism: str          # the catalog CLASS this row is, as a mechanism
    T_run: float            # K -- where the reverse is checked, from the catalog
    note: str


class PricedSurfaceReaction(NamedTuple):
    """A declaration plus the numbers Layer 4 integrates it with."""

    decl: SurfaceReaction
    dH: float               # J/mol at T_REF, + = endothermic
    dS: float               # J/(mol K) at T_REF, from the dH/dG pair
    dG: float               # J/mol at T_REF -- used ONCE, to drop the reverse
    ln_K_run: float         # at ``T_run``; must clear LN_K_IRREVERSIBLE
    Ea: float               # J/mol -- DECLARED, see ROASTING_EA
    A: float                # L^g mol^(1-g-s) / s
    minerals: tuple         # ((MineralRecord, nu, order), ...) resolved
    basis: str              # what the two halves came from


# ---------------------------------------------------------------------------
# The declarations
# ---------------------------------------------------------------------------
# Written per TWO formula units of sulfide so that every coefficient is an
# integer: ``2 MS + 3 O2 -> 2 MO + 2 SO2``. That matters for the enthalpy the
# energy balance is handed -- ``dH`` below is per mole of REACTION as written, so
# it is roughly twice a per-sulfide figure, and the flux it multiplies is in
# reaction-extents per second.
#
# ⚠ THE RATE LAW IS NOT THE STOICHIOMETRY, and this is the same declaration
# ``library.sulfur_combustion`` makes for the same reason. ``3 O2`` taken as mass
# action would be third order in oxygen, which stalls asymptotically as the
# atmosphere is consumed and makes the conversion a reading of ``ROASTING_A``
# rather than of the chemistry. First order in each participant is what a surface
# rate law is.
SURFACE_REACTIONS: tuple[SurfaceReaction, ...] = (
    SurfaceReaction(
        name="sphalerite-roasting",
        solids=(("sphalerite", -2, 1.0), ("zincite", +2, 0.0)),
        gases=(("O=O", -3, 1.0), ("O=S=O", +2, 0.0)),
        mechanism="roasting",
        T_run=1100.0,
        note=(
            "`zinc-smelting` step 1, and the SO2 half of it is a sulfuric-acid "
            "feedstock in its own right. The zincite is what a reduction "
            "furnace then takes to the metal"
        ),
    ),
    SurfaceReaction(
        name="galena-roasting",
        solids=(("galena", -2, 1.0), ("litharge", +2, 0.0)),
        gases=(("O=O", -3, 1.0), ("O=S=O", +2, 0.0)),
        mechanism="roasting",
        T_run=1100.0,
        note=(
            "`lead-smelting` step 1 -- the sinter plant. This is where the lead "
            "behind the lead chamber comes from, so chain 2's vessel has a route "
            "of its own now"
        ),
    ),
    SurfaceReaction(
        name="covellite-roasting",
        solids=(("covellite", -2, 1.0), ("tenorite", +2, 0.0)),
        gases=(("O=O", -3, 1.0), ("O=S=O", +2, 0.0)),
        mechanism="roasting",
        T_run=1100.0,
        note="`copper-smelting` step 1",
    ),
    # ⚠⚠ HALF OF A ROW, AND THE OTHER HALF IS IN ANOTHER MODULE. This makes the
    # OXIDE, and `mercury-from-cinnabar` reads `mercury-sulfide + oxygen ->
    # mercury + sulfur-dioxide` -- which is why S1 re-labelled that row
    # `roasting-to-metal` and left it uncovered rather than claim it here.
    #
    # S4 declared the other half, `solid_state.oxide-thermal-decomposition`, and
    # the two of them together ARE the row: the montroydite this makes decomposes
    # 24,610x faster than this reaction makes it at 900 K, so it never
    # accumulates and what comes over is the metal. NOTHING declares that. This
    # row's own note has not changed by one coefficient.
    SurfaceReaction(
        name="cinnabar-roasting",
        solids=(("cinnabar", -2, 1.0), ("montroydite", +2, 0.0)),
        gases=(("O=O", -3, 1.0), ("O=S=O", +2, 0.0)),
        mechanism="roasting",
        T_run=900.0,
        note=(
            "the roast in `mercury-from-cinnabar`'s 900 K retort, and it stops "
            "at the OXIDE -- which is the whole reaction, because montroydite "
            "does not survive that heat. `solid_state` takes it the rest of the "
            "way and neither declaration knows about the other"
        ),
    ),
)


def price(
    decl: SurfaceReaction, thermo, T_ref: float = T_REF
) -> PricedSurfaceReaction:
    """Resolve one declaration against the two tables, or refuse and say why.

    ``thermo`` is a ``ThermochemistryProvider``, asked only for the GASES. The
    solids come from ``mineral_data`` on the solid basis, and the subtraction of
    one basis from the other is legal here for the reason ``solid_state``'s
    docstring argues: **every participant is in its own standard state.** A
    crystal is a crystal and a gas at 1 bar is an ideal gas at 1 bar. That is
    exactly what ``standard_state`` exists to prevent for a species dissolved in
    a solvent, which is in neither.
    """
    dH = 0.0
    dG = 0.0
    resolved: list[tuple[MineralRecord, int, float]] = []
    sources: list[str] = []

    for name, nu, order in decl.solids:
        rec = MINERALS.get(name)
        if rec is None:
            raise UnpricedSurfaceReaction(
                f"{decl.name!r}: no mineral called {name!r} in mineral_data. "
                "Add it with tools/build_mineral_data.py -- a surface reaction "
                "is priced from the solid basis and there is no estimator "
                "standing behind that table."
            )
        if rec.Cp_solid is None or rec.Vm_solid is None:
            missing = [
                k for k, v in (("Cp_solid", rec.Cp_solid),
                               ("Vm_solid", rec.Vm_solid)) if v is None
            ]
            raise UnpricedSurfaceReaction(
                f"{decl.name!r}: {name!r} has no {' and no '.join(missing)}. "
                "Its formation pair is fine, but a crystal in the solid block "
                "also has to say how much room it takes and how much heat it "
                "holds -- Layer 4 asks that of every species, and borrowing an "
                "ion's placeholder for a mineral would be silent."
            )
        dH += nu * rec.Hf_solid * 1000.0
        dG += nu * rec.Gf_solid * 1000.0
        resolved.append((rec, nu, order))
        sources.append(f"{name}: {rec.source}")

    for smiles, nu, _order in decl.gases:
        data = thermo.get(smiles)
        if not any(data.source.startswith(p) for p in CURATED_FORMATION):
            raise UnpricedSurfaceReaction(
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
    # ⚠ THE ONLY USE dG IS PUT TO, AND IT IS A GATE ON THE DECLARATION RATHER
    # THAN A NUMBER THE INTEGRATOR SEES. The rate law below is irreversible, so
    # nothing downstream can notice an equilibrium; this is where that is paid
    # for. van 't Hoff from the 298 K pair with dCp = 0, the same discipline
    # ``solid_state.ln_Ksp`` and ``PrecipitationArrays.ln_Ksp`` state.
    ln_K = -(dH - decl.T_run * dS) / (R * decl.T_run)
    if ln_K < LN_K_IRREVERSIBLE:
        raise UnpricedSurfaceReaction(
            f"{decl.name!r}: ln K = {ln_K:.2f} at {decl.T_run:g} K, below the "
            f"bar of {LN_K_IRREVERSIBLE:g} this table requires. A surface "
            "reaction here is integrated FORWARD ONLY, and the reason is M6's "
            "measurement: mass action written on a solid AMOUNT settles at "
            "p/K = n_A/n_B rather than at unit activity, so a reversible "
            "declaration would reach a wrong equilibrium while looking like one "
            "that does not. A row whose reverse is a real flux therefore cannot "
            "be expressed by this term at all -- it is not a matter of "
            "tightening the rate constant."
        )
    return PricedSurfaceReaction(
        decl=decl,
        dH=dH,
        dS=dS,
        dG=dG,
        ln_K_run=ln_K,
        # DECLARED, unlike ``solid_state``'s, and the asymmetry is the whole
        # difference between the two mechanisms. There the barrier is DERIVED as
        # ``max(dH, 0)`` because the reverse of a decomposition is barrierless
        # and the equilibrium is the mechanic. Here the reaction is hugely
        # exothermic and irreversible, so ``max(dH, 0)`` would be ZERO -- a
        # barrierless roast that goes as fast as O2 can arrive, which is not
        # what a roaster is. The barrier is the surface chemistry and it has to
        # be declared; see ROASTING_EA.
        Ea=ROASTING_EA,
        A=ROASTING_A,
        minerals=tuple(resolved),
        basis="; ".join(sources),
    )


def rate_constant(priced: PricedSurfaceReaction, T: float) -> float:
    """``k(T)``, in the mixed basis of the module docstring. Reported, not hot."""
    return priced.A * math.exp(-priced.Ea / (R * T))


def time_constant(priced: PricedSurfaceReaction, T: float, C_gas: float) -> float:
    """Seconds for the gated solid to fall by 1/e at a fixed gas concentration.

    ``1 / (k C)`` -- and note what is NOT in it. With order 1 in the solid the
    charge cancels, so this is the number a roaster's residence time is compared
    against however much ore is in the bed. Reported so that a route can be
    checked against a real machine without running a vessel.
    """
    k = rate_constant(priced, T)
    if k <= 0.0 or C_gas <= 0.0:
        return float("inf")
    return 1.0 / (k * C_gas)


def lattice_species() -> frozenset:
    """Every mineral SMILES a surface reaction in this table touches.

    What a caller charges into a flask, and kept as a function rather than a
    constant so it cannot go stale against the declarations above.
    """
    return frozenset(
        MINERALS[name].lattice
        for decl in SURFACE_REACTIONS
        for name, _nu, _order in decl.solids
        if name in MINERALS
    )


def gas_species() -> frozenset:
    """Every gas SMILES a surface reaction in this table touches."""
    return frozenset(
        smiles
        for decl in SURFACE_REACTIONS
        for smiles, _nu, _order in decl.gases
    )
