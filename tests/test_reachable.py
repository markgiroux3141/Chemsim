"""T4 -- the reachability sweep, asserted without re-running its 35 minutes.

The sweep itself is a committed artefact (`data/catalog/derived/reachable.psv`)
because 630 fixpoint expansions cost more than every other check in this repo put
together. What is cheap and worth pinning is everything AROUND it: the pair
enumeration, the credit rule that keeps a reverse reaction from counting as a
second capability, the reader, and -- the thing G3 wrote `test_playable.py` for --
that the artefact on disk is the shape the current code produces and the report
quotes it rather than a hand-typed number.

The chemistry the sweep measures is covered where it lives: `test_ui.py` for the
bench library, `test_shelf.py` for the natural tier, `test_robustness.py` for the
bounds a capped pair reports.
"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in ("src", "tools", "validation"):
    _full = os.path.join(_ROOT, _p)
    if _full not in sys.path:
        sys.path.insert(0, _full)

import build_reachable as br  # noqa: E402


def test_a_reverse_reaction_is_not_a_second_capability():
    """Detailed balance derives the reverse, so a shelf reaching one reaches both.

    Counting `fischer_esterification_rev` as its own template would make the
    fired count read high by however many reversible templates fired, against a
    denominator of 57 that has no `_rev` rows in it at all.
    """
    assert br.credited({"esterification", "esterification_rev"}) == {"esterification"}
    assert br.credited({"a_rev", "b"}) == {"a", "b"}
    assert br.credited(set()) == set()


def test_the_sweep_enumerates_every_pair_of_the_natural_tier_in_a_fixed_order():
    """Deterministic, or the artefact's diff is noise. And it is CHARGEABLE
    rows: seven of the natural tier are refused a price by the element floor and
    cannot go in a flask at all, so a pair of them is not a thing a player has."""
    from chemsim.engine import inventory as inv

    natural = [i for i in inv.shelf(("natural",)) if i.chargeable]
    pairs = br.pairs_of(natural)
    assert len(pairs) == len(natural) * (len(natural) - 1) // 2
    assert pairs == br.pairs_of(list(reversed(natural))), "order must not matter"
    assert all(a.id < b.id for a, b in pairs)
    assert all(i.chargeable for p in pairs for i in p)


def test_the_reader_returns_nothing_rather_than_guessing(tmp_path):
    """A missing artefact is not an error and not a fallback number.

    `_PLAYABLE_FOOTER` exists because this report once cross-quoted another
    generated file from memory and drifted to "36 runnable, 12 playable" against
    44 and 21. The rule that came out of it: read the file or say you have not.
    """
    assert br.read_summary(tmp_path / "nothing.psv") == {}

    import catalog_coverage as cc

    if not br.OUT.exists():
        pytest.skip("the artefact has not been generated in this checkout")
    got = cc.reachable_headline()
    assert 0 < got["templates_fired"] <= got["templates"]
    assert got["capped_pairs"] + got["inert_pairs"] <= got["pairs"]
    assert got["max_species"] == br.MAX_SPECIES, (
        "the report must quote the cap the sweep actually used"
    )


def test_the_artefact_on_disk_is_the_shape_the_current_code_writes():
    """The G3 rule: a generated file with no assertion behind it is a snapshot
    of whenever somebody last ran the generator. This does not re-run the sweep
    -- it checks that every key the report reads is in the file, which is what
    breaks when a session adds a column and forgets to regenerate."""
    if not br.OUT.exists():
        pytest.skip("the artefact has not been generated in this checkout")
    got = br.read_summary()
    for key in ("natural_rows", "pairs", "distinct_reactions", "templates_fired",
                "capped_pairs", "inert_pairs", "templates", "tier"):
        assert key in got, f"{key} missing from {br.OUT}"
    assert got["tier"] == "family"
    rows = [ln for ln in br.OUT.read_text(encoding="utf-8").splitlines()
            if ln and not ln.startswith("#")]
    assert len(rows) == int(got["pairs"])


# ---------------------------------------------------------------------------
# T6 -- the classifier over the sweep's silent list.
# ---------------------------------------------------------------------------

import classify_silent as cs  # noqa: E402


def test_a_top_level_dot_separates_slots_and_a_nested_one_does_not():
    """The splitter is the whole instrument: get it wrong and a template's
    reactant count is wrong, so its witness is wrong, so its label is wrong."""
    assert cs.slots("[C:1].[O:2]>>[C:1][O:2]") == ["[C:1]", "[O:2]"]
    # A recursive SMARTS carries dots that are not separators.
    one = "[C;$(C.C):1]>>[C:1]"
    assert cs.slots(one) == ["[C;$(C.C):1]"]
    # Twenty-four reactant slots is not a bug: claus_comproportionation writes
    # eight sulfur rings out atom by atom.
    rec = cs.TEMPLATES["claus_comproportionation"]
    assert len(cs.slots(rec.smarts)) == 24


def test_atom_map_numbers_do_not_split_one_missing_substrate_into_two():
    """Four templates want carbon monoxide and two of them spell its slot with
    different map numbers. Grouping on the raw text reports two gaps, not one."""
    assert cs.unmapped("[C-:1]#[O+:2]") == cs.unmapped("[C-:3]#[O+:4]")
    assert cs.unmapped("[C-:1]#[O+:2]") == "[C-]#[O+]"


def test_the_closure_flask_is_the_small_molecule_half_and_nothing_else():
    """The one hand constant in the tool. The shelf jumps from sulfur's eight
    heavy atoms to alpha-pinene's ten, so any threshold in between picks the
    same rows -- and if a future shelf row lands in the gap, this fails."""
    rows = cs.natural_rows()
    small = cs.small_rows(rows)
    ids = {i.id for i in small}
    assert "sulfur-s8" in ids
    assert "glucose" not in ids
    assert "triolein" not in ids
    assert len(small) < len(rows)


def test_the_artefact_labels_every_template_the_sweep_named_as_silent():
    """The two files are one measurement: a template that stops being silent
    must leave this artefact, and one that starts must arrive in it."""
    if not cs.OUT.exists() or not cs.REACHABLE.exists():
        pytest.skip("the artefacts have not been generated in this checkout")
    labelled = {}
    for line in cs.OUT.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        cells = [c.strip() for c in line.split("|")]
        labelled[cells[0]] = cells[1]
    assert set(labelled) == set(cs.silent_names())
    assert set(labelled.values()) <= {"no-substrate", "needs-more-than-a-pair",
                                      "cannot-fire"}


def test_the_closure_reported_in_the_artefact_is_a_fixpoint_not_a_cap():
    """Every 'the shelf cannot make this' in the file rests on the closure. A
    non-zero frontier would turn each of them into an estimate, silently."""
    if not cs.OUT.exists():
        pytest.skip("the artefact has not been generated in this checkout")
    keys = {}
    for line in cs.OUT.read_text(encoding="utf-8").splitlines():
        if line.startswith("#! "):
            key, _, value = line[3:].partition(" = ")
            keys[key.strip()] = value.strip()
    assert keys["closure_frontier"] == "0"
    assert int(keys["closure_species"]) > int(keys["closure_rows"])


def _artefact():
    keys, rows = {}, []
    for line in cs.OUT.read_text(encoding="utf-8").splitlines():
        if line.startswith("#! "):
            key, _, value = line[3:].partition(" = ")
            keys[key.strip()] = value.strip()
        elif line and not line.startswith("#"):
            rows.append([c.strip() for c in line.split("|")])
    return keys, rows


def test_the_one_generation_tier_reports_the_bound_the_closure_does_not_need():
    """The closure is a fixpoint and says nothing more is needed. The tier that
    reaches past it -- a big row plus the closure, one generation -- is bounded,
    and a bound that does not report itself is the one thing rule 10 forbids."""
    if not cs.OUT.exists():
        pytest.skip("the artefact has not been generated in this checkout")
    keys, rows = _artefact()
    assert "step_frontier" in keys and "pool_unpriceable" in keys
    # A witness naming a @1 tier spends two sources by construction, so it can
    # never be the group that says a flask the PAIR sweep held yielded nothing.
    for row in rows:
        if cs.STEP in row[4]:
            assert row[1] != "cannot-fire", row[0]


def test_a_template_short_of_two_substrates_names_both_of_them():
    """Charging a template to its first missing slot only is what put an
    aromatic aldehyde at the top of the work order on the strength of three
    templates, one of which it would have unblocked."""
    if not cs.OUT.exists():
        pytest.skip("the artefact has not been generated in this checkout")
    keys, rows = _artefact()
    blockers = [row[5] for row in rows if row[5]]
    assert any(" + " in b for b in blockers)
    assert (int(keys["substrates_that_unblock_alone"])
            <= sum(len(b.split(" + ")) for b in blockers))
