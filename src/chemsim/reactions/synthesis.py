"""Layer 2 -- the named-route template library (M5).

``library.py`` holds the templates Layers 0-4 were BUILT on: the alcohol
chemistry that first made side products emerge, the lead chamber that first made
a catalytic cycle turn over, the sulfur burner that first forced a declared rate
order. This module holds the templates M5 added, and its purpose is different:
it exists to make **named historical routes runnable end to end**, measured
against ``data/catalog``.

Everything ``library.py`` says about parameter honesty applies here unchanged and
is not repeated. What IS worth stating is what M5 learned about choosing which
templates to write at all.

## ⚠ THE GREEDY ORDER WAS MOSTLY OUTCOME LABELS, AND FIVE OF ITS TOP TEN WERE REFUSED

M1 settled that *a reaction class is a MECHANISM claim, not an outcome*, and
re-labelled 32 catalog rows on that standard. M5 is the first milestone to spend
that standard rather than establish it, and the greedy set-cover order M1 handed
forward does not survive contact with it. Of the ten classes at the top of that
queue, **five have no template here and the reason is not difficulty**:

    fermentation            glucose -> acetone + butanol + ethanol + CO2 + H2 by
                            Clostridium. That is a metabolic NETWORK, not a
                            transformation. Refused on the M1 standard.
    pyrolysis               two of its three rows read ``coal-marker ->
                            coal-tar-marker + ...`` and ``cellulose-unit ->
                            methanol + acetic-acid + acetone + carbon + water``.
                            Lumped decompositions of things with no molecular
                            graph. Refused.
    isomerisation           THREE mechanisms wearing one label: a cis/trans
                            isomerisation on a nickel surface, an aldose-ketose
                            interconversion, and Wohler's ammonium cyanate
                            rearrangement. Refused as a class.
    thermal-cracking        ``octane + water -> ethylene + propylene + butadiene
                            + methane + hydrogen``. A lumped product slate from a
                            radical chain. Refused.
    catalytic-air-oxidation ranked THIRD by routes unlocked, and its four rows are
                            at least three mechanisms: liquid-phase radical
                            autoxidation of p-xylene (Amoco), Mars-van Krevelen
                            vapour-phase oxidation over V2O5, and an oxidative
                            ring cleavage of naphthalene that loses two carbons
                            as CO2. Refused as a class.

⚠ **AND ONE MORE WAS REFUSED FOR THE OPPOSITE REASON.** ``separation`` unlocks
``coal-tar-distillation`` alone, and this engine genuinely fractionates -- M2
built a plate column that reaches its purity target. It is still not credited: the
audit's unit is a reaction class, a distillation is not one, and the route's
feedstock is a marker with no molecular graph, so crediting it would have moved
the headline number by one while making exactly zero routes runnable. That is the
trade M1 exists to refuse.

## WHAT IS HERE INSTEAD, AND THE ONE ENGINE CHANGE IT NEEDED

Twenty templates, each a single mechanism, each unlocking at least one named
route. The engine needed **one** change to accept them: ``ReactionTemplate.run``
now collapses explicit hydrogens (see its docstring). Any template that consumes
H2 must write hydrogen as an ATOM -- ``[H][H]`` has no heavy atom to hang an
implicit count on -- and without the collapse the ammonia the Haber template makes
is ``[H]N([H])[H]``, a DIFFERENT state-vector entry from the ``N`` charged into
the flask, with no reaction connecting them and a mass balance that closes
perfectly while the answer is wrong.

## ⚠ THE PARAMETERS, AND THE ONE THING M12 ADDED TO THE STANDARD

Barriers are sourced to a literature band, quoted at each template. Pre-exponentials
are order-of-magnitude choices for the molecularity, as everywhere in this project.

M12's bequest is that **the reverse a reversible template implies is now checked,
not only the forward that was typed**: ``validation/rate_ceiling.py`` covers every
network in this module. Eight of the twenty are reversible and every one of them
was run through it.

⚠ **AND A REVERSIBLE TEMPLATE IS A CLAIM, NOT A DEFAULT.** Twelve of these are
irreversible, and the argument is the one ``library.py`` makes for the two
dehydrations: a reaction that eliminates into a large excess of the eliminated
species, or that loses a gas, or that ends on an anion nothing attacks, has a
reverse nobody runs -- and asserting reversibility would invite detailed balance
to derive a rate for it. Each irreversible template below says which of those it
is.

## ⚠ SPECIES A NEW TEMPLATE DRAGS IN

M5's routes introduce anhydrides, nitro compounds, nitriles and sugars. Several
have no UNIFAC decomposition, so ``Vessel.lle_report()`` will flag a held-ideal
fraction rather than silently assuming the phases do not separate. That is the
system working. A route whose flask reports a large held-ideal fraction has soft
phase behaviour and the example for it says so.
"""

from __future__ import annotations

from chemsim.reactions import hammett
from chemsim.reactions.library import (
    ACID_CATALYST, _kinetics, _maybe_catalyse, _surface_kinetics,
)
from chemsim.reactions.template import ReactionTemplate

# ---------------------------------------------------------------------------
# SUGARS -- the glycosidic bond, and why one template covers a disaccharide
# ---------------------------------------------------------------------------
# Ea 107 kJ/mol. Acid-catalysed inversion of sucrose is one of the oldest
# quantitative rate measurements in chemistry and its Arrhenius barrier is
# consistently reported in the 100-115 kJ/mol band. 107 is the middle of it.
#
# ⚠ THE PRE-EXPONENTIAL IS APPARENT AND SITS ABOVE A BIMOLECULAR COLLISION
# FREQUENCY ON PURPOSE, WHICH IS WORTH READING RATHER THAN FIXING. The mechanism
# is A1: a fast protonation pre-equilibrium followed by a UNIMOLECULAR cleavage
# of the protonated glycoside. The apparent second-order pre-exponential is then
# the product of a protonation constant and a unimolecular frequency factor, so
# it is not a collision frequency and is not bounded by one. Declared at 1e11 --
# the collision limit -- rather than at the ~1e15 the measured rate and the
# measured barrier together imply, because this project does not write a
# pre-exponential it cannot defend. ⚠ **THE COST IS STATED RATHER THAN HIDDEN:
# the absolute rate is then some four orders slow at 298 K.** The barrier, which
# is what sets the temperature response and the competition, is the sourced one.


def glycoside_hydrolysis(
    A: float = 1.0e11, Ea: float = 107_000.0, catalyst: str | None = None,
) -> ReactionTemplate:
    """Glycoside + water -> sugar + aglycone. Sucrose inversion, and much else.

    The pattern is the ANOMERIC CARBON -- a ring sp3 carbon carrying the ring
    oxygen and a second, exocyclic oxygen -- so it is the glycosidic linkage and
    not "an ether next to a sugar". What follows from that one clause, with
    nothing enumerated:

      * sucrose gives glucose AND fructose, and gives them whichever of its two
        anomeric carbons is attacked, because it is joined anomeric-to-anomeric;
      * salicin gives glucose and salicyl alcohol, because ``[#6:4]`` does not
        care that the aglycone is aromatic;
      * maltose and starch cleave one unit at a time, since the pattern matches
        at every linkage.

    ⚠ Irreversible, and this is the case where that is least controversial: the
    reverse is glycosylation, which does not happen in water at a measurable rate
    and is the reason a chemist reaching for it uses a protected donor instead.
    """
    return ReactionTemplate(
        name="glycoside_hydrolysis" + ("_acid" if catalyst else ""),
        smarts=_maybe_catalyse(
            "[CX4;R:1]([OX2;R:2])[OX2;!R:3][#6:4].[OX2H2:5]"
            ">>[C:1]([O:2])[OX2H1:5].[OX2H1:3][#6:4]",
            catalyst,
        ),
        A=_kinetics(A, catalyst), Ea=Ea,
    )


# ---------------------------------------------------------------------------
# AROMATIC SUBSTITUTION -- and the isomers are EMERGENT, with a caveat
# ---------------------------------------------------------------------------
# Ea 60 kJ/mol for nitration. The apparent barrier for aromatic nitration in
# mixed acid is reported in the 50-70 kJ/mol band; the spread is largely how much
# of the nitronium pre-equilibrium each study folds in.
#
# ⚠ **THE PATTERN IS ``[cH]`` -- ANY AROMATIC C-H -- SO TOLUENE GIVES ORTHO, META
# AND PARA FROM ONE TEMPLATE, AND THE RATIO IS NOT A PREDICTION.** Directing
# effects are a transition-state property and this template has no transition
# state. What it does have is ``alpha``: with Evans-Polanyi on, the three isomers'
# barriers are ordered by their own formation enthalpies, so the thermodynamically
# preferred ring positions are also the fast ones. That recovers the ORDERING for
# an activating substituent and it does NOT recover the meta-directing case, where
# the kinetic preference runs against the thermodynamic one. Read a nitration
# isomer ratio here as "which products exist", not as "in what proportion".
#
# ⚠ **AND THIS TEMPLATE FEEDS ITSELF.** A nitroarene still has aromatic C-H, so
# the network keeps nitrating: toluene -> mono -> di -> tri is the TNT route and
# it is not scripted, but the same property is what ``library.alcohol_chemistry``
# warns about. Measured on toluene + nitric acid: **18 species, 29 reactions at
# ``generations=3``**, and 2,4,6-TNT is 15.3% of the toluene charged -- the rest is
# the other nitration isomers, which is the honest answer for a template with no
# directing effects. Cap the generations or the species count for a nitration
# network; do not let it run to a fixpoint and be surprised.


# rho -6.5 on the SIGMA-PLUS scale. Nitration of substituted benzenes in mixed
# acid is the textbook Brown-Okamoto correlation and the reported band is -6.0 to
# -7.3 depending on the acid strength the partial rate factors were measured in
# (Coombes, Moodie and Schofield's 68% H2SO4 work sits near the middle of it).
# -6.5 is taken as the middle, and what it PREDICTS is the check: nitrobenzene at
# 2.4e-5 of benzene's rate and 2,4-dinitrotoluene at 1.4e-8 of toluene's, i.e.
# 4.6 and 7.9 orders of magnitude, against the four to six per nitro group that
# make TNT manufacture a three-stage process. See validation/ring_deactivation.py,
# which measures the stages rather than asserting them.
NITRATION_RHO = -6.5


def aromatic_nitration(
    A: float = 1.0e10, Ea: float = 60_000.0, alpha: float = 0.0,
    catalyst: str | None = None, rho: float = NITRATION_RHO,
    saturation: float = hammett.SATURATION_DECADES,
) -> ReactionTemplate:
    """Ar-H + HNO3 -> Ar-NO2 + water. Electrophilic aromatic nitration.

    Written on the arene and the acid rather than on nitronium, so the nitronium
    pre-equilibrium is folded into the barrier -- which is what the literature
    band is measured on anyway. ``catalyst`` makes the sulfuric acid's role
    explicit in the rate law; the mixed-acid ratio is then a lever.

    ⚠⚠ **``Ea`` IS BENZENE'S BARRIER AND NOT EVERY ARENE'S**, and that is G2. It
    used to be every arene's, and the measurement that settled it is in
    ``reactions/hammett.py``: 1.0 mol of toluene and 3.5 mol of nitric acid
    reached **96% 2,4,6-TNT in ten seconds at room temperature**, with an endpoint
    that did not move between 300 and 380 K. A ring already carrying three nitro
    groups was being nitrated exactly as fast as a fresh one.

    ⚠ **``rho`` IS A DECLARATION AND IT IS SCALE-SPECIFIC.** -6.5 is on the
    sigma-plus scale; handing it aqueous sigma constants would multiply two bases
    together. ``hammett`` carries the table, the provenance and the things the
    model does not do.

    ⚠⚠ **AND THE LINE SATURATES (G6).** ``hammett_saturation`` defaults to
    2.686 decades -- log10(485), the mesitylene datum of Belson & Strachan 1989,
    the fastest nitration in that study its authors call diffusion-controlled --
    because nitration of a strongly activated arene is ENCOUNTER-CONTROLLED and
    further activation buys no rate. It is a HAND-AUTHORED constant with a stated
    bound, which is the licence MILESTONES § STATED NON-GOALS gives an A-factor,
    and ``hammett``'s docstring carries the band (2.02 to 2.69) it was chosen
    from. Together with G5's anilinium split this puts aniline at **1.9e-3 times
    benzene** in the most acidic flask this engine can reach, on the correct side
    of benzene at last; the free base alone used to be 2.8e8 times it. ⚠ Setting
    ``hammett_saturation=math.inf`` restores the bare line, which is how the cost
    of this is measured rather than argued.

    ⚠ Setting ``rho=0.0`` restores the pre-G2 template exactly, which is how the
    cost of this is measured rather than argued.

    ⚠ Irreversible. The reverse is a nitro group leaving an arene, which does not
    happen thermally; the only real path back is ipso substitution by a different
    electrophile, which is a different mechanism and not this one.
    """
    return ReactionTemplate(
        name="aromatic_nitration" + ("_acid" if catalyst else ""),
        smarts=_maybe_catalyse(
            "[cH:1].[OX2H1:2][N+:3](=[O:4])[O-:5]"
            ">>[c:1][N+:3](=[O:4])[O-:5].[OX2H2:2]",
            catalyst,
        ),
        A=_kinetics(A, catalyst), Ea=Ea, alpha=alpha,
        hammett_rho=rho, hammett_slot=0, hammett_saturation=saturation,
    )


# Ea 85 kJ/mol. SN2 of an alkoxide or phenoxide on an alkyl halide; the classic
# measurements on phenoxide + iodomethane and on alkoxide + primary bromide sit
# in the 80-95 kJ/mol band.


