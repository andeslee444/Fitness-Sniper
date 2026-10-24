"""The platform-family review tools: propose, preview, render, answer, ratify
(families piece 2; spec 2026-10-20 §8.2, §8.3; D3).

Task 7b: `propose` writes a family under review as a `draft` family object in
data-seeds/platform_families.json (its sources merged into the top-level
sources[]) and its proposed rows into
data/research/platform_families/<pf>/review.csv and review_era_lines.csv, the
lake columns measured read-only. Nothing reaches the members or era-lines CSVs
before `ratify`. It refuses a ratified or published family, never re-proposes
a reviewed rejected or excluded row, and holds a lake result that differs from
an approved row for review rather than overturning it (era_map's
_hold_for_review pattern). Every check runs before the first write; the errors
are raised together as one RegistryError ('platform-families: <file>[:<row
id>]: <reason>', R5) and nothing is written. The writes are one atomic call.

Task 7c: `preview` builds a non-published family's history into a scratch
clone of a snapshot site (a draft only with `draft`, from its review files,
never silently), `compare_reference` sets the preview beside a batch's
reference figures at $0.1M and names each difference's cause, and `render`
writes the batch page and its manifest under tmp/platform-families/<pf>/
(D10). A preview error, or a difference whose cause is a row of the proposal,
writes no page (§8.2, Review Focus 3).

Every registry (I-REG) and history (I-HIST) function is called through the
module attribute (`reg.open_lake`, `reg.measure_member`,
`hist.export_family_histories`, …), so a test patches it there (R15).
"""
from __future__ import annotations

import codecs
import copy
import dataclasses
import hashlib
import html
import json
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from govbudget import config
from govbudget import platform_families as reg
from govbudget import platform_family_history as hist
from govbudget import verify_families as vf
from govbudget.jbooks import era_map

OUT_ROOT = config.ROOT / "tmp" / "platform-families"   # batch pages and manifests (D10), git-ignored

_LAKE_COLUMNS = ("titles_seen", "budget_activities", "drift_sha256")
_REVIEW_ONLY_COLUMNS = ("reason", "headline_actuals_k")
_FAMILY_JSON_KEYS = frozenset({"family", "sources"})
_NOT_IN_FAMILY_JSON = ("status", "published_ruling_id")


def review_files(review_root: Path, platform_family: str) -> tuple[Path, Path]:
    """(<root>/<pf>/review.csv, <root>/<pf>/review_era_lines.csv)."""
    root = Path(review_root) / platform_family
    return root / "review.csv", root / "review_era_lines.csv"


def _era_row(line: reg.EraLine) -> dict[str, str]:
    """An era line as a row over ERA_LINE_COLUMNS."""
    return line.as_row()


def _era_decisions() -> dict[str, dict[str, str]]:
    """The era seed (p1_era_code_decisions) keyed by decision_id."""
    return {row["decision_id"]: row for row in era_map.read_seed(era_map.default_seed_path())}


def _era_sort_key(row: Mapping[str, str]) -> tuple[str, str, str]:
    return (row.get("platform_family", ""), row.get("edition", ""), row.get("era_key", ""))


def _trial_registry(registry: reg.Registry, *, platform_family: str, rows: Sequence[Mapping[str, str]],
                    era_lines: Sequence[Mapping[str, str]], ruling: Mapping[str, object],
                    paths: reg.RegistryPaths) -> tuple[dict, list[dict], list[dict], reg.Registry]:
    """The one place a family under review is made buildable and checkable:
    the family as `ratified` under `ruling`, `rows` (review rows, `reason` and
    `headline_actuals_k` dropped) replacing the family's rows of the same
    member_row_id as decided by the owner under that ruling, and the era lines
    of the approved counted rows among them. Returns (doc, member rows, era
    rows, registry); stage 1 raises RegistryError with every error, naming
    `paths`' files."""
    doc = copy.deepcopy(registry.doc)
    for fam in doc["families"]:
        if fam.get("platform_family") == platform_family:
            fam["status"] = "ratified"
    doc["rulings"] = sorted([*doc["rulings"], dict(ruling)], key=lambda r: r["ruling_id"])

    replaced = {row.get("member_row_id") for row in rows}
    members = [m.as_row() for fam in registry.families for m in fam.members
               if not (fam.platform_family == platform_family and m.member_row_id in replaced)]
    for row in rows:
        trial = {key: value for key, value in row.items() if key not in _REVIEW_ONLY_COLUMNS}
        trial.update(decided_by="owner", ruling_id=ruling["ruling_id"], decided_on=ruling["decided_on"])
        members.append(trial)
    members.sort(key=lambda r: r.get("member_row_id", ""))

    counted = {row.get("member_id") for row in rows
               if row.get("verdict") == "approved" and row.get("role") == "counted"}
    era_rows = [line.as_row() for fam in registry.families for line in fam.era_lines]
    era_rows += [dict(line) for line in era_lines if line.get("member_id") in counted]
    era_rows.sort(key=_era_sort_key)
    trial_registry = reg.parse_registry(doc, members, era_rows, era_decisions=_era_decisions(), paths=paths)
    return doc, members, era_rows, trial_registry


# ---------------------------------------------------------------------------
# propose (spec §8.3)
# ---------------------------------------------------------------------------


def _read_family_json(path: Path, platform_family: str,
                      errors: list[str]) -> tuple[dict | None, list[dict] | None]:
    """Step 1: {"family": <family object without status and published_ruling_id>,
    "sources": [...]}, UTF-8 without a BOM, duplicate keys refused."""
    def add(reason: str) -> None:
        errors.append(reg._line(path.name, None, reason))

    if not path.is_file():
        add(f"missing (no file at {path})")
        return None, None
    data = path.read_bytes()
    if data.startswith(codecs.BOM_UTF8):
        add("starts with a UTF-8 BOM")
        return None, None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        add(f"is not UTF-8 ({exc.reason} at byte {exc.start})")
        return None, None
    doc, faults = reg._parse_json(text)
    for fault in faults:
        add(fault)
    if faults:
        return None, None
    if not isinstance(doc, dict) or set(doc) != _FAMILY_JSON_KEYS:
        keys = sorted(doc) if isinstance(doc, dict) else type(doc).__name__
        add(f"has keys {keys}; a family JSON is an object with exactly 'family' and 'sources'")
        return None, None

    family, sources = doc["family"], doc["sources"]
    ok = True
    if not isinstance(family, dict):
        add(f"family must be an object, got {family!r}")
        ok = False
    else:
        if family.get("platform_family") != platform_family:
            add(f"family platform_family {family.get('platform_family')!r} is not --family {platform_family!r}")
            ok = False
        for key in _NOT_IN_FAMILY_JSON:
            if key in family:
                add(f"family carries {key!r}; propose writes the family with status 'draft' and no "
                    "published_ruling_id")
                ok = False
    if not isinstance(sources, list) or not all(
            isinstance(s, dict) and isinstance(s.get("source_id"), str) for s in sources):
        add("sources must be a list of source objects, each with a string source_id")
        ok = False
    return (family, sources) if ok else (None, None)


