"""Link coverage (overview §7; spec §8 V9) on tiny synthetic site trees."""
import hashlib
import json
from pathlib import Path

import pytest

from govbudget import cli
from govbudget.link_coverage import (
    absolute_violations,
    baseline_from_report,
    compare_to_baseline,
    compute_link_coverage,
)

WB_BYTES = b"stand-in for a pinned comptroller workbook"
WB_SHA = hashlib.sha256(WB_BYTES).hexdigest()
XLSX_URL = "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p1_display.xlsx"
PDF_URL = "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/budget_justification/pdfs/x.pdf"


def fid(n: int) -> str:
    return f"{n:016x}"


def workbook(sha: str = WB_SHA) -> dict:
    return {"kind": "workbook", "sha256": sha, "sheet": "Exhibit P-1", "cells": "J10",
            "official_url": XLSX_URL, "inputs": None}


def derived(*inputs: str) -> dict:
    return {"kind": "derived", "inputs": json.dumps(list(inputs)),
            "formula": "sum(budget_lines.amount_thousands)", "official_url": None}


def receipt(complete: bool) -> dict:
    return {"amount_thousands": 1.0, "matched_amount_thousands": 1.0 if complete else 0.0,
            "complete": complete, "blank_zero_count": 0, "unmatched_count": 0 if complete else 1,
            "parts": []}


def write_site(root: Path, *, citations: dict, receipts: dict, pages: dict,
               audit_sha: str | None = "auto", workbook_bytes: bytes = WB_BYTES) -> Path:
    json_dir = root / "json"
    (json_dir / "program_details").mkdir(parents=True)
    (json_dir / "budget-pdf-receipts" / "v2").mkdir(parents=True)
    (root / "workbooks").mkdir()
    (root / "workbooks" / f"{WB_SHA}.xlsx").write_bytes(workbook_bytes)
    text = json.dumps(citations, sort_keys=True)
    (json_dir / "citations.json").write_text(text)
    shards: dict[str, dict] = {}
    for fact, rec in receipts.items():
        shards.setdefault(fact[:3], {})[fact] = rec
    for prefix, shard in shards.items():
        (json_dir / "budget-pdf-receipts" / "v2" / f"{prefix}.json").write_text(json.dumps(shard))
    for slug, detail in pages.items():
        (json_dir / "program_details" / f"{slug}.json").write_text(json.dumps(detail))
    if audit_sha is not None:
        sha = hashlib.sha256(text.encode()).hexdigest() if audit_sha == "auto" else audit_sha
        (json_dir / "budget_pdf_receipts_audit.json").write_text(json.dumps({"citation_sha256": sha}))
    return root


def page(*, lines=(), decade=(), cards=(), diff=None, recon=None, disc=None, split_lines=()) -> dict:
    """A program sidecar carrying only the budget-figure sections the tool reads."""
    split = None
    if recon or disc or split_lines:
        split = {"reconciliation": {"fid": recon} if recon else None,
                 "disc": {"fid": disc} if disc else None,
                 "lines": [{"fid": f} for f in split_lines] or None}
    return {
        "budget_lines": [{"fact_id": f} for f in lines],
        "decade_series": {"actuals": [{"fid": f} for f in decade]},
        "summary": {"cards": [{"fid": f} for f in cards] + [{"fid": None}]},
        "book_diff": {"fid": diff} if diff else None,
        "fy26_split": split,
        "details": [{"fact_id": fid(999)}],  # J-book detail rows are not budget figures
    }


CITATIONS = {
    fid(1): workbook(),                      # complete receipt -> a
    fid(2): workbook(),                      # partial receipt -> b
    fid(3): workbook(),                      # no receipt -> b
    fid(4): derived(fid(1)),                 # own complete receipt -> a
    fid(5): derived(fid(1), fid(2)),         # weakest input b -> b
    fid(6): derived(fid(1), fid(4)),         # all inputs a -> a
    fid(7): workbook(sha="f" * 64),          # workbook not pinned in workbooks/ -> c
    fid(9): {"kind": "jbook_pdf", "page_number": 3, "x0": 10.0, "official_url": PDF_URL},  # -> a
    fid(10): {"kind": "jbook_pdf", "page_number": None, "x0": None, "official_url": PDF_URL},  # -> c
    fid(11): derived(fid(10), fid(1)),       # weakest input c -> c
    fid(12): {"kind": "derived", "inputs": "[]", "formula": "x", "official_url": None},  # -> d
    fid(13): derived(fid(13)),               # cycle -> d
    fid(14): derived(fid(1), "https://example.gov/source"),  # URL input -> c
    fid(999): {"kind": "jbook_narrative", "page_number": None, "official_url": None},
}
RECEIPTS = {fid(1): receipt(True), fid(2): receipt(False), fid(4): receipt(True)}


