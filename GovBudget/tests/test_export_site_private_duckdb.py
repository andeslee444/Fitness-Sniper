"""ROADMAP #172: export_site's readers never go through DuckDB's process-wide
default connection.

`duckdb.sql(...)` runs on ONE connection every module in the process shares.
On DuckDB 1.5.3, a failed statement on it while an earlier result is still
pending leaves it aborted for the rest of the process ("Current transaction is
aborted"), and fourteen export_site reads went through it — several inside
`try/except Exception` blocks that fell back silently (a written parquet's row
count recorded as 0, the paymentaccuracy.gov URL dropped from the improper-
payment citations' inputs, the lobbyist and filing-URL maps left empty). The
integration's Python fixer met exactly this state in the test suite
(test_fiscaldata leaves a pending result; precision_study then fails a query
on purpose). These tests put the default connection in that state and require
the readers to produce the SAME output as on a healthy process, plus a
structural guard so a fifteenth call site cannot come back.
"""
from __future__ import annotations

import ast
import json
from contextlib import contextmanager
from pathlib import Path

import duckdb
import pytest

from govbudget import export_site
from govbudget.export_site import (
    _build_filing_lda_citation_rows,
    _emit_filing_sidecars,
    _export_dim_lobbyists,
    _parquet_row_count,
)

EXPORT_SITE = Path(export_site.__file__)
UUID1 = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
UUID2 = "b2c3d4e5-f6a7-8901-bcde-f12345678901"


@contextmanager
def _aborted_default():
    """The process-wide default connection, aborted the way the suite left it:
    a pending result, then a failing statement. (A merely CLOSED default
    connection is not a failure mode: DuckDB silently opens a new one.)"""
    previous = duckdb.default_connection()
    bad = duckdb.connect()
    duckdb.set_default_connection(bad)
    pending = duckdb.sql("select * from range(5)")
    pending.fetchone()
    with pytest.raises(duckdb.Error):
        duckdb.sql("select * from read_parquet('/nonexistent/x.parquet')").fetchall()
    with pytest.raises(duckdb.TransactionException):
        duckdb.sql("select 42").fetchall()
    try:
        yield
    finally:
        duckdb.set_default_connection(previous)
        bad.close()


@pytest.fixture()
def aborted_default_connection():
    with _aborted_default():
        yield


