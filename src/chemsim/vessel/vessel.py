"""Layer 5 -- the vessel: a flask with contents, phases, and a temperature.

This is where the simulation stops being a reaction and starts being an
*experiment*. A ``Vessel`` owns:

  * an inventory in moles, split between liquid and headspace vapour;
  * a temperature that it works out for itself from reaction heat, latent heat,
    the hotplate, and losses to the room;
  * a pressure, and a vent that opens when it exceeds ambient;
  * an optional ingress term -- the leaky-flask contamination the Phase-0 spike
    had to hard-code, now just a boundary flux.

Everything physical happens in Layer 4. This layer's job is *assembly*: turn
molecules into the property arrays that layer consumes, then hand back results in
terms a chemist would use (concentrations, mole fractions, pressure, phase).

The behaviour worth watching for, none of which is scripted:

  * an exotherm that heats its own vessel and accelerates itself;
  * that same exotherm losing yield as it heats, because K falls with T;
  * a solvent that boils -- and holds temperature at its boiling point while it
    does, because latent heat balances the hotplate;
  * a flask that boils dry and then rockets past the boiling point, because
    nothing is left to absorb the heat.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from chemsim.constants import R_L_BAR
from chemsim.network import ReactionNetwork
from chemsim.numerics.activity import (
    activity_coefficients,
    born_ln_gamma,
    oster_permittivity,
)
from chemsim.numerics.lle import (
    IDEAL_FRACTION_REPORT,
    held_ideal_fraction,
)
from chemsim.numerics.vessel_integrator import (
    BORN_COVERAGE_MIN,
    BORN_TRACE,
    IONIC_SPLIT_LIMIT,
    PhaseArrays,
    PrecipitationArrays,
    SolidStateArrays,
    VesselConditions,
    VesselIntegrator,
    _poly,
)
from chemsim.vessel.conditions import Condition, compile_condition
from chemsim.properties import (
    ActivityArrays,
    BornArrays,
    CondensedProvider,
    DielectricProvider,
    ThermochemistryProvider,
    UnifacProvider,
    VolatilityProvider,
    build_activity_arrays,
    build_born_arrays,
    fit_inverse_cubic,
)
from chemsim.properties import mineral_data
from chemsim.properties.volatility import NONVOLATILE_A

# Temperature window the infinite-dilution reference is fitted over. Narrower
# than the 250-450 K used for liquid properties, and deliberately so: PSRK's gas
# parameters are quadratic in T and extrapolate badly outside the range they were
# regressed in -- carbon monoxide's reference coefficient swings by a factor of
# 20 below 273 K. This window is where a solvent is actually liquid, which is the
# only place a dissolved-gas reference means anything.
T_REF_LO, T_REF_HI = 273.0, 420.0

# A fitted reference worse than this is reported rather than quietly used.
REFERENCE_FIT_TOLERANCE = 0.01     # 1% in gamma

# How much of the room's atmosphere the network must account for before the
# vessel is allowed to exchange bulk gas with it. See the note where it is used:
# partial credit is not available here, because bulk flow carries composition.
ATMOSPHERE_COMPLETE = 0.99


@dataclass(frozen=True)
class ReferenceState:
    """An infinite-dilution reference, as coefficients plus how well they fit."""

    coeffs: tuple[float, float, float, float]   # ln gamma_inf = a + b/T + c/T^2 + d/T^3
    error: float                                # max relative error in gamma


# Cache keyed by (solute, solvent) -- a pure function of the pair, so it is
# shared across every vessel in a world.
_REFERENCE_CACHE: dict[tuple[str, str], ReferenceState | None] = {}


def infinite_dilution_reference(
    solute: str, solvent: str, activity: UnifacProvider
) -> ReferenceState | None:
    """The solute's activity coefficient at infinite dilution in a solvent.

    This is the reference state a Henry's-law constant is measured against, and
    dividing by it is what turns a symmetric-convention gamma into an
    unsymmetric one. Returns ``None`` if either species has no group
    decomposition, so the caller can fall back to the tabulated constant and say
    so.

    Being a function of temperature alone it collapses to four numbers at setup,
    which is the whole point: the second convention costs the hot loop nothing.
    The basis is 1/T rather than T because the quantity is a ratio of Boltzmann
    factors -- see ``fit_inverse_cubic``.

    WHY THIS LIVES IN LAYER 5. It needs a group table (Layer 1) and the activity
    kernel (Layer 4) at the same time, and Layer 1 must not import Layer 4. Same
    reasoning that puts ``discovery`` above ``numerics``: the module that needs
    both sits above both rather than inverting a dependency.
    """
    key = (solute, solvent)
    if key in _REFERENCE_CACHE:
        return _REFERENCE_CACHE[key]

    arrays = build_activity_arrays([solute, solvent], activity)
    state: ReferenceState | None = None
    if arrays.active.all():
        # x = (0, 1): the solute vanishes, the solvent is pure. The combinatorial
        # term is written so that limit is exact rather than a 0/0.
        x = np.array([0.0, 1.0])
        Ts = np.linspace(T_REF_LO, T_REF_HI, 40)
        values = np.array([
            np.log(activity_coefficients(
                x, arrays.nu, arrays.R_k, arrays.Q_k, arrays.a_mn, arrays.active, T
            )[0])
            for T in Ts
        ])
        coeffs, residual = fit_inverse_cubic(Ts, values)
        # The residual is in ln gamma, so exp() turns it into a relative error.
        state = ReferenceState(coeffs, float(np.exp(residual) - 1.0))

    _REFERENCE_CACHE[key] = state
    return state


@dataclass
class VesselState:
    """A snapshot of the vessel -- plain data, so it serializes for save/load."""

    n_liquid: dict[str, float]   # mol, the PRIMARY liquid layer
    n_gas: dict[str, float]      # mol
    T: float                     # K
    t: float = 0.0               # s, elapsed simulated time
    n_solid: dict[str, float] = field(default_factory=dict)   # mol
    # The second liquid layer, empty unless the liquid has split. Kept as its
    # own field rather than folded into ``n_liquid`` because the whole point of
    # two layers is that they have different compositions -- a combined figure
    # would be the one number that describes neither of them.
    n_liquid2: dict[str, float] = field(default_factory=dict)  # mol

    def total(self, smiles: str) -> float:
        """Moles of a species across every phase -- what conservation acts on."""
        return (
            self.n_liquid.get(smiles, 0.0)
            + self.n_liquid2.get(smiles, 0.0)
            + self.n_gas.get(smiles, 0.0)
            + self.n_solid.get(smiles, 0.0)
        )

    def liquid_total(self, smiles: str) -> float:
        """Moles dissolved, across both liquid layers."""
        return self.n_liquid.get(smiles, 0.0) + self.n_liquid2.get(smiles, 0.0)

    @property
    def two_phase(self) -> bool:
        """Whether the liquid has separated into two layers."""
        return any(v > 0.0 for v in self.n_liquid2.values())


@dataclass
class WaitOutcome:
    """What a ``wait_until`` actually did -- see ``Vessel.wait_until``.

    ``elapsed`` is the field that has to be respected: a terminal event returns
    the state AT the event, so the span that happened is shorter than the span
    that was asked for, and a caller advancing its own clock by the timeout drifts
    out of step with the vessel.

    The other three fields exist because "it did not happen" has three different
    causes and a player is owed the difference. ``fired`` names the condition that
    stopped it; ``already`` says it was true before the wait began (an answer, not
    a failure); ``timed_out`` says the bound was reached with nothing satisfied.
    """

    elapsed: float
    fired: Condition | None
    already: bool
    timed_out: bool
    state: VesselState

    def describe(self) -> str:
        if self.already:
            return f"{self.fired.describe()} was ALREADY true -- waited 0 s"
        if self.timed_out:
            return f"nothing happened in {self.elapsed:.1f} s -- timed out"
        return f"{self.fired.describe()} after {self.elapsed:.1f} s"


G_EARTH = 9.80665                  # m/s^2
# Wetted area of a SPHERE holding a given volume:
#     V = (4/3) pi r^3,  A = 4 pi r^2  =>  A = (4 pi)^(1/3) (3 V)^(2/3)
# in SI (V in m^3, A in m^2). A sphere is the minimum-area shape for a volume, so
# this is a LOWER BOUND on holdup: a tall narrow cylinder wets more wall per unit
# volume and loses more. ``TransferLosses.shape_factor`` is how you say so.
SPHERE_SHAPE_FACTOR = (4.0 * math.pi) ** (1.0 / 3.0) * 3.0 ** (2.0 / 3.0)


@dataclass(frozen=True)
class TransferLosses:
    """What a vessel keeps when you empty it: a liquid film, and a crystal crust.

    ## Why this exists, and the rule it had to satisfy

    A full prep ran end to end at 93.2% yield and ~100% purity where a real bench
    run of it is ~80% and 97-98%. The gap was not a missing fudge factor: nothing
    wetted the glass, so ``pour_into`` and ``filter_into`` moved material with
    perfect efficiency.

    The rule for closing it: **a loss the player can fight is a mechanic, a loss
    they cannot fight is a tax.** ``yield *= 0.9`` is a tax -- a silent
    approximation with no scale dependence, undiscoverable, and a violation of the
    rule that nothing is dropped unreported. Every mechanism here owes three
    things -- MECHANISM, SCALE DEPENDENCE, COUNTERMEASURE -- before it is allowed
    in, and there are two of them.

    ## Mechanism 1: the liquid film (holdup)

    MECHANISM       Gravity drainage of a liquid film down a wetted wall. The
                    residual thickness follows the drainage law
                    ``delta = sqrt(nu / (g t))``, where ``nu`` is the KINEMATIC
                    viscosity and ``t`` is how long you let it drain. Not a
                    tabulated constant: it is derived from a transport property
                    and a time, which is why it responds to both.

    SCALE           Wetted area goes as ``V^(2/3)`` for geometrically similar
                    glassware, so the holdup is nearly CONSTANT in absolute
                    volume and the *relative* loss grows as ``V^(-1/3)``. Small
                    preps losing proportionally more arrives from the geometry
                    rather than being asserted. Measured: ~0.9% of a 100 mL
                    transfer, ~1.9% at 10 mL, ~4% at 1 mL, for water drained 5 s.

    COUNTERMEASURE  Three of them, all real bench practice. Run it on a bigger
                    scale (the scale law). **Let it drain longer** -- the film
                    thins as ``t^(-1/2)``, and this is the strongest lever.
                    **Rinse and combine** -- which works for free and needed no
                    code, because the film STAYS IN THE SOURCE VESSEL rather than
                    vanishing, so charging fresh solvent and pouring again
                    recovers most of it.

    ⚠ **And on a crystallisation route it is worth nothing**, which is the
    measurement that produced mechanism 2. The benzoic acid prep read 93.25%
    before and after turning it on, because *every transfer in that prep moves
    waste*: the product travels as a solid in the filter cake, so the film left
    on the pot wall is mother liquor that was already being discarded. Film
    holdup bites where product moves in SOLUTION -- an extraction, a
    concentration, a filtration whose product is the filtrate.

    ## Mechanism 2: the adhering crystal crust

    The loss that actually stands between a simulated crystallisation and a bench
    one. Crystals stick to the glass they grew against and to the funnel, and a
    spatula does not lift them all.

    MECHANISM       An adhering layer of crystals, of order ONE PARTICLE
                    DIAMETER thick, over the surface the slurry wetted. Its
                    areal density is not a chosen number: it is
                    ``crystal_size * packing_fraction`` of solid per unit area,
                    converted to moles through the vessel's OWN molar volume --
                    the same Rackett polynomial the RHS integrates. So a denser
                    solid leaves more mass behind than a fluffy one, and a
                    mixture of solids is left behind in the proportion it was
                    present, with no per-species parameter anywhere.

    SCALE           The same ``V^(2/3)`` wetted area, so the crust is nearly
                    constant in absolute volume while the crop scales with the
                    batch. That IS the "absolute floor" a small prep suffers
                    from, arrived at from the geometry rather than asserted: a
                    50 mg prep loses most of its crop to the flask and a 50 g
                    prep barely notices. Measured over four decades of scale.

    COUNTERMEASURE  **Rinse the flask out and re-filter**, which again needs no
                    code because the crust is left where it physically is. And
                    the choice of rinse liquid is a real decision with a real
                    trade-off: fresh cold solvent recovers the crystals but
                    dissolves some of them, while the MOTHER LIQUOR is already
                    saturated and dissolves none. Nothing scripts that; it is the
                    solubility law. Plus running it on a bigger scale.

    ⚠ **Distinct from ``filter_into``'s ``passthrough``, and they must not be
    merged.** Passthrough is fines going *through* the paper -- a defect of the
    filter. This is crystals that never left the vessel -- a fact about glass and
    spatulas. They have different scale laws and different countermeasures.

    ## Where the material goes, which is the load-bearing detail

    Both losses are left behind in the vessel that was emptied. Neither is
    destroyed and neither is moved to a sink. That is both physically right --
    the film clings to the flask you just emptied, the crust is stuck to its wall
    -- and what keeps the conservation invariant exact: every element balance
    still closes to round-off, because these operations only ever *fail to move*
    material. A loss modelled as material disappearing would have destroyed the
    property that ``numerics.project_non_negative`` was written to establish, and
    would have made rinsing unimplementable.

    ## Determinism

    Nothing here is stochastic and nothing runs inside the RHS. Both losses are
    computed once per transfer, at an event boundary, from the state -- the same
    reasoning that put the METER edge's rate in a parameter rather than a time
    window inside the ODE. A random term would break BDF outright, and Layer 6's
    saves have to reproduce exactly.

    ## Parameters

    ``drain_time``
        Seconds the vessel is left to drain. The dominant lever on the film: a
        2 s pour keeps a ~226 um film, a 30 s drain ~58 um. Default 5 s is an
        ordinary unhurried pour.
    ``kinematic_viscosity``
        m^2/s. Water 1.0e-6, ethanol 1.5e-6, toluene 6.8e-7, glycerol ~7e-4.
        Grouped as ``nu = mu / rho`` rather than taken as two parameters because
        that is exactly the combination the drainage law contains. ⚠ It is a
        single value for the whole liquid, not computed per species: this project
        has no viscosity model, and inventing one here would be the fabrication
        the curation rules forbid. Set it for the solvent in the flask.
    ``shape_factor``
        Wetted area = ``shape_factor * V^(2/3)`` in SI. Shared by both
        mechanisms, because both act on the surface the contents wetted.
        Defaults to a sphere, which is the minimum-area case and therefore
        optimistic for both.
    ``crystal_size``
        Metres -- the particle size of the crop, which sets how thick the
        adhering layer is. ⚠ **This is the calibrated parameter of mechanism 2**,
        and it is calibrated the way ``drain_time`` is: it is a real, measurable
        property of a crop with an obvious plausible range (a bench
        recrystallisation gives roughly 10 um to 1 mm), not a yield multiplier.
        Default 50 um is a fine crop. Set it to 0 to turn the crust off and
        isolate the film, which is what ``validation/process_losses.py`` does.
        ⚠ The model says a coarser crop leaves MORE mass per unit area, and that
        is the one prediction here not to lean on: it is a monolayer argument,
        and in practice fine powders also coat more completely and adhere in
        multilayers. Treat the size as a calibration with a band, not as a lever.
    ``packing_fraction``
        How much of that layer is solid rather than the liquid between the
        grains. 0.6 is random loose packing of near-spheres; random CLOSE packing
        is 0.64, and a well-formed crystal mat can be higher.
    """

    drain_time: float = 5.0                    # s
    kinematic_viscosity: float = 1.0e-6        # m^2/s (water)
    shape_factor: float = SPHERE_SHAPE_FACTOR
    crystal_size: float = 50.0e-6              # m, particle size of the crop
    packing_fraction: float = 0.6              # random loose packing

    def __post_init__(self) -> None:
        if self.drain_time <= 0.0:
            raise ValueError(
                f"drain_time must be positive, got {self.drain_time} -- the "
                "drainage law is singular at zero time (an undrained wall holds "
                "an unbounded film)"
            )
        if self.kinematic_viscosity <= 0.0 or self.shape_factor <= 0.0:
            raise ValueError("kinematic_viscosity and shape_factor must be positive")
        # Zero IS meaningful here, unlike drain_time: it means "no crust", which
        # is how the two mechanisms are measured apart. Negative is not.
        if self.crystal_size < 0.0:
            raise ValueError(
                f"crystal_size must be >= 0, got {self.crystal_size} (0 turns the "
                "adhering crust off, which is how it is isolated from the film)"
            )
        if not 0.0 <= self.packing_fraction <= 1.0:
            raise ValueError(
                f"packing_fraction must be in [0, 1], got {self.packing_fraction}"
            )

    @property
    def film_thickness(self) -> float:
        """Residual film thickness in metres, from the gravity-drainage law."""
        return math.sqrt(self.kinematic_viscosity / (G_EARTH * self.drain_time))

    @property
    def crust_thickness(self) -> float:
        """Metres of SOLID per unit wetted area -- one particle layer, packed.

        A thickness rather than a mass, so that converting it to moles is the
        vessel's job and uses the molar volume the vessel already believes in.
        """
        return self.crystal_size * self.packing_fraction

    def wetted_area(self, volume_litres: float) -> float:
        """m^2 of wall wetted by ``volume_litres`` of contents.

        The premise both mechanisms share, and the reason they share a
        ``shape_factor``: geometrically similar glassware wets area as V^(2/3),
        which is where every scale law below comes from.
        """
        if volume_litres <= 0.0:
            return 0.0
        return self.shape_factor * (volume_litres * 1.0e-3) ** (2.0 / 3.0)

    def holdup_litres(self, volume_litres: float) -> float:
        """Volume of liquid left on the wall after draining ``volume_litres``.

        Returns 0 for an empty vessel rather than extrapolating the geometry to
        nothing, and is capped at the volume present -- a film cannot hold back
        more than there was, which matters at the very small scales where the
        relative loss is heading for 100%.
        """
        if volume_litres <= 0.0:
            return 0.0
        area = self.wetted_area(volume_litres)
        return min(volume_litres, area * self.film_thickness * 1.0e3)

    def crust_litres(self, wetted_volume_litres: float) -> float:
        """Volume of crystals adhering to the wall a slurry of this size wetted.

        Takes the volume of the whole SLURRY, not of the solid: the crust sits on
        whatever surface the contents touched, so a crop grown in a big flask is
        spread over more glass and more of it stays there. That is the same
        premise the film rests on, and it is why the two share ``shape_factor``.
        """
        return self.wetted_area(wetted_volume_litres) * self.crust_thickness * 1.0e3


@dataclass(frozen=True)
class FiltrationResult:
    """What a filtration actually moved, in moles. Reported, never inferred.

    A filtration is the step where a yield becomes a number, so it says what it
    did rather than leaving the caller to difference two states -- and the
    liquid figures are what make an unwashed cake's impurity visible.
    """

    cake_solid: float
    cake_liquid: float
    filtrate_liquid: float
    filtrate_solid: float
    # Crystals that never left the vessel being filtered: the adhering crust.
    # Reported separately from ``filtrate_solid`` because they are a different
    # mechanism with a different cure -- fines through the paper are a filter
    # defect, a crust on the glass is what a rinse is for -- and because a
    # recovery figure that quietly omitted them would be the silent kind of
    # wrong this project does not allow.
    retained_solid: float = 0.0

    @property
    def recovered(self) -> float:
        """Solid actually collected, as a fraction of what was there."""
        total = self.cake_solid + self.filtrate_solid + self.retained_solid
        return 1.0 if total <= 0.0 else self.cake_solid / total


def build_phase_arrays(
    species: list[str],
    thermo: ThermochemistryProvider,
    volatility: VolatilityProvider,
    condensed: CondensedProvider,
    activity: UnifacProvider | None = None,
    dielectric: DielectricProvider | None = None,
) -> tuple[PhaseArrays, ActivityArrays, BornArrays]:
    """Resolve every species to numbers and stack them into the Layer 4 contract.

    This is the entire Layer 5 -> Layer 4 translation: after this call, nothing
    downstream can ask what a molecule is. The activity and Born blocks are
    returned alongside the arrays because their *coverage reports* -- which species
    are held ideal, which group pairs have no published parameter, which liquids
    have no measured permittivity -- are Layer 5 concerns that Layer 4 has no
    vocabulary for.
    """
    n = len(species)
    vol_A, vol_B, vol_C = np.zeros(n), np.zeros(n), np.zeros(n)
    condensable = np.zeros(n, dtype=bool)
    Hvap_Tb, Tb, Tc = np.zeros(n), np.zeros(n), np.zeros(n)
    v_liq, Cp_liq, Cp_gas = np.zeros((n, 4)), np.zeros((n, 4)), np.zeros((n, 4))
    Hfus, Tm = np.zeros(n), np.zeros(n)
    solidifies = np.zeros(n, dtype=bool)
    henry = np.zeros(n, dtype=bool)
    reference_solvent: list[str | None] = [None] * n

    lattices = mineral_data.by_lattice()

    for i, smi in enumerate(species):
        # ⚠ A MINERAL IS RESOLVED HERE AND NOT BY THE THREE PROVIDERS, BECAUSE
        # ALL THREE ARE RIGHT TO REFUSE IT. ``thermochemistry`` refuses a lattice
        # SMILES by name -- a solid-basis formation value wearing a ThermoData
        # would be shifted by ``standard_state`` and dissolved by the fusion
        # law -- and ``volatility``/``condensed`` are built on top of it. So the
        # crystal's numbers come straight from ``mineral_data``, which is where
        # SMILES meet tables, exactly as ``build_precipitation_arrays`` does one
        # function down.
        #
        # ⚠ ``solidifies`` STAYS FALSE, and that is the entire bargain. A lattice
        # in the solid block may now REACT (M6) but it still may not DISSOLVE,
        # because the only dissolution law here is the fusion law and that law is
        # measured wrong for a lattice by up to 407x in both directions. Nothing
        # about M6 softens that; the two questions never touch.
        mineral = lattices.get(smi)
        if mineral is not None:
            if mineral.Cp_solid is None or mineral.Vm_solid is None:
                raise ValueError(
                    f"{smi!r} is {mineral.name}, whose formation pair is "
                    "curated but whose crystal Cp or molar volume is not. A "
                    "species in the solid block has to say how much room it "
                    "takes and how much heat it holds; borrowing an ion's "
                    "placeholder for a mineral would be silent. Regenerate "
                    "mineral_data, or charge its ions instead: "
                    f"{list(mineral.ions)}."
                )
            vol_A[i] = NONVOLATILE_A         # 1e-30 bar; a crystal does not boil
            condensable[i] = False
            Tc[i] = 1.0                      # keeps the Watson factor defined
            v_liq[i] = (mineral.Vm_solid, 0.0, 0.0, 0.0)
            Cp_liq[i] = (mineral.Cp_solid, 0.0, 0.0, 0.0)
            # Unreachable -- nothing in this engine can put a lattice in the
            # headspace -- but a zero there would make a stray mole heat-free,
            # so the crystal's own constant stands in rather than nothing.
            Cp_gas[i] = (mineral.Cp_solid, 0.0, 0.0, 0.0)
            continue

        v = volatility.get(smi)
        c = condensed.get(smi)
        t = thermo.get(smi)

        vol_A[i], vol_B[i], vol_C[i] = v.A, v.B, v.C
        condensable[i] = v.condensable
        henry[i] = v.kind == "henry"
        reference_solvent[i] = v.reference_solvent
        Hvap_Tb[i] = (t.Hvap or 0.0) * 1000.0          # kJ/mol -> J/mol
        Tb[i] = t.Tb if t.Tb is not None else 0.0
        # Tc above Tb keeps the Watson factor well-defined even for odd estimates.
        Tc[i] = t.Tc if t.Tc is not None else max(Tb[i] * 1.5, 1.0)
        v_liq[i] = c.v_coeffs
        Cp_liq[i] = c.Cp_coeffs
        Cp_gas[i] = t.Cp_coeffs if t.Cp_coeffs is not None else (0.0, 0.0, 0.0, 0.0)

        # A species can crystallise only if we know what it costs to melt it.
        # Dissolved gases and ions have no solid state here and are excluded, so
        # the solubility law leaves them alone entirely.
        if v.condensable and t.Tm and t.Hfus:
            Hfus[i] = t.Hfus * 1000.0          # kJ/mol -> J/mol
            Tm[i] = t.Tm
            solidifies[i] = True

    # Activity coefficients, in whichever convention the species' reference state
    # calls for. A condensable species is symmetric: its reference is its own
    # pure liquid, gamma -> 1 as x -> 1, and gamma_ref stays zero.
    #
    # A Henry's-law solute has no pure liquid at these temperatures, so its
    # reference is infinite dilution in the solvent its constant was measured in.
    # Its gamma is divided by the value at that reference, which makes the
    # correction exactly 1 in that solvent -- reproducing the calibrated Henry
    # constant -- and equal to the ratio of infinite-dilution coefficients in any
    # other. That ratio IS the ratio of Henry constants, because the solute's
    # (hypothetical) pure-liquid fugacity cancels out of it:
    #
    #     H_i(S) / H_i(ref) = gamma_inf,i(S) / gamma_inf,i(ref)
    #
    # so oxygen in ethanol gets ethanol's solubility, computed rather than
    # assumed. Without this division the aqueous constant would be multiplied by
    # a symmetric gamma that already contains the same interaction, counting it
    # twice.
    activity = activity or UnifacProvider()
    act = build_activity_arrays(species, activity)
    gamma_ref = np.zeros((n, 4))

    for i, smi in enumerate(species):
        if not (henry[i] and act.active[i]):
            continue
        solvent = reference_solvent[i]
        state = (
            infinite_dilution_reference(smi, solvent, activity)
            if solvent is not None
            else None
        )
        if state is None:
            # No reference state available, so no honest way to transfer the
            # constant to another solvent. Fall back to the tabulated value by
            # holding the solute ideal, and say which species it happened to.
            act.active[i] = False
            act.unmodelled[smi] = (
                "Henry's-law solute with no usable reference state "
                f"(solvent {solvent!r} has no group decomposition); the "
                "tabulated constant is used unchanged"
            )
            continue
        gamma_ref[i] = state.coeffs
        act.reference_fits[smi] = state.error

    # Which species carry a charge. Layer 4 uses this to decide when the ION
    # TRANSFER model has to be checked before a liquid may split in two.
    from chemsim.matter import Molecule

    ionic = np.array(
        [Molecule.from_smiles(s).charge != 0 for s in species], dtype=bool
    )

    # The BORN block: what it costs an ion to leave the water. An ion has no
    # UNIFAC decomposition, so everything above skipped it -- which used to mean
    # gamma = 1, and equality of activity with gamma = 1 on both sides of an
    # interface is an ion at EQUAL MOLE FRACTION in water and in toluene. That is
    # why an electrolyte split had to be refused outright. See
    # ``properties/dielectric.py``: the transfer energy is referenced to water, so
    # it is exactly zero there and every water-anchored pKa in this project keeps
    # the value it was derived with.
    dielectric = dielectric or DielectricProvider()
    born = build_born_arrays(species, dielectric)

    arrays = PhaseArrays(
        vol_A, vol_B, vol_C, condensable, Hvap_Tb, Tb, Tc, v_liq, Cp_liq, Cp_gas,
        Hfus=Hfus, Tm=Tm, solidifies=solidifies, ionic=ionic,
        nu=act.nu, R_k=act.R_k, Q_k=act.Q_k, a_mn=act.a_mn,
        gamma_active=act.active, gamma_ref=gamma_ref,
        gamma_ref_range=np.array([T_REF_LO, T_REF_HI]),
        born_A=born.A, eps_coeffs=born.eps_coeffs, eps_range=born.eps_range,
        eps_ref_coeffs=born.eps_ref_coeffs, eps_ref_range=born.eps_ref_range,
    )
    return arrays, act, born


def build_precipitation_arrays(
    species: list[str],
) -> tuple[PrecipitationArrays, list[str]]:
    """Every ionic lattice this species set could drop, plus what it could not.

    M3. Layer 5's half of the precipitation term: this is where SMILES meet the
    mineral and ion tables, so that Layer 4 receives nothing but numbers.

    A lattice qualifies when **every one of its ions is a species in this
    vessel** and its ``Ksp`` prices on the aqueous basis. Both halves refuse
    loudly: ``solubility_product`` names the ion and the basis, and this function
    passes the refusal through into the report rather than dropping it, because
    "your silver never went cloudy" is otherwise indistinguishable from a bug.

    ⚠ Note which direction the species check runs. The lattice is not a species
    and never becomes one -- the SOLID BLOCK HOLDS THE IONS. So what has to be
    present is ``[Ag+]`` and ``[Cl-]``, which a network that dissociates silver
    nitrate and rock salt already has.
    """
    from chemsim.properties.mineral_data import MINERALS
    from chemsim.properties.solubility_product import (
        T_REF as KSP_T_REF,
        UnpricedLattice,
        solubility_product,
    )

    index = {s: i for i, s in enumerate(species)}
    n = len(species)
    rows: list[np.ndarray] = []
    names: list[str] = []
    ln_ksp: list[float] = []
    dH: list[float] = []
    dS: list[float] = []
    report: list[str] = []

    for name, record in MINERALS.items():
        missing = [ion for ion in record.ions if ion not in index]
        if missing:
            continue                      # not a candidate here; not a failure
        try:
            ksp = solubility_product(record)
        except UnpricedLattice as exc:
            report.append(
                f"{name}: every ion is present but the lattice has no Ksp -- "
                f"{str(exc).splitlines()[0]}"
            )
            continue
        row = np.zeros(n)
        for ion in record.ions:
            row[index[ion]] += 1.0
        rows.append(row)
        names.append(name)
        ln_ksp.append(ksp.ln_Ksp)
        dH.append(ksp.dH_diss * 1000.0)                        # kJ -> J
        dS.append((ksp.dH_diss - ksp.dG_diss) * 1000.0 / KSP_T_REF)

    nu = np.array(rows) if rows else np.zeros((0, n))
    return (
        PrecipitationArrays(
            nu=nu,
            total_nu=nu.sum(axis=1) if rows else np.zeros(0),
            ln_Ksp_ref=np.array(ln_ksp),
            dH_diss=np.array(dH),
            dS_diss=np.array(dS),
            names=tuple(names),
        ),
        report,
    )


def build_solid_state_arrays(
    species: list[str],
) -> tuple[SolidStateArrays, list[str]]:
    """Every solid-state reaction this species set can run, plus what it cannot.

    M6. Layer 5's half of the term, and the mirror of
    ``build_precipitation_arrays`` one function up -- with the species check
    running the OTHER WAY, which is the whole difference between the two
    representations.

    ⚠ Precipitation needs the IONS present, because the solid block holds ions
    and the lattice never becomes a species. This needs the LATTICE present,
    because a crystal that reacts while staying a crystal has no ion-by-ion
    form: quicklime ion-by-ion is ``[Ca+2].[O-2]``, and the oxide ion is in no
    aqueous table anywhere because it does not exist in water. Both
    representations of CaCO3 can be in one vessel and they are not the same
    species; nothing here reconciles them, and ``solid_state_report`` says so.

    A row qualifies when every mineral's LATTICE and every gas is a species
    here, and the declaration prices. Refusals pass through into the report
    rather than being dropped -- "the kiln did nothing" is otherwise
    indistinguishable from a bug.
    """
    from chemsim.properties.solid_state import (
        SOLID_STATE_REACTIONS,
        UnpricedSolidReaction,
        price,
    )

    thermo = ThermochemistryProvider()
    index = {s: i for i, s in enumerate(species)}
    n = len(species)
    rows_solid: list[np.ndarray] = []
    rows_gas: list[np.ndarray] = []
    names: list[str] = []
    dH: list[float] = []
    dS: list[float] = []
    A: list[float] = []
    Ea: list[float] = []
    report: list[str] = []

    for decl in SOLID_STATE_REACTIONS:
        lattices = {
            name: mineral_data.MINERALS[name].lattice
            for name, _ in decl.solids
            if name in mineral_data.MINERALS
        }
        missing = [
            name for name, _ in decl.solids
            if lattices.get(name) not in index
        ] + [smi for smi, _ in decl.gases if smi not in index]
        if missing:
            continue                      # not a candidate here; not a failure
        # ⚠ A GAS REACTANT IS REFUSED, and ``SolidStateArrays`` carries the
        # measurement: its pressure sits in the DENOMINATOR of Q, so an
        # atmosphere with none of it left drives the reverse flux to 2.6e15
        # formula units per second. That is the affinity form saying it is not
        # a rate law for a gas-CONSUMING surface reaction -- a different
        # mechanism, which wants the mass-action kernel.
        consuming = [smi for smi, nu in decl.gases if nu < 0]
        if consuming:
            report.append(
                f"{decl.name}: REFUSED -- {consuming} appear on the reactant "
                "side as gases. The affinity form puts a gas reactant's "
                "pressure in the denominator of Q, so an atmosphere depleted "
                "of it gives an unbounded reverse rate. A gas-consuming "
                "surface reaction (roasting; a solid catalyst) is a different "
                "mechanism and wants a third PHASE_INDEX entry, not this term."
            )
            continue
        try:
            priced = price(decl, thermo)
        except UnpricedSolidReaction as exc:
            report.append(
                f"{decl.name}: every species is present but the reaction has "
                f"no priced pair -- {str(exc).splitlines()[0]}"
            )
            continue
        row_s = np.zeros(n)
        for name, nu in decl.solids:
            row_s[index[lattices[name]]] += float(nu)
        row_g = np.zeros(n)
        for smi, nu in decl.gases:
            row_g[index[smi]] += float(nu)
        rows_solid.append(row_s)
        rows_gas.append(row_g)
        names.append(decl.name)
        dH.append(priced.dH)
        dS.append(priced.dS)
        A.append(priced.A)
        Ea.append(priced.Ea)

    nu_solid = np.array(rows_solid) if rows_solid else np.zeros((0, n))
    nu_gas = np.array(rows_gas) if rows_gas else np.zeros((0, n))
    return (
        SolidStateArrays(
            nu_solid=nu_solid,
            nu_gas=nu_gas,
            dH=np.array(dH),
            dS=np.array(dS),
            A_fwd=np.array(A),
            Ea_fwd=np.array(Ea),
            names=tuple(names),
        ),
        report,
    )


@dataclass
class Vessel:
    """A reaction vessel: contents, phases, temperature, and the boundary."""

    network: ReactionNetwork
    volume: float = 1.0            # L, total internal volume
    T: float = 298.15              # K, initial contents temperature
    T_env: float = 298.15          # K, room
    UA: float = 0.5                # W/K, how well it loses heat to the room
    Q_input: float = 0.0           # W, hotplate
    P_ambient: float = 1.01325     # bar
    kla: float = 5.0               # mol/(bar s), evaporation/condensation rate
    k_diss: float = 1.0e-2         # 1/s, dissolution / crystallisation rate
    k_vent: float = 1.0e3          # mol/(bar s), vent conductance
    # mol/s, how fast two liquid layers exchange -- i.e. how hard the funnel is
    # being SHAKEN. Settled layers meeting across a flat interface equilibrate
    # slowly; an emulsion equilibrates in seconds. "I did not shake it enough"
    # is a thing a player can do wrong.
    k_lle: float = 5.0
    # Whether a second liquid layer may form. Turning it off does NOT hide the
    # question: ``lle_report()`` still runs the stability test on demand and
    # says that the liquid wanted to split, because a silently single-phase
    # extraction is exactly the kind of confident wrong answer this project
    # refuses to give.
    lle: bool = True
    # Whether an ionic lattice may crystallise out of solution -- M3's term.
    # ⚠ On by default, unlike ``losses``, because a solubility product is
    # PHYSICS rather than an imperfection: a flask where AgCl stays dissolved is
    # not an idealised flask, it is a wrong one. Set False to measure what the
    # term is worth; ``precipitation_report`` still says which lattices this
    # vessel could have dropped, so turning it off cannot hide the question.
    precipitation: bool = True
    # Whether a crystal may REACT while staying a crystal -- M6's term.
    # ⚠ On by default for the same reason ``precipitation`` is: a kiln in which
    # limestone does not calcine is not an idealised kiln, it is a wrong one.
    # Set False to measure what the term is worth; ``solid_state_report`` still
    # says which reactions this vessel could have run.
    solid_state: bool = True
    heat_capacity: float = 50.0    # J/K, the glassware itself (see VesselConditions)
    ingress: dict[str, float] = field(default_factory=dict)  # mol/s into headspace
    # Composition of the room outside, as mole fractions. Air by default. Set it
    # to {"N#N": 1.0} for a glovebox, or {} for a vessel in a vacuum chamber --
    # with nothing outside, being below ambient pressure draws nothing back in.
    atmosphere: dict[str, float] = field(
        default_factory=lambda: {"N#N": 0.79, "O=O": 0.21}
    )

    # Film holdup on transfers. ``None`` is IDEAL MODE -- every transfer is
    # perfectly efficient, which is what the conservation and mass-closure tests
    # check and how you tell a loss from a bug. Left off by default for exactly
    # that reason: an invariant should not move because a default changed.
    losses: TransferLosses | None = None

    thermo: ThermochemistryProvider = None
    volatility: VolatilityProvider = None
    condensed: CondensedProvider = None
    activity: UnifacProvider = None
    dielectric: DielectricProvider = None

    def __post_init__(self) -> None:
        self.thermo = self.thermo or self.network.thermo or ThermochemistryProvider()
        self.volatility = self.volatility or VolatilityProvider(self.thermo)
        self.condensed = self.condensed or CondensedProvider(self.thermo, self.volatility)
        self.activity = self.activity or UnifacProvider()
        self.dielectric = self.dielectric or DielectricProvider()

        self.kinetics = self.network.to_arrays(self.thermo)
        self.species = self.kinetics.species
        # Cumulative film holdup, for reporting. Not part of the state vector:
        # the material is still in ``_nL`` where it physically is, and this is
        # only a record of how much of it failed to leave.
        self._holdup_moles = np.zeros(len(self.species))
        self._holdup_volume = 0.0
        # Same, for the adhering crystal crust. Also not part of the state
        # vector: the crystals are still in ``_nS``, stuck to this vessel's wall.
        self._crust_moles = np.zeros(len(self.species))
        self._crust_volume = 0.0
        self._idx = {s: i for i, s in enumerate(self.species)}
        self.phases, self.activity_model, self.born_model = build_phase_arrays(
            self.species, self.thermo, self.volatility, self.condensed,
            self.activity, self.dielectric,
        )

        ingress = np.zeros(len(self.species))
        for smi, rate in self.ingress.items():
            ingress[self._index(smi)] = rate

        # What the room is made of, so a vessel below ambient pressure draws the
        # right thing back in rather than nothing.
        #
        # This is all-or-nothing on purpose. Bulk flow carries the room's
        # composition, so a network holding O2 but not N2 would inhale PURE
        # OXYGEN until it reached one bar -- quintupling dissolved O2 and
        # oxidising everything in the flask. Renormalising is what produces
        # that; refusing to renormalise instead leaves the vessel unable to
        # repressurise and equally wrong. There is no honest way to run bulk
        # exchange against an atmosphere the network cannot represent, so a
        # vessel that cannot represent it keeps the old outward-only vent and
        # ``atmosphere_report`` says why.
        x_ambient = np.zeros(len(self.species))
        for smi, frac in self.atmosphere.items():
            try:
                x_ambient[self._index(smi)] = frac
            except KeyError:
                pass
        modelled = float(x_ambient.sum())
        if modelled < ATMOSPHERE_COMPLETE:
            missing = [s for s in self.atmosphere if s not in self._idx]
            self.atmosphere_report = (
                f"the room is only {modelled * 100:.0f}% modelled "
                f"(missing {', '.join(missing) or 'nothing'}), so this vessel "
                "vents outward but cannot draw the atmosphere back in"
            )
            x_ambient[:] = 0.0
        else:
            self.atmosphere_report = ""

        self.conditions = VesselConditions(
            volume=self.volume,
            T_env=self.T_env,
            UA=self.UA,
            Q_input=self.Q_input,
            P_ambient=self.P_ambient,
            kla=self.kla,
            k_diss=self.k_diss,
            k_vent=self.k_vent,
            k_lle=self.k_lle,
            lle=self.lle,
            heat_capacity=self.heat_capacity,
            ingress=ingress,
            x_ambient=x_ambient,
        )
        # M3: which ionic lattices this species set could drop, and why any
        # candidate could not be priced. Built even when the term is switched
        # off, so ``precipitation_report`` answers the same question either way.
        self.precipitation_arrays, self.precipitation_refusals = (
            build_precipitation_arrays(self.species)
        )
        # M6: which solid-state reactions this species set can run. Same
        # contract -- built even when the term is switched off.
        self.solid_state_arrays, self.solid_state_refusals = (
            build_solid_state_arrays(self.species)
        )
        self.integrator = VesselIntegrator(
            self.kinetics, self.phases, self.conditions,
            precipitation=(
                self.precipitation_arrays if self.precipitation else None
            ),
            solid_state=(
                self.solid_state_arrays if self.solid_state else None
            ),
        )

        self._nL = np.zeros(len(self.species))
        self._nL2 = np.zeros(len(self.species))
        self._nG = np.zeros(len(self.species))
        self._nS = np.zeros(len(self.species))
        self.t = 0.0

        # Molar masses, so the vessel can work out which layer floats. Layer 0
        # is allowed here (this module already resolves SMILES for ``_index``),
        # and it is what makes "drain the lower layer" a derived fact rather
        # than a label someone attached to a phase index.
        from chemsim.matter import Molecule

        self._molar_mass = np.array(
            [Molecule.from_smiles(s).molar_mass for s in self.species]
        )

    # -- charging ------------------------------------------------------------

    def _index(self, smiles: str) -> int:
        from chemsim.matter import Molecule

        key = Molecule.from_smiles(smiles).smiles
        if key not in self._idx:
            raise KeyError(
                f"{smiles!r} ({key}) is not a species in this network -- it must "
                "appear in the network's initial species or be reachable by a template"
            )
        return self._idx[key]

    def charge(self, amounts: dict[str, float], phase: str = "liquid") -> Vessel:
        """Add moles of each species to the liquid, headspace, or solid heap.

        Everything charged as a liquid lands in the PRIMARY layer, whatever is
        already there. It is not this method's business whether the result is
        one liquid or two -- that is decided by the stability test at the next
        integration, from the thermodynamics. Pouring toluene into water does
        not need to be announced as a two-phase operation; it just is one.
        """
        try:
            target = {
                "liquid": self._nL, "liquid2": self._nL2,
                "gas": self._nG, "solid": self._nS,
            }[phase]
        except KeyError:
            raise ValueError(
                f"phase must be 'liquid', 'liquid2', 'gas' or 'solid', got {phase!r}"
            ) from None
        for smi, mol in amounts.items():
            target[self._index(smi)] += mol
        return self

    def reset(self) -> Vessel:
        """Empty the vessel and rewind its clock. Configuration is preserved.

        ⚠ THE CUMULATIVE RECORDS GO TOO, and they used not to. A player retrying
        an experiment in the same flask saw the PREVIOUS attempt's holdup and crust
        reported back at them, plus whatever round-off the previous run's projection
        could not settle -- three readouts describing a run that no longer existed.
        Everything cleared here is a record of history rather than a piece of
        state, which is exactly why it was missed: none of it is in the state
        vector, so emptying the four amount blocks looked complete.
        """
        self._nL[:] = 0.0
        self._nL2[:] = 0.0
        self._nG[:] = 0.0
        self._nS[:] = 0.0
        self.t = 0.0
        self._holdup_moles[:] = 0.0
        self._holdup_volume = 0.0
        self._crust_moles[:] = 0.0
        self._crust_volume = 0.0
        self.integrator.created[:] = 0.0
        # The stability verdict and any refusal describe a liquid that is no longer
        # here, so they cannot be allowed to outlive it either.
        self.integrator.last_stability = None
        self.integrator.refused_split = 0.0
        self.integrator.refused_reason = ""
        self.integrator.refused_coverage = 1.0
        return self

    def fill_headspace(self, composition: dict[str, float] | None = None) -> Vessel:
        """Charge the headspace to ambient pressure with a given gas mixture.

        Defaults to air. Not decoration: dissolved O2 is what makes an open flask
        oxidize, and the Henry's-law path in Layer 4 is what carries it into the
        liquid -- so ``{"N#N": 1.0}`` is a genuine inert-atmosphere lever and not
        a cosmetic one.

        The AMOUNT depends on the headspace volume at the moment of the call,
        which is why this is a verb rather than a fixed charge: "open the flask
        to the room" means different moles once there is liquid in it.
        """
        mix = composition or {"N#N": 0.79, "O=O": 0.21}
        V_G = max(self.volume - self.liquid_volume - self.solid_volume, 0.0)
        n_total = self.P_ambient * V_G / (R_L_BAR * self.T)
        for smi, frac in mix.items():
            try:
                self._nG[self._index(smi)] += n_total * frac
            except KeyError:
                pass  # network doesn't include this gas; nothing to charge
        return self

    def fill_headspace_with_air(self) -> Vessel:
        """Air at ambient pressure -- an open flask. See ``fill_headspace``."""
        return self.fill_headspace()

    def set_shaking(self, k_lle: float) -> Vessel:
        """How hard two liquid layers are shaken together, mol/s.

        Distinct from ``set_stirring``, which is liquid<->vapour: a flask can be
        stirred hard under a condenser without ever bringing two layers into
        contact, and a separatory funnel is shaken and then deliberately left to
        settle. Zero means the layers are standing still and will not exchange.
        """
        self.k_lle = self.conditions.k_lle = float(k_lle)
        return self

    # -- operating controls --------------------------------------------------
    # Each writes through to the conditions object the integrator holds, so a
    # change takes effect on the very next step rather than at the next rebuild.

    def set_heat(self, watts: float) -> Vessel:
        """Turn the hotplate up or down."""
        self.Q_input = self.conditions.Q_input = float(watts)
        return self

    def set_environment(self, T_env: float) -> Vessel:
        """Move the vessel to a different room -- or an ice bath."""
        self.T_env = self.conditions.T_env = float(T_env)
        return self

    def set_vent(self, k_vent: float) -> Vessel:
        """Vent conductance. Zero seals the vessel, which lets pressure build."""
        self.k_vent = self.conditions.k_vent = float(k_vent)
        return self

    def set_stirring(self, kla: float) -> Vessel:
        """Mass-transfer coefficient between liquid and vapour -- i.e. agitation."""
        self.kla = self.conditions.kla = float(kla)
        return self

    # Which liquid block each ``phase`` argument names. "liquid" is both layers;
    # "upper" and "lower" are resolved from the computed densities at the moment
    # of the pour, which is what makes a separatory funnel work without anyone
    # declaring which layer is which.
    _LIQUID_PHASES = frozenset({"liquid", "upper", "lower", "liquid2"})

    def pour_into(
        self, other: Vessel, fraction: float = 1.0, phase: str = "liquid"
    ) -> float:
        """Move a fraction of one phase into another vessel. Returns moles moved.

        Transfers carry their contents' enthalpy, so the destination's temperature
        is the mole-weighted mixture rather than whichever vessel was written last.
        Pouring hot acid into cold water should warm the water, and it does.

        ``phase`` may be:

        ``"liquid"``
            both liquid layers, in the proportion this vessel holds them. What a
            transfer has always meant, and what it still means when there is
            only one.
        ``"lower"`` / ``"upper"``
            ONE layer -- a separatory funnel. Which block that is comes from the
            layer densities computed at the moment of the pour (mass over molar
            volume, both already in the vessel's own arrays), so nothing labels
            a phase index as aqueous or organic: run the same extraction with a
            dense chlorinated solvent instead of ether and the layers swap over
            by themselves. With one layer present, both names mean that layer.
        ``"gas"`` / ``"solid"``
            as before.

        **Everything liquid lands in the destination's PRIMARY layer**, whatever
        it was in here. The receiving flask then decides for itself whether it
        holds one liquid or two, from the same stability test any other charge
        goes through -- which is right, and is why "wash the organic layer with
        brine" needs no special case.
        """
        if not 0.0 <= fraction <= 1.0:
            raise ValueError(f"fraction must be in [0, 1], got {fraction}")
        if other.species != self.species:
            raise ValueError(
                "cannot pour between vessels built on different networks -- their "
                "species indices do not correspond"
            )
        if phase not in self._LIQUID_PHASES and phase not in ("gas", "solid"):
            raise ValueError(
                f"phase must be one of 'liquid', 'lower', 'upper', 'gas', "
                f"'solid', got {phase!r}"
            )

        if phase == "gas":
            return self._pour_block(other, self._nG, other._nG, fraction, "gas")
        if phase == "solid":
            return self._pour_block(
                other, self._nS, other._nS, fraction, "solid"
            )

        blocks = self._liquid_blocks_for(phase)
        total = 0.0
        for src in blocks:
            total += self._pour_block(other, src, other._nL, fraction, "liquid")
        return total

    def _liquid_blocks_for(self, phase: str) -> list[np.ndarray]:
        """The liquid block(s) a ``phase`` name selects, densest resolved here."""
        if phase == "liquid":
            return [self._nL, self._nL2]
        if phase == "liquid2":
            return [self._nL2]
        if float(self._nL2.sum()) <= 0.0:
            return [self._nL]          # one layer is both the upper and the lower
        dense_first = sorted(
            (self._nL, self._nL2), key=lambda b: -self.density_of(b)
        )
        return [dense_first[0] if phase == "lower" else dense_first[1]]

    def _pour_block(
        self,
        other: Vessel,
        src: np.ndarray,
        dst: np.ndarray,
        fraction: float,
        kind: str,
    ) -> float:
        """Move one block's share, applying whichever loss that stream suffers."""
        moved = src * fraction
        if kind == "liquid":
            moved = self._withhold_film(moved)
        elif kind == "solid":
            # A poured solid does not leave a liquid film -- it leaves crystals
            # stuck to the glass, which is a different mechanism with a
            # different scale law. Tipping a crop out of a flask is exactly the
            # operation that loses them.
            moved = self._withhold_crust(moved)
        total = float(moved.sum())
        if total <= 0.0:
            return 0.0

        # Mix temperatures by heat capacity before the inventories change.
        c_src = self._heat_capacity_of(moved, kind)
        c_dst = other.thermal_mass
        if c_src + c_dst > 0.0:
            other.T = (self.T * c_src + other.T * c_dst) / (c_src + c_dst)

        src -= moved
        dst += moved
        return total

    def filter_into(
        self,
        filtrate: Vessel | None,
        cake: Vessel | None = None,
        *,
        porosity: float = 0.4,
        passthrough: float = 0.0,
    ) -> FiltrationResult:
        """Separate this vessel's solid from its liquid. Returns what went where.

        The only new primitive solid isolation needs. Everything else in the
        workup vocabulary is already expressible:

        * **decant** is ``pour_into(other, phase="liquid")`` -- pour the liquor
          off and leave the solid behind. It always existed.
        * **wash** is charging solvent onto a cake and filtering again. It needs
          no verb of its own, and the reason that matters is that washing then
          costs what it really costs: the wash solvent dissolves some of your
          product, so a cleaner crop is a smaller one. That trade is not
          scripted anywhere -- it falls out of the solubility law.
        * **dry** is evaporation, which the vessel already does. Pull vacuum or
          warm the cake and the retained liquor boils off -- and as it goes, the
          solutes it carried become supersaturated and deposit onto the solid,
          which is exactly why an unwashed cake dries dirty.

        Two parameters, both physical rather than tuning knobs:

        ``porosity``
            The VOID FRACTION OF THE CAKE -- how much of the packed solid's bulk
            volume is space between crystals. The liquor held by capillarity is
            then what fits in those voids:

                V_held = porosity * V_solid / (1 - porosity)

            capped at the liquor actually present, because a cake cannot hold
            more than was poured onto it. **Dissolved species travel with it**, so
            a wet cake carries a share of everything in solution -- impurities,
            mother liquor, unreacted starting material. That is the whole reason
            washing exists, and a zero here would make filtration a perfect
            purification, which it emphatically is not. A well-pulled Buchner is
            ~0.4, gravity filtration through paper more, a centrifuge less.

            ⚠ **THIS USED TO BE A FRACTION OF THE LIQUOR AND THAT WAS THE WRONG
            SHAPE.** Retention is a property of the CAKE, not of the volume that
            happened to be filtered through it: 5% of a 1021 mL mother liquor is
            50 mL of holdup on 17 mL of crystals -- a cake three quarters liquor
            by volume, which is a slurry and not a cake. Worse, the error scaled
            with the wrong quantity: filter the same crop out of twice the liquor
            and it came out twice as dirty, when a real cake holds what its own
            voids hold and no more. The parameter was RENAMED rather than
            reinterpreted, so that every call site had to be looked at instead of
            silently meaning something new.
        ``passthrough``
            The fraction of solid that goes through the paper anyway -- fines,
            or a cracked cake. Zero by default because it is a defect rather
            than a mechanism, but it is here so that "my yield is low and I do
            not know why" can have an honest cause.

        Either destination may be ``None`` to discard that stream, which is what
        "filter off the solid and keep the filtrate" (or the reverse) means at
        the bench. The gas phase is not partitioned: headspace does not pour
        through a filter, so it stays with this vessel.
        """
        if not 0.0 <= porosity < 1.0:
            raise ValueError(
                f"porosity is the cake's void fraction and must be in [0, 1), "
                f"got {porosity}"
            )
        if not 0.0 <= passthrough <= 1.0:
            raise ValueError(f"passthrough must be in [0, 1], got {passthrough}")
        for dest in (filtrate, cake):
            if dest is not None and dest.species != self.species:
                raise ValueError(
                    "cannot filter between vessels built on different networks "
                    "-- their species indices do not correspond"
                )

        # Split every phase-resident amount in two. Solids follow the cake
        # except for the fines; liquid follows the filtrate except for what the
        # cake retains. Nothing is created or destroyed here -- the two shares
        # sum to the original by construction, which is what the conservation
        # test checks.
        # Both layers drain through the same paper, so the cake retains its
        # share of each and they arrive in the receiver as one liquid -- which
        # re-splits there if it is still immiscible. Keeping two layers distinct
        # through a filter funnel would be modelling a decanter, not a filter.
        liquid = self._nL + self._nL2
        solid_to_filtrate = self._nS * passthrough
        solid_to_cake = self._nS - solid_to_filtrate

        # How much liquor the cake's own voids hold, in litres, from the volume of
        # the solid that stays behind -- computed with the same Rackett molar
        # volume the RHS integrates, so a denser crop retains proportionally less
        # liquor without needing a parameter. The FINES are excluded: they leave
        # with the filtrate and have no voids on this side of the paper.
        #
        # Then converted back to a FRACTION of the liquor present, because the
        # split below has to carry every dissolved species in proportion -- a cake
        # holds a share of the solution it sat in, not a share of the solvent.
        V_liquor = self.volume_of(liquid)
        V_solid = self.volume_of(solid_to_cake)
        V_held = min(porosity * V_solid / (1.0 - porosity), V_liquor)
        held_fraction = V_held / V_liquor if V_liquor > 0.0 else 0.0
        liquid_to_cake = liquid * held_fraction
        liquid_to_filtrate = liquid - liquid_to_cake

        # The filtrate drains through the funnel and down the walls of whatever it
        # is collected in, so it wets glass exactly as a pour does and leaves the
        # same film behind. The CAKE's share does not: ``porosity`` is already
        # the liquid held in the cake's own voids, and taking a wall film off it
        # too would be counting the same physics twice under two names.
        #
        # The film stays here, in the flask being filtered from -- which is why a
        # chemist rinses the reaction flask into the funnel rather than accepting
        # it, and that recovery needs no new verb.
        withheld = liquid_to_filtrate - self._withhold_film(liquid_to_filtrate)
        liquid_to_filtrate = liquid_to_filtrate - withheld

        # And the crop leaves a crust of crystals stuck to the flask it grew in.
        # Taken off the cake's share only: the fines that go THROUGH the paper
        # were never on the wall to begin with, and charging them the crust too
        # would be pricing one crystal twice. Computed before ``_nL`` is
        # reassigned below, because the wetted area is the area the SLURRY
        # touched, not what is left after the liquor has gone.
        crust = solid_to_cake - self._withhold_crust(solid_to_cake)
        solid_to_cake = solid_to_cake - crust

        self._deposit(cake, liquid_to_cake, solid_to_cake)
        self._deposit(filtrate, liquid_to_filtrate, solid_to_filtrate)

        self._nL = withheld
        self._nL2 = np.zeros_like(self._nL2)
        self._nS = crust

        return FiltrationResult(
            cake_solid=float(solid_to_cake.sum()),
            cake_liquid=float(liquid_to_cake.sum()),
            filtrate_liquid=float(liquid_to_filtrate.sum()),
            filtrate_solid=float(solid_to_filtrate.sum()),
            retained_solid=float(crust.sum()),
        )

    def _deposit(
        self, dest: Vessel | None, liquid: np.ndarray, solid: np.ndarray
    ) -> None:
        """Add a liquid and a solid share to a vessel, mixing temperature in."""
        if dest is None:
            return
        c_src = self._heat_capacity_of(liquid, "liquid") + self._heat_capacity_of(
            solid, "liquid"          # a solid's Cp is carried on the liquid block
        )
        c_dst = dest.thermal_mass
        if c_src + c_dst > 0.0:
            dest.T = (self.T * c_src + dest.T * c_dst) / (c_src + c_dst)
        dest._nL += liquid
        dest._nS += solid

    # -- transfer losses -----------------------------------------------------

    def volume_of(self, moles: np.ndarray) -> float:
        """Volume in litres of an arbitrary liquid inventory, at this T.

        Uses the same Rackett molar-volume polynomial the RHS integrates, so the
        volume a transfer loss is computed from is the volume the vessel believes
        it has -- not a second estimate that could disagree with it. The
        ``liquid_volume`` property is this applied to the current contents.
        """
        from chemsim.numerics.vessel_integrator import _poly

        return float(moles @ np.maximum(_poly(self.phases.v_liq, self.T), 0.0))

    def _withhold_film(self, moles: np.ndarray) -> np.ndarray:
        """Hold back the wall film from a liquid transfer; return what leaves.

        The withheld share is scaled off the SAME composition as the transfer,
        because a film is the solution it drained from -- so dissolved species
        travel with it in exactly the proportion they were present, which is what
        makes rinsing worthwhile and what ``porosity`` already does for a filter
        cake.

        Whatever is withheld simply is not subtracted from this vessel, so it
        stays where it physically is: on the wall of the flask that was poured
        from. Nothing is created and nothing is destroyed, which is why the
        conservation invariants survive turning this on.
        """
        if self.losses is None:
            return moles
        volume = self.volume_of(moles)
        if volume <= 0.0:
            return moles
        holdup = self.losses.holdup_litres(volume)
        if holdup <= 0.0:
            return moles
        kept = min(1.0, holdup / volume)
        self._holdup_moles += moles * kept
        self._holdup_volume += holdup
        return moles * (1.0 - kept)

    def density_of(self, moles: np.ndarray) -> float:
        """kg/L of an arbitrary liquid inventory at this T -- mass over volume.

        Both halves come from arrays the vessel already carries: molar masses
        from Layer 0 and the same Rackett molar volume the RHS integrates. So
        which layer floats is DERIVED, and swapping ether for dichloromethane
        turns the funnel upside down without anything being relabelled.
        """
        volume = self.volume_of(moles)
        if volume <= 0.0:
            return 0.0
        return float(moles @ self._molar_mass) / volume / 1000.0

    @property
    def wetted_volume(self) -> float:
        """L of contents in contact with the wall -- liquid plus solid.

        What the crust's area law is evaluated on. A slurry wets glass with its
        whole bulk, and a dry crop tipped out of a flask still touched the wall,
        so both phases count.
        """
        return self.liquid_volume + self.solid_volume

    def _withhold_crust(self, solid: np.ndarray) -> np.ndarray:
        """Hold back the adhering crystal crust from a solid transfer.

        Same shape as ``_withhold_film`` and for the same reasons: the withheld
        share is scaled off the composition being moved, so a crop of two solids
        leaves both behind in the proportion they were present; and it is simply
        not subtracted from this vessel, so the crystals stay where they
        physically are -- stuck to the wall of the flask they grew in. Rinse it
        out and filter again and they come with it, which is why the
        countermeasure needed no code.

        The crust is an ABSOLUTE volume set by the wetted area, so it is capped
        at what is being moved rather than scaled by it. Tipping out a tenth of a
        crop does not leave a tenth of a crust; the crust is what fails to
        leave.
        """
        if self.losses is None:
            return solid
        volume = self.volume_of(solid)
        if volume <= 0.0:
            return solid
        crust = self.losses.crust_litres(self.wetted_volume)
        if crust <= 0.0:
            return solid
        kept = min(1.0, crust / volume)
        self._crust_moles += solid * kept
        self._crust_volume += min(crust, volume)
        return solid * (1.0 - kept)

    def crust_report(self) -> str:
        """Crystals left adhering to this vessel's wall, or "".

        Separate from ``holdup_report`` because they are separate mechanisms
        with separate cures, and a combined figure would hide which one is
        costing the yield -- which is the entire finding that produced this one.
        """
        if self.losses is None:
            return ""
        total = float(self._crust_moles.sum())
        if total <= 0.0:
            return ""
        ranked = sorted(
            ((s, float(self._crust_moles[i])) for i, s in enumerate(self.species)),
            key=lambda kv: -kv[1],
        )
        worst = ", ".join(f"{s} {v:.4g} mol" for s, v in ranked[:4] if v > 0.0)
        return (
            f"crystals left adhering to the wall: {total:.4g} mol in "
            f"{self._crust_volume * 1e3:.3g} mL over all transfers "
            f"(a {self.losses.crust_thickness * 1e6:.0f} um packed layer from a "
            f"{self.losses.crystal_size * 1e6:.0f} um crop); {worst}. "
            "It is still in this vessel -- rinse it through and re-filter to "
            "recover it, with mother liquor if you would rather not dissolve any."
        )

    @property
    def crust(self) -> dict[str, float]:
        """Per-species cumulative adhering crust, in moles."""
        return {s: float(self._crust_moles[i]) for i, s in enumerate(self.species)}

    def holdup_report(self) -> str:
        """Cumulative film holdup left on this vessel's wall, or "".

        Reported rather than left to be differenced out of two states, for the
        same reason ``FiltrationResult`` reports what it moved: a loss the player
        cannot see is indistinguishable from a bug, and this project's rule is
        that nothing is dropped without being named.
        """
        if self.losses is None:
            return ""
        total = float(self._holdup_moles.sum())
        if total <= 0.0:
            return ""
        ranked = sorted(
            ((s, float(self._holdup_moles[i])) for i, s in enumerate(self.species)),
            key=lambda kv: -kv[1],
        )
        worst = ", ".join(f"{s} {v:.4g} mol" for s, v in ranked[:4] if v > 0.0)
        return (
            f"film holdup retained on the wall: {total:.4g} mol in "
            f"{self._holdup_volume * 1e3:.3g} mL over all transfers "
            f"(film {self.losses.film_thickness * 1e6:.0f} um after "
            f"{self.losses.drain_time:g} s draining); {worst}. "
            "It is still in this vessel -- rinse and pour again to recover it."
        )

    @property
    def holdup(self) -> dict[str, float]:
        """Per-species cumulative holdup, in moles."""
        return {s: float(self._holdup_moles[i]) for i, s in enumerate(self.species)}

    def _heat_capacity_of(self, moles: np.ndarray, phase: str) -> float:
        from chemsim.numerics.vessel_integrator import _poly

        block = self.phases.Cp_gas if phase == "gas" else self.phases.Cp_liq
        return float(moles @ _poly(block, self.T))

    @property
    def thermal_mass(self) -> float:
        """J/K -- the glassware plus everything currently in it."""
        from chemsim.numerics.vessel_integrator import _poly

        Cp_l = _poly(self.phases.Cp_liq, self.T)
        return self.heat_capacity + float(
            (self._nL + self._nL2 + self._nS) @ Cp_l
            + self._nG @ _poly(self.phases.Cp_gas, self.T)
        )

    # -- stepping ------------------------------------------------------------

    def step(self, dt: float, **kw) -> VesselState:
        """Advance the vessel by dt seconds and return the new state."""
        y = self.integrator.pack(self._nL, self._nL2, self._nG, self._nS, self.T)
        y = self.integrator.step(y, dt, **kw)
        (self._nL, self._nL2, self._nG, self._nS,
         self.T) = self.integrator.unpack(y)
        self.t += dt
        return self.state()

    def wait_until(
        self,
        conditions: Condition | list[Condition],
        timeout: float,
        **kw,
    ) -> WaitOutcome:
        """Advance until a condition holds, or until ``timeout`` seconds pass.

        The verb a real procedure needs. "Reflux until the head stabilises",
        "cool until crystals appear", "acidify until pH 2" -- none of those is a
        duration, and the instant is DISCOVERED here (a scipy root, to solver
        tolerance) rather than guessed at by the caller. See
        ``vessel.conditions`` for the vocabulary and for the three conditions
        that had to be written differently than they read.

        Several conditions race: the first to be satisfied stops the run, which is
        how "cool until it crystallises, but give up after an hour" is said. The
        timeout is NOT optional and has no default, deliberately -- a wait with no
        bound is a hang, and a condition that never becomes true is an ordinary
        thing for a player to ask for.

        ⚠ THE CLOCK MOVES BY WHAT HAPPENED, not by what was asked for. That is the
        whole difference from ``step``: ``self.t`` advances by the ACTUAL elapsed
        time, so a caller driving several vessels has to advance the others by
        ``outcome.elapsed`` and not by the timeout.
        """
        want = [conditions] if isinstance(conditions, Condition) else list(conditions)
        if not want:
            raise ValueError("wait_until needs at least one condition")
        if timeout <= 0.0:
            raise ValueError(f"timeout must be positive, got {timeout}")
        roots = [compile_condition(c, self) for c in want]
        y = self.integrator.pack(self._nL, self._nL2, self._nG, self._nS, self.T)
        stop = self.integrator.step_until(y, timeout, roots, **kw)
        (self._nL, self._nL2, self._nG, self._nS,
         self.T) = self.integrator.unpack(stop.y)
        self.t += stop.elapsed
        return WaitOutcome(
            elapsed=stop.elapsed,
            fired=None if stop.fired is None else want[stop.fired],
            already=stop.already,
            timed_out=stop.fired is None,
            state=self.state(),
        )

    def run(self, duration: float, **kw):
        """Integrate over a duration in one solve; returns the scipy solution.

        Useful for plotting a trajectory. ``step`` is the game-facing entry point.
        """
        y0 = self.integrator.pack(self._nL, self._nL2, self._nG, self._nS, self.T)
        sol = self.integrator.run(y0, (0.0, duration), **kw)
        # ⚠ A failed solve used to be SWALLOWED here. ``sol.y[:, -1]`` is the
        # last point the solver reached, so a run that gave up after 0.2 s of a
        # 3600 s interval returned quietly with a plausible-looking state --
        # which is exactly how a broken integration turns into a wrong answer
        # instead of an error. ``step`` has always checked; ``run`` did not.
        if not sol.success:
            raise self.integrator._fail(
                y0,
                f"vessel integration failed after {float(sol.t[-1]):.4g} s of "
                f"{duration:.4g} s: {sol.message}",
            )
        # ⚠ And ``sol.success`` is necessary, not sufficient: the raw output is
        # checked before the projection tidies a cancelling dipole into something
        # plausible. See ``VesselIntegrator.check_raw_solution``.
        self.integrator.check_raw_solution(sol.y[:, -1])
        y = self.integrator.merge_phases(self.integrator.project(sol.y[:, -1]))
        (self._nL, self._nL2, self._nG, self._nS,
         self.T) = self.integrator.unpack(y)
        self.t += duration
        return sol

    # -- observation ---------------------------------------------------------

    def integrability_report(self) -> str:
        """Latent numerical fragilities of this vessel as it stands now, or "".

        Not an error and not a prediction of one -- a list of configurations that
        sit near a cliff this project has fallen off before. A frontend hands the
        driving to a player who will boil things dry, seal flasks and shake
        immiscible liquids together, and the rule for all of that is that a
        reachable state must either work or refuse with a reason. This is the third
        case: it works, and it is worth saying that it works narrowly.

        ``VesselIntegrator.diagnose`` is the same information delivered too late
        (attached to a failure); this is it delivered in time.
        """
        y = self.integrator.pack(self._nL, self._nL2, self._nG, self._nS, self.T)
        notes = self.integrator.fragilities(y)
        if not notes:
            return ""
        joined = "".join(f"{chr(10)}  - {note}" for note in notes)
        return f"{len(notes)} latent numerical fragility(ies):{joined}"

    def conservation_report(self) -> str:
        """What the non-negative projection could not conserve, or "".

        The projection that follows every solve keeps each species' total exactly
        (see ``numerics.vessel_integrator.project_non_negative``); the only
        residual it cannot settle is a species whose total went slightly negative,
        which is round-off rather than matter. Reported rather than swallowed,
        because "amounts were quietly adjusted" is precisely the class of silence
        this project does not allow -- and because a residual that stops being
        round-off sized is a real numerical problem worth seeing.
        """
        created = self.integrator.created
        bad = [
            (s, float(created[i]))
            for i, s in enumerate(self.species)
            if created[i] > 0.0
        ]
        if not bad:
            return ""
        bad.sort(key=lambda kv: -kv[1])
        worst = ", ".join(f"{s} {v:.2e} mol" for s, v in bad[:4])
        return (
            f"non-negative projection created {len(bad)} species' worth of "
            f"round-off it could not settle against a positive holding: {worst}"
        )

    def solid_state_report(self) -> str:
        """Which reactions between crystals this vessel can run, and at what
        temperature each becomes possible against the room.

        M6. Written the way ``lle_report`` and ``precipitation_report`` are: it
        answers the same question whether the term is on or off, because "the
        limestone just sat there" is otherwise indistinguishable from a bug.

        ⚠ THE TEMPERATURE IT PRINTS IS NOT A CONSTANT SOMEONE CHOSE. ``K(T)`` is
        the gas pressure a pair of crystals sits at; the reaction can only run to
        completion once that exceeds what the room is pushing back with. So the
        kiln temperature is where ``K(T) = P_ambient``, and it comes out of the
        CRC formation data rather than out of this file.
        """
        arr = self.solid_state_arrays
        lines: list[str] = []
        if not arr.m:
            lines.append(
                "no solid-state reaction is available in this vessel: none of "
                "the declared rows has all of its minerals AND gases as species "
                "here. Charge the lattice (properties/solid_state.lattice_"
                "species()), not its ions -- the two are different species and "
                "only the lattice can react as a solid."
            )
        for j, name in enumerate(arr.names):
            K = float(arr.equilibrium_pressure(self.T)[j])
            lo, hi = 200.0, 3000.0
            for _ in range(80):                       # bisect K(T) = P_ambient
                mid = 0.5 * (lo + hi)
                if float(arr.equilibrium_pressure(mid)[j]) < self.P_ambient:
                    lo = mid
                else:
                    hi = mid
            lines.append(
                f"{name}: dH {arr.dH[j] / 1000:+.1f} kJ/mol, "
                f"dS {arr.dS[j]:+.1f} J/(mol K); "
                f"K({self.T:.0f} K) = {K:.4g} bar, and it needs "
                f"{0.5 * (lo + hi):.0f} K to beat the room's "
                f"{self.P_ambient:.3f} bar"
            )
        if not self.solid_state:
            lines.append(
                "-- but solid_state=False on this vessel, so the term is OFF "
                "and no crystal will react."
            )
        lines.extend(self.solid_state_refusals)
        return "\n".join(lines)

    def energy_report(self) -> str:
        """The energy balance, the way ``state`` and ``conservation_report`` are
        the mass one: every watt the temperature equation sees, and how much
        cancellation each one is hiding.

        ⚠ WHY THE GROSS COLUMN EXISTS, AND IT IS THE WHOLE POINT OF THIS REPORT.
        M12 was an insulated flask that destroyed 495 J while conserving every
        atom to 1e-12. Nothing could see it: ``conservation_report`` audits
        MATTER, and a net reaction heat of 1e-3 W looks like a flask at rest
        whether it is one or whether it is two terms of 5.2e9 W cancelling to
        twelve digits. It was the second case. A cancellation that large turns
        the solver's ordinary error control -- denominated in kelvin and in
        moles, never in joules -- into an amplifier, and the temperature is the
        only slow variable it can accumulate in.

        So this reports the GROSS as well as the net, and the ratio between them
        is the number to read. A ratio near 1 is a flask doing chemistry; a ratio
        of 1e12 is a number about to be wrong. The standing bound is
        ``reactions.thermo.COLLISION_LIMIT``, which stops a DERIVED rate constant
        from being faster than the reactants can meet and is what keeps the ratio
        finite; see ``validation/rate_ceiling.py``.

        ⚠ It is a SNAPSHOT, not an accumulated balance. It says what the flask is
        doing now, not what it did over the last hour.
        """
        y = self.integrator.pack(self._nL, self._nL2, self._nG, self._nS, self.T)
        p = self.integrator.energy_terms(y)
        terms = p.get("q_rxn_terms")
        gross = float(np.abs(terms).sum()) if terms is not None else 0.0
        net = float(terms.sum()) if terms is not None and terms.size else 0.0
        lines = [
            f"energy balance at T = {p['T']:.4f} K, "
            f"heat capacity {p['Cp_total']:.2f} J/K",
            f"  reaction        {p['q_rxn']:+12.4e} W",
            f"  vaporisation    {p['q_vap']:+12.4e} W",
            f"  fusion/lattice  {p['q_fus']:+12.4e} W",
            f"  solid-state     {p.get('q_solid', 0.0):+12.4e} W",
            f"  wall loss       {p['q_loss']:+12.4e} W",
            f"  vent            {p['q_vent']:+12.4e} W",
            f"  applied         {p['Q_input']:+12.4e} W",
            f"  --------------- {p['q_sum']:+12.4e} W  "
            f"= {p['dT']:+.4e} K/s",
        ]
        if gross > 0.0:
            ratio = gross / abs(net) if net else float("inf")
            lines.append(
                f"  reaction heat is {gross:.4e} W gross against "
                f"{net:+.4e} W net (cancellation {ratio:.2e}x)"
            )
            if ratio > 1.0e6:
                lines.append(
                    "  !! THE NET REACTION HEAT IS A CANCELLATION OF TERMS MORE "
                    "THAN A MILLION TIMES LARGER. The temperature is integrating "
                    "the difference of two big numbers and no error control in "
                    "the solver is denominated in joules. See M12."
                )
        return "\n".join(lines)

    def state(self) -> VesselState:
        return VesselState(
            n_liquid={s: float(self._nL[i]) for i, s in enumerate(self.species)},
            n_gas={s: float(self._nG[i]) for i, s in enumerate(self.species)},
            n_solid={s: float(self._nS[i]) for i, s in enumerate(self.species)},
            n_liquid2={s: float(self._nL2[i]) for i, s in enumerate(self.species)},
            T=float(self.T),
            t=self.t,
        )

    @property
    def liquid_volume(self) -> float:
        """L of liquid in the flask, BOTH layers -- what the headspace is not."""
        return self.volume_of(self._nL) + self.volume_of(self._nL2)

    @property
    def solid_volume(self) -> float:
        """L. Solids are given the liquid molar volume -- real solids are ~10%
        denser, which is well inside the accuracy of everything around it."""
        from chemsim.numerics.vessel_integrator import _poly

        return float(self._nS @ np.maximum(_poly(self.phases.v_liq, self.T), 0.0))

    @property
    def gas_volume(self) -> float:
        return max(self.volume - self.liquid_volume - self.solid_volume, 0.0)

    @property
    def pressure(self) -> float:
        """bar, total headspace pressure (ideal gas).

        ⚠ A VESSEL EXACTLY FULL READS AMBIENT, NOT INFINITY. This used to divide by
        a gas volume of zero and return ``inf`` for a flask filled to the brim, and
        two rows of ``validation/robustness.py`` were exactly that. A flask with no
        headspace is not a flask at infinite pressure: it has nowhere for a gas to
        be, so its pressure is whatever presses on it from outside. Holding gas
        with no room for it is a different thing entirely and is not a state --
        ``VesselIntegrator.check_capacity`` refuses it, with the overflow named, so
        nothing downstream ever has to render it.
        """
        V_G = self.gas_volume
        if V_G <= 0.0:
            return self.P_ambient
        return float(self._nG.sum()) * R_L_BAR * self.T / V_G

    def partial_pressures(self) -> dict[str, float]:
        """bar per species. A vessel with no headspace has no partial pressures --
        see ``pressure`` for why that is a full flask rather than an infinite one."""
        V_G = self.gas_volume
        if V_G <= 0.0:
            return {s: 0.0 for s in self.species}
        p = self._nG * R_L_BAR * self.T / V_G
        return {s: float(p[i]) for i, s in enumerate(self.species)}

    # -- the liquid layers ---------------------------------------------------
    # ⚠ Every composition readout below is per LAYER, and defaults to the
    # primary one. A mixture-average over two immiscible layers is the single
    # number that describes neither of them -- an "average concentration" across
    # water and toluene is not a quantity anybody can measure. With one layer,
    # which is still the usual case, every one of these is exactly what it
    # always was.

    def _layer(self, layer: int) -> np.ndarray:
        try:
            return (self._nL, self._nL2)[layer]
        except IndexError:
            raise ValueError(f"layer must be 0 or 1, got {layer}") from None

    @property
    def two_phase(self) -> bool:
        """Whether the liquid has actually separated into two layers."""
        return float(self._nL2.sum()) > 0.0

    def layers(self) -> list[dict]:
        """One entry per liquid layer, DENSEST LAST -- i.e. bottom of the flask.

        The ordering is computed, not declared: each layer's density comes from
        its own composition through the vessel's molar masses and molar volumes.
        That is what makes ``pour_into(phase="lower")`` mean the same thing for
        an ether extraction (organic on top) and a dichloromethane one (organic
        underneath) without either being special-cased.
        """
        out = []
        for i, block in enumerate((self._nL, self._nL2)):
            total = float(block.sum())
            if total <= 0.0:
                continue
            out.append({
                "layer": i,
                "moles": total,
                "volume": self.volume_of(block),
                "density": self.density_of(block),
                "composition": {
                    s: float(block[j] / total)
                    for j, s in enumerate(self.species)
                    if block[j] > 0.0
                },
            })
        out.sort(key=lambda d: d["density"])
        return out

    def aqueous_layer(self) -> int:
        """Index of the layer richest in water -- where a pH electrode would sit.

        Falls back to the primary layer when the network has no water at all,
        which is the only honest answer: pH is a statement about an aqueous
        phase, and without one there is nothing to be right about.
        """
        if not self.two_phase:
            return 0
        try:
            w = self._index("O")
        except KeyError:
            return 0
        n1, n2 = float(self._nL.sum()), float(self._nL2.sum())
        x1 = float(self._nL[w]) / n1 if n1 > 0.0 else 0.0
        x2 = float(self._nL2[w]) / n2 if n2 > 0.0 else 0.0
        return 1 if x2 > x1 else 0

    def concentrations(self, layer: int = 0) -> dict[str, float]:
        """mol/L within one liquid layer -- the numbers a chemist actually quotes."""
        block = self._layer(layer)
        V_L = self.volume_of(block)
        if V_L <= 0.0:
            return {s: 0.0 for s in self.species}
        return {s: float(block[i] / V_L) for i, s in enumerate(self.species)}

    def mole_fractions(self, layer: int = 0) -> dict[str, float]:
        block = self._layer(layer)
        total = float(block.sum())
        if total <= 0.0:
            return {s: 0.0 for s in self.species}
        return {s: float(block[i] / total) for i, s in enumerate(self.species)}

    def partition(self, smiles: str) -> float:
        """Ratio of a species' CONCENTRATION in one layer to the other.

        The distribution coefficient an extraction is designed around, and it is
        measured off the state rather than tabulated: it is whatever equality of
        activity produced. Returns nan with only one layer, because a partition
        coefficient between a phase and nothing is not a number.
        """
        if not self.two_phase:
            return float("nan")
        i = self._index(smiles)
        v1, v2 = self.volume_of(self._nL), self.volume_of(self._nL2)
        if v1 <= 0.0 or v2 <= 0.0:
            return float("nan")
        c2 = float(self._nL2[i]) / v2
        if c2 <= 0.0:
            return float("inf")
        return (float(self._nL[i]) / v1) / c2

    def held_ideal(self, layer: int = 0) -> tuple[float, dict[str, float]]:
        """What fraction of a liquid layer has NO activity model, and which species.

        A species with no UNIFAC decomposition is silently given gamma = 1. That
        is not a small error in a phase calculation and it is not a symmetric
        one: an ideal liquid never splits, so everything held ideal argues for
        one phase and for two layers being more alike than they are.

        Returns the mole fraction of the layer that is neutral and held ideal,
        and the species making it up, largest first. IONS ARE EXCLUDED and the
        distinction is the point -- an ion at gamma = 1 is a stated policy with
        the Born term doing the part that decides partitioning, while a neutral
        organic at gamma = 1 is nothing but a gap. See ``numerics.lle``.
        """
        fraction, x = held_ideal_fraction(
            self._layer(layer), self.phases.gamma_active, self.phases.ionic
        )
        named = {
            self.species[i]: float(x[i])
            for i in np.argsort(-x)
            if x[i] > 0.0
        }
        return fraction, named

    def _ideal_caveat(self, layer: int = 0, label: str = "") -> str:
        """The held-ideal flag for one layer, or "" when there is nothing to say.

        Threshold and its arithmetic in ``numerics.lle.IDEAL_FRACTION_REPORT``:
        it is the ideal mole fraction at which the worst case measured can move
        a layer composition by 0.01, which is one unit in the last digit this
        report prints.
        """
        fraction, named = self.held_ideal(layer)
        if fraction < IDEAL_FRACTION_REPORT:
            return ""
        listed = ", ".join(f"{s} {x:.3f}" for s, x in list(named.items())[:4])
        if len(named) > 4:
            listed += f", and {len(named) - 4} more"
        where = f" of {label}" if label else ""
        return (
            f"{fraction:.1%}{where} is NEUTRAL species with no UNIFAC "
            f"decomposition, held at gamma = 1 rather than computed ({listed})"
        )

    def lle_report(self) -> str:
        """What the liquid-liquid phase test has to say about this flask, or "".

        Runs the tangent-plane test on demand, so it answers even when the
        vessel was built with ``lle=False`` -- a liquid that WANTED to split and
        was held as one phase is exactly the kind of quiet wrong answer this
        project reports rather than commits.

        ⚠ AND IT IS NOT EMPTY MERELY BECAUSE THE ANSWER IS "one stable phase".
        That answer can rest on activity coefficients that were never computed:
        a neutral species with no UNIFAC decomposition is held at gamma = 1, an
        ideal liquid never splits, and so the omission always argues for the
        very answer that would otherwise be reported in silence. When enough of
        the liquid is held ideal to move the split -- see
        ``numerics.lle.IDEAL_FRACTION_REPORT``, which is measured rather than
        chosen -- this says so instead of returning "".
        """
        if self.two_phase:
            layers = self.layers()
            parts = [
                f"layer {d['layer']} {d['volume'] * 1e3:.1f} mL at "
                f"{d['density']:.3f} kg/L ("
                + ", ".join(
                    f"{s} {x:.3f}"
                    for s, x in sorted(
                        d["composition"].items(), key=lambda kv: -kv[1]
                    )[:3]
                )
                + ")"
                for d in layers
            ]
            head = "two liquid layers, lightest first: " + "; ".join(parts)
            caveats = [
                c for c in (
                    self._ideal_caveat(d["layer"], f"layer {d['layer']}")
                    for d in layers
                ) if c
            ]
            if caveats:
                head += (
                    " -- but these compositions are soft: "
                    + "; ".join(caveats)
                )
            return head
        if float(self._nL.sum()) <= 0.0:
            return ""
        result = self.integrator.stability_of(self._nL, self.T)
        if not result.unstable:
            # ⚠ THE QUIET CASE, AND THE ONLY ONE WHERE SILENCE IS ITSELF THE
            # WRONG ANSWER. Everywhere else this method has something to report
            # and the caveat rides along with it; here the caveat IS the report.
            caveat = self._ideal_caveat()
            if not caveat:
                return ""
            return (
                "this liquid is stable as one phase -- but " + caveat
                + ". An ideal liquid never splits, so that verdict is the one "
                "the missing model was always going to give"
            )
        rich = ", ".join(
            f"{self.species[i]} {result.composition[i]:.3f}"
            for i in np.argsort(-result.composition)[:3]
            if result.composition[i] > 1e-3
        )
        head = (
            f"this liquid is UNSTABLE as one phase (tangent-plane distance "
            f"{result.tm:.4f}) and wants to separate into a layer richest in "
            f"{rich}"
        )
        # Recomputed here rather than read off the last integration, so the
        # report is a function of the state in front of you: asking before the
        # first step must give the same answer as asking after it.
        #
        # ⚠ An electrolyte used to be refused outright at this point. It is not
        # any more -- the Born transfer term prices what it costs an ion to leave
        # the water -- so what is left to say is only which of the two NARROW
        # refusals applies, and neither fires for ordinary chemistry. See
        # ``VesselIntegrator.split_phases``.
        refusal = self._split_refusal(self._nL, result.composition)
        caveat = self._ideal_caveat()
        tail = f" ({caveat}, so where the tie line lands is soft)" if caveat else ""
        if refusal:
            return head + tail + " -- but " + refusal
        if self.lle:
            return head + tail + " -- it will do so at the next integration"
        return (
            head + tail + " -- but this vessel was built with lle=False, so it "
            "is being held as a single phase and every concentration in it is "
            "wrong"
        )

    def _split_refusal(self, n_liquid, trial) -> str:
        """Why an electrolyte split would be refused, or "" if it would not.

        Mirrors ``VesselIntegrator.split_phases``'s two checks in Layer 5's
        vocabulary. It recomputes rather than reading the integrator's record so
        that asking before the first step gives the same answer as asking after
        it -- the same reason the stability test itself is recomputed here.
        """
        total = float(np.maximum(n_liquid, 0.0).sum())
        if total <= 0.0:
            return ""
        ionic = float(n_liquid[self.phases.ionic].sum()) / total
        if ionic <= IONIC_SPLIT_LIMIT:
            return ""
        unpriced_ions = self.born_model.unpriced_ions
        present = [
            s for s in unpriced_ions
            if s in self._idx and n_liquid[self._idx[s]] / total > BORN_TRACE
        ]
        if present:
            return (
                "the liquid holds ION(S) with no Born coefficient ("
                + "; ".join(f"{s}: {unpriced_ions[s]}" for s in present)
                + "), so their transfer between layers is unpriced and they "
                "would partition to equal mole fraction. The split is REFUSED "
                "rather than approximated and the liquid is held as one phase"
            )
        v_mol = np.maximum(_poly(self.phases.v_liq, self.T), 0.0)
        cover = min(
            self.integrator._permittivity_coverage(n_liquid, v_mol),
            self.integrator._permittivity_coverage(np.asarray(trial, float), v_mol),
        )
        if cover < BORN_COVERAGE_MIN:
            unknown = ", ".join(sorted(self.born_model.unpriced)) or "(none named)"
            return (
                f"only {cover:.1%} of the proposed layers' volume has a measured "
                f"relative permittivity (floor {BORN_COVERAGE_MIN:.0%}), so their "
                "polarity is not known and the ions in them would get no Born "
                f"term at all. Unpriced: {unknown}. The split is REFUSED rather "
                "than approximated and the liquid is held as one phase"
            )
        return ""

    def electrolyte_report(self) -> str:
        """What the ION TRANSFER model does and does not cover here, or "".

        Separate from ``lle_report`` because it is a statement about the MODEL
        rather than about this flask's current state: which ions were priced and
        how, which liquids have no measured permittivity, and whether the
        activity-coefficient clip is being hit. Empty for a network with no ions.
        """
        if not self.phases.has_ions:
            return ""
        lines = []
        priced = [
            (s, self.born_model.A[i])
            for i, s in enumerate(self.species)
            if self.born_model.A[i] > 0.0
        ]
        lines.append(
            f"{len(priced)} ion(s) priced by a Born transfer term, referenced to "
            "infinite dilution in water (so exactly gamma = 1 there, at every "
            "temperature -- which is why no pKa in this project moved):"
        )
        for s, A in sorted(priced, key=lambda kv: -kv[1]):
            lines.append(
                f"    {s:14s} A = {A / 1000.0:8.1f} kJ/mol   "
                f"[{self.born_model.sources.get(s, '')}]"
            )
        # What that term is worth in the layers actually present, which is the
        # only number a reader should act on.
        born = self.phases.born_block(self.T)
        if born is not None:
            for layer, amounts in ((1, self._nL), (2, self._nL2)):
                if float(amounts.sum()) <= 0.0:
                    continue
                held = np.maximum(amounts, 0.0)
                ln = born_ln_gamma(held, born, self.T)
                raw = born_ln_gamma(held, born, self.T, clip=False)
                worst = int(np.argmax(np.abs(ln)))
                eps = self.layer_permittivity(layer)
                # ⚠ A CEILED VALUE MUST SAY SO AND SAY BY HOW MUCH. The ceiling is
                # a resolution limit rather than a thermodynamic claim (see
                # ``activity.LN_GAMMA_BORN_MAX``), so a reader has to be able to
                # tell a computed transfer energy from a cut-off one -- otherwise
                # the number looks like a prediction.
                cut = np.flatnonzero(np.abs(raw) > np.abs(ln) + 1.0e-9)
                note = (
                    "  -- AT THE CEILING, cut from "
                    + ", ".join(
                        f"{self.species[i]} {raw[i]:+.0f}" for i in cut[:4]
                    )
                    if cut.size
                    else ""
                )
                lines.append(
                    f"  layer {layer}: permittivity {eps:.2f}, largest ion "
                    f"ln gamma {ln[worst]:+.1f} ({self.species[worst]}){note}"
                )
        report = self.born_model.report()
        if report:
            lines.append(report)
        return "\n".join(lines)

    def layer_permittivity(self, layer: int = 1) -> float:
        """Relative permittivity of a liquid layer, by Oster's rule.

        The readout behind every ion's transfer energy, and the reason a solvent
        choice is a lever: it is 78 for the aqueous layer and 2.4 for a toluene
        one, computed from the composition rather than labelled.
        """
        amounts = np.maximum(self._nL if layer == 1 else self._nL2, 0.0)
        if float(amounts.sum()) <= 0.0:
            return 0.0
        v_mol = np.maximum(_poly(self.phases.v_liq, self.T), 0.0)
        return oster_permittivity(
            amounts * v_mol,
            self.phases.permittivity(self.T),
            medium=self.phases.born_A <= 0.0,
        )

    def solids(self) -> dict[str, float]:
        """Moles of each species present as an undissolved solid."""
        return {
            s: float(self._nS[i])
            for i, s in enumerate(self.species)
            if self._nS[i] > 0.0
        }

    def activity_coefficients(self, layer: int = 0) -> dict[str, float]:
        """Liquid-phase activity coefficient of each species, at the current state.

        1.0 means ideal -- either genuinely (a pure liquid) or because the species
        has no UNIFAC model. ``activity_model.report()`` says which.
        """
        gamma = self.integrator.activity_coefficients(self._layer(layer), self.T)
        return {s: float(gamma[i]) for i, s in enumerate(self.species)}

    def solubility_limits(self, layer: int = 0) -> dict[str, float]:
        """Saturation mole fraction of each crystallisable species, at this state."""
        gamma = self.integrator.activity_coefficients(self._layer(layer), self.T)
        x_sat = self.integrator.solubility(self.T, gamma)
        return {
            s: float(x_sat[i])
            for i, s in enumerate(self.species)
            if self.phases.solidifies[i]
        }

    def saturation(self, layer: int = 0) -> dict[str, float]:
        """Ratio of each solute's mole fraction to its solubility limit.

        Below 1 the species is undersaturated and any solid will dissolve; above 1
        it is supersaturated and will crystallise out. Exactly the number a chemist
        watches when deciding whether a recrystallisation will work.
        """
        x = self.mole_fractions(layer)
        x_sat = self.solubility_limits(layer)
        return {s: x[s] / v for s, v in x_sat.items() if v > 0.0}

    @property
    def pH(self) -> float:
        """-log10 of the hydronium concentration, or nan if the network has none.

        A readout, not a state variable: the proton concentration comes out of the
        same mass-action integrator as everything else, because acid dissociation
        is entered as ordinary reversible reactions whose equilibrium constants are
        fixed by detailed balance from pKa. Nothing here solves a pH equation.

        With two layers it is read in the AQUEOUS one, because that is where an
        electrode goes and because diluting a proton count by the volume of an
        organic layer it was never in would be arithmetic rather than chemistry.
        """
        from chemsim.matter import Molecule

        key = Molecule.from_smiles("[OH3+]").smiles
        if key not in self._idx:
            return float("nan")
        block = self._layer(self.aqueous_layer())
        V_L = self.volume_of(block)
        if V_L <= 0.0:
            return float("nan")
        c = float(block[self._idx[key]]) / V_L
        if c <= 0.0:
            return float("inf")
        return -np.log10(c)

    @property
    def is_boiling(self) -> bool:
        """True when the liquid's equilibrium vapour pressure reaches ambient.

        This is a *readout*, not a switch -- nothing in the integrator consults it.
        A flask that has boiled dry is not boiling, however hot it gets, so a
        residue below the dry-out scale doesn't count.
        """
        from chemsim.numerics.vessel_integrator import DRYOUT_MOLES

        if float(self._nL.sum() + self._nL2.sum()) <= DRYOUT_MOLES:
            return False
        # ⚠ CONDENSABLE SPECIES ONLY. Dissolved air returns the headspace's own
        # partial pressures by Henry's law, so summing everything made this True
        # at any temperature for any flask left open to the room -- see
        # ``VesselIntegrator.volatile_pressure``.
        return self.integrator.volatile_pressure(
            self._nL, self.T, self._nL2
        ) >= self.P_ambient

    def bubble_point(self, lo: float = 200.0, hi: float = 700.0) -> float:
        """K, the temperature at which the current liquid would boil.

        Found by bisection on the same equilibrium-pressure expression the solver
        uses, so it agrees with the dynamics by construction rather than by a
        separately tabulated boiling point.
        """
        def excess(T: float) -> float:
            # Condensables only, for the reason ``is_boiling`` gives: with
            # dissolved air counted this bisection returned the CURRENT
            # temperature, whatever it was.
            return self.integrator.volatile_pressure(
                self._nL, T, self._nL2
            ) - self.P_ambient

        if self._nL.sum() + self._nL2.sum() <= 0.0:
            return float("nan")
        if excess(lo) > 0.0:
            return lo
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if excess(mid) < 0.0:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def describe(self) -> str:
        lines = [
            f"t={self.t:9.1f} s   T={self.T:7.2f} K   P={self.pressure:6.3f} bar"
            f"   V_liq={self.liquid_volume * 1000:7.2f} mL"
            f"   {'BOILING' if self.is_boiling else ''}"
        ]
        conc = self.concentrations()
        for s in self.species:
            nL, nG = self._nL[self._idx[s]], self._nG[self._idx[s]]
            if nL + nG < 1e-9:
                continue
            lines.append(
                f"    {s:<18} liq {nL:8.4f} mol ({conc[s]:7.3f} M)   vap {nG:9.5f} mol"
            )
        if self.two_phase:
            conc2 = self.concentrations(1)
            lines.append("    -- second liquid layer --")
            for s in self.species:
                nL2 = self._nL2[self._idx[s]]
                if nL2 < 1e-9:
                    continue
                lines.append(
                    f"    {s:<18} liq {nL2:8.4f} mol ({conc2[s]:7.3f} M)"
                )
        return "\n".join(lines)
