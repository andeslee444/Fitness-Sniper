"""Sitewide receipts keep source identity and additive TOA provenance intact."""
import copy
import json

import openpyxl
import pytest

from govbudget.program_pdf_receipts import (
    attach_additive_receipts,
    metadata_for_row,
    source_identity,
)


LEAF_A = "a" * 16
LEAF_B = "b" * 16
SUBTOTAL = "c" * 16
TOTAL = "d" * 16


@pytest.mark.parametrize(
    ("url", "identity"),
    [
        ("https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p1_display.xlsx", (2026, "P-1")),
        ("https://comptroller.defense.gov/Portals/45/Documents/defbudget/fy2017/r1_display.xlsx", (2017, "R-1")),
        ("https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p1r_display.xlsx", (2026, "P-1R")),
        ("https://COMPTROLLER.DEFENSE.GOV/Portals/45/Documents/defbudget/FY2024/R1_DISPLAY.XLSX", (2024, "R-1")),
    ],
)
def test_source_identity_is_the_official_workbook_edition_and_exhibit(url, identity):
    # A program fiscal year must not override the workbook's budget edition.
    assert source_identity({"official_url": url, "edition": 9999, "fy": 2024}) == identity


@pytest.mark.parametrize("url", [
    None,
    "",
    "http://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p1_display.xlsx",
    "https://comptroller.war.gov.evil.example/Portals/45/Documents/defbudget/FY2026/p1_display.xlsx",
    "https://evil.example/comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p1_display.xlsx",
    "https://comptroller.war.gov@evil.example/Portals/45/Documents/defbudget/FY2026/p1_display.xlsx",
    "https://example.mil/Portals/45/Documents/defbudget/FY2026/p1_display.xlsx",
    "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY26/p1_display.xlsx",
    "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p40_display.xlsx",
    "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p1_display.xls",
    "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p1_display.xlsx?edition=2025",
    "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p1_display.xlsx#FY2025",
    "https://comptroller.war.gov/Portals/45/Documents/defbudget/FY2026/p1_display.xlsx\n",
])
def test_source_identity_rejects_unreviewed_publishers_paths_and_suffixes(url):
    assert source_identity({"official_url": url}) is None


@pytest.mark.parametrize(
    ("exhibit", "cells", "expected"),
    [
        ("P-1", {"A": "3010F", "D": "05", "F": " 134 ", "G": "DECOY-CODE", "H": "DECOY-TITLE", "I": "F015EX", "J": "F-15EX", "K": "A", "L": "Gross weapon system cost"},
         {"account": "3010F", "activity": "05", "line": "134", "code": "F015EX", "title": "F-15EX", "cost_type": "A", "row_label": "Gross weapon system cost"}),
        ("R-1", {"A": "3600F", "D": "07", "F": " 203 ", "G": "0207134F", "H": "F-15E Squadrons", "I": "DECOY-CODE", "J": "DECOY-TITLE", "K": None},
         {"account": "3600F", "activity": "07", "line": "203", "code": "0207134F", "title": "F-15E Squadrons", "cost_type": "None"}),
        ("P-1R", {"A": "1506N", "D": "01", "F": "DECOY-LINE", "G": "DECOY-CODE", "H": "0123", "I": "Reserve Aircraft", "J": "C", "K": "Advance procurement (CY)"},
         {"account": "1506N", "activity": "01", "line": "", "code": "0123", "title": "Reserve Aircraft", "cost_type": "C", "row_label": "Advance procurement (CY)"}),
    ],
)
def test_each_workbook_exhibit_uses_its_own_program_identity_columns(exhibit, cells, expected):
    workbook = openpyxl.Workbook()
    try:
        for column, value in cells.items():
            workbook.active[f"{column}17"] = value
        actual = metadata_for_row(workbook.active, 17, exhibit)
        assert {key: actual[key] for key in expected} == expected
    finally:
        workbook.close()


def source_document(identity="a"):
    return {"official_url": f"https://example.gov/{identity}.pdf", "sha256": identity * 64, "edition": 2026, "exhibit": "P-1"}


def leaf_receipt(value, *, complete=True, identity="a", blanks=0, missing=0):
    return {
        "amount_thousands": value,
        "matched_amount_thousands": value if complete else 0,
        "complete": complete,
        "blank_zero_count": blanks,
        "unmatched_count": missing,
        "parts": [{"amount_thousands": value, "workbook_cell": "W17"}] if complete and value else [],
        "source_documents": [source_document(identity)],
    }


def derived(inputs, value, *, formula="sum(budget_lines.amount_thousands where amount_type=fy_2026_total)", units="USD thousands"):
    return {"kind": "derived", "units": units, "formula": formula, "inputs": json.dumps(inputs), "recorded_value": str(value)}


def test_additive_toa_receipt_preserves_signed_parts_and_canonical_input_receipts():
    receipts = {LEAF_A: leaf_receipt(120), LEAF_B: leaf_receipt(-20)}
    original = copy.deepcopy(receipts)
    citations = {TOTAL: derived([LEAF_A, LEAF_B], 100)}
    attach_additive_receipts(citations, receipts)
    assert receipts[TOTAL]["amount_thousands"] == 100
    assert receipts[TOTAL]["matched_amount_thousands"] == 100
    assert receipts[TOTAL]["complete"] is True
    assert [part["amount_thousands"] for part in receipts[TOTAL]["parts"]] == [120, -20]
    assert receipts[TOTAL]["source_documents"] == [source_document()]
    assert {fact: receipts[fact] for fact in original} == original


