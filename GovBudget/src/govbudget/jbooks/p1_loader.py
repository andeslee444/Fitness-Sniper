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
