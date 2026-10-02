<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 21: S4 proof — pre-S4 vs S4 export on one post-S3 snapshot

**Spec:** §8 (V3–V8, "proofs run on pinned snapshots"), §9 S4 ("the A/B diff equals §10; measured page gain recorded"), §10 (expected differences), §1 success criteria (page gain, fact stability, receipts).
**Files:**
- Create: `scripts/era/fact_stability.py`, `tests/test_era_fact_stability.py`
- Create: `scripts/era/s4_report.py`, `tests/test_era_s4_report.py`
- Create: `docs/superpowers/plans/2026-10-02-era-procurement-history-expected-diff.json`
- Modify: `site/scripts/gates/build.mjs` — the `/data/` `PAGE_WEIGHT_BUDGET` entry as Task 19 Step 11 left it (`:372` before Task 19): its `measured` stamp and the last lines of its comment (G6's handoff)
- Modify: `docs/superpowers/ROADMAP.md` — new first entry under `## Findings log (what we learned; feeds future phases)` (line 220 today)

**Interfaces:**
Consumes: Task 3's `govbudget proof snapshot --out DIR --scratch-db NAME` (writes `DIR/{duckdb/govbudget.duckdb, parquet/, site/, raw_docs/, manifest.jsonl, pg/<db>.dump, snapshot.json, env.sh}`, repoints the copy's views and document paths at the copy, restores Postgres into the scratch database; refuses at :15–:20) and `govbudget proof diff A B [--expect RULES.json] [--report FILE]` (rules: a JSON list of `{path, why, status?, pointer?, change?, required?}`; last line `proof diff: PASS|FAIL`); the run-dir convention `cp -c -R <snap> <run>` + `source <snap>/env.sh <run>`; `scripts/era/env.sh` (Task 1); Task 4's `tests/test_f15_era_identity.py`, `site/scripts/f15-page-snapshot.mjs <index.html> --check FILE`, `tests/fixtures/f15/page_snapshot.json`; `govbudget verify-era-map` (Tasks 14/20), `verify-phase5e`, `verify-lineage`; `govbudget export-site`; `dbt test`, `dbt parse`; Task 17's commit (CONTRACT ISSUE 6); Task 19's `/data/` stamp (G6 CONTRACT ISSUE 6 handoff).
Produces: `scripts/era/fact_stability.py` — `RUN_STAMPED_KINDS`, `F15_A1_CODES`, `F15_A1_LEAVES = 72`, `f15_a1_leaves(history) -> dict[str, str]`, `compare_citations(a, b, f15_leaves, *, expected_f15=72) -> dict`, `compare_decade_rows(a_parquet, b_parquet) -> dict`, `run(a_site, b_site, *, expected_f15=72) -> dict`, `main(argv=None) -> int` (CLI `--a --b [--expected-f15] [--report]`, last line `fact-stability: PASS|FAIL`); `scripts/era/s4_report.py` — `ERA_EDITIONS`, `page_class(sidecar) -> tuple[str, str]`, `compare_sidecar(slug, a, b) -> tuple[list[str], list[dict]]`, `sidecar_report(a_site, b_site) -> dict`, `receipt_report(a_site, b_site) -> dict`, `main(argv=None) -> int` (CLI `--a --b [--report]`, last line `s4-report: PASS|FAIL`); the expected-diff rule list; kept proof state `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/{s4,s4-A,s4-B,s4-logs}` (Task 22 clones `s4-B` and sources `s4/env.sh`; Task 23 reads `s4-logs/s4-report.json`), scratch database `govbudget_proof_s4`; the `/data/` re-stamp commit.

Measured now (read-only, `data/site` of the 2026-10-02 export): 125,409 citations; 93 F-15 era workbook leaves, all `pe_bli: null` with space-form `retrieved_at` (F01500 39, F015EX 18, F15EWS 15, F0150P 12, F015E0 9; 72 on A1 codes; seven edition timestamps); derived citations carry 22 distinct run-time `retrieved_at` stamps; `budget_lines_decade.parquet` 38,855 rows; 2,562 program sidecars: 892 PB2026 procurement and 89 decade-only procurement pages, none with a point from PB2017–PB2023 (953 PB2026 and 460 decade-only R&D pages have them); one PB2026 procurement sidecar has no `decade_series` key at all (`9999999999`); receipts audit `default_cells 67 / default_complete 67`, era P-1 books PB2017–PB2023 at 6/9/12/15/18/18/15 facts (all complete); every shard set is full already (`cite-shards` 256, `workbook-cells` 256, `budget-pdf-receipts/v2` 4,096), so new entries land in existing shards; live sitemap 4,349 URLs. Both scripts, run read-only on that export against itself, behave as designed: `fact_stability` finds exactly the 72 A1 leaves (and fails them as not restamped), `s4_report` counts 892/89 procurement pages and fails only the "more era receipts than A" rule. The Step 7 rule list loads with Task 3's `load_expectations` (prototype) and, on two synthetic trees, accepts the §10 changes while rejecting a changed `f15_funding_history.json`, a sidecar gaining a whole `decade_series` key, and a changed sidecar `lineage`.

- [ ] **Step 1: Write the failing fact-stability tests**

Create `tests/test_era_fact_stability.py`:

