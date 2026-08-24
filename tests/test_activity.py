"""Activity coefficients: the parameter table, the kernel, and what they buy.

Four groups, in increasing order of how much chemistry they assert:

  * **data** -- every R, Q and a_mn cross-checked against the `thermo` oracle, the
    same discipline the Joback table gets. Transcription errors here are silent
    and catastrophic, so none of it is trusted.
  * **fragmentation** -- our group assignments against the published ones. This
    is where the SMARTS corrections in ``unifac_data`` earn their place.
  * **kernel** -- our UNIFAC evaluation against `thermo`'s, plus the limits the
    model has to satisfy by construction (a pure liquid is ideal; an unmodelled
    species is ideal and says so).
  * **emergence** -- the two things this was built for. An azeotrope that nothing
    in the code knows about, and a solubility that stops being 300x wrong.
"""

import numpy as np
import pytest

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.numerics.activity import activity_coefficients
from chemsim.properties import (
    UnifacProvider,
    Volatility,
    VolatilityProvider,
    build_activity_arrays,
)
from chemsim.properties import fragmentation, joback
from chemsim.properties import psrk_data as psrk
from chemsim.properties import unifac as uf
from chemsim.properties import unifac_data as ud
from chemsim.properties.volatility import NONVOLATILE_A
from chemsim.vessel import Vessel

thermo_lib = pytest.importorskip("thermo", reason="thermo oracle not installed")
import thermo.unifac as tu  # noqa: E402

tu.load_unifac_ip()

ETHANOL, WATER = "CCO", "O"
BENZOIC = Molecule.from_smiles("OC(=O)c1ccccc1").smiles


@pytest.fixture(scope="module")
def unifac():
    return UnifacProvider()


# ==========================================================================
# the parameter table, against the oracle
# ==========================================================================


def test_every_subgroup_matches_the_oracle():
    assert len(ud.GROUPS) == len(tu.UFSG)
    for g in ud.GROUPS:
        ref = tu.UFSG[g.group_id]
        assert g.name == ref.group
        assert g.main_group_id == ref.main_group_id
        assert g.R == pytest.approx(ref.R, rel=1e-12)
        assert g.Q == pytest.approx(ref.Q, rel=1e-12)
        assert g.atoms == ref.atoms


def test_every_interaction_parameter_matches_the_oracle():
    reference = {
        (m, n): v for m, table in tu.UFIP.items() for n, v in table.items()
    }
    assert ud.INTERACTIONS == pytest.approx(reference, rel=1e-12)


def test_the_interaction_matrix_is_sparse_and_asymmetric():
    """Two properties the assembly code has to respect. Roughly half the pairs
    have never been regressed, and a_mn != a_nm -- treating either as otherwise
    would quietly turn 'unknown' into 'athermal'."""
    ids = sorted(ud.MAIN_GROUPS)
    pairs = [(m, n) for m in ids for n in ids if m != n]
    known = [p for p in pairs if p in ud.INTERACTIONS]
    assert 0.3 < len(known) / len(pairs) < 0.7, "expected a genuinely sparse table"

    asymmetric = [
        (m, n) for (m, n) in known
        if (n, m) in ud.INTERACTIONS and ud.INTERACTIONS[(m, n)] != ud.INTERACTIONS[(n, m)]
    ]
    assert asymmetric, "a_mn must not be symmetric"
    assert ud.INTERACTIONS[(1, 7)] != ud.INTERACTIONS[(7, 1)]   # CH2 <-> H2O


def test_only_the_documented_patterns_differ_from_the_oracle():
    """Our SMARTS are the oracle's except where the module says otherwise. This
    stops a correction being slipped in without being written down."""
    differing = set()
    for g in ud.GROUPS:
        ref = tu.UFSG[g.group_id]
        ref_smarts = (ref.smarts,) if isinstance(ref.smarts, str) else tuple(ref.smarts)
        if g.smarts != ref_smarts or g.priority != ref.priority:
            differing.add(g.group_id)
    assert differing == set(ud.CORRECTED_GROUP_IDS)


# --------------------------------------------------------------------------
# the PSRK gas extension
# --------------------------------------------------------------------------


