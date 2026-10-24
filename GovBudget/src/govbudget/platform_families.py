"""The platform-family registry: formats, vocabularies and the loader (families piece 2).

Spec: docs/superpowers/specs/2026-10-20-families-piece2-registry-design.md
§7 (the three registry files under data-seeds/: platform_families.json, the
frozen 49-column platform_family_members.csv and platform_family_era_lines.csv)
and §9 (the loader). Stage 1 reads the files alone, collects every fault and
raises one RegistryError whose lines read
'platform-families: <file>[:<row id>]: <reason>'; it never strips or otherwise
normalizes a value.

Module-level imports are the standard library, govbudget.config and
govbudget.jbooks.era_map only: stage 1 runs on every import of the F-15 facade,
program_pdf_receipts and export_site.
"""
from __future__ import annotations

import codecs
import copy
import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from govbudget import config
from govbudget.jbooks import era_map

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REGISTRY_JSON = config.ROOT / "data-seeds" / "platform_families.json"
MEMBERS_CSV = config.ROOT / "data-seeds" / "platform_family_members.csv"
ERA_LINES_CSV = config.ROOT / "data-seeds" / "platform_family_era_lines.csv"
REVIEW_ROOT = config.RESEARCH_DIR / "platform_families"


@dataclass(frozen=True)
class RegistryPaths:
    json: Path
    members: Path
    era_lines: Path


DEFAULT_PATHS = RegistryPaths(REGISTRY_JSON, MEMBERS_CSV, ERA_LINES_CSV)

# ---------------------------------------------------------------------------
# Columns and key orders (spec §7.2, §7.3, §7.4)
# ---------------------------------------------------------------------------

MEMBER_COLUMNS = (  # spec §7.3, frozen order
    "member_row_id", "platform_family", "member_id", "exhibit", "account", "organization", "code",
    "role", "verdict", "project_number", "appropriation", "budget_activities", "titles_seen",
    "display_title", "page_slug", "valid_from_edition", "valid_to_edition",
    "coverage_expected_from_edition", "expected_next_edition", "era_decision_ids", "drift_sha256",
    "member_order", "program_tag", "purpose_tag", "purpose", "variant_ids", "variant_scope",
    "scope_note", "services_using", "paying_org", "predecessor_member_id", "successor_member_id",
    "link_basis", "link_evidence", "evidence", "quantity_bearing", "quantity_row", "quantity_notes",
    "jbook_anchor", "contract_link_policy", "msar_account", "msar_funding_source_page",
    "msar_shared_flag", "allocation_source", "allocation_years", "decided_by", "ruling_id",
    "decided_on", "note")
ERA_LINE_COLUMNS = ("platform_family", "member_id", "edition", "era_key", "budget_activity",
                    "filed_title", "decision_id")
REVIEW_COLUMNS = MEMBER_COLUMNS + ("reason", "headline_actuals_k")
PREFILL_COLUMNS = tuple(c for c in MEMBER_COLUMNS if c not in {
    "member_row_id", "titles_seen", "budget_activities", "drift_sha256", "decided_by", "ruling_id",
    "decided_on"}) + ("reason",)
ON_PARTIAL_CORPUS = ("skip", "raise")
RULING_KINDS = ("class", "batch")
HEADLINE_MEASURES = ("cumulative_actuals",)
GUARD_EXHIBITS = ("P-1", "R-1")
EDITIONS = range(2017, 2027)
SEED_BASIS_ALLOWED = frozenset({"R-DEC-FAM-F15-SEED"})
F15_SEED_RULING_ID = "R-DEC-FAM-F15-SEED"
TOP_KEYS = ("schema_version", "rulings", "sources", "families")
RULING_KEYS = ("ruling_id", "kind", "platform_family", "decided_by", "decided_on", "owner_reply",
               "spec", "text", "seed_basis")
SOURCE_KEYS = ("source_id", "title", "publisher", "url", "as_of", "sha256", "bytes", "archived",
               "archive_path", "tier", "verified_by")           # optional: sha256, bytes, archive_path, verified_by
FAMILY_KEYS = ("platform_family", "status", "published_ruling_id", "short_name", "history_dataset",
               "on_partial_corpus", "headline", "scope_note", "coverage_notes", "review_guard",
               "program_notes", "variants", "program_tags", "purpose_tags", "caveat_ids",
               "exclusions", "aliases", "contract_routes", "official_estimates", "art")  # optional: published_ruling_id
HEADLINE_KEYS = ("measure", "first_fy", "last_fy")
GUARD_KEYS = ("exhibits", "title_substrings")
PROGRAM_NOTE_KEYS = ("note", "note_fact_id", "expected_receipt")
RECEIPT_KEYS = ("kind", "page_number", "pe_bli", "sha256")
VARIANT_KEYS = ("id", "note")                                   # note optional
PROGRAM_TAG_KEYS = ("tag", "mdap_code")                         # mdap_code str or null
EXCLUSION_KEYS = ("exclusion_id", "kind", "label", "size_text", "evidence")
CONTRACT_ROUTE_KEYS = ("program_codes", "description_pattern", "description_exclusions", "basis")  # basis: action|award
OFFICIAL_ESTIMATE_KEYS = ("msar_program_number", "msar_source_ids", "gao_program_key", "wsaa_exit_ruling")
ART_KEYS = ("src", "alt", "caption", "generated")              # generated true needs "AI-generated" in caption

# ---------------------------------------------------------------------------
# Vocabularies (spec §7.2, §7.3)
# ---------------------------------------------------------------------------

ROLES = ("counted", "context", "project_slice", "excluded")
VERDICTS = ("approved", "deferred", "rejected")
EXHIBITS = ("P-1", "R-1", "P-1R")
STATUSES = ("draft", "ratified", "published")
SOURCE_TIERS = ("G", "PG", "C", "X")
APPROPRIATIONS = ("procurement", "rdte")
PURPOSES = ("buy", "upgrade", "develop", "support")
VARIANT_SCOPES = ("variant", "shared")
LINK_BASES = ("book_stated", "era_map", "inferred")
CONTRACT_LINK_POLICIES = ("production+AP", "modifications_only", "development", "none")
SERVICES = ("USAF", "USN", "USMC", "USA", "USSF", "SOCOM", "DW")
PAYING_ORGS = ("AF", "NAVY", "USMC", "ARMY", "USSF", "SOCOM", "DW")
CAVEAT_IDS = ("classified", "construction", "operating_and_support", "spares", "foreign",
              "cr_years", "nominal_dollars")
EXCLUSION_KINDS = ("outside_scope", "not_a_budget_line", "shared_line")
CONTRACT_ROUTE_BASES = ("action", "award")

# Every regex in this module is applied with .fullmatch (a bare `$` would
# accept a trailing newline).
PLATFORM_FAMILY_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SHORT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 /-]*$")
HISTORY_DATASET_RE = re.compile(r"^[a-z0-9]+_funding_history$")
RULING_ID_RE = re.compile(r"^R-DEC-FAM-[A-Z0-9]+(-[A-Z0-9]+)+$")
SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MEMBER_ID_RE = re.compile(r"^(P-1|R-1|P-1R):[0-9]{4}[A-Z]+:[A-Z0-9]+:[A-Z0-9]+$")

