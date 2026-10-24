"""The generic platform-family history builder (families piece 2; spec §10, §11).

One builder for every family in the registry: cited, edition-scoped TOA
history, never a lifetime aircraft cost. The rules are code (the edition rule,
scenario selection from fct_decade_series, measures, sorts, point ids, the
default and cumulative rules, the reuse ranking); the values are registry data
(members, era rosters, the title guard, coverage, notes, names). For the F-15
the output is byte-identical to the 88538c6a builder; the facade
govbudget.f15_funding_history keeps today's names as wrappers bound to the F-15.

govbudget.export_site is imported inside the functions that use it, never at
module level.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json

from govbudget.jbooks.era_map import ERA_ORG_TO_MODERN
from govbudget.platform_families import EraLine, Family, Member

# Spec §11: filled with str.format from the registry.
ANNUAL_FORMULA = ("sum(budget_lines.amount_thousands) for reviewed {short_name} members, PB{edition}, "
                  "FY{fy} {kind}; one selected scenario column per workbook line")
CUMULATIVE_FORMULA = ("sum(budget_lines.amount_thousands) via annual reviewed {short_name} actuals totals, "
                      "FY{a}–FY{b}; each fiscal year once, nominal USD thousands; excludes "
                      "enacted/current-year figures and requests")
CELL_FORMULA = ("sum(budget_lines.amount_thousands) for workbook program {member_id}, PB{edition}, "
                "FY{fy} {kind}; each selected workbook input once")

_MODERN_TO_ERA = {modern: era for era, modern in ERA_ORG_TO_MODERN.items()}


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


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


def _spellings(organization: str) -> set[str]:
    """A member's organization in its era spelling and its modern spelling."""
    return {organization, ERA_ORG_TO_MODERN.get(organization, organization)}


@dataclass(frozen=True)
class _Roster:
    """One family's membership lookups, built once per call (not once per row)."""

    family: Family
    counted: Mapping[str, tuple[Member, ...]]                 # code -> its approved counted rows
    era: Mapping[tuple[int, str], tuple[EraLine, Member]]     # (edition, era_key) -> line, roster member
    covering: tuple[Member, ...]                              # approved non-counted rows and rejected rows


def _roster(family: Family) -> _Roster:
    counted: dict[str, tuple[Member, ...]] = {}
    for m in family.counted:
        counted[m.code] = counted.get(m.code, ()) + (m,)
    era = {}
    for line in family.era_lines:
        member = next((m for m in family.counted if m.member_id == line.member_id
                       and m.valid_from_edition <= line.edition <= m.valid_to_edition), None)
        if member is None:    # stage-1 rule 25 refuses this on a loaded registry
            raise ValueError(f"{family.short_name} era line {line.edition}/{line.era_key} has no approved "
                             f"counted row of {line.member_id}")
        era[(line.edition, line.era_key)] = (line, member)
    covering = tuple(m for m in family.members
                     if (m.verdict == "approved" and m.role != "counted") or m.verdict == "rejected")
    return _Roster(family, counted, era, covering)


def _match(roster: _Roster, row: Mapping) -> Member | None:
    """The counted member a lake row belongs to, or None.

    The check order is pinned (it reproduces the 88538c6a F-15 outcomes):
    exhibit; code-keyed member; era roster; a covering non-counted or rejected
    row; the title guard. Identity drift and an unreviewed guard match raise.
    """
    name = roster.family.short_name
    pe, edition = row["pe_bli"], int(row["edition"])
    if row["exhibit"] not in {"P-1", "R-1"}:
        return None
    if pe in roster.counted:
        for m in roster.counted[pe]:
            title = m.title_for(edition)
            if (title is not None and (row["exhibit"], row["account"], row["title"]) == (m.exhibit, m.account, title)
                    and row["organization"] in _spellings(m.organization)):
                return m
        raise ValueError(f"{name} modern member identity drift: {edition}/{pe}")
    if (edition, pe) in roster.era:
        line, m = roster.era[(edition, pe)]
        era_org = _MODERN_TO_ERA.get(m.organization, m.organization)
        if (row["exhibit"], row["account"], row["organization"], row["budget_activity"], row["title"]) != (
                "P-1", m.account, era_org, line.budget_activity, line.filed_title):
            raise ValueError(f"{name} era member identity drift: {edition}/{pe}")
        return m
    for m in roster.covering:
        if ((row["exhibit"], row["account"], pe) == (m.exhibit, m.account, m.code)
                and row["organization"] in _spellings(m.organization)
                and m.valid_from_edition <= edition <= m.valid_to_edition):
            return None
    guard = roster.family.review_guard
    title = (row.get("title") or "").upper()
    if row["exhibit"] in guard.exhibits and any(item in title for item in guard.title_substrings):
        # A family-looking new identity needs editorial review, not fuzzy inclusion.
        raise ValueError(f"Unreviewed {name} workbook identity: {edition}/{pe}")
    return None


