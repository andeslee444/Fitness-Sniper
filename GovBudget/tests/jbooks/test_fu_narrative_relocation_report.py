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


def _cites(site):
    return json.loads((site / "json" / "citations.json").read_text())


SLUG, OTHER = "0605101TST", "0605102TST"


def _edge(cites, fid, **fields):
    """A stated predecessor rail entry (export_site._emit_lineage's shape) whose
    evidence is narrative fid, on the page its citation in `cites` names."""
    return {"pe": "0605100TST", "title": "Alpha Radar (old line)", "ba": "BA 5", "fy": 2026,
            "relation": "renamed", "confidence": "stated", "resolved": True,
            "evidence": {"fact_id": fid, "page": cites[fid]["page_number"],
                         "sentence": "The Alpha program fields a new radar for the fleet."},
            **fields}


def _rail(cites, fid):
    """N1 is relocated (its page moves with the citation); N4 is kept."""
    return [_edge(cites, fid["N1"]), _edge(cites, fid["N4"], pe=OTHER)]


def _write_rail(site, *predecessors, slug=SLUG):
    path = site / "json" / "program_details" / f"{slug}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    sidecar = json.loads(path.read_text()) if path.exists() else {"pe_bli": slug}
    sidecar["lineage"] = {"rail": {"predecessors": list(predecessors), "successors": []}}
    path.write_text(json.dumps(sidecar))


def test_the_relocation_is_accounted_for(pg_dsn, exports, capsys):
    book, a, b, fid = exports
    report = compare(a, b, pg_dsn=pg_dsn, unchanged=[fid["N4"]])
    assert report["violations"] == [] and report["ok"]
    assert report["counts"] == {"narrative_citations": 6, "unchanged": 4, "located": 1, "relocated": 1,
                                "rail_pages_moved": 0}
    assert set(report["new_pdfs"]) == {book["sha"]["BA2"], book["sha"]["BA3"]}
    assert report["new_pdf_bytes"] == sum(book["path"][v].stat().st_size for v in ("BA2", "BA3"))
    assert main(["--a", str(a), "--b", str(b), "--pg-dsn", pg_dsn, "--watch", fid["N1"]]) == 0
    out = capsys.readouterr().out
    assert "narrative citations 6: unchanged 4, located 1, relocated 1" in out
    assert "rail evidence pages moved: 0" in out
    assert out.rstrip().endswith("narrative-relocation: PASS")


def test_a_rail_page_that_follows_its_citation_passes(pg_dsn, exports, capsys):
    _book, a, b, fid = exports
    _write_rail(a, *_rail(_cites(a), fid))
    _write_rail(b, *_rail(_cites(b), fid))
    report = compare(a, b, pg_dsn=pg_dsn)
    assert report["violations"] == [] and report["counts"]["rail_pages_moved"] == 1
    assert main(["--a", str(a), "--b", str(b), "--pg-dsn", pg_dsn]) == 0
    assert "rail evidence pages moved: 1" in capsys.readouterr().out


RAIL_CHANGES = {
    "an edge dropped": lambda c, fid: [_edge(c, fid["N1"])],
    "an edge added": lambda c, fid: [*_rail(c, fid), _edge(c, fid["N2"], pe="0605103TST")],
    "relation": lambda c, fid: [_edge(c, fid["N1"], relation="split"), _edge(c, fid["N4"], pe=OTHER)],
    "fy": lambda c, fid: [_edge(c, fid["N1"], fy=2027), _edge(c, fid["N4"], pe=OTHER)],
    "confidence": lambda c, fid: [_edge(c, fid["N1"], confidence="inferred"),
                                  _edge(c, fid["N4"], pe=OTHER)],
    "evidence.fact_id": lambda c, fid: [_edge(c, fid["N2"]), _edge(c, fid["N4"], pe=OTHER)],
}


@pytest.mark.parametrize("change", sorted(RAIL_CHANGES))
def test_a_rail_change_beyond_evidence_pages_fails(pg_dsn, exports, change):
    _book, a, b, fid = exports
    _write_rail(a, *_rail(_cites(a), fid))
    _write_rail(b, *RAIL_CHANGES[change](_cites(b), fid))
    assert compare(a, b, pg_dsn=pg_dsn)["violations"] == [f"rail of {SLUG} changed beyond evidence pages"]


def test_a_rail_on_one_side_only_or_off_its_citation_fails(pg_dsn, exports):
    _book, a, b, fid = exports
    ca, cb = _cites(a), _cites(b)
    _write_rail(a, *_rail(ca, fid))
    _write_rail(a, _edge(ca, fid["N4"]), slug="0605104TST")
    _write_rail(b, _edge(cb, fid["N1"]), _edge(cb, fid["N4"], pe=OTHER, evidence={
        "fact_id": fid["N4"], "page": 3, "sentence": "The Alpha program fields a new radar for the fleet."}))
    _write_rail(b, _edge(cb, fid["N4"]), slug="0605105TST")
    assert cb[fid["N4"]]["page_number"] != 3
    assert sorted(compare(a, b, pg_dsn=pg_dsn)["violations"]) == sorted([
        "rail of 0605104TST only in A", "rail of 0605105TST only in B",
        f"rail evidence {fid['N4']} on {SLUG}: page 3 is not its citation's page"])


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
