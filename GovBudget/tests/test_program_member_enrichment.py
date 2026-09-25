"""Shared BLI codes must not copy another program's prose, figures or receipts."""
from pathlib import Path
import json

import duckdb
import pytest

from govbudget.export_site import (
    _emit_json_sidecars,
    _write_typed_parquet,
)
from jbooks.test_export_site_pg import _make_test_duckdb

MEMBERS = [
    ('0145', '1506N', 'Aircraft Procurement, Navy', 'N', True),
    ('0145', '1508N', 'Procurement of Ammunition, Navy and Marine Corps', 'N', True),
    ('30', '0300D', 'Procurement, Defense-Wide', 'OSD', True),
    ('30', '0300D', 'Procurement, Defense-Wide', 'DTRA', True),
]


@pytest.fixture(autouse=True)
def _fresh_default_duckdb_connection():
    """Run each case on its own DuckDB default connection.

    `_emit_json_sidecars` reads the narratives parquet through `duckdb.sql`,
    i.e. the PROCESS-GLOBAL default connection. In a full pytest run that
    connection arrives already aborted: tests/test_fiscaldata.py leaves a
    pending `duckdb.sql(...).fetchone()` result on it, and
    tests/test_precision_study.py then runs a lake query there that fails on
    purpose and is caught (DuckDB 1.5.3 keeps the transaction aborted), so
    every later `duckdb.sql` raises "Current transaction is aborted". These
    cases test the exporter, not that leftover state, so they get a fresh
    default connection and hand the previous one back untouched.
    """
    previous = duckdb.default_connection()
    fresh = duckdb.connect()
    duckdb.set_default_connection(fresh)
    try:
        yield
    finally:
        duckdb.set_default_connection(previous)
        fresh.close()


def detail(fid, pe, account, sha, org='N', amount=12.5, project=None):
    return (fid, pe, project, 'Project' if project else None,
            'PriorYear', amount, 'USD millions', f'line[{fid}]', org,
            'procurement', 2026, sha, 'unique', account)


def _member_export(tmp_path, extra_details=(), extra_narratives=()):
    """Run the sidecar writer over the four MEMBERS plus any extra rows.

    `extra_details` are `detail(...)` tuples; `extra_narratives` are
    (fact_id, pe_bli, title, org, document_sha256) for FY2026 narrative rows.
    """
    db = tmp_path / 'warehouse.duckdb'
    _make_test_duckdb(db)
    con = duckdb.connect(str(db))
    for pe, account, title, org, _ in MEMBERS:
        name = {'1506N': 'Hornet', '1508N': 'General Purpose Bombs'}.get(account, org)
        con.execute('''insert into dim_programs
            (pe_bli,title,org,exhibit_family,project_count,fy2024_actual_millions,
             fully_reconciled,account,account_title)
            values (?,?,?,'procurement',1,12.5,true,?,?)''',
            [pe, name, org, account, title])
    con.execute('''insert into fct_program_lobbying values
        ('shared-filing','0145','General Purpose Bombs','General|Purpose',
        'General purpose bombs lobbying','https://example.test/filing',
        'A client','lockheed','2026','keyword')''')
    con.close()
    out = tmp_path / 'site'
    data = out / 'data'
    data.mkdir(parents=True)
    narratives = []
    details = []
    bl_rows = []
    for i, (pe, account, account_title, org, _) in enumerate(MEMBERS):
        sha = f'document-{i}'
        name = f'{pe}/{account}/{org}'
        # Identical code, scenario AND amount across the two members must
        # survive display dedup because they are different source facts.
        details.append(detail(f'root-{i}', pe, account, sha, org))
        details.append(detail(f'project-{i}', pe, account, sha, org, amount=4.5, project='P1'))
        narratives.append((f'narr-{i}', pe, 'description', name,
                           f'{name} source text with $4.5 million.', 'line[1]', org, 2026, sha))
        bl_rows.append((f'workbook-{i}', 'P-1', 2026, account, account_title,
                        org, '01', 'Activity', pe, name, 'fy_2026_total',
                        12500.0, 'USD thousands', 'workbook', 'Sheet', 'A1'))
    narratives.append(('unknown', '0145', 'description', 'Unassigned',
                       'A shared code alone does not assign this narrative.',
                       'line[1]', 'N', 2026, 'no-detail-document'))
    details.extend(extra_details)
    for fid, pe, title, org, sha in extra_narratives:
        narratives.append((fid, pe, 'description', title,
                           f'{title} source text.', 'line[1]', org, 2026, sha))
    _write_typed_parquet(data / 'jbook_narratives.parquet', columns=[
        ('fact_id', 'varchar'), ('pe_bli', 'varchar'), ('kind', 'varchar'),
        ('title', 'varchar'), ('body', 'varchar'), ('xml_path', 'varchar'),
        ('org', 'varchar'), ('fiscal_year', 'integer'),
        ('document_sha256', 'varchar'),
    ], rows=narratives)
    citations = []
    for d in details:
        row = [None] * 27
        row[0], row[1], row[2] = d[0], 'jbook_pdf', 'USD millions'
        row[3], row[11], row[15] = str(d[5]), 'unique', d[11]
        row[17], row[18] = f'https://example.mil/{d[11]}.pdf', d[7]
        row[23], row[24], row[25] = str(d[5]), d[1], d[4]
        citations.append(tuple(row))
    for n in narratives:
        row = [None] * 27
        row[0], row[1], row[15] = n[0], 'jbook_narrative', n[8]
        row[17], row[18], row[24] = f'https://example.mil/{n[8]}.pdf', n[5], n[1]
        citations.append(tuple(row))
    _emit_json_sidecars(out_dir=out, duckdb_path=db, detail_rows=details,
                       bl_rows=bl_rows, citation_rows=citations, manifest={})
    return out


