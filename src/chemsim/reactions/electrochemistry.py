"""Layer 2 -- M8: the electrode templates, and what makes them electrode templates.

Four templates and one idea. The idea is in ``ReactionTemplate.electrons`` and
``thermo.reaction_deltas``: a cell does ``n F E`` joules of work on the reaction,
that work is subtracted from the reaction's Gibbs energy, and a reaction whose
chemistry costs less than the cell supplies runs. The voltage at which the two
balance is the DECOMPOSITION POTENTIAL, and it is the whole mechanic --

    E_dec = dG_chem / (n F)

-- so this module adds no gate, no flag and no term. It writes four cell
reactions and declares how many electrons each passes.

WHAT A CELL REACTION IS HERE, AND WHY IT IS THE WHOLE CELL

An electrode reaction is a HALF reaction: ``2 Cl- -> Cl2 + 2 e-`` does not
conserve charge, and a species list that does not conserve charge is exactly what
``builder._element_charge_balance`` rejects. There is no electron species and
there should not be one -- an electron in this project would be a state-vector
entry with a concentration, and the electrons in a cell are not in the flask,
they are in the wire.

So every template here is a WHOLE CELL: the anode half plus the cathode half,
electrons cancelled, charge balanced on both sides. That is not a compromise, it
is what the catalog rows already say -- ``sodium-chloride + water ->
sodium-hydroxide + chlorine + hydrogen`` is the cell, not the anode -- and it is
what makes the arithmetic honest, because ``dG`` of a half reaction is not
measurable without a reference electrode and ``dG`` of a cell is.

⚠ **THE PRICE IS THAT THE TWO ELECTRODES CANNOT BE PAIRED FREELY.** A real cell's
anode reaction and cathode reaction are chosen independently by the electrode
material and the potential; here each pairing is a separate template that has to
be written. Four templates are four pairings, not two anodes times two cathodes.
That is a representation limit and it is the reason ``hall-heroult`` and
``downs-cell`` are not here even setting their species aside: both are MOLTEN
SALT cells, and a melt is a phase this project does not have.

WHAT ``Ea`` MEANS ON THESE, AND IT IS NOT AN INVENTED NUMBER

``ReactionTemplate``'s docstring records the identity in full: with the cell's
work inside ``dH``, Evans-Polanyi IS the Butler-Volmer equation and ``alpha`` IS
the transfer coefficient, at its conventional 0.5. What that makes ``Ea`` is the
ACTIVATION OVERPOTENTIAL in energy units,

    Ea = n F eta_a

where ``eta_a`` is the volts a real cell needs ON TOP of its decomposition
potential before it passes appreciable current. Those are measured quantities
with a century of Tafel data behind them, and the two that matter here are wide
apart: oxygen evolution is notoriously sluggish (``eta_a`` around 0.5 V on most
anodes) and chlorine evolution is not (around 0.1 V on a coated titanium anode).
**That gap is the entire reason a brine cell makes chlorine rather than the
oxygen its thermodynamics prefers**, and declaring it as a barrier in joules is
the only way this engine can express it.

⚠ **AND IT IS MEASURED TO WASH OUT AT HIGH VOLTAGE -- SEE
``validation/cell_potentials.py``.** ``barrier`` floors at zero, so far above
``E_dec`` every electrode reaction runs out of barrier at its own rate and the
selectivity goes with it. A real cell is transport-limited there; this one is
not limited by anything, because nothing here budgets CURRENT. Reported, not
tuned away.
"""

from __future__ import annotations

from chemsim.constants import FARADAY
from chemsim.reactions.template import ReactionTemplate

# The electrochemical transfer coefficient, dimensionless, in [0, 1]. 0.5 is the
# symmetric barrier every Butler-Volmer treatment starts from and the value
# measured for most one-electron transfers at a metal electrode. It arrives here
# as ``ReactionTemplate.alpha`` because the two really are the same coefficient
# -- see that class's docstring for the algebra.
TRANSFER_COEFFICIENT = 0.5