def _read_prefill(path: Path, errors: list[str]) -> list[dict[str, str]] | None:
    """Step 2: the prefill rows over PREFILL_COLUMNS, read as the registry CSVs
    are (a BOM, a carriage return or a trailing blank line refused; fields kept
    exactly as written)."""
    text, faults = reg._read_text(path)
    errors.extend(reg._line(path.name, None, fault) for fault in faults)
    if text is None:
        return None
    rows, faults = reg._parse_csv(text, reg.PREFILL_COLUMNS, path.name, lambda fields: None)
    errors.extend(faults)
    return rows


def _draft_doc(registry: reg.Registry, platform_family: str, family: dict, sources: Sequence[dict],
               family_json_name: str, paths: reg.RegistryPaths, errors: list[str]) -> dict | None:
    """Steps 3 and 4: the registry doc with the family as a draft (an earlier
    draft replaced in place, a new family appended) and its sources merged by
    source_id; None when the family is ratified or published."""
    pf = platform_family
    status = next((f.status for f in registry.families if f.platform_family == pf), None)
    if status in ("ratified", "published"):
        errors.append(reg._line(paths.json.name, pf, f"{pf} is {status}; propose writes draft families only"))
        return None

    merged = {s["source_id"]: s for s in registry.doc["sources"]}
    for source in sources:
        sid = source["source_id"]
        if sid not in merged:
            merged[sid] = copy.deepcopy(source)
        elif merged[sid] != source:
            errors.append(reg._line(paths.json.name, sid,
                                    f"source {sid!r} in {family_json_name} differs from the sources[] entry "
                                    f"of that id; one source_id names one source (change the id or the entry)"))

    doc = copy.deepcopy(registry.doc)
    doc["sources"] = [merged[sid] for sid in sorted(merged)]
    draft = {**copy.deepcopy(family), "status": "draft"}
    at = next((i for i, f in enumerate(doc["families"]) if f.get("platform_family") == pf), None)
    if at is None:
        doc["families"].append(draft)
    else:
        doc["families"][at] = draft
    return doc


def propose(*, platform_family: str, family_json: Path, rows_csv: Path, duckdb_path: Path,
            paths: reg.RegistryPaths = reg.DEFAULT_PATHS, review_root: Path = reg.REVIEW_ROOT) -> dict:
    """`platform-families propose` (§8.3, R12). Steps 1–5 (the two inputs, the
    registry, the sources and the family object as a zero-row draft) raise
    before the lake opens; steps 6–8 (the rows, their lake measures and stage
    1 on the measured rows, naming the review files) raise together after it
    closes. Then the draft family, review.csv and review_era_lines.csv are
    written in one atomic call; the members and era-lines CSVs are rewritten
    byte-identical. Returns {"rows", "era_lines", "held_for_review"}."""
    pf = platform_family
    family_json, rows_csv = Path(family_json), Path(rows_csv)
    review_csv, review_era_csv = review_files(review_root, pf)

    # Steps 1-5: before the lake opens.
    errors: list[str] = []
    family_obj, sources = _read_family_json(family_json, pf, errors)
    prefill = _read_prefill(rows_csv, errors)
    try:
        registry = reg.load_registry(paths)
    except reg.RegistryError as e:
        errors.extend(e.errors)
        registry = None
    existing_members = existing_era = None
    draft = None
    if family_obj is not None and registry is not None:
        doc = _draft_doc(registry, pf, family_obj, sources, family_json.name, paths, errors)
        existing_members = [m.as_row() for fam in registry.families for m in fam.members]
        existing_era = [line.as_row() for fam in registry.families for line in fam.era_lines]
        if doc is not None:
            try:   # a draft with zero rows is valid (rule 23)
                draft = reg.parse_registry(doc, existing_members, existing_era, era_decisions=_era_decisions(),
                                           paths=paths)
            except reg.RegistryError as e:
                errors.extend(e.errors)
    if errors:
        raise reg.RegistryError(errors)
    family = draft[pf]

    # Step 6: rows and ids.
    existing = {m.member_row_id: m for m in family.members}
    pending: list[tuple[reg.Member, str, reg.Member | None]] = []
    for row in prefill:
        member_row_id = f"{pf}|{row['member_id']}|{row['valid_from_edition']}-{row['valid_to_edition']}"
        old = existing.get(member_row_id)
        if old is not None and (old.verdict == "rejected" or old.role == "excluded"):
            continue                               # reviewed: never re-proposed
        full = dict.fromkeys(reg.MEMBER_COLUMNS, "")
        full.update({key: value for key, value in row.items() if key != "reason"})
        full["member_row_id"] = member_row_id
        try:
            member = reg.Member.from_row(full)
        except ValueError as e:
            errors.append(reg._line(review_csv.name, member_row_id, str(e)))
            continue
        pending.append((member, row["reason"], old if old is not None and old.verdict == "approved" else None))

    # Step 7: measure, read-only; a lock propagates with nothing written.
    start = vf._now()
    vf.sam_guard(duckdb_path, start=start)
    lake = reg.open_lake(duckdb_path)
    review_rows: list[dict[str, str]] = []
    review_era: list[dict[str, str]] = []
    held = 0
    try:
        for member, reason, approved in pending:
            measure = reg.measure_member(lake, member, headline=family.headline)
            row = dataclasses.replace(member, titles_seen=measure.titles_seen,
                                      budget_activities=measure.budget_activities,
                                      drift_sha256=measure.drift_sha256).as_row()
            if approved is not None:
                ratified = approved.as_row()
                changed = [col for col in _LAKE_COLUMNS if row[col] != ratified[col]]
                if not changed:
                    continue                       # the same lake result: not re-proposed
                reason = (f"lake result differs from ratified row {member.member_row_id} ({', '.join(changed)})"
                          " — confirm or keep the ratified row; no silent overturn")
                held += 1
            row["reason"] = reason
            row["headline_actuals_k"] = ("" if measure.headline_actuals_k is None
                                         else f"{measure.headline_actuals_k:.3f}")
            review_rows.append(row)
            review_era.extend(_era_row(line) for line in measure.era_lines)
    finally:
        lake.close()
    vf.sam_guard(duckdb_path, start=start, end=vf._now())

    # Step 8: stage 1 on the measured rows, once, naming the review files.
    ruling = {"ruling_id": f"R-DEC-FAM-{pf.replace('-', '').upper()}-PROPOSE", "kind": "batch",
              "platform_family": pf, "decided_by": "owner", "decided_on": "2026-01-01",
              "owner_reply": "propose trial (never written)", "spec": "", "text": "", "seed_basis": False}
    trial_paths = reg.RegistryPaths(json=paths.json, members=review_csv, era_lines=review_era_csv)
    try:
        _trial_registry(draft, platform_family=pf, rows=review_rows, era_lines=review_era, ruling=ruling,
                        paths=trial_paths)
    except reg.RegistryError as e:
        errors.extend(e.errors)
    if errors:
        raise reg.RegistryError(errors)

    # Step 9: one atomic write.
    review_rows.sort(key=lambda r: r["member_row_id"])
    review_era.sort(key=_era_sort_key)
    era_map._atomic_write_texts({
        review_csv: era_map._csv_text(reg.REVIEW_COLUMNS, review_rows),
        review_era_csv: era_map._csv_text(reg.ERA_LINE_COLUMNS, review_era),
        **reg.registry_texts(paths, doc=draft.doc, members=existing_members, era_lines=existing_era),
    })
    return {"rows": len(review_rows), "era_lines": len(review_era), "held_for_review": held}


