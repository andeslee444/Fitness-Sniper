<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 13: dbt `p1_era_line_map` and its tests

**Spec:** §4.4 (the map model); §4.3 (seed grain, no overlap, organization rule); §5.4 (successor
check); §7 rows "Code spanning organizations" (two legs: one decision covering several
organizations, and two organizations' `same_program` keys summing into one page on a code that
is not a PB2026 collision code), "Account or organization move", "An era key with no
decision" (warn severity while S2 is open), "Keys or titles changed after review", "P-1R rows";
V3 map legs (`assert_p1_era_map_{grain_unique,complete,one_code,decisions_no_overlap,org_split,
collision_pinned,successor_resolves,p1r_crosscheck}`; `no_undecided` ships here as
`warn_p1_era_map_undecided`, which Task 15 replaces); S2 "p1_era_line_map and its dbt tests".

**Files:**
- Create: `GovBudget/tests/dbt_render.py`
- Create: `GovBudget/tests/test_p1_era_line_map_sql.py`
- Create: `GovBudget/dbt/models/marts/p1_era_line_map.sql`
- Create: `GovBudget/dbt/tests/assert_p1_era_map_grain_unique.sql`, `assert_p1_era_map_complete.sql`,
  `assert_p1_era_map_one_code.sql`, `assert_p1_era_map_decisions_no_overlap.sql`,
  `assert_p1_era_map_org_split.sql`, `assert_p1_era_map_collision_pinned.sql`,
  `assert_p1_era_map_successor_resolves.sql`, `assert_p1_era_map_p1r_crosscheck.sql`,
  `warn_p1_era_map_undecided.sql`
- Modify: `GovBudget/dbt/models/marts/schema.yml` (append after line 416, the last line of the
  `fct_book_diff` entry)
