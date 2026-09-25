import copy
import json
from decimal import Decimal

import pytest

from govbudget.f15_funding_history import (
    ERA_MEMBERS,
    ERA_PROGRAM_CODES,
    build_history,
    build_program_matrix,
    member_row,
)


def source(pe="0207134F", edition=2026, amount_type="fy_2024_actuals", value=10, **kwargs):
    row = dict(pe_bli=pe, edition=edition, exhibit="R-1", account="3600F", account_title="RDT&E", organization="F", budget_activity="07", budget_activity_title="Operational Systems", title="F-15E Squadrons", amount_type=amount_type, amount_thousands=value, sha256="a" * 64, sheet="Exhibit R-1", cells="J20", official_url="https://comptroller.war.gov/r1.xlsx", retrieved_at="2026-09-24")
    row.update(kwargs)
    return row


def point(row, *, fy=2024, kind="actuals", n=1, amount=None):
    return dict(pe_bli=row["pe_bli"], edition=row["edition"], fy=fy, kind=kind, amount_type=row["amount_type"], n_source_rows=n, amount=row["amount_thousands"] if amount is None else amount)


def build(rows, points):
    return build_history(rows, points, retrieved_at="2026-09-24")


def test_era_membership_is_scoped_to_edition_account_activity_and_exact_title():
    row = source("3010F-AF-L21", 2017, exhibit="P-1", account="3010F", organization="AF", budget_activity="05", title="F-15")
    assert member_row(row)
    for field, value in [("account", "3020F"), ("organization", "N"), ("budget_activity", "07"), ("title", "Other fighter")]:
        with pytest.raises(ValueError, match="identity drift"):
            member_row({**row, field: value})
    assert not member_row({**row, "edition": 2018, "title": "Other fighter"})
    with pytest.raises(ValueError, match="Unreviewed"):
        member_row({**row, "edition": 2018})
    assert sum(map(len, ERA_MEMBERS.values())) == 31


def test_reserve_breakout_and_unrelated_lines_never_join_the_family():
    assert not member_row(source(exhibit="P-1R"))
    assert not member_row(source("unknown", title="Other aircraft"))
    with pytest.raises(ValueError, match="Unreviewed"):
        member_row(source("0207130F", title="F-15 Squadrons"))


def test_exact_scenario_selection_excludes_disc_reconciliation_and_earlier_request():
    actual = source()
    request = source(amount_type="fy_2026_total", value=30, cells="P20")
    alternatives = [source(amount_type="fy_2026_disc_request", value=20), source(amount_type="fy_2026_reconciliation_request", value=10)]
    payload, citations, leaves, _ = build([actual, request, *alternatives], [point(actual), point(request, fy=2026, kind="request")])
    assert len(leaves) == 2
    assert payload["cumulative"]["amount_thousands"] == 10
    assert payload["points"][-1]["amount_thousands"] == 30
    assert payload["default_point_ids"] == ["fy2024a", "fy2026r"]
    assert len(json.loads(citations[payload["cumulative"]["fact_id"]]["inputs"])) == 1


def test_multiple_activities_sum_once_with_direct_workbook_receipts():
    first = source("F015EX", exhibit="P-1", account="3010F", title="F-15EX", budget_activity="01", value=100, cells="O10")
    second = {**first, "budget_activity": "05", "amount_thousands": 20, "cells": "O20"}
    payload, citations, leaves, breakdowns = build([first, second], [point(first, n=2, amount=120)])
    annual = payload["points"][0]
    assert annual["amount_thousands"] == 120
    assert len(set(json.loads(citations[annual["fact_id"]]["inputs"]))) == 2
    assert sum(r["v"] for r in breakdowns[annual["fact_id"]]["rows"]) == 120
    assert len(leaves) == 2


@pytest.mark.parametrize("change", [dict(n_source_rows=2), dict(amount=11), dict(edition=2025)])
def test_lake_mart_drift_fails(change):
    row = source()
    p = {**point(row), **change}
    if "edition" in change:
        row["edition"] = change["edition"]
    with pytest.raises(ValueError, match="mismatch"):
        build([row], [p])


