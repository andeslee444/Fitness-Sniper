"""verify-jbook-narratives (#195; families piece-1 follow-ups Task 24): every
jbook_narrative citation names a document that prints the passage. Exports the
synthetic book set (tests/jbooks/narrative_volumes.py) before and after the
#195 relocation and checks the export."""
import duckdb
import psycopg
import pytest

from fu.s195_narratives import main as s195  # scripts/ is on sys.path via conftest
from govbudget import cli
from govbudget.verify_jbook_narratives import (
    OPENING_ONLY_CEILING,
    PAGELESS_OPENING_SEEN_CEILING,
    format_report,
    verify_jbook_narratives,
)
from jbooks.narrative_volumes import seed_book_set, seed_pre_195_rows
from jbooks.test_export_site_5f import _export


def _site(pg_dsn, tmp_path, *, relocate):
    book = seed_book_set(pg_dsn, tmp_path)
    seed_pre_195_rows(pg_dsn, book)
    if relocate:
        assert s195(["--apply", "--pre-image", str(tmp_path / "pre.json"), "--dsn", pg_dsn]) == 0
    return book, _export(pg_dsn, tmp_path)


def _check(site, pg_dsn, **ceilings):
    return verify_jbook_narratives(site, pg_dsn=pg_dsn, **{
        "opening_only_ceiling": 1, "opening_seen_ceiling": 0, **ceilings})


def _fid_of(site, pe_bli):
    narr = site / "data" / "jbook_narratives.parquet"
    return duckdb.sql(f"select fact_id from read_parquet('{narr}') where pe_bli = '{pe_bli}'").fetchone()[0]


def test_the_ceilings_are_the_measured_counts():
    assert (OPENING_ONLY_CEILING, PAGELESS_OPENING_SEEN_CEILING) == (111, 77)


def test_the_pre_195_export_fails(pg_dsn, tmp_path):
    book, site = _site(pg_dsn, tmp_path, relocate=False)
    report = _check(site, pg_dsn)
    assert not report["ok"]
    assert report["counts"] == {"citations": 6, "paged": 3, "printed": 1, "opening_only": 2,
                                "pageless": 3, "opening_seen": 0, "opening_nowhere": 2}
    reasons = dict(report["failures"])
    assert reasons[_fid_of(site, "0605002TST")] == (
        f"pageless, but located at {book['sha']['BA3']} page 1")
    assert reasons["*"] == "2 opening-only paged citations, above the ceiling of 1"


def test_the_relocated_export_passes(pg_dsn, tmp_path):
    _book, site = _site(pg_dsn, tmp_path, relocate=True)
    report = _check(site, pg_dsn)
    assert report["failures"] == [] and report["ok"]
    assert report["counts"] == {"citations": 6, "paged": 4, "printed": 3, "opening_only": 1,
                                "pageless": 2, "opening_seen": 0, "opening_nowhere": 2}
    assert report["opening_only"] == [_fid_of(site, "0605005TST")]
    assert format_report(report)[0] == (
        "narrative citations 6: paged 4 (printed 3, opening_only 1 of at most 1);"
        " pageless 2 (opening printed without its closing 0 of at most 0, opening"
        " printed nowhere 2)")


def test_the_opening_only_count_is_a_ratchet(pg_dsn, tmp_path):
    _book, site = _site(pg_dsn, tmp_path, relocate=True)
    report = _check(site, pg_dsn, opening_only_ceiling=0)
    assert report["failures"] == [("*", "1 opening-only paged citations, above the ceiling of 0")]


def test_a_pageless_opening_without_its_closing_is_counted_and_ratcheted(pg_dsn, tmp_path):
    book = seed_book_set(pg_dsn, tmp_path)
    seed_pre_195_rows(pg_dsn, book)
    with psycopg.connect(pg_dsn, autocommit=True) as con:
        con.execute("update provenance_pages set page_number = null, x0 = null, x1 = null,"
                    " top_pt = null, bottom_pt = null, page_width = null, page_height = null,"
                    " resolution = 'unresolved' where pe_bli = '0605005TST'")
    assert s195(["--apply", "--pre-image", str(tmp_path / "pre.json"), "--dsn", pg_dsn]) == 0
    site = _export(pg_dsn, tmp_path)
    report = _check(site, pg_dsn, opening_seen_ceiling=1)
    assert report["ok"] and report["opening_seen"] == [_fid_of(site, "0605005TST")]
    assert _check(site, pg_dsn)["failures"] == [
        ("*", "1 pageless citations with their opening printed, above the ceiling of 0")]


