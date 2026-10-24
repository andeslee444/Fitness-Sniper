"""The generic platform-family history builder (families piece 2; spec §10, §11, §13).

F35 is a synthetic F-35-shaped family built from the F-15 entry without stage 1:
the builder is pure, so it needs only the Family fields it reads."""
from dataclasses import replace

import pytest

from govbudget.export_site import fact_id_derived
from govbudget.platform_families import EraLine, Headline, ReviewGuard, load_registry
from govbudget.platform_family_history import (ANNUAL_FORMULA, CELL_FORMULA, CUMULATIVE_FORMULA, _json_bytes,
                                               build_history, build_program_matrix, check_headline,
                                               expected_members, member_row, program_entries, reuse_formulas)

F15 = load_registry()["f-15"]


def _member(member_id, title, *, family="f-35", valid=(2017, 2026), titles=None, order=None, role="counted",
            page_slug=None):
    first, last = valid
    exhibit, account, organization, code = member_id.split(":")
    return replace(
        F15.counted[0],
        member_row_id=f"{family}|{member_id}|{first}-{last}", platform_family=family, member_id=member_id,
        exhibit=exhibit, account=account, organization=organization, code=code, role=role, verdict="approved",
        # A tuple, never a generator: F35 is shared by every test and title_for reads it on every call.
        titles_seen=tuple((e, title) for e in (titles if titles is not None else range(first, last + 1))),
        display_title=title,
        page_slug=page_slug if page_slug is not None else (code if role == "counted" else ""),
        valid_from_edition=first, valid_to_edition=last,
        coverage_expected_from_edition=first if role == "counted" else None,
        member_order=order, era_decision_ids=(), evidence=())


F35 = replace(
    F15, platform_family="f-35", short_name="F-35", history_dataset="f35_funding_history",
    on_partial_corpus="raise",
    review_guard=ReviewGuard(exhibits=("P-1", "R-1"),
                             title_substrings=("F-35", "F35", "JSF", "JOINT STRIKE", "F135", "LIGHTNING")),
    headline=Headline("cumulative_actuals", 2015, 2024), program_notes={},
    scope_note="Synthetic F-35-shaped scope note.", coverage_notes=("Synthetic coverage note.",),
    members=(
        _member("P-1:3010F:AF:ATA000", "F-35", titles=range(2024, 2027), order=1),
        _member("P-1:1506N:NAVY:0152", "JSF STOVL", titles=range(2024, 2027), order=2),
        _member("R-1:3600F:AF:0207142F", "F-35 Squadrons", order=3),
        # Synthetic range, so a PB2026 row is in range.
        _member("R-1:1319N:NAVY:0604800M", "JSF EMD", order=4),
        _member("R-1:1319N:NAVY:0604810N", "JSF Follow-On Modernization", valid=(2017, 2020), order=5),
        _member("P-1:3020F:AF:JSM000", "Joint Strike Missile", titles=(), role="context"),
    ),
    era_lines=(EraLine("f-35", "P-1:3010F:AF:ATA000", 2020, "3010F-AF-L1", "01", "F-35", "ATA000|3010F||2017-2023"),),
)


def _row(pe, edition, *, exhibit, account, organization, title, amount_type="fy_2024_actuals", value=10,
         budget_activity="01", cells="J20"):
    """The shape of tests/test_f15_funding_history.py::source."""
    return dict(pe_bli=pe, edition=edition, exhibit=exhibit, account=account, account_title="Synthetic account",
                organization=organization, budget_activity=budget_activity,
                budget_activity_title="Synthetic activity", title=title, amount_type=amount_type,
                amount_thousands=value, sha256="a" * 64, sheet=f"Exhibit {exhibit}", cells=cells,
                official_url="https://comptroller.war.gov/synthetic.xlsx", retrieved_at="2026-10-21")


def _point(row, *, fy=2024, kind="actuals", n=1, amount=None):
    """The shape of tests/test_f15_funding_history.py::point."""
    return dict(pe_bli=row["pe_bli"], edition=row["edition"], fy=fy, kind=kind, amount_type=row["amount_type"],
                n_source_rows=n, amount=row["amount_thousands"] if amount is None else amount)


def _previews(leaves, family):
    """tests/test_f15_funding_history.py::matrix's previews; an era leaf's code comes from family.era_lines."""
    codes = {m.member_id: m.code for m in family.members}
    era = {(line.edition, line.era_key): codes[line.member_id] for line in family.era_lines}
    previews = {}
    for fid, row in leaves.items():
        code = era.get((row["edition"], row["pe_bli"]), row["pe_bli"])
        refs = row["cells"].split(",")
        col = refs[0].rstrip("0123456789")
        previews[fid] = dict(sheet=row["sheet"], col=col, units="USD thousands", total=row["amount_thousands"],
                             rows=[dict(r=int(ref[len(col):]), code=code, cited=True) for ref in refs])
    return previews


