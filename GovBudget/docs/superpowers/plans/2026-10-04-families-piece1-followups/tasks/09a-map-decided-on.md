<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the approved design is ../../../specs/2026-10-04-families-piece1-followups-design.md. -->

### Task 9a: `decided_on` on `p1_era_line_map`, proved by verify-era-map leg b (#206 T6)

Task 9 ("Map code changes") is split into 9a (`decided_on`), 9b (the strict era-key regex, both collision pins, the
unplanted dbt legs) and 9c (the verify-era-map CLI and leg a/b test gaps), one reviewer gate each. Run them in that
order: 9b and 9c quote blocks as 9a leaves them.

**Spec:** design §5.1 (T6: the decisions CTE, `bound`, the final select — column 14 of 18 — `schema.yml` `not_null`
and its description, verify-era-map `MAP_COLUMNS` and leg b, the four tests that pin 17 columns, the piece-1 spec §4.4
amendment); §2.2 Q18 (owner: `decided_on` only, not `decided_by`); §6.4's prerequisite note (the map is rebuilt once,
by Task 22's single selective build — this task builds nothing shared); §7 W2/W3.

**Files:**
- Modify: `dbt/models/marts/p1_era_line_map.sql` (header comment before "-- keys_sha_ok is the drift guard"; the
  `decisions` CTE; the `bound` CTE; the final select)
- Modify: `dbt/models/marts/schema.yml` (`p1_era_line_map` columns, after `ruling`)
- Modify: `src/govbudget/verify_era_map.py` (docstring leg (b); `MAP_COLUMNS`; `leg_b_decisions`)
- Modify: `tests/test_p1_era_line_map_sql.py`, `tests/test_verify_era_map.py`, `tests/test_export_era_line_map.py`,
  `tests/test_explorer_era_map_preset.py`
- Modify: `docs/superpowers/specs/2026-10-02-era-procurement-history-design.md` (§4.4, a dated amendment)

Line numbers are hints measured at `532205c9` (anchor on the quoted text; earlier tasks shift them).

**Interfaces:**
Consumes: the seed column `decided_on` (`dbt/seeds/p1_era_code_decisions.csv`, typed `varchar` in
`dbt/dbt_project.yml`, ISO dates checked by `assert_p1_era_map_decisions_no_overlap.sql`); Task 8's
`p1_era_line_map.sql`, which computes `program_key` from the route-safe seed — this task touches neither that
expression nor any join Task 8 adds, only the `ruling` lines of `decisions`, `bound` and the final select and the
`-- keys_sha_ok is the drift guard` comment line; `tests/dbt_render.py` (`render_dbt_sql`).
Produces: `p1_era_line_map.decided_on DATE`, column 14 of 18, right after `ruling` (NULL only for undecided keys);
`verify_era_map.MAP_COLUMNS` with 18 names; leg b's map-vs-seed tuple `(decision, ruling, program_account,
program_org, successor_code, decided_on)` (the map's date as ISO text against the seed's text); one more dbt
assertion (`not_null` on `decided_on`: the count moves 198 → 199, Task 6's `assert_route_safe_codes_valid` and Task 7's `assert_budget_lines_route_safe_pe_bli` having landed first; README decision 8). The published
`data/p1_era_line_map.parquet` gains the column at the release export (`_export_p1_era_line_map` is `select *`; no
exporter change); leg e compares columns dynamically.

Verified now (read-only, 2026-10-13, live lake, outside :12–:22): the seed holds 1,128 rows dated 2026-10-02 (the
class rulings), 121 dated 2026-10-03 (B1–B5) and 4 dated 2026-10-04 (B6); joined to the map's 6,927 keys that is
6,212 / 701 / 14, with 0 undecided. Step 5 reproduces these figures from the changed model. After this task, legs a–c
of `verify-era-map` run against the PRE-release live warehouse read "p1_era_line_map unreadable" (its map has 17
columns and `_read_map` selects `decided_on`); that is expected until Task 22's build, and no step here runs them
against the live warehouse.

- [ ] **Step 1: Write the failing tests**

In `tests/test_p1_era_line_map_sql.py` (:21-23), replace:

```python
import duckdb
import pytest
from dbt_render import render_dbt_sql
```

with:

```python
from datetime import date