# ---------------------------------------------------------------------------
# preview and compare_reference (spec §8.2, §8.3; Review Focus 3)
# ---------------------------------------------------------------------------

CAUSE_PROPOSAL = "proposal row"            # a row of the proposal: blocks the page
CAUSE_LAKE = "lake since 2026-10-19"       # lake drift; shown on the page (R14: the reference has no as_of)
PREVIEW_MARKER = ".platform-families-preview"
REFERENCE_KEYS = frozenset({"lines", "totals", "cumulative", "fy2025_enacted", "fy2026_request"})
_TENTH = Decimal("0.1")


@dataclasses.dataclass
class PreviewResult:
    """A preview's figures, read back from its history artifact. `years` holds
    one {"fy", "kind", "edition", "total_thousands"} per point, in file order;
    `member_years` holds every program cell by (member_id, fy, kind), and an
    absent cell stays absent; `members` maps each counted member's code to its
    member_id (R14)."""

    years: list[dict]
    cumulative_thousands: Decimal
    member_years: dict[tuple[str, int, str], Decimal]
    out_dir: Path
    members: dict[str, str] = dataclasses.field(default_factory=dict)


def _fam(platform_family: str) -> str:
    """<FAM> of a ruling id: the family id without hyphens, upper-case (§6)."""
    return platform_family.replace("-", "").upper()


