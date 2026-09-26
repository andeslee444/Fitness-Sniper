"""R-DEC-140 (stage-1 follow-up ruling, 2026-09-26): the 60 route moves of the
2026-09-19 announcement load are recorded BEFORE the loader next runs, from the
best evidence available, with 'unknown' where the evidence does not name the
prior method or confidence and the aggregate breakdown cited.

Migration 020 is a data migration: it matches each key AND the created_at the
evidence rests on (the loader's next delete-and-rebuild erases that
created_at), writes superseded_* + superseded_evidence, and — while the
2026-09-19 load is still the table's latest (rows carrying its transaction
time exist) — refuses to finish unless all 60 are recorded.

The migration's SQL is re-executed here against rows seeded inside a
rolled-back transaction; the fixture DB applied it once, on empty tables.
"""
import datetime as dt
import re
from pathlib import Path

import psycopg
import pytest

from govbudget.jbooks.db import MIGRATIONS_DIR

SQL = (MIGRATIONS_DIR / "020_budget_line_awards_superseded_history.sql").read_text()
LOAD_0919 = dt.datetime(2026, 9, 19, 4, 10, 37, 770102,
                        tzinfo=dt.timezone(dt.timedelta(hours=-4)))
ROW = re.compile(
    r"\('(?P<pe>[^']+)', '(?P<ex>[^']+)', (?P<fy>\d+), '(?P<piid>[^']+)',"
    r" timestamptz '(?P<created>[^']+)', '(?P<method>[^']+)',"
    r" '(?P<conf>[^']+)', '(?P<ev>[a-z_]+)'\)")


def _keys():
    return [m.groupdict() for m in ROW.finditer(SQL)]


@pytest.fixture()
def con(pg_dsn):
    with psycopg.connect(pg_dsn) as c:
        yield c
        c.rollback()


def _seed(con, k, *, created=None, method="announcement+lexicon"):
    con.execute(
        "insert into budget_line_awards (pe_bli, exhibit, fiscal_year,"
        " organization, award_piid, method, confidence, created_at)"
        " values (%s,%s,%s,'r140-test',%s,%s,'high',%s)",
        (k["pe"], k["ex"], int(k["fy"]), k["piid"], method,
         created or k["created"]))


def _the_0919_load_is_in_place(con):
    _seed(con, {"pe": "R140X", "ex": "R-1", "fy": "2026", "piid": "FRESH-0919",
                "created": LOAD_0919})


def test_the_migration_names_the_60_keys_and_their_routes():
    keys = _keys()
    assert len(keys) == 60
    assert len({(k["pe"], k["ex"], k["fy"], k["piid"]) for k in keys}) == 60
    routes = {}
    for k in keys:
        routes[(k["method"], k["conf"])] = routes.get((k["method"], k["conf"]), 0) + 1
    # fpds-ap is recorded for the 58 rows the fpds-ap transaction wrote; no
    # per-key confidence survives (45 medium / 13 low in aggregate); the two
    # mechanical rows' split (1 account low, 1 account+subagency medium) is
    # not recorded per key.
    assert routes == {("fpds-ap", "unknown"): 58, ("unknown", "unknown"): 2}


def test_the_migration_records_every_move_while_the_0919_load_stands(con):
    keys = _keys()
    _the_0919_load_is_in_place(con)
    for k in keys:
        _seed(con, k)
    con.execute(SQL)
    got = con.execute(
        "select superseded_method, superseded_confidence, superseded_at,"
        " superseded_evidence like 'R-DEC-140%%' from budget_line_awards"
        " where organization = 'r140-test' and superseded_method is not null"
    ).fetchall()
    assert len(got) == 60
    assert {(m, c, at, cited) for m, c, at, cited in got} == {
        ("fpds-ap", "unknown", LOAD_0919, True),
        ("unknown", "unknown", LOAD_0919, True)}


def test_a_key_whose_created_at_moved_is_not_recorded_and_the_migration_refuses(con):
    """A row the loader re-inserted since (new created_at) no longer carries
    the evidence: it must not be recorded, and while the 2026-09-19 load is
    still in place a short count stops the migration."""
    keys = _keys()
    _the_0919_load_is_in_place(con)
    for k in keys[:-1]:
        _seed(con, k)
    _seed(con, keys[-1], created=dt.datetime(2026, 9, 27, tzinfo=dt.timezone.utc))
    with pytest.raises(psycopg.errors.RaiseException, match="59 of the 60"):
        with con.transaction():
            con.execute(SQL)