def test_every_extension_subgroup_matches_the_psrk_oracle():
    for g in psrk.GROUPS:
        ref = tu.PSRKSG[psrk.PSRK_ID[g.group_id]]
        assert g.name == ref.group
        assert g.main_group_id - psrk.ID_OFFSET == ref.main_group_id
        assert g.R == pytest.approx(ref.R, rel=1e-12)
        assert g.Q == pytest.approx(ref.Q, rel=1e-12)


def test_every_extension_interaction_matches_the_psrk_oracle():
    for (m, n), value in psrk.INTERACTIONS.items():
        mm = m - psrk.ID_OFFSET if m > psrk.ID_OFFSET else m
        nn = n - psrk.ID_OFFSET if n > psrk.ID_OFFSET else n
        assert value == pytest.approx(tu.PSRKIP[mm][nn], rel=1e-12)


def test_the_extension_never_overwrites_a_unifac_parameter():
    """The whole basis for merging two regressions: the extension supplies only
    main groups UNIFAC does not have. If that ever stopped being true, some
    validated result would move for reasons nobody chose."""
    unifac_main = {g.main_group_id for g in ud.GROUPS}
    extension_main = {g.main_group_id for g in psrk.GROUPS}
    assert not (unifac_main & extension_main)
    assert not (set(ud.GROUPS_BY_ID) & set(psrk.GROUPS_BY_ID))

    for pair in psrk.INTERACTIONS:
        assert pair not in ud.INTERACTIONS
    for pair in psrk.INTERACTIONS:
        assert any(m > psrk.ID_OFFSET for m in pair), "must involve a gas group"


def test_interactions_are_quadratic_in_temperature():
    """UNIFAC's parameters are constant; PSRK's gas parameters are genuinely not,
    and flattening them to their constant term would be wrong rather than
    approximate."""
    assert uf.interaction(1, 5) == (986.5, 0.0, 0.0)          # CH2/OH, UNIFAC
    o2 = 58 + psrk.ID_OFFSET
    a, b, c = uf.interaction(o2, 7)                            # O2/H2O, PSRK
    assert (b, c) != (0.0, 0.0)

    arrays = build_activity_arrays(["O=O", "O"], UnifacProvider())
    assert arrays.a_mn.shape[-1] == 3
    assert np.any(arrays.a_mn[:, :, 1])


def test_the_hydrogen_pattern_does_not_eat_every_hydroxyl(unifac):
    """The published H2 pattern is '[HH]', which RDKit reads as a hydrogen-COUNT
    primitive -- so it matches any atom with one H, at priority 1e9. With it in
    the table ethanol fragments as CH3 + CH2 + H2. Regression guard for the
    correction, because the failure is silent for anything whose formula happens
    to still balance."""
    assert unifac.get("[H][H]").named() == {"H2": 1}
    assert unifac.get("CCO").named() == {"CH3": 1, "CH2": 1, "OH": 1}
    assert unifac.get("Oc1ccccc1").named() == {"ACH": 5, "ACOH": 1}


@pytest.mark.parametrize(
    "smiles,expected",
    [
        ("O=O", {"O2": 1}),
        ("N#N", {"N2": 1}),
        ("O=C=O", {"CO2": 1}),
        ("[C-]#[O+]", {"CO": 1}),
        ("[H][H]", {"H2": 1}),
        ("C", {"CH4": 1}),
        ("ClCl", {"CL2": 1}),
        ("O=S=O", {"SO2": 1}),
    ],
)
def test_the_gases_fragment(unifac, smiles, expected):
    assert unifac.get(smiles).named() == expected


# ==========================================================================
# fragmentation, against published group assignments
# ==========================================================================