def williamson_ether_synthesis(
    A: float = 1.0e9, Ea: float = 85_000.0,
) -> ReactionTemplate:
    """R-O(-) + R'-X -> R-O-R' + X(-). The Williamson ether synthesis.

    ⚠ **THE ALKOXIDE IS NOT A REAGENT HERE, IT IS A SPECIES THE NETWORK MUST
    ALREADY HOLD.** ``[#6:4][O-;X1:1]`` matches whatever the dissociation
    templates put in the flask -- so a Williamson network needs
    ``dissociation_templates()`` and a phenol or an alcohol and a base, and
    "add sodium hydroxide" becomes a real step rather than a stated condition.
    Without them this template matches nothing, the same caveat
    ``library.acid_catalysed_chemistry`` carries about hydronium.

    ⚠ **A CARBOXYLATE MATCHES TOO, AND THAT IS CORRECT.** ``[O-]`` on a carbon is
    also an acetate, and acetate + iodomethane really does give methyl acetate.
    It is O-alkylation either way; the pattern was not narrowed to exclude it,
    because narrowing it would have removed real chemistry to make one route's
    output tidier.

    ⚠ Irreversible. The reverse is halide attacking an ether, which needs
    conditions (strong acid, HI) that are a different mechanism.
    """
    return ReactionTemplate(
        name="williamson_ether_synthesis",
        smarts="[#6:4][O-;X1:1].[CX4:2][F,Cl,Br,I:3]"
               ">>[#6:4][O+0:1][C:2].[F,Cl,Br,I;-:3]",
        A=A, Ea=Ea,
    )


# Ea 65 kJ/mol. Acid-catalysed condensation of an arene with a carbonyl; the
# bisphenol-A literature (phenol + acetone over HCl or a sulfonic resin) reports
# apparent barriers of 60-75 kJ/mol.


def friedel_crafts_hydroxyalkylation(
    A: float = 1.0e8, Ea: float = 65_000.0, catalyst: str | None = None,
) -> ReactionTemplate:
    """2 Ar-H + R2C=O -> Ar2CR2 + water. The diarylmethane condensation.

    One step for what is really two -- carbinol formation then a second
    arylation -- because that is how the catalog's rows read and because the
    carbinol is not isolable under the conditions. The stoichiometry is what
    survives the simplification.

    Three named routes are the same template on different partners: chloral +
    chlorobenzene gives DDT, acetone + phenol gives bisphenol A, benzaldehyde +
    dimethylaniline gives leucomalachite green. ⚠ And as with nitration the two
    ``[cH]`` slots match independently, so chlorobenzene gives the ortho, meta
    and para isomers of DDT as well as p,p'. The historical product is a mixture
    for exactly that reason.

    ⚠ Irreversible: the water leaves and the diarylmethane is not attacked back.
    """
    return ReactionTemplate(
        name="friedel_crafts_hydroxyalkylation" + ("_acid" if catalyst else ""),
        smarts=_maybe_catalyse(
            "[cH:1].[cH:2].[CX3:3]=[OX1:4]>>[c:1][C:3][c:2].[OX2H2:4]", catalyst
        ),
        A=_kinetics(A, catalyst), Ea=Ea,
    )


# Ea 90 kJ/mol. Kolbe-Schmitt carboxylation of sodium phenoxide, run at 400 K
# and 100 bar CO2; reported apparent barriers cluster at 85-95 kJ/mol.


def kolbe_schmitt(
    A: float = 1.0e8, Ea: float = 90_000.0,
) -> ReactionTemplate:
    """Phenoxide + CO2 -> salicylate. The carboxylation that makes aspirin possible.

    ⚠ **ORTHO IS IN THE PATTERN, NOT IN A CHOICE.** ``[O-:1][c:2][cH:3]`` requires
    the carbon being carboxylated to be ADJACENT to the one bearing the oxide, so
    the template cannot produce the para isomer at all. That is a real
    simplification -- potassium phenoxide gives para -- and it is the honest one
    here, because the counter-ion that decides it is a spectator this engine does
    not model.

    ⚠ **REVERSIBLE, AND THAT IS THE INTERESTING HALF.** Salicylate decarboxylates
    on heating, which is why the industrial reaction is run under CO2 pressure and
    why over-heating destroys the product. Nothing declares a maximum temperature;
    detailed balance derives one from the formation data, the same way the lead
    chamber's carrier ceiling is derived rather than declared.
    """
    return ReactionTemplate(
        name="kolbe_schmitt_carboxylation",
        smarts="[O-:1][c:2][cH:3].[CX2:4](=[OX1:5])=[OX1:6]"
               ">>[OX2H1;+0:1][c:2][c:3][C:4](=[O:5])[O-:6]",
        A=A, Ea=Ea, reversible=True,
    )


# ---------------------------------------------------------------------------
# THE ESTER GROUP -- and the Layer 3 fact that decided how to write it
# ---------------------------------------------------------------------------
# ⚠⚠ **A REVERSIBLE TEMPLATE IS DISCOVERED IN THE FORWARD DIRECTION ONLY, AND
# THAT IS WHY "esterification is reversible, so hydrolysis is already covered" IS
# FALSE.** Measured, because it is not obvious from reading either layer:
#
#     build_network(["CCOC(C)=O", "O"], [esterification()])   ->  0 reactions
#     build_network(["CC(=O)O", "CCO"], [esterification()])   ->  2 reactions
#                                                                 (forward + reverse)
#
# ``_expand_once`` matches the template's REACTANT patterns. Fischer esterification's
# are a carboxylic acid and an alcohol, and an ester is neither, so a flask charged
# with ester and water is INERT -- the derived reverse exists only as the mirror of
# a forward reaction the expansion already found. Put an ester and water in a flask
# and nothing happens, which is not what an ester in a flask does.
#
# ⚠ **THIS IS GENERAL AND IT IS NOT FIXED HERE.** Every reversible template in the
# project has the same property: the reverse is reachable only from the forward
# side. Fixing it properly means expanding on the reverse patterns too, which is
# Layer 3 work and would roughly double the match cost of every build. What M5 does
# instead is write the reaction from the side a chemist actually starts on.
#
# So ``ester-hydrolysis`` needs TWO templates and neither is redundant:
#
#   ester_hydrolysis  the acid/neutral route, reversible, reachable FROM the ester.
#                     Ea 70 kJ/mol -- aspirin hydrolysis, band 65-80.
#   saponification    hydroxide, and NOT reversible: the product is a carboxylate
#                     and an alcohol does not attack one. Ea 46 kJ/mol -- ethyl
#                     acetate + hydroxide is one of the best-measured rate constants
#                     in chemistry (0.11 L/(mol s) at 298 K), barrier band 45-48.
#   transesterif.     Ea 55 kJ/mol -- base-catalysed methanolysis of a triglyceride,
#                     the biodiesel literature's 50-70 kJ/mol band.
#
# ⚠ ``ester_hydrolysis`` and ``library.esterification`` DO overlap once both are in
# one network -- two channels between the same four species. Unlike the
# hydration/dehydration collision documented further down, this one is
# thermodynamically harmless: both are reversible, so detailed balance gives each
# channel the SAME K from the same formation data, and only the rate doubles. They
# are still kept out of one bundle, because a doubled rate is a wrong rate.


def saponification(A: float = 1.0e8, Ea: float = 46_000.0) -> ReactionTemplate:
    """Ester + hydroxide -> carboxylate + alcohol. Irreversible, and that is the point.

    ⚠ **THE IRREVERSIBILITY IS THE CHEMISTRY, NOT A CONVENIENCE.** Fischer
    esterification is an equilibrium and stops short; saponification runs to
    completion because the product is a carboxylate ANION and an alcohol does not
    attack one. That difference is why soap is made with lye and not with acid,
    and it is expressed here as the difference between a reversible template and
    an irreversible one rather than by anyone tuning a rate.

    Matches an aryl ester as well as an alkyl one -- ``[#6:4]`` -- because
    hydroxide does not care either.
    """
    return ReactionTemplate(
        name="saponification",
        smarts="[CX3:1](=[O:2])[OX2:3][#6:4].[OH-:5]"
               ">>[CX3:1](=[O:2])[O-:5].[OX2H1:3][#6:4]",
        A=A, Ea=Ea,
    )


def ester_hydrolysis(
    A: float = 1.0e8, Ea: float = 70_000.0, catalyst: str | None = None,
) -> ReactionTemplate:
    """Ester + water <=> carboxylic acid + alcohol. Aspirin in a damp cabinet.

    Written from the ESTER side on purpose -- see the block comment above for the
    measurement that forced it. Matches an alkyl ester and an aryl one alike, which
    is what the catalog's rows need: aspirin's ester oxygen is on an aromatic
    carbon, and a gallotannin's is on a sugar carbon while its acyl half is
    aromatic.

    ⚠ **AN ANHYDRIDE IS DELIBERATELY EXCLUDED** -- ``!$([CX3]=[OX1])`` on the
    leaving carbon. An anhydride is also ``C(=O)-O-C``, and it also hydrolyses, but
    orders of magnitude faster and by its own mechanism. Letting this pattern catch
    it would give anhydride hydrolysis an ester's barrier, so a flask of acetic
    anhydride would look storable in water. It is not.

    Reversible, and here that is not a doubling of ``library.esterification`` so
    much as its other face: same K from the same formation data, reached from the
    other side. Keep them in separate networks anyway.
    """
    return ReactionTemplate(
        name="ester_hydrolysis" + ("_acid" if catalyst else ""),
        smarts=_maybe_catalyse(
            "[CX3:1](=[O:2])[OX2:3][#6;!$([CX3]=[OX1]):4].[OX2H2:5]"
            ">>[CX3:1](=[O:2])[OX2H1:5].[OX2H1:3][#6:4]",
            catalyst,
        ),
        A=_kinetics(A, catalyst), Ea=Ea, reversible=True,
    )


def transesterification(
    A: float = 1.0e7, Ea: float = 55_000.0, alpha: float = 0.0,
) -> ReactionTemplate:
    """Ester + alcohol <=> ester' + alcohol'. Alcoholysis, and it is an equilibrium.

    Reversible, and it must be: the reason biodiesel is made with a six-fold
    excess of methanol is that this reaction stops in the middle otherwise. With
    the equilibrium in place "add more methanol" is a real lever with the right
    slope, and with it declared irreversible it would not be.

    ⚠ **THIS TEMPLATE REGENERATES ITS OWN MATCHED GROUPS AND IS THEREFORE
    SELF-FEEDING** -- the product is another ester and another alcohol. That is
    the property ``library.alcohol_chemistry`` identifies as the actual cause of
    network explosion. It stays bounded here only because the acyl and alkoxy
    pools are finite: n acyl groups and m alkoxy groups give n*m esters, not an
    unbounded series. A triglyceride feed is the case to watch, since it walks
    tri -> di -> mono -> glycerol and each stage is a fresh species. ⚠ Measured on
    triolein + methanol: only **8 species -- but 104 REACTIONS**, because every
    glyceride is an ester AND an alcohol, so the two slots pair them
    combinatorially. Watch the reaction count, not the species count.

    ⚠⚠ **AND THAT SAME NETWORK IS WHERE THE MIXED-STANDARD-STATE DEFECT WAS
    FOUND.** Monoolein's estimated vapour pressure is under ``PSAT_FLOOR_BAR``, so
    it stays on the ideal-gas basis while its partners move to the liquid one, and
    59 of those 104 reactions now print a NOTICE. **None of their equilibrium
    constants should be read** -- one of them reports +330 kJ/mol for a reaction
    that is thermoneutral. See ``standard_state.mixed_basis``, and note that this
    is a SPECIES limit rather than a template one: triolein and its glycerides are
    Joback-priced at C21-C57, well outside the estimator's domain.
    """
    return ReactionTemplate(
        name="transesterification",
        smarts="[CX3:1](=[O:2])[OX2:3][CX4:4].[OX2H1:5][CX4:6]"
               ">>[CX3:1](=[O:2])[O:5][C:6].[OX2H1:3][C:4]",
        A=A, Ea=Ea, alpha=alpha, reversible=True,
    )


# ---------------------------------------------------------------------------
# CARBONYL CONDENSATIONS -- four named reactions, four single mechanisms
# ---------------------------------------------------------------------------
#   n-acylation   Ea 45 kJ/mol -- aminolysis of acetic anhydride, band 40-55.
#   cannizzaro    Ea 55 kJ/mol -- benzaldehyde in concentrated hydroxide, 50-60.
#   perkin        Ea 95 kJ/mol -- the Perkin reaction needs 450 K for 8 hours,
#                 which is what a barrier near 100 kJ/mol looks like; band 90-105.
#   knoevenagel   Ea 70 kJ/mol -- amine-catalysed Doebner condensation, 60-80.


def n_acylation(A: float = 1.0e8, Ea: float = 45_000.0) -> ReactionTemplate:
    """Amine + anhydride -> amide + carboxylic acid. Paracetamol in one line.

    The amine pattern excludes an existing amide -- ``!$(N[#6]=[O,S,N])`` -- so
    the product does not acylate again to an imide. Without that clause
    4-aminophenol runs on past paracetamol, which is not what the reaction does.

    ⚠ **AN AMINOPHENOL HAS TWO NUCLEOPHILES AND THIS TEMPLATE PICKS ONE.** The
    phenol oxygen is also acylated by an anhydride in reality (that is the O,N-
    diacetyl impurity), and the pattern here does not express it. The selectivity
    is asserted, not derived, and it is the one place in this module where a real
    side product is missing rather than emergent.

    ⚠ Irreversible: an anhydride is the activation, and the amide does not give it
    back.
    """
    return ReactionTemplate(
        name="n_acylation",
        smarts="[NX3;H1,H2;!$(N[#6]=[O,S,N]):6].[CX3:1](=[O:2])[OX2:3][CX3:4]=[O:5]"
               ">>[N:6][C:1]=[O:2].[OX2H1:3][C:4]=[O:5]",
        A=A, Ea=Ea,
    )