def test_templates_are_the_spec_section_11_text():
    assert ANNUAL_FORMULA == ("sum(budget_lines.amount_thousands) for reviewed {short_name} members, PB{edition}, "
                              "FY{fy} {kind}; one selected scenario column per workbook line")
    assert CUMULATIVE_FORMULA == ("sum(budget_lines.amount_thousands) via annual reviewed {short_name} actuals totals, "
                                  "FY{a}–FY{b}; each fiscal year once, nominal USD thousands; excludes "
                                  "enacted/current-year figures and requests")
    assert CELL_FORMULA == ("sum(budget_lines.amount_thousands) for workbook program {member_id}, PB{edition}, "
                            "FY{fy} {kind}; each selected workbook input once")


def test_reuse_formulas_lists_own_then_edition_then_bare():
    own = ("sum(budget_lines.amount_thousands) for workbook program P-1:3010F:AF:F01500, PB2018, FY2016 actuals; "
           "each selected workbook input once")
    assert reuse_formulas("P-1:3010F:AF:F01500", 2018, 2016, "actuals", "fy_2016_base_oco") == [
        own, "sum(budget_lines.amount_thousands where amount_type=fy_2016_base_oco and edition=2018)",
        "sum(budget_lines.amount_thousands where amount_type=fy_2016_base_oco)"]
    assert reuse_formulas("P-1:3010F:AF:F01500", 2018, 2016, "actuals", None) == [own]


def test_four_accounts_sum_once_into_one_annual_point():
    rows = [_row("ATA000", 2026, exhibit="P-1", account="3010F", organization="F", title="F-35", value=100, cells="J10"),
            _row("0152", 2026, exhibit="P-1", account="1506N", organization="N", title="JSF STOVL", value=20, cells="J11"),
            _row("0207142F", 2026, exhibit="R-1", account="3600F", organization="F", title="F-35 Squadrons", value=3, cells="J12"),
            _row("0604800M", 2026, exhibit="R-1", account="1319N", organization="N", title="JSF EMD", value=4, cells="J13")]
    payload, citations, leaves, _ = build_history(F35, rows, [_point(r) for r in rows], retrieved_at="2026-10-21")
    (point,) = payload["points"]
    assert point["amount_thousands"] == 127 and len(leaves) == 4
    assert {c["program_slug"] for c in point["components"]} == {"ATA000", "0152", "0207142F", "0604800M"}
    assert point["fact_id"] == fact_id_derived("family_history", "f-35|2026|2024", "actuals")
    assert citations[point["fact_id"]]["formula"] == ("sum(budget_lines.amount_thousands) for reviewed F-35 members, "
                                                      "PB2026, FY2024 actuals; one selected scenario column per workbook line")
    assert point["missing_programs"] == [] and point["coverage"] == "covered-records"
    assert payload["family_id"] == "f-35" and payload["scope_note"] == "Synthetic F-35-shaped scope note."
    assert payload["cumulative"]["fact_id"] == fact_id_derived("family_history", "f-35|2024|2024", "cumulative-actuals")


def test_navy_rows_accept_the_era_and_modern_spellings_only():
    row = _row("0604800M", 2026, exhibit="R-1", account="1319N", organization="N", title="JSF EMD")
    assert member_row(F35, row) and member_row(F35, {**row, "organization": "NAVY"})
    with pytest.raises(ValueError, match=r"^F-35 modern member identity drift: 2026/0604800M$"):
        member_row(F35, {**row, "organization": "F"})


def test_a_member_ending_at_pb2020_is_not_missing_afterwards():
    a = _row("0207142F", 2020, exhibit="R-1", account="3600F", organization="F", title="F-35 Squadrons", amount_type="fy_2018_actuals")
    b = _row("0207142F", 2021, exhibit="R-1", account="3600F", organization="F", title="F-35 Squadrons", amount_type="fy_2019_actuals")
    payload, *_ = build_history(F35, [a, b], [_point(a, fy=2018), _point(b, fy=2019)], retrieved_at="2026-10-21")
    missing = {p["edition"]: p["missing_programs"] for p in payload["points"]}
    assert missing == {2020: ["0152", "0604800M", "0604810N", "ATA000"], 2021: ["0152", "0604800M", "ATA000"]}


