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
    """The constructors are wrappers now: same name, same fields.

    They still exist and are still the public API -- `catalyst=`, `eta_a=`, `A=`
    are keyword arguments a caller can move and a row cannot be -- but called
    with their defaults they hand back exactly the row they are named for.

    The sweep compares the two sets where they MEET, and neither direction is
    total. A row with no constructor is the point of the table -- T3 added eight
    of them as data alone, and demanding a constructor per row would have made
    "adding a template is adding a row" false for every one of them. A
    constructor with no row of its own name is the other end of the same thing:
    `fischer_esterification` called with `catalyst=` hands back a template named
    `fischer_esterification_acid`, a variant a row cannot spell. What is left is
    the drift that matters: a wrapper that no longer hands back the row it is
    named for.
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
    shared = sorted(set(made) & set(TEMPLATES))
    assert shared, "no constructor name matched a row: the sweep found nothing"
    for name in shared:
        for f in data_fields:
            assert getattr(made[name], f) == getattr(TEMPLATES[name], f), (name, f)


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


def test_the_tier_says_which_file_the_row_came_from(rows):
    """A row's tier and the file it lives in are the same fact, twice.

    `templates.psv` is hand-typed, one mechanism somebody argued for;
    `literal.psv` is regenerated by `tools/extract_templates.py` and rule 5
    forbids editing it. A `literal` row appearing in the hand-typed file would
    be a row nothing regenerates, and a `family` row in the generated one would
    be a row the next extraction run deletes.

    This replaces `test_every_row_today_is_a_family_row`, whose premise T2
    ended. That test pinned a count against a state of the world rather than a
    property, so it failed on exactly the change it existed to permit -- the
    same defect the two counts above it were rewritten to shed.
    """
    by_file = {path: {r["name"] for r in bt._read_one(path, set())}
               for path in bt.TABLES}
    for row in rows:
        want = bt.PSV if row["tier"] == "family" else bt.LITERAL_PSV
        assert row["name"] in by_file[want], (
            f"{row['name']} is tier {row['tier']} and is not in {want}")
    assert sum(tier_counts().values()) == len(rows)
    assert set(tier_counts()) <= set(bt.TIERS)


# ---------------------------------------------------------------------------
# 3. THE CLASS COLUMN AGAINST THE MAP IT REPLACES
# ---------------------------------------------------------------------------


def test_the_class_column_reproduces_the_template_backed_half_of_the_map():
    """`TEMPLATE_CLASSES` is the `class` column plus the integrator TERMS.

    A term -- precipitation, calcination, roasting -- has no SMARTS and cannot
    have a row here, because a lattice is not a graph. Everything else in the
    map is what the `class` column carries, and the switch-over deletes them
    from that file.

    The partition is DERIVED, not pinned. This test asserted `len(from_table)
    == 46` until T3 added four classes, and a pinned count is a number a session
    has to be told to increment: it says nothing about the split it is standing
    in for, and it fails on exactly the change it should be indifferent to.
    """
    from_table = set(template_classes())
    from_map = set(cc.TEMPLATE_CLASSES)
    assert from_table <= from_map
    terms = sorted(from_map - from_table)
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
    # The two walls are read through now, and the reading column says where.
    assert keys["in_the_engine_reading"] == sum(
        1 for r in product_report if r[7] == "engine")
    assert keys["in_the_engine_reading"] > 0


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


# ---------------------------------------------------------------------------
# 5. T2 -- THE EXTRACTED HALF OF THE TABLE
# ---------------------------------------------------------------------------


def _literal(rows):
    return [r for r in rows if r["tier"] == "literal"]


def test_every_extracted_row_makes_what_its_step_declares(rows, product_report):
    """T2's done-when, asserted rather than quoted.

    An extracted row's whole warrant is that it was run against the catalog
    step it came from and reproduced its declared products. A row that stops
    doing so has stopped being an extraction of anything, and a `partial` here
    would be a row whose SMARTS somebody edited by hand -- which is what rule 5
    forbids for a generated file.
    """
    verdict = {name: v for name, v, *_ in product_report}
    bad = [(r["name"], verdict[r["name"]]) for r in _literal(rows)
           if verdict[r["name"]] != "pass"]
    assert bad == [], bad


def test_the_extractor_does_not_read_its_own_output_as_coverage(rows):
    """The gate is the HAND-TYPED half, and it has to stay that way.

    `tools/extract_templates.py` skips a step whose class already has a
    template. Asking `TEMPLATE_CLASSES`, which counts every tier, makes the
    second run see the first run's 58 rows as coverage and refuse all of them:
    `literal.psv` empties, `--check` fails, and nothing about the first run of a
    fresh checkout is wrong -- so it is invisible until somebody runs it twice.
    The gate reads `FAMILY_TEMPLATE_CLASSES`, and the property that says so is
    that no extracted row carries a class a hand-typed row already carries.
    """
    family = set(template_classes(tier="family"))
    for row in _literal(rows):
        overlap = set(row["catalog_classes"]) & family
        assert not overlap, (row["name"], sorted(overlap))


def test_an_extracted_row_declares_nothing_detailed_balance_would_derive(rows):
    """Rule 9, and rule 8's other half.

    A policy cannot argue for a reverse rate, so an extracted row is
    irreversible and says so in one place; and it declares no rate orders, no
    Evans-Polanyi alpha and no Hammett rho, because each of those is a claim
    about a mechanism that a barrier solved from a temperature does not make.
    """
    for row in _literal(rows):
        assert row["reversible"] is False, row["name"]
        assert row["orders"] is None, row["name"]
        assert row["alpha"] == 0.0, row["name"]
        assert row["hammett_rho"] == 0.0, row["name"]
        assert row["source"].startswith("extracted:"), row["name"]


def test_every_extracted_row_builds_a_priced_reaction_or_names_what_is_unpriced(rows):
    """`pass` in the product report is a rewrite; this is a REACTION.

    The first version of this test built with ``thermo=None``, and
    ``build_network`` prices nothing in that configuration, so "58 of 58 build a
    reaction" was a statement about SMARTS only: 15 of those rows make a species
    with no thermochemistry and could never run. It now prices, with the
    electrolyte overlay where a flask would use it, and a row that builds
    nothing must say which species stopped it -- a data gap, counted in the
    table's footer, and never a rewrite that fails for a reason of its own.
    """
    import catalog as _cat
    import extract_templates as et

    compounds = _cat.load_compounds()
    steps = {et._name(s): s for s in _cat.load_steps()}
    silent = []
    runs = 0
    for row in _literal(rows):
        step = steps[row["name"]]
        r_ids = [x for x in step.reactants if x not in step.products]
        ok, unpriced = et.builds(bt.build(row), [compounds[x].smiles for x in r_ids])
        runs += ok
        if not ok and not unpriced:
            silent.append(row["name"])
    assert silent == [], silent
    with open(os.path.join(_ROOT, "data", "templates", "literal.psv"),
              encoding="utf-8") as fh:
        foot = dict(line[3:].rsplit(" = ", 1) for line in fh
                    if line.startswith("#! rows"))
    assert int(foot["rows_that_build_a_priced_reaction"]) == runs


def test_the_two_rows_hcn_used_to_kill_build_a_reaction(rows):
    """T28b. The test above measures the extracted tier; these two are FAMILY
    rows, and they are how the hole was found in the first place.

    `methane_ammoxidation` and `cyanide_imine_addition` reach `pass` against
    their catalog steps and, until hydrogen cyanide had a formation entry,
    built zero reactions between them: `build_network` prices every discovered
    species before it constructs anything, so an unpriceable PRODUCT takes the
    whole rewrite with it. The assertion is on the reaction and on the empty
    `unpriced`, not on a count -- the point is that the product resolves.
    """
    import contextlib
    import io as _io

    from chemsim.network import build_network
    from chemsim.properties.thermochemistry import ThermochemistryProvider

    charges = {
        "methane_ammoxidation": ["C", "N", "O=O"],
        "cyanide_imine_addition": ["CC=N", "C#N"],
    }
    by_name = {row["name"]: row for row in rows}
    for name, smiles in charges.items():
        template = bt.build(by_name[name])
        with contextlib.redirect_stdout(_io.StringIO()):
            net = build_network(smiles, [template], max_species=60,
                                thermo=ThermochemistryProvider())
        assert net.reactions, name
        assert net.unpriced == {}, (name, net.unpriced)
