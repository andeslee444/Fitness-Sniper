"""A miniature lake for the era-map tests (families piece 1, plan Tasks 11–12).

Layout mirrors the live one: {root}/duckdb/govbudget.duckdb holds
fct_decade_series + dim_programs; {root}/parquet/jbooks/{budget_lines,
documents}.parquet sit beside it (all-varchar, as `jbooks export-facts`
writes them); {root}/raw_docs/fy2026/... holds PB2026 XML and one PDF.

The world (editions 2022–2023 era, 2026 modern):
  ATA000|3010F|      A1 both editions          → R-DEC-ERA-SAME
  3010|1611N|        A1, collision (account)   → SAME pinned 1611N/N
  20|0300D|DTRA      A1, collision (org)       → SAME pinned 0300D/DTRA
  20|0300D|DSS       R2 (DSS has no page)      → review, pre-fill DCSA
  20|0300D|DHRA      A1, collision, no page    → review, pre-fill history_only
  FY2017CR|2031A|    CR                        → EXCLUDE placeholder
  O&M|0390D|         UNSAFE                    → EXCLUDE route-unsafe
  5600D15603|2035A|  H, drift-free             → HISTORY + successor 5731D15610
  F015E0|3010F|      H, drift-free             → HISTORY, no successor
  50|0300D|          H, titles drift           → review
  1045|1612N|        R2 (code under 1611N)     → review

make_lake(..., org_clash=True) adds two organizations printing one code in
one edition, where the page is the other organization's (the live
PB2018 `10`: TJS's page, DPAA's line; PB2017-22 `500`: DLA's page, DCMA's
line). Tests using it set ORG_SPLIT_CODES to {'10', '20'}:
  10|0300D|TJS       A1, not a collision code  → SAME (page 10 is TJS's)
  10|0300D|DPAA      R2, PB2022 beside TJS     → review, pre-fill history_only
  20|0300D|DLA       R2, title = DTRA's page   → review, pre-fill history_only
                                                  pinned to its own 0300D/DLA
"""
from __future__ import annotations

from pathlib import Path

import duckdb

from pdf_factory import make_pdf

BL_COLS = ("exhibit", "fiscal_year", "account", "account_title", "organization",
           "budget_activity", "budget_activity_title", "pe_bli", "title",
           "amount_type", "amount_thousands", "source_document_id",
           "source_sheet", "source_cells", "line_item_code")
DOC_SHA = {"22": "22" * 32, "23": "23" * 32, "26": "26" * 32}