def _read_review_files(review_root: Path, platform_family: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """review.csv (REVIEW_COLUMNS) and review_era_lines.csv (ERA_LINE_COLUMNS),
    read as the registry CSVs are; RegistryError with every fault of both."""
    errors: list[str] = []
    out: list[list[dict[str, str]] | None] = []
    for path, columns, row_ref in zip(review_files(review_root, platform_family),
                                      (reg.REVIEW_COLUMNS, reg.ERA_LINE_COLUMNS), (reg._member_ref, reg._era_ref)):
        text, faults = reg._read_text(path)
        errors.extend(reg._line(path.name, None, fault) for fault in faults)
        rows = None
        if text is not None:
            rows, faults = reg._parse_csv(text, columns, path.name, row_ref)
            errors.extend(faults)
        out.append(rows)
    if errors:
        raise reg.RegistryError(errors)
    return out[0], out[1]


def preview(*, platform_family: str, draft: bool, site_dir: Path, duckdb_path: Path, out: Path,
            paths: reg.RegistryPaths = reg.DEFAULT_PATHS, review_root: Path = reg.REVIEW_ROOT) -> PreviewResult:
    """`platform-families preview` (§8.3): build a non-published family's
    history into `out`, an APFS clone of the snapshot `site_dir`. With `draft`
    the family is a draft, read with its review files (review.csv and
    review_era_lines.csv) as a trial registry in which it is ratified; without
    it a draft is refused, never read silently. Every refusal (an `out` inside
    config.SITE_DIR or inside `site_dir`, a published family, a draft without
    `draft`, `draft` on another status, an existing `out` that is not a preview
    scratch, a stage-1 fault of the trial) is raised together before any write;
    an earlier preview scratch at `out` is then replaced whole."""
    pf = platform_family
    out, site_dir = Path(out), Path(site_dir)
    registry = reg.load_registry(paths)
    errors: list[str] = []
    live_site = Path(config.SITE_DIR).resolve()
    if out.resolve().is_relative_to(live_site):
        errors.append(f"platform-families: --out {out} is inside config.SITE_DIR ({live_site}); a preview writes "
                      "scratch only")
    if not site_dir.is_dir():
        errors.append(f"platform-families: --site-dir {site_dir} is not a directory")
    elif out.resolve().is_relative_to(site_dir.resolve()):
        errors.append(f"platform-families: --out {out} is inside --site-dir {site_dir}; the snapshot site is "
                      "read-only")
    family = next((f for f in registry.families if f.platform_family == pf), None)
    if family is None:
        errors.append(reg._line(paths.json.name, pf, f"{pf} is not in {paths.json.name}"))
    elif family.status == "published":
        errors.append(reg._line(paths.json.name, pf, f"{pf} is published; preview builds an unpublished family"))
    elif family.status == "draft" and not draft:
        errors.append(reg._line(paths.json.name, pf,
                                f"{pf} is a draft family; pass --draft to preview its proposed rows (review.csv)"))
    elif draft and family.status != "draft":
        errors.append(reg._line(paths.json.name, pf,
                                f"--draft reads a draft family's review files; {pf} is {family.status}"))
    if out.exists() and not (out / PREVIEW_MARKER).is_file():
        errors.append(f"platform-families: {out} exists and is not a preview scratch (no {PREVIEW_MARKER}); "
                      "choose another --out")
    build = registry
    if family is not None and draft and family.status == "draft":
        review_csv, review_era_csv = review_files(review_root, pf)
        ruling = {"ruling_id": f"R-DEC-FAM-{_fam(pf)}-PREVIEW", "kind": "batch", "platform_family": pf,
                  "decided_by": "owner", "decided_on": "2026-01-01", "owner_reply": "preview trial (never written)",
                  "spec": "", "text": "", "seed_basis": False}
        try:
            rows, era_rows = _read_review_files(review_root, pf)
            build = _trial_registry(registry, platform_family=pf, rows=rows, era_lines=era_rows, ruling=ruling,
                                    paths=reg.RegistryPaths(json=paths.json, members=review_csv,
                                                            era_lines=review_era_csv))[3]
        except reg.RegistryError as e:
            errors.extend(e.errors)
    if errors:
        raise reg.RegistryError(errors)

    start = vf._now()
    vf.sam_guard(duckdb_path, start=start)
    if out.exists():
        shutil.rmtree(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["cp", "-c", "-R", str(site_dir), str(out)], check=True)
    (out / PREVIEW_MARKER).write_text(f"platform-families preview scratch for {pf}: never data/site, never "
                                      "committed\n", encoding="utf-8")
    built = hist.export_family_histories(duckdb_path=duckdb_path, out_dir=out, registry=build, families=[pf],
                                         preview=True)
    vf.sam_guard(duckdb_path, start=start, end=vf._now())
    if built is None:
        raise reg.RegistryError([f"platform-families: preview built nothing for {pf}"])

    family = build[pf]
    payload = json.loads((out / family.history_path).read_text(encoding="utf-8"))
    points = payload["points"]
    return PreviewResult(
        years=[{"fy": point["fy"], "kind": point["kind"], "edition": point["edition"],
                "total_thousands": Decimal(str(point["amount_thousands"]))} for point in points],
        cumulative_thousands=Decimal(str(payload["cumulative"]["amount_thousands"])),
        member_years={(cell["program_id"], point["fy"], point["kind"]): Decimal(str(cell["amount_thousands"]))
                      for point in points for cell in point.get("program_cells", ())},
        out_dir=out,
        members={m.code: m.member_id for m in family.counted})


def _to_m(thousands: Decimal | None) -> Decimal | None:
    """Thousands -> $M, ROUND_HALF_UP to $0.1M (the reference's precision)."""
    return None if thousands is None else (Decimal(thousands) / 1000).quantize(_TENTH, ROUND_HALF_UP)


def _ref_m(value: object) -> Decimal | None:
    """A reference figure ($M, one decimal); None is absent, 0.0 a real zero."""
    return None if value is None else Decimal(str(value)).quantize(_TENTH)


def _agrees(preview_k: Decimal | None, reference_m: Decimal | None) -> bool:
    return (preview_k is None) == (reference_m is None) and (preview_k is None or _to_m(preview_k) == reference_m)


def _difference(fy: int | None, kind: str, member_id: str | None, preview_k: Decimal | None,
                reference_m: Decimal | None, cause: str) -> dict:
    return {"fy": fy, "kind": kind, "member_id": member_id, "preview_k": preview_k, "reference_m": reference_m,
            "cause": cause, "blocks": cause == CAUSE_PROPOSAL}


def _lake_caused(member_diffs: Sequence[dict]) -> bool:
    return bool(member_diffs) and all(d["cause"] == CAUSE_LAKE for d in member_diffs)


def compare_reference(result: PreviewResult, reference: dict, *, lake) -> list[dict]:
    """The preview beside a batch's reference figures ($M), at $0.1M (Review
    Focus 3). The reference's last FY is the request, the one before it the
    enacted, every other FY actuals. A member-year difference's cause is the
    lake drift CAUSE_LAKE when fct_program_decade_series (lake.program_series)
    agrees with the preview, else CAUSE_PROPOSAL (it blocks the page). A year
    total or the cumulative is CAUSE_LAKE only when every member difference
    under it is. Order: member level by (fy, member_id), then the year totals
    by fy, then the cumulative (fy None). ValueError when the reference's
    fy2025_enacted or fy2026_request differs from its own totals."""
    totals, lines = reference["totals"], reference["lines"]
    if not totals:
        raise ValueError("reference totals is empty; a reference names at least its request year")
    last = max(int(fy) for fy in totals)

    def kind(fy: int) -> str:
        return "request" if fy == last else "enacted" if fy == last - 1 else "actuals"

    for name, fy in (("fy2025_enacted", 2025), ("fy2026_request", 2026)):
        if str(fy) in totals and reference[name] != totals[str(fy)]:
            raise ValueError(f"reference {name} {reference[name]} differs from totals[{fy}] {totals[str(fy)]}")

    member_of = {member_id.rsplit(":", 1)[1]: member_id for member_id, _fy, _kind in result.member_years}
    member_of.update(result.members)
    pairs = {(code, int(fy)) for code, by_fy in lines.items() for fy in by_fy}
    pairs |= {(member_id.rsplit(":", 1)[1], fy) for member_id, fy, _kind in result.member_years}
    series: dict[str, dict[tuple[int, str], Decimal]] = {}
    keyed: list[tuple[tuple[int, str, str], dict]] = []
    for code, fy in pairs:
        member_id = member_of.get(code)
        p = result.member_years.get((member_id, fy, kind(fy))) if member_id is not None else None
        ref = _ref_m(lines.get(code, {}).get(str(fy)))
        if _agrees(p, ref):
            continue
        if code not in series:
            series[code] = lake.program_series(code)
        mart = series[code].get((fy, kind(fy)))
        lake_moved = (mart is None) == (p is None) and (p is None or _to_m(mart) == _to_m(p))
        keyed.append(((fy, member_id or "", code),
                      _difference(fy, kind(fy), member_id, p, ref, CAUSE_LAKE if lake_moved else CAUSE_PROPOSAL)))
    member_diffs = [d for _key, d in sorted(keyed, key=lambda item: item[0])]

    year_totals = {(y["fy"], y["kind"]): y["total_thousands"] for y in result.years}
    year_diffs: list[dict] = []
    for fy in sorted(int(f) for f in totals):
        p, ref = year_totals.get((fy, kind(fy))), _ref_m(totals[str(fy)])
        if not _agrees(p, ref):
            cause = CAUSE_LAKE if _lake_caused([d for d in member_diffs if d["fy"] == fy]) else CAUSE_PROPOSAL
            year_diffs.append(_difference(fy, kind(fy), None, p, ref, cause))
    p, ref = result.cumulative_thousands, _ref_m(reference["cumulative"])
    if not _agrees(p, ref):
        cause = CAUSE_LAKE if _lake_caused([d for d in member_diffs if d["kind"] == "actuals"]) else CAUSE_PROPOSAL
        year_diffs.append(_difference(None, "cumulative", None, p, ref, cause))
    return member_diffs + year_diffs


# ---------------------------------------------------------------------------
# render and the batch page (spec §8.2; D10)
# ---------------------------------------------------------------------------

PRIOR_APPROVALS = {"f-35": ("2026-10-19", "yes this is good, except we should break out the sub contractors "
                                          "because it doesn't end with lockheed and pratt & W")}
PIECE_COMMITMENTS = {"f-35": "Subcontractors are broken out as their own layer in piece 7, as you asked on "
                             "2026-10-19."}
_FAMILY_IDENTITY_KEYS = ("platform_family", "status", "published_ruling_id")
# The look of scripts/era/review_batch_page.py (PAGE_CSS, :58-93, copied: scripts/ is
# not importable from src/), plus the rules for this page's tables.
FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500"
         "&family=IBM+Plex+Sans:wght@400;500;600&display=swap")