def test_era_roster_attribution_counts_as_present():
    era = _row("3010F-AF-L1", 2020, exhibit="P-1", account="3010F", organization="AF", title="F-35", amount_type="fy_2018_actuals")
    payload, *_ = build_history(F35, [era], [_point(era, fy=2018)], retrieved_at="2026-10-21")
    (point,) = payload["points"]
    assert point["missing_programs"] == ["0152", "0207142F", "0604800M", "0604810N"]
    assert point["components"][0]["program_slug"] is None and point["components"][0]["dataset"] == "budget_lines_decade"


def test_a_context_row_is_never_summed_and_silences_the_guard():
    ata = _row("ATA000", 2026, exhibit="P-1", account="3010F", organization="F", title="F-35", cells="J10")
    jsm = _row("JSM000", 2026, exhibit="P-1", account="3020F", organization="F", title="Joint Strike Missile", cells="J11")
    assert member_row(F35, jsm) is False
    payload, _, leaves, _ = build_history(F35, [ata, jsm], [_point(ata), _point(jsm)], retrieved_at="2026-10-21")
    assert [c["pe_bli"] for c in payload["points"][0]["components"]] == ["ATA000"] and len(leaves) == 1


def test_an_unreviewed_joint_strike_row_raises():
    row = _row("JSF999", 2026, exhibit="P-1", account="3010F", organization="F", title="JOINT STRIKE SPARES")
    with pytest.raises(ValueError, match=r"^Unreviewed F-35 workbook identity: 2026/JSF999$"):
        member_row(F35, row)


def test_a_code_keyed_row_outside_titles_seen_is_identity_drift():
    row = _row("0604810N", 2021, exhibit="R-1", account="1319N", organization="N", title="JSF Follow-On Modernization")
    with pytest.raises(ValueError, match=r"^F-35 modern member identity drift: 2021/0604810N$"):
        member_row(F35, row)


def test_a_multi_input_cell_mints_the_family_dataset_and_cell_formula():
    first = _row("ATA000", 2026, exhibit="P-1", account="3010F", organization="F", title="F-35", value=100, cells="J10")
    second = {**first, "budget_activity": "05", "amount_thousands": 20, "cells": "J20"}
    payload, _, leaves, _ = build_history(F35, [first, second], [_point(first, n=2, amount=120)], retrieved_at="2026-10-21")
    enriched, additions, _ = build_program_matrix(F35, payload, _previews(leaves, F35), existing_citations={}, retrieved_at="2026-10-21")
    (cell,) = enriched["points"][0]["program_cells"]
    assert cell["dataset"] == "f35_funding_history" and cell["amount_thousands"] == 120
    assert cell["fact_id"] == fact_id_derived("family_program_history", "P-1:3010F:AF:ATA000|2026|2024", "actuals")
    assert additions[cell["fact_id"]]["formula"] == ("sum(budget_lines.amount_thousands) for workbook program "
                                                     "P-1:3010F:AF:ATA000, PB2026, FY2024 actuals; each selected workbook input once")
    assert enriched["programs"] == program_entries(F35)
    assert [p["id"] for p in enriched["programs"]] == [m.member_id for m in F35.counted]


def test_expected_members_reproduces_the_88538c6a_f15_rule():
    for edition in range(2017, 2027):
        today = {"0207134F", "0207171F"} | ({"0207146F"} if edition >= 2021 else set()) \
            | ({"F01500", "F015EX", "F15EWS"} if edition >= 2024 else set())
        assert expected_members(F15, edition) == frozenset(today), edition


def test_check_headline_refuses_a_window_unlike_the_registry():
    assert check_headline(F35, {"cumulative": {"start_fy": 2015, "end_fy": 2024}}) is None
    with pytest.raises(ValueError, match=r"^F-35 cumulative window FY2016–FY2024 differs from the registry headline FY2015–FY2024$"):
        check_headline(F35, {"cumulative": {"start_fy": 2016, "end_fy": 2024}})


def test_the_f15_facade_delegates_to_the_generic_builder():
    from govbudget import f15_funding_history as facade
    row = _row("0207130F", 2026, exhibit="R-1", account="3600F", organization="F", title="F-15 Squadrons")
    with pytest.raises(ValueError, match=r"^Unreviewed F-15 workbook identity: 2026/0207130F$"):
        facade.member_row(row)
    assert facade.PROGRAMS == program_entries(facade.F15) and facade.F15 == F15
    assert facade._json_bytes is _json_bytes
