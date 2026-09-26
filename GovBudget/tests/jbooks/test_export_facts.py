from decimal import Decimal
from pathlib import Path

import duckdb
import psycopg
import pytest

from govbudget.jbooks.export_facts import ChainOrderError, export_facts
from govbudget.jbooks.load_details import load_document_details
from govbudget.jbooks.reconcile import reconcile_document
from govbudget.jbooks.registry import upsert_documents

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "jbooks" / "darpa_fy2026_excerpt.xml"


def _seed_full(pg_dsn, tmp_path):
    """Seed one downloaded document with sha256 + extraction_run + budget_lines + details."""
    upsert_documents(pg_dsn, [{
        "org": "DARPA", "exhibit_family": "rdte", "fiscal_year": 2026,
        "title": "darpa.pdf", "source_url": "https://example.test/darpa.pdf",
    }])
    with psycopg.connect(pg_dsn) as con:
        doc_id = con.execute("select id from jbook_documents").fetchone()[0]
        # Mark as downloaded with sha256
        con.execute(
            "update jbook_documents set status='downloaded', sha256='abc123', file_path=%s"
            " where id=%s",
            (str(tmp_path / "darpa.pdf"), doc_id),
        )
        con.execute(
            "insert into budget_lines (exhibit, fiscal_year, account, organization,"
            " pe_bli, amount_type, amount_thousands, source_document_id)"
            " values ('R-1',2026,'0400','DARPA','0601101E','fy_2024_actuals',%s,%s)",
            (Decimal("280494"), doc_id),
        )
    run_id = load_document_details(pg_dsn, document_id=doc_id, xml_path=FIXTURE)
    reconcile_document(pg_dsn, document_id=doc_id, extraction_run_id=run_id)
    return doc_id


def test_export_facts_writes_parquet(pg_dsn, tmp_path):
    upsert_documents(pg_dsn, [{
        "org": "DARPA", "exhibit_family": "rdte", "fiscal_year": 2026,
        "title": "darpa.pdf", "source_url": "https://example.test/darpa.pdf",
    }])
    with psycopg.connect(pg_dsn) as con:
        doc_id = con.execute("select id from jbook_documents").fetchone()[0]
        # Row WITHOUT source_cells (NULL array) — should export as empty string
        con.execute(
            "insert into budget_lines (exhibit, fiscal_year, account, organization,"
            " pe_bli, amount_type, amount_thousands, source_document_id)"
            " values ('R-1',2026,'0400','DARPA','0601101E','fy_2024_actuals',%s,%s)",
            (Decimal("280494"), doc_id),
        )
        # Row WITH source_cells — should export as comma-joined string
        con.execute(
            "insert into budget_lines (exhibit, fiscal_year, account, organization,"
            " pe_bli, amount_type, amount_thousands, source_cells, source_document_id)"
            " values ('R-1',2026,'0400','DARPA','0601101E','fy_2025_enacted',%s,%s,%s)",
            (Decimal("300000"), ["J4", "J5"], doc_id),
        )
        # Provenance-less orphan row: REJECTED at the schema level since
        # migration 005 (source_document_id NOT NULL — the invariant the
        # export filter used to enforce alone is now structural; the
        # export's IS NOT NULL filter stays as belt-and-braces).
        with pytest.raises(psycopg.errors.NotNullViolation):
            with con.transaction():
                con.execute(
                    "insert into budget_lines (exhibit, fiscal_year, account,"
                    " organization, pe_bli, amount_type, amount_thousands)"
                    " values ('R-1',2026,'0400','DARPA','0601101E','fy_2026_total',%s)",
                    (Decimal("999999"),),
                )
    run_id = load_document_details(pg_dsn, document_id=doc_id, xml_path=FIXTURE)
    reconcile_document(pg_dsn, document_id=doc_id, extraction_run_id=run_id)
    paths = export_facts(pg_dsn, parquet_dir=tmp_path)
    assert [p.name for p in paths] == [
        "announcement_link_reviews.parquet",
        "award_adjudications.parquet",
        "budget_line_awards.parquet",
        "budget_lines.parquet",
        "detail_narratives.parquet",
        "details.parquet",
        "documents.parquet",
        "program_family.parquet",
        "program_lineage.parquet",
    ]
    n = duckdb.sql(
        f"select count(*) from read_parquet('{tmp_path}/jbooks/budget_lines.parquet')"
    ).fetchone()[0]
    assert n == 2, "provenance-less row must not exist, let alone export"
    # NULL source_cells exports as empty string (not NULL)
    no_cells_row = duckdb.sql(
        f"select source_cells from read_parquet('{tmp_path}/jbooks/budget_lines.parquet')"
        " where amount_type='fy_2024_actuals'"
    ).fetchone()[0]
    assert no_cells_row == "", f"Expected empty string for NULL source_cells, got {no_cells_row!r}"
    # Present source_cells exports as comma-joined string
    with_cells_row = duckdb.sql(
        f"select source_cells from read_parquet('{tmp_path}/jbooks/budget_lines.parquet')"
        " where amount_type='fy_2025_enacted'"
    ).fetchone()[0]
    assert with_cells_row == "J4,J5", f"Expected 'J4,J5', got {with_cells_row!r}"
    rec = duckdb.sql(
        f"select count(*) from read_parquet('{tmp_path}/jbooks/details.parquet')"
        " where reconciled"
    ).fetchone()[0]
    assert rec > 0


