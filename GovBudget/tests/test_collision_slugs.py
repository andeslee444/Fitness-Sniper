"""Account-qualified link targets for shared BLI codes (ROADMAP #70, Task 7).

Ten pe_bli values in the PB2026 corpus are shared by TWO real programs that
differ only by appropriation ACCOUNT — '3010' is LPD Flight II in
Shipbuilding & Conversion, Navy (1611N) AND Shipboard Tactical Communications
in Other Procurement, Navy (1810N). Sprint E Task E3 already gives each member
its own page (`3010-SCN` / `3010-OPN`) and turns the bare `/program/3010/`
into a disambiguation stub, but BOTH link scripts excluded every shared key
outright (`display -= collisions`), so neither member page ever showed an
award.

This module pins the two halves of the fix:

  (a) the derivation emits DISTINCT link rows, each carrying the `account` of
      the one member the award's funding accounts identify — 097-1611 money
      lands on 1611N, 097-1810 money on 1810N, and money that names both (or
      neither) links nothing;
  (b) the exporter files those rows onto the two members' own
      `program_details/{slug}.json` sidecars and NEVER onto the bare-key stub.

Organization-split keys ('20', '30', '500' — same account 0300D, different
organization) stay excluded: account evidence cannot tell their members apart,
so there is nothing to resolve. Which axis a shared key splits on is decided
once, in govbudget.jbooks.collision_keys (ROADMAP #83) — the exporter and both
loaders import that one rule; tests/test_collision_keys.py pins their agreement.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import duckdb
import psycopg
import pytest

ADMIN_DSN = os.environ.get("GOVBUDGET_TEST_PG_DSN", "postgresql://localhost/postgres")
TEST_DB = "govbudget_test_collision"

# The real PB2026 shape this module models (see docs and dim_programs.sql).
SCN, OPN = "1611N", "1810N"
SCN_TITLE = "Shipbuilding and Conversion, Navy"
OPN_TITLE = "Other Procurement, Navy"
SCN_FED, OPN_FED = "017-1611", "017-1810"


# ---------------------------------------------------------------------------
# (0) Pure key partitioning — which shared keys can be resolved at all
# ---------------------------------------------------------------------------


def test_account_split_keys_are_separated_from_org_split_keys():
    from govbudget.jbooks.collision_keys import partition_split_keys

    rows = [
        ("0601101E", "0400", "DARPA"),                  # ordinary key — one row, never split
        ("3010", SCN, "N"), ("3010", OPN, "N"),         # account-split (ROADMAP #67)
        ("20", "0300D", "DCSA"), ("20", "0300D", "DTRA"),  # org-split (ROADMAP #45)
    ]
    account_split, org_split, unresolved = partition_split_keys(rows)
    assert account_split == {"3010": {SCN, OPN}}
    assert org_split == {"20"}
    assert unresolved == set()
    assert "0601101E" not in account_split and "0601101E" not in org_split


def test_a_key_whose_account_does_not_identify_one_row_is_not_account_split():
    """Three rows over two accounts: the account names a member ambiguously,
    so the key is NOT account-resolvable and gets no award links. With three
    distinct organizations it resolves on that axis instead (a page each);
    tests/test_collision_keys.py pins the shape NEITHER axis resolves."""
    from govbudget.jbooks.collision_keys import partition_split_keys

    account_split, org_split, unresolved = partition_split_keys(
        [("30", "0300D", "OSD"), ("30", "0300D", "DTRA"), ("30", "0301D", "DMACT")]
    )
    assert account_split == {}
    assert org_split == {"30"}
    assert unresolved == set()


def test_member_for_award_needs_exactly_one_hit():
    from govbudget.jbooks.collision_keys import member_for_award

    members = {SCN: {SCN_FED}, OPN: {OPN_FED}}
    assert member_for_award(members, {SCN_FED}) == SCN
    assert member_for_award(members, {OPN_FED, "097-3400"}) == OPN
    # named by BOTH members' money → not attributable
    assert member_for_award(members, {SCN_FED, OPN_FED}) is None
    # named by neither → not attributable
    assert member_for_award(members, {"097-3400"}) is None
    assert member_for_award(members, set()) is None


def test_member_for_document_needs_exactly_one_hit():
    from govbudget.jbooks.collision_keys import member_for_document

    members = {SCN, OPN}
    assert member_for_document({SCN}, members) == SCN
    assert member_for_document({SCN, OPN}, members) is None
    assert member_for_document(set(), members) is None
    assert member_for_document({"1507N"}, members) is None


# ---------------------------------------------------------------------------
# (0b) Task 27 fix round 1 (R-27-2', 2026-09-19) — a district row's ADDRESS
#      and its FACT-ID KEY ask the same question
# ---------------------------------------------------------------------------


def _district_identity():
    """A _ProgramIdentity over the four real shared codes that reach a
    district today, plus an ordinary code and one organization-split code.

    Accounts and titles are the live dim_programs values (read-only
    2026-09-19): 0145 = 1506N 'Aircraft Procurement, Navy' / 1508N
    'Procurement of Ammunition, Navy and Marine Corps'; 2292 = 1109N
    'Procurement, Marine Corps' / 1507N 'Weapons Procurement, Navy';
    3010 = 1611N / 1810N; 3215 = 1507N / 1810N; '20' is DCSA and DTRA under
    the ONE account 0300D.
    """
    from govbudget.export_site import _ProgramIdentity

    return _ProgramIdentity([
        ("0601101E", "0400", "RDT&E, Defense-Wide", "DARPA", True),
        ("0145", "1506N", "Aircraft Procurement, Navy", "N", True),
        ("0145", "1508N",
         "Procurement of Ammunition, Navy and Marine Corps", "N", True),
        ("2292", "1109N", "Procurement, Marine Corps", "N", True),
        ("2292", "1507N", "Weapons Procurement, Navy", "N", True),
        ("3010", SCN, SCN_TITLE, "N", True),
        ("3010", OPN, OPN_TITLE, "N", True),
        ("3215", "1507N", "Weapons Procurement, Navy", "N", True),
        ("3215", OPN, OPN_TITLE, "N", True),
        ("20", "0300D", "Procurement, Defense-Wide", "DCSA", True),
        ("20", "0300D", "Procurement, Defense-Wide", "DTRA", True),
    ])


def test_an_ordinary_code_carrying_an_account_keeps_its_pre_task_27_fact_id():
    """R-27-2' — the permalink promise rests on the collision set, not on a
    data property.

    Task 27 round 0 keyed the fact id on `account is not None` while the
    address (_member_split_key) asked `account is not None AND
    ident.is_account_split(pe_bli)`. The two agreed only because no ordinary
    code carries an account on today's corpus (measured read-only
    2026-09-19: all 11 account-bearing district rows sit on account-split
    codes). The day one did, the row would have kept its address and its
    rendered code while its /fact/{id} permalink silently rotated — the
    shape below, which now cannot happen because one predicate answers both.
    """
    from govbudget.export_site import _district_program_key, _member_split_key

    ident = _district_identity()

    # An ORDINARY code carrying a non-NULL account: no member to name, so
    # the address is the bare key AND the id is the pre-Task-27 triple.
    assert _member_split_key(ident, "0601101E", "0400") == "0601101E"
    assert _district_program_key(
        ident, "VA", "VA-08", "0601101E", "0400") == "VA|VA-08|0601101E"
    assert _district_program_key(
        ident, "VA", "VA-08", "0601101E", None) == "VA|VA-08|0601101E"

    # An ORGANIZATION-split code: both members carry 0300D, which names
    # neither, so it keeps the stub AND the bare triple.
    assert _member_split_key(ident, "20", "0300D") == "20"
    assert _district_program_key(
        ident, "VA", "VA-08", "20", "0300D") == "VA|VA-08|20"

    # An account-NULL row on an ACCOUNT-split code names BOTH members — the
    # stub, and the bare triple.
    assert _member_split_key(ident, "3010", None) == "3010"
    assert _district_program_key(
        ident, "VA", "VA-08", "3010", None) == "VA|VA-08|3010"

    # And the one case that DOES name a member: address and id both move.
    assert _member_split_key(ident, "3010", SCN) == "3010-SCN"
    assert _district_program_key(
        ident, "VA", "VA-08", "3010", SCN) == f"VA|VA-08|3010|{SCN}"


# The 11 account-bearing rows of fct_district_programs at the member grain,
# measured read-only against data/duckdb/govbudget.duckdb on 2026-09-19
# (0145 x2, 2292, 3010, 3215 x7). These are the rows whose /fact/{id}
# permalinks rotate once, and the only ones.
_ROTATING_DISTRICT_ROWS = [
    ("MA", "MA-06", "0145", "1506N"),
    ("MO", "MO-01", "0145", "1506N"),
    ("AZ", "AZ-07", "2292", "1507N"),
    ("MS", "MS-04", "3010", "1611N"),
    ("MA", "MA-08", "3215", "1507N"),
    ("MD", "MD-03", "3215", "1507N"),
    ("MO", "MO-01", "3215", "1507N"),
    ("PA", "PA-14", "3215", "1507N"),
    ("RI", "RI-01", "3215", "1507N"),
    ("VA", "VA-10", "3215", "1507N"),
    ("WA", "WA-06", "3215", "1507N"),
]


def test_the_eleven_shared_code_rows_still_rotate_under_the_shared_predicate():
    """R-27-2' changes no id on this corpus — it changes what the promise
    rests on. These 11 rows still gain their account, each id still distinct
    from the pre-Task-27 triple it replaces, and the set is still 11 rows.
    """
    from govbudget.export_site import _district_program_key

    ident = _district_identity()
    assert len(_ROTATING_DISTRICT_ROWS) == 11

    new_keys = []
    for state, district, pe_bli, account in _ROTATING_DISTRICT_ROWS:
        old = f"{state}|{district}|{pe_bli}"
        new = _district_program_key(ident, state, district, pe_bli, account)
        assert new == f"{old}|{account}", (state, district, pe_bli, account)
        assert new != old
        new_keys.append(new)
    # MO-01 holds two of them (0145 and 3215) and MA two rows on different
    # codes — 11 distinct keys, no collisions.
    assert len(set(new_keys)) == 11


# ---------------------------------------------------------------------------
# (a) derive_ap_links emits distinct, account-keyed rows for 3010's members
# ---------------------------------------------------------------------------

_ACCOUNT_IDX = 12  # out_row[12] is the new `account` column


def _line_meta():
    return {
        ("3010", SCN): {"fed_accounts": {SCN_FED}, "org": "N", "exhibit": "P-1"},
        ("3010", OPN): {"fed_accounts": {OPN_FED}, "org": "N", "exhibit": "P-1"},
        ("0601101E", None): {
            "fed_accounts": {"097-0400"}, "org": "DARPA", "exhibit": "R-1",
        },
    }


def _award_rows(award_accounts, candidates):
    from derive_ap_links import link_rows_for_award

    return link_rows_for_award(
        ap_code="542",
        piid="N0002420C0001",
        recipient_name="Huntington Ingalls",
        recipient_uei="UEI1",
        award_accounts=award_accounts,
        obligation=1_000_000.0,
        candidates=candidates,
        line_meta=_line_meta(),
        account_split={"3010": {SCN, OPN}},
    )


def test_scn_money_links_only_the_scn_member():
    rows = _award_rows({SCN_FED}, [{"pe_bli": "3010", "match_kind": "title-variant"}])
    assert len(rows) == 1
    assert rows[0][0] == "3010"
    assert rows[0][_ACCOUNT_IDX] == SCN
    assert rows[0][9] == "medium"          # confidence
    assert rows[0][8] == "fpds-ap"         # method


def test_opn_money_links_only_the_opn_member():
    rows = _award_rows({OPN_FED}, [{"pe_bli": "3010", "match_kind": "title-variant"}])
    assert len(rows) == 1
    assert rows[0][_ACCOUNT_IDX] == OPN


def test_the_two_members_get_distinct_rows_from_distinct_awards():
    """The whole point: two awards, two accounts, two DIFFERENT link rows."""
    scn = _award_rows({SCN_FED}, [{"pe_bli": "3010", "match_kind": "title-variant"}])
    opn = _award_rows({OPN_FED}, [{"pe_bli": "3010", "match_kind": "title-variant"}])
    assert {r[_ACCOUNT_IDX] for r in scn + opn} == {SCN, OPN}


def test_money_naming_both_members_links_nothing():
    rows = _award_rows(
        {SCN_FED, OPN_FED}, [{"pe_bli": "3010", "match_kind": "title-variant"}]
    )
    assert rows == []


def test_money_naming_neither_member_links_nothing():
    rows = _award_rows(
        {"097-3400"}, [{"pe_bli": "3010", "match_kind": "title-variant"}]
    )
    assert rows == []


def test_ordinary_keys_are_untouched_and_carry_a_null_account():
    rows = _award_rows(
        {"097-0400"}, [{"pe_bli": "0601101E", "match_kind": "title-exact"}]
    )
    assert len(rows) == 1
    assert rows[0][0] == "0601101E"
    assert rows[0][_ACCOUNT_IDX] is None
    assert rows[0][9] == "medium"


def test_an_unresolvable_collision_line_never_starves_its_co_candidates():
    """An award whose accounts name both 3010 members still links the
    ordinary line mapped to the same AP code."""
    rows = _award_rows(
        {SCN_FED, OPN_FED, "097-0400"},
        [
            {"pe_bli": "3010", "match_kind": "title-variant"},
            {"pe_bli": "0601101E", "match_kind": "title-exact"},
        ],
    )
    assert [r[0] for r in rows] == ["0601101E"]
    assert rows[0][_ACCOUNT_IDX] is None


# ---------------------------------------------------------------------------
# (a2) the announcement loader resolves a shared key from its lexicon document
# ---------------------------------------------------------------------------


def test_announcement_collision_account_comes_from_the_lexicon_document():
    from load_announcement_links import collision_account_for

    # doc 341 is SCN_Book.pdf; its 3010 detail rows are stamped 1611N.
    doc_accounts = {("3010", "341"): {SCN}, ("3010", "333"): {OPN}}
    members = {SCN, OPN}
    assert collision_account_for(
        "3010", {"lexicon_doc": "341"}, doc_accounts, members) == SCN
    assert collision_account_for(
        "3010", {"lexicon_doc": "333"}, doc_accounts, members) == OPN


def test_announcement_collision_without_a_usable_document_is_not_resolved():
    from load_announcement_links import collision_account_for

    doc_accounts = {("3010", "341"): {SCN}}
    members = {SCN, OPN}
    assert collision_account_for("3010", {}, doc_accounts, members) is None
    assert collision_account_for(
        "3010", {"lexicon_doc": "None"}, doc_accounts, members) is None
    # a book that carries BOTH members' lines names neither
    assert collision_account_for(
        "3010", {"lexicon_doc": "999"}, {("3010", "999"): {SCN, OPN}}, members
    ) is None


# ---------------------------------------------------------------------------
# (a3) contradictory member evidence is a finding, not a tie-break
#
# The unique key on budget_line_awards is (pe_bli, exhibit, fiscal_year,
# award_piid) — `account` is deliberately NOT part of it, so exactly-one-member
# admission keeps one award naming at most one member. The cost of that choice
# is that an `on conflict … do update set account=excluded.account` lets the
# LAST loader to run move a published link from one member's page to the
# other's, silently. Two independent evidence routes disagreeing about which
# program an award belongs to is a finding about the evidence; the loaders must
# stop rather than let run order decide.
# ---------------------------------------------------------------------------


_K1 = ("3010", "P-1", 2026, "N0002420C0001")
_K2 = ("3010", "P-1", 2026, "N0003917D0006")


def test_a_stored_link_on_the_other_member_is_a_contradiction():
    from govbudget.jbooks.collision_keys import contradictory_accounts

    conflicts = contradictory_accounts({_K1: SCN}, [(_K1, OPN)])
    assert conflicts == [(_K1, SCN, OPN)]


def test_agreeing_or_unclaimed_stored_accounts_are_not_contradictions():
    from govbudget.jbooks.collision_keys import contradictory_accounts

    # same member, twice — the normal re-run
    assert contradictory_accounts({_K1: SCN}, [(_K1, SCN)]) == []
    # no stored row at all (this loader owns the key)
    assert contradictory_accounts({}, [(_K1, SCN)]) == []
    # a stored row that claims no member (an ordinary, unshared key)
    assert contradictory_accounts({_K1: None}, [(_K1, None)]) == []
    # a different award on the same code — different key, no contradiction
    assert contradictory_accounts({_K1: SCN}, [(_K2, OPN)]) == []


def test_dropping_a_member_claim_is_also_a_contradiction():
    """A published link that names 1611N must not become member-less: the
    upsert would write account=NULL and the link would vanish from BOTH
    member pages with nothing said."""
    from govbudget.jbooks.collision_keys import contradictory_accounts

    assert contradictory_accounts({_K1: SCN}, [(_K1, None)]) == [(_K1, SCN, None)]


def test_one_batch_contradicting_itself_is_caught_too():
    """Run order between loaders is not the only tie-break available — two
    rows in ONE executemany would resolve by insertion order."""
    from govbudget.jbooks.collision_keys import contradictory_accounts

    assert contradictory_accounts({}, [(_K1, SCN), (_K1, OPN)]) == [(_K1, SCN, OPN)]


def test_raise_on_contradictory_accounts_names_both_members():
    from govbudget.jbooks.collision_keys import (
        ContradictoryAccountError,
        raise_on_contradictory_accounts,
    )

    raise_on_contradictory_accounts({_K1: SCN}, [(_K1, SCN)], loader="fpds-ap")
    with pytest.raises(ContradictoryAccountError) as e:
        raise_on_contradictory_accounts({_K1: SCN}, [(_K1, OPN)], loader="fpds-ap")
    msg = str(e.value)
    assert SCN in msg and OPN in msg and "N0002420C0001" in msg
    assert "fpds-ap" in msg


# ---------------------------------------------------------------------------
# (a4) a consumer keyed on the BARE shared code names BOTH members
#
# prog_titles (export_site) is keyed on the bare pe_bli and feeds the feed
# headline, the filing mention and the district card. For a shared code it was
# last-wins over dim_programs ordered by (pe_bli, account) — the label was
# whichever member the sort happened to end on. Every one of those consumers
# links to /program/{pe_bli}/, which for a shared code is the disambiguation
# STUB listing both members, so the honest label for that link names both.
# ---------------------------------------------------------------------------


def test_a_shared_code_label_names_every_member():
    from govbudget.export_site import shared_code_program_label

    assert shared_code_program_label(
        ["LPD Flight II", "Shipboard Tactical Communications"]
    ) == "LPD Flight II / Shipboard Tactical Communications"


def test_two_members_with_one_title_are_labelled_once():
    """2101 and 2292 publish two rows with the SAME title (Tomahawk in two
    appropriations) — 'Tomahawk / Tomahawk' would be a worse label, not a
    more honest one."""
    from govbudget.export_site import shared_code_program_label

    assert shared_code_program_label(["Tomahawk", "Tomahawk"]) == "Tomahawk"


def test_an_ordinary_key_keeps_its_own_title_object():
    from govbudget.export_site import shared_code_program_label

    assert shared_code_program_label(["Defense Research Sciences"]) == (
        "Defense Research Sciences"
    )
    # nothing to say → say nothing (the caller falls back to bl_titles)
    assert shared_code_program_label([None]) is None
    assert shared_code_program_label([None, ""]) is None
    # a member with no title of its own does not blank out its sibling
    assert shared_code_program_label([None, "Vehicles"]) == "Vehicles"


# ---------------------------------------------------------------------------
# (b) the exporter files the rows on the members' pages, not the stub
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def collision_pg_dsn():
    """A throwaway migrated database of this module's own, so seeding two
    3010 budget lines cannot leak into any other suite's fixtures."""
    try:
        admin = psycopg.connect(ADMIN_DSN, autocommit=True)
    except psycopg.OperationalError as e:
        pytest.skip(f"Postgres unavailable ({e}); start local postgres to run this suite")
    admin.execute(f"drop database if exists {TEST_DB}")
    admin.execute(f"create database {TEST_DB}")
    admin.close()

    parts = urlsplit(ADMIN_DSN)
    dsn = urlunsplit(parts._replace(path="/" + TEST_DB))

    from govbudget.jbooks.db import migrate

    migrate(dsn)
    yield dsn

    admin = psycopg.connect(ADMIN_DSN, autocommit=True)
    admin.execute(f"drop database if exists {TEST_DB}")
    admin.close()


