"""M3, the DATA half -- an aqueous ion table, and the Ksp it makes possible.

⚠ THESE TESTS REPLACED A SET THAT PINNED THE OPPOSITE VERDICT, and that is the
most useful thing about them. The previous version asserted that all 13 lattices
REFUSE, that a naive Ksp is 25-29 decades out, and that the data could not come
from `chemicals`. The first two were true of the tables as they then stood and
are kept below as history against a synthetic reproduction. The third was false:
``chemicals`` 1.5.2 ships the CRC aqueous-ion table as a data file that no
accessor function reads.

**A refusal from an API is not evidence that the data is absent.**

Cheap: arithmetic against tables, no integration. The ENGINE term M3 also needed
is in ``tests/test_precipitation.py``.
"""

from __future__ import annotations

import math

import pytest

from chemsim.constants import R
from chemsim.properties.electrolyte import electrolyte_provider
from chemsim.properties.ion_data import AQUEOUS_IONS, AqueousIon, worst_crosscheck
from chemsim.properties.element_data import REFERENCE_STATES
from chemsim.properties.mineral_data import MINERALS
from chemsim.properties.solubility_product import (
    DILUTE_LIMIT,
    MEASURED_FACTOR,
    T_REF,
    SolubilityProduct,
    UnpricedLattice,
    lattice_verdicts,
    measured_agreement,
    solubility_product,
)

T_CROSSCHECK_TOL = 1.0        # kJ/mol -- the builder's acceptance threshold


# ---------------------------------------------------------------------------
# the ion table: where it came from, and the check that proves its basis
# ---------------------------------------------------------------------------
def test_the_table_is_anchored_on_Gf_H_plus_equals_zero_exactly():
    """The convention is stated by the source, not assumed by the reader.

    The CRC row for H+ carries 0/0/0/0. That is what makes every other row a
    conventional aqueous formation value rather than an absolute one, and it is
    the single fact the whole subtraction rests on.
    """
    proton = AQUEOUS_IONS["[H+]"]
    assert proton.Hf == 0.0 and proton.Gf == 0.0 and proton.S0 == 0.0


def test_every_entry_closes_against_its_own_Hf_and_S_within_a_kJ():
    """⚠ THE CROSS-CHECK, RE-RUN HERE RATHER THAN TRUSTED FROM THE BUILDER.

    ``Gf`` is re-derived from the same row's ``Hf`` and ``S(aq)`` against the
    element reference entropies -- a basis the ion table knows nothing about. A
    row that closes has been shown to be on the conventional scale.
    """
    for smiles, ion in AQUEOUS_IONS.items():
        dS = ion.S0 + (ion.charge / 2.0) * REFERENCE_STATES["H"].S0
        for el, n in ion.elements.items():
            ref = REFERENCE_STATES[el]
            dS -= (n / ref.atoms_per_unit) * ref.S0
        derived = ion.Hf - T_REF * dS / 1000.0
        assert ion.Gf == pytest.approx(derived, abs=T_CROSSCHECK_TOL), smiles
        # ...and the residual the builder recorded is that same number.
        assert ion.crosscheck == pytest.approx(ion.Gf - derived, abs=5e-3), smiles

    smiles, worst = worst_crosscheck()
    assert abs(worst) < T_CROSSCHECK_TOL, (smiles, worst)


def test_the_half_H2_term_is_what_makes_it_a_BASIS_check():
    """⚠ Drop it and sodium misses by exactly ``T S0(H2)/2`` = 19.48 kJ/mol at
    298.15 K -- a quantity no arithmetic slip produces, and 19 times the 1 kJ/mol
    acceptance tolerance. The term exists only because the convention settles the
    electron against half a hydrogen molecule and sets S(H+,aq) = 0, so its
    presence is what distinguishes "this row is on the conventional scale" from
    "these three columns are internally tidy".

    ⚠ Do not read anything into this being ~19.5 like the chloride gap two tests
    up. That one is the pKa anchor and this one is half an entropy of hydrogen;
    they are unrelated quantities that happen to collide at two digits."""
    na = AQUEOUS_IONS["[Na+]"]
    without = na.S0 - REFERENCE_STATES["Na"].S0
    naive = na.Hf - T_REF * without / 1000.0
    half_H2 = T_REF * REFERENCE_STATES["H"].S0 / 2000.0
    assert half_H2 == pytest.approx(19.48, abs=0.01)
    assert abs(na.Gf - naive) == pytest.approx(half_H2, abs=0.05)
    assert abs(na.Gf - naive) > 19.0 * T_CROSSCHECK_TOL