```python
"""scripts/era/fact_stability.py — V6 of the S4 A/B proof (Task 21, spec §8, §10)."""
import json

import duckdb
import pytest

from era.fact_stability import (  # scripts/ is on sys.path via conftest
    F15_A1_LEAVES,
    compare_citations,
    compare_decade_rows,
    f15_a1_leaves,
    main,
)

WB = dict(kind="workbook", units="USD thousands", amount_thousands=10.0, sha256="a" * 64, sheet="Exhibit P-1",
          cells="J10", official_url="https://comptroller.war.gov/p1.xlsx",
          retrieved_at="2026-07-03T07:44:15.975561-04:00", pe_bli="F01500")
DV = dict(kind="derived", units="USD thousands", recorded_value="10.000", formula="sum(budget_lines.amount_thousands)",
          inputs='["w1"]', retrieved_at="2026-10-02T01:26:11.150859+00:00", pe_bli=None)
LEAF_A = {**WB, "pe_bli": None, "retrieved_at": "2026-07-03 07:44:15.975561-04:00"}
LEAF_B = {**WB, "pe_bli": "F01500", "retrieved_at": "2026-07-03T07:44:15.975561-04:00"}
LEAVES = {"f1": "F01500"}


def a_side():
    return {"w1": dict(WB), "d1": dict(DV), "f1": dict(LEAF_A)}


def b_side():
    return {"w1": dict(WB), "d1": {**DV, "retrieved_at": "2026-10-09T03:00:00+00:00"}, "f1": dict(LEAF_B), "n1": dict(WB)}


def test_b_may_restamp_run_times_and_the_f15_leaves_and_add_facts():
    report = compare_citations(a_side(), b_side(), LEAVES, expected_f15=1)
    assert report["ok"], report
    assert (report["new_in_b"], report["f15_restamped"]) == (1, 1)


@pytest.mark.parametrize("fid, field, value", [
    ("w1", "retrieved_at", "2026-07-04T00:00:00-04:00"),
    ("w1", "amount_thousands", 11.0),
    ("w1", "pe_bli", None),
    ("d1", "inputs", '["w1", "w2"]'),
    ("d1", "recorded_value", "11.000"),
    ("f1", "cells", "J11"),
])
def test_any_other_field_change_fails(fid, field, value):
    b = b_side()
    b[fid][field] = value
    report = compare_citations(a_side(), b, LEAVES, expected_f15=1)
    assert not report["ok"]
    assert any(c["fact_id"] == fid and c["field"] == field for c in report["changed"])


def test_a_fact_missing_from_b_fails():
    b = b_side()
    del b["w1"]
    report = compare_citations(a_side(), b, LEAVES, expected_f15=1)
    assert not report["ok"] and report["missing"] == ["w1"]


def test_an_f15_leaf_the_decade_tier_did_not_mint_fails():
    b = b_side()
    b["f1"] = dict(LEAF_A)
    report = compare_citations(a_side(), b, LEAVES, expected_f15=1)
    assert not report["ok"] and report["f15_restamped"] == 0


def test_the_restamp_must_cover_exactly_the_expected_leaves():
    assert F15_A1_LEAVES == 72
    assert not compare_citations(a_side(), b_side(), LEAVES)["ok"]


def test_f15_leaves_are_era_keys_on_a1_code_rows_only():
    history = {"programs": [{"id": "P1", "code": "F01500"}, {"id": "P2", "code": "F0150P"}, {"id": "P3", "code": "F015EX"}],
               "points": [{"components": [
                   {"pe_bli": "3010F-AF-L21", "program_id": "P1", "fact_id": "a"},
                   {"pe_bli": "3010F-AF-L69", "program_id": "P2", "fact_id": "b"},
                   {"pe_bli": "F015EX", "program_id": "P3", "fact_id": "c"},
                   {"pe_bli": "3010F-AF-L5", "program_id": "P3", "fact_id": "d"}]}]}
    assert f15_a1_leaves(history) == {"a": "F01500", "d": "F015EX"}


def parquet(path, rows, amount_type="double"):
    con = duckdb.connect()
    con.execute(f"create table t (fact_id varchar, pe_bli varchar, amount_thousands {amount_type})")
    con.executemany("insert into t values (?, ?, ?)", rows)
    con.execute(f"copy t to '{path}' (format parquet)")
    con.close()


def test_every_decade_row_of_a_ships_unchanged_in_b(tmp_path):
    a, b, bad, retyped = (tmp_path / f"{n}.parquet" for n in ("a", "b", "bad", "retyped"))
    parquet(a, [("f1", "3010F-AF-L21", 10.0), ("f2", "0207134F", 5.0)])
    parquet(b, [("f2", "0207134F", 5.0), ("f3", "3010F-AF-L4", 1.0), ("f1", "3010F-AF-L21", 10.0)])
    parquet(bad, [("f1", "3010F-AF-L21", 10.5), ("f2", "0207134F", 5.0)])
    parquet(retyped, [("f1", "3010F-AF-L21", 10.0), ("f2", "0207134F", 5.0)], amount_type="decimal(18,3)")
    assert compare_decade_rows(a, b)["ok"]
    report = compare_decade_rows(a, bad)
    assert not report["ok"] and report["lost_fact_ids"] == ["f1"]
    assert not compare_decade_rows(a, retyped)["schema_equal"]


def site(root, citations, history, rows):
    (root / "json").mkdir(parents=True)
    (root / "data").mkdir()
    (root / "json" / "citations.json").write_text(json.dumps(citations))
    (root / "json" / "f15_funding_history.json").write_text(json.dumps(history))
    parquet(root / "data" / "budget_lines_decade.parquet", rows)
    return root


def test_cli_reads_two_site_trees(tmp_path):
    history = {"programs": [{"id": "P1", "code": "F01500"}],
               "points": [{"components": [{"pe_bli": "3010F-AF-L21", "program_id": "P1", "fact_id": "f1"}]}]}
    rows = [("f1", "3010F-AF-L21", 10.0)]
    a = site(tmp_path / "a", a_side(), history, rows)
    b = site(tmp_path / "b", b_side(), history, rows + [("n1", "F01500", 10.0)])
    assert main(["--a", str(a), "--b", str(b), "--expected-f15", "1", "--report", str(tmp_path / "r.json")]) == 0
    assert json.loads((tmp_path / "r.json").read_text())["citations"]["new_in_b"] == 1
    assert main(["--a", str(b), "--b", str(a), "--expected-f15", "1"]) == 1
```

- [ ] **Step 2: Write the failing page/receipt report tests**

Create `tests/test_era_s4_report.py`:

```python
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
```

