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


def test_the_export_also_counts_rail_pages_that_no_sidecar_carries(pg_dsn, exports):
    """Task 25b Step 10: the export's `lineage: <k> rail evidence page(s)` count
    walks every block _emit_lineage builds, one per PE an edge touches, but a
    sidecar carries a block only on a page the export writes. An edge whose other
    end has no page (0101101F, 2026-10-15) moves one sidecar entry and two block
    entries, so rail_pages_moved <= k and Step 10 gates on the report alone."""
    from govbudget.export_site import _rail_evidence_pages_from_citations

    _book, a, b, fid = exports
    ca, cb = _cites(a), _cites(b)
    pageless = "0605199TST"
    lineage = {SLUG: {"rail": {"predecessors": [_edge(ca, fid["N1"], pe=pageless)], "successors": []}},
               pageless: {"rail": {"predecessors": [], "successors": [_edge(ca, fid["N1"], pe=SLUG)]}}}

    def rows(cites):
        return [(f, c.get("kind"), None, None, c.get("page_number")) + (None,) * 22 for f, c in cites.items()]

    assert _rail_evidence_pages_from_citations(json.loads(json.dumps(lineage)), rows(ca)) == 0
    _write_rail(a, *lineage[SLUG]["rail"]["predecessors"])
    k = _rail_evidence_pages_from_citations(lineage, rows(cb))
    _write_rail(b, *lineage[SLUG]["rail"]["predecessors"])
    report = compare(a, b, pg_dsn=pg_dsn)
    assert report["violations"] == [] and (report["counts"]["rail_pages_moved"], k) == (1, 2)


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


# Task 25b2: two exports of ONE snapshot differ by run-to-run export noise
# outside the narratives (derived `inputs` and usaspending `query_body`
# reorders; numeric text equal to 12 significant digits). With --noise-from
# the report judges it as scripts/era/fact_stability.py does: proof diff's
# rules, a reorder only when the control vouched for its class.
INPUTS_CLASS = {"path": "json/citations.json", "pointer": "/{fid}/inputs", "count": 1}
REORDERED, FLIPPED = "0123456789abcdef", "fedcba9876543210"  # classes read 16-hex fact IDs as {fid}
DERIVED = {"kind": "derived", "units": "USD thousands", "formula": "sum(budget_lines.amount_thousands)",
           "pe_bli": None}


def _add_noise(a, b):
    for site, inputs, value in ((a, '["w1", "w2"]', "3872766113006.810"),
                                (b, '["w2", "w1"]', "3872766113006.811")):
        path = site / "json" / "citations.json"
        cites = json.loads(path.read_text())
        cites[REORDERED] = {**DERIVED, "recorded_value": "10.000", "inputs": inputs}
        cites[FLIPPED] = {**DERIVED, "recorded_value": value, "inputs": '["w3"]'}
        path.write_text(json.dumps(cites))


def _noise_file(path, *classes):
    from govbudget.proof import NOISE_FILE_SCHEMA, NOISE_POINTER_GENERALISATION, _classes_sha256

    path.write_text(json.dumps({"schema_version": NOISE_FILE_SCHEMA, "verdict": "EQUAL", "a": "B", "b": "B2",
                                "pointer_generalisation": NOISE_POINTER_GENERALISATION,
                                "classes_sha256": _classes_sha256(list(classes), NOISE_POINTER_GENERALISATION),
                                "classes": list(classes)}))
    return path


def test_export_noise_passes_only_with_the_controls_reorder_class(pg_dsn, exports, tmp_path, capsys):
    _book, a, b, _fid = exports
    _add_noise(a, b)
    args = ["--a", str(a), "--b", str(b), "--pg-dsn", pg_dsn]
    assert main(args) == 1
    out = capsys.readouterr().out
    assert f"violation: {REORDERED} (derived): ['inputs'] changed" in out
    assert f"violation: {FLIPPED} (derived): ['recorded_value'] changed" in out
    other = _noise_file(tmp_path / "other.json",
                        {"path": "json/citations.json", "pointer": "/{fid}/query_body", "count": 1})
    assert main(args + ["--noise-from", str(other)]) == 1
    out = capsys.readouterr().out
    assert f"violation: {REORDERED} (derived): ['inputs'] changed" in out
    assert FLIPPED not in out
    assert main(args + ["--noise-from", str(_noise_file(tmp_path / "noise.json", INPUTS_CLASS))]) == 0
    out = capsys.readouterr().out
    assert ("equivalent under proof diff's noise rules: 2 field(s) (inputs 1, recorded_value 1);"
            " reorder classes trusted: [json/citations.json] /{fid}/inputs x1") in out
    assert "violation" not in out and out.rstrip().endswith("narrative-relocation: PASS")
    report = compare(a, b, pg_dsn=pg_dsn, noise_classes=[INPUTS_CLASS])
    assert report["violations"] == [] and report["ok"]
    assert report["noise_equivalent"] == {"inputs": 1, "recorded_value": 1}
    assert report["reorder_classes_trusted"] == [INPUTS_CLASS]
    assert report["counts"] == {"narrative_citations": 6, "unchanged": 4, "located": 1, "relocated": 1,
                                "rail_pages_moved": 0}


REAL_CHANGES = {
    "a value outside the tolerance": (FLIPPED, "recorded_value", "3872766200000.000"),
    "an added list element": (REORDERED, "inputs", '["w2", "w1", "w4"]'),
    "a removed list element": (REORDERED, "inputs", '["w2"]'),
}


@pytest.mark.parametrize("change", sorted(REAL_CHANGES))
def test_a_noise_file_never_excuses_a_real_change(pg_dsn, exports, change):
    _book, a, b, _fid = exports
    _add_noise(a, b)
    fid, field, value = REAL_CHANGES[change]
    _tamper(b, fid, **{field: value})
    assert compare(a, b, pg_dsn=pg_dsn, noise_classes=[INPUTS_CLASS])["violations"] == [
        f"{fid} (derived): ['{field}'] changed"]


def test_a_type_change_is_a_change_not_equality(pg_dsn, exports, capsys):
    """Task 25c2 (#199, as scripts/era/fact_stability.py): the non-narrative
    pre-filter is type-strict, so 1 vs 1.0 is a change, with or without the
    noise file (proof diff's rules never call a type change noise)."""
    _book, a, b, _fid = exports
    for site, amount in ((a, 1), (b, 1.0)):
        path = site / "json" / "citations.json"
        cites = json.loads(path.read_text())
        cites[FLIPPED] = {**DERIVED, "recorded_value": "10.000", "inputs": '["w3"]', "amount_thousands": amount}
        path.write_text(json.dumps(cites))
    assert type(_cites(a)[FLIPPED]["amount_thousands"]) is int
    assert type(_cites(b)[FLIPPED]["amount_thousands"]) is float
    expected = [f"{FLIPPED} (derived): ['amount_thousands'] changed"]
    assert compare(a, b, pg_dsn=pg_dsn)["violations"] == expected
    assert compare(a, b, pg_dsn=pg_dsn, noise_classes=[INPUTS_CLASS])["violations"] == expected
    assert main(["--a", str(a), "--b", str(b), "--pg-dsn", pg_dsn]) == 1
    assert capsys.readouterr().out.rstrip().endswith("narrative-relocation: FAIL")
