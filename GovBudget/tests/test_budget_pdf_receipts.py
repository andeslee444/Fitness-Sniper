"""Evidence tests: figures must match the same line and fiscal column, not just a numeral."""
import json
from pathlib import Path

import pytest

from govbudget.budget_pdf_receipts import (
    amount,
    combine_receipts,
    match_cell,
    normalize_header,
    page_columns,
    pdf_header_key,
)


def word(text, x0, top, x1=None):
    return dict(text=text, x0=x0, x1=x1 if x1 is not None else x0 + 4 * len(text), top=top, bottom=top + 8)


def procurement_page(title="F-15", amount_text="100"):
    words = [word("(Dollars", 330, 70), word("FY", 300, 100), word("2024", 312, 100), word("Actuals", 300, 110), word("FY", 400, 100), word("2025", 412, 100), word("Enacted", 400, 110), word("No", 10, 120), word("Ident", 250, 110), word("Code", 250, 120), word("Cost", 334, 120, 350), word("Cost", 434, 120, 450), word("1", 10, 150), word(title, 40, 150), word("A", 250, 150), word(amount_text, 320, 150, 350), word("100", 430, 150, 450), word("2", 10, 200), word("F-16", 40, 200), word("A", 250, 200), word("900", 330, 200, 350), word("900", 430, 200, 450)]
    return dict(page_number=1, width=792, height=612, text="Department of the Air Force\nAppropriation: 3010F\n(Dollars in Thousands)", words=words)


def row(**changes):
    return dict(account="3010F", activity="05", line="1", code="F01500", title="F-15", cost_type="A") | changes


def test_column_identity_disambiguates_repeated_amounts():
    page = procurement_page()
    result = match_cell(page, row(), "FY 2024 Actuals Amount", 100, "P-1", 2026)
    assert result["word"]["x1"] == 350
    other = match_cell(page, row(), "FY 2025 Enacted Amount", 100, "P-1", 2026)
    assert other["word"]["x1"] == 450
    assert match_cell(page, row(), "FY 2025 Request Amount", 100, "P-1", 2026) is None
    assert match_cell(page, row(), "FY 2024 Actuals Amount", 101, "P-1", 2026) is None


def test_identical_amount_on_another_aircraft_line_or_account_is_not_evidence():
    page = procurement_page(title="F-15EX")
    assert match_cell(page, row(), "FY 2024 Actuals Amount", 100, "P-1") is None
    assert match_cell(page, row(title="F-15EX", code="F015EX"), "FY 2024 Actuals Amount", 100, "P-1")
    assert match_cell(page, row(account="3020F", title="F-15EX"), "FY 2024 Actuals Amount", 100, "P-1") is None
    assert match_cell(page, row(line="2"), "FY 2024 Actuals Amount", 900, "P-1") is None


def test_multiword_title_is_exact_not_a_prefix():
    page = procurement_page(title="F-15 EPAW")
    page["words"] = [w for w in page["words"] if w["text"] != "F-15 EPAW"] + [word("F-15", 40, 150), word("EPAW", 64, 150)]
    assert match_cell(page, row(title="F-15 EPAW", code="F15EWS"), "FY 2024 Actuals Amount", 100, "P-1")
    assert match_cell(page, row(), "FY 2024 Actuals Amount", 100, "P-1") is None


def test_parenthesized_gross_amount_is_positive_and_explicit_minus_is_preserved():
    assert amount("(2,619,687)") == 2619687
    assert amount("(-147,919)") == -147919
    assert amount("—") is None
    page = procurement_page(amount_text="(100)")
    assert match_cell(page, row(), "FY 2024 Actuals Amount", 100, "P-1")["word"]["text"] == "(100)"
    page["words"] += [word("Less:", 40, 162), word("Advance", 68, 162), word("Procurement", 104, 162), word("(PY)", 155, 162), word("(-20)", 330, 162, 350)]
    matched = match_cell(page, row(cost_type="B"), "FY 2024 Actuals Amount", -20, "P-1")
    assert matched["word"]["text"] == "(-20)"
    assert match_cell(page, row(cost_type="B"), "FY 2024 Actuals Amount", 20, "P-1") is None


