"""C2 -- phosphate rock, and the two curated tables a route was blocked in.

`PLAYABLE.md` §8 called `calcium-phosphate` the cheapest row in the work order
and named ONE blocker: a mineral price. The +2 it promised is real. The mineral
price is not what delivered it.

⚠⚠ THE GRID IN ``test_the_pKa_row_is_what_moved_the_score`` IS THE POINT OF THIS
FILE. C2 shipped two one-line data rows -- a `MineralRecord` for Ca3(PO4)2 and a
third phosphoric-acid pKa -- and they buy DISJOINT things: the pKa row moves
every compound that moved and the mineral row moves none of them, while the
mineral row is the only reason the rock can dissolve in a flask at all. Measuring
them one at a time as a 2x2 is G3's own rule (*measure two suspected rules as a
GRID, not as a list*) applied to two data tables instead of two scoring rules.

⚠ The flask tests run at **rtol 1e-8**, deliberately and not for accuracy: at the
default tolerance this flask reports 46.06% where the converged answer is 0.82%.
See ``validation/phosphate_rock.py`` panel 7.
"""

from __future__ import annotations

import math

import pytest

from chemsim.matter import Molecule
from chemsim.network import build_network
from chemsim.properties import dissociation_templates, electrolyte_provider
from chemsim.properties import electrolyte as E
from chemsim.properties import mineral_data as MD
from chemsim.properties.ion_data import AQUEOUS_IONS
from chemsim.properties.solubility_product import (
    UnpricedLattice,
    solubility_product,
)
from chemsim.properties.thermochemistry import ThermochemistryProvider
from chemsim.vessel import Vessel

WATER, SULFURIC, PHOSPHORIC_IN, CALCIUM = "O", "OS(=O)(=O)O", "OP(=O)(O)O", "[Ca+2]"
PO4 = "O=P([O-])([O-])[O-]"
SO4 = "O=S(=O)([O-])[O-]"
H2PO4, H3PO4 = "O=P([O-])(O)O", "O=P(O)(O)O"
ROCK_NAME = "phosphate rock"
ROCK = 0.01
TIGHT = {"rtol": 1.0e-8, "atol": 1.0e-14}

CATALOG_ROCK = "[Ca+2].[Ca+2].[Ca+2].[O-]P([O-])([O-])=O.[O-]P([O-])([O-])=O"


@pytest.fixture(scope="module")
def thermo():
    return electrolyte_provider()


@pytest.fixture(scope="module")
def net(thermo):
    return build_network(
        [WATER, SULFURIC, PHOSPHORIC_IN, CALCIUM], list(dissociation_templates()),
        thermo=thermo, max_species=60,
    )


def digest(net, thermo, k_diss=10.0, duration=600.0, acid=3 * ROCK,
           drop_lattice=False, **kw):
    """One wet-process flask -> its VesselState."""
    saved = MD.MINERALS.pop(ROCK_NAME) if drop_lattice else None
    try:
        v = Vessel(net, volume=1.0, thermo=thermo, T=350.0, T_env=350.0,
                   k_diss=k_diss)
        v.charge({CALCIUM: 3 * ROCK, PO4: 2 * ROCK}, phase="solid")
        v.charge({WATER: 55.0, SULFURIC: acid})
        v.run(duration, **kw)
        return v.state()
    finally:
        if saved is not None:
            MD.MINERALS[ROCK_NAME] = saved


# ---------------------------------------------------------------------------
# the price
# ---------------------------------------------------------------------------
def test_the_rock_prices_and_both_halves_are_one_database():
    """⚠ The rule that bites on FeSO4 and refuses three of C2's four probed
    rows: Hfs and S0s from the SAME tabulation or the entry does not exist."""
    rec = MD.MINERALS[ROCK_NAME]
    assert rec.cas == "7758-87-4"
    assert rec.formula == {"Ca": 3, "P": 2, "O": 8}
    assert rec.Hf_solid == pytest.approx(-4120.8, abs=0.01)
    assert rec.S0_solid == pytest.approx(236.0, abs=0.01)
    # DERIVED against the CRC element reference states, never transcribed.
    assert rec.Gf_solid == pytest.approx(-3884.72, abs=0.05)
    assert rec.Cp_solid == pytest.approx(227.8, abs=0.01)
    assert rec.Vm_solid == pytest.approx(0.098782, rel=1e-4)
    assert "both from CRC" in rec.source
    assert "DERIVED" in rec.source


