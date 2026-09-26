"""R-DEC-SHAREDTITLE, export side (decisions fix round 2).

The ruling makes fct_program_lobbying.program_title name every member of a
shared budget-line code, " / "-joined in (account, organization, title) order
(dbt/models/marts/fct_program_lobbying.sql). /company/ sidecars copy that
column verbatim (export_site's mentions_by_fk); /filing/ pages and a company's
linked-program chips print export_site's own label for the same code
(prog_titles = shared_code_program_label over the dim_programs rows in the
order the export reads them).

The export read dim_programs `order by pe_bli, account` only. On the three
organization-split codes ('20', '30', '500': one account, two or three
organizations) the members tie on that key, so the label's member order was
whatever DuckDB returned — measured 2026-09-26 on the shared lake, read-only:
three consecutive reads gave three different labels for '30' or '500'. The
same filing mention then read "Major Equipment / Personnel Administration" on
/filing/ and "Personnel Administration / Major Equipment" in the company
sidecar. These tests pin the export's member order to the mart's, run the
committed model SQL against the same fixture, and require the two labels to
be the same string for every code.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import duckdb

from govbudget.export_site import _fetch_dim_programs_rows, shared_code_program_label

ROOT = Path(__file__).resolve().parents[1]

# (pe_bli, account, org, title) — the live shapes, deliberately inserted OUT
# of (account, org, title) order so a tie left to the engine shows.
PROGRAMS = [
    ("SOLO", "0400", "DARPA", "Defense Research Sciences"),
    ("1350", "1508N", "N", "Infantry Weapons Ammunition"),
    ("1350", "1507N", "N", "Missile Industrial Facilities"),
    ("30", "0300D", "OSD", "Major Equipment, OSD"),
    ("30", "0300D", "DTRA", "Other Major Equipment"),
    ("30", "0300D", "DMACT", "Major Equipment"),
    ("500", "0300D", "DLA", "Major Equipment"),
    ("500", "0300D", "DHRA", "Personnel Administration"),
    ("20", "0300D", "DTRA", "Vehicles"),
    ("20", "0300D", "DCSA", "Major Equipment"),
    ("2292", "1507N", "N", "Naval Strike Missile (NSM)"),
    ("2292", "1109N", "N", "Naval Strike Missile (NSM)"),
]

MART_LABELS = {
    "SOLO": "Defense Research Sciences",
    "1350": "Missile Industrial Facilities / Infantry Weapons Ammunition",
    "30": "Major Equipment / Other Major Equipment / Major Equipment, OSD",
    "500": "Personnel Administration / Major Equipment",
    "20": "Major Equipment / Vehicles",
    "2292": "Naval Strike Missile (NSM)",
}


def _lake(programs, *, with_in_scope: bool = True) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(
        "create table dim_programs (pe_bli varchar, org varchar,"
        " exhibit_family varchar, title varchar, project_count integer,"
        " fy2024_actual_millions double, fully_reconciled boolean,"
        " account varchar, account_title varchar"
        + (", reconciled_in_scope boolean" if with_in_scope else "") + ")"
    )
    for pe_bli, account, org, title in programs:
        con.execute(
            "insert into dim_programs (pe_bli, org, exhibit_family, title,"
            " project_count, fy2024_actual_millions, fully_reconciled, account,"
            " account_title) values (?, ?, 'procurement', ?, 0, 1.0, true, ?, ?)",
            (pe_bli, org, title, account, f"Account {account}"),
        )
    return con


def _export_labels(con) -> dict[str, str | None]:
    """prog_titles as export_site builds it: every row's title grouped by
    pe_bli in the order the export read the rows, then labelled."""
    by_pe: dict[str, list] = defaultdict(list)
    for r in _fetch_dim_programs_rows(con):
        by_pe[r[0]].append(r[3])
    return {pe: shared_code_program_label(t) for pe, t in by_pe.items()}


def _mart_labels(con) -> dict[str, str | None]:
    """The committed fct_program_lobbying.sql over the same dim_programs, one
    mention per code — the SQL dbt builds, not a restatement."""
    sql = (ROOT / "dbt" / "models" / "marts" / "fct_program_lobbying.sql").read_text()
    for macro, table in {
        "{{ source('influence', 'lda_program_mentions') }}": "mentions",
        "{{ source('influence', 'lda_filings') }}": "filings",
        "{{ ref('dim_programs') }}": "dim_programs",
    }.items():
        sql = sql.replace(macro, table)
    assert "{{" not in sql
    con.execute("create or replace table mentions (filing_uuid varchar, pe_bli varchar,"
                " matched_term varchar, evidence_kind varchar,"
                " description_snippet varchar)")
    con.execute("create or replace table filings (filing_uuid varchar, url varchar,"
                " client_name varchar, family_key_guess varchar,"
                " match_method varchar, filing_year varchar)")
    con.execute("insert into filings values ('F1', 'https://lda.test/F1', 'C',"
                " 'FAM', 'exact_family', '2025')")
    codes = sorted({p[0] for p in PROGRAMS})
    con.executemany("insert into mentions values ('F1', ?, ?, 'pe_literal', 's')",
                    [(c, c) for c in codes])
    return dict(con.execute(
        "select pe_bli, program_title from (" + sql + ")").fetchall())


def test_members_of_one_code_come_back_in_account_then_organization_order():
    rows = _fetch_dim_programs_rows(_lake(PROGRAMS))
    by_pe: dict[str, list] = defaultdict(list)
    for r in rows:
        by_pe[r[0]].append((r[7], r[1], r[3]))  # (account, org, title)
    for pe_bli, members in by_pe.items():
        assert members == sorted(members), (pe_bli, members)


def test_the_export_label_does_not_depend_on_insertion_order():
    forward = _export_labels(_lake(PROGRAMS))
    backward = _export_labels(_lake(list(reversed(PROGRAMS))))
    assert forward == backward


def test_the_filing_label_is_the_marts_company_label_for_every_code():
    """The /filing/ page and the /company/ sidecar name one mention the same
    way: export_site's label equals the mart's program_title on every code,
    including the organization-split ones whose members tie on account."""
    con = _lake(PROGRAMS)
    export = _export_labels(con)
    assert export == MART_LABELS
    assert _mart_labels(con) == export


def test_the_pre_reconciled_in_scope_tier_orders_members_the_same_way():
    """The first fallback query (a dim_programs predating reconciled_in_scope)
    reads the same member order; only the padded column differs."""
    con = _lake(PROGRAMS, with_in_scope=False)
    rows = _fetch_dim_programs_rows(con)
    assert all(len(r) == 10 and r[9] is None for r in rows)
    assert _export_labels(con) == MART_LABELS