- Modify: `GovBudget/tests/test_dbt_build.py` (new helper after `write_parquet`, lines 30-32; one
  call after the last two lines of `make_lake`'s `budget_lines.parquet` COPY — lines 125-126 at
  10fb4585, 129-130 once Task 7's Step 5 has added its four lines above them, 156-157 once Step
  10's helper is in)

**Interfaces:** Consumes: `stg_budget_lines.line_item_code` and the lake parquet's
`line_item_code` (Task 7; populated on every era P-1 row by Tasks 8/9 and exported to
`data/parquet/jbooks/budget_lines.parquet`); seed `dbt/seeds/p1_era_code_decisions.csv` with
header `era_map.SEED_COLUMNS` and all-varchar `+column_types` in `dbt/dbt_project.yml`
(Tasks 11/12); `govbudget.jbooks.era_map.SEED_COLUMNS`, `keys_sha256` (Task 10, rendering per
G4-1); sources `lake.jbook_budget_lines` (`source_cells`), `lake.jbook_documents` (`id`,
`sha256`, `rel_path`). Produces: table `p1_era_line_map` (`edition, account, organization,
budget_activity, era_key, line_item_code, filed_title, program_key, program_account,
program_org, decision, decision_id, ruling, keys_sha_ok, successor_code,
source_document_sha256, source_cells`); the nine dbt tests above; `tests/dbt_render.py`
`render_dbt_sql(rel_path: str, sources: dict[str, str] | None = None) -> str`;
`tests/test_dbt_build.py` `ensure_lake_columns(path: Path, columns: tuple[str, ...]) -> None`.

- [ ] **Step 1: Check the inputs this task stands on (read-only)**

Run from `GovBudget/` in the worktree:

```bash
head -1 dbt/seeds/p1_era_code_decisions.csv
grep -n "p1_era_code_decisions" -A2 dbt/dbt_project.yml
grep -n "line_item_code" dbt/models/staging/stg_budget_lines.sql
uv run --project . python -c "from govbudget.jbooks.era_map import SEED_COLUMNS, keys_sha256; print(len(SEED_COLUMNS), keys_sha256([(2019, '3010F-AF-L1', None, None)])[:12])"
uv run --project . python -c "
import duckdb
print(duckdb.connect().execute('''
  select count(distinct (fiscal_year, pe_bli)), count(*) filter (where line_item_code is null)
  from read_parquet('/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/jbooks/budget_lines.parquet')
  where exhibit = 'P-1' and cast(fiscal_year as integer) between 2017 and 2023
    and regexp_matches(pe_bli, '^[0-9]{4}[A-Z]-[A-Z]+-L')''').fetchall())"
```

Expected:
```
decision_id,line_item_code,account,organization,first_edition,last_edition,decision,program_account,program_org,successor_code,successor_account,successor_evidence,n_keys,keys_sha256,titles_seen,modern_title,proposed_rule,evidence,decided_on,decided_by,ruling,note
<n>:    p1_era_code_decisions:
<n+1>-      +column_types:
<n+2>-        decision_id: varchar
<m>:    line_item_code          (one line; a trailing comma depends on where Task 7 put it)
22 1ab1420c3e44
[(6927, 0)]
```
(`1ab1420c3e44` is the start of `sha256("2019|3010F-AF-L1||")`, the G4-1 rendering of that one
key.) Stop if any line differs: a missing seed or `column_types` block means Tasks 11/12 are not done
(an untyped seed turns code `0145` into `145`); a Binder Error or a non-zero second number in the
last line means Tasks 8/9 have not exported `line_item_code` to the lake.

- [ ] **Step 2: Add the dbt-SQL render helper for unit tests**

Create `GovBudget/tests/dbt_render.py`:

```python
"""Render a committed dbt model or singular test to plain DuckDB SQL.

Unit tests run the rendered SQL against a throwaway in-memory DuckDB (the
pattern tests/test_dbt_lobbyists_tiebreak.py uses for one model, made
reusable): `{{ config(...) }}` is dropped, `{{ ref('x') }}` becomes the
relation `x`, and `{{ source('a', 'b') }}` becomes `a__b` (or the name the
caller maps it to). Anything else left in braces fails loudly instead of
reaching DuckDB.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_CONFIG = re.compile(r"\{\{\s*config\([^}]*\)\s*\}\}")
_REF = re.compile(r"\{\{\s*ref\('([a-z0-9_]+)'\)\s*\}\}")
_SOURCE = re.compile(r"\{\{\s*source\('([a-z0-9_]+)',\s*'([a-z0-9_]+)'\)\s*\}\}")


def render_dbt_sql(rel_path: str, sources: dict[str, str] | None = None) -> str:
    """SQL of ROOT/rel_path with its dbt Jinja replaced by plain relation names."""
    sources = sources or {}
    sql = (ROOT / rel_path).read_text()
    sql = _CONFIG.sub("", sql)
    sql = _REF.sub(lambda m: m.group(1), sql)
    sql = _SOURCE.sub(
        lambda m: sources.get(f"{m.group(1)}.{m.group(2)}", f"{m.group(1)}__{m.group(2)}"),
        sql,
    )
    assert "{{" not in sql and "{%" not in sql, f"unrendered Jinja left in {rel_path}"
    return sql
```

- [ ] **Step 3: Write the failing tests**

Create `GovBudget/tests/test_p1_era_line_map_sql.py`:

```python
"""p1_era_line_map and its dbt tests, run on a hand-built lake (families
piece 1, spec §4.4, V3).

Each test renders the COMMITTED model / singular-test SQL (tests/dbt_render.py)
and runs it on a throwaway in-memory DuckDB holding the relations it reads:
stg_budget_lines (with migration 021's line_item_code), the lake's
budget_lines source (for source_cells), jbook_documents, and the seed
p1_era_code_decisions. Every singular test is shown to pass on the clean
fixture AND to fail on the defect it exists for.

The fixture lake (PB2019 + PB2020 era P-1, one PB2019 R-1 row, PB2024/PB2026
P-1 rows for the collision anchors and the JLTV successor):

  era key            ed    BA  code        title                 seed decision
  3010F-AF-L25       2019  05  F01500      F-15                  F01500|3010F||2019-2020 same_program
  3010F-AF-L79       2019  07  F01500      F-15                  (same row: an AP-style pair, two BAs)
  3010F-AF-L25       2020  05  F01500      F-15                  (same row)
  0300D-DSS-L21      2019  01  20          Major Equipment, DSS  20|0300D|DSS|2019-2019 same_program -> DCSA
  0300D-DTRA-L23     2019  01  20          Major Equipment, DTRA 20|0300D|DTRA|2019-2019 same_program -> DTRA
  2035A-ARMY-L5      2019  03  5600D15603  JLTV                  none -> undecided
"""
import duckdb
import pytest
from dbt_render import render_dbt_sql

from govbudget.jbooks.era_map import SEED_COLUMNS, keys_sha256

MODEL = "dbt/models/marts/p1_era_line_map.sql"
TESTS = "dbt/tests/{}.sql"

SHA_2019 = "a" * 64
SHA_2020 = "b" * 64

# (exhibit, fiscal_year, account, organization, ba, pe_bli, title, amount_type,
#  amount, source_document_id, line_item_code, source_cells)
LAKE = [
    ("P-1", 2019, "3010F", "AF", "05", "3010F-AF-L25", "F-15", "fy_2019_total", 100.0, "271", "F01500", "AO40"),
    ("P-1", 2019, "3010F", "AF", "05", "3010F-AF-L25", "F-15", "fy_2017_base_oco", 90.0, "271", "F01500", "O40"),
    ("P-1", 2019, "3010F", "AF", "07", "3010F-AF-L79", "F-15", "fy_2019_total", 50.0, "271", "F01500", "AO98,AO99"),
    ("P-1", 2020, "3010F", "AF", "05", "3010F-AF-L25", "F-15", "fy_2020_total_base_oco", 120.0, "282", "F01500", "AE41"),
    ("P-1", 2019, "0300D", "DSS", "01", "0300D-DSS-L21", "Major Equipment, DSS", "fy_2019_total", 7.0, "271", "20", "AO700"),
    ("P-1", 2019, "0300D", "DTRA", "01", "0300D-DTRA-L23", "Major Equipment, DTRA", "fy_2019_total", 5.0, "271", "20", "AO702"),
    ("P-1", 2019, "2035A", "ARMY", "03", "2035A-ARMY-L5", "JLTV", "fy_2019_total", 900.0, "271", "5600D15603", "AO300"),
    ("P-1R", 2019, "3010F", "AF", "05", "F01500", "F-15", "fy_2019_total", 10.0, "272", "F01500", "AO10"),
    ("R-1", 2019, "3600F", "AF", "07", "0207134F", "F-15E Squadrons", "fy_2019_total", 70.0, "270", None, "P9"),
    ("P-1", 2026, "0300D", "DCSA", "01", "20", "Major Equipment, DCSA", "fy_2026_total", 3.0, "1", "20", "Q5"),
    ("P-1", 2026, "0300D", "DTRA", "01", "20", "Major Equipment, DTRA", "fy_2026_total", 4.0, "1", "20", "Q6"),
    ("P-1", 2024, "2035A", "A", "01", "5731D15610", "Joint Light Tactical Vehicle", "fy_2024_request", 800.0, "76", "5731D15610", "S9"),
]


def _key(edition, era_key, ba, title):
    return (edition, era_key, ba, title)


F15_KEYS = [
    _key(2019, "3010F-AF-L25", "05", "F-15"),
    _key(2019, "3010F-AF-L79", "07", "F-15"),
    _key(2020, "3010F-AF-L25", "05", "F-15"),
]


def _seed_row(**values):
    row = {c: None for c in SEED_COLUMNS}
    row.update(decided_on="2026-10-02", decided_by="owner")
    row.update(values)
    return row


def _seed():
    return [
        _seed_row(decision_id="F01500|3010F||2019-2020", line_item_code="F01500", account="3010F",
                  first_edition="2019", last_edition="2020", decision="same_program",
                  n_keys="3", keys_sha256=keys_sha256(F15_KEYS), ruling="R-DEC-ERA-SAME"),
        _seed_row(decision_id="20|0300D|DSS|2019-2019", line_item_code="20", account="0300D",
                  organization="DSS", first_edition="2019", last_edition="2019",
                  decision="same_program", program_org="DCSA", n_keys="1",
                  keys_sha256=keys_sha256([_key(2019, "0300D-DSS-L21", "01", "Major Equipment, DSS")]),
                  ruling="R-DEC-ERA-B1"),
        _seed_row(decision_id="20|0300D|DTRA|2019-2019", line_item_code="20", account="0300D",
                  organization="DTRA", first_edition="2019", last_edition="2019",
                  decision="same_program", program_org="DTRA", n_keys="1",
                  keys_sha256=keys_sha256([_key(2019, "0300D-DTRA-L23", "01", "Major Equipment, DTRA")]),
                  ruling="R-DEC-ERA-SAME"),
    ]


DOCS = [
    ("271", SHA_2019, "fy2019/dod/p1_display.xlsx", "2019"),
    ("282", SHA_2020, "fy2020/dod/p1_display.xlsx", "2020"),
    ("272", "c" * 64, "fy2019/dod/p1r_display.xlsx", "2019"),
    ("270", "d" * 64, "fy2019/dod/r1_display.xlsx", "2019"),
    ("1", "e" * 64, "fy2026/dod/p1_display.xlsx", "2026"),
    ("76", "f" * 64, "fy2024/dod/p1_display.xlsx", "2024"),
    ("152", "9" * 64, "fy2025/dod/p1_display.xlsx", "2025"),
]


def _lake(lake=None, seed=None, docs=None) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(
        "create table stg_budget_lines (exhibit varchar, fiscal_year integer,"
        " account varchar, account_title varchar, organization varchar,"
        " budget_activity varchar, budget_activity_title varchar, pe_bli varchar,"
        " title varchar, amount_type varchar, amount_thousands double,"
        " source_document_id varchar, line_item_code varchar)"
    )
    con.execute(
        "create table lake__jbook_budget_lines (exhibit varchar, fiscal_year varchar,"
        " pe_bli varchar, amount_type varchar, source_cells varchar)"
    )
    for (ex, fy, acct, org, ba, pe, title, at, amt, doc, code, cells) in (LAKE if lake is None else lake):
        con.execute(
            "insert into stg_budget_lines values (?, ?, ?, null, ?, ?, null, ?, ?, ?, ?, ?, ?)",
            [ex, fy, acct, org, ba, pe, title, at, amt, doc, code],
        )
        con.execute(
            "insert into lake__jbook_budget_lines values (?, ?, ?, ?, ?)",
            [ex, str(fy), pe, at, cells],
        )
    con.execute(
        "create table lake__jbook_documents (id varchar, sha256 varchar, rel_path varchar,"
        " fiscal_year varchar)"
    )
    con.executemany("insert into lake__jbook_documents values (?, ?, ?, ?)", DOCS if docs is None else docs)
    con.execute(
        "create table p1_era_code_decisions ("
        + ", ".join(f"{c} varchar" for c in SEED_COLUMNS) + ")"
    )
    for row in (_seed() if seed is None else seed):
        con.execute(
            f"insert into p1_era_code_decisions values ({', '.join('?' * len(SEED_COLUMNS))})",
            [row[c] for c in SEED_COLUMNS],
        )
    con.execute("create table p1_era_line_map as " + render_dbt_sql(MODEL))
    return con


def _map(con) -> dict[tuple, dict]:
    cur = con.execute("select * from p1_era_line_map")
    cols = [d[0] for d in cur.description]
    return {(r[0], r[4]): dict(zip(cols, r)) for r in cur.fetchall()}


def _failures(con, test_name: str) -> list[tuple]:
    return con.execute(render_dbt_sql(TESTS.format(test_name))).fetchall()


def test_one_row_per_era_key_with_the_spec_columns():
    con = _lake()
    cols = [d[0] for d in con.execute("select * from p1_era_line_map limit 0").description]
    assert cols == [
        "edition", "account", "organization", "budget_activity", "era_key",
        "line_item_code", "filed_title", "program_key", "program_account", "program_org",
        "decision", "decision_id", "ruling", "keys_sha_ok", "successor_code",
        "source_document_sha256", "source_cells",
    ]
    assert sorted(_map(con)) == [
        (2019, "0300D-DSS-L21"), (2019, "0300D-DTRA-L23"), (2019, "2035A-ARMY-L5"),
        (2019, "3010F-AF-L25"), (2019, "3010F-AF-L79"), (2020, "3010F-AF-L25"),
    ]


def test_a_decision_binds_its_code_account_and_edition_range():
    m = _map(_lake())
    l25 = m[(2019, "3010F-AF-L25")]
    assert (l25["line_item_code"], l25["filed_title"], l25["program_key"]) == ("F01500", "F-15", "F01500")
    assert (l25["decision"], l25["decision_id"], l25["ruling"]) == (
        "same_program", "F01500|3010F||2019-2020", "R-DEC-ERA-SAME")
    assert l25["keys_sha_ok"] is True
    assert (l25["program_account"], l25["program_org"]) == (None, None)
    # a two-budget-activity pair and the next edition bind the same decision
    assert m[(2019, "3010F-AF-L79")]["decision_id"] == "F01500|3010F||2019-2020"
    assert m[(2020, "3010F-AF-L25")]["decision_id"] == "F01500|3010F||2019-2020"


def test_provenance_is_the_workbook_sha_and_the_column_i_cells():
    m = _map(_lake())
    l25 = m[(2019, "3010F-AF-L25")]
    assert l25["source_document_sha256"] == SHA_2019
    # two amount cells on row 40 -> one code cell
    assert l25["source_cells"] == "I40"
    # a key summed from two workbook rows lists both, in row order
    assert m[(2019, "3010F-AF-L79")]["source_cells"] == "I98,I99"
    assert m[(2020, "3010F-AF-L25")]["source_document_sha256"] == SHA_2020


def test_organization_narrows_a_decision_and_pins_ride_along():
    m = _map(_lake())
    dss, dtra = m[(2019, "0300D-DSS-L21")], m[(2019, "0300D-DTRA-L23")]
    assert (dss["decision_id"], dss["program_key"], dss["program_org"]) == (
        "20|0300D|DSS|2019-2019", "20", "DCSA")
    assert (dtra["decision_id"], dtra["program_org"]) == ("20|0300D|DTRA|2019-2019", "DTRA")


def test_a_key_no_decision_covers_is_undecided_and_carries_nothing():
    jltv = _map(_lake())[(2019, "2035A-ARMY-L5")]
    assert (jltv["decision"], jltv["decision_id"], jltv["program_key"], jltv["keys_sha_ok"]) == (
        "undecided", None, None, None)


def test_an_edition_outside_the_range_is_not_covered():
    seed = _seed()
    seed[0].update(decision_id="F01500|3010F||2019-2019", last_edition="2019", n_keys="2",
                   keys_sha256=keys_sha256(F15_KEYS[:2]))
    m = _map(_lake(seed=seed))
    assert m[(2019, "3010F-AF-L25")]["keys_sha_ok"] is True
    assert m[(2020, "3010F-AF-L25")]["decision"] == "undecided"


def test_exclusions_carry_no_program_key():
    seed = _seed()
    seed[0].update(decision="exclude_reused_code")
    assert _map(_lake(seed=seed))[(2019, "3010F-AF-L25")]["program_key"] is None


@pytest.mark.parametrize("lines", [
    # 'L1' sorts AFTER 'L10' as text ('|' > '0'): the hash sorts LINES, not tuples
    [(2019, "3010F-AF-L1", "05", "a"), (2019, "3010F-AF-L10", "05", "b")],
    # NULL budget activity and NULL title render as empty strings
    [(2019, "3010F-AF-L2", None, None), (2019, "3010F-AF-L3", "05", "F-15")],
    # non-ASCII, a pipe inside a title, mixed case
    [(2019, "3010F-AF-L4", "05", "Café | Équipement"), (2019, "3010F-AF-L5", "05", "a"),
     (2019, "3010F-AF-L6", "05", "B")],
])
def test_keys_sha_sql_agrees_with_era_map_keys_sha256(lines):
    lake = [("P-1", ed, "3010F", "AF", ba, key, title, "fy_2019_total", 1.0, "271", "CODE1", "AO7")
            for ed, key, ba, title in lines]
    seed = [_seed_row(decision_id="CODE1|3010F||2019-2019", line_item_code="CODE1", account="3010F",
                      first_edition="2019", last_edition="2019", decision="history_only",
                      n_keys=str(len(lines)), keys_sha256=keys_sha256(lines), ruling="R-DEC-ERA-HISTORY")]
    m = _map(_lake(lake=lake, seed=seed))
    assert {row["keys_sha_ok"] for row in m.values()} == {True}


def test_keys_sha_ok_turns_false_when_a_reviewed_title_changes():
    lake = [row if row[5] != "3010F-AF-L79" else row[:6] + ("F-15 (retitled)",) + row[7:] for row in LAKE]
    m = _map(_lake(lake=lake))
    assert {m[k]["keys_sha_ok"] for k in [(2019, "3010F-AF-L25"), (2019, "3010F-AF-L79"),
                                          (2020, "3010F-AF-L25")]} == {False}
    assert m[(2019, "0300D-DSS-L21")]["keys_sha_ok"] is True


# --- the singular tests: clean on the fixture -------------------------------

ALL_TESTS = [
    "assert_p1_era_map_grain_unique",
    "assert_p1_era_map_complete",
    "assert_p1_era_map_one_code",
    "assert_p1_era_map_decisions_no_overlap",
    "assert_p1_era_map_org_split",
    "assert_p1_era_map_collision_pinned",
    "assert_p1_era_map_successor_resolves",
    "assert_p1_era_map_p1r_crosscheck",
]


@pytest.mark.parametrize("test_name", ALL_TESTS)
def test_singular_test_passes_on_the_clean_fixture(test_name):
    assert _failures(_lake(), test_name) == []


def test_warn_test_lists_undecided_and_stale_keys():
    con = _lake()
    rows = _failures(con, "warn_p1_era_map_undecided")
    assert [(r[0], r[1], r[6]) for r in rows] == [(2019, "2035A-ARMY-L5", "undecided")]
    con.execute("update p1_era_line_map set keys_sha_ok = false where era_key = '0300D-DSS-L21'")
    assert len(_failures(con, "warn_p1_era_map_undecided")) == 2


# --- the singular tests: each fails on its defect ---------------------------

def test_grain_unique_fails_on_a_duplicate_key():
    con = _lake()
    con.execute("insert into p1_era_line_map select * from p1_era_line_map where era_key = '3010F-AF-L79'")
    assert _failures(con, "assert_p1_era_map_grain_unique") == [(2019, "3010F-AF-L79", 2)]


def test_complete_fails_on_a_dropped_key():
    con = _lake()
    con.execute("delete from p1_era_line_map where era_key = '2035A-ARMY-L5'")
    assert [r[:2] for r in _failures(con, "assert_p1_era_map_complete")] == [
        ("lake era key missing from the map", "2019/2035A-ARMY-L5")]


def test_complete_pins_the_corpus_counts_once_all_seven_workbooks_are_registered():
    docs = DOCS + [(str(900 + ed), str(ed) * 16, f"fy{ed}/dod/p1_display.xlsx", str(ed))
                   for ed in (2017, 2018, 2021, 2022, 2023)]
    rows = _failures(_lake(docs=docs), "assert_p1_era_map_complete")
    assert ("edition key count differs from the full corpus", "2019", "989", "5") in rows
    assert len([r for r in rows if r[0] == "edition key count differs from the full corpus"]) == 7


def test_complete_fails_when_a_decision_covers_a_different_key_count():
    docs = DOCS + [(str(900 + ed), str(ed) * 16, f"fy{ed}/dod/p1_display.xlsx", str(ed))
                   for ed in (2017, 2018, 2021, 2022, 2023)]
    seed = _seed()
    seed[0]["n_keys"] = "4"
    rows = _failures(_lake(seed=seed, docs=docs), "assert_p1_era_map_complete")
    assert ("decision covers a different number of keys than were reviewed",
            "F01500|3010F||2019-2020", "4", "3") in rows


def test_one_code_fails_when_one_key_prints_two_codes():
    lake = [row if not (row[5] == "3010F-AF-L25" and row[7] == "fy_2017_base_oco")
            else row[:10] + ("F01501",) + row[11:] for row in LAKE]
    rows = _failures(_lake(lake=lake), "assert_p1_era_map_one_code")
    assert [(r[0], r[1], r[2]) for r in rows] == [(2019, "3010F-AF-L25", 2)]


@pytest.mark.parametrize("mutate, failure", [
    (lambda s: s.append(dict(s[0], decision_id="F01500|3010F||2020-2020", first_edition="2020")),
     "ranges overlap"),
    (lambda s: s[0].update(decision="same_programme"), "malformed row"),
    (lambda s: s[0].update(decision_id="F01500|3010F|AF|2019-2020"), "malformed row"),
    (lambda s: s[0].update(first_edition="2016", decision_id="F01500|3010F||2016-2020"), "malformed row"),
    (lambda s: s[0].update(ruling="R-DEC-OTHER"), "malformed row"),
    (lambda s: s[0].update(decided_by="claude"), "malformed row"),
    (lambda s: s[0].update(keys_sha256="ABC"), "malformed row"),
    (lambda s: s.append(dict(s[1])), "duplicate decision_id"),
])
def test_decisions_no_overlap_fails_on_a_bad_seed(mutate, failure):
    seed = _seed()
    mutate(seed)
    con = duckdb.connect()
    con.execute("create table p1_era_code_decisions (" + ", ".join(f"{c} varchar" for c in SEED_COLUMNS) + ")")
    for row in seed:
        con.execute(f"insert into p1_era_code_decisions values ({', '.join('?' * len(SEED_COLUMNS))})",
                    [row[c] for c in SEED_COLUMNS])
    assert failure in {r[0] for r in _failures(con, "assert_p1_era_map_decisions_no_overlap")}


def test_org_split_fails_when_one_decision_spans_two_organizations():
    seed = [row for row in _seed() if row["line_item_code"] != "20"] + [
        _seed_row(decision_id="20|0300D||2019-2019", line_item_code="20", account="0300D",
                  first_edition="2019", last_edition="2019", decision="same_program",
                  program_org="DCSA", n_keys="2", keys_sha256="0" * 64, ruling="R-DEC-ERA-B1")]
    rows = _failures(_lake(seed=seed), "assert_p1_era_map_org_split")
    # '20' is a PB2026 organization-collision code, so only the first leg fires
    assert rows == [("one decision covers several organizations", "20|0300D||2019-2019", 2019, 2,
                     "DSS,DTRA")]


# PB2019 code '15' — no PB2026 collision, so its grain keeps no organization —
# printed by DISA and by TJS (the measured PB2021–PB2023 shape).
FIFTEEN_LAKE = [
    ("P-1", 2019, "0300D", "DISA", "01", "0300D-DISA-L12", "Joint Forces Headquarters - DODIN",
     "fy_2019_total", 40.0, "271", "15", "AO650"),
    ("P-1", 2019, "0300D", "TJS", "01", "0300D-TJS-L50", "Major Equipment - TJS Cyber",
     "fy_2019_total", 9.0, "271", "15", "AO690"),
]


def _fifteen(org, era_key, title, decision, ruling):
    return _seed_row(decision_id=f"15|0300D|{org}|2019-2019", line_item_code="15", account="0300D",
                     organization=org, first_edition="2019", last_edition="2019", decision=decision,
                     n_keys="1", keys_sha256=keys_sha256([_key(2019, era_key, "01", title)]),
                     ruling=ruling)


def test_org_split_fails_when_two_organizations_would_sum_into_one_page():
    disa = _fifteen("DISA", "0300D-DISA-L12", "Joint Forces Headquarters - DODIN",
                    "same_program", "R-DEC-ERA-SAME")
    tjs = _fifteen("TJS", "0300D-TJS-L50", "Major Equipment - TJS Cyber", "same_program", "R-DEC-ERA-B1")
    lake = LAKE + FIFTEEN_LAKE
    rows = _failures(_lake(lake=lake, seed=_seed() + [disa, tjs]), "assert_p1_era_map_org_split")
    assert rows == [("two organizations would sum into one page", "15", 2019, 2, "DISA,TJS")]
    # one organization same_program, the other history_only: clean
    tjs.update(decision="history_only")
    assert _failures(_lake(lake=lake, seed=_seed() + [disa, tjs]), "assert_p1_era_map_org_split") == []


def test_collision_pinned_fails_on_a_missing_or_foreign_pin():
    seed = _seed()
    seed[1]["program_org"] = None                       # DSS chain left unpinned
    seed[2]["program_org"] = "DSS"                      # pinned to an org PB2026 does not report
    seed[0]["program_account"] = "3010F"                # pin on a code that never collides
    rows = _failures(_lake(seed=seed), "assert_p1_era_map_collision_pinned")
    assert sorted((r[0], r[2]) for r in rows) == [
        ("organization-collision code without a usable organization pin", "0300D-DSS-L21"),
        ("organization-collision code without a usable organization pin", "0300D-DTRA-L23"),
        ("pin on a code that is not a PB2026 collision code", "3010F-AF-L25"),
        ("pin on a code that is not a PB2026 collision code", "3010F-AF-L25"),
        ("pin on a code that is not a PB2026 collision code", "3010F-AF-L79"),
    ]


def test_collision_pinned_lets_a_history_only_chain_keep_its_own_organization():
    seed = _seed()
    seed[1].update(decision="history_only", program_org="DSS", ruling="R-DEC-ERA-B1")
    assert _failures(_lake(seed=seed), "assert_p1_era_map_collision_pinned") == []


def test_successor_resolves_fails_on_an_unknown_successor():
    seed = _seed() + [_seed_row(
        decision_id="5600D15603|2035A||2019-2019", line_item_code="5600D15603", account="2035A",
        first_edition="2019", last_edition="2019", decision="same_program", n_keys="1",
        keys_sha256=keys_sha256([_key(2019, "2035A-ARMY-L5", "03", "JLTV")]),
        successor_code="5731D15610", successor_account="2035A",
        successor_evidence="PB2026 OPA BA1 P-40 line 5731D15610, PDF p.100", ruling="R-DEC-ERA-B1")]
    assert _failures(_lake(seed=seed), "assert_p1_era_map_successor_resolves") == []
    seed[-1]["successor_account"] = "2033A"
    rows = _failures(_lake(seed=seed), "assert_p1_era_map_successor_resolves")
    assert rows == [("successor absent from PB2024-PB2026 under its account",
                     "5600D15603|2035A||2019-2019", "5731D15610", "2033A")]
    seed[-1]["successor_evidence"] = None
    assert ("successor recorded without its account or evidence"
            in {r[0] for r in _failures(_lake(seed=seed), "assert_p1_era_map_successor_resolves")})


def test_p1r_crosscheck_fails_on_a_code_the_p1_does_not_print():
    lake = LAKE + [("P-1R", 2019, "2035A", "ARMY", "03", "9999X00001", "Ghost", "fy_2019_total",
                    1.0, "272", "9999X00001", "AO11")]
    rows = _failures(_lake(lake=lake), "assert_p1_era_map_p1r_crosscheck")
    assert [r[:4] for r in rows] == [
        ("P-1R triple absent from the era map and not allow-listed", 2019, "2035A", "9999X00001")]


def test_p1r_crosscheck_allow_list_must_stay_exact_on_the_real_corpus():
    docs = DOCS + [("189", "1" * 64, "fy2017/dod/p1_display.xlsx", "2017"),
                   ("190", "2" * 64, "fy2017/dod/p1r_display.xlsx", "2017")]
    rows = _failures(_lake(docs=docs), "assert_p1_era_map_p1r_crosscheck")
    assert sorted(r[3] for r in rows) == [
        "4000M12800", "8190G01506", "8635G15325", "9221F00001", "9693B01001"]
    assert {r[0] for r in rows} == {"allow-listed triple is no longer an exception"}
```

- [ ] **Step 4: Run the tests to see them fail**

Run: `uv run --project . pytest tests/test_p1_era_line_map_sql.py -q`

Expected: `40 failed`, each with
`FileNotFoundError: [Errno 2] No such file or directory: '…/GovBudget/dbt/models/marts/p1_era_line_map.sql'`
(the `decisions_no_overlap` cases name `…/dbt/tests/assert_p1_era_map_decisions_no_overlap.sql`).

- [ ] **Step 5: Write the model**

Create `GovBudget/dbt/models/marts/p1_era_line_map.sql`:

```sql
-- p1_era_line_map: the reviewed bridge from PB2017–PB2023 P-1 era keys to the
-- budget line code each one prints (families piece 1, spec §4.4).
--
-- Grain: one row per era key — (edition, era_key), which implies the spec
-- key (edition, account, organization, budget_activity, era_key) because the
-- era key '{account}-{org}-L{line}' already carries account and organization
-- and every era key prints exactly one budget activity (spec §3;
-- assert_p1_era_map_one_code.sql re-checks it from staging). 6,927 keys:
-- 969 / 1,029 / 989 / 975 / 1,005 / 993 / 967 for PB2017..PB2023
-- (assert_p1_era_map_complete.sql pins them against the full corpus).
--
-- Identity never changes here: era_key stays the lake/fact identity forever
-- (no pe_bli re-keying). This model only records WHICH printed code the key
-- carries (line_item_code, column I "Line Item" of the era P-1 workbook,
-- captured by the loader since migration 021) and WHAT the owner decided
-- about that code's chain (dbt/seeds/p1_era_code_decisions.csv).
--
-- Seed join. A decision row covers the era keys printing its line_item_code
-- under its account, in editions first_edition..last_edition; its
-- organization narrows the match only when set (it is blank unless the code
-- spans organizations within an edition — '10', '15', '20', '30', '500').
-- On '10' and '15', which are not PB2026 collision codes, at most one
-- organization per edition may be same_program: the program grain keeps no
-- organization there, so two would sum into one page
-- (assert_p1_era_map_org_split.sql).
-- A key no row covers is decision='undecided' and never reaches
-- fct_program_decade_series.
--
-- program_key is the bare printed code, set only for the two decisions that
-- carry points (same_program, history_only); NULL for every exclusion and
-- for undecided keys. program_account/program_org are the seed's pins (the
-- PB2026 account/organization whose page the points join); they are set
-- only for chains on one of the 13 PB2026 collision codes
-- (assert_p1_era_map_collision_pinned.sql).
--
-- keys_sha_ok is the drift guard: the seed stores keys_sha256, the sha256 of
-- the sorted 'edition|era_key|budget_activity|filed_title' lines the owner
-- reviewed (NULL parts rendered as ''), joined by '\n' with no trailing
-- newline — exactly govbudget.jbooks.era_map.keys_sha256. This model
-- recomputes it over the keys the decision row covers TODAY: a key added,
-- dropped, retitled or moved to another budget activity since review makes
-- it false (verify-era-map leg b and `era-map check` fail on it). NULL for
-- undecided keys. tests/test_p1_era_line_map_sql.py proves the SQL and the
-- Python hash agree byte for byte.
--
-- source_document_sha256 is the era P-1 workbook's sha (the
-- data/site/workbooks/<sha>.xlsx file); source_cells lists the column-I
-- cells (the printed code) of every workbook row summed into the key, in
-- row order, comma-separated ('I35,I36' for a two-cost-type key) — derived
-- from the row numbers of the lake's recorded amount cells. verify-era-map
-- leg a re-reads those cells from the workbook.

{{ config(materialized='table') }}

with era_rows as (
    select
        fiscal_year as edition,
        account,
        organization,
        budget_activity,
        pe_bli as era_key,
        line_item_code,
        title,
        source_document_id
    from {{ ref('stg_budget_lines') }}
    where exhibit = 'P-1'
      and fiscal_year between 2017 and 2023
      and regexp_matches(pe_bli, '^[0-9]{4}[A-Z]-[A-Z]+-L')
),

keys as (
    select
        edition,
        account,
        organization,
        budget_activity,
        era_key,
        min(line_item_code) as line_item_code,
        min(title) as filed_title,
        min(source_document_id) as source_document_id
    from era_rows
    group by edition, account, organization, budget_activity, era_key
),

cell_rows as (
    select distinct
        cast(c.fiscal_year as integer) as edition,
        c.pe_bli as era_key,
        cast(regexp_extract(trim(u.cell), '[0-9]+$') as integer) as sheet_row
    from {{ source('lake', 'jbook_budget_lines') }} c,
         unnest(string_split(c.source_cells, ',')) as u(cell)
    where c.exhibit = 'P-1'
      and cast(c.fiscal_year as integer) between 2017 and 2023
      and regexp_matches(c.pe_bli, '^[0-9]{4}[A-Z]-[A-Z]+-L')
      and trim(u.cell) <> ''
),

key_cells as (
    select
        edition,
        era_key,
        string_agg('I' || cast(sheet_row as varchar), ',' order by sheet_row) as source_cells
    from cell_rows
    group by edition, era_key
),

decisions as (
    select
        decision_id,
        line_item_code,
        account,
        nullif(trim(coalesce(organization, '')), '') as organization,
        cast(first_edition as integer) as first_edition,
        cast(last_edition as integer) as last_edition,
        decision,
        nullif(trim(coalesce(program_account, '')), '') as program_account,
        nullif(trim(coalesce(program_org, '')), '') as program_org,
        nullif(trim(coalesce(successor_code, '')), '') as successor_code,
        keys_sha256 as reviewed_keys_sha256,
        ruling
    from {{ ref('p1_era_code_decisions') }}
),

bound as (
    select
        k.*,
        d.decision_id,
        d.decision,
        d.program_account,
        d.program_org,
        d.successor_code,
        d.reviewed_keys_sha256,
        d.ruling
    from keys k
    left join decisions d
      on d.line_item_code = k.line_item_code
     and d.account = k.account
     and (d.organization is null or d.organization = k.organization)
     and k.edition between d.first_edition and d.last_edition
),

chain_sha as (
    select
        decision_id,
        sha256(string_agg(line, chr(10) order by line)) as keys_sha256
    from (
        select
            decision_id,
            cast(edition as varchar) || '|' || era_key || '|'
                || coalesce(budget_activity, '') || '|' || coalesce(filed_title, '') as line
        from bound
        where decision_id is not null
    )
    group by decision_id
)

select
    b.edition,
    b.account,
    b.organization,
    b.budget_activity,
    b.era_key,
    b.line_item_code,
    b.filed_title,
    case when b.decision in ('same_program', 'history_only') then b.line_item_code end as program_key,
    b.program_account,
    b.program_org,
    coalesce(b.decision, 'undecided') as decision,
    b.decision_id,
    b.ruling,
    case when b.decision_id is not null then cs.keys_sha256 = b.reviewed_keys_sha256 end as keys_sha_ok,
    b.successor_code,
    doc.sha256 as source_document_sha256,
    kc.source_cells
from bound b
left join chain_sha cs
  on cs.decision_id = b.decision_id
left join {{ source('lake', 'jbook_documents') }} doc
  on doc.id = b.source_document_id
left join key_cells kc
  on kc.edition = b.edition
 and kc.era_key = b.era_key
```

- [ ] **Step 6: Run the tests — the model tests pass, the singular-test tests still fail**

Run: `uv run --project . pytest tests/test_p1_era_line_map_sql.py -q`

Expected: `29 failed, 11 passed`; every failure is
`FileNotFoundError: … dbt/tests/assert_p1_era_map_<name>.sql` or `… warn_p1_era_map_undecided.sql`.
If `test_keys_sha_sql_agrees_with_era_map_keys_sha256` fails instead, `era_map.keys_sha256` does
not render lines as G4-1 says: stop and reconcile Task 10 with the contract (the SQL above is the
contract's rendering).

- [ ] **Step 7: Write the nine dbt tests**

Create `GovBudget/dbt/tests/assert_p1_era_map_grain_unique.sql`:

```sql
-- p1_era_line_map grain: one row per era key per edition (families piece 1,
-- spec §4.4). (edition, era_key) is stricter than the spec's key (edition,
-- account, organization, budget_activity, era_key): the era key already
-- carries account and organization, so a duplicate here means one era key
-- printed two budget activities, or two decision rows covered one key
-- (overlapping ranges — assert_p1_era_map_decisions_no_overlap.sql names them).
select edition, era_key, count(*) as n
from {{ ref('p1_era_line_map') }}
group by edition, era_key
having count(*) > 1
```

Create `GovBudget/dbt/tests/assert_p1_era_map_complete.sql`:

```sql
-- p1_era_line_map covers every era key and nothing else (families piece 1,
-- spec §4.4, V3 "coverage ≠ 6,927").
--
-- Relational legs (always on): every PB2017–PB2023 P-1 era key in staging is
-- in the map and every map key is in staging; every map row carries its
-- workbook sha and its column-I cells.
--
-- Full-corpus legs (on only when the lake registers all seven era P-1
-- workbooks, fy2017..fy2023/dod/p1_display.xlsx — the real corpus; the
-- tests/test_dbt_build.py fixture lake registers none, so a committed seed
-- written against the real corpus cannot fail the fixture build):
--   * per-edition key counts equal the measured corpus: 969 / 1,029 / 989 /
--     975 / 1,005 / 993 / 967 = 6,927 (measured 2026-10-02 from
--     data/parquet/jbooks/budget_lines.parquet, exhibit P-1, era-key pe_bli);
--   * every seed decision covers exactly the n_keys keys it was reviewed
--     over — a decision that binds no key (a typo, a stale range) or binds a
--     different number of keys fails here.
with registered as (
    select count(distinct rel_path) as n
    from {{ source('lake', 'jbook_documents') }}
    where rel_path in (
        'fy2017/dod/p1_display.xlsx', 'fy2018/dod/p1_display.xlsx',
        'fy2019/dod/p1_display.xlsx', 'fy2020/dod/p1_display.xlsx',
        'fy2021/dod/p1_display.xlsx', 'fy2022/dod/p1_display.xlsx',
        'fy2023/dod/p1_display.xlsx'
    )
),

expected (edition, n_keys) as (
    values (2017, 969), (2018, 1029), (2019, 989), (2020, 975),
           (2021, 1005), (2022, 993), (2023, 967)
),

actual as (
    select edition, count(*) as n_keys
    from {{ ref('p1_era_line_map') }}
    group by edition
),

lake_keys as (
    select distinct fiscal_year as edition, pe_bli as era_key
    from {{ ref('stg_budget_lines') }}
    where exhibit = 'P-1'
      and fiscal_year between 2017 and 2023
      and regexp_matches(pe_bli, '^[0-9]{4}[A-Z]-[A-Z]+-L')
),

map_keys as (
    select edition, era_key, source_document_sha256, source_cells
    from {{ ref('p1_era_line_map') }}
),

seed_bound as (
    select
        s.decision_id,
        try_cast(s.n_keys as integer) as n_keys,
        count(m.era_key) as bound_keys
    from {{ ref('p1_era_code_decisions') }} s
    left join {{ ref('p1_era_line_map') }} m
      on m.decision_id = s.decision_id
    group by s.decision_id, try_cast(s.n_keys as integer)
)

select
    'edition key count differs from the full corpus' as failure,
    cast(e.edition as varchar) as subject,
    cast(e.n_keys as varchar) as expected,
    cast(coalesce(a.n_keys, 0) as varchar) as actual
from expected e
left join actual a
  on a.edition = e.edition
where (select n from registered) = 7
  and coalesce(a.n_keys, 0) <> e.n_keys

union all

select
    'lake era key missing from the map',
    cast(l.edition as varchar) || '/' || l.era_key,
    null,
    null
from lake_keys l
left join map_keys m
  on m.edition = l.edition
 and m.era_key = l.era_key
where m.era_key is null

union all

select
    'map key not in the lake',
    cast(m.edition as varchar) || '/' || m.era_key,
    null,
    null
from map_keys m
left join lake_keys l
  on l.edition = m.edition
 and l.era_key = m.era_key
where l.era_key is null

union all

select
    'map key without its workbook sha or cells',
    cast(m.edition as varchar) || '/' || m.era_key,
    null,
    coalesce(m.source_document_sha256, '<null sha>') || ' ' || coalesce(m.source_cells, '<null cells>')
from map_keys m
where m.source_document_sha256 is null
   or m.source_cells is null

union all

select
    'decision covers a different number of keys than were reviewed',
    b.decision_id,
    cast(b.n_keys as varchar),
    cast(b.bound_keys as varchar)
from seed_bound b
where (select n from registered) = 7
  and b.bound_keys is distinct from b.n_keys
```

Create `GovBudget/dbt/tests/assert_p1_era_map_one_code.sql`:

```sql
-- Every era key prints exactly one budget line code, one title and one budget
-- activity, and cites one workbook (families piece 1, spec §3 and §7; the
-- loader's tripwire, EraKeyConflict, re-checked downstream of Postgres and the
-- lake export). Read from staging, not from the map: the map takes min() of
-- each, which would hide a second value.
select
    fiscal_year as edition,
    pe_bli as era_key,
    count(distinct line_item_code) as codes,
    count(*) filter (where line_item_code is null) as rows_without_code,
    count(distinct coalesce(title, '')) as titles,
    count(distinct coalesce(budget_activity, '')) as budget_activities,
    count(distinct source_document_id) as documents
from {{ ref('stg_budget_lines') }}
where exhibit = 'P-1'
  and fiscal_year between 2017 and 2023
  and regexp_matches(pe_bli, '^[0-9]{4}[A-Z]-[A-Z]+-L')
group by fiscal_year, pe_bli
having count(distinct line_item_code) <> 1
    or count(*) filter (where line_item_code is null) > 0
    or count(distinct coalesce(title, '')) <> 1
    or count(distinct coalesce(budget_activity, '')) <> 1
    or count(distinct source_document_id) <> 1
```

Create `GovBudget/dbt/tests/assert_p1_era_map_decisions_no_overlap.sql`:

```sql
-- dbt/seeds/p1_era_code_decisions.csv integrity (families piece 1, spec §4.3):
-- the reviewed artifact must be well-formed and its ranges must never overlap.
--
--   * malformed row: a missing identity column; first/last edition outside
--     2017..2023 or reversed; a decision outside the five the spec defines;
--     a decision_id that is not '{code}|{account}|{org}|{first}-{last}';
--     decided_by other than 'owner'; decided_on not an ISO date; a ruling
--     that is not R-DEC-ERA-SAME / -EXCLUDE / -HISTORY / -B<n>; keys_sha256
--     not 64 lowercase hex; n_keys not a positive integer.
--   * duplicate decision_id.
--   * ranges overlap: two rows for one (code, account) whose organizations
--     can both match one key (equal, or either blank) and whose edition
--     ranges intersect — one era key would bind two decisions.
with seed as (
    select
        decision_id,
        line_item_code,
        account,
        coalesce(nullif(trim(coalesce(organization, '')), ''), '') as organization,
        cast(first_edition as varchar) as first_edition,
        cast(last_edition as varchar) as last_edition,
        try_cast(first_edition as integer) as first_ed,
        try_cast(last_edition as integer) as last_ed,
        decision,
        decided_by,
        cast(decided_on as varchar) as decided_on,
        ruling,
        keys_sha256,
        try_cast(n_keys as integer) as n_keys
    from {{ ref('p1_era_code_decisions') }}
)

select 'malformed row' as failure, decision_id, cast(null as varchar) as other_decision_id
from seed
where decision_id is null
   or line_item_code is null
   or account is null
   or first_ed is null
   or last_ed is null
   or first_ed < 2017
   or last_ed > 2023
   or first_ed > last_ed
   or decision is null
   or decision not in ('same_program', 'history_only', 'exclude_placeholder',
                       'exclude_route_unsafe', 'exclude_reused_code')
   or decision_id <> line_item_code || '|' || account || '|' || organization
                     || '|' || first_edition || '-' || last_edition
   or coalesce(decided_by, '') <> 'owner'
   or not regexp_matches(coalesce(decided_on, ''), '^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
   or not regexp_matches(coalesce(ruling, ''), '^R-DEC-ERA-(SAME|EXCLUDE|HISTORY|B[0-9]+)$')
   or not regexp_matches(coalesce(keys_sha256, ''), '^[0-9a-f]{64}$')
   or n_keys is null
   or n_keys < 1

union all

select 'duplicate decision_id', decision_id, cast(null as varchar)
from seed
group by decision_id
having count(*) > 1

union all

select 'ranges overlap', a.decision_id, b.decision_id
from seed a
join seed b
  on a.line_item_code = b.line_item_code
 and a.account = b.account
 and (a.organization = b.organization or a.organization = '' or b.organization = '')
 and a.decision_id < b.decision_id
 and a.first_ed <= b.last_ed
 and b.first_ed <= a.last_ed
```

Create `GovBudget/dbt/tests/assert_p1_era_map_org_split.sql`:

```sql
-- A code that spans organizations within one edition is decided per
-- organization (families piece 1, spec §4.3 and §7: today '10', '15', '20',
-- '30', '500'). Two legs:
--
--   * one decision covers several organizations: a decision covers keys of
--     more than one organization in the same edition — a row left
--     `organization` blank for an organization-spanning code.
--   * two organizations would sum into one page: on a code that is NOT a
--     PB2026 collision code, fct_program_decade_series keeps neither account
--     nor organization in the grain, so every same_program key printing the
--     code in an edition sums into the code's ONE page. Keys of two
--     organizations there would put one organization's dollars on the
--     other's page, so at most one organization per (edition, code) may be
--     same_program; the others are history_only or excluded. Today this is
--     '10' (PB2018: TJS beside DPAA) and '15' (PB2021–PB2023: DISA beside
--     TJS Cyber). Collision codes are exempt: their grain splits by the
--     pinned account or organization (assert_p1_era_map_collision_pinned.sql).
--     The two anchors are fct_decade_series.sql's collision_pes /
--     org_collision_pes, re-derived from staging exactly as
--     assert_p1_era_map_collision_pinned.sql does.
with collision_slots as (
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
)

select
    'one decision covers several organizations' as failure,
    decision_id as subject,
    edition,
    count(distinct organization) as organizations,
    string_agg(distinct organization, ',' order by organization) as organizations_seen
from {{ ref('p1_era_line_map') }}
where decision_id is not null
group by decision_id, edition
having count(distinct organization) > 1

union all

select
    'two organizations would sum into one page',
    m.line_item_code,
    m.edition,
    count(distinct m.organization),
    string_agg(distinct m.organization, ',' order by m.organization)
from {{ ref('p1_era_line_map') }} m
left join collision_pes cp
  on cp.pe_bli = m.line_item_code
left join org_collision_pes ocp
  on ocp.pe_bli = m.line_item_code
where m.decision = 'same_program'
  and cp.pe_bli is null
  and ocp.pe_bli is null
group by m.line_item_code, m.edition
having count(distinct m.organization) > 1
```

Create `GovBudget/dbt/tests/assert_p1_era_map_collision_pinned.sql`:

```sql
-- Every carried era key on a PB2026 collision code is pinned to ONE side of
-- the collision (families piece 1, spec §4.3, §4.5 and §7).
--
-- fct_program_decade_series splits a collision code's grain by account (10
-- codes) or organization ('20', '30', '500') exactly like fct_decade_series,
-- and for an era row it takes the seed's program_account / program_org, never
-- the era row's own values. So for every key whose decision carries points:
--   * on an account-collision code, program_account must be set — and, for
--     same_program, be an account PB2026 reports under that code (the page
--     the points join); a history_only pin only has to be set;
--   * on an organization-collision code, the same for program_org;
--   * on any other code, both pins must be blank (they would be ignored).
-- The two anchors below are fct_decade_series.sql's collision_pes /
-- org_collision_pes, re-derived from staging (this test checks the map
-- independently of the mart).
with collision_slots as (
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
pb2026_accounts as (
    select distinct pe_bli, account from collision_slots
),
pb2026_orgs as (
    select distinct pe_bli, organization from org_collision_slots
),
carried as (
    select edition, era_key, line_item_code, decision, program_account, program_org
    from {{ ref('p1_era_line_map') }}
    where decision in ('same_program', 'history_only')
)

select
    'account-collision code without a usable account pin' as failure,
    c.edition, c.era_key, c.line_item_code, c.decision, c.program_account, c.program_org
from carried c
join collision_pes cp
  on cp.pe_bli = c.line_item_code
left join pb2026_accounts a
  on a.pe_bli = c.line_item_code
 and a.account = c.program_account
where c.program_account is null
   or (c.decision = 'same_program' and a.pe_bli is null)

union all

select
    'organization-collision code without a usable organization pin',
    c.edition, c.era_key, c.line_item_code, c.decision, c.program_account, c.program_org
from carried c
join org_collision_pes ocp
  on ocp.pe_bli = c.line_item_code
left join pb2026_orgs o
  on o.pe_bli = c.line_item_code
 and o.organization = c.program_org
where c.program_org is null
   or (c.decision = 'same_program' and o.pe_bli is null)

union all

select
    'pin on a code that is not a PB2026 collision code',
    c.edition, c.era_key, c.line_item_code, c.decision, c.program_account, c.program_org
from carried c
left join collision_pes cp
  on cp.pe_bli = c.line_item_code
left join org_collision_pes ocp
  on ocp.pe_bli = c.line_item_code
where cp.pe_bli is null
  and ocp.pe_bli is null
  and (c.program_account is not null or c.program_org is not null)
```

Create `GovBudget/dbt/tests/assert_p1_era_map_successor_resolves.sql`:

```sql
-- Every stated successor resolves (families piece 1, spec §5.4): a seed row
-- that records successor_code must also record successor_account and
-- successor_evidence, and the successor must be a P-1 budget line code
-- printed in PB2024–PB2026 under that account. The resolution leg runs only
-- when the lake registers the three modern P-1 workbooks
-- (fy2024..fy2026/dod/p1_display.xlsx — the real corpus); the shape leg
-- always runs. Known case: JLTV, 5600D15603 (2035A) -> 5731D15610 (2035A),
-- printed in PB2024, PB2025 and PB2026.
with registered as (
    select count(distinct rel_path) as n
    from {{ source('lake', 'jbook_documents') }}
    where rel_path in (
        'fy2024/dod/p1_display.xlsx', 'fy2025/dod/p1_display.xlsx',
        'fy2026/dod/p1_display.xlsx'
    )
),
modern as (
    select distinct pe_bli, account
    from {{ ref('stg_budget_lines') }}
    where exhibit = 'P-1'
      and fiscal_year between 2024 and 2026
),
successors as (
    select
        decision_id,
        nullif(trim(coalesce(successor_code, '')), '') as successor_code,
        nullif(trim(coalesce(successor_account, '')), '') as successor_account,
        nullif(trim(coalesce(successor_evidence, '')), '') as successor_evidence
    from {{ ref('p1_era_code_decisions') }}
)

select
    'successor recorded without its account or evidence' as failure,
    s.decision_id, s.successor_code, s.successor_account
from successors s
where (s.successor_code is not null
       and (s.successor_account is null or s.successor_evidence is null))
   or (s.successor_code is null
       and (s.successor_account is not null or s.successor_evidence is not null))

union all

select
    'successor absent from PB2024-PB2026 under its account',
    s.decision_id, s.successor_code, s.successor_account
from successors s
left join modern m
  on m.pe_bli = s.successor_code
 and m.account = s.successor_account
where s.successor_code is not null
  and s.successor_account is not null
  and m.pe_bli is null
  and (select n from registered) = 3
```

Create `GovBudget/dbt/tests/assert_p1_era_map_p1r_crosscheck.sql` (the allow-list was measured
read-only on 2026-10-02: the 1,650 distinct era P-1R `(edition, account, code)` triples in
`data/parquet/jbooks/budget_lines.parquet` against the codes printed in column I of the seven
era P-1 workbooks — 1,645 match; the five below are the PB2017 Army codes the PB2017 P-1 does
not print):

```sql
-- P-1R context cross-check (families piece 1, spec §7 "P-1R rows"): every
-- era P-1R (edition, account, printed code) triple must name a code the
-- edition's P-1 prints under that account — i.e. appear in p1_era_line_map —
-- except the five PB2017 Army triples below, whose codes the PB2017 P-1 does
-- not print (measured 2026-10-02: 1,645 of the 1,650 era P-1R triples match).
-- P-1R is never counted (it is the reserve-component subset of P-1); this
-- only proves the map reads the same codes the books print.
--
--   * an exception outside the allow-list fails (always on);
--   * an allow-listed triple that stopped being an exception fails, so the
--     list stays exact (on when the lake registers the PB2017 P-1 and P-1R
--     workbooks — the real corpus);
--   * the era P-1R triple count must stay 1,650 (on when the lake registers
--     all seven era P-1R workbooks).
with docs as (
    select distinct rel_path
    from {{ source('lake', 'jbook_documents') }}
),
allow_list (edition, account, line_item_code, reason) as (
    values
        (2017, '2033A', '8190G01506', 'Precision Sniper Rifle: in the PB2017 P-1R only; the P-1 prints it from PB2020'),
        (2017, '2033A', '8635G15325', 'Handgun: in the PB2017 P-1R only; the P-1 prints it from PB2018'),
        (2017, '2035A', '4000M12800', 'WATER PURIFICATION UNIT REVERSE OSMOSIS ENHAN: in the PB2017 P-1R only; no PB2017-PB2023 P-1 prints it'),
        (2017, '2035A', '9221F00001', 'Unmanned Ground Vehicle: in the PB2017 P-1R only; no PB2017-PB2023 P-1 prints it'),
        (2017, '2035A', '9693B01001', 'DCGS-A (MIP): in the PB2017 P-1R only; no PB2017-PB2023 P-1 prints it')
),
p1r as (
    select distinct fiscal_year as edition, account, pe_bli as line_item_code
    from {{ ref('stg_budget_lines') }}
    where exhibit = 'P-1R'
      and fiscal_year between 2017 and 2023
),
map_codes as (
    select distinct edition, account, line_item_code
    from {{ ref('p1_era_line_map') }}
),
exceptions as (
    select p.edition, p.account, p.line_item_code
    from p1r p
    left join map_codes m
      on m.edition = p.edition
     and m.account = p.account
     and m.line_item_code = p.line_item_code
    where m.line_item_code is null
)

select
    'P-1R triple absent from the era map and not allow-listed' as failure,
    e.edition, e.account, e.line_item_code
from exceptions e
left join allow_list a
  on a.edition = e.edition
 and a.account = e.account
 and a.line_item_code = e.line_item_code
where a.line_item_code is null

union all

select
    'allow-listed triple is no longer an exception',
    a.edition, a.account, a.line_item_code
from allow_list a
left join exceptions e
  on e.edition = a.edition
 and e.account = a.account
 and e.line_item_code = a.line_item_code
where e.line_item_code is null
  and exists (select 1 from docs where rel_path = 'fy2017/dod/p1_display.xlsx')
  and exists (select 1 from docs where rel_path = 'fy2017/dod/p1r_display.xlsx')

union all

select
    'era P-1R triple count differs from the full corpus (1,650): ' || cast(count(*) as varchar),
    cast(null as integer), cast(null as varchar), cast(null as varchar)
from p1r
having count(*) <> 1650
   and (select count(*) from docs where rel_path in (
        'fy2017/dod/p1r_display.xlsx', 'fy2018/dod/p1r_display.xlsx',
        'fy2019/dod/p1r_display.xlsx', 'fy2020/dod/p1r_display.xlsx',
        'fy2021/dod/p1r_display.xlsx', 'fy2022/dod/p1r_display.xlsx',
        'fy2023/dod/p1r_display.xlsx')) = 7
```

Create `GovBudget/dbt/tests/warn_p1_era_map_undecided.sql`:

```sql
/*
  Families piece 1 (spec §7) — WARN severity while the S2 review batches are
  open, by design: the count is the point.

  One row per era key that no owner decision covers yet (decision =
  'undecided'), or whose decision went stale (keys_sha_ok = false: the keys
  or titles it covers changed after review). Neither kind ever reaches
  fct_program_decade_series — an undecided key carries no program_key, and
  a stale one is re-reviewed — but they must never be silent: dbt prints
  "WARN <n> warn_p1_era_map_undecided" and "Got <n> results" in the build
  log. Task 15's closing commit deletes this file and adds
  assert_p1_era_map_no_undecided.sql with the same predicate at error
  severity; verify-era-map leg b is strict from S4.
*/
{{ config(severity='warn') }}

select
    edition,
    era_key,
    line_item_code,
    account,
    organization,
    filed_title,
    decision,
    decision_id,
    keys_sha_ok
from {{ ref('p1_era_line_map') }}
where decision = 'undecided'
   or keys_sha_ok = false
```

- [ ] **Step 8: Run the tests to see them pass**

Run: `uv run --project . pytest tests/test_p1_era_line_map_sql.py -q`

Expected: `40 passed`.

- [ ] **Step 9: Commit the model and its tests**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/tests/dbt_render.py GovBudget/tests/test_p1_era_line_map_sql.py GovBudget/dbt/models/marts/p1_era_line_map.sql GovBudget/dbt/tests/assert_p1_era_map_grain_unique.sql GovBudget/dbt/tests/assert_p1_era_map_complete.sql GovBudget/dbt/tests/assert_p1_era_map_one_code.sql GovBudget/dbt/tests/assert_p1_era_map_decisions_no_overlap.sql GovBudget/dbt/tests/assert_p1_era_map_org_split.sql GovBudget/dbt/tests/assert_p1_era_map_collision_pinned.sql GovBudget/dbt/tests/assert_p1_era_map_successor_resolves.sql GovBudget/dbt/tests/assert_p1_era_map_p1r_crosscheck.sql GovBudget/dbt/tests/warn_p1_era_map_undecided.sql && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(era-map): p1_era_line_map — the reviewed bridge from era P-1 keys to their printed codes, with its dbt tests (families piece 1, spec §4.4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 10: Document the model and keep the fixture-lake build green**

Append to `GovBudget/dbt/models/marts/schema.yml`, after line 416 (the file's last line today):

```yaml
      - name: to_source_fact_id
        description: "Workbook fact_id of the to side when single-source; NULL otherwise."
  - name: p1_era_line_map
    description: "Families piece 1 (spec §4.4): one row per PB2017–PB2023 P-1 era key — 6,927 keys (969 / 1,029 / 989 / 975 / 1,005 / 993 / 967) — carrying the budget line code its workbook rows print (column I, 'Line Item') and the owner's reviewed decision on that code's chain (dbt/seeds/p1_era_code_decisions.csv). Grain: (edition, era_key), which implies the spec key (edition, account, organization, budget_activity, era_key) — assert_p1_era_map_grain_unique.sql. Rows are decisions, not money (the published dataset goes on the uncited ledger). era_key stays the lake and fact identity forever; fct_program_decade_series reads program_key / program_account / program_org from here. A seed row covers the keys printing its line_item_code under its account in editions first_edition..last_edition, narrowed to its organization when one is set (only for codes spanning organizations within an edition: '10', '15', '20', '30', '500'). On '10' and '15', which are not PB2026 collision codes, at most one organization per edition is same_program, since the program grain keeps no organization there (assert_p1_era_map_org_split.sql). A key no decision covers is 'undecided', carries no program_key and never reaches the program table (warn_p1_era_map_undecided.sql while S2 review batches are open)."
    columns:
      - name: edition
        data_tests: [not_null]
        description: "PB edition (2017–2023) whose P-1 display workbook prints the key."
      - name: account
        data_tests: [not_null]
        description: "Appropriation account of the key's workbook rows (e.g. '3010F')."
      - name: organization
        data_tests: [not_null]
        description: "Workbook organization code of the key's rows (era spelling, e.g. 'AF', 'DSS')."
      - name: budget_activity
        description: "The one budget activity the key's rows print (assert_p1_era_map_one_code.sql)."
      - name: era_key
        data_tests: [not_null]
        description: "'{account}-{org}-L{line}' — budget_lines.pe_bli of the key's rows (era_keys.era_procurement_key). A within-edition identity only: line numbers are reused across editions for other programs."
      - name: line_item_code
        data_tests: [not_null]
        description: "The budget line code printed in column I ('Line Item') of every workbook row summed into the key — budget_lines.line_item_code (migration 021), source-stated, never mapped. One per key (assert_p1_era_map_one_code.sql)."
      - name: filed_title
        description: "The key's 'Line Item Title' exactly as filed (the title the owner reviewed; part of keys_sha256)."
      - name: program_key
        description: "The bare printed code (= line_item_code) when decision is same_program or history_only; NULL for every exclusion and for undecided keys. Never suffixed: a collision code's page split comes only from program_account / program_org."
      - name: program_account
        description: "Seed pin for a chain on one of the 10 PB2026 account-collision codes: the PB2026 account whose page the points join (assert_p1_era_map_collision_pinned.sql). NULL for every other code."
      - name: program_org
        description: "Seed pin for a chain on one of the 3 PB2026 organization-collision codes ('20', '30', '500'): the PB2026 organization whose page the points join (e.g. '20' DSS -> 'DCSA'). NULL for every other code."
      - name: decision
        description: "same_program (points join the code's page) · history_only (era-only code: data, no page — R-DEC-FAM-ERAONLY) · exclude_placeholder (FY2017CR/FY2018CR continuing-resolution lines) · exclude_route_unsafe (0390D O&M / RDT&E) · exclude_reused_code (the code meant a different program in this range) · undecided (no seed row covers the key)."
        data_tests:
          - not_null
          - accepted_values:
              values: ['same_program', 'history_only', 'exclude_placeholder', 'exclude_route_unsafe', 'exclude_reused_code', 'undecided']
      - name: decision_id
        description: "'{code}|{account}|{org}|{first}-{last}' of the seed row covering the key; NULL when undecided."
      - name: ruling
        description: "The owner ruling the decision was recorded under: R-DEC-ERA-SAME / R-DEC-ERA-EXCLUDE / R-DEC-ERA-HISTORY (the approved class rulings) or R-DEC-ERA-B<n> (review batch n). NULL when undecided."
      - name: keys_sha_ok
        description: "Drift guard: true when the sha256 of the sorted 'edition|era_key|budget_activity|filed_title' lines (NULL parts as '', joined by newline) of the keys this decision covers today equals the seed's keys_sha256 — what the owner reviewed (govbudget.jbooks.era_map.keys_sha256; tests/test_p1_era_line_map_sql.py proves the SQL and Python agree). false means the keys or titles changed after review (stale: `era-map check` and verify-era-map leg b fail). NULL when undecided."
      - name: successor_code
        description: "The P-1 code (as printed in PB2024–PB2026) under which a budget book states this era-only line continues (spec §5.4; e.g. JLTV 5600D15603 -> 5731D15610). Recorded, not displayed, in piece 1 (assert_p1_era_map_successor_resolves.sql). NULL otherwise."
      - name: source_document_sha256
        data_tests: [not_null]
        description: "sha256 of the edition's P-1 display workbook (jbook_documents.sha256; the file data/site/workbooks/<sha>.xlsx that verify-era-map leg a re-reads)."
      - name: source_cells
        data_tests: [not_null]
        description: "The column-I cells (the printed code) of every workbook row summed into the key, in row order, comma-separated (e.g. 'I35,I36' for a two-cost-type key) — the rows of the lake's recorded amount cells."
```

(The first two lines are the existing lines 415-416, shown for placement; add only the block
after them.)

In `GovBudget/tests/test_dbt_build.py`, add the helper after `write_parquet` (lines 30-32).
Before:

```python
def write_parquet(dir_path: Path, sql: str):
    dir_path.mkdir(parents=True, exist_ok=True)
    duckdb.sql(f"copy ({sql}) to '{dir_path}/part.parquet' (format parquet)")
```

After:

```python
def write_parquet(dir_path: Path, sql: str):
    dir_path.mkdir(parents=True, exist_ok=True)
    duckdb.sql(f"copy ({sql}) to '{dir_path}/part.parquet' (format parquet)")


def ensure_lake_columns(path: Path, columns: tuple[str, ...]) -> None:
    """Add each missing column to a fixture lake parquet as NULL varchar.

    `jbooks export-facts` always writes budget_lines.source_sheet and
    source_cells, and line_item_code since migration 021; the dbt models read
    them by name (stg_budget_lines passes line_item_code through,
    p1_era_line_map reads source_cells). NULL here: no fixture row is an era
    P-1 key. Idempotent — a column the fixture already writes is left alone.
    """
    con = duckdb.connect()
    try:
        have = {r[0] for r in con.execute(
            f"describe select * from read_parquet('{path}')").fetchall()}
        missing = [c for c in columns if c not in have]
        if not missing:
            return
        tmp = path.with_name(path.stem + ".tmp.parquet")
        extra = ", ".join(f"null::varchar as {c}" for c in missing)
        con.execute(
            f"copy (select *, {extra} from read_parquet('{path}'))"
            f" to '{tmp}' (format parquet)"
        )
    finally:
        con.close()
    tmp.replace(path)
```

Then call it right after the statement that writes `budget_lines.parquet` in `make_lake`. Its
last two lines are the ones below: lines 125-126 at 10fb4585, lines 156-157 once Task 7's Step 5
(four lines added above them) and the helper above (27 lines) are in. The text is unique in the
file. Before:

```python
        f" t({JBOOK_BUDGET_LINE_COLS})) to '{jbooks}/budget_lines.parquet' (format parquet)"
    )
```

After:

```python
        f" t({JBOOK_BUDGET_LINE_COLS})) to '{jbooks}/budget_lines.parquet' (format parquet)"
    )
    # jbooks export-facts always writes these three (line_item_code since
    # migration 021); stg_budget_lines and p1_era_line_map read them by name.
    ensure_lake_columns(
        jbooks / "budget_lines.parquet", ("line_item_code", "source_sheet", "source_cells"),
    )
```

Run: `uv run --project . pytest tests/test_dbt_build.py -q`

Expected: `7 passed` (the fixture build reports `PASS` for every `p1_era_map` test: the fixture
registers no era workbook, so the full-corpus legs are off, and its map has no rows).

- [ ] **Step 11: Commit the docs and the fixture change**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/dbt/models/marts/schema.yml GovBudget/tests/test_dbt_build.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "docs(era-map): document p1_era_line_map; fixture lake carries line_item_code/source_cells like export-facts" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 12: Build the map in the live warehouse (the sanctioned write, G4-3)**

Make sure no other session holds `data/duckdb/govbudget.duckdb` (an export or a dbt run). The
hourly SAM launchd job writes `data/parquet/sam` at :17, so the build starts only outside
minutes :12–:22. Run from `GovBudget/` in the worktree:

```bash
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: minute $MIN is in the SAM window (:12-:22); rerun after :22"; else \
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data \
GOVBUDGET_DUCKDB=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/duckdb/govbudget.duckdb \
uv run --project . dbt build --project-dir dbt --profiles-dir dbt \
  --select stg_budget_lines p1_era_code_decisions p1_era_line_map; fi
```

If it prints `WAIT: …`, nothing ran: run the same command again after :22.

Expected (order varies; other tests that read `stg_budget_lines` also run and PASS):
```
OK created sql view model main.stg_budget_lines
OK loaded seed file main.p1_era_code_decisions ....... [INSERT <seed rows>]
OK created sql table model main.p1_era_line_map
PASS assert_p1_era_map_one_code
PASS assert_p1_era_map_decisions_no_overlap
PASS assert_p1_era_map_successor_resolves
PASS assert_p1_era_map_grain_unique
PASS assert_p1_era_map_complete
PASS assert_p1_era_map_collision_pinned
PASS assert_p1_era_map_org_split
PASS assert_p1_era_map_p1r_crosscheck
PASS accepted_values_p1_era_line_map_decision__…
PASS not_null_p1_era_line_map_… (8 tests)
WARN <n> warn_p1_era_map_undecided
Done. PASS=… WARN=1 ERROR=0
```
`<n>` is the number of era keys in chains still awaiting review (WARN disappears when it is 0).
`Could not set lock on file` means another process holds the DuckDB file: wait and rerun.
In a scratch copy of the lake with a fully decided simulated seed (1,253 decision rows, every
chain decided, one organization per edition `same_program` on `10`/`15`) this selection plus
`fct_decade_series` and `fct_program_decade_series` gave `Done. PASS=50 WARN=0 ERROR=0`
(`--indirect-selection cautious`). Replayed in memory on the same lake with both organizations of
`10` and `15` set to `same_program`, `assert_p1_era_map_org_split` returned 4 rows, all labelled
`two organizations would sum into one page`: `15` in 2021, 2022 and 2023, and `10` in 2018.

- [ ] **Step 13: Check the live map (read-only)**

```bash
uv run --project . python -c "
import duckdb
con = duckdb.connect('/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/duckdb/govbudget.duckdb', read_only=True)
q = lambda s: print(con.execute(s).fetchall())
q('select edition, count(*) from p1_era_line_map group by 1 order by 1')
q('select count(*), count(distinct line_item_code) from p1_era_line_map')
q(\"select count(*) from p1_era_line_map where decision = 'undecided' or keys_sha_ok = false\")
q(\"select count(*), count(*) filter (where program_key = line_item_code) from p1_era_line_map where line_item_code in ('F01500','F015EX','F15EWS','F0150P','F015E0')\")
q(\"select source_document_sha256, source_cells from p1_era_line_map where edition = 2017 and era_key = '3010F-AF-L21'\")
"
```

Expected:
```
[(2017, 969), (2018, 1029), (2019, 989), (2020, 975), (2021, 1005), (2022, 993), (2023, 967)]
[(6927, 1158)]
[(<n>,)]                      # the same <n> as Step 12's WARN
[(31, 31)]
[('fa2d6711dc766be5cdf6148ed46b158e6420fe9653613900c43add4a28b26b31', 'I849')]
```
(1,158 distinct printed codes across the 6,927 keys and `'I849'` — where the PB2017 workbook
prints F01500 for line 21 — were measured read-only on 2026-10-02 from the workbooks' column I
and the lake's amount cells.) No commit: this step changes
only the shared warehouse.
