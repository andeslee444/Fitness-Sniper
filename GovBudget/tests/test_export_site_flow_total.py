"""R-DEC-FLOWTOTAL: a shared code's flows sidecar header fy2026_total.

_emit_flows_sidecars read its FY2026 figure as a dict over
`fct_budget_trajectory t join dim_programs p on (pe_bli, org)` with no ORDER
BY. On a code two programs share (one per appropriation account, same org)
that join fans out — two trajectory rows x two member rows — and the LAST row
the engine returned won. The same lake gave flows/0145.json 50607 (the APN
member's figure) in the shipped export and 30915 (the PANMC member's) in a
scratch emission; 3010 moved 2600000 <-> 20900.

The ruling: a shared code's header fy2026_total is the sum of its members'
FY2026 totals — the header's title already names every member
(shared_code_program_label, R-DEC-FLOWTITLE). A member's figure is the
trajectory row at the member's own (pe_bli, org, account), the row the
account-blind join above fanned out over. A code one program owns keeps the
figure the old join gave it, byte for byte (its dim_programs account is often
NULL while its trajectory row carries one, so it must NOT be read through an
account join).
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import duckdb
import pytest

import govbudget.export_site as es
from govbudget.export_site import _emit_flows_sidecars

# (pe_bli, account, org, title) — the live member shapes (read-only on the
# chain-G lake, 2026-09-26) of the four shared codes that carry a flows
# sidecar today, one org-split code ('30'), one shared code whose WPN member
# has no trajectory row ('1350'), and ordinary codes.
PROGRAMS = [
    ("0145", "1506N", "N", "F/A-18E/F (Fighter) Hornet"),
    ("0145", "1508N", "N", "General Purpose Bombs"),
    ("3215", "1507N", "N", "MK-54 Torpedo Mods"),
    ("3215", "1810N", "N", "Satellite Communications Systems"),
    ("3010", "1611N", "N", "LPD Flight II"),
    ("3010", "1810N", "N", "Shipboard Tactical Communications"),
    ("2292", "1109N", "N", "Naval Strike Missile (NSM)"),
    ("2292", "1507N", "N", "Naval Strike Missile (NSM)"),
    ("30", "0300D", "DMACT", "Major Equipment"),
    ("30", "0300D", "DTRA", "Other Major Equipment"),
    ("30", "0300D", "OSD", "Major Equipment, OSD"),
    ("1350", "1507N", "N", "Other Missile Support"),
    ("1350", "1508N", "N", "Airborne Rockets, All Types"),
    # Ordinary codes. dim_programs.account is NULL on 169 live rows whose
    # trajectory row carries an account (chain-G lake, 2026-09-26; e.g.
    # '0602024E' / '0400D').
    ("0602024E", None, "DARPA", "Electronic Technology"),
    ("1203176F", None, "F", "Combat Survivor Evader Locator"),
    ("NOTRAJ", None, "DARPA", "No Trajectory Row"),
]

# (pe_bli, organization, account, fy2026_total) — live values, USD thousands.
TRAJECTORY = [
    ("0145", "N", "1506N", 50607.0),
    ("0145", "N", "1508N", 30915.0),
    ("3215", "N", "1507N", 113513.0),
    ("3215", "N", "1810N", 62943.0),
    ("3010", "N", "1611N", 2600000.0),
    ("3010", "N", "1810N", 20900.0),
    ("2292", "N", "1109N", 164641.0),
    ("2292", "N", "1507N", 35297.0),
    ("30", "DMACT", "0300D", 7258.0),
    ("30", "DTRA", "0300D", 12023.0),
    ("30", "OSD", "0300D", 212900.0),
    ("1350", "N", "1508N", 180867.0),
    ("0602024E", "DARPA", "0400D", 278121.0),
    ("1203176F", "F", "3600F", None),
    # A trajectory-only code (no dim_programs row) never reaches a sidecar.
    ("TRAJONLY", "N", "1810N", 999.0),
]

EXPECTED = {
    "0145": 50607.0 + 30915.0,        # 81522.0
    "3215": 113513.0 + 62943.0,       # 176456.0
    "3010": 2600000.0 + 20900.0,      # 2620900.0
    "2292": 164641.0 + 35297.0,       # 199938.0
    "30": 7258.0 + 12023.0 + 212900.0,  # 232181.0
    # A member with no FY2026 figure: the sum would not be the code's total,
    # so the header carries none (it used to carry the one member's 180867).
    "1350": None,
    "0602024E": 278121.0,
    "1203176F": None,
    "NOTRAJ": None,
}


def _lake(programs, trajectory, *, with_account: bool = True) -> duckdb.DuckDBPyConnection:
    """The tables _emit_flows_sidecars reads, one high-confidence award at a
    recorded district per code (a sidecar with no awards is not written).
    Rows are inserted in the order given, so a test can hand the emitter
    several orders of the same multiset."""
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
        + (" account varchar," if with_account else "")
        + " fy2026_total double)"
    )
    for pe_bli, org, account, total in trajectory:
        if with_account:
            con.execute(
                "insert into fct_budget_trajectory values (?, ?, ?, ?)",
                (pe_bli, org, account, total),
            )
        else:
            con.execute(
                "insert into fct_budget_trajectory values (?, ?, ?)",
                (pe_bli, org, total),
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


def _emit(con, tmp_path: Path) -> dict[str, dict]:
    flows_dir = tmp_path / "flows"
    flows_dir.mkdir(parents=True)
    _emit_flows_sidecars(flows_dir=flows_dir, con=con)
    return {
        f.stem: json.loads(f.read_text())["header"]
        for f in sorted(flows_dir.glob("*.json"))
    }


def _totals(con, tmp_path: Path) -> dict[str, float | None]:
    return {pe: h["fy2026_total"] for pe, h in _emit(con, tmp_path).items()}


@pytest.fixture(autouse=True)
def _no_title_overrides(monkeypatch):
    monkeypatch.setattr(es, "load_title_overrides", lambda: {})


def test_a_shared_codes_total_is_the_sum_of_its_members(tmp_path):
    assert _totals(_lake(PROGRAMS, TRAJECTORY), tmp_path) == EXPECTED


def test_two_input_orders_give_the_same_totals(tmp_path):
    """The defect: the SAME multiset in another row order moved the figure."""
    forward = _totals(_lake(PROGRAMS, TRAJECTORY), tmp_path / "f")
    backward = _totals(
        _lake(list(reversed(PROGRAMS)), list(reversed(TRAJECTORY))), tmp_path / "b"
    )
    mixed = _totals(
        _lake(list(reversed(PROGRAMS)), TRAJECTORY), tmp_path / "m"
    )
    assert forward == backward == mixed == EXPECTED


def test_the_sum_does_not_depend_on_member_order_in_floating_point(tmp_path):
    """(0.1 + 0.2) + 0.3 != 0.1 + (0.2 + 0.3) in binary floating point: the
    sum is exactly rounded, so every member order gives the same bytes."""
    programs = [("FLT", "0300D", org, f"Member {org}") for org in ("A", "B", "C")]
    values = {"A": 0.1, "B": 0.2, "C": 0.3}
    seen = set()
    for i, perm in enumerate(itertools.permutations(programs)):
        traj = [("FLT", p[2], "0300D", values[p[2]]) for p in perm]
        seen.add(_totals(_lake(list(perm), traj), tmp_path / str(i))["FLT"])
    assert seen == {0.6}


def test_an_ordinary_codes_sidecar_is_byte_for_byte_what_the_old_join_gave(tmp_path):
    """A code one program owns reads the (pe_bli, org) join exactly as before —
    including a dim_programs row whose account is NULL — and its file is
    byte-identical to the pre-ruling emitter's."""
    con = _lake(PROGRAMS, TRAJECTORY)
    old = dict(
        con.execute(
            "select t.pe_bli, t.fy2026_total from fct_budget_trajectory t"
            " join dim_programs p on p.pe_bli = t.pe_bli"
            "  and t.organization = p.org"
        ).fetchall()
    )
    flows_dir = tmp_path / "flows"
    flows_dir.mkdir()
    _emit_flows_sidecars(flows_dir=flows_dir, con=con)
    ordinary = {
        "0602024E": ("DARPA", "Electronic Technology"),
        "1203176F": ("F", "Combat Survivor Evader Locator"),
        "NOTRAJ": ("DARPA", "No Trajectory Row"),
    }
    for pe, (org, title) in ordinary.items():
        expected = json.dumps(
            {
                "awards": [{
                    "confidence": "high", "district": "CO-05", "dollars": 1000.0,
                    "family_slug": "vendor-a", "piid": f"PIID-{pe}",
                    "recipient_name": "VENDOR A",
                }],
                "header": {
                    "fy2026_total": old.get(pe), "org": org, "pe_bli": pe,
                    "title": title,
                },
            },
            sort_keys=True,
        )
        assert (flows_dir / f"{pe}.json").read_text() == expected
    assert old["0602024E"] == 278121.0


