"""Layer 2 -- what the substituents already on an aromatic ring do to a barrier.

**THE GAP THIS CLOSES, MEASURED.** `aromatic_nitration` gives ONE `A` and ONE
`Ea` to every nitration on every substrate, so 2,4-dinitrotoluene nitrates
exactly as fast as toluene. The consequence is not subtle: 1.0 mol of toluene
and 3.5 mol of nitric acid reach **96% 2,4,6-TNT in ten seconds at room
temperature**, and the endpoint does not move with temperature at all -- 300,
340 and 380 K all land on 1.0000 mol of trinitro. There is no stage to catch and
nothing for an addition rate to control, which is why real TNT manufacture is a
three-stage process with escalating acid strength and temperature and this
engine's was one step.

## Why this is not `alpha`, which is the whole design decision

The cheap fix is to raise the Evans-Polanyi transfer coefficient, and it is the
wrong one. `alpha` scales the barrier with the REACTION ENTHALPY, so it hands the
more exothermic route the lower barrier -- and S11 measured that doing so names
the WRONG major product when kinetics fight thermodynamics, which is why `alpha`
is 0.0 on both hydroformylation templates. A substituent effect on an aromatic
ring is an ELECTRONIC property of the SUBSTRATE. It is not a function of dH, and
dressing it up as one would be that trap again, harder to find the second time
because the number would look plausible.

⚠ **AND ON THIS NETWORK THE TWO POINT IN OPPOSITE DIRECTIONS**, which is what
makes the objection a measurement rather than an argument: benzene ->
nitrobenzene is **-141.2 kJ/mol** and nitrobenzene -> 1,2-dinitrobenzene is
**-268.1 kJ/mol**. The DEACTIVATED ring's step is the more exothermic one, so any
positive `alpha` makes the second nitration FASTER than the first -- exactly
backwards. `ReactionTemplate` refuses the two together for this reason.

## What this is instead

The Hammett relation, which is the tabulated quantity for exactly this:

    log10(k / k_0) = rho * sum(sigma)

`sigma` is a property of the SUBSTITUENT and its position; `rho` is a property of
the REACTION, so it is DECLARED per template rather than living here as a
universal constant. Converted to a barrier shift:

    dEa = -ln(10) * R * T_HAMMETT * rho * sum(sigma)

⚠⚠ **A rho IS MEANINGLESS WITHOUT SAYING WHICH SIGMA SCALE IT WAS FITTED ON**,
and this table is on **sigma-plus** (Brown and Okamoto, *JACS* **1958**, 80,
4979), not on the ordinary aqueous sigma. That is not a detail. Electrophilic
aromatic substitution builds positive charge on the ring in the transition state,
so a resonance donor stabilises it far more than its ionisation-based sigma says:
methoxy is **-0.27 on sigma and -0.778 on sigma-plus**, amino **-0.66 and
-1.30**. A rho fitted against sigma-plus applied to sigma constants is two bases
multiplied together, which is S12's finding wearing different clothes.

⚠ For electron ACCEPTORS the two scales nearly agree -- nitro is 0.71/0.78 on
sigma and 0.674/0.790 on sigma-plus, cyano 0.56/0.66 against 0.562/0.659 --
because there is no lone pair to donate. That is what makes the two `sigma-proxy`
rows below tolerable, and it is why they are both acceptors and are labelled.

⚠⚠ **T_HAMMETT IS 298.15 K AND IT IS NOT THE NETWORK'S BUILD TEMPERATURE.** Ask
what a fit was anchored on: sigma-plus and rho are tabulated from rate ratios
measured at 25 C, so 25 C is the only temperature at which this conversion
reproduces the number it came from. Using `T_ref` instead would make the same
template give different barriers in networks built at different temperatures,
with no measurement anywhere saying it should.

⚠ **AND THE CONSEQUENCE OF FOLDING IT ALL INTO Ea IS STATED RATHER THAN
HIDDEN.** A substituent effect is in general part enthalpic and part entropic,
and putting all of it in the barrier asserts it is all enthalpic. What that buys
is the behaviour being modelled -- a fixed barrier DIFFERENCE means the
selectivity between a fresh ring and a deactivated one weakens as the pot heats
up, which is why a staged nitration escalates its temperature. What it costs is
that the Hammett ratio itself is only reproduced exactly at 298.15 K. Putting it
in `A` instead would make the selectivity temperature-INDEPENDENT, which a staged
process is evidence against.

## Three things this does NOT do, said plainly

**1. NO REGIOSELECTIVITY.** The sum is over the substrate's ring as a whole, so
all three dinitrobenzenes from nitrobenzene still get the same barrier and are
still made at the same rate. Doing better needs the barrier to know WHICH ring
carbon was attacked, and a `ConcreteReaction` does not carry that -- it is a pair
of SMILES tuples and the site is gone by the time the barrier is computed. What
IS modelled is the directing rule's effect on the MAGNITUDE: a meta-directing
group is priced at sigma_meta because that is where the incoming group goes. So
the staging is right and the isomer ratio is not.

**2. NO PROTONATION.** ⚠⚠ In mixed acid an aniline is an ANILINIUM ion, and
-NH3+ is strongly deactivating and meta-directing where -NH2 is the most
activating group on the table. This engine prices the free base, so it makes
aniline **2.8e8 times more reactive than benzene** where the real nitration of
aniline in sulfuric acid gives largely meta product at a rate BELOW benzene's.
That shift is large enough to drive the barrier negative, which is why
`clamp_barrier` exists and refuses quietly to no one -- it reports. Coupling
protonation into a barrier needs the pKa and the medium's acidity, which is a
real piece of work and not this one.

**3. NO STERICS.** An ortho position next to a tert-butyl group is not the same
as one next to a hydrogen, and sigma says nothing about that.

## The table's provenance

Brown and Okamoto (1958) for sigma-plus; Hansch, Leo and Taft, *Chem. Rev.*
**1991**, 91, 165-195 for the THREE proxy rows and for `meta_directing`.
⚠ It was two until the `ammonio` row went in; the count is in the table, not
in this sentence, and `tests/test_ring_deactivation.py` asserts the PROPERTY
(every proxy must be an acceptor) rather than the number.

⚠ **`meta_directing` IS DECLARED AND NOT DERIVED FROM THE SIGN OF SIGMA**,
because the obvious derivation is wrong for the halogens. Chlorine is
DEACTIVATING (sigma-plus_para +0.114) and yet ORTHO/PARA directing, because
induction and resonance pull opposite ways on it. A rule of "meta-directing iff
sigma_para > 0" would put the incoming group in the wrong place on every
halobenzene in the corpus, so which position a group directs to is data, like the
constants.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from rdkit import Chem

from chemsim.constants import R

# The temperature the Hammett constants are tabulated at. See above: this is an
# ANCHOR, not a modelling temperature, and it is deliberately not ``T_ref``.
T_HAMMETT = 298.15

# ln(10) * R * T_HAMMETT, J/mol per log unit -- 5708 J/mol at 25 C.
_PER_DECADE = math.log(10.0) * R * T_HAMMETT

BROWN_OKAMOTO = "sigma+ (Brown & Okamoto 1958)"
SIGMA_PROXY = "sigma+ unpublished; aqueous sigma used (an ACCEPTOR -- see module)"


@dataclass(frozen=True)
class Substituent:
    """One ring substituent's constants, where it directs, and where it is from.

    ``smarts`` matches the substituent WITH its ring atom, written so the first
    atom of the pattern is the aromatic carbon carrying it and the second is the
    atom attached to it -- ``survey`` claims that BOND, which is how a group that
    answers two patterns is counted once.
    """

    label: str
    smarts: str
    sigma_m: float
    sigma_p: float
    # Where the incoming electrophile goes. DECLARED -- see the module docstring
    # on why the halogens forbid deriving it from the sign of sigma_para.
    meta_directing: bool
    source: str = BROWN_OKAMOTO

    @property
    def sigma(self) -> float:
        """The constant at the position this group actually directs to."""
        return self.sigma_m if self.meta_directing else self.sigma_p


# ⚠ ORDER IS SIGNIFICANT -- most specific first. An acetamido group answers
# ``[c][NX3]`` as readily as an amine does, and an aryl ketone answers
# ``[c]C(=O)[#6]`` as readily as an ester does; matching the general pattern
# first would price paracetamol's amide as an aniline. Both are in the corpus.
_TABLE: tuple[Substituent, ...] = (
    # -- strongly deactivating, meta-directing --------------------------------
    # ⚠⚠ THE PROTONATED AMINE, AND IT IS THE ONE ROW WHOSE TWO CONSTANTS ARE
    # ORDERED THE WRONG WAY ROUND. Every other meta-directing group here has
    # sigma_meta < sigma_para (nitro 0.674 / 0.790), so ``meta_directing`` picks
    # the SMALLER of the two; -NH3+ has 0.86 / 0.60 and it picks the LARGER.
    # That inversion is the second reason ``meta_directing`` is DECLARED and not
    # derived -- the halogens are the first. A rule of "meta-directing iff
    # sigma_para > sigma_meta" would call an anilinium an ortho/para director,
    # and the observed product says otherwise: aniline nitrated in concentrated
    # sulfuric acid gives largely META-nitroaniline, and the trimethylanilinium
    # ion -- which has no N-H to lose and therefore cannot slip back to a free
    # base at all -- gives about 89% meta.
    #
    # ⚠ A PROXY ROW, and it is labelled, for the SAME reason ``sulfo`` is: no
    # sigma-plus is published for -NH3+ and none can be. The Brown-Okamoto scale
    # is built from rate ratios in electrophilic substitution, and an anilinium
    # is the deactivated case that has to be measured in strong acid where the
    # medium's own acidity function is the variable. What makes the aqueous
    # sigma tolerable here is the argument in the module docstring: a group with
    # no lone pair to donate into the ring reads the same on both scales, and
    # -NH3+ has all three of nitrogen's hydrogens and no lone pair at all.
    #
    # ⚠ It matches only a PROTONATED amine (at least one N-H). An aryl
    # QUATERNARY ammonium is a different substituent whose constants this table
    # does not source, so it falls through to ``unknown`` and is REPORTED --
    # the aspirin-acyloxy precedent, one row down.
    Substituent("ammonio", "[c][N+;X4;!H0]", 0.86, 0.60, True, SIGMA_PROXY),
    Substituent("nitro", "[c][N+](=O)[O-]", 0.674, 0.790, True),
    Substituent("cyano", "[c]C#N", 0.562, 0.659, True),
    # ⚠ A PROXY ROW, and it is labelled. No sigma-plus is published for -SO3H
    # that this table's author can source. It is an acceptor with no lone pair
    # to donate into the ring, which is the case where the two scales agree --
    # and leaving it out entirely would price a sulfonated ring at sigma = 0,
    # i.e. as unsubstituted, which is a larger error than the basis mismatch.
    Substituent("sulfo", "[c]S(=O)(=O)[OX2H1]", 0.50, 0.57, True, SIGMA_PROXY),
    # -- moderately deactivating, meta-directing ------------------------------
    Substituent("carboxy", "[c]C(=O)[OX2H1]", 0.322, 0.421, True),
    Substituent("carboxylate-ester", "[c]C(=O)O[#6]", 0.37, 0.482, True,
                SIGMA_PROXY),
    Substituent("formyl", "[c][CX3H1]=O", 0.355, 0.730, True),
    Substituent("acyl", "[c]C(=O)[#6]", 0.376, 0.567, True),
    # -- deactivating but ORTHO/PARA directing: the halogens ------------------
    # ⚠ THE EXCEPTION THE ``meta_directing`` FIELD EXISTS FOR. All four have a
    # POSITIVE sigma_meta and all four are ortho/para directors -- and note that
    # fluorine's sigma-plus_para is NEGATIVE while its sigma_para is +0.06, which
    # is the two scales disagreeing about whether fluorine deactivates the para
    # position at all. It is the scale that matters here that says it does not.
    Substituent("fluoro", "[c][F]", 0.352, -0.073, False),
    Substituent("chloro", "[c][Cl]", 0.399, 0.114, False),
    Substituent("bromo", "[c][Br]", 0.405, 0.150, False),
    Substituent("iodo", "[c][I]", 0.359, 0.135, False),
    # -- activating, ortho/para directing -------------------------------------
    # Amide before amine, for the same reason ester comes before ketone.
    Substituent("acylamino", "[c][NX3;H1,H0][CX3]=O", 0.021, -0.600, False),
    Substituent("amino", "[c][NX3;H2,H1;!$([NX3][CX3]=O)]", -0.16, -1.30,
                False),
    Substituent("hydroxy", "[c][OX2H1]", 0.121, -0.920, False),
    # ⚠ ``!$([CX3]=O)`` keeps an ACYLOXY group out of this row. Aspirin's
    # -OC(=O)CH3 is an ester oxygen whose lone pair is tied up in the carbonyl,
    # so it is nothing like a methoxy: pricing it at -0.778 would make aspirin
    # more reactive than anisole. No sigma-plus for it is sourced here, so it
    # falls through to ``unknown`` and is REPORTED rather than guessed.
    Substituent("alkoxy", "[c][OX2][#6;!$([CX3]=O)]", 0.047, -0.778, False),
    Substituent("alkyl", "[c][CX4]", -0.066, -0.311, False),
    Substituent("aryl", "[c]-[c]", 0.109, -0.179, False),
)

_PATTERNS = tuple((s, Chem.MolFromSmarts(s.smarts)) for s in _TABLE)


@dataclass(frozen=True)
class RingSurvey:
    """What was found on one molecule's aromatic rings."""

    sigma_sum: float
    found: tuple[str, ...]
    # Ring atoms carrying a heavy-atom substituent that no pattern claimed. NOT
    # an error and NOT silently zero: reported, so a network that hits one says
    # so once and keeps running. The project's third case -- a latent gap is
    # reported, not refused.
    unknown: tuple[str, ...]