def test_nested_additive_totals_resolve_without_order_dependence_and_keep_distinct_books():
    receipts = {LEAF_A: leaf_receipt(120), LEAF_B: leaf_receipt(30, identity="b")}
    citations = {
        TOTAL: derived([SUBTOTAL, LEAF_B], 150, formula="sum(budget_lines.amount_thousands) for reviewed F-15 members, PB2026, FY2026 request; one selected scenario column per workbook line"),
        SUBTOTAL: derived([LEAF_A], 120),
    }
    attach_additive_receipts(citations, receipts)
    assert receipts[SUBTOTAL]["amount_thousands"] == 120
    assert receipts[TOTAL]["amount_thousands"] == 150
    assert receipts[TOTAL]["complete"]
    assert {document["sha256"] for document in receipts[TOTAL]["source_documents"]} == {"a" * 64, "b" * 64}


def test_partial_evidence_does_not_become_complete_when_missing_values_cancel():
    receipts = {LEAF_A: leaf_receipt(100), LEAF_B: leaf_receipt(0, complete=False, blanks=1, missing=2)}
    attach_additive_receipts({TOTAL: derived([LEAF_A, LEAF_B], 100)}, receipts)
    assert receipts[TOTAL]["complete"] is False
    assert receipts[TOTAL]["unmatched_count"] == 2
    assert receipts[TOTAL]["blank_zero_count"] == 1
    assert receipts[TOTAL]["matched_amount_thousands"] == 100


@pytest.mark.parametrize(("formula", "units"), [
    ("FY2026 request - FY2025 total", "USD thousands"),
    ("(FY2026 request - FY2025 total) / FY2025 total * 100", "percent"),
    ("sum(jbook_details.amount_millions)", "USD millions"),
    ("sum(usaspending.obligations)", "USD thousands"),
    ("sum(budget_lines.amount_thousands)", "USD millions"),
    ("sum(budget_lines.amount_thousands) - 0", "USD thousands"),
    ("sum(budget_lines.amount_thousands) / 1", "USD thousands"),
])
def test_nonadditive_and_other_basis_figures_do_not_acquire_toa_receipts(formula, units):
    # Coincidental numerical equality is not proof of the same accounting measure.
    receipts = {LEAF_A: leaf_receipt(100)}
    attach_additive_receipts({TOTAL: derived([LEAF_A], 100, formula=formula, units=units)}, receipts)
    assert TOTAL not in receipts


def test_mixed_toa_and_jbook_detail_inputs_do_not_acquire_a_summed_pdf_receipt():
    receipts = {LEAF_A: leaf_receipt(100)}
    citations = {
        LEAF_B: {"kind": "jbook_pdf", "units": "USD millions", "amount_text": "0.100"},
        TOTAL: derived([LEAF_A, LEAF_B], 200),
    }
    attach_additive_receipts(citations, receipts)
    assert TOTAL not in receipts


@pytest.mark.parametrize("inputs", [[], ["https://example.gov/data"], ["not-a-fact"], [12], {LEAF_A: True}])
def test_additive_receipt_requires_an_explicit_array_of_input_fact_ids(inputs):
    receipts = {LEAF_A: leaf_receipt(100)}
    attach_additive_receipts({TOTAL: derived(inputs, 100)}, receipts)
    assert TOTAL not in receipts


def test_missing_input_and_cycles_fail_closed_without_blocking_an_independent_total():
    receipts = {LEAF_A: leaf_receipt(100)}
    independent = "e" * 16
    citations = {
        TOTAL: derived([LEAF_A, SUBTOTAL], 100),
        SUBTOTAL: derived([TOTAL], 0),
        LEAF_B: derived(["f" * 16], 100),
        independent: derived([LEAF_A], 100),
    }
    attach_additive_receipts(citations, receipts)
    assert TOTAL not in receipts and SUBTOTAL not in receipts and LEAF_B not in receipts
    assert receipts[independent]["complete"]


def test_canonical_amount_mismatch_stops_publication_instead_of_claiming_a_match():
    receipts = {LEAF_A: leaf_receipt(120), LEAF_B: leaf_receipt(-20)}
    with pytest.raises(ValueError, match="Additive budget receipt arithmetic differs"):
        attach_additive_receipts({TOTAL: derived([LEAF_A, LEAF_B], 99)}, receipts)
    assert TOTAL not in receipts


@pytest.mark.parametrize('formula', [
    'sum(budget_lines.amount_thousands) where amount_type=fy_2026_total/1',
    'sum(budget_lines.amount_thousands) where amount_type=fy_2026_total -0',
    'sum(budget_lines.amount_thousands) for reviewed F-15 members, PB2026/1',
])
def test_compact_operators_do_not_become_additive_receipts(formula):
    receipts = {LEAF_A: leaf_receipt(100)}
    attach_additive_receipts({TOTAL: derived([LEAF_A], 100, formula=formula)}, receipts)
    assert TOTAL not in receipts


def test_nested_inputs_cannot_count_the_same_workbook_cell_twice():
    receipts = {LEAF_A: leaf_receipt(100)}
    citations = {SUBTOTAL: derived([LEAF_A], 100), TOTAL: derived([SUBTOTAL, LEAF_A], 200)}
    attach_additive_receipts(citations, receipts)
    assert SUBTOTAL in receipts
    assert TOTAL not in receipts