def cannizzaro(A: float = 1.0e7, Ea: float = 55_000.0) -> ReactionTemplate:
    """2 Ar-CHO + hydroxide -> Ar-CH2OH + Ar-COO(-). Disproportionation of an aldehyde.

    ⚠ **RESTRICTED TO AN AROMATIC ALDEHYDE, AND THAT RESTRICTION IS THE
    MECHANISM.** An aldehyde with an alpha C-H enolises instead and goes down the
    aldol route; only one with no enolisable hydrogen has nowhere to go but hydride
    transfer. Writing this on ``[CX3H1]=O`` generally would have made acetaldehyde
    disproportionate, which it does not do. ``[c:3]`` is the cheapest correct
    statement of "no alpha hydrogen" for the substrates the catalog actually uses;
    formaldehyde and trimethylacetaldehyde qualify chemically and are not matched.

    Three reactant slots and two of them are the same species, so the rate is
    second order in the aldehyde -- which is real, and is why a dilute Cannizzaro
    is slow out of proportion to its concentration.
    """
    return ReactionTemplate(
        name="cannizzaro_disproportionation",
        smarts="[c:3][CX3H1:1]=[OX1:2].[c:6][CX3H1:4]=[OX1:5].[OH-:7]"
               ">>[c:3][CH2:1][OX2H1:2].[c:6][C:4](=[O:5])[O-:7]",
        A=A, Ea=Ea,
    )


def perkin_condensation(A: float = 1.0e9, Ea: float = 95_000.0) -> ReactionTemplate:
    """Ar-CHO + anhydride -> cinnamic acid + carboxylic acid. The Perkin reaction.

    The anhydride's methyl is the nucleophile and the aldehyde oxygen leaves in
    the carboxylic acid, which is what the mapping says. Restricted to ``[CH3:4]``
    on the anhydride, so acetic anhydride works and a branched anhydride does not
    -- the real reaction is fussier still.

    ⚠ Irreversible. The product is a conjugated acid and the driving force is that
    conjugation; the retro-Perkin is not a bench reaction.
    """
    return ReactionTemplate(
        name="perkin_condensation",
        smarts="[c:1][CX3H1:2]=[OX1:3].[CH3:4][CX3:5](=[O:6])[OX2:7][CX3:8]=[O:9]"
               ">>[c:1][CH:2]=[CH:4][C:5](=[O:6])[OX2H1:7].[OX2H1:3][C:8]=[O:9]",
        A=A, Ea=Ea,
    )


def knoevenagel_doebner(
    A: float = 1.0e8, Ea: float = 70_000.0, catalyst: str | None = None,
) -> ReactionTemplate:
    """Ar-CHO + malonic acid -> cinnamic acid + CO2 + water. Condense, then decarboxylate.

    Two steps written as one, and the catalog's row writes it that way too: the
    Knoevenagel condensation gives the arylidenemalonic acid and the Doebner
    modification decarboxylates it in the same pot. The intermediate is not
    isolated under these conditions, so the lumped step is the honest unit.

    ⚠ Irreversible, and unusually safe to say so: one product is CO2 leaving a
    refluxing solution. Nothing comes back from a gas that has left the flask.

    ⚠ **THE SAME PRODUCT AS ``perkin_condensation``, FROM A DIFFERENT MECHANISM
    AND A DIFFERENT BARRIER, AND THAT IS DELIBERATE.** Both make cinnamic acid
    from benzaldehyde. Perkin needs 450 K and eight hours; Knoevenagel-Doebner
    runs at reflux in pyridine. Two templates with 95 and 70 kJ/mol reproduce that
    ordering, and a flask holding both an anhydride and malonic acid will show it
    without anyone scripting which one wins.
    """
    return ReactionTemplate(
        name="knoevenagel_doebner_condensation" + ("_base" if catalyst else ""),
        smarts=_maybe_catalyse(
            "[c:1][CX3H1:2]=[OX1:3]."
            "[CX4H2:4]([CX3:5](=[O:6])[OX2H1:7])[CX3:8](=[O:9])[OX2H1:10]"
            ">>[c:1][CH:2]=[CH:4][C:5](=[O:6])[O:7].[C:8](=[O:9])=[O:10]."
            "[OX2H2:3]",
            catalyst,
        ),
        A=_kinetics(A, catalyst), Ea=Ea,
    )


# ---------------------------------------------------------------------------
# ADDITIONS TO C=C AND C#C -- and the one that collides with an existing template
# ---------------------------------------------------------------------------
#   alkene hydration  Ea 80 kJ/mol -- direct hydration of ethylene over phosphoric
#                     acid, apparent band 75-90.
#   alkyne hydration  Ea 70 kJ/mol -- mercury(II)-catalysed, band 65-80.
#   hydrogenation     Ea 50 kJ/mol -- heterogeneous alkene hydrogenation over
#                     nickel or palladium, apparent band 40-60.
#
# ⚠⚠ **``alkene_hydration`` IS REVERSIBLE AND ``library.alkene_dehydration`` IS
# NOT, AND THE TWO ARE THE SAME INTERCONVERSION.** This is the one place in the
# project where two templates describe one equilibrium, and it is declared rather
# than resolved because both readings are defensible and they are used at opposite
# ends of the temperature range:
#
#   * ``alkene_dehydration`` (Ea 160) is the neat, hot, sulfuric-acid E1 that
#     competes with ether formation. It eliminates INTO a large excess of water
#     and its reverse is negligible there, which is the argument ``library.py``
#     makes for leaving it one-way.
#   * ``alkene_hydration`` (Ea 80) is the industrial reaction run at 570 K and 70
#     bar with steam in excess, where the equilibrium is the whole engineering
#     problem -- per-pass conversion is about 5%.
#
# ⚠ **THE CONSEQUENCE, STATED: a network holding BOTH has two channels between the
# same pair of species with unequal barriers, so its steady state is not its
# equilibrium.** That is a genuine defect and the bound on it is that the two
# barriers differ by 80 kJ/mol, so at any one temperature one channel is ~1e7
# times the other and the faster one sets the answer. Do not put both in one
# network without deciding which reaction you are running. The bundles below keep
# them apart.


def alkene_hydration(
    A: float = 1.0e10, Ea: float = 80_000.0, alpha: float = 0.0,
    catalyst: str | None = None, phase: str = "liquid",
) -> ReactionTemplate:
    """Alkene + water <=> alcohol. A flask reaction and an industrial one.

    ⚠ **MARKOVNIKOV IS NOT IN THE PATTERN AND CANNOT BE.** Both carbons of the
    double bond match, so propene gives 1-propanol as well as 2-propanol. As with
    nitration, ``alpha`` is what recovers the ORDERING: the Markovnikov alcohol is
    the more stable product and Evans-Polanyi hands it the lower barrier from the
    formation data. Ethylene, the case the catalog actually runs, is symmetric and
    the question does not arise.

    ⚠⚠ **``phase`` IS AN ARGUMENT RATHER THAN ``"any"``, AND THE MEASUREMENT IS
    WHY.** Direct hydration of ethylene is a VAPOUR-phase process -- 570 K, 70 bar,
    phosphoric acid on silica -- and its defining engineering fact is that
    per-pass conversion is only about 5%, which is why the plant is mostly a
    recycle loop. Run on this template that is reproduced rather than declared:

        phase="gas",    570 K, 2 mol C2H4 / 20 mol H2O   ->  2.9% conversion
        phase="liquid", 570 K, same charge               ->  99.7% conversion

    Both numbers are right for their own standard state. The liquid one is a
    pure-liquid basis, which moves K by ``R T ln(Psat)`` per species and, for a
    reaction that consumes a gas to make a liquid, moves it hard. Declaring
    ``phase="any"`` would put BOTH channels in one network, and the liquid one
    would then run the flask to completion off a trace of condensate -- destroying
    the 2.9% that is the whole point of the process. So the caller says which
    reaction is being run.

    Reversible. See the block comment above for the collision with
    ``library.alkene_dehydration`` and why it is declared rather than fixed.
    """
    return ReactionTemplate(
        name="alkene_hydration" + ("_acid" if catalyst else ""),
        smarts=_maybe_catalyse(
            "[CX3:1]=[CX3:2].[OX2H2:3]>>[C:1][C:2][OX2H1:3]", catalyst
        ),
        A=_kinetics(A, catalyst), Ea=Ea, alpha=alpha, reversible=True,
        phase=phase,
    )


def alkyne_hydration(
    A: float = 1.0e9, Ea: float = 70_000.0, catalyst: str | None = None,
) -> ReactionTemplate:
    """Alkyne + water -> carbonyl. Acetylene to acetaldehyde, the Kucherov reaction.

    Written straight to the carbonyl rather than to the enol, because the
    tautomerisation is far faster than the hydration and an enol species in the
    state vector would be a variable that is always zero. That is a real
    simplification and it is where the irreversibility comes from as well: the
    hydration alone is reversible, the tautomerisation is the sink, and lumping
    them makes the pair one-way.
    """
    return ReactionTemplate(
        name="alkyne_hydration" + ("_acid" if catalyst else ""),
        smarts=_maybe_catalyse(
            "[CX2:1]#[CX2:2].[OX2H2:3]>>[C:1](=[O:3])[C:2]", catalyst
        ),
        A=_kinetics(A, catalyst), Ea=Ea,
    )


def alkene_hydrogenation(
    A: float = 1.0e7, Ea: float = 50_000.0, alpha: float = 0.0,
    catalyst: str | None = "nickel",
) -> ReactionTemplate:
    """Alkene + H2 -> alkane. Hardening a fat, and the first template that eats H2.

    ⚠ **HETEROGENEOUS, AND THE NICKEL IS NOW A SPECIES.** ``catalyst="nickel"``
    is the default: the metal has to be in the flask's solid block or the rate is
    exactly zero, which is what makes "you need a catalyst" a gate rather than a
    remark. Pass ``catalyst=None`` for the old behaviour -- an apparent barrier
    with the cycle folded into it, the licence ``sulfur_dioxide_oxidation`` still
    takes -- and the two give the SAME rate at
    ``library.SOLID_CATALYST_REFERENCE`` (0.1 mol, 5.9 g of nickel).

    ⚠ What is still NOT modelled is the SITE BALANCE: this is first order in the
    nickel for ever, so ten times the metal is ten times the rate. See
    ``library.py``'s docstring, where that is the remaining gap rather than a
    detail.

    ⚠ Irreversible, which is a claim about temperature rather than about
    thermodynamics. Dehydrogenation is real and industrial above ~800 K; margarine
    is hardened at 450 K, where the equilibrium is ~1e9 to the right. Declaring it
    reversible would hand detailed balance a cracking reaction to derive at
    temperatures nothing here runs at.

    Aromatics correctly refuse: benzene's ring bonds are aromatic, not double, so
    ``[CX3]=[CX3]`` does not match and nobody has to say that hydrogenating an
    arene is harder.
    """
    return ReactionTemplate(
        name="alkene_hydrogenation",
        smarts="[CX3:1]=[CX3:2].[H:3][H:4]>>[C:1]([H:3])[C:2][H:4]",
        A=_surface_kinetics(A, catalyst), Ea=Ea, alpha=alpha,
        solid_catalyst=catalyst,
    )


# ⚠ ``catalytic-hydrogenation`` WAS THE SIXTH OUTCOME LABEL, AND IT IS THE ONE M5
# SPLIT RATHER THAN REFUSED. It is the most-used class with no template in the
# whole corpus -- ten steps -- and its ten rows are at least four mechanisms:
#
#     nitro -> amine          aniline-route, phenacetin-route, polyurethane-route
#     nitro -> hydroxylamine  paracetamol-route -- a STOPPED reduction, different
#                             stoichiometry, and the whole difficulty of that route
#     C=C -> C-C              hydrogenation-margarine, menthol-route, diels-alder
#     C=O -> C-OH             vitamin-c-reichstein (glucose -> sorbitol)
#     arene -> saturated ring furfural-route (furan -> THF)
#
# Refusing the class would have been the easy call and the wrong one: unlike
# ``fermentation`` or ``pyrolysis``, every row here IS a clean mechanism -- they are
# just five different ones sharing a reactor. So the rows were re-labelled to what
# they are, on M1's precedent, and two of the five are built. ⚠ The re-label is
# recorded in ``data/catalog/README.md``; read it before quoting the class list.
#
# Ea 50 kJ/mol for the nitro reduction: apparent barrier for nitrobenzene
# hydrogenation over nickel or copper, band 40-60.


def nitro_hydrogenation(
    A: float = 1.0e5, Ea: float = 50_000.0, catalyst: str | None = "nickel",
) -> ReactionTemplate:
    """Ar-NO2 + 3 H2 -> Ar-NH2 + 2 water. Nitrobenzene to aniline.

    The arrow the whole dyestuffs industry was built on, and the second half of
    every nitration route in the catalog: nitrate the ring, then reduce it.

    ⚠ **IT GOES ALL THE WAY, AND STOPPING IT IS A DIFFERENT REACTION.** The
    paracetamol route needs nitrobenzene reduced only as far as
    phenylhydroxylamine, which is a two-hydrogen reduction with its own
    stoichiometry -- not this template run briefly. That row is labelled
    ``nitro-partial-hydrogenation`` in the catalog and has no template; writing
    this one and claiming the partial case would be a stoichiometry that does not
    balance pretending to be selectivity.

    ⚠ Heterogeneous, and the nickel is a species -- see ``alkene_hydrogenation``
    above. Irreversible: the reverse is oxidising an amine back to a nitro group
    with water, which is not a reaction.
    """
    return ReactionTemplate(
        name="nitro_hydrogenation",
        smarts="[c:1][N+:2](=[O:3])[O-:4].[H:5][H:6].[H:7][H:8].[H:9][H:10]"
               ">>[c:1][N+0:2]([H:5])[H:6].[O+0:3]([H:7])[H:8].[O+0:4]([H:9])[H:10]",
        A=_surface_kinetics(A, catalyst), Ea=Ea, solid_catalyst=catalyst,
    )


