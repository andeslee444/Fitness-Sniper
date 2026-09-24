from pathlib import Path

import duckdb

from review_award_refresh import review_partition


def partition(path: Path, rows):
    path.mkdir()
    with duckdb.connect() as con:
        con.execute('create table t(contract_transaction_unique_key varchar, action_date varchar, federal_action_obligation varchar)')
        con.executemany('insert into t values (?, ?, ?)', rows)
        con.execute('copy t to ? (format parquet)', [str(path/'part.parquet')])
    return path


def test_separates_revisions_from_new_coverage(tmp_path):
    old = partition(tmp_path/'old', [('a','2025-10-01','100'),('b','2026-04-01','20')])
    new = partition(tmp_path/'new', [('a','2025-10-01','90'),('c','2026-08-01','50')])
    report = review_partition(old,new,'contracts',2026)
    assert report['passed']
    assert report['added_keys'] == report['retired_keys'] == report['revised_amounts_or_dates'] == 1
    assert report['staged_obligations_through_previous_cutoff'] == 90
    assert report['staged']['net_obligations'] == 140


def test_rejects_invalid_records_duplicates_and_regressed_coverage(tmp_path):
    old = partition(tmp_path/'old', [('a','2026-04-01','100')])
    new = partition(tmp_path/'new', [('a','2024-01-01','bad'),('a','bad','-50')])
    report = review_partition(old,new,'contracts',2026)
    assert not report['passed']
    assert len(report['errors']) == 5


def test_rejects_truncated_archive(tmp_path):
    old = partition(tmp_path/'old', [(str(i),'2026-04-01','1') for i in range(10)])
    new = partition(tmp_path/'new', [('a','2026-08-01','1')])
    assert not review_partition(old,new,'contracts',2026)['passed']