def test_this_table_is_a_DIFFERENT_ZERO_from_electrolytes_and_says_so():
    """⚠⚠ The one confusion that would silently cost decades of Ksp.

    ``electrolyte`` anchors on ``Gf(H3O+) = Gf(H2O, liquid)``; this table anchors
    on ``Gf(H+,aq) = 0``. Chloride is a real number in both and they differ by
    19.5 kJ/mol -- 3.4 decades. Neither is wrong; subtracting one from the other
    is, so the two live in separate modules with no import between them.
    """
    here = AQUEOUS_IONS["[Cl-]"].Gf
    there = electrolyte_provider().get("[Cl-]").Gf
    gap = abs(here - there)
    assert gap == pytest.approx(19.5, abs=1.0)
    decades = gap * 1000.0 / (R * T_REF) / math.log(10)
    assert decades == pytest.approx(3.4, abs=0.2)


def test_the_ion_module_does_not_import_the_pKa_module_or_the_reverse():
    """The separation is structural, not a convention someone remembers."""
    import chemsim.properties.electrolyte as elec
    import chemsim.properties.ion_data as ions

    for mod, forbidden in ((ions, "electrolyte"), (elec, "ion_data")):
        src = open(mod.__file__, encoding="utf-8").read()
        code = "\n".join(
            ln for ln in src.splitlines()
            if ln.startswith(("import ", "from ")) or "    import " in ln
            or "    from " in ln
        )
        assert forbidden not in code, f"{mod.__name__} imports {forbidden}"


# ---------------------------------------------------------------------------
# the basis guard -- the one mistake this module must refuse
# ---------------------------------------------------------------------------
def test_passing_the_electrolyte_provider_is_REFUSED_rather_than_answered():
    """⚠ It would answer. ``get("[Cl-]")`` returns a perfectly good float on the
    wrong zero, and the resulting Ksp is 3.4 decades out and looks reasonable.
    So the type is checked rather than the interface."""
    with pytest.raises(TypeError, match="MAPPING of aqueous-basis ions"):
        solubility_product("rock salt", electrolyte_provider())


def test_a_mapping_of_the_wrong_RECORD_type_is_refused_too():
    from chemsim.properties.thermochemistry import ThermoData

    bad = {"[Na+]": ThermoData(0.0, 0.0, "x"), "[Cl-]": ThermoData(0.0, 0.0, "x")}
    with pytest.raises(TypeError, match="AqueousIon"):
        solubility_product("rock salt", bad)


# ---------------------------------------------------------------------------
# the deliverable: Ksp against solubilities that were already in the repo
# ---------------------------------------------------------------------------
def test_five_salts_over_five_decades_land_inside_a_stated_factor():
    """⚠⚠ M3's 'at least three salts within a stated factor', and the factor is 4.

    The measured solubilities come from ``mineral_data.fusion_law_bound``, which
    was entered to condemn the FUSION law and predates every line of this work.
    Nothing here is fitted: two independent tables are subtracted and the root is
    taken.
    """
    got = measured_agreement()
    assert len(got) >= 3
    for name, (predicted, measured, ratio) in got.items():
        assert 1.0 / MEASURED_FACTOR <= ratio <= MEASURED_FACTOR, (name, ratio)
    # ...and it is not three salts clustered at one solubility.
    spread = max(m for _, m, _ in got.values()) / min(m for _, m, _ in got.values())
    assert spread > 1.0e4, "the check has to span decades or it proves nothing"


def test_the_residual_factor_is_gamma_and_the_reductio_is_in_the_table():
    """⚠ The remaining factor of ~4 is activity coefficients, not tuning -- and
    the honest way to show that is the case where ideal activities become absurd.
    Caustic potash comes out at 1e5 mol/L, which is the ideal-activity law being
    extrapolated far past where it means anything, and ``dilute`` says so."""
    kop = solubility_product("caustic potash")
    assert kop.solubility() > 1.0e4
    assert not kop.dilute
    assert solubility_product("calcite").dilute
    assert solubility_product("calcite").solubility() < DILUTE_LIMIT


