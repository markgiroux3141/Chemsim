"""Layer 1 -- measured formation data, in BOTH standard states.

Joback is a group-contribution estimator, and two of its failure modes are
structural rather than a matter of accuracy:

* **It cannot distinguish homologues.** Group contributions are additive, so
  the CH3 -> C2H5 difference cancels *exactly* between an alcohol and the ester
  it makes. Esterifying methanol and esterifying ethanol therefore came out
  with an identical gas-phase dG_rxn of -7.35 kJ/mol. No downstream care can
  recover a distinction the estimator never made.
* **Its errors are several kJ/mol**, which is a factor of 2-4 in K. For
  methanol it is 17 kJ/mol -- a factor of a thousand.

This module carries measured values instead, for the species that actually turn
up in recipes, and it carries them in the two standard states separately:

    IDEAL_GAS_FORMATION[smiles] = (dHf(g), dGf(g))    kJ/mol, 298.15 K
    LIQUID_FORMATION[smiles]    = (dHf(l), dGf(l))    kJ/mol, 298.15 K

The liquid table exists because the ``R T ln(Psat)`` route into the liquid
standard state (see ``standard_state``) has one species class it cannot price:
**a carboxylic acid's vapour is not its monomer.** Acetic acid vapour is ~95%
dimer at 298 K, so the measured vapour pressure belongs to a different molecule
than the formation data does. The size of that error is visible in the data
itself -- for acetic acid, dHf(g) - dHf(l) is 51.4 kJ/mol against a *measured*
dHvap of 23.4, a 28 kJ/mol discrepancy that is simply the dimerisation
enthalpy. A curated liquid entry sidesteps it: the liquid value IS the liquid
standard state, so there is no vapour to misprice.

Where both tables hold a species, the standard-state shift becomes exact --
it is the difference of two measurements, and no correlation enters at all.

## Provenance and how every number here was checked

Enthalpies and absolute entropies are from the CRC Handbook / NIST WebBook /
ATCT compilations, via the ``chemicals`` package. dGf is *derived* from dHf and
S0 against the CODATA element reference states rather than transcribed, so the
two halves of every entry are thermodynamically consistent with each other by
construction -- which is what makes the entropy a caller derives from the pair
the real one.

Each entry then had to survive two cross-checks against correlations that never
touched the formation tables:

    enthalpy:  dHf(g) - dHf(l)  ==  dHvap(298)
    Gibbs:     dGf(l) - dGf(g)  ==  R T ln(Psat(298) / P_std)

Agreement means three independent measurements line up; the tolerance is
3 kJ/mol on both. Of 102 candidate species, 83 gas and 59 liquid entries pass.
The checks are not decoration -- they caught two tabulated ideal-gas entropies
that are ~100 J/(mol K) below what atom-count additivity predicts (dimethyl
sulfoxide, morpholine), which would have been ~30 kJ/mol of silent error.

**Carboxylic acids are exempt from the checks, and that is the point.** They
fail the enthalpy relation by 18-28 kJ/mol *because* the relation assumes a
monomeric vapour. The tabulated liquid and gas values are each fine; it is the
route between them that does not apply. They are the species this table was
built for.

Everything excluded is listed at the bottom of this module with its residual,
so a species falling back to Joback + Psat is a recorded decision rather than a
gap. Sanity anchors: this table reproduces water at -237.15 kJ/mol against a
tabulated -237.14, 1-butanol(l) at -162.38 against -162.50, and ethyl
acetate(l) at -332.27 against -332.70.
"""

from __future__ import annotations