def _write_parquet(path: Path, ddl: str, rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        con.execute(f"create table t ({ddl})")
        if rows:
            ph = ",".join("?" for _ in rows[0])
            con.executemany(f"insert into t values ({ph})", rows)
        con.execute(f"copy t to '{path}' (format parquet)")
    finally:
        con.close()


def _lda_fixture(tmp_path: Path) -> Path:
    """An empty warehouse plus the three influence parquets the LDA readers
    read, in the test layout `_stage_parquet_path` probes first."""
    db = tmp_path / "govbudget.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        "create table dim_lobbyists (name varchar, covered_position varchar,"
        " filings_count integer, revolving_door boolean)")
    con.execute("insert into dim_lobbyists values"
                " ('JANE ROE', 'Staff, SASC', 2, true),"
                " ('JOHN DOE', 'N/A', 1, false)")
    con.close()
    inf = tmp_path / "parquet" / "influence"
    _write_parquet(
        inf / "lda_filings.parquet",
        "filing_uuid varchar, url varchar, client_name varchar,"
        " registrant_name varchar, filing_year varchar, filing_period varchar,"
        " filing_type varchar, income_usd varchar, expenses_usd varchar",
        [
            (UUID1, f"https://lda.senate.gov/api/v1/filings/{UUID1}/", "ACME",
             "REG A", "2025", "Q1", "Q1", "50000", ""),
            (UUID2, f"https://lda.senate.gov/api/v1/filings/{UUID2}/", "BETA",
             "REG B", "2025", "Q2", "Q2", "", "30000"),
        ],
    )
    _write_parquet(
        inf / "lda_activities.parquet",
        "filing_uuid varchar, issue_code varchar, issue_display varchar,"
        " description varchar",
        [(UUID1, "DEF", "Defense", "Research sciences"),
         (UUID2, "BUD", "Budget", "Appropriations")],
    )
    _write_parquet(
        inf / "lda_lobbyists.parquet",
        "filing_uuid varchar, name varchar, covered_position varchar",
        [(UUID1, "JANE ROE", "Staff, SASC"), (UUID2, "JOHN DOE", "N/A")],
    )
    return db


# ---------------------------------------------------------------------------
# The structural guard
# ---------------------------------------------------------------------------


def test_export_site_never_calls_the_duckdb_module_default_connection():
    """Every DuckDB call in export_site goes through a connection it opened.

    The module object's `sql`/`query`/`execute`/`read_parquet`/… all run on
    the shared default connection; only `connect` (and exception classes,
    which are not calls) may be reached through the module.
    """
    tree = ast.parse(EXPORT_SITE.read_text())
    aliases = {"duckdb"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "duckdb":
                    aliases.add(a.asname or "duckdb")
    offenders = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in aliases
                and node.func.attr != "connect"):
            offenders.append(f"export_site.py:{node.lineno} "
                             f"{node.func.value.id}.{node.func.attr}(…)")
    assert offenders == [], (
        "these run on DuckDB's process-wide default connection (ROADMAP "
        "#172) — open a private one (`_private_duckdb()`):\n"
        + "\n".join(offenders))


# ---------------------------------------------------------------------------
# A broken default connection changes no reader's output
# ---------------------------------------------------------------------------


def test_filing_citation_rows_survive_an_aborted_default_connection(
    tmp_path, aborted_default_connection
):
    db = _lda_fixture(tmp_path)
    got = _build_filing_lda_citation_rows(duckdb_path=db)
    assert len(got) == 2, "one income row (UUID1) and one expenses row (UUID2)"


def test_filing_citation_rows_match_a_healthy_process(tmp_path):
    db = _lda_fixture(tmp_path)
    healthy = _build_filing_lda_citation_rows(duckdb_path=db)
    with _aborted_default():
        broken = _build_filing_lda_citation_rows(duckdb_path=db)
    assert healthy and broken == healthy


def test_filing_sidecars_survive_an_aborted_default_connection(
    tmp_path, aborted_default_connection
):
    db = _lda_fixture(tmp_path)
    json_dir = tmp_path / "json"
    json_dir.mkdir()
    n = _emit_filing_sidecars(json_dir=json_dir, duckdb_path=db, lob_rows=[],
                              prog_titles={}, cited_fact_ids=set())
    assert n == 3, "two per-filing sidecars and the index"
    one = json.loads((json_dir / "filings" / f"{UUID1}.json").read_text())
    assert [a["issue_code"] for a in one["activities"]] == ["DEF"]
    assert [lb["name"] for lb in one["lobbyists"]] == ["JANE ROE"]


def test_dim_lobbyists_keeps_its_disclosing_filings_on_an_aborted_connection(
    tmp_path, aborted_default_connection
):
    db = _lda_fixture(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    con = duckdb.connect(str(db), read_only=True)
    try:
        rows = _export_dim_lobbyists(con=con, duckdb_path=db, data_dir=data_dir)
    finally:
        con.close()
    by_name = {r[0]: r for r in rows}
    assert by_name["JANE ROE"][4] == UUID1
    assert by_name["JANE ROE"][5] == f"https://lda.senate.gov/api/v1/filings/{UUID1}/"
    assert by_name["JOHN DOE"][4] == UUID2


def test_the_parquet_row_count_survives_an_aborted_connection(
    tmp_path, aborted_default_connection
):
    """site_meta.datasets used to record a written parquet as 0 rows when the
    count failed; the count now runs privately and a failure raises."""
    pq = tmp_path / "x.parquet"
    _write_parquet(pq, "a integer", [(1,), (2,), (3,)])
    assert _parquet_row_count(pq) == 3
    bad = tmp_path / "bad.parquet"
    bad.write_bytes(b"not a parquet file")
    with pytest.raises(duckdb.Error):
        _parquet_row_count(bad)


# ---------------------------------------------------------------------------
# A guarded read that still falls back says what it dropped
# ---------------------------------------------------------------------------


def test_a_dropped_lobbyist_map_is_reported_not_silent(tmp_path, capsys):
    db = _lda_fixture(tmp_path)
    (tmp_path / "parquet" / "influence" / "lda_lobbyists.parquet").write_bytes(
        b"not a parquet file")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    con = duckdb.connect(str(db), read_only=True)
    try:
        rows = _export_dim_lobbyists(con=con, duckdb_path=db, data_dir=data_dir)
    finally:
        con.close()
    assert all(r[4] is None for r in rows), "the map really was dropped"
    out = capsys.readouterr().out
    assert "export-site: WARNING" in out
    assert "lda_lobbyists.parquet" in out