PAGE_CSS = """
:root{--paper:#f4f6f9;--sheet:#ffffff;--ink:#16202c;--muted:#556173;--rule:#d3dae3;--accent:#21507f;--same:#1d6a45;--same-bg:#e1f0e7;--hist:#7a520c;--hist-bg:#f5ead3;--excl:#8e2b22;--excl-bg:#f6e0dc;--other:#3b4553;--other-bg:#e6e9ee}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){color-scheme:dark;--paper:#0e131a;--sheet:#151c25;--ink:#e2e7ee;--muted:#9ba7b7;--rule:#2a3441;--accent:#8fb6e4;--same:#8fd2ac;--same-bg:#16321f;--hist:#e5c27f;--hist-bg:#382b11;--excl:#f0a69d;--excl-bg:#3b1b18;--other:#c2cad5;--other-bg:#242c37}}
:root[data-theme="dark"]{color-scheme:dark;--paper:#0e131a;--sheet:#151c25;--ink:#e2e7ee;--muted:#9ba7b7;--rule:#2a3441;--accent:#8fb6e4;--same:#8fd2ac;--same-bg:#16321f;--hist:#e5c27f;--hist-bg:#382b11;--excl:#f0a69d;--excl-bg:#3b1b18;--other:#c2cad5;--other-bg:#242c37}
body{background:var(--paper);color:var(--ink);font:15px/1.55 "IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif}
.page{max-width:880px;margin:0 auto;padding-inline:16px;padding-block:28px 64px}
.eyebrow,.label{margin:0;font:500 12px/1.4 "IBM Plex Mono",ui-monospace,Menlo,monospace;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
h1{margin:6px 0 10px;font-size:26px;line-height:1.2;font-weight:600;text-wrap:balance}
.lede,.how{margin:0 0 10px;max-width:68ch}
.how{color:var(--muted)}.how b{color:var(--ink)}
.legend{display:grid;gap:6px;margin:14px 0 0;padding-block:12px;border-block:1px solid var(--rule)}
.legend div{display:grid;grid-template-columns:minmax(0,max-content) 1fr;gap:10px;align-items:baseline}
.legend dd{margin:0;color:var(--muted)}
.chains{list-style:none;margin:8px 0 0;padding:0}
.chain{padding-block:18px;border-bottom:1px solid var(--rule)}
.chain-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 12px}
.num{font:500 13px/1 "IBM Plex Mono",ui-monospace,Menlo,monospace;color:var(--muted);min-width:2ch}
.chain h2{margin:0;flex:1 1 auto;display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline;font-size:18px;line-height:1.3;font-weight:600}
code,.usd,.acct,.org,.cid{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace}
.acct,.org{font-size:14px;font-weight:400;color:var(--muted)}
.usd{font-size:16px;font-weight:500;font-variant-numeric:tabular-nums}
.span{margin:4px 0 10px;color:var(--muted);font-size:14px}
.cid{font-size:12px;overflow-wrap:anywhere}
dl{margin:0}.chain dl{display:grid;gap:8px}
.chain dl div{display:grid;grid-template-columns:150px minmax(0,1fr);gap:4px 14px}
dt{font-size:13px;color:var(--muted)}
dd{margin:0;min-width:0;overflow-wrap:anywhere}
.pre{display:block;white-space:pre-wrap}
.proposal{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 10px;margin:12px 0 0;padding:10px 12px;background:var(--sheet);border:1px solid var(--rule);border-radius:4px}
.chip{display:inline-block;padding:2px 8px;border-radius:3px;font:500 13px/1.5 "IBM Plex Mono",ui-monospace,Menlo,monospace}
.chip-same{color:var(--same);background:var(--same-bg)}.chip-hist{color:var(--hist);background:var(--hist-bg)}
.chip-excl{color:var(--excl);background:var(--excl-bg)}.chip-other{color:var(--other);background:var(--other-bg)}
.pins{font-size:14px;color:var(--accent)}
.reason{flex:1 1 100%}
@media (max-width:560px){.chain dl div{grid-template-columns:1fr}h1{font-size:22px}}
""".strip() + """
h2.section{margin:36px 0 6px;font-size:20px;line-height:1.3;font-weight:600}
h3.section{margin:22px 0 6px;font-size:16px;line-height:1.3;font-weight:600}
blockquote{margin:0 0 10px;padding:2px 0 2px 12px;border-left:3px solid var(--accent);max-width:68ch}
.table-wrap{overflow-x:auto;margin:8px 0 12px}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:6px 8px;border-bottom:1px solid var(--rule);text-align:left;vertical-align:baseline}
th{font:500 12px/1.4 "IBM Plex Mono",ui-monospace,Menlo,monospace;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
td.n{text-align:right;font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-variant-numeric:tabular-nums;white-space:nowrap}
tr.total td{font-weight:600}
.refs{margin:0;padding-left:18px}
.fields div{display:grid;grid-template-columns:170px minmax(0,1fr);gap:4px 14px;padding-block:6px;border-bottom:1px solid var(--rule)}
@media (max-width:560px){.fields div{grid-template-columns:1fr}table{font-size:13px}th,td{padding:6px 4px}th{letter-spacing:0}}
"""