def survey(mol: Chem.Mol) -> RingSurvey:
    """Sum the sigma-plus constants of every substituent on ``mol``'s aromatic rings.

    ⚠ EVERY aromatic ring, not one of them, and that is the honest reading of a
    sum with no site in it: with no attacked carbon to measure positions from
    there is no basis for preferring one ring over another. It is exact for the
    single-ring substrates the corpus is made of and it OVER-COUNTS a biphenyl,
    which is named here rather than discovered later.
    """
    if mol is None:
        return RingSurvey(0.0, (), ())

    total = 0.0
    found: list[str] = []
    # Which ring-atom/substituent-atom bonds a pattern has already claimed, in
    # BOTH directions -- a biaryl bond is a substituent seen from either end and
    # would otherwise be claimed once and reported unknown once.
    claimed: set[tuple[int, int]] = set()

    for sub, patt in _PATTERNS:
        for match in mol.GetSubstructMatches(patt):
            a, b = match[0], match[1]
            if (a, b) in claimed:
                continue
            claimed.add((a, b))
            claimed.add((b, a))
            total += sub.sigma
            found.append(sub.label)

    ring_info = mol.GetRingInfo().AtomRings()
    unknown: list[str] = []
    for atom in mol.GetAtoms():
        if not atom.GetIsAromatic():
            continue
        for nb in atom.GetNeighbors():
            i, j = atom.GetIdx(), nb.GetIdx()
            if nb.GetAtomicNum() == 1 or (i, j) in claimed:
                continue
            # Two atoms of the SAME ring are the ring itself, not a substituent.
            if any(i in r and j in r for r in ring_info):
                continue
            unknown.append(f"-{nb.GetSymbol()} on an aromatic carbon")

    return RingSurvey(total, tuple(sorted(found)), tuple(sorted(set(unknown))))


