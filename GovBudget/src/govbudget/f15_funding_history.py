"""Cited, edition-scoped F-15 TOA history; never a lifetime aircraft cost.

Era procurement identifiers are line numbers, not durable program identities.
Their membership is reviewed at (edition, account, organization, activity, key)
and checked against the exact filed title. Existing scenario selection comes
from fct_decade_series; we never sum base/OCO/total or request/reconciliation
alternatives. Every annual fact sums the selected workbook leaf facts once.
"""
from __future__ import annotations

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

    export_family_histories restricted to the F-15 (never json/families/index.json),
    with today's six return keys; None when the export carries no full F-15 corpus.
    """
    result = platform_family_history.export_family_histories(
        duckdb_path=duckdb_path, out_dir=out_dir,
        registry=platform_families.load_registry(platform_families.DEFAULT_PATHS), families=[F15.platform_family])
    if result is None:
        return None
    family = result["families"][F15.platform_family]
    return {"annual_points": family["annual_points"], "source_facts": family["source_facts"],
            "added_citations": family["added_citations"], "citations": result["citations"],
            "json_files": result["json_files"], "cumulative_actuals_thousands": family["cumulative_actuals_thousands"]}