def _seed_split_key_budget_lines(dsn: str) -> None:
    """One P-1 workbook row per 3010 member, in its own appropriation."""
    with psycopg.connect(dsn, autocommit=True) as con:
        doc_id = con.execute(
            "insert into jbook_documents (org, exhibit_family, fiscal_year,"
            " title, source_url, status) values ('N','procurement',2026,"
            " 'SCN_Book.pdf','https://example.test/scn.pdf','downloaded')"
            " returning id"
        ).fetchone()[0]
        for account, account_title, title in (
            (SCN, SCN_TITLE, "LPD Flight II"),
            (OPN, OPN_TITLE, "Shipboard Tactical Communications"),
        ):
            con.execute(
                "insert into budget_lines (exhibit, fiscal_year, account,"
                " account_title, organization, budget_activity,"
                " budget_activity_title, pe_bli, title, amount_type,"
                " amount_thousands, source_document_id, source_sheet,"
                " source_cells) values ('P-1',2026,%s,%s,'N','01','Ships',"
                " '3010',%s,'fy_2026_total',100000,%s,'Exhibit P-1',"
                " ARRAY['B7'])",
                (account, account_title, title, doc_id),
            )


#: J-book volumes seeded by `_seed_split_key_jbooks`, in the shape ROADMAP #82
#: (narrative axis) has to tell apart. Each of the first two is one member's
#: own book; the third files a narrative under the same code and NO accounted
#: detail row, so nothing says which member it is about.
_VOLUMES = (
    # (title, sha256, account, narrative title, narrative body)
    ("SCN_Book.pdf", "a" * 64, SCN, "LPD Flight II — Mission",
     "The LPD Flight II amphibious transport dock supports the Marine Corps."),
    ("OPN_BA1_Book.pdf", "b" * 64, OPN, "Shipboard Tactical Comms — Mission",
     "Shipboard Tactical Communications fields radio room upgrades."),
    ("ORPHAN_Book.pdf", "c" * 64, None, "Orphan Volume — Mission",
     "A volume whose rows say nothing about which program this line is."),
)