_ISO_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EDITION_RE = re.compile(r"^[0-9]{4}$")
_POSITIVE_RE = re.compile(r"^[1-9][0-9]*$")
_TITLE_ITEM_RE = re.compile(r"^([0-9]{4}): (.+)$")
_QUANTITY_ROW_RE = re.compile(r"^[A-Z]$")
_JBOOK_ANCHOR_RE = re.compile(
    r"^doc:[0-9a-f]{64}#p[1-9][0-9]*;xml=[^;]+;units=(Thousands|Millions)$")

# The inverse of era_map.ERA_ORG_TO_MODERN: a modern spelling -> its era spelling.
_MODERN_TO_ERA = {modern: era for era, modern in era_map.ERA_ORG_TO_MODERN.items()}

# Member columns by how Member.from_row parses them.
_INT_COLUMNS = frozenset({"valid_from_edition", "valid_to_edition",
                          "coverage_expected_from_edition", "expected_next_edition",
                          "member_order"})
_LIST_COLUMNS = ("budget_activities", "era_decision_ids", "variant_ids", "services_using",
                 "allocation_years")
_REF_COLUMNS = ("evidence", "link_evidence")
_BOOL_COLUMNS = ("quantity_bearing", "msar_shared_flag")
_REQUIRED_MEMBER_COLUMNS = ("platform_family", "member_id", "exhibit", "account", "organization",
                            "code", "role", "verdict", "appropriation", "display_title")
_ALWAYS_VOCABULARY = (("role", ROLES), ("verdict", VERDICTS), ("exhibit", EXHIBITS),
                      ("appropriation", APPROPRIATIONS))
_OPTIONAL_VOCABULARY = (("purpose", PURPOSES), ("variant_scope", VARIANT_SCOPES),
                        ("link_basis", LINK_BASES),
                        ("contract_link_policy", CONTRACT_LINK_POLICIES),
                        ("paying_org", PAYING_ORGS))


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class RegistryError(ValueError):
    """Every stage-1 fault at once, one 'platform-families: …' line each."""

    def __init__(self, errors: Sequence[str]):
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


@dataclass(frozen=True)
class Ruling:
    ruling_id: str
    kind: str
    platform_family: str
    decided_by: str
    decided_on: str
    owner_reply: str
    spec: str
    text: str
    seed_basis: bool


@dataclass(frozen=True)
class Source:
    source_id: str
    title: str
    publisher: str
    url: str
    as_of: str
    sha256: str | None
    bytes: int | None
    archived: bool
    archive_path: str | None
    tier: str
    verified_by: tuple[str, ...]


def split_refs(text: str) -> tuple[str, ...]:
    """A ';'-list of typed evidence refs (§7.5). A `q=` segment belongs to the
    `doc:` ref before it (a quote is the last part of a doc ref), so it is
    re-attached; prefixes are not validated here."""
    if text == "":
        return ()
    refs: list[str] = []
    for seg in text.split(";"):
        if seg.startswith("q="):
            if refs and refs[-1].startswith("doc:") and ";q=" not in refs[-1]:
                refs[-1] = f"{refs[-1]};{seg}"
                continue
            raise ValueError("dangling q=")
        if seg == "":
            raise ValueError("empty list item")
        refs.append(seg)
    return tuple(refs)


def _parse_int(text: str) -> int | None:
    if text == "":
        return None
    if not (text.isascii() and text.isdigit() and str(int(text)) == text):
        raise ValueError(f"not an integer: {text!r}")
    return int(text)


def _parse_list(text: str) -> tuple[str, ...]:
    if text == "":
        return ()
    items = tuple(text.split(";"))
    if "" in items:
        raise ValueError(f"empty list item in {text!r}")
    return items


def _parse_bool(text: str) -> bool | None:
    if text == "":
        return None
    if text not in ("true", "false"):
        raise ValueError(f"not 'true' or 'false': {text!r}")
    return text == "true"


def _parse_titles(text: str) -> tuple[tuple[int, str], ...]:
    if text == "":
        return ()
    out = []
    for item in text.split("; "):
        m = _TITLE_ITEM_RE.fullmatch(item)
        if not m:
            raise ValueError(f"titles_seen item {item!r} is not '<edition>: <title>'")
        out.append((int(m.group(1)), m.group(2)))
    return tuple(out)


@dataclass(frozen=True)
class Member:
    """One row of platform_family_members.csv, one field per MEMBER_COLUMNS name."""

    member_row_id: str
    platform_family: str
    member_id: str
    exhibit: str
    account: str
    organization: str
    code: str
    role: str
    verdict: str
    project_number: str
    appropriation: str
    budget_activities: tuple[str, ...]
    titles_seen: tuple[tuple[int, str], ...]
    display_title: str
    page_slug: str
    valid_from_edition: int | None
    valid_to_edition: int | None
    coverage_expected_from_edition: int | None
    expected_next_edition: int | None
    era_decision_ids: tuple[str, ...]
    drift_sha256: str
    member_order: int | None
    program_tag: str
    purpose_tag: str
    purpose: str
    variant_ids: tuple[str, ...]
    variant_scope: str
    scope_note: str
    services_using: tuple[str, ...]
    paying_org: str
    predecessor_member_id: str
    successor_member_id: str
    link_basis: str
    link_evidence: tuple[str, ...]
    evidence: tuple[str, ...]
    quantity_bearing: bool | None
    quantity_row: str
    quantity_notes: str
    jbook_anchor: str
    contract_link_policy: str
    msar_account: str
    msar_funding_source_page: str
    msar_shared_flag: bool | None
    allocation_source: str
    allocation_years: tuple[str, ...]
    decided_by: str
    ruling_id: str
    decided_on: str
    note: str

    @classmethod
    def from_row(cls, row: Mapping[str, str]) -> Member:
        """Parse a row over MEMBER_COLUMNS; ValueError on an unparsable value."""
        values: dict[str, object] = {}
        for col in MEMBER_COLUMNS:
            if col not in row:
                raise ValueError(f"missing column {col!r}")
            text = row[col]
            if not isinstance(text, str):
                raise ValueError(f"{col} must be a string, got {text!r}")
            if col in _INT_COLUMNS:
                values[col] = _parse_int(text)
            elif col in _LIST_COLUMNS:
                values[col] = _parse_list(text)
            elif col in _REF_COLUMNS:
                values[col] = split_refs(text)
            elif col in _BOOL_COLUMNS:
                values[col] = _parse_bool(text)
            elif col == "titles_seen":
                values[col] = _parse_titles(text)
            else:
                values[col] = text
        return cls(**values)

    def title_for(self, edition: int) -> str | None:
        return dict(self.titles_seen).get(edition)

    def as_row(self) -> dict[str, str]:
        """The exact inverse of from_row for every row stage 1 accepts."""
        row: dict[str, str] = {}
        for col in MEMBER_COLUMNS:
            value = getattr(self, col)
            if col == "titles_seen":
                row[col] = "; ".join(f"{e}: {t}" for e, t in value)
            elif col in _LIST_COLUMNS or col in _REF_COLUMNS:
                row[col] = ";".join(value)
            elif value is None:
                row[col] = ""
            elif isinstance(value, bool):
                row[col] = "true" if value else "false"
            else:
                row[col] = str(value)
        return row