def test_export_facts_path_with_single_quote(pg_dsn, tmp_path):
    """COPY target path must be escaped so single quotes in tmp dir names don't break SQL."""
    upsert_documents(pg_dsn, [{
        "org": "DARPA", "exhibit_family": "rdte", "fiscal_year": 2026,
        "title": "darpa.pdf", "source_url": "https://example.test/darpa.pdf",
    }])
    with psycopg.connect(pg_dsn) as con:
        doc_id = con.execute("select id from jbook_documents").fetchone()[0]
        con.execute(
            "insert into budget_lines (exhibit, fiscal_year, account, organization,"
            " pe_bli, amount_type, amount_thousands, source_document_id)"
            " values ('R-1',2026,'0400','DARPA','0601101E','fy_2024_actuals',%s,%s)",
            (Decimal("280494"), doc_id),
        )
    run_id = load_document_details(pg_dsn, document_id=doc_id, xml_path=FIXTURE)
    reconcile_document(pg_dsn, document_id=doc_id, extraction_run_id=run_id)

    # Create a parquet_dir whose path contains a single quote
    quoted_dir = tmp_path / "o'brien"
    quoted_dir.mkdir()
    # Must not raise a DuckDB SQL syntax error
    paths = export_facts(pg_dsn, parquet_dir=quoted_dir)
    assert any(p.name == "budget_lines.parquet" for p in paths)
    bl_path = quoted_dir / "jbooks" / "budget_lines.parquet"
    escaped = str(bl_path).replace("'", "''")
    n = duckdb.sql(
        f"select count(*) from read_parquet('{escaped}')"
    ).fetchone()[0]
    assert n == 1


def test_export_facts_includes_provenance_columns(pg_dsn, tmp_path):
    _seed_full(pg_dsn, tmp_path)
    paths = export_facts(pg_dsn, parquet_dir=tmp_path)
    bl_cols = set(duckdb.sql(
        f"select * from read_parquet('{tmp_path}/jbooks/budget_lines.parquet') limit 0"
    ).columns)
    assert {"source_document_id", "source_sheet", "source_cells"} <= bl_cols
    nr_cols = set(duckdb.sql(
        f"select * from read_parquet('{tmp_path}/jbooks/detail_narratives.parquet') limit 0"
    ).columns)
    assert "document_id" in nr_cols
    dt_cols = set(duckdb.sql(
        f"select * from read_parquet('{tmp_path}/jbooks/details.parquet') limit 0"
    ).columns)
    assert "document_sha256" in dt_cols
    doc_cols = set(duckdb.sql(
        f"select * from read_parquet('{tmp_path}/jbooks/documents.parquet') limit 0"
    ).columns)
    assert {"id", "org", "fiscal_year", "title", "source_url", "sha256",
            "downloaded_at", "rel_path"} <= doc_cols


