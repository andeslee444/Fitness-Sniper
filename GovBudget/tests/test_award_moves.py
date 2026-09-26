"""ROADMAP #133 / ruling R-DEC-133b (2026-09-26) — the fiscal-year move rule
for every reader of the RAW award archives outside dbt.

dbt staging drops the retired copy of a fiscal-year move and fails loudly on
any other duplicate (dbt/macros/award_fy_moves.sql,
dbt/models/audit/audit_award_duplicate_copies.sql). Code that sums the raw
contracts/assistance parquet itself — `govbudget entity-graph` and the site
gates' lake recomputes — must apply the SAME rule, or a fresh sync that moves
a key double-counts it there while the warehouse counts it once.

govbudget.award_moves is that rule, once, in Python. These tests hold it to
the dbt audit model on the SAME fixture shapes tests/test_dbt_award_fy_moves.py
builds (its helpers are imported, not restated), then prove each caller reads
through it: a moved key retires exactly one copy; an ambiguous one raises.
"""
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import duckdb
import pytest

from govbudget import award_moves
from govbudget.award_moves import (
    AmbiguousAwardDuplicateError,
    AwardArchiveError,
    RetiredCopy,
    duplicate_copies,
    find_moves,
    register_award_rows,
)
from test_dbt_award_fy_moves import (
    _assistance,
    _audit_sql,
    _contract,
    _write_assistance,
    _write_contracts,
    _write_the_moves,
)

ROOT = Path(__file__).resolve().parents[1]
GATES = ROOT / "site" / "scripts" / "gates"


def _globs(data_dir: Path) -> list[str]:
    """The two archive globs, as cmd_entity_graph and the gates spell them."""
    return [
        str(data_dir / "parquet" / "contracts" / "*" / "*.parquet"),
        str(data_dir / "parquet" / "assistance" / "*" / "*.parquet"),
    ]


def _write_ambiguous(data_dir: Path) -> None:
    """test_an_ambiguous_duplicate_fails_the_build_loudly's lake: every shape
    the rule refuses, at once (two copies in one FY, equal dates, three
    copies, an undated copy)."""
    _write_contracts(data_dir, 2024, [
        _contract("THREE001", "2024-01-01", "1", "2024-02-01 00:00:00+00"),
    ])
    _write_contracts(data_dir, 2025, [
        _contract("SAMEFY01", "2025-01-01", "5", "2025-02-01 00:00:00+00"),
        _contract("TIEDATE1", "2025-01-02", "6", "2026-01-01 00:00:00+00"),
        _contract("THREE001", "2025-01-03", "2", "2025-02-01 00:00:00+00"),
        _contract("NODATE01", "2025-01-04", "7", None),
    ])
    _write_contracts(data_dir, 2025, [
        _contract("SAMEFY01", "2025-01-05", "8", "2026-02-01 00:00:00+00"),
    ], part="part-2")
    _write_contracts(data_dir, 2026, [
        _contract("TIEDATE1", "2025-10-01", "9", "2026-01-01 00:00:00+00"),
        _contract("THREE001", "2025-10-02", "3", "2026-08-02 00:00:00+00"),
        _contract("NODATE01", "2025-10-03", "4", "2026-08-02 00:00:00+00"),
    ])


def _dbt_audit(data_dir: Path) -> Counter:
    """The committed dbt audit model's own SQL over the same parquet, read the
    way dbt/models/sources.yml reads it (hive_partitioning, union_by_name,
    filename) — one entry per copy (a multiset: two copies in one fiscal
    year are two entries)."""
    con = duckdb.connect()
    try:
        for table, key, sub in (
            ("contracts", "contract_transaction_unique_key", "contracts"),
            ("assistance", "assistance_transaction_unique_key", "assistance"),
        ):
            d = data_dir / "parquet" / sub
            if any(d.glob("*/*.parquet")):
                con.execute(
                    f"create view {table} as select * from read_parquet("
                    f"'{d}/*/*.parquet', hive_partitioning=true,"
                    f" union_by_name=true, filename=true)"
                )
            else:
                con.execute(
                    f"create table {table} ({key} varchar, fy varchar,"
                    f" last_modified_date varchar, filename varchar)"
                )
        rows = con.execute(
            "select award_type, transaction_key, fiscal_year, resolution, ambiguity"
            " from (" + _audit_sql() + ")"
        ).fetchall()
    finally:
        con.close()
    return Counter(rows)


