"""The /data/ Explorer's "Lobbying totals by family + year" preset, run for real.

R-DEC-EXPLORER (final-review rulings, 2026-09-27; final review finding #9).
The preset's SQL lives in site/src/components/explorer.tsx and runs in the
reader's browser on DuckDB-WASM against the shipped parquet. Its old form
returned ``filing_count = 1`` on every row (COUNT(*) over a mart that is one
row per family and year) and no lobbying dollars. This test lifts the SQL
out of the component and runs it on data/site/data/fct_influence.parquet with
DuckDB — an in-memory connection reading one parquet file, nothing written.

The site-side shape (no COUNT(*), no obligations, income and expense never
added) is pinned in site/src/__tests__/explorer-influence-preset.test.ts.
"""

from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
EXPLORER = ROOT / "site" / "src" / "components" / "explorer.tsx"
PARQUET = ROOT / "data" / "site" / "data" / "fct_influence.parquet"
LABEL = "Lobbying totals by family + year"


def _preset_sql() -> str:
    src = EXPLORER.read_text(encoding="utf-8")
    case = src.index('case "fct_influence":')
    nxt = src.index("case ", case + len('case "fct_influence":'))
    block = src[case:nxt]
    assert f'label: "{LABEL}"' in block, "the fct_influence preset lost its label"
    m = re.search(r"sql: t\(`(.*?)`\)", block, re.S)
    assert m, "no sql: t(`...`) in the fct_influence case"
    return m.group(1).strip()


@pytest.fixture(scope="module")
def result():
    if not PARQUET.exists():
        pytest.skip("no exported fct_influence.parquet")
    sql = _preset_sql()
    con = duckdb.connect()  # in-memory; the parquet is only read
    try:
        # The browser registers each dataset under its file name; here the
        # quoted name resolves against the export directory instead.
        rel = sql.replace("'fct_influence.parquet'", f"'{PARQUET.as_posix()}'")
        cur = con.execute(rel)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        truth = con.execute(
            "select family_key, filing_year, filings_count, lobbying_income_usd,"
            " lobbying_expense_usd from read_parquet(?)",
            [PARQUET.as_posix()],
        ).fetchall()
        n = con.execute("select count(*) from read_parquet(?)", [PARQUET.as_posix()]).fetchone()[0]
    finally:
        con.close()
    return cols, rows, {(r[0], r[1]): r[2:] for r in truth}, n


def test_columns_are_the_ones_the_title_promises(result):
    cols, _rows, _truth, _n = result
    assert cols == ["family_key", "filing_year", "filings", "income_usd", "expense_usd"]


def test_every_row_is_the_marts_own_figures(result):
    _cols, rows, truth, n = result
    assert len(rows) == min(50, n) and rows, "the preset returned nothing"
    for family_key, filing_year, filings, income, expense in rows:
        want = truth[(family_key, filing_year)]
        assert (filings, income, expense) == want, (family_key, filing_year)


def test_filing_counts_are_real_not_one_per_row(result):
    # The defect's signature: every row read 1. Lockheed Martin's years are
    # 59 / 65 / 33 on the chain-G export; any real export has a family-year
    # with more than one filing.
    cols, rows, _truth, _n = result
    assert "filings" in cols, f"no filings column: {cols}"
    i = cols.index("filings")
    assert max(r[i] for r in rows) > 1
    assert len({r[i] for r in rows}) > 1


def test_order_is_most_filings_first_and_total(result):
    _cols, rows, _truth, _n = result
    keys = [(-r[2], r[0], -int(r[1])) for r in rows]
    assert keys == sorted(keys)