# Standard enthalpy and Gibbs energy of formation of the IDEAL GAS at 298.15 K,
# kJ/mol. Overlays Joback's estimate; the fully curated entries in
# ``thermochemistry._CURATED_RAW`` still take precedence over both.
IDEAL_GAS_FORMATION: dict[str, tuple[float, float]] = {
    # -- water
    "O": (-241.80, -228.55),                  # water
    # -- alcohols
    "CO": (-201.00, -162.31),                 # methanol
    "CCO": (-234.80, -167.87),                # ethanol
    "CCCO": (-255.10, -159.72),               # 1-propanol
    "CC(C)O": (-272.60, -173.22),             # 2-propanol
    "CCCCO": (-274.90, -150.58),              # 1-butanol
    "CCC(C)O": (-292.80, -167.75),            # 2-butanol
    "CC(C)CO": (-283.80, -155.91),            # 2-methyl-1-propanol
    "CC(C)(C)O": (-312.50, -177.67),          # 2-methyl-2-propanol
    "CCCCCO": (-294.60, -141.33),             # 1-pentanol
    "OC1CCCCC1": (-286.20, -117.07),          # cyclohexanol
    "C=CCO": (-124.50, -63.80),               # allyl alcohol
    "Oc1ccccc1": (-96.40, -32.50),            # phenol
    # -- carboxylic acids -- vapour dimerises, see the module docstring
    "O=CO": (-378.70, -351.01),               # formic acid
    "CC(=O)O": (-432.20, -374.21),            # acetic acid
    "CCC(=O)O": (-455.70, -369.60),           # propanoic acid
    "CCCC(=O)O": (-475.90, -357.36),          # butanoic acid
    "C=CC(=O)O": (-330.58, -278.08),          # acrylic acid
    "CC(O)C(=O)O": (-621.00, -516.00),        # lactic acid
    # -- esters
    "COC=O": (-357.40, -299.95),              # methyl formate
    "COC(C)=O": (-413.30, -326.83),           # methyl acetate
    "CCOC(C)=O": (-443.60, -327.89),          # ethyl acetate
    "CCCOC(C)=O": (-464.79, -320.39),         # propyl acetate
    "CC(=O)OC(C)C": (-481.60, -333.60),       # isopropyl acetate
    "CCCCOC(C)=O": (-485.30, -312.30),        # n-butyl acetate
    "CCC(=O)OC": (-427.50, -311.00),          # methyl propanoate
    "CCOC(=O)CC": (-463.40, -319.10),         # ethyl propanoate
    "COC(=O)c1ccccc1": (-287.90, -181.00),    # methyl benzoate
    "CCOC(=O)c1ccccc1": (-284.00, -148.00),   # ethyl benzoate
    "COC(=O)c1ccccc1O": (-464.30, -339.00),   # methyl salicylate
    # -- ketones and aldehydes
    "CC(C)=O": (-217.10, -152.54),            # acetone
    "CCC(C)=O": (-238.50, -146.56),           # 2-butanone
    "CCCC(C)=O": (-258.80, -137.80),          # 2-pentanone
    "O=C1CCCCC1": (-226.10, -90.48),          # cyclohexanone
    "CC(=O)c1ccccc1": (-86.70, 2.25),         # acetophenone
    "CCC=O": (-185.60, -123.78),              # propanal
    "CCCC=O": (-204.80, -114.00),             # butanal
    "O=Cc1ccccc1": (-36.70, 22.60),           # benzaldehyde
    "O=Cc1ccco1": (-151.00, -102.83),         # furfural
    # -- ethers
    "CCOCC": (-252.10, -122.04),              # diethyl ether
    "C1CCOC1": (-184.10, -80.98),             # tetrahydrofuran
    "COC(C)(C)C": (-283.70, -117.46),         # methyl tert-butyl ether
    "COc1ccccc1": (-67.90, 22.73),            # anisole
    "COCOC": (-348.50, -226.45),              # dimethoxymethane
    # -- halogenated
    "ClCCl": (-95.40, -68.78),                # dichloromethane
    "ClC(Cl)Cl": (-102.70, -69.90),           # chloroform
    "ClC(Cl)(Cl)Cl": (-97.59, -55.18),        # carbon tetrachloride
    "CCCl": (-112.10, -60.31),                # chloroethane
    "CCCCCl": (-154.40, -45.91),              # 1-chlorobutane
    "CCBr": (-61.90, -23.86),                 # bromoethane
    "CI": (14.40, 16.11),                     # iodomethane
    "CC(=O)Cl": (-242.80, -205.08),           # acetyl chloride
    # -- hydrocarbons
    "CCCCC": (-146.90, -8.27),                # pentane
    "CCCCCC": (-166.94, 0.14),                # hexane
    "CCCCCCC": (-187.34, 8.66),               # heptane
    "CCCCCCCC": (-208.22, 16.88),             # octane
    "C1CCCC1": (-76.40, 39.70),               # cyclopentane
    "C1CCCCC1": (-122.08, 33.06),             # cyclohexane
    "C=CCCCC": (-43.50, 86.10),               # 1-hexene
    "c1ccccc1": (82.90, 129.79),              # benzene
    "Cc1ccccc1": (50.41, 122.51),             # toluene
    "Cc1ccccc1C": (19.10, 122.18),            # o-xylene
    "Cc1cccc(C)c1": (17.30, 119.00),          # m-xylene
    "Cc1ccc(C)cc1": (18.00, 121.50),          # p-xylene
    "CCc1ccccc1": (29.90, 130.89),            # ethylbenzene
    "C=Cc1ccccc1": (147.90, 214.55),          # styrene
    # -- nitrogen
    "CC#N": (74.00, 91.86),                   # acetonitrile
    "Nc1ccccc1": (87.50, 167.92),             # aniline
    "c1ccncc1": (140.40, 190.70),             # pyridine
    "O=[N+]([O-])c1ccccc1": (68.50, 161.91),  # nitrobenzene
    "CCCN": (-70.10, 41.91),                  # propylamine
    "CCCCN": (-91.90, 49.10),                 # butylamine
    "CCNCC": (-72.20, 72.50),                 # diethylamine
    "CCN(CC)CC": (-92.70, 118.00),            # triethylamine
    "CN(C)C=O": (-192.40, -89.11),            # N,N-dimethylformamide
    "NC=O": (-193.90, -148.75),               # formamide
    "CC(N)=O": (-238.30, -163.20),            # acetamide
    # -- sulfur
    "CSC": (-37.40, 7.19),                    # dimethyl sulfide
    "CCS": (-46.10, -4.55),                   # ethanethiol
    "c1ccsc1": (114.90, 126.10),              # thiophene
    "S=C=S": (116.70, 66.62),                 # carbon disulfide
    # -- anhydrides
    "CCC(=O)OC(=O)CC": (-626.50, -470.00),    # propionic anhydride
}


