"""T1 -- templates as data: the table, the generated module, and the two sets.

Fifty-seven templates were transcribed out of Python into a PSV, and a
transcription is exactly the kind of change that looks finished and is not: a
dropped `orders=` tuple silently un-declares a rate law, a dropped
`solid_catalyst` un-gates a heterogeneous catalyst, a dropped `hammett_rho`
turns a staged nitration into one stage. P4 measured all three from the other
side of the same hole in `TemplateSpec`.

The first half of T1 checked every row against the constructor it copied, field
for field. That test retired with the switch-over, because the constructors now
READ their row: comparing them would compare the table with itself.
`test_the_only_construction_sites_are_the_loaders` is what took its place, and it
is the inverse claim -- if no code outside the loader can build a template, then
every template IS a row, which is the property the equality check was defending.

Both surviving structural tests are about a SET rather than about whichever
field or file somebody remembered: the set of `ReactionTemplate` fields
(`test_the_columns_cover_every_field`) and the set of construction sites. That is
the half of P4's lesson that generalises.
"""

from __future__ import annotations

import importlib
import os
import re
import sys
from dataclasses import fields

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in ("src", "tools", "validation"):
    _full = os.path.join(_ROOT, _p)
    if _full not in sys.path:
        sys.path.insert(0, _full)

import build_templates as bt                                    # noqa: E402
import catalog_coverage as cc                                   # noqa: E402
from chemsim.reactions.template import ReactionTemplate         # noqa: E402
from chemsim.reactions.template_data import (                   # noqa: E402
    TEMPLATES,
    TemplateRecord,
    load_templates,
    template_classes,
    tier_counts,
)


@pytest.fixture(scope="module")
def rows():
    return bt.read_table()


# ---------------------------------------------------------------------------
# 1. THE TABLE IS THE ONLY PLACE A TEMPLATE COMES FROM
# ---------------------------------------------------------------------------


def test_the_only_construction_sites_are_the_loaders():
    """Nothing under `src/chemsim` builds a template except from a row.

    Found by walking the whole package, not by a list here, so a template
    hand-written into `synthesis.py` tomorrow fails this instead of quietly
    becoming a fifty-eighth template that no report counts and no extractor can
    write. The four loaders and the save-file path are named in
    `bt.CONSTRUCTION_SITES` with the reason each is allowed.
    """
    bt.check_construction_sites()
    assert set(bt.construction_sites()) == set(bt.CONSTRUCTION_SITES)


def test_every_public_constructor_returns_its_row(rows):
    """The 57 constructors are wrappers now: same name, same fields.

    They still exist and are still the public API -- `catalyst=`, `eta_a=`, `A=`
    are keyword arguments a caller can move and a row cannot be -- but called
    with their defaults they hand back exactly the row they are named for.
    """
    # NOTE: ``import_module`` and not ``from chemsim.reactions import
    # electrochemistry`` -- the package re-exports a BUNDLE FUNCTION of that
    # name, so the plain import binds the function and the four electrode
    # templates go missing. That is one of the three causes that made
    # ``ui.examples.full_library`` gather 50 of 57 (T1c); it reads the table
    # now, so this sweep is the last place the shadow can bite.
    mods = [importlib.import_module(m) for m in (
        "chemsim.reactions.library",
        "chemsim.reactions.synthesis",
        "chemsim.reactions.electrochemistry",
        "chemsim.properties.electrolyte",
    )]

    made = {}
    for mod in mods:
        for name in dir(mod):
            fn = getattr(mod, name)
            if (name.startswith("_") or not callable(fn)
                    or getattr(fn, "__module__", None) != mod.__name__):
                continue
            try:
                got = fn()
            except Exception:                              # noqa: BLE001, S112
                continue
            for tmpl in (got if isinstance(got, list) else [got]):
                if isinstance(tmpl, ReactionTemplate):
                    made.setdefault(tmpl.name, tmpl)

    data_fields = [f.name for f in fields(ReactionTemplate)
                   if not f.name.startswith("_")]
    for name, rec in TEMPLATES.items():
        assert name in made, f"{name} is a row no constructor hands back"
        for f in data_fields:
            assert getattr(made[name], f) == getattr(rec, f), (name, f)


