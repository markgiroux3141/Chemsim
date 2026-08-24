"""Layer 2 -- the curated reaction-template library.

Every other kind of parameter in this project is curated with provenance:
formation enthalpies in ``formation_data``, group values in ``benson_data``,
Antoine constants in ``volatility``, boiling points in ``physical_data``.
Templates were the exception -- they lived inline in whichever example needed
one -- and that had a cost beyond tidiness.

**The cost was that nothing ever competed.** A network with one template cannot
produce a side product, so purity was ~100% by construction and every
"impurity" the simulator could report was unreacted starting material or an ion.
The project's founding claim is that *yields, side products and
temperature/contamination sensitivity emerge* from integrating a network, and
two thirds of that was untested: `spike/spike_reactor.py` hand-wrote three
competing reactions in Phase 0 and demonstrated exactly this, and the real code
had never reproduced it.

## What a template's parameters are, and how honest each one is

    smarts      REAL. The transformation is chemistry, and its SPECIFICITY is
                the selectivity mechanism -- see below.
    Ea          SOURCED. Each barrier below carries the literature band it came
                from, and the ORDERING between templates is the load-bearing
                part: ethanol over sulfuric acid gives diethyl ether at 140 C
                and ethylene at 180 C because dehydration to the alkene has the
                higher barrier. Get that ordering wrong and the temperature
                response is backwards, however good the numbers look.
    alpha       DERIVED where used -- Evans-Polanyi ties the barrier to the
                reaction enthalpy the network already computes, so selectivity
                WITHIN a family follows from thermochemistry rather than from an
                author's choice.
    A           ⚠ THE REMAINING HAND-AUTHORED PARAMETER, and the honest weak
                point of this module. Pre-exponentials are order-of-magnitude
                choices inside the range physically sensible for the molecularity
                (~1e11-1e14 s^-1 for a unimolecular thermal step, lower for a
                bimolecular one). They set the absolute timescale; the barriers
                set the temperature response and the competition. Do not read a
                simulated reaction TIME as a prediction.
    reversible  Never a free parameter: the reverse Arrhenius pair is derived by
                detailed balance from the thermochemistry. There is no
                hand-typed reverse rate anywhere in this project by design.

## Selectivity is SMARTS specificity, and that is the point

The oxidation template below is written ``[CX4;!H0:1][OX2H1:2]`` -- a carbinol
carbon that still has a hydrogen to lose. That one clause is the whole
selectivity model for the family:

  * methanol -> formaldehyde, ethanol -> acetaldehyde, propanol -> propanal;
  * a SECONDARY alcohol -> the ketone (isopropanol -> acetone), because the
    pattern never said how many hydrogens, only "not zero";
  * a TERTIARY alcohol REFUSES, because there is no hydrogen on the carbinol
    carbon and you cannot make a carbonyl there without breaking a C-C bond;
  * glycerol yields BOTH the primary and the secondary oxidation product, from
    one template, because the pattern matches at two different sites.

None of that is enumerated. It follows from the pattern, which is why growing
this library is cheaper than it looks and why writing the pattern carelessly is
the main way to get a confidently wrong answer.

## EXPLICIT ACID CATALYSIS, and what it cost to make honest

Esterification and both dehydrations are acid-catalysed in reality, and for three
sessions they ran here uncatalysed with the catalysis folded into the barrier. The
audit was right that this needs NO ENGINE WORK -- a catalyst is an explicit
species with rate-law exponent 1 and net stoichiometry 0, which is what a species
appearing on BOTH sides of a reaction SMARTS already produces:
``builder.to_arrays`` adds 1 to its ``order`` as a reactant and then cancels it in
``delta``. Nothing in Layer 3 or Layer 4 needed a line.

What it did need was honesty about the pre-exponential, and this is the part worth
reading. An apparent rate is

    rate = A_apparent * exp(-Ea/RT) * [acid][alcohol]

and an explicit one is

    rate = A_intrinsic * exp(-Ea/RT) * [acid][alcohol][H3O+]

so the two agree only at one catalyst concentration, and ``A_apparent =
A_intrinsic * [H3O+]_folded``. **That folded concentration was invisible and is
now declared**: ``CATALYST_REFERENCE``. So the catalysed and uncatalysed forms of
each template are the SAME RATE at the reference loading -- asserted in
``tests/test_catalysis.py``, which is the whole point of naming the number rather
than re-fitting A -- and away from it "add more acid" is a real lever with the
right slope.

⚠ **The barrier does not change, and that is deliberate.** ``Ea`` here has always
been the *catalysed* apparent barrier (the literature bands quoted below are for
the acid-catalysed reactions), so re-declaring the catalyst does not license
re-declaring the barrier. What is still missing is the UNcatalysed pathway
alongside the catalysed one -- two routes with genuinely different barriers, which
is what would make an uncatalysed flask slow rather than dead. That needs a second
Ea per family, from a second literature band, and it is a data job.

⚠ **A catalysed template needs the catalyst IN THE NETWORK**, and gives no
reaction at all without it. That is why ``catalyst`` is opt-in per template and
why ``alcohol_chemistry()`` is unchanged: a network built without dissociation
templates has no ``[OH3+]`` to price, and silently losing the esterification would
be far worse than folding the catalysis in.

## What is still deliberately NOT modelled

**Heterogeneous catalysis** -- a surface has a site balance, so it needs a
Langmuir-Hinshelwood rate form the kernel cannot express (it evaluates
``A T**n exp(-Ea/RT)`` times a product of powers, and nothing else). Homogeneous
catalysis fits the mass-action form exactly; that is the whole reason this was
cheap and that is not.
"""