def _python_audit(data_dir: Path) -> Counter:
    con = duckdb.connect()
    try:
        copies = duplicate_copies(con, _globs_present(data_dir))
    finally:
        con.close()
    return Counter(
        (c.award_type, c.transaction_key, c.fiscal_year, c.resolution, c.ambiguity)
        for c in copies
    )


def _globs_present(data_dir: Path) -> list[str]:
    return [g for g in _globs(data_dir) if list(Path(g).parent.parent.glob("*/*.parquet"))]


# ── the rule itself ──────────────────────────────────────────────────────────

def test_a_moved_key_retires_exactly_one_copy(tmp_path):
    """The 2026-09-24 shape, un-reconciled: two contract moves and one
    assistance move. Exactly the three older copies are retired — the same
    three dbt's audit_award_fy_moves lists — and nothing else is touched."""
    _write_the_moves(tmp_path)
    con = duckdb.connect()
    try:
        moves = register_award_rows(
            con, _globs(tmp_path), view="awards", require_transaction_keys=True
        )
        assert [
            (m.award_type, m.transaction_key, m.kept_fiscal_year,
             m.kept_last_modified_date, m.retired_fiscal_year,
             m.retired_last_modified_date,
             Path(m.kept_file).parent.name + "/" + Path(m.kept_file).name,
             Path(m.retired_file).parent.name + "/" + Path(m.retired_file).name)
            for m in moves.retired
        ] == [
            ("assistance", "AMOVED01", 2025, "2026-08-01 12:00:00.5+00", 2024,
             "2024-03-01 00:00:00+00", "fy=2025/part.parquet", "fy=2024/part.parquet"),
            ("contract", "MOVED001", 2026, "2026-08-02 00:00:00+00", 2025,
             "2025-04-01 09:00:00+00", "fy=2026/part.parquet", "fy=2025/part.parquet"),
            ("contract", "MOVED002", 2026, "2026-08-02 00:00:00+00", 2024,
             "2025-01-01 00:00:00+00", "fy=2026/part.parquet", "fy=2024/part.parquet"),
        ]
        # 7 contract + 2 assistance rows in the archives; 3 retired.
        assert con.execute("select count(*) from awards").fetchone()[0] == 6
        kept = con.execute(
            "select coalesce(contract_transaction_unique_key,"
            " assistance_transaction_unique_key), cast(fy as integer),"
            " try_cast(federal_action_obligation as double)"
            " from awards where coalesce(contract_transaction_unique_key,"
            " assistance_transaction_unique_key) in ('MOVED001','MOVED002','AMOVED01')"
            " order by 1"
        ).fetchall()
        assert kept == [("AMOVED01", 2025, 650.0), ("MOVED001", 2026, 120.0),
                        ("MOVED002", 2026, 450.0)]
        # The warehouse totals test_dbt_award_fy_moves expects (raw: 1,211 / 1,350).
        totals = dict(con.execute(
            "select recipient_uei, sum(try_cast(federal_action_obligation as double))"
            " from awards group by 1"
        ).fetchall())
        assert totals == {"UEI9": 611.0, "UEI8": 650.0}
    finally:
        con.close()
    assert moves.summary() == (
        "fiscal-year move rule (ROADMAP #133): retired 2 contract and"
        " 1 assistance copies"
    )


def test_the_python_rule_and_the_dbt_audit_model_agree_on_the_moves(tmp_path):
    _write_the_moves(tmp_path)
    got = _python_audit(tmp_path)
    assert got == _dbt_audit(tmp_path)
    assert {r[3] for r in got} == {"keep", "retire"} and sum(got.values()) == 6


def test_an_ambiguous_duplicate_raises_and_names_every_key(tmp_path):
    _write_ambiguous(tmp_path)
    con = duckdb.connect()
    try:
        with pytest.raises(AmbiguousAwardDuplicateError) as exc:
            register_award_rows(con, _globs_present(tmp_path), view="awards")
        # Nothing is registered: no reader can go on to sum a half-applied rule.
        assert not con.execute(
            "select count(*) from duckdb_views() where view_name = 'awards'"
        ).fetchone()[0]
    finally:
        con.close()
    msg = str(exc.value)
    for key, reason in (
        ("NODATE01", "a copy has no parseable last_modified_date"),
        ("SAMEFY01", "both copies sit in one fiscal year"),
        ("THREE001", "more than two copies"),
        ("TIEDATE1", "both copies carry the same last_modified_date"),
    ):
        assert f"{key}: {reason}" in msg, msg
    assert "4 ambiguous" in msg and "ROADMAP #133" in msg
    # ...and the dbt audit model classifies the same nine copies the same way.
    assert _python_audit(tmp_path) == _dbt_audit(tmp_path)


