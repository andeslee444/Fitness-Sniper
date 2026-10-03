<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 6: Loader split, printed-code capture, era-key tripwire (with migration 021)

**Spec:** §4.1 (migration 021, moved here by CONTRACT ISSUE 1), §4.2 bullets 1–3, §7 row 1
(tripwire), §8 V2, §9 S1 (loader half).

**Files:**
- Create: `migrations/021_budget_lines_line_item_code.sql`
- Create: `tests/jbooks/test_migration_021.py`
- Modify: `src/govbudget/jbooks/p1_loader.py` (whole file, 212 lines today: `load_p1_rollup` at
  :79-212 is split into `parse_p1_rollup` / `write_p1_rows` / `load_p1_rollup`; `P1Row`,
  `P1Parse`, `EraKeyConflict`, `_code` are added; :1-77 keep their content)
- Create: `tests/jbooks/test_p1_loader_era.py`
- Test (unchanged, must stay green): `tests/jbooks/test_p1_loader.py` (12 tests)

Line numbers cited in this task are hints (anchor on the quoted text; line numbers are approximate): earlier tasks shift them.

**Interfaces:** Consumes: Task 1's throwaway cluster (`GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres`)
and `uv sync`; `era_keys.era_procurement_key`, `era_keys.is_era_procurement_key`,
`rollup_loader.norm_header` (unchanged). / Produces: `budget_lines.line_item_code text`
(+ comment, + modern backfill); `P1Row`, `P1Parse`, `EraKeyConflict(ValueError)`,
`parse_p1_rollup(xlsx_path, *, exhibit, fiscal_year) -> P1Parse`,
`write_p1_rows(con, rows, *, source_document_id) -> int` (never commits),
`load_p1_rollup(dsn, xlsx_path, *, exhibit, fiscal_year, source_document_id) -> int`
(signature unchanged; `cli._jbooks_load_rollups` at `cli.py:144-180` and
`scripts/backfill_pb2024_p1{,r}_titles.py` keep calling it unchanged).

- [ ] **Step 1: Write the failing migration test**

Create `tests/jbooks/test_migration_021.py`:

```python
"""Migration 021 (spec docs/superpowers/specs/2026-10-02-era-procurement-
history-design.md §4.1): budget_lines.line_item_code, the budget line code
printed in the source P-1/P-1R row.

The backfill copies pe_bli onto every P-1/P-1R row whose pe_bli is not an
era key: modern P-1 and every P-1R row already key by the printed code. Era
P-1 rows ('{account}-{org}-L{line}') stay NULL until the S1 re-run
(scripts/era/s1_reload_era_p1.py --apply); R-1 rows stay NULL (a program
element, not a budget line code).

The migration's SQL is re-executed inside a rolled-back transaction after
dropping the column the session fixture already added (the pattern of
tests/test_migration_019_recipient_basis.py).
"""
import psycopg
import pytest

from govbudget.jbooks.db import MIGRATIONS_DIR

SQL_PATH = MIGRATIONS_DIR / "021_budget_lines_line_item_code.sql"
COMMENT = (
    'Budget line code printed in the source P-1/P-1R row (era "Line Item",'
    ' modern "Budget Line Item"); source-stated, never mapped'
)

# (exhibit, fiscal_year, account, organization, budget_activity, pe_bli),
# and the line_item_code the backfill must leave on the row.
ROWS = [
    (("P-1", 2026, "3010F", "F", "01", "F01500"), "F01500"),
    (("P-1", 2026, "3080F", "", "04", "9999999999"), "9999999999"),
    (("P-1", 2021, "1506N", "N", "01", "1506N-N-L1"), None),
    (("P-1", 2017, "0300D", "WHS", "01", "0300D-WHS-L46-1"), None),
    (("P-1R", 2021, "2035A", "ARMY", "02", "9675A00010"), "9675A00010"),
    (("P-1R", 2024, "2035A", "A", "02", "BZ7015"), "BZ7015"),
    (("R-1", 2026, "0400", "DARPA", "01", "0601101E"), None),
]


@pytest.fixture()
def con(pg_dsn):
    with psycopg.connect(pg_dsn) as c:
        yield c
        c.rollback()


def test_021_adds_a_commented_text_column(con):
    assert con.execute(
        "select data_type from information_schema.columns"
        " where table_name = 'budget_lines' and column_name = 'line_item_code'"
    ).fetchall() == [("text",)]
    assert con.execute(
        "select col_description('budget_lines'::regclass, attnum)"
        " from pg_attribute where attrelid = 'budget_lines'::regclass"
        " and attname = 'line_item_code'"
    ).fetchone()[0] == COMMENT


def test_021_backfills_the_printed_code_everywhere_but_era_keys(con):
    con.execute("alter table budget_lines drop column line_item_code")
    doc_id = con.execute(
        "insert into jbook_documents (org, exhibit_family, fiscal_year, title,"
        " source_url, status) values ('DoD', 'rollup', 2026, 'm021.xlsx',"
        " 'https://example.test/m021.xlsx', 'downloaded') returning id"
    ).fetchone()[0]
    for (exhibit, fy, account, org, ba, pe_bli), _ in ROWS:
        con.execute(
            "insert into budget_lines (exhibit, fiscal_year, account,"
            " organization, budget_activity, pe_bli, amount_type,"
            " amount_thousands, source_document_id)"
            " values (%s, %s, %s, %s, %s, %s, 'fy_2020_total', 1, %s)",
            (exhibit, fy, account, org, ba, pe_bli, doc_id),
        )
    con.execute(SQL_PATH.read_text())
    got = dict(con.execute(
        "select pe_bli, line_item_code from budget_lines").fetchall())
    assert got == {key[5]: code for key, code in ROWS}
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_migration_021.py -q`

