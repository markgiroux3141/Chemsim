"""Layer 1 -- Benson group assignment.

The scheme, not the numbers: ``benson`` deliberately estimates nothing yet (see
its docstring for why the parameter half is blocked). What is tested here is
that the groups come out as Benson defines them, that the scheme reaches the
functional classes Joback cannot, and that it refuses rather than guesses.
"""

import pytest

from chemsim.matter import Molecule
from chemsim.properties import benson
from chemsim.properties.joback import estimate


def g(smiles):
    return benson.assign(smiles)


# ---------------------------------------------------------------------------
# the groups are the conventional ones
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("smiles, expected", [
    ("CC", {"C-(C)(H)3": 2}),
    ("CCC", {"C-(C)(H)3": 2, "C-(C)2(H)2": 1}),
    ("CC(C)C", {"C-(C)(H)3": 3, "C-(C)3(H)": 1}),
    # ethanol: three groups for three heavy atoms, and note the carbon bonded to
    # oxygen is NOT the same group as the one bonded only to carbon
    ("CCO", {"C-(C)(H)3": 1, "C-(C)(H)2(O)": 1, "O-(C)(H)": 1}),
    # acetic acid: the carbonyl oxygen is folded into CO, not counted separately
    ("CC(=O)O", {"C-(CO)(H)3": 1, "CO-(C)(O)": 1, "O-(CO)(H)": 1}),
    ("CC(C)=O", {"C-(CO)(H)3": 2, "CO-(C)2": 1}),
    ("CC=O", {"C-(CO)(H)3": 1, "CO-(C)(H)": 1}),
    ("CC#N", {"C-(CN)(H)3": 1, "CN-(C)": 1}),
    ("CSC", {"C-(H)3(S)": 2, "S-(C)2": 1}),
    ("CS(C)=O", {"C-(H)3(SO)": 2, "SO-(C)2": 1}),
    ("C[N+](=O)[O-]", {"C-(H)3(NO2)": 1, "NO2-(C)": 1}),
    ("C=C", {"Cd-(Cd)(H)2": 2}),
])
def test_groups_match_bensons_own_notation(smiles, expected):
    assert g(smiles) == expected


def test_a_ring_gets_a_correction_term_per_ring():
    """Ring strain is not additive over atoms -- cyclopropane's carbons are
    ordinary CH2 groups plus a large correction no atom-local scheme can see."""
    assert g("C1CC1") == {"C-(C)2(H)2": 3, "ring3": 1}
    assert g("c1ccc2ccccc2c1")["ring6"] == 2      # naphthalene, two rings


def test_aromatics_are_typed_by_substitution():
    toluene = g("Cc1ccccc1")
    assert toluene["Cb-(Cb)2(H)"] == 5           # the unsubstituted ring carbons
    assert toluene["Cb-(C)(Cb)2"] == 1           # the one bearing the methyl
    assert toluene["C-(Cb)(H)3"] == 1            # and the methyl itself
    assert toluene["ring6"] == 1


def test_every_polyvalent_heavy_atom_contributes_exactly_one_group():
    """The property that makes this unambiguous, and the reason it is not a
    SMARTS table: there is nothing to arbitrate. Terminal oxo oxygens and
    halogens are ligands, so they are the only heavy atoms without a group."""
    for smiles in ("CCOC(C)=O", "O=Cc1ccccc1", "CN(C)C=O", "CCCl", "CC(=O)O"):
        mol = Molecule.from_smiles(smiles)
        atoms = mol.topology()
        ligand_only = sum(
            1 for a in atoms
            if a.element in benson.HALOGENS or benson._is_terminal_oxo(a, atoms)
        )
        groups = benson.assign(mol)
        n_groups = sum(v for k, v in groups.items() if not k.startswith("ring"))
        assert n_groups == mol.n_heavy_atoms - ligand_only, smiles


# ---------------------------------------------------------------------------
# the two Joback defects, structurally
# ---------------------------------------------------------------------------


