<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 9: S1b — load the era Classified Programs rows

**Spec:** §4.2 bullet 4 (S1b, separate commit), §7 row "Classified 9999999999", §9 S1b
("Lake gains exactly the budget_lines rows V1's parse predicts (one per amount column);
export diff empty").

**Choice: by default, no flag.** The parse change is permanent: from this commit every
`parse_p1_rollup` of an era P-1 workbook yields the Classified Programs rows, exactly as a
modern workbook does (PB2024–26 already load 85 such rows), so any future
`jbooks load-rollups` agrees with Postgres. An `--include-classified` flag would make the
S1 script and the CLI loader disagree about what an era workbook contains. The S1 script
therefore treats parse rows that Postgres lacks as a difference **except** rows with
`pe_bli = '9999999999'`, which it reports as "classified rows to load" and inserts; its
post-write check already requires the inserted set to equal exactly the parse rows the
table lacked.

**Prediction (measured read-only from the 7 workbooks with this task's parse):**
409 new `budget_lines` rows, one per non-blank amount column of the 50 workbook rows
(7 per edition, 8 in PB2023): PB2017 49 · PB2018 91 · PB2019 91 · PB2020 63 · PB2021 70 ·
PB2022 21 · PB2023 24. PB2023's two 3080F rows are in budget activities 03 and 04, so
they are separate keys (the upsert key includes `budget_activity`): 50 keys, 0 merges.
All carry organization `''` (as the 85 PB2024–26 rows do: `select fiscal_year, count(*)
from budget_lines where exhibit = 'P-1' and pe_bli = '9999999999' group by 1` → 2024 35,
2025 21, 2026 29), title `Classified Programs`,
`line_item_code '9999999999'`, and FY(N−2) actuals of $19.06B–$23.05B per edition
(PB2017 19,055,055 … PB2022 23,049,726 thousand). P-1/P-1R rows 84,463 → 84,872;
`budget_lines` 159,494 → 159,903.

**Consumer audit (read-only, 2026-10-02): no published surface reads these rows.**
Every reader of era-edition P-1 rows is fenced by edition, amount type, the
`9999999999` exclusion or a member filter:

| Consumer | Fence |
|---|---|
| `dbt/models/marts/fct_decade_series.sql:169-187` (`detail`, the only source of published grains), `:198-201`, `:218-219` | `pe_bli <> '9999999999'`; collision anchors `fiscal_year = 2026` |
| `dbt/models/marts/fct_decade_series.sql:156-166` (`lake`, unfiltered) | feeds only `lake_sums` (`:337-357`), read only through `where exists (… ls.pe_bli = ch.pe_bli …)` for grains `detail` chose — a `9999999999` sum is computed and never matched |
| `dbt/models/marts/dim_programs.sql:220, 260, 304, 429, 472, 494, 536` | `fiscal_year = 2026` on every reference |
| `dbt/models/marts/fct_program_trajectory.sql:90-94`, `dim_pe_titles.sql:34-36` | `fiscal_year = 2026` |
| `dbt/models/marts/fct_budget_trajectory.sql:72-73` | `amount_type in ('fy_2024_actuals','fy_2025_total','fy_2026_total')` — no era edition prints these (era types run fy_2015_* … fy_2023_*) |
| `dbt/models/marts/fct_budget_trajectory.sql:176-180` (`account_titles`: `max(account_title)` per account, all editions) | the 7 (account, account_title) pairs the new rows carry (0300D Procurement, Defense-Wide; 1109N Procurement, Marine Corps; 1810N Other Procurement, Navy; 2035A Other Procurement, Army; 3010F Aircraft Procurement, Air Force; 3020F Missile Procurement, Air Force; 3080F Other Procurement, Air Force) each equal `select account, max(account_title) from budget_lines where account is not null group by 1` for that account today — max unchanged |
| `dbt/models/marts/fct_flow_edges.sql:53-55`, `dbt/tests/assert_flow_budget_total_matches_lake.sql:20-22`, `site/scripts/gates/flowdown-recompute.py:69`, `site/scripts/gates/programs-excluded-recompute.py:95,110,132` | `amount_type = 'fy_2026_total'` |
| `dbt/tests/assert_dim_programs_detail_dedup.sql:63`, `assert_program_trajectory_component_sum.sql:48`, `assert_decade_series_no_p1r_contamination.sql:31,48,71` | `fiscal_year = 2026` and/or `pe_bli <> '9999999999'` |
| `src/govbudget/export_site.py:7650-7663` (`_load_budget_line_rows`) | `fiscal_year = 2026` |
| `src/govbudget/export_site.py:7014-7035` (decade tier lake read), `:6828-6834` | `pe_bli <> '9999999999'` |
| `src/govbudget/export_site.py:6155-6160, 6192-6198, 13550-13555` | `amount_type = 'fy_2024_actuals'` |
| `src/govbudget/export_site.py:6818-6822` | `fiscal_year = 2026` |
| `src/govbudget/export_site.py:10540-10547` (feed exhibit family) | only `pe_bli in fct_feed_events`; `9999999999` has 0 feed events (`select count(*) from fct_feed_events where pe_bli = '9999999999'` on the live warehouse, read-only → 0) |
| `src/govbudget/f15_funding_history.py:331-345` (lake P-1/R-1, all editions) | `build_history`'s `member_row` keeps F-15 members only |
| `src/govbudget/verify_phase5e.py` (leakage gate `:295-340`; decade gates via `cli.py:2133`) | leakage compares a row's edition with its document's (true for the new rows); decade gates recompute only `fct_decade_series` grains |
| `src/govbudget/jbooks/crosswalk.py:370, 409-422` | organization `''` lines are never run by default (`:403` comment); only the comment's count at `:423` changes (13 → 20 identities) |
| `src/govbudget/jbooks/edition_probe.py:360` → `data/research/edition_manifest.json` | a load-time count written by `jbooks backfill`; no gate reads it (`edition_coverage_gate5e` reads document statuses and reconciliation counts). It stays at its pre-S1b values |
| `src/govbudget/jbooks/{reconcile,gaps,trace,verify}.py` | extraction-time tools keyed on R-2/P-40 detail `pe_bli` (never `9999999999`); `gaps.py` excludes `SENTINEL_PE` |
| `evals/phase5_questions.yaml:102,126,138,159` | `amount_type = 'fy_2024_actuals'` |

No district model reads budget lines (the 24 references to `stg_budget_lines`,
`fct_budget_lines` and `source('lake','jbook_budget_lines')` in `dbt/` are the ones above).
The export diff in Step 12 is the arbiter.

**Files:**
- Modify: `src/govbudget/jbooks/p1_loader.py` (Task 6's version: after `P1_BLI_HEADERS`; the
  row loop's blank-line skip, section-header guard and pe_bli branch)
- Modify: `tests/jbooks/test_p1_loader_era.py` (replace
  `test_parse_skips_classified_footnote_and_section_header_rows`; add one test)
- Modify: `scripts/era/s1_reload_era_p1.py` (docstring, import, `compare_edition`, `print_report`)
- Modify: `tests/jbooks/test_s1_reload_era_p1.py` (import; append two tests)
- Modify: `src/govbudget/jbooks/crosswalk.py:423` (comment count, Step 15)
- Create: `docs/superpowers/reviews/families-s1b-proof.md` (Step 16)
- Shared writes (after the proof): live Postgres (409 inserted rows), live lake (`jbooks export-facts`)

**Interfaces:** Consumes: Tasks 6–8 (loader, export order, S1 script), Task 3 (proof tool).
/ Produces: `p1_loader.CLASSIFIED_CODE = "9999999999"`; era P-1 parse rows and
`budget_lines` rows with `pe_bli = line_item_code = '9999999999'`, organization `''`,
fiscal_year 2017–2023 (409 rows); S1 script output segment
`classified rows to load N`; snapshot `.proofs/s1` (its `pg/` dump is the post-S1,
pre-S1b database).

- [ ] **Step 1: Change the loader tests**

In `tests/jbooks/test_p1_loader_era.py`, replace:

```python
def test_parse_skips_classified_footnote_and_section_header_rows(tmp_path):
    """Blank-Line-Number rows (the Classified Programs line, footnotes) and
    the section-header label are skipped. S1b (Task 9) changes the first."""
    rows = ADVANCE_PROCUREMENT_PAIR[:1] + [CLASSIFIED, SECTION_HEADER] + FOOTNOTES
    parsed = parse_p1_rollup(make_era_xlsx(tmp_path, rows), exhibit="P-1", fiscal_year=2021)
    assert {r.pe_bli for r in parsed.rows} == {"1506N-N-L1"}
    assert parsed.skipped_invalid == 1  # the 'RDT&E' label row
```

with:

```python
def test_parse_loads_classified_and_skips_footnote_and_section_header_rows(tmp_path):
    """S1b: the blank-line Classified Programs row loads under its printed
    code, as modern editions load it; footnotes and the section header
    (blank or label Line Number, no classified code) stay skipped."""
    rows = ADVANCE_PROCUREMENT_PAIR[:1] + [CLASSIFIED, SECTION_HEADER] + FOOTNOTES
    parsed = parse_p1_rollup(make_era_xlsx(tmp_path, rows), exhibit="P-1", fiscal_year=2021)
    assert {r.pe_bli for r in parsed.rows} == {"1506N-N-L1", "9999999999"}
    assert parsed.skipped_invalid == 1  # the 'RDT&E' label row
    classified = sorted(
        (r for r in parsed.rows if r.pe_bli == "9999999999"), key=lambda r: r.amount_type)
    assert classified == [
        P1Row(
            exhibit="P-1", fiscal_year=2021, account="3080F",
            account_title="Other Procurement, Air Force", organization="",
            budget_activity="04",
            budget_activity_title="Other Base Maintenance and Support Equip",
            pe_bli="9999999999", title="Classified Programs",
            amount_type=amount_type, amount_thousands=Decimal(amount),
            source_sheet="Exhibit P-1", source_cells=(cell,),
            line_item_code="9999999999",
        )
        for amount_type, amount, cell in (
            ("fy_2019_base_oco", "20743417", "O4"),
            ("fy_2020_base_enacted", "21086112", "Q4"),
        )
    ]


def test_parse_skips_a_blank_line_row_with_any_other_code(tmp_path):
    stray = _row(OPAF, "", "04", "Other Base Maintenance and Support Equip", "",
                 "3080F00001", "Not classified", "", "Add", 5, 6)
    parsed = parse_p1_rollup(make_era_xlsx(tmp_path, [stray]), exhibit="P-1", fiscal_year=2021)
    assert parsed.rows == []
    assert parsed.skipped_invalid == 0
```

(openpyxl writes nothing for an empty-string cell, so the fixture's blank organization
reads back as `None`; the real workbooks print `''`. Both must load as `''`.)

- [ ] **Step 2: Add the S1 script tests**

In `tests/jbooks/test_s1_reload_era_p1.py`, replace:

```python
import hashlib
import importlib.util
from pathlib import Path
```

with:

```python
import hashlib
import importlib.util
from decimal import Decimal
from pathlib import Path
```

and append at the end of the file, after two blank lines:

```python
# S1b: the era Classified Programs line (blank Line Number, organization '',
# code 9999999999 — live PB2021 row 1096).
CLASSIFIED_2021 = ["3080F", "Other Procurement, Air Force", "", "04",
                   "Other Base Maintenance and Support Equip", "", "99",
                   "Classified Programs", "9999999999", "Classified Programs",
                   "", "", "Add", 0, 20743417, 0, 21086112]


def _add_classified(pg_dsn, era_db):
    doc_id, path = era_db[2021]
    _workbook(path, EDITION_ROWS[2021] + [CLASSIFIED_2021])
    with psycopg.connect(pg_dsn) as con:
        con.execute("update jbook_documents set sha256 = %s where id = %s",
                    (hashlib.sha256(path.read_bytes()).hexdigest(), doc_id))


def test_check_counts_classified_rows_to_load_without_failing(pg_dsn, era_db, capsys):
    _add_classified(pg_dsn, era_db)
    assert _run(pg_dsn, "--check") == 0
    out = capsys.readouterr().out
    assert "missing in db 0" in out
    assert "classified rows to load 2" in out
    assert "V1: CLEAN (2 editions, 8 parsed rows)" in out


def test_apply_inserts_exactly_the_classified_rows(pg_dsn, era_db, capsys):
    _add_classified(pg_dsn, era_db)
    before = _snapshot(pg_dsn)
    assert _run(pg_dsn, "--apply") == 0
    out = capsys.readouterr().out
    assert "apply: rows inserted: 2 (expected 2); P-1/P-1R rows now 10" in out
    assert "apply: era keys 3, with exactly one line_item_code: 3" in out
    after = _snapshot(pg_dsn)
    assert [r[:8] for r in after[:len(before)]] == [r[:8] for r in before]
    assert [r[1:] for r in after[len(before):]] == [
        ("P-1", 2021, "9999999999", "fy_2019_base_oco", Decimal("20743417"),
         "Classified Programs", ["O5"], "9999999999"),
        ("P-1", 2021, "9999999999", "fy_2020_base_enacted", Decimal("21086112"),
         "Classified Programs", ["Q5"], "9999999999"),
    ]
    assert _run(pg_dsn, "--check") == 0
    assert "classified rows to load 0" in capsys.readouterr().out
```

- [ ] **Step 3: Run them to see them fail**

Run: `GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_p1_loader_era.py tests/jbooks/test_s1_reload_era_p1.py -q`

Expected: `3 failed, 22 passed`:
`test_parse_loads_classified_and_skips_footnote_and_section_header_rows`
(`assert {'1506N-N-L1'} == {'1506N-N-L1', '9999999999'}`),
`test_check_counts_classified_rows_to_load_without_failing`
(`assert 'classified rows to load 2' in 'V1 PB2020 P-1 …'`) and
`test_apply_inserts_exactly_the_classified_rows`
(`assert 'apply: rows inserted: 2 (expected 2); P-1/P-1R rows now 10' in …`).
`test_parse_skips_a_blank_line_row_with_any_other_code` passes before and after: it pins
that only the classified code is admitted.

- [ ] **Step 4: Load the Classified Programs rows in the parse**

In `src/govbudget/jbooks/p1_loader.py`, replace:

```python
P1_REQUIRED = {"Account", "Organization"}
P1_BLI_HEADERS = ("Budget Line Item", "Line Item")
```

with:

```python
P1_REQUIRED = {"Account", "Organization"}
P1_BLI_HEADERS = ("Budget Line Item", "Line Item")
# The Classified Programs line: every P-1 edition prints it under this code.
# Modern workbooks key it by its 'Budget Line Item' like any line; era
# workbooks print it with a blank Line Number, so it needs its own rule.
CLASSIFIED_CODE = "9999999999"
```

replace:

```python
        ids = {name: row[j] for j, name in id_cols.items() if j < len(row)}
        if not ids.get("pe_bli"):
            continue
        # Reject appropriation section-header rows ('RDT&E', 'O&M', …) whose
        # label mis-parses into the BLI cell. Guard the RAW cell (before era
        # re-keying), so a valid alphanumeric BLI / era line number survives.
        if not _is_valid_pe_bli(ids.get("pe_bli")):
            skipped_invalid += 1
            continue
```

with:

```python
        ids = {name: row[j] for j, name in id_cols.items() if j < len(row)}
        # S1b: an era row with a blank Line Number is the Classified Programs
        # line when its Line Item is CLASSIFIED_CODE (it loads under that
        # code, as in modern editions); any other blank-line row (footnotes,
        # spacer rows) is skipped.
        classified = (
            era_line_keying and not ids.get("pe_bli")
            and code_col < len(row) and _code(row[code_col]) == CLASSIFIED_CODE
        )
        if not ids.get("pe_bli") and not classified:
            continue
        # Reject appropriation section-header rows ('RDT&E', 'O&M', …) whose
        # label mis-parses into the BLI cell. Guard the RAW cell (before era
        # re-keying), so a valid alphanumeric BLI / era line number survives.
        if not classified and not _is_valid_pe_bli(ids.get("pe_bli")):
            skipped_invalid += 1
            continue
```

and replace:

```python
        if era_line_keying:
            pe_bli = era_procurement_key(
```

with:

```python
        if classified:
            pe_bli = code = CLASSIFIED_CODE
            # The line names no organization: the workbooks print '' (as
            # PB2024-PB2026 rows store it); an empty cell reads back as None,
            # which must load as '' too, never the string 'None'.
            if ids.get("organization") is None:
                ids["organization"] = ""
        elif era_line_keying:
            pe_bli = era_procurement_key(
```

The classified row is not an era key, so it never enters `era_prints` (the tripwire),
and the key tuple, amount melt and cells are unchanged.

- [ ] **Step 5: Let the S1 script admit exactly those rows**

In `scripts/era/s1_reload_era_p1.py`, replace:

```python
The parse runs before any database work, so EraKeyConflict propagates
uncaught (this script never goes through the CLI's per-workbook catch-all).
```

with:

```python
S1b: a key the parse yields but Postgres lacks is a difference, except
an era Classified Programs row (pe_bli 9999999999, which the loader skipped
before S1b): --check counts those as "classified rows to load" and --apply
inserts them; the post-write check requires exactly those inserts.

The parse runs before any database work, so EraKeyConflict propagates
uncaught (this script never goes through the CLI's per-workbook catch-all).
```

replace:

```python
from govbudget.jbooks.p1_loader import P1Parse, P1Row, parse_p1_rollup, write_p1_rows
```

with:

```python
from govbudget.jbooks.p1_loader import (
    CLASSIFIED_CODE,
    P1Parse,
    P1Row,
    parse_p1_rollup,
    write_p1_rows,
)
```

replace (in `compare_edition`):

```python
    missing = sorted(set(parse_by_key) - set(db), key=repr)
```

with:

```python
    absent = sorted(set(parse_by_key) - set(db), key=repr)
    # S1b: the era Classified Programs rows the loader used to skip are the
    # only rows the parse may add; any other absent key is a difference.
    to_load = [k for k in absent if k[5] == CLASSIFIED_CODE]
    missing = [k for k in absent if k[5] != CLASSIFIED_CODE]
```

replace (in `compare_edition`'s return dict):

```python
        "dup_keys": dup_keys, "missing": missing, "extra": extra,
```

with:

```python
        "dup_keys": dup_keys, "missing": missing, "extra": extra,
        "to_load": to_load,
```

and replace (in `print_report`):

```python
        f" {len(rep['diffs'])} | line_item_code: {codes}"
```

with:

```python
        f" {len(rep['diffs'])} | classified rows to load {len(rep['to_load'])}"
        f" | line_item_code: {codes}"
```

`report_ok` is unchanged (it fails on `missing`, which no longer holds the classified
keys); `verify_apply` is unchanged (its expected inserts are the parse keys the table
lacked).

- [ ] **Step 6: Run the tests to see them pass**

Run: `GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks -q`

Expected: `458 passed, 2 skipped`.

- [ ] **Step 7: Commit the code**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/src/govbudget/jbooks/p1_loader.py GovBudget/tests/jbooks/test_p1_loader_era.py GovBudget/scripts/era/s1_reload_era_p1.py GovBudget/tests/jbooks/test_s1_reload_era_p1.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(jbooks): load the era P-1 Classified Programs line under 9999999999, as modern editions do (families S1b)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Steps 8–17 run in one shell from the worktree's `GovBudget/`; stop at the first
unexpected output. Set once:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget
set -o pipefail
PROOFS=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
LIVE_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data
LIVE_PG=postgresql://localhost/govbudget
LOGS=$PROOFS/s1b-logs
mkdir -p $LOGS
```

- [ ] **Step 8: V1 against the live database (read-only) — the prediction**

```bash
GOVBUDGET_PG_DSN=$LIVE_PG uv run --project . python scripts/era/s1_reload_era_p1.py --check 2>&1 | tee $LOGS/01-v1-live.log
```

Expected (exit 0; the parse and `db` counts were measured read-only with this parse on
2026-10-02; the `line_item_code` counts are the state Task 8 leaves):

```
V1 PB2017 P-1 (doc 189): parse 6832 rows | db 6783 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 49 | line_item_code: null 0, equal 6783, differ 0
V1 PB2018 P-1 (doc 261): parse 13468 rows | db 13377 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 91 | line_item_code: null 0, equal 13377, differ 0
V1 PB2019 P-1 (doc 271): parse 12948 rows | db 12857 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 91 | line_item_code: null 0, equal 12857, differ 0
V1 PB2020 P-1 (doc 282): parse 8838 rows | db 8775 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 63 | line_item_code: null 0, equal 8775, differ 0
V1 PB2021 P-1 (doc 292): parse 10120 rows | db 10050 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 70 | line_item_code: null 0, equal 10050, differ 0
V1 PB2022 P-1 (doc 302): parse 3000 rows | db 2979 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 21 | line_item_code: null 0, equal 2979, differ 0
V1 PB2023 P-1 (doc 312): parse 2925 rows | db 2901 | missing in db 0 | extra in db 0 | duplicate parse keys 0 | column diffs 0 | classified rows to load 24 | line_item_code: null 0, equal 2901, differ 0
V1: CLEAN (7 editions, 58131 parsed rows)
```

- [ ] **Step 9: Snapshot the post-S1 state**

Check `date +%M` is not 15–20. Then:

```bash
GOVBUDGET_DATA=$LIVE_DATA GOVBUDGET_PG_DSN=$LIVE_PG uv run --project . python -m govbudget proof snapshot --out $PROOFS/s1 --scratch-db govbudget_proof_s1 2>&1 | tee $LOGS/02-snapshot.log
ls $PROOFS/s1/snapshot.json $PROOFS/s1/env.sh
```

Expected: exit 0; both files listed.

- [ ] **Step 10: Export A — the post-S1 state under this commit**

```bash
cp -c -R $PROOFS/s1 $PROOFS/s1-A
( source $PROOFS/s1/env.sh $PROOFS/s1-A \
  && uv run --project . python -m govbudget jbooks export-facts \
  && uv run --project . python -m govbudget build \
  && uv run --project . python -m govbudget export-site ) 2>&1 | tee $LOGS/03-A.log
```

Expected: exit 0; the nine `exported:` names; dbt `Completed successfully`; the
`export-site:` summary line.

- [ ] **Step 11: Export B — A plus the S1b insert**

```bash
cp -c -R $PROOFS/s1 $PROOFS/s1-B
( source $PROOFS/s1/env.sh $PROOFS/s1-B \
  && uv run --project . python scripts/era/s1_reload_era_p1.py --apply \
  && uv run --project . python -m govbudget jbooks export-facts \
  && uv run --project . python -m govbudget build \
  && uv run --project . python -m govbudget export-site ) 2>&1 | tee $LOGS/04-B.log
```

Expected: exit 0; the apply prints the Step 8 V1 block (it re-runs V1 under its lock), then:

```
apply: snapshot 84463 P-1/P-1R rows
apply: PB2017 wrote 6832 rows
apply: PB2018 wrote 13468 rows
apply: PB2019 wrote 12948 rows
apply: PB2020 wrote 8838 rows
apply: PB2021 wrote 10120 rows
apply: PB2022 wrote 3000 rows
apply: PB2023 wrote 2925 rows
apply: pre-existing rows changed outside line_item_code: 0
apply: line_item_code equals the parse on 57722 pre-existing era-edition P-1 rows (null before: 0)
apply: rows inserted: 409 (expected 409); P-1/P-1R rows now 84872
apply: era keys 6927, with exactly one line_item_code: 6927
apply: COMMITTED
```

then the export-facts, dbt and export-site lines.

- [ ] **Step 12: Site diff — A = B**

```bash
uv run --project . python -m govbudget proof diff $PROOFS/s1-A/site $PROOFS/s1-B/site 2>&1 | tee $LOGS/05-diff-A-B.log
```

Expected: the log ends `proof diff: EQUAL`. If `DIFFERENT`: stop, do not run Steps 13–17,
and file the changed files as a consumer the audit above missed (spec: "export diff
empty").

- [ ] **Step 13: Lake check — exactly the predicted rows were added**

```bash
uv run --project . python - $PROOFS/s1-A/parquet/jbooks $PROOFS/s1-B/parquet/jbooks <<'EOF' 2>&1 | tee $LOGS/06-lake.log
import sys
from collections import Counter
from pathlib import Path

import duckdb

A, B = (Path(p) for p in sys.argv[1:3])
COLS = ("exhibit, fiscal_year, account, account_title, organization, budget_activity,"
        " budget_activity_title, pe_bli, title, amount_type, amount_thousands,"
        " source_document_id, source_sheet, source_cells, line_item_code")
con = duckdb.connect()


def q(sql):
    return con.execute(sql).fetchall()


a, b = (q(f"select {COLS} from read_parquet('{d}/budget_lines.parquet')") for d in (A, B))
added = b[len(a):]
print(f"rows: A {len(a)} | B {len(b)} | added {len(added)}")
print("B starts with A, row for row (15 columns):", b[:len(a)] == a)
print("every added row is P-1 / pe_bli 9999999999 / organization '' /"
      " title Classified Programs / line_item_code 9999999999:",
      all(r[0] == "P-1" and r[7] == "9999999999" and r[4] == ""
          and r[8] == "Classified Programs" and r[14] == "9999999999" for r in added))
print("added per edition:", sorted(Counter(r[1] for r in added).items()))
others = sorted(p.name for p in A.glob("*.parquet") if p.name != "budget_lines.parquet")
same = all(
    sorted(map(repr, q(f"select * from read_parquet('{A}/{n}')")))
    == sorted(map(repr, q(f"select * from read_parquet('{B}/{n}')")))
    for n in others
)
print(f"other jbooks parquets equal as multisets, A = B: {same} ({len(others)} files)")
EOF
```

Expected:

```
rows: A 159494 | B 159903 | added 409
B starts with A, row for row (15 columns): True
every added row is P-1 / pe_bli 9999999999 / organization '' / title Classified Programs / line_item_code 9999999999: True
added per edition: [('2017', 49), ('2018', 91), ('2019', 91), ('2020', 63), ('2021', 70), ('2022', 21), ('2023', 24)]
other jbooks parquets equal as multisets, A = B: True (8 files)
```

(The new rows take the next ids, so the id-ordered export appends them.)

- [ ] **Step 14: Live write — rehearse, apply, re-check, export**

```bash
export GOVBUDGET_DATA=$LIVE_DATA GOVBUDGET_PG_DSN=$LIVE_PG
uv run --project . python scripts/era/s1_reload_era_p1.py --apply --dry-run 2>&1 | tee $LOGS/07-live-dry-run.log
uv run --project . python scripts/era/s1_reload_era_p1.py --apply 2>&1 | tee $LOGS/08-live-apply.log
uv run --project . python scripts/era/s1_reload_era_p1.py --check 2>&1 | tee $LOGS/09-live-v1-after.log
m=$((10#$(date +%M))); if [ $m -ge 15 ] && [ $m -le 20 ]; then echo "SAM write window: wait until :21 and re-run this line"; else uv run --project . python -m govbudget jbooks export-facts 2>&1 | tee $LOGS/10-live-export-facts.log; fi
uv run --project . python - $LIVE_PG postgresql://localhost/govbudget_proof_s1 $LIVE_DATA/parquet/jbooks $PROOFS/s1-B/parquet/jbooks <<'EOF' 2>&1 | tee $LOGS/11-live-equals-rehearsal.log
import sys

import duckdb
import psycopg

LIVE_DSN, REHEARSAL_DSN, LIVE_LAKE, REHEARSAL_LAKE = sys.argv[1:5]
COLS = ("id, exhibit, fiscal_year, account, account_title, organization,"
        " budget_activity, budget_activity_title, line_number, pe_bli, title,"
        " amount_type, amount_thousands, source_document_id, source_sheet,"
        " source_cells, line_item_code")


def pg_rows(dsn):
    with psycopg.connect(dsn) as con:
        con.read_only = True
        return con.execute(
            f"select {COLS} from budget_lines where exhibit in ('P-1', 'P-1R')"
            " order by id").fetchall()


live, reh = pg_rows(LIVE_DSN), pg_rows(REHEARSAL_DSN)
print(f"P-1/P-1R rows: live {len(live)} | rehearsal {len(reh)} |"
      f" identical (17 columns, by id): {live == reh}")
con = duckdb.connect()
l, r = (con.execute(f"select * from read_parquet('{p}/budget_lines.parquet')").fetchall()
        for p in (LIVE_LAKE, REHEARSAL_LAKE))
print(f"lake budget_lines: live {len(l)} rows | rehearsal {len(r)} rows |"
      f" identical row for row: {l == r}")
EOF
```

Expected: the dry run prints the Step 11 V1 and apply blocks with the last line
`apply: dry run, every check passed: ROLLED BACK`; the apply ends `apply: COMMITTED`
with `rows inserted: 409 (expected 409); P-1/P-1R rows now 84872`; the check prints
seven lines with `missing in db 0 | … | classified rows to load 0 | line_item_code: null 0, equal <n>, differ 0`
(`<n>` = 6832, 13468, 12948, 8838, 10120, 3000, 2925) and
`V1: CLEAN (7 editions, 58131 parsed rows)`; the export prints the nine `exported:` names;
the last command prints:

```
P-1/P-1R rows: live 84872 | rehearsal 84872 | identical (17 columns, by id): True
lake budget_lines: live 159903 rows | rehearsal 159903 rows | identical row for row: True
```

- [ ] **Step 15: Keep crosswalk.py's live count true**

Run (read-only):

```bash
uv run --project . python -c "import psycopg; c = psycopg.connect('postgresql://localhost/govbudget'); c.read_only = True; print(c.execute(\"select count(*) from (select distinct pe_bli, exhibit, fiscal_year from budget_lines where organization = '') t\").fetchone()[0])"
```

Expected: `20` (13 before S1b: R-1 PB2017–26 and P-1 PB2024–26; + the seven era P-1
editions). In `src/govbudget/jbooks/crosswalk.py`, replace (`:423`):

```python
#: How an empty organization code prints in a refusal (13 live identities).
```

with:

```python
#: How an empty organization code prints in a refusal (20 live identities since
#: S1b loaded the seven PB2017-PB2023 P-1 Classified Programs lines, 2026-10-02).
```

- [ ] **Step 16: Run the whole test suite, write the proof note, commit**

Step 14 exported the live lake and database into this shell; no test may see them:

Run: `unset GOVBUDGET_DATA GOVBUDGET_PG_DSN GOVBUDGET_DUCKDB; GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest -q`

Expected: `3560 passed, 42 skipped` (measured on a copy of this branch with Tasks 6–9
applied; Tasks 1–5 add their own tests on top, so the requirement is `0 failed`).

```bash
NOTE=docs/superpowers/reviews/families-s1b-proof.md
{
  echo "# Families piece 1 — S1b proof (era Classified Programs rows, Task 9)"
  echo
  echo "Spec: docs/superpowers/specs/2026-10-02-era-procurement-history-design.md §4.2, §9 S1b."
  echo "Code: $(git rev-parse HEAD). Snapshot: .proofs/s1 (snapshot.json sha256 $(shasum -a 256 $PROOFS/s1/snapshot.json | cut -d' ' -f1)); scratch database govbudget_proof_s1."
  echo
  echo "Prediction (parse of the 7 workbooks): 409 rows = 49/91/91/63/70/21/24 (PB2017-PB2023), 50 keys; PB2023's two 3080F rows are BA 03 and BA 04."
  echo "A = the post-S1 snapshot, jbooks export-facts, govbudget build, export-site. B = A + s1_reload_era_p1.py --apply, then the same."
  echo "Consumer audit: see the Task 9 table in the families piece 1 plan; no published reader takes era-edition 9999999999 rows."
  echo "data/research/edition_manifest.json budget_lines counts are load-time records (no gate reads them) and stay at their pre-S1b values."
  for f in $LOGS/*.log; do
    echo; echo "## $(basename $f .log)"; echo; echo '```'; tail -n 25 "$f"; echo '```'
  done
} > $NOTE
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/docs/superpowers/reviews/families-s1b-proof.md GovBudget/src/govbudget/jbooks/crosswalk.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "docs(families): S1b proof — 409 era Classified Programs rows loaded as predicted, site export unchanged" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget
```

- [ ] **Step 17: Clean up the run clones and the scratch database**

```bash
rm -rf $PROOFS/s1-A $PROOFS/s1-B
/opt/homebrew/opt/postgresql@17/bin/dropdb govbudget_proof_s1
ls $PROOFS/s1/pg/
```

Expected: the `ls` lists the post-S1 dump (kept until the release, Task 23).