import duckdb
import pytest
from dbt_render import render_dbt_sql
```

In `tests/test_p1_era_line_map_sql.py` (:150-157, `test_one_row_per_era_key_with_the_spec_columns`), replace:

```python
        "line_item_code", "filed_title", "program_key", "program_account", "program_org",
        "decision", "decision_id", "ruling", "keys_sha_ok", "successor_code",
        "source_document_sha256", "source_cells",
    ]
```

with:

```python
        "line_item_code", "filed_title", "program_key", "program_account", "program_org",
        "decision", "decision_id", "ruling", "decided_on", "keys_sha_ok", "successor_code",
        "source_document_sha256", "source_cells",
    ]
```

In `tests/test_p1_era_line_map_sql.py` (:196), replace:

```python
def test_a_key_no_decision_covers_is_undecided_and_carries_nothing():
```

with:

```python
def test_decided_on_is_the_date_of_the_decision_the_key_binds():
    """ROADMAP #206 T6: the map publishes each decision's date (the seed's
    decided_on, as a date), so "a dated decision" is true of the dataset
    itself. An undecided key has none."""
    seed = _seed()
    seed[1]["decided_on"] = "2026-10-03"
    m = _map(_lake(seed=seed))
    assert m[(2019, "0300D-DSS-L21")]["decided_on"] == date(2026, 10, 3)
    assert {m[k]["decided_on"] for k in [(2019, "3010F-AF-L25"), (2019, "3010F-AF-L79"),
                                         (2020, "3010F-AF-L25"), (2019, "0300D-DTRA-L23")]} == {
        date(2026, 10, 2)}
    assert m[(2019, "2035A-ARMY-L5")]["decided_on"] is None


def test_a_key_no_decision_covers_is_undecided_and_carries_nothing():
```

In `tests/test_verify_era_map.py` (:77, `_write_map`), replace:

```python
    types = {"edition": "integer", "keys_sha_ok": "boolean"}
```

with:

```python
    types = {"edition": "integer", "keys_sha_ok": "boolean", "decided_on": "date"}
```

In `tests/test_verify_era_map.py` (:139-141, `Corpus.__init__`), replace:

```python
                k.update(program_key=code, program_account=None, program_org=None,
                         decision=decision, decision_id=did,
                         ruling=self.seed[-1]["ruling"], keys_sha_ok=True, successor_code=None)
```

with:

```python
                k.update(program_key=code, program_account=None, program_org=None,
                         decision=decision, decision_id=did,
                         ruling=self.seed[-1]["ruling"], decided_on="2026-10-02",
                         keys_sha_ok=True, successor_code=None)
```

In `tests/test_verify_era_map.py` (:295), replace:

```python
def test_leg_b_fails_on_an_unreadable_seed(corpus):
```

with:

```python
def test_leg_b_fails_when_the_published_date_is_not_the_seed_date(corpus):
    """ROADMAP #206 T6: leg b proves the map's decided_on is the seed's, so a
    date edited in the seed after the build reads as a stale build."""
    next(s for s in corpus.seed if s["line_item_code"] == "F15EWS")["decided_on"] = "2026-10-03"
    corpus.save()
    failures = _failures(corpus.leg_b())
    assert failures == [
        "F15EWS|3010F||2019-2023: map ('same_program', 'R-DEC-ERA-SAME', None, None, None,"
        " '2026-10-02') != seed ('same_program', 'R-DEC-ERA-SAME', None, None, None,"
        " '2026-10-03') (stale build)"]