def test_homologues_cannot_collapse_onto_each_other():
    """Joback's additive fragments make the CH3 -> C2H5 difference cancel
    EXACTLY between an alcohol and the ester it makes, so it gives methanol and
    ethanol esterification an identical gas-phase dG. Benson groups are defined
    by their ligands, so the two alcohols do not even share a carbon group --
    the collapse is impossible by construction rather than merely unlikely."""
    assert g("CO") == {"C-(H)3(O)": 1, "O-(C)(H)": 1}
    assert "C-(H)3(O)" not in g("CCO")
    assert g("COC(C)=O") != g("CCOC(C)=O")


JOBACK_CANNOT = [
    "O=Cc1ccccc1",      # benzaldehyde -- aryl aldehyde
    "O=CO",             # formic acid
    "CS(C)=O",          # dimethyl sulfoxide
    "CS(=O)(=O)C",      # dimethyl sulfone
    "CN(C)C=O",         # DMF -- formamide
    "NC=O",             # formamide
    "CC(=O)OC(C)=O",    # acetic anhydride
    "O=Cc1ccco1",       # furfural
]


@pytest.mark.parametrize("smiles", JOBACK_CANNOT)
def test_the_scheme_reaches_classes_joback_has_no_groups_for(smiles):
    mol = Molecule.from_smiles(smiles)
    with pytest.raises(Exception):
        estimate(mol)                    # Joback has nothing for these
    assert benson.assign(mol), smiles    # Benson types every atom


def test_coverage_is_a_strict_superset_of_jobacks():
    """The claim worth pinning: adopting this scheme cannot LOSE a species.
    If that ever stops being true, the assignment has a gap Joback covers."""
    targets = [
        "CC(=O)O", "CCO", "CCOC(C)=O", "O=Cc1ccccc1", "CS(C)=O", "CN(C)C=O",
        "NC=O", "O=CO", "CC(=O)OC(C)=O", "CS(=O)(=O)C", "c1ccc2ccccc2c1",
        "OC(=O)c1ccccc1", "CC(N)=O", "c1ccncc1", "O=Cc1ccco1", "CC#N",
        "C[N+](=O)[O-]", "ClC(Cl)Cl", "CCOCC", "NC(N)=O", "OCC(O)CO",
        "CC(=O)Nc1ccccc1", "COc1ccccc1", "CSCC", "O=C1CCCCC1", "CCCCO",
    ]
    joback_only = []
    for smi in targets:
        mol = Molecule.from_smiles(smi)
        try:
            estimate(mol)
            joback = True
        except Exception:
            joback = False
        if joback and not benson.can_assign(mol):
            joback_only.append(smi)

    assert joback_only == [], f"Benson lost species Joback can do: {joback_only}"
    assert all(benson.can_assign(s) for s in targets)


# ---------------------------------------------------------------------------
# refusing rather than guessing
# ---------------------------------------------------------------------------


def test_an_untypable_element_is_refused_loudly():
    """The lesson from Joback returning a confident -74.8 kJ/mol for Cl2, whose
    true value is 0 by definition: a silent wrong answer is worse than a loud
    failure. Phosphorus has no groups here, so it must raise."""
    with pytest.raises(benson.BensonError, match="P"):
        benson.assign("OP(=O)(O)O")
    assert not benson.can_assign("OP(=O)(O)O")


# ---------------------------------------------------------------------------
# the estimate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("smiles, Hf, Gf", [
    # measured ideal-gas values, kJ/mol
    ("c1ccccc1", 82.9, 129.7),          # benzene: 6 Cb groups, no ring correction
    ("Cc1ccccc1", 50.4, 122.5),         # toluene
    ("C1CCCCC1", -123.1, 31.8),         # cyclohexane: ring correction ~0
    ("CC(C)=O", -217.1, -152.5),        # acetone
    ("CCCCC", -146.9, -8.3),            # pentane
    ("CC(=O)O", -432.2, -374.2),        # acetic acid
])
def test_the_estimate_lands_near_measured_values(smiles, Hf, Gf):
    e = benson.estimate(smiles)
    assert e.Hf == pytest.approx(Hf, abs=8.0), f"{smiles} Hf"
    assert e.Gf == pytest.approx(Gf, abs=8.0), f"{smiles} Gf"