def test_the_columns_cover_every_field():
    """A ``ReactionTemplate`` field with no column is a field the table drops."""
    bt.check_columns()
    data_fields = {f.name for f in fields(ReactionTemplate)
                   if not f.name.startswith("_")}
    assert set(bt.FIELD_DEFAULTS) == data_fields
    assert set(TemplateRecord.__dataclass_fields__) >= data_fields


def test_the_generated_module_is_current(rows):
    """A committed module that no longer matches the table is a stale number."""
    with open(bt.OUT, encoding="utf-8") as fh:
        assert fh.read() == bt.render(rows)


def test_the_table_and_the_module_hold_the_same_rows(rows):
    assert {r["name"] for r in rows} == set(TEMPLATES)
    assert len(TEMPLATES) == sum(cc.template_counts().values())


# ---------------------------------------------------------------------------
# 2. THE TIER, WHICH IS T2a's GUARD ARRIVING BEFORE THE ROWS IT GUARDS
# ---------------------------------------------------------------------------


def test_a_literal_row_cannot_enter_the_default_library():
    """S11: selectivity is a rate ratio between templates racing in one flask.

    A hundred extracted rows carrying class-policy kinetics would make every
    multi-template flask's selectivity noise, so `tier` is a gate rather than a
    label and the default side of it is the family.
    """
    base = TEMPLATES["fischer_esterification"]
    literal = TemplateRecord(**{**base.__dict__, "name": "extracted_row",
                                "tier": "literal"})
    try:
        TEMPLATES["extracted_row"] = literal
        assert "extracted_row" not in {t.name for t in load_templates()}
        assert "extracted_row" in {t.name for t in load_templates(tier="literal")}
        assert "extracted_row" in {t.name for t in load_templates(tier="any")}
    finally:
        del TEMPLATES["extracted_row"]


def test_every_row_today_is_a_family_row(rows):
    assert tier_counts() == {"family": len(rows)}


# ---------------------------------------------------------------------------
# 3. THE CLASS COLUMN AGAINST THE MAP IT REPLACES
# ---------------------------------------------------------------------------


def test_the_class_column_reproduces_the_template_backed_half_of_the_map():
    """`TEMPLATE_CLASSES` has 59 keys; 13 of them are integrator TERMS.

    A term -- precipitation, calcination, roasting -- has no SMARTS and cannot
    have a row here, because a lattice is not a graph. The other 46 are what the
    `class` column carries, and the switch-over deletes them from that file.
    """
    from_table = set(template_classes())
    from_map = set(cc.TEMPLATE_CLASSES)
    assert from_table <= from_map
    terms = sorted(from_map - from_table)
    assert len(from_table) == 46
    assert all("TERM" in cc.TEMPLATE_CLASSES[c] for c in terms), terms


def test_a_class_covered_by_a_family_names_every_member():
    """Two templates cover `hydroformylation`, and both have to be there.

    S11's measurement: the class's two catalog rows are one reaction with two
    regiochemistries, so a single template makes one of the row's two products
    and would look identical in a coverage table.
    """
    assert template_classes()["hydroformylation"] == (
        "hydroformylation_linear", "hydroformylation_branched")
    assert len(template_classes()["proton-transfer"]) == 8


# ---------------------------------------------------------------------------
# 4. WHAT THE TABLE MAY NOT SAY
# ---------------------------------------------------------------------------


def test_no_row_declares_both_an_order_and_a_reverse():
    """Rule 9, and the constructor enforces it -- this says the table obeys it.

    Detailed balance derives the reverse from k_f/k_r = K(T), which holds only
    because the exponents ARE the stoichiometric coefficients.
    """
    for rec in TEMPLATES.values():
        assert not (rec.orders is not None and rec.reversible), rec.name


def test_every_row_carries_its_barrier_s_provenance():
    for rec in TEMPLATES.values():
        assert rec.source.strip(), rec.name


def test_a_declared_order_has_one_exponent_per_reactant_slot():
    """The constructor checks it; building every row is what runs the check."""
    for rec in TEMPLATES.values():
        if rec.orders is None:
            continue
        assert len(rec.orders) == rec.build().n_reactant_slots, rec.name