from __future__ import annotations

from chemsim.reactions.template import ReactionTemplate

# mol/L of catalyst that the APPARENT pre-exponentials below were standing in for.
# 0.1 M is an ordinary Fischer-esterification loading (a couple of mole percent of
# sulfuric acid in a neat alcohol/acid mixture), and declaring it is what makes the
# catalysed and uncatalysed forms of a template the same rate rather than two
# unrelated calibrations. See the module docstring.
CATALYST_REFERENCE = 0.1

# The proton, as this project spells it. Written with water on both sides
# everywhere else (see ``properties/electrolyte``), so the catalyst a network
# actually contains is hydronium rather than a bare H+.
ACID_CATALYST = "[OH3+]"


def _maybe_catalyse(smarts: str, catalyst: str | None) -> str:
    """Put ``catalyst`` on both sides of a reaction SMARTS, unchanged.

    That is the entire mechanism: an extra reactant slot raises the species'
    mass-action exponent to 1, and the identical product slot cancels it out of
    the stoichiometry, so the rate depends on how much catalyst is present and the
    catalyst is not consumed. Map number 99 is used so it cannot collide with a
    template's own.
    """
    if catalyst is None:
        return smarts
    reactants, products = smarts.split(">>")
    tag = catalyst.replace("]", ":99]") if catalyst.endswith("]") else f"[{catalyst}:99]"
    return f"{reactants}.{tag}>>{products}.{tag}"


def _kinetics(A: float, catalyst: str | None) -> float:
    """The pre-exponential to declare, given whether the catalyst is explicit.

    Dividing by ``CATALYST_REFERENCE`` is what makes the two forms agree at that
    loading; without it, making the catalysis explicit would silently slow every
    esterification in the project by a factor of ten.
    """
    return A if catalyst is None else A / CATALYST_REFERENCE

# ---------------------------------------------------------------------------
# esterification
# ---------------------------------------------------------------------------
# Ea 55 kJ/mol: apparent barrier for acid-catalysed/autocatalysed Fischer
# esterification, literature band ~50-60 kJ/mol. Reversible, so the hydrolysis
# direction is DERIVED -- and that reverse is what makes the equilibrium sit
# where it does rather than running to completion.