def test_benzene_needs_no_ring_correction_and_that_is_the_check():
    """Six Cb groups reproduce benzene's formation enthalpy to under a kJ/mol,
    with a ring correction of exactly zero. That is not luck -- the aromatic
    group value already carries the resonance stabilisation -- and it is the
    cleanest available confirmation that the group values and the ring table are
    on the same footing."""
    assert benson.RING_CORRECTIONS["benzene"][0] == 0.0
    assert benson.estimate("c1ccccc1").Hf == pytest.approx(82.9, abs=1.0)


@pytest.mark.parametrize("smiles, sigma", [
    ("CC", 18),                 # ethane: 2 methyl rotors x mutual swap
    ("CCO", 3),                 # ethanol: one methyl
    ("c1ccccc1", 12),           # benzene
    ("Cc1ccccc1", 6),           # toluene: ring C2 x methyl
    ("CC(C)=O", 18),            # acetone
])
def test_symmetry_numbers_are_right(smiles, sigma):
    """Group additivity gives INTRINSIC entropy, so -R ln(sigma) is owed and is
    not optional: benzene would be out by R ln 12 = 20.7 J/(mol K), which is
    6 kJ/mol in dGf. Hydrogens are excluded from the automorphism count on
    purpose -- with them a methyl contributes 3! where only 3 rotations are
    physical, making ethane 72 instead of 18."""
    assert benson.symmetry_number(smiles) == sigma


def test_dropping_the_symmetry_correction_would_be_visible():
    """The correction is worth asserting rather than trusting, because omitting
    it is silent on anything unsymmetric and only shows up on molecules like
    benzene -- exactly the ones a quick test would skip."""
    import math

    from chemsim.constants import R
    e = benson.estimate("c1ccccc1")
    uncorrected = e.S + R * math.log(e.sigma)
    assert uncorrected - e.S == pytest.approx(20.7, abs=0.5)
    assert e.S == pytest.approx(269.2, abs=3.0)     # measured benzene S(g)


def test_an_unnamed_ring_refuses_the_whole_estimate():
    """A missing ring correction is up to 115 kJ/mol of silent error, so a ring
    the scheme cannot name must refuse rather than omit it. Cyclononane is the
    clean case: every group it needs exists (it is nine ordinary CH2 groups), so
    the ring correction is the only thing missing."""
    assert benson.can_assign("C1CCCCCCCC1")
    assert benson.assign("C1CCCCCCCC1") == {"C-(C)2(H)2": 9, "ring9": 1}
    with pytest.raises(benson.BensonError, match="no strain correction"):
        benson.estimate("C1CCCCCCCC1")


def test_pyridine_refuses_because_rmg_has_no_aromatic_nitrogen_at_all():
    """Worth pinning as a known gap rather than leaving it looking like a bug.
    Heteroaromatics are priced on their KEKULE structure, and RMG's group table
    has no nitrogen entry for the localised ring -- nor a pyridine ring correction
    -- so there is nothing to fall back on but Joback."""
    groups = benson.assign("c1ccncc1")
    assert "Nd-(Cd)2" in groups, "pyridine must be typed from the Kekule view"
    assert "Nb-(Cb)2" not in groups
    with pytest.raises(benson.BensonError, match="Nd-\\(Cd\\)2"):
        benson.estimate("c1ccncc1")


def test_aromatic_esters_refuse_because_two_tabulations_cannot_be_mixed():
    """The sharpest lesson of the data pipeline, and the group-level form of a
    rule this project already had: RMG carries Benson's aryl-ester carbonyl and
    Paraskevas's CBS-QB3 ester oxygen, whose SUMS agree to 3 kJ/mol and whose
    SPLITS differ by 78. Combining them put methyl benzoate 70 kJ/mol out --
    worse than the estimator Benson is meant to improve on -- so the key is
    dropped and aromatic esters keep Joback."""
    from chemsim.properties.benson_data import GROUP_VALUES

    assert "CO-(C)(O)" in GROUP_VALUES        # the aliphatic ester still works
    assert "CO-(Cb)(O)" not in GROUP_VALUES
    with pytest.raises(benson.BensonError, match="CO-\\(Cb\\)\\(O\\)"):
        benson.estimate("COC(=O)c1ccccc1")