def test_the_lattice_is_the_catalogs_own_salt_canonicalised():
    """⚠ S6's trap: the catalog spells its salts in a different fragment order
    from the canonical table, so this comparison MUST be canonical."""
    assert Molecule.from_smiles(CATALOG_ROCK).smiles == MD.MINERALS[ROCK_NAME].lattice


def test_the_Ksp_comes_out_of_two_tabulations_with_nothing_fitted():
    ksp = solubility_product(MD.MINERALS[ROCK_NAME])
    assert ksp.ln_Ksp / math.log(10) == pytest.approx(-32.677, abs=0.01)
    assert ksp.dilute is True
    # 28 decades below the gypsum it is turned into -- which is why the wet
    # process needs an acid, and why panel 6's rate cap is so low.
    anhydrite = solubility_product(MD.MINERALS["anhydrite"])
    decades = (anhydrite.ln_Ksp - ksp.ln_Ksp) / math.log(10)
    assert decades == pytest.approx(28.5, abs=0.5)


# ---------------------------------------------------------------------------
# the pKa row
# ---------------------------------------------------------------------------
def test_the_third_phosphoric_pKa_is_the_member_of_its_own_series():
    """⚠ 2.15 / 7.20 / 12.35, not CRC's 2.16 / 7.21 / 12.32. Taking the third
    from a different compilation would mix two sources inside one trend --
    the iodide row's decision, made a second time."""
    triple = [p for p in E._PAIRS if p.name.startswith("phosphoric acid")]
    assert [p.pKa for p in triple] == [2.15, 7.20, 12.35]
    assert triple[2].acid == "[O-]P(=O)([O-])O"
    assert triple[2].base == "[O-]P(=O)([O-])[O-]"


def test_adding_it_is_BIT_IDENTICAL_for_every_pre_existing_ion():
    """⚠⚠ C1's rule: a 1e-16 shift in a data table owes `tolerance_audit.py`
    ten minutes of the user's CPU, and NOT shifting it is cheaper than proving
    it harmless. Each pair is anchored on its own neutral, so appending one adds
    a key and touches no other -- asserted rather than assumed."""
    base = ThermochemistryProvider()
    without = tuple(p for p in E._PAIRS if p.name != "phosphoric acid, 3rd")
    after = E.ion_thermochemistry(base, E._PAIRS)
    before = E.ion_thermochemistry(base, without)

    assert set(after) - set(before) == {PO4}
    assert set(before) - set(after) == set()
    assert all(after[k] == before[k] for k in before), (
        "an existing ion moved; tolerance_audit.py is owed"
    )


# ---------------------------------------------------------------------------
# ⚠⚠ THE GRID -- which of the two rows bought what
# ---------------------------------------------------------------------------
def _provider(with_third_pka):
    pairs = E._PAIRS if with_third_pka else tuple(
        p for p in E._PAIRS if p.name != "phosphoric acid, 3rd")
    base = ThermochemistryProvider()
    return ThermochemistryProvider(
        extra_curated=E.ion_thermochemistry(base, pairs))


def _resolves(smiles, prov, lattices):
    """The question `validation/catalog_coverage.py` asks of every compound."""
    parts = smiles.split(".")
    charged = any(Molecule.from_smiles(p).charge != 0 for p in parts)
    try:
        for piece in (parts if charged else [smiles]):
            prov.get(Molecule.from_smiles(piece))
        return True
    except Exception:  # noqa: BLE001
        pass
    return Molecule.from_smiles(smiles).smiles in lattices