def _seed_split_key_jbooks(dsn: str) -> None:
    """One J-book volume per 3010 member, plus one that belongs to neither
    (ROADMAP #82, narrative axis).

    The two member volumes file the SAME budget-line code with the SAME
    scenario and DISTINCT amounts, so which page a row reaches can only come
    from the document's own appropriation — never from the prose, and never
    from an amount that happens to be unique.

    The third volume carries a narrative and no accounted detail row at all,
    which is how a narrative becomes unattributable in the real corpus: the
    account lives on the P-40 detail rows (migration 007), so a book that
    files none says nothing about which of two programs its prose describes.
    Ruling 2 sends it to NEITHER page.

    status stays 'registered': the export's PDF copy step only walks
    'downloaded' documents and these volumes have no bytes on disk. The detail
    and narrative queries filter on sha256, not status.
    """
    with psycopg.connect(dsn, autocommit=True) as con:
        for i, (title, sha, account, n_title, n_body) in enumerate(_VOLUMES):
            doc_id = con.execute(
                "insert into jbook_documents (org, exhibit_family, fiscal_year,"
                " title, source_url, sha256, status) values"
                " ('N','procurement',2026,%s,%s,%s,'registered') returning id",
                (title, f"https://example.test/{title}", sha),
            ).fetchone()[0]
            run_id = con.execute(
                "insert into extraction_runs (document_id, tier, tool_versions)"
                " values (%s, 1, '{}') returning id",
                (doc_id,),
            ).fetchone()[0]
            con.execute(
                "insert into detail_narratives (extraction_run_id, document_id,"
                " pe_bli, kind, title, body, xml_path)"
                " values (%s,%s,'3010','mission',%s,%s,%s)",
                (run_id, doc_id, n_title, n_body, f"LineItem[{i}]/Narrative"),
            )
            if account is None:
                continue
            con.execute(
                "insert into budget_line_details (extraction_run_id,"
                " document_id, pe_bli, scenario, amount_millions, xml_path,"
                " account) values (%s,%s,'3010','BudgetYearOne',%s,%s,%s)",
                (run_id, doc_id, 100.0 + i, f"LineItem[{i}]", account),
            )


