#!/usr/bin/env python3
"""P2b: the /years/ shard proof (families piece-1 follow-ups, Task 21b; design
§3.2-§3.6, §7 P2b, Q11, Q15).

A is a data/site tree exported by the deployed code (one schema-1
json/years_matrix.json); B is a tree exported by the follow-ups code from the
SAME snapshot (a schema-2 core json/years_matrix.json plus the lazy
json/years_matrix/decade.json and json/years_matrix/detail.json). The proof:

  1. B's three files carry one 64-hex build_id; when the core lists its
     shards (a list of {"path", "bytes", "sha256", ...}), each listed file
     has exactly those bytes and that sha256.
  2. B merged (govbudget.export_site.merge_years_matrix, the inverse of
     split_years_matrix) has A's header (every top-level key A has, except
     schema_version) and A's rows, keyed (org, slug or pe_bli).
  3. Every A cell is in B with the same fid and value.
  4. Non-decade cells are identical, except on the seven org-split rows
     (ORG_SPLIT_ROWS, ROADMAP #207), where B may add amount-type or delta
     cells (reported).
  5. Leg j: for every B row and every decade column, a cell is present if and
     only if the row's program sidecar json/program_details/<slug or
     pe_bli>.json has a decade_series point with the same (kind, edition, fy),
     and the cell's fid and value equal the point's.
  6. Every file is at most MAX_BYTES on disk, and the core is at most
     CORE_GZIP_MAX bytes at gzip level 9 (the exporter's own constants).

It reports the decade cells B adds (era = edition <= 2023, modern; default
view; the org-split rows) and the totals chart's balanced panel for A and B
(rows with a value in every default decade column; FY2024A->FY2026R and
first->last change), and compares the added counts with --expect-* when given.

Last line `years-shard-proof: PASS|FAIL`; exit 0/1; a tool error prints
`years-shard-proof: ERROR — <message>` and exits 2.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ORG_SPLIT_ROWS = frozenset({"20-DCSA", "20-DTRA", "30-DMACT", "30-DTRA", "30-OSD", "500-DHRA", "500-DLA"})
ERA_LAST_EDITION = 2023
ROW_META = frozenset({"cells", "np"})
_HEX64 = re.compile(r"[0-9a-f]{64}")
CORE, DECADE, DETAIL = "years_matrix.json", "years_matrix/decade.json", "years_matrix/detail.json"
SHOW = 20


def _load(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    return json.loads(data), data


def _rows(payload: dict) -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    for org in payload["orgs"]:
        for row in org["programs"]:
            key = (org["org"], row.get("slug") or row["pe_bli"])
            if key in out:
                raise ValueError(f"duplicate row key {key}")
            out[key] = row
    return out


def _panel(payload: dict, rows: dict) -> dict:
    meta = {c["key"]: c for c in payload["decade_columns"]}
    keys = payload["decade_default_columns"]
    panel = [r for r in rows.values() if all(r["cells"].get(k) is not None for k in keys)]
    sums = {k: sum(r["cells"][k]["v"] for r in panel) for k in keys}
    ordered = sorted(keys, key=lambda k: meta[k]["fy"])

    def pct(x, y):
        return round(100 * (sums[y] - sums[x]) / sums[x], 2) if sums.get(x) else None

    return {"programs": len(panel), "of": len(rows),
            "first_to_last_pct": pct(ordered[0], ordered[-1]),
            "fy2024a_to_fy2026r_pct": pct("fy2024a", "fy2026r") if {"fy2024a", "fy2026r"} <= set(keys) else None}


def run(a_site: Path, b_site: Path, *, merge=None, max_bytes: int | None = None,
        core_gzip_max: int | None = None) -> dict:
    if merge is None or max_bytes is None or core_gzip_max is None:
        from govbudget import export_site
        merge = merge or export_site.merge_years_matrix
        max_bytes = max_bytes or export_site._YEARS_MATRIX_MAX_BYTES
        core_gzip_max = core_gzip_max or export_site._YEARS_MATRIX_CORE_GZIP_MAX
    a_json, b_json = Path(a_site) / "json", Path(b_site) / "json"
    violations: list[str] = []

    a_payload, _ = _load(a_json / CORE)
    files = {name: _load(b_json / name) for name in (CORE, DECADE, DETAIL)}
    core, decade, detail = (files[n][0] for n in (CORE, DECADE, DETAIL))
    sizes = {}
    for name, (_, data) in files.items():
        gz = len(gzip.compress(data, compresslevel=9, mtime=0))
        sizes[name] = {"bytes": len(data), "gzip": gz}
        if len(data) > max_bytes:
            violations.append(f"{name}: {len(data):,} bytes, over the {max_bytes:,}-byte cap")
    if sizes[CORE]["gzip"] > core_gzip_max:
        violations.append(f"{CORE}: {sizes[CORE]['gzip']:,} gzip bytes, over {core_gzip_max:,}")

    ids = {name: obj.get("build_id") for name, (obj, _) in files.items()}
    if len(set(ids.values())) != 1 or not _HEX64.fullmatch(str(ids[CORE])):
        violations.append(f"build_id differs or is not 64 hex: {ids}")
    for shard in core.get("shards") or []:
        path = b_json / shard["path"] if (b_json / shard["path"]).is_file() else Path(b_site) / shard["path"]
        data = path.read_bytes() if path.is_file() else None
        if data is None or len(data) != shard.get("bytes") or hashlib.sha256(data).hexdigest() != shard.get("sha256"):
            violations.append(f"shard manifest entry {shard.get('path')} does not match the file")

    merged = merge(core, decade, detail)
    for key in sorted(set(a_payload) - {"schema_version", "orgs"}):
        if merged.get(key) != a_payload[key]:
            violations.append(f"header {key} differs")
    rows_a, rows_b = _rows(a_payload), _rows(merged)
    if set(rows_a) != set(rows_b):
        violations.append(f"row sets differ: {len(set(rows_a) - set(rows_b))} only in A, "
                          f"{len(set(rows_b) - set(rows_a))} only in B")
    decade_cols = merged["decade_columns"]
    decade_keys = {c["key"] for c in decade_cols}
    defaults = set(merged["decade_default_columns"])
    extra_ok = set(merged["amount_types"]) | set(merged["delta_columns"])

    added = Counter()
    org_split_added: dict[str, list[str]] = {}
    mismatches = 0
    for key in sorted(set(rows_a) & set(rows_b)):
        ra, rb = rows_a[key], rows_b[key]
        slug = key[1]
        for field in sorted((set(ra) | set(rb)) - ROW_META):
            if ra.get(field) != rb.get(field):
                violations.append(f"{slug}: {field} differs")
        for col, cell in ra["cells"].items():
            if rb["cells"].get(col) != cell:
                violations.append(f"{slug}: A cell {col} changed or missing in B")
        b_only = sorted(set(rb["cells"]) - set(ra["cells"]))
        nondecade = [c for c in b_only if c not in decade_keys]
        if nondecade:
            if slug in ORG_SPLIT_ROWS and set(nondecade) <= extra_ok:
                org_split_added[slug] = nondecade
            else:
                violations.append(f"{slug}: B adds non-decade cells {nondecade}")
        sidecar_path = Path(b_site) / "json" / "program_details" / f"{slug}.json"
        series = (json.loads(sidecar_path.read_text()).get("decade_series") or {}) if sidecar_path.is_file() else {}
        points = {(kind, p["edition"], p["fy"]): p for kind, pts in series.items() for p in pts}
        for col in decade_cols:
            cell, point = rb["cells"].get(col["key"]), points.get((col["kind"], col["edition"], col["fy"]))
            if (cell is None) != (point is None) or (cell and (cell["fid"], cell["v"]) != (point["fid"], point["v"])):
                mismatches += 1
                if mismatches <= SHOW:
                    violations.append(f"{slug}: leg j {col['key']} cell {cell} vs sidecar point "
                                      f"{None if point is None else {'fid': point['fid'], 'v': point['v']}}")
                continue
            if cell is not None and col["key"] not in ra["cells"]:
                era = "era" if col["edition"] <= ERA_LAST_EDITION else "modern"
                added[era] += 1
                if col["key"] in defaults:
                    added[f"{era}_default"] += 1
                if slug in ORG_SPLIT_ROWS:
                    added[f"{era}_org_split"] += 1
    if mismatches > SHOW:
        violations.append(f"... leg j: {mismatches} mismatches in all")
    return {"ok": not violations, "sizes": sizes, "build_id": ids[CORE],
            "rows": {"a": len(rows_a), "b": len(rows_b)},
            "decade_cells_added": {k: added.get(k, 0) for k in (
                "era", "modern", "era_default", "modern_default", "era_org_split", "modern_org_split")},
            "org_split_nondecade_added": org_split_added, "leg_j_mismatches": mismatches,
            "panel": {"a": _panel(a_payload, rows_a), "b": _panel(merged, rows_b)},
            "violations": violations}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="P2b: /years/ shards against the v1 matrix and the program sidecars")
    p.add_argument("--a", type=Path, required=True, help="data/site exported by the deployed code")
    p.add_argument("--b", type=Path, required=True, help="data/site exported by the follow-ups code, same snapshot")
    p.add_argument("--expect-era-added", type=int, default=None)
    p.add_argument("--expect-modern-added", type=int, default=None)
    p.add_argument("--report", type=Path, default=None)
    args = p.parse_args(argv)
    try:
        report = run(args.a, args.b)
    except Exception as e:  # noqa: BLE001 — a tool error is exit 2, never a verdict
        print(f"years-shard-proof: ERROR — {e}", file=sys.stderr)
        return 2
    got = report["decade_cells_added"]
    for flag, key in ((args.expect_era_added, "era"), (args.expect_modern_added, "modern")):
        if flag is not None and got[key] != flag:
            report["violations"].append(f"{key} decade cells added {got[key]:,}, expected {flag:,}")
    report["ok"] = not report["violations"]
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    for name, s in report["sizes"].items():
        print(f"{name}: {s['bytes']:,} bytes, {s['gzip']:,} gzip")
    print(f"build_id {report['build_id']}; rows A {report['rows']['a']:,}, B {report['rows']['b']:,}; "
          f"leg j mismatches {report['leg_j_mismatches']:,}")
    print("decade cells added: " + ", ".join(f"{k} {v:,}" for k, v in got.items()))
    print(f"org-split rows' non-decade cells added: {json.dumps(report['org_split_nondecade_added'], sort_keys=True)}")
    for side in ("a", "b"):
        pn = report["panel"][side]
        print(f"totals-chart panel {side.upper()}: {pn['programs']:,} of {pn['of']:,} programs; "
              f"FY2024A->FY2026R {pn['fy2024a_to_fy2026r_pct']}%; first->last {pn['first_to_last_pct']}%")
    for v in report["violations"][:SHOW]:
        print(f"  violation: {v}")
    print(f"years-shard-proof: {'PASS' if report['ok'] else 'FAIL'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