@dataclass(frozen=True)
class EraLine:
    platform_family: str
    member_id: str
    edition: int
    era_key: str
    budget_activity: str
    filed_title: str
    decision_id: str

    def as_row(self) -> dict[str, str]:
        return {"platform_family": self.platform_family, "member_id": self.member_id,
                "edition": str(self.edition), "era_key": self.era_key,
                "budget_activity": self.budget_activity, "filed_title": self.filed_title,
                "decision_id": self.decision_id}


@dataclass(frozen=True)
class Headline:
    measure: str
    first_fy: int
    last_fy: int


@dataclass(frozen=True)
class ReviewGuard:
    exhibits: tuple[str, ...]
    title_substrings: tuple[str, ...]


@dataclass(frozen=True)
class ProgramNote:
    note: str
    note_fact_id: str
    expected_receipt: Mapping[str, object]


def _counted_order(member: Member) -> tuple[bool, int]:
    return (member.member_order is None, member.member_order or 0)


@dataclass(frozen=True)
class Family:
    """A family object of platform_families.json plus its CSV rows."""

    platform_family: str
    status: str
    published_ruling_id: str | None
    short_name: str
    history_dataset: str
    on_partial_corpus: str
    headline: Headline
    scope_note: str
    coverage_notes: tuple[str, ...]
    review_guard: ReviewGuard
    program_notes: Mapping[str, ProgramNote]
    variants: tuple[Mapping[str, str], ...]
    program_tags: tuple[Mapping[str, str | None], ...]
    purpose_tags: tuple[str, ...]
    caveat_ids: tuple[str, ...]
    exclusions: tuple[Mapping[str, object], ...]
    aliases: tuple[str, ...]
    contract_routes: Mapping[str, object] | None
    official_estimates: Mapping[str, object] | None
    art: Mapping[str, object] | None
    members: tuple[Member, ...]
    era_lines: tuple[EraLine, ...]

    @property
    def counted(self) -> tuple[Member, ...]:
        """Approved counted rows in member_order."""
        return tuple(sorted((m for m in self.members if m.verdict == "approved" and m.role == "counted"),
                            key=_counted_order))

    @property
    def code_keyed(self) -> tuple[Member, ...]:
        """D5: the counted rows with code-keyed lake rows (a non-empty titles_seen)."""
        return tuple(m for m in self.counted if m.titles_seen)

    @property
    def context(self) -> tuple[Member, ...]:
        """Approved context rows by member_id."""
        return tuple(sorted((m for m in self.members if m.verdict == "approved" and m.role == "context"),
                            key=lambda m: m.member_id))

    @property
    def route(self) -> str:
        return f"/families/{self.platform_family}/"

    @property
    def history_path(self) -> str:
        return f"json/{self.history_dataset}.json"


@dataclass(frozen=True)
class Registry:
    schema_version: int
    rulings: Mapping[str, Ruling]
    sources: Mapping[str, Source]
    families: tuple[Family, ...]
    doc: dict

    def __getitem__(self, platform_family: str) -> Family:
        for fam in self.families:
            if fam.platform_family == platform_family:
                return fam
        raise KeyError(platform_family)

    def published(self) -> tuple[Family, ...]:
        return tuple(f for f in self.families if f.status == "published")


# ---------------------------------------------------------------------------
# Stage 1 (spec §9.1): the JSON
# ---------------------------------------------------------------------------

_STRS = "a list of strings"
_STR_OR_NULL = "a string or null"
_OBJ_OR_NULL = "an object or null"
_TYPE_WORDS = {str: "a string", bool: "a boolean", int: "an integer", list: "a list",
               dict: "an object"}

_RULING_TYPES = {"ruling_id": str, "kind": str, "platform_family": str, "decided_by": str,
                 "decided_on": str, "owner_reply": str, "spec": str, "text": str,
                 "seed_basis": bool}
_SOURCE_TYPES = {"source_id": str, "title": str, "publisher": str, "url": str, "as_of": str,
                 "sha256": str, "bytes": int, "archived": bool, "archive_path": str, "tier": str,
                 "verified_by": _STRS}
_FAMILY_TYPES = {"platform_family": str, "status": str, "published_ruling_id": str,
                 "short_name": str, "history_dataset": str, "on_partial_corpus": str,
                 "headline": dict, "scope_note": str, "coverage_notes": _STRS,
                 "review_guard": dict, "program_notes": dict, "variants": list,
                 "program_tags": list, "purpose_tags": _STRS, "caveat_ids": _STRS,
                 "exclusions": list, "aliases": _STRS, "contract_routes": _OBJ_OR_NULL,
                 "official_estimates": _OBJ_OR_NULL, "art": _OBJ_OR_NULL}
_HEADLINE_TYPES = {"measure": str, "first_fy": int, "last_fy": int}
_GUARD_TYPES = {"exhibits": _STRS, "title_substrings": _STRS}
_PROGRAM_NOTE_TYPES = {"note": str, "note_fact_id": str, "expected_receipt": dict}
_RECEIPT_TYPES = {"kind": str, "page_number": int, "pe_bli": str, "sha256": str}
_VARIANT_TYPES = {"id": str, "note": str}
_PROGRAM_TAG_TYPES = {"tag": str, "mdap_code": _STR_OR_NULL}
_EXCLUSION_TYPES = {"exclusion_id": str, "kind": str, "label": str, "size_text": str,
                    "evidence": _STRS}
_CONTRACT_ROUTE_TYPES = {"program_codes": _STRS, "description_pattern": str,
                         "description_exclusions": _STRS, "basis": str}
_OFFICIAL_ESTIMATE_TYPES = {"msar_program_number": _STR_OR_NULL, "msar_source_ids": _STRS,
                            "gao_program_key": _STR_OR_NULL, "wsaa_exit_ruling": _STR_OR_NULL}
_ART_TYPES = {"src": str, "alt": str, "caption": str, "generated": bool}

_Add = Callable[[str], None]


def _has_type(value: object, kind: object) -> bool:
    if kind is int:
        return type(value) is int          # never a bool
    if kind is bool:
        return type(value) is bool         # never an int
    if kind == _STRS:
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    if kind == _STR_OR_NULL:
        return value is None or isinstance(value, str)
    if kind == _OBJ_OR_NULL:
        return value is None or isinstance(value, dict)
    return isinstance(value, kind)


def _check_shape(obj: object, keys: Sequence[str], types: Mapping[str, object], add: _Add, *,
                 label: str = "", optional: frozenset[str] = frozenset()) -> bool:
    """Exact keys (required = all but `optional`) and JSON types. False when
    `obj` is not an object at all."""
    prefix = f"{label}: " if label else ""
    if not isinstance(obj, dict):
        add(f"{label or 'entry'} must be an object, got {obj!r}")
        return False
    for key in obj:
        if key not in keys:
            add(f"{prefix}unknown key {key!r}")
    for key in keys:
        if key not in obj:
            if key not in optional:
                add(f"{prefix}missing key {key!r}")
        elif not _has_type(obj[key], types[key]):
            word = types[key] if isinstance(types[key], str) else _TYPE_WORDS[types[key]]
            add(f"{prefix}{key} must be {word}, got {obj[key]!r}")
    return True