Expected: `2 failed`, with `AssertionError: assert [] == [('text',)]` and
`psycopg.errors.UndefinedColumn: column "line_item_code" of relation "budget_lines" does not exist`.

- [ ] **Step 3: Create the migration (spec §4.1 statements verbatim)**

Create `migrations/021_budget_lines_line_item_code.sql`:

```sql
-- 021: the budget line code printed in each P-1/P-1R source row
-- (families piece 1, spec docs/superpowers/specs/2026-10-02-era-procurement-history-design.md §4.1).
--
-- PB2017-PB2023 P-1 rows key pe_bli by the era display line
-- ('{account}-{org}-L{line}', era_keys.py) and the loader used to drop the
-- printed code (column I, 'Line Item'). This column keeps it, source-stated
-- and never mapped. Modern P-1 rows and every P-1R row already key pe_bli by
-- the printed code, so the backfill below is exact for them; era P-1 rows
-- are filled by the S1 re-run (scripts/era/s1_reload_era_p1.py --apply).
-- R-1 rows stay NULL (a program element, not a budget line code).
alter table budget_lines add column line_item_code text;
comment on column budget_lines.line_item_code is
  'Budget line code printed in the source P-1/P-1R row (era "Line Item", modern "Budget Line Item"); source-stated, never mapped';
update budget_lines set line_item_code = pe_bli
 where exhibit in ('P-1','P-1R') and pe_bli !~ '^\d{4}[A-Z]-[A-Z]+-L';
```

- [ ] **Step 4: Run the test to see it pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_migration_021.py tests/jbooks/test_db.py -q`

Expected: `3 passed` (the session fixture's `migrate` applied 021; `test_db.py`'s
idempotence check still sees nothing left to apply).

- [ ] **Step 5: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/migrations/021_budget_lines_line_item_code.sql GovBudget/tests/jbooks/test_migration_021.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(jbooks): migration 021 adds budget_lines.line_item_code, backfilled on modern P-1 and all P-1R rows (families S1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Write the failing loader tests (V2)**

The header row below is copied from `data/raw_docs/fy2021/dod/p1_display.xlsx`, sheet
`Exhibit P-1`, row 2 (read-only, 2026-10-02; columns A–Q, wrapped headers included):
`['Account', 'Account Title', 'Organization', 'Budget\nActivity', 'Budget Activity Title', 'Line\nNumber', 'BSA', 'Budget Sub Activity (BSA) Title', 'Line Item', 'Line Item Title', 'Cost\nType', 'Cost Type Title', 'Add/\nNon-Add', 'FY 2019\n(Base + OCO)\nQuantity', 'FY 2019\n(Base + OCO)\nAmount', 'FY 2020\nBase Enacted\nQuantity', 'FY 2020\nBase Enacted\nAmount', …]`.
Row 1 carries `Total of Displayed Rows` in column K; the Classified Programs row (PB2021
row 1096) has a blank Line Number, organization `''` and Line Item `9999999999`; the
footnote rows (PB2022 rows 1156–1159) have prose in column A and nothing else.

Create `tests/jbooks/test_p1_loader_era.py`:

```python
"""V2 (spec 2026-10-02-era-procurement-history-design.md §8): the split
P-1 loader on a PB2021-shaped era workbook.

The header row is copied cell for cell from the real PB2021 P-1 display
workbook (data/raw_docs/fy2021/dod/p1_display.xlsx, sheet 'Exhibit P-1',
row 2, wrapped headers included), truncated after the FY 2019 and FY 2020
Base Enacted columns; the banner row 1 carries 'Total of Displayed Rows'
in column K as the real one does. Rows mirror real era shapes: column I
('Line Item') is the printed budget line code, column F ('Line Number')
the display line the era key is minted from.
"""
from decimal import Decimal