def test_each_figure_takes_its_best_link_and_derived_takes_the_weakest_input(tmp_path):
    pages = {
        "AAA": page(lines=[fid(1), fid(2), None], decade=[fid(3)], cards=[fid(9)]),
        "BBB": page(decade=[fid(4)], diff=fid(5), cards=[fid(6)]),
        "CCC": page(disc=fid(7), recon=fid(8), split_lines=[fid(11), fid(12), fid(13), fid(14)]),
    }
    report = compute_link_coverage(write_site(tmp_path, citations=CITATIONS, receipts=RECEIPTS, pages=pages))
    assert report["figures"] == {
        fid(1): "a", fid(2): "b", fid(3): "b", fid(4): "a", fid(5): "b", fid(6): "a",
        fid(7): "c", fid(8): "d", fid(9): "a", fid(11): "c", fid(12): "d", fid(13): "d",
        fid(14): "c", "nofid:AAA:budget_lines:2": "d",
    }
    assert fid(999) not in report["figures"]


def test_scores_count_distinct_figures_per_page_and_site(tmp_path):
    pages = {
        "AAA": page(lines=[fid(1)], cards=[fid(1)], decade=[fid(3)]),  # fid(1) shown twice
        "BBB": page(decade=[fid(4)], cards=[fid(6)]),
    }
    report = compute_link_coverage(write_site(tmp_path, citations=CITATIONS, receipts=RECEIPTS, pages=pages))
    assert report["pages"]["AAA"] == {"figures": 2, "a": 1, "b": 1, "c": 0, "d": 0,
                                      "source_linked": 1.0, "pdf_highlighted": 0.5,
                                      "not_a": {fid(3): "b"}}
    assert report["pages"]["BBB"]["pdf_highlighted"] == 1.0
    site = report["site"]
    assert (site["figures"], site["a"], site["b"], site["c"], site["d"]) == (4, 3, 1, 0, 0)
    assert site["source_linked"] == 1.0 and site["pdf_highlighted"] == 0.75
    assert (site["pages"], site["pages_fully_source_linked"], site["pages_fully_pdf_highlighted"]) == (2, 2, 1)
    assert site["occurrences"]["budget_lines"] == {"a": 1, "b": 0, "c": 0, "d": 0}
    assert site["occurrences"]["summary_cards"] == {"a": 2, "b": 0, "c": 0, "d": 0}
    assert site["occurrences"]["decade_series"] == {"a": 1, "b": 1, "c": 0, "d": 0}
    assert site["receipts_match_citations"] is True and site["workbooks_pinned"] == 1
    assert (site["workbook_citations"], site["workbook_citations_pdf_highlighted"]) == (4, 1)


def test_a_workbook_that_does_not_hash_to_its_name_is_not_pinned(tmp_path):
    pages = {"AAA": page(lines=[fid(1), fid(3)])}
    report = compute_link_coverage(write_site(tmp_path, citations=CITATIONS, receipts=RECEIPTS,
                                              pages=pages, workbook_bytes=b"edited copy"))
    assert report["site"]["workbooks_pinned"] == 0
    assert report["figures"] == {fid(1): "a", fid(3): "c"}  # the receipt still highlights fid(1)


def test_baseline_round_trip_passes_and_new_or_upgraded_figures_are_allowed(tmp_path):
    before = compute_link_coverage(write_site(tmp_path / "s0", citations=CITATIONS, receipts=RECEIPTS,
                                              pages={"AAA": page(lines=[fid(1), fid(2)])}))
    baseline = json.loads(json.dumps(baseline_from_report(before)))
    assert baseline["figures"] == {"a": [fid(1)], "b": [fid(2)], "c": [], "d": []}
    assert baseline["pages_not_fully_pdf_highlighted"] == ["AAA"]
    assert compare_to_baseline(before, baseline) == []
    upgraded = dict(RECEIPTS, **{fid(2): receipt(True)})
    after = compute_link_coverage(write_site(tmp_path / "s4", citations=CITATIONS, receipts=upgraded,
                                             pages={"AAA": page(lines=[fid(1), fid(2)], decade=[fid(4)])}))
    assert compare_to_baseline(after, baseline) == []


