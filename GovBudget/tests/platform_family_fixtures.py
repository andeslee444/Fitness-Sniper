"""A miniature platform-families registry (piece 2, Tasks 2a–2c; spec §7, §9)."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from govbudget.jbooks import era_map
from govbudget.jbooks.era_map import keys_sha256
from govbudget.platform_families import MEMBER_COLUMNS, RegistryPaths, parse_registry, write_registry

ON = "2026-10-21"
RULING_X1 = "R-DEC-FAM-X1-B1"
XA, XR, XC = "P-1:3010F:AF:XA0001", "R-1:3600F:AF:XR0001", "P-1:3010F:AF:XC0001"
ERA_XA = "XA0001|3010F||2023-2023"
SRC_BYTES = b"x-book archived copy\n"            # site/sources/x-book.txt (Task 2c)
SRC_SHA = hashlib.sha256(SRC_BYTES).hexdigest()
DOC_SHA = "d" * 64                               # site/pdfs/<DOC_SHA>.pdf (Task 2c)
# (edition, code or era key, budget activity, filed title): the lines each member binds.
LINES = {
    "XA0001": [(2023, "3010F-AF-L7", "05", "X-1"), (2024, "XA0001", "05", "X-1"),
               (2025, "XA0001", "05", "X-1"), (2026, "XA0001", "05", "X-1")],
    "XR0001": [(2025, "XR0001", "07", "X-1 Dev"), (2026, "XR0001", "07", "X-1 Dev")],
    "XC0001": [(2024, "XC0001", "06", "X-1 Spares"), (2025, "XC0001", "06", "X-1 Spares"),
               (2026, "XC0001", "06", "X-1 Spares")],
}
DRIFT = {code: keys_sha256(lines) for code, lines in LINES.items()}


def ruling(rid: str, pf: str, **kv) -> dict:
    return {"ruling_id": rid, "kind": "batch", "platform_family": pf, "decided_by": "owner",
            "decided_on": ON, "owner_reply": f"yes, ratify {pf}", "spec": "docs/x.md#b1",
            "text": f"Ratifies the {pf} rows.", "seed_basis": False, **kv}


def source(**kv) -> dict:
    return {"source_id": "x-book", "title": "X-1 Selected Acquisition Report", "publisher": "DoD",
            "url": "https://x.test/sar.pdf", "as_of": "2026-04-21", "sha256": SRC_SHA, "bytes": 21,
            "archived": True, "archive_path": "sources/x-book.txt", "tier": "G", "verified_by": [], **kv}


def family(pf: str, *, status: str, ruling_id: str | None = None, **kv) -> dict:
    short = pf.upper()
    fam = {"platform_family": pf, "status": status}
    if ruling_id:
        fam["published_ruling_id"] = ruling_id
    fam.update({
        "short_name": short, "history_dataset": f"{pf.replace('-', '')}_funding_history",
        "on_partial_corpus": "raise",
        "headline": {"measure": "cumulative_actuals", "first_fy": 2015, "last_fy": 2024},
        "scope_note": f"{short} scope.", "coverage_notes": [f"{short} coverage."],
        "review_guard": {"exhibits": ["P-1", "R-1"], "title_substrings": [short]},
        "program_notes": {}, "variants": [{"id": "A"}, {"id": "B", "note": "B is the trainer."}],
        "program_tags": [{"tag": short, "mdap_code": "999"}], "purpose_tags": ["production"],
        "caveat_ids": ["classified", "nominal_dollars"], "exclusions": [], "aliases": [],
        "contract_routes": None, "official_estimates": None, "art": None, **kv})
    return fam


def member(pf: str, member_id: str, frm: int, to: int, **kv) -> dict[str, str]:
    exhibit, account, org, code = member_id.split(":")
    row = dict.fromkeys(MEMBER_COLUMNS, "")
    row.update(member_row_id=f"{pf}|{member_id}|{frm}-{to}", platform_family=pf, member_id=member_id,
               exhibit=exhibit, account=account, organization=org, code=code, verdict="approved",
               appropriation="rdte" if exhibit == "R-1" else "procurement",
               valid_from_edition=str(frm), valid_to_edition=str(to), services_using="USAF",
               paying_org="AF", decided_by="owner",
               ruling_id=f"R-DEC-FAM-{pf.replace('-', '').upper()}-B1", decided_on=ON)
    row.update(kv)
    return row


def decision(decision_id: str, kind: str) -> dict[str, str]:
    code, account, org, editions = decision_id.split("|")
    row = dict.fromkeys(era_map.SEED_COLUMNS, "")
    row.update(decision_id=decision_id, line_item_code=code, account=account, organization=org,
               first_edition=editions[:4], last_edition=editions[5:], decision=kind,
               decided_on=ON, decided_by="owner", ruling="R-DEC-ERA-SAME")
    return row


ERA_DECISIONS = {d: decision(d, k) for d, k in [
    (ERA_XA, "same_program"), ("XA0001|3010F||2017-2022", "exclude_placeholder"),
    ("XB0001|3010F||2023-2023", "same_program"), ("XZ0001|3010F||2023-2023", "same_program"),
    ("20|0300D|DSS|2022-2022", "same_program"),
]}


def _doc() -> dict:
    x1 = family("x-1", status="published", ruling_id=RULING_X1, exclusions=[
        {"exclusion_id": "spares", "kind": "shared_line", "label": "Spares",
         "size_text": "X-1 spares: $1.0M in FY2024", "evidence": ["src:x-book#p2"]}])
    return {"schema_version": 1, "rulings": [ruling(RULING_X1, "x-1")], "sources": [source()],
            "families": [x1, family("y-1", status="draft")]}


def _members() -> list[dict[str, str]]:
    return [
        member("x-1", XA, 2023, 2026, role="counted", budget_activities="05",
               titles_seen="2024: X-1; 2025: X-1; 2026: X-1", display_title="X-1", page_slug="XA0001",
               coverage_expected_from_edition="2023", era_decision_ids=ERA_XA,
               drift_sha256=DRIFT["XA0001"], member_order="1", program_tag="X-1",
               purpose_tag="production", purpose="buy", variant_ids="A", variant_scope="variant",
               evidence=f"era:{ERA_XA};src:x-book#p3"),
        member("x-1", XR, 2025, 2026, role="counted", budget_activities="07",
               titles_seen="2025: X-1 Dev; 2026: X-1 Dev", display_title="X-1 Dev", page_slug="XR0001",
               coverage_expected_from_edition="2025", drift_sha256=DRIFT["XR0001"], member_order="2",
               program_tag="X-1", purpose="develop", variant_ids="A;B", variant_scope="shared",
               scope_note="Shared A/B development.", evidence=f"doc:{DOC_SHA}#p1;q=X-1 development"),
        member("x-1", XC, 2024, 2026, role="context", budget_activities="06",
               titles_seen="2024: X-1 Spares; 2025: X-1 Spares; 2026: X-1 Spares",
               display_title="X-1 Spares", drift_sha256=DRIFT["XC0001"],
               scope_note="A shared spares line; never summed.", evidence="src:x-book#p4"),
    ]


def _era_rows() -> list[dict[str, str]]:
    return [{"platform_family": "x-1", "member_id": XA, "edition": "2023", "era_key": "3010F-AF-L7",
             "budget_activity": "05", "filed_title": "X-1", "decision_id": ERA_XA}]


class World:
    """A fresh deep copy of the registry; a test mutates it, then parses it."""

    def __init__(self):
        self.doc, self.members, self.era_rows = _doc(), _members(), _era_rows()
        self.decisions = copy.deepcopy(ERA_DECISIONS)

    def family(self, pf: str = "x-1") -> dict:
        return next(f for f in self.doc["families"] if f["platform_family"] == pf)

    def member(self, code: str, pf: str = "x-1") -> dict[str, str]:
        return next(m for m in self.members if m["platform_family"] == pf and m["code"] == code)

    def add_family(self, pf: str, *, status: str) -> dict:
        rid = f"R-DEC-FAM-{pf.replace('-', '').upper()}-B1"
        if status != "draft":
            self.doc["rulings"].append(ruling(rid, pf))
        fam = family(pf, status=status, ruling_id=rid if status == "published" else None)
        self.doc["families"].append(fam)
        return fam

    def add_member(self, pf: str, member_id: str, frm: int, to: int, **kv) -> dict[str, str]:
        row = member(pf, member_id, frm, to, **kv)
        self.members.append(row)
        return row

    def parse(self):
        return parse_registry(self.doc, self.members, self.era_rows, era_decisions=self.decisions)


def tmp_paths(root: Path) -> RegistryPaths:
    return RegistryPaths(root / "platform_families.json", root / "platform_family_members.csv",
                         root / "platform_family_era_lines.csv")


def write_world(root: Path, world: World) -> tuple[RegistryPaths, Path]:
    """The world as committed files plus an era seed holding its decisions."""
    paths = tmp_paths(root / "data-seeds")
    write_registry(paths, doc=world.doc, members=world.members, era_lines=world.era_rows)
    seed = root / "p1_era_code_decisions.csv"
    era_map.write_csv(seed, era_map.SEED_COLUMNS, world.decisions.values())
    return paths, seed
