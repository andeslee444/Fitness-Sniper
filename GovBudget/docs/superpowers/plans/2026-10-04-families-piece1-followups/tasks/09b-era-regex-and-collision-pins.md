<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the approved design is ../../../specs/2026-10-04-families-piece1-followups-design.md. -->

### Task 9b: one full era-key regex at every site, both collision pins, the unplanted era legs (#203)

Second part of Task 9 (after 9a). It hardens the era tests and touches the map model only at its two regex lines,
so the live map is still rebuilt once, by Task 22.

**Spec:** design §6.4 (#203): "Replace the loose regex `^[0-9]{4}[A-Z]-[A-Z]+-L` with the full one at every site
(ten literal copies — eight dbt files, the exporter's parity check at `export_site.py:7252` and one test)", "In
`era_keys._ERA_KEY_RE`, change `$` to `\Z`", "`assert_p1_era_map_collision_pinned` requires both pins", "Plant the four
unplanted legs: complete × 2, P-1R triple count, and account collision", "`ensure_lake_columns` unlinks its temporary
file on failure"; §6.9 (a sheet name in `source_cells` is not done); piece-1 plan binding decision 5 (the seed sets
both pins on a collision code); §7 W1/W2.

**Files:**
- Create: `tests/test_era_key_regex_sites.py`
- Modify (one scripted replacement, Step 3): `dbt/models/marts/p1_era_line_map.sql` (2 sites, :68 and :94),
  `dbt/models/marts/fct_program_decade_series.sql` (:124), `dbt/models/marts/fct_book_diff.sql` (:73),
  `dbt/tests/assert_p1_era_map_one_code.sql` (:17), `dbt/tests/assert_book_diff_no_era_procurement.sql` (:10),
  `dbt/tests/assert_program_decade_native_equals_line.sql` (:16), `dbt/tests/assert_p1_era_map_complete.sql` (:45),
  `src/govbudget/export_site.py` (:7252, the runtime native-parity check), `tests/test_program_decade_series_sql.py`
  (:251)
- Modify: `src/govbudget/jbooks/era_keys.py` (:68-69, `_ERA_KEY_RE`)
- Replace: `dbt/tests/assert_p1_era_map_collision_pinned.sql` (whole file)
- Modify: `tests/test_p1_era_line_map_sql.py`, `tests/jbooks/test_era_keys.py`, `tests/test_dbt_build.py` (imports;
  `ensure_lake_columns` :35-59; a test appended)

Line numbers are hints measured at `532205c9` (anchor on the quoted text).

**Interfaces:**
Consumes: Task 9a's `p1_era_line_map.sql` (this task's script asserts exactly 2 prefix-only regex sites in it, which
Tasks 8 and 9a leave alone); Task 4's `era_keys.py` (Task 4 moves `EraKeyConflict` there; this task changes only the
`_ERA_KEY_RE` line and the comment above it — if Task 4 put code between "# including sub-line forms…" and
`_ERA_KEY_RE`, anchor on the `_ERA_KEY_RE` line alone); `tests/dbt_render.py`.
Produces: the SQL era-key pattern `'^[0-9]{4}[A-Z]-[A-Z]+-L[0-9][0-9A-Za-z-]*$'` at the ten sites and nowhere else
under `dbt/models`, `dbt/tests`, `src`, `tests` (pinned by `tests/test_era_key_regex_sites.py`; a new site must be
added to its `SITES`); `era_keys.is_era_procurement_key` rejects a trailing newline; `assert_p1_era_map_collision_pinned`
failure labels `'account-collision code without a usable pin pair'` / `'organization-collision code without a usable
pin pair'` / `'pin on a code that is not a PB2026 collision code'` (same 7 columns as before); no new dbt test file, so
the dbt assertion count does not move here.