# Published UNIFAC decompositions (Poling/DDBST), by group NAME so the
# expectation is readable as chemistry rather than as subgroup ids.
PUBLISHED = {
    "O": {"H2O": 1},
    "CO": {"CH3OH": 1},
    "CCO": {"CH3": 1, "CH2": 1, "OH": 1},
    "CCCCO": {"CH3": 1, "CH2": 3, "OH": 1},
    "CC(C)O": {"CH3": 2, "CH": 1, "OH": 1},
    "CC(=O)O": {"CH3": 1, "COOH": 1},
    "OC=O": {"HCOOH": 1},
    "OC(=O)CCC(=O)O": {"CH2": 2, "COOH": 2},
    "CCOC(C)=O": {"CH3": 1, "CH2": 1, "CH3COO": 1},
    "CC(C)=O": {"CH3": 1, "CH3CO": 1},
    "CCOCC": {"CH3": 2, "CH2": 1, "CH2O": 1},
    "C1CCOC1": {"CH2": 3, "THF": 1},
    "c1ccccc1": {"ACH": 6},
    "Cc1ccccc1": {"ACH": 5, "ACCH3": 1},
    "Oc1ccccc1": {"ACH": 5, "ACOH": 1},
    "Nc1ccccc1": {"ACH": 5, "ACNH2": 1},
    "COc1ccccc1": {"ACH": 5, "AC": 1, "CH3O": 1},
    "OC(=O)c1ccccc1": {"ACH": 5, "AC": 1, "COOH": 1},
    "O=Cc1ccccc1": {"ACH": 5, "AC": 1, "CHO": 1},
    "CCCCCC": {"CH3": 2, "CH2": 4},
    "C1CCCCC1": {"CH2": 6},
    "CC#N": {"CH3CN": 1},
    "CCN": {"CH3": 1, "CH2NH2": 1},
    "ClC(Cl)Cl": {"CHCL3": 1},
    "OCCO": {"DOH": 1},
    "CN(C)C=O": {"DMF": 1},
    "CS(C)=O": {"DMSO": 1},
}


@pytest.mark.parametrize("smiles,expected", sorted(PUBLISHED.items()))
def test_fragmentation_matches_the_published_assignment(unifac, smiles, expected):
    assert unifac.get(smiles).named() == expected


def test_an_alcohol_is_not_claimed_by_the_ether_group(unifac):
    """The specific failure the SMARTS corrections exist for. The conventional
    CH2O pattern is '[CH2][O]', which matches ethanol's -CH2-OH and drops a
    hydrogen; without the correction ethanol fragments as CH3 + CH2O."""
    assert unifac.get("CCO").named() == {"CH3": 1, "CH2": 1, "OH": 1}
    assert unifac.get("CCOCC").named() == {"CH3": 2, "CH2": 1, "CH2O": 1}


def test_an_acid_is_not_claimed_by_the_ester_group(unifac):
    assert unifac.get("CC(=O)O").named() == {"CH3": 1, "COOH": 1}
    assert unifac.get("CCOC(C)=O").named() == {"CH3": 1, "CH2": 1, "CH3COO": 1}


def test_a_KETONE_group_does_not_claim_an_ALDEHYDE(unifac):
    """The correction that cost a whole homologous series to find.

    ``CH3CO`` is published as a ketone subgroup but its conventional pattern,
    ``[CX4;H3][CX3](=O)``, leaves the carbonyl carbon unconstrained -- so it
    matches ethanal's CH3-CHO as readily as acetone's CH3-CO-, wins the greedy
    pass by being the larger match, and strands the aldehyde hydrogen. The
    formula check then refused the molecule, which is it working: a wrong
    decomposition became a refusal rather than a wrong gamma. Every aliphatic
    aldehyde from ethanal to dodecanal failed this way.

    A ketone carbonyl carbon bears no hydrogen -- that is what makes it a ketone
    rather than an aldehyde, which has its own subgroup -- so ``;H0`` states the
    published definition instead of tightening it. The ketones must therefore be
    untouched by it, and the pair of assertions is the test."""
    assert unifac.get("CC=O").named() == {"CH3": 1, "CHO": 1}
    assert unifac.get("CCCCCC=O").named() == {"CH3": 1, "CH2": 4, "CHO": 1}
    assert unifac.get("O=CCCCC=O").named() == {"CH2": 3, "CHO": 2}
    # ... and the groups the correction is ABOUT keep their own molecules.
    assert unifac.get("CC(C)=O").named() == {"CH3": 1, "CH3CO": 1}
    assert unifac.get("CCC(C)=O").named() == {"CH3": 1, "CH2": 1, "CH3CO": 1}
    assert unifac.get("CC(=O)CC(C)=O").named() == {"CH2": 1, "CH3CO": 2}


# --------------------------------------------------------------------------
# the fallback search
# --------------------------------------------------------------------------
# ⚠ Priority says which group is PREFERRED, not which is POSSIBLE. A greedy pass
# can therefore eat an atom that the only workable cover needed elsewhere, and
# refuse a molecule the table does in fact cover. The fallback is a depth-first
# search over covers, bounded by the atom tally -- and the property that makes
# it safe is not what it finds but WHEN IT RUNS.

