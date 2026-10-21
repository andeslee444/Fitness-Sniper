"""Test helper: dbt/models/marts/link_award_keys.sql against a throwaway DuckDB.

link_award_keys is the one point where a published crosswalk link resolves to
the AWARD it names (R-DEC-LINK-2026-10-21 R4). Every model and export read
that joins a link to fct_award_transactions joins through it, so a fixture
that runs one of them builds it first — from the committed model SQL, never a
restatement, the reasoning of test_dbt_build._model_sql.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def link_award_keys_sql(links: str = "fct_budget_to_awards",
                        transactions: str = "fct_award_transactions") -> str:
    sql = (ROOT / "dbt" / "models" / "marts" / "link_award_keys.sql").read_text()
    for model, table in (("fct_budget_to_awards", links),
                         ("fct_award_transactions", transactions)):
        sql = sql.replace("{{ ref('%s') }}" % model, table)
    assert "{{" not in sql, "unsubstituted macro left in link_award_keys.sql"
    return sql


def materialize_link_award_keys(con, links: str = "fct_budget_to_awards",
                                transactions: str = "fct_award_transactions",
                                name: str = "link_award_keys") -> str:
    """Create `name` from the committed model over the fixture's own link and
    transaction tables; returns the name for _model_sql. A VIEW, not dbt's
    table: a fixture that adds links or transactions after building it reads
    them, as a rebuilt warehouse would."""
    con.execute(f"create or replace view {name} as "
                + link_award_keys_sql(links, transactions))
    return name
