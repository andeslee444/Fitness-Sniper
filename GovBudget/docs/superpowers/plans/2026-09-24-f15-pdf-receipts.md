# F-15 PDF receipts and named workbook downloads

The family funding matrix keeps its workbook amounts and fiscal statuses. Clicking a funded cell leads with the corresponding official P-1 or R-1 PDF and an overlay on the exact printed amount. A program/year total containing multiple government lines exposes each contribution separately; it never claims the computed total is printed in one location.

Matching requires the same budget edition, service/account, line/PE, fiscal-year column and amount. Advance-procurement deductions retain their sign. Blank PDF cells cannot become zero-number highlights. Partial matches retain the original spreadsheet evidence and explain the gap. R-2/P-40 justification figures are not substituted for P-1/R-1 total obligational authority.

PDF source bytes are saved by SHA-256 with direct government page links. Verified geometry and arithmetic live in on-demand receipt shards, keeping the full matrix's initial payload bounded. The PDF viewer uses the source page's dimensions, supports selectable text, and provides an enlarged view.

Spreadsheet actions fetch the saved government bytes, verify SHA-256, then initiate a real browser download. Filenames describe the full document and publication edition, for example `PB2026_DoD_P-1_Procurement.xlsx`. Downloads do not imply that the complete workbook covers only F-15 or only the clicked historical year. The government original remains linked.

Validation includes matching/mismatch and contribution tests; PDF highlights and downloads in the browser; existing provenance and matrix checks; release gates; and production verification after asset-first deployment.

Refresh evidence with `.venv/bin/python scripts/export_budget_pdf_receipts.py` after exporting family history. The source registry is `data-seeds/f15_budget_pdf_sources.json`; source hash changes require review. PB2025 R-1 uses a reviewed, edition-scoped header equivalence: workbook "FY 2024 PB Request with CR Amounts*" and PDF "FY 2024 PB Request with CR Adjustments*". Both carry the same annualized continuing-resolution footnote; this does not equate CR estimates with final enactment.