def test_leg_b_fails_on_an_unreadable_seed(corpus):
```

In `tests/test_export_era_line_map.py` (:21-42), replace:

```python
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
```

with:

```python
    " program_org varchar, decision varchar, decision_id varchar,"
    " ruling varchar, decided_on date, keys_sha_ok boolean, successor_code varchar,"
    " source_document_sha256 varchar, source_cells varchar)"
)
ROWS = [
    (2018, "3010F", "AF", "01", "3010F-AF-L2", "ATA000", "F-35", "ATA000", None, None,
     "same_program", "ATA000|3010F||2017-2018", "R-DEC-ERA-SAME", "2026-10-02", True, None, "sha18", "J9"),
    (2017, "3010F", "AF", "01", "3010F-AF-L1", "ATA000", "F-35", "ATA000", None, None,
     "same_program", "ATA000|3010F||2017-2018", "R-DEC-ERA-SAME", "2026-10-02", True, None, "sha17", "J8"),
    (2017, "3010F", "AF", "05", "3010F-AF-L9", "F0150P", "LEGACY LINE", "F0150P", None, None,
     "history_only", "F0150P|3010F||2017-2017", "R-DEC-ERA-HISTORY", "2026-10-02", True, None, "sha17", "J20"),
    (2017, "0300D", "OSD", "01", "0300D-OSD-L50", "50", "INDIAN FINANCING ACT", None, None, None,
     "exclude_reused_code", "50|0300D||2017-2019", "R-DEC-ERA-B1", "2026-10-03", True, None, "sha17", "J60"),
    (2017, "2035A", "A", "01", "2035A-A-L3", "FY2017CR", "CR ADJUSTMENT", None, None, None,
     "exclude_placeholder", "FY2017CR|2035A||2017-2017", "R-DEC-ERA-EXCLUDE", "2026-10-02", True, None, "sha17", "J70"),
]
INSERT = "insert into p1_era_line_map values (" + ",".join("?" * 18) + ")"
```

In `tests/test_export_era_line_map.py` (:156), replace:

```python
def test_refuses_an_undecided_line(tmp_path):
```

with:

```python
def test_ships_each_decisions_date(tmp_path):
    """ROADMAP #206 T6: the export is `select *` of the mart, so the decision
    date ships as column 14, a DATE, right after ruling."""
    con = _con_with_map()
    _export_p1_era_line_map(con, tmp_path)
    cur = duckdb.connect().execute(
        "select * from read_parquet(?) order by edition, era_key",
        [str(tmp_path / "p1_era_line_map.parquet")])
    names = [d[0] for d in cur.description]
    assert names.index("decided_on") == 13 and names[12] == "ruling" and len(names) == 18
    rows = cur.fetchall()
    assert [str(r[13]) for r in rows] == [
        "2026-10-03", "2026-10-02", "2026-10-02", "2026-10-02", "2026-10-02"]


def test_refuses_an_undecided_line(tmp_path):
```

In `tests/test_explorer_era_map_preset.py` (:20-40), replace:

```python
    " program_org varchar, decision varchar, decision_id varchar,"
    " ruling varchar, keys_sha_ok boolean, successor_code varchar,"
    " source_document_sha256 varchar, source_cells varchar)"
)
ROWS = [
    (2017, "3010F", "AF", "01", "3010F-AF-L1", "ATA000", "F-35", "ATA000", None, None,
     "same_program", "ATA000|3010F||2017-2021", "R-DEC-ERA-SAME", True, None, "sha17", "J8"),
    (2017, "3010F", "AF", "01", "3010F-AF-L2", "ATA000", "F-35 AP", "ATA000", None, None,
     "same_program", "ATA000|3010F||2017-2021", "R-DEC-ERA-SAME", True, None, "sha17", "J9"),
    (2017, "1611N", "N", "02", "1611N-N-L4", "1045", "OHIO REPLACEMENT", "1045", "1611N", None,
     "same_program", "1045|1611N||2017-2020", "R-DEC-ERA-B1", True, None, "sha17", "J30"),
    (2018, "1611N", "N", "02", "1611N-N-L4", "1045", "OHIO REPLACEMENT", "1045", "1611N", None,
     "same_program", "1045|1611N||2017-2020", "R-DEC-ERA-B1", True, None, "sha18", "J31"),
    (2018, "0300D", "OSD", "01", "0300D-OSD-L50", "50", "INDIAN FINANCING ACT", None, None, None,
     "exclude_reused_code", "50|0300D||2017-2019", "R-DEC-ERA-B2", True, None, "sha18", "J60"),
]
```

with:

```python
    " program_org varchar, decision varchar, decision_id varchar,"
    " ruling varchar, decided_on date, keys_sha_ok boolean, successor_code varchar,"
    " source_document_sha256 varchar, source_cells varchar)"
)
ROWS = [
    (2017, "3010F", "AF", "01", "3010F-AF-L1", "ATA000", "F-35", "ATA000", None, None,
     "same_program", "ATA000|3010F||2017-2021", "R-DEC-ERA-SAME", "2026-10-02", True, None, "sha17", "J8"),
    (2017, "3010F", "AF", "01", "3010F-AF-L2", "ATA000", "F-35 AP", "ATA000", None, None,
     "same_program", "ATA000|3010F||2017-2021", "R-DEC-ERA-SAME", "2026-10-02", True, None, "sha17", "J9"),
    (2017, "1611N", "N", "02", "1611N-N-L4", "1045", "OHIO REPLACEMENT", "1045", "1611N", None,
     "same_program", "1045|1611N||2017-2020", "R-DEC-ERA-B1", "2026-10-03", True, None, "sha17", "J30"),
    (2018, "1611N", "N", "02", "1611N-N-L4", "1045", "OHIO REPLACEMENT", "1045", "1611N", None,
     "same_program", "1045|1611N||2017-2020", "R-DEC-ERA-B1", "2026-10-03", True, None, "sha18", "J31"),
    (2018, "0300D", "OSD", "01", "0300D-OSD-L50", "50", "INDIAN FINANCING ACT", None, None, None,
     "exclude_reused_code", "50|0300D||2017-2019", "R-DEC-ERA-B2", "2026-10-03", True, None, "sha18", "J60"),
]
```

In `tests/test_explorer_era_map_preset.py` (:56), replace:

```python
    con.executemany("insert into m values (" + ",".join("?" * 17) + ")", ROWS)