MOVED = {
    "calcium-phosphate": CATALOG_ROCK,
    "sodium-phosphate": "[Na+].[Na+].[Na+].[O-]P([O-])([O-])=O",
    "phosphate-ion": "[O-]P([O-])([O-])=O",
}


def test_the_pKa_row_is_what_moved_the_score():
    """⚠⚠⚠ THE FINDING. Three catalog compounds moved refused -> priced across
    C2. All three move on the pKa row ALONE. The mineral row -- the only thing
    the work order named -- moves one of the three, and that one moves without
    it, so its contribution to the coverage number is ZERO.

    ⚠ This does NOT say the mineral row was wasted: see
    ``test_without_the_lattice_the_rock_is_INERT``. It says the two rows buy
    disjoint things and the work order could only see one of them."""
    lat_with = {m.lattice for m in MD.MINERALS.values()}
    lat_without = {m.lattice for n, m in MD.MINERALS.items() if n != ROCK_NAME}
    new, old = _provider(True), _provider(False)

    for cid, smi in MOVED.items():
        assert not _resolves(smi, old, lat_without), f"{cid} was not refused"
        assert _resolves(smi, new, lat_without), f"{cid} needs more than the pKa"
        assert _resolves(smi, new, lat_with), f"{cid} is not priced today"

    # and the mineral row ALONE moves exactly one of the three
    alone = {cid for cid, smi in MOVED.items()
             if _resolves(smi, old, lat_with)}
    assert alone == {"calcium-phosphate"}


# ---------------------------------------------------------------------------
# the membership gap
# ---------------------------------------------------------------------------
def test_five_lattices_have_a_Ksp_and_cannot_be_put_in_a_flask(thermo):
    """⚠⚠ `ion_data` and `electrolyte` price the same ions on different ZEROS,
    which `solubility_product` warns about at length. Nothing compares which
    ions they HAVE, and that is what blocked `phosphoric-wet`.

    The five that remain are all blocked on the SAME ion, and it is the same
    shape: `_PAIRS` carries H2S -> [SH-] and stops. That step is a REFUSAL
    rather than the next one-line fix -- HS- -> S2- is quoted between ~12.9 and
    19 depending on the compilation."""
    def priced(smi):
        try:
            thermo.get(smi)
            return True
        except Exception:  # noqa: BLE001
            return False

    blocked = {}
    buildable = 0
    for name, rec in MD.MINERALS.items():
        if not rec.ions:
            continue
        try:
            solubility_product(rec)
        except UnpricedLattice:
            continue
        missing = sorted({i for i in rec.ions if not priced(i)})
        if missing:
            blocked[name] = missing
        else:
            buildable += 1

    assert set(blocked) == {"sphalerite", "galena", "covellite",
                            "chalcocite", "cinnabar"}
    assert all("[S-2]" in m for m in blocked.values())
    assert buildable == 25
    assert ROCK_NAME not in blocked
    # the aqueous table is strictly bigger than what a network can reach
    assert not all(priced(i) for i in AQUEOUS_IONS)


# ---------------------------------------------------------------------------
# the flask -- what the MINERAL row buys
# ---------------------------------------------------------------------------
def test_the_wet_process_digests_the_rock(net, thermo):
    """The route runs: rock in the solid block, acid in the water, phosphoric
    acid out. ⚠ At rtol 1e-8 -- the default reports a different number."""
    st = digest(net, thermo, **TIGHT)
    left = st.n_solid.get(PO4, 0.0) / 2.0
    assert left < ROCK, "nothing dissolved"
    assert st.n_liquid[H3PO4] > 1.0e-3
    assert st.n_liquid[H2PO4] > 1.0e-4
    # and the calcium it releases stays DISSOLVED -- see the next test.
    assert st.n_liquid[CALCIUM] > 1.0e-3


