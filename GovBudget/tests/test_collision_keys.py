"""One rule for "which axis tells a shared BLI code's members apart" (ROADMAP #83).

Before #83 the exporter (export_site._ProgramIdentity.is_account_split) and
the two link loaders (scripts/derive_ap_links.py and
scripts/load_announcement_links.py via collision_keys.partition_split_keys)
each carried their own copy of the rule. They agreed on all 13 keys the
warehouse ships and disagreed on two shapes it does not: three rows over two
accounts (the exporter said account-split, the loaders said unresolvable) and
a row with no account (same disagreement). This module pins (1) that all three
callers now import the SAME function object, (2) what that function says
about the live warehouse, and (3) what it says about the shapes the old rules
disagreed on.
"""
from __future__ import annotations

import duckdb
import pytest

from govbudget import config
from govbudget.export_site import _ProgramIdentity
from govbudget.jbooks.collision_keys import (
    SplitAxis,
    UnresolvedSharedKeyError,
    classify_shared_keys,
    partition_split_keys,
    require_resolved,
)

# The shipped PB2026 warehouse, measured read-only 2026-09-10 (dim_programs:
# 1,936 rows, 1,922 distinct pe_bli, 13 shared over 27 rows, every shared row
# with a non-null account and org). If a rebuild changes these sets, re-verify
# every member page and link target before editing them — a new shared key is
# a new page and a new link rule, not a test to silence.
LIVE_ACCOUNT_SPLIT = {"0145", "1350", "2101", "2210", "2292", "3010", "3050",
                      "3215", "3302", "4217"}
LIVE_ORG_SPLIT = {"20", "30", "500"}

# The loaders' own query (derive_ap_links.main / load_announcement_links.main)
# with the `org` column this task adds — the test feeds the predicate exactly
# what they feed it.
LOADER_SHARED_KEY_SQL = (
    "select pe_bli, account, org from dim_programs"
    " where pe_bli in (select pe_bli from dim_programs"
    "                  group by pe_bli having count(*) > 1)"
)


# ---------------------------------------------------------------------------
# (1) three callers, one function object
# ---------------------------------------------------------------------------


def test_both_loaders_and_the_exporter_import_the_one_predicate():
    import derive_ap_links  # scripts/ is on sys.path via tests/conftest.py
    import load_announcement_links
    from govbudget import export_site
    from govbudget.jbooks import collision_keys as ck

    assert derive_ap_links.partition_split_keys is ck.partition_split_keys
    assert load_announcement_links.partition_split_keys is ck.partition_split_keys
    assert export_site.require_resolved is ck.require_resolved


def test_the_scripts_copy_of_the_rule_is_gone():
    assert not (config.ROOT / "scripts" / "collision_keys.py").exists(), (
        "scripts/collision_keys.py was the second definition #83 removed;"
        " the rule lives in src/govbudget/jbooks/collision_keys.py only"
    )


# ---------------------------------------------------------------------------
# (2) the live warehouse
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def live_con():
    """Read-only handle on the shipped warehouse; skips (never fails) when it
    is absent or another session holds the write lock."""
    if not config.DUCKDB_PATH.exists():
        pytest.skip(f"{config.DUCKDB_PATH} absent; build the warehouse to run this")
    try:
        con = duckdb.connect(str(config.DUCKDB_PATH), read_only=True)
    except duckdb.Error as e:  # IOException when a writer holds the file
        pytest.skip(f"warehouse not readable ({e}); another session may be writing")
    yield con
    con.close()


@pytest.fixture(scope="module")
def live_identity_rows(live_con):
    """The exporter's row shape (see export_site._fetch_program_identity)
    restricted to the shared keys."""
    return [tuple(r) for r in live_con.execute(
        "select pe_bli, account, account_title, org,"
        " exhibit_family is not null"
        " from dim_programs"
        " where pe_bli in (select pe_bli from dim_programs"
        "                  group by pe_bli having count(*) > 1)"
        " order by pe_bli, account, org"
    ).fetchall()]


def test_live_shared_keys_are_the_thirteen_we_ship(live_con):
    rows = live_con.execute(LOADER_SHARED_KEY_SQL).fetchall()
    axes = classify_shared_keys(rows)
    assert {pe for pe, ax in axes.items() if ax is SplitAxis.ACCOUNT} == LIVE_ACCOUNT_SPLIT
    assert {pe for pe, ax in axes.items() if ax is SplitAxis.ORGANIZATION} == LIVE_ORG_SPLIT
    assert {pe for pe, ax in axes.items() if ax is SplitAxis.UNRESOLVED} == set()
    # the loaders' wrapper says the same thing about the same rows
    account_split, org_split, unresolved = partition_split_keys(rows)
    assert set(account_split) == LIVE_ACCOUNT_SPLIT
    assert org_split == LIVE_ORG_SPLIT
    assert unresolved == set()