def test_a_metathesis_target_is_sparingly_soluble_by_many_decades():
    """The whole point of the mechanic: AgCl and BaSO4 have to be far enough
    below a soluble salt that a precipitate is unambiguous rather than a slight
    shift. Asserted as a GAP against rock salt rather than as an absolute Ksp,
    because an absolute value here would be a remembered literature number."""
    salt = solubility_product("rock salt").ln_Ksp / math.log(10)
    for name in ("chlorargyrite", "barite"):
        assert salt - solubility_product(name).ln_Ksp / math.log(10) > 10.0


# ---------------------------------------------------------------------------
# what still refuses, and each refusal is a fact rather than a gap
# ---------------------------------------------------------------------------
def test_quicklime_refuses_on_the_OXIDE_ION_and_that_is_chemistry():
    """CaO does not dissolve to Ca2+ + O2-. It hydrates to Ca(OH)2 and THAT
    dissolves, which is why no aqueous compilation carries an oxide ion and why
    refusing is the right answer rather than a missing row.

    ⚠ M6 TURNED THIS FROM ONE MINERAL INTO A CLASS, WHICH IS A STRONGER CLAIM.
    Curating the roasting oxides put eight oxide lattices in the table, and
    EVERY refusal in the whole table is now the same ion for the same reason:
    hematite, corundum, periclase, zincite, litharge, tenorite, montroydite and
    quicklime. Nothing refuses for any other reason at all.

    ⚠ And it is exactly why M6 could not hold a reacting crystal ion-by-ion --
    the representation that works for precipitation has no form for an oxide.
    See ``properties/solid_state.py``.
    """
    verdicts = lattice_verdicts()
    refused = {k for k, v in verdicts.items() if v}
    assert refused == {
        "quicklime", "hematite", "corundum", "periclase", "zincite",
        "litharge", "tenorite", "montroydite",
    }, refused
    # one ion, one reason, eight lattices
    assert all("[O-2]" in v[0] for v in verdicts.values() if v)
    assert all(len(v) == 1 for v in verdicts.values() if v)
    with pytest.raises(UnpricedLattice, match=r"\[O-2\]"):
        solubility_product("quicklime")


def test_the_new_sulfides_widened_what_can_PRECIPITATE():
    """M6 curated four sulfides for roasting, and a sulfide lattice that prices
    is also a lattice that can drop out of solution. Not what they were added
    for, which is the point of keeping one table."""
    verdicts = lattice_verdicts()
    for name in ("galena", "covellite", "chalcocite", "cinnabar"):
        assert not verdicts[name], (name, verdicts[name])
        assert solubility_product(name).ln_Ksp < 0.0    # all sparingly soluble


def test_the_refusal_still_names_the_ion_and_reports_the_lattice_as_sound():
    with pytest.raises(UnpricedLattice) as caught:
        solubility_product("quicklime")
    msg = str(caught.value)
    assert "[O-2]" in msg
    assert "LATTICE half is sound" in msg and "-603.27" in msg


def test_a_named_pigment_refuses_on_the_LATTICE_half_for_once():
    """⚠ Chrome yellow (PbCrO4) never reaches this module: ``mineral_data``
    refuses it because CRC has an Hfs and no S0s in any shared database, and
    mixing two tabulations inside one entry is what that builder forbids. First
    time a target has been lost on the lattice side rather than the ion side."""
    assert "chrome yellow" not in MINERALS
    assert "[Pb+2]" in AQUEOUS_IONS       # the ion half was ready for it


# ---------------------------------------------------------------------------
# the arithmetic, on SYNTHETIC numbers so no chemistry is invented
# ---------------------------------------------------------------------------
def _synthetic(values: dict[str, tuple[float, float]]) -> dict[str, AqueousIon]:
    """A basis-consistent ion table with made-up values.

    ⚠ DELIBERATELY SYNTHETIC, and still so now that real data exists. Asserting
    a remembered literature Ksp would put an unsourced number in a test and call
    it verified; the physics assertion belongs above, against solubilities the
    repo can cite.
    """
    return {
        smi: AqueousIon(
            smiles=smi, formula=smi, cas="", name="", charge=0, elements={},
            Hf=Hf, Gf=Gf, S0=0.0, Cp=None, purpose="test fixture",
            crosscheck=0.0, source="synthetic aqueous basis (test fixture)",
        )
        for smi, (Hf, Gf) in values.items()
    }


