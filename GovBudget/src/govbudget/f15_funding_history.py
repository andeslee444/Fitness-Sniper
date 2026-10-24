"""Cited, edition-scoped F-15 TOA history; never a lifetime aircraft cost.

Era procurement identifiers are line numbers, not durable program identities.
Their membership is reviewed at (edition, account, organization, activity, key)
and checked against the exact filed title. Existing scenario selection comes
from fct_decade_series; we never sum base/OCO/total or request/reconciliation
alternatives. Every annual fact sums the selected workbook leaf facts once.
"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal
import json
import os
from pathlib import Path
import tempfile

from govbudget import platform_families, platform_family_history
from govbudget.jbooks.era_keys import _ERA_KEY_RE
from govbudget.platform_family_history import _json_bytes as _json_bytes
from govbudget.platform_family_history import program_entries

# Source: the registry entry f-15 in data-seeds/platform_families.json and its two CSVs; tests/test_f15_registry_parity.py holds the 88538c6a literals.
F15 = platform_families.load_registry(platform_families.DEFAULT_PATHS)["f-15"]


def _facade_error(file: str, row: str, reason: str) -> platform_families.RegistryError:
    return platform_families.RegistryError([f"platform-families: {file}:{row}: the F-15 facade {reason}"])


def _one_title(member: platform_families.Member) -> str:
    titles = {title for _edition, title in member.titles_seen}
    if len(titles) != 1:
        raise _facade_error("platform_family_members.csv", member.member_row_id,
                            f"needs one title in titles_seen, found {sorted(titles)}")
    return next(iter(titles))


def _era_rows(family: platform_families.Family) -> list[tuple[int, int, platform_families.EraLine]]:
    """(edition, line, era line), editions and lines ascending as integers: the CSV's
    string order puts L25 before L3, so file order is never kept."""
    rows = []
    for era in family.era_lines:
        match = _ERA_KEY_RE.fullmatch(era.era_key)
        try:
            line = int(match.group(3)) if match else None
        except ValueError:
            line = None
        if line is None:
            raise _facade_error("platform_family_era_lines.csv", f"f-15|{era.edition}|{era.era_key}",
                                "needs an integer line number")
        rows.append((era.edition, line, era))
    return sorted(rows, key=lambda row: row[:2])


def _era_members(family: platform_families.Family) -> dict[int, list[tuple[int, str, str]]]:
    out: dict[int, list[tuple[int, str, str]]] = {}
    for edition, line, era in _era_rows(family):
        out.setdefault(edition, []).append((line, era.budget_activity, era.filed_title))
    return out


def _era_program_codes(family: platform_families.Family) -> dict[int, dict[int, str]]:
    code_of = {m.member_id: m.code for m in family.members}
    out: dict[int, dict[int, str]] = {}
    for edition, line, era in _era_rows(family):
        out.setdefault(edition, {})[line] = code_of[era.member_id]
    return out


def _note_fields(note: platform_families.ProgramNote) -> dict:
    return dict(note=note.note, note_fact_id=note.note_fact_id)


MODERN_MEMBERS = {m.code: (m.exhibit, m.account, _one_title(m)) for m in F15.code_keyed}
ERA_MEMBERS = _era_members(F15)
ERA_PROGRAM_CODES = _era_program_codes(F15)
PROGRAM_NOTES = {next(m.code for m in F15.counted if m.member_id == member_id): _note_fields(note)
                 for member_id, note in F15.program_notes.items()}
NOTE_RECEIPTS = {pn.note_fact_id: dict(pn.expected_receipt) for pn in F15.program_notes.values()}
PROGRAMS = program_entries(F15)
SCOPE_NOTE = F15.scope_note
COVERAGE_NOTES = list(F15.coverage_notes)


def check_program_notes(programs, registry) -> None:
    """A program note ships only with the reviewed narrative receipt it quotes."""
    platform_family_history.check_program_notes(F15, programs, registry)


def member_row(row: dict) -> bool:
    """Explicit membership, with source title/account/activity drift rejected."""
    return platform_family_history.member_row(F15, row)


def build_history(source_rows: list[dict], series: list[dict], *, retrieved_at: str, current_fact_ids: set[str] | None = None):
    """Pure builder returning payload, citations and additive breakdowns.

    source_rows must include workbook source identity; series is the canonical
    edition-relative mart. A count/value mismatch stops generation.
    """
    return platform_family_history.build_history(F15, source_rows, series, retrieved_at=retrieved_at,
                                                 current_fact_ids=current_fact_ids)


def build_program_matrix(payload, previews, *, existing_citations, retrieved_at):
    """Group exact workbook inputs by verified code, without changing totals."""
    return platform_family_history.build_program_matrix(F15, payload, previews, existing_citations=existing_citations,
                                                        retrieved_at=retrieved_at)


def export_f15_funding_history(*, duckdb_path, out_dir):
    """Append verified family artifacts to a completed export, idempotently.

    All file replacements are staged only after source/citation/workbook checks.
    Existing canonical facts are retained verbatim and conflicting identities
    raise. This does not rewrite source data or run the general site exporter.
    """
    import duckdb
    from govbudget.export_site import _stage_parquet_path
    from govbudget.workbook_cells import build_workbook_previews

    out_dir = Path(out_dir)
    json_dir = out_dir / "json"
    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        try:
            cursor = con.execute("select pe_bli, fy, edition_year as edition, amount_type_kind as kind, amount, amount_type, n_source_rows from fct_decade_series")
            series = [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]
        except duckdb.CatalogException:
            return None
    finally:
        con.close()
    # Small/partial exports (including test fixtures) need not carry this
    # curated family. A full six-record corpus owns the additional surface.
    if not set(MODERN_MEMBERS).issubset({r["pe_bli"] for r in series}):
        return None
    lake = _stage_parquet_path(duckdb_path, "jbooks", "budget_lines.parquet")
    documents = _stage_parquet_path(duckdb_path, "jbooks", "documents.parquet")
    if not lake or not documents:
        raise ValueError("F-15 family history requires the workbook source lake")
    con = duckdb.connect()
    try:
        cursor = con.execute("""select b.exhibit, cast(b.fiscal_year as integer) as edition,
            b.account, b.account_title, b.organization, b.budget_activity,
            b.budget_activity_title, b.pe_bli, b.title, b.amount_type,
            cast(b.amount_thousands as double) as amount_thousands,
            d.sha256, b.source_sheet as sheet, b.source_cells as cells,
            d.source_url as official_url, d.downloaded_at as retrieved_at
            from read_parquet(?) b join read_parquet(?) d on b.source_document_id=d.id
            where b.exhibit in ('P-1','R-1')""", [str(lake), str(documents)])
        source_rows = [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]
        manifest = json.loads((out_dir / "manifest.json").read_text())
        current_fact_ids = {row[0] for row in con.execute("select fact_id from read_parquet(?)", [str(out_dir / "data" / "budget_lines.parquet")]).fetchall()}
        payload, additions, workbook_rows, breakdowns = build_history(source_rows, series, retrieved_at=manifest["built_at"], current_fact_ids=current_fact_ids)
        if payload is None:
            return None
        registry_path = json_dir / "citations.json"
        registry = json.loads(registry_path.read_text())
        check_program_notes(PROGRAMS, registry)
        wb_citations = {fid: additions[fid] for fid in workbook_rows}
        previews = build_workbook_previews(workbook_dir=out_dir / "workbooks", citations=wb_citations)
        if len(previews) != len(workbook_rows):
            raise ValueError("Not every F-15 workbook input has a verified preview")
        payload, matrix_citations, matrix_breakdowns = build_program_matrix(payload, previews, existing_citations=registry, retrieved_at=manifest["built_at"])
        additions.update(matrix_citations)
        # Preserve published canonical breakdowns, generating only absent ones.
        breakdowns.update({fid: obj for fid, obj in matrix_breakdowns.items() if not (json_dir / "breakdowns" / f"{fid}.json").exists()})
        cit_path = out_dir / "citations" / "citations.parquet"
        cit_schema = con.execute("describe select * from read_parquet(?)", [str(cit_path)]).fetchall()
        cit_columns = [r[0] for r in cit_schema]
        new_rows = []
        for fid, source in additions.items():
            if fid in registry:
                existing = registry[fid]
                fields = ("kind", "units", "amount_thousands", "sha256", "sheet", "cells", "official_url") if source["kind"] == "workbook" else ("kind", "units", "recorded_value", "formula", "inputs")
                if any(existing.get(k) != source.get(k) for k in fields):
                    raise ValueError(f"F-15 citation identity conflicts with published fact {fid}")
                continue
            full = {key: source.get(key) for key in cit_columns if key != "fact_id"}
            new_rows.append([fid if key == "fact_id" else full[key] for key in cit_columns])
            registry[fid] = {key: value for key, value in full.items() if key not in {"scenario", "amount_type"}}
        decade_path = out_dir / "data" / "budget_lines_decade.parquet"
        existing_wb = set(row[0] for row in con.execute("select fact_id from read_parquet(?)", [str(decade_path)]).fetchall())
        decade_new = []
        for fid, row in workbook_rows.items():
            if fid not in existing_wb:
                decade_new.append([fid, row["exhibit"], row["edition"], row["account"], row["account_title"], row["organization"], row["budget_activity"], row["budget_activity_title"], row["pe_bli"], row["title"], row["amount_type"], row["amount_thousands"], "USD thousands", row["sha256"], row["sheet"], row["cells"]])
        # Recompute each chain from independently stored workbook amounts before writes.
        values = {fid: Decimal(str(row["amount_thousands"])) for fid, row in workbook_rows.items()}
        for p in payload["points"] + [payload["cumulative"]]:
            fid = p["fact_id"]
            values[fid] = sum((values[item] for item in json.loads(additions[fid]["inputs"])), Decimal(0))
            if values[fid] != Decimal(additions[fid]["recorded_value"]):
                raise ValueError(f"F-15 derived receipt recomputation failed: {fid}")
        for point in payload["points"]:
            for cell in point["program_cells"]:
                amount = sum((values[fid] for fid in cell["input_fact_ids"]), Decimal(0))
                citation = additions[cell["fact_id"]]
                recorded = citation["recorded_value"] if citation["kind"] == "derived" else citation["amount_thousands"]
                if amount != Decimal(str(cell["amount_thousands"])) or amount != Decimal(str(recorded)):
                    raise ValueError(f"F-15 program cell recomputation failed: {cell['fact_id']}")
        with tempfile.TemporaryDirectory(prefix=".f15-history-", dir=out_dir) as staging:
            stage = Path(staging)
            staged = {}
            def put(relative, data):
                target = stage / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                staged[relative] = target
            def append_parquet(relative, rows):
                src = out_dir / relative
                target = stage / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                con.execute("create or replace temp table history_patch as select * from read_parquet(?)", [str(src)])
                if rows:
                    con.executemany(f"insert into history_patch values ({','.join('?' for _ in rows[0])})", rows)
                if con.execute("select count(*) != count(distinct fact_id) from history_patch").fetchone()[0]:
                    raise ValueError(f"Duplicate fact IDs in {relative}")
                con.execute("copy history_patch to ? (format parquet, compression zstd)", [str(target)])
                staged[relative] = target
                return con.execute("select count(*) from history_patch").fetchone()[0]
            citation_count = append_parquet("citations/citations.parquet", new_rows)
            decade_count = append_parquet("data/budget_lines_decade.parquet", decade_new)
            if citation_count != len(registry):
                raise ValueError("F-15 citation JSON/parquet population mismatch")
            put("json/citations.json", _json_bytes(registry))
            put("json/f15_funding_history.json", _json_bytes(payload))
            for prefix in {fid[:2] for fid in additions}:
                put(f"json/cite-shards/{prefix}.json", _json_bytes({fid: obj for fid, obj in registry.items() if fid.startswith(prefix)}))
            for prefix in {fid[:2] for fid in previews}:
                rel = f"json/workbook-cells/{prefix}.json"
                old = json.loads((out_dir / rel).read_text()) if (out_dir / rel).exists() else {}
                old.update({fid: obj for fid, obj in previews.items() if fid.startswith(prefix)})
                put(rel, _json_bytes(old))
            for fid, obj in breakdowns.items():
                put(f"json/breakdowns/{fid}.json", _json_bytes(obj))
            manifest["citations"] = dict(sorted(Counter(c["kind"] for c in registry.values()).items()))
            manifest["datasets"]["budget_lines_decade"] = decade_count
            manifest["f15_funding_history"] = {"annual_points": len(payload["points"]), "source_facts": len(workbook_rows), "start_fy": payload["start_fy"], "end_fy": payload["end_fy"]}
            manifest["json_sidecars"] = len(list(json_dir.rglob("*.json"))) + sum(not (out_dir / rel).exists() for rel in staged if rel.startswith("json/"))
            put("manifest.json", _json_bytes(manifest))
            meta = json.loads((json_dir / "site_meta.json").read_text())
            meta["counts"]["citations"] = citation_count
            meta["datasets"]["budget_lines_decade"] = decade_count
            put("json/site_meta.json", _json_bytes(meta))
            datasets = json.loads((json_dir / "datasets.json").read_text())
            for entry in datasets.get("datasets", []):
                if entry["name"] == "budget_lines_decade":
                    entry["row_count"] = decade_count
                    entry["bytes"] = staged["data/budget_lines_decade.parquet"].stat().st_size
            put("json/datasets.json", _json_bytes(datasets))
            # All source and value validation precedes the first replacement.
            for relative, path in staged.items():
                destination = out_dir / relative
                if destination.exists() and destination.read_bytes() == path.read_bytes():
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(path, destination)
        return {"annual_points": len(payload["points"]), "source_facts": len(workbook_rows), "added_citations": len(new_rows), "citations": citation_count, "json_files": manifest["json_sidecars"], "cumulative_actuals_thousands": payload["cumulative"]["amount_thousands"]}
    finally:
        con.close()
