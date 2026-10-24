"""Shared fixtures for the platform-families tools' tests (families piece 2,
Tasks 7a–7d; spec §8.3, §13).

pytest puts tests/ on sys.path, so these import as
`from platform_families_helpers import …`. The data is fixed by the plan
(Task 7a Step 1): the committed F-15 entry, a draft F-35 family object (§7.2's
F-35 column), its MSAR source, four prefill rows with their lake measures and
the B1 reference figures.
"""
from __future__ import annotations

import copy
import csv
import json
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal
from pathlib import Path

import duckdb

from govbudget import platform_families as reg
from govbudget.platform_family_history import _json_bytes

# ---------------------------------------------------------------------------
# Data (exact values, plan Task 7a Step 1)
# ---------------------------------------------------------------------------

MSAR = {"source_id": "msar-pb2027", "title": "DoD MSAR for the FY2027 budget, effective 21 April 2026",
        "publisher": "Department of Defense", "url": "https://www.esd.whs.mil/", "as_of": "2026-04-21",
        "sha256": "063345e4a46f7d58cf89356389fb36986e5a0f8c06c716030ead49932e8dca50", "bytes": 1298631,
        "archived": False, "tier": "G", "verified_by": []}
DRAFT_F35 = {  # §7.2's F-35 column; keys in §7.2 table order
    "platform_family": "f-35", "status": "draft", "short_name": "F-35", "history_dataset": "f35_funding_history",
    "on_partial_corpus": "raise", "headline": {"measure": "cumulative_actuals", "first_fy": 2015, "last_fy": 2024},
    "scope_note": "Draft scope note for the B1 page.", "coverage_notes": [],
    "review_guard": {"exhibits": ["P-1", "R-1"], "title_substrings": ["F-35", "F35", "JSF", "JOINT STRIKE", "F135", "LIGHTNING"]},
    "program_notes": {}, "variants": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
    "program_tags": [{"tag": "F-35", "mdap_code": "198"}],
    "purpose_tags": ["production", "modifications", "sdd", "block4", "usaf_squadrons"],
    "caveat_ids": ["classified", "construction", "operating_and_support", "spares", "foreign", "cr_years", "nominal_dollars"],
    "exclusions": [], "aliases": [], "contract_routes": None, "official_estimates": None, "art": None}

F15_ORDER = ["R-1:3600F:AF:0207134F", "R-1:3600F:AF:0207146F", "R-1:3600F:AF:0207171F", "P-1:3010F:AF:F01500",
             "P-1:3010F:AF:F015EX", "P-1:3010F:AF:F15EWS", "P-1:3010F:AF:F0150P", "P-1:3010F:AF:F015E0"]  # §7.6

F35_RULING_ID = "R-DEC-FAM-F35-B1"
ATA000, EMD, JSM000, CIP = ("P-1:3010F:AF:ATA000", "R-1:3600F:AF:0604800F", "P-1:3020F:AF:JSM000",
                            "R-1:3600F:AF:0207268F")


def _prefill_row(member_id: str, **kv: str) -> dict[str, str]:
    """A row over reg.PREFILL_COLUMNS, blank where the plan names nothing. The
    exhibit, account, organization and code come from the member_id; every row
    carries platform_family f-35 (ruling R-PF-2)."""
    exhibit, account, organization, code = member_id.split(":")
    row = dict.fromkeys(reg.PREFILL_COLUMNS, "")
    row.update(platform_family="f-35", member_id=member_id, exhibit=exhibit, account=account,
               organization=organization, code=code)
    for key, value in kv.items():
        if key not in row:
            raise KeyError(key)
        row[key] = value
    return row