def member_row(family: Family, row: Mapping) -> bool:
    """Explicit membership, with source title/account/activity drift rejected."""
    return _match(_roster(family), row) is not None


def expected_members(family: Family, edition: int) -> frozenset[str]:
    """Spec §10.3: the codes a point of this edition must carry to be covered."""
    return frozenset(m.code for m in family.counted if m.coverage_expected_from_edition is not None
                     and m.coverage_expected_from_edition <= edition <= m.valid_to_edition)


def program_entries(family: Family) -> list[dict]:
    """The matrix's programs[], in member_order (the facade's PROGRAMS)."""
    return [
        dict(id=m.member_id, code=m.code, title=m.display_title, program_slug=m.page_slug or None,
             exhibit=m.exhibit, account=m.account, organization=m.organization,
             **(dict(note=family.program_notes[m.member_id].note,
                     note_fact_id=family.program_notes[m.member_id].note_fact_id)
                if m.member_id in family.program_notes else {}))
        for m in family.counted
    ]


def reuse_formulas(member_id: str, edition: int, fy: int, kind: str, amount_type: str | None) -> list[str]:
    """The reuse allow-list, best first: the cell's own formula, then (for one
    amount type) the edition-qualified and the bare decade receipt."""
    own = CELL_FORMULA.format(member_id=member_id, edition=edition, fy=fy, kind=kind)
    if amount_type is None:
        return [own]
    return [own, f"sum(budget_lines.amount_thousands where amount_type={amount_type} and edition={edition})",
            f"sum(budget_lines.amount_thousands where amount_type={amount_type})"]


def check_headline(family: Family, payload: dict) -> None:
    """The cumulative window equals the registry headline (the export post-pass only)."""
    a, b = payload["cumulative"]["start_fy"], payload["cumulative"]["end_fy"]
    first, last = family.headline.first_fy, family.headline.last_fy
    if (a, b) != (first, last):
        raise ValueError(f"{family.short_name} cumulative window FY{a}–FY{b} differs from the registry "
                         f"headline FY{first}–FY{last}")


def check_program_notes(family: Family, programs: list[dict], registry: Mapping[str, dict]) -> None:
    """A program note ships only with the reviewed narrative receipt it quotes."""
    receipts = {pn.note_fact_id: dict(pn.expected_receipt) for pn in family.program_notes.values()}
    for program in programs:
        if "note" not in program and "note_fact_id" not in program:
            continue
        fid = program.get("note_fact_id")
        expected = receipts.get(fid)
        citation = registry.get(fid) if fid else None
        if (not program.get("note") or expected is None or citation is None
                or any(citation.get(key) != value for key, value in expected.items())):
            raise ValueError(f"{family.short_name} program note receipt mismatch: {program['code']}/{fid}")


