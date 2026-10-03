"""p1_era_line_map ships as an uncited dataset (families piece 1, spec
2026-10-02 §4.4, §7; Task 19).

The map's rows are decisions, not money: it goes on the uncited ledger, its
scope sentence names both meanings of pe_bli the spec keeps apart (§6.1), an
undecided era line never ships, and era points can never ship without the map
that put them there.
"""
from __future__ import annotations

import duckdb
import pytest

from govbudget.export_site import (
    _CITED_DATASETS,
    _DATASET_SCOPES,
    ERA_MAP_DATASET,
    _export_p1_era_line_map,
)

MAP_DDL = (
    "create table p1_era_line_map ("
    " edition integer, account varchar, organization varchar,"
    " budget_activity varchar, era_key varchar, line_item_code varchar,"
    " filed_title varchar, program_key varchar, program_account varchar,"
    " program_org varchar, decision varchar, decision_id varchar,"
    " ruling varchar, keys_sha_ok boolean, successor_code varchar,"
    " source_document_sha256 varchar, source_cells varchar)"
)
ROWS = [
    (2018, "3010F", "AF", "01", "3010F-AF-L2", "ATA000", "F-35", "ATA000", None, None,
     "same_program", "ATA000|3010F||2017-2018", "R-DEC-ERA-SAME", True, None, "sha18", "J9"),
    (2017, "3010F", "AF", "01", "3010F-AF-L1", "ATA000", "F-35", "ATA000", None, None,
     "same_program", "ATA000|3010F||2017-2018", "R-DEC-ERA-SAME", True, None, "sha17", "J8"),
    (2017, "3010F", "AF", "05", "3010F-AF-L9", "F0150P", "LEGACY LINE", "F0150P", None, None,
     "history_only", "F0150P|3010F||2017-2017", "R-DEC-ERA-HISTORY", True, None, "sha17", "J20"),
    (2017, "0300D", "OSD", "01", "0300D-OSD-L50", "50", "INDIAN FINANCING ACT", None, None, None,
     "exclude_reused_code", "50|0300D||2017-2019", "R-DEC-ERA-B1", True, None, "sha17", "J60"),
    (2017, "2035A", "A", "01", "2035A-A-L3", "FY2017CR", "CR ADJUSTMENT", None, None, None,
     "exclude_placeholder", "FY2017CR|2035A||2017-2017", "R-DEC-ERA-EXCLUDE", True, None, "sha17", "J70"),
]
INSERT = "insert into p1_era_line_map values (" + ",".join("?" * 17) + ")"


def _con_with_map(rows=ROWS):
    con = duckdb.connect()
    con.execute(MAP_DDL)
    con.executemany(INSERT, rows)
    return con


def test_scope_is_registered_after_budget_lines_decade():
    names = list(_DATASET_SCOPES)
    assert ERA_MAP_DATASET == "p1_era_line_map"
    assert names.index("p1_era_line_map") == names.index("budget_lines_decade") + 1


def test_scope_names_both_meanings_of_pe_bli_and_carries_no_money():
    scope = _DATASET_SCOPES["p1_era_line_map"]
    assert scope.startswith("One row per PB2017–PB2023 P-1 display line")
    assert "era_key (its pe_bli in budget_lines_decade)" in scope
    assert "line_item_code (the budget line code printed on it, the pe_bli its era citations carry)" in scope
    assert scope.endswith("Every row is a decision; none carries an amount.")


def test_the_map_stays_on_the_uncited_ledger():
    assert "p1_era_line_map" not in _CITED_DATASETS


def test_exports_every_row_in_key_order(tmp_path):
    con = _con_with_map()
    assert _export_p1_era_line_map(con, tmp_path) == 5
    keys = duckdb.connect().execute(
        "select edition, era_key from read_parquet(?)",
        [str(tmp_path / "p1_era_line_map.parquet")],
    ).fetchall()
    assert keys == [
        (2017, "0300D-OSD-L50"), (2017, "2035A-A-L3"), (2017, "3010F-AF-L1"),
        (2017, "3010F-AF-L9"), (2018, "3010F-AF-L2"),
    ]


def test_refuses_an_undecided_line(tmp_path):
    undecided = list(ROWS[0])
    undecided[10] = "undecided"
    con = _con_with_map([tuple(undecided)])
    with pytest.raises(RuntimeError, match="undecided"):
        _export_p1_era_line_map(con, tmp_path)
    assert not (tmp_path / "p1_era_line_map.parquet").exists()


def test_refuses_era_points_without_the_map(tmp_path):
    con = duckdb.connect()
    con.execute("create table fct_program_decade_series (program_key varchar, map_basis varchar)")
    con.execute("insert into fct_program_decade_series values ('ATA000', 'era_line_map'), ('0601101E', 'native')")
    with pytest.raises(RuntimeError, match="era point"):
        _export_p1_era_line_map(con, tmp_path)


def test_no_map_and_no_era_points_ships_nothing_and_removes_a_stale_file(tmp_path):
    (tmp_path / "p1_era_line_map.parquet").write_bytes(b"stale")
    con = duckdb.connect()
    con.execute("create table fct_program_decade_series (program_key varchar, map_basis varchar)")
    con.execute("insert into fct_program_decade_series values ('0601101E', 'native')")
    assert _export_p1_era_line_map(con, tmp_path) is None
    assert not (tmp_path / "p1_era_line_map.parquet").exists()


def test_a_fixture_program_table_without_map_basis_is_not_an_error(tmp_path):
    con = duckdb.connect()
    con.execute("create table fct_program_decade_series (program_key varchar)")
    assert _export_p1_era_line_map(con, tmp_path) is None
