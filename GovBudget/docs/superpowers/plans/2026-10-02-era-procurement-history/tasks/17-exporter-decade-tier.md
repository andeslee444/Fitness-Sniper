<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 17: Exporter decade-tier switch — the program table, era points through the reviewed map

**Spec:** §6.1 (every bullet; the dataset-scope sentence is met by Task 19's `p1_era_line_map` scope, see CONTRACT ISSUE 3, withdrawn); §8 V5 (the `decade_era_map` key and formula Task 4's fresh-state test injects are pinned against what this tier mints); §4.5 "row_fact_id still hashes the source row's own pe_bli"; §7 rows "Several era lines share one code", "The program table missing at export", "Mart/lake drift during export"; §10 "F-15's 72 A1 era-leaf entries are now minted by the decade tier"; S4 step "Decade tier switch (§6.1)".
**Files:**
- Modify: `src/govbudget/export_site.py:3055-3056` (caller), `:6905-7333` (`_build_decade_citation_rows`), `:17702-17705` (`_emit_breakdowns` decade rows)
- Create: `tests/test_export_decade_era_map.py`
- Modify (test): `tests/test_export_breakdowns.py` (append after line 586), `tests/jbooks/test_export_basis.py:266-269`, `tests/jbooks/test_export_site_pg.py:1961-1963`

**Interfaces:** Consumes: `fct_program_decade_series` (Task 16; columns and conventions in CONTRACT ISSUE 1), `fct_decade_series` (unchanged base table, read for row order), `p1_era_line_map` (Task 13), `program_pdf_receipts.additive_budget_formula`, `fact_id_workbook`, `fact_id_derived`. / Produces: `_build_decade_citation_rows(*, duckdb_path, existing_fids: set, scope_pes: set) -> tuple[list, list, list, dict, frozenset]` (fifth element `era_grain_fids: frozenset[str]`); `_decade_era_map_formula(program_key: str, account: str | None, organization: str | None, amount_type: str, edition: int) -> str`; derived surface `"decade_era_map"` with key `f"{program_key}|{account or ''}|{organization or ''}|{edition}"` and metric = the grain's `amount_type`; `decade_side_meta` now also maps every era grain and era leaf fid to `(label, page slug)`, which `_emit_breakdowns` uses as the row's `pe_bli`.

What changes and why, in one place (so the edits read as one design):
- The tier reads `fct_program_decade_series`. `map_basis='native'` rows take the
  unchanged path; their output is byte-identical, including row order (native
  grains are read in `fct_decade_series`' `rowid` order). If
  `fct_decade_series` exists without the program table the export raises.
- `map_basis='era_line_map'` rows match lake rows through `p1_era_line_map`
  (`same_program` only): key `(program_key, edition, amount_type)` plus the
  PINNED `program_account`/`program_org`, never the row's own
  account/organization.
- Era leaf: `w_fid = fact_id_workbook(...)` over the row's own `pe_bli` (its era
  key); its `budget_lines_decade` row keeps the era key; its citation `pe_bli`
  is the program key, which is the bare printed code.
- A multi-line era grain mints `fact_id_derived("decade_era_map", ...)`, formula
  `sum(budget_lines.amount_thousands where era_line_map='{code}'[ and
  account='…'][ and organization='…'] and amount_type={at} and
  edition={edition})`, inputs sorted by fact id. The grammar it must pass is
  `program_pdf_receipts.py:255-258`:
  `predicate = r"[a-z_]+=(?:'[^'\n]*'|[a-z0-9_]+)"`,
  `selection = rf" where {predicate}(?: and {predicate})*"`, full match of
  `sum\(budget_lines\.amount_thousands(?:{selection})?\)(?:{selection})?` — so
  codes, accounts and organizations (capitals) are quoted and the slug and the
  edition are bare.
- Task 4's V5 test (`tests/test_f15_era_identity.py`) keeps its own literal
  key `f"{code}|||{edition}"` and formula text. So the two cannot drift apart
  unnoticed, this task's test drives the tier over F-15's real PB2018 FY2016
  actuals cell (lines 23 and 79, both `F01500`, both `fy_2016_base_oco`) and
  asserts the minted receipt is exactly what V5 injects:
  `fact_id_derived("decade_era_map", "F01500|||2018", "fy_2016_base_oco")`
  (= `6e96742c09a7e36e`), formula `sum(budget_lines.amount_thousands where
  era_line_map='F01500' and amount_type=fy_2016_base_oco and edition=2018)`,
  inputs V5's `TARGET_INPUTS` `["28f53c8d681494cc", "cce72b42a96bfcb7"]`.
- Era points only for `program_key in scope_pes` (never the top-rva extras);
  `era_history_only` grains mint nothing; era grains never enter the book-diff
  join.
- `era_grain_fids` = fids of the returned `decade_grains` that came through
  the map; Task 18 hands it to the fenced emitters. Between this commit and
  Task 18's, lineage funding lines and `/years/` would include era points, so
  no export is run in between (the S4 proof is Task 21).

- [ ] **Step 1: Write the failing hermetic test**

Create `tests/test_export_decade_era_map.py`:

```python
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
```

- [ ] **Step 2: Run it and watch it fail**

Run (from `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget`):

```bash
uv run --project . pytest tests/test_export_decade_era_map.py -q
```

Expected: a collection error, because the formula helper does not exist yet:

```
E   ImportError: cannot import name '_decade_era_map_formula' from 'govbudget.export_site'
ERROR tests/test_export_decade_era_map.py
1 error in …
```

- [ ] **Step 3: Write the failing breakdown test**

Append to the end of `tests/test_export_breakdowns.py` (after line 586; the
file already imports `json`, `_null_derived_row`, `fact_id_derived`, `_emit`,
`_load` and `_citation_rows`):

```python
# ---------------------------------------------------------------------------
# Families piece 1 (spec 2026-10-02 §6.1): decade_era_map sums link to pages
# ---------------------------------------------------------------------------

EW1 = "f111000000000031"  # PB2019 era leaf 3010F-AF-L5 (300.0 thousands)
EW2 = "f211000000000032"  # PB2019 era leaf 3010F-AF-L6 (200.0 thousands)
ERA_SUM = fact_id_derived("decade_era_map", "XB0100|||2019", "fy_2017_actuals")
ERA_SIDE = ("PB2019 FY2017 actuals", "XB0100")


def _era_bl_rows() -> list[tuple]:
    """budget_lines_decade rows of two era leaves: pe_bli is the era key."""
    return [
        (EW1, "P-1", 2019, "3010F", "Aircraft Procurement, Air Force", "AF",
         "01", "Combat Aircraft", "3010F-AF-L5", "XB Aircraft",
         "fy_2017_actuals", 300.0, "USD thousands", "sha_pb2019",
         "Exhibit P-1", "Q9"),
        (EW2, "P-1", 2019, "3010F", "Aircraft Procurement, Air Force", "AF",
         "05", "Modification of Aircraft", "3010F-AF-L6", "XB Aircraft Mods",
         "fy_2017_actuals", 200.0, "USD thousands", "sha_pb2019",
         "Exhibit P-1", "Q10"),
    ]


def _era_leaf_row(fid, amount, cells):
    """27-tuple era workbook citation: pe_bli is the printed code."""
    return (
        fid, "workbook", "USD thousands",
        None, None, None, None, None, None, None, None,
        None, "Exhibit P-1", cells, amount,
        "sha_pb2019", None, "https://example.mil/fy2019/p1.xlsx", None,
        "2026-07-01T00:00:00",
        None, None, None, None,
        "XB0100", None, "fy_2017_actuals",
    )


def _era_citation_rows() -> list[tuple]:
    return _citation_rows() + [
        _era_leaf_row(EW1, 300.0, "Q9"),
        _era_leaf_row(EW2, 200.0, "Q10"),
        _null_derived_row(
            ERA_SUM, "derived", "USD thousands",
            "sum(budget_lines.amount_thousands where era_line_map='XB0100'"
            " and amount_type=fy_2017_actuals and edition=2019)",
            json.dumps(sorted([EW1, EW2])), "500.000",
            "2026-10-02T00:00:00+00:00",
        ),
    ]


class TestEraMapBreakdown:
    def test_rows_link_to_the_page_not_the_era_key(self, tmp_path):
        """breakdown-table.tsx links every row's pe_bli to /program/; an era
        key ('3010F-AF-L5') has no page. The decade tier names the page in
        decade_side_meta and the row carries it; the label stays the filed
        title of the cited workbook row."""
        _emit(tmp_path, citation_rows=_era_citation_rows(),
              decade_bl_rows=_era_bl_rows(),
              decade_side_meta={EW1: ERA_SIDE, EW2: ERA_SIDE, ERA_SUM: ERA_SIDE})
        obj = _load(tmp_path, ERA_SUM)
        assert obj["op"] == "sum"
        assert obj["recorded_value"] == "500.000"
        assert [(r["fid"], r["pe_bli"], r["label"], r["v"]) for r in obj["rows"]] == [
            (EW1, "XB0100", "XB Aircraft", 300.0),
            (EW2, "XB0100", "XB Aircraft Mods", 200.0),
        ]

    def test_a_row_without_a_side_entry_keeps_its_own_pe_bli(self, tmp_path):
        """Native decade rows have no side entry of their own unless they are
        a single-source grain, whose entry names the same pe_bli — so the
        lookup is byte-identical for every native row."""
        _emit(tmp_path, citation_rows=_era_citation_rows(),
              decade_bl_rows=_era_bl_rows(), decade_side_meta={})
        obj = _load(tmp_path, ERA_SUM)
        assert [r["pe_bli"] for r in obj["rows"]] == ["3010F-AF-L5", "3010F-AF-L6"]
```

- [ ] **Step 4: Run it and watch the page test fail**

```bash
uv run --project . pytest tests/test_export_breakdowns.py -q
```

Expected: `1 failed, 21 passed`; the failure is
`TestEraMapBreakdown::test_rows_link_to_the_page_not_the_era_key` with
`AssertionError` (the rows carry `pe_bli` `'3010F-AF-L5'` / `'3010F-AF-L6'`,
not `'XB0100'`).

- [ ] **Step 5: Implement the switch in `src/govbudget/export_site.py`**

Apply these exact replacements (line numbers at base `10fb4585`; apply in any
order — every "old" text is unique):

**Edit 17.1 signature and docstring head** — `src/govbudget/export_site.py:6905-6914`. Replace this exact text:

```python
def _build_decade_citation_rows(
    *,
    duckdb_path,
    existing_fids: set,
    scope_pes: set,
) -> tuple[list, list, list, dict]:
    """Build the Phase 5E decade fact space from fct_decade_series +
    fct_book_diff (Task 5 marts) and the jbooks parquet lake.

    Returns (decade_bl_rows, decade_cit_rows, decade_grains, decade_side_meta):
```

with:

```python
def _build_decade_citation_rows(
    *,
    duckdb_path,
    existing_fids: set,
    scope_pes: set,
) -> tuple[list, list, list, dict, frozenset]:
    """Build the Phase 5E decade fact space from fct_program_decade_series +
    fct_book_diff (marts), p1_era_line_map (the reviewed era map) and the
    jbooks parquet lake.

    Families piece 1 (spec 2026-10-02 §6.1). The grain table is
    fct_program_decade_series. Its map_basis='native' rows equal
    fct_decade_series row for row and take exactly the pre-piece path below,
    so native output is byte-identical. Its map_basis='era_line_map' rows are
    PB2017-PB2023 P-1 lines summed under their bare printed code through
    same_program decisions; 'era_history_only' rows are data only and never
    become points (R-DEC-FAM-ERAONLY). fct_decade_series present while the
    program table is missing RAISES: there is no silent fallback.

    Returns (decade_bl_rows, decade_cit_rows, decade_grains, decade_side_meta,
    era_grain_fids):
```

**Edit 17.2 docstring: side meta and era_grain_fids** — `src/govbudget/export_site.py:6939-6940`. Replace this exact text:

```python
      decade_side_meta — fid → (label, pe_bli) for _emit_breakdowns
                         difference-row labels ('PB2024 FY2022 actuals').
```

with:

```python
      decade_side_meta — fid → (label, pe_bli) for _emit_breakdowns
                         difference-row labels ('PB2024 FY2022 actuals').
                         Era grains AND their leaves carry the PAGE slug the
                         points join (the bare code, or '{code}-{ORG}' /
                         '{code}-{ACCOUNT_CODE}' on a split key): an era
                         leaf's own pe_bli is its era key, which has no page,
                         and _emit_breakdowns links every row to /program/.
      era_grain_fids   — frozenset of the fids of the decade_grains added
                         through the map. Never serialized: decade_grains and
                         the sidecar decade_series keep their exact shape;
                         the lineage and /years/ emitters skip these fids
                         (spec §6.2 fences).
```

**Edit 17.3 the mart read (program table, ordered; era map)** — `src/govbudget/export_site.py:6960-6987`. Replace this exact text:

```python
    empty: tuple[list, list, list, dict] = ([], [], [], {})

    con = _duckdb.connect(str(duckdb_path), read_only=True)
    try:
        try:
            series = con.execute(
                "select pe_bli, fy, edition_year, amount_type_kind, amount,"
                " amount_type, n_source_rows, source_fact_id, account,"
                " organization"
                " from fct_decade_series"
            ).fetchall()
        except _duckdb.CatalogException:
            print("decade: fct_decade_series not in warehouse — decade tier skipped")
            return empty
        except _duckdb.BinderException:
            # ROADMAP #45: the table exists but predates the `organization`
            # column (an older test fixture) — fall back and pad None, the
            # same "schema without the column cannot carry real split-key
            # data" contract _query_with_account_fallback already uses for
            # `account`.
            series = [
                (*r, None)
                for r in con.execute(
                    "select pe_bli, fy, edition_year, amount_type_kind,"
                    " amount, amount_type, n_source_rows, source_fact_id,"
                    " account from fct_decade_series"
                ).fetchall()
            ]
```

with:

```python
    empty: tuple[list, list, list, dict, frozenset] = ([], [], [], {}, frozenset())

    con = _duckdb.connect(str(duckdb_path), read_only=True)
    try:
        def _has_table(name: str) -> bool:
            try:
                con.execute(f"select 1 from {name} limit 0")
            except _duckdb.CatalogException:
                return False
            return True

        has_program, has_line = (
            _has_table("fct_program_decade_series"),
            _has_table("fct_decade_series"),
        )
        if not has_program and not has_line:
            print("decade: fct_program_decade_series not in warehouse — decade tier skipped")
            return empty
        if not has_program:
            raise RuntimeError(
                "decade: fct_decade_series exists but fct_program_decade_series"
                " does not. The decade tier reads the program table (spec"
                " 2026-10-02 §6.1) and never falls back to the line table;"
                " run `govbudget build` so dbt adds it."
            )
        if not has_line:
            raise RuntimeError(
                "decade: fct_program_decade_series exists without"
                " fct_decade_series — native grains are emitted in the line"
                " table's row order, and its parity contract needs it"
            )
        # program_key is the PAGE key: exactly fct_decade_series.pe_bli on
        # native rows, the bare printed code on era rows. account /
        # organization follow fct_decade_series' convention (non-NULL only
        # on the 13 PB2026 collision codes; on an era row they are the
        # PINNED program_account / program_org).
        #
        # ORDER: native grains come back in fct_decade_series' own row order
        # (rowid — what the pre-piece unordered read returned), so the
        # native rows of budget_lines_decade.parquet and citations.parquet
        # keep their positions byte for byte; era grains follow, in a fixed
        # key order. The program table's native rows equal the line table's
        # row for row on this key (assert_program_decade_native_equals_line).
        series = con.execute(
            "select p.program_key, p.fy, p.edition_year, p.amount_type_kind,"
            " p.amount, p.amount_type, p.n_source_rows, p.source_fact_id,"
            " p.account, p.organization, p.map_basis"
            " from fct_program_decade_series p"
            " left join (select l.pe_bli, l.account, l.organization, l.fy,"
            "                   l.edition_year, l.rowid as line_pos"
            "            from fct_decade_series l) d"
            "   on p.map_basis = 'native'"
            "  and d.pe_bli = p.program_key"
            "  and d.account is not distinct from p.account"
            "  and d.organization is not distinct from p.organization"
            "  and d.fy = p.fy and d.edition_year = p.edition_year"
            " order by d.line_pos nulls last, p.program_key,"
            "          p.account nulls first, p.organization nulls first,"
            "          p.edition_year, p.fy, p.amount_type_kind"
        ).fetchall()
        # The reviewed era map: (edition, account, organization,
        # budget_activity, era_key) → (program_key, pinned account, pinned
        # organization), same_program decisions only. history_only rows
        # never become points, so their keys are not needed here.
        era_map: dict[tuple, tuple] = {}
        if any(r[10] == "era_line_map" for r in series):
            try:
                map_rows = con.execute(
                    "select cast(edition as integer), account, organization,"
                    " budget_activity, era_key, line_item_code, program_key,"
                    " program_account, program_org"
                    " from p1_era_line_map where decision = 'same_program'"
                ).fetchall()
            except _duckdb.CatalogException:
                raise RuntimeError(
                    "decade: fct_program_decade_series carries era_line_map"
                    " rows but p1_era_line_map is missing; era source rows are"
                    " matched only through the reviewed map"
                ) from None
            for (m_ed, m_acct, m_org, m_ba, m_key, m_code, m_prog,
                 m_pin_acct, m_pin_org) in map_rows:
                if m_code != m_prog:
                    raise ValueError(
                        f"decade: p1_era_line_map row PB{m_ed} {m_key} prints"
                        f" {m_code!r} but names program_key {m_prog!r}; the"
                        " program key is always the bare printed code (spec"
                        " §4.5), and era citations publish that code as pe_bli"
                    )
                era_map[(m_ed, m_acct, m_org, m_ba, m_key)] = (
                    m_prog, m_pin_acct or None, m_pin_org or None,
                )
```

**Edit 17.4 era source index** — `src/govbudget/export_site.py:7045-7047`. Replace this exact text:

```python
    src_by_key: dict[tuple, list] = {}
    for r in src_rows:
        src_by_key.setdefault((r[7], r[1], r[9]), []).append(r)
```

with:

```python
    src_by_key: dict[tuple, list] = {}
    for r in src_rows:
        src_by_key.setdefault((r[7], r[1], r[9]), []).append(r)

    # Era P-1 rows → the program key their reviewed decision names (spec
    # §6.1), keyed (program_key, edition, amount_type) and carrying the
    # PINNED program_account / program_org. A grain matches through the pin,
    # never through the row's own account/organization, so a chain filed
    # under DSS and pinned to the DCSA page neither trips the source-count
    # guard below nor drops silently. Entries: (row, pin account, pin org).
    era_src_by_key: dict[tuple, list] = {}
    for r in src_rows:
        if r[0] != "P-1":
            continue
        hit = era_map.get((r[1], r[2], r[4], r[5], r[7]))
        if hit is None:
            continue
        program_key, pin_account, pin_org = hit
        era_src_by_key.setdefault((program_key, r[1], r[9]), []).append(
            (r, pin_account, pin_org)
        )
```

**Edit 17.5 era scope** — `src/govbudget/export_site.py:7054-7055`. Replace this exact text:

```python
    top_rva_pes = {d[0] for d in rva[:_DECADE_TOP_RVA]}
    pes = set(scope_pes) | top_rva_pes
```

with:

```python
    top_rva_pes = {d[0] for d in rva[:_DECADE_TOP_RVA]}
    pes = set(scope_pes) | top_rva_pes
    # Era points go only to today's PAGE universe (PB2026 lines plus the
    # decade-only pages), never to a top-rva PE that has no page.
    era_scope = set(scope_pes)
```

**Edit 17.6 counters and loop head** — `src/govbudget/export_site.py:7073-7080`. Replace this exact text:

```python
    n_wb_new = 0
    n_wb_dedup = 0
    n_derived_sum = 0

    for pe_bli, fy, edition, kind, amount, at, n_src, src_fid, account, series_org in series:
        if pe_bli not in pes:
            continue
        candidate_rows = src_by_key.get((pe_bli, edition, at), [])
```

with:

```python
    n_wb_new = 0
    n_wb_dedup = 0
    n_derived_sum = 0
    n_era_sum = 0
    # (grain 9-tuple, its leaf fids) for every grain added through the map
    era_grains: list[tuple[tuple, list[str]]] = []

    for (pe_bli, fy, edition, kind, amount, at, n_src, src_fid, account,
         series_org, map_basis) in series:
        # pe_bli is the program table's program_key (see the read above).
        if map_basis == "era_history_only":
            # R-DEC-FAM-ERAONLY: a history-only chain stays in the program
            # table and the map; it never becomes a page point.
            continue
        if map_basis not in ("native", "era_line_map"):
            raise ValueError(
                f"decade: unknown map_basis {map_basis!r} on grain"
                f" ({pe_bli}, PB{edition}, {at})"
            )
        is_era = map_basis == "era_line_map"
        if pe_bli not in (era_scope if is_era else pes):
            continue
        if is_era:
            if account is not None and series_org is not None:
                raise ValueError(
                    f"decade: era grain ({pe_bli}, PB{edition}, {at}) pins"
                    f" both account={account!r} and organization="
                    f"{series_org!r}; a collision code splits on ONE axis"
                )
            era_cands = era_src_by_key.get((pe_bli, edition, at), [])
            if account is not None:
                era_cands = [c for c in era_cands if c[1] == account]
            if series_org is not None:
                era_cands = [c for c in era_cands if c[2] == series_org]
            candidate_rows = [c[0] for c in era_cands]
        else:
            candidate_rows = src_by_key.get((pe_bli, edition, at), [])
```