def _make_collision_duckdb(db_path: Path) -> None:
    """The shared 1-row mart fixture, widened to the E1 (account, pe_bli)
    grain and given 3010's two members plus one account-keyed link each."""
    from jbooks.test_export_site_pg import _make_test_duckdb

    _make_test_duckdb(db_path)
    con = duckdb.connect(str(db_path))
    con.execute("alter table dim_programs add column account varchar")
    con.execute("alter table dim_programs add column account_title varchar")
    con.execute(
        "insert into dim_programs (pe_bli, title, org, exhibit_family,"
        " project_count, fy2024_actual_millions, fully_reconciled, account,"
        " account_title) values"
        f" ('3010','LPD Flight II','N','procurement',0,10.0,true,'{SCN}','{SCN_TITLE}'),"
        f" ('3010','Shipboard Tactical Communications','N','procurement',0,"
        f"  5.0,true,'{OPN}','{OPN_TITLE}')"
    )
    con.execute(
        "insert into fct_budget_to_awards (pe_bli, exhibit, fiscal_year,"
        " organization, award_piid, recipient_name, recipient_uei, method,"
        " confidence, program_title, account) values"
        f" ('3010','P-1',2026,'N','N0002420C0001','Huntington Ingalls','UEI1',"
        f"  'fpds-ap','medium','LPD Flight II','{SCN}'),"
        f" ('3010','P-1',2026,'N','N0003917D0006','Serco','UEI2',"
        f"  'fpds-ap','medium','Shipboard Tactical Communications','{OPN}')"
    )
    # District rows on the SAME shared code. Since Task 27 (2026-09-19)
    # fct_district_programs is grained on (state, district, pe_bli, ACCOUNT)
    # and carries both the account and the per-account program_title of the
    # member whose high-confidence links produced the dollars, so the exporter
    # addresses each row by that member's own split key rather than guessing
    # one from the title.
    #
    #   VA-08 gets BOTH members — the two-members-one-district case the
    #     account grain exists for, and the shape the pre-Task-27 model would
    #     have fused into one card under min(program_title);
    #   CO-05 gets the SECOND member alone (1810N), the one a last-wins
    #     prog_titles lookup happens to land on;
    #   TX-01 gets a NULL-account row on the same shared code — an account
    #     that names BOTH members, so the honest destination is the
    #     disambiguation stub and the honest label names both.
    con.execute(
        "insert into fct_district_programs values"
        f" ('VA','VA-08','3010','{SCN}','LPD Flight II','N',3,2,1,900000.0),"
        f" ('VA','VA-08','3010','{OPN}','Shipboard Tactical Communications',"
        f"  'N',1,1,1,400000.0),"
        f" ('CO','CO-05','3010','{OPN}','Shipboard Tactical Communications',"
        f"  'N',2,1,1,100000.0),"
        f" ('TX','TX-01','3010',null,'LPD Flight II','N',1,1,1,50000.0)"
    )
    # ROADMAP #82: a mart figure for the shared code, so the exporter has
    # something to WITHHOLD (both members carry a link above) rather than a
    # plain absence. Column order is the live two-basis one (ROADMAP #80):
    # (pe_bli, hhi_all, top_family_all, family_count_all, award_count_all,
    #  program_dollars_all, hhi_high, top_family_high, family_count_high,
    #  award_count_high, program_dollars_high) — the *_high values clear the
    # high-only floor, so this figure WOULD publish if it were either
    # member's.
    con.execute(
        "insert into fct_program_concentration values"
        " ('3010', 8411.8, 'HUNTINGTON INGALLS INDUSTRIES', 3, 8, 3059296982.0,"
        "  8411.8, 'HUNTINGTON INGALLS INDUSTRIES', 3, 8, 3059296982.0)"
    )
    # ROADMAP #82 (mention axis), fix round 1: lobbying rows on the shared
    # code, one per evidence tier. fct_program_lobbying is keyed on the BARE
    # pe_bli (it has no account column and a Senate LDA filing carries
    # nothing that could populate one), so ALL FOUR of these arrive at both
    # member pages and the exporter decides per row which page each is
    # evidence about:
    #   pe_literal  '3010'                      -> both (names the LINE)
    #   multi_token 'Shipboard|Communications'  -> the OPN member only
    #   alias       'Flight'                    -> the SCN member only
    #   multi_token 'Orphan|Volume'             -> NEITHER, and counted
    # The last is the mention-axis twin of the orphan J-book volume above:
    # terms that match no member's title are evidence about no member.
    _lob = (
        ("11111111-1111-4111-8111-111111111111", "3010", "pe_literal"),
        ("22222222-2222-4222-8222-222222222222", "Shipboard|Communications",
         "multi_token"),
        ("33333333-3333-4333-8333-333333333333", "Flight", "alias"),
        ("44444444-4444-4444-8444-444444444444", "Orphan|Volume", "multi_token"),
    )
    for _uuid, _term, _kind in _lob:
        con.execute(
            "insert into fct_program_lobbying values"
            " (?, '3010', 'LPD Flight II', ?, 'lobbied on the line',"
            "  ?, 'ACME LOBBYING', 'acme', '2025', ?)",
            (_uuid, _term, f"https://lda.senate.gov/filings/{_uuid}/", _kind),
        )
    con.close()


