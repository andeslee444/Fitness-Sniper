#!/usr/bin/env python3
"""Refresh only cited F-15 family history after an existing complete site export."""
import argparse
import json
from govbudget.f15_funding_history import export_f15_funding_history

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--duckdb", default="data/duckdb/govbudget.duckdb")
parser.add_argument("--out-dir", default="data/site")
args = parser.parse_args()
print(json.dumps(export_f15_funding_history(duckdb_path=args.duckdb, out_dir=args.out_dir), sort_keys=True))
