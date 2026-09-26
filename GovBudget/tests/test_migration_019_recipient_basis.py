"""R-DEC-DERIVE (fix-round-6 ruling, 2026-09-26): derive_ap_links is not run in
chain G, so the stored fpds-ap recipients stay the values an earlier run wrote,
before R-DEC-RECIPIENT; "their recipient_basis is recorded as 'pre_rule'
(allowed by the CHECK)".

Migration 019 (unapplied on the production database: schema_migrations stops
at 017, checked read-only 2026-09-26) therefore
  * allows 'pre_rule' beside the rule's three bases, and NULL;
  * backfills 'pre_rule' onto every existing row of a recipient-picking
    loader's methods (derive_ap_links: fpds-ap%; load_announcement_links:
    announcement+lexicon, subaward+lexicon) that carries no basis — the rows
    whose recipient predates the rule;
  * leaves NULL on the mechanical crosswalk's account* rows: R-DEC-RECIPIENT
    does not govern their recipient (jbooks/crosswalk.py picks its own), so
    'pre_rule' would claim a rule that never applies to them.

The migration's SQL is re-executed here inside a rolled-back transaction; the
fixture database applied it once, on empty tables (the pattern of
tests/test_migration_020_superseded_history.py).
"""
import re

import psycopg
import pytest

from govbudget.jbooks.db import MIGRATIONS_DIR

SQL = (MIGRATIONS_DIR / "019_budget_line_awards_superseded_route.sql").read_text()
ORG = "r-dec-derive-test"


@pytest.fixture()
def con(pg_dsn):
    with psycopg.connect(pg_dsn) as c:
        yield c
        c.rollback()


def _seed(con, piid, method, *, basis="omit"):
    cols = ["pe_bli", "exhibit", "fiscal_year", "organization", "award_piid",
            "recipient_name", "recipient_uei", "method", "confidence",
            "rationale"]
    vals = ["RD0601101E", "R-1", 2026, ORG, piid, "X INC", "UEIX", method,
            "low", f"{method} route"]
    if basis != "omit":
        cols.append("recipient_basis")
        vals.append(basis)
    con.execute(
        f"insert into budget_line_awards ({', '.join(cols)})"
        f" values ({', '.join(['%s'] * len(vals))})", vals)


def _bases(con):
    return dict(con.execute(
        "select award_piid, recipient_basis from budget_line_awards"
        " where organization = %s", (ORG,)).fetchall())


#: One row per method the tables hold today (production, read-only
#: 2026-09-26: account 114,637; account+subagency 9,336; account+tokens 527;
#: announcement+lexicon 1,075; fpds-ap 38,964; subaward+lexicon 114).
METHODS = {
    "P-FPDS": "fpds-ap",
    "P-ANN": "announcement+lexicon",
    "P-SUB": "subaward+lexicon",
    "P-ACCT": "account",
    "P-ACSA": "account+subagency",
    "P-ACTK": "account+tokens",
}
PRE_RULE_EXPECTED = {
    "P-FPDS": "pre_rule",
    "P-ANN": "pre_rule",
    "P-SUB": "pre_rule",
    "P-ACCT": None,
    "P-ACSA": None,
    "P-ACTK": None,
}


def test_019_backfills_pre_rule_onto_the_rows_it_adds_the_column_to(con):
    """The production path: 019 adds recipient_basis to a table whose rows
    were all written before R-DEC-RECIPIENT. Every recipient-picking loader's
    row is recorded 'pre_rule'; the crosswalk's account* rows stay NULL."""
    con.execute("alter table budget_line_awards"
                " drop constraint budget_line_awards_recipient_basis_known")
    con.execute("alter table budget_line_awards drop column recipient_basis")
    for piid, method in METHODS.items():
        _seed(con, piid, method)
    con.execute(SQL)
    assert _bases(con) == PRE_RULE_EXPECTED


def test_019_never_overwrites_a_basis_a_loader_recorded(con):
    """Re-executing 019 (idempotent) touches only rows with no basis: a rule
    pick a loader stored keeps its basis."""
    _seed(con, "K-OBL", "fpds-ap", basis="obligation")
    _seed(con, "K-ANN", "announcement+lexicon", basis="announcement_named")
    _seed(con, "K-TIE", "subaward+lexicon", basis="uei_tiebreak")
    _seed(con, "K-NULL", "fpds-ap", basis=None)
    _seed(con, "K-ACCT", "account", basis=None)
    con.execute(SQL)
    assert _bases(con) == {
        "K-OBL": "obligation",
        "K-ANN": "announcement_named",
        "K-TIE": "uei_tiebreak",
        "K-NULL": "pre_rule",
        "K-ACCT": None,
    }


