"""A flows sidecar sums the AWARD a link names, never every award that
happens to share its PIID (R-DEC-LINK-2026-10-21, owner 2026-10-21;
verify.md 7).

An award's PIID is unique only under its parent IDV and agency: USAspending
keys an award by contract_award_unique_key
(CONT_AWD_{piid}_{agency}_{parent piid}_{parent agency}). N0001922F0001 is two
awards in the lake — a Lockheed Martin F-35 DMS-redesign order under BOA
N0001919G0008 and a Rolls-Royce "MAINTENANCE AND RELATED SERVICES AT NASM"
order under IDIQ N6134019D0004. The ATA000 link (announcement 3028388) names
the Lockheed order, but _emit_flows_sidecars joined fct_award_transactions to
the link on the PIID alone, so flows/ATA000.json published the Rolls-Royce
order too: $157.9M of unrelated maintenance on the F-35 follow-the-money
flow.

The rule: a linked PIID that is ONE award in the lake contributes that award,
byte for byte as before (every UEI on it — a novated award keeps its
successor's rows). A PIID that is SEVERAL awards contributes only the
award(s) whose transactions carry the recipient the link records; the
others are another contract that happens to share the number.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from govbudget.export_site import _emit_flows_sidecars
from link_award_keys_fixture import materialize_link_award_keys

PE = "ATA000"


def _lake(links, transactions) -> duckdb.DuckDBPyConnection:
    """links: (award_piid, recipient_uei); transactions: (award_id_piid,
    award_unique_key, recipient_uei, obligation, pop_district)."""
    con = duckdb.connect()
    con.execute(
        "create table dim_programs (pe_bli varchar, title varchar, org varchar,"
        " exhibit_family varchar, project_count integer,"
        " fy2024_actual_millions double, fully_reconciled boolean,"
        " account varchar, account_title varchar)")
    con.execute(
        "insert into dim_programs values (?, 'F-35', 'F', 'procurement', 0, 1.0,"
        " true, '3010F', 'Aircraft Procurement, Air Force')", (PE,))
    con.execute(
        "create table fct_budget_trajectory (pe_bli varchar, organization varchar,"
        " account varchar, fy2026_total double)")
    con.execute(
        "create table fct_budget_to_awards (award_piid varchar, pe_bli varchar,"
        " confidence varchar, recipient_uei varchar)")
    con.execute(
        "create table fct_award_transactions (award_id_piid varchar,"
        " award_unique_key varchar, recipient_uei varchar, obligation double,"
        " pop_state varchar, pop_district varchar)")
    con.execute(
        "create table entity_xwalk (recipient_uei varchar, recipient_name varchar,"
        " family_key varchar)")
    con.execute(
        "create table fct_district_programs (pop_state varchar,"
        " pop_district varchar, pe_bli varchar, account varchar)")
    con.execute("insert into fct_district_programs values ('TX', 'TX-12', ?, '3010F')",
                (PE,))
    for piid, uei in links:
        con.execute("insert into fct_budget_to_awards values (?, ?, 'high', ?)",
                    (piid, PE, uei))
    for piid, key, uei, obligation, district in transactions:
        con.execute(
            "insert into fct_award_transactions values (?, ?, ?, ?, ?, ?)",
            (piid, key, uei, obligation, district[:2], district))
    for uei in sorted({t[2] for t in transactions}):
        con.execute("insert into entity_xwalk values (?, ?, ?)",
                    (uei, f"VENDOR {uei}", f"VENDOR {uei}"))
    # every link->award join reads dbt's link_award_keys (R-DEC-LINK-2026-10-21 R4)
    materialize_link_award_keys(con)
    return con


def _awards(tmp_path: Path, links, transactions) -> list[tuple]:
    flows_dir = tmp_path / "flows"
    flows_dir.mkdir()
    con = _lake(links, transactions)
    try:
        _emit_flows_sidecars(flows_dir=flows_dir, con=con)
    finally:
        con.close()
    path = flows_dir / f"{PE}.json"
    assert path.exists(), "no flows sidecar written (the award query raised?)"
    return [(a["piid"], a["recipient_name"], a["dollars"])
            for a in json.loads(path.read_text())["awards"]]


LM_KEY = "CONT_AWD_N0001922F0001_9700_N0001919G0008_9700"
RR_KEY = "CONT_AWD_N0001922F0001_9700_N6134019D0004_9700"


def test_a_piid_shared_by_two_awards_contributes_only_the_linked_award(tmp_path):
    awards = _awards(
        tmp_path,
        links=[("N0001922F0001", "UEI-LM"), ("N0001925C0070", "UEI-LM")],
        transactions=[
            ("N0001922F0001", LM_KEY, "UEI-LM", 184_551_699.01, "TX-12"),
            ("N0001922F0001", RR_KEY, "UEI-RR", 157_917_295.93, "IN-07"),
            ("N0001925C0070", "CONT_AWD_N0001925C0070_9700_-NONE-_-NONE-",
             "UEI-LM", 4_370_682_239.0, "TX-12"),
        ])
    assert awards == [
        ("N0001925C0070", "VENDOR UEI-LM", 4_370_682_239.0),
        ("N0001922F0001", "VENDOR UEI-LM", 184_551_699.01),
    ], awards


def test_a_single_award_keeps_every_recipient_on_it(tmp_path):
    """A novated award carries two UEIs under ONE award key: both keep their
    rows, exactly as before, whichever recipient the link records."""
    key = "CONT_AWD_N0001919C0001_9700_-NONE-_-NONE-"
    awards = _awards(
        tmp_path,
        links=[("N0001919C0001", "UEI-NEW")],
        transactions=[
            ("N0001919C0001", key, "UEI-OLD", 300.0, "TX-12"),
            ("N0001919C0001", key, "UEI-NEW", 200.0, "TX-12"),
        ])
    assert awards == [("N0001919C0001", "VENDOR UEI-OLD", 300.0),
                      ("N0001919C0001", "VENDOR UEI-NEW", 200.0)], awards


def test_awards_sharing_a_piid_and_the_linked_recipient_all_count(tmp_path):
    """Two awards under one PIID that BOTH carry the link's recipient are
    indistinguishable by the link's evidence: both count, as before."""
    awards = _awards(
        tmp_path,
        links=[("N0001922F0002", "UEI-LM")],
        transactions=[
            ("N0001922F0002", "CONT_AWD_A", "UEI-LM", 500.0, "TX-12"),
            ("N0001922F0002", "CONT_AWD_B", "UEI-LM", 400.0, "TX-12"),
            ("N0001922F0002", "CONT_AWD_C", "UEI-RR", 900.0, "TX-12"),
        ])
    assert awards == [("N0001922F0002", "VENDOR UEI-LM", 900.0)], awards
