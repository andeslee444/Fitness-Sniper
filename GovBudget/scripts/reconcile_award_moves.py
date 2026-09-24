"""Reconcile source-corrected transactions moved into one refreshed fiscal year.

Report-only unless --apply. A move is accepted only with exactly one old and
one refreshed row, different fiscal years, and a strictly newer source
last_modified_date. Ambiguity aborts the entire operation. Original Parquet
files and the row-level before/after report are retained for rollback.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil

import duckdb

from review_award_refresh import KEYS


def review_moves(parquet_dir: Path, dataset: str, fiscal_year: int) -> dict:
    key = KEYS[dataset]
    glob = str(parquet_dir/dataset/'fy=*/*.parquet')
    report = {'dataset':dataset,'fiscal_year':fiscal_year,'moves':[],'files':{}}
    with duckdb.connect(config={'threads':4}) as con:
        con.execute(f'create temp table duplicates as select {key} as key from read_parquet(?,hive_partitioning=true,union_by_name=true) group by {key} having count(*)>1', [glob])
        rows = con.execute(f'''select {key},fy,action_date,last_modified_date,federal_action_obligation,filename,
            try_cast(last_modified_date as timestamptz) as modified
            from read_parquet(?,hive_partitioning=true,union_by_name=true,filename=true) a
            join duplicates d on a.{key}=d.key order by {key},fy''',[glob]).fetchall()
        groups = defaultdict(list)
        for row in rows: groups[row[0]].append(row)
        for transaction_key, candidates in groups.items():
            fresh = [r for r in candidates if int(r[1])==fiscal_year]
            old = [r for r in candidates if int(r[1])!=fiscal_year]
            if len(fresh)!=1 or len(old)!=1 or not fresh[0][6] or not old[0][6] or fresh[0][6]<=old[0][6]:
                raise ValueError(f'Ambiguous or unproven fiscal-year move: {transaction_key}')
            fields = ['transaction_key','fiscal_year','action_date','last_modified_date','obligation','file']
            before=dict(zip(fields,old[0][:6]));after=dict(zip(fields,fresh[0][:6]))
            report['moves'].append({'before':before,'after':after})
        for path in sorted({r[side]['file'] for r in report['moves'] for side in ('before','after')}):
            report['files'][path]=hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return report


def apply_moves(report: dict, backup_dir: Path) -> int:
    key=KEYS[report['dataset']]
    if backup_dir.exists():
        raise ValueError('Use a new backup directory; never overwrite an earlier rollback snapshot')
    for name, digest in report['files'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:
            raise ValueError(f'Source changed after review: {name}')
    backup_dir.mkdir(parents=True)
    (backup_dir/'review.json').write_text(json.dumps(report,default=str,indent=2)+'\n')
    by_file=defaultdict(list)
    for move in report['moves']: by_file[move['before']['file']].append(move['before']['transaction_key'])
    replacements=[]
    with duckdb.connect(config={'threads':4}) as con:
        for i,(name,keys) in enumerate(sorted(by_file.items())):
            live=Path(name);backup=backup_dir/f'{i:03d}-before.parquet';replacement=backup_dir/f'{i:03d}-after.parquet'
            shutil.copy2(live,backup)
            con.execute('create or replace temp table retiring (key varchar)')
            con.executemany('insert into retiring values (?)',[(k,) for k in keys])
            removed=con.execute(f'select count(*) from read_parquet(?,hive_partitioning=false) p join retiring r on p.{key}=r.key',[str(live)]).fetchone()[0]
            if removed!=len(keys): raise ValueError('Retirement count changed after review')
            con.execute(f'create or replace temp table replacement as select p.* from read_parquet(?,hive_partitioning=false) p anti join retiring r on p.{key}=r.key',[str(live)])
            con.execute('copy replacement to ? (format parquet, compression zstd)',[str(replacement)])
            replacements.append((live,backup,replacement))
    changed=[]
    try:
        for live,backup,replacement in replacements:
            changed.append((live,backup))
            replacement.replace(live)
    except BaseException:
        for live,backup in changed: shutil.copy2(backup,live)
        raise
    return len(report['moves'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parquet-dir',type=Path,required=True)
    parser.add_argument('--dataset',choices=KEYS,required=True)
    parser.add_argument('--fiscal-year',type=int,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--backup-dir',type=Path)
    args=parser.parse_args()
    if args.apply and not args.backup_dir: parser.error('--apply requires --backup-dir')
    report=review_moves(args.parquet_dir,args.dataset,args.fiscal_year)
    args.report.write_text(json.dumps(report,default=str,indent=2)+'\n')
    if args.apply: apply_moves(report,args.backup_dir)
    print(json.dumps({'dataset':args.dataset,'proven_moves':len(report['moves']),'applied':args.apply}))


if __name__=='__main__': main()
