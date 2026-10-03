"""Families piece 1, Task 17 — the decade tier reads fct_program_decade_series.

Spec docs/superpowers/specs/2026-10-02-era-procurement-history-design.md §6.1.
_build_decade_citation_rows is driven directly against a hermetic DuckDB
fixture (no Postgres): a program table carrying native rows, a two-line era
chain (one PB2019 program key summed over two era lines in two budget
activities), a collision chain filed under DSS and pinned to the DCSA page of
'20', a history-only chain, and an out-of-scope chain, plus the reviewed map
and the jbooks lake parquets the tier joins.

Pinned here:
  * an era leaf's fact id is fact_id_workbook over its OWN era key, so every
    era fact F-15 already published is reproduced, never re-minted;
  * an era citation's pe_bli is the printed code; its budget_lines_decade
    row keeps the era key;
  * a multi-line era sum mints decade_era_map with the §6.1 formula and
    inputs sorted by fact id, and the formula passes
    program_pdf_receipts.additive_budget_formula;
  * F-15's PB2018 FY2016 actuals cell (the live lake's two rows) mints
    exactly the decade_era_map receipt tests/test_f15_era_identity.py
    (Task 4, V5) injects: same fact id, formula and inputs, so V5's
    literal strings cannot drift from _decade_era_map_formula unnoticed;
  * the collision chain lands on '20-DCSA' (matched through the pin, not
    the row's own DSS organization), DTRA's on '20-DTRA';
  * history-only and out-of-scope chains mint nothing;
  * native rows come out exactly as without any era rows, in
    fct_decade_series' own row order;
  * fct_decade_series without fct_program_decade_series raises (and the
    reverse), and era rows without p1_era_line_map raise.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from govbudget.export_site import (
    _build_decade_citation_rows,
    _decade_era_map_formula,
    fact_id_derived,
    fact_id_workbook,
)
from govbudget.program_pdf_receipts import additive_budget_formula

SHA19 = "sha_pb2019_p1"
SHA24 = "sha_pb2024_r1"

# Lake budget_lines rows (every lake column is VARCHAR, as in the live lake).
# (exhibit, fiscal_year, account, account_title, organization,
#  budget_activity, budget_activity_title, pe_bli, title, amount_type,
#  amount_thousands, source_document_id, source_sheet, source_cells)
LAKE_ROWS = [
    # native R-1 grains (PB2024 FY2022 actuals), single source each
    ("R-1", "2024", "0400", "RDT&E, Defense-Wide", "DARPA", "01",
     "Basic Research", "0601101E", "Defense Research Sciences",
     "fy_2022_actuals", "100000", "8", "Exhibit R-1", "J4"),
    ("R-1", "2024", "0400", "RDT&E, Defense-Wide", "DARPA", "02",
     "Applied Research", "0602702E", "Tactical Technology",
     "fy_2022_actuals", "5000", "8", "Exhibit R-1", "J5"),
    # era chain XB0100: two lines (BA 01 and BA 05) in PB2019, one code
    ("P-1", "2019", "3010F", "Aircraft Procurement, Air Force", "AF", "01",
     "Combat Aircraft", "3010F-AF-L5", "XB Aircraft", "fy_2017_actuals",
     "300", "7", "Exhibit P-1", "Q9"),
    ("P-1", "2019", "3010F", "Aircraft Procurement, Air Force", "AF", "05",
     "Modification of Aircraft", "3010F-AF-L6", "XB Aircraft Mods",
     "fy_2017_actuals", "200", "7", "Exhibit P-1", "Q10"),
    # the same chain's PB2019 request, one line only → single-source grain
    ("P-1", "2019", "3010F", "Aircraft Procurement, Air Force", "AF", "01",
     "Combat Aircraft", "3010F-AF-L5", "XB Aircraft", "fy_2019_total",
     "400", "7", "Exhibit P-1", "U9"),
    # collision code '20': DSS (pinned → DCSA) and DTRA (pinned → DTRA)
    ("P-1", "2019", "0300D", "Procurement, Defense-Wide", "DSS", "01",
     "Major Equipment", "0300D-DSS-L21", "Major Equipment",
     "fy_2017_actuals", "1234", "7", "Exhibit P-1", "Q30"),
    ("P-1", "2019", "0300D", "Procurement, Defense-Wide", "DTRA", "01",
     "Major Equipment", "0300D-DTRA-L23", "Vehicles",
     "fy_2017_actuals", "77", "7", "Exhibit P-1", "Q32"),
    # history-only chain HH0001 and out-of-scope chain XC0200
    ("P-1", "2019", "3010F", "Aircraft Procurement, Air Force", "AF", "01",
     "Combat Aircraft", "3010F-AF-L9", "Retired Line", "fy_2017_actuals",
     "50", "7", "Exhibit P-1", "Q13"),
    ("P-1", "2019", "3010F", "Aircraft Procurement, Air Force", "AF", "01",
     "Combat Aircraft", "3010F-AF-L10", "Other Line", "fy_2017_actuals",
     "60", "7", "Exhibit P-1", "Q14"),
]

# p1_era_line_map rows the tier reads: (edition, account, organization,
# budget_activity, era_key, line_item_code, program_key, program_account,
# program_org, decision)
MAP_ROWS = [
    (2019, "3010F", "AF", "01", "3010F-AF-L5", "XB0100", "XB0100", None, None, "same_program"),
    (2019, "3010F", "AF", "05", "3010F-AF-L6", "XB0100", "XB0100", None, None, "same_program"),
    (2019, "0300D", "DSS", "01", "0300D-DSS-L21", "20", "20", "0300D", "DCSA", "same_program"),
    (2019, "0300D", "DTRA", "01", "0300D-DTRA-L23", "20", "20", "0300D", "DTRA", "same_program"),
    (2019, "3010F", "AF", "01", "3010F-AF-L9", "HH0001", "HH0001", None, None, "history_only"),
    (2019, "3010F", "AF", "01", "3010F-AF-L10", "XC0200", "XC0200", None, None, "same_program"),
]


def wb(org, ba, era_key, at, account="3010F", sha=SHA19, exhibit="P-1", ed=2019):
    return fact_id_workbook(sha, exhibit, ed, account, org, ba, era_key, at)


L5_ACT = wb("AF", "01", "3010F-AF-L5", "fy_2017_actuals")
L6_ACT = wb("AF", "05", "3010F-AF-L6", "fy_2017_actuals")
L5_REQ = wb("AF", "01", "3010F-AF-L5", "fy_2019_total")
DSS_ACT = wb("DSS", "01", "0300D-DSS-L21", "fy_2017_actuals", account="0300D")
DTRA_ACT = wb("DTRA", "01", "0300D-DTRA-L23", "fy_2017_actuals", account="0300D")
NATIVE = fact_id_workbook(SHA24, "R-1", 2024, "0400", "DARPA", "01",
                          "0601101E", "fy_2022_actuals")
NATIVE2 = fact_id_workbook(SHA24, "R-1", 2024, "0400", "DARPA", "02",
                           "0602702E", "fy_2022_actuals")
ERA_SUM = fact_id_derived("decade_era_map", "XB0100|||2019", "fy_2017_actuals")
ERA_FORMULA = (
    "sum(budget_lines.amount_thousands where era_line_map='XB0100'"
    " and amount_type=fy_2017_actuals and edition=2019)"
)

# fct_program_decade_series rows: (program_key, fy, edition_year,
# amount_type_kind, amount, amount_type, account, organization,
# n_source_rows, source_fact_id, map_basis)
NATIVE_GRAINS = [
    ("0601101E", 2022, 2024, "actuals", 100000.0, "fy_2022_actuals", None,
     None, 1, NATIVE, "native"),
]
NATIVE2_GRAIN = ("0602702E", 2022, 2024, "actuals", 5000.0, "fy_2022_actuals",
                 None, None, 1, NATIVE2, "native")
ERA_GRAINS = [
    ("XB0100", 2017, 2019, "actuals", 500.0, "fy_2017_actuals", None, None,
     2, None, "era_line_map"),
    ("XB0100", 2019, 2019, "request", 400.0, "fy_2019_total", None, None,
     1, L5_REQ, "era_line_map"),
    ("20", 2017, 2019, "actuals", 1234.0, "fy_2017_actuals", None, "DCSA",
     1, DSS_ACT, "era_line_map"),
    ("20", 2017, 2019, "actuals", 77.0, "fy_2017_actuals", None, "DTRA",
     1, DTRA_ACT, "era_line_map"),
    ("HH0001", 2017, 2019, "actuals", 50.0, "fy_2017_actuals", None, None,
     1, wb("AF", "01", "3010F-AF-L9", "fy_2017_actuals"), "era_history_only"),
    ("XC0200", 2017, 2019, "actuals", 60.0, "fy_2017_actuals", None, None,
     1, wb("AF", "01", "3010F-AF-L10", "fy_2017_actuals"), "era_line_map"),
]
SCOPE = {"0601101E", "XB0100", "20", "HH0001"}  # XC0200 is NOT a page

# F-15's PB2018 FY2016 actuals cell, copied from the live lake (2026-10-02,
# read-only; real sha256): PB2018 P-1 lines 23 (BA 05) and 79 (BA 07), both
# printing F01500, both fy_2016_base_oco, $596,932K + $0K.
# tests/test_f15_era_identity.py (Task 4, V5) injects a decade_era_map
# receipt for exactly this cell with its own literal key and formula; the
# tier must mint the same strings or V5's fresh-state proof stops describing
# what S4 ships. Only test_f15_cell_mints_exactly_the_receipt_v5_injects
# loads these rows.
SHA18 = "863ea56b3d32294c4c61f12ec6e99622d74d12cfcce6a9c7c7c1e17e439cb318"
F15_LAKE_ROWS = [
    ("P-1", "2018", "3010F", "Aircraft Procurement, Air Force", "AF", "05",
     "Modification of Inservice Aircraft", "3010F-AF-L23", "F-15",
     "fy_2016_base_oco", "596932", "9", "Exhibit P-1", "O904"),
    ("P-1", "2018", "3010F", "Aircraft Procurement, Air Force", "AF", "07",
     "Aircraft Supt Equipment & Facilities", "3010F-AF-L79", "F-15",
     "fy_2016_base_oco", "0", "9", "Exhibit P-1", "O963"),
]
F15_MAP_ROWS = [
    (2018, "3010F", "AF", "05", "3010F-AF-L23", "F01500", "F01500", None, None, "same_program"),
    (2018, "3010F", "AF", "07", "3010F-AF-L79", "F01500", "F01500", None, None, "same_program"),
]
F15_GRAIN = ("F01500", 2016, 2018, "actuals", 596932.0, "fy_2016_base_oco",
             None, None, 2, None, "era_line_map")
# The strings V5 injects for this cell (tests/test_f15_era_identity.py:
# fact_id_derived("decade_era_map", f"{code}|||{edition}", amount_type), the
# era_line_map formula, inputs = its TARGET_INPUTS).
V5_FID = fact_id_derived("decade_era_map", "F01500|||2018", "fy_2016_base_oco")
V5_FORMULA = (
    "sum(budget_lines.amount_thousands where era_line_map='F01500'"
    " and amount_type=fy_2016_base_oco and edition=2018)"
)
V5_INPUTS = ["28f53c8d681494cc", "cce72b42a96bfcb7"]


def _write_lake(base: Path, extra_rows: list[tuple] | None = None) -> None:
    lake = base / "parquet" / "jbooks"
    lake.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        con.execute(
            "create table b (exhibit varchar, fiscal_year varchar, account varchar,"
            " account_title varchar, organization varchar, budget_activity varchar,"
            " budget_activity_title varchar, pe_bli varchar, title varchar,"
            " amount_type varchar, amount_thousands varchar,"
            " source_document_id varchar, source_sheet varchar,"
            " source_cells varchar)"
        )
        con.executemany(f"insert into b values ({','.join('?' * 14)})",
                        LAKE_ROWS + (extra_rows or []))
        con.execute(f"copy b to '{lake / 'budget_lines.parquet'}' (format parquet)")
        con.execute(
            "create table d (id varchar, org varchar, exhibit_family varchar,"
            " fiscal_year varchar, title varchar, source_url varchar,"
            " sha256 varchar, bytes varchar, downloaded_at varchar,"
            " rel_path varchar)"
        )
        con.executemany(f"insert into d values ({','.join('?' * 10)})", [
            ("7", "DOD", "procurement", "2019", "p1_display",
             "https://example.mil/fy2019/p1_display.xlsx", SHA19, "1000",
             "2026-07-01 00:00:00", "fy2019/p1_display.xlsx"),
            ("8", "DARPA", "rdte", "2024", "r1_display",
             "https://example.mil/fy2024/r1_display.xlsx", SHA24, "1000",
             "2026-07-01 00:00:00", "fy2024/r1_display.xlsx"),
            ("9", "DoD", "rollup", "2018", "p1_display.xlsx",
             "https://comptroller.war.gov/Portals/45/Documents/defbudget/"
             "fy2018/p1_display.xlsx", SHA18, "904708",
             "2026-07-03 07:55:51", "fy2018/dod/p1_display.xlsx"),
        ])
        con.execute(f"copy d to '{lake / 'documents.parquet'}' (format parquet)")
    finally:
        con.close()


def _make_warehouse(
    tmp_path: Path,
    *,
    grains: list[tuple] | None = None,
    line_grains: list[tuple] | None = None,
    line_table: bool = True,
    program_table: bool = True,
    era_map: bool = True,
    extra_lake: list[tuple] | None = None,
    extra_map: list[tuple] | None = None,
) -> Path:
    db = tmp_path / "wh.duckdb"
    con = duckdb.connect(str(db))
    try:
        # the line table still exists in every real warehouse
        if line_table:
            con.execute(
                "create table fct_decade_series (pe_bli varchar, fy integer,"
                " edition_year integer, amount_type_kind varchar, amount double,"
                " amount_type varchar, account varchar, organization varchar,"
                " n_source_rows bigint, source_fact_id varchar)"
            )
            con.executemany(
                "insert into fct_decade_series values (?,?,?,?,?,?,?,?,?,?)",
                [g[:10] for g in (NATIVE_GRAINS if line_grains is None else line_grains)],
            )
        if program_table:
            con.execute(
                "create table fct_program_decade_series (program_key varchar,"
                " fy integer, edition_year integer, amount_type_kind varchar,"
                " amount double, amount_type varchar, account varchar,"
                " organization varchar, n_source_rows bigint,"
                " source_fact_id varchar, map_basis varchar)"
            )
            rows = NATIVE_GRAINS + ERA_GRAINS if grains is None else grains
            if rows:
                con.executemany(
                    "insert into fct_program_decade_series values"
                    " (?,?,?,?,?,?,?,?,?,?,?)", rows,
                )
        if era_map:
            con.execute(
                "create table p1_era_line_map (edition integer, account varchar,"
                " organization varchar, budget_activity varchar,"
                " era_key varchar, line_item_code varchar,"
                " program_key varchar, program_account varchar,"
                " program_org varchar, decision varchar)"
            )
            con.executemany(
                "insert into p1_era_line_map values (?,?,?,?,?,?,?,?,?,?)",
                MAP_ROWS + (extra_map or []),
            )
        # '20' is organization-split: two PB2026 pages, 20-DCSA and 20-DTRA
        con.execute(
            "create table dim_programs (pe_bli varchar, account varchar,"
            " account_title varchar, org varchar, exhibit_family varchar)"
        )
        con.execute(
            "insert into dim_programs values"
            " ('20', '0300D', 'Procurement, Defense-Wide', 'DCSA', 'procurement'),"
            " ('20', '0300D', 'Procurement, Defense-Wide', 'DTRA', 'procurement')"
        )
    finally:
        con.close()
    _write_lake(tmp_path, extra_lake)
    return db


def _build(db: Path, scope=SCOPE):
    return _build_decade_citation_rows(
        duckdb_path=db, existing_fids=set(), scope_pes=set(scope),
    )


@pytest.fixture
def built(tmp_path):
    bl_rows, cit_rows, grains, side_meta, era_fids = _build(_make_warehouse(tmp_path))
    return {
        "bl": {r[0]: r for r in bl_rows},
        "bl_rows": bl_rows,
        "cit": {r[0]: r for r in cit_rows},
        "grains": grains,
        "side": side_meta,
        "era_fids": era_fids,
    }


def test_era_leaf_fact_id_is_its_own_era_key_workbook_id(built):
    for fid in (L5_ACT, L6_ACT, L5_REQ, DSS_ACT, DTRA_ACT):
        assert fid in built["bl"], fid
        assert built["cit"][fid][1] == "workbook"
    assert built["bl"][L5_ACT][8] == "3010F-AF-L5"     # lake identity kept
    assert built["bl"][DSS_ACT][8] == "0300D-DSS-L21"
    assert built["bl"][DSS_ACT][5] == "DSS"            # the row's own org


def test_era_citation_pe_bli_is_the_printed_code(built):
    assert built["cit"][L5_ACT][24] == "XB0100"
    assert built["cit"][L6_ACT][24] == "XB0100"
    assert built["cit"][DSS_ACT][24] == "20"
    assert built["cit"][L5_ACT][26] == "fy_2017_actuals"
    assert built["cit"][L5_ACT][12:16] == ("Exhibit P-1", "Q9", 300.0, SHA19)
    assert built["cit"][L5_ACT][19] == "2026-07-01T00:00:00"


def test_multi_line_era_sum_mints_decade_era_map(built):
    row = built["cit"][ERA_SUM]
    assert row[1] == "derived"
    assert row[2] == "USD thousands"
    assert row[20] == ERA_FORMULA
    # inputs sorted by fact id — NOT the tier's natural largest-row-first
    # order (L5 300 before L6 200), so this pins the sort itself
    assert json.loads(row[21]) == [L6_ACT, L5_ACT] == sorted([L5_ACT, L6_ACT])
    assert row[23] == "500.000"
    assert ("XB0100", 2017, 2019, "actuals", 500.0, ERA_SUM,
            "fy_2017_actuals", None, None) in built["grains"]
    # single-line era grain: the leaf IS the grain, no derived sum
    assert ("XB0100", 2019, 2019, "request", 400.0, L5_REQ,
            "fy_2019_total", None, None) in built["grains"]
    assert not any(
        r[20] == "sum(budget_lines.amount_thousands where amount_type="
        "fy_2017_actuals and edition=2019)" for r in built["cit"].values()
    )


def test_formula_passes_the_additive_receipt_grammar():
    assert additive_budget_formula(ERA_FORMULA)
    assert _decade_era_map_formula(
        "XB0100", None, None, "fy_2017_actuals", 2019) == ERA_FORMULA
    with_org = _decade_era_map_formula("20", None, "DCSA", "fy_2017_actuals", 2019)
    assert with_org == (
        "sum(budget_lines.amount_thousands where era_line_map='20'"
        " and organization='DCSA' and amount_type=fy_2017_actuals"
        " and edition=2019)"
    )
    assert additive_budget_formula(with_org)
    with_acct = _decade_era_map_formula("3010", "1611N", None, "fy_2019_total", 2021)
    assert additive_budget_formula(with_acct)
    with pytest.raises(ValueError, match="cannot be quoted"):
        _decade_era_map_formula("X'1", None, None, "fy_2017_actuals", 2019)
    with pytest.raises(ValueError, match="not a slug"):
        _decade_era_map_formula("XB0100", None, None, "FY 2017", 2019)


def test_f15_cell_mints_exactly_the_receipt_v5_injects(tmp_path):
    """tests/test_f15_era_identity.py (Task 4, V5) injects a decade_era_map
    receipt with its own literal key and formula. Pin the tier to the same
    strings over F-15's real PB2018 FY2016 actuals rows, so a change to
    _decade_era_map_formula or to the key fails here, not silently in V5."""
    assert _decade_era_map_formula(
        "F01500", None, None, "fy_2016_base_oco", 2018) == V5_FORMULA
    assert additive_budget_formula(V5_FORMULA)
    assert V5_FID == "6e96742c09a7e36e"
    db = _make_warehouse(
        tmp_path, grains=NATIVE_GRAINS + [F15_GRAIN],
        extra_lake=F15_LAKE_ROWS, extra_map=F15_MAP_ROWS,
    )
    bl, cit, grains, side, era_fids = _build(db, scope=SCOPE | {"F01500"})
    # the two era leaves keep their own era-key fact ids: V5's inputs
    assert [r[0] for r in bl if r[1] == "P-1"] == V5_INPUTS
    row = {r[0]: r for r in cit}[V5_FID]
    assert (row[1], row[2], row[20], json.loads(row[21]), row[23]) == (
        "derived", "USD thousands", V5_FORMULA, V5_INPUTS, "596932.000")
    assert ("F01500", 2016, 2018, "actuals", 596932.0, V5_FID,
            "fy_2016_base_oco", None, None) in grains
    assert era_fids == frozenset({V5_FID})
    assert side[V5_FID] == ("PB2018 FY2016 actuals", "F01500")


def test_collision_chain_lands_on_the_pinned_page(built):
    assert ("20", 2017, 2019, "actuals", 1234.0, DSS_ACT, "fy_2017_actuals",
            None, "DCSA") in built["grains"]
    assert ("20", 2017, 2019, "actuals", 77.0, DTRA_ACT, "fy_2017_actuals",
            None, "DTRA") in built["grains"]
    assert built["side"][DSS_ACT] == ("PB2019 FY2017 actuals", "20-DCSA")
    assert built["side"][DTRA_ACT] == ("PB2019 FY2017 actuals", "20-DTRA")


def test_era_leaves_name_their_page_for_breakdowns(built):
    assert built["side"][L5_ACT] == ("PB2019 FY2017 actuals", "XB0100")
    assert built["side"][L6_ACT] == ("PB2019 FY2017 actuals", "XB0100")
    assert built["side"][ERA_SUM] == ("PB2019 FY2017 actuals", "XB0100")


def test_history_only_and_out_of_scope_chains_mint_nothing(built):
    keys = {r[8] for r in built["bl_rows"]}
    assert "3010F-AF-L9" not in keys     # history_only, even though in scope
    assert "3010F-AF-L10" not in keys    # same_program but not a page
    assert not {g[0] for g in built["grains"]} & {"HH0001", "XC0200"}


def test_era_grain_fids_are_exactly_the_mapped_grains(built):
    assert built["era_fids"] == frozenset({ERA_SUM, L5_REQ, DSS_ACT, DTRA_ACT})
    assert isinstance(built["era_fids"], frozenset)
    assert NATIVE not in built["era_fids"]


def test_native_rows_are_unchanged_by_era_rows(tmp_path, built):
    native_only = tmp_path / "native"
    native_only.mkdir()
    bl, cit, grains, side, era_fids = _build(
        _make_warehouse(native_only, grains=list(NATIVE_GRAINS), era_map=False)
    )
    assert era_fids == frozenset()
    assert bl == [built["bl"][NATIVE]]
    assert cit == [built["cit"][NATIVE]]
    assert grains == [g for g in built["grains"] if g[5] == NATIVE]
    assert side == {NATIVE: built["side"][NATIVE]}
    assert bl[0] == (
        NATIVE, "R-1", 2024, "0400", "RDT&E, Defense-Wide", "DARPA", "01",
        "Basic Research", "0601101E", "Defense Research Sciences",
        "fy_2022_actuals", 100000.0, "USD thousands", SHA24, "Exhibit R-1", "J4",
    )
    assert cit[0][24] == "0601101E"
    assert side[NATIVE] == ("PB2024 FY2022 actuals", "0601101E")


def test_native_rows_keep_the_line_table_order(tmp_path):
    """Native rows come out in fct_decade_series' row order whatever order
    the program table holds them in, so budget_lines_decade.parquet and
    citations.parquet keep every native row's position."""
    for name, line_order in (("ab", [NATIVE_GRAINS[0], NATIVE2_GRAIN]),
                             ("ba", [NATIVE2_GRAIN, NATIVE_GRAINS[0]])):
        d = tmp_path / name
        d.mkdir()
        db = _make_warehouse(
            d, line_grains=line_order,
            grains=ERA_GRAINS + list(reversed(line_order)),
        )
        bl, cit, grains, _side, _era = _build(db, scope=SCOPE | {"0602702E"})
        expected = [g[9] for g in line_order]
        assert [r[0] for r in bl if r[1] == "R-1"] == expected
        assert [r[0] for r in cit if r[0] in expected] == expected
        assert [g[5] for g in grains][:2] == expected