def test_the_newer_copy_is_kept_whichever_year_it_sits_in(tmp_path):
    _write_contracts(tmp_path, 2025, [_contract("K", "2025-01-01", "1", "2026-08-02 00:00:00+00")])
    _write_contracts(tmp_path, 2026, [_contract("K", "2025-10-01", "2", "2025-01-01 00:00:00+00")])
    con = duckdb.connect()
    try:
        moves = find_moves(con, _globs_present(tmp_path))
    finally:
        con.close()
    assert [(m.transaction_key, m.kept_fiscal_year, m.retired_fiscal_year)
            for m in moves.retired] == [("K", 2025, 2026)]
    assert _python_audit(tmp_path) == _dbt_audit(tmp_path)


@pytest.mark.parametrize("copies, reason", [
    ([("2025", "2025-01-01"), ("2025", "2026-01-01")],
     "both copies sit in one fiscal year"),
    ([("2025", "2026-01-01 00:00:00+00"), ("2026", "2026-01-01 00:00:00+00")],
     "both copies carry the same last_modified_date"),
    ([("2024", "2024-01-01"), ("2025", "2025-01-01"), ("2026", "2026-01-01")],
     "more than two copies"),
    ([("2025", None), ("2026", "2026-01-01")],
     "a copy has no parseable last_modified_date"),
    ([("2025", "not a date"), ("2026", "2026-01-01")],
     "a copy has no parseable last_modified_date"),
    # the same instant spelled two ways is one date, not two
    ([("2025", "2026-01-01 00:00:00+00"), ("2026", "2026-01-01 01:00:00+01")],
     "both copies carry the same last_modified_date"),
])
def test_every_other_duplicate_is_ambiguous_and_nothing_is_retired(tmp_path, copies, reason):
    """test_dbt_award_fy_moves' parametrized shapes, as parquet archives."""
    for i, (fy, modified) in enumerate(copies):
        _write_contracts(tmp_path, int(fy), [_contract("K", f"{fy}-01-0{i + 1}", "1", modified)],
                         part=f"part-{i}")
    got = _python_audit(tmp_path)
    assert {r[3] for r in got} == {"ambiguous"}
    assert {r[4] for r in got} == {reason}
    assert sum(got.values()) == len(copies)
    assert got == _dbt_audit(tmp_path)
    con = duckdb.connect()
    try:
        with pytest.raises(AmbiguousAwardDuplicateError, match=reason):
            find_moves(con, _globs_present(tmp_path))
    finally:
        con.close()


def test_a_key_in_both_archives_is_not_a_move(tmp_path):
    """Per archive, as dbt and the reconcile script: a key present once in
    contracts and once in assistance is left to the warehouse's unique test."""
    _write_contracts(tmp_path, 2025, [_contract("X1", "2025-01-01", "1", "2025-02-01")])
    _write_assistance(tmp_path, 2026, [_assistance("X1", "2025-10-01", "2", "2026-02-01")])
    con = duckdb.connect()
    try:
        moves = register_award_rows(con, _globs(tmp_path), view="awards")
        assert moves.retired == ()
        assert con.execute("select count(*) from awards").fetchone()[0] == 2
    finally:
        con.close()
    assert _python_audit(tmp_path) == _dbt_audit(tmp_path) == Counter()


def test_rows_without_a_key_are_never_duplicates(tmp_path):
    """dbt finds duplicates among non-NULL keys only; two key-less rows in two
    fiscal years are two rows, never a move and never ambiguous."""
    _write_contracts(tmp_path, 2025, [_contract("K1", "2025-01-01", "1", "2025-02-01")])
    _write_contracts(tmp_path, 2026, [_contract("K2", "2025-10-01", "1", "2026-02-01")])
    c = tmp_path / "parquet" / "contracts"
    for src, dst in (("fy=2025", "fy=2026"), ("fy=2026", "fy=2025")):
        duckdb.sql(
            f"copy (select * replace (null::varchar as contract_transaction_unique_key)"
            f" from read_parquet('{c / src}/part.parquet', hive_partitioning=false))"
            f" to '{c / dst}/nokey.parquet' (format parquet)"
        )
    con = duckdb.connect()
    try:
        moves = register_award_rows(con, _globs_present(tmp_path), view="awards")
        assert moves.retired == ()
        assert con.execute("select count(*) from awards").fetchone()[0] == 4
    finally:
        con.close()