# Pre-exponential for an electrode reaction: the rate in mol/(L s) at unit
# concentrations and zero barrier.
#
# ⚠⚠ **AND IT IS NOT A COLLISION FREQUENCY, WHICH IS THE THING THIS NUMBER GOT
# WRONG FIRST AND THE SOLVER IS WHAT SAID SO.** Every other pre-exponential in
# this project is a homogeneous one, bounded above by ``thermo.COLLISION_LIMIT``
# because two dissolved molecules cannot react faster than they meet. **An
# electrode reaction is not two molecules meeting.** It happens on a SURFACE, its
# rate is proportional to electrode AREA and not to volume, and the molecules in
# the bulk are not at the electrode at all. Declaring it at 1e10 asserts that
# every chloride in the flask is touching the anode.
#
# What it cost, measured, before it was fixed: at 1e10 a cell at 3.0 V consumed
# 0.2 mol of chloride inside a nanosecond and ``Vessel.run`` died with *required
# step size is less than spacing between numbers* after 4.2e-09 s of a 3600 s
# interval. The rate cap had been firing at the low-voltage end too, scaling the
# pair by 4.031e-14 -- both are the same wrong ceiling seen from two ends.
#
# THE RIGHT UNITS, AND WHERE THE VALUE COMES FROM. An electrode reaction's rate
# is a CURRENT DENSITY divided by the charge it carries:
#
#     rate [mol/(L s)] = j0 [A/cm2] * a [cm2/L] / (n F [C/mol])
#
# with ``j0`` the exchange current density and ``a`` the electrode area per litre
# of electrolyte. For a bench cell -- a pair of 10 cm2 electrodes in a litre,
# ``j0`` around 1e-3 A/cm2 for halogen evolution on a coated anode, n = 2 --
#
#     5e-8 = 1e-3 * 10 / (2 * 96485)
#
# and the sanity check is that it comes back out as an ampere: 5e-8 mol/(L s) at
# unit concentrations is 1e-2 A, and the cells below draw between a milliamp and
# a couple of amps. **That is what makes the value defensible: it is a current,
# and a current is a thing a bench power supply has.**
#
# ⚠ ONE VALUE FOR ALL FOUR, DELIBERATELY, BECAUSE THE SELECTIVITY MUST COME FROM
# THE BARRIER. A real ``j0`` differs by orders of magnitude between oxygen and
# chlorine evolution -- but that difference IS the overpotential, by
# ``eta_a = (RT / alpha n F) ln(j / j0)``, and it is already declared once as
# ``eta_a``. Splitting it across both would count it twice and would let an
# author choose which product a flask makes while appearing to derive it.
_A_ELECTRODE = 5.0e-8


def _activation_barrier(electrons: int, eta_a: float) -> float:
    """Activation overpotential (V) -> barrier (J/mol). ``Ea = n F eta_a``.

    A function rather than four hand-multiplied literals so that what is declared
    stays the VOLTAGE, which is the quantity Tafel data is published in and the
    quantity a reader can check.
    """
    return electrons * FARADAY * eta_a


def water_electrolysis(
    A: float = _A_ELECTRODE, eta_a: float = 0.80,
) -> ReactionTemplate:
    """2 H2O -> 2 H2 + O2. The reference cell, and the one everything competes with.

    ``E_dec`` = 1.229 V in the textbooks, and whatever this project's own water
    and its own standard-state correction make it -- which is the number
    ``validation/cell_potentials.py`` exists to print, because it is derived here
    and not curated.

    ⚠ **IT IS IN EVERY AQUEOUS CELL WHETHER OR NOT ANYONE WANTS IT**, and that is
    the honest reason to build it first rather than the reason to leave it out.
    Water is the solvent; any pair of electrodes in it can split it. A brine cell
    that made only chlorine because its author declined to write this template
    would be a recipe wearing a mechanism's clothes.

    ``eta_a`` = 0.80 V is the sum of the two half-cell activation overpotentials
    a plain metal electrode pair shows -- roughly 0.5 V for oxygen evolution,
    which is the sluggish one, and 0.3 V for hydrogen evolution. It is why a
    demonstration electrolyser needs about 2 V to bubble rather than the 1.23 V
    its thermodynamics asks for.
    """
    return ReactionTemplate(
        name="water_electrolysis",
        # ⚠ The two product H2 are UNMAPPED and the O2 carries both mapped
        # oxygens. Mapping the hydrogens would need them written as atoms, and
        # ``run``'s RemoveHs would then collapse them onto a heavy neighbour they
        # do not have; unmapped, RDKit builds them fresh and the balance check in
        # the builder is what confirms it got them right.
        smarts="[OX2H2:1].[OX2H2:2]>>[H][H].[H][H].[O:1]=[O:2]",
        A=A, Ea=_activation_barrier(4, eta_a),
        reversible=True, alpha=TRANSFER_COEFFICIENT, electrons=4,
    )


