"""A shared budget-line code keeps each program's money, link and receipt."""
from pathlib import Path
import json

import duckdb

from govbudget.export_site import (
    _build_geography_citation_rows,
    _build_usaspending_citation_rows,
    _emit_breakdowns,
    _emit_district_sidecars,
    fact_id_derived,
    fact_id_usaspending,
)

ROOT = Path(__file__).resolve().parents[1]


def test_two_members_in_one_district_keep_separate_amounts_and_receipts(tmp_path):
    db = tmp_path / "district.duckdb"
    con = duckdb.connect(str(db))
    con.execute("""
        create table dim_programs (
            pe_bli varchar, account varchar, account_title varchar,
            org varchar, exhibit_family varchar
        )
    """)
    con.execute("""
        insert into dim_programs values
            ('3010','1611N','Shipbuilding and Conversion, Navy','N','procurement'),
            ('3010','1810N','Other Procurement, Navy','N','procurement')
    """)
    con.execute("""
        create table fct_budget_to_awards (
            award_piid varchar, pe_bli varchar, account varchar,
            program_title varchar, organization varchar, confidence varchar
        )
    """)
    con.execute("""
        insert into fct_budget_to_awards values
            ('SHIP','3010','1611N','LPD Flight II','N','high'),
            ('RADIO','3010','1810N','Shipboard Tactical Communications','N','high'),
            ('SHIP','3010','1611N','LPD Flight II','N','high')
    """)
    con.execute("""
        create table fct_award_transactions (
            pop_state varchar, pop_district varchar, award_id_piid varchar,
            transaction_key varchar, recipient_uei varchar, obligation double
        )
    """)
    con.execute("""
        insert into fct_award_transactions values
            ('VA','VA-08','SHIP','T1','UEI1',900.0),
            ('VA','VA-08','SHIP','T2','UEI1',-100.0),
            ('VA','VA-08','RADIO','T3','UEI2',200.0)
    """)
    model = (ROOT / "dbt/models/marts/fct_district_programs.sql").read_text()
    for name in ('fct_award_transactions', 'fct_budget_to_awards'):
        model = model.replace("{{ ref('%s') }}" % name, name)
    con.execute("create table fct_district_programs as " + model)
    assert con.execute("""
        select account, program_title, transaction_count, total_obligation
        from fct_district_programs order by account
    """).fetchall() == [
        ('1611N', 'LPD Flight II', 2, 800.0),
        ('1810N', 'Shipboard Tactical Communications', 1, 200.0),
    ]
    con.execute("""
        create table fct_district_totals as
        select 'VA-08' as pop_district, 2 as award_count, 1000.0 as total_obligation
    """)
    con.execute("""
        create table dim_geography as
        select 'VA' as pop_state, 'VA-08' as pop_district,
               1000.0 as total_obligation
    """)
    con.close()

    citations = _build_usaspending_citation_rows(duckdb_path=db)
    fids = {
        account: fact_id_usaspending(
            'district_program', f'VA|VA-08|3010|{account}', 'total_obligation'
        )
        for account in ('1611N', '1810N')
    }
    by_fid = {row[0]: row for row in citations}
    assert len(by_fid) == len(citations) == 2
    assert json.loads(by_fid[fids['1611N']][22])['filters']['award_ids'] == ['SHIP']
    assert json.loads(by_fid[fids['1810N']][22])['filters']['award_ids'] == ['RADIO']
    geography = _build_geography_citation_rows(duckdb_path=db)
    total_fid = fact_id_derived('district', 'VA-08', 'total_cited_dollars')
    total = next(row for row in geography if row[0] == total_fid)
    assert set(json.loads(total[21])) == set(fids.values())

    con = duckdb.connect(str(db), read_only=True)
    out = tmp_path / 'districts'
    out.mkdir()
    _emit_district_sidecars(
        dist_dir=out, con=con,
        prog_titles={'3010': 'LPD Flight II / Shipboard Tactical Communications'},
        cited_fact_ids=set(by_fid), shared_pe_blis={'3010'},
    )
    _emit_breakdowns(
        json_dir=tmp_path, con=con, citation_rows=citations + geography,
        bl_rows=[], detail_rows=[],
    )
    con.close()
    breakdown = json.loads((tmp_path / 'breakdowns' / f'{total_fid}.json').read_text())
    assert {row['label']: row['v'] for row in breakdown['rows']} == {
        'LPD Flight II': 800.0, 'Shipboard Tactical Communications': 200.0,
    }
    detail = json.loads((out / 'VA-08.json').read_text())
    assert detail['program_count'] == 2
    assert detail['total_linkable_dollars'] == 1000
    assert detail['total_cited_dollars'] == 1000
    assert [(p['split_key'], p['title'], p['total_obligation'], p['fact_id'])
            for p in detail['programs']] == [
        ('3010-SCN', 'LPD Flight II', 800.0, fids['1611N']),
        ('3010-OPN', 'Shipboard Tactical Communications', 200.0, fids['1810N']),
    ]
    assert [p['program_url'] for p in detail['programs']] == [
        '/program/3010-SCN/', '/program/3010-OPN/',
    ]
