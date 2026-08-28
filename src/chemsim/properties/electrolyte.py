"""Layer 1 -- electrolytes: acids, bases, ions and pH.

There is no pH solver in this codebase, and there should not be one. Acid
dissociation is *chemistry*, so it enters as ordinary reversible reactions:

    HA + H2O  <=>  A- + H3O+
    2 H2O     <=>  H3O+ + OH-

and everything already built handles them. Detailed balance fixes each reverse
rate from the thermochemistry, the stiff integrator resolves the fast equilibrium,
and the network builder's charge-balance check -- which has been enforcing
electroneutrality on every reaction since Layer 3 -- suddenly starts earning its
keep. pH is then a *readout*, ``-log10[H3O+]``, not a state variable.

Two decisions make this work cleanly.

**Write dissociation with water on both sides.** ``HA + H2O <=> A- + H3O+`` has
delta_n = 0, where the more familiar ``HA <=> A- + H+`` has delta_n = +1. That
matters more than it looks: a mole-changing reaction drags in the activity-to-
molarity standard-state conversion (see ``reactions.thermo``), and our formation
data is ideal-gas while aqueous ion data is on the molarity scale. Writing it the
balanced way makes the conversion cancel exactly, so the two unit systems never
have to be reconciled.

**Derive ion formation data from pKa, against our own water entry.** Rather than
importing tabulated aqueous ion values -- which are referenced to liquid water and
would silently disagree with our ideal-gas water -- each ion's Gibbs energy is
back-calculated so that the measured pKa comes out right *with the water value
this project already uses*:

    dG_rxn = 2.303 * R * T * pKa      and      dGf(A-) = dGf(HA) + dG_rxn

using the convention dGf(H3O+) = dGf(H2O), i.e. the proton is the zero. The
resulting numbers are not literature aqueous values and are not labelled as such;
they are internally consistent constants that reproduce measured acidity.

**The anchor is the NEUTRAL member of the pair, in its LIQUID standard state.**
⚠ It used to be the ACID, unconditionally, and that was a bug: four rows of the
table below are CATION/neutral pairs whose acid IS the ion, and the ordinary
providers refuse to price a charge. See ``ion_thermochemistry`` for what those
four rows were worth. A neutral acid anchors its anion, a neutral base anchors
its cation, and the second is the first read backwards. A pKa is a
solution-phase measurement, so the neutral member and the water it is derived
against must be on the solution basis too (see ``standard_state``). An ion has
no volatility model and therefore never gets shifted at reaction level;
anchoring it here on the shifted neutral is what makes the two conventions meet. Skip this and every pKa
moves by about three units, because acetic acid and water are each worth ~9 kJ/mol
of vaporization Gibbs energy and both land on the same side of the reaction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from chemsim.constants import R
from chemsim.matter import Molecule
from chemsim.properties import standard_state
from chemsim.properties.thermochemistry import ThermoData, ThermochemistryProvider
from chemsim.properties.volatility import VolatilityProvider

T_REF = 298.15
LN10 = math.log(10.0)

# Water autoionization. Kw = 1e-14 at 298 K.
PKW = 14.0


@dataclass(frozen=True)
class AcidPair:
    """A conjugate acid/base pair and the measured acidity that connects them."""

    acid: str          # SMILES of the protonated form
    base: str          # SMILES of the deprotonated form
    pKa: float
    name: str = ""
    dH_diss: float = 0.0   # kJ/mol, enthalpy of dissociation (often near zero)


# Aqueous pKa at 298 K. Sources: CRC Handbook; Bordwell compilations.
# dH_diss for carboxylic acids is genuinely small -- their acidity is entropic --
# which is why most entries leave it at zero rather than inventing a number.
_PAIRS: tuple[AcidPair, ...] = (
    # --- mineral acids (strong: negative pKa) -----------------------------
    AcidPair("Cl", "[Cl-]", -6.3, "hydrochloric acid"),
    AcidPair("Br", "[Br-]", -8.7, "hydrobromic acid"),
    # ⚠ ADDED BY M5 AND THE REASON IS A ROUTE, NOT TIDINESS. The Williamson ether
    # synthesis makes iodide, and without this pair ``[I-]`` was REFUSED -- so a
    # network could form methyl phenyl ether and then not be integrable, which is
    # the worst of the three outcomes. HI's own formation data is measured (NIST
    # CODATA, Hf +26.50 / Gf +1.70 kJ/mol), so only the pKa was needed, and -9.3
    # is the member of the SAME halide series this table already carries: HCl
    # -6.3, HBr -8.7, HI -9.3. Taking -10 from a different compilation would have
    # mixed two sources inside one trend, which is the error the curation rules
    # exist to prevent.
    AcidPair("I", "[I-]", -9.3, "hydroiodic acid"),
    AcidPair("O[N+](=O)[O-]", "[O-][N+](=O)[O-]", -1.4, "nitric acid"),
    AcidPair("OS(=O)(=O)O", "[O-]S(=O)(=O)O", -3.0, "sulfuric acid, 1st"),
    AcidPair("[O-]S(=O)(=O)O", "[O-]S(=O)(=O)[O-]", 1.99, "sulfuric acid, 2nd"),
    AcidPair("OP(=O)(O)O", "[O-]P(=O)(O)O", 2.15, "phosphoric acid, 1st"),
    AcidPair("[O-]P(=O)(O)O", "[O-]P(=O)([O-])O", 7.20, "phosphoric acid, 2nd"),
    # ⚠⚠⚠ ADDED BY C2, AND THE REASON IS THAT A LATTICE COULD NOT BE PUT IN A
    # FLASK -- not that a number was missing.
    #
    # `ion_data` has carried phosphate, hydrogen phosphate AND dihydrogen
    # phosphate on the aqueous basis since M3. This table stopped one proton
    # short, and nothing anywhere compares the two tables' MEMBERSHIP -- the
    # module docstring's warning about them is entirely about their different
    # ZEROS. So `mineral_data` could price phosphate rock, `solubility_product`
    # could return a Ksp for it against ions this table cannot reach, the
    # coverage audit could read `phosphoric-wet` species-ready, and
    # `build_network` would then REFUSE `O=P([O-])([O-])[O-]` for want of a
    # pKa. **Two curated tables over the same ions, and only one of them had
    # all three.** ``validation/phosphate_rock.py`` panel 2 measures the gap
    # across every anion in both tables so it cannot happen silently again.
    #
    # ⚠ 12.35 IS THE MEMBER OF THE SERIES THIS TABLE ALREADY CARRIES, which is
    # the HI decision above applied a second time: the two rows above are 2.15
    # and 7.20, and 12.35 is the third of that same triple. CRC's own row is
    # 2.16 / 7.21 / 12.32; taking 12.32 to sit under a 2.15 and a 7.20 would
    # mix two compilations inside one trend, which is exactly what the iodide
    # comment refuses.
    #
    # ⚠⚠ AND ITS VALUE IS MEASURED IRRELEVANT WHERE IT IS USED, WHICH IS THE
    # HONEST WAY TO SHIP A CONSTANT THAT WAS NEEDED FOR REPRESENTABILITY RATHER
    # THAN FOR AN ANSWER. The wet process runs at pH ~1, twelve decades below
    # this pKa, so the trianion is never populated -- it is in the network only
    # because it is what the ROCK is made of. Swept over 11.35/12.35/13.35 the
    # digestion's phosphoric acid agrees to eight figures
    # (``validation/phosphate_rock.py`` panel 4). **A constant whose error is
    # measured invisible is a different thing from one nobody checked.**
    AcidPair("[O-]P(=O)([O-])O", "[O-]P(=O)([O-])[O-]", 12.35,
             "phosphoric acid, 3rd"),
    AcidPair("F", "[F-]", 3.17, "hydrofluoric acid"),
    AcidPair("C#N", "[C-]#N", 9.21, "hydrogen cyanide"),
    AcidPair("S", "[SH-]", 7.00, "hydrogen sulfide"),
    # ⚠ BOTH CARBONATE PAIRS ARE PRESENT AND BOTH ARE INERT, and the reason is
    # worth reading before anyone "fixes" it with a number.
    #
    # ``ion_thermochemistry`` skips a pair whose ACID cannot be priced, and
    # carbonic acid cannot: Benson prices its formation half well (Hf -611.8,
    # Gf -559.1 kJ/mol) but there is NO physical half -- no source has a boiling
    # point, because it decomposes to CO2 and water rather than boiling. The
    # only melting point on offer anywhere is 484.65 K from a crowd-sourced
    # compilation, for a species that has never been isolated as a bulk solid
    # at ambient conditions; taking it to unlock carbonate would be exactly the
    # confident estimate of an unmeasured quantity that ``element_data`` exists
    # to prevent. So these two sit here recognised and unpriced, which is the
    # same standing-refusal shape as Benson's ``AROMATIC_INTERACTIONS``.
    #
    # **THE HONEST ANCHOR IS DISSOLVED CO2, AND IT IS NOT A ONE-LINE ENTRY.**
    # The quantity everyone calls "carbonic acid pKa 6.35" is the acidity of the
    # CO2/water system, not of true H2CO3 (whose own pKa is ~3.45). Written the
    # way this module writes everything else that is:
    #
    #     CO2 + 2 H2O  <=>  HCO3-  +  H3O+
    #
    # which consumes TWO waters and has delta_n = -1. Both of those break the
    # convention the whole ion table rests on -- see the module docstring: every
    # pair here is written with ONE water on each side precisely so delta_n = 0
    # and the activity-to-molarity standard-state conversion cancels exactly.
    # Supporting it means ``AcidPair`` carrying an explicit water count AND the
    # anchoring arithmetic handling a mole-changing dissociation. Bounded work,
    # and it gates chain 1's wood-ash detour (a carbonate is a WEAK base, so
    # crude lye under-hydrolyses the ester) -- but it is engine-adjacent work
    # rather than a data line, and calling it a data line is how it would get
    # done wrong.
    AcidPair("OC(=O)O", "[O-]C(=O)O", 6.35, "carbonic acid, 1st", dH_diss=9.2),
    AcidPair("[O-]C(=O)O", "[O-]C(=O)[O-]", 10.33, "carbonic acid, 2nd", dH_diss=14.9),
    # --- carboxylic acids --------------------------------------------------
    AcidPair("OC=O", "[O-]C=O", 3.75, "formic acid"),
    AcidPair("CC(=O)O", "CC(=O)[O-]", 4.76, "acetic acid", dH_diss=-0.4),
    AcidPair("CCC(=O)O", "CCC(=O)[O-]", 4.87, "propanoic acid"),
    AcidPair("OC(=O)c1ccccc1", "[O-]C(=O)c1ccccc1", 4.20, "benzoic acid"),
    # Salicylic acid -- chain 1's product, and a full pKa unit stronger than
    # benzoic acid (2.97 against 4.20) because the ortho hydroxyl hydrogen-bonds
    # to the carboxylate and stabilises it. That difference is what makes the
    # acidification step of the aspirin route behave differently from the
    # benzoic-acid prep it is otherwise identical to, so it is not decoration.
    AcidPair("OC(=O)c1ccccc1O", "[O-]C(=O)c1ccccc1O", 2.97, "salicylic acid"),
    # ⚠⚠⚠ ADDED BY C5, AND IT WAS EXPOSED RATHER THAN MISSED. The Kolbe-
    # Schmitt network makes salicylate and then wants to take its PHENOL
    # proton as well -- real chemistry, pKa2 = 13.4 -- and until C5 fixed
    # `ReactionTemplate.run` the engine could not run a template on a
    # species another template had MADE, so `phenol_dissociation` never
    # reached the mono-anion and this row was never asked for. **The fix
    # did not create a gap; it made a two-generation network reachable and
    # the gap was already there.** C2's rule, from the other side: a table
    # can be short a row for years if nothing can get far enough to ask.
    #
    # ⚠⚠ 13.4 against phenol's own 9.95, and the 3.5 units are the point:
    # the ortho CARBOXYLATE hydrogen-bonds to the phenol proton and holds
    # onto it, which is the same interaction that makes the FIRST proton
    # come off at 2.97 instead of benzoic acid's 4.20. One hydrogen bond,
    # both directions, and this table now carries both ends of it.
    AcidPair("[O-]C(=O)c1ccccc1O", "[O-]C(=O)c1ccccc1[O-]", 13.4,
             "salicylic acid, 2nd"),
    AcidPair("CC(O)C(=O)O", "CC(O)C(=O)[O-]", 3.86, "lactic acid"),
    AcidPair("OC(=O)C(=O)O", "[O-]C(=O)C(=O)O", 1.25, "oxalic acid, 1st"),
    AcidPair("OC(=O)CCCCC(=O)O", "[O-]C(=O)CCCCC(=O)O", 4.43, "adipic acid, 1st"),
    AcidPair("CC(=O)Oc1ccccc1C(=O)O", "CC(=O)Oc1ccccc1C(=O)[O-]", 3.49, "aspirin"),
    # --- weak organic acids / bases ---------------------------------------
    AcidPair("Oc1ccccc1", "[O-]c1ccccc1", 9.95, "phenol"),
    AcidPair("[NH4+]", "N", 9.25, "ammonium", dH_diss=52.2),
    AcidPair("C[NH3+]", "CN", 10.66, "methylammonium"),
    AcidPair("c1ccc[nH+]c1", "c1ccncc1", 5.23, "pyridinium"),
    AcidPair("[NH3+]c1ccccc1", "Nc1ccccc1", 4.62, "anilinium"),
)

_IONIC_SOLIDS: dict[str, tuple[str, str]] = {
    # A salt that is fully dissociated in solution: stored as its ions directly.
    "[Na+].[OH-]": ("[Na+]", "[OH-]"),
}

_DERIVED = "derived from measured pKa against this project's water reference"


class _NoShiftVolatility:
    """A volatility provider that declines every standard-state shift.

    Exists so the pre-correction ideal-gas basis can still be constructed and
    compared against, rather than only described.
    """

    def get(self, molecule):
        from chemsim.properties.volatility import NONVOLATILE_A, Volatility

        return Volatility(
            NONVOLATILE_A, 0.0, 0.0, "standard-state shift disabled", "nonvolatile"
        )


_NO_SHIFT_VOLATILITY = _NoShiftVolatility()


# Molarity of pure water, from THIS project's curated molar volume (0.01807 L/mol)
# rather than a textbook 55.5 -- the integrator computes [H2O] from that same
# number, and the two must agree exactly or the correction below is wrong.
C_WATER = 1.0 / 0.01807     # mol/L


def _dG_from_pKa(pKa: float, T: float = T_REF) -> float:
    """Standard Gibbs energy of dissociation in kJ/mol."""
    return LN10 * R * T * pKa / 1000.0


def _solvent_correction(n_water: int, T: float = T_REF) -> float:
    """kJ/mol to add so that mass action in molarity reproduces a measured pKa.

    A pKa is defined with the *activity* of water equal to 1, because water is the
    solvent and its standard state is the pure liquid. Mass action has no such
    convention: it multiplies by [H2O] = 55.3 M like any other reactant. So a
    reaction consuming n water molecules comes out 55.3**n too favourable unless
    the constants absorb the difference:

        dG_massaction = dG_measured + n * R * T * ln(C_water)

    Without this, acetic acid reads pH 1.5 instead of 2.4 and pure water reads
    pH 5.3 instead of 7.0 -- both off by exactly sqrt(55.3) and 55.3, which is how
    the discrepancy was identified.
    """
    return n_water * R * T * math.log(C_WATER) / 1000.0


def ion_thermochemistry(
    thermo: ThermochemistryProvider,
    pairs: tuple[AcidPair, ...] = _PAIRS,
    T: float = T_REF,
    volatility: VolatilityProvider | None = None,
) -> dict[str, ThermoData]:
    """Formation data for every conjugate base whose acid we can already price.

    Skips any pair whose acid has no thermochemistry -- there is nothing to
    anchor the ion to, and inventing a value would be worse than omitting it.

    ``volatility`` supplies the liquid standard-state shift the anchors are taken
    in; omit it only to reproduce the old ideal-gas basis.
    """
    volatility = volatility or VolatilityProvider(thermo)

    def anchored(smiles: str) -> ThermoData:
        """Formation data for a neutral species in its liquid standard state."""
        data = thermo.get(smiles)
        s = standard_state.shift(smiles, volatility, T)
        if not s.applied:
            return data
        return replace(data, Hf=data.Hf + s.dHf, Gf=data.Gf + s.dGf)

    out: dict[str, ThermoData] = {}
    water = anchored("O")

    # The proton, by convention, costs the same as the water that carries it.
    out["[OH3+]"] = ThermoData(
        Hf=water.Hf, Gf=water.Gf, source=_DERIVED + " (proton is the zero)",
        Cp_coeffs=(75.0, 0.0, 0.0, 0.0),
    )
    # Hydroxide follows from Kw: 2 H2O <=> H3O+ + OH-  (two waters consumed)
    dG_w = _dG_from_pKa(PKW, T) + _solvent_correction(2, T)
    out["[OH-]"] = ThermoData(
        Hf=2 * water.Hf - out["[OH3+]"].Hf + 55.8,   # dH of autoionization
        Gf=2 * water.Gf - out["[OH3+]"].Gf + dG_w,
        source=_DERIVED + " (from pKw = 14.0)",
        Cp_coeffs=(75.0, 0.0, 0.0, 0.0),
    )

    # Order matters: a polyprotic acid's second dissociation is anchored on the
    # ion produced by its first, so each derived value must be visible to the
    # pairs that follow. Sulfate, for instance, is priced from bisulfate, which
    # Joback cannot touch and which is itself derived from sulfuric acid.
    # ⚠⚠ AND THE ANCHOR IS THE **NEUTRAL** MEMBER, NOT THE ACID -- MEASURED,
    # AND IT USED TO BE THE ACID. Four rows of this table are CATION/neutral
    # pairs (ammonium 9.25, methylammonium 10.66, pyridinium 5.23, anilinium
    # 4.62) whose acid is the ION and whose base is the neutral molecule. On the
    # acid-anchored form ``anchored(pair.acid)`` refused all four -- Joback and
    # Benson are fitted to NEUTRAL molecules and refuse a charge, loudly and
    # correctly -- and the bare ``except Exception: continue`` below swallowed
    # it, so those four curated rows produced NOTHING. The table shipped 24
    # anions and one hard-coded hydronium and no cation at all. An anilinium
    # could not be priced, so nothing could protonate an amine, so ``hammett``
    # had no choice but to price an aniline as a free base.
    #
    # ⚠ The DIRECTION the arithmetic runs in is a property of the PAIR, not of
    # the table: a neutral acid anchors its anion, a neutral base anchors its
    # cation, and the second is the first read backwards. Both directions use
    # the same measured pKa and the same one-water correction, so the pair
    # reproduces its own pKa either way round -- which is what
    # ``validation/protonation.py`` asserts rather than assumes.
    for pair in pairs:
        acid_key = Molecule.from_smiles(pair.acid).smiles
        base_key = Molecule.from_smiles(pair.base).smiles
        note = f"{_DERIVED} (pKa = {pair.pKa} for {pair.name or pair.acid})"

        if acid_key in out:
            # An ion anchoring the next dissociation. Already on the solution
            # basis by construction, so it must NOT be shifted again.
            anchor, target, sign = out[acid_key], base_key, +1
        elif base_key in out:
            anchor, target, sign = out[base_key], acid_key, -1
        else:
            # ⚠ THE ACID IS TRIED FIRST AND THAT ORDER IS THE COMPATIBILITY
            # GUARANTEE: every value this table derived before the fix is
            # anchored the same way and comes out bit-identical.
            try:
                anchor, target, sign = anchored(pair.acid), base_key, +1
            except Exception:
                try:
                    anchor, target, sign = anchored(pair.base), acid_key, -1
                except Exception:
                    continue          # neither side has an anchor; skip silently
        if target in out:
            continue
        # ⚠ THE TWO TERMS ARE ADDED SEPARATELY AND IN THIS ORDER ON PURPOSE.
        # dG of  HA + H2O <=> A- + H3O+  in the sense the pKa is quoted in, plus
        # the mass-action correction for the one water it consumes -- and
        # summing them into a single ``dG_diss`` first re-groups the addition,
        # which moved TEN of the pre-existing anions in the last bit. Floating
        # point is not associative and a data table that shifts by 1e-16 owes
        # ``tolerance_audit.py`` a ten-minute run to prove it did not matter.
        out[target] = ThermoData(
            Hf=anchor.Hf + sign * pair.dH_diss,
            Gf=(anchor.Gf + sign * _dG_from_pKa(pair.pKa, T)
                + sign * _solvent_correction(1, T)),
            source=note,
            Cp_coeffs=anchor.Cp_coeffs,
        )
    return out


def electrolyte_provider(
    base: ThermochemistryProvider | None = None,
    extra_pairs: tuple[AcidPair, ...] = (),
    volatility: VolatilityProvider | None = None,
) -> ThermochemistryProvider:
    """A ThermochemistryProvider that also prices ions.

    Ions are injected as curated entries, so everything downstream -- detailed
    balance, the energy balance, the phase model -- treats them exactly like any
    other species and needs no special case.
    """
    base = base or ThermochemistryProvider()
    ions = ion_thermochemistry(
        base, _PAIRS + tuple(extra_pairs), volatility=volatility
    )
    return ThermochemistryProvider(extra_curated=ions)


# ---------------------------------------------------------------------------
# Dissociation as graph rewrites
# ---------------------------------------------------------------------------
# Written with water explicitly on both sides so delta_n = 0 -- see the module
# docstring. A is deliberately large and Ea zero: proton transfer is diffusion
# limited, far faster than anything else in the pot, so these equilibrate
# essentially instantly and the stiff solver is what makes that affordable.

# Proton transfer is diffusion limited -- far faster than anything else in the pot
# -- so these equilibrate essentially instantly and the stiff solver is what makes
# that affordable. Ea is set above the largest dissociation enthalpy in the table
# (water's, 55.8 kJ/mol) so the elementary-barrier clamp in detailed_balance does
# not have to fire for the ordinary case; A is raised to keep the rate fast.
_FAST_A = 1.0e12
_FAST_EA = 60_000.0


def dissociation_templates(A: float = _FAST_A, Ea: float = _FAST_EA):
    """Templates covering the common ionizable groups, plus water autoionization."""
    from chemsim.reactions import ReactionTemplate

    return [
        ReactionTemplate(
            name="water_autoionization",
            smarts="[OX2H2:1].[OX2H2:2]>>[OH3+:1].[OH-:2]",
            A=A, Ea=Ea, reversible=True,
        ),
        ReactionTemplate(
            name="carboxylic_acid_dissociation",
            smarts="[CX3:1](=[O:2])[OX2H1:3].[OX2H2:4]>>[CX3:1](=[O:2])[O-:3].[OH3+:4]",
            A=A, Ea=Ea, reversible=True,
        ),
        ReactionTemplate(
            name="phenol_dissociation",
            smarts="[c:1][OX2H1:2].[OX2H2:3]>>[c:1][O-:2].[OH3+:3]",
            A=A, Ea=Ea, reversible=True,
        ),
        ReactionTemplate(
            name="hydrogen_halide_dissociation",
            smarts="[F,Cl,Br,I;H1:1].[OX2H2:2]>>[F,Cl,Br,I;-:1].[OH3+:2]",
            A=A, Ea=Ea, reversible=True,
        ),
        ReactionTemplate(
            name="mineral_oxyacid_dissociation",
            smarts="[S,N,P;+0,+1:1](=[O:2])[OX2H1:3].[OX2H2:4]"
                   ">>[S,N,P:1](=[O:2])[O-:3].[OH3+:4]",
            A=A, Ea=Ea, reversible=True,
        ),
        # ⚠⚠⚠ WRITTEN IN THE PROTONATION DIRECTION, AND IT REPLACES A
        # ``ammonium_dissociation`` THAT COULD NOT DEPROTONATE AN AMMONIUM.
        #
        # The old pattern was ``[NX4H+:1].[OX2H2:2]>>[NX3:1].[OH3+:2]``. In
        # SMARTS a bare ``H`` inside brackets means EXACTLY ONE hydrogen, so
        # ``[NX4H+]`` matches a protonated TERTIARY amine and nothing else --
        # measured, it is False against [NH4+], against anilinium, against
        # methylammonium and against pyridinium, and True only against
        # C[NH+](C)C. The template named for the ammonium ion was the one ion it
        # could not touch, and no example ever caught it because nothing in the
        # corpus can put a trialkylammonium in a flask.
        #
        # ⚠⚠ AND THE DIRECTION IS THE POINT, NOT THE PATTERN. Discovery in
        # ``network.builder`` runs templates FORWARD ONLY -- a reversible
        # template's reverse is a concrete reaction in the network, but it is
        # never used to enumerate species. So a deprotonation-forward template
        # can only find an anilinium in a flask that already contains one, and a
        # flask of aniline and mixed acid does not. Writing the same equilibrium
        # protonation-forward finds it from the free base, which is the
        # ``ester_hydrolysis`` decision again: when only one direction is
        # discoverable, the direction you need is the direction you declare.
        # Nothing is lost by the swap -- ``reversible=True`` puts the
        # deprotonation in the network with its rate fixed by detailed balance
        # from the same pKa.
        #
        # ⚠ ``[OX2H2;+0:2]`` and not ``[OX2H2:2]``: a mapped atom keeps its
        # formal charge through a rewrite, so the un-annotated form hands back
        # water with a +1 on it. ``_element_charge_balance`` catches that and
        # drops the rewrite, which means the bug's symptom is a template that
        # silently does nothing rather than a wrong number.
        #
        # ⚠ AN AMIDE, A NITRO GROUP, A NITRILE AND A PYRIDINE ARE ALL EXCLUDED
        # and all four are measured in ``tests/test_protonation.py``. The amide
        # exclusion is chemistry: its conjugate acid is a different pair with a
        # pKa near zero, and this table does not carry it. The pyridine
        # exclusion is a LIMIT and it is named -- an aromatic ring nitrogen is
        # X2, not X3, so the pyridinium row now in ``_PAIRS`` is priced and
        # still unreachable.
        ReactionTemplate(
            name="amine_protonation",
            smarts="[NX3;!$([N+]);!$([NX3][CX3]=O);!$([NX3]=*);!$([NX3]#*):1]"
                   ".[OH3+:2]>>[NX4+:1].[OX2H2;+0:2]",
            A=A, Ea=Ea, reversible=True,
        ),
    ]


def known_pairs() -> tuple[AcidPair, ...]:
    """The curated acid/base table -- exposed so callers can inspect coverage."""
    return _PAIRS


def ionic_solids() -> dict[str, tuple[str, str]]:
    return dict(_IONIC_SOLIDS)