- [ ] **Step 3: Run both test files to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && uv run --project . pytest tests/test_era_fact_stability.py tests/test_era_s4_report.py -q`
Expected: two collection errors, `ModuleNotFoundError: No module named 'era.fact_stability'` and `ModuleNotFoundError: No module named 'era.s4_report'`.

- [ ] **Step 4: Implement `scripts/era/fact_stability.py`**

```python
#!/usr/bin/env python3
"""V6 fact stability for the S4 A/B proof (spec §8 V6, §10).

A and B are two data/site trees exported from ONE pinned post-S3 snapshot: A
by the code just before the decade-tier switch, B by the S4 code. Every fact A
publishes must still be published by B with the same fields, and every
budget_lines_decade row A ships must ship unchanged in B. The only allowed
differences:

  * retrieved_at on the kinds the export stamps with its own run time
    (derived, state_file, state_soql): two runs, two stamps;
  * the 72 F-15 era leaves on A1 code chains (F01500 39, F015EX 18,
    F15EWS 15), which B's decade tier now mints before the F-15 builder runs:
    pe_bli null -> the printed code, and retrieved_at's space form -> its 'T'
    form (the same instant). Each of the 72 must show exactly that move.

Facts new in B are counted here and judged elsewhere (verify-era-map leg d,
verify-phase5b1, the S4 page and receipt report).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RUN_STAMPED_KINDS = frozenset({"derived", "state_file", "state_soql"})
F15_A1_CODES = frozenset({"F01500", "F015EX", "F15EWS"})
F15_A1_LEAVES = 72
_ERA_KEY = re.compile(r"^\d{4}[A-Z]-[A-Z]+-L\d+$")


def f15_a1_leaves(history: dict) -> dict[str, str]:
    """fact_id -> printed code, for F-15 workbook inputs keyed by an era key on an A1 chain."""
    codes = {program["id"]: program["code"] for program in history["programs"]}
    leaves: dict[str, str] = {}
    for point in history["points"]:
        for row in point["components"]:
            code = codes[row["program_id"]]
            if _ERA_KEY.match(row["pe_bli"]) and code in F15_A1_CODES:
                leaves[row["fact_id"]] = code
    return leaves


def compare_citations(a: dict, b: dict, f15_leaves: dict[str, str], *, expected_f15: int = F15_A1_LEAVES) -> dict:
    missing: list[str] = []
    changed: list[dict] = []
    restamped = 0
    for fid in sorted(a):
        ca, cb = a[fid], b.get(fid)
        if cb is None:
            missing.append(fid)
            continue
        moved: set[str] = set()
        for field in sorted(set(ca) | set(cb)):
            va, vb = ca.get(field), cb.get(field)
            if va == vb:
                continue
            if field == "retrieved_at" and ca.get("kind") in RUN_STAMPED_KINDS:
                continue
            if fid in f15_leaves and field == "pe_bli" and va is None and vb == f15_leaves[fid]:
                moved.add(field)
                continue
            if (fid in f15_leaves and field == "retrieved_at" and isinstance(va, str)
                    and " " in va and va.replace(" ", "T", 1) == vb):
                moved.add(field)
                continue
            changed.append({"fact_id": fid, "field": field, "a": va, "b": vb})
        if fid in f15_leaves:
            if moved == {"pe_bli", "retrieved_at"}:
                restamped += 1
            else:
                changed.append({"fact_id": fid, "field": "f15_restamp", "a": sorted(moved),
                                "b": ["pe_bli", "retrieved_at"]})
    ok = (not missing and not changed and len(f15_leaves) == expected_f15 and restamped == expected_f15)
    return {"ok": ok, "a_facts": len(a), "b_facts": len(b), "new_in_b": len(set(b) - set(a)),
            "missing": missing, "changed": changed, "f15_leaves": len(f15_leaves),
            "f15_restamped": restamped}


def compare_decade_rows(a_parquet: Path, b_parquet: Path) -> dict:
    """Every budget_lines_decade row of A, every column, is a row of B."""
    import duckdb

    con = duckdb.connect()
    try:
        a, b = str(a_parquet), str(b_parquet)
        schema_a = [r[:2] for r in con.execute("describe select * from read_parquet(?)", [a]).fetchall()]
        schema_b = [r[:2] for r in con.execute("describe select * from read_parquet(?)", [b]).fetchall()]
        a_rows = con.execute("select count(*) from read_parquet(?)", [a]).fetchone()[0]
        b_rows = con.execute("select count(*) from read_parquet(?)", [b]).fetchone()[0]
        lost = [r[0] for r in con.execute(
            "select fact_id from (select * from read_parquet(?) except select * from read_parquet(?)) "
            "order by fact_id", [a, b]).fetchall()]
    finally:
        con.close()
    return {"ok": schema_a == schema_b and not lost, "schema_equal": schema_a == schema_b,
            "a_rows": a_rows, "b_rows": b_rows, "lost": len(lost), "lost_fact_ids": lost[:20]}


def run(a_site: Path, b_site: Path, *, expected_f15: int = F15_A1_LEAVES) -> dict:
    a_site, b_site = Path(a_site), Path(b_site)
    a = json.loads((a_site / "json" / "citations.json").read_text())
    b = json.loads((b_site / "json" / "citations.json").read_text())
    history = json.loads((a_site / "json" / "f15_funding_history.json").read_text())
    citations = compare_citations(a, b, f15_a1_leaves(history), expected_f15=expected_f15)
    decade = compare_decade_rows(a_site / "data" / "budget_lines_decade.parquet",
                                 b_site / "data" / "budget_lines_decade.parquet")
    return {"ok": citations["ok"] and decade["ok"], "citations": citations, "budget_lines_decade": decade}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="V6: every fact export A publishes, export B publishes unchanged")
    p.add_argument("--a", type=Path, required=True, help="data/site exported by the pre-S4 code")
    p.add_argument("--b", type=Path, required=True, help="data/site exported by the S4 code")
    p.add_argument("--expected-f15", type=int, default=F15_A1_LEAVES)
    p.add_argument("--report", type=Path, default=None, help="write the full JSON report here")
    args = p.parse_args(argv)
    report = run(args.a, args.b, expected_f15=args.expected_f15)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    c, d = report["citations"], report["budget_lines_decade"]
    print(f"citations: A {c['a_facts']:,}, B {c['b_facts']:,}, new in B {c['new_in_b']:,}, "
          f"missing {len(c['missing']):,}, changed {len(c['changed']):,}, "
          f"F-15 era leaves restamped {c['f15_restamped']}/{c['f15_leaves']} (expected {args.expected_f15})")
    print(f"budget_lines_decade: A {d['a_rows']:,} rows, B {d['b_rows']:,} rows, A rows not in B {d['lost']:,}, "
          f"schema {'equal' if d['schema_equal'] else 'DIFFERS'}")
    for fid in c["missing"][:20]:
        print(f"  missing {fid}")
    for item in c["changed"][:20]:
        print(f"  changed {item['fact_id']} {item['field']}: {item['a']!r} -> {item['b']!r}")
    for fid in d["lost_fact_ids"]:
        print(f"  budget_lines_decade row changed or dropped: {fid}")
    print(f"fact-stability: {'PASS' if report['ok'] else 'FAIL'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Implement `scripts/era/s4_report.py`**

```python
#!/usr/bin/env python3
"""S4 page and receipt report, export A vs export B (spec §8 V7, §10, §1).

sidecars  Every json/program_details/<slug>.json keeps every key except
          decade_series and decade_absent unchanged (lineage funding lines,
          book diffs, budget lines, awards ...). Every decade point A shows,
          B shows unchanged. B adds points only from PB2017-PB2023 and only
          on procurement pages; decade_absent appears or vanishes nowhere.
          Measures the page gain: procurement pages with PB2026 lines and
          decade-only procurement pages that gained era points, how many of
          them now carry all seven era editions, and how many points.
receipts  No figure with a complete PDF receipt in A loses it in B; the F-15
          default cells stay 67/67 complete; every PB2017-PB2023 P-1 book is
          in the receipts audit with more receipted facts than A had, and its
          completeness is reported per edition.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ERA_EDITIONS = tuple(range(2017, 2024))
VOLATILE_KEYS = frozenset({"decade_series", "decade_absent"})
F15_DEFAULT_CELLS = 67
SAMPLES = 5