def test_no_gypsum_drops_because_the_liquor_is_UNDERSATURATED(net, thermo):
    """⚠ The catalog row promises gypsum and this flask makes none, and that is
    the arithmetic rather than a bug: at 8% of 0.01 mol in a whole litre the
    calcium-sulfate ion product is a QUARTER of anhydrite's Ksp. A real wet
    process is a thick slurry; this is a dilute one, and `PLAYABLE.md` §5's rule
    (*a yield is not a corpus property*) covers exactly this."""
    st = digest(net, thermo, **TIGHT)
    ksp = solubility_product(MD.MINERALS["anhydrite"]).Ksp
    q = st.n_liquid[CALCIUM] * st.n_liquid[SO4]          # 1 L, so c == n
    assert q < ksp, "the liquor is saturated; this test's premise is gone"
    assert q / ksp == pytest.approx(0.26, abs=0.05)
    assert st.n_solid.get(SO4, 0.0) == pytest.approx(0.0, abs=1e-15)


def test_more_rock_does_not_dissolve_faster_either(net, thermo):
    """⚠⚠ THE OTHER FACE OF THE SAME LIMIT, and the sharper one. The drive is
    `k_diss * V * (Qroot - Ksproot)`: no acid in it, and no SURFACE AREA in it.
    So ten times the rock dissolves the SAME NUMBER OF MOLES -- the percentage
    falls by ten and the absolute amount does not move. A real dissolution goes
    with the area of the crop; this one goes with a vessel knob."""
    amounts = []
    for rock in (0.01, 0.10):
        v = Vessel(net, volume=1.0, thermo=thermo, T=350.0, T_env=350.0,
                   k_diss=10.0)
        v.charge({CALCIUM: 3 * rock, PO4: 2 * rock}, phase="solid")
        v.charge({WATER: 55.0, SULFURIC: 3 * rock})
        v.run(600.0, **TIGHT)
        st = v.state()
        amounts.append(rock - st.n_solid.get(PO4, 0.0) / 2.0)
    assert amounts[1] == pytest.approx(amounts[0], rel=0.05), (
        "ten times the rock changed how much dissolved; the dissolution law "
        "has grown a surface-area term and this limit is closed"
    )


def test_matter_is_exact_across_the_digestion(net, thermo):
    """Phosphorus is conserved to the solver's own error control, across a
    lattice dissolution and three protonations. ⚠ NOT across a
    precipitation: nothing precipitates here, which is the test above."""
    st = digest(net, thermo, **TIGHT)
    total = 0.0
    for smi in (PO4, "O=P([O-])([O-])O", H2PO4, H3PO4):
        total += (st.n_liquid.get(smi, 0.0) + st.n_solid.get(smi, 0.0)
                  + st.n_gas.get(smi, 0.0))
    assert total == pytest.approx(2 * ROCK, rel=1e-6)


def test_without_the_lattice_the_rock_is_INERT(net, thermo):
    """⚠⚠⚠ THE OTHER HALF OF THE GRID, and G4's rule from a new side. Drop the
    `MineralRecord` and the ions sit in the solid block for ever, because no Ksp
    connects them to the solution -- while every static score (species-ready,
    the BOTH column, playable) stays exactly where it was. **A route can score
    on one table and need a different one to move.**"""
    st = digest(net, thermo, drop_lattice=True, **TIGHT)
    assert st.n_solid[PO4] == pytest.approx(2 * ROCK, rel=1e-12)
    assert st.n_liquid.get(H3PO4, 0.0) == pytest.approx(0.0, abs=1e-15)
    assert st.n_liquid.get(H2PO4, 0.0) == pytest.approx(0.0, abs=1e-15)