def batch_ruling_id(platform_family: str, batch: str) -> str:
    """The batch ruling R-DEC-FAM-<FAM>-B<n> (§6), e.g. R-DEC-FAM-F35-B1."""
    return f"R-DEC-FAM-{_fam(platform_family)}-{batch}"


def ref_tier(ref: str, sources: Mapping[str, reg.Source]) -> str:
    """An evidence ref's tier as the page shows it (§7.5): doc: G, src: its
    source's tier, era: era decision, fact: fact, ev: reserved."""
    prefix, _, rest = ref.partition(":")
    if prefix == "doc":
        return "G"
    if prefix == "src":
        return sources[rest.split("#", 1)[0]].tier
    tier = {"era": "era decision", "fact": "fact", "ev": "reserved"}.get(prefix)
    if tier is None:
        raise ValueError(f"evidence ref {ref!r} has no known prefix (doc:, src:, era:, fact:, ev:)")
    return tier


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)


def _fmt_m(value: Decimal | None) -> str:
    """$M with thousands separators and one decimal; — when absent."""
    return "—" if value is None else f"{value:,.1f}"


def _sections(rows: Sequence[Mapping[str, str]]) -> tuple[list, list, list]:
    """The page's three row groups (§8.2): approved counted rows by FY actuals
    (headline_actuals_k), largest first; approved context rows; every other
    row (deferred, rejected or excluded)."""
    def approved(row: Mapping[str, str], role: str) -> bool:
        return row["verdict"] == "approved" and row["role"] == role

    counted = sorted((r for r in rows if approved(r, "counted")),
                     key=lambda r: (-Decimal(r["headline_actuals_k"] or 0), r["member_row_id"]))
    context = sorted((r for r in rows if approved(r, "context")), key=lambda r: (r["member_id"], r["member_row_id"]))
    other = sorted((r for r in rows if not approved(r, "counted") and not approved(r, "context")),
                   key=lambda r: (r["member_id"], r["member_row_id"]))
    return counted, context, other


def _refs_html(refs: Sequence[str], sources: Mapping[str, reg.Source]) -> str:
    if not refs:
        return "—"
    items = "".join(f"<li>{_e(ref)} ({_e(ref_tier(ref, sources))})</li>" for ref in refs)
    return f'<ul class="refs">{items}</ul>'


def _tone(row: Mapping[str, str]) -> str:
    if row["verdict"] == "approved" and row["role"] == "counted":
        return "same"
    if row["verdict"] == "deferred":
        return "hist"
    if row["verdict"] == "rejected" or row["role"] == "excluded":
        return "excl"
    return "other"


def _row_html(n: int, row: Mapping[str, str], sources: Mapping[str, reg.Source], *, not_counted: bool) -> str:
    amount = "—" if row["headline_actuals_k"] == "" else _fmt_m(_to_m(Decimal(row["headline_actuals_k"])))
    usd = amount if amount == "—" else f"${amount}M"
    label = ' <span class="label">not counted</span>' if not_counted else ""
    tags = " · ".join(f"{name} {_e(row[col]) or '—'}" for name, col in (
        ("program", "program_tag"), ("purpose", "purpose_tag"), ("variants", "variant_ids"),
        ("variant scope", "variant_scope")))
    return (
        f'<li class="chain" id="row-{n}">\n'
        f'<div class="chain-head"><span class="num">{n}</span><h2><code>{_e(row["member_id"])}</code>'
        f'<span class="acct">{_e(row["display_title"])}</span></h2>'
        f'<span class="usd">{_e(usd)}</span>{label}</div>\n'
        f'<p class="span"><span class="chip chip-{_tone(row)}">{_e(row["role"])} · {_e(row["verdict"])}</span> '
        f'PB{_e(row["valid_from_edition"])}–PB{_e(row["valid_to_edition"])}<br>'
        f'<span class="cid">{_e(row["member_row_id"])}</span></p>\n'
        f"<dl>\n"
        f"<div><dt>Tags</dt><dd>{tags}</dd></div>\n"
        f"<div><dt>Evidence</dt><dd>{_refs_html(reg.split_refs(row['evidence']), sources)}</dd></div>\n"
        f'<div><dt>drift_sha256</dt><dd><code class="cid">{_e(row["drift_sha256"]) or "—"}</code></dd></div>\n'
        f"</dl>\n"
        f'<p class="proposal"><span class="label">Reason</span><span class="reason">{_e(row["reason"])}</span></p>\n'
        f"</li>"
    )


def _rows_section(title: str, intro: str, rows: Sequence[Mapping[str, str]], first: int,
                  sources: Mapping[str, reg.Source], *, not_counted: bool = False) -> str:
    items = "\n".join(_row_html(n, row, sources, not_counted=not_counted) for n, row in enumerate(rows, first))
    body = f'<ol class="chains">\n{items}\n</ol>' if rows else '<p class="how">None.</p>'
    return f'<section>\n<h2 class="section">{_e(title)}</h2>\n<p class="how">{intro}</p>\n{body}\n</section>\n'


def _difference_label(d: Mapping) -> str:
    where = f"FY{d['fy']} {d['kind']}" if d["fy"] is not None else d["kind"]
    return f"{where} {d['member_id'] or 'total'}"


