<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G2 (2026-10-13). -->

### Task 6: Route-safe seed, loader alias and the R-1 restatement rule (#194)

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §4.1 (where the skip fires), §4.2 (the seed `dbt/seeds/p1_route_safe_codes.csv`, `jbooks/route_safe_codes.py`, dbt test `assert_route_safe_codes_valid`), §4.3 (alias rows, the named rule `P1_R1_RESTATEMENTS`, `P1RestatementMismatch`, `UnsafeBudgetLineCode`, the rewritten loader test); §2.3's cross-review paragraph (the seed gains `exhibit_family`; `P1_R1_RESTATEMENTS` lives in `jbooks/route_safe_codes.py` as a mapping the loader and the exporter share; the rollup loader loads each edition's R-1 first; PB2025's CR column compares under `R1_AMOUNT_TYPE_EQUIVALENTS`). Owner decisions 2026-10-04 (ROADMAP "Follow-ups first", commits 53dff043 and 532205c9): Q1 (a) — the RDT&E line gets no page and is recorded as an R-1 restatement of 0708081D + 0708083D; Q2 — the O&M line's key is `0390DOM`, the printed code stays in `line_item_code`.

**Files:**
- Create: `src/govbudget/jbooks/route_safe_codes.py`
- Create: `dbt/seeds/p1_route_safe_codes.csv`
- Create: `dbt/tests/assert_route_safe_codes_valid.sql`
- Create: `tests/jbooks/test_route_safe_codes.py`
- Create: `tests/test_route_safe_codes_sql.py`
- Create: `tests/jbooks/test_p1_loader_route_safe.py`
- Create: `tests/jbooks/test_cli_rollup_order.py`
- Modify: `dbt/dbt_project.yml` — after the `p1_era_code_decisions` seed block (anchor on its last two lines `        ruling: varchar` / `        note: varchar`, about lines 47–48, the end of the file)
- Modify: `src/govbudget/jbooks/p1_loader.py` as Tasks 3 and 4a leave it — the `collections.abc` import (line 4); the `rollup_loader` import through the end of `_is_valid_pe_bli` (about lines 14–37); `class P1Parse` (about lines 89–94); the `parse_p1_rollup` signature (about line 133) and the `wb = load_workbook(` line after its docstring; the `skipped_invalid = 0` counter (about line 199); the row-skip block (anchor on `if not ids.get("pe_bli") and not classified:`); the era and modern branches (anchor on `elif era_line_keying:` and `pe_bli = str(ids.get("pe_bli")).strip()`); `codes[key] = code`; the `if skipped_invalid:` log through `rows.append(P1Row(` (after Task 3's `ROADMAP #202` tripwire); the `return P1Parse(` block; the body of `load_p1_rollup`
- Modify: `src/govbudget/cli.py` — `_jbooks_load_rollups`' document query (anchor on `"where exhibit_family='rollup' and status='downloaded'"`, about line 155)
- Modify: `tests/jbooks/test_p1_loader.py` — remove `test_p1_loader_skips_appropriation_section_header_rows` (about lines 312–349 before Task 3)
- Modify: `tests/jbooks/test_p1_loader_era.py` — the import block's last two lines; `SECTION_HEADER` (about lines 81–83); `test_parse_loads_classified_and_skips_footnote_and_section_header_rows` (about lines 114–121); the end of `test_parse_skips_a_blank_line_row_with_any_other_code` (about lines 146–147)

Line numbers are hints; anchor on the quoted text. Tasks 3 and 4a edit `p1_loader.py` first: Task 3 adds `class P1KeyConflict` before `_slug`, rewrites the grouping comment and inserts its tripwire block before `    if skipped_invalid:`; Task 4a imports `EraKeyConflict` from `era_keys` and deletes its class here. None of the blocks quoted below overlaps theirs.

**Interfaces:**
Consumes: Task 3 (`P1KeyConflict`, the tripwire on `sums`, which also covers the restated line's group — it is summed like any line and only split off when rows are built); Task 4a (`from govbudget.jbooks.era_keys import EraKeyConflict, era_procurement_key` in `p1_loader.py`; `era_map` imports nothing from `p1_loader`, so `route_safe_codes` must import neither `p1_loader` nor `psycopg`/`openpyxl`); Task 1's test cluster on 127.0.0.1:55432.
Produces (Tasks 7, 8, 12 and the release tasks read these):
- `govbudget.jbooks.route_safe_codes`: `SEED_COLUMNS = ("account", "line_item_code", "page_key", "exhibit_family", "decided_on", "decided_by", "note")`; `PAGE_KEY_RE`; `ROUTE_UNSAFE_CHARS = frozenset("&#/?%")`; `class UnsafeBudgetLineCode(ValueError)`; `class P1RestatementMismatch(ValueError)`; `@dataclass(frozen=True) RouteSafeCode(account, line_item_code, page_key, exhibit_family, decided_on: date, decided_by, note)`; `@dataclass(frozen=True) R1Restatement(title: str, program_elements: tuple[str, ...])`; `P1_R1_RESTATEMENTS: dict[tuple[str, str], R1Restatement] = {("0390D", "RDT&E"): R1Restatement("Chem Demilitarization - RDT&E", ("0708081D", "0708083D"))}`; `R1_AMOUNT_TYPE_EQUIVALENTS = {"fy_2024_pb_request_with_cr_adjustments": "fy_2024_pb_request_with_cr_amounts"}`; `is_route_safe_code(code) -> bool`; `default_seed_path() -> Path`; `read_route_safe_codes(path) -> dict[tuple[str, str], RouteSafeCode]` (validates, raises `ValueError`); `load_route_safe_codes()` (the committed seed, cached); `page_key(account, code, codes=None) -> str | None`; `by_page_key(codes=None) -> dict[str, RouteSafeCode]`; `restated_lines(account) -> list[dict]` (`[{"line_item_code", "title", "program_elements": [...]}]`).
- `dbt/seeds/p1_route_safe_codes.csv` (one row: `0390D,O&M,0390DOM,om,2026-10-04,owner,…`), the dbt seed `p1_route_safe_codes` (every column varchar) and the singular test `assert_route_safe_codes_valid`. The release's selective dbt build must load this seed before `p1_era_line_map` (Task 8 joins it).
- `p1_loader`: `P1Parse.restated: tuple[P1Row, ...]` replaces `P1Parse.skipped_invalid`; `parse_p1_rollup(xlsx_path, *, exhibit, fiscal_year, route_safe=None)` (alias rows carry `pe_bli = page key`, `line_item_code = printed code`; a `P1_R1_RESTATEMENTS` line goes to `restated`, never `rows`; any other route-unsafe code or era line number on an Add row raises `UnsafeBudgetLineCode`); `verify_r1_restatements(con, parsed) -> int` (rows checked; raises `P1RestatementMismatch`); `load_p1_rollup` calls it before `write_p1_rows`. `_INVALID_PE_BLI_CHARS` and `_is_valid_pe_bli` are gone.
- `cli._jbooks_load_rollups` loads documents `order by fiscal_year, R-1 first, id`.

Measured for this task (2026-10-13, read-only; workbooks in `data/raw_docs`, Postgres `govbudget` in read-only transactions):
- The route-unsafe rows of all 20 P-1/P-1R display workbooks (a scratch scan of the raw `Budget Line Item` / era `Line Number` / era P-1R `Line Item` cell with `_is_valid_pe_bli`): exactly two per PB2024–PB2026 P-1, all `Add` rows of account 0390D, org `A` — PB2024 rows 1137 `O&M` (BA 01) / 1138 `RDT&E` (BA 02), PB2025 rows 1190/1191, PB2026 rows 303/304 — and none in the other 17 workbooks.
- Postgres holds 16 of them: PB2024 ids 349016–349020 (`O&M`, five amount types) and 349021–349025 (`RDT&E`), PB2025 ids 47733–47735 and 47736–47738; `line_item_code` equals `pe_bli` on all 16. `0390DOM` is the pe_bli of no `budget_lines` row and of no `jbook_details` row in the lake (`select count(*) … where pe_bli='0390DOM'` → 0 and 0).
- The RDT&E line equals the R-1 sum of 0708081D + 0708083D (account 0390D, same edition) in all 12 PB2024–PB2026 columns: PB2024 1,026,665 / 975,206 / 0 / 975,206 / 1,002,560; PB2025 975,206 / 1,002,560 (P-1 `fy_2024_pb_request_with_cr_adjustments` against R-1 `fy_2024_pb_request_with_cr_amounts`) / 754,762; PB2026 1,002,560 / 754,762 / 210,039 / 210,039 (a scratch run of this task's parse and `verify_r1_restatements`, Step 10). The R-1 0390D account holds no other program element in those editions.
- Today's parse against Postgres (`scripts/era/s1_reload_era_p1.py --check --editions 2024 2025 2026`): PB2024 parse 4,575 / db 4,585, PB2025 2,426 / 2,432, PB2026 3,163 / 3,163; every shared key equal; the extra db rows are exactly the 16 above.
- On a scratch tree of HEAD plus Tasks 3, 4a and 4c, the test files below give: `tests/jbooks/test_route_safe_codes.py` 26 passed, `tests/test_route_safe_codes_sql.py` 6, `tests/jbooks/test_p1_loader_route_safe.py` 10, `tests/jbooks/test_cli_rollup_order.py` 1, `tests/jbooks/test_p1_loader.py` 14 (15 after Task 3, minus the removed test), `tests/jbooks/test_p1_loader_era.py` 14 (13 after Task 3, plus one); `tests/jbooks/test_s1_reload_era_p1.py` 13, `tests/jbooks/test_era_map.py` 51, `tests/jbooks/test_era_map_propose.py` 34 and `tests/jbooks/test_edition_probe.py` 24 stay green. With the new loader, `s1_reload_era_p1.py --check` on the seven era editions still prints `V1: CLEAN (7 editions, 58131 parsed rows)`.

- [ ] **Step 1: Write the failing seed tests**

Create `tests/jbooks/test_route_safe_codes.py`:

```python
"""jbooks/route_safe_codes.py — the owner-approved page keys for printed
codes a web address cannot carry, and the P-1 lines that restate R-1
program elements (families piece-1 follow-ups design §4.2–§4.3, #194;
owner decisions 2026-10-04: Q1 (a), Q2)."""
from datetime import date
from pathlib import Path

import pytest

from govbudget.export_site import is_route_safe_pe
from govbudget.jbooks import route_safe_codes as rsc
from govbudget.jbooks.route_safe_codes import (
    P1_R1_RESTATEMENTS,
    R1_AMOUNT_TYPE_EQUIVALENTS,
    SEED_COLUMNS,
    R1Restatement,
    RouteSafeCode,
    by_page_key,
    is_route_safe_code,
    load_route_safe_codes,
    page_key,
    read_route_safe_codes,
    restated_lines,
)

HEADER = ",".join(SEED_COLUMNS)
OM_ROW = '0390D,O&M,0390DOM,om,2026-10-04,owner,"a note, with a comma"'


def _seed(tmp_path: Path, *lines: str, header: str = HEADER) -> Path:
    p = tmp_path / "p1_route_safe_codes.csv"
    p.write_text("\n".join([header, *lines]) + "\n", encoding="utf-8")
    return p


def test_the_committed_seed_holds_exactly_the_owner_approved_o_and_m_key():
    codes = load_route_safe_codes()
    assert list(codes) == [("0390D", "O&M")]
    om = codes[("0390D", "O&M")]
    assert (om.page_key, om.exhibit_family, om.decided_on, om.decided_by) == (
        "0390DOM", "om", date(2026, 10, 4), "owner")
    assert om.line_item_code == "O&M" and om.account == "0390D"


def test_page_key_and_reverse_lookup():
    assert page_key("0390D", "O&M") == "0390DOM"
    assert page_key("0390D", "RDT&E") is None       # Q1 (a): no page
    assert page_key("2035A", "O&M") is None         # another account
    assert by_page_key()["0390DOM"].line_item_code == "O&M"


def test_the_rdte_line_is_a_recorded_r1_restatement():
    assert P1_R1_RESTATEMENTS == {
        ("0390D", "RDT&E"): R1Restatement(
            title="Chem Demilitarization - RDT&E",
            program_elements=("0708081D", "0708083D")),
    }
    assert R1_AMOUNT_TYPE_EQUIVALENTS == {
        "fy_2024_pb_request_with_cr_adjustments": "fy_2024_pb_request_with_cr_amounts"}
    assert restated_lines("0390D") == [{
        "line_item_code": "RDT&E", "title": "Chem Demilitarization - RDT&E",
        "program_elements": ["0708081D", "0708083D"]}]
    assert restated_lines("2035A") == []


@pytest.mark.parametrize("code", ["O&M", "RDT&E", "A/B", "A?B", "A%B", "A#B",
                                  "A B", "A\tB", "D15610", "0390DOM", "46-1"])
def test_route_safety_mirrors_the_exporter(code):
    assert is_route_safe_code(code) is is_route_safe_pe(code)


def test_a_valid_seed_reads_back(tmp_path):
    codes = read_route_safe_codes(_seed(tmp_path, OM_ROW))
    assert codes == {("0390D", "O&M"): RouteSafeCode(
        account="0390D", line_item_code="O&M", page_key="0390DOM",
        exhibit_family="om", decided_on=date(2026, 10, 4), decided_by="owner",
        note="a note, with a comma")}


@pytest.mark.parametrize("lines, header, match", [
    ([OM_ROW], "account,line_item_code,page_key", "header"),
    (["0390D,O&M,0390-DOM,om,2026-10-04,owner,"], HEADER, r"is not \[A-Z0-9\]\+"),
    (["0390D,O&M,0390dom,om,2026-10-04,owner,"], HEADER, r"is not \[A-Z0-9\]\+"),
    ([OM_ROW, "0390D,A/B,0390DOM,om,2026-10-04,owner,"], HEADER, "repeats"),
    (["0390D,PROC,0390DPROC,om,2026-10-04,owner,"], HEADER, "already route-safe"),
    ([OM_ROW, "0390D,O&M,0390DOM2,om,2026-10-04,owner,"], HEADER, "repeats"),
    (["0390D,RDT&E,0390DRDTE,rdte,2026-10-04,owner,"], HEADER, "R-1 restatement"),
    (["0390D,O&M,0390DOM,,2026-10-04,owner,"], HEADER, "exhibit_family is blank"),
    (["0390D,O&M,0390DOM,om,04/10/2026,owner,"], HEADER, "not an ISO date"),
    (["0390D,O&M,0390DOM,om,2026-10-04,claude,"], HEADER, "not 'owner'"),
])
def test_a_bad_seed_is_refused(tmp_path, lines, header, match):
    with pytest.raises(ValueError, match=match):
        read_route_safe_codes(_seed(tmp_path, *lines, header=header))


def test_the_default_path_is_the_dbt_seed():
    assert rsc.default_seed_path().parts[-3:] == ("dbt", "seeds", "p1_route_safe_codes.csv")
```

Create `tests/test_route_safe_codes_sql.py`:

```python
"""dbt/tests/assert_route_safe_codes_valid.sql on a hand-built lake (families
piece-1 follow-ups design §4.2, #194): the committed seed passes on the
post-write shape (the 0390DOM alias rows print O&M under 0390D), and every
defect the test exists for fails it."""
import csv

import duckdb
import pytest
from dbt_render import ROOT, render_dbt_sql

from govbudget.jbooks.route_safe_codes import SEED_COLUMNS

TEST = "dbt/tests/assert_route_safe_codes_valid.sql"
SEED = ROOT / "dbt" / "seeds" / "p1_route_safe_codes.csv"

# (exhibit, fiscal_year, account, pe_bli, line_item_code)
LINES = [
    ("P-1", 2026, "0390D", "0390DOM", "O&M"),
    ("P-1", 2024, "0390D", "0390DOM", "O&M"),
    ("P-1", 2019, "0390D", "0390D-ARMY-L1", "O&M"),
    ("R-1", 2026, "0390D", "0708083D", None),
    ("P-1", 2026, "0300D", "7001SA1000", "7001SA1000"),
]
DETAILS = [("0708083D",), ("7001SA1000",)]


def _committed_seed() -> list[dict]:
    with open(SEED, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _failures(lines=LINES, details=DETAILS, seed=None) -> list[tuple]:
    con = duckdb.connect()
    con.execute("create table stg_budget_lines (exhibit varchar, fiscal_year integer,"
                " account varchar, pe_bli varchar, line_item_code varchar)")
    con.executemany("insert into stg_budget_lines values (?, ?, ?, ?, ?)", lines)
    con.execute("create table stg_budget_details (pe_bli varchar)")
    con.executemany("insert into stg_budget_details values (?)", details)
    con.execute("create table p1_route_safe_codes ("
                + ", ".join(f"{c} varchar" for c in SEED_COLUMNS) + ")")
    for row in (_committed_seed() if seed is None else seed):
        con.execute(f"insert into p1_route_safe_codes values ({', '.join('?' * len(SEED_COLUMNS))})",
                    [row[c] for c in SEED_COLUMNS])
    return con.execute(render_dbt_sql(TEST)).fetchall()


def test_the_committed_seed_passes_on_the_post_write_lake():
    assert _failures() == []


def _row(**changes):
    row = dict(_committed_seed()[0])
    row.update(changes)
    return row


OTHER_CODE = "page_key is the pe_bli of a budget_lines row of another code"


@pytest.mark.parametrize("lines, details, seed, failures", [
    # the second row names another code, so the alias rows fail it as well
    (LINES, DETAILS, [_row(), _row(line_item_code="A/B")],
     {"page_key repeats in the seed", OTHER_CODE}),
    (LINES, DETAILS, [_row(page_key="0390D-OM")], {"page_key is not [A-Z0-9]+"}),
    (LINES + [("P-1", 2026, "0300D", "0390DOM", "0390DOM")], DETAILS, None, {OTHER_CODE}),
    (LINES + [("P-1", 2025, "0390D", "0390DOM", "RDT&E")], DETAILS, None, {OTHER_CODE}),
    (LINES, DETAILS + [("0390DOM",)], None, {"page_key is the pe_bli of a J-book detail row"}),
])
def test_each_defect_fails(lines, details, seed, failures):
    assert {r[0] for r in _failures(lines, details, seed)} == failures
```

- [ ] **Step 2: Run them to see them fail**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_route_safe_codes.py tests/test_route_safe_codes_sql.py -q 2>&1 | tail -4
```

Expected: `2 errors` during collection — `ImportError: cannot import name 'route_safe_codes' from 'govbudget.jbooks'` and `ModuleNotFoundError: No module named 'govbudget.jbooks.route_safe_codes'`.

- [ ] **Step 3: Write the module, the seed, its dbt config and the dbt test**

Create `src/govbudget/jbooks/route_safe_codes.py`:

```python
"""Route-safe page keys for printed budget line codes a web address cannot
carry, and the P-1 lines that restate R-1 program elements (#194).

Families piece-1 follow-ups design §4.2–§4.3 (owner decisions 2026-10-04:
Q1 (a), Q2, Q8). A program page is a static route, so its key must survive a
URL path segment: no '&', '#', '/', '?', '%' or whitespace
(export_site.is_route_safe_pe applies the same rule to the page universe).
Two real PB2024–PB2026 P-1 lines of account 0390D (Chemical Agents and
Munitions Destruction, Defense) print exactly such codes:

  * 'O&M' ("Chem Demilitarization - O&M") loads under the owner-approved page
    key in dbt/seeds/p1_route_safe_codes.csv (0390DOM). budget_lines.pe_bli
    is the page key; budget_lines.line_item_code keeps the printed code.
  * 'RDT&E' ("Chem Demilitarization - RDT&E") equals R-1 program elements
    0708081D + 0708083D in every column of every edition, so loading it would
    count those dollars twice. P1_R1_RESTATEMENTS records it; the loader
    skips it only after checking it still equals that R-1 sum
    (p1_loader.verify_r1_restatements), and never gives it a page.

Any other route-unsafe code raises UnsafeBudgetLineCode: it is never skipped
silently again (the 2026-07-05 guard treated these two real lines as junk).

The seed is read here for Python (the loader, era_map, the exporter and the
receipt matcher) and by dbt as the seed table p1_route_safe_codes
(p1_era_line_map, assert_route_safe_codes_valid).
"""
from __future__ import annotations

import csv
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

SEED_COLUMNS = (
    "account", "line_item_code", "page_key", "exhibit_family",
    "decided_on", "decided_by", "note",
)
PAGE_KEY_RE = re.compile(r"[A-Z0-9]+")
# The exporter's route-safety character set (export_site.is_route_safe_pe).
ROUTE_UNSAFE_CHARS = frozenset("&#/?%")


class UnsafeBudgetLineCode(ValueError):
    """A workbook row prints a budget line code (or era line number) that a
    web address cannot carry, and neither the route-safe seed nor
    P1_R1_RESTATEMENTS names it. The loader refuses rather than skip a real
    line in silence."""


class P1RestatementMismatch(ValueError):
    """A P-1 line P1_R1_RESTATEMENTS names no longer equals the R-1 program
    elements it restates (or that R-1 is not loaded), so skipping it could
    drop real money. The loader refuses; re-measure the line before changing
    the rule."""


@dataclass(frozen=True)
class RouteSafeCode:
    """One owner-approved page key for a printed code under one account."""

    account: str
    line_item_code: str
    page_key: str
    exhibit_family: str
    decided_on: date
    decided_by: str
    note: str


@dataclass(frozen=True)
class R1Restatement:
    """A P-1 line that prints the same dollars as these R-1 program elements."""

    title: str
    program_elements: tuple[str, ...]


# (account, printed code) -> what the P-1 line restates. Measured 2026-10-04
# and re-measured 2026-10-13 (read-only, data/raw_docs/fy202{4,5,6}/dod/
# p1_display.xlsx rows 1138 / 1191 / 304 against the loaded R-1): every
# column of every PB2024–PB2026 edition matches to the thousand
# (PB2026: 1,002,560 / 754,762 / 210,039 / 210,039).
P1_R1_RESTATEMENTS: dict[tuple[str, str], R1Restatement] = {
    ("0390D", "RDT&E"): R1Restatement(
        title="Chem Demilitarization - RDT&E",
        program_elements=("0708081D", "0708083D"),
    ),
}

# A P-1 amount column whose R-1 twin is slugged differently. PB2025's P-1
# prints 'FY 2024 PB Request with CR Adjustments' where its R-1 prints
# 'FY 2024 PB Request with CR Amounts'.
R1_AMOUNT_TYPE_EQUIVALENTS: dict[str, str] = {
    "fy_2024_pb_request_with_cr_adjustments": "fy_2024_pb_request_with_cr_amounts",
}


def is_route_safe_code(code: str) -> bool:
    """True when a code can be a page key: no '&#/?%' and no whitespace."""
    return not (set(code) & ROUTE_UNSAFE_CHARS or any(c.isspace() for c in code))


def default_seed_path() -> Path:
    from govbudget import config

    return config.ROOT / "dbt" / "seeds" / "p1_route_safe_codes.csv"


def read_route_safe_codes(path: Path) -> dict[tuple[str, str], RouteSafeCode]:
    """{(account, printed code): RouteSafeCode} from a seed file, validated.

    Raises ValueError on a header other than SEED_COLUMNS, a page key that is
    not [A-Z0-9]+ or repeats, a printed code that is already route-safe, a
    repeated (account, code), a pair P1_R1_RESTATEMENTS also names, a blank
    exhibit_family, a decided_on that is not an ISO date, or decided_by other
    than 'owner'."""
    path = Path(path)
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != SEED_COLUMNS:
            raise ValueError(f"{path}: header {reader.fieldnames} != {list(SEED_COLUMNS)}")
        rows = list(reader)
    out: dict[tuple[str, str], RouteSafeCode] = {}
    keys: set[str] = set()
    for n, r in enumerate(rows, start=2):
        where = f"{path.name} line {n}"
        pair = (r["account"], r["line_item_code"])
        if not PAGE_KEY_RE.fullmatch(r["page_key"]):
            raise ValueError(f"{where}: page_key {r['page_key']!r} is not [A-Z0-9]+")
        if r["page_key"] in keys:
            raise ValueError(f"{where}: page_key {r['page_key']!r} repeats")
        if is_route_safe_code(r["line_item_code"]):
            raise ValueError(f"{where}: {r['line_item_code']!r} is already route-safe;"
                             " only a code a web address cannot carry gets a page key")
        if pair in out:
            raise ValueError(f"{where}: {pair} repeats")
        if pair in P1_R1_RESTATEMENTS:
            raise ValueError(f"{where}: {pair} is an R-1 restatement and gets no page")
        if not r["exhibit_family"].strip():
            raise ValueError(f"{where}: exhibit_family is blank")
        try:
            decided_on = date.fromisoformat(r["decided_on"])
        except ValueError as exc:
            raise ValueError(f"{where}: decided_on {r['decided_on']!r} is not an ISO date") from exc
        if r["decided_by"] != "owner":
            raise ValueError(f"{where}: decided_by {r['decided_by']!r} is not 'owner'")
        keys.add(r["page_key"])
        out[pair] = RouteSafeCode(
            account=r["account"], line_item_code=r["line_item_code"],
            page_key=r["page_key"], exhibit_family=r["exhibit_family"],
            decided_on=decided_on, decided_by=r["decided_by"], note=r["note"],
        )
    return out


@lru_cache(maxsize=1)
def load_route_safe_codes() -> dict[tuple[str, str], RouteSafeCode]:
    """The committed seed, read once per process."""
    return read_route_safe_codes(default_seed_path())


def page_key(account: str, code: str,
             codes: Mapping[tuple[str, str], RouteSafeCode] | None = None) -> str | None:
    """The page key the seed gives (account, printed code), or None."""
    hit = (load_route_safe_codes() if codes is None else codes).get((account, code))
    return hit.page_key if hit else None


def by_page_key(codes: Mapping[tuple[str, str], RouteSafeCode] | None = None,
                ) -> dict[str, RouteSafeCode]:
    """{page_key: RouteSafeCode}."""
    return {c.page_key: c for c in (load_route_safe_codes() if codes is None else codes).values()}


def restated_lines(account: str) -> list[dict]:
    """The P1_R1_RESTATEMENTS entries of one account, in code order, as the
    exporter publishes them on that account's alias page."""
    return [
        {"line_item_code": code, "title": rule.title,
         "program_elements": list(rule.program_elements)}
        for (acct, code), rule in sorted(P1_R1_RESTATEMENTS.items())
        if acct == account
    ]
```

Create `dbt/seeds/p1_route_safe_codes.csv` (the owner approved the key 0390DOM on 2026-10-04, design Q2; `exhibit_family` is the §2.3 cross-review column the exporter reads in Task 12):

```csv
account,line_item_code,page_key,exhibit_family,decided_on,decided_by,note
0390D,O&M,0390DOM,om,2026-10-04,owner,"#194 (owner Q2, 2026-10-04): the P-1 prints Chem Demilitarization - O&M under the code O&M; a web address cannot carry the '&', so its pe_bli and page key are 0390DOM and line_item_code keeps O&M"
```

In `dbt/dbt_project.yml` (the end of the `p1_era_code_decisions` seed block, about lines 47–48; every column varchar so dbt never re-types `decided_on` or a numeric-looking key), replace:

```yaml
        ruling: varchar
        note: varchar
```

with:

```yaml
        ruling: varchar
        note: varchar
    p1_route_safe_codes:
      +column_types:
        account: varchar
        line_item_code: varchar
        page_key: varchar
        exhibit_family: varchar
        decided_on: varchar
        decided_by: varchar
        note: varchar
```

Create `dbt/tests/assert_route_safe_codes_valid.sql`:

```sql
-- p1_route_safe_codes (families piece-1 follow-ups design §4.2, #194): every
-- owner-approved page key is a usable, unique address that names exactly one
-- printed code.
--   * page_key repeats in the seed;
--   * page_key is not [A-Z0-9]+ (it must pass the llms.txt /program/ pattern
--     and the receipts grammar, and survive a URL path segment);
--   * page_key is the pe_bli of a budget_lines row that does not print the
--     seed's code under the seed's account (the alias rows themselves print
--     it: pe_bli 0390DOM, line_item_code 'O&M', account 0390D);
--   * page_key is the pe_bli of a J-book detail row (no R-2/P-40 line may
--     share an alias's address).
with codes as (
    select account, line_item_code, page_key
    from {{ ref('p1_route_safe_codes') }}
)

select 'page_key repeats in the seed' as failure, page_key, null as pe_bli, count(*) as n
from codes
group by page_key
having count(*) > 1

union all

select 'page_key is not [A-Z0-9]+', page_key, null, 1
from codes
where not regexp_matches(page_key, '^[A-Z0-9]+$')

union all

select 'page_key is the pe_bli of a budget_lines row of another code', c.page_key, b.pe_bli, count(*)
from codes c
join {{ ref('stg_budget_lines') }} b
  on b.pe_bli = c.page_key
where b.account is distinct from c.account
   or b.line_item_code is distinct from c.line_item_code
group by c.page_key, b.pe_bli

union all

select 'page_key is the pe_bli of a J-book detail row', c.page_key, d.pe_bli, count(*)
from codes c
join {{ ref('stg_budget_details') }} d
  on d.pe_bli = c.page_key
group by c.page_key, d.pe_bli
```

- [ ] **Step 4: Run the seed tests — they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_route_safe_codes.py tests/test_route_safe_codes_sql.py -q 2>&1 | tail -1
```

Expected: `32 passed` (26 + 6).

- [ ] **Step 5: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/jbooks/route_safe_codes.py GovBudget/dbt/seeds/p1_route_safe_codes.csv GovBudget/dbt/dbt_project.yml GovBudget/dbt/tests/assert_route_safe_codes_valid.sql GovBudget/tests/jbooks/test_route_safe_codes.py GovBudget/tests/test_route_safe_codes_sql.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(jbooks): route-safe page keys (0390D O&M -> 0390DOM) and the R-1 restatement rule for 0390D RDT&E; dbt seed and assert_route_safe_codes_valid (#194)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `6 files changed`.

- [ ] **Step 6: Write the failing loader tests**

Create `tests/jbooks/test_p1_loader_route_safe.py`:

```python
"""The P-1 loader on 0390D's Chem Demilitarization lines (families piece-1
follow-ups design §4.3, #194; owner decisions 2026-10-04: Q1 (a), Q2).

The rows copy data/raw_docs/fy2026/dod/p1_display.xlsx rows 303-304 (read
2026-10-13): O&M 87,404 / 20,745 / 3,243 and RDT&E 1,002,560 / 754,762 /
210,039 in the FY2024 actuals, FY2025 enacted and FY2026 discretionary
request columns. O&M loads under its route-safe key 0390DOM with the printed
code kept in line_item_code; RDT&E restates R-1 program elements 0708081D +
0708083D (live budget_lines ids 1031-1035) and is checked against them, then
left out; any other code a web address cannot carry raises.
"""
import re
from decimal import Decimal

import psycopg
import pytest
from openpyxl import Workbook

from govbudget.jbooks.p1_loader import load_p1_rollup, parse_p1_rollup, verify_r1_restatements
from govbudget.jbooks.route_safe_codes import P1RestatementMismatch, UnsafeBudgetLineCode
from jbooks.test_p1_loader import P1_HEADERS

CHEM_DEMIL_OM = ["0390D", "Chemical Agents and Munitions Destruction, Defense", "A", "01",
                 "Operation and maintenance", "1", "", "", "O&M", "Chem Demilitarization - O&M",
                 "A", "Weapon System Cost", "Add", "", 87404, "", 20745, "", 3243]
CHEM_DEMIL_RDTE = ["0390D", "Chemical Agents and Munitions Destruction, Defense", "A", "02",
                   "Research, Development, Test, and Evaluation", "2", "", "", "RDT&E",
                   "Chem Demilitarization - RDT&E", "A", "Weapon System Cost", "Add",
                   "", 1002560, "", 754762, "", 210039]
REAL_BLI = ["2035A", "Other Procurement, Army", "A", "02", "Comm", "10", "1", "A", "BZ7015",
            "Handheld Manpack", "A", "Weapon System Cost", "Add", "", 114329, "", 98000, "", 105500]
# PB2026 R-1 rows of 0390D in the three columns above
R1_ROWS = [("0708081D", "fy_2024_actuals", 2093), ("0708083D", "fy_2024_actuals", 1000467),
           ("0708083D", "fy_2025_enacted", 754762), ("0708083D", "fy_2026_disc_request", 210039)]


def _xlsx(tmp_path, *rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Exhibit P-1"
    ws.append(["Total of Displayed Rows"])
    ws.append(P1_HEADERS)
    for r in rows or (CHEM_DEMIL_OM, CHEM_DEMIL_RDTE, REAL_BLI):
        ws.append(r)
    p = tmp_path / "p1_display.xlsx"
    wb.save(p)
    return p


def _load_r1(pg_dsn, doc_id, rows=R1_ROWS):
    with psycopg.connect(pg_dsn) as con:
        for pe, at, amt in rows:
            con.execute(
                "insert into budget_lines (exhibit, fiscal_year, account, organization,"
                " budget_activity, pe_bli, title, amount_type, amount_thousands,"
                " source_document_id) values ('R-1', 2026, '0390D', 'A', '02', %s, 'x',"
                " %s, %s, %s)", (pe, at, amt, doc_id))


def _p1_rows(pg_dsn):
    with psycopg.connect(pg_dsn) as con:
        return con.execute(
            "select pe_bli, line_item_code, title, amount_type, amount_thousands"
            " from budget_lines where exhibit = 'P-1' order by pe_bli, amount_type"
        ).fetchall()


def test_the_o_and_m_line_loads_under_its_route_safe_key(pg_dsn, tmp_path, doc_id):
    _load_r1(pg_dsn, doc_id)
    n = load_p1_rollup(pg_dsn, _xlsx(tmp_path), exhibit="P-1", fiscal_year=2026,
                       source_document_id=doc_id)
    assert n == 6       # O&M's three FY columns + the real BLI's three
    rows = _p1_rows(pg_dsn)
    assert [r for r in rows if r[0] == "0390DOM"] == [
        ("0390DOM", "O&M", "Chem Demilitarization - O&M", "fy_2024_actuals", Decimal("87404")),
        ("0390DOM", "O&M", "Chem Demilitarization - O&M", "fy_2025_enacted", Decimal("20745")),
        ("0390DOM", "O&M", "Chem Demilitarization - O&M", "fy_2026_disc_request", Decimal("3243")),
    ]
    assert {r[0] for r in rows} == {"0390DOM", "BZ7015"}   # no 'O&M', no 'RDT&E'


def test_the_rdte_line_is_checked_against_the_r1_and_left_out(pg_dsn, tmp_path, doc_id):
    _load_r1(pg_dsn, doc_id)
    parsed = parse_p1_rollup(_xlsx(tmp_path), exhibit="P-1", fiscal_year=2026)
    assert sorted((r.pe_bli, r.line_item_code, r.amount_type, r.amount_thousands)
                  for r in parsed.restated) == [
        ("RDT&E", "RDT&E", "fy_2024_actuals", Decimal("1002560")),
        ("RDT&E", "RDT&E", "fy_2025_enacted", Decimal("754762")),
        ("RDT&E", "RDT&E", "fy_2026_disc_request", Decimal("210039")),
    ]
    assert all(r.pe_bli != "RDT&E" for r in parsed.rows)
    with psycopg.connect(pg_dsn) as con:
        assert verify_r1_restatements(con, parsed) == 3


def test_a_restatement_that_no_longer_matches_the_r1_refuses(pg_dsn, tmp_path, doc_id):
    _load_r1(pg_dsn, doc_id, [r if r[1] != "fy_2026_disc_request" else (r[0], r[1], 210038)
                              for r in R1_ROWS])
    with pytest.raises(P1RestatementMismatch,
                       match="fy_2026_disc_request = 210039 but R-1 0708081D [+] 0708083D"):
        load_p1_rollup(pg_dsn, _xlsx(tmp_path), exhibit="P-1", fiscal_year=2026,
                       source_document_id=doc_id)
    assert _p1_rows(pg_dsn) == []


def test_a_restatement_whose_r1_is_not_loaded_refuses(pg_dsn, tmp_path, doc_id):
    with pytest.raises(P1RestatementMismatch, match="load the edition's R-1 before its P-1"):
        load_p1_rollup(pg_dsn, _xlsx(tmp_path), exhibit="P-1", fiscal_year=2026,
                       source_document_id=doc_id)
    assert _p1_rows(pg_dsn) == []


def test_a_restatement_printed_under_another_title_refuses(pg_dsn, tmp_path, doc_id):
    _load_r1(pg_dsn, doc_id)
    renamed = CHEM_DEMIL_RDTE[:9] + ["Chem Demil RDT&E"] + CHEM_DEMIL_RDTE[10:]
    with pytest.raises(P1RestatementMismatch, match="not 'Chem Demilitarization - RDT&E'"):
        load_p1_rollup(pg_dsn, _xlsx(tmp_path, CHEM_DEMIL_OM, renamed), exhibit="P-1",
                       fiscal_year=2026, source_document_id=doc_id)


@pytest.mark.parametrize("account, code", [("2035A", "A/B"), ("2035A", "O&M"),
                                           ("0390D", "PROC #2"), ("0390D", "RDT&E/O&M")])
def test_any_other_route_unsafe_code_raises(tmp_path, account, code):
    # A page key belongs to one (account, code): O&M under 2035A has none.
    row = [account] + CHEM_DEMIL_OM[1:8] + [code] + CHEM_DEMIL_OM[9:]
    with pytest.raises(UnsafeBudgetLineCode, match=f"{account} prints {re.escape(repr(code))}"):
        parse_p1_rollup(_xlsx(tmp_path, row), exhibit="P-1", fiscal_year=2026)


def test_a_route_unsafe_non_add_row_is_ignored(tmp_path):
    memo = CHEM_DEMIL_OM[:8] + ["A/B"] + CHEM_DEMIL_OM[9:12] + ["Non-Add"] + CHEM_DEMIL_OM[13:]
    parsed = parse_p1_rollup(_xlsx(tmp_path, REAL_BLI, memo), exhibit="P-1", fiscal_year=2026)
    assert {r.pe_bli for r in parsed.rows} == {"BZ7015"}
    assert parsed.restated == ()
```

Create `tests/jbooks/test_cli_rollup_order.py`:

```python
"""cli._jbooks_load_rollups loads each edition's R-1 before its P-1 and P-1R
(families piece-1 follow-ups design §4.3, #194): the P-1 loader checks the
line it records as an R-1 restatement against the loaded R-1, so the R-1
must already be in budget_lines."""
import psycopg

from govbudget import cli, config
from govbudget.jbooks import p1_loader, rollup_loader


def test_r1_loads_before_p1_within_each_edition(pg_dsn, monkeypatch):
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        # registered P-1 first, so table order alone would load it first
        for fy, title in ((2026, "p1_display.xlsx"), (2026, "p1r_display.xlsx"),
                          (2025, "p1_display.xlsx"), (2026, "r1_display.xlsx"),
                          (2025, "r1_display.xlsx")):
            con.execute(
                "insert into jbook_documents (org, exhibit_family, fiscal_year, title,"
                " source_url, file_path, status) values ('DoD', 'rollup', %s, %s,"
                " %s, %s, 'downloaded')",
                (fy, title, f"https://example.test/fy{fy}/{title}", f"/x/fy{fy}/{title}"))
    calls = []
    monkeypatch.setattr(config, "PG_DSN", pg_dsn)
    monkeypatch.setattr(rollup_loader, "load_rollup",
                        lambda dsn, path, *, exhibit, fiscal_year, source_document_id:
                        calls.append((fiscal_year, exhibit)) or 1)
    monkeypatch.setattr(p1_loader, "load_p1_rollup",
                        lambda dsn, path, *, exhibit, fiscal_year, source_document_id:
                        calls.append((fiscal_year, exhibit)) or 1)
    loaded, failures = cli._jbooks_load_rollups()
    assert (loaded, failures) == (5, [])
    assert calls == [(2025, "R-1"), (2025, "P-1"), (2026, "R-1"), (2026, "P-1"),
                     (2026, "P-1R")]
```

In `tests/jbooks/test_p1_loader.py` (about lines 312–349 at HEAD; Task 3 does not touch it), replace:

```python
def test_p1_loader_skips_appropriation_section_header_rows(pg_dsn, tmp_path, doc_id):
    """Army P-1 appropriation SECTION-HEADER rows carry an appropriation label
    ('RDT&E', 'O&M', …) in the BLI cell instead of a real Budget Line Item.
    Those are not program elements — the '&' also breaks the /program/[peBli]
    static route — so the loader must reject them at the pe_bli guard, NOT
    insert a junk budget_lines row. A genuine alphanumeric BLI on the same
    sheet still loads."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Exhibit P-1"
    ws.append(["Total of Displayed Rows"])
    ws.append(P1_HEADERS)
    # Section-header rows: the 'Budget Line Item' cell is an appropriation
    # label. Both must be skipped (any FY amount they carry is a section total).
    ws.append(["0390D", "RDT&E, Defense-Wide", "A", "", "",
               "", "", "A", "RDT&E", "RDT&E Total",
               "A", "Weapon System Cost", "Add", "", 1002560, "", 754762, "", 210039])
    ws.append(["0390D", "O&M, Defense-Wide", "A", "", "",
               "", "", "A", "O&M", "O&M Total",
               "A", "Weapon System Cost", "Add", "", 87404, "", 20745, "", 3243])
    # A genuine BLI on the same sheet must survive.
    ws.append(["2035A", "Other Procurement, Army", "A", "02", "Comm",
               "10", "1", "A", "BZ7015", "Handheld Manpack",
               "A", "Weapon System Cost", "Add", "", 114329, "", 98000, "", 105500])
    p = tmp_path / "p1_section_headers.xlsx"
    wb.save(p)

    n = load_p1_rollup(pg_dsn, p, exhibit="P-1", fiscal_year=2026, source_document_id=doc_id)
    # Only the real BLI's three FY amount columns load; the two label rows are skipped.
    assert n == 3
    with psycopg.connect(pg_dsn) as con:
        junk = con.execute(
            "select count(*) from budget_lines where pe_bli in ('RDT&E', 'O&M')"
        ).fetchone()[0]
        real = con.execute(
            "select count(*) from budget_lines where pe_bli = 'BZ7015'"
        ).fetchone()[0]
    assert junk == 0, "appropriation-label rows must never insert budget_lines"
    assert real == 3, "the genuine alphanumeric BLI must still load"
```

with:

```python
# Corrected (#194, owner decisions 2026-10-04): test_p1_loader_skips_
# appropriation_section_header_rows stood here. It fed the loader 0390D's two
# Chem Demilitarization lines as "section totals" and required both dropped.
# They are real P-1 lines (PB2026 rows 303-304): O&M loads under its route-
# safe key 0390DOM, and RDT&E, which restates R-1 PEs 0708081D + 0708083D, is
# checked against that R-1 and left out. tests/jbooks/test_p1_loader_route_safe.py
# holds the tests that replace it.
```

In `tests/jbooks/test_p1_loader_era.py` (the end of the `p1_loader` import block, which Task 3 extends with `P1KeyConflict`), replace:

```python
    write_p1_rows,
)
```

with:

```python
    write_p1_rows,
)
from govbudget.jbooks.route_safe_codes import UnsafeBudgetLineCode
```

and replace:

```python
# Section header: an appropriation label in the line slot (the guard's '&').
SECTION_HEADER = _row(("0390D", "RDT&E, Defense-Wide"), "DW", "", "", "RDT&E",
                      "RDT&E", "RDT&E Total", "A", "Add", 1002560, 754762)
```

with:

```python
# A route-unsafe value in the era line slot. No PB2017-PB2023 P-1 or P-1R
# workbook prints one (all 14, measured 2026-10-13); since #194 the loader
# raises on it instead of skipping it as a "section header".
UNSAFE_LINE = _row(("0390D", "RDT&E, Defense-Wide"), "DW", "", "", "RDT&E",
                   "RDT&E", "RDT&E Total", "A", "Add", 1002560, 754762)
```

and replace:

```python
def test_parse_loads_classified_and_skips_footnote_and_section_header_rows(tmp_path):
    """S1b: the blank-line Classified Programs row loads under its printed
    code, as modern editions load it; footnotes and the section header
    (blank or label Line Number, no classified code) stay skipped."""
    rows = ADVANCE_PROCUREMENT_PAIR[:1] + [CLASSIFIED, SECTION_HEADER] + FOOTNOTES
    parsed = parse_p1_rollup(make_era_xlsx(tmp_path, rows), exhibit="P-1", fiscal_year=2021)
    assert {r.pe_bli for r in parsed.rows} == {"1506N-N-L1", "9999999999"}
    assert parsed.skipped_invalid == 1  # the 'RDT&E' label row
```

with:

```python
def test_parse_loads_classified_and_skips_footnote_rows(tmp_path):
    """S1b: the blank-line Classified Programs row loads under its printed
    code, as modern editions load it; footnotes (blank Line Number, no
    classified code) stay skipped. Corrected (#194, owner decisions
    2026-10-04): this test also fed a 'RDT&E' line-slot row and required it
    skipped; such a row now raises (test_parse_raises_on_a_route_unsafe_era_line)."""
    rows = ADVANCE_PROCUREMENT_PAIR[:1] + [CLASSIFIED] + FOOTNOTES
    parsed = parse_p1_rollup(make_era_xlsx(tmp_path, rows), exhibit="P-1", fiscal_year=2021)
    assert {r.pe_bli for r in parsed.rows} == {"1506N-N-L1", "9999999999"}
    assert parsed.restated == ()
```

and (the end of `test_parse_skips_a_blank_line_row_with_any_other_code`) replace:

```python
    assert parsed.rows == []
    assert parsed.skipped_invalid == 0
```

with:

```python
    assert parsed.rows == []
    assert parsed.restated == ()


def test_parse_raises_on_a_route_unsafe_era_line(tmp_path):
    with pytest.raises(UnsafeBudgetLineCode, match="era line number 'RDT&E' under 0390D"):
        parse_p1_rollup(make_era_xlsx(tmp_path, ADVANCE_PROCUREMENT_PAIR[:1] + [UNSAFE_LINE]),
                        exhibit="P-1", fiscal_year=2021)
```

- [ ] **Step 7: Run them to see them fail**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_p1_loader_route_safe.py tests/jbooks/test_cli_rollup_order.py tests/jbooks/test_p1_loader.py tests/jbooks/test_p1_loader_era.py -q 2>&1 | tail -6
```

Expected: `1 error` during collection (`ImportError: cannot import name 'verify_r1_restatements' from 'govbudget.jbooks.p1_loader'`, from `test_p1_loader_route_safe.py`), so pytest stops before running. Run the other three on their own:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_cli_rollup_order.py tests/jbooks/test_p1_loader.py tests/jbooks/test_p1_loader_era.py -q 2>&1 | tail -6
```

Expected: `4 failed, 25 passed` (1 + 14 + 14 tests): `test_r1_loads_before_p1_within_each_edition` (`At index 0 diff: (2026, 'P-1') != (2025, 'R-1')` — table order loads the first-registered P-1 first), `test_parse_loads_classified_and_skips_footnote_rows` and `test_parse_skips_a_blank_line_row_with_any_other_code` (`AttributeError: 'P1Parse' object has no attribute 'restated'`), and `test_parse_raises_on_a_route_unsafe_era_line` (`DID NOT RAISE`: the old guard skips the row).

- [ ] **Step 8: Rewrite the loader's route-safety step**

In `src/govbudget/jbooks/p1_loader.py` (line 4), replace:

```python
from collections.abc import Iterable
```

with:

```python
from collections.abc import Iterable, Mapping
```

and (the line after the `era_keys` import, through the end of `_is_valid_pe_bli`) replace:

```python
from govbudget.jbooks.rollup_loader import norm_header

logger = logging.getLogger(__name__)

# Chars that never appear in a real P-1 BLI (or an era P-1 line number) but DO
# appear in Army P-1 appropriation SECTION-HEADER labels ('RDT&E', 'O&M', …)
# that mis-parse into the BLI cell. A valid BLI is alphanumeric; era line
# numbers are digits plus optional hyphen sub-line forms ('46-1'), so the
# hyphen is deliberately NOT rejected — only these label chars + whitespace.
_INVALID_PE_BLI_CHARS = set("&/%#")


def _is_valid_pe_bli(raw) -> bool:
    """False for an appropriation-label / section-header cell wrongly in the
    BLI slot (the '&' also breaks the /program/[peBli] static route). Applied
    to the RAW workbook cell before era re-keying, so digits, letters and era
    sub-line hyphens all pass; 'RDT&E', 'O&M', and any whitespace-bearing label
    are rejected."""
    s = str(raw).strip()
    if not s:
        return False
    if _INVALID_PE_BLI_CHARS & set(s):
        return False
    return not any(c.isspace() for c in s)
```

with:

```python
from govbudget.jbooks.rollup_loader import norm_header
from govbudget.jbooks.route_safe_codes import (
    P1_R1_RESTATEMENTS,
    R1_AMOUNT_TYPE_EQUIVALENTS,
    P1RestatementMismatch,
    RouteSafeCode,
    UnsafeBudgetLineCode,
    is_route_safe_code,
    load_route_safe_codes,
)

logger = logging.getLogger(__name__)

# #194 (owner decisions 2026-10-04): a '_is_valid_pe_bli' guard used to skip
# every row whose Budget Line Item cell held '&', '/', '%', '#' or
# whitespace, taking them for appropriation section-header labels. It caught
# exactly two rows in each PB2024-PB2026 P-1 workbook and none in the other
# 17 P-1/P-1R workbooks (measured 2026-10-04, re-measured 2026-10-13): 0390D's
# real Chem Demilitarization O&M and RDT&E lines. Route-unsafe codes now
# resolve through route_safe_codes: a seeded page key (O&M -> 0390DOM), a
# checked R-1 restatement (RDT&E), or UnsafeBudgetLineCode.
```

and replace:

```python
@dataclass(frozen=True)
class P1Parse:
    rows: list[P1Row]
    sheet_title: str
    skipped_invalid: int
    era_line_keying: bool
```

with:

```python
@dataclass(frozen=True)
class P1Parse:
    rows: list[P1Row]
    sheet_title: str
    # P1_R1_RESTATEMENTS lines, parsed exactly like a loaded line but never
    # in `rows`: verify_r1_restatements checks them against the R-1 first.
    restated: tuple[P1Row, ...]
    era_line_keying: bool
```

and replace:

```python
def parse_p1_rollup(xlsx_path: Path, *, exhibit: str, fiscal_year: int) -> P1Parse:
```

with:

```python
def parse_p1_rollup(
    xlsx_path: Path, *, exhibit: str, fiscal_year: int,
    route_safe: Mapping[tuple[str, str], RouteSafeCode] | None = None,
) -> P1Parse:
```

and (the first line after the docstring) replace:

```python
    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
```

with:

```python
    # #194: a modern Budget Line Item a web address cannot carry loads under
    # its seeded page key with line_item_code the printed code (route_safe,
    # default dbt/seeds/p1_route_safe_codes.csv), or, when P1_R1_RESTATEMENTS
    # names it, goes to P1Parse.restated instead of rows. Any other
    # route-unsafe code, or era line number, on an Add row raises
    # UnsafeBudgetLineCode.
    if route_safe is None:
        route_safe = load_route_safe_codes()
    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
```

and replace:

```python
    era_prints: dict[str, set[tuple]] = defaultdict(set)
    skipped_invalid = 0
```

with:

```python
    era_prints: dict[str, set[tuple]] = defaultdict(set)
    # keys of the P1_R1_RESTATEMENTS lines (summed like any line, kept apart)
    restated_keys: set[tuple] = set()
```

and replace:

```python
        if not ids.get("pe_bli") and not classified:
            continue
        # Reject appropriation section-header rows ('RDT&E', 'O&M', …) whose
        # label mis-parses into the BLI cell. Guard the RAW cell (before era
        # re-keying), so a valid alphanumeric BLI / era line number survives.
        if not classified and not _is_valid_pe_bli(ids.get("pe_bli")):
            skipped_invalid += 1
            continue
        if add_col is not None and (
            add_col >= len(row) or str(row[add_col]).strip().lower() != "add"
        ):
            continue
        if classified:
```

with:

```python
        raw = ids.get("pe_bli")
        if (raw is None or not str(raw).strip()) and not classified:
            continue
        if add_col is not None and (
            add_col >= len(row) or str(row[add_col]).strip().lower() != "add"
        ):
            continue
        restated = False
        if classified:
```

and replace:

```python
        elif era_line_keying:
            pe_bli = era_procurement_key(
```

with:

```python
        elif era_line_keying:
            if not is_route_safe_code(str(raw).strip()):
                raise UnsafeBudgetLineCode(
                    f"{xlsx_path.name} ({exhibit} PB{fiscal_year}) row {row_idx}:"
                    f" era line number {str(raw).strip()!r} under"
                    f" {ids.get('account')} is not route-safe")
            pe_bli = era_procurement_key(
```

and replace:

```python
        else:
            pe_bli = str(ids.get("pe_bli")).strip()
            code = pe_bli
```

with:

```python
        else:
            code = str(raw).strip()
            account = str(ids.get("account"))
            alias = route_safe.get((account, code))
            if is_route_safe_code(code):
                pe_bli = code
            elif alias is not None:
                pe_bli = alias.page_key
            elif (account, code) in P1_R1_RESTATEMENTS:
                pe_bli = code
                restated = True
            else:
                raise UnsafeBudgetLineCode(
                    f"{xlsx_path.name} ({exhibit} PB{fiscal_year}) row {row_idx}:"
                    f" {account} prints {code!r}, which a web address cannot"
                    " carry; give it a page key in dbt/seeds/p1_route_safe_codes.csv"
                    " (owner decision) or record it in P1_R1_RESTATEMENTS")
```

and replace:

```python
        codes[key] = code
```

with:

```python
        codes[key] = code
        if restated:
            restated_keys.add(key)
```

and (after Task 3's tripwire block) replace:

```python
    if skipped_invalid:
        logger.info(
            "parse_p1_rollup(%s): skipped %d row(s) with an invalid/non-BLI"
            " pe_bli (appropriation section-header labels)",
            xlsx_path.name, skipped_invalid,
        )

    rows: list[P1Row] = []
    for key, amounts in sums.items():
        (account, account_title, organization, ba, ba_title,
         pe_bli, title) = key
        for amount_type, amount in amounts.items():
            rows.append(P1Row(
```

with:

```python
    rows: list[P1Row] = []
    restated_rows: list[P1Row] = []
    for key, amounts in sums.items():
        (account, account_title, organization, ba, ba_title,
         pe_bli, title) = key
        target = restated_rows if key in restated_keys else rows
        for amount_type, amount in amounts.items():
            target.append(P1Row(
```

and replace:

```python
    return P1Parse(
        rows=rows, sheet_title=sheet.title, skipped_invalid=skipped_invalid,
        era_line_keying=era_line_keying,
    )
```

with:

```python
    if restated_rows:
        logger.info(
            "parse_p1_rollup(%s): %d row(s) of %d P-1 line(s) that restate R-1"
            " program elements kept apart (P1_R1_RESTATEMENTS)",
            xlsx_path.name, len(restated_rows), len(restated_keys),
        )
    return P1Parse(
        rows=rows, sheet_title=sheet.title, restated=tuple(restated_rows),
        era_line_keying=era_line_keying,
    )


def verify_r1_restatements(con: psycopg.Connection, parsed: P1Parse) -> int:
    """Check every restated row of a parse against the R-1 it restates, on
    the CALLER's connection, before anything is written (#194, design §4.3).

    For each (account, code) of parsed.restated: the printed title must be
    P1_R1_RESTATEMENTS' title, and each amount must equal the sum of the
    named R-1 program elements' budget_lines rows for the same edition,
    account and amount type (R1_AMOUNT_TYPE_EQUIVALENTS maps PB2025's CR
    column). Raises P1RestatementMismatch on any difference, or when that
    R-1 holds no row at all (load each edition's R-1 before its P-1:
    cli._jbooks_load_rollups orders them). Returns the rows checked."""
    groups: dict[tuple, list[P1Row]] = defaultdict(list)
    for r in parsed.restated:
        groups[(r.fiscal_year, r.account, r.line_item_code)].append(r)
    checked = 0
    for (fiscal_year, account, code), rows in sorted(groups.items()):
        rule = P1_R1_RESTATEMENTS[(account, code)]
        titles = sorted({r.title or "" for r in rows})
        if titles != [rule.title]:
            raise P1RestatementMismatch(
                f"PB{fiscal_year} P-1 {account} {code!r} prints title(s) {titles},"
                f" not {rule.title!r}")
        r1 = dict(con.execute(
            "select amount_type, sum(amount_thousands) from budget_lines"
            " where exhibit = 'R-1' and fiscal_year = %s and account = %s"
            "   and pe_bli = any(%s) group by amount_type",
            (fiscal_year, account, list(rule.program_elements)),
        ).fetchall())
        if not r1:
            raise P1RestatementMismatch(
                f"PB{fiscal_year} R-1 holds no {account} row for"
                f" {', '.join(rule.program_elements)}: load the edition's R-1"
                f" before its P-1, which restates it ({code!r})")
        for r in sorted(rows, key=lambda r: r.amount_type):
            r1_type = R1_AMOUNT_TYPE_EQUIVALENTS.get(r.amount_type, r.amount_type)
            if r1.get(r1_type) != r.amount_thousands:
                raise P1RestatementMismatch(
                    f"PB{fiscal_year} P-1 {account} {code!r} {r.amount_type}"
                    f" = {r.amount_thousands} but R-1"
                    f" {' + '.join(rule.program_elements)} {r1_type}"
                    f" = {r1.get(r1_type)}")
            checked += 1
    return checked
```

and (the body of `load_p1_rollup`) replace:

```python
    parsed = parse_p1_rollup(xlsx_path, exhibit=exhibit, fiscal_year=fiscal_year)
    with psycopg.connect(dsn) as con:
        return write_p1_rows(con, parsed.rows, source_document_id=source_document_id)
```

with:

```python
    parsed = parse_p1_rollup(xlsx_path, exhibit=exhibit, fiscal_year=fiscal_year)
    with psycopg.connect(dsn) as con:
        verify_r1_restatements(con, parsed)
        return write_p1_rows(con, parsed.rows, source_document_id=source_document_id)
```

In `src/govbudget/cli.py` (`_jbooks_load_rollups`, about lines 152–158; the parameter tuple is never None, so psycopg parses `%%` to `%` on both branches), replace:

```python
    with psycopg.connect(config.PG_DSN) as con:
        rows = con.execute(
            "select id, title, file_path, fiscal_year from jbook_documents "
            "where exhibit_family='rollup' and status='downloaded'"
            + (" and fiscal_year = %s" if fiscal_year is not None else ""),
            ((fiscal_year,) if fiscal_year is not None else ()),
        ).fetchall()
```

with:

```python
    with psycopg.connect(config.PG_DSN) as con:
        # Each edition's R-1 loads before its P-1/P-1R: the P-1 loader checks
        # the lines it records as R-1 restatements against the loaded R-1
        # (p1_loader.verify_r1_restatements, #194).
        rows = con.execute(
            "select id, title, file_path, fiscal_year from jbook_documents "
            "where exhibit_family='rollup' and status='downloaded'"
            + (" and fiscal_year = %s" if fiscal_year is not None else "")
            + " order by fiscal_year, case when title like 'r1%%' then 0 else 1 end, id",
            ((fiscal_year,) if fiscal_year is not None else ()),
        ).fetchall()
```

- [ ] **Step 9: Run the tests — they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_p1_loader_route_safe.py tests/jbooks/test_cli_rollup_order.py tests/jbooks/test_p1_loader.py tests/jbooks/test_p1_loader_era.py tests/jbooks/test_route_safe_codes.py tests/test_route_safe_codes_sql.py -q 2>&1 | tail -1
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_s1_reload_era_p1.py tests/jbooks/test_era_map.py tests/jbooks/test_era_map_propose.py tests/jbooks/test_edition_probe.py -q 2>&1 | tail -1
uvx --offline ruff check --isolated --select F,E9 src/govbudget/jbooks/p1_loader.py src/govbudget/jbooks/route_safe_codes.py | tail -1
grep -rn '_is_valid_pe_bli\|skipped_invalid' src tests scripts | grep -v clean_junk_pe_bli
```

Expected: `71 passed` (10 + 1 + 14 + 14 + 26 + 6); `122 passed` (13 + 51 + 34 + 24, Task 4a's propose count); `All checks passed!`; and the grep prints one line, `src/govbudget/jbooks/p1_loader.py:27:# #194 (owner decisions 2026-10-04): a '_is_valid_pe_bli' guard used to skip` (the history comment; `scripts/clean_junk_pe_bli.py`, filtered out here, is deleted in Task 7).

- [ ] **Step 10: Measure the new parse on the real workbooks (read-only)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
uv run --project . python - <<'EOF'
import psycopg
from pathlib import Path
from govbudget import config
from govbudget.jbooks.p1_loader import parse_p1_rollup, verify_r1_restatements
with psycopg.connect(config.PG_DSN) as con:
    con.read_only = True
    for fy in (2024, 2025, 2026):
        path, = con.execute("select file_path from jbook_documents where exhibit_family = 'rollup'"
                            " and status = 'downloaded' and fiscal_year = %s and title = 'p1_display.xlsx'",
                            (fy,)).fetchone()
        p = parse_p1_rollup(Path(path), exhibit="P-1", fiscal_year=fy)
        alias = sum(r.pe_bli == "0390DOM" for r in p.rows)
        print(f"PB{fy}: rows {len(p.rows)}, 0390DOM {alias}, restated {len(p.restated)},"
              f" checked against the R-1 {verify_r1_restatements(con, p)}")
EOF
uv run --project . python scripts/era/s1_reload_era_p1.py --check | tail -1
```

Expected (measured on a scratch tree, 2026-10-13):

```
PB2024: rows 4580, 0390DOM 5, restated 5, checked against the R-1 5
PB2025: rows 2429, 0390DOM 3, restated 3, checked against the R-1 3
PB2026: rows 3167, 0390DOM 4, restated 4, checked against the R-1 4
V1: CLEAN (7 editions, 58131 parsed rows)
```

Each edition's row count is today's parse plus its O&M rows (4,575 + 5, 2,426 + 3, 3,163 + 4). Nothing is written: Task 7 is the only writer of the 0390D rows. A `P1RestatementMismatch` here means the R-1 or the workbook moved since 2026-10-13: stop and report it.

- [ ] **Step 11: dbt parse sees the seed and the test**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . dbt parse --project-dir dbt --profiles-dir dbt > /dev/null && python3 -c "import json; m = json.load(open('dbt/target/manifest.json')); print(sorted(n for n in m['nodes'] if 'route_safe' in n))"
```

Expected: `['seed.govbudget.p1_route_safe_codes', 'test.govbudget.assert_route_safe_codes_valid']`. (`dbt parse` builds no table; the seed is loaded by the release's selective build, Task 22.)

- [ ] **Step 12: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/jbooks/p1_loader.py GovBudget/src/govbudget/cli.py GovBudget/tests/jbooks/test_p1_loader_route_safe.py GovBudget/tests/jbooks/test_cli_rollup_order.py GovBudget/tests/jbooks/test_p1_loader.py GovBudget/tests/jbooks/test_p1_loader_era.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "fix(jbooks): load 0390D Chem Demil O&M under 0390DOM, check the RDT&E line against the R-1 it restates, raise on any other route-unsafe code; R-1 loads first (#194)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `6 files changed`.
