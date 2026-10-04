"""scripts/era/s4_report.py — S4 page gain, sidecar stability, receipts (Task 21)."""
import copy
import json

from era.s4_report import (  # scripts/ is on sys.path via conftest
    compare_sidecar,
    main,
    page_class,
    receipt_report,
    sidecar_report,
)


def pt(edition, fid, v=1.0):
    return {"basis": "toa", "edition": edition, "fid": fid, "fy": edition - 2, "measure": "actuals", "v": v}


PROC = {"budget_lines": [{"exhibit": "P-1"}], "lineage": {"family": "x"}, "book_diff": [1],
        "decade_series": {"actuals": [pt(2024, "p24"), pt(2025, "p25")]}}
DECADE_ONLY = {"budget_lines": [], "exhibit_family": "procurement",
               "decade_absent": {"first_edition": 2024, "edition_count": 2},
               "decade_series": {"actuals": [pt(2024, "d24")]}}
RDTE = {"budget_lines": [{"exhibit": "R-1"}], "decade_series": {"actuals": [pt(2017, "r17"), pt(2024, "r24")]}}


def b_sides():
    proc = copy.deepcopy(PROC)
    proc["decade_series"]["actuals"] = [pt(e, f"p{e}") for e in range(2017, 2024)] + PROC["decade_series"]["actuals"]
    decade = copy.deepcopy(DECADE_ONLY)
    decade["decade_series"]["actuals"].insert(0, pt(2019, "d19"))
    decade["decade_absent"] = {"first_edition": 2019, "edition_count": 3}
    return {"P1": proc, "D1": decade, "R1": copy.deepcopy(RDTE)}


def audit(facts, default=67):
    return {"default_cells": 67, "default_complete": default,
            "books": [{"edition": e, "exhibit": "P-1", "facts": facts, "complete": facts} for e in range(2017, 2024)]
            + [{"edition": 2026, "exhibit": "P-1", "facts": 3163, "complete": 3123}]}


def site(root, sidecars, receipts, audit_obj):
    (root / "json" / "program_details").mkdir(parents=True)
    for slug, obj in sidecars.items():
        (root / "json" / "program_details" / f"{slug}.json").write_text(json.dumps(obj))
    v2 = root / "json" / "budget-pdf-receipts" / "v2"
    v2.mkdir(parents=True)
    shards = {}
    for fid, receipt in receipts.items():
        shards.setdefault(fid[:3], {})[fid] = receipt
    for prefix, body in shards.items():
        (v2 / f"{prefix}.json").write_text(json.dumps(body))
    (root / "json" / "budget_pdf_receipts_audit.json").write_text(json.dumps(audit_obj))
    return root


A_RECEIPTS = {"aaa1": {"complete": True}, "aab2": {"complete": False}}
B_RECEIPTS = {"aaa1": {"complete": True}, "aab2": {"complete": True}, "abc3": {"complete": False}}


def test_page_class_reads_decade_only_and_the_exhibit_family():
    assert page_class(PROC) == ("pb2026", "procurement")
    assert page_class(DECADE_ONLY) == ("decade_only", "procurement")
    assert page_class(RDTE) == ("pb2026", "rdte")


def test_gain_is_counted_by_page_kind_with_all_seven_editions(tmp_path):
    a = site(tmp_path / "a", {"P1": PROC, "D1": DECADE_ONLY, "R1": RDTE}, A_RECEIPTS, audit(6))
    b = site(tmp_path / "b", b_sides(), B_RECEIPTS, audit(900))
    report = sidecar_report(a, b)
    assert report["ok"], report["violations"]
    assert report["procurement_pages"] == {"pb2026": 1, "decade_only": 1}
    assert report["gained"] == {"pb2026": 1, "decade_only": 1}
    assert report["all_seven_editions"] == {"pb2026": 1, "decade_only": 0}
    assert report["new_points"] == 8 and report["samples"] == {"pb2026": ["P1"], "decade_only": ["D1"]}


def test_any_change_outside_the_era_points_is_a_violation():
    b = copy.deepcopy(PROC)
    b["lineage"] = {"family": "y"}
    b["decade_series"]["actuals"][0]["v"] = 2.0
    b["decade_series"]["actuals"].append(pt(2026, "p26"))
    b["decade_absent"] = {"first_edition": 2017}
    violations, _ = compare_sidecar("P1", PROC, b)
    assert "P1: lineage changed" in violations
    assert "P1: actuals point p24 changed or removed" in violations
    assert "P1: new actuals point p26 is from PB2026" in violations
    assert "P1: decade_absent appeared or vanished" in violations


def test_an_rdte_page_may_not_gain_points(tmp_path):
    rdte_b = copy.deepcopy(RDTE)
    rdte_b["decade_series"]["actuals"].append(pt(2018, "r18"))
    a = site(tmp_path / "a", {"R1": RDTE}, A_RECEIPTS, audit(6))
    b = site(tmp_path / "b", {"R1": rdte_b}, B_RECEIPTS, audit(900))
    assert sidecar_report(a, b)["violations"] == ["R1: rdte page gained 1 point(s)"]


def test_receipts_keep_every_complete_receipt_and_report_each_era_edition(tmp_path):
    a = site(tmp_path / "a", {}, A_RECEIPTS, audit(6))
    b = site(tmp_path / "b", {}, B_RECEIPTS, audit(900))
    report = receipt_report(a, b)
    assert report["ok"], report["violations"]
    assert report["f15_default"] == "67/67" and report["lost_complete"] == 0
    assert report["era_p1_by_edition"]["2017"] == {"facts": 900, "complete": 900}


def test_receipt_violations(tmp_path):
    a = site(tmp_path / "a", {}, A_RECEIPTS, audit(6))
    lost = site(tmp_path / "lost", {}, {"aab2": {"complete": True}, "aaa1": {"complete": False}}, audit(900, default=66))
    report = receipt_report(a, lost)
    assert "complete receipt lost: aaa1" in report["violations"]
    assert "F-15 default cells 66/67 complete, expected 67/67" in report["violations"]
    flat = site(tmp_path / "flat", {}, B_RECEIPTS, audit(6))
    assert "PB2017 P-1 receipts 6 facts, not more than A's 6" in receipt_report(a, flat)["violations"]


def test_cli_passes_and_fails(tmp_path):
    a = site(tmp_path / "a", {"P1": PROC, "D1": DECADE_ONLY, "R1": RDTE}, A_RECEIPTS, audit(6))
    b = site(tmp_path / "b", b_sides(), B_RECEIPTS, audit(900))
    assert main(["--a", str(a), "--b", str(b), "--report", str(tmp_path / "r.json")]) == 0
    assert json.loads((tmp_path / "r.json").read_text())["sidecars"]["gained"]["pb2026"] == 1
    assert main(["--a", str(b), "--b", str(a)]) == 1