def esterification(
    A: float = 5.0e7,
    Ea: float = 55_000.0,
    alpha: float = 0.0,
    catalyst: str | None = None,
):
    """Carboxylic acid + alcohol <=> ester + water.

    ``alpha`` turns on Evans-Polanyi, which is what distinguishes homologues:
    three alcohols on this one template get 44532 / 45018 / 45655 J/mol ordered
    by reaction enthalpy, so the more exothermic member is faster without anyone
    declaring it.

    ``catalyst`` makes the acid catalysis EXPLICIT rather than folded into ``A``
    -- pass ``ACID_CATALYST`` for a network that carries hydronium. The rate then
    depends on how much acid is present, which is the lever a chemist actually
    pulls, and it reproduces the uncatalysed rate exactly at
    ``CATALYST_REFERENCE``. ⚠ It gives NO reaction in a network with no catalyst
    species; the default is None for that reason.

    ⚠ The REVERSE is catalysed too, and it must be. Detailed balance derives it
    from the forward rate, so the catalyst appears in both directions with the
    same exponent and cancels out of K exactly -- which is the definition of a
    catalyst. Had it been put on the forward direction only, adding acid would
    have moved the equilibrium.
    """
    return ReactionTemplate(
        name="fischer_esterification" + ("_acid" if catalyst else ""),
        smarts=_maybe_catalyse(
            "[CX3:1](=[O:2])[OX2H1:3].[OX2H1:4][CX4:5]"
            ">>[CX3:1](=[O:2])[O:4][CX4:5].[OH2:3]",
            catalyst,
        ),
        A=_kinetics(A, catalyst), Ea=Ea, alpha=alpha, reversible=True,
    )


# ---------------------------------------------------------------------------
# dehydration -- two routes, and their ORDERING is the chemistry
# ---------------------------------------------------------------------------
# Ethanol over sulfuric acid gives diethyl ether at ~140 C and ethylene at
# ~180 C. Both are dehydrations of the same alcohol; which one you get is
# decided by temperature, because the alkene route has the higher barrier.
# Reproducing that ordering is the whole test of whether these two barriers are
# defensible, and it is asserted in tests/test_competing_templates.py.
#
#   ether    Ea 125 kJ/mol -- literature ~100-130 for the bimolecular route
#   alkene   Ea 160 kJ/mol -- literature ~145-170 for the unimolecular E1
#
# Neither is reversible here. Both eliminate water into a large excess of it, so
# the reverse (hydration / ether cleavage) is negligible under bench conditions
# and asserting reversibility would invite detailed balance to derive a
# hydration rate for a reaction nobody runs that way.


def ether_condensation(
    A: float = 1.0e11, Ea: float = 125_000.0,
    catalyst: str | None = None,
):
    """2 R-OH -> R-O-R + water. The lower-temperature dehydration.

    Bimolecular, so it consumes two alcohol molecules and is second order in
    alcohol -- which is why it fades faster than the alkene route when the
    alcohol is dilute, and why it dominates when the alcohol is the solvent.
    Note the two slots match independently, so a mixed feed gives the mixed
    ether as well as both symmetrical ones.
    """
    return ReactionTemplate(
        name="ether_condensation" + ("_acid" if catalyst else ""),
        smarts=_maybe_catalyse(
            "[CX4:1][OX2H1:2].[CX4:3][OX2H1:4]>>[C:1][O:2][C:3].[OH2:4]",
            catalyst,
        ),
        A=_kinetics(A, catalyst), Ea=Ea,
    )


def alkene_dehydration(
    A: float = 1.0e13, Ea: float = 160_000.0,
    catalyst: str | None = None,
):
    """R-CH2-CH2-OH -> alkene + water. The higher-temperature dehydration.

    The hydrogen leaves the BETA carbon, so that is where the pattern's
    ``!H0`` belongs. Getting it on the carbinol carbon instead is a silent
    no-match: ethanol's carbinol carbon has two hydrogens and would match
    happily, but the resulting rewrite is not an elimination.

    Methanol correctly refuses -- there is no beta carbon to eliminate towards.
    """
    return ReactionTemplate(
        name="alkene_dehydration" + ("_acid" if catalyst else ""),
        smarts=_maybe_catalyse(
            "[CX4;!H0:1][CX4:2][OX2H1:3]>>[C:1]=[C:2].[OH2:3]", catalyst
        ),
        A=_kinetics(A, catalyst), Ea=Ea,
    )


