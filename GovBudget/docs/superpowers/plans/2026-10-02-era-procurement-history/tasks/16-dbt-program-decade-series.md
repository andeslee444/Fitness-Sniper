<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 16: dbt `fct_program_decade_series` and its tests

**Spec:** §4.5 (program grain, bare `program_key`, pinned account/organization on collision codes,
same aggregation, `row_fact_id` from the source row, `map_basis`, `source_keys`, native parity
over all editions, `fct_decade_series` untouched), with the grain corrected per G4-4 (`map_basis`
is part of the grain; the five-column key is unique among the `native` and `era_line_map` rows
pages read); §7 "Several era lines share one code" and "Code spanning organizations" (a
history-only chain never adds dollars to a same_program page); V3
`assert_program_decade_{native_equals_line,conservation,grain_unique}`; S3.

**Files:**
- Create: `GovBudget/tests/test_program_decade_series_sql.py`
- Create: `GovBudget/dbt/models/marts/fct_program_decade_series.sql`
- Create: `GovBudget/dbt/tests/assert_program_decade_native_equals_line.sql`,
  `assert_program_decade_conservation.sql`, `assert_program_decade_grain_unique.sql`
- Modify: `GovBudget/dbt/models/marts/schema.yml` (append after the `p1_era_line_map` entry Task 13
  added at the end of the file)
- Not modified: `GovBudget/dbt/models/marts/fct_decade_series.sql`

**Interfaces:** Consumes: `p1_era_line_map` (`edition, era_key, program_key, program_account,
program_org, decision`; Task 13, every key decided by Task 15); `stg_budget_lines`;
`fct_decade_series` (tests only); source `lake.jbook_documents`; `tests/dbt_render.py`
(Task 13). Produces: table `fct_program_decade_series` with columns `program_key, fy,
edition_year, amount_type_kind, amount, amount_thousands, scenario, amount_type, account,
organization, n_source_rows, source_fact_id, map_basis, source_keys`; grain `(program_key,
account, organization, fy, edition_year, map_basis)`, unique on `(program_key, account,
organization, fy, edition_year)` among rows with `map_basis` in (`native`, `era_line_map`)
(G4-4); the three dbt tests.

Measured read-only on 2026-10-02 from the live `fct_decade_series` (the numbers the tests and
steps cite): 59,179 rows = 20,781 era grains (6,927 keys × 3 kinds, every one single-source) +
38,398 native grains, of which 22,008 are PB2017–PB2023 R-1 and 16,390 PB2024–PB2026;
account non-NULL on 163 rows of 10 codes, organization on 71 rows of 3 codes (`0145 1350 2101
2210 2292 3010 3050 3215 3302 4217` / `20 30 500`). Within each era edition every key picks the
same slug per scenario (PB2017 `fy_2015_base_oco`/`fy_2016_total_enacted`/`fy_2017_total` …
PB2023 `fy_2021_base_oco`/`fy_2022_enactment`/`fy_2023_request`), no era printed code equals an
R-1 program element in any edition, and every `budget_lines` amount is a whole number of
thousands (0 of 159,494 rows carry a fraction). From the research classes
(`scratchpad/era_map/era_map_proposal.csv`): a non-collision code can carry a `history_only`
chain and a `same_program` chain in one edition (`10` PB2018 DPAA/TJS, `15` PB2021–PB2023 TJS
Cyber/DISA, and two-account codes such as `0182` PB2017–PB2022), which is why `map_basis` is part
of the grain (G4-4).

- [ ] **Step 1: Confirm the design and the inputs (read-only)**

Design choice — (ii) a separate model, not (i) a macro shared with `fct_decade_series`:
1. Spec §4.5 says `fct_decade_series` is not touched. A macro means rewriting that file into a
   call, so the mart F-15's builder, verify-phase5e and `fct_book_diff` read would have to be
   proven byte-identical in compiled SQL (Jinja whitespace makes that a proof of its own),
   re-reviewed, and its 150-line decision history would move away from the SQL it explains.
2. The difference is small and local: a map join in `lake`/`detail`, the era-row filter,
   `map_basis` carried as a grouping column (`detail_sums`, the slug-pick partition, `lake_sums`
   and the lake check), and `source_keys`. As macro parameters those become `{% if %}` branches
   through the shared body, and every later change to either model has to reason about both.
3. Drift is guarded without sharing code: `assert_program_decade_native_equals_line` compares every
   native row with `fct_decade_series` on every build, and
   `tests/test_program_decade_series_sql.py` fails at unit-test time if the collision anchors, the
   candidate patterns or the `row_fact_id` formula stop being verbatim copies, or the slug pick
   stops being `fct_decade_series`' with `map_basis` as its one added partition column.
Cost: about 100 lines of copied SQL, held in step by those two guards.

Check the inputs:

```bash
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data \
uv run --project . python -c "
import duckdb
con = duckdb.connect('/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/duckdb/govbudget.duckdb', read_only=True)
print(con.execute(\"select count(*), count(*) filter (where decision = 'undecided' or keys_sha_ok = false) from p1_era_line_map\").fetchall())
print(con.execute('select count(*) from fct_decade_series').fetchall())"
grep -rn "fct_program_decade_series" src/ | wc -l
```

Expected: `[(6927, 0)]` (Task 15 closed S2), `[(59179,)]`, `0` (`wc` pads it with spaces). If the second number of the first
line is not 0, finish Task 15 first.

- [ ] **Step 2: Write the failing tests**

Create `GovBudget/tests/test_program_decade_series_sql.py`:

```python
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
  0300D-DSS-L21     2019  20              7   same_program, program_org DCSA
  1810N-NAVY-L72    2019  3010           45   same_program, program_account 1810N
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
    (2019, "0300D-DSS-L21", "20", "20", None, "DCSA", "same_program"),
    (2019, "1810N-NAVY-L72", "3010", "3010", "1810N", None, "same_program"),
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
    con = _lake()
    [org_side] = _rows(con, "program_key = '20' and edition_year = 2019")
    assert (org_side["account"], org_side["organization"], org_side["amount"]) == (None, "DCSA", 7.0)
    [acct_side] = _rows(con, "program_key = '3010' and edition_year = 2019")
    assert (acct_side["account"], acct_side["organization"], acct_side["amount"]) == ("1810N", None, 45.0)


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
        (2019, "request", "fy_2019_total", 232.0, 202.0, 5, 4)]


def test_conservation_fails_when_an_excluded_key_leaks_in():
    con = _lake()
    con.execute(
        "insert into fct_program_decade_series select 'FY2019CR', 2019, 2019, 'request', 12.0, 12.0,"
        " 'BudgetYearOne', 'fy_2019_total', null, null, 1, null, 'era_line_map', '2035A-ARMY-L9'"
    )
    assert _failures(con, "assert_program_decade_conservation") == [
        (2019, "request", "fy_2019_total", 232.0, 244.0, 5, 6)]


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
```

- [ ] **Step 3: Run the tests to see them fail**

Run: `uv run --project . pytest tests/test_program_decade_series_sql.py -q`

Expected: `21 failed`, each with
`FileNotFoundError: [Errno 2] No such file or directory: '…/GovBudget/dbt/models/marts/fct_program_decade_series.sql'`.

- [ ] **Step 4: Write the model**