F35_PREFILL = [
    _prefill_row(ATA000, role="counted", verdict="approved", appropriation="procurement",
                 valid_from_edition="2017", valid_to_edition="2026", coverage_expected_from_edition="2017",
                 member_order="1", program_tag="F-35", purpose_tag="production", purpose="buy",
                 variant_ids="A", variant_scope="variant", services_using="USAF", paying_org="AF",
                 display_title="F-35", page_slug="ATA000", era_decision_ids="ATA000|3010F||2017-2023",
                 evidence="era:ATA000|3010F||2017-2023;src:msar-pb2027#p25", reason="MDAP 198 on the P-40"),
    _prefill_row(EMD, role="counted", verdict="approved", appropriation="rdte",
                 valid_from_edition="2017", valid_to_edition="2023", coverage_expected_from_edition="2017",
                 member_order="2", program_tag="F-35", purpose_tag="sdd", purpose="develop",
                 variant_ids="A;B;C", variant_scope="shared", services_using="USAF;USN;USMC", paying_org="AF",
                 display_title="F-35 EMD", page_slug="0604800F",
                 scope_note="Development shared by A, B and C, counted by paying service.",
                 evidence="src:msar-pb2027", reason="MSAR funding sources"),
    _prefill_row(JSM000, role="context", verdict="approved", appropriation="procurement",
                 valid_from_edition="2022", valid_to_edition="2026", display_title="Joint Strike Missile",
                 scope_note="A missile the F-35 carries, not the aircraft; never summed.",
                 evidence="src:msar-pb2027", reason="review-guard match JOINT STRIKE; not counted"),
    _prefill_row(CIP, role="project_slice", verdict="deferred", appropriation="rdte",
                 valid_from_edition="2017", valid_to_edition="2026", project_number="675365",
                 display_title="F135 CIP (project 675365)", evidence="src:msar-pb2027",
                 reason="waits for the project-slice pilot"),
]

# A member's family: the F-15's eight members, else the F-35 (the family every
# Task 7b-7d fixture reviews).
_FAMILY_OF = {**{member_id: "f-15" for member_id in F15_ORDER},
              **{row["member_id"]: row["platform_family"] for row in F35_PREFILL}}

B1_REF = {"lines": {"ATA000": {"2015": 4044.7, "2025": 4972.5, "2026": 4086.7},
                    "0604800F": {"2015": 566.9, "2025": None, "2026": None}},
          "totals": {"2015": 4611.6, "2025": 4972.5, "2026": 4086.7},
          "cumulative": 4611.6, "fy2025_enacted": 4972.5, "fy2026_request": 4086.7}
B1_POINTS = [(2015, "actuals", 2017, "4611600.000", {"P-1:3010F:AF:ATA000": "4044700.000", "R-1:3600F:AF:0604800F": "566900.000"}),
             (2025, "enacted", 2026, "4972500.000", {"P-1:3010F:AF:ATA000": "4972500.000"}),
             (2026, "request", 2026, "4086700.000", {"P-1:3010F:AF:ATA000": "4086700.000"})]
B1_MART = {"ATA000": {(2015, "actuals"): Decimal("4044700"), (2025, "enacted"): Decimal("4972500"), (2026, "request"): Decimal("4086700")},
           "0604800F": {(2015, "actuals"): Decimal("566900")}}


# ---------------------------------------------------------------------------
# Measures (Task 2c's MemberMeasure, stubbed)
# ---------------------------------------------------------------------------


def era_line(member_id, edition, era_key, ba, title, decision_id) -> reg.EraLine:
    """EraLine(platform_family=member's family, member_id, edition, era_key, budget_activity, filed_title, decision_id)."""
    return reg.EraLine(platform_family=_FAMILY_OF.get(member_id, "f-35"), member_id=member_id, edition=edition,
                       era_key=era_key, budget_activity=ba, filed_title=title, decision_id=decision_id)


