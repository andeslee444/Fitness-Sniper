#!/usr/bin/env python3
"""Fact-level judgement of an A/B pair of data/site trees (families piece-1
follow-ups, Task 21b; design §7 P1 and P2, §1 "Facts", §4.7).

`govbudget proof diff` judges files and JSON pointers; this judges facts.

  * Every fact A publishes is in B. A fact in both may differ only by export
    noise and run stamps (judged by era.fact_stability.compare_citations,
    which applies proof diff's own rules, with no F-15 restamp expected), or —
    when an --expect file names it under "moved" — as a derived aggregate
    that GAINED inputs: B's inputs are A's plus k facts, each new in B and
    explained (below), no input is dropped, only `inputs` and
    `recorded_value` change, and recorded_value moved by exactly the summed
    amount of the added inputs, which must equal the expected delta. A named
    aggregate that did not move is a failure too.
  * Every fact new in B is explained: a workbook citation whose pe_bli is in
    "explained_by_pe_bli", or a derived citation every input of which is an
    explained fact new in B. Without --expect, B may add no fact at all.
  * Every row of each named site parquet in A is a row of B (EXCEPT ALL,
    every column), and each row only B has carries a pe_bli in that
    dataset's allowed list. Without --expect the datasets compare equal both
    ways: data/budget_lines.parquet, data/budget_lines_decade.parquet and
    data/fct_budget_trajectory.parquet.
  * With --diff-report (a `proof diff --report` file for the same pair): a
    breakdown file json/breakdowns/<fid>.json changed only for a moved fact,
    exists only in B only for a fact new in B, and never exists only in A.

--expect is a JSON object:
  {"explained_by_pe_bli": ["0390DOM"],
   "moved": {"<fid>": {"why": "...", "delta_thousands": "3243.000"}, ...},
   "rows": {"data/budget_lines.parquet": ["0390DOM"], ...}}

Last line `fact-delta: PASS|FAIL`; exit 0/1; a tool error prints
`fact-delta: ERROR — <message>` and exits 2.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # scripts/, for era.fact_stability when run directly
from era.fact_stability import compare_citations  # noqa: E402

DEFAULT_ROWS = ("data/budget_lines.parquet", "data/budget_lines_decade.parquet",
                "data/fct_budget_trajectory.parquet")
MOVABLE_FIELDS = frozenset({"inputs", "recorded_value"})
SHOW = 20


def _inputs(citation: dict) -> list[str]:
    raw = citation.get("inputs")
    value = json.loads(raw) if isinstance(raw, str) else raw
    return [item for item in value or [] if isinstance(item, str)]


def _amount(citation: dict) -> Decimal:
    if citation.get("kind") == "workbook":
        return Decimal(str(citation["amount_thousands"]))
    return Decimal(str(citation["recorded_value"]))


def explained_new(a: dict, b: dict, pe_bli: set[str]) -> tuple[set[str], list[str]]:
    """(explained, unexplained) facts new in B."""
    new = set(b) - set(a)
    explained = {fid for fid in new if b[fid].get("kind") == "workbook" and b[fid].get("pe_bli") in pe_bli}
    grew = True
    while grew:
        grew = False
        for fid in sorted(new - explained):
            if b[fid].get("kind") != "derived":
                continue
            ins = _inputs(b[fid])
            if ins and all(i in explained for i in ins):
                explained.add(fid)
                grew = True
    return explained, sorted(new - explained)


def judge_citations(a: dict, b: dict, *, expect: dict, noise_classes: list[dict] | None) -> dict:
    base = compare_citations(a, b, {}, expected_f15=0, noise_classes=noise_classes)
    pe_bli = set(expect.get("explained_by_pe_bli", []))
    moved_expected: dict = expect.get("moved", {})
    explained, unexplained = explained_new(a, b, pe_bli)
    violations = [f"missing in B: {fid}" for fid in base["missing"]]
    violations += [f"new in B and not explained by {sorted(pe_bli) or 'nothing'}: {fid} ({b[fid].get('kind')})"
                   for fid in unexplained]
    changed: dict[str, set[str]] = {}
    for item in base["changed"]:
        changed.setdefault(item["fact_id"], set()).add(item["field"])
    moved = {}
    for fid, fields in sorted(changed.items()):
        if fid not in moved_expected:
            violations.append(f"changed outside the expected moves: {fid} ({', '.join(sorted(fields))})")
            continue
        ca, cb = a[fid], b[fid]
        if ca.get("kind") != "derived" or cb.get("kind") != "derived":
            violations.append(f"moved fact {fid} is not a derived aggregate on both sides")
            continue
        if not fields <= MOVABLE_FIELDS:
            violations.append(f"moved fact {fid} changed {sorted(fields - MOVABLE_FIELDS)} (only inputs/recorded_value may)")
            continue
        ins_a, ins_b = _inputs(ca), _inputs(cb)
        dropped = sorted(set(ins_a) - set(ins_b))
        added = sorted(set(ins_b) - set(ins_a))
        if dropped:
            violations.append(f"moved fact {fid} dropped inputs {dropped[:5]}")
            continue
        if not added or any(i not in explained for i in added):
            violations.append(f"moved fact {fid} gained inputs that are not explained new facts: {added[:5]}")
            continue
        delta = Decimal(cb["recorded_value"]) - Decimal(ca["recorded_value"])
        summed = sum((_amount(b[i]) for i in added), Decimal(0))
        want = Decimal(moved_expected[fid]["delta_thousands"])
        if delta != summed or delta != want:
            violations.append(f"moved fact {fid}: recorded_value moved {delta}, added inputs sum {summed}, expected {want}")
            continue
        moved[fid] = {"added_inputs": added, "delta_thousands": str(delta),
                      "a": ca["recorded_value"], "b": cb["recorded_value"]}
    for fid in sorted(set(moved_expected) - set(changed)):
        violations.append(f"expected move did not happen: {fid} ({moved_expected[fid].get('why', '')})")
    new_kinds: dict[str, int] = {}
    for fid in set(b) - set(a):
        new_kinds[b[fid].get("kind")] = new_kinds.get(b[fid].get("kind"), 0) + 1
    return {"ok": not violations, "a_facts": len(a), "b_facts": len(b), "new_in_b": len(set(b) - set(a)),
            "new_by_kind": dict(sorted(new_kinds.items())), "moved": moved,
            "noise_equivalent": base["noise_equivalent"],
            "reorder_classes_trusted": base["reorder_classes_trusted"], "violations": violations}


def judge_rows(a_site: Path, b_site: Path, rel: str, allowed: list[str] | None) -> dict:
    import duckdb

    pa, pb = Path(a_site) / rel, Path(b_site) / rel
    con = duckdb.connect()
    try:
        a, b = f"read_parquet('{pa.as_posix()}')", f"read_parquet('{pb.as_posix()}')"
        schema_a = [r[:2] for r in con.execute(f"describe select * from {a}").fetchall()]
        schema_b = [r[:2] for r in con.execute(f"describe select * from {b}").fetchall()]
        if schema_a != schema_b:
            return {"ok": False, "violations": [f"{rel}: schema differs"]}
        rows_a = con.execute(f"select count(*) from {a}").fetchone()[0]
        rows_b = con.execute(f"select count(*) from {b}").fetchone()[0]
        lost = con.execute(f"select count(*) from (select * from {a} except all select * from {b})").fetchone()[0]
        added = con.execute(f"select pe_bli, count(*) from (select * from {b} except all select * from {a})"
                            " group by pe_bli order by pe_bli").fetchall()
    finally:
        con.close()
    violations = [f"{rel}: {lost} row(s) of A are not in B"] if lost else []
    allowed_set = set(allowed or [])
    bad = [(p, n) for p, n in added if p not in allowed_set]
    if bad:
        violations.append(f"{rel}: rows only in B with pe_bli outside {sorted(allowed_set)}: {bad[:SHOW]}")
    return {"ok": not violations, "rows_a": rows_a, "rows_b": rows_b, "lost": lost,
            "added_by_pe_bli": {p: n for p, n in added}, "violations": violations}


def judge_breakdowns(diff_report: dict, *, moved: set[str], new_in_b: set[str]) -> dict:
    files = diff_report["report"]["files"]
    violations = []
    counts = {"changed": 0, "only_b": 0}
    for rel, entry in sorted(files.items()):
        if not rel.startswith("json/breakdowns/"):
            continue
        fid = rel[len("json/breakdowns/"):-len(".json")]
        status = entry["status"]
        if status in ("identical", "equivalent", "reordered"):
            continue
        if status == "changed" and fid in moved:
            counts["changed"] += 1
        elif status == "only_b" and fid in new_in_b:
            counts["only_b"] += 1
        else:
            violations.append(f"breakdown {fid}: {status}")
    return {"ok": not violations, **counts, "violations": violations}


def run(a_site: Path, b_site: Path, *, expect: dict | None, noise_from: Path | None,
        diff_report: Path | None) -> dict:
    from govbudget.proof import load_noise_classes

    a_site, b_site = Path(a_site), Path(b_site)
    expect = expect or {}
    a = json.loads((a_site / "json" / "citations.json").read_text())
    b = json.loads((b_site / "json" / "citations.json").read_text())
    classes = load_noise_classes(noise_from) if noise_from else None
    citations = judge_citations(a, b, expect=expect, noise_classes=classes)
    rows_spec = expect.get("rows") or {rel: [] for rel in DEFAULT_ROWS}
    rows = {rel: judge_rows(a_site, b_site, rel, allowed) for rel, allowed in sorted(rows_spec.items())}
    report = {"citations": citations, "rows": rows, "breakdowns": None}
    if diff_report is not None:
        report["breakdowns"] = judge_breakdowns(json.loads(Path(diff_report).read_text()),
                                                moved=set(citations["moved"]), new_in_b=set(b) - set(a))
    parts = [citations, *rows.values()] + ([report["breakdowns"]] if report["breakdowns"] else [])
    report["ok"] = all(part["ok"] for part in parts)
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fact-level judgement of two data/site trees")
    p.add_argument("--a", type=Path, required=True)
    p.add_argument("--b", type=Path, required=True)
    p.add_argument("--expect", type=Path, default=None, help="explained pe_bli, moved aggregates, row rules")
    p.add_argument("--noise-from", type=Path, default=None, help="a `proof diff --control --write-noise` file")
    p.add_argument("--diff-report", type=Path, default=None, help="the `proof diff --report` file for this pair")
    p.add_argument("--report", type=Path, default=None)
    args = p.parse_args(argv)
    try:
        expect = json.loads(args.expect.read_text()) if args.expect else None
        report = run(args.a, args.b, expect=expect, noise_from=args.noise_from, diff_report=args.diff_report)
    except Exception as e:  # noqa: BLE001 — a tool error is exit 2, never a verdict
        print(f"fact-delta: ERROR — {e}", file=sys.stderr)
        return 2
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    c = report["citations"]
    print(f"citations: A {c['a_facts']:,}, B {c['b_facts']:,}, new in B {c['new_in_b']:,} "
          f"{json.dumps(c['new_by_kind'], sort_keys=True)}, moved {len(c['moved'])}, "
          f"noise-equivalent fields {sum(c['noise_equivalent'].values()):,}")
    for fid, m in c["moved"].items():
        print(f"  moved {fid}: {m['a']} -> {m['b']} (+{m['delta_thousands']}, inputs +{len(m['added_inputs'])})")
    for rel, r in report["rows"].items():
        if "rows_a" in r:
            print(f"{rel}: A {r['rows_a']:,} rows, B {r['rows_b']:,}, A rows not in B {r['lost']:,}, "
                  f"B-only rows by pe_bli {json.dumps(r['added_by_pe_bli'], sort_keys=True)}")
    if report["breakdowns"]:
        bd = report["breakdowns"]
        print(f"breakdowns: changed {bd['changed']} (moved facts), only in B {bd['only_b']} (new facts)")
    violations = c["violations"] + [v for r in report["rows"].values() for v in r["violations"]]
    violations += report["breakdowns"]["violations"] if report["breakdowns"] else []
    for v in violations[:SHOW]:
        print(f"  violation: {v}")
    if len(violations) > SHOW:
        print(f"  ... and {len(violations) - SHOW} more violation(s) (see --report)")
    print(f"fact-delta: {'PASS' if report['ok'] else 'FAIL'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
