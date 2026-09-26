"""R-DEC-FLOWTITLE: a shared code's flows sidecar header title.

_emit_flows_sidecars built its title map as a dict over
`select pe_bli, title, org from dim_programs` with no ORDER BY, so on a code
two programs share the LAST member row the engine returned won. Chain G's two
exports read the same dim_programs (identical as a multiset, 1,936 rows) in a
different row order after a dbt rebuild, and flows/0145.json went from
"General Purpose Bombs" to "F/A-18E/F (Fighter) Hornet" and flows/3215.json
from "MK-54 Torpedo Mods" to "Satellite Communications Systems" — no figure
moved, only the pick.

The ruling: a shared code's header title is export_site.shared_code_program_label
over every member, in the export's member order (account, org, title) — the
same label prog_titles gives the /program/{pe_bli}/ disambiguation stub. A code
one program owns keeps its own title, byte for byte.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import duckdb
import pytest

import govbudget.export_site as es
from govbudget.export_site import (
    _emit_flows_sidecars,
    _fetch_dim_programs_rows,
    apply_title_override,
    shared_code_program_label,
)

# (pe_bli, account, org, title) — the live member shapes of the four shared
# codes that carry a flows sidecar today (read-only on the chain-G lake,
# 2026-09-26), plus one ordinary code.
PROGRAMS = [
    ("0145", "1506N", "N", "F/A-18E/F (Fighter) Hornet"),
    ("0145", "1508N", "N", "General Purpose Bombs"),
    ("3215", "1507N", "N", "MK-54 Torpedo Mods"),
    ("3215", "1810N", "N", "Satellite Communications Systems"),
    ("3010", "1611N", "N", "LPD Flight II"),
    ("3010", "1810N", "N", "Shipboard Tactical Communications"),
    ("2292", "1109N", "N", "Naval Strike Missile (NSM)"),
    ("2292", "1507N", "N", "Naval Strike Missile (NSM)"),
    ("0603760E", None, "DARPA", "Command Control"),
]

EXPECTED = {
    "0145": "F/A-18E/F (Fighter) Hornet / General Purpose Bombs",
    "3215": "MK-54 Torpedo Mods / Satellite Communications Systems",
    "3010": "LPD Flight II / Shipboard Tactical Communications",
    # Members with one title collapse to it (shared_code_program_label).
    "2292": "Naval Strike Missile (NSM)",
    # One program on the code: its own title, unchanged.
    "0603760E": "Command Control",
}


def _lake(programs, *, with_account: bool = True) -> duckdb.DuckDBPyConnection:
    """The tables _emit_flows_sidecars reads, with one high-confidence award
    at a recorded district per code (a sidecar with no awards is not
    written). dim_programs rows are inserted in the order given, so a test
    can hand the emitter two orders of the same multiset."""
    con = duckdb.connect()
    con.execute(
        "create table dim_programs (pe_bli varchar, title varchar, org varchar,"
        " exhibit_family varchar, project_count integer,"
        " fy2024_actual_millions double, fully_reconciled boolean"
        + (", account varchar, account_title varchar" if with_account else "")
        + ")"
    )
    for pe_bli, account, org, title in programs:
        if with_account:
            con.execute(
                "insert into dim_programs values (?, ?, ?, 'procurement', 0,"
                " 1.0, true, ?, ?)",
                (pe_bli, title, org, account, f"Account {account}"),
            )
        else:
            con.execute(
                "insert into dim_programs values (?, ?, ?, 'procurement', 0,"
                " 1.0, true)",
                (pe_bli, title, org),
            )
    con.execute(
        "create table fct_budget_trajectory (pe_bli varchar, organization varchar,"
        " fy2026_total double)"
    )
    con.execute(
        "create table fct_budget_to_awards (award_piid varchar, pe_bli varchar,"
        " confidence varchar)"
    )
    con.execute(
        "create table fct_award_transactions (award_id_piid varchar,"
        " recipient_uei varchar, obligation double, pop_state varchar,"
        " pop_district varchar)"
    )
    con.execute(
        "create table entity_xwalk (recipient_uei varchar, recipient_name varchar,"
        " family_key varchar)"
    )
    con.execute(
        "create table fct_district_programs (pop_state varchar,"
        " pop_district varchar, pe_bli varchar, account varchar)"
    )
    con.execute("insert into entity_xwalk values ('UEI-A', 'VENDOR A', 'VENDOR A')")
    for code in sorted({p[0] for p in programs}):
        piid = f"PIID-{code}"
        con.execute("insert into fct_budget_to_awards values (?, ?, 'high')", (piid, code))
        con.execute(
            "insert into fct_award_transactions values (?, 'UEI-A', 1000.0, 'CO', 'CO-05')",
            (piid,),
        )
        con.execute(
            "insert into fct_district_programs values ('CO', 'CO-05', ?, null)", (code,)
        )
    return con


def _titles(con, tmp_path: Path) -> dict[str, str | None]:
    flows_dir = tmp_path / "flows"
    flows_dir.mkdir(parents=True)
    _emit_flows_sidecars(flows_dir=flows_dir, con=con)
    return {
        f.stem: json.loads(f.read_text())["header"]["title"]
        for f in sorted(flows_dir.glob("*.json"))
    }


@pytest.fixture(autouse=True)
def _no_title_overrides(monkeypatch):
    """The committed seed has no row on these codes; pin that so a future
    seed row cannot make these expectations pass or fail by accident."""
    monkeypatch.setattr(es, "load_title_overrides", lambda: {})


def test_a_shared_code_names_every_member_in_member_order(tmp_path):
    assert _titles(_lake(PROGRAMS), tmp_path) == EXPECTED


def test_two_orders_of_the_input_rows_give_the_same_title(tmp_path):
    forward = _titles(_lake(PROGRAMS), tmp_path / "f")
    backward = _titles(_lake(list(reversed(PROGRAMS))), tmp_path / "b")
    assert forward == backward == EXPECTED


def test_the_title_is_the_program_stub_label(tmp_path):
    """The sidecar and the /program/{pe_bli}/ stub name a code the same way:
    prog_titles is shared_code_program_label over _fetch_dim_programs_rows'
    titles, grouped by pe_bli in the order the export reads them."""
    con = _lake(list(reversed(PROGRAMS)))
    by_pe: dict[str, list] = defaultdict(list)
    for r in _fetch_dim_programs_rows(con):
        by_pe[r[0]].append(r[3])
    stub = {pe: shared_code_program_label(t) for pe, t in by_pe.items()}
    assert _titles(con, tmp_path) == stub


def test_a_title_override_applies_to_its_member_before_the_label(tmp_path, monkeypatch):
    """ROADMAP #39: the override is keyed on (pe_bli, source title), so it
    corrects the ONE member it names and the label joins the corrected title."""
    overrides = {
        ("0145", "General Purpose Bombs"): "General-Purpose Bombs",
        ("0603760E", "Command Control"): "Command and Control",
    }
    monkeypatch.setattr(es, "load_title_overrides", lambda: overrides)
    titles = _titles(_lake(list(reversed(PROGRAMS))), tmp_path)
    assert titles["0145"] == "F/A-18E/F (Fighter) Hornet / General-Purpose Bombs"
    assert titles["0603760E"] == "Command and Control"
    assert titles["0145"] == shared_code_program_label([
        apply_title_override("0145", "F/A-18E/F (Fighter) Hornet", overrides),
        apply_title_override("0145", "General Purpose Bombs", overrides),
    ])


def test_an_ordinary_code_keeps_its_title_byte_for_byte(tmp_path):
    """shared_code_program_label drops an empty title; a code one program
    owns is not a shared code, so its title passes through untouched."""
    programs = [("SOLO", None, "DARPA", ""), *PROGRAMS]
    titles = _titles(_lake(programs), tmp_path)
    assert titles["SOLO"] == ""
    assert titles["0603760E"] == "Command Control"


def test_a_lake_without_the_account_column_still_labels_deterministically(tmp_path):
    """An older fixture's dim_programs has no account: no code is
    account-split there, so members order by (org, title)."""
    programs = [
        ("30", None, "OSD", "Major Equipment, OSD"),
        ("30", None, "DTRA", "Other Major Equipment"),
        ("30", None, "DMACT", "Major Equipment"),
        ("SOLO", None, "DARPA", "Defense Research Sciences"),
    ]
    forward = _titles(_lake(programs, with_account=False), tmp_path / "f")
    backward = _titles(_lake(list(reversed(programs)), with_account=False), tmp_path / "b")
    assert forward == backward == {
        "30": "Major Equipment / Other Major Equipment / Major Equipment, OSD",
        "SOLO": "Defense Research Sciences",
    }