# ---------------------------------------------------------------------------
# HALOGEN IN BASE -- one template, and the reason bleach and acid do not mix
# ---------------------------------------------------------------------------
# Ea 35 kJ/mol. Chlorine hydrolysis and disproportionation in alkali is fast at
# room temperature; the reported barriers for the hydrolysis step sit at 30-40.


def halogen_disproportionation(
    A: float = 1.0e9, Ea: float = 35_000.0,
) -> ReactionTemplate:
    """X2 + 2 OH(-) <=> X(-) + XO(-) + water. Chlorine into caustic gives bleach.

    ⚠ **REVERSIBLE, AND THE REVERSE IS THE SAFETY WARNING ON THE BOTTLE.** Running
    it backwards is hypochlorite plus chloride plus acid giving chlorine gas back,
    which is the single most common way a domestic chemist is injured. Nothing here
    declares that: the flask holds the equilibrium, an acid added to the flask
    consumes hydroxide through the dissociation templates, and the chlorine comes
    off into the headspace because the equilibrium moved. It is the lead chamber's
    lesson again -- a mechanic that is watchable and losable beats a rule.

    ⚠ **AND IT NEEDS THE DISSOCIATION TEMPLATES TO MEAN ANYTHING**, since both
    hydroxide and the hypochlorite it makes are ions. A network built without them
    has no ``[OH-]`` and this template matches nothing.

    Bromine and iodine match too, which is right: the same reaction makes
    hypobromite and hypoiodite, and the iodine case is the first step of the
    iodoform test.
    """
    return ReactionTemplate(
        name="halogen_disproportionation",
        smarts="[Cl,Br,I;X1:1][Cl,Br,I;X1:2].[O;H1;X1;-:3].[O;H1;X1;-:4]"
               ">>[Cl,Br,I;-:1].[Cl,Br,I;+0:2][O-;H0:3].[O;H2;+0:4]",
        A=A, Ea=Ea, reversible=True,
    )


# ---------------------------------------------------------------------------
# SYNTHESIS GAS -- three reversible gas-phase equilibria, and no catalyst species
# ---------------------------------------------------------------------------
# ⚠⚠ **ALL THREE ARE HETEROGENEOUS AND ALL THREE NOW SAY SO.** "Promoted iron"
# and "Cu/ZnO" are the entire reason these processes exist, and for several
# sessions they were folded into an apparent barrier -- so a flask with no iron in
# it made ammonia, and this project reported that rather than hiding it. The metal
# is now a declared ``solid_catalyst`` and has to be in the flask.
#
# ⚠ WHICH SOLID, AND WHY THE TWO METHANOL ROWS DIFFER FROM EACH OTHER IN NOTHING
# ELSE. Haber-Bosch is iron. Cu/ZnO is a two-component catalyst and this kernel
# expresses one solid per reaction, so the COPPER is declared and the zinc oxide
# is not: the metal is where the hydrogen dissociates, and ``zincite`` is already
# a species in ``mineral_data`` for anyone who wants to charge it as well (it will
# sit there and do nothing, which is honest -- a promoter is not modelled).
#
# What survives unchanged is the STOICHIOMETRY and the EQUILIBRIUM, and the
# catalyst cannot touch either: its exponent is identical on both arrows, so it
# divides out of ``k_f/k_r``. Both processes are pressure-driven and
# temperature-limited and neither of those facts is declared anywhere.
#
#   ammonia    Ea 100 kJ/mol -- apparent barrier over promoted iron, band 100-170;
#              the low end, because the low end is what a promoted catalyst buys.
#   CO route   Ea 70 kJ/mol  -- Cu/ZnO methanol synthesis, band 60-85.
#   CO2 route  Ea 80 kJ/mol  -- the same catalyst on CO2, consistently the slower
#              of the two, which is why the barrier is the higher of the two.
#
# ⚠ **THE PRE-EXPONENTIALS ARE FOR A FOURTH- AND THIRD-ORDER RATE LAW AND ARE NOT
# COLLISION FREQUENCIES.** N2 + 3 H2 taken as mass action is fourth order, and
# unlike the sulfur burner that is NOT a reason to declare an apparent order here:
# an apparent order may never be reversible (see ``ReactionTemplate.orders``) and
# the equilibrium is the only thing these templates are for. The burner's problem
# does not arise anyway -- it was ``[O2]^8`` stalling at 3e-20, and at 200 bar
# these concentrations are of order 1 mol/L, so the high order costs nothing.
# ⚠ Run them at pressure. At 1 bar the fourth-order rate is ~1e4 times slower and
# the flask will look inert, which is also what a real ammonia plant would be.


def ammonia_synthesis(
    A: float = 1.0e6, Ea: float = 100_000.0, catalyst: str | None = "iron",
) -> ReactionTemplate:
    """N2 + 3 H2 <=> 2 NH3. Haber-Bosch, and the iron is a SPECIES.

    Reversible, and everything a player would want from it follows from that plus
    the thermochemistry: the reaction is exothermic and loses moles, so it is
    favoured cold and compressed and it has an emergent temperature ceiling. None
    of that is declared. It is the lead chamber's derived ceiling again, on a
    reaction where the ceiling is the famous part.

    ⚠ **A FLASK WITH NO IRON IN IT MAKES NO AMMONIA**, which is the whole point
    of ``catalyst="iron"`` being the default. The iron is in the network whether
    or not anyone charges it, so "put iron in the flask" is a runtime action and a
    player can add it half way through a run. ``catalyst=None`` reproduces the old
    behaviour exactly, and the two agree to the last digit at 0.1 mol of iron --
    ``library.SOLID_CATALYST_REFERENCE``.

    ⚠ The catalyst does NOT move the equilibrium and could not. Detailed balance
    puts its order-1 factor on both arrows, so it cancels out of ``k_f/k_r``: what
    an uncatalysed flask reaches is the same equilibrium, infinitely slowly.

    ⚠ Hydrogen is written as an ATOM pair, which is what forced
    ``ReactionTemplate.run`` to collapse explicit hydrogens. See the module
    docstring.
    """
    return ReactionTemplate(
        name="ammonia_synthesis",
        smarts="[N:1]#[N:2].[H:3][H:4].[H:5][H:6].[H:7][H:8]"
               ">>[N:1]([H:3])([H:5])[H:7].[N:2]([H:4])([H:6])[H:8]",
        A=_surface_kinetics(A, catalyst), Ea=Ea, phase="gas", reversible=True,
        solid_catalyst=catalyst,
    )


def methanol_from_carbon_monoxide(
    A: float = 1.0e6, Ea: float = 70_000.0, catalyst: str | None = "copper",
) -> ReactionTemplate:
    """CO + 2 H2 <=> methanol. The main arrow of the Cu/ZnO synthesis."""
    return ReactionTemplate(
        name="methanol_from_carbon_monoxide",
        smarts="[C-:1]#[O+:2].[H:3][H:4].[H:5][H:6]"
               ">>[C+0:1]([H:3])([H:4])([H:5])[O+0:2][H:6]",
        A=_surface_kinetics(A, catalyst), Ea=Ea, phase="gas", reversible=True,
        solid_catalyst=catalyst,
    )


def methanol_from_carbon_dioxide(
    A: float = 1.0e5, Ea: float = 80_000.0, catalyst: str | None = "copper",
) -> ReactionTemplate:
    """CO2 + 3 H2 <=> methanol + water. The same reactor's second arrow.

    A separate template rather than a variant, because it is a different
    stoichiometry with a different equilibrium and a different barrier -- and
    because running the two together is what the catalog's ``methanol-synthesis``
    route actually is. The water it makes is not a detail: it is why a real
    methanol loop needs a drier.
    """
    return ReactionTemplate(
        name="methanol_from_carbon_dioxide",
        smarts="[O:1]=[C:2]=[O:3].[H:4][H:5].[H:6][H:7].[H:8][H:9]"
               ">>[C:2]([H:4])([H:5])([H:6])[O:1][H:7].[O:3]([H:8])[H:9]",
        A=_surface_kinetics(A, catalyst), Ea=Ea, phase="gas", reversible=True,
        solid_catalyst=catalyst,
    )


# ---------------------------------------------------------------------------
# S7 -- THE FOUR INORGANIC GAS PROCESSES, AND WHY THEY WERE THE RIGHT FOUR
# ---------------------------------------------------------------------------
# ⚠⚠ **CHOSEN OFF THE `RUNNABLE` COLUMN, NOT THE UNLOCK COUNT** -- and then off a
# THIRD column the instrument does not have. `catalog_coverage`'s work queue is
# ranked by routes a class unlocks that are also species-ready, and its top two
# rows are `isomerisation` (+3/+2) and `crosslinking` (+2/+2). S7 measured both
# before costing either, and **both are worth zero honest routes**:
#
#   `isomerisation`   three rows, three mechanisms -- the split M5 refused to do
#                     blind. And every one of the three fails for its OWN reason:
#                     `oleic -> elaidic` is priced by Benson at **dH = dG = 0.000
#                     EXACTLY** because no estimator here can tell a cis alkene
#                     from a trans one, so the template would report a confident
#                     50:50 for a real 5:1; `glucose -> fructose` comes out at
#                     **dG +41.8 kJ/mol, K = 4.8e-08**, because the catalog spells
#                     glucose as a PYRANOSE and fructose as a FURANOSE and Benson
#                     charges the ring difference -- an industrial process the
#                     engine would say cannot happen; and `ammonium-cyanate ->
#                     urea` is not species-ready at all (a dot-separated ionic
#                     pair, and cyanate is in no ion table here).
#   `crosslinking`    two rows, two products with no chemistry behind them.
#                     `tanned-leather-marker` has no molecular graph. And
#                     `vulcanised-rubber-marker` is spelled `CC(C)=CC.S1SSSSSSS1`
#                     -- **its own two reactants written side by side**, so the
#                     "reaction" is `A + B -> A.B`, which nothing makes. Joback
#                     priced that mixture **+222.11 kJ/mol above the sum of its
#                     own parts**, which is the measurement that closed the
#                     neutral-fragment hole in `thermochemistry`.
#
# ⚠ **SO THE `RUNNABLE` COLUMN HAS THE SAME SHAPE OF FAULT `ALONE` HAD.** It
# asks whether every species RESOLVES. It cannot ask whether the number that
# comes back is RIGHT, and it cannot ask whether the row's product is a graph at
# all. Two of the queue's top two rows fail on exactly those two questions.
#
# What is below is the four rows that pass all three: an inorganic gas-phase
# process whose every species is measured, whose product is a real molecule, and
# whose equilibrium comes out at the textbook value before a line of code is
# written. The bound, computed against this project's own tables at 298.15 K and
# at each row's own operating temperature:
#
#   water-gas shift   dH -41.15 (book -41.2)   K = 22.0 at 620 K
#   steam reforming   dH +206.2 (book +206)    K = 1.2e-25 at 298 K, 295 at 1100 K
#   Deacon            dH -114.4 (book -114.5)  K = 2.0e+13 at 298 K, 46.4 at 700 K
#   Claus             dH -108.0 per SO2        ln K = 29.0 at 298 K, 11.8 at 500 K
#
# ⚠ **THREE OF THE FOUR ARE INTERESTING ONLY BECAUSE THEY ARE REVERSIBLE.** Steam
# reforming is impossible at room temperature and spontaneous above ~900 K; the
# shift runs the other way when you heat it; Deacon never went to completion and
# that is the historical fact that killed it. None of those three behaviours is
# declared anywhere -- each is `reversible=True` meeting the formation table.
#
# ⚠ AND THE FOURTH IS NOT REVERSIBLE, ON THE BURNER'S OWN ARGUMENT. See
# `claus_comproportionation`.
#
# The barriers, each an APPARENT barrier over the named catalyst and each inside
# a published band:
#
#   water-gas shift   Ea 110 kJ/mol  -- Fe/Cr high-temperature shift, band 95-130
#   steam reforming   Ea 240 kJ/mol  -- Xu & Froment's E1 over Ni, the standard
#                                       value; it is why the reformer is a furnace
#   Deacon            Ea 100 kJ/mol  -- Cu-catalysed HCl oxidation, band 85-120
#   H2S combustion    Ea 100 kJ/mol  -- the burner's own number, same footing:
#                                       an apparent barrier on a branched chain
#   Claus             Ea  50 kJ/mol  -- the catalytic stage over alumina, band 40-70


def water_gas_shift(
    A: float = 1.0e8, Ea: float = 110_000.0, catalyst: str | None = "hematite",
) -> ReactionTemplate:
    """CO + H2O <=> CO2 + H2. The shift, and the reason it is a SEPARATE reactor.

    ⚠ **THE WHOLE PROCESS IS THE REVERSIBILITY.** dH is -41.15 kJ/mol, so the
    equilibrium constant FALLS as the reactor heats: 1.0e5 at 298 K, 22 at the
    620 K high-temperature shift, 9.4 at 700 K. That is exactly why a real
    ammonia plant runs the shift twice -- hot to get the rate, then cold to get
    the conversion -- and nothing here declares it. Heat this flask and it
    unshifts.

    ⚠ The mole count is unchanged on both sides, so pressure does NOT move it,
    which is the one lever a player will reach for first and the one that does
    nothing. That falls out of the stoichiometry rather than being stated.

    The catalyst is hematite, which is what the catalog row carries and what the
    high-temperature shift actually uses (Fe3O4/Cr2O3 in service, magnetite
    reduced in situ from the hematite charged into it -- this engine holds the
    charged form, and the reduction is not modelled).
    """
    return ReactionTemplate(
        name="water_gas_shift",
        smarts="[C-:1]#[O+:2].[OX2H2:3]>>[O+0:2]=[C+0:1]=[O:3].[H][H]",
        A=_surface_kinetics(A, catalyst), Ea=Ea, phase="gas", reversible=True,
        solid_catalyst=catalyst,
    )