def _iso_date(value: object) -> bool:
    if not isinstance(value, str) or not _ISO_DATE_RE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _entry_id(obj: object, key: str, fallback: str) -> str:
    value = obj.get(key) if isinstance(obj, Mapping) else None
    return value if isinstance(value, str) else fallback


def _strs(obj: Mapping, key: str) -> list[str]:
    """The value as a list of strings, or [] when it is anything else."""
    value = obj.get(key)
    return value if _has_type(value, _STRS) else []


def _objects(obj: Mapping, key: str) -> list[dict]:
    value = obj.get(key)
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def _check_unique(seen: set, value: object, key: str, add: _Add) -> None:
    if not isinstance(value, str):
        return
    if value in seen:
        add(f"duplicate {key} {value!r}")
    seen.add(value)


def _check_rulings(rulings: list, add_at: Callable[[str, str], None]) -> None:
    seen: set[str] = set()
    for i, r in enumerate(rulings):
        rid = _entry_id(r, "ruling_id", f"rulings[{i}]")

        def add(reason: str, rid: str = rid) -> None:
            add_at(rid, reason)

        if not _check_shape(r, RULING_KEYS, _RULING_TYPES, add):
            continue
        ruling_id = r.get("ruling_id")
        if isinstance(ruling_id, str) and not RULING_ID_RE.fullmatch(ruling_id):
            add(f"ruling_id {ruling_id!r} does not match {RULING_ID_RE.pattern}")
        _check_unique(seen, ruling_id, "ruling_id", add)
        kind = r.get("kind")
        if isinstance(kind, str) and kind not in RULING_KINDS:
            add(f"kind {kind!r} is not one of {', '.join(RULING_KINDS)}")
        decided_by = r.get("decided_by")
        if isinstance(decided_by, str) and decided_by != "owner":
            add(f"decided_by {decided_by!r} must be 'owner'")
        reply = r.get("owner_reply")
        if isinstance(reply, str) and not reply.strip():
            add(f"owner_reply {reply!r} is blank")
        if isinstance(r.get("decided_on"), str) and not _iso_date(r["decided_on"]):
            add(f"decided_on {r['decided_on']!r} is not an ISO date (YYYY-MM-DD)")
        if r.get("seed_basis") is True and ruling_id not in SEED_BASIS_ALLOWED:
            add(f"seed_basis true is allowed only on {', '.join(sorted(SEED_BASIS_ALLOWED))}, "
                f"not on {ruling_id!r}")


def _check_sources(sources: list, add_at: Callable[[str, str], None]) -> None:
    seen: set[str] = set()
    optional = frozenset({"sha256", "bytes", "archive_path", "verified_by"})
    for i, s in enumerate(sources):
        sid = _entry_id(s, "source_id", f"sources[{i}]")

        def add(reason: str, sid: str = sid) -> None:
            add_at(sid, reason)

        if not _check_shape(s, SOURCE_KEYS, _SOURCE_TYPES, add, optional=optional):
            continue
        source_id = s.get("source_id")
        if isinstance(source_id, str) and not SOURCE_ID_RE.fullmatch(source_id):
            add(f"source_id {source_id!r} does not match {SOURCE_ID_RE.pattern}")
        _check_unique(seen, source_id, "source_id", add)
        tier = s.get("tier")
        if isinstance(tier, str) and tier not in SOURCE_TIERS:
            add(f"tier {tier!r} is not one of {', '.join(SOURCE_TIERS)}")
        sha = s.get("sha256")
        if isinstance(sha, str) and not _SHA256_RE.fullmatch(sha):
            add(f"sha256 {sha!r} is not 64 lower-case hex")
        if isinstance(s.get("as_of"), str) and not _iso_date(s["as_of"]):
            add(f"as_of {s['as_of']!r} is not an ISO date (YYYY-MM-DD)")
        if s.get("archived") is True and not s.get("archive_path"):
            add(f"archive_path is required when archived is true (got {s.get('archive_path')!r})")


def _check_family_fields(fam: dict, add: _Add) -> None:
    """Rule 1 for the family's nested objects and lists, rules 5, 18 (the
    vocabularies' own duplicates), 26 and 27."""
    status = fam.get("status")
    if isinstance(status, str) and status not in STATUSES:
        add(f"status {status!r} is not one of {', '.join(STATUSES)}")
    opc = fam.get("on_partial_corpus")
    if isinstance(opc, str) and opc not in ON_PARTIAL_CORPUS:
        add(f"on_partial_corpus {opc!r} is not one of {', '.join(ON_PARTIAL_CORPUS)}")
    for caveat in _strs(fam, "caveat_ids"):
        if caveat not in CAVEAT_IDS:
            add(f"caveat_ids item {caveat!r} is not one of {', '.join(CAVEAT_IDS)}")

    headline = fam.get("headline")
    if isinstance(headline, dict) and _check_shape(headline, HEADLINE_KEYS, _HEADLINE_TYPES, add,
                                                   label="headline"):
        measure = headline.get("measure")
        if isinstance(measure, str) and measure not in HEADLINE_MEASURES:
            add(f"headline measure {measure!r} is not one of {', '.join(HEADLINE_MEASURES)}")
        first, last = headline.get("first_fy"), headline.get("last_fy")
        if type(first) is int and type(last) is int and first > last:
            add(f"headline first_fy {first!r} is after last_fy {last!r}")

    guard = fam.get("review_guard")
    if isinstance(guard, dict) and _check_shape(guard, GUARD_KEYS, _GUARD_TYPES, add,
                                                label="review_guard"):
        subs = guard.get("title_substrings")
        if _has_type(subs, _STRS):
            if not subs:
                add("review_guard title_substrings [] is empty")
            for sub in subs:
                if sub == "" or sub != sub.upper():
                    add(f"review_guard title_substrings item {sub!r} is not a non-empty "
                        "upper-case string")
        exhibits = guard.get("exhibits")
        if _has_type(exhibits, _STRS) and (not exhibits or not set(exhibits) <= set(GUARD_EXHIBITS)):
            add(f"review_guard exhibits {exhibits!r} must be a non-empty subset of "
                f"{', '.join(GUARD_EXHIBITS)}")

    notes = fam.get("program_notes")
    if isinstance(notes, dict):
        for member_id, note in notes.items():
            label = f"program_notes[{member_id!r}]"
            if _check_shape(note, PROGRAM_NOTE_KEYS, _PROGRAM_NOTE_TYPES, add, label=label):
                receipt = note.get("expected_receipt")
                if isinstance(receipt, dict):
                    _check_shape(receipt, RECEIPT_KEYS, _RECEIPT_TYPES, add,
                                 label=f"{label}.expected_receipt")

    for key, keys, types, optional in (
            ("variants", VARIANT_KEYS, _VARIANT_TYPES, frozenset({"note"})),
            ("program_tags", PROGRAM_TAG_KEYS, _PROGRAM_TAG_TYPES, frozenset()),
            ("exclusions", EXCLUSION_KEYS, _EXCLUSION_TYPES, frozenset())):
        items = fam.get(key)
        if isinstance(items, list):
            for j, item in enumerate(items):
                _check_shape(item, keys, types, add, label=f"{key}[{j}]", optional=optional)

    seen_exclusions: set[str] = set()
    for j, exclusion in enumerate(_objects(fam, "exclusions")):
        kind = exclusion.get("kind")
        if isinstance(kind, str) and kind not in EXCLUSION_KINDS:
            add(f"exclusions[{j}] kind {kind!r} is not one of {', '.join(EXCLUSION_KINDS)}")
        _check_unique(seen_exclusions, exclusion.get("exclusion_id"), "exclusion_id", add)

    seen_variants: set[str] = set()
    for variant in _objects(fam, "variants"):
        _check_unique(seen_variants, variant.get("id"), "variants id", add)
    seen_tags: set[str] = set()
    for tag in _objects(fam, "program_tags"):
        _check_unique(seen_tags, tag.get("tag"), "program_tags tag", add)
    seen_purposes: set[str] = set()
    for purpose_tag in _strs(fam, "purpose_tags"):
        _check_unique(seen_purposes, purpose_tag, "purpose_tags item", add)

    for key, keys, types in (("contract_routes", CONTRACT_ROUTE_KEYS, _CONTRACT_ROUTE_TYPES),
                             ("official_estimates", OFFICIAL_ESTIMATE_KEYS, _OFFICIAL_ESTIMATE_TYPES),
                             ("art", ART_KEYS, _ART_TYPES)):
        if isinstance(fam.get(key), dict):
            _check_shape(fam[key], keys, types, add, label=key)
    routes = fam.get("contract_routes")
    if isinstance(routes, dict) and isinstance(routes.get("basis"), str) \
            and routes["basis"] not in CONTRACT_ROUTE_BASES:
        add(f"contract_routes basis {routes['basis']!r} is not one of {', '.join(CONTRACT_ROUTE_BASES)}")
    art = fam.get("art")
    if isinstance(art, dict) and art.get("generated") is True and (
            not isinstance(art.get("caption"), str) or "AI-generated" not in art["caption"]):
        add(f"art generated true needs a caption containing 'AI-generated' (caption {art.get('caption')!r})")