def halide_electrolysis(
    A: float = _A_ELECTRODE, eta_a: float = 0.40,
) -> ReactionTemplate:
    """2 X- + 2 H2O -> X2 + H2 + 2 OH-, for X = Cl, Br, I. The chloralkali cell.

    The industrial reaction of the nineteenth century's second half: brine in,
    caustic soda and chlorine and hydrogen out, and no other route to any of the
    three at that scale. Here it is one template over the halides rather than one
    per halide, so a flask of potassium bromide gives bromine by the same
    mechanism and for the same reason -- and gives it at a LOWER voltage, because
    bromide's chemistry costs less, which the template does not have to be told.

    ⚠ **THE SODIUM NEVER APPEARS AND MUST NOT.** In an aqueous cell the cathode
    reduces WATER, not the alkali metal -- that is the whole difference between
    this cell and the Downs cell, and the reason the caustic soda that comes out
    is a spectator cation meeting a manufactured hydroxide. The template matches
    ``[Cl,Br,I;-1]``, so it fires on the halide ion the electrolyte model has
    already made from the salt, and the counter-ion is left where it was.

    ``eta_a`` = 0.40 V: roughly 0.1 V for chlorine evolution on a coated titanium
    anode plus 0.3 V for hydrogen evolution at the cathode. **Half of oxygen's
    0.80 V, and that difference is the mechanism** -- it is what makes a cell
    at 3 V evolve chlorine rather than oxygen even though oxygen is
    thermodynamically the easier product by more than a volt.
    """
    return ReactionTemplate(
        name="halide_electrolysis",
        smarts="[Cl,Br,I;-1:1].[Cl,Br,I;-1:2].[OX2H2:3].[OX2H2:4]"
               ">>[*;+0:1][*;+0:2].[OH-:3].[OH-:4].[H][H]",
        A=A, Ea=_activation_barrier(2, eta_a),
        reversible=True, alpha=TRANSFER_COEFFICIENT, electrons=2,
    )


def kolbe_electrolysis(
    A: float = _A_ELECTRODE, eta_a: float = 1.20,
) -> ReactionTemplate:
    """2 RCOO- + 2 H2O -> R-R + 2 CO2 + H2 + 2 OH-. Kolbe, 1849.

    Anodic decarboxylation: a carboxylate gives up an electron, loses CO2, and
    the two radicals left over find each other. It is the oldest carbon-carbon
    bond-forming reaction in organic chemistry and it is still the cleanest
    demonstration that electricity is a reagent.

    The template is written on ``[#6:1][CX3](=O)[O-]`` and couples the two
    ``[#6]`` groups, so nothing is enumerated: **acetate gives ethane, propanoate
    gives butane, and a half-and-half mixture gives all three products** -- the
    cross-coupling included, because the two slots are filled independently. That
    last is real Kolbe chemistry and a real Kolbe nuisance.

    ⚠ **IT NEEDS THE CARBOXYLATE, NOT THE ACID**, which means it needs the
    electrolyte model to have deprotonated something first. A flask of glacial
    acetic acid does not electrolyse; a flask of sodium acetate does. The
    template says so by matching ``[O-]``, and nothing else has to enforce it.

    ``eta_a`` = 1.20 V. Kolbe is the high-overpotential case and famously so: it
    only outruns oxygen evolution on a platinum anode at high current density and
    high carboxylate concentration, which is exactly a large activation barrier
    that a large overpotential eventually beats. Under those conditions the
    catalog row's "platinum anode, concentrated" is the whole recipe.
    """
    return ReactionTemplate(
        name="kolbe_electrolysis",
        smarts="[#6:1][CX3:2](=[O:3])[O-:4].[#6:5][CX3:6](=[O:7])[O-:8]"
               ".[OX2H2:9].[OX2H2:10]"
               ">>[#6:1][#6:5].[O:3]=[C;+0:2]=[O;+0:4].[O:7]=[C;+0:6]=[O;+0:8]"
               ".[OH-:9].[OH-:10].[H][H]",
        A=A, Ea=_activation_barrier(2, eta_a),
        reversible=True, alpha=TRANSFER_COEFFICIENT, electrons=2,
    )