**Edit 17.7 native-only row filter** — `src/govbudget/export_site.py:7096-7101`. Replace this exact text:

```python
        key_rows = candidate_rows
        if account is not None:
            key_rows = [r for r in key_rows if r[2] == account]
        if series_org is not None:
            key_rows = [r for r in key_rows if r[4] == series_org]
        if len(key_rows) != n_src:
```

with:

```python
        key_rows = candidate_rows
        if account is not None and not is_era:
            key_rows = [r for r in key_rows if r[2] == account]
        if series_org is not None and not is_era:
            key_rows = [r for r in key_rows if r[4] == series_org]
        if len(key_rows) != n_src:
```

**Edit 17.8 row identity unpack** — `src/govbudget/export_site.py:7122-7125`. Replace this exact text:

```python
            (exhibit, ed_year, row_account, account_title, organization,
             budget_activity, ba_title, _pe, title, _at, amount_thousands,
             sha256, source_sheet, source_cells, source_url,
             downloaded_at) = r
```

with:

```python
            #
            # row_pe_bli is the source row's OWN pe_bli: equal to pe_bli on a
            # native grain, the era key ('{account}-{org}-L{line}') on an era
            # grain. The workbook fact id and the budget_lines_decade row use
            # it, so every era fact id F-15 already published is reproduced,
            # never re-minted; the citation's pe_bli below is the grain's
            # program key, i.e. the code printed at the cited cell (column I).
            (exhibit, ed_year, row_account, account_title, organization,
             budget_activity, ba_title, row_pe_bli, title, _at,
             amount_thousands, sha256, source_sheet, source_cells,
             source_url, downloaded_at) = r
```

**Edit 17.9 row identity in the fact id and the decade row** — `src/govbudget/export_site.py:7131-7138`. Replace this exact text:

```python
            w_fid = fact_id_workbook(
                sha256, exhibit, ed_year, row_account, organization,
                budget_activity, pe_bli, at,
            )
            input_fids.append(w_fid)
            decade_bl_rows.append((
                w_fid, exhibit, int(ed_year), row_account, account_title,
                organization, budget_activity, ba_title, pe_bli, title, at,
```

with:

```python
            w_fid = fact_id_workbook(
                sha256, exhibit, ed_year, row_account, organization,
                budget_activity, row_pe_bli, at,
            )
            input_fids.append(w_fid)
            decade_bl_rows.append((
                w_fid, exhibit, int(ed_year), row_account, account_title,
                organization, budget_activity, ba_title, row_pe_bli, title, at,
```

**Edit 17.10 decade_era_map surface** — `src/govbudget/export_site.py:7177-7182`. Replace this exact text:

```python
                    f" {src_fid}; the mart's sha256 derivation and"
                    " fact_id_workbook disagree (STOP: fix the derivation,"
                    " never ship mismatched identities)"
                )
        else:
            grain_fid = fact_id_derived("decade", f"{pe_bli}|{edition}", at)
```

with:

```python
                    f" {src_fid}; the mart's sha256 derivation and"
                    " fact_id_workbook disagree (STOP: fix the derivation,"
                    " never ship mismatched identities)"
                )
        elif is_era:
            # Several era lines summed under one program key (advance-
            # procurement pairs, lines in several budget activities). A new
            # surface, NOT 'decade': F-15's matrix reuses only the formulas
            # on its allow-list, so its 27 legacy multi-input cells keep
            # their own receipts. Inputs sorted by fact id: byte-stable.
            leaf_total = sum(r[10] for r in key_rows)
            if abs(leaf_total - amount) > 0.0005:
                raise ValueError(
                    f"decade: era grain ({pe_bli}, PB{edition}, {at}) amount"
                    f" {amount} != the sum of its {len(key_rows)} lake rows"
                    f" ({leaf_total}) — mart/lake drift; refusing to mint"
                )
            grain_fid = fact_id_derived(
                "decade_era_map",
                f"{pe_bli}|{account or ''}|{series_org or ''}|{edition}",
                at,
            )
            if grain_fid not in minted_fids:
                minted_fids.add(grain_fid)
                n_era_sum += 1
                decade_cit_rows.append(_null_derived_row(
                    grain_fid, "derived", "USD thousands",
                    _decade_era_map_formula(
                        pe_bli, account, series_org, at, edition,
                    ),
                    _json.dumps(sorted(input_fids)),
                    f"{amount:.3f}",
                    built_at,
                ))
        else:
            grain_fid = fact_id_derived("decade", f"{pe_bli}|{edition}", at)
```

**Edit 17.11 grain bookkeeping** — `src/govbudget/export_site.py:7195-7210`. Replace this exact text:

```python
        # E2/#45: account/organization are part of the lookup key —
        # grain_fid_by_key must resolve to THIS account's (or organization's)
        # own fid, not whichever row happened to be processed last for this
        # (pe_bli, edition, at).
        grain_fid_by_key[(pe_bli, account, series_org, edition, at)] = grain_fid
        # 9-tuple (+account/organization internally): the trailing
        # amount_type is the grain's CHOSEN slug — consumers derive the
        # point's `measure` from it (slug-accurate: a CurrentYear grain
        # built from fy_2025_total is measure 'total', matching the P-1
        # table row it must agree with; one built from fy_2025_enacted is
        # 'enacted').
        decade_grains_full.append(
            (pe_bli, int(fy), int(edition), kind, float(amount), grain_fid,
             at, account, series_org)
        )
        decade_side_meta[grain_fid] = (f"PB{edition} FY{fy} {kind}", pe_bli)
```

with:

```python
        # 9-tuple (+account/organization internally): the trailing
        # amount_type is the grain's CHOSEN slug — consumers derive the
        # point's `measure` from it (slug-accurate: a CurrentYear grain
        # built from fy_2025_total is measure 'total', matching the P-1
        # table row it must agree with; one built from fy_2025_enacted is
        # 'enacted').
        grain = (pe_bli, int(fy), int(edition), kind, float(amount),
                 grain_fid, at, account, series_org)
        if is_era:
            # Never a book-diff side: era book diffs are a non-goal and
            # fct_book_diff reads fct_decade_series, which has no era
            # program keys — a diff naming one fails the join loudly below.
            era_grains.append((grain, input_fids))
        else:
            # E2/#45: account/organization are part of the lookup key —
            # grain_fid_by_key must resolve to THIS account's (or
            # organization's) own fid, not whichever row happened to be
            # processed last for this (pe_bli, edition, at).
            grain_fid_by_key[(pe_bli, account, series_org, edition, at)] = grain_fid
        decade_grains_full.append(grain)
        decade_side_meta[grain_fid] = (f"PB{edition} FY{fy} {kind}", pe_bli)
```

**Edit 17.12 tail: page slugs, era_grain_fids, return, formula helper** — `src/govbudget/export_site.py:7325-7333`. Replace this exact text:

```python
    decade_grains = [g for g in decade_grains_full if _decade_grain_has_page(g)]

    print(
        f"decade: {len(decade_grains)} grains for {len(pes & {g[0] for g in decade_grains})}"
        f" in-scope PEs → {len(decade_bl_rows)} source rows"
        f" ({n_wb_new} new workbook citations, {n_wb_dedup} deduped),"
        f" {n_derived_sum} derived decade sums, {n_diffs} book-diff facts"
    )
    return decade_bl_rows, decade_cit_rows, decade_grains, decade_side_meta
```

with:

```python
    decade_grains = [g for g in decade_grains_full if _decade_grain_has_page(g)]

    def _era_page_slug(g: tuple) -> str:
        """The page an era grain's points join: the slug decade_series_by_pe
        files them under (_write_all_sidecars), the bare code otherwise."""
        pe, g_account, g_org = g[0], g[7], g[8]
        if pe not in _decade_ident.split_pe_blis or not _decade_grain_has_page(g):
            return pe
        title = next(
            (t for a, t, _o, _hd in _decade_ident.accounts(pe) if a == g_account),
            None,
        )
        return _decade_ident.slug(pe, g_account, title, g_org)

    # Breakdown rows link to /program/{pe_bli}/ (_emit_breakdowns reads
    # decade_side_meta): an era leaf names its page, never its era key.
    for g, leaf_fids in era_grains:
        side = (f"PB{g[2]} FY{g[1]} {g[3]}", _era_page_slug(g))
        decade_side_meta[g[5]] = side
        for leaf in leaf_fids:
            decade_side_meta[leaf] = side
    _era_fids = {g[5] for g, _leaves in era_grains}
    era_grain_fids = frozenset(g[5] for g in decade_grains if g[5] in _era_fids)

    print(
        f"decade: {len(decade_grains)} grains for {len(pes & {g[0] for g in decade_grains})}"
        f" in-scope PEs → {len(decade_bl_rows)} source rows"
        f" ({n_wb_new} new workbook citations, {n_wb_dedup} deduped),"
        f" {n_derived_sum} derived decade sums, {n_diffs} book-diff facts;"
        f" era map: {len(era_grain_fids)} grains with a page,"
        f" {n_era_sum} decade_era_map sums"
    )
    return (decade_bl_rows, decade_cit_rows, decade_grains, decade_side_meta,
            era_grain_fids)


def _decade_era_map_formula(
    program_key: str,
    account: str | None,
    organization: str | None,
    amount_type: str,
    edition: int,
) -> str:
    """The recompute formula of a decade_era_map sum (spec §6.1).

    It must pass program_pdf_receipts.additive_budget_formula, whose
    predicates are `name='quoted'` or `name=bare` with bare values limited
    to [a-z0-9_]: codes, accounts and organizations carry capitals, so they
    are quoted; the slug and the edition are bare. A value the grammar cannot carry raises rather than
    shipping a receipt the PDF pipeline would silently skip.
    """
    for name, value in (("program_key", program_key), ("account", account),
                        ("organization", organization)):
        if value is not None and ("'" in value or "\n" in value):
            raise ValueError(
                f"decade_era_map formula: {name}={value!r} cannot be quoted"
            )
    if not re.fullmatch(r"[a-z0-9_]+", amount_type):
        raise ValueError(
            f"decade_era_map formula: amount_type {amount_type!r} is not a slug"
        )
    predicates = [f"era_line_map='{program_key}'"]
    if account is not None:
        predicates.append(f"account='{account}'")
    if organization is not None:
        predicates.append(f"organization='{organization}'")
    predicates += [f"amount_type={amount_type}", f"edition={int(edition)}"]
    return (
        "sum(budget_lines.amount_thousands where "
        + " and ".join(predicates) + ")"
    )
```

