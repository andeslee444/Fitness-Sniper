import os

import psycopg
import pytest

ADMIN_DSN = os.environ.get("GOVBUDGET_TEST_PG_DSN", "postgresql://localhost/postgres")
TEST_DB = "govbudget_test"


@pytest.fixture(scope="session")
def pg_dsn():
    try:
        admin = psycopg.connect(ADMIN_DSN, autocommit=True)
    except psycopg.OperationalError as e:
        pytest.skip(f"Postgres unavailable ({e}); start local postgres to run jbooks tests")
    admin.execute(f"drop database if exists {TEST_DB}")
    admin.execute(f"create database {TEST_DB}")
    admin.close()
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(ADMIN_DSN)
    dsn = urlunsplit(parts._replace(path="/" + TEST_DB))

    from govbudget.jbooks.db import migrate

    migrate(dsn)
    yield dsn


@pytest.fixture()
def pg(pg_dsn):
    import psycopg

    with psycopg.connect(pg_dsn) as con:
        yield con
        con.rollback()


@pytest.fixture()
def doc_id(pg_dsn):
    """A jbook_documents row id for loader provenance (migration 005 made
    budget_lines.source_document_id NOT NULL — loaders require it)."""
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        return con.execute(
            "insert into jbook_documents (org, exhibit_family, fiscal_year,"
            " title, source_url, status) values ('DOD', 'rollup', 2026,"
            " 'fixture_display.xlsx', 'https://example.test/fixture.xlsx',"
            " 'downloaded') returning id"
        ).fetchone()[0]


@pytest.fixture(autouse=True)
def _clean_tables(request):
    """Truncate Phase 1 tables after any test that actually used the DB.

    Resolves pg_dsn only for tests that requested it, so DB-free tests
    (parser, attachments) never trigger the Postgres session fixture.
    """
    uses_db = "pg_dsn" in request.fixturenames
    dsn = request.getfixturevalue("pg_dsn") if uses_db else None
    yield
    if dsn:
        with psycopg.connect(dsn, autocommit=True) as con:
            con.execute(
                "truncate jbook_documents, budget_lines, extraction_runs, budget_line_details, "
                "detail_narratives, reconciliation_checks, review_queue, extraction_gaps,"
                " budget_line_awards, provenance_pages restart identity cascade"
            )


@pytest.fixture()
def single_failure_doc(pg_dsn):
    """A DARPA FY2026 rdte document loaded from the fixture XML, with the four
    R-1 control rows of test_reconcile.py:461-466 — which make every fixture
    check pass — except 0601101E/PriorYear, whose control is deliberately
    999999 $K against the XML's 280.494M. Exactly one Gate B failure
    (expected=999.999, actual=280.494). Returns (document_id, run_id) of the
    first extraction run."""
    from decimal import Decimal
    from pathlib import Path

    from govbudget.jbooks.load_details import load_document_details
    from govbudget.jbooks.registry import upsert_documents

    fixture = (
        Path(__file__).resolve().parents[1]
        / "fixtures" / "jbooks" / "darpa_fy2026_excerpt.xml"
    )
    upsert_documents(pg_dsn, [{
        "org": "DARPA", "exhibit_family": "rdte", "fiscal_year": 2026,
        "title": "darpa.pdf", "source_url": "https://example.test/darpa.pdf",
    }])
    with psycopg.connect(pg_dsn) as con:
        doc_id = con.execute(
            "select id from jbook_documents where source_url='https://example.test/darpa.pdf'"
        ).fetchone()[0]
        for pe, amount_type, amt in (
            ("0601101E", "fy_2024_actuals", Decimal("999999")),   # wrong -> the one failure
            ("0601101E", "fy_2025_total", Decimal("293145")),
            ("0601117E", "fy_2024_actuals", Decimal("55913")),
            ("0601117E", "fy_2025_total", Decimal("89143")),
        ):
            con.execute(
                "insert into budget_lines (exhibit, fiscal_year, account, organization,"
                " pe_bli, amount_type, amount_thousands, source_document_id)"
                " values ('R-1',2026,'0400','DARPA',%s,%s,%s,%s)",
                (pe, amount_type, amt, doc_id),
            )
    run_id = load_document_details(pg_dsn, document_id=doc_id, xml_path=fixture)
    return doc_id, run_id