@pytest.fixture()
def member_export(tmp_path):
    return _member_export(tmp_path)


def _narrative_fids(out, slug):
    obj = json.loads((out / f'json/program_details/{slug}.json').read_text())
    return {n.get('fact_id') or n['title'] for n in obj['narratives']}


def test_narrative_assignment_needs_one_account_from_its_own_document(tmp_path):
    """A shared code's narrative publishes on a member only when its OWN
    document names exactly one member (ROADMAP #82, narrative axis).

    Rewritten at the 2026-09-25 integration. The live branch unit-tested this
    rule through two helpers of its own (`_narrative_document_accounts`,
    `_narrative_member_key`); the merged exporter keeps this branch's reviewed
    #82 implementation, which resolves the same rule inline (`_doc_account` +
    `_ProgramIdentity.split_key` inside `_emit_json_sidecars`). So the cases
    now run through the sidecar writer and assert what each page publishes.
    """
    out = _member_export(
        tmp_path,
        extra_details=[
            # 'mixed' files P-40 rows for 0145 under BOTH appropriations, so
            # the document cannot say which member its prose is about.
            detail('mixed-a', '0145', '1506N', 'mixed', amount=1.0, project='M1'),
            detail('mixed-b', '0145', '1508N', 'mixed', amount=2.0, project='M2'),
        ],
        extra_narratives=[
            ('narr-mixed', '0145', 'Mixed book', 'N', 'mixed'),
            ('narr-missing', '0145', 'No detail rows', 'N', 'missing'),
            ('narr-osd', '30', 'OSD book', 'OSD', 'no-detail-osd'),
            ('narr-unknown-org', '30', 'Unknown org', 'UNKNOWN', 'no-detail-x'),
            ('narr-unsplit', '0601101E', 'Ordinary code', 'DARPA', 'no-detail-y'),
        ],
    )
    # A document with ONE account for the code assigns its narrative to
    # that member (the fixture's own documents, unchanged by the extras).
    assert _narrative_fids(out, '0145-APN') == {'narr-0'}
    assert _narrative_fids(out, '0145-PANMC') == {'narr-1'}
    # An organization-split code keys on the row's own org; an org that
    # names no member publishes nowhere.
    assert _narrative_fids(out, '30-OSD') == {'narr-2', 'narr-osd'}
    assert _narrative_fids(out, '30-DTRA') == {'narr-3'}
    # Mixed-account and detail-less documents land on NEITHER member.
    published = set().union(*(
        _narrative_fids(out, slug)
        for slug in ('0145-APN', '0145-PANMC', '30-OSD', '30-DTRA')
    ))
    assert not published & {'narr-mixed', 'narr-missing', 'narr-unknown-org'}
    # An ordinary (unsplit) code keeps the bare-code list.
    assert 'narr-unsplit' in _narrative_fids(out, '0601101E')