# ---------------------------------------------------------------------------
# aerobic oxidation -- the contamination pathway, and it CASCADES
# ---------------------------------------------------------------------------
# Written as alcohol + O2 -> carbonyl + H2O2 rather than
# alcohol + 1/2 O2 -> carbonyl + H2O, because a graph rewrite cannot express
# half-stoichiometry and an unbalanced template is refused by build_network --
# correctly, since an unbalanced reaction silently creates matter.
#
# That is not a workaround, it is better chemistry: the peroxide is real, it is
# already a curated species, and it then OVER-OXIDISES the aldehyde to the
# carboxylic acid. So a single air leak produces an aldehyde AND extra acid,
# and the extra acid re-enters the esterification. Nothing scripts that cascade;
# it is three templates meeting.
#
#   oxidation   Ea 65 kJ/mol -- apparent barrier for uncatalysed autoxidation
#   over_ox     Ea 50 kJ/mol -- peroxide oxidation of an aldehyde, faster


def aerobic_oxidation(A: float = 1.0e9, Ea: float = 65_000.0):
    """R-CH(OH)- + O2 -> R-C(=O)- + H2O2. Alcohol to carbonyl.

    ``[CX4;!H0:1]`` is the whole selectivity model -- see the module docstring.
    Primary alcohols give aldehydes, secondary give ketones, tertiary refuse,
    and a polyol gives every product its distinct sites allow.
    """
    return ReactionTemplate(
        name="aerobic_oxidation",
        smarts="[CX4;!H0:1][OX2H1:2].[OX1:3]=[OX1:4]"
               ">>[C:1]=[O:2].[OX2H1:3][OX2H1:4]",
        A=A, Ea=Ea,
    )


def peroxide_over_oxidation(A: float = 1.0e8, Ea: float = 50_000.0):
    """R-CHO + H2O2 -> R-COOH + water. Aldehyde to carboxylic acid.

    Restricted to an ALDEHYDE (``[CX3H1:1]=[OX1:2]``) rather than any carbonyl,
    because a ketone has no hydrogen on the carbonyl carbon and cannot be
    oxidised to an acid without cleaving the skeleton. So isopropanol under air
    stops cleanly at acetone while ethanol runs on to acetic acid -- a
    difference nobody declared.
    """
    return ReactionTemplate(
        name="peroxide_over_oxidation",
        smarts="[CX3H1:1]=[OX1:2].[OX2H1:3][OX2H1:4]"
               ">>[CX3:1](=[O:2])[OX2H1:3].[OH2:4]",
        A=A, Ea=Ea,
    )


