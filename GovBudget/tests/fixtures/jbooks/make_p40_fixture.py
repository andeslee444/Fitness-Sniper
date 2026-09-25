#!/usr/bin/env python3
"""Generate tests/fixtures/jbooks/p40_resource_summary.pdf.

A synthetic, P-40-shaped Resource Summary page for the row-label leg's
procurement branch (`exhibit_family == "procurement"`), which had zero
coverage before this fixture: no test passed `exhibit_family="procurement"`
and the DARPA R-2 fixture has no `Obligation` word anywhere, so
`_row_basis_check` — the P0-1 check — was never exercised end to end.

The venv carries no PDF writer (no reportlab, no fpdf), so the page is
emitted as a hand-written PDF 1.4 with a base-14 Helvetica font and one
`Tj` per cell. Extraction in the tests goes through real `pdfplumber`
words, never a mocked list.

Two properties this page exists to have (tests/test_verify_phase5b1.py): the
first is asserted by `test_fixture_value_columns_are_right_aligned`; the second
is what `test_highlight_off_the_toa_row_with_a_different_basis_fails` relies on
when it requires the failure to name the FY 2025 column's TOA (407.046) rather
than the FY 2024 column's (97.500):

  * value columns are RIGHT-aligned, so a cell's `x0` moves with the number's
    WIDTH (a Helvetica digit is 0.556 em: at 9 pt one character is 5.0 pt,
    well past the 2.0 pt column tolerance the leg used to apply to `x0`)
    while its right edge does not. That is the reviewer's exemplar (doc
    e7e1302…, page 223: column right edge x1 368.5 holds `407.046` at x0
    343.3 and `52.191` at x0 347.1) and the reason a left-edge match is
    wrong: it finds the TOA cell only when the two numbers are the same
    width, i.e. it goes blind precisely when they disagree. The leg matches
    the column by SPAN OVERLAP rather than by either edge alone, because a
    footnote marker inside a cell moves the right edge too (see
    _toa_column_value).
  * TWO value columns, so matching the wrong one is visible: the FY 2025
    column's TOA reads 407.046, the FY 2024 column's reads 97.500.

Run: uv run --no-sync python tests/fixtures/jbooks/make_p40_fixture.py
"""
from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent / "p40_resource_summary.pdf"

FONT_SIZE = 9.0
PAGE_W, PAGE_H = 612.0, 792.0

# Adobe Helvetica AFM widths, /1000 em — only the glyphs the value columns
# use. Right-alignment is computed, not eyeballed, so the two columns land on
# an exact shared right edge.
_W = {".": 278, ",": 278}
for _d in "0123456789":
    _W[_d] = 556


def _num_width(s: str) -> float:
    return sum(_W[c] for c in s) * FONT_SIZE / 1000.0


# (label, FY2024 cell, FY2025 cell) — one P-40 Resource Summary block.
# FY 2025: Net Procurement 52.191 against a Total Obligation Authority of
# 407.046 is P0-1's species (the published basis is TOA; the highlight sits
# on Net Procurement) with the two cells at different widths.
ROWS = [
    ("Gross/Weapon System Cost ($ in Millions)", "100.000", "459.237"),
    ("Less PY Advance Procurement ($ in Millions)", "1.000", "12.500"),
    ("Plus CY Advance Procurement ($ in Millions)", "2.000", "3.100"),
    ("Net Procurement (P-1) ($ in Millions)", "97.000", "52.191"),
    ("Plus Cost To Complete ($ in Millions)", "0.500", "0.000"),
    ("Total Obligation Authority ($ in Millions)", "97.500", "407.046"),
]

COL_RIGHT = (300.0, 368.5)   # the two value columns' shared right edges
LABEL_X = 54.0
FIRST_ROW_TOP = 150.0
ROW_PITCH = 15.0

HEADINGS = [
    (54.0, 60.0, "UNCLASSIFIED"),
    (54.0, 75.0, "Exhibit P-40, Budget Line Item Justification: PB 2026 Air Force"),
    (54.0, 90.0, "Appropriation / Budget Activity / Budget Sub Activity: 3010F / 01 / 05"),
    # The BLI is printed here and nowhere else: the row-label leg accepts a
    # bare Resource Summary label only when the fact's pe_bli appears on the
    # page, so a fixture without this line would be rejected, not skipped.
    (54.0, 105.0, "P-1 Line Item Number / Title: 0449 / Test Procurement Line"),
    (54.0, 130.0, "Resource Summary"),
    (247.0, 130.0, "FY 2024"),
    (315.0, 130.0, "FY 2025"),
]


def _esc(s: str) -> str:
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _text(x: float, top: float, s: str) -> str:
    """One Helvetica text object. `top` is from the page TOP, as pdfplumber reports."""
    y = PAGE_H - top - FONT_SIZE
    return f"BT /F1 {FONT_SIZE} Tf 1 0 0 1 {x:.3f} {y:.3f} Tm ({_esc(s)}) Tj ET\n"


def build() -> bytes:
    content = "".join(_text(x, top, s) for x, top, s in HEADINGS)
    for i, (label, c1, c2) in enumerate(ROWS):
        top = FIRST_ROW_TOP + i * ROW_PITCH
        content += _text(LABEL_X, top, label)
        for cell, right in ((c1, COL_RIGHT[0]), (c2, COL_RIGHT[1])):
            content += _text(right - _num_width(cell), top, cell)
    stream = content.encode("latin-1")

    objs = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        (
            b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"
        ),
        b"<</Length " + str(len(stream)).encode() + b">>\nstream\n" + stream + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica/Encoding/WinAnsiEncoding>>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<</Size {len(objs) + 1}/Root 1 0 R>>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    return bytes(out)


if __name__ == "__main__":
    OUT.write_bytes(build())
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