import psycopg
import pytest
from openpyxl import Workbook

from govbudget.jbooks.p1_loader import (
    EraKeyConflict,
    P1Parse,
    P1Row,
    load_p1_rollup,
    parse_p1_rollup,
    write_p1_rows,
)

# data/raw_docs/fy2021/dod/p1_display.xlsx, 'Exhibit P-1', row 2, columns A-Q.
PB2021_ERA_HEADERS = [
    "Account", "Account Title", "Organization", "Budget\nActivity",
    "Budget Activity Title", "Line\nNumber", "BSA",
    "Budget Sub Activity (BSA) Title", "Line Item", "Line Item Title",
    "Cost\nType", "Cost Type Title", "Add/\nNon-Add",
    "FY 2019\n(Base + OCO)\nQuantity", "FY 2019\n(Base + OCO)\nAmount",
    "FY 2020\nBase Enacted\nQuantity", "FY 2020\nBase Enacted\nAmount",
]

APN = ("1506N", "Aircraft Procurement, Navy")
OPAF = ("3080F", "Other Procurement, Air Force")


def _row(acct, org, ba, ba_title, line, code, title, cost_type, add, fy19, fy20):
    return [acct[0], acct[1], org, ba, ba_title, line, "10", "BSA", code, title,
            cost_type, "Cost", add, 0, fy19, 0, fy20]