# Standard enthalpy and Gibbs energy of formation of the PURE LIQUID at
# 298.15 K, kJ/mol -- the standard state a solution-phase reaction actually
# runs in. Consumed by ``standard_state.shift``.
LIQUID_FORMATION: dict[str, tuple[float, float]] = {
    # -- water
    "O": (-285.80, -237.13),                  # water
    # -- alcohols
    "CO": (-239.20, -166.79),                 # methanol
    "CCO": (-277.60, -174.62),                # ethanol
    "CCCO": (-302.60, -168.76),               # 1-propanol
    "CC(C)O": (-318.10, -180.53),             # 2-propanol
    "CCCCO": (-327.30, -162.38),              # 1-butanol
    "CCC(C)O": (-342.60, -174.43),            # 2-butanol
    "CC(C)CO": (-334.70, -166.47),            # 2-methyl-1-propanol
    "CC(C)(C)O": (-359.20, -184.59),          # 2-methyl-2-propanol
    "CCCCCO": (-351.60, -155.86),             # 1-pentanol
    "OC1CCCCC1": (-348.20, -134.35),          # cyclohexanol
    # -- carboxylic acids -- vapour dimerises, see the module docstring
    "O=CO": (-425.00, -361.62),               # formic acid
    "CC(=O)O": (-484.30, -389.43),            # acetic acid
    "CCC(=O)O": (-510.70, -384.46),           # propanoic acid
    "CCCC(=O)O": (-533.80, -376.19),          # butanoic acid
    # -- esters
    "CCOC(C)=O": (-479.30, -332.27),          # ethyl acetate
    # -- ketones and aldehydes
    "CC(C)=O": (-248.40, -155.37),            # acetone
    "CCC(C)=O": (-273.30, -151.31),           # 2-butanone
    "CCCC(C)=O": (-297.30, -144.86),          # 2-pentanone
    "O=C1CCCCC1": (-271.20, -103.82),         # cyclohexanone
    "CCC=O": (-215.60, -126.47),              # propanal
    "CCCC=O": (-239.20, -119.45),             # butanal
    "O=Cc1ccccc1": (-87.00, 6.50),            # benzaldehyde
    "O=Cc1ccco1": (-201.60, -118.95),         # furfural
    # -- ethers
    "CCOCC": (-279.50, -122.84),              # diethyl ether
    "C1CCOC1": (-216.20, -83.83),             # tetrahydrofuran
    "COC(C)(C)C": (-313.60, -119.79),         # methyl tert-butyl ether
    "COCOC": (-377.80, -228.40),              # dimethoxymethane
    # -- halogenated
    "ClCCl": (-124.20, -70.03),               # dichloromethane
    "ClC(Cl)Cl": (-134.10, -73.28),           # chloroform
    "ClC(Cl)(Cl)Cl": (-130.09, -59.66),       # carbon tetrachloride
    "CCBr": (-90.50, -26.22),                 # bromoethane
    "CI": (-13.60, 15.21),                    # iodomethane
    "CC(=O)Cl": (-272.90, -207.06),           # acetyl chloride
    # -- hydrocarbons
    "CCCCC": (-173.50, -9.71),                # pentane
    "CCCCCC": (-198.49, -3.29),               # hexane
    "CCCCCCC": (-223.91, 1.84),               # heptane
    "CCCCCCCC": (-249.73, 6.96),              # octane
    "C1CCCC1": (-105.10, 37.30),              # cyclopentane
    "C1CCCCC1": (-156.40, 26.71),             # cyclohexane
    "C=CCCCC": (-74.20, 81.83),               # 1-hexene
    "c1ccccc1": (49.10, 124.56),              # benzene
    "Cc1ccccc1": (12.36, 114.32),             # toluene
    "Cc1ccccc1C": (-24.40, 110.60),           # o-xylene
    "Cc1cccc(C)c1": (-25.40, 107.54),         # m-xylene
    "Cc1ccc(C)cc1": (-24.40, 110.42),         # p-xylene
    "CCc1ccccc1": (-12.30, 120.10),           # ethylbenzene
    "C=Cc1ccccc1": (103.80, 201.73),          # styrene
    # -- nitrogen
    "CC#N": (40.60, 86.43),                   # acetonitrile
    "Nc1ccccc1": (31.60, 149.76),             # aniline
    "c1ccncc1": (100.20, 181.13),             # pyridine
    "O=[N+]([O-])c1ccccc1": (12.50, 143.03),  # nitrobenzene
    "CCCN": (-101.50, 39.61),                 # propylamine
    # -- sulfur
    "CS(C)=O": (-204.20, -99.89),             # dimethyl sulfoxide
    "CSC": (-65.30, 6.01),                    # dimethyl sulfide
    "CCS": (-73.60, -5.45),                   # ethanethiol
    "c1ccsc1": (80.20, 120.50),               # thiophene
    "S=C=S": (89.00, 64.71),                  # carbon disulfide
}