def test_an_unguarded_rebuild_that_erased_every_created_at_is_refused(con):
    """Fix round 2 (pg checker, 2026-09-26): a loader run WITHOUT
    require_migrations (the pre-wave loader in the main checkout) deletes and
    re-inserts every row it owns, so no row carries the 2026-09-19 load's
    transaction time any more and not one of the 60 keys still carries the
    created_at its evidence rests on. That database must not pass as a fresh
    one: migrate tracks by file name, so a silent no-op would mark 020 applied
    with none of the 60 moves recorded (R-DEC-140: never lose provenance
    silently)."""
    rebuilt = dt.datetime(2026, 9, 27, tzinfo=dt.timezone.utc)
    for k in _keys():
        _seed(con, k, created=rebuilt)
    with pytest.raises(psycopg.errors.RaiseException,
                       match=r"60 of the 60 moved key\(s\)"):
        with con.transaction():
            con.execute(SQL)
    assert con.execute(
        "select count(*) from budget_line_awards where superseded_method"
        " is not null").fetchone()[0] == 0


def test_one_erased_key_is_refused_even_after_the_0919_load_is_gone(con):
    """The same, for a single key: no 2026-09-19 row is left (so the 60-count
    leg cannot fire), but one moved key is held by a loader-owned row whose
    created_at no longer matches and which carries no record."""
    keys = _keys()
    for k in keys[1:]:
        _seed(con, k, created=dt.datetime(2026, 9, 20, tzinfo=dt.timezone.utc))
        con.execute(
            "update budget_line_awards set superseded_method='fpds-ap',"
            " superseded_confidence='unknown', superseded_at=%s,"
            " superseded_evidence='carried' where award_piid=%s and pe_bli=%s",
            (LOAD_0919, k["piid"], k["pe"]))
    _seed(con, keys[0], created=dt.datetime(2026, 9, 20, tzinfo=dt.timezone.utc))
    with pytest.raises(psycopg.errors.RaiseException,
                       match=r"1 of the 60 moved key\(s\)"):
        with con.transaction():
            con.execute(SQL)


def test_rows_the_guarded_loader_rebuilt_with_their_records_pass(con):
    """After 020 and the guarded loader (which carries every record across its
    rebuild), the 60 keys carry new created_at values AND their records: that
    is not lost evidence, and re-executing 020 changes nothing."""
    rebuilt = dt.datetime(2026, 9, 27, tzinfo=dt.timezone.utc)
    for k in _keys():
        _seed(con, k, created=rebuilt)
    con.execute(
        "update budget_line_awards set superseded_method='fpds-ap',"
        " superseded_confidence='unknown', superseded_at=%s,"
        " superseded_evidence='carried' where organization='r140-test'",
        (LOAD_0919,))
    con.execute(SQL)
    assert con.execute(
        "select count(*) from budget_line_awards where organization='r140-test'"
        " and superseded_evidence = 'carried'").fetchone()[0] == 60


def test_a_key_another_route_holds_again_is_not_lost_evidence(con):
    """A moved key now held by a non-announcement route (the key moved back)
    has no announcement row to carry a record: nothing to refuse."""
    for k in _keys():
        _seed(con, k, created=dt.datetime(2026, 9, 27, tzinfo=dt.timezone.utc),
              method="fpds-ap")
    con.execute(SQL)
    assert con.execute(
        "select count(*) from budget_line_awards where superseded_method"
        " is not null").fetchone()[0] == 0


def test_on_a_database_without_the_0919_load_the_migration_is_a_no_op(con):
    con.execute(SQL)          # the fixture DB: nothing to match, nothing refused
    assert con.execute(
        "select count(*) from budget_line_awards where superseded_evidence"
        " is not null").fetchone()[0] == 0


def test_a_route_already_recorded_is_left_alone(con):
    """A key that already carries a record (say, one the loader wrote at a
    move) keeps it: the migration only fills a record that is missing, and a
    key recorded either way counts toward the 60."""
    keys = _keys()
    _the_0919_load_is_in_place(con)
    for k in keys:
        _seed(con, k)
    k = keys[0]
    con.execute(
        "update budget_line_awards set superseded_method='fpds-ap',"
        " superseded_confidence='medium', superseded_at=now()"
        " where award_piid=%s and pe_bli=%s", (k["piid"], k["pe"]))
    con.execute(SQL)
    assert con.execute(
        "select superseded_method, superseded_confidence, superseded_evidence"
        " from budget_line_awards where award_piid=%s and pe_bli=%s",
        (k["piid"], k["pe"])).fetchone() == ("fpds-ap", "medium", None)
    assert con.execute(
        "select count(*) from budget_line_awards where organization='r140-test'"
        " and superseded_evidence is not null").fetchone()[0] == 59