def test_a_slot_written_out_three_times_names_one_species():
    """T12. A repeated slot MULTIPLIES, so its pattern must be unambiguous.

    `claus_comproportionation` writes its global stoichiometry out in full: 16
    hydrogen-sulfide slots and 8 sulfur-dioxide slots. The sulfur-dioxide slot
    was `[O]=[S]=[O]`, which also matches a SULFATE -- so the moment a flask
    held H2S at all, the builder tried every assignment of the two sulfates on
    the shelf to eight slots, 2**8 rewrites of a 24-molecule template, and the
    24-species closure that used to reach a fixpoint in four seconds took
    sixteen minutes. Nothing was wrong with the chemistry and nothing failed.

    The pool is the SHELF rather than a list written here, because the shelf is
    what a flask is charged from and a pattern that cannot tell two shelf rows
    apart is the defect whatever the numbers do.
    """
    from rdkit import Chem

    from chemsim.engine.shelf_data import ROSTER, SHELF

    pool = []
    for entry in SHELF:
        for smiles, _n in ROSTER[entry.id].charge:
            mol = Chem.MolFromSmiles(smiles)
            if mol is not None:
                pool.append((smiles, mol))
    assert len(pool) > 60

    for rec in TEMPLATES.values():
        counts: dict[str, int] = {}
        for slot in _reactant_slots(rec.smarts):
            counts[slot] = counts.get(slot, 0) + 1
        for slot, repeats in counts.items():
            if repeats < 3:
                continue
            query = Chem.MolFromSmarts(slot)
            assert query is not None, (rec.name, slot)
            hits = [s for s, m in pool if m.HasSubstructMatch(query)]
            assert len(hits) <= 1, (rec.name, slot, repeats, hits)


def _reactant_slots(smarts: str) -> list[str]:
    """The dot-separated reactant patterns, map numbers stripped."""
    out, depth, current = [], 0, ""
    for ch in smarts.split(">>")[0]:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "." and depth == 0:
            out.append(current)
            current = ""
        else:
            current += ch
    out.append(current)
    return [re.sub(r":\d+\]", "]", s) for s in out]


# ---------------------------------------------------------------------------
# T1b -- the row against the catalog step it claims.
# ---------------------------------------------------------------------------
# The two structural tests above ask about sets -- of fields, of construction
# sites -- and neither can ask whether a row's SMARTS still makes the products
# the catalog says it makes. That is what the per-template test files do, one
# file per template. `tools/check_template_products.py` asks it for every row at
# once, and these are the claims that make its committed artefact mean something
# rather than record whenever somebody last ran the generator.

import check_template_products as ctp                           # noqa: E402


@pytest.fixture(scope="module")
def product_report():
    return ctp.rows_report()[0]


def _on_disk() -> str:
    with open(ctp.OUT, encoding="utf-8", newline="") as fh:
        return fh.read().replace("\r\n", "\n")


def test_the_product_report_on_disk_is_what_the_current_code_writes(product_report):
    """The ratchet. A SMARTS edit that changes which species a row makes moves a
    verdict here and fails, which is the property the per-template test files
    hold one template at a time."""
    if not os.path.exists(ctp.OUT):
        pytest.skip("the artefact has not been generated in this checkout")
    assert _on_disk() == ctp.render(product_report), (
        "run python tools/check_template_products.py"
    )


def test_every_verdict_is_one_the_tool_defines(product_report):
    assert {v for _, v, *_ in product_report} <= set(ctp.RANK) | {"no-class"}
    assert len(product_report) == len(bt.read_table())


def test_no_row_fires_on_a_step_and_dies_in_the_rewrite(product_report):
    """`no-fire` is the verdict that means a defect: every slot found a
    candidate and no assignment survived, so the SMARTS matched a substructure
    rather than a substrate, or wrote a product that will not sanitise. It is
    zero today and this is what keeps it there. `no-substrate` is a different
    claim -- the class has no step exercising the row -- and is allowed."""
    bad = [name for name, verdict, *_ in product_report if verdict == "no-fire"]
    assert bad == [], bad