def test_blank_zero_has_no_invented_highlight_and_missing_positive_is_not_a_zero():
    page = procurement_page()
    page["words"] = [w for w in page["words"] if not (w["top"] == 150 and w["x1"] == 350)]
    match = match_cell(page, row(), "FY 2024 Actuals Amount", 0, "P-1")
    assert match["blank_zero"] is True
    assert "word" not in match
    assert match_cell(page, row(), "FY 2024 Actuals Amount", 100, "P-1") is None


def test_printed_zero_can_be_highlighted():
    result = match_cell(procurement_page(amount_text="0"), row(), "FY 2024 Actuals Amount", 0, "P-1")
    assert result["word"]["text"] == "0"
    assert "blank_zero" not in result


def test_advance_procurement_before_its_line_requires_the_same_prior_aircraft():
    page = procurement_page()
    page["words"] = [w for w in page["words"] if not (w["top"] == 200 and w["text"] in {"F-16", "A", "900"})]
    page["words"] += [word("F-15", 40, 200), word("Advance", 40, 185), word("Procurement", 76, 185), word("(CY)", 127, 185), word("80", 340, 185, 350)]
    assert match_cell(page, row(line="2", cost_type="C"), "FY 2024 Actuals Amount", 80, "P-1")["word"]["text"] == "80"
    page["words"] = [dict(w, text="F-15EX") if w["top"] == 150 and w["text"] == "F-15" else w for w in page["words"]]
    assert match_cell(page, row(line="2", cost_type="C"), "FY 2024 Actuals Amount", 80, "P-1") is None


def test_fiscal_year_and_scenario_terms_remain_distinct():
    assert normalize_header("FY 2024 Actuals Amount") == normalize_header("FY 2024 Actual*")
    assert normalize_header("FY 2026 Disc Request") != normalize_header("FY 2026 Total")
    assert normalize_header("FY 2023 Total Enacted") != normalize_header("FY 2023 Less Supplementals Enacted")
    assert normalize_header("FY 2023 Supplementals Enacted") != normalize_header("FY 2023 Total Enacted")


def test_known_pb2025_cr_label_alias_never_spills_into_other_books():
    workbook = "FY 2024 PB Request with CR Amounts*"
    printed = "FY 2024 PB Request with CR Adjustments*"
    assert pdf_header_key(workbook, edition=2025, exhibit="R-1") == normalize_header(printed)
    assert pdf_header_key(workbook, edition=2024, exhibit="R-1") != normalize_header(printed)
    assert pdf_header_key(workbook, edition=2025, exhibit="P-1") != normalize_header(printed)
    assert pdf_header_key(workbook.replace("2024", "2023"), edition=2025, exhibit="R-1") != normalize_header(printed.replace("2024", "2023"))


def test_total_requires_all_inputs_even_when_unmatched_values_cancel():
    good = dict(complete=True, unmatched_count=0, blank_zero_count=1, parts=[dict(amount_thousands=120), dict(amount_thousands=-20)])
    total = combine_receipts([good], 100)
    assert total["complete"] and total["matched_amount_thousands"] == 100 and total["blank_zero_count"] == 1
    missing = dict(complete=False, unmatched_count=2, blank_zero_count=0, parts=[])
    assert not combine_receipts([good, missing], 100)["complete"]
    assert not combine_receipts([good], 120)["complete"]


def test_shipped_f15_evidence_preserves_all_default_and_historical_cells():
    root = Path(__file__).resolve().parents[1] / "data/site/json"
    if not (root / "budget_pdf_receipts_audit.json").exists():
        pytest.skip("Run export_budget_pdf_receipts.py against the local site export")
    audit = json.loads((root / "budget_pdf_receipts_audit.json").read_text())
    assert audit["source_count"] == 20
    assert audit["leaf_count"] == 207
    assert audit["default_complete"] == audit["default_cells"] == 67
    assert audit["unmatched_cells"] == []
    receipts = {}
    shards = list((root / "budget-pdf-receipts").glob("*.json"))
    assert len(shards) == 256
    for shard in shards:
        receipts.update(json.loads(shard.read_text()))
    history = json.loads((root / "f15_funding_history.json").read_text())
    for point in history["points"]:
        for cell in point["program_cells"]:
            receipt = receipts[cell["fact_id"]]
            assert receipt["complete"]
            assert sum(p["amount_thousands"] for p in receipt["parts"]) == cell["amount_thousands"]
            assert receipt["unmatched_count"] == 0
    assert receipts[history["cumulative"]["fact_id"]]["amount_thousands"] == history["cumulative"]["amount_thousands"]
