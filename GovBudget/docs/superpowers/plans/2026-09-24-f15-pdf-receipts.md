# F-15 PDF receipts and named workbook downloads

The family funding matrix keeps its workbook amounts and fiscal statuses. Clicking a funded cell leads with the corresponding official P-1 or R-1 PDF and an overlay on the exact printed amount. A program/year total containing multiple government lines exposes each contribution separately; it never claims the computed total is printed in one location.

Matching requires the same budget edition, service/account, line/PE, fiscal-year column and amount. Advance-procurement deductions retain their sign. Blank PDF cells cannot become zero-number highlights. Partial matches retain the original spreadsheet evidence and explain the gap. R-2/P-40 justification figures are not substituted for P-1/R-1 total obligational authority.

PDF source bytes are saved by SHA-256 with direct government page links. Verified geometry and arithmetic live in on-demand receipt shards, keeping the full matrix's initial payload bounded. The PDF viewer uses the source page's dimensions, supports selectable text, and provides an enlarged view.

Highlight geometry uses the visible PDF crop frame, including nonzero page origins. After the budget row and column are verified, exact source text and its first-character origin identify the same printed token in PDFium. Tight glyph outlines set the displayed rectangle; font-em boxes do not reliably enclose digits in every edition. Ambiguous identities and unsupported page geometry fail export. Closing the enlarged view returns keyboard focus to the opening button.

Spreadsheet actions fetch the saved government bytes, verify SHA-256, then initiate a real browser download. Filenames describe the full document and publication edition, for example `PB2026_DoD_P-1_Procurement.xlsx`. Downloads do not imply that the complete workbook covers only F-15 or only the clicked historical year. The government original remains linked.

Validation includes matching/mismatch and contribution tests; PDF highlights and downloads in the browser; existing provenance and matrix checks; release gates; and production verification after asset-first deployment.

PB2025 R-1 uses a reviewed, edition-scoped header equivalence: workbook "FY 2024 PB Request with CR Amounts*" and PDF "FY 2024 PB Request with CR Adjustments*". Both carry the same annualized continuing-resolution footnote; this does not equate CR estimates with final enactment.

## Sitewide standard and regeneration

The PDF-first receipt is the standard for program funding across the site. P-1, R-1 and P-1R workbook citations use the same budget edition's government PDF. Verified line items have a highlighted receipt action plus a direct government PDF link; a named download of the original workbook remains available. Program source sections show both budget totals and detailed justification sources, with related TOA spreadsheets labeled as a different accounting basis from R-2/P-40 details.

The normal `.venv/bin/python -m govbudget export-site` command now regenerates PDF evidence after the full artifact export, including F-15 family-history facts. It uses the sitewide reviewed registry at `data-seeds/budget_pdf_sources.json`. Source PDFs are reused by SHA-256 when present; missing source PDFs are downloaded from their pinned official URLs. Hash changes or canonical arithmetic mismatches fail the command rather than publish a claimed match.

To regenerate evidence against an already exported site bundle, run `.venv/bin/python -m govbudget export-budget-pdf-receipts` or the existing `.venv/bin/python scripts/export_budget_pdf_receipts.py` wrapper. Both default to the sitewide exporter and accept `--site-dir`, `--manifest` and `--cache-dir`. These are complete evidence refreshes, not edition-specific patches. The low-level `export_site()` Python function remains a local artifact operation so its small synthetic warehouse tests never fetch PDFs; production and refresh workflows use the CLI above.

Evidence is emitted to `json/budget-pdf-receipts/v2/` in 4,096 shards keyed by the first three fact-ID characters. Existing two-character F-15 shards remain available to older deployed clients. Detailed coverage and unmatched cells are recorded in `json/budget_pdf_receipts_audit.json`; the CLI prints a concise completion count and its path.

Matching a document is separate from matching its printed amount. If a reviewed book is available but the exact amount is not verified, the source action links the government PDF without claiming a page highlight and keeps the spreadsheet receipt visible. Partial matches identify only verified contributions. Blank PDF entries retain their zero spreadsheet evidence without an invented printed zero. Only validated additive TOA sums inherit combined PDF receipts; differences, percentages, obligations, and R-2/P-40 detail retain their own receipts and accounting context. No program/year name match alone establishes spreadsheet equivalence.

Sitewide validation scanned 21 pinned government books across PB2017–PB2026: 41,772 of 42,153 workbook receipts fully reconcile, and 46,682 of 47,081 receipts including additive totals are complete. All original 276 F-15 receipts and 67 default matrix cells remain complete. Of 1,655 current program FY2026 totals, 1,653 fully reconcile; the remaining two retain explicit partial/source-only evidence. Zero cells without printed numbers do not acquire highlights. The audit records every unmatched cell and any geometry disagreement.

Production builds require the complete v2 shard set, a full-corpus audit, and the current citation-bundle checksum. Edition-only probes or evidence generated before a citation refresh cannot pass prebuild. Source matching rejects transformed formulas and overlapping workbook inputs; continuation receipts link the PDF page containing the program heading as well as the amount page.