FRAGMENTS_GREEDILY = sorted(PUBLISHED) + [
    "CCO", "CC(=O)O", "CCOC(C)=O", "CC(C)=O", "CC=O", "OCC(O)CO",
    "OC(=O)c1ccccc1", "ClCCl", "C1CCOC1", "CCCCCCCC",
]


def _disable_search(monkeypatch):
    """Leave the greedy pass exactly as it is and take the fallback away."""
    monkeypatch.setattr(fragmentation, "_search", lambda *a, **k: (None, True))


def test_the_search_recovers_a_molecule_greedy_stranded(unifac, monkeypatch):
    """Benzyl chloride: the aromatic groups take the ring carbon CH2CL's own
    pattern needed, and greedy then has nowhere to put the CH2Cl."""
    assert unifac.get("ClCc1ccccc1").named() == {"ACH": 5, "AC": 1, "CH2CL": 1}
    _disable_search(monkeypatch)
    assert not uf.UnifacProvider().get("ClCc1ccccc1").modelled


def test_the_search_NEVER_overrules_an_answer_greedy_already_had(monkeypatch):
    """⚠ THE SAFETY PROPERTY, and it is an ordering rather than a result.

    The search runs only after the greedy pass has been REFUSED, so for any
    molecule that fragments today it is unreachable. What it can turn into an
    answer is a refusal; what it can never do is turn one answer into another --
    which is what lets it sit in a matcher Joback also uses without the rest of
    the project having to be re-validated."""
    both = uf.UnifacProvider()
    with_search = {s: both.get(s) for s in FRAGMENTS_GREEDILY}   # evaluated FIRST

    _disable_search(monkeypatch)
    greedy_only = uf.UnifacProvider()
    for smiles in FRAGMENTS_GREEDILY:
        greedy = greedy_only.get(smiles)
        assert greedy.modelled, f"{smiles} needs the search, so it proves nothing"
        assert with_search[smiles].counts == greedy.counts, smiles


def test_joback_is_unmoved_by_a_search_it_shares(monkeypatch):
    """The same claim for the other method that goes through this matcher. The
    catalog-wide measurement is in ``validation/unifac_gap.py`` -- 1057 species,
    zero gained and zero changed -- and this is the standing cheap guard."""
    molecules = [
        Molecule.from_smiles(s) for s in
        ("CCO", "CC(=O)O", "CCOC(C)=O", "CC(C)=O", "CC=O", "Cc1ccccc1",
         "OC(=O)c1ccccc1", "CCCCCC", "ClCc1ccccc1")
    ]
    with_search = [joback.fragment(m) for m in molecules]
    _disable_search(monkeypatch)
    assert [joback.fragment(m) for m in molecules] == with_search


def test_an_unsearchable_molecule_still_refuses_with_the_GREEDY_diagnostic(unifac):
    """A refusal has to name what went wrong with the decomposition the table
    PREFERS -- that is the half a reader can act on. The search's own outcome is
    appended to it rather than substituted for it."""
    groups = unifac.get("OP(=O)(O)O")
    assert not groups.modelled
    assert "incomplete UNIFAC fragmentation" in groups.source
    assert "no other assignment of these patterns covers it" in groups.source


def test_a_search_that_runs_out_of_budget_says_so_rather_than_claiming_absence(
    monkeypatch,
):
    """⚠ "I DID NOT FIND A COVER" IS NOT "THERE IS NO COVER". A refusal that ran
    the two together would be this project quietly telling itself the published
    table is smaller than it is, so the two messages are different."""
    monkeypatch.setattr(fragmentation, "SEARCH_NODE_LIMIT", 1)
    groups = uf.UnifacProvider().get("ClCc1ccccc1")
    assert not groups.modelled
    assert "budget" in groups.source
    assert "rather than a statement that no decomposition exists" in groups.source


def test_a_molecule_outside_the_table_is_reported_not_guessed(unifac):
    """Group contribution is most dangerous when it succeeds on something it
    does not cover, so incomplete coverage must be a stated fact."""
    # The table covers C/N/O/S/halogens/Si and, through the PSRK extension, the
    # permanent gases -- but nothing with phosphorus or boron in it.
    for smiles in ("OP(=O)(O)O", "OB(O)O", "[Fe]"):
        groups = unifac.get(smiles)
        assert not groups.modelled
        assert "incomplete UNIFAC fragmentation" in groups.source


