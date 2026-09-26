"""R-DEC-LDACITE (controller ruling 2026-09-26, under the owner's 2026-09-25
delegation): every lobbying aggregate citation lists its constituent filings.

The /company/ lobbying table cites three derived facts per (family, filing
year) row of fct_influence: lobbying_income_usd, lobbying_expense_usd and
lobbying_total_usd. The page tells the reader "Each figure opens to its
formula and constituent filings". Measured read-only 2026-09-26 on the
shipped data/site/citations/citations.parquet, all 630 of those citations
had inputs '[]'. The exporter looked for `family_key` / `filing_url` columns
in lda_filings.parquet, but the lake's columns are `family_key_guess` /
`url`, so the URL index was always empty. It also capped the list at 20 and
summed nothing the amendment rule knew about.

The fix reads the constituents from the warehouse's audit_lda_filings, the
relation fct_influence itself sums (R-DEC-AMEND: an amended quarter counts
once, from its amendment). It then checks each row against fct_influence:
same filing count, same income sum, same expense sum. A disagreement RAISES,
and so does a row with no constituent filing. No lobbying citation ships
with empty inputs, or with inputs that are not exactly the counted filings.

The fixtures run the COMMITTED dbt SQL (audit_lda_filings.sql and
fct_influence.sql) against a throwaway DuckDB. A rename on the dbt side
therefore fails here, not silently on the site.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from govbudget.export_site import (
    _build_derived_citation_rows,
    _influence_citation_rows,
    fact_id_derived,
)
from test_export_site_5b3 import _make_trajectory_duckdb

ROOT = Path(__file__).resolve().parents[1]
FORMULA, INPUTS, RECORDED = 20, 21, 23          # _null_derived_row layout
METRICS = ("lobbying_income_usd", "lobbying_expense_usd", "lobbying_total_usd")
FILING_COLS = (
    "filing_uuid", "url", "client_name", "registrant_name", "filing_year",
    "filing_period", "filing_type", "income_usd", "expenses_usd",
    "family_key_guess", "match_method",
)


def _dbt_sql(rel: str, **subs: str) -> str:
    sql = (ROOT / "dbt" / "models" / rel).read_text()
    for macro, name in subs.items():
        sql = sql.replace(macro, name)
    assert "{{" not in sql, f"unsubstituted macro left in {rel}"
    return sql


def _url(uuid: str) -> str:
    return f"https://lda.gov/filings/public/filing/{uuid}/print/"


def _filing(uuid, family, year, period, ftype, *, income="", expenses="",
            registrant="OUTSIDE FIRM", client="ACME INC",
            match="exact_family", url=True):
    return (uuid, _url(uuid) if url else None, client, registrant, year,
            period, ftype, income, expenses, family, match)


def _add_lda_models(con, filings) -> None:
    """lda_filings rows + the committed audit_lda_filings / fct_influence
    SQL as views (dbt materializes both as views)."""
    con.execute("drop table if exists fct_influence")
    con.execute("drop view if exists fct_influence")
    con.execute("create table if not exists dim_entities (family_key varchar,"
                " display_name varchar, total_obligation double)")
    defs = ", ".join(f"{c} varchar" for c in FILING_COLS)
    con.execute(f"create table lda_filings_src ({defs})")
    for f in filings:
        con.execute(f"insert into lda_filings_src values ({', '.join('?' * 11)})",
                    list(f))
    con.execute(
        "create view audit_lda_filings as "
        + _dbt_sql("audit/audit_lda_filings.sql",
                   **{"{{ source('influence', 'lda_filings') }}": "lda_filings_src"}))
    con.execute(
        "create view fct_influence as "
        + _dbt_sql("marts/fct_influence.sql",
                   **{"{{ ref('audit_lda_filings') }}": "audit_lda_filings",
                      "{{ ref('dim_entities') }}": "dim_entities"}))


def _lake(tmp_path, filings) -> Path:
    """The derived-citation fixture warehouse, with a real LDA layer."""
    Path(tmp_path).mkdir(parents=True, exist_ok=True)
    db = _make_trajectory_duckdb(tmp_path)
    con = duckdb.connect(str(db))
    try:
        _add_lda_models(con, filings)
    finally:
        con.close()
    return db


def _influence_rows(db) -> dict[str, tuple]:
    derived = _build_derived_citation_rows(duckdb_path=db, bl_rows=[],
                                           citation_rows=[])
    fids = {}
    con = duckdb.connect(str(db), read_only=True)
    try:
        keys = con.execute(
            "select family_key, filing_year from fct_influence").fetchall()
    finally:
        con.close()
    for fk, fy in keys:
        for m in METRICS:
            fids[fact_id_derived("influence", f"{fk}|{fy}", m)] = (fk, str(fy), m)
    return {fids[r[0]]: r for r in derived if r[0] in fids}


Q1, Q2, Q3 = "first_quarter", "second_quarter", "third_quarter"

#: ACME 2024: a Q1 report superseded by its amendment, an unamended Q2 report,
#: a registration, and a filing whose client never matched the family.
#: BETA 2025: an in-house filer (expenses) with an amendment of an amendment.
FILINGS = [
    _filing("a-q1-orig", "ACME", "2024", Q1, "Q1", income="150000"),
    _filing("a-q1-amend", "ACME", "2024", Q1, "1A", income="120000"),
    _filing("a-q2", "ACME", "2024", Q2, "Q2", income="90000"),
    _filing("a-rr", "ACME", "2024", Q1, "RR"),
    _filing("a-unmatched", "ACME", "2024", Q3, "Q3", income="70000",
            client="ACME HOLDINGS UNRELATED", match="none"),
    _filing("b-q1", "BETA", "2025", Q1, "Q1", expenses="3350000",
            registrant="BETA CORP", client="BETA CORP"),
    _filing("b-q1-a1", "BETA", "2025", Q1, "1A", expenses="3410000",
            registrant="BETA CORP", client="BETA CORP"),
    _filing("b-q1-a2", "BETA", "2025", Q1, "1A", expenses="3410000",
            registrant="BETA CORP", client="BETA CORP"),
    _filing("b-q2", "BETA", "2025", Q2, "Q2", expenses="3000000",
            registrant="BETA CORP", client="BETA CORP"),
]


def test_every_lobbying_citation_lists_exactly_the_filings_the_amendment_rule_counts(tmp_path):
    rows = _influence_rows(_lake(tmp_path, FILINGS))
    assert len(rows) == 6                       # 2 family-years x 3 metrics

    counted = {
        ("ACME", "2024"): ["a-q1-amend", "a-rr", "a-q2"],
        ("BETA", "2025"): ["b-q1-a1", "b-q2"],
    }
    for (fk, fy, metric), row in rows.items():
        inputs = json.loads(row[INPUTS])
        assert sorted(inputs) == sorted(_url(u) for u in counted[(fk, fy)]), (
            fk, fy, metric, inputs)
        # the superseded report, the superseded amendment and the unmatched
        # client's filing are NOT constituents
        for gone in ("a-q1-orig", "a-unmatched", "b-q1", "b-q1-a2"):
            assert _url(gone) not in inputs

    acme = rows[("ACME", "2024", "lobbying_income_usd")]
    assert float(acme[RECORDED]) == 120000 + 90000    # never 150000 + 120000
    beta = rows[("BETA", "2025", "lobbying_expense_usd")]
    assert float(beta[RECORDED]) == 3410000 + 3000000


def test_the_inputs_are_in_quarter_order_and_deterministic(tmp_path):
    rows = _influence_rows(_lake(tmp_path, FILINGS))
    beta = json.loads(rows[("BETA", "2025", "lobbying_total_usd")][INPUTS])
    assert beta == [_url("b-q1-a1"), _url("b-q2")]
    again = _influence_rows(_lake(tmp_path / "again", FILINGS))
    assert {k: r[INPUTS] for k, r in rows.items()} == {
        k: r[INPUTS] for k, r in again.items()}


def test_no_lobbying_citation_ships_with_empty_inputs(tmp_path):
    rows = _influence_rows(_lake(tmp_path, FILINGS))
    assert rows
    for key, row in rows.items():
        assert json.loads(row[INPUTS]), f"{key}: lobbying citation with empty inputs"


def test_the_list_is_not_capped(tmp_path):
    """The old exporter kept filing_urls[:20]: a 21st filing vanished from a
    figure it was summed into."""
    many = [
        _filing(f"g-{i:02d}", "GAMMA", "2025", Q1, "Q1", income="1000",
                registrant=f"FIRM {i:02d}")
        for i in range(25)
    ]
    rows = _influence_rows(_lake(tmp_path, many))
    for m in METRICS:
        assert len(json.loads(rows[("GAMMA", "2025", m)][INPUTS])) == 25


def test_the_formula_names_the_amendment_rule_and_the_count(tmp_path):
    rows = _influence_rows(_lake(tmp_path, FILINGS))
    income = rows[("ACME", "2024", "lobbying_income_usd")][FORMULA]
    expense = rows[("BETA", "2025", "lobbying_expense_usd")][FORMULA]
    total = rows[("ACME", "2024", "lobbying_total_usd")][FORMULA]
    assert income.startswith("sum(income_usd) over the 3 LDA filings counted")
    assert expense.startswith("sum(expenses_usd) over the 2 LDA filings counted")
    assert total.startswith("lobbying_income_usd + lobbying_expense_usd over the same 3")
    for text in (income, expense):
        assert "counted once, from its amendment" in text
        assert "registrant-year" not in text      # the grain is the family-year
        # every amendment of these quarters agrees: no smallest-figure clause
        assert "smallest" not in text


def test_a_quarter_whose_amendments_disagree_says_the_smallest_is_counted(tmp_path):
    """R-DEC-AMEND-b: the lake carries no posting date, so where a quarter's
    amendments report different figures the smallest is counted; the formula
    of that family-year says so (and only that one)."""
    filings = FILINGS + [
        _filing("d-q1", "DELTA", "2025", Q1, "Q1", expenses="2710000",
                registrant="DELTA", client="DELTA"),
        _filing("d-a-big", "DELTA", "2025", Q1, "1A", expenses="2830000",
                registrant="DELTA", client="DELTA"),
        _filing("d-a-small", "DELTA", "2025", Q1, "1A", expenses="1600000",
                registrant="DELTA", client="DELTA"),
    ]
    rows = _influence_rows(_lake(tmp_path, filings))
    delta = rows[("DELTA", "2025", "lobbying_expense_usd")]
    assert json.loads(delta[INPUTS]) == [_url("d-a-small")]
    assert float(delta[RECORDED]) == 1600000
    assert "where its amendments disagree, from the smallest" in delta[FORMULA]
    assert "smallest" not in rows[("BETA", "2025", "lobbying_expense_usd")][FORMULA]


def test_a_filing_with_no_url_cites_its_lda_api_record(tmp_path):
    filings = [_filing("e-q1", "EPSILON", "2024", Q1, "Q1", income="5000",
                       url=False)]
    rows = _influence_rows(_lake(tmp_path, filings))
    assert json.loads(rows[("EPSILON", "2024", "lobbying_income_usd")][INPUTS]) == [
        "https://lda.senate.gov/api/v1/filings/e-q1/"]


# ---------------------------------------------------------------------------
# The guards: a figure whose constituents cannot be named does not ship.
# ---------------------------------------------------------------------------

def _influence_table(con, rows) -> None:
    """A STATIC fct_influence (a stale or hand-built mart) beside the real
    audit view — what the exporter must refuse to cite."""
    con.execute("drop view if exists fct_influence")
    con.execute(
        "create table fct_influence (family_key varchar, display_name varchar,"
        " filing_year varchar, filings_count bigint, lobbying_income_usd double,"
        " lobbying_expense_usd double, lobbying_total_usd double,"
        " family_obligations_usd double)")
    for r in rows:
        con.execute("insert into fct_influence values (?,?,?,?,?,?,?,?)", list(r))


def test_a_row_with_no_constituent_filing_refuses(tmp_path):
    con = duckdb.connect()
    _add_lda_models(con, FILINGS)
    _influence_table(con, [
        ("ACME", None, "2024", 3, 210000.0, 0.0, 210000.0, None),
        ("ZETA", None, "2024", 2, 5000.0, 0.0, 5000.0, None),   # no filings
    ])
    with pytest.raises(ValueError, match="ZETA.*no counted filing"):
        _influence_citation_rows(con, built_at="t")


def test_a_count_or_sum_that_disagrees_with_fct_influence_refuses(tmp_path):
    """A fct_influence built before R-DEC-AMEND summed every filing: its
    ACME 2024 income is 150,000 + 120,000 + 90,000. Citing the counted
    filings beside that figure would publish inputs that do not add up."""
    for bad in [
        ("ACME", None, "2024", 4, 360000.0, 0.0, 360000.0, None),   # both off
        ("ACME", None, "2024", 3, 360000.0, 0.0, 360000.0, None),   # sum off
        ("ACME", None, "2024", 4, 210000.0, 0.0, 210000.0, None),   # count off
        ("ACME", None, "2024", 3, 210000.0, 5.0, 210005.0, None),   # expense off
    ]:
        con = duckdb.connect()
        _add_lda_models(con, FILINGS)
        _influence_table(con, [bad])
        with pytest.raises(ValueError, match="ACME\\|2024"):
            _influence_citation_rows(con, built_at="t")
        con.close()


def test_a_warehouse_without_the_audit_model_refuses(tmp_path):
    """fct_influence has rows but audit_lda_filings is absent: the warehouse
    predates R-DEC-AMEND. Rebuild it; never cite lobbying figures blind."""
    con = duckdb.connect()
    _influence_table(con, [("ACME", None, "2024", 1, 5.0, 0.0, 5.0, None)])
    with pytest.raises(ValueError, match="audit_lda_filings.*govbudget build"):
        _influence_citation_rows(con, built_at="t")


def test_an_empty_fct_influence_needs_no_audit_model(tmp_path):
    con = duckdb.connect()
    _influence_table(con, [])
    assert _influence_citation_rows(con, built_at="t") == []
