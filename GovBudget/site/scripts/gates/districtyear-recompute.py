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
#
# R-DEC-LINK-2026-10-21 R4: a link's dollars are the AWARD it names, never
# every award sharing its PIID — restated here from the raw inputs, not read
# from dbt's link_award_keys (the model the mart under test is built on). A
# PIID that is one award in the lake (a NULL award_unique_key is one award)
# contributes it whole; a PIID that is several contributes the award(s) whose
# transactions carry the recipient the link records.
_SQL = """
with links as (
    select distinct award_piid, recipient_uei
    from fct_budget_to_awards
    where confidence = 'high'
),
award_recipients as (
    select distinct award_id_piid, award_unique_key, recipient_uei
    from fct_award_transactions
    where award_id_piid in (select award_piid from links)
),
piid_awards as (
    select award_id_piid, award_unique_key,
           count(*) over (partition by award_id_piid) as n_awards
    from (select distinct award_id_piid, award_unique_key from award_recipients)
),
named as (
    select distinct a.award_id_piid, a.award_unique_key
    from piid_awards a
    join links l on l.award_piid = a.award_id_piid
    where a.n_awards = 1
       or exists (
            select 1 from award_recipients r
            where r.award_id_piid = a.award_id_piid
              and r.award_unique_key is not distinct from a.award_unique_key
              and r.recipient_uei = l.recipient_uei)
),
linked as (
    select
        t.pop_district,
        t.fiscal_year,
        t.award_id_piid,
        sum(coalesce(t.obligation, 0))              as obligation,
        sum(greatest(coalesce(t.obligation, 0), 0)) as positive_obligation
    from fct_award_transactions t
    join named b
      on t.award_id_piid = b.award_id_piid
     and t.award_unique_key is not distinct from b.award_unique_key
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