**Edit 17.13 caller unpacks five values** — `src/govbudget/export_site.py:3055-3056`. Replace this exact text:

```python
    (decade_bl_rows, decade_cit_rows, decade_grains,
     decade_side_meta) = _build_decade_citation_rows(
```

with:

```python
    (decade_bl_rows, decade_cit_rows, decade_grains,
     decade_side_meta, era_grain_fids) = _build_decade_citation_rows(
```

**Edit 17.14 breakdown rows name their page** — `src/govbudget/export_site.py:17702-17705`. Replace this exact text:

```python
    for r in (decade_bl_rows or []):
        bl_by_fid.setdefault(
            r[0], (r[11], apply_title_override(r[8], r[9], _title_overrides), r[8])
        )
```

with:

```python
    for r in (decade_bl_rows or []):
        # The row's link target. A native decade row's pe_bli IS its page; an
        # era leaf's is its era key ('{account}-{org}-L{line}'), which has no
        # page, so the decade tier records the page slug the leaf joins in
        # decade_side_meta (spec 2026-10-02 §6.1). For a native row that
        # entry, when present, names r[8] itself — byte-identical.
        page = (decade_side_meta or {}).get(r[0], (None, r[8]))[1]
        bl_by_fid.setdefault(
            r[0], (r[11], apply_title_override(r[8], r[9], _title_overrides), page)
        )
```


- [ ] **Step 6: Run the new tests**

```bash
uv run --project . pytest tests/test_export_decade_era_map.py tests/test_export_breakdowns.py -q
```

Expected: `38 passed` (16 + 22).

- [ ] **Step 7: See the intended raise in the Postgres-backed exporter fixtures**

