"""Cited, edition-scoped F-15 TOA history; never a lifetime aircraft cost.

Era procurement identifiers are line numbers, not durable program identities.
Their membership is reviewed at (edition, account, organization, activity, key)
and checked against the exact filed title. Existing scenario selection comes
from fct_decade_series; we never sum base/OCO/total or request/reconciliation
alternatives. Every annual fact sums the selected workbook leaf facts once.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import tempfile

from govbudget import platform_families
from govbudget.jbooks.era_keys import _ERA_KEY_RE

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
PROGRAMS = [
    dict(id=m.member_id, code=m.code, title=m.display_title, program_slug=m.page_slug or None,
         exhibit=m.exhibit, account=m.account, organization=m.organization,
         **(_note_fields(F15.program_notes[m.member_id]) if m.member_id in F15.program_notes else {}))
    for m in F15.counted
]
SCOPE_NOTE = F15.scope_note
COVERAGE_NOTES = list(F15.coverage_notes)


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def check_program_notes(programs, registry) -> None:
    """A program note ships only with the reviewed narrative receipt it quotes."""
    for program in programs:
        if "note" not in program and "note_fact_id" not in program:
            continue
        fid = program.get("note_fact_id")
        expected = NOTE_RECEIPTS.get(fid)
        citation = registry.get(fid) if fid else None
        if (not program.get("note") or expected is None or citation is None
                or any(citation.get(key) != value for key, value in expected.items())):
            raise ValueError(f"F-15 program note receipt mismatch: {program['code']}/{fid}")


def member_row(row: dict) -> bool:
    """Explicit membership, with source title/account/activity drift rejected."""
    pe, edition = row["pe_bli"], int(row["edition"])
    if row["exhibit"] not in {"P-1", "R-1"}:
        return False
    if pe in MODERN_MEMBERS:
        exhibit, account, title = MODERN_MEMBERS[pe]
        if (row["exhibit"], row["account"], row["title"]) != (exhibit, account, title) or row["organization"] not in {"F", "AF"}:
            raise ValueError(f"F-15 modern member identity drift: {edition}/{pe}")
        return True
    expected = {f"3010F-AF-L{line}": (activity, title) for line, activity, title in ERA_MEMBERS.get(edition, [])}
    if pe not in expected:
        # An F-15-looking new identity needs editorial review, not fuzzy inclusion.
        if "F-15" in (row.get("title") or "").upper() or "F15" in (row.get("title") or "").upper():
            raise ValueError(f"Unreviewed F-15 workbook identity: {edition}/{pe}")
        return False
    activity, title = expected[pe]
    if (row["exhibit"], row["account"], row["organization"], row["budget_activity"], row["title"]) != ("P-1", "3010F", "AF", activity, title):
        raise ValueError(f"F-15 era member identity drift: {edition}/{pe}")
    return True


def _point_measure(kind: str, measures: set[str]):
    if kind == "actuals":
        return "actuals", "Recorded actuals"
    if kind == "request":
        return "request", "Request"
    if any("request" in item for item in measures):
        return "enacted-request", "Current-year figures (includes requests with CR adjustments)"
    if "enacted-total" in measures or "total" in measures:
        return "enacted-total", "Enacted / current-year total"
    return "enacted", "Enacted"


def build_history(source_rows: list[dict], series: list[dict], *, retrieved_at: str, current_fact_ids: set[str] | None = None):
    """Pure builder returning payload, citations and additive breakdowns.

    source_rows must include workbook source identity; series is the canonical
    edition-relative mart. A count/value mismatch stops generation.
    """
    from govbudget.export_site import fact_id_workbook, fact_id_derived, _amount_type_meta, _decade_measure_token

    members = [row for row in source_rows if member_row(row)]
    by_grain = defaultdict(list)
    for row in members:
        by_grain[(row["pe_bli"], row["edition"], row["amount_type"])].append(row)
    annual = defaultdict(list)
    citations, workbook_rows = {}, {}
    seen_series = set()
    for point in series:
        key = (point["pe_bli"], point["edition"], point["amount_type"])
        rows = by_grain.get(key)
        if not rows:
            continue
        fy, kind, edition = point["fy"], point["kind"], point["edition"]
        if edition - fy != {"actuals": 2, "enacted": 1, "request": 0}[kind]:
            raise ValueError("F-15 scenario edition mismatch")
        series_key = (point["pe_bli"], edition, kind)
        if series_key in seen_series:
            raise ValueError(f"Duplicate F-15 scenario: {series_key}")
        seen_series.add(series_key)
        amount = sum((Decimal(str(row["amount_thousands"])) for row in rows), Decimal(0))
        if len(rows) != point["n_source_rows"] or amount != Decimal(str(point["amount"])):
            raise ValueError(f"F-15 lake/mart count or value mismatch: {key}")
        for row in rows:
            if not row.get("sha256") or not row.get("official_url") or not row.get("sheet") or not row.get("cells"):
                raise ValueError(f"F-15 workbook provenance missing: {key}")
            fid = fact_id_workbook(row["sha256"], row["exhibit"], edition, row["account"], row["organization"], row["budget_activity"], row["pe_bli"], row["amount_type"])
            if fid in workbook_rows:
                raise ValueError(f"Duplicate F-15 workbook input: {fid}")
            _, raw_measure = _amount_type_meta(row["amount_type"], edition)
            measure = _decade_measure_token(kind, raw_measure)
            component = {k: row[k] for k in ("pe_bli", "title", "exhibit", "account", "organization", "budget_activity", "amount_type", "amount_thousands", "official_url", "sheet", "cells")}
            component.update(fact_id=fid, program_slug=row["pe_bli"] if row["pe_bli"] in MODERN_MEMBERS else None, measure=measure, dataset="budget_lines" if fid in (current_fact_ids or set()) else "budget_lines_decade")
            annual[(fy, edition, kind)].append(component)
            workbook_rows[fid] = row
            citations[fid] = dict(kind="workbook", units="USD thousands", amount_thousands=row["amount_thousands"], sha256=row["sha256"], sheet=row["sheet"], cells=row["cells"], official_url=row["official_url"], retrieved_at=row.get("retrieved_at"), pe_bli=component["program_slug"], amount_type=row["amount_type"])
    if not annual:
        return None, {}, {}, {}
    points, breakdowns = [], {}
    for (fy, edition, kind), components in sorted(annual.items()):
        components.sort(key=lambda row: (row["exhibit"], row["pe_bli"], row["budget_activity"] or "", row["fact_id"]))
        ids = [row["fact_id"] for row in components]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate F-15 annual input")
        amount = sum((Decimal(str(row["amount_thousands"])) for row in components), Decimal(0))
        fid = fact_id_derived("family_history", f"f-15|{edition}|{fy}", kind)
        formula = f"sum(budget_lines.amount_thousands) for reviewed F-15 members, PB{edition}, FY{fy} {kind}; one selected scenario column per workbook line"
        citations[fid] = dict(kind="derived", units="USD thousands", recorded_value=f"{amount:.3f}", formula=formula, inputs=json.dumps(ids), retrieved_at=retrieved_at)
        measure, label = _point_measure(kind, {r["measure"] for r in components})
        present = {r["pe_bli"] for r in components}
        expected = {"0207134F", "0207171F"}
        if edition >= 2021:
            expected.add("0207146F")
        if edition >= 2024:
            expected.update({"F01500", "F015EX", "F15EWS"})
        missing = sorted(expected - present)
        point = dict(id=f"fy{fy}{ {'actuals':'a','enacted':'e','request':'r'}[kind] }", fy=fy, edition=edition, kind=kind, measure=measure, measure_label=label, amount_thousands=float(amount), fact_id=fid, coverage="partial" if missing else "covered-records", missing_programs=missing, components=components)
        points.append(point)
        breakdowns[fid] = dict(fact_id=fid, op="sum", units="USD thousands", formula=formula, recorded_value=f"{amount:.3f}", rows=[dict(label=f"{r['title']} · {r['pe_bli']} · BA {r['budget_activity']}", pe_bli=r["program_slug"], v=r["amount_thousands"], fid=r["fact_id"]) for r in components])
    actuals = [p for p in points if p["kind"] == "actuals"]
    years = sorted({p["fy"] for p in actuals})
    if years != list(range(min(years), max(years) + 1)):
        raise ValueError("F-15 cumulative actuals cannot silently cross a missing year")
    total = sum((Decimal(str(p["amount_thousands"])) for p in actuals), Decimal(0))
    total_fid = fact_id_derived("family_history", f"f-15|{min(years)}|{max(years)}", "cumulative-actuals")
    total_formula = f"sum(budget_lines.amount_thousands) via annual reviewed F-15 actuals totals, FY{min(years)}–FY{max(years)}; each fiscal year once, nominal USD thousands; excludes enacted/current-year figures and requests"
    citations[total_fid] = dict(kind="derived", units="USD thousands", recorded_value=f"{total:.3f}", formula=total_formula, inputs=json.dumps([p["fact_id"] for p in actuals]), retrieved_at=retrieved_at)
    breakdowns[total_fid] = dict(fact_id=total_fid, op="sum", units="USD thousands", formula=total_formula, recorded_value=f"{total:.3f}", rows=[dict(label=f"FY{p['fy']} actuals · PB{p['edition']}", pe_bli=None, v=p["amount_thousands"], fid=p["fact_id"]) for p in actuals])
    defaults = {}
    for p in sorted(points, key=lambda p: {"request": 0, "enacted": 1, "actuals": 2}[p["kind"]]):
        defaults[p["fy"]] = p["id"]
    payload = dict(schema_version=1, family_id="f-15", units="USD thousands", basis="toa", start_fy=min(defaults), end_fy=max(defaults), scope_note=SCOPE_NOTE, coverage_notes=COVERAGE_NOTES, default_point_ids=[defaults[fy] for fy in sorted(defaults)], points=points, cumulative=dict(start_fy=min(years), end_fy=max(years), kind="actuals", measure="actuals", amount_thousands=float(total), fact_id=total_fid, point_ids=[p["id"] for p in actuals], scope_note="Sum of covered annual recorded actuals only, in nominal dollars. This is not a lifetime cost; missing or unallocated funding is excluded."))
    return payload, citations, workbook_rows, breakdowns


def build_program_matrix(payload, previews, *, existing_citations, retrieved_at):
    """Group exact workbook inputs by verified code, without changing totals.

    Existing line numbers and source identities stay on the components. Every
    populated cell has an exact receipt; absent program/year combinations are
    omitted, never supplied with a manufactured zero. A reusable receipt must
    sum precisely the same distinct workbook facts under the same scenario.
    """
    from govbudget.export_site import fact_id_derived

    payload = deepcopy(payload)
    payload["programs"] = deepcopy(PROGRAMS)
    programs = {p["code"]: p for p in PROGRAMS}
    by_inputs = defaultdict(list)
    for fid, citation in existing_citations.items():
        if citation.get("kind") != "derived" or citation.get("units") != "USD thousands":
            continue
        try:
            ids = json.loads(citation["inputs"])
        except (KeyError, TypeError, ValueError):
            continue
        if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
            continue
        if len(ids) > 1 and len(ids) == len(set(ids)):
            by_inputs[tuple(sorted(ids))].append((fid, citation))
    additions, breakdowns = {}, {}
    for point in payload["points"]:
        groups = defaultdict(list)
        seen = set()
        for row in point["components"]:
            fid = row["fact_id"]
            if fid in seen:
                raise ValueError(f"Duplicate F-15 matrix input: {fid}")
            seen.add(fid)
            if not member_row({**row, "edition": point["edition"]}):
                raise ValueError(f"Unreviewed F-15 matrix input: {fid}")
            expected = row["pe_bli"] if row["pe_bli"] in MODERN_MEMBERS else ERA_PROGRAM_CODES[point["edition"]].get(int(row["pe_bli"].rsplit("L", 1)[1]))
            preview = previews.get(fid, {})
            cited = [r for r in preview.get("rows", []) if r.get("cited")]
            codes = {r.get("code") for r in cited}
            cells = {f"{preview.get('col')}{r.get('r')}" for r in cited}
            if codes != {expected} or expected not in programs:
                raise ValueError(f"F-15 workbook program code mismatch: {fid}: {codes} != {expected}")
            if (preview.get("sheet") != row["sheet"] or preview.get("units") != "USD thousands"
                    or cells != {cell.strip() for cell in row["cells"].split(",")}
                    or preview.get("total") is None
                    or Decimal(str(preview["total"])) != Decimal(str(row["amount_thousands"]))):
                raise ValueError(f"F-15 matrix workbook preview mismatch: {fid}")
            program = programs[expected]
            if (row["exhibit"], row["account"], row["organization"] in {"F", "AF"}) != (program["exhibit"], program["account"], True):
                raise ValueError(f"F-15 matrix program account mismatch: {fid}")
            row["program_id"] = program["id"]
            groups[program["id"]].append(row)
        cells = []
        for program in PROGRAMS:
            rows = groups.get(program["id"])
            if not rows:
                continue
            ids = sorted(row["fact_id"] for row in rows)
            amount = sum((Decimal(str(row["amount_thousands"])) for row in rows), Decimal(0))
            measures = {row["measure"] for row in rows}
            measure = next(iter(measures)) if len(measures) == 1 else _point_measure(point["kind"], measures)[0]
            if len(rows) == 1:
                fid, dataset = rows[0]["fact_id"], rows[0]["dataset"]
            else:
                dataset = "f15_funding_history"
                edition, fy, kind = point["edition"], point["fy"], point["kind"]
                fid = fact_id_derived("family_program_history", f"{program['id']}|{edition}|{fy}", kind)
                formula = f"sum(budget_lines.amount_thousands) for workbook program {program['id']}, PB{edition}, FY{fy} {kind}; each selected workbook input once"
                allowed = [formula]
                amount_types = {row["amount_type"] for row in rows}
                if len(amount_types) == 1:
                    amount_type = next(iter(amount_types))
                    allowed.extend([
                        f"sum(budget_lines.amount_thousands where amount_type={amount_type} and edition={edition})",
                        f"sum(budget_lines.amount_thousands where amount_type={amount_type})",
                    ])
                candidates = []
                for existing_fid, citation in by_inputs.get(tuple(ids), []):
                    if citation.get("formula") not in allowed:
                        continue
                    try:
                        matches = Decimal(str(citation.get("recorded_value"))) == amount
                    except (InvalidOperation, ValueError):
                        matches = False
                    if matches:
                        # Prefer the canonical edition-qualified receipt over a
                        # current-page duplicate; retain our own ID on reruns.
                        candidates.append((allowed.index(citation["formula"]), existing_fid, citation))
                if candidates:
                    _, fid, citation = min(candidates)
                    additions[fid] = deepcopy(citation)
                    formula = citation["formula"]
                else:
                    additions[fid] = dict(kind="derived", units="USD thousands", recorded_value=f"{amount:.3f}", formula=formula, inputs=json.dumps(ids), retrieved_at=retrieved_at)
                breakdowns[fid] = dict(fact_id=fid, op="sum", units="USD thousands", formula=formula, recorded_value=f"{amount:.3f}", rows=[dict(label=f"{r['title']} · {r['pe_bli']} · BA {r['budget_activity']}", pe_bli=program["program_slug"], v=r["amount_thousands"], fid=r["fact_id"]) for r in rows])
            cells.append(dict(program_id=program["id"], amount_thousands=float(amount), fact_id=fid, measure=measure, input_fact_ids=ids, dataset=dataset))
        if sum((Decimal(str(cell["amount_thousands"])) for cell in cells), Decimal(0)) != Decimal(str(point["amount_thousands"])):
            raise ValueError(f"F-15 matrix/annual total mismatch: {point['id']}")
        point["program_cells"] = cells
    return payload, additions, breakdowns


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