def test_export_facts_writes_the_announcement_link_reviews_contract(pg_dsn, tmp_path):
    """#110 (decided 2026-09-25; R-DEC-110 2026-09-26): the announcement
    path's recorded reviews reach the mart as
    data/parquet/jbooks/announcement_link_reviews.parquet (dbt source
    jbook_announcement_link_reviews), EVERY migration-018 column but the
    table's own recorded_at. The column names are the contract the mart's
    high-tier predicate reads; an empty table still exports a typed,
    zero-row file so the source always resolves."""
    paths = export_facts(pg_dsn, parquet_dir=tmp_path)
    out = tmp_path / "jbooks" / "announcement_link_reviews.parquet"
    assert out in paths
    cols = duckdb.sql(f"select * from read_parquet('{out}') limit 0").columns
    assert cols == [
        "award_piid", "pe_bli", "exhibit", "fiscal_year", "record_kind",
        "reviewer_verdict", "adversarial_verdict", "adversarial_lenses_passed",
        "upholds", "article_id", "article_source", "record_index",
        "entry_index", "cites_reviewed_article", "reason", "reviewed_at",
        "source_file",
    ]
    assert duckdb.sql(f"select count(*) from read_parquet('{out}')").fetchone()[0] == 0

    with psycopg.connect(pg_dsn) as con:
        con.execute(
            "insert into announcement_link_reviews (award_piid, pe_bli, exhibit,"
            " fiscal_year, record_kind, reviewer_verdict, adversarial_verdict,"
            " adversarial_lenses_passed, upholds, article_id, article_source,"
            " record_index, entry_index, cites_reviewed_article, reason,"
            " source_file) values"
            " ('P1','PE1','R-1',2026,'verdict_pair','link','upheld',2,true,'A1',"
            "  'verdict_file',0,0,true,null,"
            "  'data/research/announcements/wave4_verdicts/chunk_000_A.json'),"
            " ('P1','PE1','R-1',2026,'survivor_list','link','upheld',null,true,"
            "  null,null,null,3,null,'owns it',"
            "  'data/research/announcements/wave3_result.json')")
    try:
        export_facts(pg_dsn, parquet_dir=tmp_path)
        got = duckdb.sql(
            f"select record_kind, fiscal_year, upholds, adversarial_lenses_passed,"
            f" article_id, entry_index, reason, reviewed_at"
            f" from read_parquet('{out}')").fetchall()
        # every exported column is varchar (export_facts' one rule): a boolean
        # is Python's str() of it, 'True'/'False', as details.reconciled has
        # always been; a NULL stays NULL, never the string 'None'. Ordered by
        # the table's key (…, source_file, record_kind, entry_index).
        assert got == [
            ("survivor_list", "2026", "True", None, None, "3", "owns it", None),
            ("verdict_pair", "2026", "True", "2", "A1", "0", None, None),
        ]
    finally:
        with psycopg.connect(pg_dsn) as con:
            con.execute("delete from announcement_link_reviews")


def test_export_facts_exports_the_superseded_route(pg_dsn, tmp_path):
    """#140: the route an evidence-graded link replaced on its key (migration
    019) reaches the lake beside the link, so the move is auditable
    downstream and not only in Postgres."""
    with psycopg.connect(pg_dsn) as con:
        con.execute(
            "insert into budget_line_awards (pe_bli, exhibit, fiscal_year,"
            " organization, award_piid, method, confidence, superseded_method,"
            " superseded_confidence, superseded_at, superseded_evidence)"
            " values ('PE1','R-1',2026,'N','P1','fpds-ap','medium',null,null,null,null)")
    paths = export_facts(pg_dsn, parquet_dir=tmp_path)
    out = tmp_path / "jbooks" / "budget_line_awards.parquet"
    assert out in paths
    cols = duckdb.sql(f"select * from read_parquet('{out}') limit 0").columns
    assert cols[-4:] == ["superseded_method", "superseded_confidence",
                         "superseded_at", "superseded_evidence"]


# ── R-DEC-LOADER: migrate -> loader -> backfill -> export-facts -> dbt ─────

def _owned_link(con, created_at):
    con.execute(
        "insert into budget_line_awards (pe_bli, exhibit, fiscal_year,"
        " organization, award_piid, method, confidence, created_at)"
        " values ('PE1','R-1',2026,'N','P1','announcement+lexicon','high',%s)",
        (created_at,))


def _review(con, recorded_at):
    con.execute(
        "insert into announcement_link_reviews (award_piid, pe_bli, exhibit,"
        " fiscal_year, record_kind, reviewer_verdict, adversarial_verdict,"
        " upholds, entry_index, reason, source_file, recorded_at) values"
        " ('P1','PE1','R-1',2026,'survivor_list','link','upheld',true,0,'r',"
        "  'data/research/announcements/wave1_result.json',%s)", (recorded_at,))


@pytest.mark.parametrize(("review_at", "message"), [
    (None, "no announcement_link_reviews row"),
    ("2026-09-26 09:00:00+00", "before the link loader's last run"),
])
def test_export_facts_refuses_reviews_the_loader_has_outrun(
    pg_dsn, tmp_path, review_at, message,
):
    """The mart grades announcement links on the review table; a table the
    backfill wrote BEFORE the loader's last rebuild (or never wrote) would
    grade links it never saw — refused before any file is written."""
    with psycopg.connect(pg_dsn) as con:
        _owned_link(con, "2026-09-26 10:00:00+00")
        if review_at:
            _review(con, review_at)
    try:
        with pytest.raises(ChainOrderError, match=message):
            export_facts(pg_dsn, parquet_dir=tmp_path)
        assert not (tmp_path / "jbooks").exists()
    finally:
        with psycopg.connect(pg_dsn) as con:
            con.execute("delete from announcement_link_reviews")