# ---------------------------------------------------------------------------
# THE LEAD CHAMBER -- a real catalytic CYCLE, not a rate multiplier
# ---------------------------------------------------------------------------
# The historical route to oil of vitriol, and the first GAS-PHASE chemistry in
# this library. Two templates, and between them they turn:
#
#     SO2 + NO2 + H2O  ->  H2SO4 + NO      the carrier is CONSUMED
#     2 NO + 1/2 O2    ->  2 NO2           the carrier is REGENERATED
#     ------------------------------------------------------------------
#     net: SO2 + 1/2 O2 + H2O -> H2SO4,  catalysed by NOx
#
# ## WHY THIS IS A DIFFERENT OBJECT FROM ``CATALYST_REFERENCE``, and must stay so
#
# The acid catalysis above is a FOLDED catalyst: hydronium appears on both sides
# of one SMARTS, so its rate-law exponent is 1 and its net stoichiometry is 0 --
# one reaction, one species, no cycle to watch. ``CATALYST_REFERENCE`` exists to
# make that folding honest.
#
# ⚠ **NONE OF THAT APPLIES HERE, AND FOLDING THIS WOULD DESTROY THE MECHANIC.**
# NO2 is genuinely consumed by the first reaction and genuinely regenerated by
# the second, so the carrier has a real, integrated concentration that rises and
# falls. Three things follow that a folded catalyst cannot give:
#
#   * **the cycle is watchable.** NO and NO2 are both state variables, so a
#     player sees the carrier turning over;
#   * **the cycle is LOSABLE.** NO and NO2 are gases, so opening the vent carries
#     them out of the chamber and the process stops -- "keep the chamber shut"
#     becomes a skill, and it runs on the headspace-budget mechanic that already
#     exists;
#   * **the cycle has a TEMPERATURE CEILING, and it is emergent.** The
#     regeneration is written reversible, and ``2 NO2 -> 2 NO + O2`` really does
#     take over above ~600 K. Nothing declares a maximum operating temperature;
#     detailed balance derives one from the thermochemistry.
#
# ## THE PRE-EXPONENTIAL OF THE REGENERATION IS SOURCED, WHICH IS RARE HERE
#
# ``A`` is described above as the remaining hand-authored parameter, and for the
# regeneration it is not. ``2 NO + O2 -> 2 NO2`` is one of the few genuinely
# TERMOLECULAR reactions in chemistry and one of the few with a measured
# NEGATIVE activation energy: k = 1.2e-31 exp(+530/T) cm^6 molecule^-2 s^-1
# (JPL/IUPAC evaluations). Converted to this project's units,
#
#     1.2e-31 cm^6 molecule^-2 s^-1 * (6.022e23)^2 * (1e-3 L cm^-3)^2
#         = 4.35e10 L^2 mol^-2 s^-1
#
# and Ea = -R * 530 = -4.4 kJ/mol. So this template's rate law is elementary --
# third order, exactly as written -- and both parameters are measured.
#
# ⚠ **THE NEGATIVE BARRIER IS REAL AND IS NOT A SIGN ERROR.** The reaction goes
# through an ONOONO dimer whose formation is favoured by cooling, so the carrier
# regenerates FASTER in a cold chamber. Combined with the ceiling above, "run it
# cool" is doubly right, and nobody wrote either half of that down.
#
# ## THE CORE STEP'S BARRIER IS AN APPARENT ONE, AND THE MODULE SAYS SO
#
# Ea 40 kJ/mol, literature band ~30-50 for SO2 oxidation by NO2. ⚠ That band is
# for the reaction as it actually runs -- in an aqueous film or droplet, not in
# dry gas -- so writing it as a homogeneous gas-phase step is a real
# simplification and the barrier is apparent rather than elementary. What
# survives it is the STOICHIOMETRY and the CYCLE, which is what the mechanic
# rests on. Do not read a chamber residence time as a prediction.


def sulfur_dioxide_oxidation(
    A: float = 1.0e9, Ea: float = 40_000.0,
) -> ReactionTemplate:
    """SO2 + NO2 + H2O -> H2SO4 + NO. The lead chamber's core step.

    Written on the SMARTS rather than the names, so it is the transformation and
    not a lookup: a sulfur with two double-bonded oxygens takes one oxygen from
    the nitro group and two hydrogens plus an oxygen from water, and the nitrogen
    leaves reduced.

    ⚠ Two atom-level details that were each a silent wrong answer first time.
    The oxygen transferred from NO2 arrives carrying its formal -1, so the
    product is BISULFATE unless the product template neutralises it
    (``[O+0;H1:6]``) -- and neutralising the charge without also declaring the
    hydrogen count leaves an oxygen RADICAL on the sulfur, which sanitises
    perfectly happily and is not sulfuric acid. Both were caught by reading the
    product SMILES rather than by anything failing.
    """
    return ReactionTemplate(
        name="sulfur_dioxide_oxidation_by_nitrogen_dioxide",
        smarts="[O:1]=[S:2]=[O:3].[N+:4](=[O:5])[O-:6].[OX2H2:7]"
               ">>[O:1]=[S:2](=[O:3])([O+0;H1:6])[O:7].[N+0;H0:4]=[O:5]",
        A=A, Ea=Ea, phase="gas", reversible=True,
    )


def nitric_oxide_reoxidation(
    A: float = 4.35e10, Ea: float = -4_400.0,
) -> ReactionTemplate:
    """2 NO + O2 -> 2 NO2. The step that makes the carrier a CYCLE.

    Both parameters are measured rather than chosen -- see the block comment
    above -- including the NEGATIVE activation energy, which is real: the
    reaction runs through an ONOONO dimer and goes faster as it gets colder.

    Reversible on purpose. ``2 NO2 -> 2 NO + O2`` genuinely takes over above
    ~600 K, so a chamber run too hot loses its carrier to dissociation, and that
    ceiling is DERIVED by detailed balance from the formation data rather than
    declared as an operating limit.
    """
    return ReactionTemplate(
        name="nitric_oxide_reoxidation",
        smarts="[N;H0:1]=[O:2].[N;H0:3]=[O:4].[OX1:5]=[OX1:6]"
               ">>[N+1;H0:1](=[O:2])[O-:5].[N+1;H0:3](=[O:4])[O-:6]",
        A=A, Ea=Ea, phase="gas", reversible=True,
    )