@pytest.fixture(scope="module")
def collision_export(collision_pg_dsn, tmp_path_factory):
    from govbudget.export_site import export_site

    tmp_path = tmp_path_factory.mktemp("collision")
    _seed_split_key_budget_lines(collision_pg_dsn)
    _seed_split_key_jbooks(collision_pg_dsn)
    db = tmp_path / "wh.duckdb"
    _make_collision_duckdb(db)
    site = tmp_path / "site"
    export_site(
        collision_pg_dsn, db, out_dir=site,
        pdf_base_url="https://cdn.example/pdfs",
    )
    return site


def _sidecar(site: Path, slug: str) -> dict:
    return json.loads((site / "json" / "program_details" / f"{slug}.json").read_text())


def test_each_member_page_carries_only_its_own_award(collision_export):
    scn = _sidecar(collision_export, "3010-SCN")
    opn = _sidecar(collision_export, "3010-OPN")
    assert [a["award_piid"] for a in scn["awards"]] == ["N0002420C0001"]
    assert [a["award_piid"] for a in opn["awards"]] == ["N0003917D0006"]


def test_the_two_member_pages_share_no_award(collision_export):
    scn = {a["award_piid"] for a in _sidecar(collision_export, "3010-SCN")["awards"]}
    opn = {a["award_piid"] for a in _sidecar(collision_export, "3010-OPN")["awards"]}
    assert scn and opn and not (scn & opn)


def test_no_bare_key_sidecar_is_written_for_a_split_key(collision_export):
    bare = collision_export / "json" / "program_details" / "3010.json"
    assert not bare.exists(), "the bare key is a disambiguation stub — it owns no links"


def test_programs_json_award_counts_are_per_member(collision_export):
    programs = json.loads(
        (collision_export / "json" / "programs.json").read_text()
    )
    by_slug = {p["slug"]: p for p in programs if p["pe_bli"] == "3010"}
    assert set(by_slug) == {"3010-SCN", "3010-OPN"}
    assert by_slug["3010-SCN"]["award_count"] == 1
    assert by_slug["3010-OPN"]["award_count"] == 1