def test_duplicate_grains_and_duplicate_leaf_identity_fail():
    row = source()
    with pytest.raises(ValueError, match="Duplicate F-15 scenario"):
        build([row], [point(row), point(row)])
    with pytest.raises(ValueError, match="Duplicate F-15 workbook"):
        build([row, copy.deepcopy(row)], [point(row, n=2, amount=20)])


def test_missing_member_is_disclosed_without_zero_or_jbook_substitution():
    row = source()
    payload, *_ = build([row], [point(row)])
    annual = payload["points"][0]
    assert annual["coverage"] == "partial"
    assert "0207171F" in annual["missing_programs"]
    assert annual["amount_thousands"] == 10
    assert "lifetime" in payload["scope_note"]


def test_cumulative_requires_contiguous_actual_years_and_uses_each_year_once():
    first = source(edition=2024, amount_type="fy_2022_actuals", value=4)
    last = source()
    with pytest.raises(ValueError, match="missing year"):
        build([first, last], [point(first, fy=2022), point(last)])
    middle = source(edition=2025, amount_type="fy_2023_actuals", value=6)
    payload, citations, *_ = build([first, middle, last], [point(first, fy=2022), point(middle, fy=2023), point(last)])
    assert payload["cumulative"]["amount_thousands"] == 20
    ids = json.loads(citations[payload["cumulative"]["fact_id"]]["inputs"])
    assert len(ids) == len(set(ids)) == 3
    assert sum(Decimal(citations[fid]["recorded_value"]) for fid in ids) == 20


def test_cr_current_year_snapshot_keeps_its_qualified_measure():
    actual = source()
    adjusted = source(edition=2025, amount_type="fy_2024_pb_request_with_cr_adjustments", value=15, cells="K20")
    payload, *_ = build([actual, adjusted], [point(actual), point(adjusted, kind="enacted")])
    current = next(p for p in payload["points"] if p["kind"] == "enacted")
    assert current["measure"] == "enacted-request"
    assert "CR adjustments" in current["measure_label"]
    assert payload["default_point_ids"] == ["fy2024a"]


def test_missing_workbook_locator_fails_before_emission():
    row = source(cells=None)
    with pytest.raises(ValueError, match="provenance missing"):
        build([row], [point(row)])


def matrix(payload, leaves, existing_citations=None, change_previews=None):
    previews = {}
    for fid, row in leaves.items():
        code = row["pe_bli"]
        if code.startswith("3010F-AF-L"):
            code = ERA_PROGRAM_CODES[row["edition"]][int(code.rsplit("L", 1)[1])]
        refs = row["cells"].split(",")
        col = refs[0].rstrip("0123456789")
        previews[fid] = dict(sheet=row["sheet"], col=col, units="USD thousands", total=row["amount_thousands"], rows=[dict(r=int(ref[len(col):]), code=code, cited=True) for ref in refs])
    if change_previews:
        change_previews(previews)
    return build_program_matrix(payload, previews, existing_citations=existing_citations or {}, retrieved_at="2026-09-24")


