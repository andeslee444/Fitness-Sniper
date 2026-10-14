import logging
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import psycopg
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from govbudget.jbooks.era_keys import EraKeyConflict, era_procurement_key
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
# The Classified Programs line: every P-1 edition prints it under this code.
# Modern workbooks key it by its 'Budget Line Item' like any line; era
# workbooks print it with a blank Line Number, so it needs its own rule.
CLASSIFIED_CODE = "9999999999"


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
    # P1_R1_RESTATEMENTS lines, parsed exactly like a loaded line but never
    # in `rows`: verify_r1_restatements checks them against the R-1 first.
    restated: tuple[P1Row, ...]
    era_line_keying: bool


class P1KeyConflict(ValueError):
    """Two parsed groups that differ only in a title (account title, budget
    activity title or line title) share one budget_lines upsert key
    (exhibit, fiscal_year, account, organization, budget_activity, pe_bli,
    amount_type; exhibit and fiscal year are fixed per parse). Both would
    upsert into one row and the last write would win, so the parse refuses
    (ROADMAP #202)."""


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


def parse_p1_rollup(
    xlsx_path: Path, *, exhibit: str, fiscal_year: int,
    route_safe: Mapping[tuple[str, str], RouteSafeCode] | None = None,
) -> P1Parse:
    """Melt a P-1/P-1R display workbook into BLI-grain budget_lines rows,
    without touching any database (V1 diffs this against Postgres; the S1
    script writes it inside a transaction it owns).

    P-1 rows are (BLI x cost type x BSA) grain with Add/Non-Add memo rows;
    this keeps 'Add' rows only, melts the per-FY '... Amount' columns (slug
    drops the suffix so amount_types align with reconcile.scenario_map:
    fy_2024_actuals etc.), and sums to (account, organization, budget
    activity, BLI) grain.

    Raises EraKeyConflict when an era key prints more than one code, title
    or budget activity across its Add rows, and P1KeyConflict when two
    groups would upsert into one budget_lines row (ROADMAP #202).
    """
    # #194: a modern Budget Line Item a web address cannot carry loads under
    # its seeded page key with line_item_code the printed code (route_safe,
    # default dbt/seeds/p1_route_safe_codes.csv), or, when P1_R1_RESTATEMENTS
    # names it, goes to P1Parse.restated instead of rows. Any other
    # route-unsafe code, or era line number, on an Add row raises
    # UnsafeBudgetLineCode.
    if route_safe is None:
        route_safe = load_route_safe_codes()
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

    # Grouping key: (account, account_title, organization, ba, ba_title, bli,
    # title). It is NOT the DB upsert key, which holds no title: (exhibit,
    # fiscal_year, account, organization, budget_activity, pe_bli,
    # amount_type). The P1KeyConflict tripwire after the loop refuses two
    # groups that would upsert into one row (ROADMAP #202). line_number is
    # intentionally excluded so all cost-type sub-rows for the same BLI
    # aggregate into a single bucket before insert (avoiding last-write-wins
    # collision).
    sums: dict[tuple, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    cells: dict[tuple, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    codes: dict[tuple, str | None] = {}
    # era key -> every (code, title, budget activity) its Add rows print
    era_prints: dict[str, set[tuple]] = defaultdict(set)
    # keys of the P1_R1_RESTATEMENTS lines (summed like any line, kept apart)
    restated_keys: set[tuple] = set()
    for row_idx, row in enumerate(
        sheet.iter_rows(min_row=header_row + 1, values_only=True),
        start=header_row + 1,
    ):
        ids = {name: row[j] for j, name in id_cols.items() if j < len(row)}
        # S1b: an era row with a blank Line Number is the Classified Programs
        # line when its Line Item is CLASSIFIED_CODE (it loads under that
        # code, as in modern editions); any other blank-line row (footnotes,
        # spacer rows) is skipped.
        classified = (
            era_line_keying and not ids.get("pe_bli")
            and code_col < len(row) and _code(row[code_col]) == CLASSIFIED_CODE
        )
        raw = ids.get("pe_bli")
        if (raw is None or not str(raw).strip()) and not classified:
            continue
        if add_col is not None and (
            add_col >= len(row) or str(row[add_col]).strip().lower() != "add"
        ):
            continue
        restated = False
        if classified:
            pe_bli = code = CLASSIFIED_CODE
            # The line names no organization: the workbooks print '' (as
            # PB2024-PB2026 rows store it); an empty cell reads back as None,
            # which must load as '' too, never the string 'None'.
            if ids.get("organization") is None:
                ids["organization"] = ""
        elif era_line_keying:
            if not is_route_safe_code(str(raw).strip()):
                raise UnsafeBudgetLineCode(
                    f"{xlsx_path.name} ({exhibit} PB{fiscal_year}) row {row_idx}:"
                    f" era line number {str(raw).strip()!r} under"
                    f" {ids.get('account')} is not route-safe")
            pe_bli = era_procurement_key(
                str(ids.get("account")), str(ids.get("organization")),
                str(ids.get("pe_bli")),
            )
            code = _code(row[code_col]) if code_col < len(row) else None
            era_prints[pe_bli].add(
                (code, ids.get("title"), _str(ids.get("budget_activity")))
            )
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
        key = (
            str(ids.get("account")), ids.get("account_title"),
            str(ids.get("organization")), _str(ids.get("budget_activity")),
            ids.get("budget_activity_title"),
            pe_bli,
            ids.get("title"),
        )
        codes[key] = code
        if restated:
            restated_keys.add(key)
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

    # ROADMAP #202: the grouping key holds three titles the upsert key does
    # not, so two groups can share one upsert key and the last write would
    # win. 0 cases in the 20 P-1/P-1R workbooks (measured 2026-10-13); the
    # key WITHOUT amount_type has one (PB2026 3022F/F/03/SFV000, two titles
    # on disjoint amount columns, nothing lost), so amount_type belongs in it.
    upsert_owner: dict[tuple, tuple] = {}
    key_clashes: dict[tuple, set[tuple]] = defaultdict(set)
    for key, amounts in sums.items():
        account, _a_title, organization, ba, _ba_title, pe_bli, _title = key
        for amount_type in amounts:
            upsert = (account, organization, ba, pe_bli, amount_type)
            first = upsert_owner.setdefault(upsert, key)
            if first != key:
                key_clashes[upsert] |= {first, key}
    if key_clashes:
        detail = "; ".join(
            f"{'/'.join('' if p is None else str(p) for p in upsert)}: titles"
            f" {sorted({(g[1], g[4], g[6]) for g in groups}, key=repr)}"
            for upsert, groups in sorted(key_clashes.items(), key=lambda kv: repr(kv[0]))[:5]
        )
        raise P1KeyConflict(
            f"{xlsx_path.name} ({exhibit} PB{fiscal_year}): {len(key_clashes)} upsert"
            " key(s) (account, organization, budget activity, pe_bli, amount_type) hold"
            f" more than one (account title, budget activity title, title): {detail}"
        )

    rows: list[P1Row] = []
    restated_rows: list[P1Row] = []
    for key, amounts in sums.items():
        (account, account_title, organization, ba, ba_title,
         pe_bli, title) = key
        target = restated_rows if key in restated_keys else rows
        for amount_type, amount in amounts.items():
            target.append(P1Row(
                exhibit=exhibit, fiscal_year=fiscal_year, account=account,
                account_title=_str(account_title), organization=organization,
                budget_activity=ba, budget_activity_title=_str(ba_title),
                pe_bli=pe_bli, title=_str(title), amount_type=amount_type,
                amount_thousands=amount, source_sheet=sheet.title,
                source_cells=tuple(cells[key][amount_type]),
                line_item_code=codes[key],
            ))
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
        verify_r1_restatements(con, parsed)
        return write_p1_rows(con, parsed.rows, source_document_id=source_document_id)
