"""A published link's dollars are the AWARD it names, on every surface
(R-DEC-LINK-2026-10-21 R4; controller ruling on review 1 finding I-4,
2026-10-21).

A PIID is unique only under its parent IDV and agency; the lake keys an award
by award_unique_key (contract_award_unique_key). N0001922F0001 is two awards:
a Lockheed Martin F-35 order (the one the ATA000 link names) and an unrelated
Rolls-Royce NASM maintenance order ($157,917,295.93 FY2022 positive
obligation, $147,027,390.49 net, all of it in IN-07). The round-1 fix keyed
the flows sidecar on the award; every OTHER join from a published link to
fct_award_transactions still read the PIID alone and published the
Rolls-Royce order as F-35 money: /district/IN-07/ (F-35 $147,027,390.49), the
district totals and years, the feed's concentration shifts, the
programs.json HHI and flow_chart.json's families.

dbt/models/marts/link_award_keys.sql is now the one resolution point: one row
per published link key (award_piid, recipient_uei) and per award the lake
carries under its PIID, `named` where the link names it — the PIID's only
award (whole: every UEI on it), or, when the PIID is several awards, the
award(s) whose transactions carry the link's recipient. Every surface below
joins through it. The fixture: N0001922F0001 as the lake carries it, beside a
novated single award, a single award with a NULL key, a PIID whose two awards
both carry the link's recipient, and a PIID whose link names no recipient.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import duckdb
import pytest

from link_award_keys_fixture import materialize_link_award_keys
from test_dbt_build import _model_sql

ROOT = Path(__file__).resolve().parents[1]
F35 = "ATA000"
SHARED = "N0001922F0001"
LM_NET = 184_551_699.01
RR_POS = 157_917_295.93
RR_NET = 147_027_390.49

#: (award_id_piid, award_unique_key, recipient_uei, pop_state, pop_district,
#:  fiscal_year, obligation)
TRANSACTIONS = [
    (SHARED, "CONT_AWD_N0001922F0001_9700_N0001919G0008_9700", "UEI_LM",
     "TX", "TX-12", 2022, LM_NET),
    (SHARED, "CONT_AWD_N0001922F0001_9700_N6134019D0004_9700", "UEI_RR",
     "IN", "IN-07", 2022, RR_POS),
    (SHARED, "CONT_AWD_N0001922F0001_9700_N6134019D0004_9700", "UEI_RR",
     "IN", "IN-07", 2022, RR_NET - RR_POS),
    ("IN_OTHER", "IO_KEY", "UEI_IO", "IN", "IN-07", 2022, 12_000_000.0),
    # one award, novated: both UEIs' rows are the award the link names
    ("NOVATED", "NOV_KEY", "UEI_OLD", "CA", "CA-01", 2021, 50_000_000.0),
    ("NOVATED", "NOV_KEY", "UEI_NEW", "CA", "CA-01", 2022, 30_000_000.0),
    # one award whose key the lake leaves NULL
    ("NULLKEY", None, "UEI_N", "TX", "TX-12", 2022, 20_000_000.0),
    # two awards, both carrying the link's recipient: both are named
    ("BOTH", "K1", "UEI_B", "CA", "CA-01", 2022, 7_000_000.0),
    ("BOTH", "K2", "UEI_B", "CA", "CA-02", 2022, 6_000_000.0),
    # two awards and a link with no recipient: neither is named
    ("NOREC", "KA", "UEI_X", "CA", "CA-03", 2022, 9_000_000.0),
    ("NOREC", "KB", "UEI_Y", "CA", "CA-03", 2022, 8_000_000.0),
    ("MEDIUM1", "M1", "UEI_M", "VA", "VA-08", 2022, 5_000_000.0),
]
#: (pe_bli, award_piid, recipient_uei, confidence)
LINKS = [
    (F35, SHARED, "UEI_LM", "high"),
    ("0147", SHARED, "UEI_LM", "high"),
    (F35, "IN_OTHER", "UEI_IO", "high"),
    (F35, "NOVATED", "UEI_NEW", "high"),
    (F35, "NULLKEY", "UEI_N", "high"),
    (F35, "MEDIUM1", "UEI_M", "medium"),
    ("0592", "BOTH", "UEI_B", "high"),
    ("0592", "NOREC", None, "high"),
]
FAMILY = {"UEI_LM": "LOCKHEED MARTIN", "UEI_RR": "ROLLS-ROYCE", "UEI_IO": "INDY",
          "UEI_OLD": "NOVCO", "UEI_NEW": "NOVCO", "UEI_N": "NULLCO",
          "UEI_B": "BCO", "UEI_X": "XCO", "UEI_Y": "YCO", "UEI_M": "MCO"}
TITLE = {F35: "F-35", "0147": "F-35 Spares", "0592": "F-35 Modifications"}


@pytest.fixture()
def lake(tmp_path) -> Path:
    db = tmp_path / "lake.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        "create table fct_award_transactions (transaction_key varchar,"
        " award_id_piid varchar, award_unique_key varchar, recipient_uei varchar,"
        " pop_state varchar, pop_district varchar, fiscal_year integer,"
        " obligation double)")
    for i, row in enumerate(TRANSACTIONS):
        con.execute("insert into fct_award_transactions values"
                    " (?, ?, ?, ?, ?, ?, ?, ?)", [f"T{i}", *row])
    con.execute(
        "create table fct_budget_to_awards (pe_bli varchar, award_piid varchar,"
        " recipient_uei varchar, recipient_name varchar, confidence varchar,"
        " account varchar, program_title varchar, organization varchar)")
    for pe, piid, uei, conf in LINKS:
        con.execute("insert into fct_budget_to_awards values"
                    " (?, ?, ?, ?, ?, null, ?, 'N')",
                    [pe, piid, uei, FAMILY.get(uei, "NONE"), conf, TITLE[pe]])
    con.execute("create table entity_xwalk (recipient_uei varchar,"
                " recipient_name varchar, family_key varchar)")
    con.executemany("insert into entity_xwalk values (?, ?, ?)",
                    [(u, f, f) for u, f in FAMILY.items()])
    con.execute(
        "create table dim_programs (pe_bli varchar, title varchar, org varchar,"
        " exhibit_family varchar, account varchar, account_title varchar)")
    con.executemany("insert into dim_programs values (?, ?, 'N', 'procurement',"
                    " null, null)", [(pe, t) for pe, t in TITLE.items()])
    con.execute("create table fct_budget_trajectory (pe_bli varchar,"
                " organization varchar, account varchar, fy2025_total double,"
                " fy2026_total double, fy2526_pct_change double)")
    materialize_link_award_keys(con)
    refs = dict(fct_award_transactions="fct_award_transactions",
                fct_budget_to_awards="fct_budget_to_awards",
                link_award_keys="link_award_keys", entity_xwalk="entity_xwalk",
                dim_programs="dim_programs",
                fct_budget_trajectory="fct_budget_trajectory")
    for model in ("fct_district_programs", "fct_district_programs_by_year",
                  "fct_district_totals", "fct_district_totals_by_year",
                  "fct_feed_events", "fct_program_concentration"):
        sql = _model_sql(model, **{k: v for k, v in refs.items()
                                   if "{{ ref('%s') }}" % k in _raw(model)})
        con.execute(f"create table {model} as {sql}")
    con.close()
    return db


def _raw(model: str) -> str:
    return (ROOT / "dbt" / "models" / "marts" / f"{model}.sql").read_text()


def _q(db, sql, params=()):
    con = duckdb.connect(str(db), read_only=True)
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def test_each_link_names_its_award(lake):
    rows = _q(lake, "select award_piid, recipient_uei, award_unique_key,"
                    " n_awards, named from link_award_keys"
                    " order by 1, 2 nulls first, 3 nulls first")
    LMK, RRK = TRANSACTIONS[0][1], TRANSACTIONS[1][1]
    assert rows == [
        ("BOTH", "UEI_B", "K1", 2, True), ("BOTH", "UEI_B", "K2", 2, True),
        ("IN_OTHER", "UEI_IO", "IO_KEY", 1, True),
        ("MEDIUM1", "UEI_M", "M1", 1, True),
        (SHARED, "UEI_LM", LMK, 2, True), (SHARED, "UEI_LM", RRK, 2, False),
        ("NOREC", None, "KA", 2, False), ("NOREC", None, "KB", 2, False),
        ("NOVATED", "UEI_NEW", "NOV_KEY", 1, True),
        ("NULLKEY", "UEI_N", None, 1, True),
    ], rows


def test_district_programs_count_only_the_named_award(lake):
    rows = _q(lake, "select pe_bli, pop_district, award_count, total_obligation"
                    " from fct_district_programs order by 1, 2")
    assert rows == [
        ("0147", "TX-12", 1, pytest.approx(LM_NET)),
        ("0592", "CA-01", 1, 7_000_000.0), ("0592", "CA-02", 1, 6_000_000.0),
        (F35, "CA-01", 1, 80_000_000.0),
        # IN-07's F-35 money is the IN_OTHER award only, never Rolls-Royce
        (F35, "IN-07", 1, 12_000_000.0),
        (F35, "TX-12", 2, pytest.approx(LM_NET + 20_000_000.0)),
    ], rows
    by_year = _q(lake, "select pe_bli, pop_district, fiscal_year, award_count,"
                       " total_obligation, positive_obligation"
                       " from fct_district_programs_by_year"
                       " where pop_district in ('IN-07', 'CA-03') order by 1, 2, 3")
    assert by_year == [(F35, "IN-07", 2022, 1, 12_000_000.0, 12_000_000.0)], by_year


def test_district_totals_count_only_the_named_award(lake):
    rows = _q(lake, "select pop_district, award_count, total_obligation"
                    " from fct_district_totals order by 1")
    assert rows == [
        ("CA-01", 2, 87_000_000.0), ("CA-02", 1, 6_000_000.0),
        ("IN-07", 1, 12_000_000.0),
        ("TX-12", 2, pytest.approx(LM_NET + 20_000_000.0)),
    ], rows
    by_year = _q(lake, "select pop_district, fiscal_year, award_count,"
                       " total_obligation, positive_obligation"
                       " from fct_district_totals_by_year"
                       " where pop_district = 'IN-07'")
    assert by_year == [("IN-07", 2022, 1, 12_000_000.0, 12_000_000.0)], by_year


def test_feed_concentration_shift_counts_only_the_named_award(lake):
    rows = _q(lake, "select pe_bli, fiscal_year, comparison_value"
                    " from fct_feed_events where event_type = 'concentration_shift'"
                    " order by 1, 2")
    assert rows == [
        ("0147", 2022, pytest.approx(LM_NET)),
        ("0592", 2022, 13_000_000.0),
        (F35, 2021, 50_000_000.0),
        (F35, 2022, pytest.approx(LM_NET + 12e6 + 30e6 + 20e6)),
    ], rows


def test_program_concentration_counts_only_the_named_award(lake):
    rows = _q(lake, "select pe_bli, program_dollars_all, program_dollars_high,"
                    " award_count_high from fct_program_concentration order by 1")
    high = LM_NET + 12e6 + 80e6 + 20e6
    assert rows == [
        ("0147", pytest.approx(LM_NET), pytest.approx(LM_NET), 1),
        # NOREC names no award, so it adds nothing (it was +$17M by PIID)
        ("0592", 13_000_000.0, 13_000_000.0, 2),
        (F35, pytest.approx(high + 5e6), pytest.approx(high), 4),
    ], rows
    fams = _q(lake, "select top_family_high from fct_program_concentration"
                    " where pe_bli = ?", [F35])
    assert fams == [("LOCKHEED MARTIN",)]


def test_flows_sum_the_named_award_and_warn_on_a_link_that_names_none(
        lake, tmp_path, capsys):
    from govbudget.export_site import _emit_flows_sidecars

    out = tmp_path / "flows"
    out.mkdir()
    con = duckdb.connect(str(lake), read_only=True)
    try:
        _emit_flows_sidecars(flows_dir=out, con=con)
    finally:
        con.close()
    f35 = json.loads((out / f"{F35}.json").read_text())["awards"]
    assert sorted((a["piid"], a["recipient_name"], a["district"], a["dollars"])
                  for a in f35) == sorted([
        (SHARED, "LOCKHEED MARTIN", "TX-12", LM_NET),
        ("IN_OTHER", "INDY", "IN-07", 12_000_000.0),
        ("NOVATED", "NOVCO", "CA-01", 50_000_000.0),
        ("NOVATED", "NOVCO", "CA-01", 30_000_000.0),
        ("NULLKEY", "NULLCO", "TX-12", 20_000_000.0),
    ])
    mods = json.loads((out / "0592.json").read_text())["awards"]
    assert sorted((a["piid"], a["district"]) for a in mods) == [
        ("BOTH", "CA-01"), ("BOTH", "CA-02")]
    log = capsys.readouterr().out
    assert "WARNING" in log and "NOREC" in log and "flows/0592.json" in log, log
    assert SHARED not in log and "NOVATED" not in log


def test_flows_raise_on_an_error_that_is_not_a_missing_table(lake, tmp_path):
    """M-4: only a warehouse that lacks a relation or column empties a flows
    file; any other failure of the award query raises."""
    from govbudget.export_site import _emit_flows_sidecars

    class Broken:
        def __init__(self, con):
            self._con = con

        def execute(self, sql, *a):
            if "obligation > 0" in sql:
                raise duckdb.ConversionException("Could not convert string")
            return self._con.execute(sql, *a)

    out = tmp_path / "flows"
    out.mkdir()
    con = duckdb.connect(str(lake), read_only=True)
    try:
        with pytest.raises(duckdb.ConversionException):
            _emit_flows_sidecars(flows_dir=out, con=Broken(con))
    finally:
        con.close()


def test_district_citations_and_fanout_read_the_named_award(lake, tmp_path):
    from govbudget.export_site import (
        _build_usaspending_citation_rows,
        _emit_district_sidecars,
        fact_id_usaspending,
    )

    citations = _build_usaspending_citation_rows(duckdb_path=lake)
    by_fid = {row[0]: row for row in citations}

    def award_ids(state, district, pe):
        fid = fact_id_usaspending("district_program", f"{state}|{district}|{pe}",
                                  "total_obligation")
        return sorted(json.loads(by_fid[fid][22])["filters"]["award_ids"])

    assert award_ids("IN", "IN-07", F35) == ["IN_OTHER"]
    assert award_ids("TX", "TX-12", F35) == [SHARED, "NULLKEY"]
    assert award_ids("TX", "TX-12", "0147") == [SHARED]

    out = tmp_path / "districts"
    out.mkdir()
    con = duckdb.connect(str(lake), read_only=True)
    try:
        _emit_district_sidecars(dist_dir=out, con=con, prog_titles=TITLE,
                                cited_fact_ids=set(by_fid))
    finally:
        con.close()
    fanout = {p["pe_bli"]: p["shared_award_count"] for p in
              json.loads((out / "IN-07.json").read_text())["programs"]}
    # IN_OTHER is matched to one program; N0001922F0001 (two programs) never
    # performed in IN-07 under the award the link names
    assert fanout == {F35: 1}, fanout
    tx = {p["pe_bli"]: p["shared_award_count"] for p in
          json.loads((out / "TX-12.json").read_text())["programs"]}
    assert tx == {F35: 2, "0147": 2}, tx


def test_flow_chart_families_are_the_named_awards_recipients(lake):
    from govbudget.flow_chart import _XWALK_FAMILIES_SQL

    fams = {}
    for pe, fam in _q(lake, _XWALK_FAMILIES_SQL):
        if fam is not None:  # build_flow_chart skips a link with no family
            fams.setdefault(pe, set()).add(fam)
    assert fams == {
        F35: {"LOCKHEED MARTIN", "INDY", "NOVCO", "NULLCO"},
        "0147": {"LOCKHEED MARTIN"},
        "0592": {"BCO"},
    }, fams


def test_the_district_year_gate_recomputes_the_named_award(lake):
    """gate 24 leg r recomputes a sampled (district, year) cell from the
    lake's inputs — independently of the mart under test — so it states the
    same rule, or it fails the release on IN-07 2022."""
    path = ROOT / "site" / "scripts" / "gates" / "districtyear-recompute.py"
    spec = importlib.util.spec_from_file_location("districtyear_recompute", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert _q(lake, mod._SQL, ["IN-07", 2022]) == [(1, 12_000_000.0, 12_000_000.0)]
    assert _q(lake, mod._SQL, ["CA-03", 2022]) == [(0, None, None)]
    assert _q(lake, mod._SQL, ["TX-12", 2022])[0][0] == 2
