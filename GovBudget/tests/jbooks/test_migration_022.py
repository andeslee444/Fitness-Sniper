"""Migration 022 (#195; families piece-1 follow-ups design §5.6):
provenance_pages.printed_document_sha256, the volume that prints a narrative
row's passage when it is not the attached document.

The session fixture (tests/jbooks/conftest.py) built the test database through
migrate(), so the column and its constraint exist; each test runs in a
transaction that is rolled back.
"""
import psycopg
import pytest

from govbudget.jbooks.db import MIGRATIONS_DIR

SQL_PATH = MIGRATIONS_DIR / "022_provenance_pages_printed_document.sql"
COMMENT = (
    "sha256 of the volume of the same book set that prints this narrative row's"
    " passage, when it is not document_sha256 (#195); page_number and the box"
    " refer to it; null = document_sha256"
)
A, B = "a" * 64, "b" * 64


@pytest.fixture()
def con(pg_dsn):
    with psycopg.connect(pg_dsn) as c:
        yield c
        c.rollback()


def _narrative(con, printed, *, document=A):
    con.execute(
        "insert into provenance_pages (target_kind, document_sha256, pe_bli,"
        " narrative_kind, xml_path, amount_text, resolution, printed_document_sha256)"
        " values ('narrative', %s, 'PE022', 'mission', 'ProgramElement[0]', 'x',"
        " 'unique', %s)", (document, printed))


def test_022_adds_a_commented_nullable_text_column(con):
    assert SQL_PATH.exists()
    assert con.execute(
        "select data_type, is_nullable from information_schema.columns"
        " where table_name = 'provenance_pages'"
        " and column_name = 'printed_document_sha256'"
    ).fetchall() == [("text", "YES")]
    assert con.execute(
        "select col_description('provenance_pages'::regclass, attnum)"
        " from pg_attribute where attrelid = 'provenance_pages'::regclass"
        " and attname = 'printed_document_sha256'"
    ).fetchone()[0] == COMMENT


def test_022_a_narrative_row_may_name_another_volume(con):
    _narrative(con, None)
    _narrative(con, B, document="c" * 64)
    assert con.execute(
        "select count(*) from provenance_pages where printed_document_sha256 = %s", (B,)
    ).fetchone()[0] == 1


@pytest.mark.parametrize("printed", ["b" * 63, "B" * 64, A])
def test_022_the_printing_volume_is_another_lowercase_sha(con, printed):
    with pytest.raises(psycopg.errors.CheckViolation):
        _narrative(con, printed)


def test_022_amount_rows_never_name_a_printing_volume(con):
    with pytest.raises(psycopg.errors.CheckViolation):
        con.execute(
            "insert into provenance_pages (target_kind, document_sha256, pe_bli,"
            " scenario, amount_millions, amount_text, resolution,"
            " printed_document_sha256) values ('amount', %s, 'PE022', 'BY1', 1.0,"
            " '1.000', 'unique', %s)", (A, B))