def test_live_exporter_and_loaders_agree_key_by_key(live_con, live_identity_rows):
    """The exporter's wrapper and the loaders' wrapper, fed the same
    dim_programs rows, must say the same thing about every shared key."""
    ident = _ProgramIdentity(live_identity_rows)  # must not raise on the live corpus
    account_split, org_split, unresolved = partition_split_keys(
        live_con.execute(LOADER_SHARED_KEY_SQL).fetchall()
    )
    assert unresolved == set()
    assert ident.split_pe_blis == LIVE_ACCOUNT_SPLIT | LIVE_ORG_SPLIT
    for pe in ident.split_pe_blis:
        assert ident.is_account_split(pe) == (pe in account_split), pe
        assert ident.is_org_split(pe) == (pe in org_split), pe
    # the members a loader may pick between are exactly the exporter's rows
    for pe, members in account_split.items():
        assert members == {a for a, _t, _o, _hd in ident.accounts(pe)}, pe
    # every member page the exporter mints is composite — never the bare key
    slugs = {
        ident.slug(pe, account, account_title, org)
        for pe, account, account_title, org, _hd in live_identity_rows
    }
    assert len(slugs) == len(live_identity_rows) == 27
    assert all(s.split("-", 1)[0] in ident.split_pe_blis and "-" in s for s in slugs)


# ---------------------------------------------------------------------------
# (3) the shapes the two old rules disagreed on
# ---------------------------------------------------------------------------

# three rows over two accounts: account 'A' names TWO programs, and the
# organizations do not name one row either (org1 twice)
THREE_ROWS_TWO_ACCOUNTS = [("X", "A", "org1"), ("X", "A", "org2"), ("X", "B", "org1")]
# three rows over two accounts, but every organization is distinct
THREE_ROWS_ORG_RESOLVES = [("X", "A", "org1"), ("X", "A", "org2"), ("X", "B", "org3")]
# a member with no account at all, same organization on both rows
NULL_ACCOUNT = [("Y", None, "N"), ("Y", "1507N", "N")]
# both axes distinct — ACCOUNT wins (pages and links are account-addressed)
BOTH_AXES = [("Z", "A", "org1"), ("Z", "B", "org2")]


def _ident(triples):
    """_ProgramIdentity's 5-column row from a classify triple; account_title
    is synthesized from the account so slug() can derive a code
    ('Account A' -> 'AA' via export_site._account_slug)."""
    return _ProgramIdentity([
        (pe, account, f"Account {account}" if account else None, org, True)
        for pe, account, org in triples
    ])


def test_three_rows_over_two_accounts_is_unresolved_for_every_caller():
    assert classify_shared_keys(THREE_ROWS_TWO_ACCOUNTS) == {"X": SplitAxis.UNRESOLVED}
    # loaders: not a link target on either axis
    assert partition_split_keys(THREE_ROWS_TWO_ACCOUNTS) == ({}, set(), {"X"})
    # exporter: refuses to build an identity map at all
    with pytest.raises(UnresolvedSharedKeyError) as e:
        _ident(THREE_ROWS_TWO_ACCOUNTS)
    msg = str(e.value)
    assert "_ProgramIdentity" in msg and "'X'" in msg
    assert "account='A'" in msg and "organization='org2'" in msg


def test_three_rows_over_two_accounts_resolve_on_organization_when_it_is_a_key():
    assert classify_shared_keys(THREE_ROWS_ORG_RESOLVES) == {"X": SplitAxis.ORGANIZATION}
    assert partition_split_keys(THREE_ROWS_ORG_RESOLVES) == ({}, {"X"}, set())
    ident = _ident(THREE_ROWS_ORG_RESOLVES)
    assert ident.axis("X") is SplitAxis.ORGANIZATION
    assert ident.is_org_split("X") and not ident.is_account_split("X")
    assert ident.slug("X", "A", "Account A", "org2") == "X-org2"
    assert ident.split_key("X", "A", "org2") == ("X", None, "org2")
    assert ident.has_own_detail("X", "A", "org2") is True
    assert ident.has_own_detail("X", "A", "org9") is False


def test_a_null_account_never_resolves_the_account_axis():
    assert classify_shared_keys(NULL_ACCOUNT) == {"Y": SplitAxis.UNRESOLVED}
    assert partition_split_keys(NULL_ACCOUNT) == ({}, set(), {"Y"})
    with pytest.raises(UnresolvedSharedKeyError):
        _ident(NULL_ACCOUNT)


def test_account_wins_when_both_axes_would_resolve():
    assert classify_shared_keys(BOTH_AXES) == {"Z": SplitAxis.ACCOUNT}
    assert partition_split_keys(BOTH_AXES) == ({"Z": {"A", "B"}}, set(), set())
    ident = _ident(BOTH_AXES)
    assert ident.axis("Z") is SplitAxis.ACCOUNT
    assert ident.is_account_split("Z") and not ident.is_org_split("Z")
    # the slug carries the ACCOUNT code only — the address a #70 link resolves to
    assert ident.slug("Z", "A", "Account A", "org1") == "Z-AA"
    assert ident.split_key("Z", "A", "org1") == ("Z", "A", None)


def test_an_ordinary_key_has_no_axis_and_keeps_its_bare_identity():
    triple = [("0601101E", "0400", "DARPA")]
    assert classify_shared_keys(triple) == {}
    ident = _ident(triple)
    assert not ident.is_split("0601101E")
    assert ident.axis("0601101E") is None
    assert ident.slug("0601101E", "0400", "Account 0400", "DARPA") == "0601101E"
    assert ident.split_key("0601101E", "0400", "DARPA") == ("0601101E", None, None)
    assert ident.has_own_detail("0601101E", None) is True


def test_require_resolved_returns_the_axes_when_every_key_resolves():
    rows = BOTH_AXES + [("20", "0300D", "DCSA"), ("20", "0300D", "DTRA")]
    assert require_resolved(rows, caller="t") == {
        "Z": SplitAxis.ACCOUNT, "20": SplitAxis.ORGANIZATION,
    }
    assert require_resolved([], caller="t") == {}