def test_ions_are_excluded_by_policy_not_by_accident(unifac):
    groups = unifac.get("[OH3+]")
    assert not groups.modelled
    assert "non-electrolyte" in groups.source


# ==========================================================================
# the kernel
# ==========================================================================

MIXTURES = [
    (["CCO", "O"], [0.5, 0.5], 298.15),
    (["CCO", "O"], [0.9, 0.1], 351.0),
    (["CCO", "O"], [0.05, 0.95], 298.15),
    (["c1ccccc1", "CCO"], [0.3, 0.7], 320.0),
    (["CCCCCC", "CC(C)=O"], [0.4, 0.6], 300.0),
    (["OC(=O)c1ccccc1", "O"], [1.0e-4, 1.0 - 1.0e-4], 298.15),
    (["CC(=O)O", "CCO", "CCOC(C)=O", "O"], [0.25] * 4, 340.0),
    (["CO", "O", "c1ccccc1"], [0.2, 0.5, 0.3], 310.0),
]


@pytest.mark.parametrize("species,x,T", MIXTURES)
def test_gamma_matches_the_oracle(unifac, species, x, T):
    """Our kernel against `thermo`'s UNIFAC, to machine precision. Same strategy
    as the Joback cross-check: the implementation is verified, not trusted."""
    arrays = build_activity_arrays(species, unifac)
    ours = activity_coefficients(
        np.array(x, float), arrays.nu, arrays.R_k, arrays.Q_k,
        arrays.a_mn, arrays.active, T,
    )
    reference = tu.UNIFAC.from_subgroups(
        T=T, xs=list(x), chemgroups=[unifac.get(s).counts for s in species]
    ).gammas()
    assert ours == pytest.approx(np.array(reference), rel=1e-10)


def test_a_pure_liquid_is_ideal(unifac):
    """gamma -> 1 as x -> 1 is the symmetric convention's defining property, and
    it is what makes a single-component vessel behave exactly as it did before."""
    for smiles in ("CCO", "O", "c1ccccc1"):
        arrays = build_activity_arrays([smiles], unifac)
        gamma = activity_coefficients(
            np.array([1.0]), arrays.nu, arrays.R_k, arrays.Q_k,
            arrays.a_mn, arrays.active, 298.15,
        )
        assert gamma == pytest.approx([1.0], rel=1e-12)


def test_a_species_at_zero_concentration_still_has_a_gamma(unifac):
    """In a reaction network most species are at zero for part of the run. The
    combinatorial term is written so x cancels analytically rather than as 0/0,
    so the infinite-dilution limit must be finite and match the trend."""
    arrays = build_activity_arrays(["CCO", "O"], unifac)

    def gamma(x_eth):
        return activity_coefficients(
            np.array([x_eth, 1.0 - x_eth]), arrays.nu, arrays.R_k,
            arrays.Q_k, arrays.a_mn, arrays.active, 298.15,
        )[0]

    at_zero = gamma(0.0)
    assert np.isfinite(at_zero)
    assert at_zero > 1.0, "ethanol in water is strongly non-ideal"
    assert gamma(1.0e-8) == pytest.approx(at_zero, rel=1e-5)
    # and gamma falls monotonically toward 1 as the liquid becomes pure ethanol
    assert at_zero > gamma(0.5) > gamma(0.99) > 1.0


def test_an_empty_liquid_is_ideal_rather_than_undefined(unifac):
    """Composition is undefined with no liquid. The kernel must say 1, not nan --
    a flask poured out mid-run passes through exactly this state."""
    arrays = build_activity_arrays(["CCO", "O"], unifac)
    gamma = activity_coefficients(
        np.zeros(2), arrays.nu, arrays.R_k, arrays.Q_k,
        arrays.a_mn, arrays.active, 350.0,
    )
    assert gamma == pytest.approx([1.0, 1.0])


