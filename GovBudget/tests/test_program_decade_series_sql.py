"""fct_program_decade_series and its dbt tests on a hand-built lake (families
piece 1, spec §4.5, V3).

The model is fct_decade_series plus one step: PB2017–PB2023 P-1 era rows the
owner decided (same_program / history_only in p1_era_line_map) are carried to
the bare printed code, with the map's pinned account/organization. These
tests render BOTH committed models (tests/dbt_render.py) on one throwaway
DuckDB and compare them, then show each singular test passing on the clean
fixture and failing on its defect.

Fixture (one slug per edition keeps the arithmetic visible):

  era key           ed    code        amount  map decision
  3010F-AF-L25      2019  F01500        100   same_program
  3010F-AF-L79      2019  F01500         50   same_program   (two BAs, one code)
  3010F-AF-L25      2020  F01500        120   same_program   (single-source grain)
  0300D-DSS-L21     2019  20              7   same_program, program_org DCSA (+
                                               a garbage program_account pin,
                                               dropped: '20' collides on org only)
  1810N-NAVY-L72    2019  3010           45   same_program, program_account 1810N
                                               (+ a garbage program_org pin,
                                               dropped: '3010' collides on acct only)
  3010F-AF-L80      2019  F0150P         30   history_only
  2035A-ARMY-L5     2019  5600D15603    900   undecided
  2035A-ARMY-L9     2019  FY2019CR       12   exclude_placeholder
  native: R-1 0207134F 2019 (70); PB2026 P-1 '20' DCSA 3 / DTRA 4,
          '3010' 1611N 1000 / 1810N 50, F01500 200 (+ a P-1R twin of 20)

FIFTEEN_* (added by the tests that need it): PB2019 code '15', no PB2026
collision, printed by DISA (40, same_program) and by TJS (9, history_only) —
the measured PB2021–PB2023 shape.
"""
import duckdb
import pytest
from dbt_render import ROOT, render_dbt_sql

LINE_MODEL = "dbt/models/marts/fct_decade_series.sql"
PROGRAM_MODEL = "dbt/models/marts/fct_program_decade_series.sql"
TESTS = "dbt/tests/{}.sql"

# (exhibit, fiscal_year, account, organization, ba, pe_bli, title, amount_type, amount, doc)
LAKE = [
    ("P-1", 2019, "3010F", "AF", "05", "3010F-AF-L25", "F-15", "fy_2019_total", 100.0, "271"),
    ("P-1", 2019, "3010F", "AF", "07", "3010F-AF-L79", "F-15", "fy_2019_total", 50.0, "271"),
    ("P-1", 2020, "3010F", "AF", "05", "3010F-AF-L25", "F-15", "fy_2020_total_base_oco", 120.0, "282"),
    ("P-1", 2019, "0300D", "DSS", "01", "0300D-DSS-L21", "Major Equipment, DSS", "fy_2019_total", 7.0, "271"),
    ("P-1", 2019, "1810N", "NAVY", "02", "1810N-NAVY-L72", "Shipboard Tactical Communications", "fy_2019_total", 45.0, "271"),
    ("P-1", 2019, "3010F", "AF", "07", "3010F-AF-L80", "F-15", "fy_2019_total", 30.0, "271"),
    ("P-1", 2019, "2035A", "ARMY", "03", "2035A-ARMY-L5", "JLTV", "fy_2019_total", 900.0, "271"),
    ("P-1", 2019, "2035A", "ARMY", "03", "2035A-ARMY-L9", "FY2019 CR adjustment", "fy_2019_total", 12.0, "271"),
    ("R-1", 2019, "3600F", "AF", "07", "0207134F", "F-15E Squadrons", "fy_2019_total", 70.0, "270"),
    ("P-1", 2026, "0300D", "DCSA", "01", "20", "Major Equipment, DCSA", "fy_2026_total", 3.0, "1"),
    ("P-1", 2026, "0300D", "DTRA", "01", "20", "Major Equipment, DTRA", "fy_2026_total", 4.0, "1"),
    ("P-1", 2026, "1611N", "N", "02", "3010", "LPD Flight II", "fy_2026_total", 1000.0, "1"),
    ("P-1", 2026, "1810N", "N", "02", "3010", "Shipboard Tactical Communications", "fy_2026_total", 50.0, "1"),
    ("P-1", 2026, "3010F", "F", "05", "F01500", "F-15", "fy_2026_total", 200.0, "1"),
    ("P-1R", 2026, "0300D", "DCSA", "01", "20", "Major Equipment, DCSA", "fy_2026_total", 1.0, "2"),
]