def steam_reforming(
    A: float = 1.0e11, Ea: float = 240_000.0, catalyst: str | None = "nickel",
) -> ReactionTemplate:
    """CH4 + H2O <=> CO + 3 H2. Where nearly all industrial hydrogen comes from.

    ⚠ **IMPOSSIBLE COLD AND SPONTANEOUS HOT, AND THAT CROSSING IS DERIVED.** dG
    is +142.2 kJ/mol at 298 K (K = 1.2e-25) and -52.0 at 1100 K (K = 295): the
    reaction is strongly endothermic and makes two extra moles of gas, so it
    needs heat twice over -- once for the enthalpy and once for the entropy. The
    engine finds the crossing near 900 K on its own, from the formation table.

    ⚠ And the mole increase means it is the ONE gas-phase equilibrium in this
    project that pressure hurts. A real reformer runs at 25 bar anyway, for the
    downstream synthesis loop, and pays for it in temperature.

    ⚠ **THE PRE-EXPONENTIAL IS LARGE AND THAT IS THE BARRIER'S DOING.** 240
    kJ/mol at 1100 K is a factor of 4e-12, so a collision-limited A would give a
    dead reactor; 1e11 L/(mol s) IS the collision limit for a bimolecular gas
    reaction, and this rate law is bimolecular as written. Both numbers are at
    their physical ceiling and the reaction is still slow below 900 K, which is
    what a reformer is like.
    """
    return ReactionTemplate(
        name="steam_reforming",
        smarts="[C;H4:1].[O;H2:2]>>[C-:1]#[O+:2].[H][H].[H][H].[H][H]",
        A=_surface_kinetics(A, catalyst), Ea=Ea, phase="gas", reversible=True,
        solid_catalyst=catalyst,
    )


def deacon_oxidation(
    A: float = 1.0e13, Ea: float = 100_000.0, catalyst: str | None = "tenorite",
) -> ReactionTemplate:
    """4 HCl + O2 <=> 2 Cl2 + 2 H2O. Chlorine back out of spent hydrochloric acid.

    ⚠ **REVERSIBLE, AND THE REVERSE IS WHY THIS PROCESS LOST.** ln K is +30.6 at
    298 K and +3.84 at the 700 K it has to be run at to go at all, so the
    conversion ceiling falls as the rate rises and the reactor can never have
    both. Deacon was displaced by electrolysis for exactly that reason, and the
    engine reproduces the squeeze without being told: heat it for rate and watch
    the equilibrium conversion collapse.

    ⚠⚠ **A IS 1e13 AND IT IS NOT A COLLISION FREQUENCY -- THE RATE LAW IS FIFTH
    ORDER.** ``ammonia_synthesis`` makes the same statement for a fourth-order
    law and the units are the point (M8's lesson): a fifth-order pre-exponential
    is in L^4/(mol^4 s) and the collision limit is a number in L/(mol s), so
    comparing them is a category error. What bounds it instead is the measured
    behaviour of the real reactor, and ``validation/gas_processes.py`` panel 3
    is that measurement: at 1e13 the flask is at equilibrium inside TEN SECONDS
    at 600 K and above, and still climbing after an hour below 500 K. A Deacon
    converter's contact time is seconds, so the crossing lands where the process
    actually sat. ⚠ The brief for this template said "on a scale of minutes at
    700 K" and the run said ten seconds; the number stayed and the claim was
    corrected, because ten seconds is the defensible one.
    ⚠ Mass action, not a declared order, because the equilibrium is the
    whole point and a declared order may never be reversible.

    ⚠ Like Haber-Bosch it wants pressure -- [HCl]^4 at 1 bar is a small number --
    and unlike Haber-Bosch it gains nothing thermodynamically by it: 5 moles in,
    4 out, so compressing it helps the rate and the equilibrium alike here.
    """
    return ReactionTemplate(
        name="deacon_oxidation",
        smarts="[Cl;H1:1].[Cl;H1:2].[Cl;H1:3].[Cl;H1:4].[OX1:5]=[OX1:6]"
               ">>[Cl;H0:1][Cl;H0:2].[Cl;H0:3][Cl;H0:4].[O;H2:5].[O;H2:6]",
        A=_surface_kinetics(A, catalyst), Ea=Ea, phase="gas", reversible=True,
        solid_catalyst=catalyst,
    )


def hydrogen_sulfide_combustion(
    A: float = 1.0e10, Ea: float = 100_000.0,
) -> ReactionTemplate:
    """2 H2S + 3 O2 -> 2 SO2 + 2 H2O. The Claus THERMAL stage.

    The burner's twin, and it takes the burner's two decisions verbatim because
    it is the same kind of reaction: an apparent barrier on a branched chain, and
    a DECLARED order rather than the fifth order the stoichiometry would impose.
    First order in hydrogen sulfide, first order in oxygen. ln K is 227 at 298 K,
    so nothing is lost by giving up the reverse.

    ⚠ It is deliberately written to burn hydrogen sulfide ALL the way, which is
    what the catalog row says and what a Claus furnace does to one third of the
    feed. The other two thirds pass through unburnt to meet this SO2 in the
    catalytic stage, and that ratio is a FEED decision rather than a chemistry
    one -- charge two moles of H2S for every one you want burnt and the pair of
    templates does the rest.
    """
    h2s = "[S;H2:1].[S;H2:2]"
    o2 = ".".join(f"[OX1:{3 + 2 * i}]=[OX1:{4 + 2 * i}]" for i in range(3))
    out = ("[O:3]=[S;H0:1]=[O:4].[O:5]=[S;H0:2]=[O:6]"
           ".[O;H2:7].[O;H2:8]")
    return ReactionTemplate(
        name="hydrogen_sulfide_combustion",
        smarts=f"{h2s}.{o2}>>{out}",
        A=A, Ea=Ea, phase="gas",
        orders=(1.0, 0.0, 1.0, 0.0, 0.0),
    )


def claus_comproportionation(
    A: float = 1.0e9, Ea: float = 50_000.0,
) -> ReactionTemplate:
    """16 H2S + 8 SO2 -> 3 S8 + 16 H2O. Sulfur out of both of its own oxidation states.

    ⚠ **TWENTY-FOUR REACTANT SLOTS, AND THE REASON IS S8.** The chemistry is
    ``2 H2S + SO2 -> 3 S + 2 H2O``; this project's sulfur is the S8 crown, and
    the smallest whole-number multiple that makes crowns out of it is sixteen
    and eight. A graph rewrite cannot write 3/8 of a ring.

    ⚠ **DECLARED ORDER, AND THEREFORE NOT REVERSIBLE -- the burner's argument,
    with a bigger number in it.** Mass action on twenty-four slots would put
    ``[H2S]^16 [SO2]^8`` in the rate law, which at any concentration a flask ever
    holds is zero to several hundred digits. Declared first order in each of the
    two reagents, which is the apparent rate law measured over alumina. Giving up
    the reverse costs nothing: ln K is +232 at 298 K and still +61 at 600 K.

    ⚠ **THE REAL PROCESS'S CONVERSION CEILING IS NOT THERMODYNAMIC HERE, AND THE
    ENGINE STILL FINDS ONE.** A real Claus train stops near 70% per stage; this
    equilibrium says 100%. What the vessel does instead is CONDENSE the sulfur --
    S8 boils at 717.8 K and the catalytic stage runs at 500 K, so the product
    leaves the gas phase as it forms. That is the sulfur condenser between the
    stages, and it is the vapour-pressure curve rather than the equilibrium.

    ⚠ No solid catalyst is declared, because the catalog row does not carry one.
    The alumina is real and its absence is the barrier being apparent; declaring
    `corundum` would make the row's own reactant list unable to run it.
    """
    h2s = ".".join(f"[S;H2:{i + 1}]" for i in range(16))
    so2 = ".".join(
        f"[O:{100 + 2 * i}]=[S;H0:{17 + i}]=[O:{101 + 2 * i}]" for i in range(8)
    )
    rings = ".".join(
        "".join([f"[S;H0:{1 + 8 * r}]1"]
                + [f"[S;H0:{1 + 8 * r + k}]" for k in range(1, 8)]
                + ["1"])
        for r in range(3)
    )
    waters = ".".join(f"[O;H2:{100 + i}]" for i in range(16))
    return ReactionTemplate(
        name="claus_comproportionation",
        smarts=f"{h2s}.{so2}>>{rings}.{waters}",
        A=A, Ea=Ea, phase="gas",
        orders=(1.0,) + (0.0,) * 15 + (1.0,) + (0.0,) * 7,
    )

# ---------------------------------------------------------------------------
# S11 -- HYDROFORMYLATION, AND THE FIRST TEMPLATE PAIR WHOSE POINT IS WHICH ONE
# WINS
# ---------------------------------------------------------------------------
# ⚠⚠ **THE CATALOG'S TWO ROWS ARE ONE REACTION WITH TWO REGIOCHEMISTRIES**, and
# that is why this class was worth building rather than merely worth +1:
#
#     oxo-process 1  propene + CO + H2 -> butyraldehyde      420 K, 200 bar
#     oxo-process 2  propene + CO + H2 -> isobutyraldehyde   "same reactor,
#                                                             n:iso selectivity"
#
# Same reactants, same reactor, same catalyst, two products. Nothing about that
# can be expressed by ONE template, and the pair is the mechanic: two SMARTS
# competing for the same alkene, whose ratio is a rate ratio and nothing else.
#
# ⚠⚠ **AND THE THERMODYNAMICS GET IT BACKWARDS, WHICH IS THE FINDING.** Priced
# off this project's own tables:
#
#     propene + CO + H2 -> butanal            dH -113.73   dG298 -38.72
#     propene + CO + H2 -> 2-methylpropanal   dH -123.08   dG298 -43.54
#
# The BRANCHED aldehyde is 9.35 kJ/mol more exothermic and 4.82 kJ/mol more
# favourable, so at equilibrium it wins 2.3 to 1 at 420 K. The real reactor makes
# the LINEAR one, about four to one. **The oxo process is under kinetic control
# and running against its own thermodynamics**, which is exactly why the linear
# aldehyde -- the one industry wants, for plasticiser alcohols -- has to be taken
# out of a reactor rather than waited for.
#
# ⚠⚠ **SO EVANS-POLANYI MUST BE OFF HERE, AND THAT IS A DECLARATION AND NOT AN
# OMISSION.** ``alpha`` scales the barrier with dH, so any alpha > 0 gives the
# more exothermic branched route the LOWER barrier and predicts the wrong major
# product with confidence. The regiochemistry of a cobalt hydroformylation is set
# by which alkyl-cobalt intermediate forms, not by how exothermic the product is.
# ``alpha=0.0`` on both, stated.
#
# THE BARRIER, AND THE ONE FITTED NUMBER IN THIS PAIR:
#
#   Ea (linear)   96 kJ/mol -- Natta's apparent barrier for cobalt
#                 hydroformylation, ~23 kcal/mol; published band 85-125.
#   dEa           4.8 kJ/mol, THE ONLY FITTED NUMBER HERE. It is set so that
#                 ``exp(dEa / R T)`` is 4.0 at the catalog row's own 420 K,
#                 i.e. the reported n:iso for unmodified HCo(CO)4. Everything
#                 else about the selectivity -- above all its TEMPERATURE
#                 DEPENDENCE -- is then a prediction and not an input.
#
# ⚠ **A IS 1e10 AND IT IS NOT A COLLISION FREQUENCY.** The rate law is third
# order in the gas (alkene, CO, H2) and first order in the cobalt, so its
# pre-exponential is in L^3/(mol^3 s) and the collision limit is a number in
# L/(mol s) -- comparing them is the category error M8 named and
# ``deacon_oxidation`` already documents. What bounds it instead is the REACTOR:
# at 1e10, a 1 L flask charged to 200 bar at 420 K over 0.1 mol of cobalt is
# **94.3% converted in one hour**, against a real cobalt oxo reactor's residence
# time of tens of minutes to a couple of hours. ``validation/hydroformylation.py``
# is that measurement.
#
# ⚠⚠ **REVERSIBLE, AND THE ALTERNATIVE WAS MEASURED RATHER THAN ARGUED.** Three
# moles of gas become one, so this equilibrium turns over on heating: an
# irreversible pair reports **77.9% conversion at 600 K and 1 bar where the
# reversible pair reports 0.013%**. That is a factor of 6000, on a flask a player
# can build, and it is why ``alkene_hydrogenation``'s "irreversible is a claim
# about temperature" argument does NOT transfer here -- retro-hydroformylation is
# real, industrial, and the reason the process is run at 200 bar at all.
#
# ⚠⚠ **AND THE PAIR THEN DOES SOMETHING NOBODY DECLARED: IT CROSSES FROM KINETIC
# TO THERMODYNAMIC CONTROL ON ITS OWN.** With detailed balance supplying both
# reverses, the HEADSPACE n:iso at 420 K reads 3.30 after an hour, 3.23 after
# four days, 0.99 after a year and settles at **0.4283** -- which is
# ``K(n)/K(iso)`` = 10.08/23.52 to four figures. The kinetic product is eaten by
# the thermodynamic one through the shared reactant, at a rate set by a reverse
# barrier nobody typed (``Ea - dH``, 209.7 and 223.9 kJ/mol). ⚠ Nothing a player
# does reaches that timescale; it is the equilibrium the pair is anchored to,
# made visible.
#
# ⚠⚠ **AND READ THAT AGAINST THE HEADSPACE, NOT THE INVENTORY.** An equilibrium
# constant is a statement about PARTIAL PRESSURES. At 200 bar and 420 K this
# reactor holds ~1.7 mol of LIQUID product, and butanal (Tb 347.95 K) is the less
# volatile of the two, so the flask's total-mole ratio settles at **0.513** while
# its headspace settles at 0.4283. A real cobalt oxo reactor is a liquid-phase
# process for exactly this reason, and the two-phase reactor was not asked for --
# it is what a 200-bar charge of these five species IS.
#
# ⚠ THE COBALT IS A GATE AND A KNOB: ``solid_catalyst="cobalt"``, so a flask with
# no metal in it converts EXACTLY zero. The real catalyst is HCo(CO)4 formed in
# situ from the charged cobalt under syngas, which is not modelled -- the same
# statement ``water_gas_shift`` makes about magnetite reduced in situ from the
# hematite it is charged with. And the site balance is still missing (M10), so
# the metal is a first-order knob for ever.