def _figures_html(result: PreviewResult, reference: Mapping | None, differences: Sequence[Mapping],
                  batch: str) -> str:
    totals = reference["totals"] if reference is not None else {}
    rows = [f'<tr><td>FY{_e(y["fy"])}</td><td>{_e(y["kind"])}</td><td>PB{_e(y["edition"])}</td>'
            f'<td class="n">{_fmt_m(_to_m(y["total_thousands"]))}</td>'
            f'<td class="n">{_fmt_m(_ref_m(totals.get(str(y["fy"]))))}</td></tr>' for y in result.years]
    actuals = [y["fy"] for y in result.years if y["kind"] == "actuals"]
    span = ("Cumulative actuals" if not actuals else f"FY{min(actuals)} cumulative actuals"
            if min(actuals) == max(actuals) else f"FY{min(actuals)}–{max(actuals)} cumulative actuals")
    cumulative_ref = _ref_m(reference["cumulative"]) if reference is not None else None
    rows.append(f'<tr class="total"><td colspan="3">{_e(span)}</td>'
                f'<td class="n">{_fmt_m(_to_m(result.cumulative_thousands))}</td>'
                f'<td class="n">{_fmt_m(cumulative_ref)}</td></tr>')
    table = ('<div class="table-wrap"><table>\n<thead><tr><th>FY</th><th>Kind</th><th>Edition</th>'
             '<th>Preview $M</th><th>Reference $M</th></tr></thead>\n<tbody>\n' + "\n".join(rows)
             + "\n</tbody></table></div>")
    if reference is None:
        note = f'<p class="how">No reference figures for {_e(batch)}.</p>'
    elif not differences:
        note = ('<p class="how">The preview agrees with the reference in every year and in the cumulative, '
                "at $0.1M.</p>")
    else:
        items = "\n".join(
            f"<li><b>{_e(_difference_label(d))}</b>: preview {_fmt_m(_to_m(d['preview_k']))} vs reference "
            f'{_fmt_m(d["reference_m"])} ($M) <span class="chip chip-hist">{_e(d["cause"])}</span></li>'
            for d in differences)
        note = (f'<p class="how">{len(differences)} difference(s) from the reference, each with its cause. '
                f"Rows are never adjusted to match.</p>\n<ul>\n{items}\n</ul>")
    return (f'<section>\n<h2 class="section">Preview figures</h2>\n'
            f'<p class="how">The counted rows built by the history builder from this draft against the snapshot, '
            f"in $M (thousands rounded half-up to $0.1M), beside the reference figures for {_e(batch)} "
            f"(— where a figure is absent).</p>\n{table}\n{note}\n</section>\n")


def _field_text(value: object) -> str:
    if value is None or value in ("", [], {}):
        return "—"
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return "; ".join(value)
    return json.dumps(value, ensure_ascii=False)


def _family_html(family: Mapping, sources: Mapping[str, reg.Source]) -> str:
    fields = "\n".join(f'<div><dt>{_e(key)}</dt><dd class="pre">{_e(_field_text(family[key]))}</dd></div>'
                       for key in reg.FAMILY_KEYS
                       if key in family and key not in _FAMILY_IDENTITY_KEYS and key != "exclusions")
    exclusions = family.get("exclusions") or []
    if exclusions:
        rows = "\n".join(
            f"<tr><td><code>{_e(x['exclusion_id'])}</code></td><td>{_e(x['kind'])}</td><td>{_e(x['label'])}</td>"
            f"<td>{_e(x['size_text'])}</td><td>{_refs_html(x.get('evidence') or [], sources)}</td></tr>"
            for x in exclusions)
        table = ('<div class="table-wrap"><table>\n<thead><tr><th>exclusion_id</th><th>kind</th><th>label</th>'
                 f"<th>size_text</th><th>evidence</th></tr></thead>\n<tbody>\n{rows}\n</tbody></table></div>")
    else:
        table = '<p class="how">None proposed.</p>'
    return (f'<section>\n<h2 class="section">Family fields</h2>\n'
            f'<p class="how">The draft family object as written in platform_families.json. Ratify refuses it if it '
            f"changes after this page; a change here means re-running propose and a new page.</p>\n"
            f'<dl class="fields">\n{fields}\n</dl>\n'
            f'<h3 class="section">Exclusions</h3>\n{table}\n</section>\n')


def render_page(*, family: Mapping, rows: Sequence[Mapping[str, str]], sources: Mapping[str, reg.Source],
                result: PreviewResult, reference: Mapping | None, differences: Sequence[Mapping],
                batch: str) -> str:
    """One self-contained Artifact page fragment (<title>, the font link,
    <style>, <main>), as scripts/era/review_batch_page.py:render_page emits.
    `family` is the family object as written in platform_families.json;
    `rows` are its review.csv rows; every interpolated value is escaped. The
    sections follow §8.2: the preview figures, the counted rows, the context
    rows (not counted), every other row, then the family's fields and its
    exclusions."""
    pf, short = family["platform_family"], family["short_name"]
    counted, context, other = _sections(rows)
    headline = family.get("headline") or {}
    actuals = (f"FY{headline['first_fy']}–{headline['last_fy'] % 100:02d} actuals"
               if {"first_fy", "last_fy"} <= set(headline) else "recorded actuals")
    prior = PRIOR_APPROVALS.get(pf)
    prior_html = (f'<p class="how"><b>Prior approval of the member set, {_e(prior[0])}:</b></p>\n'
                  f"<blockquote>“{_e(prior[1])}”</blockquote>\n") if prior else ""
    commitment = PIECE_COMMITMENTS.get(pf)
    commitment_html = f'<p class="how">{_e(commitment)}</p>\n' if commitment else ""
    n = len(counted) + len(context) + len(other)
    header = (
        f'<header class="intro">\n'
        f'<p class="eyebrow">Fiscal Receipts · platform families</p>\n'
        f"<h1>Family review, {_e(short)}, batch {_e(batch)}</h1>\n"
        f'<p class="lede">{n} proposed row{"" if n == 1 else "s"} for the {_e(short)} family: {len(counted)} counted, '
        f"{len(context)} context and {len(other)} other. Your answer ratifies them as shown, under ruling "
        f"{_e(batch_ruling_id(pf, batch))}; nothing is published by it.</p>\n"
        f"{prior_html}{commitment_html}"
        f'<p class="how">Reply in chat with <b>approved</b> to ratify every row as shown, or name a row and its '
        f"change: a new value for an amendable column (for example its role, verdict, tags or evidence), or "
        f"<b>defer</b>. A change to a family field means a new page.</p>\n"
        f"</header>\n"
    )
    body = (
        _figures_html(result, reference, differences, batch)
        + _rows_section("Counted rows", f"Sorted by {_e(actuals)} ($M), largest first.", counted, 1, sources)
        + _rows_section("Context rows (not counted)",
                        f"Whole-line {_e(actuals)} ($M), shown for context; never summed into the family.",
                        context, 1 + len(counted), sources, not_counted=True)
        + _rows_section("Other rows (deferred, rejected or excluded)",
                        f"Outside the family as ratified ({_e(actuals)}, $M); a deferred row returns in a later "
                        "batch.",
                        other, 1 + len(counted) + len(context), sources)
        + _family_html(family, sources)
    )
    return (f"<title>{_e(short)} family review {_e(batch)}</title>\n"
            f'<link rel="stylesheet" href="{_e(FONTS)}">\n'
            f"<style>\n{PAGE_CSS}</style>\n"
            f'<main class="page">\n{header}{body}</main>\n')


