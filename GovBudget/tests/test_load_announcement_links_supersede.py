"""#140: the announcement loader keeps its override but records the route it
replaced (decided 2026-09-25 under the owner's delegation).

THE DEFECT. load_announcement_links.py upserts on budget_line_awards' unique
key (pe_bli, exhibit, fiscal_year, award_piid) with `do update set method=…,
confidence=…`. An announcement link that lands on a key another route already
holds (fpds-ap, a mechanical account* row) re-attributes that row in place, and
nothing records what it had been. On 2026-09-19 that moved 60 rows and two
published precision figures with no verdict changing.

These tests run the loader's REAL write step (`write_links`, hoisted out of
main() for this) against the fixture Postgres, inside a transaction that is
rolled back, so the delete of the loader's owned partition never reaches
another test's rows.
"""
import datetime as dt

import psycopg
import pytest

import load_announcement_links as lal  # scripts/ on sys.path (tests/conftest.py)

ORG = "supersede-test"
PE = "SU0601101E"


def _row(piid, method="announcement+lexicon", confidence="high", *,
         rationale="defense.gov contract announcement 1 (2020-01-01)",
         account=None, pe=PE):
    """One 13-column budget_line_awards tuple in the loader's own order."""
    return (pe, "R-1", 2026, ORG, piid, "RECIPIENT INC", "UEI000000000",
            1000.0, method, confidence, 2, rationale, account)


@pytest.fixture()
def con(pg_dsn):
    with psycopg.connect(pg_dsn) as c:
        yield c
        c.rollback()


def _seed(con, piid, method, confidence, **extra):
    cols = ["pe_bli", "exhibit", "fiscal_year", "organization", "award_piid",
            "method", "confidence", "rationale", *extra]
    vals = [PE, "R-1", 2026, ORG, piid, method, confidence, f"{method} route",
            *extra.values()]
    con.execute(
        f"insert into budget_line_awards ({', '.join(cols)})"
        f" values ({', '.join(['%s'] * len(vals))})", vals)


def _state(con, piid):
    return con.execute(
        "select method, confidence, superseded_method, superseded_confidence,"
        " superseded_at is not null from budget_line_awards"
        " where organization = %s and award_piid = %s", (ORG, piid)).fetchone()


def test_an_override_records_the_route_it_replaced(con):
    _seed(con, "PIID-FPDS", "fpds-ap", "medium")
    stats = lal.write_links(con.cursor(), [_row("PIID-FPDS")], [])
    assert _state(con, "PIID-FPDS") == (
        "announcement+lexicon", "high", "fpds-ap", "medium", True)
    assert stats["superseded_new"] == 1


def test_a_first_insert_records_no_prior_route(con):
    stats = lal.write_links(con.cursor(), [_row("PIID-FRESH")], [])
    assert _state(con, "PIID-FRESH") == (
        "announcement+lexicon", "high", None, None, False)
    assert stats["superseded_new"] == 0


def test_a_mechanical_row_is_recorded_too(con):
    """The mechanical crosswalk's rows are a route as well: 1 `account` low
    and 1 `account+subagency` medium row were among the 60 of 2026-09-19."""
    _seed(con, "PIID-ACCT", "account+subagency", "medium")
    lal.write_links(con.cursor(), [_row("PIID-ACCT")], [])
    assert _state(con, "PIID-ACCT") == (
        "announcement+lexicon", "high", "account+subagency", "medium", True)


def test_the_record_survives_the_loaders_own_rebuild(con):
    """Every run deletes the loader's whole partition and rebuilds it, so the
    fpds-ap row an earlier run replaced no longer exists to conflict with: the
    record has to be carried, unchanged, across the rebuild."""
    when = dt.datetime(2026, 9, 19, 4, 10, tzinfo=dt.timezone.utc)
    _seed(con, "PIID-CARRY", "announcement+lexicon", "high",
          superseded_method="fpds-ap", superseded_confidence="low",
          superseded_at=when)
    stats = lal.write_links(con.cursor(), [_row("PIID-CARRY")], [])
    row = con.execute(
        "select method, superseded_method, superseded_confidence, superseded_at"
        " from budget_line_awards where organization = %s and award_piid = %s",
        (ORG, "PIID-CARRY")).fetchone()
    assert row == ("announcement+lexicon", "fpds-ap", "low", when)
    assert stats["superseded_carried"] == 1
    assert stats["superseded_dropped"] == 0


