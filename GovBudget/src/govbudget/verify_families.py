"""Families piece 2 release gate: verify-families (spec 2026-10-20 §13; D9, R16).

CLI: `govbudget verify-families [--legs abc] [--site-dir DIR] [--duckdb PATH]`.
With no arguments it checks every leg against the committed registry
(data-seeds/platform_families.json and its two CSVs), config.DUCKDB_PATH and
config.SITE_DIR, prints one line per leg and then exactly one final line,
`verify-families: PASS` or `verify-families: FAIL`, and exits 1 on FAIL. A
missing artifact is a FAIL, never a skip. A tool error (an unknown --legs
letter, a DuckDB lock held by another writer, the SAM refusal below) prints
`verify-families: ERROR — <message>` instead and exits 2; it never becomes a
leg failure.

  Leg (a) — registry. The three registry files load (stage 1, §9.1). A
    RegistryError fails the leg with its 'platform-families: <file>[:<row>]'
    lines, and legs b and c then report "registry unreadable".

  Leg (b) — lake. Stage 2 (§9.2) for every family, draft included, against
    the warehouse opened read-only. Failures and stale rows (a moved
    drift_sha256) fail the leg (R4); a draft family's guard matches and the
    recorded deferrals are reported as undecided, never failed.

  Leg (c) — export. Against the site directory: json/families/index.json
    equals index_projection(registry) byte for byte (§12); each published
    family's history artifact exists, names its platform_family as family_id
    and lists the counted members in member_order as programs[].id; every
    fact ID it names is in json/citations.json and passes stage 3 (§9.3,
    check_citations, one `claimed` map across the families, R10); and the
    leak scan (D9) finds no unpublished family's history_dataset,
    '<platform_family>|' key or 'reviewed <short_name> members' formula in any
    *.json file or in any VARCHAR column of citations/citations.parquet, and
    no json/<history_dataset>.json for it. A control requires each published
    family's formula needle to match at least one citations formula, so a
    blind scan fails.

The SAM guard: legs b and c read the warehouse, so when the DuckDB path is
config.DUCKDB_PATH (and not inside a proof snapshot tree, whose grandparent
holds snapshot.json, R16) a run that starts in, or spans, minutes :15–:20 is
refused (the hourly SAM job writes data/parquet/sam at :17).
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

from govbudget import config, proof
from govbudget import platform_families as reg
from govbudget.platform_family_history import INDEX_PATH, _json_bytes

LEGS = ("a", "b", "c")
LEG_NAMES = {"a": "registry", "b": "lake", "c": "export"}

_MAX_LISTED = 25
_CITATIONS_JSON = "json/citations.json"
_CITATIONS_PARQUET = "citations/citations.parquet"


def _now() -> datetime.datetime:
    return datetime.datetime.now()


def sam_guard(duckdb_path: Path, *, start: datetime.datetime, end: datetime.datetime | None = None) -> None:
    """Refuse a read of the live lake that starts in, or spans, the SAM window.

    A no-op unless duckdb_path is config.DUCKDB_PATH; a proof snapshot or its
    clone (its grandparent holds snapshot.json) is never guarded, even when its
    env.sh makes it config.DUCKDB_PATH (R16)."""
    path = Path(duckdb_path).resolve()
    if path != Path(config.DUCKDB_PATH).resolve():
        return
    if len(path.parents) > 1 and (path.parents[1] / "snapshot.json").exists():
        return
    touched = start.minute in proof.SAM_WINDOW_MINUTES if end is None else proof._sam_window_touched(start, end)
    if touched:
        now = end or start
        raise RuntimeError(f"refusing at {now:%H:%M} — the live lake was read across the SAM window (the hourly "
                           "SAM job writes data/parquet/sam at :17); run outside :15-:20")


def _program_identity(duckdb_path: Path):
    """export_site's program identity, from the warehouse opened read-only."""
    import duckdb

    from govbudget.export_site import _fetch_program_identity

    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        return _fetch_program_identity(con)
    finally:
        con.close()


def _read_json(path: Path, failures: list[str], label: str) -> dict | None:
    """The file's JSON object, or None after recording why it cannot be read."""
    if not path.is_file():
        failures.append(f"{label} is missing")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        failures.append(f"{label} is not valid JSON: {e}")
        return None
    if not isinstance(value, dict):
        failures.append(f"{label} is not a JSON object")
        return None
    return value


def _leg(ok: bool, summary: str, failures: list[str]) -> dict:
    return {"ok": ok, "summary": summary, "failures": failures}