```

with:

```python
    con.executemany("insert into m values (" + ",".join("?" * 18) + ")", ROWS)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_p1_era_line_map_sql.py tests/test_verify_era_map.py tests/test_export_era_line_map.py tests/test_explorer_era_map_preset.py -q`
Expected: exactly three failures — `test_one_row_per_era_key_with_the_spec_columns` (the map has 17 columns),
`test_decided_on_is_the_date_of_the_decision_the_key_binds` (`KeyError: 'decided_on'`) and
`test_leg_b_fails_when_the_published_date_is_not_the_seed_date` (leg b compares no date, so it reports nothing).
`test_ships_each_decisions_date` already passes: the export is `select *` of the mart (measured on a scratch overlay
of `532205c9`, 2026-10-13).

- [ ] **Step 3: Implement the column, its schema entry and leg b**

In `dbt/models/marts/p1_era_line_map.sql` (:36, the header comment), replace:

```sql
-- keys_sha_ok is the drift guard: the seed stores keys_sha256, the sha256 of
```

with:

```sql
-- decided_on is the seed row's decided_on as a DATE (ROADMAP #206 T6): the
-- date the owner approved the ruling the decision is recorded under. For the
-- class rulings R-DEC-ERA-SAME / -HISTORY / -EXCLUDE that is the spec's
-- approval date, 2026-10-02, applied by rule rather than row by row; for
-- R-DEC-ERA-B<n> it is the date the owner answered the batch, as its answers
-- file records it. NULL only for undecided keys. verify-era-map leg b proves
-- it equals the seed on disk.
--
-- keys_sha_ok is the drift guard: the seed stores keys_sha256, the sha256 of
```

In `dbt/models/marts/p1_era_line_map.sql` (:107-122, the `decisions` CTE), replace:

```sql
        keys_sha256 as reviewed_keys_sha256,
        ruling
    from {{ ref('p1_era_code_decisions') }}
```

with:

```sql
        keys_sha256 as reviewed_keys_sha256,
        ruling,
        cast(decided_on as date) as decided_on
    from {{ ref('p1_era_code_decisions') }}
```

In `dbt/models/marts/p1_era_line_map.sql` (:124-140, the `bound` CTE), replace:

```sql
        d.reviewed_keys_sha256,
        d.ruling
    from keys k
```

with:

```sql
        d.reviewed_keys_sha256,
        d.ruling,
        d.decided_on
    from keys k
```

In `dbt/models/marts/p1_era_line_map.sql` (:157-174, the final select), replace:

```sql
    b.ruling,
    case when b.decision_id is not null then cs.keys_sha256 = b.reviewed_keys_sha256 end as keys_sha_ok,
```

with:

```sql
    b.ruling,
    b.decided_on,
    case when b.decision_id is not null then cs.keys_sha256 = b.reviewed_keys_sha256 end as keys_sha_ok,
```

In `dbt/models/marts/schema.yml` (:453-456), replace:

```yaml
        description: "The owner ruling the decision was recorded under: R-DEC-ERA-SAME / R-DEC-ERA-EXCLUDE / R-DEC-ERA-HISTORY (the approved class rulings) or R-DEC-ERA-B<n> (review batch n). NULL when undecided."
      - name: keys_sha_ok
