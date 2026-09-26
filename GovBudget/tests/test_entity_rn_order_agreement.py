"""R-DEC-ENTITYTIE-b (controller ruling, 2026-09-26): every recomputation of a
family's dominant member agrees with dim_entities.

dim_entities reads display_name from its `rn = 1` member, and rn's order is
now total (R-DEC-ENTITYTIE): total_obligation desc nulls last, then the
registration UEI — coalesce(parent_uei, recipient_uei) — ascending, then
recipient_uei ascending. Two copies of that rn=1 pick live outside the model:

  * site/scripts/gates/familylabel-recompute.py (gate 24 leg l) — the member
    whose parent-registration margin the leg reports beside the label;
  * src/govbudget/entity_label_review.py — the member whose registrations
    the published near-tie census ranks.

Both still stopped at the obligation, so on a tied family they could measure
a DIFFERENT member than the one whose name the model published. These tests
build dim_entities with the committed model's own SQL, feed every insertion
order of tied rows to all three, and require the copies to name the model's
member.
"""
from __future__ import annotations

import importlib.util
from itertools import permutations
from pathlib import Path

import duckdb
import pytest

from govbudget.entity_label_review import build_entity_label_review

ROOT = Path(__file__).resolve().parents[1]
GATE_SCRIPT = ROOT / "site" / "scripts" / "gates" / "familylabel-recompute.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The model's SQL, with ref()/macro substituted, from the model's own test —
# one substitution, not a second restatement of it.
_model_sql = _load(
    "_dim_entities_tiebreak", ROOT / "tests" / "test_dbt_entity_display_tiebreak.py"
)._model_sql
_gate = _load("_familylabel_recompute", GATE_SCRIPT)

XWALK_COLS = (
    "recipient_uei varchar, recipient_name varchar, parent_uei varchar,"
    " parent_name varchar, family_key varchar, method varchar,"
    " confidence varchar, total_obligation double"
)


def _x(family, recipient_uei, recipient_name, parent_uei, parent_name, total):
    return (recipient_uei, recipient_name, parent_uei, parent_name, family,
            "parent_name", "high", total)


# Two tied families, each shaped so the two tied members' registrations tell
# them apart: the model's member has ONE registration (margin 1.0, not a near
# tie); its tied sibling has two within 15% (a near tie).
XWALK = [
    # Tie across two parents: the LOWER registration (PA) is the model's
    # member, though R1 is the lower recipient_uei.
    _x("FAM", "R1", "SUB ONE", "PB", "ALPHA PARENT", 100.0),
    _x("FAM", "R2", "SUB TWO", "PA", "ZULU PARENT", 100.0),
    # Tie on ONE registration (PP): recipient_uei closes it — R4.
    _x("FAM2", "R8", "EIGHT SUB", "PP", "PP HOLDINGS", 30.0),
    _x("FAM2", "R4", "FOUR SUB", "PP", None, 30.0),
]
MODEL_MEMBER = {"FAM": "R2", "FAM2": "R4"}
MODEL_LABEL = {"FAM": "ZULU PARENT", "FAM2": "FOUR SUB"}

TX = [
    # recipient_uei, recipient_name, parent_uei, parent_name, obligation
    ("R2", "SUB TWO", "PA", "ZULU PARENT", 100.0),
    ("R1", "SUB ONE", "PB", "ALPHA PARENT", 51.0),
    ("R1", "SUB ONE", "PX", "X-RAY PARENT", 49.0),
    ("R4", "FOUR SUB", "PP", "PP HOLDINGS", 30.0),
    ("R8", "EIGHT SUB", "PP", "PP HOLDINGS", 16.0),
    ("R8", "EIGHT SUB", "PQ", "QUEBEC HOLDINGS", 14.0),
]


@pytest.fixture()
def lake(tmp_path):
    d = tmp_path / "contracts" / "fy=2025"
    d.mkdir(parents=True)
    con = duckdb.connect()
    con.execute(
        "create table t (recipient_uei varchar, recipient_name varchar,"
        " recipient_parent_uei varchar, recipient_parent_name varchar,"
        " federal_action_obligation varchar)"
    )
    con.executemany(
        "insert into t values (?, ?, ?, ?, ?)",
        [(u, n, pu, pn, str(o)) for u, n, pu, pn, o in TX],
    )
    con.execute(f"copy t to '{d / 'part.parquet'}' (format parquet)")
    con.close()
    return [str(tmp_path / "contracts" / "fy=*" / "*.parquet")]


def _warehouse(xwalk_rows) -> duckdb.DuckDBPyConnection:
    """entity_xwalk in the given row order, dim_entities built from it by the
    committed model SQL, fct_award_transactions from TX."""
    con = duckdb.connect(config={"threads": 4})
    con.execute(f"create table entity_xwalk ({XWALK_COLS})")
    con.executemany("insert into entity_xwalk values (?, ?, ?, ?, ?, ?, ?, ?)", xwalk_rows)
    con.execute("create view xwalk as select * from entity_xwalk")
    con.execute("create table dim_entities as " + _model_sql())
    con.execute(
        "create table fct_award_transactions (recipient_uei varchar,"
        " recipient_parent_uei varchar, recipient_parent_name varchar,"
        " obligation double)"
    )
    con.executemany(
        "insert into fct_award_transactions values (?, ?, ?, ?)",
        [(u, pu, pn, o) for u, _n, pu, pn, o in TX],
    )
    return con


ORDERS = list(permutations(XWALK))


def test_the_model_names_the_expected_member_in_every_order():
    for rows in ORDERS:
        con = _warehouse(list(rows))
        labels = dict(con.execute(
            "select family_key, display_name from dim_entities"
        ).fetchall())
        con.close()
        assert labels == MODEL_LABEL


def test_the_gate_helper_measures_the_models_member_in_every_order(lake):
    for rows in ORDERS:
        con = _warehouse(list(rows))
        out = _gate.recompute(con, lake, [])
        con.close()
        by_family = {f["family_key"]: f for f in out["families"]}
        assert {k: f["dominant_uei"] for k, f in by_family.items()} == MODEL_MEMBER, rows
        # The helper's member IS the one whose name the model published.
        assert {k: f["display_name"] for k, f in by_family.items()} == MODEL_LABEL
        # …so it reports that member's margin: one registration each.
        assert {k: f["margin"] for k, f in by_family.items()} == {"FAM": 1.0, "FAM2": 1.0}
        assert out["unmeasured"] == []


def test_the_census_ranks_the_models_member_in_every_order():
    for rows in ORDERS:
        con = _warehouse(list(rows))
        # Neither model member has a second registration; either tied sibling
        # would have added a near tie (51 vs 49, 16 vs 14).
        assert build_entity_label_review(con, ()) == {
            "near_ties": 0, "families": 2, "threshold_pct": 15,
        }, rows
        con.close()