def leg_a_registry(registry: reg.Registry) -> dict:
    summary = (f"families={len(registry.families)} published={len(registry.published())} "
               f"member_rows={sum(len(f.members) for f in registry.families)} "
               f"era_lines={sum(len(f.era_lines) for f in registry.families)} rulings={len(registry.rulings)}")
    return _leg(True, summary, [])


def leg_b_lake(registry: reg.Registry, *, site_dir: Path, duckdb_path: Path) -> dict:
    lake = reg.open_lake(duckdb_path)
    try:
        report = reg.check_lake(registry, lake=lake, site_dir=site_dir)   # every family, draft included
    finally:
        lake.close()
    failures = list(report.failures) + [f"stale {line}" for line in report.stale]
    summary = (f"families={len(registry.families)} failures={len(report.failures)} "
               f"undecided={len(report.undecided)} stale={len(report.stale)}")
    return _leg(not report.failures and not report.stale, summary, failures)


def _named_fact_ids(payload: dict) -> list[str]:
    """Every fact ID a history artifact names: the cumulative, each point,
    its program cells and its workbook components (R10, R-PF-5)."""
    ids = [(payload.get("cumulative") or {}).get("fact_id")]
    for point in payload.get("points") or ():
        ids.append(point.get("fact_id"))
        ids.extend(cell.get("fact_id") for cell in point.get("program_cells") or ())
        ids.extend(component.get("fact_id") for component in point.get("components") or ())
    return list(dict.fromkeys(fid for fid in ids if fid))


def leg_c_export(registry: reg.Registry, *, site_dir: Path, duckdb_path: Path) -> dict:
    site_dir = Path(site_dir)
    failures: list[str] = []
    index = site_dir / INDEX_PATH
    if not index.is_file():
        failures.append(f"{INDEX_PATH} is missing")
    elif index.read_bytes() != _json_bytes(reg.index_projection(registry)):
        failures.append(f"{INDEX_PATH} differs from index_projection(registry)")
    citations = _read_json(site_dir / _CITATIONS_JSON, failures, _CITATIONS_JSON)
    have_citations = citations is not None
    citations = citations or {}
    published = registry.published()
    identity = _program_identity(duckdb_path) if published else None
    claimed: dict[tuple[str, str, str], str] = {}    # stage-3 item 7 across the families of the leg (R10)
    histories = stage3 = 0
    for family in published:
        pf, history_path = family.platform_family, family.history_path
        minted: dict = {}
        payload = _read_json(site_dir / history_path, failures, f"{pf}: {history_path}")
        if payload is not None:
            histories += 1
            if payload.get("family_id") != pf:
                failures.append(f"{pf}: {history_path} family_id is {payload.get('family_id')!r}, not {pf!r}")
            if [p.get("id") for p in payload.get("programs") or ()] != [m.member_id for m in family.counted]:
                failures.append(f"{pf}: {history_path} programs[].id differ from the counted members in member_order")
            for fid in _named_fact_ids(payload):
                if fid in citations:
                    minted[fid] = citations[fid]
                elif have_citations:     # else the missing file is the one failure
                    failures.append(f"{pf}: fact {fid} named by {history_path} is not in {_CITATIONS_JSON}")
        lines = reg.check_citations(family, registry=registry, citations=citations, minted=minted,
                                    identity=identity, site_dir=site_dir, claimed=claimed)
        stage3 += len(lines)
        failures.extend(f"{pf}: {line}" for line in lines)
    leaks, scanned = scan_leaks(site_dir, registry)
    failures.extend(leaks)
    summary = (f"published={len(published)} histories={histories} stage3={stage3} leaks={len(leaks)} "
               f"files_scanned={scanned}")
    return _leg(not failures, summary, failures)


def _needles(family: reg.Family) -> tuple[str, ...]:
    return (family.history_dataset, f"{family.platform_family}|", f"reviewed {family.short_name} members")