# (edition, era_key, line_item_code, program_key, program_account, program_org, decision)
MAP = [
    (2019, "3010F-AF-L25", "F01500", "F01500", None, None, "same_program"),
    (2019, "3010F-AF-L79", "F01500", "F01500", None, None, "same_program"),
    (2020, "3010F-AF-L25", "F01500", "F01500", None, None, "same_program"),
    # Both pins set (fix round 1): '20' collides on organization only in the
    # PB2026 fixture, so its garbage program_account ("ZZZZ") must be dropped;
    # '3010' collides on account only, so its garbage program_org ("ZZZZ")
    # must be dropped. See test_collision_codes_take_the_pinned_side_never_the_era_rows_own.
    (2019, "0300D-DSS-L21", "20", "20", "ZZZZ", "DCSA", "same_program"),
    (2019, "1810N-NAVY-L72", "3010", "3010", "1810N", "ZZZZ", "same_program"),
    (2019, "3010F-AF-L80", "F0150P", "F0150P", None, None, "history_only"),
    (2019, "2035A-ARMY-L5", "5600D15603", None, None, None, "undecided"),
    (2019, "2035A-ARMY-L9", "FY2019CR", None, None, None, "exclude_placeholder"),
]

DOCS = [("271", "s" * 64), ("282", "t" * 64), ("270", "u" * 64), ("1", "v" * 64), ("2", "w" * 64)]

FIFTEEN_LAKE = [
    ("P-1", 2019, "0300D", "DISA", "01", "0300D-DISA-L12", "Joint Forces Headquarters - DODIN", "fy_2019_total", 40.0, "271"),
    ("P-1", 2019, "0300D", "TJS", "01", "0300D-TJS-L50", "Major Equipment - TJS Cyber", "fy_2019_total", 9.0, "271"),
]
FIFTEEN_MAP = [
    (2019, "0300D-DISA-L12", "15", "15", None, None, "same_program"),
    (2019, "0300D-TJS-L50", "15", "15", None, None, "history_only"),
]


def _lake(lake=LAKE, era_map=MAP) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(
        "create table stg_budget_lines (exhibit varchar, fiscal_year integer,"
        " account varchar, account_title varchar, organization varchar,"
        " budget_activity varchar, budget_activity_title varchar, pe_bli varchar,"
        " title varchar, amount_type varchar, amount_thousands double,"
        " source_document_id varchar, line_item_code varchar)"
    )
    for ex, fy, acct, org, ba, pe, title, at, amt, doc in lake:
        con.execute(
            "insert into stg_budget_lines values (?, ?, ?, null, ?, ?, null, ?, ?, ?, ?, ?, null)",
            [ex, fy, acct, org, ba, pe, title, at, amt, doc],
        )
    con.execute("create table lake__jbook_documents (id varchar, sha256 varchar)")
    con.executemany("insert into lake__jbook_documents values (?, ?)", DOCS)
    con.execute(
        "create table p1_era_line_map (edition integer, era_key varchar,"
        " line_item_code varchar, program_key varchar, program_account varchar,"
        " program_org varchar, decision varchar)"
    )
    con.executemany("insert into p1_era_line_map values (?, ?, ?, ?, ?, ?, ?)", era_map)
    con.execute("create table fct_decade_series as " + render_dbt_sql(LINE_MODEL))
    con.execute("create table fct_program_decade_series as " + render_dbt_sql(PROGRAM_MODEL))
    return con


def _rows(con, where: str) -> list[dict]:
    cur = con.execute(f"select * from fct_program_decade_series where {where} order by all")
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _failures(con, test_name: str) -> list[tuple]:
    return con.execute(render_dbt_sql(TESTS.format(test_name))).fetchall()


# --- the verbatim-copy guard ------------------------------------------------

def _block(sql: str, start: str, end: str) -> str:
    i = sql.index(start)
    return sql[i:sql.index(end, i)].rstrip()


