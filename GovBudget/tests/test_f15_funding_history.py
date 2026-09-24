import copy
import json
from decimal import Decimal

import pytest

from govbudget.f15_funding_history import build_history, member_row, ERA_MEMBERS


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
