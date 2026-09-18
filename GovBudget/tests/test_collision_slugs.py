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
    con.execute("alter table fct_budget_to_awards add column account varchar")
    con.execute(
        "insert into fct_budget_to_awards (pe_bli, exhibit, fiscal_year,"
        " organization, award_piid, recipient_name, recipient_uei, method,"
        " confidence, program_title, account) values"
        f" ('3010','P-1',2026,'N','N0002420C0001','Huntington Ingalls','UEI1',"
        f"  'fpds-ap','medium','LPD Flight II','{SCN}'),"
        f" ('3010','P-1',2026,'N','N0003917D0006','Serco','UEI2',"
        f"  'fpds-ap','medium','Shipboard Tactical Communications','{OPN}')"
    )
    # Two district rows on the SAME shared code, one per member, in two
    # different districts. fct_district_programs is pe-grained and carries the
    # per-account program_title of the member whose high-confidence links
    # produced the dollars (fct_budget_to_awards resolves it through
    # (pe_bli, account)); the exporter must render THAT title rather than the
    # bare-code label. VA-08 gets the FIRST member by account order (1611N),
    # CO-05 the SECOND (1810N) — a last-wins prog_titles lookup renders the
    # second member's title on both.
    con.execute(
        "insert into fct_district_programs values"
        " ('VA','VA-08','3010','LPD Flight II','N',3,2,1,900000.0),"
        " ('CO','CO-05','3010','Shipboard Tactical Communications','N',"
        "  2,1,1,100000.0)"
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


def _district_program(site: Path, code: str, pe_bli: str) -> dict:
    rows = [p for p in _district(site, code)["programs"] if p["pe_bli"] == pe_bli]
    assert len(rows) == 1, f"{code}: expected one {pe_bli} row, got {len(rows)}"
    return rows[0]


def test_a_district_card_names_the_member_whose_links_produced_the_dollars(
    collision_export,
):
    """The SECOND member by account order (1810N) — the one a last-wins
    prog_titles lookup happens to land on."""
    row = _district_program(collision_export, "CO-05", "3010")
    assert row["title"] == "Shipboard Tactical Communications"


def test_a_district_card_on_the_first_member_is_not_relabelled_as_its_sibling(
    collision_export,
):
    """The reverse case — and the one last-wins got wrong. VA-08's dollars are
    LPD Flight II's (1611N, the FIRST member by account order); labelling them
    'Shipboard Tactical Communications' names a different program in a
    different appropriation."""
    row = _district_program(collision_export, "VA-08", "3010")
    assert row["title"] == "LPD Flight II"


def test_an_ordinary_district_card_still_reads_its_program_title(collision_export):
    """The correction is scoped to shared codes: an ordinary pe_bli keeps the
    dim_programs title prog_titles has always given it."""
    row = _district_program(collision_export, "CO-05", "0601101E")
    assert row["title"] == "Defense Research Sciences"


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
    assert _district_program(collision_export, "VA-08", "3010")["program_url"] == "/program/3010-SCN/"
    assert _district_program(collision_export, "CO-05", "3010")["program_url"] == "/program/3010-OPN/"


def test_an_ordinary_district_card_still_links_its_bare_key(collision_export):
    assert _district_program(collision_export, "CO-05", "0601101E")["program_url"] == "/program/0601101E/"


def test_member_slugs_by_title_refuses_identical_member_titles():
    """'2101' publishes "Tomahawk" in two appropriations — a title names
    nobody there, so no entry is minted and the district card keeps the stub."""
    from govbudget.export_site import _ProgramIdentity, member_slugs_by_title

    rows = [
        ("2101", "N", "procurement", "Tomahawk", 0, 1.0, True, "1109N", "Procurement, Marine Corps", None),
        ("2101", "N", "procurement", "Tomahawk", 0, 1.0, True, "1507N", "Weapons Procurement, Navy", None),
        ("3010", "N", "procurement", "LPD Flight II", 0, 1.0, True, SCN, SCN_TITLE, None),
        ("3010", "N", "procurement", "Shipboard Tactical Communications", 0, 1.0, True, OPN, OPN_TITLE, None),
        ("0601101E", "DARPA", "rdte", "Defense Research Sciences", 1, 1.0, True, None, None, None),
    ]
    # _ProgramIdentity rows are (pe_bli, account, account_title, organization, has_detail).
    ident = _ProgramIdentity([(r[0], r[7], r[8], r[1], True) for r in rows])
    out = member_slugs_by_title(rows, {"2101", "3010"}, ident)
    assert out == {
        ("3010", "LPD Flight II"): "3010-SCN",
        ("3010", "Shipboard Tactical Communications"): "3010-OPN",
    }


def test_member_slugs_by_title_never_names_an_org_split_member():
    """'20' DCSA/DTRA share one account, so fct_district_programs' title
    (resolved per (pe_bli, account)) cannot have picked one of them — a
    distinct-looking title there names nobody, and the stub is the honest
    destination. Org-split codes carry no crosswalk links today, so this
    guard is what keeps a future loader change from turning "no district
    rows" into "the wrong member"."""
    from govbudget.export_site import _ProgramIdentity, member_slugs_by_title

    rows = [
        ("20", "DTRA", "procurement", "Vehicles", 0, 1.0, True, "0300D", "Procurement, Defense-Wide", None),
        ("20", "DCSA", "procurement", "Major Equipment", 0, 1.0, True, "0300D", "Procurement, Defense-Wide", None),
        ("3010", "N", "procurement", "LPD Flight II", 0, 1.0, True, SCN, SCN_TITLE, None),
        ("3010", "N", "procurement", "Shipboard Tactical Communications", 0, 1.0, True, OPN, OPN_TITLE, None),
    ]
    ident = _ProgramIdentity([(r[0], r[7], r[8], r[1], True) for r in rows])
    out = member_slugs_by_title(rows, {"20", "3010"}, ident)
    assert set(out) == {
        ("3010", "LPD Flight II"),
        ("3010", "Shipboard Tactical Communications"),
    }


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
