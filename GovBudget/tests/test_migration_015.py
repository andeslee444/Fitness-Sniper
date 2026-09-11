"""Migration 015: link_precision_samples.rubric (ROADMAP #79).

A verdict is only comparable to a verdict that answered the same question.
The 2026-09-04 study judged four strata on program ATTRIBUTION and one
(account+subagency) on whether the mechanical RULE had fired; the exporter
told them apart with a hand-named set. The column makes the distinction a
property of the row, so the filter is `rubric = 'attribution'` and nothing
else.

`pg_dsn` (root conftest) is a fresh DB with every migration applied, so the
column's constraints are tested directly; the BACKFILL is tested by replaying
the migration file against a probe table shaped like production's run.
"""
from pathlib import Path

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations" / "015_link_precision_rubric.sql"


def test_rubric_column_exists_and_is_not_null(pg_dsn):
    with psycopg.connect(pg_dsn) as pg:
        row = pg.execute(
            "select data_type, is_nullable from information_schema.columns"
            " where table_name = 'link_precision_samples' and column_name = 'rubric'"
        ).fetchone()
    assert row == ("text", "NO")


def test_insert_without_rubric_is_refused(pg_dsn):
    with psycopg.connect(pg_dsn) as pg, pytest.raises(psycopg.errors.NotNullViolation):
        pg.execute(
            "insert into link_precision_samples"
            " (sample_id, award_piid, pe_bli, method, verdict)"
            " values ('m015-null', 'M015-1', '0601101E', 'fpds-ap', 'confirmed')"
        )


def test_unknown_rubric_is_refused(pg_dsn):
    with psycopg.connect(pg_dsn) as pg, pytest.raises(psycopg.errors.CheckViolation):
        pg.execute(
            "insert into link_precision_samples"
            " (sample_id, award_piid, pe_bli, method, rubric, verdict)"
            " values ('m015-bad', 'M015-2', '0601101E', 'fpds-ap', 'vibes', 'confirmed')"
        )


def _probe_sql() -> str:
    # Same statements, different table: the migration's text is the thing
    # under test, so it is not re-typed here.
    return MIGRATION.read_text().replace("link_precision_samples", "lps_probe_015")


def test_backfill_stamps_the_2026_09_04_run_by_stratum(pg_dsn):
    """account+subagency -> rule-fired (its verdicts restated the rule), the
    four attribution strata -> attribution. Keyed on the DRAW-TIME method
    column, which is what the study table recorded."""
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("drop table if exists lps_probe_015")
        pg.execute(
            "create table lps_probe_015 (sample_id text, award_piid text,"
            " pe_bli text, method text, verdict text)"
        )
        pg.execute(
            """insert into lps_probe_015 values
               ('2026-09-04', 'HR001115C0035', '0602115E', 'account+subagency', 'confirmed'),
               ('2026-09-04', 'FA862019F2815', '0205219F', 'fpds-ap+account', 'confirmed'),
               ('2026-09-04', 'N0001917F0399', '0528', 'announcement+lexicon', 'confirmed'),
               ('2026-09-04', 'X1', '0601101E', 'fpds-ap', 'refuted'),
               ('2026-09-04', 'X2', '0601101E', 'subaward+lexicon', 'refuted')"""
        )
        pg.execute(_probe_sql())
        got = dict(pg.execute("select award_piid, rubric from lps_probe_015").fetchall())
        pg.execute("drop table lps_probe_015")
        pg.commit()
    assert got == {
        "HR001115C0035": "rule-fired",
        "FA862019F2815": "attribution",
        "N0001917F0399": "attribution",
        "X1": "attribution",
        "X2": "attribution",
    }


def test_backfill_refuses_to_guess_a_rubric_for_any_other_run(pg_dsn):
    """A row from a run the migration does not know about must fail SET NOT
    NULL loudly, never receive a label by default."""
    with psycopg.connect(pg_dsn) as pg:
        pg.execute("drop table if exists lps_probe_015")
        pg.execute(
            "create table lps_probe_015 (sample_id text, award_piid text,"
            " pe_bli text, method text, verdict text)"
        )
        pg.execute(
            "insert into lps_probe_015 values"
            " ('2026-09-05', 'HR001120C0001', '0602303E', 'account+subagency', 'refuted')"
        )
        pg.commit()
        with pytest.raises(psycopg.errors.NotNullViolation):
            pg.execute(_probe_sql())
        pg.rollback()
        pg.execute("drop table if exists lps_probe_015")
        pg.commit()