def build_history(family: Family, source_rows: list[dict], series: list[dict], *, retrieved_at: str,
                  current_fact_ids: set[str] | None = None) -> tuple[dict | None, dict, dict, dict]:
    """Pure builder returning payload, citations and additive breakdowns.

    source_rows must include workbook source identity; series is the canonical
    edition-relative mart. A count/value mismatch stops generation.
    """
    from govbudget.export_site import fact_id_workbook, fact_id_derived, _amount_type_meta, _decade_measure_token

    name, roster = family.short_name, _roster(family)
    by_grain = defaultdict(list)
    for row in source_rows:
        member = _match(roster, row)
        if member is not None:
            by_grain[(row["pe_bli"], row["edition"], row["amount_type"])].append((row, member))
    annual = defaultdict(list)
    citations, workbook_rows = {}, {}
    code_of = {}    # leaf fact id -> its member's code (spec §10.3: era rows count for their roster member)
    seen_series = set()
    for point in series:
        key = (point["pe_bli"], point["edition"], point["amount_type"])
        matched = by_grain.get(key)
        if not matched:
            continue
        rows = [row for row, _ in matched]
        fy, kind, edition = point["fy"], point["kind"], point["edition"]
        if edition - fy != {"actuals": 2, "enacted": 1, "request": 0}[kind]:
            raise ValueError(f"{name} scenario edition mismatch")
        series_key = (point["pe_bli"], edition, kind)
        if series_key in seen_series:
            raise ValueError(f"Duplicate {name} scenario: {series_key}")
        seen_series.add(series_key)
        amount = sum((Decimal(str(row["amount_thousands"])) for row in rows), Decimal(0))
        if len(rows) != point["n_source_rows"] or amount != Decimal(str(point["amount"])):
            raise ValueError(f"{name} lake/mart count or value mismatch: {key}")
        for row, member in matched:
            if not row.get("sha256") or not row.get("official_url") or not row.get("sheet") or not row.get("cells"):
                raise ValueError(f"{name} workbook provenance missing: {key}")
            fid = fact_id_workbook(row["sha256"], row["exhibit"], edition, row["account"], row["organization"], row["budget_activity"], row["pe_bli"], row["amount_type"])
            if fid in workbook_rows:
                raise ValueError(f"Duplicate {name} workbook input: {fid}")
            _, raw_measure = _amount_type_meta(row["amount_type"], edition)
            measure = _decade_measure_token(kind, raw_measure)
            component = {k: row[k] for k in ("pe_bli", "title", "exhibit", "account", "organization", "budget_activity", "amount_type", "amount_thousands", "official_url", "sheet", "cells")}
            program_slug = (member.page_slug or None) if row["pe_bli"] in roster.counted else None
            component.update(fact_id=fid, program_slug=program_slug, measure=measure, dataset="budget_lines" if fid in (current_fact_ids or set()) else "budget_lines_decade")
            annual[(fy, edition, kind)].append(component)
            workbook_rows[fid] = row
            code_of[fid] = member.code
            citations[fid] = dict(kind="workbook", units="USD thousands", amount_thousands=row["amount_thousands"], sha256=row["sha256"], sheet=row["sheet"], cells=row["cells"], official_url=row["official_url"], retrieved_at=row.get("retrieved_at"), pe_bli=component["program_slug"], amount_type=row["amount_type"])
    if not annual:
        return None, {}, {}, {}
    points, breakdowns = [], {}
    for (fy, edition, kind), components in sorted(annual.items()):
        components.sort(key=lambda row: (row["exhibit"], row["pe_bli"], row["budget_activity"] or "", row["fact_id"]))
        ids = [row["fact_id"] for row in components]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate {name} annual input")
        amount = sum((Decimal(str(row["amount_thousands"])) for row in components), Decimal(0))
        fid = fact_id_derived("family_history", f"{family.platform_family}|{edition}|{fy}", kind)
        formula = ANNUAL_FORMULA.format(short_name=name, edition=edition, fy=fy, kind=kind)
        citations[fid] = dict(kind="derived", units="USD thousands", recorded_value=f"{amount:.3f}", formula=formula, inputs=json.dumps(ids), retrieved_at=retrieved_at)
        measure, label = _point_measure(kind, {r["measure"] for r in components})
        present = {code_of[r["fact_id"]] for r in components}
        missing = sorted(expected_members(family, edition) - present)
        point = dict(id=f"fy{fy}{ {'actuals':'a','enacted':'e','request':'r'}[kind] }", fy=fy, edition=edition, kind=kind, measure=measure, measure_label=label, amount_thousands=float(amount), fact_id=fid, coverage="partial" if missing else "covered-records", missing_programs=missing, components=components)
        points.append(point)
        breakdowns[fid] = dict(fact_id=fid, op="sum", units="USD thousands", formula=formula, recorded_value=f"{amount:.3f}", rows=[dict(label=f"{r['title']} · {r['pe_bli']} · BA {r['budget_activity']}", pe_bli=r["program_slug"], v=r["amount_thousands"], fid=r["fact_id"]) for r in components])
    actuals = [p for p in points if p["kind"] == "actuals"]
    years = sorted({p["fy"] for p in actuals})
    if years != list(range(min(years), max(years) + 1)):
        raise ValueError(f"{name} cumulative actuals cannot silently cross a missing year")
    total = sum((Decimal(str(p["amount_thousands"])) for p in actuals), Decimal(0))
    total_fid = fact_id_derived("family_history", f"{family.platform_family}|{min(years)}|{max(years)}", "cumulative-actuals")
    total_formula = CUMULATIVE_FORMULA.format(short_name=name, a=min(years), b=max(years))
    citations[total_fid] = dict(kind="derived", units="USD thousands", recorded_value=f"{total:.3f}", formula=total_formula, inputs=json.dumps([p["fact_id"] for p in actuals]), retrieved_at=retrieved_at)
    breakdowns[total_fid] = dict(fact_id=total_fid, op="sum", units="USD thousands", formula=total_formula, recorded_value=f"{total:.3f}", rows=[dict(label=f"FY{p['fy']} actuals · PB{p['edition']}", pe_bli=None, v=p["amount_thousands"], fid=p["fact_id"]) for p in actuals])
    defaults = {}
    for p in sorted(points, key=lambda p: {"request": 0, "enacted": 1, "actuals": 2}[p["kind"]]):
        defaults[p["fy"]] = p["id"]
    payload = dict(schema_version=1, family_id=family.platform_family, units="USD thousands", basis="toa", start_fy=min(defaults), end_fy=max(defaults), scope_note=family.scope_note, coverage_notes=list(family.coverage_notes), default_point_ids=[defaults[fy] for fy in sorted(defaults)], points=points, cumulative=dict(start_fy=min(years), end_fy=max(years), kind="actuals", measure="actuals", amount_thousands=float(total), fact_id=total_fid, point_ids=[p["id"] for p in actuals], scope_note="Sum of covered annual recorded actuals only, in nominal dollars. This is not a lifetime cost; missing or unallocated funding is excluded."))
    return payload, citations, workbook_rows, breakdowns


