"""Persist only the six already-reviewed PDF locators, after rechecking bytes.

Default is report-only. --apply updates provenance geometry atomically; source
identity, canonical amounts and adjudications are unchanged. The report saves
all prior rows for rollback. Run against the corrected, reviewed site artifacts
before regeneration, not against a new unresolved export.
"""
import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pdfplumber
import psycopg
from psycopg.rows import dict_row

from govbudget import config
from govbudget.export_site import fact_id_jbook
from repair_pdf_citation_units import REVIEWED, LOCATION_FIELDS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--site', type=Path, default=config.SITE_DIR)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    citations = json.loads((args.site/'json/citations.json').read_text())
    patches = []
    with psycopg.connect(config.PG_DSN, row_factory=dict_row) as pg:
        if not args.apply:
            pg.execute('set transaction read only')
        for fid, (token, y0, y1, x0, x1) in REVIEWED.items():
            c = citations[fid]
            assert c['kind'] == 'jbook_pdf' and c['resolution'] == 'unique'
            assert c['amount_text'] == token and c['units'] == 'USD millions'
            pdf = args.site/'pdfs'/f"{c['sha256']}.pdf"
            assert hashlib.sha256(pdf.read_bytes()).hexdigest() == c['sha256']
            with pdfplumber.open(pdf) as doc:
                page = doc.pages[c['page_number']-1]
                words = [w for w in page.extract_words() if w['text'] == token and y0 < w['top'] < y1 and x0 < w['x0'] < x1]
                assert len(words) == 1, f'Reviewed token is no longer unique: {fid}'
                word = words[0]
                assert all(abs(float(c[k])-word[w]) < 0.01 for k,w in [('x0','x0'),('x1','x1'),('top_pt','top'),('bottom_pt','bottom')])
            rows = pg.execute("select * from provenance_pages where target_kind='amount' and document_sha256=%s and pe_bli=%s and amount_millions=%s", (c['sha256'],c['pe_bli'],Decimal(token))).fetchall()
            matches = [r for r in rows if fact_id_jbook(r['document_sha256'],r['pe_bli'],r['project_number'],r['scenario'],r['amount_millions']) == fid]
            assert len(matches) == 1, f'Expected one source identity: {fid}'
            after = {k:c[k] for k in (*LOCATION_FIELDS,'amount_text','resolution')}
            after['candidate_pages'] = 1
            patches.append({'fact_id':fid,'before':matches[0],'after':after})
        args.report.write_text(json.dumps({'apply':args.apply,'patches':patches},default=str,indent=2)+'\n')
        if args.apply:
            for patch in patches:
                fields = list(patch['after'])
                result = pg.execute('update provenance_pages set '+', '.join(f'{f}=%s' for f in fields)+' where id=%s', [*(patch['after'][f] for f in fields),patch['before']['id']])
                assert result.rowcount == 1
    print(json.dumps({'reviewed_locators':len(patches),'applied':args.apply,'report':str(args.report)}))


if __name__ == '__main__':
    main()