@pytest.mark.parametrize("start, end", [
    ("-- Collision anchor (E2.1 correction", "editions as ("),
    ("editions as (", "detail_sums as ("),
])
def test_shared_ctes_are_copied_verbatim_from_fct_decade_series(start, end):
    line_sql = (ROOT / LINE_MODEL).read_text()
    program_sql = (ROOT / PROGRAM_MODEL).read_text()
    block = _block(line_sql, start, end)
    assert block in program_sql, (
        f"fct_program_decade_series.sql no longer carries fct_decade_series.sql's"
        f" '{start}' block verbatim — change both models together")


def test_the_slug_pick_is_fct_decade_series_with_map_basis_in_the_partition():
    line_sql = (ROOT / LINE_MODEL).read_text()
    block = _block(line_sql, "chosen as (", "-- Raw lake sums per candidate slug")
    partition = "partition by pe_bli, account, organization, edition_year, scenario"
    assert block.count(partition) == 1
    expected = block.replace(
        partition, "partition by pe_bli, account, organization, map_basis, edition_year, scenario")
    assert expected in (ROOT / PROGRAM_MODEL).read_text(), (
        "fct_program_decade_series.sql's slug pick is no longer fct_decade_series.sql's"
        " with map_basis added to the partition — change both models together")


def test_the_row_fact_id_formula_is_fct_decade_series_byte_for_byte():
    line_sql = (ROOT / LINE_MODEL).read_text()
    formula = _block(line_sql, "substr(sha256(", "as row_fact_id")
    assert formula in (ROOT / PROGRAM_MODEL).read_text()


# --- behaviour --------------------------------------------------------------

def test_columns_are_fct_decade_series_plus_map_basis_and_source_keys():
    con = _lake()
    cols = [d[0] for d in con.execute("select * from fct_program_decade_series limit 0").description]
    assert cols == [
        "program_key", "fy", "edition_year", "amount_type_kind", "amount", "amount_thousands",
        "scenario", "amount_type", "account", "organization", "n_source_rows", "source_fact_id",
        "map_basis", "source_keys",
    ]


def test_era_lines_sharing_a_code_sum_into_one_program_grain():
    [row] = _rows(_lake(), "program_key = 'F01500' and edition_year = 2019")
    assert (row["fy"], row["amount_type_kind"], row["amount"], row["n_source_rows"]) == (
        2019, "request", 150.0, 2)
    assert (row["source_fact_id"], row["map_basis"], row["source_keys"]) == (
        None, "era_line_map", "3010F-AF-L25,3010F-AF-L79")
    assert (row["account"], row["organization"]) == (None, None)


def test_a_single_era_key_keeps_the_fact_id_it_already_has():
    con = _lake()
    [row] = _rows(con, "program_key = 'F01500' and edition_year = 2020")
    line_fid = con.execute(
        "select source_fact_id from fct_decade_series"
        " where pe_bli = '3010F-AF-L25' and edition_year = 2020"
    ).fetchone()[0]
    assert row["source_fact_id"] == line_fid and line_fid is not None
    assert (row["amount"], row["n_source_rows"], row["source_keys"]) == (120.0, 1, "3010F-AF-L25")


def test_collision_codes_take_the_pinned_side_never_the_era_rows_own():
    # MAP sets BOTH program_account and program_org for '20' and '3010' (fix
    # round 1), with a garbage sentinel ("ZZZZ") on the axis each code does
    # NOT actually collide on in the PB2026 fixture. Asserting None on that
    # axis proves the model discards it — not merely that it was never set.
    con = _lake()
    [org_side] = _rows(con, "program_key = '20' and edition_year = 2019")
    assert (org_side["account"], org_side["organization"], org_side["amount"]) == (None, "DCSA", 7.0)
    [acct_side] = _rows(con, "program_key = '3010' and edition_year = 2019")
    assert (acct_side["account"], acct_side["organization"], acct_side["amount"]) == ("1810N", None, 45.0)