def test_member_sidecars_keep_their_own_details_prose_and_sources(member_export):
    expected = {
        '0145-APN': (0, '1506N', 'N'), '0145-PANMC': (1, '1508N', 'N'),
        '30-OSD': (2, '0300D', 'OSD'), '30-DTRA': (3, '0300D', 'DTRA'),
    }
    programs = json.loads((member_export / 'json/programs.json').read_text())
    by_slug = {r['slug']: r for r in programs}
    citations = json.loads((member_export / 'json/citations.json').read_text())
    for slug, (i, account, org) in expected.items():
        obj = json.loads((member_export / f'json/program_details/{slug}.json').read_text())
        assert {r['fact_id'] for r in obj['details']} == {f'root-{i}', f'project-{i}'}
        assert [n['title'] for n in obj['narratives']] == [f'{slug.split("-")[0]}/{account}/{org}']
        assert [b['fact_id'] for b in obj['budget_lines']] == [f'workbook-{i}']
        assert by_slug[slug]['narrative_count'] == 1
        assert by_slug[slug]['fy2024_fact_id'] == f'root-{i}'
        assert [n['fact_id'] for n in obj['narratives']] == [f'narr-{i}']
        assert [link['fact_id'] for link in obj['narratives'][0]['amount_links']] == [f'project-{i}']
        cited = [r['fact_id'] for r in obj['details'] + obj['narratives']]
        assert {citations[fid]['official_url'] for fid in cited} == {
            f'https://example.mil/document-{i}.pdf'}
        # ROADMAP #82 (mention axis), the merged rule: on a shared code a
        # title-basis lobbying row publishes only on the member whose own
        # title carries every matched term. 'General|Purpose' is in
        # 0145-PANMC's title ("General Purpose Bombs") and not in 0145-APN's
        # ("Hornet"); code '30' has no lobbying rows.
        if slug == '0145-PANMC':
            assert [(m['filing_uuid'], m['matched_term'], m['evidence_kind'])
                    for m in obj['mentions']] == [
                ('shared-filing', 'General|Purpose', 'keyword')]
        else:
            assert obj['mentions'] == []
        assert obj['summary']['named_primes'] == []
        assert obj['summary']['lobbied_by'] is None
    assert not (member_export / 'json/program_details/0145.json').exists()


def test_years_matrix_projects_use_each_members_source(member_export):
    years = json.loads((member_export / 'json/years_matrix.json').read_text())
    # Inspect all nested program rows without coupling the regression to the
    # presentation wrapper used by the years page.
    def entries(value):
        if isinstance(value, dict):
            if 'slug' in value and 'projects' in value:
                yield value
            for v in value.values():
                yield from entries(v)
        elif isinstance(value, list):
            for v in value:
                yield from entries(v)
    rows = {r['slug']: r for r in entries(years)}
    for slug, i in [('0145-APN', 0), ('0145-PANMC', 1), ('30-OSD', 2), ('30-DTRA', 3)]:
        assert len(rows[slug]['projects']) == 1
        assert rows[slug]['projects'][0]['title'] == 'Project'
        assert list(rows[slug]['projects'][0]['cells'].values())[0]['fid'] == f'project-{i}'
