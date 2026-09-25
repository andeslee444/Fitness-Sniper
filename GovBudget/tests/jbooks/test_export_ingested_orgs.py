"""FIX 1 — data-derived ingested-service-org set (site_meta.ingested_service_orgs).

export_site._ingested_service_orgs is the single source of truth the site reads
to decide the rollup-note wording. It must:

  * include every FY2026 status='downloaded' org THAT LOADED DETAIL,
    TRANSLATED into the budget_lines.organization (workbook) code space via
    workbook_org — because the site keys the note off details.service_org (a
    workbook org), NOT the jbook_documents document org (CYBERCOM→CYBER,
    CHIPS/DPAP→OSD);
  * exclude orgs whose FY2026 book loaded no detail — DHA (its book carries no
    embedded XML), DEFW (a summary line only), IG (no justification book
    published), and any org whose book DOWNLOADED but extracted no detail.
    DHA's, DEFW's and IG's pages state the recorded absence instead
    (site_meta.org_absences, ROADMAP #111), never "not yet ingested";
  * exclude non-2026 / non-downloaded rows.
"""
import psycopg

from govbudget.export_site import _ingested_service_orgs

# pg_dsn / _clean_tables come from tests/jbooks/conftest.py (this module lives
# under tests/jbooks/ so they apply automatically).


def _insert_doc(dsn: str, org: str, *, fiscal_year: int = 2026,
                status: str = "downloaded", with_detail: bool = True) -> int:
    """Insert a jbook_documents row; by default also load one detail row.

    `with_detail=False` is the DHP shape this module now pins: a book that
    DOWNLOADS but whose extract loaded nothing (no .zzz payload, or a schema
    the jb-2009 parser rejects). Such an org must NOT read as ingested —
    otherwise registering a book flips its pages to "the book is ingested,
    this element simply has no narrative" while the corpus holds no
    narrative for ANY of that org's elements.
    """
    # source_url has a UNIQUE constraint — make it distinct per fixture row.
    url = f"https://example.test/{org}-{fiscal_year}-{status}.xlsx"
    with psycopg.connect(dsn, autocommit=True) as con:
        doc_id = con.execute(
            "insert into jbook_documents (org, exhibit_family, fiscal_year,"
            " title, source_url, status) values (%s, 'rollup', %s,"
            " 'fixture.xlsx', %s, %s) returning id",
            (org, fiscal_year, url, status),
        ).fetchone()[0]
        if with_detail:
            run_id = con.execute(
                "insert into extraction_runs (document_id, tier, tool_versions,"
                " status) values (%s, 1, '{}'::jsonb, 'ok') returning id",
                (doc_id,),
            ).fetchone()[0]
            con.execute(
                "insert into budget_line_details (extraction_run_id, document_id,"
                " pe_bli, scenario, amount_millions, xml_path)"
                " values (%s, %s, '0601101X', 'base', 1.0, 'x.xml')",
                (run_id, doc_id),
            )
    return doc_id


def test_ingested_set_includes_agency_books_in_workbook_code_space(pg_dsn):
    # A real slice of the live FY2026 loaded-book org set, spanning the three
    # aliasing cases and the defense-wide agencies that the old hardcoded A/N/F
    # set wrongly excluded.
    for org in ["A", "N", "F", "OSD", "DCSA", "MDA", "DISA", "DARPA",
                "CYBERCOM", "CHIPS", "DPAP", "DoD"]:
        _insert_doc(pg_dsn, org)

    with psycopg.connect(pg_dsn) as con:
        got = _ingested_service_orgs(con)

    # Defense-wide agencies must be present (these are the pages that used to lie).
    for org in ["OSD", "DCSA", "MDA", "DISA", "DARPA"]:
        assert org in got, f"{org} book is loaded — its rollup pages must not say 'not yet ingested'"
    # Services still present.
    for org in ["A", "N", "F"]:
        assert org in got
    # Code-space aliasing: the DOCUMENT orgs CYBERCOM/CHIPS/DPAP land under their
    # WORKBOOK org codes (CYBER / OSD), matching details.service_org.
    assert "CYBER" in got, "CYBERCOM book must map to workbook org CYBER (service_org space)"
    assert "CYBERCOM" not in got, "the document-org spelling must not leak into the set"
    # CHIPS + DPAP both alias to OSD (already asserted present); confirm no stray leak.
    assert "CHIPS" not in got and "DPAP" not in got


def test_ingested_set_excludes_orgs_with_no_loaded_book(pg_dsn):
    # Only these three orgs have a loaded book; DHA/DEFW/IG never get one here.
    for org in ["OSD", "DCSA", "MDA"]:
        _insert_doc(pg_dsn, org)

    with psycopg.connect(pg_dsn) as con:
        got = _ingested_service_orgs(con)

    for org in ["DHA", "DEFW", "IG"]:
        assert org not in got, (
            f"{org} has no loaded FY2026 book — it must stay out of the ingested"
            " set; its pages state the recorded absence (site_meta.org_absences)")


def test_ingested_set_excludes_wrong_year_and_pending_status(pg_dsn):
    _insert_doc(pg_dsn, "OSD")                              # counts
    _insert_doc(pg_dsn, "DHA", fiscal_year=2025)            # wrong year
    _insert_doc(pg_dsn, "IG", status="pending")            # not downloaded

    with psycopg.connect(pg_dsn) as con:
        got = _ingested_service_orgs(con)

    assert got == ["OSD"]


def test_downloaded_book_with_no_loaded_detail_is_not_ingested(pg_dsn):
    """ROADMAP #14 / findings 2026-07-05. The DHP book downloads (3.3 MB,
    HTTP 200) but may carry no jb-2009 .zzz payload, so extract loads
    nothing. 'Downloaded' must not read as 'ingested': the site's sentence
    is about whether a NARRATIVE exists, and a file on disk is not one.

    This is not hypothetical — `DoD` (the 3 R-1/P-1 display workbooks) has
    been in the shipped set with zero detail rows behind it since the
    2026-07-05 fix."""
    _insert_doc(pg_dsn, "OSD")                       # loaded detail -> ingested
    _insert_doc(pg_dsn, "DHA", with_detail=False)    # downloaded only
    _insert_doc(pg_dsn, "DoD", with_detail=False)    # the live precedent

    with psycopg.connect(pg_dsn) as con:
        got = _ingested_service_orgs(con)

    assert got == ["OSD"], (
        "an org whose FY2026 book downloaded but loaded no R-2/P-40 detail must"
        " stay OUT of the set — otherwise every one of its pages says 'the book"
        " is ingested, this element simply has no narrative', which is the"
        " ingested-orgs liar species with a new cause"
    )