These two fixtures build only `fct_decade_series`, so the switched tier must
refuse them (needs Task 1's throwaway cluster):

```bash
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_export_basis.py tests/jbooks/test_export_site_pg.py -q
```

Expected: `5 failed, 39 passed, 16 errors` — the 16 `basis_site`/`task3_site`
tests error in their fixture and the 5 `_run_decade_export` tests fail, all with
`RuntimeError: decade: fct_decade_series exists but fct_program_decade_series does not. The decade tier reads the program table (spec 2026-10-02 §6.1) and never falls back to the line table; run `govbudget build` so dbt adds it.`

- [ ] **Step 8: Give both fixtures the program table**

**Edit 17.15** — `tests/jbooks/test_export_basis.py:266-269`. Replace this exact text:

```python
        con.execute(
            "insert into fct_decade_series values (?,?,?,?,?,?,?,?,?,?,?)",
            (PE, fy, 2026, kind, amt, amt, scenario, at, 1, _wb_fid(sha, at), None),
        )
```

with:

```python
        con.execute(
            "insert into fct_decade_series values (?,?,?,?,?,?,?,?,?,?,?)",
            (PE, fy, 2026, kind, amt, amt, scenario, at, 1, _wb_fid(sha, at), None),
        )
    # Families piece 1 (spec 2026-10-02 §6.1): the decade tier reads the
    # program table and raises when only fct_decade_series exists, and it
    # orders native grains by the line table's rows, joining on its
    # `organization` (ROADMAP #45 column, present on the live mart). Every
    # row here is native: the program table equals the line table row for row.
    con.execute("alter table fct_decade_series add column organization varchar")
    con.execute(
        "create table fct_program_decade_series as select"
        " pe_bli as program_key, fy, edition_year, amount_type_kind, amount,"
        " amount_thousands, scenario, amount_type, account,"
        " cast(null as varchar) as organization, n_source_rows,"
        " source_fact_id, 'native' as map_basis"
        " from fct_decade_series"
    )
```

**Edit 17.16** — `tests/jbooks/test_export_site_pg.py:1961-1963`. Replace this exact text:

```python
        f"('0601101E', 2024, 2024, 'request', 200000.0, 200000.0,"
        f" 'BudgetYearOne', 'fy_2024_total', 2, NULL, NULL)"
    )
```

with:

```python
        f"('0601101E', 2024, 2024, 'request', 200000.0, 200000.0,"
        f" 'BudgetYearOne', 'fy_2024_total', 2, NULL, NULL)"
    )
    # Families piece 1 (spec 2026-10-02 §6.1): the decade tier reads the
    # program table and raises when only fct_decade_series exists, and it
    # orders native grains by the line table's rows, joining on its
    # `organization` (ROADMAP #45 column, present on the live mart). Every
    # row here is native: the program table equals the line table row for row.
    con.execute("alter table fct_decade_series add column organization varchar")
    con.execute(
        "create table fct_program_decade_series as select"
        " pe_bli as program_key, fy, edition_year, amount_type_kind, amount,"
        " amount_thousands, scenario, amount_type, account,"
        " cast(null as varchar) as organization, n_source_rows,"
        " source_fact_id, 'native' as map_basis"
        " from fct_decade_series"
    )
```


- [ ] **Step 9: Run the Postgres-backed exporter tests again**

```bash
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_export_basis.py tests/jbooks/test_export_site_pg.py -q
```

Expected: `60 passed` (17 + 43). `test_decade_parquet_and_citations` still sees
4 `budget_lines_decade` rows, the `decade` sum `200000.000` over 2 inputs and the
book-diff fact — the native path is unchanged.

- [ ] **Step 10: Regression over the other decade consumers**

```bash
uv run --project . pytest tests/test_export_years_matrix.py tests/jbooks/test_export_lineage.py tests/test_export_site_decade_only.py tests/test_f15_funding_history.py tests/lineage/test_flow.py -q
```

Expected: `0 failed` (measured on the change: `110 passed, 4 skipped`; the 4 skips
are `years_matrix.json` live-file checks that skip when `data/site` is absent).

- [ ] **Step 11: Native byte-identity on the live warehouse (read-only)**

Precondition: Task 16 has built `fct_program_decade_series` into the live
warehouse and S2 is closed. Create
`/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/task17/native_identity_proof.py`
(`.proofs/` is gitignored; nothing here writes data):

```python
"""Read-only proof (families piece 1, spec §6.1): on a warehouse that has
fct_program_decade_series, the switched decade tier's NATIVE output equals
the base commit's tier output, row for row and in order.

usage: python native_identity_proof.py WAREHOUSE.duckdb SCOPE_WAREHOUSE.duckdb
Reads only (DuckDB read_only, lake parquets). Prints one summary line and
exits 1 on any difference.
"""
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

import duckdb

from govbudget import export_site as new
from govbudget.jbooks.era_keys import is_era_procurement_key

WORKTREE = "/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families"
BASE = "10fb4585"
ERA_PREFIX = "sum(budget_lines.amount_thousands where era_line_map="

db, scope_db = sys.argv[1], sys.argv[2]
src = subprocess.run(
    ["git", "-C", WORKTREE, "show", f"{BASE}:GovBudget/src/govbudget/export_site.py"],
    capture_output=True, text=True, check=True,
).stdout
path = Path(tempfile.mkdtemp()) / "export_site_base.py"
path.write_text(src)
spec = importlib.util.spec_from_file_location("export_site_base", path)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

lake = new._stage_parquet_path(scope_db, "jbooks", "budget_lines.parquet")
con = duckdb.connect()
pb26 = {r[0] for r in con.execute(
    f"select distinct pe_bli from read_parquet('{lake}') where fiscal_year = '2026'"
    " and exhibit in ('R-1', 'P-1') and source_document_id is not null").fetchall()}
con.close()
scope = pb26 | set(new.decade_only_page_pes(scope_db)[0])

o_bl, o_cit, o_grains, o_side = base._build_decade_citation_rows(
    duckdb_path=db, existing_fids=set(), scope_pes=scope)
n_bl, n_cit, n_grains, n_side, era = new._build_decade_citation_rows(
    duckdb_path=db, existing_fids=set(), scope_pes=scope)

era_leaf = {r[0] for r in n_bl if is_era_procurement_key(r[8])}
era_sum = {r[0] for r in n_cit if (r[20] or "").startswith(ERA_PREFIX)}
era_any = era_leaf | era_sum


def mask(rows):  # derived rows carry the build timestamp in retrieved_at
    return [r[:19] + (None,) + r[20:] if r[1] == "derived" else r for r in rows]


checks = {
    "bl": [r for r in n_bl if r[0] not in era_leaf] == o_bl,
    "cit": mask([r for r in n_cit if r[0] not in era_any]) == mask(o_cit),
    "grains": [g for g in n_grains if g[5] not in era_any] == o_grains,
    "side": {k: v for k, v in n_side.items() if k not in era_any} == o_side,
    "era_marker": era <= era_any and all(g[5] in era for g in n_grains if g[5] in era_any),
}
print(
    f"native identical: {all(checks.values())} {checks} |"
    f" native bl {len(o_bl)}, cit {len(o_cit)}, grains {len(o_grains)} |"
    f" era bl {len(era_leaf)}, decade_era_map sums {len(era_sum)},"
    f" era grains with a page {len(era)}"
)
sys.exit(0 if all(checks.values()) else 1)
```

Run:

```bash
uv run --project . python /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/task17/native_identity_proof.py /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/duckdb/govbudget.duckdb /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/duckdb/govbudget.duckdb
```

Expected: exit 0 and a final line starting
`native identical: True {'bl': True, 'cit': True, 'grains': True, 'side': True, 'era_marker': True}`,
with native counts equal to the base tier's on the day (2026-10-02 on this
lake: `native bl 38762, cit 57566, grains 38354`) and positive era counts
(`era bl …, decade_era_map sums …, era grains with a page …`). Record the era
counts in the task report. If it prints `False`, rerun once (another session's
`dbt build` between the two reads is the only benign cause); a second `False`
is a defect — stop.

- [ ] **Step 12: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/src/govbudget/export_site.py GovBudget/tests/test_export_decade_era_map.py GovBudget/tests/test_export_breakdowns.py GovBudget/tests/jbooks/test_export_basis.py GovBudget/tests/jbooks/test_export_site_pg.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(export): decade tier reads fct_program_decade_series; era P-1 points through the reviewed map (families piece 1, spec §6.1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
