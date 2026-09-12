#!/usr/bin/env python3
"""districtyear-recompute.py — gate 24 leg (r) helper (ROADMAP #6).

Answers, on stdout as JSON, the one question the gate cannot answer in Node:
what does the LAKE say a sampled (district, fiscal year) cell is worth?

Recomputed INDEPENDENTLY from fct_award_transactions joined to the
high-confidence fct_budget_to_awards links — never from
fct_district_totals_by_year, which is the artifact under test. Reading the
mart here would make the leg tautological in exactly the way
familylabel-recompute.py's header warns about.

Invoked by site/scripts/gates/datatruth.mjs with the request JSON on STDIN:
    {"cells": [{"district": "VA-11", "fy": 2019}, ...]}

Response JSON (stdout):
    {"VA-11|2019": {"total_obligation": float, "positive_obligation": float,
                    "award_count": int}, ...}
A requested cell with no rows in the lake answers null, which the gate reports
as a failure rather than a skip.
"""

import json
import sys
from pathlib import Path

import duckdb

# site/scripts/gates/x.py → parents[3] is the GovBudget root. Same derivation
# as familylabel-recompute.py: the helper must not depend on the govbudget
# package being importable from whatever cwd the gate spawns it in.
REPO = Path(__file__).resolve().parents[3]
DUCKDB = REPO / "data" / "duckdb" / "govbudget.duckdb"

# The award-distinct recomputation, spelled out rather than ref'd: dedupe to
# one row per (district, fiscal year, award) first, then aggregate. Summing
# transactions directly would give the same dollars here, but not the same
# award_count, and the point of this helper is to reproduce the model's
# reasoning from its inputs.
_SQL = """
with linked as (
    select
        t.pop_district,
        t.fiscal_year,
        t.award_id_piid,
        sum(coalesce(t.obligation, 0))              as obligation,
        sum(greatest(coalesce(t.obligation, 0), 0)) as positive_obligation
    from fct_award_transactions t
    join (
        select distinct award_piid
        from fct_budget_to_awards
        where confidence = 'high'
    ) b on t.award_id_piid = b.award_piid
    where t.pop_district = ? and t.fiscal_year = ?
    group by 1, 2, 3
)
select count(distinct award_id_piid), sum(obligation), sum(positive_obligation)
from linked
"""


def main() -> int:
    if not DUCKDB.exists():
        print(json.dumps({"__error__": f"missing {DUCKDB}"}))
        return 1
    request = json.loads(sys.stdin.read() or "{}")

    con = duckdb.connect(str(DUCKDB), read_only=True)
    out: dict[str, dict | None] = {}
    try:
        for cell in request.get("cells", []):
            district = str(cell["district"])
            fy = int(cell["fy"])
            n, total, positive = con.execute(_SQL, [district, fy]).fetchone()
            out[f"{district}|{fy}"] = (
                None
                if not n
                else {
                    "award_count": int(n),
                    "total_obligation": float(total),
                    "positive_obligation": float(positive),
                }
            )
    finally:
        con.close()
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
