"""Receipt scale follows the source page and its own canonical amount."""
from decimal import Decimal

import pytest

from govbudget.jbooks.citation_units import jbook_pdf_citation_units, pdf_page_currency_units


def test_f15ex_thousands_token_keeps_its_78345_million_canonical_amount():
    assert jbook_pdf_citation_units("78,345", Decimal("78.345"), source_units=pdf_page_currency_units("Exhibit R-1\n(Dollars in Thousands)")) == "USD thousands"


@pytest.mark.parametrize("header,expected", [
    ("(Dollars in Thousands)", "USD thousands"),
    ("COST ($ in Millions)", "USD millions"),
    ("Total Cost ($ in millions)", "USD millions"),
    ("Quantity (Units in Each)", None),
    ("Dollars in Thousands; Unit Cost ($ in Millions)", None),
])
def test_requires_an_explicit_unambiguous_currency_scale(header, expected):
    assert pdf_page_currency_units(header) == expected


@pytest.mark.parametrize("token,value", [("5.112", "5.112"), ("1,808.472", "1808.472"), ("5,423.418", "5423.418")])
def test_existing_f15_procurement_million_receipts_remain_millions(token, value):
    assert jbook_pdf_citation_units(token, Decimal(value)) == "USD millions"


@pytest.mark.parametrize("source_units", [None, "USD millions", "USD"])
def test_ratio_alone_cannot_prove_thousands(source_units):
    with pytest.raises(ValueError, match="explicit Dollars in Thousands"):
        jbook_pdf_citation_units("2", Decimal("0.002"), source_units=source_units)


@pytest.mark.parametrize("token,value,units", [
    ("78,345", "78.344", "USD thousands"),
    ("78.345", "78.345", "USD thousands"),
    ("NaN", "1", None), ("-", "1", None), ("12,34", "12.34", None),
    ("0", "0", "USD thousands"), ("1", "NaN", None),
])
def test_rejects_inconsistent_values_instead_of_guessing(token, value, units):
    with pytest.raises(ValueError):
        jbook_pdf_citation_units(token, value, source_units=units)


def test_negative_source_amounts_retain_their_sign():
    assert jbook_pdf_citation_units("(1,200)", "-1.200", source_units="USD thousands") == "USD thousands"