def alkene_hydrodimerisation(
    A: float = 1.0e8, Ea: float = 55_000.0,
) -> ReactionTemplate:
    """2 CH2=CH-C#N + H2 -> NC(CH2)4CN. Baizer's adiponitrile coupling.

    ⚠⚠ **AND IT IS NOT AN ELECTRODE REACTION -- ``electrons`` IS ZERO, AND THAT
    IS A MEASUREMENT.** The catalog row reads ``acrylonitrile + water ->
    adiponitrile + oxygen``, which is a cell reaction, so the expected shape here
    was a fourth ``electrons``-carrying template. Running the arithmetic first
    said otherwise, and it is worth recording which part is which:

      * ``4 AN + 2 H2O -> 2 ADN + O2`` costs **+212.7 kJ/mol**, so the CELL is
        genuinely uphill and genuinely needs a voltage -- 0.551 V of it;
      * but ``2 AN + H2 -> ADN`` is downhill on its own. **The coupling is not
        what the voltage pays for.** What the voltage pays for is tearing the
        hydrogen out of water, which is ``water_electrolysis``, already built and
        already in any aqueous cell.

    So the honest decomposition is two steps, not one lump: the cell splits
    water, and the hydrogen it liberates reduces two acrylonitriles into one
    adiponitrile. The catalog row's overall stoichiometry -- oxygen and all --
    EMERGES from the pair rather than being declared, which is what this project
    prefers everywhere else and had no reason to abandon here.

    ⚠ **THE COST OF THAT DECOMPOSITION IS A VOLTAGE, AND IT IS 0.89 V TOO HIGH.**
    Routing the electrons through free H2 means the route cannot start until
    water splitting can, at 1.441 V, where the real cell reduces acrylonitrile
    directly at its own cathode from 0.551 V. Baizer's cell runs near 4 V, so
    nothing about whether the route RUNS turns on this -- but the threshold this
    engine reports for it is the wrong one, and that is a modelling limit rather
    than a datum.

    ⚠ The alternative was measured and refused: written as the one 6-slot lump
    the row implies, the rate law is FOURTH ORDER in acrylonitrile, which is the
    limiting reagent. That is ``library.sulfur_combustion``'s stall in the case
    its own note says is NOT forgiven -- the yield stops being chemistry and
    becomes a reading of ``A``.

    The pattern is an alkene bearing an ELECTRON-WITHDRAWING nitrile, because
    that is what makes the coupling go: an unactivated alkene simply hydrogenates.
    Written over ``[CH2]=[CH]C#N``, so it fires on acrylonitrile and on
    methacrylonitrile and on nothing that has no nitrile to activate it.
    """
    return ReactionTemplate(
        name="alkene_hydrodimerisation",
        smarts="[CH2:1]=[CH1:2][C:3]#[N:4].[CH2:5]=[CH1:6][C:7]#[N:8].[H][H]"
               ">>[N:4]#[C:3][CH2:2][CH2:1][CH2:5][CH2:6][C:7]#[N:8]",
        A=A, Ea=Ea, reversible=True,
    )


def electrochemistry() -> list[ReactionTemplate]:
    """Every M8 template. The set a flask with a pair of electrodes in it gets.

    ⚠ Handing all four to one network is the point rather than a convenience:
    ``water_electrolysis`` is in there competing with ``halide_electrolysis`` for
    the same volts, and what a brine cell actually makes is then a result and not
    a choice. Pass a subset only when the flask genuinely lacks the chemistry --
    never to pick the answer.
    """
    return [
        water_electrolysis(),
        halide_electrolysis(),
        kolbe_electrolysis(),
        alkene_hydrodimerisation(),
    ]