def build_program_matrix(family: Family, payload: dict, previews: dict, *, existing_citations: dict,
                         retrieved_at: str) -> tuple[dict, dict, dict]:
    """Group exact workbook inputs by verified code, without changing totals.

    Existing line numbers and source identities stay on the components. Every
    populated cell has an exact receipt; absent program/year combinations are
    omitted, never supplied with a manufactured zero. A reusable receipt must
    sum precisely the same distinct workbook facts under the same scenario.
    """
    from govbudget.export_site import fact_id_derived

    name, roster = family.short_name, _roster(family)
    entries = program_entries(family)
    payload = deepcopy(payload)
    payload["programs"] = deepcopy(entries)
    programs = {p["code"]: p for p in entries}
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
                raise ValueError(f"Duplicate {name} matrix input: {fid}")
            seen.add(fid)
            member = _match(roster, {**row, "edition": point["edition"]})
            if member is None:
                raise ValueError(f"Unreviewed {name} matrix input: {fid}")
            expected = member.code
            preview = previews.get(fid, {})
            cited = [r for r in preview.get("rows", []) if r.get("cited")]
            codes = {r.get("code") for r in cited}
            cells = {f"{preview.get('col')}{r.get('r')}" for r in cited}
            if codes != {expected} or expected not in programs:
                raise ValueError(f"{name} workbook program code mismatch: {fid}: {codes} != {expected}")
            if (preview.get("sheet") != row["sheet"] or preview.get("units") != "USD thousands"
                    or cells != {cell.strip() for cell in row["cells"].split(",")}
                    or preview.get("total") is None
                    or Decimal(str(preview["total"])) != Decimal(str(row["amount_thousands"]))):
                raise ValueError(f"{name} matrix workbook preview mismatch: {fid}")
            program = programs[expected]
            if (row["exhibit"], row["account"], row["organization"] in _spellings(program["organization"])) != (program["exhibit"], program["account"], True):
                raise ValueError(f"{name} matrix program account mismatch: {fid}")
            row["program_id"] = program["id"]
            groups[program["id"]].append(row)
        cells = []
        for program in entries:
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
                dataset = family.history_dataset
                edition, fy, kind = point["edition"], point["fy"], point["kind"]
                fid = fact_id_derived("family_program_history", f"{program['id']}|{edition}|{fy}", kind)
                amount_types = {row["amount_type"] for row in rows}
                allowed = reuse_formulas(program["id"], edition, fy, kind,
                                         next(iter(amount_types)) if len(amount_types) == 1 else None)
                formula = allowed[0]
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
            raise ValueError(f"{name} matrix/annual total mismatch: {point['id']}")
        point["program_cells"] = cells
    return payload, additions, breakdowns
