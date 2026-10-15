"""scripts/fu/narrative_relocation_report.py — the release-2 proof's account
of what the #195 relocation changed (families piece-1 follow-ups Task 25a),
on two exports of the synthetic book set: before and after s195 --apply."""
import json

import pytest

from fu.narrative_relocation_report import compare, main  # scripts/ is on sys.path via conftest
from fu.s195_narratives import main as s195
from jbooks.narrative_volumes import seed_book_set, seed_pre_195_rows, xml_path
from jbooks.test_export_site_5f import _export

from govbudget.export_site import fact_id_narrative


@pytest.fixture()
def exports(pg_dsn, tmp_path):
    book = seed_book_set(pg_dsn, tmp_path)
    seed_pre_195_rows(pg_dsn, book)
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    a = _export(pg_dsn, tmp_path / "a")
    assert s195(["--apply", "--pre-image", str(tmp_path / "pre.json"), "--dsn", pg_dsn]) == 0
    b = _export(pg_dsn, tmp_path / "b")
    fid = {key: fact_id_narrative(book["sha"]["BA1"], pe, "mission", xml_path(key))
           for key, pe in (("N1", "0605001TST"), ("N2", "0605002TST"), ("N4", "0605004TST"))}
    return book, a, b, fid


def _tamper(site, fid, **fields):
    path = site / "json" / "citations.json"
    cites = json.loads(path.read_text())
    cites[fid].update(fields)
    path.write_text(json.dumps(cites))


def test_the_relocation_is_accounted_for(pg_dsn, exports, capsys):
    book, a, b, fid = exports
    report = compare(a, b, pg_dsn=pg_dsn, unchanged=[fid["N4"]])
    assert report["violations"] == [] and report["ok"]
    assert report["counts"] == {"narrative_citations": 6, "unchanged": 4, "located": 1, "relocated": 1}
    assert set(report["new_pdfs"]) == {book["sha"]["BA2"], book["sha"]["BA3"]}
    assert report["new_pdf_bytes"] == sum(book["path"][v].stat().st_size for v in ("BA2", "BA3"))
    assert main(["--a", str(a), "--b", str(b), "--pg-dsn", pg_dsn, "--watch", fid["N1"]]) == 0
    out = capsys.readouterr().out
    assert "narrative citations 6: unchanged 4, located 1, relocated 1" in out
    assert out.rstrip().endswith("narrative-relocation: PASS")


def test_a_change_outside_the_location_fields_fails(pg_dsn, exports):
    _book, a, b, fid = exports
    _tamper(b, fid["N1"], xml_path="ProgramElement[9]/Narrative[0]")
    assert any("changed outside the location fields" in v
               for v in compare(a, b, pg_dsn=pg_dsn)["violations"])


def test_a_volume_outside_the_book_set_fails(pg_dsn, exports):
    book, a, b, fid = exports
    navy = book["sha"]["NAVY"]
    _tamper(b, fid["N1"], sha256=navy, hosted_pdf_url=f"https://cdn.example/pdfs/{navy}.pdf#page=2")
    assert any("is not in the book set of" in v for v in compare(a, b, pg_dsn=pg_dsn)["violations"])


def test_losing_a_page_or_a_pdf_fails(pg_dsn, exports):
    book, a, b, fid = exports
    _tamper(b, fid["N4"], page_number=None)
    (b / "pdfs" / f"{book['sha']['BA3']}.pdf").unlink()
    violations = compare(a, b, pg_dsn=pg_dsn, unchanged=[fid["N4"]])["violations"]
    assert f"{fid['N4']}: paged in A, pageless in B" in violations
    assert f"cited PDF {book['sha']['BA3']} is not hosted in B" in violations
    assert f"{fid['N4']} changed but must not" in violations