def _check_families(families: list, add_at: Callable[[str, str], None]) -> dict[str, dict]:
    """Rules 1–5, 18 (family side), 26, 27. Returns the well-formed family
    objects by platform_family (first occurrence) for the row checks."""
    by_id: dict[str, dict] = {}
    seen = {"platform_family": set(), "short_name": set(), "history_dataset": set()}
    patterns = {"platform_family": PLATFORM_FAMILY_RE, "short_name": SHORT_NAME_RE,
                "history_dataset": HISTORY_DATASET_RE}
    for i, fam in enumerate(families):
        pf = _entry_id(fam, "platform_family", f"families[{i}]")

        def add(reason: str, pf: str = pf) -> None:
            add_at(pf, reason)

        if not _check_shape(fam, FAMILY_KEYS, _FAMILY_TYPES, add,
                            optional=frozenset({"published_ruling_id"})):
            continue
        for key, pattern in patterns.items():
            value = fam.get(key)
            if isinstance(value, str) and not pattern.fullmatch(value):
                add(f"{key} {value!r} does not match {pattern.pattern}")
            _check_unique(seen[key], value, key, add)
        _check_family_fields(fam, add)
        if isinstance(fam.get("platform_family"), str):
            by_id.setdefault(fam["platform_family"], fam)
    return by_id


def _check_doc(doc: object, add_at: Callable[[str | None, str], None]) -> dict[str, dict]:
    if not isinstance(doc, dict):
        add_at(None, f"the top level must be a JSON object, got {type(doc).__name__}")
        return {}
    for key in doc:
        if key not in TOP_KEYS:
            add_at(None, f"unknown key {key!r}")
    for key in TOP_KEYS:
        if key not in doc:
            add_at(None, f"missing key {key!r}")
    if "schema_version" in doc and not (type(doc["schema_version"]) is int and doc["schema_version"] == 1):
        add_at(None, f"schema_version must be 1, got {doc['schema_version']!r}")
    for key in ("rulings", "sources", "families"):
        if key in doc and not isinstance(doc[key], list):
            add_at(None, f"{key} must be a list, got {doc[key]!r}")
    if isinstance(doc.get("rulings"), list):
        _check_rulings(doc["rulings"], add_at)
    if isinstance(doc.get("sources"), list):
        _check_sources(doc["sources"], add_at)
    if isinstance(doc.get("families"), list):
        return _check_families(doc["families"], add_at)
    return {}


# ---------------------------------------------------------------------------
# Stage 1 (spec §9.1): the CSV rows
# ---------------------------------------------------------------------------


def _row_columns(row: Mapping, columns: Sequence[str], add: _Add) -> bool:
    """Rule 8: exactly the frozen columns, in order, every value a string."""
    keys = tuple(row.keys())
    if keys != tuple(columns):
        missing = [c for c in columns if c not in row]
        extra = [k for k in keys if k not in columns]
        detail = "; ".join(filter(None, (
            f"missing {', '.join(map(repr, missing))}" if missing else "",
            f"unexpected {', '.join(map(repr, extra))}" if extra else ""))) or "out of order"
        add(f"columns are not the frozen {len(columns)}-column header ({detail})")
        return False
    bad = [(k, v) for k, v in row.items() if not isinstance(v, str)]
    for key, value in bad:
        add(f"column {key} must be a string, got {value!r}")
    return not bad


def _check_editions(row: Mapping[str, str], add: _Add) -> None:
    """Rule 12."""
    bounds: dict[str, int] = {}
    for col in ("valid_from_edition", "valid_to_edition"):
        text = row[col]
        if not _EDITION_RE.fullmatch(text) or int(text) not in EDITIONS:
            add(f"{col} {text!r} is not an edition in {EDITIONS[0]}–{EDITIONS[-1]}")
        else:
            bounds[col] = int(text)
    frm, to = bounds.get("valid_from_edition"), bounds.get("valid_to_edition")
    span = frm is not None and to is not None
    if span and frm > to:
        add(f"valid_from_edition {frm!r} is after valid_to_edition {to!r}")
    cov = row["coverage_expected_from_edition"]
    if cov:
        if not _EDITION_RE.fullmatch(cov):
            add(f"coverage_expected_from_edition {cov!r} is not a 4-digit edition")
        elif span and not frm <= int(cov) <= to:
            add(f"coverage_expected_from_edition {cov!r} is outside [{frm}, {to}]")
    nxt = row["expected_next_edition"]
    if nxt:
        if not _EDITION_RE.fullmatch(nxt):
            add(f"expected_next_edition {nxt!r} is not a 4-digit edition")
        elif to is not None and int(nxt) <= to:
            add(f"expected_next_edition {nxt!r} is not after valid_to_edition {to!r}")
    order = row["member_order"]
    if order and not _POSITIVE_RE.fullmatch(order):
        add(f"member_order {order!r} is not a positive integer")
    titles = row["titles_seen"]
    if titles:
        prev = None
        for item in titles.split("; "):
            m = _TITLE_ITEM_RE.fullmatch(item)
            if not m:
                add(f"titles_seen item {item!r} is not '<edition>: <title>'")
                break
            edition = int(m.group(1))
            if prev is not None and edition <= prev:
                add(f"titles_seen {titles!r}: editions are not strictly ascending ({prev} then {edition})")
                break
            if span and not frm <= edition <= to:
                add(f"titles_seen {titles!r}: edition {edition} is outside [{frm}, {to}]")
                break
            prev = edition


