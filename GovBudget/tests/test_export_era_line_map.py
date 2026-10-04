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
    assert scope.startswith("One row per era-keyed PB2017–PB2023 P-1 display line")
    assert "era_key (its pe_bli in budget_lines_decade)" in scope
    assert ("line_item_code (the budget line code printed on it, the pe_bli a same_program"
            " line's era citations carry)") in scope
    assert scope.endswith("Every row is a decision; none carries an amount.")


def test_scope_leaves_out_the_classified_programs_lines():
    """Final review T5: S1b loaded each era edition's Classified Programs
    lines under 9999999999 (7 per edition, 8 in PB2023; 50 in all), and the
    map selects era keys only, so "one row per P-1 display line" overstated
    it: /downloads/ counts 969 PB2017 lines against the 976 the P-1 prints."""
    scope = _DATASET_SCOPES["p1_era_line_map"]
    assert ("(the Classified Programs lines, loaded under 9999999999, are not"
            " in the map)") in scope


def test_decade_scope_says_what_an_era_rows_pe_bli_is():
    """Final review T3: 17,502 of the S5 export's 56,264 budget_lines_decade
    rows carry an era key as pe_bli, so the decade scope says so and points at
    the map for the printed code (spec §6.1: both meanings in the scopes)."""
    scope = _DATASET_SCOPES["budget_lines_decade"]
    assert ("(a PB2017–PB2023 P-1 row's pe_bli is its era_key; p1_era_line_map"
            " gives the code printed on it)") in scope
    assert scope.endswith("Editions are parallel publications, never reconciled.")


def test_scope_names_both_minters_of_era_rows_and_citations():
    """Task 19 fix rounds 1-2: era rows in budget_lines_decade and their
    citations come from the decade tier (same_program lines whose code has a
    program page) and from the F-15 family-history builder, so the scope must
    not read as if every line has both, nor as if only the first does."""
    scope = _DATASET_SCOPES["p1_era_line_map"]
    assert ("Only a same_program line whose code has a program page, or an F-15"
            " family-history line, has those rows and citations.") in scope


def test_the_f15_history_mints_era_rows_the_decade_tier_never_would():
    """Task 19 fix round 2: what made the round-1 "only" false. The F-15
    family-history builder appends a budget_lines_decade row (its leaves) and
    a workbook citation for every reviewed member line the decade tier has not
    minted: here PB2017 line 69, printed F0150P, a code with no program page,
    decided history_only. Its citation carries no pe_bli, so the scope claims
    the printed-code pe_bli only for same_program lines, and that holds only
    while every F-15 code decided same_program has a page."""
    import csv
    from pathlib import Path

    from govbudget.f15_funding_history import ERA_PROGRAM_CODES, MODERN_MEMBERS, build_history

    row = dict(pe_bli="3010F-AF-L69", edition=2017, exhibit="P-1", account="3010F",
               account_title="Aircraft Procurement, Air Force", organization="AF",
               budget_activity="07", budget_activity_title="Other Production Charges",
               title="F-15", amount_type="fy_2015_actuals", amount_thousands=10,
               sha256="a" * 64, sheet="Exhibit P-1", cells="J70",
               official_url="https://comptroller.war.gov/p1.xlsx", retrieved_at="2026-10-03")
    point = dict(pe_bli=row["pe_bli"], edition=2017, fy=2015, kind="actuals",
                 amount_type=row["amount_type"], n_source_rows=1, amount=10)
    _, citations, leaves, _ = build_history([row], [point], retrieved_at="2026-10-03")
    (fid,) = leaves
    assert leaves[fid]["pe_bli"] == "3010F-AF-L69"              # a decade row under the era key
    assert citations[fid]["kind"] == "workbook"
    assert citations[fid]["pe_bli"] is None                    # no printed code on it

    f15_codes = {code for codes in ERA_PROGRAM_CODES.values() for code in codes.values()}
    seed = Path(__file__).resolve().parents[1] / "dbt" / "seeds" / "p1_era_code_decisions.csv"
    with seed.open(encoding="utf-8") as fh:
        decided = {(r["line_item_code"], r["decision"]) for r in csv.DictReader(fh)
                   if r["line_item_code"] in f15_codes}
    off_the_decade_tier = {c for c, d in decided if d != "same_program" or c not in MODERN_MEMBERS}
    assert "F0150P" in off_the_decade_tier
    scope = _DATASET_SCOPES["p1_era_line_map"]
    if off_the_decade_tier:
        assert "or an F-15 family-history line, has those rows and citations" in scope
    # a same_program F-15 code without a page would get the builder's
    # pe_bli-less citations, and the line_item_code clause would be false
    assert all(c in MODERN_MEMBERS for c, d in decided if d == "same_program")


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