def barrier_shift(rho: float, sigma_sum: float) -> float:
    """J/mol to add to a barrier for a ring carrying ``sigma_sum``.

    ``dEa = -ln(10) * R * T_HAMMETT * rho * sum(sigma)``. Exactly 0.0 when either
    factor is zero, which is what makes an unsubstituted ring keep the template's
    declared barrier BIT FOR BIT rather than nearly so.
    """
    if rho == 0.0 or sigma_sum == 0.0:
        return 0.0
    return -_PER_DECADE * rho * sigma_sum


def clamp_barrier(Ea: float) -> float:
    """A barrier may not be negative, however activated the ring is.

    ⚠ THIS IS REACHABLE AND IT IS NOT A DEFENSIVE FLOOR. Aniline's sigma-plus_para
    is -1.30, so at rho = -6.5 the shift is **-48.2 kJ/mol** -- and against
    `aromatic_nitration`'s declared 60 kJ/mol that leaves 11.8, while a phenol
    plus an amine on one ring would go straight through zero. A negative
    activation energy in an Arrhenius law is a rate that RISES as the flask
    cools, which is not a slow reaction or a fast one but a wrong one.

    ⚠ AND THE CLAMP IS NOT THE FIX FOR THE UNDERLYING ERROR. What actually
    happens to an aniline in mixed acid is that it protonates, and the anilinium
    ion is deactivating -- see the module docstring's point 2. The clamp keeps the
    arithmetic legal; the physics is still missing and is named.
    """
    return max(Ea, 0.0)


def rate_ratio(rho: float, sigma_sum: float, T: float = T_HAMMETT) -> float:
    """k / k_0 implied by a shift, for reporting. At ``T_HAMMETT`` this is exactly
    ``10 ** (rho * sigma_sum)`` -- the Hammett relation, read back."""
    return math.exp(-barrier_shift(rho, sigma_sum) / (R * T))