def measure(member_id, *, drift, actuals_k=None, titles=(), era_lines=()) -> reg.MemberMeasure:
    """budget_activities=("01",), editions = the titles' editions, headline_actuals_k = Decimal(actuals_k) or None."""
    titles = tuple(titles)
    return reg.MemberMeasure(titles_seen=titles, budget_activities=("01",),
                             editions=tuple(edition for edition, _title in titles), drift_sha256=drift,
                             era_lines=tuple(era_lines),
                             headline_actuals_k=Decimal(actuals_k) if actuals_k is not None else None)


MEASURES = {
    ATA000: measure(ATA000, drift="a" * 64, actuals_k="53368300.000",
                    titles=((2024, "F-35"), (2025, "F-35"), (2026, "F-35")),
                    era_lines=(era_line(ATA000, 2018, "3010F-AF-L1", "01", "F-35", "ATA000|3010F||2017-2023"),)),
    EMD: measure(EMD, drift="b" * 64, actuals_k="1939500.000", titles=((2023, "F-35 EMD"),)),
    JSM000: measure(JSM000, drift="c" * 64, actuals_k="373500.000", titles=((2026, "Joint Strike Missile"),)),
    CIP: measure(CIP, drift="d" * 64, actuals_k=None, titles=((2026, "F-35 Squadrons"),)),
}


def _lake_columns(m: reg.MemberMeasure) -> dict[str, str]:
    return {"titles_seen": "; ".join(f"{edition}: {title}" for edition, title in m.titles_seen),
            "budget_activities": ";".join(m.budget_activities), "drift_sha256": m.drift_sha256}


class FakeLake:  # program_series(code) -> series.get(code, {}); close() sets .closed
    def __init__(self, series: dict[str, dict[tuple[int, str], Decimal]] | None = None):
        self.series = series or {}
        self.closed = False

    def program_series(self, code: str) -> dict[tuple[int, str], Decimal]:
        return self.series.get(code, {})

    def close(self) -> None:
        self.closed = True


# ---------------------------------------------------------------------------
# Registries on disk
# ---------------------------------------------------------------------------


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def _read(paths: reg.RegistryPaths) -> tuple[dict, list[dict[str, str]], list[dict[str, str]]]:
    return (json.loads(paths.json.read_text(encoding="utf-8")), _read_rows(paths.members),
            _read_rows(paths.era_lines))


def _replace_by(entries: list, new: Iterable, key) -> None:
    """Replace each entry whose key matches in place, else append (a deep copy)."""
    for item in new:
        item = copy.deepcopy(dict(item))
        at = next((i for i, old in enumerate(entries) if key(old) == key(item)), None)
        if at is None:
            entries.append(item)
        else:
            entries[at] = item


def _era_key(row: Mapping[str, str]) -> tuple[str, str, str]:
    return (row["platform_family"], str(row["edition"]), row["era_key"])


def f15_registry(tmp_path: Path) -> reg.RegistryPaths:
    """The committed registry's F-15 entries only: family f-15, ruling R-DEC-FAM-F15-SEED,
    its 8 member rows and its 31 era lines. They are written with reg.write_registry under
    tmp_path/"data-seeds". Counts stay fixed after Tasks 8a/8b add the F-35 to the
    committed files."""
    committed = reg.DEFAULT_PATHS
    doc, members, era_rows = _read(committed)
    doc.update(rulings=[r for r in doc["rulings"] if r["ruling_id"] == reg.F15_SEED_RULING_ID],
               sources=[],  # the F-15 entry cites no source (§7.6)
               families=[f for f in doc["families"] if f["platform_family"] == "f-15"])
    root = Path(tmp_path) / "data-seeds"
    paths = reg.RegistryPaths(*(root / p.name for p in (committed.json, committed.members, committed.era_lines)))
    reg.write_registry(paths, doc=doc, members=[r for r in members if r["platform_family"] == "f-15"],
                       era_lines=[r for r in era_rows if r["platform_family"] == "f-15"])
    return paths