Verified now (read-only, 2026-10-13): the prefix-only and the full pattern select the same rows live — 57,722
`stg_budget_lines` rows and 20,781 `fct_decade_series` rows each; every carried era key on a collision code has both
pins (118 keys on the 10 account-collision codes, 67 on '20'/'30'/'500'), and every same_program one names a
(code, account, organization) that PB2026 prints (Step 5 re-runs these). `scripts/era/s1_reload_era_p1.py` and
`scripts/era/fact_stability.py` keep their own Python spellings; they are operator scripts outside the ten sites.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_era_key_regex_sites.py`:

```python
r"""One spelling of the era-key pattern at every SQL site (ROADMAP #203;
families piece-1 follow-ups design §6.4, Task 9).

dbt's era tests and models, the exporter's runtime parity check and one unit
test each select era P-1 keys with a regex literal. They used the prefix
'^[0-9]{4}[A-Z]-[A-Z]+-L', looser than era_keys._ERA_KEY_RE: it accepts
'0300D-DEFW-L' and '0300D-DEFW-Lx'. Every site now spells the full pattern,
and the full pattern agrees with era_keys.is_era_procurement_key, whose `$`
became `\Z` (a Python `$` also matches before a trailing newline, so
'0300D-DEFW-L1\n' was an era key). The live lake has no such key: the loose
and the full pattern select the same 57,722 stg_budget_lines rows (measured
read-only 2026-10-13).
"""
from __future__ import annotations

from pathlib import Path

import duckdb

from govbudget.jbooks.era_keys import is_era_procurement_key

ROOT = Path(__file__).resolve().parents[1]
FULL_SQL = "'^[0-9]{4}[A-Z]-[A-Z]+-L[0-9][0-9A-Za-z-]*$'"
LOOSE_SQL = "'^[0-9]{4}[A-Z]-[A-Z]+-L'"
SITES = {
    "dbt/models/marts/p1_era_line_map.sql": 2,
    "dbt/models/marts/fct_program_decade_series.sql": 1,
    "dbt/models/marts/fct_book_diff.sql": 1,
    "dbt/tests/assert_p1_era_map_one_code.sql": 1,
    "dbt/tests/assert_book_diff_no_era_procurement.sql": 1,
    "dbt/tests/assert_program_decade_native_equals_line.sql": 1,
    "dbt/tests/assert_p1_era_map_complete.sql": 1,
    "src/govbudget/export_site.py": 1,
    "tests/test_program_decade_series_sql.py": 1,
}
PROBES = [
    "3010F-AF-L1", "0300D-WHS-L46-1", "2031A-ARMY-L102",
    "0300D-DEFW-L1\n", "0300D-DEFW-L", "0300D-DEFW-Lx", "0300D-DEFW-L1 ",
    "X0300D-DEFW-L1", "0300D-defw-L1", "9999999999", "0601101E", "70", "",
]


def test_every_site_spells_the_full_pattern():
    for rel, n in SITES.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert text.count(LOOSE_SQL) == 0, f"{rel}: still spells the prefix-only era-key regex"
        assert text.count(FULL_SQL) == n, f"{rel}: expected {n} full era-key regex(es)"


def test_no_unlisted_site_spells_an_era_key_regex():
    found = set()
    for base in ("dbt/models", "dbt/tests", "src", "tests"):
        for path in (ROOT / base).rglob("*"):
            if path.suffix in (".sql", ".py") and "[0-9]{4}[A-Z]-[A-Z]+-L" in path.read_text(encoding="utf-8"):
                found.add(path.relative_to(ROOT).as_posix())
    assert found == set(SITES) | {"tests/test_era_key_regex_sites.py"}


def test_sql_and_python_agree_on_what_an_era_key_is():
    con = duckdb.connect()
    in_sql = [con.execute(f"select regexp_matches(?, {FULL_SQL})", [p]).fetchone()[0] for p in PROBES]
    assert in_sql == [is_era_procurement_key(p) for p in PROBES]
    assert in_sql == [True, True, True] + [False] * 10