```

with:

```yaml
        description: "The owner ruling the decision was recorded under: R-DEC-ERA-SAME / R-DEC-ERA-EXCLUDE / R-DEC-ERA-HISTORY (the approved class rulings) or R-DEC-ERA-B<n> (review batch n). NULL when undecided."
      - name: decided_on
        data_tests: [not_null]
        description: "The date the owner approved the ruling the decision is recorded under: for R-DEC-ERA-SAME/HISTORY/EXCLUDE the spec's approval date (2026-10-02), applied by rule rather than row by row; for R-DEC-ERA-B<n> the date the owner answered the batch, as its answers file records it."
      - name: keys_sha_ok
```

In `src/govbudget/verify_era_map.py` (:23-28, the module docstring), replace:

```python
  Leg (b) — decisions. No era key is undecided; every decided key's
    keys_sha_ok (the dbt-side drift hash) is true; the map was built from the
    seed on disk (each decided key's decision_id exists there with the same
    decision, ruling, pins and successor); no seed row binds zero keys; and,
```

with:

```python
  Leg (b) — decisions. No era key is undecided; every decided key's
    keys_sha_ok (the dbt-side drift hash) is true; the map was built from the
    seed on disk (each decided key's decision_id exists there with the same
    decision, ruling, pins, successor and decided_on — the published date,
    ROADMAP #206 T6); no seed row binds zero keys; and,
```

In `src/govbudget/verify_era_map.py` (:88-93), replace:

```python
    "decision", "decision_id", "ruling", "keys_sha_ok", "successor_code",
    "source_document_sha256", "source_cells",
)
```

with:

```python
    "decision", "decision_id", "ruling", "decided_on", "keys_sha_ok", "successor_code",
    "source_document_sha256", "source_cells",
)
```

In `src/govbudget/verify_era_map.py` (:307-313, `leg_b_decisions`), replace:

```python
        for r in rows:
            got = (r["decision"], r["ruling"], r["program_account"], r["program_org"],
                   r["successor_code"])
            want = (s["decision"], s["ruling"], s["program_account"], s["program_org"],
                    s["successor_code"])
```

with:

```python
        for r in rows:
            decided_on = r["decided_on"]
            got = (r["decision"], r["ruling"], r["program_account"], r["program_org"],
                   r["successor_code"],
                   decided_on.isoformat() if hasattr(decided_on, "isoformat") else decided_on)
            want = (s["decision"], s["ruling"], s["program_account"], s["program_org"],
                    s["successor_code"], s["decided_on"])
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_p1_era_line_map_sql.py tests/test_verify_era_map.py tests/test_verify_era_map_def.py tests/test_export_era_line_map.py tests/test_explorer_era_map_preset.py tests/test_program_decade_series_sql.py -q`
Expected: no failures (on the scratch overlay of `532205c9` plus this task: `131 passed`; earlier tasks may add tests
to these files).

- [ ] **Step 5: Prove the column on the live lake, read-only**

Renders the changed model and runs it in memory against the live warehouse (attached `read_only`) and the live
parquets; nothing is written. The guard line keeps it out of the SAM window.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
uv run --project . python - <<'EOF'
"""Read-only: run the worktree's p1_era_line_map.sql on the live lake, in memory.
Each ref() resolves to the committed seed CSV under dbt/seeds (all varchar, as
dbt_project.yml types the era seed) or else to the live warehouse table of that
name, attached read_only; the two lake sources are the live parquets. Nothing
is written anywhere."""
import os
import re
from pathlib import Path

import duckdb

ROOT, DATA = Path("."), Path(os.environ["GOVBUDGET_DATA"])
sql = (ROOT / "dbt/models/marts/p1_era_line_map.sql").read_text()
sql = re.sub(r"\{\{\s*config\([^}]*\)\s*\}\}", "", sql)
refs = sorted(set(re.findall(r"\{\{\s*ref\('([a-z0-9_]+)'\)\s*\}\}", sql)))
sql = re.sub(r"\{\{\s*ref\('([a-z0-9_]+)'\)\s*\}\}", r"\1", sql)
sources = {"jbook_budget_lines": DATA / "parquet/jbooks/budget_lines.parquet",
           "jbook_documents": DATA / "parquet/jbooks/documents.parquet"}
sql = re.sub(r"\{\{\s*source\('lake',\s*'([a-z_]+)'\)\s*\}\}",
             lambda m: f"read_parquet('{sources[m.group(1)]}')", sql)
assert "{{" not in sql
con = duckdb.connect()
con.execute(f"attach '{os.environ['GOVBUDGET_DUCKDB']}' as live (read_only)")
for ref in refs:
    seed = ROOT / "dbt" / "seeds" / f"{ref}.csv"
    if seed.is_file():
        con.execute(f"create table {ref} as select * from read_csv('{seed}', all_varchar=true, header=true)")
    else:
        con.execute(f"create view {ref} as select * from live.main.{ref}")
con.execute("create table new_map as " + sql)
cols = [d[0] for d in con.execute("select * from new_map limit 0").description]
print("refs:", refs)
print("columns:", len(cols), "decided_on at", cols.index("decided_on") + 1)
print("rows:", con.execute("select count(*) from new_map").fetchone()[0])
print("decided_on:", con.execute(
    "select cast(decided_on as varchar), count(*) from new_map group by 1 order by 1").fetchall())
live_cols = [d[0] for d in con.execute("select * from live.main.p1_era_line_map limit 0").description]
shared = ", ".join(c for c in live_cols if c in cols)
for a, b in (("new_map", "live.main.p1_era_line_map"), ("live.main.p1_era_line_map", "new_map")):
    n = con.execute(f"select count(*) from (select {shared} from {a}"
                    f" except all select {shared} from {b})").fetchone()[0]
    print(f"{a} except all {b} on the {len(live_cols)} live columns: {n}")
EOF
```
Expected (measured 2026-10-13 on the overlay; Task 8 adds `p1_route_safe_codes` to `refs` if its SQL refs that seed):