def test_a_member_without_a_figure_leaves_the_code_total_empty(tmp_path):
    """'1350': the WPN member has no trajectory row. The old join returned the
    PANMC member's 180867 twice and shipped it under both members' names."""
    totals = _totals(_lake(PROGRAMS, TRAJECTORY), tmp_path)
    assert totals["1350"] is None
    # A null figure on a member counts as missing too.
    traj = [r if r[:3] != ("0145", "N", "1508N") else ("0145", "N", "1508N", None)
            for r in TRAJECTORY]
    assert _totals(_lake(PROGRAMS, traj), tmp_path / "n")["0145"] is None


def test_a_lake_without_the_account_column_sums_org_split_members(tmp_path):
    """An older fixture has no account column on either table: no code is
    account-split there, so members are told apart by org alone."""
    programs = [p for p in PROGRAMS if p[0] in ("30", "0602024E", "NOTRAJ")]
    traj = [t for t in TRAJECTORY if t[0] in ("30", "0602024E")]
    forward = _totals(_lake(programs, traj, with_account=False), tmp_path / "f")
    backward = _totals(
        _lake(list(reversed(programs)), list(reversed(traj)), with_account=False),
        tmp_path / "b",
    )
    assert forward == backward == {
        "30": 232181.0,
        "0602024E": 278121.0,
        "NOTRAJ": None,
    }


def test_title_and_org_are_untouched(tmp_path):
    """R-DEC-FLOWTITLE's header fields stay what fix 3 made them."""
    headers = _emit(_lake(PROGRAMS, TRAJECTORY), tmp_path)
    assert headers["0145"]["title"] == "F/A-18E/F (Fighter) Hornet / General Purpose Bombs"
    assert headers["0145"]["org"] == "N"
    assert headers["0602024E"]["title"] == "Electronic Technology"