# (edition, account, org, line, code, title, actuals_k, enacted_k)
ERA = [
    (2022, "3010F", "AF", "1", "ATA000", "F-35", "100", "150"),
    (2023, "3010F", "AF", "1", "ATA000", "F-35", "200", "250"),
    (2023, "1611N", "NAVY", "5", "3010", "LPD Flight II", "900", None),
    (2022, "0300D", "DSS", "20", "20", "Major Equipment", "40", None),
    (2022, "0300D", "DTRA", "21", "20", "Vehicles", "30", None),
    (2023, "0300D", "DHRA", "22", "20", "Personnel Administration", "5", None),
    (2022, "2031A", "ARMY", "99", "FY2017CR", "FY 2017 CR Adjustment", None, None),
    (2023, "0390D", "CBDP", "2", "O&M", "Operation & Maintenance", "60", None),
    (2022, "2035A", "ARMY", "7", "5600D15603", "Joint Light Tactical Vehicle", "3000", None),
    (2023, "2035A", "ARMY", "7", "5600D15603", "JOINT LIGHT TACTICAL VEHICLE", "1000", None),
    (2022, "3010F", "AF", "3", "F015E0", "F-15e", "600", None),
    (2023, "3010F", "AF", "4", "F015E0", "F-15e", "20", None),
    (2022, "0300D", "DTRA", "50", "50", "Indian Financing Act", "7", None),
    (2023, "0300D", "DTRA", "50", "50", "DTRA Cyber Activities", None, None),
    (2022, "1612N", "NAVY", "3", "1045", "OHIO Replacement Submarine", "500", None),
]
# (code, account, org, title, actuals_k, has a PB2026 page in dim_programs)
MODERN = [
    ("ATA000", "3010F", "F", "F-35", "250", True),
    ("3010", "1611N", "N", "LPD Flight II", "950", True),
    ("3010", "1810N", "N", "Shipboard Tactical Communications", "20", True),
    ("20", "0300D", "DCSA", "Major Equipment", "45", True),
    ("20", "0300D", "DTRA", "Vehicles", "31", True),
    ("20", "0300D", "DHRA", "Personnel Administration", "6", False),
    ("5731D15610", "2035A", "A", "Joint Light Tactical Vehicle (JLTV)", "900", True),
    ("1045", "1611N", "N", "Columbia Class Submarine", "2000", True),
]
# make_lake(org_clash=True) only
ERA_ORG_CLASH = [
    (2022, "0300D", "TJS", "43", "10", "Major Equipment, TJS", "600", None),
    (2023, "0300D", "TJS", "44", "10", "Major Equipment, TJS", "700", None),
    (2022, "0300D", "DPAA", "22", "10", "Major Equipment, DPAA", "90", None),
    (2022, "0300D", "DLA", "23", "20", "Vehicles", "8", None),
]
MODERN_ORG_CLASH = [
    ("10", "0300D", "TJS", "Major Equipment, TJS", "800", True),
]
JLTV_SENTENCE = (
    "NOTE: This budget line D15610 is a continuation of an existing effort"
    " where prior year funds through FY 2020 are reflected under the previous"
    " budget line D15603."
)
F15_SENTENCE = (
    "This exhibit does not include the eight aircraft in Lot 1 which were"
    " funded outside this exhibit in FY 2020 (two test aircraft were purchased"
    " with RDT&amp;E funds (PE 0207134F); four operationally representative test"
    " aircraft and two operational aircraft were purchased with procurement"
    " funds (F015E0, Line #3))."
)


def era_key(account: str, org: str, line: str) -> str:
    return f"{account}-{org}-L{line}"


def _era_bl_rows(era, blank_code: bool):
    rows = []
    for ed, acct, org, line, code, title, act, enacted in era:
        pe = era_key(acct, org, line)
        for slot, amt in ((f"fy_{ed - 2}_actuals", act or "0"),
                          (f"fy_{ed - 1}_total", enacted or "0")):
            cells = f"O{line}" if slot.endswith("actuals") else f"Q{line}"
            rows.append(("P-1", str(ed), acct, "Acct", org, "01", "BA", pe, title,
                         slot, amt, str(ed - 2000), "Exhibit P-1", cells,
                         "" if blank_code else code))
    return rows


def _modern_bl_rows(modern):
    return [("P-1", "2026", acct, "Acct", org, "01", "BA", code, title,
             "fy_2024_actuals", act, "26", "Exhibit P-1", "O9", code)
            for code, acct, org, title, act, _page in modern]