def _check_member_values(row: Mapping[str, str], add: _Add) -> None:
    """Rules 10 and 11."""
    member_id = row["member_id"]
    if not MEMBER_ID_RE.fullmatch(member_id):
        add(f"member_id {member_id!r} does not match {MEMBER_ID_RE.pattern}")
    else:
        for col, part in zip(("exhibit", "account", "organization", "code"), member_id.split(":")):
            if row[col] != part:
                add(f"{col} {row[col]!r} disagrees with member_id {member_id!r} ({part!r})")
    org = row["organization"]
    if org in _MODERN_TO_ERA:
        add(f"organization {org!r} is a modern spelling; the member uses the era spelling "
            f"{_MODERN_TO_ERA[org]!r}")

    for col in _REQUIRED_MEMBER_COLUMNS:
        if row[col] == "":
            add(f"{col} is required (got '')")
    for col, vocab in _ALWAYS_VOCABULARY + _OPTIONAL_VOCABULARY:
        if row[col] != "" and row[col] not in vocab:
            add(f"{col} {row[col]!r} is not one of {', '.join(vocab)}")
    if row["purpose"] == "" and row["page_slug"] != "":
        add(f"purpose is blank but page_slug {row['page_slug']!r} is set")
    if row["exhibit"] == "P-1R" and row["role"] != "context":
        add(f"exhibit 'P-1R' is allowed only with role 'context', not {row['role']!r}")

    for col in _LIST_COLUMNS:
        if row[col] and "" in row[col].split(";"):
            add(f"{col} {row[col]!r} has an empty list item")
    for item in filter(None, row["services_using"].split(";")):
        if item not in SERVICES:
            add(f"services_using item {item!r} is not one of {', '.join(SERVICES)}")
    for item in filter(None, row["allocation_years"].split(";")):
        if not _EDITION_RE.fullmatch(item):
            add(f"allocation_years item {item!r} is not a 4-digit year")
    for col in _REF_COLUMNS:
        try:
            split_refs(row[col])
        except ValueError as exc:
            add(f"{col} {row[col]!r}: {exc}")
    for col in _BOOL_COLUMNS:
        if row[col] not in ("", "true", "false"):
            add(f"{col} {row[col]!r} must be blank, 'true' or 'false'")

    drift = row["drift_sha256"]
    if drift == "":
        if row["verdict"] == "approved":
            add("drift_sha256 is required on an approved row (got '')")
    elif not _SHA256_RE.fullmatch(drift):
        add(f"drift_sha256 {drift!r} is not 64 lower-case hex")
    if row["quantity_row"] and not _QUANTITY_ROW_RE.fullmatch(row["quantity_row"]):
        add(f"quantity_row {row['quantity_row']!r} is not one upper-case letter")
    page = row["msar_funding_source_page"]
    if page and not _POSITIVE_RE.fullmatch(page):
        add(f"msar_funding_source_page {page!r} is not a positive integer")
    anchor = row["jbook_anchor"]
    if anchor and not _JBOOK_ANCHOR_RE.fullmatch(anchor):
        add(f"jbook_anchor {anchor!r} does not match {_JBOOK_ANCHOR_RE.pattern}")


def _check_role_rules(row: Mapping[str, str], add: _Add) -> None:
    """Rule 17."""
    role = row["role"]
    if role == "project_slice" and not row["project_number"]:
        add("project_number is required on a project_slice row (got '')")
    if role != "project_slice" and row["project_number"]:
        add(f"project_number {row['project_number']!r} is allowed only on a project_slice row, "
            f"not role {role!r}")
    if row["variant_scope"] == "shared" and not row["scope_note"]:
        add("scope_note is required on a shared row (got '')")
    elif role == "context" and not row["scope_note"]:
        add("scope_note is required on a context row (got '')")
    if role == "context":
        for col in ("coverage_expected_from_edition", "member_order"):
            if row[col]:
                add(f"{col} {row[col]!r} is not allowed on a context row")
    else:
        for col in ("allocation_source", "allocation_years"):
            if row[col]:
                add(f"{col} {row[col]!r} is allowed only on a context row, not role {role!r}")
    if role != "counted":
        for col in ("quantity_bearing", "quantity_row", "quantity_notes"):
            if row[col]:
                add(f"{col} {row[col]!r} is allowed only on a counted row, not role {role!r}")


def _check_tags(row: Mapping[str, str], fam: Mapping, add: _Add) -> None:
    """Rule 18 (row side): tags and variants from the family's own lists."""
    pf = row["platform_family"]
    variant_ids = {v.get("id") for v in _objects(fam, "variants")}
    for item in filter(None, row["variant_ids"].split(";")):
        if item not in variant_ids:
            add(f"variant_ids item {item!r} is not a variants id of {pf!r}")
    tag = row["program_tag"]
    if tag and tag not in {t.get("tag") for t in _objects(fam, "program_tags")}:
        add(f"program_tag {tag!r} is not in the program_tags of {pf!r}")
    purpose_tag = row["purpose_tag"]
    if purpose_tag and purpose_tag not in _strs(fam, "purpose_tags"):
        add(f"purpose_tag {purpose_tag!r} is not in the purpose_tags of {pf!r}")


def _check_members(rows: Sequence[Mapping[str, str]], families: Mapping[str, dict],
                   add_at: Callable[[str, str], None]) -> None:
    seen: set[str] = set()
    for i, row in enumerate(rows):
        # The row id is member_row_id as written; without one, the row's line
        # in the CSV (the header is line 1).
        rid = _entry_id(row, "member_row_id", "") or f"line {i + 2}"

        def add(reason: str, rid: str = rid) -> None:
            add_at(rid, reason)

        if not isinstance(row, Mapping):
            add(f"row must be a mapping of the frozen columns, got {row!r}")
            continue
        if not _row_columns(row, MEMBER_COLUMNS, add):
            continue
        expected = (f"{row['platform_family']}|{row['member_id']}|"
                    f"{row['valid_from_edition']}-{row['valid_to_edition']}")
        if row["member_row_id"] != expected:
            add(f"member_row_id {row['member_row_id']!r} is not {expected!r} "
                "(platform_family|member_id|valid_from_edition-valid_to_edition)")
        _check_unique(seen, row["member_row_id"], "member_row_id", add)
        _check_member_values(row, add)
        _check_editions(row, add)
        _check_role_rules(row, add)
        fam = families.get(row["platform_family"])
        if fam is not None:
            _check_tags(row, fam, add)