def test_019_backfill_leaves_created_at_alone(con):
    """Migration 020 runs after 019 and matches each of the 60 historical
    moves by its row's created_at; the backfill must not touch it."""
    con.execute("alter table budget_line_awards"
                " drop constraint budget_line_awards_recipient_basis_known")
    con.execute("alter table budget_line_awards drop column recipient_basis")
    _seed(con, "T-FPDS", "fpds-ap")
    con.execute(
        "update budget_line_awards set created_at = timestamptz"
        " '2026-09-04 18:28:01.819115-04' where organization = %s", (ORG,))
    con.execute(SQL)
    assert con.execute(
        "select created_at = timestamptz '2026-09-04 18:28:01.819115-04',"
        " recipient_basis from budget_line_awards where organization = %s",
        (ORG,)).fetchone() == (True, "pre_rule")


@pytest.mark.parametrize("basis", [
    "obligation", "announcement_named", "uei_tiebreak", "pre_rule", None,
])
def test_the_check_allows_the_rule_bases_pre_rule_and_null(con, basis):
    _seed(con, "OK", "fpds-ap", basis=basis)
    assert _bases(con) == {"OK": basis}


@pytest.mark.parametrize("basis", [
    "alphabet", "", "PRE_RULE", "pre-rule", "prerule", "unknown",
])
def test_the_check_refuses_any_other_basis(con, basis):
    with pytest.raises(psycopg.errors.CheckViolation):
        with con.transaction():
            _seed(con, "BAD", "fpds-ap", basis=basis)


def test_the_checks_vocabulary_is_the_rule_bases_plus_pre_rule(con):
    """The migration's CHECK list and the loaders' constants cannot drift: the
    CHECK allows exactly RECIPIENT_BASES (what the rule writes) plus
    PRE_RULE_BASIS (what only 019's backfill writes), in the file and in the
    migrated database."""
    from derive_ap_links import PRE_RULE_BASIS, RECIPIENT_BASES

    assert PRE_RULE_BASIS == "pre_rule"
    assert PRE_RULE_BASIS not in RECIPIENT_BASES
    want = set(RECIPIENT_BASES) | {PRE_RULE_BASIS}

    m = re.search(r"recipient_basis in \(([^)]*)\)", SQL)
    assert m, "019 has no recipient_basis CHECK list"
    assert set(re.findall(r"'([^']*)'", m.group(1))) == want

    (defn,) = con.execute(
        "select pg_get_constraintdef(oid) from pg_constraint where conname ="
        " 'budget_line_awards_recipient_basis_known'").fetchone()
    assert set(re.findall(r"'([^']*)'::text", defn)) == want


def test_the_backfill_names_every_method_a_recipient_picking_loader_owns():
    """The backfill's method list is the two loaders' own: derive_ap_links
    deletes and rewrites `method like 'fpds-ap%'`, load_announcement_links
    its OWNED_METHODS. A loader that gains a method must gain it here too."""
    import load_announcement_links as lal

    m = re.search(r"update budget_line_awards\s+set recipient_basis = 'pre_rule'"
                  r"\s+where recipient_basis is null\s+and \((.*?)\);", SQL, re.S)
    assert m, "019 has no pre_rule backfill"
    c = re.search(r"add constraint budget_line_awards_pre_rule_is_a_loaders_row"
                  r"\s+check \(recipient_basis is distinct from 'pre_rule'"
                  r"\s+or (.*?)\);", SQL, re.S)
    assert c, "019 does not confine 'pre_rule' to the loaders' rows"
    for pred in (m.group(1), c.group(1)):
        assert "method like 'fpds-ap%'" in pred
        for method in lal.OWNED_METHODS:
            assert f"'{method}'" in pred


@pytest.mark.parametrize("method", ["fpds-ap", "announcement+lexicon", "subaward+lexicon"])
def test_pre_rule_is_admitted_on_a_recipient_picking_loaders_row(con, method):
    _seed(con, "PRE", method, basis="pre_rule")
    assert _bases(con) == {"PRE": "pre_rule"}


@pytest.mark.parametrize("method", ["account", "account+subagency", "account+tokens"])
def test_pre_rule_is_refused_on_a_mechanical_crosswalk_row(con, method):
    """'pre_rule' says a recipient-picking loader wrote the row before the
    rule; the crosswalk's account* rows were never under the rule."""
    with pytest.raises(psycopg.errors.CheckViolation,
                       match="budget_line_awards_pre_rule_is_a_loaders_row"):
        with con.transaction():
            _seed(con, "PRE", method, basis="pre_rule")