def _write_parquet(path: Path, cols, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("create table t (" + ", ".join(f'"{c}" varchar' for c in cols) + ")")
    if rows:
        con.executemany("insert into t values (" + ", ".join("?" * len(cols)) + ")", rows)
    con.execute(f"copy t to '{path}' (format parquet)")
    con.close()


def make_lake(root: Path, *, code_column: bool = True, blank_code: bool = False,
              extra_era: list[tuple] = (), org_clash: bool = False) -> Path:
    """Write the miniature lake under root; return the DuckDB path."""
    era = ERA + (ERA_ORG_CLASH if org_clash else [])
    modern = MODERN + (MODERN_ORG_CLASH if org_clash else [])
    cols = BL_COLS if code_column else BL_COLS[:-1]
    rows = _era_bl_rows(era, blank_code) + _modern_bl_rows(modern) + list(extra_era)
    if not code_column:
        rows = [r[:-1] for r in rows]
    _write_parquet(root / "parquet" / "jbooks" / "budget_lines.parquet", cols, rows)
    _write_parquet(
        root / "parquet" / "jbooks" / "documents.parquet",
        ("id", "org", "exhibit_family", "fiscal_year", "title", "source_url",
         "sha256", "bytes", "downloaded_at", "rel_path"),
        [(i, "DOD", "rollup", f"20{i}", "p1_display.xlsx", "https://x.test",
          sha, "1", "2026-01-01", f"fy20{i}/dod/p1_display.xlsx")
         for i, sha in DOC_SHA.items()],
    )
    db = root / "duckdb" / "govbudget.duckdb"
    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    con.execute("create table fct_decade_series (pe_bli varchar, account varchar,"
                " organization varchar, fy integer, edition_year integer,"
                " amount_type_kind varchar, amount double)")
    for ed, acct, org, line, _code, _t, act, enacted in era:
        pe = era_key(acct, org, line)
        if act is not None:
            con.execute("insert into fct_decade_series values (?,null,null,?,?,'actuals',?)",
                        [pe, ed - 2, ed, float(act)])
        if enacted is not None:
            con.execute("insert into fct_decade_series values (?,null,null,?,?,'enacted',?)",
                        [pe, ed - 1, ed, float(enacted)])
    for code, acct, org, _t, act, _page in modern:
        a = acct if code == "3010" else None
        o = org if code == "20" else None
        con.execute("insert into fct_decade_series values (?,?,?,2024,2026,'actuals',?)",
                    [code, a, o, float(act)])
    con.execute("create table dim_programs (pe_bli varchar, account varchar, org varchar)")
    con.executemany("insert into dim_programs values (?,?,?)",
                    [(code, acct, org) for code, acct, org, _t, _a, page in modern
                     if page])
    con.close()
    return db


def make_raw_docs(root: Path) -> Path:
    """PB2026 XML: the JLTV continuation in its own BA1 JB (and in a master
    MJB of another volume, which must lose), F-15's 'funded outside' sentence;
    a sibling PDF printing the JLTV sentence on page 2."""
    raw = root / "raw_docs"
    ba1 = raw / "fy2026" / "a" / "Other Procurement - BA1 - Tactical & Support Vehicles__xml"
    mjb = raw / "fy2026" / "a" / "Other Procurement - BA 3, 4 & 6 - Other__xml"
    af = raw / "fy2026" / "f" / "xml"
    for d in (ba1, mjb, af):
        d.mkdir(parents=True, exist_ok=True)
    body = ("<proc:Justification>JLTV allocations are based on fielding plans.\n\n"
            f"{JLTV_SENTENCE}\n\nIn accordance with Section 1815.</proc:Justification>")
    (ba1 / "U_PROCUREMENT_JB_2506261600ZZZZ_ARMY_PB_2026.xml").write_text(
        "<?xml version='1.0'?>\n<root>\n" + body + "\n</root>\n")
    (mjb / "U_PROCUREMENT_MJB_2506261600XAYF_ARMY_PB_2026.xml").write_text(
        "<?xml version='1.0'?>\n<root>\n\n\n" + body + "\n</root>\n")
    (af / "U_PROCUREMENT_JB_2506261600ZZZZ_AF_PB_2026.xml").write_text(
        f"<?xml version='1.0'?>\n<root><proc:Description>{F15_SENTENCE}"
        "</proc:Description></root>\n")
    make_pdf(ba1.parent / "Other Procurement - BA1 - Tactical & Support Vehicles.pdf", [
        ["Exhibit P-40, Budget Line Item Justification", "Joint Light Tactical Vehicle"],
        ["NOTE: This budget line D15610 is a continuation of an existing effort",
         "where prior year funds through FY 2020 are reflected under the previous",
         "budget line D15603."],
    ])
    return raw
