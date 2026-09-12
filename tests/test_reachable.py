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