# ---------------------------------------------------------------------------
# Excluded, with the residual that excluded them
# ---------------------------------------------------------------------------
# These species have tabulated data that FAILED a cross-check, so one of the
# three numbers involved is wrong and we cannot tell which. They keep the
# Joback + R T ln(Psat) route, which is what they had before. Listed rather
# than dropped silently, because a future session with a better source should
# start here.
#
#   gas    1,2-dichloroethane      Gibbs check -5.0 kJ/mol
#   gas    1,2-dimethoxyethane     enthalpy check -21.2 kJ/mol
#   gas    1,2-propylene glycol    enthalpy check +4.5 kJ/mol
#   gas    1,4-dioxane             Gibbs check -22.4 kJ/mol
#   gas    1-bromobutane           Gibbs check -16.4 kJ/mol
#   gas    1-octene                Gibbs check -3.5 kJ/mol
#   gas    N-methylaniline         enthalpy check -3.1 kJ/mol
#   gas    N-methylpyrrolidone     enthalpy check +11.7 kJ/mol
#   gas    acetaldehyde            Gibbs check +4.4 kJ/mol
#   gas    acetic anhydride        enthalpy check +3.4 kJ/mol
#   gas    benzyl alcohol          Gibbs check +4.4 kJ/mol
#   gas    chlorobenzene           Gibbs check +3.9 kJ/mol
#   gas    dimethyl sulfoxide      tabulated gas entropy is an additivity outlier
#   gas    ethyl acetoacetate      enthalpy check -3.1 kJ/mol
#   gas    ethyl formate           enthalpy check -16.9 kJ/mol
#   gas    ethylene glycol         Gibbs check -3.5 kJ/mol
#   gas    glycerol                Gibbs check +3.1 kJ/mol
#   gas    morpholine              tabulated gas entropy is an additivity outlier
#   gas    nitromethane            Gibbs check +8.8 kJ/mol
#   gas    piperidine              Gibbs check +6.5 kJ/mol
#   liquid 1,2-dichloroethane      Gibbs check -5.0 kJ/mol
#   liquid 1,4-dioxane             Gibbs check -22.4 kJ/mol
#   liquid 1-bromobutane           Gibbs check -16.4 kJ/mol
#   liquid 1-octene                Gibbs check -3.5 kJ/mol
#   liquid acetaldehyde            not a liquid at 298 K, Psat = 1.21 bar
#   liquid benzyl alcohol          Gibbs check +4.4 kJ/mol
#   liquid chlorobenzene           Gibbs check +3.9 kJ/mol
#   liquid chloroethane            not a liquid at 298 K, Psat = 1.60 bar
#   liquid ethylene glycol         Gibbs check -3.5 kJ/mol
#   liquid glycerol                Gibbs check +3.1 kJ/mol
#   liquid nitromethane            Gibbs check +8.8 kJ/mol
#   liquid piperidine              Gibbs check +6.5 kJ/mol