# ---------------------------------------------------------------------------
# THE SULFUR BURNER -- chain 2's first arrow, and the first DECLARED rate law
# ---------------------------------------------------------------------------
# ``S8 + 8 O2 -> 8 SO2``. This was written, measured and REFUSED once already,
# and the record of why is worth keeping, because the refusal is what named the
# engine work that made it shippable.
#
# ## WHAT KILLED IT THE FIRST TIME
#
# Never the SMARTS, never the network (4 species, 1 reaction, 0.45 s to build,
# no explosion) and never the thermochemistry, which is excellent: dG = -2449.7
# kJ, ln K = 988, a hard ATTRACTOR. **It was the RATE LAW.** The kernel took
# mass-action exponents from stoichiometry, so a global stoichiometry written as
# one step was NINTH ORDER, first in S8 and EIGHTH in O2:
#
#   1. it could not run with a physical pre-exponential. At 700 K and
#      atmospheric oxygen [O2]^8 = 2.9e-20, so a plausible burn rate needed
#      **A = 7e24**, whose units are (L/mol)^8/s -- not a pre-exponential's;
#   2. where O2 was in EXCESS the attractor still held and the wrong form was
#      FORGIVEN, exactly as GAME_DESIGN section 3(a) predicts: 100.0% at
#      550/700/900 K and at A = 1e20 and 1e24 alike;
#   3. **where O2 was LIMITING it was not, and that was the disqualifying
#      result**: 86.5 / 92.8% at A = 1e20 against 96.4 / 98.0% at A = 1e24,
#      because [O2]^8 stalls asymptotically and the last oxygen never burns. The
#      yield read the author's pre-exponential rather than the chemistry, which
#      corrupts the headspace-budget gate -- one of the six that already work;
#   4. forced to A = 1e26 the projection CREATED MATTER: 334.8% yield.
#
# ## WHAT CHANGED: ``ReactionTemplate.orders``
#
# Nine molecules do not meet. The stoichiometry is real and the rate law is not
# its coefficients, and that distinction now has somewhere to live -- see
# ``ReactionTemplate.orders`` for the argument, including why a declared order
# may NOT be reversible. The burner declares ``(1, 1, 0, 0, 0, 0, 0, 0, 0)``:
# eight oxygens are CONSUMED, one appears in the rate law.
#
# **Measured, and this is the result that matters**: with O2 LIMITING the yield
# is now 100.000% at A = 1e7, 1e8, 1e9, 1e10 and 1e12 -- FIVE DECADES of
# pre-exponential, and the answer has stopped depending on it. Below that
# (A = 1e6) it reads 85.5%, which is not a stall but honest kinetics: the burn
# has not finished in ten minutes.
#
# ## THE TWO PARAMETERS, AND WHAT THEY ARE WORTH
#
# ⚠ **BOTH ARE HAND-AUTHORED.** Unlike the regeneration above, nothing here is
# sourced, and the rate law is an APPARENT one -- real sulfur combustion is a
# branched-chain process, not a bimolecular collision. They are BOUNDED rather
# than fitted, by two observables at the ends:
#
#   * ``A = 1e10 L/(mol s)`` is held at the order of the gas-kinetic COLLISION
#     LIMIT (~1e11), so it is not a knob dialled until the yield looked right.
#     That constraint is one the ninth-order form could not satisfy at all.
#   * ``Ea = 100 kJ/mol`` is then the only remaining freedom, set so the burn is
#     complete above sulfur's ignition point and negligible cold. Measured yield
#     against temperature, 0.02 mol S8 under 0.40 mol O2 for 600 s:
#
#         298 K   0.00%      550 K   100.00%
#         400 K   0.00%      600 K   100.00%
#         500 K   68.14%     700 K   100.00%
#
#     ⚠ **The threshold is SOFT, and that is stated rather than tuned away.**
#     68% at 500 K is more than real sulfur does below its ~523 K ignition point.
#     A sharper knee is available at Ea = 150 kJ, but it needs A = 1e14 -- a
#     thousand times the collision limit -- and buying a prettier threshold with
#     an impossible pre-exponential is the wrong trade. The soft edge is the
#     honest cost of one apparent barrier standing in for a chain mechanism.
#
# ## AND IT IS WRITTEN FOR A MOLTEN CHARGE AT 550-650 K, WHICH IS NOW A PHYSICAL
# ## REASON RATHER THAN A NUMERICAL ONE
#
# A real sulfur burner IS molten sulfur sprayed into air, well below the boiling
# point, so the window is what the apparatus is. It used to be a numerical
# requirement as well and that half is GONE.
#
# ⚠ WHAT USED TO BE HERE, because the shape of it generalises. Sulfur boils at
# 717.8 K, so a burner run near that holds only a TRACE of condensate -- and if
# the trace landed inside ``DRYOUT_MOLES`` (1e-6 mol) the flask's two liquid gates
# overlapped while the mole fractions were floored on the SAME scale, so they
# summed to 0.57, every activity was understated, and the solve CREATED oxygen:
# 1.1e-01 of it at 690 K, i.e. a reported yield of 111%. Closed by
# ``_dryout_gates`` + ``MOLE_FRACTION_DENOM``: the same flask now conserves to
# 1.9e-11 once nothing else is being driven to zero beside it.
#
# ⚠ AND THE TABLE THAT USED TO SIT HERE HAS BEEN RETIRED RATHER THAN UPDATED,
# because its numbers were not a property. What is left in the O2-limiting case is
# the ordinary stiff-reactant-at-zero residual (M7's), and nudging the INERT
# nitrogen charge by 0.5% swings it over five orders of magnitude -- so no single
# value of it was ever an invariant. See the dryout-band test in
# ``tests/test_lead_chamber.py`` for the measurements that stand.


