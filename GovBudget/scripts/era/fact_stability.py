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