def test_a_record_whose_link_drops_out_is_counted_not_hidden(con):
    """A link that stops being published takes its row with it — and the
    replaced route is not restored by this loader. The count says so."""
    when = dt.datetime(2026, 9, 19, 4, 10, tzinfo=dt.timezone.utc)
    _seed(con, "PIID-GONE", "announcement+lexicon", "high",
          superseded_method="fpds-ap", superseded_confidence="medium",
          superseded_at=when)
    stats = lal.write_links(con.cursor(), [_row("PIID-OTHER")], [])
    assert _state(con, "PIID-GONE") is None
    assert stats["superseded_dropped"] == 1
    assert stats["superseded_dropped_keys"] == [
        ((PE, "R-1", 2026, "PIID-GONE"), "fpds-ap", "medium")]


def test_a_pair_two_waves_both_carry_does_not_supersede_itself(con):
    """The loader concatenates every wave's surviving list, so a pair two
    waves produced arrives twice; the second upsert conflicts with the
    first. That is not a move from another route and must not be recorded
    as one."""
    rows = [_row("PIID-TWICE", rationale="wave 1"),
            _row("PIID-TWICE", rationale="wave 4")]
    stats = lal.write_links(con.cursor(), rows, [])
    assert _state(con, "PIID-TWICE") == (
        "announcement+lexicon", "high", None, None, False)
    assert stats["superseded_new"] == 0


def test_the_override_is_kept(con):
    """The ruling keeps the override: the announcement row wins the key."""
    _seed(con, "PIID-KEEP", "fpds-ap", "low")
    lal.write_links(con.cursor(), [_row("PIID-KEEP")], [])
    assert _state(con, "PIID-KEEP")[:2] == ("announcement+lexicon", "high")


def test_the_supersession_columns_are_all_or_none(con):
    with pytest.raises(psycopg.errors.CheckViolation):
        with con.transaction():
            _seed(con, "PIID-HALF", "announcement+lexicon", "high",
                  superseded_method="fpds-ap")


# ── R-DEC-140: the historical record survives, and the loader needs migrate ──

def test_a_historical_record_keeps_its_evidence_across_the_rebuild(con):
    """Migration 020 records the 60 moves of 2026-09-19 from evidence, with
    that evidence cited in superseded_evidence; the loader's rebuild must
    carry the evidence with the route, or the next run would turn a cited
    historical record into one that looks recorded at the move."""
    when = dt.datetime(2026, 9, 19, 8, 10, 37, 770102, tzinfo=dt.timezone.utc)
    _seed(con, "PIID-HIST", "announcement+lexicon", "high",
          superseded_method="fpds-ap", superseded_confidence="unknown",
          superseded_at=when, superseded_evidence="R-DEC-140: cited")
    stats = lal.write_links(con.cursor(), [_row("PIID-HIST")], [])
    row = con.execute(
        "select superseded_method, superseded_confidence, superseded_at,"
        " superseded_evidence from budget_line_awards"
        " where organization = %s and award_piid = %s",
        (ORG, "PIID-HIST")).fetchone()
    assert row == ("fpds-ap", "unknown", when, "R-DEC-140: cited")
    assert stats["superseded_carried"] == 1


def test_evidence_without_a_route_is_refused(con):
    with pytest.raises(psycopg.errors.CheckViolation):
        with con.transaction():
            _seed(con, "PIID-EV", "announcement+lexicon", "high",
                  superseded_evidence="a note about nothing")


def test_the_record_census_says_what_a_rebuild_carries_and_drops(con):
    when = dt.datetime(2026, 9, 19, 4, 10, tzinfo=dt.timezone.utc)
    for piid, evidence in (("PIID-C1", None), ("PIID-C2", "R-DEC-140: x"),
                           ("PIID-C3", "R-DEC-140: y")):
        _seed(con, piid, "announcement+lexicon", "high",
              superseded_method="fpds-ap", superseded_confidence="medium",
              superseded_at=when, superseded_evidence=evidence)
    census = lal.supersession_census(
        con.cursor(), {(PE, "R-1", 2026, "PIID-C1"), (PE, "R-1", 2026, "PIID-C2")},
        owner=ORG)
    assert census == {"stored": 3, "historical": 2, "carried": 2, "dropped": 1,
                      "dropped_keys": [(PE, "R-1", 2026, "PIID-C3")]}


def test_the_loader_refuses_to_write_before_every_migration_is_applied(con, tmp_path):
    """R-DEC-LOADER: chain order is migrate -> loader. Migration 019 adds the
    columns the loader writes and 020 records the 60 historical moves from
    created_at evidence the loader's next rebuild erases — so the loader
    refuses to write while any migration file is unapplied."""
    lal.require_migrations(con.cursor())               # the fixture DB: all applied
    (tmp_path / "001_init.sql").write_text("-- applied")
    (tmp_path / "999_not_yet.sql").write_text("select 1;")
    con.execute("insert into schema_migrations (name) values ('001_init.sql')"
                " on conflict do nothing")
    with pytest.raises(SystemExit, match="999_not_yet.sql"):
        lal.require_migrations(con.cursor(), migrations_dir=tmp_path)