def hydroformylation_linear(
    A: float = 1.0e10, Ea: float = 96_000.0, catalyst: str | None = "cobalt",
) -> ReactionTemplate:
    """Alkene + CO + H2 -> the LINEAR aldehyde. The oxo process's major product.

    The formyl group goes onto the TERMINAL carbon and the hydrogen onto the
    substituted one, so propene gives butanal. ``[CX3H2:1]`` is what makes
    "terminal" a pattern rather than a comment: the matched carbon must carry two
    hydrogens, which is true of the CH2 end of a 1-alkene and of both ends of
    ethylene -- where the two templates correctly become the same reaction,
    because hydroformylating ethylene has no regiochemistry to get wrong.

    ⚠ Its twin is ``hydroformylation_branched`` and neither is meaningful
    alone. See the block comment above: the class's two catalog rows are this
    reaction twice, and the selectivity between them is the whole process.
    """
    return ReactionTemplate(
        name="hydroformylation_linear",
        smarts="[CX3H2:1]=[CX3:2].[C-:3]#[O+:4].[H:5][H:6]"
               ">>[C:1]([C+0:3](=[O+0:4])[H:6])[C:2][H:5]",
        A=_surface_kinetics(A, catalyst), Ea=Ea, phase="gas", reversible=True,
        alpha=0.0, solid_catalyst=catalyst,
    )


def hydroformylation_branched(
    A: float = 1.0e10, Ea: float = 100_800.0, catalyst: str | None = "cobalt",
) -> ReactionTemplate:
    """Alkene + CO + H2 -> the BRANCHED aldehyde. The oxo process's by-product.

    The same addition the other way round: formyl onto the substituted carbon,
    hydrogen onto the terminal one, so propene gives 2-methylpropanal.

    ⚠⚠ **ITS BARRIER IS 4.8 kJ/mol HIGHER AND THAT IS THE ONLY FITTED NUMBER IN
    THE PAIR.** ``exp(4800 / R T)`` is 4.0 at the catalog row's 420 K, which is
    the reported n:iso for unmodified cobalt. ⚠ The number is a SELECTIVITY
    declared as a barrier difference; it is not derived from anything, and the
    thermodynamics point the other way (this product is the more stable one).
    ⚠⚠ **AND WHAT THE RATIO DOES WHEN THE REACTOR IS MOVED IS NOT FITTED, NOR
    IS IT JUST THE EXPONENTIAL.** Measured in a sealed 200-bar flask over an
    hour: 4.57 at 380 K, 4.23 at 400, 3.95 at 420, 3.52 at 450 -- tracking
    ``exp(dEa/RT)`` to three figures -- and then **1.61 at 480 K and 0.70 at
    520**, against a pure kinetic 3.33 and 3.03. Above ~450 K the two REVERSE
    reactions get inside the reactor's own residence time and the branched
    product, which is the more stable one, starts winning; the conversion turns
    over in the same place. **Nothing declares a maximum operating temperature
    and a real cobalt oxo reactor sits at 410-450 K.**
    ``validation/hydroformylation.py`` panel 3 prints both columns side by side.
    """
    return ReactionTemplate(
        name="hydroformylation_branched",
        smarts="[CX3H2:1]=[CX3:2].[C-:3]#[O+:4].[H:5][H:6]"
               ">>[C:1]([H:5])[C:2][C+0:3](=[O+0:4])[H:6]",
        A=_surface_kinetics(A, catalyst), Ea=Ea, phase="gas", reversible=True,
        alpha=0.0, solid_catalyst=catalyst,
    )


# ---------------------------------------------------------------------------
# S11 -- THE WACKER PROCESS, AND THE FIRST TEMPLATE WHOSE CATALYST IS AN ION
# ---------------------------------------------------------------------------
# `wacker-process` is one row and one class:
#
#     ethylene + oxygen + copper-ii-ion -> acetaldehyde + copper-ii-ion
#                                          PdCl2/CuCl2, 400 K
#
# ⚠⚠ **THE CATALYST WRITTEN ON BOTH SIDES IS `[Cu+2]`, AND THAT MAKES THIS THE
# ONE TEMPLATE HERE THAT CANNOT RUN IN A DRY FLASK.** Every other explicit
# catalyst in this project is either a proton (`_maybe_catalyse`'s original case)
# or a CRYSTAL in the solid block (`solid_catalyst`). A copper(II) ion is
# neither: it is priced from `ion_data` against this project's own water, it has
# no neutral graph any estimator will touch, and `thermochemistry` refuses it by
# name unless the network is built with `electrolyte_provider()`. So the gate
# here is not "did you add the catalyst" but "is there a SOLVENT for it to be an
# ion in" -- which is what a real Wacker reactor is: an aqueous chloride liquor
# with ethylene and air bubbled through it.
#
# ⚠ **THE COPPER IS NOT THE OXIDANT IN THE STOICHIOMETRY AND IS THE OXIDANT IN
# THE MECHANISM.** The real cycle is three steps -- palladium oxidises the
# alkene and is reduced to metal, copper(II) reoxidises the palladium, oxygen
# reoxidises the copper(I) -- and the catalog row folds all three, keeping only
# the copper because that is the species a chemist charges. Palladium is not
# modelled and its absence is why the barrier below is an APPARENT one.
#
# ⚠⚠ **AND THE RATE LAW IS A DECLARATION THAT IS DELIBERATELY WRONG IN ONE
# PLACE, WHICH IS WORTH MORE THAN GETTING IT SILENTLY RIGHT.** The real Wacker
# rate law is first order in ethylene, first order in palladium, and **ZERO order
# in oxygen** -- the O2 only reoxidises the copper and never appears in the
# rate-determining hydroxypalladation. This template declares FIRST order in
# oxygen, and the reason is mechanical rather than chemical: the kinetics kernel
# has no availability gate (`_avail` exists only for the solid block), so a
# reactant at order zero keeps reacting after it runs out and is driven negative.
# `hydrogen_sulfide_combustion` keeps one O2 slot at order 1 for the same reason.
# ⚠ **The cost is stated and measured**: doubling the oxygen here doubles the
# rate, where a real Wacker reactor would not notice. That is right at low
# oxygen -- where the copper(I) really is waiting for air -- and wrong at high,
# which is the same shape as the missing site balance (M10).
#
# What IS declared correctly is the alkene order: the SMARTS has to consume TWO
# ethylenes to balance one O2, and mass action would then make the reaction
# SECOND order in the alkene. `orders=(1.0, 0.0, 1.0, 1.0)` puts it back to
# first, which is the measured law. ⚠ A declared order may never be reversible,
# and here that costs nothing: ln K is +113 at 400 K.
#
# Ea 65 kJ/mol -- apparent barrier for the aqueous PdCl2/CuCl2 oxidation of
# ethylene, published band 55-80.
#
# ⚠ A IS 1e9 AND IT IS NOT A COLLISION FREQUENCY, for the third-order reason
# `deacon_oxidation` and `hydroformylation_linear` both document. What bounds it
# is the REACTOR: at 1e9, a litre of water holding 0.02 mol of Cu(II) at 400 K
# is **40% converted in one minute and 98% in ten**, against a real one-stage
# Wacker reactor's 30-40% per pass on a residence time of minutes.
# `validation/wacker.py` is that measurement.


def wacker_oxidation(
    A: float = 1.0e9, Ea: float = 65_000.0, catalyst: str | None = "[Cu+2]",
) -> ReactionTemplate:
    """2 C2H4 + O2 -> 2 CH3CHO over aqueous copper(II). Acetaldehyde from ethylene.

    ⚠ **NEEDS `electrolyte_provider()` AND `dissociation_templates()` BESIDE
    IT**, because `[Cu+2]` is not a species any of the three neutral providers
    will price. Build the network with them or the flask refuses loudly, which is
    the correct behaviour and not a limitation.

    ⚠ Liquid phase, and that is the process: ethylene and oxygen have to
    DISSOLVE before they can meet the copper. Oxygen is a Henry's-law solute
    here, so its concentration in the liquor is a computed thing rather than a
    charged one, and the flask reproduces a bubble column's dependence on how
    much gas is above it without being told.

    ⚠ Irreversible. ln K is +113 at 400 K, and a declared rate order may never be
    reversible in any case -- see the block comment for both halves of that.
    """
    return ReactionTemplate(
        name="wacker_oxidation",
        smarts=_maybe_catalyse(
            "[CH2:1]=[CH2:2].[CH2:3]=[CH2:4].[OX1:5]=[OX1:6]"
            ">>[CH3:1][CH1:2]=[O:5].[CH3:3][CH1:4]=[O:6]",
            catalyst,
        ),
        A=_kinetics(A, catalyst), Ea=Ea, phase="liquid",
        orders=(1.0, 0.0, 1.0, 1.0) if catalyst else (1.0, 0.0, 1.0),
    )


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# S12 -- THE SKRAUP, AND THE FIRST TEMPLATE WHOSE OXIDANT IS ALSO ITS PRODUCT
# ---------------------------------------------------------------------------
# ⚠⚠ **THE CATALOG ROW HAS ANILINE ON BOTH SIDES AND IT IS NOT THE `spurious`
# PATTERN.** `corpus_balance`'s `spurious` bucket is for a reagent written as
# consumed that is really a catalyst; here the aniline on the right is a
# DIFFERENT molecule from the aniline on the left -- it is what the nitrobenzene
# oxidant BECOMES when it is reduced. The row is real, and reading the class name
# instead of the row would have thrown it away:
#
#     skraup-route 2 | aniline + acrolein + nitrobenzene + sulfuric-acid
#                    -> quinoline + aniline + water + sulfuric-acid
#
# ⚠⚠ **AND THE STOICHIOMETRY IS WHAT MAKES IT A SEVEN-SLOT TEMPLATE.** Each
# quinoline is an aniline plus an acrolein minus one water, and the ring it
# closes is a DIHYDRO-quinoline that has to lose two hydrogens to aromatise.
# Nitrobenzene takes six of them:
#
#     3 x  aniline + acrolein  ->  quinoline + H2O + 2 [H]
#          PhNO2 + 6 [H]       ->  PhNH2 + 2 H2O
#     ----------------------------------------------------
#     3 aniline + 3 acrolein + nitrobenzene -> 3 quinoline + aniline + 5 water
#
# C33H38N4O5 on both sides, four aromatic rings in and four out. The threefold
# multiple is not decorative: a graph rewrite cannot write 1/3 of a nitrobenzene,
# exactly as `claus_comproportionation` cannot write 3/8 of a sulfur crown.
#
# ⚠⚠ **PRICED OFF THIS PROJECT'S OWN TABLES -- AND IT HAD TO BE PRICED TWICE,
# BECAUSE A PHASE LABEL CARRIES A STANDARD STATE:**
#
#                     dH / kJ    dG298 / kJ    dS / J/(mol K)
#     ideal gas       -561.63       -572.55           +36.65
#     pure liquid     -715.04       -623.12          -308.31   (S13; was
#                                                               -725.16 /
#                                                               -627.05 /
#                                                               -329.08)
#
# ⚠⚠ **THE TWO BASES DO NOT AGREE ON THE SIGN OF dS, AND THE EASY ONE IS THE
# WRONG ONE.** Seven molecules become nine, so counting molecules gives a
# POSITIVE dS and an argument that heating the flask makes the forward direction
# more favourable. That argument is about a gas-phase reaction and this is not
# one: `phase="liquid"` makes `reaction_deltas` put every condensable species on
# its own pure liquid, and NINE product molecules condense against SEVEN reactant
# ones. It is worth 153.41 kJ/mol in dH and it flips dS. **The gas-basis numbers
# were written into this comment first, off a hand calculation, and the audit
# caught them.**
#
# ⚠ S13 MOVED THE LIQUID ROW AND LEFT THE GAS ROW ALONE, WHICH IS THE CLEANEST
# demonstration of what the two bases are made of. The corpus sweep gave
# acrolein and quinoline measured boiling points; the liquid standard state is a
# stack of enthalpies of vaporisation built out of exactly those, so it moved by
# 10 kJ/mol. Formation data did not change, so the gas row did not move by a
# digit. `test_the_two_standard_states_disagree_on_the_sign_of_dS` pins both.
#
# ⚠ **IRREVERSIBLE IS SAFE ANYWAY, FOR THE OTHER REASON.** ln K on the basis the
# engine actually uses is **251.4 at 298 K, 154.0 at 450 and 106.3 at 600**, and
# dG reaches zero only at **2319 K**. S11's rule -- count the moles of GAS on
# each side before giving up a reverse, because hydroformylation's three-gas-to-
# one equilibrium turns over at a reachable temperature and irreversible lied by
# a factor of 6000 -- is answered here by there being no gas in the rate law at
# all. (A declared rate order may never be reversible in any case -- see
# `claus_comproportionation` -- but that rule is not what makes this one honest.)
#
# ⚠ **EVERY SLOT THE TEMPLATE CONSUMES KEEPS ORDER 1**, which is S11's other
# rule and the reason nitrobenzene carries an exponent at all: the kinetics
# kernel has no availability gate, so an order-0 reactant keeps reacting after it
# has run out and is driven negative. Here that costs nothing to be honest about
# -- a real Skraup DOES slow as its oxidant is spent -- unlike the Wacker, where
# the same rule forces a first order in oxygen that the real rate law says is
# zero.
#
# ⚠ Ea 80 kJ/mol: the apparent barrier of the acid-catalysed Michael addition /
# cyclisation sequence, literature band ~60-90 kJ/mol for conjugate additions of
# an aromatic amine. It is an APPARENT barrier over a four-step sequence and is
# declared as such. A is fitted to the one thing the preparation actually
# reports: a Skraup at violent reflux is over in an hour or two, not a day and
# not a second.