def test_a_page_that_does_not_print_the_opening_fails(pg_dsn, tmp_path):
    _book, site = _site(pg_dsn, tmp_path, relocate=True)
    fid = _fid_of(site, "0605004TST")
    pq = site / "citations" / "citations.parquet"
    con = duckdb.connect()
    con.execute(f"create table c as select * from read_parquet('{pq}')")
    con.execute("update c set page_number = 1,"
                " hosted_pdf_url = replace(hosted_pdf_url, '#page=2', '#page=1'),"
                " official_url = replace(official_url, '#page=2', '#page=1')"
                " where fact_id = ?", [fid])
    con.execute(f"copy c to '{pq}' (format parquet)")
    con.close()
    reasons = dict(_check(site, pg_dsn)["failures"])
    assert reasons[fid].startswith("opening not printed on page 1")


def test_an_unhosted_or_altered_volume_fails(pg_dsn, tmp_path):
    book, site = _site(pg_dsn, tmp_path, relocate=True)
    (site / "pdfs" / f"{book['sha']['BA2']}.pdf").unlink()
    (site / "pdfs" / f"{book['sha']['BA3']}.pdf").write_bytes(b"%PDF-1.4 altered")
    reasons = dict(_check(site, pg_dsn)["failures"])
    assert reasons[_fid_of(site, "0605001TST")] == f"cited PDF {book['sha']['BA2']} is not hosted in pdfs/"
    assert reasons[_fid_of(site, "0605002TST")].startswith("sha256 mismatch:")


def test_a_missing_input_is_a_tool_error(pg_dsn, tmp_path):
    with pytest.raises(FileNotFoundError):
        verify_jbook_narratives(tmp_path / "nowhere", pg_dsn=pg_dsn)


def test_cli_exit_codes(pg_dsn, tmp_path, capsys):
    _book, site = _site(pg_dsn, tmp_path, relocate=False)
    argv = ["verify-jbook-narratives", "--site-dir", str(site), "--pg-dsn", pg_dsn]
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    out = capsys.readouterr().out.splitlines()
    assert exc.value.code == 1 and out[-1] == "verify-jbook-narratives: FAIL"
    with pytest.raises(SystemExit) as exc:
        cli.main(["verify-jbook-narratives", "--site-dir", str(tmp_path / "x"), "--pg-dsn", pg_dsn])
    assert exc.value.code == 2
    assert capsys.readouterr().out.startswith("verify-jbook-narratives: ERROR — ")


def test_verify_phase5b1_runs_it_as_gate_5(monkeypatch, capsys):
    import govbudget.verify_jbook_narratives as vjn
    import govbudget.verify_phase5b1 as v

    monkeypatch.setattr(v, "citation_gate5b1", lambda site: {
        "ok": True, "sampled": 1, "passed": 1, "failures": [], "row_label": {}})
    monkeypatch.setattr(v, "integrity_gate5b1", lambda site: {"ok": True, "checks": {}, "failures": []})
    monkeypatch.setattr(v, "narrative_gate5b1", lambda site: {
        "ok": True, "narrative_total": 1, "resolved_total": 1, "sampled": 1, "passed": 1,
        "failures": []})
    monkeypatch.setattr(v, "coverage_report5b1", lambda site: {})
    report = {"ok": False, "counts": {"citations": 1, "paged": 1, "printed": 0,
                                      "opening_only": 0, "pageless": 0, "opening_seen": 0,
                                      "opening_nowhere": 0},
              "ceilings": {"opening_only": 111, "opening_seen": 77},
              "failures": [("f1", "opening not printed on page 3: 'x'")]}
    monkeypatch.setattr(vjn, "verify_jbook_narratives", lambda site, **kw: report)
    with pytest.raises(SystemExit) as exc:
        cli.main(["verify-phase5b1"])
    out = capsys.readouterr().out
    assert exc.value.code == 1
    assert "gate 5 narrative printed-in: → FAIL" in out
    assert "  FAIL f1: opening not printed on page 3: 'x'" in out
    report["ok"], report["failures"] = True, []
    with pytest.raises(SystemExit) as exc:
        cli.main(["verify-phase5b1"])
    assert exc.value.code == 0 and "gate 5 narrative printed-in: → PASS" in capsys.readouterr().out