def test_ordinary_program_award_attachment_is_unchanged(collision_export):
    """The 1-row fixture's ordinary PE keeps its own link — an account-NULL
    mart row must behave exactly as it did before this task."""
    d = _sidecar(collision_export, "0601101E")
    assert [a["award_piid"] for a in d["awards"]] == ["W911QX-24-C-0001"]


def _district(site: Path, code: str) -> dict:
    return json.loads((site / "json" / "districts" / f"{code}.json").read_text())


def _district_program(site: Path, code: str, split_key: str) -> dict:
    """The district row addressed by SPLIT KEY, not by bare pe_bli.

    Task 27: a district can hold one row per member of a shared code, so the
    bare pe_bli no longer identifies a row. split_key is the member slug
    ('3010-SCN'), and equals the pe_bli for every code that names one program.
    """
    rows = [
        p for p in _district(site, code)["programs"]
        if p["split_key"] == split_key
    ]
    assert len(rows) == 1, f"{code}: expected one {split_key} row, got {len(rows)}"
    return rows[0]


def test_a_district_card_names_the_member_whose_links_produced_the_dollars(
    collision_export,
):
    """The SECOND member by account order (1810N) — the one a last-wins
    prog_titles lookup happens to land on."""
    row = _district_program(collision_export, "CO-05", "3010-OPN")
    assert row["title"] == "Shipboard Tactical Communications"
    assert row["account"] == OPN


def test_a_district_card_on_the_first_member_is_not_relabelled_as_its_sibling(
    collision_export,
):
    """The reverse case — and the one last-wins got wrong. Since Task 27 the
    VA-08 fixture holds BOTH members, so this is about ONE of its rows: the
    1611N row's dollars are LPD Flight II's (the FIRST member by account
    order), and labelling that row 'Shipboard Tactical Communications' — the
    title of its sibling row on the same page — names a different program in
    a different appropriation."""
    row = _district_program(collision_export, "VA-08", "3010-SCN")
    assert row["title"] == "LPD Flight II"
    assert row["account"] == SCN


def test_an_ordinary_district_card_still_reads_its_program_title(collision_export):
    """The correction is scoped to shared codes: an ordinary pe_bli keeps the
    dim_programs title prog_titles has always given it."""
    row = _district_program(collision_export, "CO-05", "0601101E")
    assert row["title"] == "Defense Research Sciences"
    # An ordinary code's split key IS its pe_bli, and its account is NULL.
    assert row["split_key"] == "0601101E" and row["account"] is None


def test_link_citation_row_names_the_account_for_a_split_key(collision_export):
    """The link's provenance sentence must say WHICH member it links, or the
    citation is ambiguous between two programs sharing one code."""
    from govbudget.export_site import fact_id_derived

    by_fid = json.loads(
        (collision_export / "json" / "citations.json").read_text()
    )
    scn_fid = fact_id_derived(
        "budget_to_awards", "3010|N0002420C0001", "link")
    assert scn_fid in by_fid
    assert SCN in (by_fid[scn_fid].get("formula") or "")


def test_a_sidecar_award_row_carries_the_links_own_citation_fact_id(
    collision_export,
):
    """Chain-B fix 3: the sidecar award row and the citation row for the SAME
    (pe_bli, award_piid) pair carry the SAME fact_id.

    The sidecar is the dossier bundle's source, so an award row without a
    resolvable fact_id is an award a `players` claim cannot cite — the measured
    reason 3010-SCN's dossier named none of the five recipients its page
    publishes. The id is minted from the BARE pe_bli on both sides (never the
    page slug), which is what lets two members of one shared code each resolve
    their own links.
    """
    from govbudget.export_site import fact_id_derived

    by_fid = json.loads(
        (collision_export / "json" / "citations.json").read_text()
    )
    for slug, pe_bli, piid in (
        ("3010-SCN", "3010", "N0002420C0001"),
        ("3010-OPN", "3010", "N0003917D0006"),
        ("0601101E", "0601101E", "W911QX-24-C-0001"),
    ):
        rows = _sidecar(collision_export, slug)["awards"]
        assert [a["award_piid"] for a in rows] == [piid]
        expected = fact_id_derived(
            "budget_to_awards", f"{pe_bli}|{piid}", "link")
        assert rows[0]["fact_id"] == expected, slug
        assert expected in by_fid, slug


def test_every_sidecar_award_fact_id_resolves_or_is_null(collision_export):
    """The field is guarded, not assumed: it is populated only when the
    citation row was actually minted (the `_cited_fact_ids` test), so a
    non-null value always resolves and a null one is an honest absence."""
    by_fid = json.loads(
        (collision_export / "json" / "citations.json").read_text()
    )
    details = collision_export / "json" / "program_details"
    seen = 0
    for path in sorted(details.glob("*.json")):
        for award in json.loads(path.read_text()).get("awards", []):
            assert "fact_id" in award, path.stem
            if award["fact_id"] is not None:
                assert award["fact_id"] in by_fid, (path.stem, award["award_piid"])
                seen += 1
    assert seen >= 3, "fixture should publish at least the three linked awards"


# ---------------------------------------------------------------------------
# (c) ROADMAP #82 — links from other surfaces reach the member, and a figure
#     withheld from both members is said, not hidden
# ---------------------------------------------------------------------------


def test_a_district_card_on_a_shared_code_links_the_member_page(collision_export):
    """The mart title names the member whose high-confidence links produced
    the dollars; the card links THAT page, not the bare-key chooser."""
    assert _district_program(collision_export, "VA-08", "3010-SCN")["program_url"] == "/program/3010-SCN/"
    assert _district_program(collision_export, "CO-05", "3010-OPN")["program_url"] == "/program/3010-OPN/"


def test_an_ordinary_district_card_still_links_its_bare_key(collision_export):
    assert _district_program(collision_export, "CO-05", "0601101E")["program_url"] == "/program/0601101E/"


