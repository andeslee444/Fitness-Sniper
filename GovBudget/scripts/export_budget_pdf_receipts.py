#!/usr/bin/env python3
"""Refresh sitewide DoD PDF evidence without changing exported workbook facts."""
import sys
from govbudget.cli import main

if __name__ == "__main__":
    main(["export-budget-pdf-receipts", *sys.argv[1:]])