```

In `tests/test_p1_era_line_map_sql.py` (:74-77, `_seed()`), replace:

```python
        _seed_row(decision_id="20|0300D|DSS|2019-2019", line_item_code="20", account="0300D",
                  organization="DSS", first_edition="2019", last_edition="2019",
                  decision="same_program", program_org="DCSA", n_keys="1",
```

with:

```python
        _seed_row(decision_id="20|0300D|DSS|2019-2019", line_item_code="20", account="0300D",
                  organization="DSS", first_edition="2019", last_edition="2019",
                  decision="same_program", program_account="0300D", program_org="DCSA", n_keys="1",
```

In `tests/test_p1_era_line_map_sql.py` (:79-82, `_seed()`), replace:

```python
        _seed_row(decision_id="20|0300D|DTRA|2019-2019", line_item_code="20", account="0300D",
                  organization="DTRA", first_edition="2019", last_edition="2019",
                  decision="same_program", program_org="DTRA", n_keys="1",
```

with:

```python
        _seed_row(decision_id="20|0300D|DTRA|2019-2019", line_item_code="20", account="0300D",
                  organization="DTRA", first_edition="2019", last_edition="2019",
                  decision="same_program", program_account="0300D", program_org="DTRA", n_keys="1",
```

In `tests/test_p1_era_line_map_sql.py` (:287), replace:

```python
def test_complete_pins_the_corpus_counts_once_all_seven_workbooks_are_registered():
```

with:

```python
def test_complete_fails_on_a_map_key_the_lake_does_not_hold():
    # ROADMAP #203: one of the two relational legs no test planted.
    con = _lake()
    con.execute("insert into p1_era_line_map select * replace ('3010F-AF-L99' as era_key)"
                " from p1_era_line_map where era_key = '3010F-AF-L79'")
    assert [r[:2] for r in _failures(con, "assert_p1_era_map_complete")] == [
        ("map key not in the lake", "2019/3010F-AF-L99")]


def test_complete_fails_on_a_map_key_without_its_workbook_sha_or_cells():
    # ROADMAP #203: the other unplanted relational leg.
    con = _lake()
    con.execute("update p1_era_line_map set source_cells = null where era_key = '3010F-AF-L79'")
    assert _failures(con, "assert_p1_era_map_complete") == [
        ("map key without its workbook sha or cells", "2019/3010F-AF-L79", None,
         f"{SHA_2019} <null cells>")]


def test_complete_pins_the_corpus_counts_once_all_seven_workbooks_are_registered():
```

In `tests/test_p1_era_line_map_sql.py` (:380-382, `test_collision_pinned_fails_on_a_missing_or_foreign_pin`), replace:

```python
    assert sorted((r[0], r[2]) for r in rows) == [
        ("organization-collision code without a usable organization pin", "0300D-DSS-L21"),
        ("organization-collision code without a usable organization pin", "0300D-DTRA-L23"),
```

with:

```python
    assert sorted((r[0], r[2]) for r in rows) == [
        ("organization-collision code without a usable pin pair", "0300D-DSS-L21"),
        ("organization-collision code without a usable pin pair", "0300D-DTRA-L23"),
```

In `tests/test_p1_era_line_map_sql.py` (:389), replace:

```python
def test_collision_pinned_lets_a_history_only_chain_keep_its_own_organization():
```

with:

```python
def test_collision_pinned_requires_both_pins():
    """ROADMAP #203: plan binding decision 5 — the seed sets BOTH pins on a
    collision code (ratify refuses a row with one), but the test checked only
    the pin the page split reads."""
    seed = _seed()
    seed[1]["program_account"] = None                    # DSS same_program: org pin only
    rows = _failures(_lake(seed=seed), "assert_p1_era_map_collision_pinned")
    assert [(r[0], r[2], r[5], r[6]) for r in rows] == [
        ("organization-collision code without a usable pin pair", "0300D-DSS-L21", None, "DCSA")]
    seed = _seed()
    seed[2].update(decision="history_only", program_org=None, ruling="R-DEC-ERA-B1")
    rows = _failures(_lake(seed=seed), "assert_p1_era_map_collision_pinned")
    assert [(r[0], r[2]) for r in rows] == [
        ("organization-collision code without a usable pin pair", "0300D-DTRA-L23")]


# ROADMAP #203: no fixture row exercised the account side. PB2026 prints '0145'
# under two Navy accounts (an account-collision code, like the ten live ones);
# the PB2019 era key prints it under 1506N.
ACCOUNT_LAKE = [
    ("P-1", 2026, "1506N", "N", "01", "0145", "Training Aircraft", "fy_2026_total", 1.0, "1", "0145", "Q7"),
    ("P-1", 2026, "1508N", "N", "01", "0145", "Training Ammunition", "fy_2026_total", 2.0, "1", "0145", "Q8"),
    ("P-1", 2019, "1506N", "N", "01", "1506N-N-L9", "Training Aircraft", "fy_2019_total", 3.0, "271", "0145",
     "AO900"),
]


def _account_seed_row(**pins):
    return _seed_row(decision_id="0145|1506N||2019-2019", line_item_code="0145", account="1506N",
                     first_edition="2019", last_edition="2019", decision="same_program", n_keys="1",
                     keys_sha256=keys_sha256([_key(2019, "1506N-N-L9", "01", "Training Aircraft")]),
                     ruling="R-DEC-ERA-B1", **pins)


def test_collision_pinned_checks_an_account_collision_code():
    lake = LAKE + ACCOUNT_LAKE
    clean = _account_seed_row(program_account="1506N", program_org="N")
    assert _failures(_lake(lake=lake, seed=_seed() + [clean]),
                     "assert_p1_era_map_collision_pinned") == []
    for pins in (dict(program_org="N"), dict(program_account="1506N"),
                 dict(program_account="1611N", program_org="N")):
        rows = _failures(_lake(lake=lake, seed=_seed() + [_account_seed_row(**pins)]),
                         "assert_p1_era_map_collision_pinned")
        assert [(r[0], r[2]) for r in rows] == [
            ("account-collision code without a usable pin pair", "1506N-N-L9")], pins


def test_collision_pinned_lets_a_history_only_chain_keep_its_own_organization():
```

In `tests/test_p1_era_line_map_sql.py` (:420), replace:

```python
def test_p1r_crosscheck_allow_list_must_stay_exact_on_the_real_corpus():
```

with:

```python
def test_p1r_crosscheck_pins_the_triple_count_once_all_seven_p1r_workbooks_are_registered():
    # ROADMAP #203: the count leg no test planted (1,650 on the real corpus).
    docs = DOCS + [(str(910 + ed), str(ed % 10) * 64, f"fy{ed}/dod/p1r_display.xlsx", str(ed))
                   for ed in (2017, 2018, 2020, 2021, 2022, 2023)]
    rows = _failures(_lake(docs=docs), "assert_p1_era_map_p1r_crosscheck")
    assert rows == [("era P-1R triple count differs from the full corpus (1,650): 1", None, None, None)]


def test_p1r_crosscheck_allow_list_must_stay_exact_on_the_real_corpus():
```

In `tests/jbooks/test_era_keys.py` (:69-72, class `TestEraKeyAnchor`), replace:

```python
    def test_non_era_keys_return_none(self):
        # R-1 PE codes, modern BLI codes, bare line numbers, era P-1R codes
        for v in ("0601101E", "7001SA1000", "70", "013005", "0300D", None, ""):
            assert era_key_anchor(v) is None
```

with:

```python
    def test_non_era_keys_return_none(self):
        # R-1 PE codes, modern BLI codes, bare line numbers, era P-1R codes
        for v in ("0601101E", "7001SA1000", "70", "013005", "0300D", None, ""):
            assert era_key_anchor(v) is None

    def test_a_trailing_newline_is_not_an_era_key(self):
        # ROADMAP #203: `$` matched before a final newline; `\Z` does not.
        assert is_era_procurement_key("0300D-DEFW-L1\n") is False
        assert era_key_anchor("0300D-DEFW-L1\n") is None
        assert is_era_procurement_key("0300D-DEFW-L1") is True
```

In `tests/test_dbt_build.py` (:5-7), replace:

```python
import duckdb

ROOT = Path(__file__).resolve().parents[1]
```

with:

```python
import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
```

Append to the end of `tests/test_dbt_build.py`:

```python


def test_ensure_lake_columns_leaves_no_temp_file_when_the_copy_fails(tmp_path, monkeypatch):
    """ROADMAP #203: a COPY that fails after it began writing left
    budget_lines.tmp.parquet beside the fixture parquet."""
    path = tmp_path / "budget_lines.parquet"
    duckdb.sql(f"copy (select 1 as a) to '{path}' (format parquet)")
    real_connect = duckdb.connect

    class FailingCopy:
        def __init__(self):
            self._con = real_connect()

        def execute(self, sql, *args):
            if sql.lstrip().lower().startswith("copy"):
                (tmp_path / "budget_lines.tmp.parquet").write_bytes(b"partial")
                raise duckdb.IOException("disk full")
            return self._con.execute(sql, *args)

        def close(self):
            self._con.close()

    monkeypatch.setattr(duckdb, "connect", FailingCopy)
    with pytest.raises(duckdb.IOException, match="disk full"):
        ensure_lake_columns(path, ("line_item_code",))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["budget_lines.parquet"]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_era_key_regex_sites.py tests/test_p1_era_line_map_sql.py tests/jbooks/test_era_keys.py "tests/test_dbt_build.py::test_ensure_lake_columns_leaves_no_temp_file_when_the_copy_fails" -q`
Expected: exactly seven failures — `test_every_site_spells_the_full_pattern`, `test_sql_and_python_agree_on_what_an_era_key_is`
(Python calls '0300D-DEFW-L1\n' an era key), `test_collision_pinned_fails_on_a_missing_or_foreign_pin` (old labels),
`test_collision_pinned_requires_both_pins`, `test_collision_pinned_checks_an_account_collision_code`,
`TestEraKeyAnchor::test_a_trailing_newline_is_not_an_era_key` and
`test_ensure_lake_columns_leaves_no_temp_file_when_the_copy_fails`. The two `test_complete_fails_on_a_map_key_…` tests,
the P-1R count test and `test_no_unlisted_site_spells_an_era_key_regex` pass already: they plant the defects the
existing legs catch (measured on a scratch overlay of `532205c9`, 2026-10-13).

- [ ] **Step 3: Implement**

Replace the prefix-only pattern at the ten sites with this script (it refuses any count other than the one measured):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . python - <<'EOF'
"""Task 9 Step: replace the prefix-only era-key regex with the full pattern at
the nine files (ten sites) that spell it, refusing any count that is not the
one measured on 2026-10-13."""
from pathlib import Path
import sys

ROOT = Path(".")
LOOSE = "'^[0-9]{4}[A-Z]-[A-Z]+-L'"
FULL = "'^[0-9]{4}[A-Z]-[A-Z]+-L[0-9][0-9A-Za-z-]*$'"
SITES = {
    "dbt/models/marts/p1_era_line_map.sql": 2,
    "dbt/models/marts/fct_program_decade_series.sql": 1,
    "dbt/models/marts/fct_book_diff.sql": 1,
    "dbt/tests/assert_p1_era_map_one_code.sql": 1,
    "dbt/tests/assert_book_diff_no_era_procurement.sql": 1,
    "dbt/tests/assert_program_decade_native_equals_line.sql": 1,
    "dbt/tests/assert_p1_era_map_complete.sql": 1,
    "src/govbudget/export_site.py": 1,
    "tests/test_program_decade_series_sql.py": 1,
}
for rel, n in SITES.items():
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    if text.count(LOOSE) != n:
        sys.exit(f"{rel}: {text.count(LOOSE)} prefix-only era-key regex(es), expected {n}")
    path.write_text(text.replace(LOOSE, FULL), encoding="utf-8")
    print(f"{rel}: {n} site(s) now spell {FULL}")
EOF
```
Expected: nine lines, `dbt/models/marts/p1_era_line_map.sql: 2 site(s) now spell '^[0-9]{4}[A-Z]-[A-Z]+-L[0-9][0-9A-Za-z-]*$'`
first, then one site each for the other eight files.

In `src/govbudget/jbooks/era_keys.py` (:68-69), replace:

```python
# including sub-line forms like WHS '46-1' (live PB2017 workbook evidence).
_ERA_KEY_RE = re.compile(r"^(\d{4}[A-Z])-([A-Z]+)-L([0-9][0-9A-Za-z-]*)$")
```

with:

```python
# including sub-line forms like WHS '46-1' (live PB2017 workbook evidence).
# `\Z`, not `$`: a Python `$` also matches before a final newline, which made
# '0300D-DEFW-L1\n' an era key (ROADMAP #203). The ten SQL sites spell the
# same pattern with an RE2 `$`, which is the end of the text;
# tests/test_era_key_regex_sites.py holds them and this one together.
_ERA_KEY_RE = re.compile(r"^(\d{4}[A-Z])-([A-Z]+)-L([0-9][0-9A-Za-z-]*)\Z")
```

Replace the whole of `dbt/tests/assert_p1_era_map_collision_pinned.sql` with:

```sql
-- Every carried era key on a PB2026 collision code is pinned to ONE side of
-- the collision (families piece 1, spec §4.3, §4.5 and §7; plan binding
-- decision 5: the seed sets BOTH pins — ROADMAP #203, follow-ups Task 9).
--
-- fct_program_decade_series splits a collision code's grain by account (10
-- codes) or organization ('20', '30', '500') exactly like fct_decade_series,
-- and for an era row it takes the seed's program_account / program_org, never
-- the era row's own values. So for every key whose decision carries points:
--   * on an account- or organization-collision code, program_account AND
--     program_org must both be set — and, for same_program, name a line
--     PB2026 prints under that code (the page the points join; the same test
--     `era-map ratify` applies before a batch is written); a history_only
--     pair only has to be set;
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
pb2026_lines as (
    select distinct pe_bli, account, organization
    from {{ ref('stg_budget_lines') }}
    where fiscal_year = 2026
      and title is not null
      and pe_bli <> '9999999999'
),
carried as (
    select edition, era_key, line_item_code, decision, program_account, program_org
    from {{ ref('p1_era_line_map') }}
    where decision in ('same_program', 'history_only')
)

select
    'account-collision code without a usable pin pair' as failure,
    c.edition, c.era_key, c.line_item_code, c.decision, c.program_account, c.program_org
from carried c
join collision_pes cp
  on cp.pe_bli = c.line_item_code
left join pb2026_lines l
  on l.pe_bli = c.line_item_code
 and l.account = c.program_account
 and l.organization = c.program_org
where c.program_account is null
   or c.program_org is null
   or (c.decision = 'same_program' and l.pe_bli is null)

union all

select
    'organization-collision code without a usable pin pair',
    c.edition, c.era_key, c.line_item_code, c.decision, c.program_account, c.program_org
from carried c
join org_collision_pes ocp
  on ocp.pe_bli = c.line_item_code
left join pb2026_lines l
  on l.pe_bli = c.line_item_code
 and l.account = c.program_account
 and l.organization = c.program_org
where c.program_account is null
   or c.program_org is null
   or (c.decision = 'same_program' and l.pe_bli is null)

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

In `tests/test_dbt_build.py` (:35-59, `ensure_lake_columns`), replace:

```python
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

with:

```python
    con = duckdb.connect()
    tmp = path.with_name(path.stem + ".tmp.parquet")
    try:
        have = {r[0] for r in con.execute(
            f"describe select * from read_parquet('{path}')").fetchall()}
        missing = [c for c in columns if c not in have]
        if not missing:
            return
        extra = ", ".join(f"null::varchar as {c}" for c in missing)
        try:
            con.execute(
                f"copy (select *, {extra} from read_parquet('{path}'))"
                f" to '{tmp}' (format parquet)"
            )
        except BaseException:
            # ROADMAP #203: never leave a partial budget_lines.tmp.parquet.
            tmp.unlink(missing_ok=True)
            raise
    finally:
        con.close()
    tmp.replace(path)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_era_key_regex_sites.py tests/test_p1_era_line_map_sql.py tests/jbooks/test_era_keys.py tests/test_dbt_build.py tests/test_program_decade_series_sql.py tests/test_verify_era_map.py tests/test_verify_era_map_def.py tests/test_export_era_line_map.py tests/test_explorer_era_map_preset.py -q`
Expected: no failures (`tests/test_dbt_build.py` runs the full fixture `dbt build`, which compiles every changed
model and test; on the scratch overlay all 8 of its tests passed).

- [ ] **Step 5: Re-check the hardened tests on the live lake, read-only**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
uv run --project . python - <<'EOF'
"""Read-only: the hardened singular tests, rendered with every ref() pointing at
the live warehouse (attached read_only), and the two era-key patterns counted
on staging and on fct_decade_series. Nothing is written."""
import os
import re
from pathlib import Path

import duckdb

con = duckdb.connect()
con.execute(f"attach '{os.environ['GOVBUDGET_DUCKDB']}' as live (read_only)")
for name in ("assert_p1_era_map_collision_pinned", "assert_p1_era_map_one_code",
             "assert_book_diff_no_era_procurement", "assert_program_decade_native_equals_line"):
    sql = Path(f"dbt/tests/{name}.sql").read_text()
    assert "source(" not in sql, name
    sql = re.sub(r"\{\{\s*ref\('([a-z0-9_]+)'\)\s*\}\}", r"live.main.\1", sql)
    print(f"{name}: {con.execute(f'select count(*) from ({sql})').fetchone()[0]} failing row(s)")
for label, rx in (("prefix-only", "^[0-9]{4}[A-Z]-[A-Z]+-L"),
                  ("full", "^[0-9]{4}[A-Z]-[A-Z]+-L[0-9][0-9A-Za-z-]*$")):
    n = con.execute("select count(*) from live.main.stg_budget_lines where regexp_matches(pe_bli, ?)", [rx]).fetchone()[0]
    m = con.execute("select count(*) from live.main.fct_decade_series where regexp_matches(pe_bli, ?)", [rx]).fetchone()[0]
    print(f"{label} era-key regex: stg_budget_lines {n:,} rows, fct_decade_series {m:,} rows")
EOF
```
Expected (measured 2026-10-13 on the overlay):

```
assert_p1_era_map_collision_pinned: 0 failing row(s)
assert_p1_era_map_one_code: 0 failing row(s)
assert_book_diff_no_era_procurement: 0 failing row(s)
assert_program_decade_native_equals_line: 0 failing row(s)
prefix-only era-key regex: stg_budget_lines 57,722 rows, fct_decade_series 20,781 rows
full era-key regex: stg_budget_lines 57,722 rows, fct_decade_series 20,781 rows
```
A failing row in the collision test means a live seed row carries one pin: stop and report it (piece-1 binding
decision 5 says ratify never writes one).

- [ ] **Step 6: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/tests/test_era_key_regex_sites.py GovBudget/dbt/models/marts/p1_era_line_map.sql GovBudget/dbt/models/marts/fct_program_decade_series.sql GovBudget/dbt/models/marts/fct_book_diff.sql GovBudget/dbt/tests/assert_p1_era_map_one_code.sql GovBudget/dbt/tests/assert_book_diff_no_era_procurement.sql GovBudget/dbt/tests/assert_program_decade_native_equals_line.sql GovBudget/dbt/tests/assert_p1_era_map_complete.sql GovBudget/dbt/tests/assert_p1_era_map_collision_pinned.sql GovBudget/src/govbudget/export_site.py GovBudget/src/govbudget/jbooks/era_keys.py GovBudget/tests/test_program_decade_series_sql.py GovBudget/tests/test_p1_era_line_map_sql.py GovBudget/tests/jbooks/test_era_keys.py GovBudget/tests/test_dbt_build.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "fix(era-map): one full era-key regex at every site, a strict end anchor in era_keys, both collision pins, the unplanted legs (#203)" -m "Ten SQL sites spell the full era-key pattern (57,722 = 57,722 staging rows live); _ERA_KEY_RE ends in a strict end anchor; collision_pinned requires both pins naming a PB2026 line; complete x2, P-1R count and an account-collision fixture planted; ensure_lake_columns leaves no temp file." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
