"""Read-only review of one staged USAspending fiscal-year partition.

Write the report before replacing any live partition. Changes in cumulative
archive totals are coverage/revision changes, not year-over-year spending growth.
"""
import argparse
import json
from pathlib import Path

import duckdb

KEYS = {"contracts": "contract_transaction_unique_key", "assistance": "assistance_transaction_unique_key"}


def review_partition(previous: Path, staged: Path, dataset: str, fiscal_year: int) -> dict:
    key = KEYS[dataset]
    report = {"dataset": dataset, "fiscal_year": fiscal_year, "errors": []}
    with duckdb.connect() as con:
        for label, directory in (("previous", previous), ("staged", staged)):
            files = sorted(str(p) for p in directory.glob("*.parquet"))
            if not files:
                raise ValueError(f"No Parquet files in {directory}")
            con.read_parquet(files, union_by_name=True).create_view(label)
            row = con.execute(f"""
                select count(*) as rows, count(distinct {key}) as distinct_keys,
                    count(*) filter (where {key} is null or {key} = '') as missing_keys,
                    min(try_cast(action_date as date)) as first_action,
                    max(try_cast(action_date as date)) as last_action,
                    count(*) filter (where try_cast(action_date as date) is null) as invalid_dates,
                    count(*) filter (where try_cast(action_date as date) < make_date(?, 10, 1)
                        or try_cast(action_date as date) >= make_date(?, 10, 1)) as wrong_fiscal_year,
                    sum(try_cast(federal_action_obligation as decimal(24,2))) as net_obligations,
                    count(*) filter (where try_cast(federal_action_obligation as decimal(24,2)) is null) as invalid_amounts
                from {label}
            """, [fiscal_year - 1, fiscal_year])
            report[label] = dict(zip([d[0] for d in row.description], row.fetchone()))
        old, new = report['previous'], report['staged']
        for field in ('missing_keys', 'invalid_dates', 'wrong_fiscal_year', 'invalid_amounts'):
            if new[field]:
                report['errors'].append(f"staged {field}: {new[field]}")
        if new['rows'] != new['distinct_keys']:
            report['errors'].append('staged transaction keys are not unique')
        if new['rows'] < max(1, old['rows'] * 0.8):
            report['errors'].append('staged partition is empty or below the 80% row-retention floor')
        if old['last_action'] and (not new['last_action'] or new['last_action'] < old['last_action']):
            report['errors'].append('staged action-date coverage regressed')
        report['retired_keys'] = con.execute(f'select count(*) from previous p anti join staged s using ({key})').fetchone()[0]
        report['added_keys'] = con.execute(f'select count(*) from staged s anti join previous p using ({key})').fetchone()[0]
        report['revised_amounts_or_dates'] = con.execute(f"""
            select count(*) from previous p join staged s using ({key})
            where try_cast(p.federal_action_obligation as decimal(24,2)) is distinct from try_cast(s.federal_action_obligation as decimal(24,2))
                or try_cast(p.action_date as date) is distinct from try_cast(s.action_date as date)
        """).fetchone()[0]
        report['staged_obligations_through_previous_cutoff'] = con.execute('select sum(try_cast(federal_action_obligation as decimal(24,2))) from staged where try_cast(action_date as date) <= ?', [old['last_action']]).fetchone()[0]
    report['passed'] = not report['errors']
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--staged', type=Path, required=True)
    parser.add_argument('--dataset', choices=KEYS, required=True)
    parser.add_argument('--fiscal-year', type=int, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = review_partition(args.previous, args.staged, args.dataset, args.fiscal_year)
    args.report.write_text(json.dumps(report, default=str, indent=2) + '\n')
    print(json.dumps(report, default=str))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