def test_both_members_of_a_shared_code_in_one_district_keep_their_own_row(
    collision_export,
):
    """Task 27, the case the whole grain change exists for.

    VA-08's sidecar carries BOTH members of '3010'. Before the account joined
    fct_district_programs' grain these were one row whose dollars were the sum
    of two programs' money and whose label was min(program_title) — ROADMAP
    #56's fusion shape, with every number<->citation gate still green because
    each underlying link is individually true. Two rows, two titles, two member
    pages, two distinct fact_ids, and the published
    total_obligation:desc order.
    """
    rows = [
        p for p in _district(collision_export, "VA-08")["programs"]
        if p["pe_bli"] == "3010"
    ]
    assert [p["split_key"] for p in rows] == ["3010-SCN", "3010-OPN"]
    assert [p["account"] for p in rows] == [SCN, OPN]
    assert [p["title"] for p in rows] == [
        "LPD Flight II", "Shipboard Tactical Communications",
    ]
    assert [p["program_url"] for p in rows] == [
        "/program/3010-SCN/", "/program/3010-OPN/",
    ]
    assert [p["total_obligation"] for p in rows] == [900000.0, 400000.0]
    # Two members, two facts: one fact_id per member, both resolvable.
    fids = [p["fact_id"] for p in rows]
    assert len(set(fids)) == 2 and all(fids), fids
    by_fid = json.loads(
        (collision_export / "json" / "citations.json").read_text()
    )
    assert all(f in by_fid for f in fids)
    # The whole page stays in its published order, which gate 24 leg f reads
    # off the rendered table (data-sort-order="total_obligation:desc").
    page = [p["total_obligation"] for p in _district(collision_export, "VA-08")["programs"]]
    assert page == sorted(page, reverse=True), page


def test_the_two_members_fact_ids_key_on_the_account(collision_export):
    """The ids are the helper's, per member — not one id for the bare pair.

    The four sites that mint a district_program fact_id all call
    _district_program_key, so this pins the shape at the only place a reader
    ever sees it: the sidecar.
    """
    from govbudget.export_site import _district_program_key, fact_id_usaspending

    ident = _district_identity()
    for split_key, account in (("3010-SCN", SCN), ("3010-OPN", OPN)):
        row = _district_program(collision_export, "VA-08", split_key)
        assert row["fact_id"] == fact_id_usaspending(
            "district_program",
            _district_program_key(ident, "VA", "VA-08", "3010", account),
            "total_obligation",
        )
    # An ordinary row's key is the bare triple, byte for byte — the
    # /fact/{id} permalinks minted before Task 27 still resolve.
    ordinary = _district_program(collision_export, "VA-08", "0601101E")
    assert ordinary["fact_id"] == fact_id_usaspending(
        "district_program", "VA|VA-08|0601101E", "total_obligation")


def test_a_null_account_row_on_a_shared_code_keeps_the_stub(collision_export):
    """An account-NULL row names BOTH members, so it may not name one.

    This is the case the narrowed
    assert_district_programs_single_member_high_links still guards in dbt, and
    the exporter's half of the same rule: no guessed member. The label is the
    both-members one shared_code_program_label mints for a link to the
    disambiguation stub, and the link is that stub.
    """
    row = _district_program(collision_export, "TX-01", "3010")
    assert row["account"] is None
    assert row["program_url"] == "/program/3010/"
    assert row["title"] == "LPD Flight II / Shipboard Tactical Communications"


def test_both_linked_members_carry_the_withheld_flag_and_no_hhi(collision_export):
    """Both 3010 members carry a link and the mart has a bare-key figure: it
    is neither member's, programs.json publishes hhi=null on each, and the
    sidecar says WHY so the page does not claim the crosswalk is silent.

    This is the end-to-end pin on the exporter's withheld marker (green the
    moment the fixture row above exists) — the red for the builder change is
    the unit suite in tests/test_who_gets_it_fallbacks.py."""
    for slug in ("3010-SCN", "3010-OPN"):
        assert _sidecar(collision_export, slug)["summary"]["concentration_withheld"] is True
    programs = json.loads((collision_export / "json" / "programs.json").read_text())
    by_slug = {p["slug"]: p for p in programs}
    assert by_slug["3010-SCN"]["hhi"] is None
    assert by_slug["3010-OPN"]["hhi"] is None
    assert by_slug["0601101E"]["hhi"] is not None
    assert _sidecar(collision_export, "0601101E")["summary"]["concentration_withheld"] is False


# ---------------------------------------------------------------------------
# (c) ROADMAP #82, the narrative axis: each member publishes its OWN J-book
# ---------------------------------------------------------------------------
#
# Measured 2026-09-12 on the shipped corpus, BEFORE this fix: all 13 shared
# codes published identical `narratives` and identical `details` on every
# member — 55 narrative and 139 detail fact ids appearing on more than one
# member page. /program/3010-SCN/ rendered the Shipboard Tactical
# Communications mission paragraph and the OPN volume's money under the LPD
# Flight II heading, and every citation on it resolved, because each row is
# individually true of SOMETHING. The discriminator is the row's own J-book
# document: the SCN volume and the OPN volume are different books.


def _fids(sidecar: dict, kind: str) -> set:
    return {r["fact_id"] for r in sidecar[kind] if r.get("fact_id")}


def test_each_member_publishes_only_its_own_volumes_narratives(collision_export):
    scn = _sidecar(collision_export, "3010-SCN")
    opn = _sidecar(collision_export, "3010-OPN")
    assert [n["title"] for n in scn["narratives"]] == ["LPD Flight II — Mission"]
    assert [n["title"] for n in opn["narratives"]] == [
        "Shipboard Tactical Comms — Mission"
    ]


def test_each_member_publishes_only_its_own_volumes_details(collision_export):
    scn = _sidecar(collision_export, "3010-SCN")
    opn = _sidecar(collision_export, "3010-OPN")
    assert [d["amount_millions"] for d in scn["details"]] == [100.0]
    assert [d["amount_millions"] for d in opn["details"]] == [101.0]


def test_no_narrative_or_detail_fact_id_reaches_both_members(collision_export):
    """The property gate 21 leg n check 8 asserts on the built corpus."""
    scn = _sidecar(collision_export, "3010-SCN")
    opn = _sidecar(collision_export, "3010-OPN")
    for kind in ("narratives", "details"):
        shared = _fids(scn, kind) & _fids(opn, kind)
        assert shared == set(), (kind, shared)
        assert _fids(scn, kind), f"{kind}: SCN must publish something to check"
        assert _fids(opn, kind), f"{kind}: OPN must publish something to check"


def test_a_volume_belonging_to_neither_member_publishes_on_neither(
    collision_export,
):
    """ROADMAP #82 ruling 2. The orphan volume files a 3010 narrative and no
    accounted detail row, so nothing in it says which of the two programs it
    describes — the live shape is the PROC_DoDEA volume, which files rows
    under code '30' for an organization that has no page. A row no member
    owns publishes on NO page; publishing it on both is the defect, and
    picking one would be a guess."""
    for slug in ("3010-SCN", "3010-OPN"):
        side = _sidecar(collision_export, slug)
        assert "Orphan Volume — Mission" not in [
            n["title"] for n in side["narratives"]
        ]
    # and it does not reappear under the bare code either — the stub owns no
    # sidecar at all
    assert not (collision_export / "json" / "program_details" / "3010.json").exists()