# ---------------------------------------------------------------------------
# heteroaromatics, and the two conventions RMG's values live on
# ---------------------------------------------------------------------------


def test_a_heteroaromatic_is_priced_on_its_kekule_structure():
    """Benzene rings are priced with delocalised ``Cb`` groups and a ring
    correction of exactly zero; every other aromatic ring is priced with
    LOCALISED groups plus a large correction that is what makes the aromaticity
    appear. RMG has no aromatic-oxygen group at all, so furan used to refuse for
    want of ``Ob-(Cb)2`` while its -26.4 kJ/mol ring correction sat unused."""
    groups = benson.assign("c1ccoc1")
    assert groups == {"Cd-(Cd)(H)(O)": 2, "Cd-(Cd)2(H)": 2, "O-(Cd)2": 1, "ring5": 1}
    assert benson.ring_key(
        Molecule.from_smiles("c1ccoc1"),
        Molecule.from_smiles("c1ccoc1").ring_atom_indices()[0],
    ) == "furan"
    # measured furan Hf(g) = -34.8 kJ/mol
    assert benson.estimate("c1ccoc1").Hf == pytest.approx(-34.8, abs=2.0)


def test_benzene_still_takes_the_delocalised_route_and_has_not_moved():
    """The invariant that guards the convention split: if a benzene ring ever
    started being kekulized, its groups would change and the zero ring correction
    would no longer apply."""
    assert benson.assign("c1ccccc1") == {"Cb-(Cb)2(H)": 6, "ring6": 1}
    assert benson.RING_CORRECTIONS["benzene"][0] == 0.0
    assert benson.estimate("c1ccccc1").Hf == pytest.approx(82.9, abs=1.0)


def test_a_fused_aromatic_carbon_is_its_own_group():
    """Naphthalene's two shared carbons have three aromatic neighbours where an
    ordinary benzenoid carbon has two plus a substituent, and Benson prices them
    separately. Their NEIGHBOURS still name them ``Cb`` -- that is Benson's own
    convention and RMG's, and departing from it asks for keys like
    ``Cb-(Cb)(Cbf)(H)`` that no tabulation has."""
    groups = benson.assign("c1ccc2ccccc2c1")
    assert groups["Cbf-(Cb)2(Cbf)"] == 2
    assert groups["Cb-(Cb)2(H)"] == 8
    assert groups["ring6"] == 2
    assert benson.can_estimate("c1ccc2ccccc2c1")


def test_rings_are_named_by_cyclic_sequence_not_by_an_element_tally():
    """1,3-dioxane and 1,4-dioxane have the same size, the same elements and the
    same bonds; only the ORDER differs, and their ring corrections differ by
    6.4 kJ/mol. A tally-based scheme has to refuse both or silently pick one."""
    def name(smiles):
        mol = Molecule.from_smiles(smiles)
        return benson.ring_key(mol, mol.ring_atom_indices()[0])

    assert name("C1COCOC1") == "13dioxane"
    assert name("C1COCCO1") == "14dioxane"
    assert name("C1=CC=CCC1") == "13cyclohexadiene"
    assert name("C1=CCC=CC1") == "14cyclohexadiene"
    assert (
        benson.RING_CORRECTIONS["13dioxane"][0]
        != benson.RING_CORRECTIONS["14dioxane"][0]
    )
    # And the exemplar table is checked for collisions at import, so two rings
    # cannot quietly share a signature.
    assert len(benson.RING_SIGNATURES) == len(benson._RING_EXEMPLARS)


def test_species_too_small_for_group_additivity_are_refused():
    """A group is an atom plus its ligands, which says nothing about a two-atom
    molecule -- and the symmetry model is wrong there too (methane reads 1
    against a true 12). These are curated instead."""
    for smiles in ("CO", "O", "CI"):
        with pytest.raises(benson.BensonError, match="heavy atoms"):
            benson.estimate(smiles)


# ---------------------------------------------------------------------------
# non-nearest-neighbour corrections
# ---------------------------------------------------------------------------


