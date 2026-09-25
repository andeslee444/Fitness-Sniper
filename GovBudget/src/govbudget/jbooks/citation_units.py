"""Bind literal PDF amounts to their canonical amount without guessing a scale."""
from decimal import Decimal, InvalidOperation
import re


def pdf_page_currency_units(text: str) -> str | None:
    """Read an explicit dollar-scale declaration; mixed/absent declarations stay unknown."""
    declarations = {
        match.group(1).lower()
        for match in re.finditer(r"(?:\bdollars?\s+in\s+|\$\s*(?:in\s+)?)(thousands|millions)\b", text, re.IGNORECASE)
    }
    return f"USD {next(iter(declarations))}" if len(declarations) == 1 else None


def jbook_pdf_citation_units(amount_text: str, amount_millions, *, source_units: str | None = None) -> str:
    """Retain a matching canonical million value, or require proven thousand units.

    A thousands-looking ratio alone is insufficient: a wrong PDF locator can
    happen to hit that numeral. The scaled branch requires the page's explicit
    currency declaration as well as exact equality to the canonical amount.
    This function never changes the glyph, canonical amount, or fact identity.
    """
    if not isinstance(amount_text, str):
        raise ValueError("PDF citation amount_text must be a numeric source token")
    token = amount_text.strip()
    if token.startswith("(") and token.endswith(")"):
        token = "-" + token[1:-1]
    if not re.fullmatch(r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", token):
        raise ValueError("PDF citation amount_text must be a numeric source token")
    try:
        literal = Decimal(token.replace(",", ""))
        canonical = Decimal(str(amount_millions))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("PDF citation lacks a valid canonical amount") from exc
    if not literal.is_finite() or not canonical.is_finite() or canonical == 0:
        raise ValueError("PDF citation requires a finite nonzero canonical amount")
    if literal == canonical:
        if source_units not in (None, "USD millions"):
            raise ValueError("PDF page currency units contradict the canonical million amount")
        return "USD millions"
    if literal / Decimal(1000) == canonical:
        if source_units != "USD thousands":
            raise ValueError("Scaled PDF amount requires explicit Dollars in Thousands page evidence")
        return "USD thousands"
    raise ValueError("PDF source token does not equal its canonical amount at a supported dollar scale")