def test_unmodelled_species_are_held_ideal_and_named(unifac):
    arrays = build_activity_arrays(["O", "OP(=O)(O)O", "[OH3+]"], unifac)
    assert list(arrays.active) == [True, False, False]

    gamma = activity_coefficients(
        np.array([0.99, 0.005, 0.005]), arrays.nu, arrays.R_k,
        arrays.Q_k, arrays.a_mn, arrays.active, 298.15,
    )
    assert gamma[1] == 1.0 and gamma[2] == 1.0

    report = arrays.report()
    assert "OP(=O)(O)O" in report and "[OH3+]" in report


def test_a_missing_interaction_pair_is_reported_not_assumed(unifac):
    """About half the published pairs were never regressed. Zero is the claim
    that two groups mix athermally, which is a real statement -- so an absent
    pair has to be named rather than silently becoming zero."""
    arrays = build_activity_arrays(["CS(C)=O", "C(=S)=S"], unifac)
    assert arrays.missing_pairs, "DMSO/CS2 has no published parameter"
    assert "athermal" in arrays.report()


# ==========================================================================
# emergence: the two gaps this closes
# ==========================================================================


@pytest.fixture(scope="module")
def ethanol_water(thermo_module):
    return build_network([ETHANOL, WATER], [], thermo=thermo_module)


def _vapour_fraction(network, x_ethanol, T):
    v = Vessel(network, volume=1.0, T=T)
    v.charge({ETHANOL: x_ethanol, WATER: 1.0 - x_ethanol})
    p = v.integrator.equilibrium_pressures(v._nL, T)
    return float(p[v.species.index(ETHANOL)] / p.sum())


