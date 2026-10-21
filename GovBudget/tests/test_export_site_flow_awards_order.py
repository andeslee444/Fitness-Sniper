"""A flows sidecar's top-12 awards come out in one order, whatever the lake's
row order (Task 21f2, 2026-10-14).

_emit_flows_sidecars picked each crosswalked program's awards with
`group by 1,2,3,4,5 order by dollars desc limit 12` and no tiebreaker. Two
awards with equal dollars came out in whatever order the engine produced the
groups, and that order followed the lake: the release-1 proof's P1 diff
(B@fu-pre vs B@fu-post, one exporter, two warehouse states) read
json/flows/0605502E.json `/awards` reordered, because two $1,500,000 awards
(W31P4Q19C0008, IN-08 and W31P4Q17C0103, CA-36) swapped places 8 and 9 after
the fu-post rebuild recreated the views the query reads. The control (two
exports of one warehouse) could not see it. A tie at the 12th place would
also have let the lake pick WHICH award is published.

The ruling: the query's order is total — `order by dollars desc, piid,
recipient_uei, pop_state, pop_district, family_key`, the group-by columns.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import duckdb
import pytest

import govbudget.export_site as es
from govbudget.export_site import _emit_flows_sidecars
from link_award_keys_fixture import materialize_link_award_keys

PE = "0605502E"

# (piid, recipient_uei, pop_state, pop_district, obligation) — one
# transaction row each. The two $1,500,000 awards are the live pair that
# swapped in the proof; the pair of P-SPLIT rows is ONE award that spends in
# two districts of one state, equal per district, so its tie is broken only
# past piid and recipient_uei (pop_district).
AWARDS_WITH_TIES = [
    ("P-TOP", "UEI-A", "VA", "VA-08", 9_000_000.0),
    ("W31P4Q19C0008", "UEI-MAG", "IN", "IN-08", 1_500_000.0),
    ("P-MID", "UEI-B", "MD", "MD-04", 2_000_000.0),
    ("W31P4Q17C0103", "UEI-INF", "CA", "CA-36", 1_500_000.0),
    ("P-SPLIT", "UEI-C", "CO", "CO-06", 250_000.0),
    ("P-LOW", "UEI-D", "TX", "TX-21", 100_000.0),
    ("P-SPLIT", "UEI-C", "CO", "CO-05", 250_000.0),
]

# Expected order: dollars desc, then piid, recipient_uei, pop_state,
# pop_district, family_key.
EXPECTED_WITH_TIES = [
    ("P-TOP", "VA-08"),
    ("P-MID", "MD-04"),
    ("W31P4Q17C0103", "CA-36"),
    ("W31P4Q19C0008", "IN-08"),
    ("P-SPLIT", "CO-05"),
    ("P-SPLIT", "CO-06"),
    ("P-LOW", "TX-21"),
]

# Eleven awards above the cut, then four tied at the 12th place: the limit
# can publish only one of the four.
AWARDS_STRADDLING_12TH = [
    (f"P-{i:02d}", f"UEI-{i:02d}", "CO", "CO-05", 1_000_000.0 - i * 10_000.0)
    for i in range(11)
] + [
    (piid, f"UEI-{piid}", "CO", "CO-05", 500_000.0)
    for piid in ("TIE-D", "TIE-B", "TIE-C", "TIE-A")
]

EXPECTED_STRADDLING_12TH = [f"P-{i:02d}" for i in range(11)] + ["TIE-A"]


def _lake(awards) -> duckdb.DuckDBPyConnection:
    """The tables _emit_flows_sidecars reads, for one crosswalked program.
    Award rows are inserted in the order given, so a test can hand the
    emitter several orders of the same multiset."""
    con = duckdb.connect()
    con.execute(
        "create table dim_programs (pe_bli varchar, title varchar, org varchar,"
        " exhibit_family varchar, project_count integer,"
        " fy2024_actual_millions double, fully_reconciled boolean,"
        " account varchar, account_title varchar)"
    )
    con.execute(
        "insert into dim_programs values (?, 'Small Business Innovative Research',"
        " 'DARPA', 'rdte', 0, 1.0, true, '0400D', 'RDT&E, Defense-Wide')",
        (PE,),
    )
    con.execute(
        "create table fct_budget_trajectory (pe_bli varchar, organization varchar,"
        " account varchar, fy2026_total double)"
    )
    # The real marts carry fct_budget_to_awards.recipient_uei and
    # fct_award_transactions.award_unique_key; the flows query keys a
    # link on its award (R-DEC-LINK-2026-10-21). One award per PIID here
    # (P-SPLIT's two rows are one award).
    con.execute(
        "create table fct_budget_to_awards (award_piid varchar, pe_bli varchar,"
        " confidence varchar, recipient_uei varchar)"
    )
    con.execute(
        "create table fct_award_transactions (award_id_piid varchar,"
        " recipient_uei varchar, obligation double, pop_state varchar,"
        " pop_district varchar, award_unique_key varchar)"
    )
    con.execute(
        "create table entity_xwalk (recipient_uei varchar, recipient_name varchar,"
        " family_key varchar)"
    )
    con.execute(
        "create table fct_district_programs (pop_state varchar,"
        " pop_district varchar, pe_bli varchar, account varchar)"
    )
    for piid, uei, state, district, obligation in awards:
        con.execute(
            "insert into fct_budget_to_awards values (?, ?, 'high', ?)",
            (piid, PE, uei),
        )
        con.execute(
            "insert into fct_award_transactions values (?, ?, ?, ?, ?, ?)",
            (piid, uei, obligation, state, district, f"CONT_AWD_{piid}"),
        )
    for uei in dict.fromkeys(a[1] for a in awards):
        con.execute(
            "insert into entity_xwalk values (?, ?, ?)",
            (uei, f"VENDOR {uei}", f"VENDOR {uei}"),
        )
    con.execute(
        "insert into fct_district_programs values ('CO', 'CO-05', ?, '0400D')", (PE,)
    )
    # every link->award join reads dbt's link_award_keys (R-DEC-LINK-2026-10-21 R4)
    materialize_link_award_keys(con)
    return con


def _awards(awards, tmp_path: Path) -> list[tuple[str, str]]:
    flows_dir = tmp_path / "flows"
    flows_dir.mkdir(parents=True)
    con = _lake(awards)
    try:
        _emit_flows_sidecars(flows_dir=flows_dir, con=con)
    finally:
        con.close()
    path = flows_dir / f"{PE}.json"
    assert path.exists(), "no flows sidecar written (the award query raised?)"
    return [(a["piid"], a["district"]) for a in json.loads(path.read_text())["awards"]]


def _orders(rows) -> list[list]:
    """The given rows, reversed, and three fixed shuffles."""
    shuffled = []
    for seed in (1, 2, 3):
        r = list(rows)
        random.Random(seed).shuffle(r)
        shuffled.append(r)
    return [list(rows), list(reversed(rows)), *shuffled]


@pytest.fixture(autouse=True)
def _no_title_overrides(monkeypatch):
    monkeypatch.setattr(es, "load_title_overrides", lambda: {})


def test_tied_awards_keep_one_order_whatever_the_row_order(tmp_path):
    """The defect: the SAME awards in another row order swapped two tied
    awards' places (json/flows/0605502E.json, release-1 proof P1)."""
    results = [
        _awards(rows, tmp_path / f"order-{i}")
        for i, rows in enumerate(_orders(AWARDS_WITH_TIES))
    ]
    assert results == [EXPECTED_WITH_TIES] * len(results)


def test_a_tie_at_the_12th_place_publishes_the_same_twelve(tmp_path):
    """The limit cuts through four tied awards: the row order must not pick
    which one is published."""
    results = [
        [piid for piid, _ in _awards(rows, tmp_path / f"order-{i}")]
        for i, rows in enumerate(_orders(AWARDS_STRADDLING_12TH))
    ]
    assert results == [EXPECTED_STRADDLING_12TH] * len(results)
