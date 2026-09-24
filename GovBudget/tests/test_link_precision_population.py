import duckdb
import psycopg
import pytest

from govbudget.export_site import _link_precision_for_export, _announcement_scope_precision
from govbudget.link_precision import published_link_rows
from precision_study import precision_by_method


def test_mart_membership_and_pair_grain_control_both_reports(pg_dsn):
    method = 'announcement+lexicon'
    with psycopg.connect(pg_dsn) as pg:
        for year in (2025,2026):
            pg.execute("insert into budget_line_awards (pe_bli,exhibit,fiscal_year,organization,award_piid,method,confidence) values ('POP-PE','R-1',%s,'TEST','POP-KEEP',%s,'high')",(year,method))
        pg.execute("insert into budget_line_awards (pe_bli,exhibit,fiscal_year,organization,award_piid,method,confidence) values ('POP-PE','R-1',2026,'TEST','POP-DEMOTED',%s,'high')",(method,))
        for piid,verdict in [('POP-KEEP','confirmed'),('POP-DEMOTED','refuted')]:
            pg.execute("insert into link_precision_samples (sample_id,award_piid,pe_bli,method,rubric,verdict) values ('2026-09-04',%s,'POP-PE',%s,'attribution',%s)",(piid,method,verdict))
    links=[{'award_piid':'POP-KEEP','pe_bli':'POP-PE','method':method}]*2
    with psycopg.connect(pg_dsn) as pg:
        block=_link_precision_for_export(pg,{method},published_links=links)
        wave=_announcement_scope_precision(pg,'2026-09-04',published_links=links)
    assert block['methods'][method]['confirmed'] == block['methods'][method]['sampled'] == 1
    assert wave['confirmed'] == wave['sampled'] == 1
    assert precision_by_method(pg_dsn,'2026-09-04',published_links=links) == {method:(1,1)}
    with psycopg.connect(pg_dsn) as pg:
        assert _link_precision_for_export(pg,{method},published_links=[]) == {}


def test_conflicting_methods_fail_closed(tmp_path):
    db=tmp_path/'mart.duckdb'
    with duckdb.connect(str(db)) as con:
        con.execute('create table fct_budget_to_awards (award_piid varchar, pe_bli varchar, method varchar, confidence varchar)')
        con.execute("insert into fct_budget_to_awards values ('A','P','fpds-ap','medium'),('A','P','account','medium')")
    with pytest.raises(ValueError,match='conflicting methods'):
        published_link_rows(db)
