<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 7: line_item_code through export_facts (in id order) and stg_budget_lines

**Spec:** §4.2 bullet 5 (export_facts + stg), CONTRACT ISSUE 2 (fixture lake column, id order).

**Files:**
- Modify: `src/govbudget/jbooks/export_facts.py:19-25` (the `"budget_lines"` entry of `EXPORTS`)
- Modify: `dbt/models/staging/stg_budget_lines.sql:12-14`
- Modify: `tests/jbooks/test_export_facts.py` (append after `:426`)
- Modify: `tests/test_dbt_build.py:68-69` (`make_lake`'s `budget_lines.parquet` COPY) and `:450-452` (`test_dbt_build_succeeds_on_fixture_lake`)

**Interfaces:** Consumes: `budget_lines.line_item_code` (Task 6). / Produces: lake
`data/parquet/jbooks/budget_lines.parquet` column `line_item_code` (varchar, appended
last; rows in `budget_lines.id` order); `stg_budget_lines.line_item_code` (and so
`fct_budget_lines.line_item_code`, which is `select *` from it).

- [ ] **Step 1: Write the failing export tests**

Append to `tests/jbooks/test_export_facts.py`, after two blank lines following the last line (`:426`):

```python
#: budget_lines.parquet, column for column (all varchar). line_item_code
#: (migration 021, families piece 1) is appended last, so no earlier column
#: moved; the mart reads it by name (stg_budget_lines).
BUDGET_LINES_EXPORT_COLUMNS = [
    "exhibit", "fiscal_year", "account", "account_title", "organization",
    "budget_activity", "budget_activity_title", "pe_bli", "title",
    "amount_type", "amount_thousands", "source_document_id", "source_sheet",
    "source_cells", "line_item_code",
]


def test_export_facts_carries_line_item_code_last(pg_dsn, tmp_path):
    upsert_documents(pg_dsn, [{
        "org": "DoD", "exhibit_family": "rollup", "fiscal_year": 2021,
        "title": "p1_display.xlsx", "source_url": "https://example.test/p1.xlsx",
    }])
    with psycopg.connect(pg_dsn) as con:
        doc_id = con.execute("select id from jbook_documents").fetchone()[0]
        con.execute(
            "insert into budget_lines (exhibit, fiscal_year, account, organization,"
            " budget_activity, pe_bli, amount_type, amount_thousands,"
            " source_document_id, line_item_code)"
            " values ('P-1',2021,'1506N','N','01','1506N-N-L1','fy_2019_base_oco',"
            "  1010,%s,'0577')", (doc_id,))
        con.execute(
            "insert into budget_lines (exhibit, fiscal_year, account, organization,"
            " pe_bli, amount_type, amount_thousands, source_document_id)"
            " values ('R-1',2021,'0400','DARPA','0601101E','fy_2019_base_oco',"
            "  5,%s)", (doc_id,))
    export_facts(pg_dsn, parquet_dir=tmp_path)
    out = tmp_path / "jbooks" / "budget_lines.parquet"
    cols = duckdb.sql(f"select * from read_parquet('{out}') limit 0").columns
    assert cols == BUDGET_LINES_EXPORT_COLUMNS
    got = duckdb.sql(
        f"select pe_bli, line_item_code from read_parquet('{out}') order by pe_bli"
    ).fetchall()
    assert got == [("0601101E", None), ("1506N-N-L1", "0577")]


def test_export_facts_orders_budget_lines_by_id(pg_dsn, tmp_path):
    """An UPDATE writes a new tuple at the end of the heap, so an unordered
    export moves the row. S1 rewrites every era P-1 tuple (migration 021
    every modern P-1/P-1R one); the lake file follows id, so a rewrite of
    unchanged rows never reorders it."""
    upsert_documents(pg_dsn, [{
        "org": "DoD", "exhibit_family": "rollup", "fiscal_year": 2021,
        "title": "p1_display.xlsx", "source_url": "https://example.test/p1.xlsx",
    }])
    with psycopg.connect(pg_dsn) as con:
        doc_id = con.execute("select id from jbook_documents").fetchone()[0]
        for pe_bli in ("1506N-N-L1", "1506N-N-L2"):
            con.execute(
                "insert into budget_lines (exhibit, fiscal_year, account,"
                " organization, budget_activity, pe_bli, amount_type,"
                " amount_thousands, source_document_id)"
                " values ('P-1',2021,'1506N','N','01',%s,'fy_2019_base_oco',1,%s)",
                (pe_bli, doc_id))
        con.execute("update budget_lines set line_item_code = '0577'"
                    " where pe_bli = '1506N-N-L1'")
        heap = [r[0] for r in con.execute("select pe_bli from budget_lines").fetchall()]
    assert heap == ["1506N-N-L2", "1506N-N-L1"]  # the update moved L1 behind L2
    export_facts(pg_dsn, parquet_dir=tmp_path)
    got = duckdb.sql(
        f"select pe_bli from read_parquet('{tmp_path}/jbooks/budget_lines.parquet')"
    ).fetchall()
    assert got == [("1506N-N-L1",), ("1506N-N-L2",)]
```

- [ ] **Step 2: Run them to see them fail**

Run: `GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_export_facts.py -q -k "line_item_code or orders_budget_lines"`

Expected: `2 failed`: `Right contains one more item: 'line_item_code'` and
`At index 0 diff: ('1506N-N-L2',) != ('1506N-N-L1',)`.

- [ ] **Step 3: Export the column, in id order**

In `src/govbudget/jbooks/export_facts.py`, replace (`:19-25`):

```python
    "budget_lines": (
        "select exhibit, fiscal_year, account, account_title, organization,"
        " budget_activity, budget_activity_title, pe_bli, title, amount_type,"
        " amount_thousands, source_document_id, source_sheet,"
        " coalesce(array_to_string(source_cells, ','), '') as source_cells from budget_lines"
        " where source_document_id is not null"
    ),
```

with:

```python
    "budget_lines": (
        "select exhibit, fiscal_year, account, account_title, organization,"
        " budget_activity, budget_activity_title, pe_bli, title, amount_type,"
        " amount_thousands, source_document_id, source_sheet,"
        " coalesce(array_to_string(source_cells, ','), '') as source_cells,"
        " line_item_code from budget_lines"
        " where source_document_id is not null"
        # Row order is the table's id (insertion) order. An unordered select
        # returns heap order, which moves whenever an UPDATE rewrites a
        # tuple: migration 021 rewrites every modern P-1/P-1R row and the S1
        # re-run every era P-1 row, so the lake file would reorder under
        # unchanged data. Switching heap -> id order permutes the file once
        # (159,494 rows on 2026-10-02); the S1 proof's Z-vs-A export diff
        # shows the published site does not depend on that order.
        " order by id"
    ),
```

- [ ] **Step 4: Run the export tests to see them pass**

Run: `GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_export_facts.py -q`

Expected: `16 passed`.

- [ ] **Step 5: Give the dbt fixture lake the column and assert stg passes it**

In `tests/test_dbt_build.py`, replace (`:68-69`):

```python
    duckdb.sql(
        f"copy (select * from (values ('R-1','2026','0400','Research','DARPA','1','Basic Research',"
```

with:

```python
    duckdb.sql(
        # line_item_code (migration 021): the printed budget line code, as
        # migration 021 backfills it — pe_bli on P-1/P-1R rows (none of this
        # fixture's P-1 rows is an era key), NULL on R-1 rows.
        f"copy (select *, case when exhibit in ('P-1', 'P-1R') then pe_bli end"
        f" as line_item_code from (values ('R-1','2026','0400','Research','DARPA','1','Basic Research',"
```

and replace (`:450-452`):

```python
    assert result.returncode == 0, result.stdout + result.stderr
    con = duckdb.connect(str(tmp_path / "duckdb" / "test.duckdb"))
    # 4 since the ROADMAP #6 rider added K3, a deobligation on K1's award.
```

with:

```python
    assert result.returncode == 0, result.stdout + result.stderr
    con = duckdb.connect(str(tmp_path / "duckdb" / "test.duckdb"))
    # Families piece 1 (migration 021): stg_budget_lines passes the printed
    # budget line code through by name; R-1 rows carry none.
    assert con.sql(
        "select exhibit, count(*), count(line_item_code),"
        " count(*) filter (where line_item_code = pe_bli)"
        " from stg_budget_lines group by 1 order by 1"
    ).fetchall() == [("P-1", 5, 5, 5), ("P-1R", 1, 1, 1), ("R-1", 7, 0, 0)]
    # 4 since the ROADMAP #6 rider added K3, a deobligation on K1's award.
```

(The fixture lake holds 5 P-1, 1 P-1R and 7 R-1 budget rows.)

- [ ] **Step 6: Run it to see it fail**

Run: `uv run --project . pytest tests/test_dbt_build.py -q -k succeeds_on_fixture_lake`

Expected: `1 failed` with `_duckdb.BinderException: Binder Error: Referenced column "line_item_code" not found in FROM clause!`
(the build succeeds — stg selects by name and ignores the new parquet column — and the new
assertion's query fails).

- [ ] **Step 7: Pass the column through stg_budget_lines**

In `dbt/models/staging/stg_budget_lines.sql`, replace (`:12-14`):

```sql
    try_cast(amount_thousands as double) as amount_thousands,
    source_document_id
from {{ source('lake', 'jbook_budget_lines') }}
```

with:

```sql
    try_cast(amount_thousands as double) as amount_thousands,
    source_document_id,
    line_item_code
from {{ source('lake', 'jbook_budget_lines') }}
```

- [ ] **Step 8: Run the dbt fixture tests to see them pass**

Run: `uv run --project . pytest tests/test_dbt_build.py tests/test_dbt_program_lobbying_title.py tests/test_dbt_award_fy_moves.py tests/test_dbt_link_grading.py tests/test_dbt_lda_amendments.py -q`

Expected: `61 passed` (every dbt build that uses `make_lake` now sees the column).

- [ ] **Step 9: Run the jbooks suite**

Run: `GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks -q`

Expected: `444 passed, 2 skipped`.

- [ ] **Step 10: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/src/govbudget/jbooks/export_facts.py GovBudget/dbt/models/staging/stg_budget_lines.sql GovBudget/tests/jbooks/test_export_facts.py GovBudget/tests/test_dbt_build.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(jbooks): export budget_lines.line_item_code to the lake in id order; stg_budget_lines passes it through (families S1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Do **not** run `jbooks export-facts` or `govbudget build` against the shared lake here:
the live Postgres has no `line_item_code` until Task 8's migrate (export-facts would fail),
and the live lake parquet has none until Task 8's export (a branch build would fail).

---
