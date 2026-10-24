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

Every registry (I-REG) function is called through the module attribute
(`reg.open_lake`, `reg.measure_member`, …), so a test patches it there (R15).
"""
from __future__ import annotations

import codecs
import copy
import dataclasses
from collections.abc import Mapping, Sequence
from pathlib import Path

from govbudget import config
from govbudget import platform_families as reg
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
