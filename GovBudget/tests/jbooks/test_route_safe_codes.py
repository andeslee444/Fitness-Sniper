"""jbooks/route_safe_codes.py — the owner-approved page keys for printed
codes a web address cannot carry, and the P-1 lines that restate R-1
program elements (families piece-1 follow-ups design §4.2–§4.3, #194;
owner decisions 2026-10-04: Q1 (a), Q2)."""
from datetime import date
from pathlib import Path

import pytest

from govbudget.export_site import is_route_safe_pe
from govbudget.jbooks import route_safe_codes as rsc
from govbudget.jbooks.route_safe_codes import (
    P1_R1_RESTATEMENTS,
    R1_AMOUNT_TYPE_EQUIVALENTS,
    SEED_COLUMNS,
    R1Restatement,
    RouteSafeCode,
    by_page_key,
    is_route_safe_code,
    load_route_safe_codes,
    page_key,
    read_route_safe_codes,
    restated_lines,
)

HEADER = ",".join(SEED_COLUMNS)
OM_ROW = '0390D,O&M,0390DOM,om,2026-10-04,owner,"a note, with a comma"'


def _seed(tmp_path: Path, *lines: str, header: str = HEADER) -> Path:
    p = tmp_path / "p1_route_safe_codes.csv"
    p.write_text("\n".join([header, *lines]) + "\n", encoding="utf-8")
    return p


def test_the_committed_seed_holds_exactly_the_owner_approved_o_and_m_key():
    codes = load_route_safe_codes()
    assert list(codes) == [("0390D", "O&M")]
    om = codes[("0390D", "O&M")]
    assert (om.page_key, om.exhibit_family, om.decided_on, om.decided_by) == (
        "0390DOM", "om", date(2026, 10, 4), "owner")
    assert om.line_item_code == "O&M" and om.account == "0390D"


def test_page_key_and_reverse_lookup():
    assert page_key("0390D", "O&M") == "0390DOM"
    assert page_key("0390D", "RDT&E") is None       # Q1 (a): no page
    assert page_key("2035A", "O&M") is None         # another account
    assert by_page_key()["0390DOM"].line_item_code == "O&M"


def test_the_rdte_line_is_a_recorded_r1_restatement():
    assert P1_R1_RESTATEMENTS == {
        ("0390D", "RDT&E"): R1Restatement(
            title="Chem Demilitarization - RDT&E",
            program_elements=("0708081D", "0708083D")),
    }
    assert R1_AMOUNT_TYPE_EQUIVALENTS == {
        "fy_2024_pb_request_with_cr_adjustments": "fy_2024_pb_request_with_cr_amounts"}
    assert restated_lines("0390D") == [{
        "line_item_code": "RDT&E", "title": "Chem Demilitarization - RDT&E",
        "program_elements": ["0708081D", "0708083D"]}]
    assert restated_lines("2035A") == []


@pytest.mark.parametrize("code", ["O&M", "RDT&E", "A/B", "A?B", "A%B", "A#B",
                                  "A B", "A\tB", "D15610", "0390DOM", "46-1"])
def test_route_safety_mirrors_the_exporter(code):
    assert is_route_safe_code(code) is is_route_safe_pe(code)


def test_a_valid_seed_reads_back(tmp_path):
    codes = read_route_safe_codes(_seed(tmp_path, OM_ROW))
    assert codes == {("0390D", "O&M"): RouteSafeCode(
        account="0390D", line_item_code="O&M", page_key="0390DOM",
        exhibit_family="om", decided_on=date(2026, 10, 4), decided_by="owner",
        note="a note, with a comma")}


@pytest.mark.parametrize("lines, header, match", [
    ([OM_ROW], "account,line_item_code,page_key", "header"),
    (["0390D,O&M,0390-DOM,om,2026-10-04,owner,"], HEADER, r"is not \[A-Z0-9\]\+"),
    (["0390D,O&M,0390dom,om,2026-10-04,owner,"], HEADER, r"is not \[A-Z0-9\]\+"),
    ([OM_ROW, "0390D,A/B,0390DOM,om,2026-10-04,owner,"], HEADER, "repeats"),
    (["0390D,PROC,0390DPROC,om,2026-10-04,owner,"], HEADER, "already route-safe"),
    ([OM_ROW, "0390D,O&M,0390DOM2,om,2026-10-04,owner,"], HEADER, "repeats"),
    (["0390D,RDT&E,0390DRDTE,rdte,2026-10-04,owner,"], HEADER, "R-1 restatement"),
    (["0390D,O&M,0390DOM,,2026-10-04,owner,"], HEADER, "exhibit_family is blank"),
    (["0390D,O&M,0390DOM,om,04/10/2026,owner,"], HEADER, "not an ISO date"),
    (["0390D,O&M,0390DOM,om,2026-10-04,claude,"], HEADER, "not 'owner'"),
])
def test_a_bad_seed_is_refused(tmp_path, lines, header, match):
    with pytest.raises(ValueError, match=match):
        read_route_safe_codes(_seed(tmp_path, *lines, header=header))


def test_the_default_path_is_the_dbt_seed():
    assert rsc.default_seed_path().parts[-3:] == ("dbt", "seeds", "p1_route_safe_codes.csv")