def test_the_load_bearing_rows_still_make_what_their_step_declares(product_report):
    """Named rather than counted: a count moves when the catalog gains a step,
    and these five are chains the engine is demonstrated on."""
    verdict = {name: v for name, v, *_ in product_report}
    for name in ("sulfur_combustion", "ammonia_synthesis", "water_gas_shift",
                 "wacker_oxidation", "oxidative_cleavage"):
        assert verdict[name] == "pass", (name, verdict[name])


def test_the_medium_is_three_species_and_it_reports_when_it_was_used(product_report):
    """The instrument's own trap, and the reason that column exists. The first
    version offered a row only what its step named, so `skraup_cyclisation` --
    whose homogeneous catalyst is spelled `[OH3+:99]` while the step names
    sulfuric acid -- came back refused, and so did a fermentation whose step
    does not list water. Both work in the engine. The pool is now those three
    and nothing else, and a row that needed them says so."""
    assert ctp.MEDIUM == ("O", "[OH3+]", "[OH-]")
    used = {name for name, _, _, med, *_ in product_report if med == "yes"}
    assert "skraup_cyclisation" in used
    assert used < {name for name, *_ in product_report}, (
        "if every row needs the medium, the pool has stopped discriminating"
    )


def test_a_slot_nothing_in_the_step_matches_is_no_substrate_and_not_a_defect():
    """The split that keeps `no-fire` meaningful. `assignments` returns None
    rather than an empty list, because "there was nothing to try" and "I tried
    and everything failed" are different findings about a row."""
    from chemsim.matter.molecule import Molecule

    table = {r["name"]: r for r in bt.read_table()}
    water = Molecule.from_smiles("O")
    assert ctp.assignments(bt.build(table["hydrosulfide_protonation"]), [water]) is None
    autoionization = bt.build(table["water_autoionization"])
    combos = ctp.assignments(autoionization, [water])
    assert combos and all(len(c) == autoionization.n_reactant_slots for c in combos)


def test_the_footer_keys_are_counted_from_the_rows_above_them(product_report):
    """T0.5's lesson, applied to a new report before it can drift: a generated
    file that ASSERTS a number stops agreeing with the rows it sits under, and a
    test pinning the number would pass forever. So count them here."""
    if not os.path.exists(ctp.OUT):
        pytest.skip("the artefact has not been generated in this checkout")
    keys = {}
    for line in _on_disk().splitlines():
        if line.startswith("#! "):
            key, _, value = line[3:].partition(" = ")
            keys[key.strip()] = int(value)
    assert sum(keys[v] for v in ("pass", "partial", "wrong-product", "no-fire",
                                 "no-substrate", "no-runnable-step",
                                 "no-class")) == len(product_report)
    for verdict in ("pass", "partial", "no-substrate"):
        assert keys[verdict] == sum(1 for _, v, *_ in product_report if v == verdict)
    assert keys["through_the_medium"] == sum(
        1 for r in product_report if r[3] == "yes")
    # Every row that did not pass is in exactly one cause bucket.
    unexplained = sum(1 for _, v, *_ in product_report
                      if v not in ("pass", "no-class", "no-substrate",
                                   "no-runnable-step"))
    assert (keys["missing_because_salt"] + keys["missing_because_stereo"]
            + keys["missing_because_other"]) == unexplained
    assert keys["missing_because_salt"] > 0 and keys["missing_because_stereo"] > 0


def test_the_two_systematic_causes_are_read_off_the_smiles_and_not_a_list():
    """`cause` is a rule over the missing SMILES, so a new row lands in the
    right bucket without anybody adding its name anywhere."""
    assert ctp.cause("[Na+].[O-]c1ccccc1") == "salt"
    assert ctp.cause("C[C@H](O)C(=O)O") == "stereo"
    assert ctp.cause("O=C(O)/C=C/c1ccccc1") == "stereo"
    assert ctp.cause("CCO") == "other"
    assert ctp.cause("") == ""
    # A salt AND a flat species missing is not a salt-only explanation.
    assert ctp.cause("[Na+].[O-]c1ccccc1,CCO") == "other"