def test_with_nothing_to_retire_every_row_is_read(tmp_path):
    _write_contracts(tmp_path, 2025, [_contract("A1", "2025-01-01", "5", "2025-02-01")])
    _write_assistance(tmp_path, 2025, [_assistance("B1", "2025-01-01", "7", "2025-02-01")])
    con = duckdb.connect()
    try:
        moves = register_award_rows(con, _globs(tmp_path), view="awards",
                                    require_transaction_keys=True)
        assert moves.retired == () and moves.unkeyed == ()
        assert con.execute(
            "select count(*), sum(try_cast(federal_action_obligation as double)) from awards"
        ).fetchone() == (2, 12.0)
    finally:
        con.close()
    assert moves.summary() == (
        "fiscal-year move rule (ROADMAP #133): retired 0 contract and"
        " 0 assistance copies"
    )


def _write_keyless(data_dir: Path) -> str:
    d = data_dir / "contracts" / "fy=2024"
    d.mkdir(parents=True)
    duckdb.sql(
        "copy (select 'U1' as recipient_uei, '10' as federal_action_obligation)"
        f" to '{d}/part.parquet' (format parquet)"
    )
    return str(data_dir / "contracts" / "*" / "*.parquet")


def test_an_archive_without_a_transaction_key_is_refused_when_keys_are_required(tmp_path):
    glob = _write_keyless(tmp_path)
    con = duckdb.connect()
    try:
        with pytest.raises(AwardArchiveError, match="no transaction key column"):
            register_award_rows(con, [glob], view="awards", require_transaction_keys=True)
        # Not required (synthetic fixtures): read whole, as dbt treats a NULL
        # key — never a duplicate — and named in the report.
        moves = register_award_rows(con, [glob], view="awards")
        assert moves.unkeyed == (glob,)
        assert "no transaction key column" in moves.summary()
        assert con.execute("select count(*) from awards").fetchone()[0] == 1
    finally:
        con.close()


def test_a_keyed_archive_without_fiscal_year_or_revision_time_is_refused(tmp_path):
    d = tmp_path / "flat"
    d.mkdir()
    duckdb.sql(
        "copy (select 'K' as contract_transaction_unique_key, '1' as federal_action_obligation)"
        f" to '{d}/part.parquet' (format parquet)"
    )
    con = duckdb.connect()
    try:
        with pytest.raises(AwardArchiveError, match="fy.*last_modified_date"):
            register_award_rows(con, [str(d / "*.parquet")], view="awards")
    finally:
        con.close()


def test_a_glob_that_mixes_both_archives_is_refused(tmp_path):
    _write_the_moves(tmp_path)
    con = duckdb.connect()
    try:
        with pytest.raises(AwardArchiveError, match="both"):
            register_award_rows(
                con, [str(tmp_path / "parquet" / "*" / "*" / "*.parquet")], view="awards"
            )
    finally:
        con.close()


# ── the gate helpers read through the same rule ─────────────────────────────