def test_an_azeotrope_appears_where_the_experiment_puts_one(ethanol_water):
    """The headline result. Under ideal Raoult the vapour is ALWAYS richer in
    ethanol, so distillation runs to a pure product; real ethanol/water stalls at
    95.6 wt% because the mixture is strongly non-ideal. Nothing in the code
    mentions an azeotrope -- it is the composition where y = x, and it appears
    because gamma bends the equilibrium line across the diagonal."""
    def enrichment(x):
        v = Vessel(ethanol_water, volume=1.0, T=298.15)
        v.charge({ETHANOL: x, WATER: 1.0 - x})
        return _vapour_fraction(ethanol_water, x, v.bubble_point()) - x

    assert enrichment(0.5) > 0.0, "ethanol-lean liquid must enrich in ethanol"
    assert enrichment(0.95) < 0.0, "past the azeotrope the enrichment reverses"

    lo, hi = 0.5, 0.99
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if enrichment(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    azeotrope = 0.5 * (lo + hi)
    assert azeotrope == pytest.approx(0.894, abs=0.02)   # 95.6 wt%


def test_the_azeotrope_boils_below_both_pure_components(ethanol_water):
    """A minimum-boiling azeotrope, which is the reason it cannot be distilled
    past: the mixture is MORE volatile than either component alone."""
    def bubble(x):
        v = Vessel(ethanol_water, volume=1.0, T=298.15)
        v.charge({ETHANOL: x, WATER: 1.0 - x})
        return v.bubble_point()

    assert bubble(0.89) < bubble(1.0) < bubble(0.0)
    assert bubble(0.89) == pytest.approx(351.3, abs=1.5)   # experiment: 351.3 K


def test_ideal_raoult_would_have_no_azeotrope(ethanol_water):
    """The control. Turning gamma off must restore the old behaviour exactly --
    otherwise the result above is an artefact of something else that changed."""
    v = Vessel(ethanol_water, volume=1.0, T=298.15)
    v.phases.gamma_active[:] = False
    for x in (0.5, 0.9, 0.95, 0.99):
        v.reset()
        v.charge({ETHANOL: x, WATER: 1.0 - x})
        p = v.integrator.equilibrium_pressures(v._nL, v.bubble_point())
        y = float(p[v.species.index(ETHANOL)] / p.sum())
        assert y > x, f"ideal Raoult enriches without limit (x={x})"


@pytest.fixture(scope="module")
def benzoic_water(thermo_module):
    return build_network([BENZOIC, WATER], [], thermo=thermo_module)


def test_benzoic_acid_solubility_lands_near_the_experiment(benzoic_water):
    """Ideal solubility overestimates a solute in a dissimilar solvent by orders
    of magnitude: benzoic acid in water came out ~300x too soluble. The activity
    coefficient is the whole correction -- gamma is ~350 here, and 350 is exactly
    the factor that was missing."""
    v = Vessel(benzoic_water, volume=1.0, T=298.15)
    v.charge({WATER: 55.0, BENZOIC: 0.02})
    i = v.species.index(BENZOIC)

    gamma = v.integrator.activity_coefficients(v._nL, 298.15)
    assert 200.0 < gamma[i] < 600.0

    x_sat = float(v.integrator.solubility(298.15, gamma)[i])
    measured = 5.03e-4          # 3.44 g/L at 298 K, CRC
    assert 0.5 < x_sat / measured < 2.0

    ideal = float(v.integrator.saturation_activity(298.15)[i])
    assert ideal / measured > 100.0, "the ideal law must still be the bad one"


def test_solubility_still_rises_with_temperature(benzoic_water):
    """Non-ideality must not cost the trend that was already right."""
    v = Vessel(benzoic_water, volume=1.0, T=298.15)
    v.charge({WATER: 55.0, BENZOIC: 0.02})
    i = v.species.index(BENZOIC)

    limits = []
    for T in (280.0, 298.15, 320.0, 340.0):
        gamma = v.integrator.activity_coefficients(v._nL, T)
        limits.append(float(v.integrator.solubility(T, gamma)[i]))
    assert limits == sorted(limits)


# ==========================================================================
# the unsymmetric convention: gas solubility that knows its solvent
# ==========================================================================

O2 = "O=O"


def _dissolved_per_bar(solvent: str, moles: float, thermo, T: float = 298.15):
    """Equilibrate O2 over a solvent and return (mM at 0.21 bar, gamma*)."""
    net = build_network([solvent, O2], [], thermo=thermo)
    v = Vessel(net, volume=2.0, T=T, T_env=T, UA=50.0, kla=2.0)
    v.charge({solvent: moles})
    v.charge({O2: 2.0}, phase="gas")     # large, so equilibrating barely moves p
    v.run(40_000.0)

    i = v.species.index(Molecule.from_smiles(solvent).smiles)
    assert i is not None
    p = v.partial_pressures()[O2]
    c = v.concentrations()[O2]
    gamma = v.integrator.activity_coefficients(v._nL, v.T)[v.species.index(O2)]
    return c / p * 0.21 * 1e3, float(gamma)


def test_a_dissolved_gas_now_has_an_activity_coefficient(thermo_module):
    """It used to be held ideal because standard UNIFAC has no group for a
    permanent gas. The PSRK extension supplies them, so O2 is a modelled species
    like any other."""
    net = build_network([WATER, O2], [], thermo=thermo_module)
    v = Vessel(net, volume=1.0, T=298.15)
    assert v.phases.gamma_active[v.species.index(O2)]
    assert not v.phases.condensable[v.species.index(O2)]


def test_the_reference_solvent_reproduces_its_measured_henry_constant(thermo_module):
    """The defining property of the unsymmetric convention. Our Henry constants
    are measured in water, so at infinite dilution IN WATER the correction must
    be exactly 1 and the calibrated number must come back untouched. If this
    drifts, every gas solubility drifts with it."""
    mM, gamma = _dissolved_per_bar(WATER, 55.0, thermo_module)
    assert gamma == pytest.approx(1.0, abs=2e-3)
    assert mM == pytest.approx(0.27, rel=0.15)      # measured 0.27 mM under air


@pytest.mark.parametrize(
    "solvent,name,moles,measured",
    [
        ("CCO", "ethanol", 17.0, 2.10),
        ("CO", "methanol", 24.7, 2.10),
        ("CCCCCC", "n-hexane", 7.6, 3.10),
        ("c1ccccc1", "benzene", 11.2, 1.80),
    ],
)
def test_gas_solubility_is_solvent_dependent(
    thermo_module, solvent, name, moles, measured
):
    """The gap this closes. Oxygen is ~8x more soluble in ethanol than in water,
    and every one of these used to come back with water's number because the
    Henry constant was aqueous and nothing could transfer it. The transfer is
    the ratio of infinite-dilution activity coefficients, which is exactly the
    ratio of Henry constants -- the solute's pure-liquid fugacity cancels."""
    mM, gamma = _dissolved_per_bar(solvent, moles, thermo_module)
    aqueous, _ = _dissolved_per_bar(WATER, 55.0, thermo_module)

    assert gamma < 0.5, "a gas is far happier in an organic solvent than in water"
    assert mM > 3.0 * aqueous, f"{name} must dissolve far more O2 than water does"
    assert 0.5 < mM / measured < 2.0


def test_the_transfer_goes_the_right_way_for_a_polar_solvent(thermo_module):
    """Ordering, not just magnitude: O2 is least soluble in water, most in an
    alkane, with alcohols in between. That ordering is the physical content."""
    water, _ = _dissolved_per_bar(WATER, 55.0, thermo_module)
    ethanol, _ = _dissolved_per_bar("CCO", 17.0, thermo_module)
    hexane, _ = _dissolved_per_bar("CCCCCC", 7.6, thermo_module)
    assert water < ethanol < hexane


def test_the_reference_state_is_fitted_and_its_error_reported(thermo_module):
    """The reference is a correlation fitted at setup, so it has a residual, and
    a residual that is not reported is a silent approximation."""
    net = build_network([WATER, O2, "O=C=O", "[C-]#[O+]"], [], thermo=thermo_module)
    v = Vessel(net, volume=1.0, T=298.15)
    fits = v.activity_model.reference_fits

    assert set(fits) >= {O2, "O=C=O"}
    assert fits[O2] < 0.01, "oxygen's reference fits well"
    # Carbon monoxide does not: PSRK's parameters for it are strongly quadratic
    # in T and its reference swings sharply. That must be visible, not buried.
    assert fits["[C-]#[O+]"] > 0.01
    assert "[C-]#[O+]" in v.activity_model.report()


def test_a_gas_with_no_reference_state_falls_back_and_says_so(thermo_module):
    """If the reference solvent cannot be modelled there is no honest way to
    transfer the constant, so the tabulated value is used unchanged -- named,
    not silently."""
    from chemsim.properties import Volatility, VolatilityProvider

    # Declare a Henry solute whose reference solvent has no decomposition.
    volatility = VolatilityProvider(
        thermo_module,
        extra_curated={
            O2: Volatility(
                4.0, 500.0, 0.0, "test", "henry", reference_solvent="OP(=O)(O)O"
            )
        },
    )
    net = build_network([WATER, O2], [], thermo=thermo_module)
    v = Vessel(net, volume=1.0, T=298.15, volatility=volatility)

    assert not v.phases.gamma_active[v.species.index(O2)]
    assert "no usable reference state" in v.activity_model.report()


def test_a_non_volatile_solute_still_gets_an_activity_coefficient(thermo_module):
    """Only HENRY solutes are excluded, not everything that fails to be
    condensable. Sugars and most drugs are non-volatile -- they decompose before
    they boil -- but they are ordinary liquid-phase solutes, and a solubility is
    precisely where their activity coefficient matters most. Excluding them by
    testing `not condensable` instead of `henry` would silently make the species
    this feature exists for ideal again."""
    solute = "OCC(O)CO"        # glycerol, standing in for any non-volatile solute
    volatility = VolatilityProvider(
        thermo_module,
        extra_curated={
            solute: Volatility(
                NONVOLATILE_A, 0.0, 0.0, "declared non-volatile", "nonvolatile"
            )
        },
    )
    net = build_network([WATER, solute], [], thermo=thermo_module)
    v = Vessel(net, volume=1.0, T=298.15, volatility=volatility)

    i = v.species.index(Molecule.from_smiles(solute).smiles)
    assert not v.phases.condensable[i], "this test needs a non-volatile species"
    assert v.phases.gamma_active[i], "a non-volatile solute must not be held ideal"

    v.charge({WATER: 50.0, solute: 1.0})
    gamma = v.integrator.activity_coefficients(v._nL, 298.15)
    assert gamma[i] != 1.0


def test_a_single_component_vessel_is_unchanged(thermo_module):
    """Regression guard for every existing result: with one liquid species there
    is nothing to be non-ideal about, so Raoult must hold exactly as before."""
    net = build_network([ETHANOL], [], thermo=thermo_module)
    v = Vessel(net, volume=1.0, T=330.0)
    v.charge({ETHANOL: 2.0})
    gamma = v.integrator.activity_coefficients(v._nL, 330.0)
    assert gamma == pytest.approx(np.ones(len(v.species)))
    assert v.bubble_point() == pytest.approx(351.45, abs=0.5)