def test_matrix_groups_verified_legacy_codes_without_merging_different_lines():
    rows = [
        source("3010F-AF-L25", 2020, amount_type="fy_2018_actuals", value=430273, exhibit="P-1", account="3010F", organization="AF", budget_activity="05", title="F-15", cells="J10"),
        source("3010F-AF-L79", 2020, amount_type="fy_2018_actuals", value=20000, exhibit="P-1", account="3010F", organization="AF", budget_activity="07", title="F-15", cells="J20"),
        source("3010F-AF-L80", 2020, amount_type="fy_2018_actuals", value=2524, exhibit="P-1", account="3010F", organization="AF", budget_activity="07", title="F-15", cells="J30"),
    ]
    payload, _, leaves, _ = build(rows, [point(row, fy=2018) for row in rows])
    enriched, citations, breakdowns = matrix(payload, leaves)
    annual = enriched["points"][0]
    cells = {cell["program_id"].rsplit(":", 1)[1]: cell for cell in annual["program_cells"]}
    assert cells.keys() == {"F01500", "F0150P"}
    assert cells["F01500"]["amount_thousands"] == 450273
    assert cells["F0150P"]["amount_thousands"] == 2524
    assert cells["F01500"]["dataset"] == "f15_funding_history"
    assert cells["F0150P"]["dataset"] == "budget_lines_decade"
    assert len(citations) == len(breakdowns) == 1
    assert sorted(fid for cell in cells.values() for fid in cell["input_fact_ids"]) == sorted(leaves)
    assert annual["fact_id"] == payload["points"][0]["fact_id"]
    assert enriched["cumulative"] == payload["cumulative"]
    assert "program_id" not in payload["points"][0]["components"][0]


def test_matrix_keeps_legacy_f15e_separate_from_ex_and_retains_real_zero():
    rows = [
        source("3010F-AF-L4", 2022, amount_type="fy_2020_actuals", value=621100, exhibit="P-1", account="3010F", organization="AF", budget_activity="01", title="F-15e", cells="J10"),
        source("3010F-AF-L5", 2022, amount_type="fy_2020_actuals", value=0, exhibit="P-1", account="3010F", organization="AF", budget_activity="01", title="F-15EX", cells="J20"),
        source("3010F-AF-L6", 2022, amount_type="fy_2020_actuals", value=0, exhibit="P-1", account="3010F", organization="AF", budget_activity="01", title="F-15EX", cells="J30"),
    ]
    payload, _, leaves, _ = build(rows, [point(row, fy=2020) for row in rows])
    enriched, citations, _ = matrix(payload, leaves)
    cells = {cell["program_id"].rsplit(":", 1)[1]: cell for cell in enriched["points"][0]["program_cells"]}
    assert cells.keys() == {"F015E0", "F015EX"}
    assert cells["F015E0"]["amount_thousands"] == 621100
    assert cells["F015EX"]["amount_thousands"] == 0
    assert len(json.loads(citations[cells["F015EX"]["fact_id"]]["inputs"])) == 2
    assert next(p for p in enriched["programs"] if p["code"] == "F015E0")["program_slug"] is None
    assert not any(cell["program_id"].endswith(":0207171F") for cell in cells.values())


def test_matrix_preserves_two_development_activities_and_multicell_leaf():
    first = source("0207171F", title="F-15 EPAWSS", budget_activity="05", value=0)
    second = source("0207171F", title="F-15 EPAWSS", budget_activity="07", value=20, cells="J30,J31")
    payload, _, leaves, _ = build([first, second], [point(first, n=2, amount=20)])
    enriched, citations, _ = matrix(payload, leaves)
    cell = enriched["points"][0]["program_cells"][0]
    assert cell["amount_thousands"] == 20
    assert len(cell["input_fact_ids"]) == 2
    assert set(json.loads(citations[cell["fact_id"]]["inputs"])) == set(leaves)


@pytest.mark.parametrize("defect", ["code", "missing_code", "mixed_codes", "missing_preview", "cells", "total", "sheet"])
def test_matrix_rejects_unverified_or_drifted_workbook_codes_and_locators(defect):
    row = source(cells="J20,J21")
    payload, _, leaves, _ = build([row], [point(row)])
    def corrupt(previews):
        fid = next(iter(previews))
        preview = previews[fid]
        if defect == "code":
            for item in preview["rows"]:
                item["code"] = "0207146F"
        elif defect == "missing_code":
            for item in preview["rows"]:
                item.pop("code")
        elif defect == "mixed_codes":
            preview["rows"][0]["code"] = "0207146F"
        elif defect == "missing_preview":
            previews.clear()
        elif defect == "cells":
            preview["rows"][0]["r"] = 22
        elif defect == "total":
            preview["total"] += 1
        else:
            preview["sheet"] = "Other sheet"
    with pytest.raises(ValueError, match="mismatch"):
        matrix(payload, leaves, change_previews=corrupt)