def _gate(name: str):
    spec = importlib.util.spec_from_file_location(
        name.replace("-", "_"), GATES / f"{name}.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_gate_helpers_load_this_module_by_path():
    """No gate helper may depend on the package being importable from its
    cwd; each loads src/govbudget/award_moves.py itself — this file."""
    for name in ("flowdown-recompute", "entitytotals-recompute", "familylabel-recompute"):
        mod = _gate(name)
        assert Path(mod.award_moves.__file__).resolve() == Path(award_moves.__file__).resolve()


def _xwalk(data_dir: Path) -> Path:
    from govbudget.entity_graph import build_entity_xwalk

    return build_entity_xwalk(
        award_glob=_globs_present(data_dir),
        out_path=data_dir / "parquet" / "entities" / "entity_xwalk.parquet",
        parent_exclusions=(),
    )


def _flowdown(monkeypatch, capsys, data_dir: Path, request: dict):
    mod = _gate("flowdown-recompute")
    monkeypatch.setattr(mod, "LAKE", data_dir / "parquet")
    req = data_dir / "req.json"
    req.write_text(json.dumps(request))
    monkeypatch.setattr(sys, "argv", ["flowdown-recompute.py", str(req)])
    capsys.readouterr()
    mod.main()
    return json.loads(capsys.readouterr().out), mod


def test_flowdown_recompute_counts_a_moved_contract_once(tmp_path, monkeypatch, capsys):
    """G9's lake recompute agrees with stg_flow_contracts: FY2025 is 13 (the
    MOVED001 FY2025 copy, 100, is retired — test_dbt_award_fy_moves asserts
    the same 13.0 on the warehouse), FY2024 11, FY2026 587."""
    _write_the_moves(tmp_path)
    _xwalk(tmp_path)
    out, _mod = _flowdown(monkeypatch, capsys, tmp_path,
                          {"spend_fys": [2024, 2025, 2026], "class_totals": True})
    assert {fy: out["spend"][fy]["total"] for fy in ("2024", "2025", "2026")} == {
        "2024": 11.0, "2025": 13.0, "2026": 587.0,
    }
    assert out["class_totals"] == {
        "2024": {"full_and_open": 11.0},
        "2025": {"full_and_open": 13.0},
        "2026": {"full_and_open": 587.0},
    }


def test_flowdown_recompute_refuses_an_ambiguous_lake(tmp_path, monkeypatch, capsys):
    _write_ambiguous(tmp_path)
    (tmp_path / "parquet" / "entities").mkdir(parents=True)
    duckdb.sql(
        "copy (select 'x' as recipient_uei, 'X' as family_key)"
        f" to '{tmp_path}/parquet/entities/entity_xwalk.parquet' (format parquet)"
    )
    mod = _gate("flowdown-recompute")
    monkeypatch.setattr(mod, "LAKE", tmp_path / "parquet")
    req = tmp_path / "req.json"
    req.write_text(json.dumps({"class_totals": True}))
    monkeypatch.setattr(sys, "argv", ["flowdown-recompute.py", str(req)])
    with pytest.raises(mod.award_moves.AmbiguousAwardDuplicateError):
        mod.main()


def test_entitytotals_recompute_sums_the_lake_the_crosswalk_reads(tmp_path):
    """basis.mjs leg d fits the crosswalk's total to a window of per-FY lake
    totals; a move-aware crosswalk needs a move-aware lake side, or the fit
    breaks by exactly the retired copies."""
    _write_the_moves(tmp_path)
    xw = _xwalk(tmp_path)
    mod = _gate("entitytotals-recompute")
    con = duckdb.connect()
    try:
        per_fy = mod.lake_totals_by_fy(con, _globs(tmp_path), xw)
    finally:
        con.close()
    assert per_fy == [(2024, 11.0), (2025, 13.0 + 650.0), (2026, 587.0)]
    xwalk_total = duckdb.sql(f"select sum(total_obligation) from read_parquet('{xw}')").fetchone()[0]
    assert sum(v for _, v in per_fy) == xwalk_total == 1261.0

    _write_ambiguous(tmp_path / "amb")
    con = duckdb.connect()
    try:
        with pytest.raises(mod.award_moves.AmbiguousAwardDuplicateError):
            mod.lake_totals_by_fy(con, _globs_present(tmp_path / "amb"), xw)
    finally:
        con.close()


def test_familylabel_recompute_ranks_registrations_without_the_retired_copy(tmp_path):
    """Leg l mirrors entity_graph's parent pick; the pick no longer sees a
    retired copy, so the margin census must not either."""
    _write_the_moves(tmp_path)
    xw = _xwalk(tmp_path)
    mod = _gate("familylabel-recompute")
    con = duckdb.connect()
    try:
        con.execute(f"create table entity_xwalk as select * from read_parquet('{xw}')")
        con.execute(
            "create table dim_entities as select family_key, max(family_key) as display_name,"
            " sum(total_obligation) as total_obligation from entity_xwalk group by 1"
        )
        out = mod.recompute(con, _globs(tmp_path), [], require_transaction_keys=True)
        assert con.execute(
            "select sum(obligation) from _tx where recipient_uei = 'UEI9'"
        ).fetchone()[0] == 611.0
        won = {f["dominant_uei"]: f["won_dollars"] for f in out["families"]}
        assert won == {"UEI9": 611.0, "UEI8": 650.0}
    finally:
        con.close()

    _write_ambiguous(tmp_path / "amb")
    con = duckdb.connect()
    try:
        con.execute(f"create table entity_xwalk as select * from read_parquet('{xw}')")
        con.execute("create table dim_entities as select family_key, family_key as display_name,"
                    " total_obligation from entity_xwalk")
        with pytest.raises(mod.award_moves.AmbiguousAwardDuplicateError):
            mod.recompute(con, _globs_present(tmp_path / "amb"), [])
    finally:
        con.close()
