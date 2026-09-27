"""Both reasons the site gives for an empty company awards table are real.

R-DEC-PRIMES (final-review rulings, 2026-09-27; final review finding #4).
/methodology/, /coverage/ and every company page without awards now say:

    "A profile lists a budget→award crosswalk link only when the award's
    recipient name is exactly the family's registered name in the award data.
    A profile shows none when no member's award is linked to a budget line,
    or when the links carry a member's own, different name."

The first sentence is the exporter's rule (entity_details joins
``awards_by_display.get(display_name, [])``; the site test
company-award-linkage-prose.test.tsx binds the prose to that line). This
file checks the second against the warehouse: among the profiled top-200
families with no exact-name link, BOTH kinds occur — a family none of whose
members' awards is linked, and a family whose members' awards ARE linked but
under a member's own name. Measured 2026-09-27 on the chain-G lake: 32 shown,
49 linked under another name (Northrop Grumman, RTX, General Dynamics, BAE
Systems, ...), 119 with no link at all.

Read-only: the shared lake is opened with ``read_only=True``.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
LAKE = Path(os.environ.get("GOVBUDGET_DUCKDB", ROOT / "data" / "duckdb" / "govbudget.duckdb"))

SQL = """
with top as (
    select family_key, display_name from dim_entities
    order by total_obligation desc limit 200
),
members as (select distinct recipient_uei, family_key from entity_xwalk),
per as (
    select t.family_key,
           (select count(*) from fct_budget_to_awards b
              join members m on m.recipient_uei = b.recipient_uei
             where m.family_key = t.family_key)              as member_links,
           (select count(*) from fct_budget_to_awards b
             where b.recipient_name = t.display_name)        as exact_links
    from top t
)
select
    count(*) filter (where exact_links > 0)                       as shown,
    count(*) filter (where exact_links = 0 and member_links > 0)  as other_name,
    count(*) filter (where exact_links = 0 and member_links = 0)  as unlinked
from per
"""


@pytest.fixture(scope="module")
def split():
    if not LAKE.exists():
        pytest.skip("no warehouse")
    try:
        con = duckdb.connect(str(LAKE), read_only=True)
    except duckdb.IOException as e:  # another process holds the write lock
        pytest.skip(f"warehouse locked: {e}")
    try:
        tables = {r[0] for r in con.execute("select table_name from information_schema.tables").fetchall()}
        need = {"dim_entities", "entity_xwalk", "fct_budget_to_awards"}
        if not need <= tables:
            pytest.skip(f"warehouse lacks {sorted(need - tables)}")
        return con.execute(SQL).fetchone()
    finally:
        con.close()


def test_the_three_buckets_cover_the_profiled_families(split):
    shown, other_name, unlinked = split
    assert shown + other_name + unlinked == 200


def test_both_stated_reasons_occur(split):
    _shown, other_name, unlinked = split
    assert other_name > 0, "no family has links under a member's own name — drop that reason"
    assert unlinked > 0, "every family has a linked award — drop that reason"


def test_the_crosswalks_largest_recipients_are_the_largest_primes():
    """docs/methodology.md §5 records why the old explanation was withdrawn:
    "the published crosswalk's largest recipients are prime contractors".
    Held here as: the three recipients with the most published links all
    belong to families among the five largest by DoD obligations (chain-G
    lake, 2026-09-27: Lockheed Martin 557, Raytheon Company [RTX] 311, The
    Boeing Company 220)."""
    if not LAKE.exists():
        pytest.skip("no warehouse")
    try:
        con = duckdb.connect(str(LAKE), read_only=True)
    except duckdb.IOException as e:
        pytest.skip(f"warehouse locked: {e}")
    try:
        top5 = {r[0] for r in con.execute(
            "select family_key from dim_entities order by total_obligation desc limit 5"
        ).fetchall()}
        leaders = con.execute(
            "with m as (select distinct recipient_uei, family_key from entity_xwalk)"
            " select m.family_key, count(*) as n from fct_budget_to_awards b"
            " left join m using (recipient_uei)"
            " group by b.recipient_uei, m.family_key order by n desc, b.recipient_uei limit 3"
        ).fetchall()
    finally:
        con.close()
    assert leaders and all(fk in top5 for fk, _n in leaders), (leaders, top5)