```
refs: ['p1_era_code_decisions', 'stg_budget_lines']
columns: 18 decided_on at 14
rows: 6927
decided_on: [('2026-10-02', 6212), ('2026-10-03', 701), ('2026-10-04', 14)]
new_map except all live.main.p1_era_line_map on the 17 live columns: 0
live.main.p1_era_line_map except all new_map on the 17 live columns: 0
```
If either `except all` count is not 0, stop: Task 8's alias, or a seed change, moved a row that this task must not move.

- [ ] **Step 6: Record the amendment in the piece-1 spec**

In `docs/superpowers/specs/2026-10-02-era-procurement-history-design.md` (§4.4, :169-170), replace:

```markdown
A small `json/era_map_summary.json` (chains and dollars by decision and ruling,
receipt completeness per edition) is exported for the site to render (§6.4).
```

with:

```markdown
A small `json/era_map_summary.json` (chains and dollars by decision and ruling,
receipt completeness per edition) is exported for the site to render (§6.4).

*Amendment (owner decision 2026-10-04, families piece-1 follow-ups, ROADMAP
#206 T6; nothing above reworded).* The map also publishes `decided_on`, the
seed row's date as a DATE, placed right after `ruling` (column 14 of 18): the
date the owner approved the ruling the decision is recorded under. For the
class rulings R-DEC-ERA-SAME/HISTORY/EXCLUDE that is this spec's approval
date, 2026-10-02, applied by rule rather than row by row; for R-DEC-ERA-B<n>
it is the date the owner answered the batch, as its answers file records it
(B7: 2026-10-04, before its ratify). `decided_by` is not published (it is always
`owner`, and `assert_p1_era_map_decisions_no_overlap` enforces that).
verify-era-map leg b proves the published date equals the seed.
```

- [ ] **Step 7: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/dbt/models/marts/p1_era_line_map.sql GovBudget/dbt/models/marts/schema.yml GovBudget/src/govbudget/verify_era_map.py GovBudget/tests/test_p1_era_line_map_sql.py GovBudget/tests/test_verify_era_map.py GovBudget/tests/test_export_era_line_map.py GovBudget/tests/test_explorer_era_map_preset.py GovBudget/docs/superpowers/specs/2026-10-02-era-procurement-history-design.md && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(era-map): publish decided_on in p1_era_line_map; verify-era-map leg b proves it (#206 T6)" -m "Column 14 of 18, the seed date as a DATE (class rulings 2026-10-02, B1-B5 2026-10-03, B6 2026-10-04; 6,212/701/14 keys live). schema.yml not_null (+1 dbt assertion); leg b compares it; piece-1 spec 4.4 amended. The live map is rebuilt by Task 22." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
