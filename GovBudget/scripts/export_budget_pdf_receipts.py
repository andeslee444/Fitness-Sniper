#!/usr/bin/env python3
"""Export verified matching DoD PDF highlights without changing workbook facts."""
import argparse
import json
from pathlib import Path
from govbudget.budget_pdf_receipts import export_budget_pdf_receipts

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--site-dir", type=Path, default=Path("data/site"))
parser.add_argument("--manifest", type=Path, default=Path("data-seeds/f15_budget_pdf_sources.json"))
parser.add_argument("--cache-dir", type=Path, default=Path("tmp/pdfs"))
args = parser.parse_args()
print(json.dumps(export_budget_pdf_receipts(site_dir=args.site_dir, manifest=args.manifest, cache_dir=args.cache_dir), indent=2))
