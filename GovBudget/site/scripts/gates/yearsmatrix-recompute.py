"""yearsmatrix-recompute.py — G8 leg (a) helper.

Recomputes sampled /years/ matrix cells INDEPENDENTLY from the parquet lake
(data/site/data/budget_lines.parquet + jbook_details.parquet) so the gate can
compare the rendered payload against a from-source recomputation — the same
trust chain the exporter claims (trajectory pivot == sum of titled detail
lines; project cells == jbook_details rows).

Invoked by site/scripts/gates/yearsmatrix.mjs:
    uv run python site/scripts/gates/yearsmatrix-recompute.py <request.json> [site_data_dir]

site_data_dir defaults to data/site/data (tests pass a fixture directory).

Request JSON:
    {
      "programs": [{"pe_bli": ..., "org": <section org>, "at": <amount_type>}],
      "deltas":   [{"pe_bli": ..., "org": <section org>}],
      "projects": [{"pe_bli": ..., "project_number": ..., "scenario": ...}],
      "decade_fids": ["<fact_id>", ...]
    }

Response JSON (stdout):
    {
      "programs": {"{pe_bli}|{org}|{at}": float|null},
      "deltas":   {"{pe_bli}|{org}": float|null},
      "projects": {"{pe_bli}|{project_number}|{scenario}": float|null},
      "decade":   {"{fact_id}": {"v": float, "n": int, "fys": [int],
                                 "pes": [str], "shas": [str],
                                 "era": [{"era_key", "program_key",
                                          "decision", "program_account",
                                          "program_org"}]} | null}
    }

Program cells: sum(amount_thousands) over budget_lines.parquet detail rows
(title IS NOT NULL — the rollup+detail dedup rule) for
(pe_bli, workbook_org(org), amount_type); null when no rows.
Deltas: fy_2026_total sum − fy_2025_total sum; null unless both exist.
Project cells: jbook_details.parquet amount_millions for
(pe_bli, project_number, scenario) — LAST row in file order (mirrors the
exporter's last-wins dedup, which mirrors the program-page scenarioMap).
Decade fids (Phase 5E, G8 legs f+g): per workbook fact_id, the matching
budget_lines_decade.parquet rows aggregated — value sum, row count, and
the DISTINCT fiscal_years (edition years), pe_blis and document sha256s
behind the fact. The gate checks the value against the payload cell AND
that every source row's edition equals the column's stated edition.
Era rows (ROADMAP #193): a row whose pe_bli is an era procurement key
('3020F-AF-L8') is listed under "era" with its p1_era_line_map row for
(edition = fiscal_year, era_key = pe_bli) — program_key and decision null
when the map has none — so the gate can prove the cell reaches its program
through a reviewed decision.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

from govbudget.config import ROOT
from govbudget.jbooks.era_keys import is_era_procurement_key
from govbudget.jbooks.orgs import workbook_org


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(
            "usage: yearsmatrix-recompute.py <request.json> [site_data_dir]",
            file=sys.stderr,
        )
        return 2
    request = json.loads(Path(sys.argv[1]).read_text())
    data_dir = Path(sys.argv[2]) if len(sys.argv) == 3 else ROOT / "data" / "site" / "data"
    BL_PARQUET = data_dir / "budget_lines.parquet"
    JD_PARQUET = data_dir / "jbook_details.parquet"
    DEC_PARQUET = data_dir / "budget_lines_decade.parquet"
    MAP_PARQUET = data_dir / "p1_era_line_map.parquet"

    if not BL_PARQUET.exists() or not JD_PARQUET.exists():
        print(
            f"parquet lake missing: {BL_PARQUET} / {JD_PARQUET}",
            file=sys.stderr,
        )
        return 2

    con = duckdb.connect()
    bl = str(BL_PARQUET).replace("'", "''")
    jd = str(JD_PARQUET).replace("'", "''")

    def _sum_lines(pe_bli: str, org: str, at: str):
        row = con.execute(
            f"select sum(amount_thousands) from read_parquet('{bl}')"
            " where pe_bli = ? and organization = ? and amount_type = ?"
            " and title is not null",
            [pe_bli, workbook_org(org), at],
        ).fetchone()
        return float(row[0]) if row and row[0] is not None else None

    out: dict = {"programs": {}, "deltas": {}, "projects": {}}

    for req in request.get("programs", []):
        pe, org, at = req["pe_bli"], req["org"], req["at"]
        out["programs"][f"{pe}|{org}|{at}"] = _sum_lines(pe, org, at)

    for req in request.get("deltas", []):
        pe, org = req["pe_bli"], req["org"]
        fy25 = _sum_lines(pe, org, "fy_2025_total")
        fy26 = _sum_lines(pe, org, "fy_2026_total")
        out["deltas"][f"{pe}|{org}"] = (
            fy26 - fy25 if fy25 is not None and fy26 is not None else None
        )

    for req in request.get("projects", []):
        pe, pn, scenario = req["pe_bli"], req["project_number"], req["scenario"]
        row = con.execute(
            f"select amount_millions from read_parquet('{jd}', file_row_number=true)"
            " where pe_bli = ? and project_number = ? and scenario = ?"
            " order by file_row_number desc limit 1",
            [pe, pn, scenario],
        ).fetchone()
        out["projects"][f"{pe}|{pn}|{scenario}"] = (
            float(row[0]) if row and row[0] is not None else None
        )

    decade_fids = request.get("decade_fids", [])
    out["decade"] = {}
    if decade_fids:
        for needed in (DEC_PARQUET, MAP_PARQUET):
            if not needed.exists():
                print(f"decade recompute input missing: {needed}", file=sys.stderr)
                return 2
        dec = str(DEC_PARQUET).replace("'", "''")
        emap = str(MAP_PARQUET).replace("'", "''")
        for fid in decade_fids:
            rows = con.execute(
                f"select d.amount_thousands, d.fiscal_year, d.pe_bli,"
                f" d.document_sha256, m.program_key, m.decision,"
                f" m.program_account, m.program_org"
                f" from read_parquet('{dec}') d"
                f" left join read_parquet('{emap}') m"
                f" on m.edition = d.fiscal_year and m.era_key = d.pe_bli"
                f" where d.fact_id = ?",
                [fid],
            ).fetchall()
            if not rows or any(r[0] is None for r in rows):
                out["decade"][fid] = None
                continue
            out["decade"][fid] = {
                "v": float(sum(r[0] for r in rows)),
                "n": len(rows),
                "fys": sorted({int(r[1]) for r in rows}),
                "pes": sorted({r[2] for r in rows}),
                "shas": sorted({r[3] for r in rows}),
                "era": [
                    {
                        "era_key": r[2],
                        "program_key": r[4],
                        "decision": r[5],
                        "program_account": r[6],
                        "program_org": r[7],
                    }
                    for r in rows
                    if is_era_procurement_key(r[2])
                ],
            }

    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