def make_era_xlsx(tmp_path, rows, name="p1_display.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "Exhibit P-1"
    ws.append(["", "", "", "", "", "", "", "", "", "", "Total of Displayed Rows"])
    ws.append(PB2021_ERA_HEADERS)
    for r in rows:
        ws.append(r)
    p = tmp_path / name
    wb.save(p)
    return p


# A program line plus its advance-procurement line: the SAME printed code on
# two display lines (live PB2021 shape: 0577 F/A-18E/F lines 1 and 2).
ADVANCE_PROCUREMENT_PAIR = [
    _row(APN, "N", "01", "Combat Aircraft", "1", "0577", "F/A-18E/F (Fighter) Hornet",
         "A", "Add", 1000, 1100),
    _row(APN, "N", "01", "Combat Aircraft", "1", "0577", "F/A-18E/F (Fighter) Hornet",
         "B", "Add", 10, 20),
    _row(APN, "N", "01", "Combat Aircraft", "1", "0577", "F/A-18E/F (Fighter) Hornet",
         "Z", "Non-Add", 999999, 999999),
    _row(APN, "N", "01", "Combat Aircraft", "2", "0577", "F/A-18E/F (Fighter) Hornet",
         "A", "Add", 300, 400),
]
# Classified Programs: blank Line Number, organization '', code 9999999999
# (live PB2021 row 1096).
CLASSIFIED = _row(OPAF, "", "04", "Other Base Maintenance and Support Equip", "",
                  "9999999999", "Classified Programs", "", "Add", 20743417, 21086112)
# Footnote rows: blank Line Number, prose in column A (live PB2022 rows 1156-1157).
FOOTNOTES = [
    [""] + [None] * 16,
    ["*Includes Division A, Title IX and X of the Consolidated Appropriations Act, 2020"]
    + [None] * 16,
]
# Section header: an appropriation label in the line slot (the guard's '&').
SECTION_HEADER = _row(("0390D", "RDT&E, Defense-Wide"), "DW", "", "", "RDT&E",
                      "RDT&E", "RDT&E Total", "A", "Add", 1002560, 754762)


def test_parse_captures_the_printed_code_and_keys_by_line(tmp_path):
    parsed = parse_p1_rollup(
        make_era_xlsx(tmp_path, ADVANCE_PROCUREMENT_PAIR), exhibit="P-1", fiscal_year=2021)
    assert isinstance(parsed, P1Parse)
    assert parsed.era_line_keying is True
    assert parsed.sheet_title == "Exhibit P-1"
    got = {(r.pe_bli, r.amount_type): r for r in parsed.rows}
    assert sorted(got) == [
        ("1506N-N-L1", "fy_2019_base_oco"), ("1506N-N-L1", "fy_2020_base_enacted"),
        ("1506N-N-L2", "fy_2019_base_oco"), ("1506N-N-L2", "fy_2020_base_enacted"),
    ]
    line1 = got[("1506N-N-L1", "fy_2019_base_oco")]
    assert line1 == P1Row(
        exhibit="P-1", fiscal_year=2021, account="1506N",
        account_title="Aircraft Procurement, Navy", organization="N",
        budget_activity="01", budget_activity_title="Combat Aircraft",
        pe_bli="1506N-N-L1", title="F/A-18E/F (Fighter) Hornet",
        amount_type="fy_2019_base_oco", amount_thousands=Decimal("1010"),
        source_sheet="Exhibit P-1", source_cells=("O3", "O4"),
        line_item_code="0577",
    )
    # the advance-procurement line stays its own era key with its own code
    line2 = got[("1506N-N-L2", "fy_2020_base_enacted")]
    assert line2.line_item_code == "0577"
    assert line2.amount_thousands == Decimal("400")
    assert line2.source_cells == ("Q6",)


def test_parse_skips_classified_footnote_and_section_header_rows(tmp_path):
    """Blank-Line-Number rows (the Classified Programs line, footnotes) and
    the section-header label are skipped. S1b (Task 9) changes the first."""
    rows = ADVANCE_PROCUREMENT_PAIR[:1] + [CLASSIFIED, SECTION_HEADER] + FOOTNOTES
    parsed = parse_p1_rollup(make_era_xlsx(tmp_path, rows), exhibit="P-1", fiscal_year=2021)
    assert {r.pe_bli for r in parsed.rows} == {"1506N-N-L1"}
    assert parsed.skipped_invalid == 1  # the 'RDT&E' label row


@pytest.mark.parametrize("field, value", [
    ("code", "0578"),
    ("title", "F/A-18E/F (Fighter) Hornet (AP-CY)"),
    ("ba", "02"),
])
def test_parse_raises_when_an_era_key_prints_two_values(tmp_path, field, value):
    second = dict(code="0577", title="F/A-18E/F (Fighter) Hornet", ba="01")
    second[field] = value
    rows = [
        ADVANCE_PROCUREMENT_PAIR[0],
        _row(APN, "N", second["ba"], "Combat Aircraft", "1", second["code"],
             second["title"], "B", "Add", 10, 20),
    ]
    with pytest.raises(EraKeyConflict, match="1506N-N-L1"):
        parse_p1_rollup(make_era_xlsx(tmp_path, rows), exhibit="P-1", fiscal_year=2021)


def test_tripwire_ignores_non_add_rows(tmp_path):
    rows = [
        ADVANCE_PROCUREMENT_PAIR[0],
        _row(APN, "N", "01", "Combat Aircraft", "1", "0578", "Other",
             "Z", "Non-Add", 1, 1),
    ]
    parsed = parse_p1_rollup(make_era_xlsx(tmp_path, rows), exhibit="P-1", fiscal_year=2021)
    assert {r.line_item_code for r in parsed.rows} == {"0577"}


def test_parse_is_pure(tmp_path, monkeypatch):
    def no_db(*a, **k):
        raise AssertionError("parse_p1_rollup must not open a database connection")
    monkeypatch.setattr(psycopg, "connect", no_db)
    parsed = parse_p1_rollup(
        make_era_xlsx(tmp_path, ADVANCE_PROCUREMENT_PAIR), exhibit="P-1", fiscal_year=2021)
    assert len(parsed.rows) == 4


def test_modern_and_p1r_rows_carry_pe_bli_as_code(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Exhibit P-1R"
    ws.append(["Account", "Account Title", "Organization", "Budget\nActivity",
               "Budget Activity Title", "BSA", "Budget Sub Activity (BSA) Title",
               "Line Item", "Line Item Title", "Cost\nType", "Cost Type Title",
               "FY 2018\nQuantity", "FY 2018\nAmount", "Classification"])
    ws.append(["0300D", "Procurement, Defense-Wide", "DEFW", "01", "Major Equipment",
               "1", "Major Equipment", "23", "Vehicles", "A", "Weapon System Cost",
               "", 21000, "U"])
    p = tmp_path / "p1r_display.xlsx"
    wb.save(p)
    parsed = parse_p1_rollup(p, exhibit="P-1R", fiscal_year=2017)
    assert parsed.era_line_keying is False
    assert [(r.pe_bli, r.line_item_code) for r in parsed.rows] == [("23", "23")]


def test_write_p1_rows_never_commits(pg_dsn, tmp_path, doc_id):
    parsed = parse_p1_rollup(
        make_era_xlsx(tmp_path, ADVANCE_PROCUREMENT_PAIR), exhibit="P-1", fiscal_year=2021)
    con = psycopg.connect(pg_dsn)
    try:
        n = write_p1_rows(con, parsed.rows, source_document_id=doc_id)
        assert n == 4
        inside = con.execute("select count(*) from budget_lines").fetchone()[0]
        assert inside == 4
        con.rollback()
    finally:
        con.close()
    with psycopg.connect(pg_dsn) as other:
        assert other.execute("select count(*) from budget_lines").fetchone()[0] == 0


def test_load_writes_line_item_code(pg_dsn, tmp_path, doc_id):
    n = load_p1_rollup(pg_dsn, make_era_xlsx(tmp_path, ADVANCE_PROCUREMENT_PAIR),
                       exhibit="P-1", fiscal_year=2021, source_document_id=doc_id)
    assert n == 4
    with psycopg.connect(pg_dsn) as con:
        rows = con.execute(
            "select pe_bli, line_item_code, count(*) from budget_lines"
            " group by 1, 2 order by 1"
        ).fetchall()
    assert rows == [("1506N-N-L1", "0577", 2), ("1506N-N-L2", "0577", 2)]


def test_update_branch_sets_line_item_code_on_an_existing_row(pg_dsn, tmp_path, doc_id):
    xlsx = make_era_xlsx(tmp_path, ADVANCE_PROCUREMENT_PAIR)
    load_p1_rollup(pg_dsn, xlsx, exhibit="P-1", fiscal_year=2021, source_document_id=doc_id)
    with psycopg.connect(pg_dsn) as con:
        con.execute("update budget_lines set line_item_code = null")
        ids_before = con.execute("select id from budget_lines order by id").fetchall()
    load_p1_rollup(pg_dsn, xlsx, exhibit="P-1", fiscal_year=2021, source_document_id=doc_id)
    with psycopg.connect(pg_dsn) as con:
        ids_after = con.execute("select id from budget_lines order by id").fetchall()
        codes = con.execute(
            "select distinct line_item_code from budget_lines").fetchall()
    assert ids_after == ids_before  # updated in place, nothing inserted
    assert codes == [("0577",)]
```

- [ ] **Step 7: Run them to see them fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_p1_loader_era.py -q`

Expected: collection error `ImportError: cannot import name 'EraKeyConflict' from 'govbudget.jbooks.p1_loader'`.

- [ ] **Step 8: Split the loader**

Replace the whole of `src/govbudget/jbooks/p1_loader.py` with:

```python
import logging
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import psycopg
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from govbudget.jbooks.era_keys import era_procurement_key
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


P1_ID_HEADERS = {
    "Account": "account",
    "Account Title": "account_title",
    "Organization": "organization",
    "Budget Activity": "budget_activity",
    "Budget Activity Title": "budget_activity_title",
    "Line Number": "line_number",
    "Budget Line Item": "pe_bli",
    "Budget Line Item (BLI) Title": "title",
    # PB2024 spelling (the R-1 header reused verbatim on P-1/P-1R; PB2025+
    # shortened it to 'Budget Line Item (BLI) Title' above — missing this
    # variant loaded PB2024's 4,585 P-1 rows title-NULL)
    "Program Element/Budget Line Item (BLI) Title": "title",
    # PB2017–PB2023 era spellings (no workbook carries both variants)
    "Line Item": "pe_bli",
    "Line Item Title": "title",
}
P1_REQUIRED = {"Account", "Organization"}
P1_BLI_HEADERS = ("Budget Line Item", "Line Item")


@dataclass(frozen=True)
class P1Row:
    """One budget_lines row a P-1/P-1R workbook yields: one (account,
    organization, budget activity, pe_bli) bucket x one FY amount column."""
    exhibit: str
    fiscal_year: int
    account: str
    account_title: str | None
    organization: str
    budget_activity: str | None
    budget_activity_title: str | None
    pe_bli: str
    title: str | None
    amount_type: str
    amount_thousands: Decimal
    source_sheet: str
    source_cells: tuple[str, ...]
    # The budget line code printed in the row: era P-1 column I ('Line
    # Item'); everywhere else the code pe_bli already is (modern 'Budget
    # Line Item', era P-1R 'Line Item').
    line_item_code: str | None


@dataclass(frozen=True)
class P1Parse:
    rows: list[P1Row]
    sheet_title: str
    skipped_invalid: int
    era_line_keying: bool


class EraKeyConflict(ValueError):
    """An era key ('{account}-{org}-L{line}') printed more than one budget
    line code, title or budget activity across its rows. The era key is a
    display line; if it ever carries two programs, keying by line number
    would silently merge them, so the parse refuses."""


def _slug(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", header.lower()).strip("_")


def _str(v) -> str | None:
    return None if v is None else str(v)


def _code(v) -> str | None:
    """A printed budget line code cell, stripped; None when blank."""
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _find_header_row(ws) -> tuple[int, dict[int, str]]:
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=20, values_only=True), start=1):
        cells = {j: norm_header(v) for j, v in enumerate(row) if v is not None}
        vals = set(cells.values())
        if P1_REQUIRED <= vals and any(h in vals for h in P1_BLI_HEADERS):
            return i, cells
    raise ValueError(
        f"No header row with {P1_REQUIRED} + one of {P1_BLI_HEADERS}"
        " found in first 20 rows"
    )


def parse_p1_rollup(xlsx_path: Path, *, exhibit: str, fiscal_year: int) -> P1Parse:
    """Melt a P-1/P-1R display workbook into BLI-grain budget_lines rows,
    without touching any database (V1 diffs this against Postgres; the S1
    script writes it inside a transaction it owns).

    P-1 rows are (BLI x cost type x BSA) grain with Add/Non-Add memo rows;
    this keeps 'Add' rows only, melts the per-FY '... Amount' columns (slug
    drops the suffix so amount_types align with reconcile.scenario_map:
    fy_2024_actuals etc.), and sums to (account, organization, budget
    activity, BLI) grain.

    Raises EraKeyConflict when an era key prints more than one code, title
    or budget activity across its Add rows.
    """
    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
    sheet = wb[f"Exhibit {exhibit}"] if f"Exhibit {exhibit}" in wb.sheetnames else wb[wb.sheetnames[0]]
    header_row, headers = _find_header_row(sheet)
    # PB2025 suffixes footnoted columns with '*' ('FY 2024 PB Request with CR
    # Adjustments Amount*') — strip footnote markers before the suffix check.
    clean = {j: h.rstrip("*").strip() for j, h in headers.items()}
    amount_cols = {
        j: _slug(clean[j][: -len(" Amount")])
        for j, h in headers.items()
        if h.upper().startswith("FY ") and clean[j].endswith(" Amount")
    }
    id_cols = {j: P1_ID_HEADERS[h] for j, h in headers.items() if h in P1_ID_HEADERS}
    # PB2017–PB2023 P-1 workbooks key rows by 'Line Item' display codes the
    # era P-40 XML never carries; the era's shared identifier is the P-1 line
    # number (the XML's P1LineNumber), so pe_bli comes from 'Line Number' —
    # namespaced to '{account}-{org}-L{line}' via era_procurement_key
    # (Finding D: bare line numbers collide with modern BLI codes, span
    # orgs, and conflate programs; load_details keys the era XML side
    # identically so reconciliation still joins). The printed 'Line Item'
    # code (column I) is kept as line_item_code: source-stated, never
    # mapped. Modern workbooks ('Budget Line Item' BLI codes) are
    # untouched; era P-1R has neither 'Budget Line Item' nor 'Line Number'
    # and keeps the 'Line Item' code as pe_bli (P-1R is never reconciled
    # against XML details).
    header_vals = set(headers.values())
    era_line_keying = (
        "Budget Line Item" not in header_vals and "Line Number" in header_vals
    )
    code_col = None
    if era_line_keying:
        code_col = next(j for j, h in headers.items() if h == "Line Item")
        id_cols = {
            j: n for j, n in id_cols.items() if n not in ("pe_bli", "line_number")
        }
        id_cols[next(j for j, h in headers.items() if h == "Line Number")] = "pe_bli"
    # PB2017–PB2023 P-1R workbooks have no Add/Non-Add column: nothing to filter.
    add_col = next((j for j, h in headers.items() if h == "Add/Non-Add"), None)

    # key matches the DB unique constraint grain:
    # (account, account_title, organization, ba, ba_title, bli, title)
    # line_number is intentionally excluded so all cost-type sub-rows for the same
    # BLI aggregate into a single bucket before insert (avoiding last-write-wins collision).
    sums: dict[tuple, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    cells: dict[tuple, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    codes: dict[tuple, str | None] = {}
    # era key -> every (code, title, budget activity) its Add rows print
    era_prints: dict[str, set[tuple]] = defaultdict(set)
    skipped_invalid = 0
    for row_idx, row in enumerate(
        sheet.iter_rows(min_row=header_row + 1, values_only=True),
        start=header_row + 1,
    ):
        ids = {name: row[j] for j, name in id_cols.items() if j < len(row)}
        if not ids.get("pe_bli"):
            continue
        # Reject appropriation section-header rows ('RDT&E', 'O&M', …) whose
        # label mis-parses into the BLI cell. Guard the RAW cell (before era
        # re-keying), so a valid alphanumeric BLI / era line number survives.
        if not _is_valid_pe_bli(ids.get("pe_bli")):
            skipped_invalid += 1
            continue
        if add_col is not None and (
            add_col >= len(row) or str(row[add_col]).strip().lower() != "add"
        ):
            continue
        if era_line_keying:
            pe_bli = era_procurement_key(
                str(ids.get("account")), str(ids.get("organization")),
                str(ids.get("pe_bli")),
            )
            code = _code(row[code_col]) if code_col < len(row) else None
            era_prints[pe_bli].add(
                (code, ids.get("title"), _str(ids.get("budget_activity")))
            )
        else:
            pe_bli = str(ids.get("pe_bli")).strip()
            code = pe_bli
        key = (
            str(ids.get("account")), ids.get("account_title"),
            str(ids.get("organization")), _str(ids.get("budget_activity")),
            ids.get("budget_activity_title"),
            pe_bli,
            ids.get("title"),
        )
        codes[key] = code
        for j, amount_type in amount_cols.items():
            if j >= len(row) or row[j] is None or str(row[j]).strip() == "":
                continue
            try:
                amount = Decimal(str(row[j]))
            except ArithmeticError:
                continue
            if amount.is_nan():
                continue
            sums[key][amount_type] += amount
            cells[key][amount_type].append(f"{get_column_letter(j + 1)}{row_idx}")

    conflicts = {k: v for k, v in era_prints.items() if len(v) > 1}
    if conflicts:
        detail = "; ".join(
            f"{k}: {sorted(v, key=repr)}" for k, v in sorted(conflicts.items())[:5]
        )
        raise EraKeyConflict(
            f"{xlsx_path.name} ({exhibit} PB{fiscal_year}): {len(conflicts)} era"
            f" key(s) print more than one (code, title, budget activity): {detail}"
        )

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
                exhibit=exhibit, fiscal_year=fiscal_year, account=account,
                account_title=_str(account_title), organization=organization,
                budget_activity=ba, budget_activity_title=_str(ba_title),
                pe_bli=pe_bli, title=_str(title), amount_type=amount_type,
                amount_thousands=amount, source_sheet=sheet.title,
                source_cells=tuple(cells[key][amount_type]),
                line_item_code=codes[key],
            ))
    return P1Parse(
        rows=rows, sheet_title=sheet.title, skipped_invalid=skipped_invalid,
        era_line_keying=era_line_keying,
    )


_UPSERT = """
    insert into budget_lines
      (exhibit, fiscal_year, account, account_title, organization,
       budget_activity, budget_activity_title, pe_bli,
       title, amount_type, amount_thousands, source_document_id,
       source_sheet, source_cells, line_item_code)
    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    on conflict (exhibit, fiscal_year, account, organization, budget_activity, pe_bli, amount_type)
    do update set amount_thousands = excluded.amount_thousands,
                  title = excluded.title,
                  source_document_id = excluded.source_document_id,
                  source_sheet = excluded.source_sheet,
                  source_cells = excluded.source_cells,
                  line_item_code = excluded.line_item_code
"""


def write_p1_rows(
    con: psycopg.Connection, rows: Iterable[P1Row], *, source_document_id: int,
) -> int:
    """Upsert parsed rows on the CALLER's connection. Never commits: the
    caller owns the transaction (load_p1_rollup commits; the S1 script
    compares and rolls back on any difference). Returns rows upserted."""
    upserted = 0
    for r in rows:
        con.execute(
            _UPSERT,
            (r.exhibit, r.fiscal_year, r.account, r.account_title, r.organization,
             r.budget_activity, r.budget_activity_title, r.pe_bli, r.title,
             r.amount_type, r.amount_thousands, source_document_id,
             r.source_sheet, list(r.source_cells), r.line_item_code),
        )
        upserted += 1
    return upserted


def load_p1_rollup(
    dsn: str, xlsx_path: Path, *, exhibit: str, fiscal_year: int,
    source_document_id: int,
) -> int:
    """Parse a P-1/P-1R display workbook and upsert it into budget_lines in
    one committed transaction. Returns upserts.

    source_document_id is REQUIRED (migration 005: budget_lines provenance
    is a structural invariant — every row must trace to a jbook_documents
    row, the same contract the lake export enforces).
    """
    parsed = parse_p1_rollup(xlsx_path, exhibit=exhibit, fiscal_year=fiscal_year)
    with psycopg.connect(dsn) as con:
        return write_p1_rows(con, parsed.rows, source_document_id=source_document_id)
```

What changed against today's file: `:79-212` (`load_p1_rollup` parsing and writing in
one call, opening its own connection at `:187`) becomes `parse_p1_rollup` (the same
parse, plus `code_col` / `codes` / `era_prints` and the `EraKeyConflict` check),
`write_p1_rows` (the same upsert, `line_item_code` added to the column list, the
`values` placeholders and the `do update set` list, on the caller's connection) and a
three-line `load_p1_rollup`. The bucket key, the Add/Non-Add filter, the section-header
guard, the amount melt and the cell lists are byte-for-byte today's logic, so V1
(Task 8) can require equality with every stored row.

- [ ] **Step 9: Run the loader tests to see them pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_p1_loader_era.py tests/jbooks/test_p1_loader.py -q`

Expected: `23 passed` (11 new, 12 existing).

- [ ] **Step 10: Run the whole jbooks suite**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks -q`

Expected: `442 passed, 2 skipped` (measured on a copy of this branch: 429 passed and 2
skipped before this task, + 2 migration tests + 11 loader tests).

- [ ] **Step 11: Read-only check of the parse on the real era workbooks**

Run:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data uv run --project . python - <<'EOF'
from pathlib import Path
from govbudget.jbooks.p1_loader import parse_p1_rollup
from govbudget.jbooks.era_keys import is_era_procurement_key
RAW = Path("/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/raw_docs")
total_rows = total_keys = 0
for fy in range(2017, 2024):
    p = parse_p1_rollup(RAW / f"fy{fy}/dod/p1_display.xlsx", exhibit="P-1", fiscal_year=fy)
    keys = {}
    for r in p.rows:
        keys.setdefault(r.pe_bli, set()).add(r.line_item_code)
    era = {k: v for k, v in keys.items() if is_era_procurement_key(k)}
    one = sum(1 for v in era.values() if len(v) == 1 and None not in v)
    print(f"PB{fy}: era_line_keying={p.era_line_keying} rows={len(p.rows)}"
          f" era keys={len(era)} with one code={one} skipped_invalid={p.skipped_invalid}")
    total_rows += len(p.rows); total_keys += len(era)
print(f"total rows={total_rows} era keys={total_keys}")
EOF
```

Expected (measured 2026-10-02; raw workbooks are read-only, nothing is written):

```
PB2017: era_line_keying=True rows=6783 era keys=969 with one code=969 skipped_invalid=0
PB2018: era_line_keying=True rows=13377 era keys=1029 with one code=1029 skipped_invalid=0
PB2019: era_line_keying=True rows=12857 era keys=989 with one code=989 skipped_invalid=0
PB2020: era_line_keying=True rows=8775 era keys=975 with one code=975 skipped_invalid=0
PB2021: era_line_keying=True rows=10050 era keys=1005 with one code=1005 skipped_invalid=0
PB2022: era_line_keying=True rows=2979 era keys=993 with one code=993 skipped_invalid=0
PB2023: era_line_keying=True rows=2901 era keys=967 with one code=967 skipped_invalid=0
total rows=57722 era keys=6927
```

No `EraKeyConflict` is raised: every era key prints one code, one title and one budget
activity (spec §3). The row counts equal Postgres' era P-1 rows per edition (6,783 /
13,377 / 12,857 / 8,775 / 10,050 / 2,979 / 2,901; `select fiscal_year, count(*) from
budget_lines where exhibit='P-1' and fiscal_year between 2017 and 2023 group by 1`).

- [ ] **Step 12: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/src/govbudget/jbooks/p1_loader.py GovBudget/tests/jbooks/test_p1_loader_era.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(jbooks): split the P-1 loader into parse_p1_rollup/write_p1_rows, keep the printed era code, refuse an era key that prints two codes, titles or budget activities (families S1, V2)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