def test_programs_json_narrative_count_is_per_member(collision_export):
    programs = json.loads((collision_export / "json" / "programs.json").read_text())
    by_slug = {p["slug"]: p for p in programs}
    assert by_slug["3010-SCN"]["narrative_count"] == 1
    assert by_slug["3010-OPN"]["narrative_count"] == 1


def test_an_ordinary_programs_narratives_are_unchanged(collision_export):
    """The re-keying collapses to (pe, None, None) for every unsplit code, so
    an ordinary page keeps whatever its bare key held."""
    side = _sidecar(collision_export, "0601101E")
    assert isinstance(side["narratives"], list)
    assert isinstance(side["details"], list)
    programs = json.loads((collision_export / "json" / "programs.json").read_text())
    by_slug = {p["slug"]: p for p in programs}
    assert by_slug["0601101E"]["narrative_count"] == len(side["narratives"])


# ---------------------------------------------------------------------------
# (d) ROADMAP #82, the MENTION axis (fix round 1): per-row attribution
# ---------------------------------------------------------------------------
#
# fct_program_lobbying is keyed on the bare pe_bli, so every mention on a
# shared code arrives at both members. WHICH member a row is evidence about
# is decided from the mart's own evidence, never from the filing's text:
# a `pe_literal` row names the budget LINE itself and is true of every
# program using it; a `multi_token`/`alias` row qualified by matching ONE
# title's terms and is evidence about the program whose title carries them —
# which is exactly what the rendered badge claims ("2+ distinct, non-generic
# words from this program's title").
#
# Measured 2026-09-18 on the shipped corpus: /program/0145-APN/ "F/A-18E/F
# (Fighter) Hornet" rendered 5 rows badged `General|Purpose` (its SIBLING is
# "General Purpose Bombs") and /program/1350-WPN/ "Missile Industrial
# Facilities" rendered 2 badged `Weapons|Ammunition`.


def _mention_terms(sidecar: dict) -> set:
    return {m["matched_term"] for m in sidecar["mentions"]}


def test_a_pe_literal_mention_publishes_on_every_member(collision_export):
    """The filing's text contains the code '3010' itself, which names the
    LINE and nothing finer — so it is evidence for both programs."""
    for slug in ("3010-SCN", "3010-OPN"):
        assert "3010" in _mention_terms(_sidecar(collision_export, slug))


def test_a_multi_token_mention_publishes_only_on_the_member_it_matched(
    collision_export,
):
    opn = _sidecar(collision_export, "3010-OPN")
    scn = _sidecar(collision_export, "3010-SCN")
    assert "Shipboard|Communications" in _mention_terms(opn)
    assert "Shipboard|Communications" not in _mention_terms(scn)


def test_an_alias_mention_publishes_only_on_the_member_it_matched(
    collision_export,
):
    scn = _sidecar(collision_export, "3010-SCN")
    opn = _sidecar(collision_export, "3010-OPN")
    assert "Flight" in _mention_terms(scn)          # "LPD Flight II"
    assert "Flight" not in _mention_terms(opn)


def test_a_mention_matching_no_member_title_publishes_on_neither(
    collision_export,
):
    """The mention-axis twin of the orphan volume: terms that appear in no
    member's title are evidence about no member, so the row publishes
    nowhere rather than on both."""
    for slug in ("3010-SCN", "3010-OPN"):
        assert "Orphan|Volume" not in _mention_terms(_sidecar(collision_export, slug))


def test_mentions_shared_code_declares_the_basis_per_evidence_kind(
    collision_export,
):
    """The declaration gate 21 leg n check 8 reads. A blanket `true` asserted
    the pe_literal rule over every row, which is false for a multi_token
    one."""
    scn = _sidecar(collision_export, "3010-SCN")
    opn = _sidecar(collision_export, "3010-OPN")
    assert scn["mentions_shared_code"] == {"pe_literal": "code", "alias": "title"}
    assert opn["mentions_shared_code"] == {
        "pe_literal": "code", "multi_token": "title",
    }


def test_every_title_basis_mention_is_true_of_the_page_that_renders_it(
    collision_export,
):
    """The property check 8 asserts on the built corpus, computed here from
    the page's own title."""
    programs = json.loads((collision_export / "json" / "programs.json").read_text())
    by_slug = {p["slug"]: p for p in programs}
    for slug in ("3010-SCN", "3010-OPN"):
        side = _sidecar(collision_export, slug)
        title = by_slug[slug]["title"]
        checked = 0
        for m in side["mentions"]:
            if m["evidence_kind"] == "pe_literal":
                continue
            checked += 1
            for term in m["matched_term"].split("|"):
                assert re.search(
                    r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])",
                    title,
                    re.IGNORECASE,
                ), (slug, title, term)
        assert checked, f"{slug} must render a title-basis mention to check"


def test_the_mention_census_line_names_the_row_that_matched_no_member(
    collision_export, collision_pg_dsn, tmp_path, capsys
):
    """The census print is the ONLY signal a row published on NEITHER member.

    Nothing renders such a row — that is the point — so if the print stopped
    firing, rows would disappear from the corpus in silence and the export log
    would say the corpus was clean. Driven here by the fixture's
    `Orphan|Volume`, the mention-axis twin of the orphan J-book volume.

    Re-exports rather than reading the module-scoped fixture's output, because
    capsys cannot see what a module-scoped fixture printed. `collision_export`
    is requested only to guarantee the Postgres seed is already in place.
    """
    from govbudget.export_site import export_site

    db = tmp_path / "census.duckdb"
    _make_collision_duckdb(db)
    capsys.readouterr()
    export_site(
        collision_pg_dsn, db, out_dir=tmp_path / "census-site",
        pdf_base_url="https://cdn.example/pdfs",
    )
    lines = [
        ln for ln in capsys.readouterr().out.splitlines()
        if "mention axis" in ln and "matched no member" in ln
    ]
    assert len(lines) == 1, lines
    assert "1 lobbying mention row(s)" in lines[0]
    assert "3010/Orphan|Volume" in lines[0]
    assert "NEITHER member" in lines[0]


def test_an_ordinary_programs_mentions_are_unchanged(collision_export):
    """Attribution runs only on a shared code; an unsplit program keeps the
    bare-code list and declares nothing."""
    side = _sidecar(collision_export, "0601101E")
    assert _mention_terms(side) == {"darpa"}
    assert "mentions_shared_code" not in side
