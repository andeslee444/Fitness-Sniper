"""The release-1 expected-difference file (follow-ups Task 21c / 22c): what the
release-state check lets through.

Design §8 step 4 says the release export may differ from B@fu-post only by SAM
registrations the hourly job stored after the proof snapshot ("what ships is
what was proven"). The company-page rule must therefore excuse a company
sidecar's `sam` block and nothing else in it: a change at /awards, /influence,
/linked_programs or /mentions has to stop the release. These tests run the real
rule file over miniature `json/entity_details/` trees, so a rule that goes back
to matching a whole sidecar fails here, not on the owner's release night.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from govbudget import proof

ROOT = Path(__file__).resolve().parents[1]
RELEASE_RULES = (ROOT / "docs" / "superpowers" / "plans"
                 / "2026-10-04-families-piece1-followups" / "expected-diff-release.json")
SIDECAR = "json/entity_details/ACME.json"
BARE_SIDECAR = "json/entity_details/BARE.json"   # a company with no SAM registration yet

SAM_BLOCK = {"uei": "UEI000000001", "legal_name": "ACME CORP", "status": "Active",
             "naics": ["336411", "541715"]}


def _write(root: Path, docs: dict[str, dict]) -> None:
    for rel, doc in docs.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")


def _company(**overrides) -> dict:
    """A company sidecar with the five top-level keys the 200 real ones carry."""
    doc = {
        "awards": {"total": 1000, "by_year": [{"fy": 2025, "amount": 400}, {"fy": 2026, "amount": 600}]},
        "influence": {"lobbying_total": 70},
        "linked_programs": [{"program_key": "0603000D8Z"}],
        "mentions": [{"title": "A hearing"}],
        "sam": dict(SAM_BLOCK),
    }
    doc.update(overrides)
    return doc


def _release_verdict(tmp_path: Path, b_docs: dict[str, dict]) -> tuple[dict, list[dict], int]:
    """Diff the baseline tree (one company with a SAM block, one without) against
    `b_docs` under the real release rules; return the verdict, the rules and the
    index of the company-page rule."""
    _write(tmp_path / "a", {SIDECAR: _company(), BARE_SIDECAR: _bare()})
    _write(tmp_path / "b", b_docs)
    rules = proof.load_expectations(RELEASE_RULES)
    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    verdict = proof.check_expectations(report, rules)
    company_rule = next(i for i, r in enumerate(rules) if r["path"] == "json/entity_details/*.json")
    return verdict, rules, company_rule


def _bare() -> dict:
    doc = _company()
    doc.pop("sam")
    return doc


@pytest.mark.parametrize("label, b_docs, count", [
    ("a company gains its first registration",
     {SIDECAR: _company(), BARE_SIDECAR: _company()}, 1),
    ("an existing registration changes a field",
     {SIDECAR: _company(sam={**SAM_BLOCK, "status": "Expired"}), BARE_SIDECAR: _bare()}, 1),
    ("an existing registration gains a field",
     {SIDECAR: _company(sam={**SAM_BLOCK, "cage_code": "1ABC2"}), BARE_SIDECAR: _bare()}, 1),
    ("a registration and a first registration at once",
     {SIDECAR: _company(sam={**SAM_BLOCK, "status": "Expired"}), BARE_SIDECAR: _company()}, 2),
])
def test_release_rules_excuse_a_new_or_updated_sam_block(tmp_path, label, b_docs, count):
    verdict, _, company_rule = _release_verdict(tmp_path, b_docs)
    assert verdict["ok"], (label, verdict["unexpected"])
    assert verdict["matched"][company_rule]["count"] == count, label


@pytest.mark.parametrize("label, b_docs, pattern, change", [
    ("an award total changes",
     {"awards": {"total": 1001, "by_year": [{"fy": 2025, "amount": 400}, {"fy": 2026, "amount": 600}]}},
     "/awards/total", "changed"),
    ("an award key is added",
     {"awards": {"total": 1000, "by_year": [{"fy": 2025, "amount": 400}, {"fy": 2026, "amount": 600}],
                 "restated": True}},
     "/awards/restated", "added"),
    ("an influence figure changes",
     {"influence": {"lobbying_total": 71}}, "/influence/lobbying_total", "changed"),
    ("a linked program is added",
     {"linked_programs": [{"program_key": "0603000D8Z"}, {"program_key": "0708081D"}]},
     "/linked_programs/[]", "added"),
    ("a mention is removed", {"mentions": []}, "/mentions/[]", "removed"),
    ("a new top-level key appears", {"tags": ["x"]}, "/tags", "added"),
])
def test_release_rules_do_not_excuse_a_change_outside_the_sam_block(
        tmp_path, label, b_docs, pattern, change):
    verdict, _, company_rule = _release_verdict(
        tmp_path, {SIDECAR: _company(**b_docs), BARE_SIDECAR: _bare()})
    assert not verdict["ok"], label
    assert [(u["path"], u["pattern"], u["change"]) for u in verdict["unexpected"]] == [
        (SIDECAR, pattern, change)], label
    assert verdict["matched"][company_rule]["count"] == 0, label


def test_a_sam_change_does_not_excuse_a_non_sam_change_beside_it(tmp_path):
    verdict, _, company_rule = _release_verdict(tmp_path, {
        SIDECAR: _company(sam={**SAM_BLOCK, "status": "Expired"}, influence={"lobbying_total": 71}),
        BARE_SIDECAR: _company(),
    })
    assert not verdict["ok"]
    assert [(u["path"], u["pattern"]) for u in verdict["unexpected"]] == [
        (SIDECAR, "/influence/lobbying_total")]
    assert verdict["matched"][company_rule]["count"] == 2   # the changed field + the first registration


def test_the_company_page_rule_names_the_sam_block():
    rules = proof.load_expectations(RELEASE_RULES)
    (rule,) = [r for r in rules if r["path"] == "json/entity_details/*.json"]
    assert rule["pointer"] == "/sam*"
    assert rule["status"] == ["changed"]