def _check_era_rows(rows: Sequence[Mapping[str, str]], add_at: Callable[[str, str], None]) -> None:
    for i, row in enumerate(rows):
        parts = [row.get(k) for k in ("platform_family", "edition", "era_key")] \
            if isinstance(row, Mapping) else []
        rid = "|".join(parts) if parts and all(isinstance(p, str) for p in parts) else f"line {i + 2}"

        def add(reason: str, rid: str = rid) -> None:
            add_at(rid, reason)

        if not isinstance(row, Mapping):
            add(f"row must be a mapping of the frozen columns, got {row!r}")
            continue
        if not _row_columns(row, ERA_LINE_COLUMNS, add):
            continue
        edition = row["edition"]
        if not _EDITION_RE.fullmatch(edition) or int(edition) not in EDITIONS:
            add(f"edition {edition!r} is not an edition in {EDITIONS[0]}–{EDITIONS[-1]}")


# ---------------------------------------------------------------------------
# parse / load
# ---------------------------------------------------------------------------


def _line(file: str, row: str | None, reason: str) -> str:
    return f"platform-families: {file}:{row}: {reason}" if row is not None \
        else f"platform-families: {file}: {reason}"


def _family(fam: dict, members: Sequence[Member], era_lines: Sequence[EraLine]) -> Family:
    headline, guard = fam["headline"], fam["review_guard"]
    return Family(
        platform_family=fam["platform_family"], status=fam["status"],
        published_ruling_id=fam.get("published_ruling_id"), short_name=fam["short_name"],
        history_dataset=fam["history_dataset"], on_partial_corpus=fam["on_partial_corpus"],
        headline=Headline(headline["measure"], headline["first_fy"], headline["last_fy"]),
        scope_note=fam["scope_note"], coverage_notes=tuple(fam["coverage_notes"]),
        review_guard=ReviewGuard(tuple(guard["exhibits"]), tuple(guard["title_substrings"])),
        program_notes={mid: ProgramNote(n["note"], n["note_fact_id"], dict(n["expected_receipt"]))
                       for mid, n in fam["program_notes"].items()},
        variants=tuple(dict(v) for v in fam["variants"]),
        program_tags=tuple(dict(t) for t in fam["program_tags"]),
        purpose_tags=tuple(fam["purpose_tags"]), caveat_ids=tuple(fam["caveat_ids"]),
        exclusions=tuple(copy.deepcopy(e) for e in fam["exclusions"]),
        aliases=tuple(fam["aliases"]),
        contract_routes=copy.deepcopy(fam["contract_routes"]),
        official_estimates=copy.deepcopy(fam["official_estimates"]),
        art=copy.deepcopy(fam["art"]),
        members=tuple(members), era_lines=tuple(era_lines))


def _era_line(row: Mapping[str, str]) -> EraLine:
    return EraLine(row["platform_family"], row["member_id"], int(row["edition"]), row["era_key"],
                   row["budget_activity"], row["filed_title"], row["decision_id"])


def parse_registry(doc: dict, member_rows: Sequence[Mapping[str, str]],
                   era_rows: Sequence[Mapping[str, str]], *,
                   era_decisions: Mapping[str, Mapping[str, str]],
                   paths: RegistryPaths = DEFAULT_PATHS) -> Registry:
    """Stage 1 on in-memory files (pure): collect every fault, then raise one
    RegistryError; otherwise build the Registry. `era_decisions` is the era
    seed keyed by decision_id."""
    errors: list[str] = []
    json_name, members_name, era_name = paths.json.name, paths.members.name, paths.era_lines.name
    families = _check_doc(doc, lambda row, reason: errors.append(_line(json_name, row, reason)))
    _check_members(member_rows, families,
                   lambda row, reason: errors.append(_line(members_name, row, reason)))
    _check_era_rows(era_rows, lambda row, reason: errors.append(_line(era_name, row, reason)))
    if errors:
        raise RegistryError(errors)

    members: dict[str, list[Member]] = defaultdict(list)
    for row in member_rows:
        members[row["platform_family"]].append(Member.from_row(row))
    era_lines: dict[str, list[EraLine]] = defaultdict(list)
    for row in era_rows:
        era_lines[row["platform_family"]].append(_era_line(row))
    sources = {}
    for s in doc["sources"]:
        sources[s["source_id"]] = Source(
            source_id=s["source_id"], title=s["title"], publisher=s["publisher"], url=s["url"],
            as_of=s["as_of"], sha256=s.get("sha256"), bytes=s.get("bytes"), archived=s["archived"],
            archive_path=s.get("archive_path"), tier=s["tier"],
            verified_by=tuple(s.get("verified_by", ())))
    return Registry(
        schema_version=doc["schema_version"],
        rulings={r["ruling_id"]: Ruling(**{k: r[k] for k in RULING_KEYS}) for r in doc["rulings"]},
        sources=sources,
        families=tuple(_family(f, members[f["platform_family"]], era_lines[f["platform_family"]])
                       for f in doc["families"]),
        doc=copy.deepcopy(doc))


def _read_text(path: Path) -> tuple[str | None, list[str]]:
    """The file as text, or None with its byte-level faults."""
    if not path.is_file():
        return None, [f"missing (no file at {path})"]
    data = path.read_bytes()
    faults = []
    if data.startswith(codecs.BOM_UTF8):
        faults.append("starts with a UTF-8 BOM")
    text = None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        faults.append(f"is not UTF-8 ({exc.reason} at byte {exc.start})")
    if b"\r" in data:
        faults.append("contains a carriage return (CRLF or CR line endings)")
    if not data:
        faults.append("is empty")
    elif not data.endswith(b"\n"):
        faults.append("does not end with a newline")
    elif data.endswith(b"\n\n"):
        faults.append("ends with a trailing blank line")
    return (None if faults else text), faults


def _reject_constant(name: str) -> object:
    raise ValueError(f"{name} is not JSON")


def _parse_json(text: str) -> tuple[object, list[str]]:
    duplicates: list[str] = []

    def pairs_hook(pairs: list[tuple[str, object]]) -> dict:
        obj: dict = {}
        for key, value in pairs:
            if key in obj:
                duplicates.append(key)
            obj[key] = value
        return obj

    try:
        doc = json.loads(text, object_pairs_hook=pairs_hook, parse_constant=_reject_constant)
    except json.JSONDecodeError as exc:
        return None, [f"is not valid JSON ({exc.msg} at line {exc.lineno} column {exc.colno})"]
    except ValueError as exc:
        return None, [f"is not valid JSON ({exc})"]
    if duplicates:
        return None, [f"duplicate key {key!r} in a JSON object" for key in duplicates]
    return doc, []


def _header_fault(header: list[str], columns: Sequence[str]) -> str | None:
    if tuple(header) == tuple(columns):
        return None
    if len(header) != len(columns):
        return f"header has {len(header)} columns, the frozen header has {len(columns)}"
    i = next(i for i, (a, b) in enumerate(zip(header, columns)) if a != b)
    return (f"header column {i + 1} is {header[i]!r}, the frozen header has {columns[i]!r} "
            f"(the {len(columns)}-column tuple, in order)")