def add_family(paths, family: dict, *, sources=(), members=(), era_lines=(), rulings=()) -> None:
    """Add a family object (plus its sources, member rows, era rows and rulings) to the
    registry at `paths`, through reg.write_registry. Replace-by-id, like ratified_f35: a
    family with the same platform_family is replaced in place (keeping its index in
    families[]), and so is a source with the same source_id, a ruling with the same
    ruling_id, a member row with the same member_row_id and an era row with the same
    (platform_family, edition, era_key). Anything new is appended. cli_env has already
    added DRAFT_F35, so a test that calls add_family for f-35 again replaces that draft
    rather than adding a second f-35, which stage 1 would refuse as a duplicate (rule 2)."""
    doc, member_rows, era_rows = _read(paths)
    _replace_by(doc["families"], [family], lambda f: f["platform_family"])
    _replace_by(doc["sources"], sources, lambda s: s["source_id"])
    _replace_by(doc["rulings"], rulings, lambda r: r["ruling_id"])
    _replace_by(member_rows, members, lambda r: r["member_row_id"])
    _replace_by(era_rows, era_lines, _era_key)
    reg.write_registry(paths, doc=doc, members=member_rows, era_lines=era_rows)


def add_source(paths, source: dict) -> None:
    """Add one sources[] entry to the registry at `paths`, through reg.write_registry,
    replacing the entry with the same source_id in place (else appending): MSAR | {"bytes": 1}
    replaces cli_env's MSAR instead of duplicating msar-pb2027 (rule 7)."""
    doc, member_rows, era_rows = _read(paths)
    _replace_by(doc["sources"], [source], lambda s: s["source_id"])
    reg.write_registry(paths, doc=doc, members=member_rows, era_lines=era_rows)


def ratified_f35(paths) -> None:
    """Make f-35 ratified at `paths` through reg.write_registry, replacing any f-35 family in
    place (cli_env has added the draft) and adding MSAR to sources only when absent:
    DRAFT_F35 with status "ratified"; ruling R-DEC-FAM-F35-B1 (kind batch, decided_by owner,
    decided_on 2026-10-22, owner_reply "approved", spec "docs/x.md#b1", text "Ratifies the
    f-35 rows.", seed_basis False); one fully measured member row over MEMBER_COLUMNS:
    F35_PREFILL[0] without "reason", plus member_row_id "f-35|P-1:3010F:AF:ATA000|2017-2026",
    platform_family "f-35", MEASURES["P-1:3010F:AF:ATA000"]'s lake columns (titles_seen
    "2024: F-35; 2025: F-35; 2026: F-35", budget_activities "01", drift_sha256 "a"*64) and
    decided_by "owner", ruling_id "R-DEC-FAM-F35-B1", decided_on "2026-10-22"; and that
    measure's one era line (era_line(...).as_row()). reg.load_registry(paths) loads the
    result with no error, so a caller's refusal is the only one raised."""
    doc, _members, _era_rows = _read(paths)
    sources = [] if any(s["source_id"] == MSAR["source_id"] for s in doc["sources"]) else [MSAR]
    ruling = {"ruling_id": F35_RULING_ID, "kind": "batch", "platform_family": "f-35", "decided_by": "owner",
              "decided_on": "2026-10-22", "owner_reply": "approved", "spec": "docs/x.md#b1",
              "text": "Ratifies the f-35 rows.", "seed_basis": False}
    row = dict.fromkeys(reg.MEMBER_COLUMNS, "")
    row.update({key: value for key, value in F35_PREFILL[0].items() if key != "reason"})
    row.update(member_row_id="f-35|P-1:3010F:AF:ATA000|2017-2026", platform_family="f-35",
               **_lake_columns(MEASURES[ATA000]), decided_by="owner", ruling_id=F35_RULING_ID,
               decided_on="2026-10-22")
    add_family(paths, {**DRAFT_F35, "status": "ratified"}, sources=sources, rulings=[ruling], members=[row],
               era_lines=[line.as_row() for line in MEASURES[ATA000].era_lines])