def skraup_cyclisation(
    A: float = 3.0e6, Ea: float = 80_000.0,
    catalyst: str | None = ACID_CATALYST,
) -> ReactionTemplate:
    """3 aniline + 3 acrolein + nitrobenzene -> 3 quinoline + aniline + 5 water.

    The Skraup synthesis: the oldest quinoline ring closure there is, and the one
    whose reputation is that it goes off like a bomb if you do not moderate it.

    ⚠ **SEVEN REACTANT SLOTS AND NINE PRODUCT SLOTS**, plus the sulfuric acid on
    both sides, which `_maybe_catalyse` writes in as an eighth. See the block
    comment above for where the threefold multiple comes from -- it is the
    oxidant's own stoichiometry, not a fudge.

    ⚠ **THE TEMPLATE IS GENERAL IN THE ANILINE AND IN THE ENAL, AND SPECIFIC IN
    THE OXIDANT.** The aniline slot matches any primary aromatic amine with a
    free ortho position, and the enal slot any CH2=CH-CHO; the oxidant slot is
    written as a nitroarene because that is the only reductant-of-six-hydrogens
    this corpus has, and because a general "any oxidant" slot would have no
    stoichiometry at all. So a substituted aniline gives the substituted
    quinoline and the corresponding substituted aniline comes back out -- which
    is right, and is also why the three aniline slots do NOT have to be the same
    molecule.

    ⚠ **DECLARED ORDERS, THEREFORE NOT REVERSIBLE.** Mass action on seven slots
    would put [aniline]^3 [acrolein]^3 [PhNO2] in the rate law, which at bench
    concentrations is zero to a dozen digits -- `claus_comproportionation`'s
    argument with a smaller number in it. Declared first order in the amine, the
    enal, the oxidant and the acid. Giving up the reverse costs nothing: on the
    pure-liquid basis this template actually runs on, ln K is +252.9 at 298 K and
    still +105.8 at 600 K. ⚠ Read the block comment for why the obvious
    seven-molecules-to-nine entropy argument is about the WRONG standard state.

    ⚠ **THE ACID IS EXPLICIT, AND IT IS SPELLED AS THE HYDRONIUM IT MAKES.**
    The catalog row writes `sulfuric-acid` on both sides; this project writes an
    acid catalyst as ``ACID_CATALYST`` -- the same choice `esterification`,
    `ether_condensation` and `alkene_dehydration` already make, and the honest
    one, because it is the proton that catalyses this rather than the sulfate.
    A flask with no acid in it does nothing at all, which is the correct answer
    for a Skraup.
    """
    b = [1 + 12 * i for i in range(3)]
    amines = [
        f"[N;H2;+0:{k}][c:{k+1}]1[c;H1:{k+2}][c:{k+3}][c:{k+4}][c:{k+5}]"
        f"[c:{k+6}]1"
        for k in b
    ]
    enals = [f"[C;H2:{k+7}]=[C;H1:{k+8}][C;H1:{k+9}]=[O;+0:{k+10}]" for k in b]
    quinolines = [
        f"[n;+0:{k}]1[c;H1:{k+7}][c;H1:{k+8}][c;H1:{k+9}][c;H0:{k+2}]2"
        f"[c:{k+3}][c:{k+4}][c:{k+5}][c:{k+6}][c;H0:{k+1}]12"
        for k in b
    ]
    waters = [f"[O;H2;+0:{k+10}]" for k in b]
    nitro_in = ("[O;+0:41]=[N;+1:40]([O;-1:42])[c:43]1[c:44][c:45][c:46]"
                "[c:47][c:48]1")
    nitro_out = ("[N;H2;+0:40][c:43]1[c:44][c:45][c:46][c:47][c:48]1"
                 ".[O;H2;+0:41].[O;H2;+0:42]")
    lhs = ".".join(x for pair in zip(amines, enals) for x in pair)
    rhs = ".".join(x for pair in zip(quinolines, waters) for x in pair)
    return ReactionTemplate(
        name="skraup_cyclisation",
        smarts=_maybe_catalyse(f"{lhs}.{nitro_in}>>{rhs}.{nitro_out}", catalyst),
        A=_kinetics(A, catalyst), Ea=Ea, phase="liquid",
        orders=((1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0) if catalyst
                else (1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0)),
    )

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# C3 -- VANILLIN, AND THE CLASS S11 REFUSED AFTER READING ONE OF ITS TWO ROWS
# ---------------------------------------------------------------------------
# `oxidative-cleavage` has TWO rows in the catalog and S11 read the harder one:
#
#   vanillin-lignin  1 | coniferyl alcohol + O2 + NaOH -> vanillin + water + NaOH
#   vanillin-eugenol 2 | isoeugenol + O2               -> vanillin + acetaldehyde
#
# S11 went to build the class off the LIGNIN row, found that a C10 monolignol
# cannot make one C8 vanillin and a water, and refused the class -- on the
# grounds that "naming the missing C2 product would be inventing chemistry
# inside the corpus". That refusal is recorded in MILESTONES S11 section 12 and
# printed by `validation/corpus_balance.py`'s last panel.
#
# ⚠⚠⚠ **THE REFUSAL WAS ABOUT THE ROW AND WAS WRITTEN ABOUT THE CLASS, AND THE
# OTHER ROW IS BALANCED 1:1 WITH THE C2 FRAGMENT NAMED.** Measured:
#
#   isoeugenol + O2 -> vanillin + acetaldehyde     C10H12O4 both sides, EXACT
#   coniferyl  + O2 -> vanillin + glycolaldehyde   C10H12O5 both sides, EXACT
#   coniferyl  + O2 -> vanillin + water            C10H12O5 -> C8H10O4   NO
#
# So the template below is written off the row that balances, and the C2
# fragment the lignin row omits is `glycolaldehyde` -- **a compound the corpus
# has already carried all along** (`07-carbonyls.psv`, "simplest sugar"). Not
# one atom of chemistry is invented: the mechanism supplies the fragment and the
# corpus supplies the name.
#
# ⚠⚠ THE LESSON IS C1's AND C2's, APPLIED TO A REFUSAL RATHER THAN A BLOCKER.
# C1: a route blocked on a price for a species that was not in its chemistry.
# C2: a route blocked on a price in a different table from the one named. C3: a
# CLASS refused on the evidence of one of its rows. **Read every row of a class
# before refusing the class** -- and S11's own reason survives intact where it
# was aimed: the lignin row IS still wrong, and it is wrong in a way this
# template now says out loud rather than leaving unnamed.
#
# ⚠ AND THE ARITHMETIC WAS DONE BEFORE EITHER TEMPLATE WAS WRITTEN -- ON THE
# WRONG BASIS, WHICH IS WHY IT IS PRINTED HERE ON BOTH. Both templates are
# phase="liquid", so `reaction_deltas` moves every condensable species onto its
# own pure liquid and the flask uses the second pair of columns:
#
#                                          IDEAL GAS        PURE LIQUID
#                                        dH   ln K 470     dH   ln K 470
#   eugenol -> isoeugenol             -21.80     +8.04  -56.56      +7.89
#   isoeugenol + O2 -> vanil + MeCHO -325.58    +85.71 -320.92     +94.37
#   coniferyl  + O2 -> vanil + HOCH2CHO
#                                    -318.56    +83.62     -- see below
#
# ⚠⚠ THE TWO ln K VALUES FOR THE ISOMERISATION AGREE TO 2% AND THE dH
# VALUES DISAGREE BY 35 kJ/mol, WITH THE SIGN OF dS FLIPPING (+20.45 against
# -54.72 J/K). **That agreement is a coincidence and not a licence** -- it is two
# errors cancelling at one temperature. S12's rule: a phase label carries a
# standard state, and C3 had to correct this comment against
# `validation/vanillin.py` panel 3 rather than the other way round.
#
# ⚠ AND THE LIGNIN READING HAS NO USABLE ln K AT ALL. Coniferyl alcohol has
# no vapour-pressure curve, so `build_network` prints M5's MIXES STANDARD STATES
# notice on it: its formation data stays on the ideal-gas basis while vanillin's
# and glycolaldehyde's take the liquid shift. The reaction is irreversible so no
# rate depends on it. **Which is a SECOND, independent reason the eugenol row was
# the right one to build from -- all four of its species carry a curve and it
# triggers no notice. S11 picked the row that is worse in both ways.**
#
# ⚠⚠ **AND PRICING THE UNBALANCED ROW IS SILENT, WHICH IS THE WHOLE REASON THE
# BALANCE HAS TO BE CHECKED BY HAND.** `coniferyl + O2 -> vanillin + water`
# prices at dH -251.99 and dS **+148.23 J/K** against its balanced neighbour's
# +16.97 -- an entropy eight times the real one, because two carbons have been
# destroyed -- and nothing anywhere raises. A row that is not a reaction still
# comes back with a number.


# Ea 115 kJ/mol -- apparent barrier for the base-catalysed allyl -> propenyl
# migration on an arene, literature band ~90-120. A is 1e9 for the reason
# `wacker_oxidation` documents: it is not a collision frequency, and what bounds
# it is the REACTOR.
#
# ⚠⚠ AND 115 IS A CALIBRATION AGAINST THE PROCESS, MEASURED IN A FLASK
# RATHER THAN ARGUED FOR. In `validation/vanillin.py`'s reference autoclave --
# 0.73 L of liquor, [OH-] = 0.137 mol/L, 470 K -- this template alone converts
# **51.96% in 1 h and 94.65% in 4 h**, against a real KOH isomerisation's 95%+
# in 3-6 h at 470-490 K. ⚠ The first attempt declared 110 kJ/mol on hand
# arithmetic that assumed a ONE-LITRE liquid and was 8x fast, because the
# flask's liquor is 0.73 L and the base is correspondingly more concentrated.
# **An apparent barrier calibrated against a rate has to be calibrated against
# the rate the FLASK computes, not the one the envelope does.**


def alkene_isomerisation(
    A: float = 1.0e9, Ea: float = 115_000.0, catalyst: str | None = "[OH-]",
) -> ReactionTemplate:
    """Aryl allyl -> aryl propenyl. Eugenol to isoeugenol, over hydroxide.

    ⚠⚠ **THE PRODUCT'S DOUBLE-BOND GEOMETRY IS NOT DECLARED, AND THAT IS A
    DECISION RATHER THAN AN OMISSION.** The corpus spells isoeugenol
    ``C/C=C/c1ccc(O)c(OC)c1`` -- trans -- and this template makes
    ``CC=Cc1ccc(O)c(OC)c1``, which ``Molecule.from_smiles`` canonicalises to a
    DIFFERENT STRING and therefore a different species. Two measurements decide
    it:

      * **nothing here can price the difference.** cis, trans and geometry-free
        isoeugenol all come back at Hf -216.705 and Gf -49.315, identical to
        three decimals, which is S7's ``oleic -> elaidic`` finding (*"no
        estimator here tells a cis alkene from a trans one"*) re-measured on
        this pair. Declaring a geometry would assert a distinction the
        thermochemistry cannot carry.
      * **and the geometry-free species reacts onward identically**, because
        ``oxidative_cleavage``'s pattern does not query bond stereo. The chain
        still reaches vanillin.

    ⚠ **AND IT MAKES NO SPURIOUS CYCLE, BECAUSE DISCOVERY IS FORWARD-ONLY.**
    With the corpus's trans isoeugenol charged instead, the reverse of this
    template is in the network but nothing enumerates species through it (M5's
    rule), so trans isoeugenol is inert to this template rather than draining
    into eugenol and back out as the geometry-free isomer. **A rule that has
    cost this project a template twice does useful work here.**

    ⚠ Reversible, and it is worth being: ln K is +11.3 at 298 K and +8.0 at
    470 K, so the equilibrium sits ~3000:1 towards the conjugated isomer and the
    flask keeps a real trace of eugenol rather than running to completion. That
    is the right shape -- a real isomerisation stops at 95-98%.

    ⚠ **NEEDS ``electrolyte_provider()``**, for ``wacker_oxidation``'s
    reason: ``[OH-]`` is not a species any of the three neutral providers will
    price, so the gate is "is there a solvent for the base to be a base in".
    Pass ``catalyst=None`` for the uncatalysed form at the same apparent rate.

    ⚠⚠ **AND IT MUST *NOT* BE GIVEN ``dissociation_templates()``, WHICH
    IS THE OPPOSITE OF WHAT ``wacker_chemistry`` NEEDS AND WAS MEASURED RATHER
    THAN ASSUMED.** Eugenol IS a phenol, so ``phenol_dissociation`` fires on it
    and ``build_network`` refuses the whole network for want of a pKa for the
    eugenolate. That is G5's rule reaching a new substrate -- **an open-ended
    rewrite over a curated table will find the edge of the table** -- met on an
    amine there and on a phenol here. The refusal is KEPT: this route needs no
    phenolate, and G5 measured what curating pKa values to satisfy an unused
    template buys. ⚠ This docstring first claimed the dissociation set was
    REQUIRED, copied from ``wacker_chemistry``, and running it is what caught
    that.

    ⚠ The SMARTS is narrow at the far end -- ``[CH2:4]`` is a terminal methylene
    -- so it matches an allyl arene and NOT an already-conjugated one. That is
    what stops it feeding itself: its own product has no CH2 next to the ring.
    """
    return ReactionTemplate(
        name="alkene_isomerisation",
        smarts=_maybe_catalyse(
            "[c:1][CH2:2][CH1:3]=[CH2:4]>>[c:1][CH1:2]=[CH1:3][CH3:4]",
            catalyst,
        ),
        A=_kinetics(A, catalyst), Ea=Ea, phase="liquid", reversible=True,
    )