def _canon(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def page_class(sidecar: dict) -> tuple[str, str]:
    """(pb2026 | decade_only, procurement | rdte | other) for one program sidecar."""
    kind = "decade_only" if "decade_absent" in sidecar else "pb2026"
    family = sidecar.get("exhibit_family")
    if family is None:
        exhibits = {row.get("exhibit") for row in sidecar.get("budget_lines") or []}
        family = "procurement" if "P-1" in exhibits else "rdte" if "R-1" in exhibits else "other"
    return kind, family


def compare_sidecar(slug: str, a: dict, b: dict) -> tuple[list[str], list[dict]]:
    violations = [f"{slug}: {key} changed" for key in sorted((set(a) | set(b)) - VOLATILE_KEYS)
                  if _canon(a.get(key)) != _canon(b.get(key))]
    if ("decade_absent" in a) != ("decade_absent" in b):
        violations.append(f"{slug}: decade_absent appeared or vanished")
    new: list[dict] = []
    series_a, series_b = a.get("decade_series") or {}, b.get("decade_series") or {}
    for kind in sorted(set(series_a) | set(series_b)):
        in_a = {_canon(p) for p in series_a.get(kind, [])}
        in_b = {_canon(p) for p in series_b.get(kind, [])}
        for point in series_a.get(kind, []):
            if _canon(point) not in in_b:
                violations.append(f"{slug}: {kind} point {point.get('fid')} changed or removed")
        for point in series_b.get(kind, []):
            if _canon(point) in in_a:
                continue
            if point.get("edition") not in ERA_EDITIONS:
                violations.append(f"{slug}: new {kind} point {point.get('fid')} is from PB{point.get('edition')}")
            new.append(point)
    return violations, new


def sidecar_report(a_site: Path, b_site: Path) -> dict:
    a_dir = Path(a_site) / "json" / "program_details"
    b_dir = Path(b_site) / "json" / "program_details"
    a_names = sorted(p.name for p in a_dir.glob("*.json"))
    b_names = set(p.name for p in b_dir.glob("*.json"))
    violations: list[str] = []
    if set(a_names) != b_names:
        violations.append(f"program_details sets differ: {len(set(a_names) - b_names)} only in A, "
                          f"{len(b_names - set(a_names))} only in B")
    pages = {"pb2026": 0, "decade_only": 0}
    gained = {"pb2026": 0, "decade_only": 0}
    all_seven = {"pb2026": 0, "decade_only": 0}
    samples: dict[str, list[str]] = {"pb2026": [], "decade_only": []}
    new_points = 0
    for name in a_names:
        if name not in b_names:
            continue
        a = json.loads((a_dir / name).read_text())
        b = json.loads((b_dir / name).read_text())
        slug = name[: -len(".json")]
        kind, family = page_class(a)
        bad, new = compare_sidecar(slug, a, b)
        violations.extend(bad)
        if family == "procurement":
            pages[kind] += 1
        if not new:
            continue
        if family != "procurement":
            violations.append(f"{slug}: {family} page gained {len(new)} point(s)")
            continue
        gained[kind] += 1
        new_points += len(new)
        if len(samples[kind]) < SAMPLES:
            samples[kind].append(slug)
        editions = {p.get("edition") for points in (b.get("decade_series") or {}).values() for p in points}
        if set(ERA_EDITIONS) <= editions:
            all_seven[kind] += 1
    return {"ok": not violations, "procurement_pages": pages, "gained": gained,
            "all_seven_editions": all_seven, "new_points": new_points, "samples": samples,
            "violations": violations}


def _receipts(site: Path) -> dict:
    receipts: dict = {}
    for shard in sorted((Path(site) / "json" / "budget-pdf-receipts" / "v2").glob("*.json")):
        receipts.update(json.loads(shard.read_text()))
    return receipts


def _era_books(audit: dict) -> dict[int, dict]:
    return {book["edition"]: {"facts": book["facts"], "complete": book["complete"]}
            for book in audit.get("books", []) if book["exhibit"] == "P-1" and book["edition"] in ERA_EDITIONS}


def receipt_report(a_site: Path, b_site: Path) -> dict:
    receipts_a, receipts_b = _receipts(a_site), _receipts(b_site)
    lost = sorted(fid for fid, r in receipts_a.items()
                  if r.get("complete") and not receipts_b.get(fid, {}).get("complete"))
    audit_a = json.loads((Path(a_site) / "json" / "budget_pdf_receipts_audit.json").read_text())
    audit_b = json.loads((Path(b_site) / "json" / "budget_pdf_receipts_audit.json").read_text())
    era_a, era_b = _era_books(audit_a), _era_books(audit_b)
    violations = [f"complete receipt lost: {fid}" for fid in lost[:20]]
    if len(lost) > 20:
        violations.append(f"... and {len(lost) - 20} more complete receipts lost")
    default = (audit_b.get("default_complete"), audit_b.get("default_cells"))
    if default != (F15_DEFAULT_CELLS, F15_DEFAULT_CELLS):
        violations.append(f"F-15 default cells {default[0]}/{default[1]} complete, expected 67/67")
    for edition in ERA_EDITIONS:
        before = era_a.get(edition, {"facts": 0})["facts"]
        if edition not in era_b:
            violations.append(f"PB{edition} P-1 is missing from the receipts audit")
        elif era_b[edition]["facts"] <= before:
            violations.append(f"PB{edition} P-1 receipts {era_b[edition]['facts']} facts, not more than A's {before}")
    return {"ok": not violations,
            "receipts": {"a": len(receipts_a), "b": len(receipts_b)},
            "complete": {"a": sum(bool(r.get("complete")) for r in receipts_a.values()),
                         "b": sum(bool(r.get("complete")) for r in receipts_b.values())},
            "lost_complete": len(lost), "f15_default": f"{default[0]}/{default[1]}",
            "era_p1_by_edition": {str(e): era_b.get(e) for e in ERA_EDITIONS},
            "violations": violations}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="S4 page gain, sidecar stability and PDF receipts, A vs B")
    p.add_argument("--a", type=Path, required=True)
    p.add_argument("--b", type=Path, required=True)
    p.add_argument("--report", type=Path, default=None, help="write the full JSON report here")
    args = p.parse_args(argv)
    report = {"sidecars": sidecar_report(args.a, args.b), "receipts": receipt_report(args.a, args.b)}
    report["ok"] = report["sidecars"]["ok"] and report["receipts"]["ok"]
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    summary = {part: {k: v for k, v in report[part].items() if k != "violations"} for part in ("sidecars", "receipts")}
    print(json.dumps(summary, indent=2, sort_keys=True))
    for violation in (report["sidecars"]["violations"] + report["receipts"]["violations"])[:40]:
        print(f"  violation: {violation}")
    print(f"s4-report: {'PASS' if report['ok'] else 'FAIL'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && uv run --project . pytest tests/test_era_fact_stability.py tests/test_era_s4_report.py -q`
Expected: `20 passed`.

- [ ] **Step 7: Write the expected-diff rule list (spec §10)**

Task 3's `proof diff --expect` takes a JSON list of rules (`load_expectations`): every difference between the A and B site trees must match a rule, and every `required` rule must match at least one. `path` and `pointer` are globs where only `*` is special (it also crosses `/`); a JSON pointer pattern collapses 16-hex fact IDs to `{fid}` and writes list elements as `/[]`; lists compare as multisets, so a list entry whose value changed is one `removed` plus one `added`. Build stamps (`built_at`, run-time `retrieved_at` inside each tree's own build window, `measured_on`) are masked before comparing, so the derived citations' run stamps never appear.

Create `docs/superpowers/plans/2026-10-02-era-procurement-history-expected-diff.json`:

```json
[
  {"path": "data/p1_era_line_map.parquet", "status": ["only_b"], "required": true,
   "why": "§10: new p1_era_line_map.parquet (the reviewed era map, uncited dataset)"},
  {"path": "json/era_map_summary.json", "status": ["only_b"], "required": true,
   "why": "§10: new json/era_map_summary.json (per-edition chains, lines and receipts by decision)"},

  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}", "change": ["added"], "required": true,
   "why": "§10: new era leaf and decade_era_map citations; V6 (fact_stability) proves every A fact is unchanged"},
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}/pe_bli", "change": ["changed"], "required": true,
   "why": "§10: the 72 F-15 A1 era leaves, now minted by the decade tier: pe_bli null -> F01500/F015EX/F15EWS (V6 counts exactly 72)"},
  {"path": "json/citations.json", "status": ["changed"], "pointer": "/{fid}/retrieved_at", "change": ["changed"], "required": true,
   "why": "§10: the same 72 leaves: retrieved_at space form -> T form, same instant (V6 checks each)"},
  {"path": "json/cite-shards/*.json", "status": ["changed"], "pointer": "/{fid}", "change": ["added"], "required": true,
   "why": "§10: cite shards carry the new citations (same objects as citations.json)"},
  {"path": "json/cite-shards/*.json", "status": ["changed"], "pointer": "/{fid}/pe_bli", "change": ["changed"], "required": true,
   "why": "§10: the 72 F-15 A1 era leaves' pe_bli, as in citations.json"},
  {"path": "json/cite-shards/*.json", "status": ["changed"], "pointer": "/{fid}/retrieved_at", "change": ["changed"], "required": true,
   "why": "§10: the 72 F-15 A1 era leaves' retrieved_at form, as in citations.json"},
  {"path": "citations/citations.parquet", "status": ["changed"], "required": true,
   "why": "§10: new citation rows; the 72 F-15 leaves' pe_bli/retrieved_at (V6 compares citations.json field by field)"},

  {"path": "data/budget_lines_decade.parquet", "status": ["changed"], "required": true,
   "why": "§10: new era rows, schema unchanged; V6 proves every A row ships unchanged in B"},

  {"path": "json/program_details/*.json", "status": ["changed"], "pointer": "/decade_series/*", "change": ["added"], "required": true,
   "why": "§10: new PB2017-PB2023 decade points on procurement pages (s4_report: append-only, era editions, procurement only)"},
  {"path": "json/program_details/*.json", "status": ["changed"], "pointer": "/decade_absent/*", "change": ["changed"], "required": true,
   "why": "§10: decade-only procurement pages' decade_absent block (first edition, edition count, FY span)"},

  {"path": "json/breakdowns/*.json", "status": ["only_b"], "required": true,
   "why": "§10: a new breakdown for each decade_era_map sum with two or more inputs; existing breakdowns never change"},
  {"path": "json/workbook-cells/*.json", "status": ["changed"], "pointer": "/{fid}", "change": ["added"], "required": true,
   "why": "§10: workbook-cell previews for the new era leaves (all 256 shards exist in A)"},
  {"path": "json/workbook-cells/*.json", "status": ["only_b"],
   "why": "§10: a preview shard A lacked (none expected: A has all 256)"},
  {"path": "json/budget-pdf-receipts/v2/*.json", "status": ["changed"], "pointer": "/{fid}", "change": ["added"], "required": true,
   "why": "§10: receipts for the new facts (all 4,096 shards exist in A); V7: no complete receipt lost"},
  {"path": "json/budget-pdf-receipts/v2/*.json", "status": ["only_b"],
   "why": "§10: a receipt shard A lacked (none expected: A has all 4,096)"},
  {"path": "json/budget_pdf_receipts_audit.json", "status": ["changed"], "pointer": "/books/[]", "change": ["added", "removed"], "required": true,
   "why": "§10 / V7: the seven era P-1 books' facts and complete counts grow"},
  {"path": "json/budget_pdf_receipts_audit.json", "status": ["changed"], "pointer": "/unmatched_cells/[]", "change": ["added"],
   "why": "§6.3: era cells the matcher cannot place yet (e.g. shipbuilding cost-type rows), disclosed per edition"},
  {"path": "json/budget_pdf_receipts_audit.json", "status": ["changed"], "pointer": "/citation_sha256", "change": ["changed"], "required": true,
   "why": "§10: the audit fingerprints the citation registry it read"},
  {"path": "json/budget_pdf_receipts_audit.json", "status": ["changed"], "pointer": "/leaf_count", "change": ["changed"], "required": true,
   "why": "§10: more workbook leaves"},
  {"path": "json/budget_pdf_receipts_audit.json", "status": ["changed"], "pointer": "/receipt_count", "change": ["changed"], "required": true,
   "why": "§10: more receipts"},
  {"path": "json/budget_pdf_receipts_audit.json", "status": ["changed"], "pointer": "/complete_receipts", "change": ["changed"], "required": true,
   "why": "§10: more complete receipts (V7: none lost)"},

  {"path": "manifest.json", "status": ["changed"], "pointer": "/citations/workbook", "change": ["changed"], "required": true,
   "why": "§10: the manifest's citation counts (new era leaves)"},
  {"path": "manifest.json", "status": ["changed"], "pointer": "/citations/derived", "change": ["changed"], "required": true,
   "why": "§10: the manifest's citation counts (new decade_era_map sums)"},
  {"path": "manifest.json", "status": ["changed"], "pointer": "/datasets/budget_lines_decade", "change": ["changed"], "required": true,
   "why": "§10: the manifest's dataset counts"},
  {"path": "manifest.json", "status": ["changed"], "pointer": "/datasets/p1_era_line_map", "change": ["added"], "required": true,
   "why": "§10: the new map dataset's row count"},
  {"path": "manifest.json", "status": ["changed"], "pointer": "/uncited_datasets/[]", "change": ["added"], "required": true,
   "why": "§4.4: p1_era_line_map goes on the uncited ledger (rows are decisions, not money)"},
  {"path": "manifest.json", "status": ["changed"], "pointer": "/json_sidecars", "change": ["changed"], "required": true,
   "why": "§10: the manifest's sidecar count (new breakdowns, era_map_summary.json)"},
  {"path": "json/site_meta.json", "status": ["changed"], "pointer": "/counts/citations", "change": ["changed"], "required": true,
   "why": "§10: site_meta counts.citations"},
  {"path": "json/site_meta.json", "status": ["changed"], "pointer": "/datasets/budget_lines_decade", "change": ["changed"], "required": true,
   "why": "§10: site_meta datasets.budget_lines_decade"},
  {"path": "json/site_meta.json", "status": ["changed"], "pointer": "/datasets/p1_era_line_map", "change": ["added"], "required": true,
   "why": "§10: site_meta lists the new map dataset"},
  {"path": "json/site_meta.json", "status": ["changed"], "pointer": "/uncited_datasets/[]", "change": ["added"], "required": true,
   "why": "§4.4: site_meta mirrors the manifest's uncited ledger"},
  {"path": "json/datasets.json", "status": ["changed"], "pointer": "/datasets/[]", "change": ["added", "removed"], "required": true,
   "why": "§10: budget_lines_decade's row_count/bytes entry is replaced; p1_era_line_map's entry is added (a list compares as a multiset)"},
  {"path": "json/datasets.json", "status": ["changed"], "pointer": "/citations/row_count", "change": ["changed"], "required": true,
   "why": "§10: the citations card's row count"},
  {"path": "json/datasets.json", "status": ["changed"], "pointer": "/citations/kinds/[]", "change": ["added", "removed"], "required": true,
   "why": "§10: the citations card's per-kind counts (workbook, derived)"}
]
```

Deliberately no rule (any change there FAILS the proof): `json/f15_funding_history.json` and the F-15 summary in `manifest.json` (`/f15_funding_history/*` — annual points, source facts and FY span come from the fenced F-15 payload, so a change there is a fence breach), `json/years_matrix.json`, `json/lineage_flow.json`, `json/feed.json`, `json/feed-sections/*`, `json/programs.json`, `json/search_quick.json`, `data/budget_lines.parquet` and every other parquet but the three named, every other key of a program sidecar (lineage, `book_diff`, `budget_lines`, awards …; and a sidecar that had no `decade_series` key gaining one), existing breakdowns, existing receipts and previews (only `/{fid}` additions to a shard are allowed), `pdfs/`, `workbooks/`, and `json/site_meta.json` `/build_checks/*` (A and B read the same dbt manifest, Step 13). Changes inside the allowed patterns are judged by Steps 17–18: V6 compares every A citation field by field and every `budget_lines_decade` row, `s4_report` checks that sidecars only gain era points on procurement pages and that no complete receipt is lost.

- [ ] **Step 8: Commit the proof tools**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/scripts/era/fact_stability.py GovBudget/scripts/era/s4_report.py GovBudget/tests/test_era_fact_stability.py GovBudget/tests/test_era_s4_report.py GovBudget/docs/superpowers/plans/2026-10-02-era-procurement-history-expected-diff.json && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "test(era): S4 proof tools — fact stability (V6), page gain + receipts report (V7), expected diff (spec §10)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 9: Identify the A commit and check the preconditions**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git status --porcelain -- GovBudget | grep -v '^??' ; FIRST=$(git log --reverse --format=%H main..HEAD -- GovBudget/src/govbudget/export_site.py | head -1) && A_SHA=$(git rev-parse "${FIRST}^") && echo "A_SHA=${A_SHA}" && git log -1 --format='first S4 export commit: %h %s' "${FIRST}" && git log -1 --format='A: %h %s' "${A_SHA}" && git diff --quiet "${A_SHA}" HEAD -- GovBudget/dbt && echo "dbt unchanged since A" && git rev-parse HEAD
```
Expected: no tracked change listed; `first S4 export commit:` shows Task 17's subject (`feat(export): decade tier reads fct_program_decade_series; era P-1 points through the reviewed map …`); `dbt unchanged since A`; HEAD printed. Record `A_SHA` and HEAD (`B_SHA`). If the first subject is not Task 17's, set `A_SHA` to the parent of Task 17's commit from `git log --oneline main..HEAD` and re-run the dbt check. If dbt changed after A, stop (CONTRACT ISSUE 6).

Also confirm S2/S3 are closed on the live lake (read-only):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python -c "import duckdb,os; c=duckdb.connect(os.environ['GOVBUDGET_DUCKDB'], read_only=True); print(c.execute(\"select count(*) filter (where decision = 'undecided' or keys_sha_ok = false), count(*) from p1_era_line_map\").fetchone(), c.execute('select count(*) from fct_program_decade_series').fetchone())"
```
Expected: `(0, 6927) (<n>,)` with `<n>` > 0 (one map row per era key, spec §4.4; Task 16 built the program table).

