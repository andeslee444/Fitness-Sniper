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
