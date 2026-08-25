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

from chemsim.reactions.library import (
    _kinetics, _maybe_catalyse, _surface_kinetics,
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


def aromatic_nitration(
    A: float = 1.0e10, Ea: float = 60_000.0, alpha: float = 0.0,
    catalyst: str | None = None,
) -> ReactionTemplate:
    """Ar-H + HNO3 -> Ar-NO2 + water. Electrophilic aromatic nitration.

    Written on the arene and the acid rather than on nitronium, so the nitronium
    pre-equilibrium is folded into the barrier -- which is what the literature
    band is measured on anyway. ``catalyst`` makes the sulfuric acid's role
    explicit in the rate law; the mixed-acid ratio is then a lever.

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

    ⚠ Run at pressure; see the block comment above. And note there is no catalyst
    species -- the flask will make ammonia with no iron in it.
    """
    return [
        ammonia_synthesis(),
        methanol_from_carbon_monoxide(),
        methanol_from_carbon_dioxide(),
    ]


def bleach_chemistry() -> list[ReactionTemplate]:
    """Halogen disproportionation. ⚠ Needs ``dissociation_templates()`` beside it."""
    return [halogen_disproportionation()]