- [ ] **Step 10: Take the post-S3 snapshot (shared Postgres: creates the scratch database only)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && mkdir -p "$GOVBUDGET_PROOFS/s4-logs" && date +%H:%M && uv run --project . python -m govbudget proof snapshot --out "$GOVBUDGET_PROOFS/s4" --scratch-db govbudget_proof_s4 > "$GOVBUDGET_PROOFS/s4-logs/snapshot.log" 2>&1; echo "exit=$?"; cat "$GOVBUDGET_PROOFS/s4-logs/snapshot.log"
```
Expected (counts drift with the lake; shas vary):
```
exit=0
proof snapshot: /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s4
  duckdb sha256 <64 hex> (<k> of <v> views repointed)
  parquet files <n> · site files <n> · raw_docs files <n>
  postgres govbudget -> govbudget_proof_s4 (18 tables, dump sha256 <64 hex>)
  source /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s4/env.sh [RUN_DIR]
```
The command refuses by itself at :15–:20 (`proof snapshot: refusing at HH:MM …`): wait and re-run. If it refused "after the copy", `rm -rf "$GOVBUDGET_PROOFS/s4"` first (the scratch database is created only after that check). A DuckDB writer holding the lake also makes it refuse before writing anything.

Record the snapshot's shas for the proof note:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python -c "import json,sys; m=json.load(open(sys.argv[1])); print(json.dumps({'created_at': m['created_at'], 'duckdb_sha256_at_copy': m['duckdb']['sha256_at_copy'], 'duckdb_sha256': m['duckdb']['sha256'], 'views_rewritten': m['duckdb']['views_rewritten'], 'site_sha256': m['site']['sha256'], 'raw_docs_sha256': m['raw_docs']['sha256'], 'manifest_jsonl_sha256': m['manifest_jsonl_sha256'], 'pg_dump_sha256': m['pg']['dump_sha256'], 'pg_scratch_dsn': m['pg']['scratch_dsn'], 'jbook_documents_rewritten': m['pg']['rewrites']}, indent=1))" "$GOVBUDGET_PROOFS/s4/snapshot.json" > "$GOVBUDGET_PROOFS/s4-logs/snapshot-shas.json" && cat "$GOVBUDGET_PROOFS/s4-logs/snapshot-shas.json"
```
Expected: the JSON object with every sha filled and `"pg_scratch_dsn": "postgresql://localhost/govbudget_proof_s4"`.

- [ ] **Step 11: V3 on the pinned state — the dbt tests, no rebuild**

Task 3 already repointed the snapshot's views at its own parquet copy; nothing is rebuilt here (a rebuild would make the A/B warehouse differ from the live warehouse the release exports). Run the era tests against the snapshot, then check it reads nothing live:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && P="$GOVBUDGET_PROOFS" && (source "$P/s4/env.sh" && uv run --project . dbt test --project-dir dbt --profiles-dir dbt --select p1_era_code_decisions p1_era_line_map fct_program_decade_series) > "$P/s4-logs/v3-dbt-test.log" 2>&1; echo "exit=$?"; grep -E "assert_p1_era_map_no_undecided|assert_program_decade_" "$P/s4-logs/v3-dbt-test.log"; tail -1 "$P/s4-logs/v3-dbt-test.log"; uv run --project . python - "$P/s4" <<'PY'
import duckdb, hashlib, json, sys
snap = sys.argv[1]
db = f"{snap}/duckdb/govbudget.duckdb"
con = duckdb.connect(db, read_only=True)
print("views reading the live lake:", con.execute(
    "select count(*) from duckdb_views() where not internal and contains(sql, ?)",
    ["/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/"]).fetchone()[0])
print("undecided:", con.execute(
    "select count(*) from p1_era_line_map where decision = 'undecided' or keys_sha_ok = false").fetchone()[0])
con.close()
h = hashlib.sha256()
with open(db, "rb") as fh:
    for chunk in iter(lambda: fh.read(1 << 20), b""):
        h.update(chunk)
print("duckdb unchanged by dbt test:", h.hexdigest() == json.load(open(f"{snap}/snapshot.json"))["duckdb"]["sha256"])
PY
```
Expected: `exit=0`; `PASS assert_p1_era_map_no_undecided` and the three `PASS assert_program_decade_{native_equals_line,conservation,grain_unique}` lines; `Done. PASS=<n> WARN=0 ERROR=0 SKIP=0 …` (this is V3 on the pinned state); then `views reading the live lake: 0`, `undecided: 0`, `duckdb unchanged by dbt test: True` (`dbt test` only reads: measured on a scratch dbt-duckdb project, it leaves the file's bytes and mtime unchanged). This dbt run also rewrote the worktree's own `dbt/target/manifest.json`, which the B export reads for `site_meta.build_checks.dbt_assertions` (`export_site.py:1386-1395`).

- [ ] **Step 12: Clone the snapshot twice (APFS clones)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && P="$GOVBUDGET_PROOFS" && cp -c -R "$P/s4" "$P/s4-A" && cp -c -R "$P/s4" "$P/s4-B" && for d in s4-A s4-B; do (source "$P/s4/env.sh" "$P/$d" && echo "$d: $GOVBUDGET_DATA | $GOVBUDGET_DUCKDB | $GOVBUDGET_PG_DSN"); done
```
Expected (seconds; the clones share blocks):
```
s4-A: /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s4-A | /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s4-A/duckdb/govbudget.duckdb | postgresql://localhost/govbudget_proof_s4
s4-B: /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s4-B | /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s4-B/duckdb/govbudget.duckdb | postgresql://localhost/govbudget_proof_s4
```
Never write `.proofs/s4` again: both clones' DuckDB views read `.proofs/s4/parquet` and their documents resolve to `.proofs/s4/raw_docs`. Always pass the run dir to the snapshot's `env.sh` (without it, `env.sh` points at `.proofs/s4` itself).

- [ ] **Step 13: Check out the A code in a detached worktree and give it its own dbt manifest**