Create `GovBudget/dbt/models/marts/fct_program_decade_series.sql`. The blocks from
`-- Collision anchor (E2.1 correction` through `org_collision_pes` and from `editions as (` through
`candidates` are copied byte for byte from `fct_decade_series.sql` lines 190-232 and 234-272;
`chosen as (` is lines 307-326 with one line changed — `map_basis` added to the `partition by`
(their comments refer to that file's header):

```sql
-- fct_program_decade_series: the edition-aware decade series at PROGRAM grain
-- (families piece 1, spec §4.5). The same CTEs as fct_decade_series, with one
-- step added: PB2017–PB2023 P-1 era rows are carried to the budget line code
-- they print, through the owner-reviewed p1_era_line_map.
--
-- Grain: (program_key, account, organization, fy, edition_year, map_basis).
-- Among the rows pages read — map_basis 'native' and 'era_line_map' — the
-- five columns without map_basis are unique: exactly fct_decade_series'
-- uniqueness key with pe_bli renamed program_key
-- (assert_program_decade_grain_unique.sql). program_key is ALWAYS the bare
-- printed code; account/organization are non-NULL only for the 13 PB2026
-- collision codes, exactly as in fct_decade_series. No suffixed key exists.
--
-- What changes against fct_decade_series, and nothing else:
--   * an era row (pe_bli '{account}-{org}-L{line}') enters ONLY when its map
--     decision is same_program or history_only. Its pe_bli becomes the map's
--     program_key, and its account/organization become the map's pinned
--     program_account/program_org — never the era row's own values — so a
--     pinned chain (e.g. '20' DSS -> DCSA) lands on the PB2026 side it was
--     decided for. Excluded and undecided era rows produce no grain at all.
--   * Same aggregation as today: era lines that share a code and a
--     map_basis in an edition (advance-procurement pairs, lines in two
--     budget activities, a non-collision code under two accounts) are summed
--     at the detail step before slug selection, exactly as modern lines that
--     share a code already are. Measured 2026-10-02: every era key of an
--     edition picks the same slug per scenario, so the program sum equals the
--     sum of the fct_decade_series era grains it absorbs
--     (assert_program_decade_conservation.sql).
--   * row_fact_id still hashes the SOURCE row's own identity (its era key,
--     its own account and organization) — the formula below is
--     fct_decade_series' byte for byte — so a single-source era grain's
--     source_fact_id is the fact ID the era row already has.
--   * map_basis is part of the grouping key, from detail through the slug
--     pick to the lake check: 'native' (no era row), 'era_line_map'
--     (same_program era keys — what the code's page reads), and
--     'era_history_only' (history_only era keys — data, no page). Rows of
--     different bases never sum into one grain. A history_only chain and a
--     same_program chain that print the same code in the same edition
--     (measured 2026-10-02: '10' in PB2018, DPAA beside TJS; '15' in
--     PB2021–PB2023, TJS Cyber beside DISA) give two rows, and the
--     era_line_map row the page reads sums only the same_program keys. A
--     native row and an era row on one five-column key would be two rows a
--     page reads: assert_program_decade_grain_unique.sql fails on that
--     (measured 2026-10-02: no era code equals an R-1 program element in any
--     edition).
--   * source_keys: the era keys summed, sorted, comma-separated; NULL for
--     native grains.
--
-- Parity: every map_basis='native' row — all editions, including the 22,008
-- PB2017–PB2023 R-1 grains — equals its fct_decade_series row column for
-- column (assert_program_decade_native_equals_line.sql). The collision
-- anchors and the candidate patterns below are copied VERBATIM from
-- fct_decade_series.sql, and the slug pick is copied with map_basis added to
-- its partition; tests/test_program_decade_series_sql.py fails if they drift
-- apart. fct_decade_series itself is not touched (F-15's builder,
-- verify-phase5e and fct_book_diff keep reading it).

{{ config(materialized='table') }}

with era_map as (
    select
        edition,
        era_key,
        program_key,
        program_account,
        program_org,
        decision
    from {{ ref('p1_era_line_map') }}
    where decision in ('same_program', 'history_only')
),

lake as (
    select
        b.exhibit,
        coalesce(m.program_key, b.pe_bli) as pe_bli,
        b.fiscal_year as edition_year,
        b.amount_type,
        b.amount_thousands,
        case when m.era_key is not null then m.program_account else b.account end as account,
        case when m.era_key is not null then m.program_org else b.organization end as organization,
        case m.decision
            when 'same_program' then 'era_line_map'
            when 'history_only' then 'era_history_only'
            else 'native'
        end as map_basis
    from {{ ref('stg_budget_lines') }} b
    left join era_map m
      on b.exhibit = 'P-1'
     and m.edition = b.fiscal_year
     and m.era_key = b.pe_bli
),

detail as (
    select
        coalesce(m.program_key, b.pe_bli) as pe_bli,
        b.fiscal_year as edition_year,
        b.amount_type,
        case when m.era_key is not null then m.program_account else b.account end as account,
        case when m.era_key is not null then m.program_org else b.organization end as organization,
        b.amount_thousands,
        substr(sha256(
            d.sha256 || '|' || b.exhibit || '|' || cast(b.fiscal_year as varchar)
            || '|' || b.account || '|' || b.organization || '|'
            || coalesce(b.budget_activity, '') || '|' || b.pe_bli || '|' || b.amount_type
        ), 1, 16) as row_fact_id,
        case when m.era_key is not null then b.pe_bli end as source_key,
        case m.decision
            when 'same_program' then 'era_line_map'
            when 'history_only' then 'era_history_only'
            else 'native'
        end as map_basis
    from {{ ref('stg_budget_lines') }} b
    left join {{ source('lake', 'jbook_documents') }} d
      on d.id = b.source_document_id
    left join era_map m
      on b.exhibit = 'P-1'
     and m.edition = b.fiscal_year
     and m.era_key = b.pe_bli
    where b.exhibit in ('R-1', 'P-1')
      and b.source_document_id is not null
      and b.pe_bli <> '9999999999'
      and (
          m.era_key is not null
          or not (b.exhibit = 'P-1' and regexp_matches(b.pe_bli, '^[0-9]{4}[A-Z]-[A-Z]+-L'))
      )
),

-- Collision anchor (E2.1 correction, 2026-08-21 — see the model-level
-- comment above): >1 distinct account reporting at the SAME amount_type,
-- checked across EVERY amount_type PB2026's own workbook carries (not
-- only fy_2026_total). Independently re-derived (this mart reads
-- stg_budget_lines directly and is not downstream of dim_programs in the
-- dbt DAG).
collision_slots as (
    select pe_bli, amount_type, account
    from {{ ref('stg_budget_lines') }}
    where fiscal_year = 2026
      and title is not null
      and pe_bli <> '9999999999'
    group by pe_bli, amount_type, account
),
collision_pes as (
    select distinct pe_bli
    from (
        select pe_bli
        from collision_slots
        group by pe_bli, amount_type
        having count(distinct account) > 1
    )
),

-- ROADMAP #45 organization collision anchor — collision_pes' mirror on
-- organization instead of account (see the model-level comment above).
org_collision_slots as (
    select pe_bli, amount_type, organization
    from {{ ref('stg_budget_lines') }}
    where fiscal_year = 2026
      and title is not null
      and pe_bli <> '9999999999'
    group by pe_bli, amount_type, organization
),
org_collision_pes as (
    select distinct pe_bli
    from (
        select pe_bli
        from org_collision_slots
        group by pe_bli, amount_type
        having count(distinct organization) > 1
    )
),

editions as (
    select distinct edition_year from detail
),

-- Candidate slug patterns: a 1:1 transcription of reconcile.scenario_map
-- (PriorYear / CurrentYear / BudgetYearOne; BudgetYearOneBase is not a
-- series kind). priority = list order = the any-candidate pick order.
cand_patterns (scenario, priority, slug_template, fy_offset) as (
    values
        ('PriorYear', 1, 'fy_%d_actuals', 2),
        ('PriorYear', 2, 'fy_%d_base_oco', 2),
        ('PriorYear', 3, 'fy_%d_actual', 2),
        ('CurrentYear', 1, 'fy_%d_total', 1),
        ('CurrentYear', 2, 'fy_%d_enacted', 1),
        ('CurrentYear', 3, 'fy_%d_total_enacted', 1),
        ('CurrentYear', 4, 'fy_%d_less_supplementals_enacted', 1),
        ('CurrentYear', 5, 'fy_%d_pb_request_with_cr_amounts', 1),
        ('CurrentYear', 6, 'fy_%d_pb_request_with_cr_adjustments', 1),
        ('CurrentYear', 7, 'fy_%d_enactment', 1),
        ('CurrentYear', 8, 'fy_%d_total_enacted_base_emerg_oco', 1),
        ('CurrentYear', 9, 'fy_%d_total_pb_requests_with_cr_adj_base_oco', 1),
        ('CurrentYear', 10, 'fy_%d_total_pb_requests_with_cr_adj_base_oco_saa', 1),
        ('CurrentYear', 11, 'fy_%d_total_pb_requests_with_cr_adj_base_oco_emergency', 1),
        ('BudgetYearOne', 1, 'fy_%d_total', 0),
        ('BudgetYearOne', 2, 'fy_%d_disc_request', 0),
        ('BudgetYearOne', 3, 'fy_%d_request', 0),
        ('BudgetYearOne', 4, 'fy_%d_total_base_oco', 0)
),

candidates as (
    select
        e.edition_year,
        c.scenario,
        c.priority,
        c.fy_offset,
        printf(c.slug_template, e.edition_year - c.fy_offset) as amount_type
    from editions e
    cross join cand_patterns c
),

detail_sums as (
    select
        d.pe_bli,
        d.edition_year,
        c.scenario,
        c.priority,
        c.fy_offset,
        c.amount_type,
        case when cp.pe_bli is not null then d.account end as account,
        case when ocp.pe_bli is not null then d.organization end as organization,
        d.map_basis,
        sum(d.amount_thousands) as amount,
        count(*) as n_source_rows,
        case when count(*) = 1 then min(d.row_fact_id) end as source_fact_id,
        string_agg(distinct d.source_key, ',' order by d.source_key) as source_keys
    from detail d
    join candidates c
      on c.edition_year = d.edition_year
     and c.amount_type = d.amount_type
    left join collision_pes cp
      on cp.pe_bli = d.pe_bli
    left join org_collision_pes ocp
      on ocp.pe_bli = d.pe_bli
    group by
        d.pe_bli, d.edition_year, c.scenario, c.priority, c.fy_offset, c.amount_type,
        case when cp.pe_bli is not null then d.account end,
        case when ocp.pe_bli is not null then d.organization end,
        d.map_basis
),

-- The slug pick is fct_decade_series' with one change: map_basis joins the
-- partition, so a same_program grain and a history_only grain of one code
-- and edition each pick their own top-priority slug (every era key of an
-- edition prints the same slugs, so both pick the same one).
chosen as (
    select * from (
        select
            *,
            row_number() over (
                -- account/organization in the partition: each side of a
                -- genuine collision (account OR organization, whichever
                -- axis this pe_bli actually splits on) picks its OWN
                -- top-priority candidate slug independently. Without this,
                -- row_number() would rank every side's rows together and
                -- could arbitrarily discard one side's only row as a
                -- tie-broken rn=2 (DuckDB does not guarantee priority ties
                -- resolve by account/organization) — this pins the fix.
                partition by pe_bli, account, organization, map_basis, edition_year, scenario
                order by priority
            ) as rn
        from detail_sums
    )
    where rn = 1
),

-- Raw lake sums per candidate slug, as in fct_decade_series (no title
-- filter, every exhibit except P-1R), over the same mapped lake: an era row
-- carried by the map counts under its program_key, pinned
-- account/organization and map_basis, so a program grain is verified against
-- the lake sum of exactly the rows it absorbed.
lake_sums as (
    select
        l.pe_bli,
        l.edition_year,
        c.scenario,
        case when cp.pe_bli is not null then l.account end as account,
        case when ocp.pe_bli is not null then l.organization end as organization,
        l.map_basis,
        sum(l.amount_thousands) as lake_amount
    from lake l
    join candidates c
      on c.edition_year = l.edition_year
     and c.amount_type = l.amount_type
    left join collision_pes cp
      on cp.pe_bli = l.pe_bli
    left join org_collision_pes ocp
      on ocp.pe_bli = l.pe_bli
    where l.exhibit <> 'P-1R'
    group by l.pe_bli, l.edition_year, c.scenario, c.amount_type,
             case when cp.pe_bli is not null then l.account end,
             case when ocp.pe_bli is not null then l.organization end,
             l.map_basis
)

select
    ch.pe_bli as program_key,
    ch.edition_year - ch.fy_offset as fy,
    ch.edition_year,
    case ch.scenario
        when 'PriorYear' then 'actuals'
        when 'CurrentYear' then 'enacted'
        when 'BudgetYearOne' then 'request'
    end as amount_type_kind,
    ch.amount,
    ch.amount as amount_thousands,
    ch.scenario,
    ch.amount_type,
    ch.account,
    ch.organization,
    ch.n_source_rows,
    ch.source_fact_id,
    ch.map_basis,
    ch.source_keys
from chosen ch
where exists (
    select 1
    from lake_sums ls
    where ls.pe_bli = ch.pe_bli
      and ls.edition_year = ch.edition_year
      and ls.scenario = ch.scenario
      and ls.account is not distinct from ch.account
      and ls.organization is not distinct from ch.organization
      and ls.map_basis = ch.map_basis
      and abs(ls.lake_amount - ch.amount) <= 0.5
)
```

- [ ] **Step 5: Run the tests — the model tests pass, the singular-test tests still fail**

Run: `uv run --project . pytest tests/test_program_decade_series_sql.py -q`

Expected: `10 failed, 11 passed`; every failure is
`FileNotFoundError: … dbt/tests/assert_program_decade_<name>.sql` (5 name `grain_unique`, 3
`conservation`, 2 `native_equals_line`).

- [ ] **Step 6: Write the three dbt tests**

Create `GovBudget/dbt/tests/assert_program_decade_native_equals_line.sql`:

```sql
-- Native parity (families piece 1, spec §4.5): every fct_program_decade_series
-- row that involves no era row (map_basis = 'native') equals its
-- fct_decade_series row column for column, in EVERY edition — PB2024–PB2026
-- R-1 and P-1, and the 22,008 PB2017–PB2023 R-1 grains (measured
-- 2026-10-02: 38,398 native grains in all). The book-diff join and the
-- exporter's derived-ID mirror depend on it.
--
-- Checked both ways: a fct_decade_series grain that is not an era key must
-- appear in the program table as a native row, and a native program row
-- must have a fct_decade_series twin. Amounts compare exactly: every lake
-- amount is a whole number of thousands (measured 2026-10-02: 0 of 159,494
-- budget_lines rows carry a fraction), so both double sums are exact.
with line as (
    select *
    from {{ ref('fct_decade_series') }}
    where not regexp_matches(pe_bli, '^[0-9]{4}[A-Z]-[A-Z]+-L')
),
native as (
    select *
    from {{ ref('fct_program_decade_series') }}
    where map_basis = 'native'
)

select
    'fct_decade_series grain missing from the program table' as failure,
    l.pe_bli as program_key, l.account, l.organization, l.fy, l.edition_year
from line l
left join native n
  on n.program_key = l.pe_bli
 and n.account is not distinct from l.account
 and n.organization is not distinct from l.organization
 and n.fy = l.fy
 and n.edition_year = l.edition_year
where n.program_key is null

union all

select
    'native program row without a fct_decade_series twin',
    n.program_key, n.account, n.organization, n.fy, n.edition_year
from native n
left join line l
  on l.pe_bli = n.program_key
 and l.account is not distinct from n.account
 and l.organization is not distinct from n.organization
 and l.fy = n.fy
 and l.edition_year = n.edition_year
where l.pe_bli is null

union all

select
    'native program row differs from fct_decade_series',
    n.program_key, n.account, n.organization, n.fy, n.edition_year
from native n
join line l
  on l.pe_bli = n.program_key
 and l.account is not distinct from n.account
 and l.organization is not distinct from n.organization
 and l.fy = n.fy
 and l.edition_year = n.edition_year
where l.amount_type_kind is distinct from n.amount_type_kind
   or l.amount is distinct from n.amount
   or l.amount_thousands is distinct from n.amount_thousands
   or l.scenario is distinct from n.scenario
   or l.amount_type is distinct from n.amount_type
   or l.n_source_rows is distinct from n.n_source_rows
   or l.source_fact_id is distinct from n.source_fact_id
   or n.source_keys is not null
```

Create `GovBudget/dbt/tests/assert_program_decade_conservation.sql`:

```sql
-- Conservation (families piece 1, spec §4.5 and V3): for every edition and
-- slug, the program grains that carry era rows (map_basis era_line_map /
-- era_history_only) hold exactly the dollars and the source rows of the
-- fct_decade_series era grains whose keys the map carries (decision
-- same_program or history_only) — no era key dropped, double-counted, or
-- withheld by the lake-verifiability filter, and nothing excluded or
-- undecided leaking in. Per (edition_year, amount_type_kind, amount_type).
-- Amounts are whole thousands (see assert_program_decade_native_equals_line),
-- so the 0.5 tolerance only absorbs representation, never a real dollar.
with carried as (
    select edition, era_key
    from {{ ref('p1_era_line_map') }}
    where decision in ('same_program', 'history_only')
),
line as (
    select
        f.edition_year,
        f.amount_type_kind,
        f.amount_type,
        sum(f.amount) as amount,
        sum(f.n_source_rows) as n_source_rows
    from {{ ref('fct_decade_series') }} f
    join carried k
      on k.era_key = f.pe_bli
     and k.edition = f.edition_year
    group by f.edition_year, f.amount_type_kind, f.amount_type
),
program as (
    select
        edition_year,
        amount_type_kind,
        amount_type,
        sum(amount) as amount,
        sum(n_source_rows) as n_source_rows
    from {{ ref('fct_program_decade_series') }}
    where map_basis in ('era_line_map', 'era_history_only')
    group by edition_year, amount_type_kind, amount_type
)

select
    coalesce(l.edition_year, p.edition_year) as edition_year,
    coalesce(l.amount_type_kind, p.amount_type_kind) as amount_type_kind,
    coalesce(l.amount_type, p.amount_type) as amount_type,
    l.amount as line_amount,
    p.amount as program_amount,
    l.n_source_rows as line_rows,
    p.n_source_rows as program_rows
from line l
full outer join program p
  on p.edition_year = l.edition_year
 and p.amount_type_kind = l.amount_type_kind
 and p.amount_type = l.amount_type
where l.amount is null
   or p.amount is null
   or abs(l.amount - p.amount) > 0.5
   or l.n_source_rows <> p.n_source_rows
```

Create `GovBudget/dbt/tests/assert_program_decade_grain_unique.sql`:

```sql
-- fct_program_decade_series grain (families piece 1, spec §4.5). Two legs:
--
--   * duplicate grain: (program_key, account, organization, fy,
--     edition_year, map_basis) is unique. Era lines sharing a code, or two
--     era chains pinned to the same side of a collision, must SUM into one
--     row per map_basis, never publish two.
--   * two rows a page reads share one grain: among the rows pages read
--     (map_basis 'native' and 'era_line_map'), the five columns without
--     map_basis — fct_decade_series' own uniqueness key with pe_bli renamed
--     — are unique. An 'era_history_only' row may share its five columns
--     with an 'era_line_map' row (a history-only chain printing the same
--     code in the same edition as a same_program chain: '10' in PB2018 and
--     '15' in PB2021–PB2023, if review decides them that way). A native row
--     and an era_line_map row may not (measured 2026-10-02: no era code
--     equals an R-1 program element in any edition).
select
    'duplicate grain' as failure,
    program_key,
    account,
    organization,
    fy,
    edition_year,
    map_basis,
    count(*) as n
from {{ ref('fct_program_decade_series') }}
group by program_key, account, organization, fy, edition_year, map_basis
having count(*) > 1

union all

select
    'two rows a page reads share one grain',
    program_key,
    account,
    organization,
    fy,
    edition_year,
    string_agg(map_basis, ',' order by map_basis),
    count(*)
from {{ ref('fct_program_decade_series') }}
where map_basis in ('native', 'era_line_map')
group by program_key, account, organization, fy, edition_year
having count(*) > 1
```

- [ ] **Step 7: Run the tests to see them pass**

Run: `uv run --project . pytest tests/test_program_decade_series_sql.py tests/test_p1_era_line_map_sql.py -q`

Expected: `61 passed`.

- [ ] **Step 8: Document the model and run the fixture-lake build**

Append to `GovBudget/dbt/models/marts/schema.yml`, after the last line of the `p1_era_line_map`
entry Task 13 appended (its `source_cells` column):

```yaml
  - name: fct_program_decade_series
    description: "Families piece 1 (spec §4.5): fct_decade_series at PROGRAM grain — the same CTEs (collision anchors and candidate patterns copied verbatim, the slug pick copied with map_basis added to its partition; tests/test_program_decade_series_sql.py guards the copies) plus one step: a PB2017–PB2023 P-1 era row whose p1_era_line_map decision is same_program or history_only is carried to its bare printed code (program_key), with the map's pinned program_account / program_org on the 13 PB2026 collision codes. Era lines sharing a code and a map_basis in an edition sum exactly as modern lines sharing a code do; a same_program and a history_only chain of one code and edition stay two rows. Excluded and undecided era rows produce no grain. Grain: (program_key, account, organization, fy, edition_year, map_basis), and (program_key, account, organization, fy, edition_year) is unique among the native and era_line_map rows pages read — assert_program_decade_grain_unique.sql. Every map_basis='native' row equals its fct_decade_series row in every edition (assert_program_decade_native_equals_line.sql); era grains conserve the mapped fct_decade_series era grains per edition and slug (assert_program_decade_conservation.sql). fct_decade_series itself is unchanged and keeps feeding F-15's builder, verify-phase5e and fct_book_diff."
    columns:
      - name: program_key
        data_tests: [not_null]
        description: "The bare printed budget line code (P-1) or program element (R-1). For native rows it is fct_decade_series.pe_bli; for era rows it is p1_era_line_map.program_key. Never an era key, never suffixed."
      - name: fy
        data_tests: [not_null]
        description: "Fiscal year the amount describes (edition_year - 2/1/0 for actuals/enacted/request)."
      - name: edition_year
        data_tests: [not_null]
        description: "PB edition that reports this amount. Part of the grain — editions are never merged."
      - name: amount_type_kind
        data_tests:
          - not_null
          - accepted_values:
              values: ['actuals', 'enacted', 'request']
      - name: amount
        data_tests: [not_null]
        description: "USD thousands: the sum of the grain's detail rows under amount_type (for an era grain, the sum of the era keys in source_keys)."
      - name: amount_thousands
        data_tests: [not_null]
        description: "Alias of amount."
      - name: scenario
        data_tests: [not_null]
      - name: amount_type
        data_tests: [not_null]
        description: "The picked source workbook column slug, as in fct_decade_series."
      - name: account
        description: "As fct_decade_series.account: non-NULL only for the 10 PB2026 account-collision codes. For an era grain on one of them it is the map's pinned program_account, never the era row's own account."
      - name: organization
        description: "As fct_decade_series.organization: non-NULL only for '20', '30', '500'. For an era grain it is the map's pinned program_org."
      - name: n_source_rows
        data_tests: [not_null]
        description: "Number of budget_lines rows summed (for an era grain, the number of era keys: every era key is one row per slug)."
      - name: source_fact_id
        description: "fact_id_workbook of the single source row when n_source_rows = 1 — for an era grain, hashed from that row's own era key, account and organization, so it is the fact ID the era row already has; NULL for multi-row grains (the exporter mints a decade_era_map sum)."
      - name: map_basis
        description: "Part of the grain. native (no era row; equals fct_decade_series), era_line_map (same_program era keys only: what the code's page reads), era_history_only (history_only era keys only: data, no page). Era rows of different bases never sum together: a history_only chain printing the same code in the same edition as a same_program chain is its own era_history_only row, and the era_line_map row sums only the same_program keys."
        data_tests:
          - not_null
          - accepted_values:
              values: ['native', 'era_line_map', 'era_history_only']
      - name: source_keys
        description: "The era keys summed into an era grain, sorted, comma-separated (e.g. '3010F-AF-L25,3010F-AF-L79'); NULL for native grains."
```

Run: `uv run --project . pytest tests/test_dbt_build.py -q`

Expected: `7 passed` (the fixture lake has no era rows, so every program row is native and the
three tests pass).

- [ ] **Step 9: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/tests/test_program_decade_series_sql.py GovBudget/dbt/models/marts/fct_program_decade_series.sql GovBudget/dbt/tests/assert_program_decade_native_equals_line.sql GovBudget/dbt/tests/assert_program_decade_conservation.sql GovBudget/dbt/tests/assert_program_decade_grain_unique.sql GovBudget/dbt/models/marts/schema.yml && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(decade): fct_program_decade_series — decided era P-1 lines join their printed code's series; native rows equal fct_decade_series (families piece 1, spec §4.5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 10: Build the program table in the live warehouse (the sanctioned write, G4-3)**

Make sure no other session holds the DuckDB file. The hourly SAM launchd job writes
`data/parquet/sam` at :17, so the build starts only outside minutes :12–:22. From `GovBudget/` in
the worktree:

```bash
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: minute $MIN is in the SAM window (:12-:22); rerun after :22"; else \
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data \
GOVBUDGET_DUCKDB=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/duckdb/govbudget.duckdb \
uv run --project . dbt build --project-dir dbt --profiles-dir dbt --select fct_program_decade_series; fi
```

If it prints `WAIT: …`, nothing ran: run the same command again after :22.

Expected:
```
OK created sql table model main.fct_program_decade_series
PASS accepted_values_fct_program_decade_series_amount_type_kind__actuals__enacted__request
PASS accepted_values_fct_program_decade_series_map_basis__native__era_line_map__era_history_only
PASS not_null_fct_program_decade_series_… (10 tests)
PASS assert_program_decade_conservation
PASS assert_program_decade_grain_unique
PASS assert_program_decade_native_equals_line
Done. PASS=16 WARN=0 ERROR=0
```
(The model takes about 2 s; on the scratch copy of the live lake it built in 1.6-1.9 s.)

- [ ] **Step 11: Check the live program table (read-only)**

```bash
uv run --project . python -c "
import duckdb
con = duckdb.connect('/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/duckdb/govbudget.duckdb', read_only=True)
q = lambda s: print(con.execute(s).fetchall())
q(\"select edition_year, count(*) filter (where map_basis = 'native') from fct_program_decade_series group by 1 order by 1\")
q(\"select count(*) filter (where map_basis <> 'native'), count(*) filter (where map_basis <> 'native') % 3, count(*) filter (where map_basis = 'native') from fct_program_decade_series\")
q(\"select amount_type_kind, fy, amount, n_source_rows, source_fact_id, map_basis, source_keys from fct_program_decade_series where program_key = 'F01500' and edition_year = 2019 order by fy\")
q(\"select amount_type_kind, source_fact_id from fct_program_decade_series where program_key = 'F01500' and edition_year = 2017 order by fy\")
q(\"select count(*) from fct_program_decade_series where map_basis <> 'native' and ((program_key in ('0145','1350','2101','2210','2292','3010','3050','3215','3302','4217') and account is null) or (program_key in ('20','30','500') and organization is null))\")
q(\"with k as (select p.edition_year, p.map_basis, u.k from fct_program_decade_series p, unnest(string_split(p.source_keys, ',')) as u(k) where p.map_basis <> 'native') select count(*), count(*) filter (where (k.map_basis = 'era_line_map' and m.decision <> 'same_program') or (k.map_basis = 'era_history_only' and m.decision <> 'history_only') or m.decision is null) from k left join p1_era_line_map m on m.era_key = k.k and m.edition = k.edition_year\")
q(\"select count(*) filter (where decision in ('same_program', 'history_only')) * 3 from p1_era_line_map\")
"
grep -rn "fct_program_decade_series" src/ | wc -l
```

Expected:
```
[(2017, 2754), (2018, 3102), (2019, 3171), (2020, 3156), (2021, 3354), (2022, 3270), (2023, 3201), (2024, 5874), (2025, 5294), (2026, 5222)]
[(<era grains>, 0, 38398)]
[('actuals', 2017, 145406.0, 2, None, 'era_line_map', '3010F-AF-L25,3010F-AF-L79'), ('enacted', 2018, 437193.0, 2, None, 'era_line_map', '3010F-AF-L25,3010F-AF-L79'), ('request', 2019, 550654.0, 2, None, 'era_line_map', '3010F-AF-L25,3010F-AF-L79')]
[('actuals', '3bd9c921b2397209'), ('enacted', 'd741e73aad8c9cf6'), ('request', '2ae658b54a7b963d')]
[(0,)]
[(<k>, 0)]
[(<k>,)]
       0
```
The two `<k>` are the same number: every carried era key (decision `same_program` or
`history_only`) appears once per kind in some era grain's `source_keys`, and the `0` says no
`era_line_map` row holds a key not decided `same_program` and no `era_history_only` row holds a
key not decided `history_only` — the G4-4 split, checked on the live table (the scratch copy gave
`[(20646, 0)]` and `[(20646,)]`).
`<era grains>` depends on the ratified decisions; it is a multiple of 3 and at most 20,781
(6,927 keys × 3 kinds: every carried key adds at most one row per kind). On a scratch copy of the
lake with a fully decided simulated seed (one organization per edition `same_program` on `10`/`15`)
the model gave 16,461 `era_line_map` + 3,198 `era_history_only` = 19,659, with `15` PB2021 split
into an `era_line_map` row of DISA's key alone (request 3,091) and an `era_history_only` row of
TJS Cyber's (1,247). The F-15 values are PB2019's lines 25
(BA 05) and 79 (BA 07) summed — 145,406 + 0, 417,193 + 20,000, 548,109 + 2,545 — and PB2017's
single line 21 keeps the fact IDs `fct_decade_series` already gives `3010F-AF-L21`. The last `0`:
nothing in `src/` reads the new table yet (Task 17 switches the exporter), so the export is
unchanged by construction; Task 21's A/B diff is the export proof. No commit: this step changes
only the shared warehouse.