def test_losing_a_receipt_or_unpublishing_an_a_figure_is_a_violation(tmp_path):
    before = compute_link_coverage(write_site(tmp_path / "s0", citations=CITATIONS, receipts=RECEIPTS,
                                              pages={"AAA": page(lines=[fid(1)], decade=[fid(4)])}))
    baseline = baseline_from_report(before)
    degraded = dict(RECEIPTS, **{fid(1): receipt(False)})
    after = compute_link_coverage(write_site(tmp_path / "s4", citations=CITATIONS, receipts=degraded,
                                             pages={"AAA": page(lines=[fid(1)])}))
    assert compare_to_baseline(after, baseline) == [
        f"lost PDF receipt: {fid(1)} was (a) in the baseline, now (b)",
        f"lost PDF receipt: {fid(4)} was (a) in the baseline, no longer published",
    ]


def test_unlinked_budget_figures_fail_without_a_baseline(tmp_path):
    report = compute_link_coverage(write_site(tmp_path, citations=CITATIONS, receipts=RECEIPTS,
                                              pages={"CCC": page(lines=[fid(1)], disc=fid(7), recon=fid(8))}))
    assert absolute_violations(report) == [
        f"not source-linked: {fid(7)} is (c) on /program/CCC/",
        f"not source-linked: {fid(8)} is (d) on /program/CCC/",
        "site source-linked share 0.333333 < 1.0: 2 of 3 budget figures are (c) or (d)",
    ]


def test_a_receipt_store_built_for_other_citations_is_a_violation(tmp_path):
    stale = compute_link_coverage(write_site(tmp_path / "stale", citations=CITATIONS, receipts=RECEIPTS,
                                             pages={"AAA": page(lines=[fid(1)])}, audit_sha="0" * 64))
    assert stale["site"]["receipts_match_citations"] is False
    assert absolute_violations(stale) == [
        "receipt store is stale: json/budget_pdf_receipts_audit.json was built for a "
        "different citations.json (re-run export-budget-pdf-receipts)"
    ]
    unaudited = compute_link_coverage(write_site(tmp_path / "none", citations=CITATIONS, receipts=RECEIPTS,
                                                 pages={"AAA": page(lines=[fid(1)])}, audit_sha=None))
    assert unaudited["site"]["receipts_match_citations"] is None
    assert absolute_violations(unaudited) == []


def test_a_hand_edited_or_foreign_baseline_is_refused(tmp_path):
    report = compute_link_coverage(write_site(tmp_path, citations=CITATIONS, receipts=RECEIPTS,
                                              pages={"AAA": page(lines=[fid(1), fid(4)])}))
    baseline = baseline_from_report(report)
    baseline["figures"]["a"].remove(fid(4))
    with pytest.raises(ValueError, match="figures_sha256"):
        compare_to_baseline(report, baseline)
    with pytest.raises(ValueError, match="schema"):
        compare_to_baseline(report, {**baseline_from_report(report), "schema_version": 2})


def test_a_site_dir_without_program_sidecars_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="program sidecars"):
        compute_link_coverage(tmp_path)


def test_cli_writes_a_baseline_then_passes_and_fails_against_it(tmp_path, capsys):
    s0 = write_site(tmp_path / "s0", citations=CITATIONS, receipts=RECEIPTS,
                    pages={"AAA": page(lines=[fid(1), fid(2)])})
    target = tmp_path / "research" / "baseline.json"
    cli.main(["link-coverage", "--site-dir", str(s0), "--write-baseline", str(target)])
    out = capsys.readouterr().out
    assert "link-coverage: 2 budget figures on 1 program pages: a 1 · b 1 · c 0 · d 0;" in out
    assert out.rstrip().endswith("link-coverage: PASS")
    text = target.read_text()
    assert f'"{fid(1)}"' in text.splitlines()  # one fact ID per line: per-figure git diffs
    cli.main(["link-coverage", "--site-dir", str(s0), "--baseline", str(target)])
    assert capsys.readouterr().out.rstrip().endswith("link-coverage: PASS")

    s4 = write_site(tmp_path / "s4", citations=CITATIONS, receipts=dict(RECEIPTS, **{fid(1): receipt(False)}),
                    pages={"AAA": page(lines=[fid(1), fid(2)])})
    with pytest.raises(SystemExit) as exc:
        cli.main(["link-coverage", "--site-dir", str(s4), "--baseline", str(target)])
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert f"  - lost PDF receipt: {fid(1)} was (a) in the baseline, now (b)" in out
    assert out.rstrip().endswith("link-coverage: FAIL")