`export-site` reads the code checkout's `dbt/target/manifest.json` for `site_meta.build_checks.dbt_assertions` (`export_site.py:1386-1395`); a fresh worktree has none, so A would omit the field and B would not. `dbt parse` writes the manifest from A's own `dbt/` without opening a warehouse (Task 1 Step 7's method; ROADMAP #173: never another checkout's manifest), and Step 9 proved A's `dbt/` equals HEAD's, so the test-node counts must agree:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git worktree add --detach /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-proof-a "${A_SHA}" && cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-proof-a/GovBudget && uv sync --frozen && source scripts/era/env.sh && GOVBUDGET_DUCKDB="$GOVBUDGET_PROOFS/dbt-parse-a.duckdb" uv run --project . dbt parse --project-dir dbt --profiles-dir dbt > "$GOVBUDGET_PROOFS/s4-logs/dbt-parse-a.log" 2>&1; echo "parse exit=$?"; test ! -e "$GOVBUDGET_PROOFS/dbt-parse-a.duckdb" && echo no-warehouse-opened; uv run --project . python - /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/dbt/target/manifest.json dbt/target/manifest.json <<'PY'
import json, sys
counts = [sum(1 for n in json.load(open(p))["nodes"].values() if n.get("resource_type") == "test") for p in sys.argv[1:]]
print(f"dbt test nodes: B {counts[0]}, A {counts[1]}")
sys.exit(0 if counts[0] == counts[1] else 1)
PY
echo "count check exit=$?"; git log -1 --format='%h %s'
```
(`A_SHA` from Step 9; re-export it in this shell.) Expected: `Preparing worktree (detached HEAD …)`, uv installs the locked environment into this worktree's own `.venv`, `parse exit=0`, `no-warehouse-opened`, `dbt test nodes: B <n>, A <n>` with the same `<n>` (above 163, the live count: Tasks 13, 15 and 16 added tests), `count check exit=0`, and A's subject. No stash is used anywhere.

Optional speed-up for both exports (the receipt step otherwise rescans 21 PDFs): `for d in /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-proof-a/GovBudget /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget; do mkdir -p ${d}/tmp/pdfs && cp -c /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/decisions/GovBudget/tmp/pdfs/*-program-pages-v1.json ${d}/tmp/pdfs/ 2>/dev/null; done; true` (the cache is keyed by PDF sha256).

- [ ] **Step 14: Export A (pre-S4 code)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-proof-a/GovBudget && P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs && (source "$P/s4/env.sh" "$P/s4-A" && uv run --project . python -m govbudget export-site) > "$P/s4-logs/export-A.log" 2>&1; echo "exit=$?"; tail -3 "$P/s4-logs/export-A.log"
```
Expected: `exit=0`; lines `budget PDF receipts: <c>/<n> complete, 21 government documents; audit -> …/.proofs/s4-A/site/json/budget_pdf_receipts_audit.json` and `export-site: <d> datasets, <N_A> citations, … -> …/.proofs/s4-A/site`. The export reads only the pinned clone (and the scratch database), so the :15–:20 rule does not apply to it.

- [ ] **Step 15: Export B (S4 code)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs && (source "$P/s4/env.sh" "$P/s4-B" && uv run --project . python -m govbudget export-site) > "$P/s4-logs/export-B.log" 2>&1; echo "exit=$?"; tail -3 "$P/s4-logs/export-B.log"
```
Expected: `exit=0`; the same two lines for `s4-B`, with `<N_B>` citations above `<N_A>` (spec §11.4 estimates 16–21k new leaf citations plus `decade_era_map` sums).

- [ ] **Step 16: Diff A against B with the expected-diff rules**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs && uv run --project . python -m govbudget proof diff "$P/s4-A/site" "$P/s4-B/site" --expect docs/superpowers/plans/2026-10-02-era-procurement-history-expected-diff.json --report "$P/s4-logs/diff-report.json" > "$P/s4-logs/diff.txt" 2>&1; echo "exit=$?"; tail -45 "$P/s4-logs/diff.txt"
```
Expected: `exit=0`; one `rule <i> [<path>] matched <count>: <why>` line per rule — the four `/{fid}/pe_bli` and `/{fid}/retrieved_at` rules (citations.json and the cite shards) each match exactly 72 — no `UNEXPECTED differences` and no `UNMET required rule` line, last line `proof diff: PASS`. A FAIL names each unexpected path/pattern or unmet rule: stop and explain it before going on; never widen the rule list to make it pass without the owner.

- [ ] **Step 17: V6 — fact stability**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs && uv run --project . python scripts/era/fact_stability.py --a "$P/s4-A/site" --b "$P/s4-B/site" --report "$P/s4-logs/s4-fact-stability.json"
```
Expected: `citations: A <N_A>, B <N_B>, new in B <N_B−N_A>, missing 0, changed 0, F-15 era leaves restamped 72/72 (expected 72)`, `budget_lines_decade: A <a> rows, B <b> rows, A rows not in B 0, schema equal`, last line `fact-stability: PASS`.

- [ ] **Step 18: V7 + page gain — sidecars and receipts**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs && uv run --project . python scripts/era/s4_report.py --a "$P/s4-A/site" --b "$P/s4-B/site" --report "$P/s4-logs/s4-report.json"
```
Expected: last line `s4-report: PASS`; `sidecars.procurement_pages` `{"decade_only": 89, "pb2026": 892}` (measured today; the A export is post-S3 but S1–S3 add no page); `sidecars.gained.pb2026` about 800 and `gained.decade_only` about 80 (spec §1), `all_seven_editions.pb2026` about 581; `receipts.lost_complete 0`, `f15_default "67/67"`, `era_p1_by_edition` filled for 2017–2023 with facts above A's 6/9/12/15/18/18/15. Keep `s4-report.json`: Task 23's live checks use its `samples`.

- [ ] **Step 19: V5 — F-15 identity on hermetic fixtures**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && uv run --project . pytest tests/test_f15_era_identity.py -q`
Expected: all tests pass, none skipped.

- [ ] **Step 20: verify-phase5e, verify-era-map, verify-lineage on B**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs && for gate in verify-phase5e verify-era-map verify-lineage; do (source "$P/s4/env.sh" "$P/s4-B" && uv run --project . python -m govbudget ${gate}) > "$P/s4-logs/${gate}.log" 2>&1; echo "${gate} exit=$?"; tail -1 "$P/s4-logs/${gate}.log"; done
```
Expected: `verify-phase5e exit=0` / `verify-phase5e: PASS`, `verify-era-map exit=0` / `verify-era-map: PASS` (all six legs; leg f still matches the S0 F-15 pin because S4 leaves `f15_funding_history.json` unchanged), `verify-lineage exit=0` / `verify-lineage: PASS`.

- [ ] **Step 21: V8 — site build and `npm run verify` against B's site; F-15 page; sitemap; re-measure `/data/`**

The site reads the repo-relative `data/site` and `data/duckdb` (CONTRACT ISSUE 8). Point them at B (refusing if any is a real directory), build, verify, compare the F-15 page with the S0 baseline, compare the sitemap, re-stamp `/data/`, then point the links back at the main lake:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs && BAD=0; for d in site duckdb parquet; do if [ -e "data/$d" ] && [ ! -L "data/$d" ]; then echo "STOP: data/$d is a real directory"; BAD=1; fi; done; [ "$BAD" = 0 ] && for d in site duckdb parquet; do ln -sfn "$P/s4-B/$d" "data/$d"; done; ls -l data | grep -- '->'; ls dbt/target/manifest.json
```
Expected: three symlinks `data/{site,duckdb,parquet} -> /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s4-B/{site,duckdb,parquet}` (excluded by the shared `info/exclude`), and the dbt manifest path (Step 11 wrote it). Then:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build > "$P/s4-logs/site-build.log" 2>&1; echo "build exit=$?"; NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run verify > "$P/s4-logs/site-verify.log" 2>&1; echo "verify exit=$?"; grep -E "^gate |^  gate |^overall:" "$P/s4-logs/site-verify.log" | tail -40
```
Expected: `build exit=0`, `verify exit=0`, every gate line `→ PASS` (program-skeleton incl. leg k's `decade_absent` recompute and leg p, linkgraph, datatruth incl. the map dataset card, Explorer entry and era summary table, years-matrix, page weight with `/families/f-15/` and `/methodology/` inside their unchanged ceilings), last line `overall: PASS`. Port 4173 must be free (no other session running verify). This is the first build of Task 19 Part C (the `/data/` page throws on an export that does not ship `p1_era_line_map`).

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs && node scripts/f15-page-snapshot.mjs out/families/f-15/index.html --check ../tests/fixtures/f15/page_snapshot.json; echo "exit=$?"; grep -o '<loc>[^<]*</loc>' out/sitemap.xml | sort > "$P/s4-logs/sitemap-b.txt" && curl -s https://fiscalreceipts.com/sitemap.xml | grep -o '<loc>[^<]*</loc>' | sort > "$P/s4-logs/sitemap-live.txt" && diff -q "$P/s4-logs/sitemap-live.txt" "$P/s4-logs/sitemap-b.txt" && wc -l < "$P/s4-logs/sitemap-b.txt"
```
Expected: `f15-page-snapshot: PASS — equal to ../tests/fixtures/f15/page_snapshot.json`, `exit=0`; no `diff` output; `4349` (the live sitemap measured 2026-10-02 at aa714d7f; if production has been redeployed since, compare against the URL list of that deploy instead). A FAIL names the first differing path of the normalized F-15 page: stop (the F-15 fence leaked).

Re-measure `/data/` now that the `p1_era_line_map` inventory row ships (Task 19 stamped it before the map shipped; G6 estimated +400 to +650 gzip). The computation is gate 1's `weigh()` (`site/scripts/gates/build.mjs:889-892`, not exported):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && node -e 'const fs=require("fs"),z=require("zlib");const b=fs.readFileSync("out/data/index.html");console.log(b.length.toLocaleString("en-US")+" / "+z.gzipSync(b,{level:9}).length.toLocaleString("en-US"))'
```
Expected: `<raw> / <gzip>` within `105,000 / 15,600` (verify already passed, so it is). In `site/scripts/gates/build.mjs`, the `/data/` entry as Task 19 Step 11 left it (`<D>`, `<R>`, `<G>` are Task 19's date and numbers) ends:

```js
  // issue 1). CEILINGS UNCHANGED. RE-MEASURED <D> (Task 19 build, before the
  // map ships; gate 1's weigh()): <R> / <G>. Task 21 re-measures with the row.
  { label: "/data/", file: "data/index.html", maxRaw: 105_000, maxGzip: 15_600, measured: "<R> / <G>" },
```
Replace those three lines with (filling today's date, B's short sha from Step 9 and the printed numbers; the headroom is the ceiling minus the measurement):

```js
  // issue 1). CEILINGS UNCHANGED. RE-MEASURED <D> (Task 19 build, before the
  // map ships; gate 1's weigh()): <R> / <G>. RE-MEASURED <YYYY-MM-DD> (Task 21,
  // the S4 proof build of <B short sha> on the S4 export, with the
  // p1_era_line_map row; gate 1's weigh(), zlib level 9): <R> / <G> ->
  // <raw> / <gzip>. CEILINGS UNCHANGED; <105,000 − raw> raw / <15,600 − gzip> gzip left.
  { label: "/data/", file: "data/index.html", maxRaw: 105_000, maxGzip: 15_600, measured: "<raw> / <gzip>" },
```
Then check the entry and commit it:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && node --input-type=module -e 'import("./scripts/gates/build.mjs").then(({checkPageWeight})=>{const r=checkPageWeight();console.log(r.errors.filter(e=>/\/data\//.test(e)).length)})' && cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/site/scripts/gates/build.mjs && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "chore(site): re-measure /data/ with the p1_era_line_map inventory row (S4 proof build; ceilings unchanged)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: `0` (no ceiling or stamp-drift error for `/data/`), then the commit (`1 file changed`).

Restore the worktree and the data links:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && git checkout -- site/public/llms.txt && for d in site duckdb parquet; do ln -sfn "/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/$d" "data/$d"; done && git -C .. status --porcelain -- GovBudget | grep -v '^??' ; echo "clean check done"
```
Expected: no tracked change listed (the build's `llms.txt` rewrite is discarded — the release commits its own in Task 23).

- [ ] **Step 22: Record the S4 proof in the ROADMAP**

Insert as the first entry under `## Findings log (what we learned; feeds future phases)` in `docs/superpowers/ROADMAP.md`, filling every `<…>` from the logs and reports named in brackets (all under `.proofs/s4-logs/`):

```markdown
- **<YYYY-MM-DD>: Families piece 1, S4 proof — pre-S4 code against S4 code on one
  post-S3 snapshot.** Snapshot `.proofs/s4` (`govbudget proof snapshot`, <created_at>;
  DuckDB sha256 <duckdb_sha256_at_copy> at copy, <duckdb_sha256> after <views_rewritten>
  views were repointed at the copy; site <site_sha256>; raw_docs <raw_docs_sha256>;
  Postgres dump <pg_dump_sha256> restored as `govbudget_proof_s4`) [snapshot-shas.json].
  V3 on the pinned state: `dbt test` of the seed, the map and the program table
  passed, 0 views read the live lake, 0 undecided keys, the DuckDB bytes unchanged
  [v3-dbt-test.log]. Export A ran the code at `<A_SHA>` (the parent of the decade-tier
  switch), export B the code at `<B_SHA>`, each in its own clone (`s4-A`, `s4-B`)
  through `govbudget export-site`, both with <n> dbt test nodes in their manifests.
  The masked A/B diff passes the spec §10 rule list
  (`docs/superpowers/plans/2026-10-02-era-procurement-history-expected-diff.json`)
  [diff.txt]. V6: all <citations.a_facts> facts A publishes are in B unchanged; B adds
  <citations.new_in_b>; the 72 F-15 A1 era leaves moved only `pe_bli` (null →
  F01500/F015EX/F15EWS) and `retrieved_at` (space → `T` form);
  `budget_lines_decade` keeps all <a_rows> A rows (B <b_rows>) [s4-fact-stability.json].
  Page gain: <gained.pb2026> of <procurement_pages.pb2026> procurement pages with
  PB2026 lines (<all_seven_editions.pb2026> of them with all seven era editions)
  and <gained.decade_only> of <procurement_pages.decade_only> decade-only
  procurement pages gain PB2017–PB2023 points, <new_points> points in all; no R&D
  page changed [s4-report.json]. V7: no complete PDF receipt lost; F-15 default
  cells 67/67; era P-1 receipts complete by edition PB2017 <c>/<f>, PB2018 <c>/<f>,
  PB2019 <c>/<f>, PB2020 <c>/<f>, PB2021 <c>/<f>, PB2022 <c>/<f>, PB2023 <c>/<f>.
  V5, V8 (`npm run verify`: overall PASS), verify-phase5e, verify-era-map and
  verify-lineage pass on B; the normalized F-15 page equals the S0 snapshot and
  `f15_funding_history.json` is unchanged; the sitemap keeps 4,349 URLs; `/data/`
  re-measured with the map row at <raw> / <gzip> (ceilings unchanged).
```

- [ ] **Step 23: Commit the proof note and drop the A worktree**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/docs/superpowers/ROADMAP.md && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "docs(roadmap): families piece 1 S4 proof — A/B diff passes the spec §10 rules; measured page gain" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git worktree remove --force /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-proof-a && git worktree list | grep -c families-proof-a
```
Expected: the commit, then `0`. Keep `.proofs/s4`, `.proofs/s4-A`, `.proofs/s4-B`, `.proofs/s4-logs` and the `govbudget_proof_s4` database: Task 22 clones `s4-B` and sources `s4/env.sh`; Task 23 reads `s4-logs/s4-report.json` and asks the owner before removing any of them.

---