def scan_leaks(site_dir: Path, registry: reg.Registry) -> tuple[list[str], int]:
    """D9: no non-published family's needles anywhere in the export.

    The needles are its history_dataset, '<platform_family>|' and
    'reviewed <short_name> members', searched in every *.json file under
    site_dir (as bytes) and in every VARCHAR column of
    citations/citations.parquet; json/<history_dataset>.json must not exist.
    The control: each published family's 'reviewed <short_name> members'
    matches at least one citations formula, else the scan reports itself
    blind. Returns (failures, number of *.json files scanned)."""
    import duckdb

    site_dir = Path(site_dir)
    hidden = [f for f in registry.families if f.status != "published"]
    failures: list[str] = []
    files = sorted(site_dir.rglob("*.json"))
    if hidden:
        for path in files:
            data = path.read_bytes()
            relative = path.relative_to(site_dir).as_posix()
            for family in hidden:
                for needle in _needles(family):
                    if needle.encode() in data:
                        failures.append(f"leak: {needle!r} of unpublished {family.platform_family} in {relative}")
    for family in hidden:
        if (site_dir / family.history_path).exists():
            failures.append(f"leak: {family.history_path} of unpublished {family.platform_family} exists")
    parquet = site_dir / _CITATIONS_PARQUET
    if not parquet.is_file():
        failures.append(f"leak scan: {_CITATIONS_PARQUET} is missing")
        return failures, len(files)
    con = duckdb.connect()
    try:
        columns = [name for name, kind, *_ in
                   con.execute("describe select * from read_parquet(?)", [str(parquet)]).fetchall()
                   if kind == "VARCHAR"]

        def rows_containing(needle: str, cols: list[str]) -> int:
            if not cols:
                return 0
            where = " or ".join(f'contains(coalesce("{c}", \'\'), ?)' for c in cols)
            return con.execute(f"select count(*) from read_parquet(?) where {where}",
                               [str(parquet), *([needle] * len(cols))]).fetchone()[0]

        for family in hidden:
            for needle in _needles(family):
                n = rows_containing(needle, columns)
                if n:
                    failures.append(f"leak: {needle!r} of unpublished {family.platform_family} in "
                                    f"{_CITATIONS_PARQUET} ({n} row(s))")
        formula = [c for c in columns if c == "formula"]
        for family in registry.published():
            needle = f"reviewed {family.short_name} members"
            if not rows_containing(needle, formula):
                failures.append(f"leak scan control: no {_CITATIONS_PARQUET} formula contains {needle!r}")
    finally:
        con.close()
    return failures, len(files)


def run_verify_families(*, site_dir: Path, duckdb_path: Path, legs: str = "abc",
                        registry: reg.Registry | None = None) -> dict:
    """Run the selected legs, always in a, b, c order. Returns
    {"legs": {leg: {"ok", "summary", "failures"}}, "verdict": "PASS" | "FAIL"}.
    Exceptions from the lake (a DuckDB lock) and the SAM refusal propagate."""
    unknown = sorted(set(legs) - set(LEGS))
    if unknown or not legs:
        raise ValueError(f"legs must be letters from {''.join(LEGS)}; got {legs!r}")
    errors: list[str] = []
    if registry is None:
        try:
            registry = reg.load_registry(reg.DEFAULT_PATHS)
        except reg.RegistryError as e:
            errors = e.errors
    chosen = [leg for leg in LEGS if leg in legs]
    results: dict[str, dict] = {}
    if "a" in chosen:
        results["a"] = (_leg(False, f"stage 1 failed: {len(errors)} error(s)", errors) if errors
                        else leg_a_registry(registry))
    lake_legs = [leg for leg in chosen if leg in "bc"]
    if lake_legs and errors:
        for leg in lake_legs:
            results[leg] = _leg(False, "registry unreadable", [f"stage 1 failed (leg a): {len(errors)} error(s)"])
    elif lake_legs:
        start = _now()
        sam_guard(duckdb_path, start=start)
        for leg in lake_legs:
            run = leg_b_lake if leg == "b" else leg_c_export
            results[leg] = run(registry, site_dir=Path(site_dir), duckdb_path=Path(duckdb_path))
        sam_guard(duckdb_path, start=start, end=_now())
    verdict = "PASS" if all(r["ok"] for r in results.values()) else "FAIL"
    return {"legs": results, "verdict": verdict}


def format_report(out: dict) -> list[str]:
    """One line per leg plus its first failures; the CLI prints the verdict after."""
    lines = []
    for leg, r in out["legs"].items():
        lines.append(f"leg {leg} {LEG_NAMES[leg]}: {r['summary']} → {'PASS' if r['ok'] else 'FAIL'}")
        for failure in r["failures"][:_MAX_LISTED]:
            lines.append(f"  FAIL {failure}")
        extra = len(r["failures"]) - _MAX_LISTED
        if extra > 0:
            lines.append(f"  … and {extra} more")
    return lines