def sulfur_combustion(
    A: float = 1.0e10, Ea: float = 100_000.0,
) -> ReactionTemplate:
    """S8 + 8 O2 -> 8 SO2. Native sulfur to the chamber's feedstock.

    First order in sulfur and FIRST ORDER IN OXYGEN, declared -- not eighth, as
    the stoichiometry would otherwise impose. See the block comment above for
    what that cost to find out, and ``ReactionTemplate.orders`` for why a
    declared order may not be reversible. This one does not need to be: ln K
    = 988, so the reverse is 400 orders of magnitude away.

    Burn it at 550-650 K with the sulfur MOLTEN, which is what a real sulfur
    burner is. That used to be a NUMERICAL requirement too -- above ~690 K the
    trace of condensate landed in the ``DRYOUT_MOLES`` band and the solve created
    oxygen -- and that half is closed; see the block comment above.
    """
    ring = "[S:1]1[S:2][S:3][S:4][S:5][S:6][S:7][S:8]1"
    o2 = ".".join(f"[OX1:{9 + 2 * i}]=[OX1:{10 + 2 * i}]" for i in range(8))
    so2 = ".".join(f"[O:{9 + 2 * i}]=[S:{1 + i}]=[O:{10 + 2 * i}]"
                   for i in range(8))
    return ReactionTemplate(
        name="sulfur_combustion",
        smarts=f"{ring}.{o2}>>{so2}",
        A=A, Ea=Ea, phase="gas",
        orders=(1.0, 1.0) + (0.0,) * 7,
    )


# ⚠ THE LOW-ORDER WORKAROUND IS STILL BLOCKED BY THE ELEMENT TABLE, CORRECTLY,
# and it is worth keeping now that it is no longer needed. Cracking the ring
# first (``S8 <=> 4 S2``, real -- it is why hot sulfur vapour is S2) and then
# burning ``S2 + 2 O2 -> 2 SO2`` is third order and perfectly well posed on
# paper. It needs S2 priced, and S2 REFUSES: its formation half is measured and
# good (Hf +128.60, Gf +79.70, both CRC) but it has no measured Tb, Tc or Pc in
# any source, because a diatomic that never condenses as itself has no boiling
# point. Inventing two critical constants would be exactly the confident estimate
# of an unmeasured quantity ``element_data`` exists to prevent. The declared
# order made the honest route work instead of the clever one.