def test_branching_corrections_fix_what_a_first_order_scheme_cannot_see():
    """Two crowded sp3 centres interact, and no amount of group refinement can
    express it -- the groups are identical whether the branches are adjacent or
    at opposite ends of the chain. Measured on 2,2,3,3-tetramethylbutane, whose
    reference Hf(g) is -226.0 kJ/mol."""
    plain = benson.estimate("CC(C)(C)C(C)(C)C", nn=False)
    full = benson.estimate("CC(C)(C)C(C)(C)C", nn=True)
    assert full.nn_corrections == {"nn13_CsQ_CsQ": 1}
    assert abs(plain.Hf - (-226.0)) > 20.0        # first order is 25.9 out
    assert abs(full.Hf - (-226.0)) < 8.0          # corrected is 5.8


def test_a_straight_chain_takes_no_branching_correction():
    """The control. A term that fired on n-hexane would be double-counting the
    ordinary CH2 group."""
    assert benson.corrections("CCCCCC") == {}
    assert benson.estimate("CCCCCC", nn=False).Hf == benson.estimate("CCCCCC").Hf


def test_symmetric_corrections_are_doubled_out_of_rmgs_half_value():
    """RMG's matcher tries both assignments of its two labelled atoms, so it
    stores a symmetric interaction at HALF value -- announced only in prose. We
    count each unordered pair once, so those entries must be doubled. Miss it and
    every symmetric case is exactly half-corrected, which looks like scatter."""
    rec = benson.CORRECTIONS["nn13_CsQ_CsQ"]
    assert "doubled" in rec[3]
    # 3.2 kcal/mol stored as 2.4 -> 10.04 kJ/mol, doubled to 20.08
    assert rec[0] == pytest.approx(20.08, abs=0.1)
    assert "doubled" not in benson.CORRECTIONS["nn13_CsQ_CsT"][3]


def test_a_missing_correction_is_zero_rather_than_a_refusal():
    """The opposite of the rule for groups and rings, deliberately. A correction
    refines a complete estimate; a missing group or ring correction means the
    estimate is INCOMPLETE. Refusing on a missing interaction term would refuse
    nearly every molecule -- m-xylene has no meta CH3/CH3 value, and must still
    be priced."""
    assert "m_CH3_CH3" not in benson.CORRECTIONS
    assert benson.can_estimate("Cc1cccc(C)c1")


def test_the_aromatic_interactions_are_extracted_but_withheld():
    """They are real chemistry on the wrong basis: Ince & Reyniers regressed them
    together with their own group values, and against RMG's Benson-basis Cb groups
    they make things worse -- mean |Hf| error over eleven disubstituted benzenes
    6.66 -> 9.75 kJ/mol, with salicylaldehyde going 6.0 -> 33.4 because the ortho
    OH/CHO term double-counts a hydrogen bond the Cb values already partly carry.
    Kept in a separate table so the rejection stays measurable rather than becoming
    a deleted branch. ``validation/benson_accuracy.py`` re-measures it."""
    from chemsim.properties.benson_data import AROMATIC_INTERACTIONS

    assert AROMATIC_INTERACTIONS, "the table must still be extracted"
    assert not any(k[:2] in ("o_", "m_", "p_") for k in benson.CORRECTIONS)

    # The recognition is live either way -- only the values are withheld.
    assert benson.corrections("O=Cc1ccccc1O") == {}
    assert benson.corrections("O=Cc1ccccc1O", AROMATIC_INTERACTIONS) == {
        "o_CHO_OH": 1
    }
    # And salicylaldehyde is better off without it.
    ref = -214.95
    plain = benson.estimate("O=Cc1ccccc1O").Hf
    withheld = AROMATIC_INTERACTIONS["o_CHO_OH"][0]
    assert abs(plain - ref) < abs(plain + withheld - ref)


def test_the_estimate_reports_the_provenance_of_every_group_it_used():
    """Several RMG values are later CBS-QB3 refits rather than Benson's own
    numbers, and a caller must be able to tell which."""
    e = benson.estimate("CCOC(C)=O")
    assert len(e.sources) == len([k for k in e.groups if not k.startswith("ring")])
    assert any("BENSON" in s.upper() for s in e.sources)