def write_prefill(tmp_path, rows) -> tuple[Path, Path]:
    """family.json = {"family": DRAFT_F35 minus "status", "sources": [MSAR]} and rows.csv
    under reg.PREFILL_COLUMNS (blank where a row omits a column)."""
    root = Path(tmp_path)
    root.mkdir(parents=True, exist_ok=True)
    family_json, rows_csv = root / "family.json", root / "rows.csv"
    family = {key: value for key, value in DRAFT_F35.items() if key != "status"}
    family_json.write_text(json.dumps({"family": family, "sources": [MSAR]}, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    with rows_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(reg.PREFILL_COLUMNS), lineterminator="\n",
                                extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({**dict.fromkeys(reg.PREFILL_COLUMNS, ""), **row})   # an unknown column raises
    return family_json, rows_csv


# ---------------------------------------------------------------------------
# Export stand-ins
# ---------------------------------------------------------------------------


class _FakeExport:
    def __init__(self, points: Sequence[tuple[int, str, int, str, dict[str, str]]]):
        self.points = list(points)
        self.calls: list[dict] = []

    def __call__(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        family = kwargs["registry"][kwargs["families"][0]]
        payload = {
            "family_id": family.platform_family,
            "programs": [{"id": m.member_id, "code": m.code} for m in family.counted],
            "points": [{"fy": fy, "kind": kind, "edition": edition, "amount_thousands": float(Decimal(total_k)),
                        "program_cells": [{"program_id": member_id, "amount_thousands": float(Decimal(cell_k))}
                                          for member_id, cell_k in cells.items()]}
                       for fy, kind, edition, total_k, cells in self.points],
            "cumulative": {"amount_thousands": float(sum((Decimal(total_k) for _fy, kind, _e, total_k, _c
                                                          in self.points if kind == "actuals"), Decimal(0)))},
        }
        target = Path(kwargs["out_dir"]) / "json" / f"{family.history_dataset}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_json_bytes(payload))
        return {"json_files": 1}


def fake_export(points: list[tuple[int, str, int, str, dict[str, str]]]):
    """Stand-in for platform_family_history.export_family_histories. Each point is
    (fy, kind, edition, total_k, {member_id: cell_k}). The callable records each call's
    kwargs in .calls, then writes out_dir/json/<history_dataset>.json for families[0]:
    family_id, programs [{"id", "code"} per counted member], points (fy, kind, edition,
    amount_thousands, program_cells [{program_id, amount_thousands}]) and cumulative
    (amount_thousands = the sum of the actuals totals). It returns {"json_files": 1}."""
    return _FakeExport(points)


def site_tree(tmp_path, *, formulas=(), citations=None) -> Path:
    """tmp_path/"site" holding manifest.json {"built_at": "2026-10-21T00:00:00Z"},
    json/citations.json (citations or {}), and citations/citations.parquet with VARCHAR
    columns fact_id, kind, formula, inputs, query_body (one row per formula, written with
    DuckDB COPY)."""
    site = Path(tmp_path) / "site"
    (site / "json").mkdir(parents=True, exist_ok=True)
    (site / "citations").mkdir(parents=True, exist_ok=True)
    (site / "manifest.json").write_text(json.dumps({"built_at": "2026-10-21T00:00:00Z"}) + "\n", encoding="utf-8")
    (site / "json" / "citations.json").write_text(json.dumps(citations or {}) + "\n", encoding="utf-8")
    con = duckdb.connect()
    try:
        con.execute("create table c (fact_id varchar, kind varchar, formula varchar, inputs varchar,"
                    " query_body varchar)")
        rows = [(f"{i + 1:016x}", "derived", formula, "[]", "") for i, formula in enumerate(formulas)]
        if rows:
            con.executemany("insert into c values (?, ?, ?, ?, ?)", rows)
        con.execute("copy c to ? (format parquet)", [str(site / "citations" / "citations.parquet")])
    finally:
        con.close()
    return site