def test_a_mapped_key_with_null_program_key_surfaces_as_null_not_as_the_era_key():
    # Fix round 1: a map row whose program_key is wrongly NULL (data bug —
    # program_key is non-NULL for every same_program/history_only decision in
    # practice) must publish program_key = NULL, never silently fall back to
    # the era key. coalesce(m.program_key, b.pe_bli) used to do exactly that
    # fallback and pass every test; `case when m.era_key is not null then
    # m.program_key else b.pe_bli end` does not.
    bad_map = MAP + [(2019, "0300D-DSS-L99", "UNSET", None, None, None, "same_program")]
    bad_lake = LAKE + [
        ("P-1", 2019, "0300D", "DSS", "01", "0300D-DSS-L99", "Bad row", "fy_2019_total", 5.0, "271"),
    ]
    con = _lake(lake=bad_lake, era_map=bad_map)
    rows = con.execute(
        "select program_key from fct_program_decade_series where source_keys = '0300D-DSS-L99'"
    ).fetchall()
    assert rows and all(r[0] is None for r in rows), (
        "a mapped key with NULL program_key must publish program_key = NULL so"
        " not_null_fct_program_decade_series_program_key catches it, never the era key")
    keys = {r[0] for r in con.execute("select program_key from fct_program_decade_series").fetchall()}
    assert "0300D-DSS-L99" not in keys


def test_history_only_is_carried_and_labelled():
    [row] = _rows(_lake(), "program_key = 'F0150P'")
    assert (row["edition_year"], row["amount"], row["map_basis"]) == (2019, 30.0, "era_history_only")


def test_undecided_and_excluded_era_keys_produce_no_grain():
    con = _lake()
    keys = {r[0] for r in con.execute("select program_key from fct_program_decade_series").fetchall()}
    assert not keys & {"5600D15603", "FY2019CR", "2035A-ARMY-L5", "2035A-ARMY-L9"}
    assert not [k for k in keys if "-L" in k], "no era key survives as a program key"


def test_native_rows_are_fct_decade_series_rows():
    con = _lake()
    native = con.execute(
        "select program_key, account, organization, fy, edition_year, amount, amount_type,"
        " n_source_rows, source_fact_id from fct_program_decade_series"
        " where map_basis = 'native' order by all"
    ).fetchall()
    line = con.execute(
        "select pe_bli, account, organization, fy, edition_year, amount, amount_type,"
        " n_source_rows, source_fact_id from fct_decade_series"
        " where not regexp_matches(pe_bli, '^[0-9]{4}[A-Z]-[A-Z]+-L') order by all"
    ).fetchall()
    assert native == line and len(native) == 6


def test_history_only_and_same_program_keys_of_one_code_and_edition_stay_apart():
    con = _lake(lake=LAKE + FIFTEEN_LAKE, era_map=MAP + FIFTEEN_MAP)
    rows = sorted(_rows(con, "program_key = '15'"), key=lambda r: r["map_basis"])
    assert [(r["map_basis"], r["amount"], r["n_source_rows"], r["source_keys"]) for r in rows] == [
        ("era_history_only", 9.0, 1, "0300D-TJS-L50"),
        ("era_line_map", 40.0, 1, "0300D-DISA-L12"),
    ]
    page = rows[1]
    assert (page["account"], page["organization"], page["fy"], page["edition_year"]) == (
        None, None, 2019, 2019)
    # the page's row is single-source again, so it keeps DISA's own fact ID
    disa_fid = con.execute(
        "select source_fact_id from fct_decade_series where pe_bli = '0300D-DISA-L12'"
    ).fetchone()[0]
    assert page["source_fact_id"] == disa_fid and disa_fid is not None
    for test_name in ("assert_program_decade_grain_unique", "assert_program_decade_conservation",
                      "assert_program_decade_native_equals_line"):
        assert _failures(con, test_name) == [], test_name


def test_an_era_code_equal_to_a_native_key_in_the_same_edition_fails_grain_unique():
    era_map = MAP + [(2019, "3600F-AF-L1", "0207134F", "0207134F", None, None, "same_program")]
    lake = LAKE + [("P-1", 2019, "3600F", "AF", "01", "3600F-AF-L1", "Odd", "fy_2019_total", 1.0, "271")]
    con = _lake(lake=lake, era_map=era_map)
    rows = _rows(con, "program_key = '0207134F'")
    assert sorted((r["map_basis"], r["amount"]) for r in rows) == [("era_line_map", 1.0), ("native", 70.0)]
    assert _failures(con, "assert_program_decade_grain_unique") == [
        ("two rows a page reads share one grain", "0207134F", None, None, 2019, 2019,
         "era_line_map,native", 2)]
    # the native row stays fct_decade_series' row: the era dollar sits beside it
    assert _failures(con, "assert_program_decade_native_equals_line") == []