# ---------------------------------------------------------------------------
# bundles
# ---------------------------------------------------------------------------


def alcohol_chemistry(alpha: float = 0.0) -> list[ReactionTemplate]:
    """Everything above: the esterification a chemist wants, and the four ways it
    goes wrong.

    This is the set that reproduces `spike/spike_reactor.py` from templates.
    Measured on a 1:1 acetic acid / ethanol charge (see
    ``examples/competing_pathways.py``): at 340 K the ester is 99.99% of the
    organic product; by 480 K diethyl ether has overtaken it, ethylene is
    climbing faster still, and the ether/ethylene ratio has fallen from 5700
    to 35. Admitting air introduces acetaldehyde and roughly doubles the acetic
    acid. Nothing in the network knows about any of that.

    ⚠ It stays BOUNDED -- 10 species, 6 reactions, built in under 0.01 s -- and
    that is worth understanding rather than being relieved about. Network
    explosion comes from templates that REGENERATE their own matched group
    (polyesterification makes an ester bearing another acid and another alcohol,
    which is why it reached 80 species from one template). These five terminate:
    an ether, an alkene and a ketone have no hydroxyl left to attack. Adding
    templates is not what explodes a network; adding a self-feeding one is.
    """
    return [
        esterification(alpha=alpha),
        ether_condensation(),
        alkene_dehydration(),
        aerobic_oxidation(),
        peroxide_over_oxidation(),
    ]


def acid_catalysed_chemistry(
    alpha: float = 0.0, catalyst: str = ACID_CATALYST
) -> list[ReactionTemplate]:
    """``alcohol_chemistry`` with the three ACID-CATALYSED routes made explicit.

    The oxidation pair is unchanged -- autoxidation and peroxide oxidation are not
    acid-catalysed, and pretending otherwise to make the bundle uniform would be
    the kind of tidiness that costs a fact.

    ⚠ **Use it only with a network that carries the catalyst**, i.e. one built
    with ``dissociation_templates()`` and something to protonate. Without
    ``[OH3+]`` the three catalysed templates match nothing and the bundle quietly
    becomes an oxidation-only network. ``build_network`` cannot warn about this:
    "no reaction found" is indistinguishable from a template that legitimately
    does not apply to the species present.

    What it buys, and it is the point: the esterification rate is now
    proportional to the acid concentration, so pH is a lever on RATE as well as on
    speciation. At ``CATALYST_REFERENCE`` it reproduces ``alcohol_chemistry``
    exactly.
    """
    return [
        esterification(alpha=alpha, catalyst=catalyst),
        ether_condensation(catalyst=catalyst),
        alkene_dehydration(catalyst=catalyst),
        aerobic_oxidation(),
        peroxide_over_oxidation(),
    ]


def lead_chamber() -> list[ReactionTemplate]:
    """The two templates that make oil of vitriol, and nothing else.

    ⚠ **THE CARRIER IS NOT IN THIS BUNDLE, AND MUST BE CHARGED.** Both templates
    need a nitrogen oxide to match, and ``build_network`` cannot warn about its
    absence -- "matched nothing" is indistinguishable from a template that
    legitimately does not apply, which is the same caveat
    ``acid_catalysed_chemistry`` carries about hydronium. A chamber charged with
    SO2, water and air and NO NOx is inert, and that is correct: the historical
    process needed a nitre bed for exactly this reason.

    ⚠ **AND THE FIRST ARROW OF THE CHAIN IS MISSING ON PURPOSE.** Burning the
    sulfur is not here; see the block comment above for the four measurements
    that disqualified it and the engine change that would let it in.

    Bounded, and for the usual reason: neither template regenerates its own
    matched group. Measured at **7 species and 4 reactions** on a full chamber
    charge (the two forward steps plus their derived reverses), which is
    asserted in ``tests/test_lead_chamber.py`` so a future self-feeding template
    shows up as a jump in that number.
    """
    return [sulfur_dioxide_oxidation(), nitric_oxide_reoxidation()]