def test_the_Ksp_arithmetic_is_right_once_the_basis_is_consistent():
    rock_salt = MINERALS["rock salt"]
    target = -10.0                             # kJ/mol, chosen to be round
    table = _synthetic({
        "[Na+]": (-240.0, rock_salt.Gf_solid + target - (-131.0)),
        "[Cl-]": (-167.0, -131.0),
    })
    out = solubility_product(rock_salt, table, T=T_REF)
    assert isinstance(out, SolubilityProduct)
    assert out.dG_diss == pytest.approx(target, abs=1e-9)
    assert out.ln_Ksp == pytest.approx(-target * 1000.0 / (R * T_REF), rel=1e-12)
    assert out.solubility() == pytest.approx(math.sqrt(out.Ksp), rel=1e-12)


def test_the_stoichiometric_root_handles_a_2_to_1_salt():
    """⚠ Ksp = (2s)^2 (s) for M2X, so s = (Ksp/4)^(1/3) -- not sqrt. Getting the
    exponent wrong is a decade-scale error that looks plausible."""
    soda = MINERALS["soda ash"]
    table = _synthetic({
        "[Na+]": (-240.0, -262.0),
        "O=C([O-])[O-]": (-677.0, -528.0),
    })
    out = solubility_product(soda, table)
    assert out.ions.count("[Na+]") == 2
    assert out.solubility() == pytest.approx((out.Ksp / 4.0) ** (1.0 / 3.0),
                                             rel=1e-10)


def test_dG_moves_with_temperature_by_vant_Hoff_from_the_298_K_pair():
    table = _synthetic({"[Na+]": (-240.0, -262.0), "[Cl-]": (-167.0, -131.0)})
    a = solubility_product("rock salt", table, T=T_REF)
    b = solubility_product("rock salt", table, T=T_REF + 50.0)
    dS = (a.dH_diss - a.dG_diss) / T_REF
    assert b.dG_diss == pytest.approx(a.dH_diss - (T_REF + 50.0) * dS, abs=1e-9)
    assert b.dH_diss == pytest.approx(a.dH_diss, abs=1e-12)


def test_an_endothermic_lattice_gets_MORE_soluble_when_heated():
    """Sign check on the van't Hoff slope, against the one salt whose direction
    is not a matter of opinion: AgCl dissolves endothermically, so warming the
    flask dissolves more of it."""
    cold = solubility_product("chlorargyrite", T=278.15)
    hot = solubility_product("chlorargyrite", T=348.15)
    assert cold.dH_diss > 0.0
    assert hot.solubility() > 10.0 * cold.solubility()


# ---------------------------------------------------------------------------
# history: the failure this arc started from, reproduced so it cannot recur
# ---------------------------------------------------------------------------
def test_a_SPECTATOR_zero_still_destroys_a_Ksp_and_the_engine_still_holds_one():
    """⚠⚠ THE FINDING THAT SHAPED M3, KEPT AS A TEST BECAUSE IT IS STILL LIVE.

    ``thermochemistry`` still prices ``[Na+]`` at exactly 0.0 as a spectator, and
    that is still correct: the cation appears on both sides of every proton
    transfer and cancels, which is why the five pH invariants hold. What changed
    is that the Ksp is no longer computed from it. Feed the spectator zero into
    the subtraction anyway and rock salt comes out 25 decades too insoluble --
    which is exactly what the basis guard above exists to prevent.
    """
    thermo = electrolyte_provider()
    assert thermo.get("[Na+]").Gf == 0.0
    assert "spectator" in thermo.get("[Na+]").source

    naive = _synthetic({
        "[Na+]": (0.0, 0.0),
        "[Cl-]": (thermo.get("[Cl-]").Hf, thermo.get("[Cl-]").Gf),
    })
    wrong = solubility_product("rock salt", naive)
    measured = MINERALS["rock salt"].fusion_law_bound[1]
    assert wrong.solubility() / measured < 1.0e-20

    # ...and the same lattice on the aqueous basis is inside the stated factor.
    right = solubility_product("rock salt")
    assert 1.0 / MEASURED_FACTOR < right.solubility() / measured < MEASURED_FACTOR