def _read_reference(path: Path) -> dict:
    """reference-<batch>.json: exactly REFERENCE_KEYS ($M; a null is absent)."""
    try:
        reference = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise reg.RegistryError([reg._line(path.name, None, f"is not valid JSON ({e})")]) from e
    if not isinstance(reference, dict) or set(reference) != REFERENCE_KEYS:
        keys = sorted(reference) if isinstance(reference, dict) else type(reference).__name__
        raise reg.RegistryError([reg._line(path.name, None, f"has keys {keys}; a reference has exactly "
                                                            f"{sorted(REFERENCE_KEYS)}")])
    return reference


def _manifest_difference(d: Mapping) -> dict:
    return {"fy": d["fy"], "kind": d["kind"], "member_id": d["member_id"],
            "preview_k": None if d["preview_k"] is None else f"{d['preview_k']:.3f}",
            "reference_m": None if d["reference_m"] is None else f"{d['reference_m']:.1f}",
            "cause": d["cause"], "blocks": d["blocks"]}


def render(*, platform_family: str, batch: str, duckdb_path: Path, site_dir: Path, review_root: Path = reg.REVIEW_ROOT,
           out_root: Path = OUT_ROOT, preview_out: Path) -> dict:
    """`platform-families render` (§8.2, §8.3): preview the draft (--draft)
    into `preview_out`, set it beside the batch's reference figures when
    review_root/<pf>/reference-<batch>.json exists, then write the batch page
    and its manifest, out_root/<pf>/B<n>.{html,json} (D10), in one atomic
    call. A preview error, or a difference caused by a row of the proposal,
    raises and writes no page; a lake-drift difference is shown on the page.
    Returns {"page", "manifest", "rows", "differences"}."""
    pf = platform_family
    paths = reg.DEFAULT_PATHS
    registry = reg.load_registry(paths)
    review_csv, review_era_csv = review_files(review_root, pf)
    ruling_id = batch_ruling_id(pf, batch)
    errors: list[str] = []
    if not era_map.BATCH_RE.fullmatch(batch):  # .match: `$` accepts "B1\n"
        errors.append(f"platform-families: batch {batch!r} is not B<n> (e.g. B1)")
    status = next((f.status for f in registry.families if f.platform_family == pf), None)
    if status is None:
        errors.append(reg._line(paths.json.name, pf, f"{pf} is not in {paths.json.name}"))
    elif status != "draft":
        errors.append(reg._line(paths.json.name, pf, f"{pf} is {status}; render pages draft families only"))
    if ruling_id in registry.rulings:
        errors.append(reg._line(paths.json.name, ruling_id,
                                f"{ruling_id} is already in rulings; batch {batch} was ratified, render the next one"))
    if not review_csv.is_file():
        errors.append(reg._line(review_csv.name, None, f"missing (no file at {review_csv}); run propose first"))
    if errors:
        raise reg.RegistryError(errors)

    # Step 1: the preview, from the draft; any error propagates and writes no page.
    result = preview(platform_family=pf, draft=True, site_dir=site_dir, duckdb_path=duckdb_path, out=preview_out,
                     paths=reg.DEFAULT_PATHS, review_root=review_root)

    # Step 2: the reference, and each difference's cause from the lake.
    reference_path = Path(review_root) / pf / f"reference-{batch.lower()}.json"
    reference = _read_reference(reference_path) if reference_path.exists() else None
    differences: list[dict] = []
    if reference is not None:
        start = vf._now()
        vf.sam_guard(duckdb_path, start=start)
        lake = reg.open_lake(duckdb_path)
        try:
            differences = compare_reference(result, reference, lake=lake)
        finally:
            lake.close()
        vf.sam_guard(duckdb_path, start=start, end=vf._now())

    # Step 3: a difference caused by a row of the proposal blocks the page.
    blocking = [d for d in differences if d["blocks"]]
    if blocking:
        def shown(value: Decimal | None) -> str:
            return "—" if value is None else str(value)

        raise reg.RegistryError([
            f"platform-families: {review_csv.name}: {_difference_label(d)}: preview {shown(_to_m(d['preview_k']))} "
            f"vs reference {shown(d['reference_m'])} ($M) — {CAUSE_PROPOSAL}; fix the prefill, re-run propose, "
            f"render again" for d in blocking])

    # Step 4: the page and its manifest, in one atomic call.
    rows, _era_rows = _read_review_files(review_root, pf)
    counted, context, other = _sections(rows)
    ordered = [*counted, *context, *other]
    family = next(f for f in registry.doc["families"] if f.get("platform_family") == pf)
    page = render_page(family=family, rows=ordered, sources=registry.sources, result=result, reference=reference,
                       differences=differences, batch=batch)
    manifest = {
        "schema_version": 1, "platform_family": pf, "batch": batch, "rows": ordered,
        "review_sha256": hashlib.sha256(review_csv.read_bytes()).hexdigest(),
        "review_era_lines_sha256": hashlib.sha256(review_era_csv.read_bytes()).hexdigest(),
        "family_sha256": reg.family_hash(registry.doc, pf),
        "preview": {
            "years": [{"fy": y["fy"], "kind": y["kind"], "edition": y["edition"],
                       "total_thousands": f"{y['total_thousands']:.3f}"} for y in result.years],
            "cumulative_thousands": f"{result.cumulative_thousands:.3f}",
            "differences": [_manifest_difference(d) for d in differences],
        },
    }
    page_path = Path(out_root) / pf / f"{batch}.html"
    manifest_path = Path(out_root) / pf / f"{batch}.json"
    era_map._atomic_write_texts({page_path: page,
                                 manifest_path: json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"})
    return {"page": page_path, "manifest": manifest_path, "rows": len(ordered), "differences": len(differences)}