def test_matrix_reuses_only_exact_additive_receipts_and_prefers_edition_context():
    first = source("F015EX", exhibit="P-1", account="3010F", title="F-15EX", budget_activity="01", value=100, cells="J10")
    second = {**first, "budget_activity": "05", "amount_thousands": 20, "cells": "J20"}
    payload, _, leaves, _ = build([first, second], [point(first, n=2, amount=120)])
    exact = dict(kind="derived", units="USD thousands", recorded_value="120.000", formula="sum(budget_lines.amount_thousands where amount_type=fy_2024_actuals and edition=2026)", inputs=json.dumps(sorted(leaves)))
    existing = {
        "canonical": exact,
        "current-page": {**exact, "formula": "sum(budget_lines.amount_thousands where amount_type=fy_2024_actuals)"},
        "wrong-year": {**exact, "formula": "sum(budget_lines.amount_thousands where amount_type=fy_2025_enacted and edition=2026)"},
        "wrong-value": {**exact, "recorded_value": "121.000"},
        "wrong-operation": {**exact, "formula": "max(budget_lines.amount_thousands)"},
        "duplicate-input": {**exact, "inputs": json.dumps([*leaves, next(iter(leaves))])},
        "different-input": {**exact, "inputs": json.dumps([next(iter(leaves)), "other"])},
    }
    enriched, citations, _ = matrix(payload, leaves, existing)
    cell = enriched["points"][0]["program_cells"][0]
    assert cell["fact_id"] == "canonical"
    assert citations == {"canonical": exact}
    for key in ("canonical", "current-page"):
        existing.pop(key)
    generated, fresh, _ = matrix(payload, leaves, existing)
    fresh_id = generated["points"][0]["program_cells"][0]["fact_id"]
    assert fresh_id not in existing
    repeated, reused, _ = matrix(payload, leaves, fresh)
    assert repeated == generated
    assert reused == fresh


def test_matrix_rejects_duplicate_inputs_and_changed_annual_total():
    row = source()
    payload, _, leaves, _ = build([row], [point(row)])
    changed = copy.deepcopy(payload)
    changed["points"][0]["components"].append(changed["points"][0]["components"][0])
    with pytest.raises(ValueError, match="Duplicate F-15 matrix input"):
        matrix(changed, leaves)
    changed = copy.deepcopy(payload)
    changed["points"][0]["amount_thousands"] += 1
    with pytest.raises(ValueError, match="matrix/annual total mismatch"):
        matrix(changed, leaves)


@pytest.mark.parametrize("amount_type,kind,fy,expected", [
    ("fy_2015_base_oco", "actuals", 2015, "actuals-base-oco"),
    ("fy_2017_base_oco", "request", 2017, "request-base-oco"),
    ("fy_2016_pb_request_with_cr_adjustments", "enacted", 2016, "enacted-request"),
])
@pytest.mark.parametrize("activity_count", [1, 2])
def test_matrix_preserves_exact_scenario_measure_for_homogeneous_inputs(amount_type, kind, fy, expected, activity_count):
    first = source("0207171F", edition=2017, title="F-15 EPAWSS", amount_type=amount_type, budget_activity="05")
    rows = [first]
    if activity_count == 2:
        rows.append({**first, "budget_activity": "07", "cells": "J30"})
    points = [point(first, fy=fy, kind=kind, n=activity_count, amount=10 * activity_count)]
    if kind != "actuals":
        actual = source(edition=2017, amount_type="fy_2015_base_oco", cells="J40")
        rows.append(actual)
        points.append(point(actual, fy=2015))
    payload, _, leaves, _ = build(rows, points)
    enriched, _, _ = matrix(payload, leaves)
    selected = next(p for p in enriched["points"] if p["kind"] == kind)
    assert selected["program_cells"][0]["measure"] == expected
    assert {row["measure"] for row in selected["components"]} == {expected}