def _parse_csv(text: str, columns: Sequence[str], file: str,
               row_ref: Callable[[list[str]], str | None]) -> tuple[list[dict[str, str]] | None, list[str]]:
    """Rows over the frozen header, or None with the file's lines. Fields are
    kept exactly as written (no skipinitialspace, no strip)."""
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    rows: list[dict[str, str]] = []
    faults: list[str] = []
    try:
        header = next(reader, [])
        fault = _header_fault(header, columns)
        if fault:
            return None, [_line(file, None, fault)]
        for fields in reader:
            if len(fields) != len(columns):
                ref = row_ref(fields) or f"line {reader.line_num}"
                faults.append(_line(file, ref, f"{len(fields)} fields, the header has {len(columns)}"))
                continue
            rows.append(dict(zip(columns, fields)))
    except csv.Error as exc:
        return None, [_line(file, None, f"is not valid CSV (line {reader.line_num}: {exc})")]
    return (None if faults else rows), faults


def _member_ref(fields: list[str]) -> str | None:
    return fields[0] if fields and fields[0] else None


def _era_ref(fields: list[str]) -> str | None:
    return f"{fields[0]}|{fields[2]}|{fields[3]}" if len(fields) >= 4 else None


def load_registry(paths: RegistryPaths = DEFAULT_PATHS, *,
                  era_decisions_path: Path | None = None) -> Registry:
    """Read the three files and run stage 1. File-level faults (missing, BOM,
    not UTF-8, carriage returns, empty, no final newline, a trailing blank
    line, bad JSON, duplicate JSON keys, a CSV header other than the frozen
    tuple, a row whose field count differs from the header's) are all raised
    together before parse_registry runs."""
    errors: list[str] = []
    texts: dict[Path, str | None] = {}
    for path in (paths.json, paths.members, paths.era_lines):
        text, faults = _read_text(path)
        errors.extend(_line(path.name, None, fault) for fault in faults)
        texts[path] = text
    doc: object = None
    if texts[paths.json] is not None:
        doc, faults = _parse_json(texts[paths.json])
        errors.extend(_line(paths.json.name, None, fault) for fault in faults)
    member_rows = era_rows = None
    if texts[paths.members] is not None:
        member_rows, faults = _parse_csv(texts[paths.members], MEMBER_COLUMNS, paths.members.name,
                                         _member_ref)
        errors.extend(faults)
    if texts[paths.era_lines] is not None:
        era_rows, faults = _parse_csv(texts[paths.era_lines], ERA_LINE_COLUMNS,
                                      paths.era_lines.name, _era_ref)
        errors.extend(faults)
    if errors:
        raise RegistryError(errors)
    seed = era_map.read_seed(era_decisions_path or era_map.default_seed_path())
    decisions = {row["decision_id"]: row for row in seed}
    return parse_registry(doc, member_rows, era_rows, era_decisions=decisions, paths=paths)


# ---------------------------------------------------------------------------
# Writers (D11) and the family hash (D10)
# ---------------------------------------------------------------------------


def _ordered(obj: object, keys: Sequence[str], label: str) -> dict:
    if not isinstance(obj, dict):
        raise ValueError(f"{label} must be an object, got {obj!r}")
    for key in obj:
        if key not in keys:
            raise ValueError(f"{label}: unknown key {key!r}")
    return {key: obj[key] for key in keys if key in obj}


def _canonical_family(fam: object) -> dict:
    out = _ordered(fam, FAMILY_KEYS, "families[]")
    for key, keys in (("headline", HEADLINE_KEYS), ("review_guard", GUARD_KEYS),
                      ("contract_routes", CONTRACT_ROUTE_KEYS),
                      ("official_estimates", OFFICIAL_ESTIMATE_KEYS), ("art", ART_KEYS)):
        if out.get(key) is not None:
            out[key] = _ordered(out[key], keys, key)
    for key, keys in (("variants", VARIANT_KEYS), ("program_tags", PROGRAM_TAG_KEYS),
                      ("exclusions", EXCLUSION_KEYS)):
        if key in out:
            out[key] = [_ordered(item, keys, f"{key}[]") for item in out[key]]
    if "program_notes" in out:
        notes = {}
        for member_id, note in sorted(out["program_notes"].items()):
            note = _ordered(note, PROGRAM_NOTE_KEYS, "program_notes")
            if "expected_receipt" in note:
                note["expected_receipt"] = _ordered(note["expected_receipt"], RECEIPT_KEYS,
                                                    "expected_receipt")
            notes[member_id] = note
        out["program_notes"] = notes
    return out


def _canonical_doc(doc: dict) -> dict:
    """Every object's keys in its key tuple's order (program_notes by
    member_id); families and list items keep their given order."""
    out = _ordered(doc, TOP_KEYS, "the top level")
    if "rulings" in out:
        out["rulings"] = [_ordered(r, RULING_KEYS, "rulings[]") for r in out["rulings"]]
    if "sources" in out:
        out["sources"] = [_ordered(s, SOURCE_KEYS, "sources[]") for s in out["sources"]]
    if "families" in out:
        out["families"] = [_canonical_family(f) for f in out["families"]]
    return out


def registry_texts(paths: RegistryPaths, *, doc: dict, members: Sequence[Mapping[str, str]],
                   era_lines: Sequence[Mapping[str, str]]) -> dict[Path, str]:
    """The three registry files' texts (D11). Does not validate: callers run
    parse_registry first."""
    return {
        paths.json: json.dumps(_canonical_doc(doc), indent=2, ensure_ascii=False) + "\n",
        paths.members: era_map._csv_text(MEMBER_COLUMNS,
                                         sorted(members, key=lambda r: r["member_row_id"])),
        paths.era_lines: era_map._csv_text(
            ERA_LINE_COLUMNS,
            sorted(era_lines, key=lambda r: (r["platform_family"], r["edition"], r["era_key"]))),
    }


def write_registry(paths: RegistryPaths, *, doc: dict, members: Sequence[Mapping[str, str]],
                   era_lines: Sequence[Mapping[str, str]]) -> None:
    """The three files in one era_map._atomic_write_texts call."""
    era_map._atomic_write_texts(registry_texts(paths, doc=doc, members=members, era_lines=era_lines))


def family_hash(doc: dict, platform_family: str) -> str:
    """D10: sha256 over the family object as written plus the sources its
    exclusions cite by `src:` ref (sorted by source_id)."""
    fam = next((f for f in doc["families"] if f.get("platform_family") == platform_family), None)
    if fam is None:
        raise KeyError(platform_family)
    cited = {ref[len("src:"):].split("#", 1)[0]
             for exclusion in fam.get("exclusions") or ()
             for ref in exclusion.get("evidence") or ()
             if ref.startswith("src:")}
    sources = sorted((s for s in doc.get("sources") or () if s.get("source_id") in cited),
                     key=lambda s: s["source_id"])
    text = json.dumps({"family": fam, "sources": sources}, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
