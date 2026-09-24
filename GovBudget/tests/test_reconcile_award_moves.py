import duckdb
import pytest
from reconcile_award_moves import review_moves, apply_moves


def setup(root,newer='2026-08-02'):
    with duckdb.connect() as con:
        for year,modified in [(2025,'2026-01-01'),(2026,newer)]:
            p=root/'contracts'/f'fy={year}';p.mkdir(parents=True)
            con.execute('create or replace table t(contract_transaction_unique_key varchar, action_date varchar, last_modified_date varchar, federal_action_obligation varchar)')
            con.execute('insert into t values (?,?,?,?)',['moved',f'{year}-01-01',modified,'12'])
            con.execute('insert into t values (?,?,?,?)',[f'unique-{year}',f'{year}-01-01',modified,'7'])
            con.execute('copy t to ? (format parquet)',[str(p/'part.parquet')])


def test_only_proven_old_version_is_retired_and_operation_is_idempotent(tmp_path):
    setup(tmp_path/'lake')
    report=review_moves(tmp_path/'lake','contracts',2026)
    assert len(report['moves'])==1
    assert apply_moves(report,tmp_path/'backup')==1
    assert review_moves(tmp_path/'lake','contracts',2026)['moves']==[]
    with duckdb.connect() as con:
        assert con.execute('select count(*) from read_parquet(?)',[str(tmp_path/'lake/contracts/*/*.parquet')]).fetchone()[0]==3
        assert con.execute('select count(*) from read_parquet(?)',[str(tmp_path/'backup/000-before.parquet')]).fetchone()[0]==2


def test_equal_source_revision_fails_closed(tmp_path):
    setup(tmp_path/'lake',newer='2026-01-01')
    with pytest.raises(ValueError,match='Ambiguous'):
        review_moves(tmp_path/'lake','contracts',2026)


def test_changed_source_aborts_before_any_replace(tmp_path):
    setup(tmp_path/'lake')
    report=review_moves(tmp_path/'lake','contracts',2026)
    report['files'][next(iter(report['files']))]='wrong'
    with pytest.raises(ValueError,match='Source changed'):
        apply_moves(report,tmp_path/'backup')
    assert not (tmp_path/'backup').exists()