# ---------------------------------------------------------------------------
# The rest of the record, for species Joback cannot fragment at all
# ---------------------------------------------------------------------------
# The formation table above is an OVERLAY on a Joback record: it substitutes
# Hf/Gf and leaves Tb/Tc/Pc/Cp/Tm/Hfus alone. So for a species Joback cannot
# fragment -- an aryl aldehyde, a formamide, a sulfoxide, an anhydride, all of
# which it simply has no groups for -- there is nothing to overlay onto, and
# good measured formation data sits inert. Formic acid was the sharpest case:
# an ordinary bench reagent, in the electrolyte pKa table, with no
# thermochemistry at all.
#
# These entries supply the missing half, so the species becomes a fully curated
# record. Same sources, same package, same discipline as above.
#
# **Cp is FITTED, not transcribed.** The tabulated ideal-gas heat capacity is a
# correlation of a different functional form, so it is sampled over 273-600 K --
# a bench-realistic window, wide enough for a reflux and narrow enough that a
# cubic is not extrapolating -- and least-squares fitted to the a + bT + cT^2 +
# dT^3 form the rest of the codebase uses. That is the same move as
# ``volatility._estimate`` fitting Lee-Kesler to Antoine, for the same reason:
# one functional form reaches the kernel. Every residual is under 0.15%, and
# each is recorded next to its entry.
#
# Tm/Hfus are omitted where none is tabulated. That is not a gap being papered
# over -- ``vessel`` reads a missing Hfus as ``solidifies = False``, and both
# species it affects (methyl formate, propionic anhydride) melt below 180 K,
# so "never freezes" is the correct behaviour on any bench.
PHYSICAL_PROPERTIES: dict[str, dict] = {
    # N,N-dimethylformamide  (Cp fit residual 0.11%)
    "CN(C)C=O": dict(
        Cp_coeffs=(2.77, 0.2378, 0.0002532, -3.493e-07), Tb=425.95,
        Tc=649.60, Pc=44.00, Vc=262.0, Hvap=39.49, Tm=212.15, Hfus=7.90),
    # benzaldehyde  (Cp fit residual 0.06%)
    "O=Cc1ccccc1": dict(
        Cp_coeffs=(-9.078, 0.4323, -3.839e-05, -1.762e-07), Tb=451.85,
        Tc=695.00, Pc=47.00, Vc=318.0, Hvap=41.08, Tm=216.90, Hfus=9.32),
    # carbon disulfide  (Cp fit residual 0.01%)
    "S=C=S": dict(
        Cp_coeffs=(23.14, 0.1107, -0.0001407, 7.134e-08), Tb=319.35,
        Tc=552.00, Pc=79.03, Vc=160.0, Hvap=27.01, Tm=161.15, Hfus=4.39),
    # dimethyl sulfoxide  (Cp fit residual 0.11%)
    "CS(C)=O": dict(
        Cp_coeffs=(-15.44, 0.3103, 5.326e-05, -2.09e-07), Tb=465.05,
        Tc=707.00, Pc=46.00, Vc=213.0, Hvap=43.78, Tm=291.55, Hfus=14.37),
    # formamide  (Cp fit residual 0.07%)
    "NC=O": dict(
        Cp_coeffs=(14.79, 0.09531, 3.293e-05, -5.453e-08), Tb=490.15,
        Tc=771.00, Pc=78.00, Vc=125.0, Hvap=51.34, Tm=275.15, Hfus=8.44),
    # formic acid  (Cp fit residual 0.02%)
    "O=CO": dict(
        Cp_coeffs=(18.25, 0.09163, 1.279e-05, -3.749e-08), Tb=374.15,
        Tc=588.00, Pc=58.10, Vc=115.9, Hvap=22.07, Tm=281.45, Hfus=12.68),
    # furfural  (Cp fit residual 0.06%)
    "O=Cc1ccco1": dict(
        Cp_coeffs=(-9.421, 0.421, -0.0001887, -4.641e-08), Tb=434.65,
        Tc=670.00, Pc=55.10, Vc=252.0, Hvap=41.90, Tm=235.90, Hfus=14.37),
    # methyl formate  (Cp fit residual 0.02%)
    "COC=O": dict(
        Cp_coeffs=(19.67, 0.1535, 4.379e-05, -1.021e-07), Tb=304.75,
        Tc=487.20, Pc=60.00, Vc=172.0, Hvap=28.18, Tm=173.15),
    # propionic anhydride  (Cp fit residual 0.11%)
    "CCC(=O)OC(=O)CC": dict(
        Cp_coeffs=(-17.02, 0.4767, 0.0002577, -4.776e-07), Tb=441.15,
        Tc=625.54, Pc=28.34, Vc=420.0, Hvap=42.47, Tm=228.15),
}


# Gas-phase formation data DERIVED from the liquid entry, for a species whose
# tabulated ideal-gas entropy failed the additivity check and was excluded
# above. Uses the liquid value -- which is sound -- plus the two measured
# quantities the standard-state shift already runs on:
#
#     dHf(g) = dHf(l) + dHvap(298)
#     dGf(g) = dGf(l) - R T ln(Psat / P_std)
#
# For dimethyl sulfoxide the enthalpy half lands within 0.6 kJ/mol of the
# tabulated gas value, which is the check that the derivation is sound; it is
# only the entropy that was bad, and this route does not use it.
DERIVED_GAS_FORMATION: dict[str, tuple[float, float]] = {
    "CS(C)=O": (-150.72, -82.22),
}
