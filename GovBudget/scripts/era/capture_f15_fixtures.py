#!/usr/bin/env python3
"""Capture the hermetic F-15 identity fixtures (spec 2026-10-02 era procurement, §8 V5, §9 S0).

Reads, never writes, the live export and lake:
  - fct_decade_series from the DuckDB file (read_only=True),
  - the staged jbooks budget_lines/documents parquets beside it,
  - data/site: manifest.json, data/budget_lines.parquet, json/citations.json,
    json/f15_funding_history.json, json/workbook-cells/*, workbooks/*.xlsx.

Writes only into --out-dir (default tests/fixtures/f15/):
  history.json            byte copy of data/site/json/f15_funding_history.json
  history.sha256          its sha256 as 64 hex characters plus a newline
  builder_inputs.json.gz  exactly what build_history/build_program_matrix read:
                          the F-15 member workbook rows, their fct_decade_series
                          rows, the member fact ids already in budget_lines,
                          the 207 workbook-cell previews, and every derived
                          citation with at least one F-15 workbook leaf among
                          its inputs (a superset of what the matrix may reuse).

Nothing is written unless all of these hold: the member-only rebuild equals
the full-lake rebuild; the previews rebuilt from the sha-named workbooks equal
the shipped workbook-cells entries; the rebuild from the captured inputs is
byte-identical to the shipped history; and that history's sha256 equals
--expect-sha256 (the value the owner-approved record pins).

Usage (from GovBudget/):
  S0 capture, from the live export:
  GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data \\
    uv run --project . python scripts/era/capture_f15_fixtures.py \\
    --expect-sha256 9f70c770eb7c91e33919fd66e6f316a1461035cdfcfa446a725f063d593c8800
  S5 re-pin, from the proof clone (never the live lake; tests/fixtures/f15/README.md):
  uv run --project . python scripts/era/capture_f15_fixtures.py \\
    --site-dir /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s5/site \\
    --duckdb /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s5/duckdb/govbudget.duckdb \\
    --out-dir tests/fixtures/f15 --expect-sha256 <S5 sha>
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

import duckdb

from govbudget import config
from govbudget.export_site import _stage_parquet_path
from govbudget.f15_funding_history import _json_bytes, build_history, build_program_matrix, member_row
from govbudget.workbook_cells import build_workbook_previews

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_SCHEMA = 1
SERIES_SQL = ("select pe_bli, fy, edition_year as edition, amount_type_kind as kind, amount, amount_type, n_source_rows "
              "from fct_decade_series")
# The exact projection export_f15_funding_history reads (f15_funding_history.py:337-344).
SOURCE_SQL = """select b.exhibit, cast(b.fiscal_year as integer) as edition,
    b.account, b.account_title, b.organization, b.budget_activity,
    b.budget_activity_title, b.pe_bli, b.title, b.amount_type,
    cast(b.amount_thousands as double) as amount_thousands,
    d.sha256, b.source_sheet as sheet, b.source_cells as cells,
    d.source_url as official_url, d.downloaded_at as retrieved_at
    from read_parquet(?) b join read_parquet(?) d on b.source_document_id=d.id
    where b.exhibit in ('P-1','R-1')"""


def _rows(cursor) -> list[dict]:
    names = [d[0] for d in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def capture(*, site_dir: Path, duckdb_path: Path) -> tuple[dict, bytes]:
    """Return (fixture, shipped history bytes); raise when any proof fails."""
    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        series = _rows(con.execute(SERIES_SQL))
    finally:
        con.close()
    lake = _stage_parquet_path(duckdb_path, "jbooks", "budget_lines.parquet")
    documents = _stage_parquet_path(duckdb_path, "jbooks", "documents.parquet")
    if not lake or not documents:
        raise SystemExit(f"capture_f15_fixtures: no staged jbooks parquets beside {duckdb_path}")
    con = duckdb.connect()
    try:
        source_rows = _rows(con.execute(SOURCE_SQL, [str(lake), str(documents)]))
        current_fact_ids = {row[0] for row in con.execute(
            "select fact_id from read_parquet(?)", [str(site_dir / "data" / "budget_lines.parquet")]).fetchall()}
    finally:
        con.close()
    retrieved_at = json.loads((site_dir / "manifest.json").read_text())["built_at"]

    members = sorted((row for row in source_rows if member_row(row)),
                     key=lambda r: (r["edition"], r["exhibit"], r["pe_bli"], r["budget_activity"] or "", r["amount_type"]))
    grains = {(r["pe_bli"], r["edition"], r["amount_type"]) for r in members}
    member_series = sorted((p for p in series if (p["pe_bli"], p["edition"], p["amount_type"]) in grains),
                           key=lambda p: (p["edition"], p["pe_bli"], p["fy"], p["kind"], p["amount_type"]))

    payload, citations, workbook_rows, _ = build_history(
        members, member_series, retrieved_at=retrieved_at, current_fact_ids=current_fact_ids)
    full_payload, _, _, _ = build_history(
        source_rows, series, retrieved_at=retrieved_at, current_fact_ids=current_fact_ids)
    if _json_bytes(payload) != _json_bytes(full_payload):
        raise SystemExit("capture_f15_fixtures: the member-only rebuild differs from the full-lake rebuild")
    leaves = set(workbook_rows)

    previews = build_workbook_previews(workbook_dir=site_dir / "workbooks",
                                       citations={fid: citations[fid] for fid in sorted(leaves)})
    shipped_previews = {}
    for prefix in sorted({fid[:2] for fid in leaves}):
        shard = json.loads((site_dir / "json" / "workbook-cells" / f"{prefix}.json").read_text())
        shipped_previews.update({fid: obj for fid, obj in shard.items() if fid in leaves})
    if set(previews) != leaves or _json_bytes(previews) != _json_bytes(shipped_previews):
        raise SystemExit("capture_f15_fixtures: rebuilt workbook previews differ from the shipped workbook-cells entries")

    registry = json.loads((site_dir / "json" / "citations.json").read_text())
    subset = {}
    for fid, citation in sorted(registry.items()):
        if citation.get("kind") != "derived":
            continue
        try:
            inputs = json.loads(citation.get("inputs") or "null")
        except (TypeError, ValueError):
            continue
        if isinstance(inputs, list) and leaves & {item for item in inputs if isinstance(item, str)}:
            subset[fid] = citation

    shipped = (site_dir / "json" / "f15_funding_history.json").read_bytes()
    for label, existing in (("full registry", registry), ("captured registry subset", subset)):
        rebuilt, _, _ = build_program_matrix(payload, previews, existing_citations=existing, retrieved_at=retrieved_at)
        if _json_bytes(rebuilt) != shipped:
            raise SystemExit(f"capture_f15_fixtures: rebuild with the {label} differs from the shipped history")

    fixture = dict(
        schema=FIXTURE_SCHEMA,
        captured_from=dict(
            site_built_at=retrieved_at,
            history_sha256=_sha256(shipped),
            citations_json_sha256=_sha256((site_dir / "json" / "citations.json").read_bytes()),
        ),
        retrieved_at=retrieved_at,
        source_rows=members,
        series=member_series,
        current_fact_ids=sorted(leaves & current_fact_ids),
        previews=previews,
        registry=subset,
    )
    return fixture, shipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site-dir", type=Path, default=config.SITE_DIR)
    parser.add_argument("--duckdb", type=Path, default=config.DUCKDB_PATH)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "tests" / "fixtures" / "f15")
    parser.add_argument("--expect-sha256", required=True)
    args = parser.parse_args(argv)

    fixture, shipped = capture(site_dir=args.site_dir, duckdb_path=args.duckdb)
    actual = fixture["captured_from"]["history_sha256"]
    if actual != args.expect_sha256:
        print(f"capture_f15_fixtures: shipped history sha256 {actual} != expected {args.expect_sha256}", file=sys.stderr)
        return 1
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "history.json").write_bytes(shipped)
    (args.out_dir / "history.sha256").write_text(actual + "\n")
    (args.out_dir / "builder_inputs.json.gz").write_bytes(gzip.compress(_json_bytes(fixture), mtime=0))
    print(json.dumps(dict(
        history_sha256=actual, history_bytes=len(shipped), source_rows=len(fixture["source_rows"]),
        series=len(fixture["series"]), previews=len(fixture["previews"]), registry=len(fixture["registry"]),
        current_fact_ids=len(fixture["current_fact_ids"]),
    ), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