def test_missing_program_table_raises(tmp_path):
    db = _make_warehouse(tmp_path, program_table=False)
    with pytest.raises(RuntimeError, match="fct_program_decade_series"):
        _build(db)


def test_program_table_without_line_table_raises(tmp_path):
    db = _make_warehouse(tmp_path, line_table=False)
    with pytest.raises(RuntimeError, match="without fct_decade_series"):
        _build(db)


def test_era_rows_without_the_map_raise(tmp_path):
    db = _make_warehouse(tmp_path, era_map=False)
    with pytest.raises(RuntimeError, match="p1_era_line_map is missing"):
        _build(db)


def test_pin_mismatch_trips_the_source_count_guard(tmp_path):
    # a DCSA grain that claims two source rows: only the DSS row is pinned to
    # DCSA (the DTRA row is pinned to DTRA), so the guard must refuse
    bad = [g if g[9] != DSS_ACT else ("20", 2017, 2019, "actuals", 1311.0,
           "fy_2017_actuals", None, "DCSA", 2, None, "era_line_map")
           for g in NATIVE_GRAINS + ERA_GRAINS]
    bad = [g for g in bad if g[9] != DTRA_ACT]
    with pytest.raises(ValueError, match="mart/lake drift"):
        _build(_make_warehouse(tmp_path, grains=bad))


def test_no_warehouse_tables_skips_the_tier(tmp_path):
    db = tmp_path / "empty.duckdb"
    duckdb.connect(str(db)).close()
    assert _build(db) == ([], [], [], {}, frozenset())