# Ea 75 kJ/mol -- apparent barrier for the alkaline aerobic side-chain cleavage
# of a propenyl arene, literature band ~60-90 for alkaline nitrobenzene and air
# oxidations of lignin and its model compounds. A is 1e9, uncatalysed.
#
# ⚠ NO DECLARED ORDERS, AND THAT IS WHY THIS ONE IS SIMPLE. The SMARTS consumes
# ONE alkene and ONE O2, so plain mass action already IS the rate law -- unlike
# `wacker_oxidation`, which has to consume two ethylenes to balance one oxygen
# and then declare the alkene order back down to 1. Nothing here is order zero,
# so the trap `wacker_oxidation` and `hydrogen_sulfide_combustion` both document
# -- a reactant at order zero keeps reacting after it runs out and is driven
# negative -- cannot fire.
#
# ⚠ Irreversible: ln K is +94.4 at 470 K on the basis the flask uses, so the
# reverse is ~1e-41 of the forward and carrying it would buy stiffness and
# nothing else.
#
# ⚠ Ea 85 kJ/mol is likewise a calibration: this template alone takes
# isoeugenol to 47% vanillin in 10 min and 97% in 1 h at 470 K, so it stays
# comfortably FASTER than the isomerisation and the intermediate never
# accumulates -- which is the real preparation's shape.
# `validation/vanillin.py` panel 5 is the knockout that says which step is
# rate-determining.


def oxidative_cleavage(
    A: float = 1.0e9, Ea: float = 85_000.0, catalyst: str | None = None,
) -> ReactionTemplate:
    """Ar-CH=CH-R + O2 -> Ar-CHO + R-CHO. Vanillin from isoeugenol or lignin.

    ⚠⚠ **THIS IS THE CLASS S11 REFUSED, BUILT OFF THE OTHER ROW.** See the block
    comment above for the whole argument; the short form is that
    `vanillin-eugenol` step 2 balances exactly 1:1 and names its C2 fragment,
    while `vanillin-lignin` step 1 does not and cannot. **This template makes
    the lignin row's missing fragment explicit: glycolaldehyde, which the corpus
    has carried since it was written.**

    ⚠ **SO IT DISAGREES WITH A CATALOG ROW, AND THE ROW IS THE ONE THAT IS
    WRONG.** S3's rule -- *"the mechanism doesn't make the row's product" is not
    a verdict; ask which one is WRONG* -- and here the answer is arithmetic
    rather than judgement: `coniferyl + O2 -> vanillin + water` is short a
    whole **C2H2O** on the right (C10H12O5 against C8H10O4), and what the
    mechanism puts there instead is glycolaldehyde, C2H4O2 -- which balances
    it exactly.

    ⚠ Liquid phase, so the oxygen has to DISSOLVE before it can reach the
    alkene: its concentration in the liquor is a Henry's-law computed thing and
    not a charged one, and a flask with a bigger headspace cleaves faster
    without being told. That is what an alkaline oxidation tower is.

    ⚠ THE SMARTS IS NARROW AT BOTH ENDS AND EACH END EARNS IT. ``[c:1]``
    requires the alkene to be conjugated to a ring, which is what makes the
    cleavage go under these conditions at all; ``[#6:4]`` requires a carbon
    substituent on the far end, so **plain styrene does not match** -- correct
    here, because this template is about the propenyl side chain a monolignol
    carries, and a terminal vinyl arene is a different oxidation. Measured
    against eleven substrates: it fires on isoeugenol, coniferyl alcohol,
    stilbene (to two benzaldehydes) and cinnamaldehyde (to glyoxal and
    benzaldehyde), and refuses eugenol, styrene, vanillin, safrole, toluene,
    propene and 1-butene. ⚠ It cannot feed itself: neither product has a C=C
    left.
    """
    return ReactionTemplate(
        name="oxidative_cleavage",
        smarts=_maybe_catalyse(
            "[c:1][CH1:2]=[CH1:3][#6:4].[OX1:5]=[OX1:6]"
            ">>[c:1][CH1:2]=[O:5].[#6:4][CH1:3]=[O:6]",
            catalyst,
        ),
        A=_kinetics(A, catalyst), Ea=Ea, phase="liquid",
    )


# bundles
# ---------------------------------------------------------------------------
# Small on purpose. ``alcohol_chemistry`` is one bundle because its five templates
# genuinely compete for the same substrate; these do not, and a bundle that pulled
# all nineteen into one network would mostly be measuring how long RDKit takes to
# fail to match. ⚠ Note that ``alkene_hydration`` and ``library.alkene_dehydration``
# are never in the same bundle -- see the block comment above.


def sugar_chemistry(catalyst: str | None = None) -> list[ReactionTemplate]:
    """The glycosidic bond. Sucrose inversion, salicin, starch saccharification."""
    return [glycoside_hydrolysis(catalyst=catalyst)]


def ester_chemistry(catalyst: str | None = None) -> list[ReactionTemplate]:
    """The three ester mechanisms a reversible Fischer esterification cannot reach.

    ⚠ Add ``library.esterification`` to this if the alkyl-ester equilibrium
    matters; it is deliberately not here, so that a saponification network does not
    also carry an acid-catalysed channel it was never meant to have.
    """
    return [
        saponification(),
        ester_hydrolysis(catalyst=catalyst),
        transesterification(),
    ]


def aromatic_chemistry(catalyst: str | None = None) -> list[ReactionTemplate]:
    """Nitration, hydroxyalkylation, Kolbe-Schmitt, Williamson.

    ⚠ **CAP THE EXPANSION.** Nitration feeds itself and hydroxyalkylation nearly
    does; a fixpoint build on a substituted arene is not what you want. Pass
    ``generations=`` or a modest ``max_species=`` to ``build_network``.
    """
    return [
        aromatic_nitration(catalyst=catalyst),
        friedel_crafts_hydroxyalkylation(catalyst=catalyst),
        kolbe_schmitt(),
        williamson_ether_synthesis(),
    ]


def condensation_chemistry(catalyst: str | None = None) -> list[ReactionTemplate]:
    """The four carbonyl condensations, including the two that race for cinnamic acid."""
    return [
        n_acylation(),
        cannizzaro(),
        perkin_condensation(),
        knoevenagel_doebner(catalyst=catalyst),
    ]


def addition_chemistry(catalyst: str | None = None) -> list[ReactionTemplate]:
    """Hydration of an alkene and an alkyne, and hydrogenation of an alkene."""
    return [
        alkene_hydration(catalyst=catalyst),
        alkyne_hydration(catalyst=catalyst),
        alkene_hydrogenation(),
    ]


def hydrogenation_chemistry() -> list[ReactionTemplate]:
    """The two hydrogenations the catalog's re-labelled rows need.

    ⚠ Kept apart from ``addition_chemistry`` because a nitroarene and an alkene in
    one flask compete for the same hydrogen, and that competition is real -- but it
    is decided by the two APPARENT barriers, which stand in for two different
    catalysts. Run them together knowing that.
    """
    return [alkene_hydrogenation(), nitro_hydrogenation()]


def synthesis_gas_chemistry() -> list[ReactionTemplate]:
    """Ammonia and methanol from synthesis gas. Three reversible gas-phase equilibria.

    ⚠ Run at pressure; see the block comment above.

    ⚠ This docstring used to end "and note there is no catalyst species -- the
    flask will make ammonia with no iron in it", which S1 made false and nothing
    caught until S7 read it. All three declare a ``solid_catalyst`` and a flask
    with no metal in it makes nothing.
    """
    return [
        ammonia_synthesis(),
        methanol_from_carbon_monoxide(),
        methanol_from_carbon_dioxide(),
    ]


def syngas_generation_chemistry() -> list[ReactionTemplate]:
    """Where the synthesis gas comes FROM: reforming, then the shift.

    Two reversible equilibria pulling opposite ways on temperature -- the
    reformer wants 1100 K and the shift wants to be cold -- which is why a real
    plant is two vessels and not one. Run them in one flask and the hot one wins
    both ways.

    ⚠ Both declare a solid catalyst: nickel for the reformer, hematite for the
    shift. A flask with neither in it is inert.
    """
    return [steam_reforming(), water_gas_shift()]


def oxo_chemistry() -> list[ReactionTemplate]:
    """The oxo process: a 1-alkene, syngas and cobalt, giving BOTH aldehydes.

    ⚠ **A BUNDLE OF EXACTLY TWO, AND THEY ARE THE SAME REACTION.** The pair is
    the point -- the linear and branched additions compete for one alkene and
    the ratio between them IS the process. Charging only one of them would make
    a reactor with a selectivity of infinity.

    ⚠ Wants PRESSURE: three moles of gas become one, so at 1 bar the equilibrium
    turns over just above the reactor's own temperature. And it wants cobalt in
    the solid block; without it the flask is a flask of propene.
    """
    return [hydroformylation_linear(), hydroformylation_branched()]


def wacker_chemistry() -> list[ReactionTemplate]:
    """The Wacker process. ⚠ ONE template, and it needs THREE things beside it.

    ``electrolyte_provider()`` so that ``[Cu+2]`` can be priced at all,
    ``dissociation_templates()`` so the water it lives in is modelled, and a
    charge-balancing counter-ion in the flask. A dry flask of ethylene and air
    does nothing here, which is the correct answer.
    """
    return [wacker_oxidation()]


def claus_chemistry() -> list[ReactionTemplate]:
    """Sulfur recovery: burn a third of the H2S, comproportionate the rest.

    ⚠ **THE FEED RATIO IS THE PROCESS AND IT IS NOT DECLARED ANYWHERE.** Charge
    hydrogen sulfide and enough oxygen to burn one third of it, and the two
    templates make the 2:1 H2S:SO2 the second one wants. Charge too much air and
    the SO2 runs away with it; too little and the burner starves. Nothing in
    either template knows that -- it is two rate laws sharing a flask.
    """
    return [hydrogen_sulfide_combustion(), claus_comproportionation()]


def chlorine_recovery_chemistry() -> list[ReactionTemplate]:
    """The Deacon process alone. Chlorine back out of by-product hydrochloric acid.

    ⚠ Wants pressure and 700 K, and the two fight each other -- see the
    template. Needs `tenorite` in the flask.
    """
    return [deacon_oxidation()]


def bleach_chemistry() -> list[ReactionTemplate]:
    """Halogen disproportionation. ⚠ Needs ``dissociation_templates()`` beside it."""
    return [halogen_disproportionation()]


def vanillin_chemistry(base: str | None = "[OH-]") -> list[ReactionTemplate]:
    """Vanillin: isomerise the clove-oil allyl, then cleave the side chain.

    ⚠⚠ **A BUNDLE OF EXACTLY TWO, AND THE PAIR IS THE ROUTE.**
    `vanillin-eugenol` is two steps and this is both of them, in order. Charge
    eugenol, hydroxide and air; the isomerisation is what makes a substrate the
    cleavage can match, because `oxidative_cleavage` deliberately does not fire
    on an allyl arene. **Either template alone leaves the flask inert.**

    ⚠ And `vanillin-lignin` needs only the second one -- coniferyl alcohol is
    already conjugated. Pass this bundle at a lignin liquor and the
    isomerisation simply finds nothing, which is the correct answer and not a
    wasted template.

    ⚠⚠ **NEEDS ``electrolyte_provider()`` AND MUST NOT BE GIVEN
    ``dissociation_templates()``.** The first because ``[OH-]`` has no neutral
    graph any estimator will price; the second because eugenol is a PHENOL and
    ``phenol_dissociation`` then refuses the whole network for want of an
    eugenolate pKa. See ``alkene_isomerisation``'s docstring -- this line
    claimed the opposite until it was run. Pass ``base=None`` for a network with
    no ionic chemistry in it at all; the apparent rate is unchanged at the
    reference loading.

    ⚠ THE FLASK IS AN AUTOCLAVE, AND THAT IS NOT OPTIONAL. An alkaline
    liquor at 470 K sits under ~30 bar of its own steam, which is what an
    alkaline oxidation digester is; at 400 K the route gives **0.43% in four
    hours**.
    """
    return [alkene_isomerisation(catalyst=base), oxidative_cleavage()]


def quinoline_chemistry() -> list[ReactionTemplate]:
    """The Skraup ring closure alone. ⚠ ONE template, and it needs FOUR things.

    Aniline, acrolein, nitrobenzene and sulfuric acid, all four in one liquid.
    Leave the acid out and the flask does nothing; leave the nitrobenzene out and
    it does nothing either, because the dihydroquinoline has nowhere to put its
    two hydrogens and this template does not write one.

    ⚠ **THE ACROLEIN IS NOT SUPPOSED TO BE CHARGED.** `skraup-route` step 1 makes
    it in situ out of glycerol, which is the whole reason the preparation uses
    glycerol at all -- neat acrolein is a lachrymator that polymerises in the
    bottle, and generating it slowly is what keeps the Skraup from running away.
    That step is `library.alcohol_dehydration`'s class and is not in this bundle,
    because a bundle that carried both would also carry every other dehydration
    the flask can reach.
    """
    return [skraup_cyclisation()]