def test_export_facts_accepts_reviews_backfilled_after_the_loader(pg_dsn, tmp_path):
    with psycopg.connect(pg_dsn) as con:
        _owned_link(con, "2026-09-26 10:00:00+00")
        _review(con, "2026-09-26 10:05:00+00")
    try:
        paths = export_facts(pg_dsn, parquet_dir=tmp_path)
        assert tmp_path / "jbooks" / "announcement_link_reviews.parquet" in paths
    finally:
        with psycopg.connect(pg_dsn) as con:
            con.execute("delete from announcement_link_reviews")


# ── R-DEC-110b: the precision study's refutations are review records ───────

def _refuted_sample(con, adjudicated_at, verdict="refuted", rubric="attribution"):
    con.execute(
        "insert into link_precision_samples (sample_id, award_piid, pe_bli,"
        " method, verdict, reason, adjudicated_at, rubric) values"
        " ('2026-09-12','P1','PE1','announcement+lexicon',%s,'r',%s,%s)",
        (verdict, adjudicated_at, rubric))


def _cleanup(pg_dsn):
    with psycopg.connect(pg_dsn) as con:
        con.execute("delete from announcement_link_reviews")
        con.execute("delete from link_precision_samples")


def test_export_facts_refuses_reviews_older_than_the_last_precision_refutation(
    pg_dsn, tmp_path,
):
    """A refuted attribution verdict loaded AFTER the backfill ran is a
    recorded refutation the review table does not carry: the mart would keep
    a known-refuted link at high. Refused before any file is written."""
    with psycopg.connect(pg_dsn) as con:
        _owned_link(con, "2026-09-26 10:00:00+00")
        _review(con, "2026-09-26 10:05:00+00")
        _refuted_sample(con, "2026-09-26 10:10:00+00")
    try:
        with pytest.raises(ChainOrderError, match="precision"):
            export_facts(pg_dsn, parquet_dir=tmp_path)
        assert not (tmp_path / "jbooks").exists()
    finally:
        _cleanup(pg_dsn)


@pytest.mark.parametrize(("adjudicated_at", "verdict", "rubric"), [
    ("2026-09-26 10:01:00+00", "refuted", "attribution"),   # before the backfill
    ("2026-09-26 10:10:00+00", "confirmed", "attribution"),  # not a refutation
    ("2026-09-26 10:10:00+00", "refuted", "rule-fired"),     # another question
])
def test_export_facts_accepts_reviews_that_carry_every_precision_refutation(
    pg_dsn, tmp_path, adjudicated_at, verdict, rubric,
):
    with psycopg.connect(pg_dsn) as con:
        _owned_link(con, "2026-09-26 10:00:00+00")
        _review(con, "2026-09-26 10:05:00+00")
        _refuted_sample(con, adjudicated_at, verdict, rubric)
    try:
        assert tmp_path / "jbooks" / "announcement_link_reviews.parquet" in (
            export_facts(pg_dsn, parquet_dir=tmp_path))
    finally:
        _cleanup(pg_dsn)


def test_export_facts_carries_precision_sample_rows(pg_dsn, tmp_path):
    """A precision_sample row reaches the lake like any review row: no
    article (it binds to the pair), the sample id as source_file, the
    link_precision_samples row id as entry_index, and a reason whose head
    names the tier the link was drawn from."""
    reason = ("drawn from the announcement+lexicon tier of held-out precision"
              " sample 2026-09-12 (rubric attribution), judged refuted: r")
    with psycopg.connect(pg_dsn) as con:
        con.execute(
            "insert into announcement_link_reviews (award_piid, pe_bli, exhibit,"
            " fiscal_year, record_kind, reviewer_verdict, adversarial_verdict,"
            " upholds, entry_index, reason, source_file) values"
            " ('P1','PE1','R-1',2026,'precision_sample','link','refuted',false,"
            "  379,%s,'2026-09-12')", (reason,))
    try:
        export_facts(pg_dsn, parquet_dir=tmp_path)
        out = tmp_path / "jbooks" / "announcement_link_reviews.parquet"
        got = duckdb.sql(
            f"select record_kind, adversarial_verdict, upholds, article_id,"
            f" cites_reviewed_article, entry_index, reason, source_file"
            f" from read_parquet('{out}')").fetchall()
        assert got == [("precision_sample", "refuted", "False", None, None,
                        "379", reason, "2026-09-12")]
    finally:
        _cleanup(pg_dsn)