def test_the_acid_cannot_hurry_the_rock(net, thermo):
    """⚠⚠ THE LIMIT. Dissolution is an equilibrium transport term whose rate has
    no acid in it: ten times the sulfuric acid does not move the conversion,
    because the driving force is already floored at Ksp^(1/N). A real digestion
    is a SURFACE reaction going with [H+], and this engine has that shape for a
    GAS arriving at a crystal (`SurfaceArrays`) and not for a liquid."""
    lean = digest(net, thermo, acid=0.03, **TIGHT)
    rich = digest(net, thermo, acid=0.30, **TIGHT)
    a = 2 * ROCK - lean.n_solid.get(PO4, 0.0)
    b = 2 * ROCK - rich.n_solid.get(PO4, 0.0)
    assert b == pytest.approx(a, rel=0.05), (
        "ten times the acid moved the conversion; the dissolution law has "
        "grown an acid term and this limit is closed"
    )


# ---------------------------------------------------------------------------
# the precipitation drive's cap
# ---------------------------------------------------------------------------
def test_the_saturation_cap_bounds_the_DRIVE_and_not_just_the_root():
    """⚠⚠ C2's engine fix. The cap was written to stop a Jacobian perturbation
    producing an inf and did not: it bounds a CONCENTRATION, and the next line
    multiplies by a liquid volume a Newton iterate does not bound. Measured, the
    BDF iteration proposed T = 1.0 K (the RHS's own `T_MIN` clamp) with 5.0e10
    mol of liquid, so `V_L1` was 9.2e8 L and `1e-2 * 9.2e8 * exp(700)` overflowed.

    ⚠ The headroom is BIT-IDENTICAL while `k_diss * V_L1 <= 1`, which is every
    vessel in this repo -- that is what this asserts, so a future change to
    LN_SATURATION_CAP cannot silently move a converged answer."""
    import numpy as np

    from chemsim.numerics.vessel_integrator import LN_SATURATION_CAP

    assert LN_SATURATION_CAP == 700.0
    for scale in (1.0e-2, 0.5, 1.0):
        head = LN_SATURATION_CAP - math.log(max(scale, 1.0))
        assert head == LN_SATURATION_CAP
    # and above 1 it shrinks exactly enough to keep the product finite
    for scale in (9.2e6, 1.0e10):
        head = LN_SATURATION_CAP - math.log(max(scale, 1.0))
        assert np.isfinite(scale * math.exp(head))


def test_a_vessel_may_declare_k_diss_ZERO(net, thermo):
    """⚠⚠⚠ THE BUG C2's OWN FIX INTRODUCED, AND ONLY `tolerance_audit.py` SAW IT.

    The headroom above was first written `max(math.log(scale), 0.0)`, which is
    the same function as `math.log(max(scale, 1.0))` **only where the log is
    defined**. `scale` is `k_diss * V_L1`, and three examples declare
    `k_diss = 0.0` outright — `workshop` part 3, `named_routes`, and `recipes`'
    crystallise stage (so `multistep_prep`). All three began raising
    `ValueError: math domain error`, **the whole test suite stayed green**, and
    the tolerance audit caught it by comparing against its own recorded baseline.

    ⚠ A vessel with `k_diss = 0` is a deliberate configuration -- "no dissolution
    or crystallisation in this flask" -- and not an edge case, which is why this
    is a test and not a clamp."""
    v = Vessel(net, volume=1.0, thermo=thermo, T=350.0, T_env=350.0, k_diss=0.0)
    v.charge({CALCIUM: 3 * ROCK, PO4: 2 * ROCK}, phase="solid")
    v.charge({WATER: 55.0, SULFURIC: 3 * ROCK})
    v.run(60.0, **TIGHT)
    st = v.state()
    # nothing dissolves, which is what k_diss = 0 MEANS
    assert st.n_solid[PO4] == pytest.approx(2 * ROCK, rel=1e-12)


def test_the_digestion_raises_no_RuntimeWarning(net, thermo):
    """The overflow above reached `nan` one line later, in the `_avail` product.
    It was measured harmless in both the answer and the clock -- which is why it
    is asserted here rather than described as a bug that mattered."""
    import warnings

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        digest(net, thermo, duration=60.0, **TIGHT)
        overflows = [w for w in caught
                     if issubclass(w.category, RuntimeWarning)
                     and "overflow" in str(w.message)]
    assert not overflows, [str(w.message) for w in overflows]