# --- the singular tests -------------------------------------------------------

@pytest.mark.parametrize("test_name", [
    "assert_program_decade_native_equals_line",
    "assert_program_decade_conservation",
    "assert_program_decade_grain_unique",
])
def test_singular_test_passes_on_the_clean_fixture(test_name):
    assert _failures(_lake(), test_name) == []


def test_native_equals_line_fails_on_a_changed_amount_and_a_lost_row():
    con = _lake()
    con.execute("update fct_program_decade_series set amount = amount + 1 where program_key = '0207134F'")
    con.execute("delete from fct_program_decade_series where program_key = 'F01500' and edition_year = 2026")
    failures = sorted(r[0] for r in _failures(con, "assert_program_decade_native_equals_line"))
    assert failures == ["fct_decade_series grain missing from the program table",
                        "native program row differs from fct_decade_series"]


def test_conservation_fails_when_an_era_grain_is_lost():
    con = _lake()
    con.execute("delete from fct_program_decade_series where program_key = 'F0150P'")
    assert _failures(con, "assert_program_decade_conservation") == [
        ("era grain does not conserve the fct_decade_series era grains it carries",
         2019, "request", "fy_2019_total", 232.0, 202.0, 5, 4)]


def test_conservation_fails_when_an_excluded_key_leaks_in():
    con = _lake()
    con.execute(
        "insert into fct_program_decade_series select 'FY2019CR', 2019, 2019, 'request', 12.0, 12.0,"
        " 'BudgetYearOne', 'fy_2019_total', null, null, 1, null, 'era_line_map', '2035A-ARMY-L9'"
    )
    # The bogus grain also disagrees on basis (2035A-ARMY-L9 is decided
    # exclude_placeholder, not same_program), so both legs fire.
    assert sorted(_failures(con, "assert_program_decade_conservation")) == sorted([
        ("era grain does not conserve the fct_decade_series era grains it carries",
         2019, "request", "fy_2019_total", 232.0, 244.0, 5, 6),
        ("grain map_basis disagrees with the decision of a summed source key",
         2019, "era_line_map", "2035A-ARMY-L9", None, None, None, None),
    ])


def test_conservation_fails_when_a_grain_basis_is_relabelled():
    # Fix round 1: relabelling F0150P's grain from era_history_only to
    # era_line_map leaves the combined dollar/row-count leg untouched (the
    # key's amount is still counted somewhere under map_basis in
    # ('era_line_map', 'era_history_only')) — only the new basis-fidelity leg
    # catches it, since the key's own decision (history_only) no longer
    # matches the map_basis it now carries (era_line_map).
    con = _lake()
    con.execute(
        "update fct_program_decade_series set map_basis = 'era_line_map'"
        " where program_key = 'F0150P'"
    )
    assert _failures(con, "assert_program_decade_conservation") == [
        ("grain map_basis disagrees with the decision of a summed source key",
         2019, "era_line_map", "3010F-AF-L80", None, None, None, None)]


def test_grain_unique_fails_on_a_duplicate_grain():
    con = _lake()
    con.execute(
        "insert into fct_program_decade_series select * from fct_program_decade_series"
        " where program_key = '20' and edition_year = 2019"
    )
    assert sorted(_failures(con, "assert_program_decade_grain_unique")) == [
        ("duplicate grain", "20", None, "DCSA", 2019, 2019, "era_line_map", 2),
        ("two rows a page reads share one grain", "20", None, "DCSA", 2019, 2019,
         "era_line_map,era_line_map", 2),
    ]


def test_grain_unique_fails_on_a_duplicate_history_only_grain():
    con = _lake()
    con.execute(
        "insert into fct_program_decade_series select * from fct_program_decade_series"
        " where program_key = 'F0150P'"
    )
    # pages never read history_only rows, so only the per-basis leg fires
    assert _failures(con, "assert_program_decade_grain_unique") == [
        ("duplicate grain", "F0150P", None, None, 2019, 2019, "era_history_only", 2)]
