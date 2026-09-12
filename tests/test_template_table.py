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
    assert len(template_classes()["proton-transfer"]) == 6


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
